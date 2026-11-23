"""Digital Image Processing (PDI) utilities for attendance sheets using OpenCV."""

import cv2
import numpy as np

from .contracts import UMBRAL_DENSIDAD_TINTA_DEFAULT


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


def corregir_perspectiva(
    imagen: np.ndarray,
    ancho_destino: int = 800,
    alto_destino: int = 1100,
) -> np.ndarray:
    """Corrige la perspectiva de una foto de planilla torcida mediante homografía cuadrilátera."""
    if imagen is None or imagen.size == 0:
        raise ValueError("La imagen provista es inválida o está vacía.")

    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen.copy()

    suave = cv2.GaussianBlur(gris, (5, 5), 0)
    bordes = cv2.Canny(suave, 50, 200)

    contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)

    cuadrilatero = None
    area_minima = imagen.shape[0] * imagen.shape[1] * 0.15

    for c in contornos:
        if cv2.contourArea(c) < area_minima:
            break
        perimetro = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        if len(aprox) == 4:
            cuadrilatero = aprox.reshape(4, 2)
            break

    if cuadrilatero is not None:
        puntos_origen = ordenar_puntos(cuadrilatero)
        puntos_destino = np.array(
            [
                [0, 0],
                [ancho_destino - 1, 0],
                [ancho_destino - 1, alto_destino - 1],
                [0, alto_destino - 1],
            ],
            dtype="float32",
        )
        matriz = cv2.getPerspectiveTransform(puntos_origen, puntos_destino)
        return cv2.warpPerspective(imagen, matriz, (ancho_destino, alto_destino))

    # Si no se detectan 4 bordes externos nítidos (hoja completa en plano), reescala proporcionalmente
    return cv2.resize(imagen, (ancho_destino, alto_destino))


def binarizar_imagen(imagen: np.ndarray, metodo: str = "otsu") -> np.ndarray:
    """Convierte la imagen a blanco y negro eliminando sombras e irregularidades de luz."""
    if imagen is None or imagen.size == 0:
        raise ValueError("La imagen provista es inválida o está vacía.")

    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen.copy()

    if metodo == "adaptativo":
        # Umbral adaptativo gaussiano para fotos con sombras desparejas
        return cv2.adaptiveThreshold(
            gris,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21,
            10,
        )

    # Por defecto Otsu: calcula el umbral bimodal óptimo
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


def clasificar_celda_marcada(
    densidad: float,
    umbral: float = UMBRAL_DENSIDAD_TINTA_DEFAULT,
) -> bool:
    """Determina si una celda contiene escritura o firma según el umbral de tinta."""
    return bool(densidad >= umbral)
