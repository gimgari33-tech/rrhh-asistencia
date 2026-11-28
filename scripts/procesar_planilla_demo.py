"""Pipeline de Procesamiento Digital de Imágenes (PDI) sobre una foto de planilla de asistencia.

Pasos (cuatro pasos de la práctica):
  1. Limpieza: corrección de perspectiva y binarización (normalizada, comparada con Otsu global).
  2. Reducción del entorno: recorte a la tabla detectada por las líneas de la grilla.
  3. Extracción: detección de líneas y recorte de cada celda ENTRADA y FIRMA.
  4. Decisión: densidad de tinta por celda contra un umbral -> Presente / Falta sin aviso.

Uso:
  python scripts/procesar_planilla_demo.py --imagen data/planillas/2026-11-05.jpg \
      --verdad data/planillas/2026-11-05_verdad.csv [--esquinas x1,y1,...,x4,y4] [--columnas x1,...,x6] [--umbral 0.02]

El CSV de verdad tiene columnas: fila,legajo,estado_real (Presente o Ausente), en el orden de la hoja.
"""

import argparse
import csv
import json
import os
import sys
from datetime import date
from decimal import Decimal

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.rrhh.vision.contracts import (
    UMBRAL_DENSIDAD_TINTA_DEFAULT,
    ConfiguracionEmpleado,
    FilaPlanillaExtraida,
)
from backend.rrhh.vision.image_processing import (
    binarizar_imagen,
    corregir_perspectiva,
    densidad_celda_limpia,
    detectar_posiciones_lineas,
    extraer_lineas_grilla,
    recortar_celdas,
)
from backend.rrhh.vision.service import ServicioAsistenciaVision

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PADRON = os.path.join(RAIZ, "static", "js", "empleados.json")

# Columnas de la planilla, de izquierda a derecha
COL_ENTRADA = 2
COL_FIRMA = 4
FILAS_ENCABEZADO = 1  # una banda de encabezado antes de los empleados
COLUMNAS_ESPERADAS = (
    6  # 6 líneas verticales = 5 columnas: LEGAJO, NOMBRE, ENTRADA, SALIDA, FIRMA
)


def cargar_padron() -> dict[str, dict]:
    with open(PADRON, encoding="utf-8") as f:
        return {str(e["legajo"]): e for e in json.load(f)}


def configuracion_desde_padron(
    legajo: str, padron: dict[str, dict]
) -> ConfiguracionEmpleado:
    dato = padron.get(legajo, {})
    horas = dato.get("horas_jornada_numero") or 8.0
    return ConfiguracionEmpleado(
        legajo=legajo,
        nombre=dato.get("nombre", f"Legajo {legajo}"),
        jornada_horas=Decimal(str(horas)),
        dia_franco_semanal=None,  # el padrón guarda el franco en texto, no como día
    )


