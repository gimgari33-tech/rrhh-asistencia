"""Computer vision module for attendance sheet processing and bank hour integration."""

from .contracts import (
    JORNADA_5_HORAS,
    JORNADA_8_HORAS,
    UMBRAL_DENSIDAD_TINTA_DEFAULT,
    CeldaExtraida,
    ConfiguracionEmpleado,
    FilaPlanillaExtraida,
    ResultadoAsistenciaFila,
)
from .image_processing import (
    binarizar_imagen,
    calcular_densidad_tinta,
    clasificar_celda_marcada,
    corregir_perspectiva,
    extraer_lineas_grilla,
    ordenar_puntos,
)
from .service import (
    ServicioAsistenciaVision,
    calcular_horas_trabajadas,
)

__all__ = [
    "JORNADA_5_HORAS",
    "JORNADA_8_HORAS",
    "UMBRAL_DENSIDAD_TINTA_DEFAULT",
    "CeldaExtraida",
    "ConfiguracionEmpleado",
    "FilaPlanillaExtraida",
    "ResultadoAsistenciaFila",
    "ServicioAsistenciaVision",
    "binarizar_imagen",
    "calcular_densidad_tinta",
    "calcular_horas_trabajadas",
    "clasificar_celda_marcada",
    "corregir_perspectiva",
    "extraer_lineas_grilla",
    "ordenar_puntos",
]
