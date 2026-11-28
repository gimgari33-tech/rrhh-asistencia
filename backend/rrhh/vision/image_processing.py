"""Digital Image Processing (PDI) utilities for attendance sheets using OpenCV."""

import itertools

import cv2
import numpy as np

from .contracts import UMBRAL_DENSIDAD_TINTA_DEFAULT

# Lado máximo usado para buscar bordes: reduce costo y ruido de textura fina.
LADO_BUSQUEDA_PX = 1000


def ordenar_puntos(puntos: np.ndarray) -> np.ndarray:
    """Ordena 4 puntos en sentido horario: superior-izq, superior-der, inferior-der, inferior-izq."""
    rect = np.zeros((4, 2), dtype="float32")
    s = puntos.sum(axis=1)
    rect[0] = puntos[np.argmin(s)]
    rect[2] = puntos[np.argmax(s)]

    diff = np.diff(puntos, axis=1)
    rect[1] = puntos[np.argmin(diff)]
    rect[3] = puntos[np.argmax(diff)]
    return rect


def _a_gris(imagen: np.ndarray) -> np.ndarray:
    if len(imagen.shape) == 3:
        return cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    return imagen.copy()


def detectar_esquinas_hoja(imagen: np.ndarray) -> np.ndarray | None:
    """Busca el cuadrilátero más grande de la foto (los 4 bordes de la hoja).

    Devuelve los 4 vértices ordenados en coordenadas de la imagen original,
    o None si no hay un cuadrilátero convexo que ocupe al menos el 15 % del área.
    """
    if imagen is None or imagen.size == 0:
        raise ValueError("La imagen provista es inválida o está vacía.")

    alto, ancho = imagen.shape[:2]
    escala = min(1.0, LADO_BUSQUEDA_PX / max(alto, ancho))
    chica = cv2.resize(_a_gris(imagen), None, fx=escala, fy=escala)

    suave = cv2.GaussianBlur(chica, (5, 5), 0)
    bordes = cv2.Canny(suave, 50, 200)
    bordes = cv2.dilate(bordes, np.ones((3, 3), np.uint8), iterations=1)

    contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)

    area_minima = chica.shape[0] * chica.shape[1] * 0.15
    for c in contornos[:5]:
        if cv2.contourArea(c) < area_minima:
            break
        perimetro = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        if len(aprox) == 4 and cv2.isContourConvex(aprox):
            puntos = aprox.reshape(4, 2).astype("float32") / escala
            return ordenar_puntos(puntos)
    return None


def corregir_perspectiva(
    imagen: np.ndarray,
    esquinas: np.ndarray | None = None,
    ancho_destino: int | None = None,
    alto_destino: int | None = None,
) -> np.ndarray:
    """Corrige la perspectiva de una foto de planilla mediante homografía cuadrilátera.

    Si no se pasan `esquinas`, intenta detectarlas. Si no encuentra los 4 bordes
    lanza ValueError: no reescala en silencio, porque una hoja sin enderezar
    hace que las celdas no caigan donde deben.
    El tamaño de salida conserva la proporción real de la hoja salvo que se indique otro.
    """
    if imagen is None or imagen.size == 0:
        raise ValueError("La imagen provista es inválida o está vacía.")

    if esquinas is None:
        esquinas = detectar_esquinas_hoja(imagen)
    if esquinas is None:
        raise ValueError(
            "No se detectaron los 4 bordes de la hoja. Indicá las esquinas manualmente."
        )

    origen = ordenar_puntos(np.asarray(esquinas, dtype="float32").reshape(4, 2))
    if ancho_destino is None:
        ancho_destino = round(
            max(
                np.linalg.norm(origen[1] - origen[0]),
                np.linalg.norm(origen[2] - origen[3]),
            )
        )
    if alto_destino is None:
        alto_destino = round(
            max(
                np.linalg.norm(origen[3] - origen[0]),
                np.linalg.norm(origen[2] - origen[1]),
            )
        )

    destino = np.array(
        [
            [0, 0],
            [ancho_destino - 1, 0],
            [ancho_destino - 1, alto_destino - 1],
            [0, alto_destino - 1],
        ],
        dtype="float32",
    )
    matriz = cv2.getPerspectiveTransform(origen, destino)
    return cv2.warpPerspective(imagen, matriz, (ancho_destino, alto_destino))


