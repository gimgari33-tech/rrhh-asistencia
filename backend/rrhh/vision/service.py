"""Application and domain service connecting vision sheet extraction with attendance and time bank rules."""

from datetime import date, datetime
from decimal import Decimal

from ..domain.period import RegistroJornada
from ..domain.rules import CENT
from .contracts import (
    UMBRAL_DENSIDAD_TINTA_DEFAULT,
    ConfiguracionEmpleado,
    FilaPlanillaExtraida,
    ResultadoAsistenciaFila,
)


def calcular_horas_trabajadas(
    hora_entrada: str | None, hora_salida: str | None
) -> Decimal | None:
    """Calcula las horas reales trabajadas entre entrada y salida en formato HH:MM."""
    if not hora_entrada or not hora_salida:
        return None

    try:
        entrada_dt = datetime.strptime(hora_entrada.strip(), "%H:%M")
        salida_dt = datetime.strptime(hora_salida.strip(), "%H:%M")
    except ValueError:
        return None

    minutos = (salida_dt - entrada_dt).total_seconds() / 60
    if minutos < 0:
        # Cruce de medianoche (ej. 22:00 a 06:00)
        minutos += 24 * 60

    horas_decimal = Decimal(str(round(minutos / 60.0, 2))).quantize(CENT)
    return horas_decimal


class ServicioAsistenciaVision:
    """Servicio de orquestación de asistencia diaria basada en visión e integración con Banco de Horas."""

    def __init__(self, umbral_tinta: float = UMBRAL_DENSIDAD_TINTA_DEFAULT):
        self.umbral_tinta = umbral_tinta

    def clasificar_fila(
        self,
        fila: FilaPlanillaExtraida,
        configuracion: ConfiguracionEmpleado,
        fecha: date,
    ) -> ResultadoAsistenciaFila:
        """Aplica las reglas de negocio sobre la fila extraída de la planilla física."""
        es_dia_franco = (
            configuracion.dia_franco_semanal is not None
            and fecha.weekday() == configuracion.dia_franco_semanal
        )

        tiene_marca_asistencia = (
            fila.tiene_firma
            or fila.tiene_entrada
            or fila.densidad_firma >= self.umbral_tinta
            or bool(fila.hora_entrada)
        )

        # Regla 1: Si es su día de franco y no hay marcas, es FRANCO (estado neutral)
        if es_dia_franco and not tiene_marca_asistencia:
            return ResultadoAsistenciaFila(
                legajo=configuracion.legajo,
                nombre=configuracion.nombre,
                estado="Franco",
                horas_jornada=configuracion.jornada_horas,
                horas_trabajadas=Decimal("0.00"),
                diferencia_banco_horas=Decimal("0.00"),
                olvido_salida=False,
                observaciones="Franco semanal programado; estado neutral sin impacto en banco de horas.",
            )

        # Regla 2: Sin marcas y no es franco -> Falta sin aviso (descuenta la jornada contratada: 8h o 5h)
        if not tiene_marca_asistencia:
            return ResultadoAsistenciaFila(
                legajo=configuracion.legajo,
                nombre=configuracion.nombre,
                estado="Falta sin aviso",
                horas_jornada=configuracion.jornada_horas,
                horas_trabajadas=Decimal("0.00"),
                diferencia_banco_horas=(-configuracion.jornada_horas).quantize(CENT),
                olvido_salida=False,
                observaciones=f"Sin registro de ingreso. Descuenta jornada contratada ({configuracion.jornada_horas}h).",
            )

        # Regla 3: Si tiene entrada pero falta la salida ("se olvidan la salida -> presentes")
        horas_calculadas = calcular_horas_trabajadas(
            fila.hora_entrada, fila.hora_salida
        )

        if horas_calculadas is None:
            # Presente con olvido de fichaje de salida: se le reconoce la jornada contratada base
            return ResultadoAsistenciaFila(
                legajo=configuracion.legajo,
                nombre=configuracion.nombre,
                estado="Presente",
                horas_jornada=configuracion.jornada_horas,
                horas_trabajadas=configuracion.jornada_horas,
                diferencia_banco_horas=Decimal("0.00"),
                olvido_salida=True,
                observaciones="Presente. Fichaje de salida no registrado; se computa jornada contratada estándar.",
            )

        # Regla 4: Entrada y salida completas -> cálculo de horas reales vs jornada contratada
        diferencia = (horas_calculadas - configuracion.jornada_horas).quantize(CENT)
        if diferencia > Decimal("0.00"):
            detalle = f"Presente con horas extra a favor (+{diferencia}h)."
        elif diferencia < Decimal("0.00"):
            detalle = f"Presente con horas faltantes a compensar ({diferencia}h)."
        else:
            detalle = "Presente con cumplimiento exacto de jornada contratada."

        return ResultadoAsistenciaFila(
            legajo=configuracion.legajo,
            nombre=configuracion.nombre,
            estado="Presente",
            horas_jornada=configuracion.jornada_horas,
            horas_trabajadas=horas_calculadas,
            diferencia_banco_horas=diferencia,
            olvido_salida=False,
            observaciones=detalle,
        )

    def convertir_a_registros_jornada(
        self,
        resultados: list[ResultadoAsistenciaFila],
        fecha: date,
    ) -> list[RegistroJornada]:
        """Convierte los resultados del procesamiento visual al modelo de dominio RegistroJornada."""
        registros = []
        for r in resultados:
            registros.append(
                RegistroJornada(
                    fecha=fecha,
                    estado=r.estado,
                    horas_trabajadas=r.horas_trabajadas,
                )
            )
        return registros
