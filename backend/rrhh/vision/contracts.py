"""Contracts, models, and configuration for computer vision attendance processing."""

from dataclasses import dataclass
from decimal import Decimal

# Tipos de jornada contractual soportados
JORNADA_8_HORAS = Decimal("8.0")
JORNADA_5_HORAS = Decimal("5.0")

# Umbral predeterminado de densidad de tinta para considerar una celda marcada (>2% de píxeles oscuros)
UMBRAL_DENSIDAD_TINTA_DEFAULT = 0.02


@dataclass(frozen=True)
class ConfiguracionEmpleado:
    """Configuración contractual y de turno para un empleado."""

    legajo: str
    nombre: str
    jornada_horas: Decimal = JORNADA_8_HORAS
    dia_franco_semanal: int | None = None  # 0 = Lunes, 6 = Domingo

    def __post_init__(self):
        if not self.legajo or not self.legajo.strip():
            raise ValueError("El legajo no puede estar vacío.")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre no puede estar vacío.")
        if self.jornada_horas <= Decimal(0):
            raise ValueError("La jornada laboral debe ser mayor a cero.")
        if self.dia_franco_semanal is not None and not (
            0 <= self.dia_franco_semanal <= 6
        ):
            raise ValueError(
                "El día de franco semanal debe ser un número entre 0 (Lunes) y 6 (Domingo)."
            )


@dataclass(frozen=True)
class CeldaExtraida:
    """Información visual y métricas de una celda individual de la planilla."""

    columna: str  # 'LEGAJO', 'NOMBRE', 'ENTRADA', 'SALIDA', 'FIRMA'
    densidad_tinta: float
    tiene_contenido: bool
    texto_leido: str | None = None


@dataclass(frozen=True)
class FilaPlanillaExtraida:
    """Fila detectada en la planilla física con sus celdas y métricas."""

    numero_fila: int
    legajo: str
    nombre: str
    densidad_firma: float
    tiene_firma: bool
    tiene_entrada: bool
    tiene_salida: bool
    hora_entrada: str | None = None
    hora_salida: str | None = None


@dataclass(frozen=True)
class ResultadoAsistenciaFila:
    """Resultado de clasificación de asistencia y cálculo para el banco de horas."""

    legajo: str
    nombre: str
    estado: str  # 'Presente', 'Falta sin aviso', 'Franco'
    horas_jornada: Decimal
    horas_trabajadas: Decimal
    diferencia_banco_horas: Decimal
    olvido_salida: bool
    observaciones: str

    def to_dict(self) -> dict[str, object]:
        return {
            "legajo": self.legajo,
            "nombre": self.nombre,
            "estado": self.estado,
            "horas_jornada": float(self.horas_jornada),
            "horas_trabajadas": float(self.horas_trabajadas),
            "diferencia_banco_horas": float(self.diferencia_banco_horas),
            "olvido_salida": self.olvido_salida,
            "observaciones": self.observaciones,
        }