def binarizar_imagen(imagen: np.ndarray, metodo: str = "otsu") -> np.ndarray:
    """Convierte la imagen a blanco y negro (tinta = 255) eliminando sombras e irregularidades de luz.

    Métodos:
      - "otsu": umbral global. Falla cuando la foto tiene sombra desigual.
      - "adaptativo": umbral local gaussiano.
      - "normalizado": divide por el fondo estimado (desenfoque grande) para
        quitar la sombra antes de aplicar Otsu. Es el que usa el pipeline por defecto.
    """
    if imagen is None or imagen.size == 0:
        raise ValueError("La imagen provista es inválida o está vacía.")

    gris = _a_gris(imagen)

    if metodo == "adaptativo":
        return cv2.adaptiveThreshold(
            gris,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21,
            10,
        )

    if metodo == "normalizado":
        # Kernel impar, grande respecto al trazo de la lapicera
        lado = (max(gris.shape[:2]) // 8) | 1
        fondo = cv2.medianBlur(gris, max(lado, 3))
        gris = cv2.divide(gris, fondo, scale=255)

    _, binarizada = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binarizada


def extraer_lineas_grilla(
    binarizada: np.ndarray,
    escala_h: int = 25,
    escala_v: int = 25,
) -> tuple[np.ndarray, np.ndarray]:
    """Aísla las líneas horizontales y verticales de la tabla mediante morfología matemática."""
    ancho = binarizada.shape[1]
    alto = binarizada.shape[0]

    kernel_h = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(10, ancho // escala_h), 1)
    )
    lineas_h = cv2.morphologyEx(binarizada, cv2.MORPH_OPEN, kernel_h)

    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, alto // escala_v)))
    lineas_v = cv2.morphologyEx(binarizada, cv2.MORPH_OPEN, kernel_v)

    return lineas_h, lineas_v


def detectar_posiciones_lineas(
    mascara: np.ndarray,
    eje: int,
    fraccion_minima: float = 0.4,
    separacion_minima: int = 8,
) -> list[int]:
    """Devuelve las posiciones (en píxeles) de las líneas de una máscara de grilla.

    `eje=0` para líneas horizontales (perfil por filas), `eje=1` para verticales.
    Un pico es una fila/columna con al menos `fraccion_minima` del máximo de tinta.
    Picos a menos de `separacion_minima` píxeles se fusionan en una sola línea.
    """
    if mascara is None or mascara.size == 0:
        return []
    # Tinta por fila (eje=0) o por columna (eje=1)
    perfil = np.count_nonzero(mascara, axis=1 if eje == 0 else 0)
    if perfil.max() == 0:
        return []

    candidatos = np.flatnonzero(perfil >= fraccion_minima * perfil.max())
    grupos: list[list[int]] = []
    for pos in candidatos:
        if grupos and pos - grupos[-1][-1] <= separacion_minima:
            grupos[-1].append(int(pos))
        else:
            grupos.append([int(pos)])
    return [round(float(np.mean(g))) for g in grupos]


def recortar_celdas(
    binarizada: np.ndarray,
    ys: list[int],
    xs: list[int],
    margen: int = 4,
) -> list[list[np.ndarray]]:
    """Recorta cada celda entre líneas consecutivas.

    Con n líneas horizontales (`ys`) y m verticales (`xs`) devuelve (n-1) filas de (m-1) celdas.
    `margen` se descuenta de cada borde para no incluir el grosor de las líneas.
    """
    filas = []
    for y0, y1 in itertools.pairwise(ys):
        fila = []
        for x0, x1 in itertools.pairwise(xs):
            fila.append(
                binarizada[y0 + margen : y1 - margen, x0 + margen : x1 - margen].copy()
            )
        filas.append(fila)
    return filas


def calcular_densidad_tinta(
    celda_binarizada: np.ndarray, margen_borde: int = 2
) -> float:
    """Calcula la proporción de píxeles oscuros (tinta) respecto al área útil de la celda."""
    if celda_binarizada is None or celda_binarizada.size == 0:
        return 0.0

    alto, ancho = celda_binarizada.shape[:2]
    if alto <= margen_borde * 2 or ancho <= margen_borde * 2:
        recorte = celda_binarizada
    else:
        # Excluye los bordes de la celda para no contar las líneas divisorias de la tabla
        recorte = celda_binarizada[
            margen_borde : alto - margen_borde, margen_borde : ancho - margen_borde
        ]

    pixeles_tinta = np.count_nonzero(recorte)
    total_pixeles = recorte.size
    return float(pixeles_tinta / total_pixeles) if total_pixeles > 0 else 0.0


def densidad_celda_limpia(celda_binarizada: np.ndarray) -> float:
    """Densidad de tinta tras una apertura 2x2 que elimina puntitos de ruido."""
    if celda_binarizada is None or celda_binarizada.size == 0:
        return 0.0
    limpia = cv2.morphologyEx(
        celda_binarizada, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)
    )
    return calcular_densidad_tinta(limpia)


def clasificar_celda_marcada(
    densidad: float,
    umbral: float = UMBRAL_DENSIDAD_TINTA_DEFAULT,
) -> bool:
    """Determina si una celda contiene escritura o firma según el umbral de tinta."""
    return bool(densidad >= umbral)