def leer_verdad(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def dibujar_decision(
    warped: np.ndarray, ys: list[int], xs: list[int], estados: list[str]
) -> np.ndarray:
    salida = warped.copy()
    for i, estado in enumerate(estados):
        color = (0, 160, 0) if estado == "Presente" else (0, 0, 220)
        cv2.rectangle(
            salida,
            (xs[0], ys[i + FILAS_ENCABEZADO]),
            (xs[-1], ys[i + FILAS_ENCABEZADO + 1]),
            color,
            3,
        )
    return salida


def mosaico_celdas(
    filas: list[list[np.ndarray]],
    legajos: list[str],
    alto_celda: int = 40,
    ancho_celda: int = 160,
) -> np.ndarray:
    bloques = []
    for fila, legajo in zip(filas, legajos, strict=True):
        partes = []
        for celda in (fila[COL_ENTRADA], fila[COL_FIRMA]):
            partes.append(cv2.resize(celda, (ancho_celda, alto_celda)))
        bloque = np.hstack([np.full((alto_celda, 70), 40, np.uint8), *partes])
        cv2.putText(
            bloque,
            legajo,
            (4, alto_celda // 2 + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            255,
            1,
        )
        bloques.append(
            np.vstack([bloque, np.full((2, bloque.shape[1]), 128, np.uint8)])
        )
    return np.vstack(bloques)


def metricas(predicho: list[str], real: list[str]) -> dict:
    pares = list(zip(real, predicho, strict=True))
    vp = sum(1 for r, p in pares if r == "Ausente" and p == "Falta sin aviso")
    vn = sum(1 for r, p in pares if r == "Presente" and p == "Presente")
    fp = sum(1 for r, p in pares if r == "Presente" and p == "Falta sin aviso")
    fn = sum(1 for r, p in pares if r == "Ausente" and p == "Presente")
    total = len(pares)
    return {
        "filas": total,
        "exactitud": round((vp + vn) / total, 3) if total else None,
        "matriz": {"vp_ausente": vp, "vn_presente": vn, "fp": fp, "fn": fn},
        "precision_ausente": round(vp / (vp + fp), 3) if (vp + fp) else None,
        "recall_ausente": round(vp / (vp + fn), 3) if (vp + fn) else None,
        "errores": [
            {"indice": i, "real": r, "predicho": p}
            for i, (r, p) in enumerate(pares)
            if r != ("Ausente" if p == "Falta sin aviso" else "Presente")
        ],
    }


def procesar(args: argparse.Namespace) -> None:
    img = cv2.imread(args.imagen)
    if img is None:
        raise SystemExit(f"No se pudo leer la imagen: {args.imagen}")

    nombre = os.path.splitext(os.path.basename(args.imagen))[0]
    salida = args.salida or os.path.join(RAIZ, "docs", "pdi_evidencias", nombre)
    os.makedirs(salida, exist_ok=True)

    def guardar(nombre_archivo: str, imagen: np.ndarray) -> None:
        cv2.imwrite(os.path.join(salida, nombre_archivo), imagen)

    print(f"1. Imagen original: {img.shape}")
    guardar("01_original.jpg", img)

    esquinas = None
    if args.esquinas:
        esquinas = np.array(
            [float(v) for v in args.esquinas.split(",")], dtype="float32"
        ).reshape(4, 2)
    warped = corregir_perspectiva(img, esquinas=esquinas)
    guardar("02_perspectiva_corregida.jpg", warped)
    print(f"2. Perspectiva corregida: {warped.shape}")

    binarizada = binarizar_imagen(warped, metodo="normalizado")
    guardar("03_binarizada_normalizada.jpg", binarizada)
    guardar("03b_binarizada_otsu_global.jpg", binarizar_imagen(warped, metodo="otsu"))
    print("3. Binarización normalizada guardada (comparada con Otsu global).")

    lineas_h, lineas_v = extraer_lineas_grilla(binarizada)
    guardar("04_grilla_detectada.jpg", cv2.add(lineas_h, lineas_v))
    ys = detectar_posiciones_lineas(lineas_h, eje=0)
    xs = detectar_posiciones_lineas(lineas_v, eje=1)
    if args.columnas:
        xs = [int(v) for v in args.columnas.split(",")]
        print(f"   Columnas fijadas a mano: {xs}")
    print(
        f"4. Líneas detectadas: {len(ys)} horizontales, {len(xs)} verticales (se esperan {COLUMNAS_ESPERADAS})."
    )
    verdad = leer_verdad(args.verdad) if args.verdad else []
    if len(xs) != COLUMNAS_ESPERADAS:
        mensaje = (
            f"Se detectaron {len(xs)} líneas verticales y la planilla tiene {COLUMNAS_ESPERADAS}. "
            "Revisar 04 o indicar --columnas x1,...,x6."
        )
        if verdad:
            raise SystemExit(f"No se mide: {mensaje}")
        print(f"   ADVERTENCIA: {mensaje}")

    filas_celdas = recortar_celdas(binarizada, ys, xs)[FILAS_ENCABEZADO:]
    if verdad and len(verdad) != len(filas_celdas):
        raise SystemExit(
            f"La grilla tiene {len(filas_celdas)} filas de empleados y el CSV de verdad {len(verdad)}. "
            "Revisar 04 o ajustar --esquinas."
        )
    legajos = (
        [r["legajo"] for r in verdad]
        if verdad
        else [f"fila{i + 1}" for i in range(len(filas_celdas))]
    )
    guardar("05_celdas_recortadas.jpg", mosaico_celdas(filas_celdas, legajos))

    # Decisión: densidad medida por celda -> FilaPlanillaExtraida -> reglas del servicio
    padron = cargar_padron()
    servicio = ServicioAsistenciaVision(umbral_tinta=args.umbral)
    fecha = date.today()
    resultados, estados = [], []
    for i, (fila, legajo) in enumerate(
        zip(filas_celdas, legajos, strict=True), start=1
    ):
        d_entrada = densidad_celda_limpia(fila[COL_ENTRADA])
        d_firma = densidad_celda_limpia(fila[COL_FIRMA])
        extraida = FilaPlanillaExtraida(
            numero_fila=i,
            legajo=legajo,
            nombre="",
            densidad_firma=d_firma,
            tiene_firma=d_firma >= args.umbral,
            tiene_entrada=d_entrada >= args.umbral,
            tiene_salida=False,
        )
        res = servicio.clasificar_fila(
            extraida, configuracion_desde_padron(legajo, padron), fecha
        )
        estados.append(res.estado)
        resultados.append(
            {
                "fila": i,
                "legajo": legajo,
                "densidad_entrada": round(d_entrada, 4),
                "densidad_firma": round(d_firma, 4),
                "estado": res.estado,
                "observaciones": res.observaciones,
            }
        )
    guardar("06_decision.jpg", dibujar_decision(warped, ys, xs, estados))

    with open(os.path.join(salida, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    if verdad:
        real = [r["estado_real"] for r in verdad]
        met = metricas(estados, real)
        met["umbral"] = args.umbral
        met["imagen"] = os.path.basename(args.imagen)
        with open(os.path.join(salida, "metricas.json"), "w", encoding="utf-8") as f:
            json.dump(met, f, indent=2, ensure_ascii=False)
        print(
            f"5. Exactitud {met['exactitud']} | recall Ausente {met['recall_ausente']} | errores {len(met['errores'])}"
        )
    print(f"Salidas en: {salida}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--imagen", required=True, help="Foto de la planilla")
    parser.add_argument("--verdad", help="CSV con fila,legajo,estado_real para medir")
    parser.add_argument(
        "--esquinas", help="Esquinas manuales x1,y1,x2,y2,x3,y3,x4,y4 si no se detectan"
    )
    parser.add_argument(
        "--columnas",
        help="Líneas verticales x1,...,x6 si la detección automática falla",
    )
    parser.add_argument("--umbral", type=float, default=UMBRAL_DENSIDAD_TINTA_DEFAULT)
    parser.add_argument(
        "--salida", help="Carpeta de salida (por defecto docs/pdi_evidencias/<nombre>)"
    )
    procesar(parser.parse_args())


if __name__ == "__main__":
    main()
