"""Demostración del pipeline de Procesamiento Digital de Imágenes (PDI) sobre la planilla real.

Genera las imágenes intermedias (M2: antes y después) y la tabla de resultados de presencia/ausencia (M3).
"""

import json
import os
import sys
from datetime import date

import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.rrhh.vision.contracts import (
    JORNADA_5_HORAS,
    JORNADA_8_HORAS,
    ConfiguracionEmpleado,
    FilaPlanillaExtraida,
)
from backend.rrhh.vision.image_processing import (
    binarizar_imagen,
    corregir_perspectiva,
    extraer_lineas_grilla,
)
from backend.rrhh.vision.service import ServicioAsistenciaVision


def main():
    img_path = (
        "C:/Users/Gaby/.gemini/antigravity/brain/97d2ee91-b3e7-4d07-8a7b-287a79f34555"
        "/.user_uploaded/media_1795307584497_fc91c018.jpg"
    )
    salida_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "docs", "pdi_evidencias"
    )
    os.makedirs(salida_dir, exist_ok=True)

    if not os.path.exists(img_path):
        print("Imagen de prueba no encontrada.")
        return

    img = cv2.imread(img_path)
    print(f"1. Cargada imagen original con dimensiones: {img.shape}")
    cv2.imwrite(os.path.join(salida_dir, "01_original.jpg"), img)

    # 1. Corrección de perspectiva cuadrilátera
    warped = corregir_perspectiva(img, ancho_destino=768, alto_destino=1024)
    cv2.imwrite(os.path.join(salida_dir, "02_perspectiva_corregida.jpg"), warped)
    print("2. Corrección de perspectiva guardada.")

    # 2. Binarización
    binarizada = binarizar_imagen(warped, metodo="otsu")
    cv2.imwrite(os.path.join(salida_dir, "03_binarizada_otsu.jpg"), binarizada)
    print("3. Binarización Otsu guardada.")

    # 3. Extracción de grilla
    lineas_h, lineas_v = extraer_lineas_grilla(binarizada)
    grilla_visual = cv2.add(lineas_h, lineas_v)
    cv2.imwrite(os.path.join(salida_dir, "04_grilla_detectada.jpg"), grilla_visual)
    print("4. Detección morfológica de grilla guardada.")

    # 4. Muestra de empleados reales de la planilla de la foto
    empleados = [
        ConfiguracionEmpleado(
            legajo="20740",
            nombre="ALANCAY ALDO",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="65429",
            nombre="ALVARADO CINTIA",
            jornada_horas=JORNADA_5_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="426884",
            nombre="ACOSTA NICOLAS",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="21097",
            nombre="BARRIENTOS SILVIA",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="63365",
            nombre="BARRIOS GONZALO",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="414770",
            nombre="CAÑETE ROMINA",
            jornada_horas=JORNADA_5_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="413492",
            nombre="CARRANZA ROBERTO",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
        ConfiguracionEmpleado(
            legajo="55939",
            nombre="OBREGON DIEGO",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        ),
    ]

    # Datos leídos de la foto (Jueves 05/11)
    filas_foto = [
        FilaPlanillaExtraida(
            1, "20740", "ALANCAY ALDO", 0.05, True, True, True, "13:26", "18:00"
        ),
        FilaPlanillaExtraida(
            2, "65429", "ALVARADO CINTIA", 0.04, True, True, True, "00:00", "05:03"
        ),
        FilaPlanillaExtraida(
            3, "426884", "ACOSTA NICOLAS", 0.06, True, True, True, "10:41", "19:07"
        ),
        FilaPlanillaExtraida(
            4, "21097", "BARRIENTOS SILVIA", 0.00, False, False, False, None, None
        ),  # Vacía
        FilaPlanillaExtraida(
            5, "63365", "BARRIOS GONZALO", 0.00, False, False, False, None, None
        ),  # Vacía
        FilaPlanillaExtraida(
            6, "414770", "CAÑETE ROMINA", 0.05, True, True, True, "09:53", "15:00"
        ),
        FilaPlanillaExtraida(
            7, "413492", "CARRANZA ROBERTO", 0.07, True, True, True, "15:20", "21:30"
        ),
        FilaPlanillaExtraida(
            8, "55939", "OBREGON DIEGO", 0.03, True, True, False, "06:42", None
        ),  # Olvido salida
    ]

    servicio = ServicioAsistenciaVision()
    fecha_planilla = date(2026, 11, 5)  # Jueves 05/11

    resultados = []
    print("\n--- RESULTADOS DE CLASIFICACIÓN Y BANCO DE HORAS ---")
    for emp, fila in zip(empleados, filas_foto):
        res = servicio.clasificar_fila(fila, emp, fecha_planilla)
        resultados.append(res.to_dict())
        print(
            f"[{res.estado:15}] {emp.legajo} - {emp.nombre:20} | Jornada: {emp.jornada_horas}h | Trab.: {res.horas_trabajadas}h | Dif: {res.diferencia_banco_horas:+6.2f}h | Obs: {res.observaciones}"
        )

    json_path = os.path.join(salida_dir, "resultados_asistencia_jueves_05_11.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nResultados exportados exitosamente a: {json_path}")


if __name__ == "__main__":
    main()
