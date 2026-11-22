"""Domain models and rules for monthly work periods and bank hour balance cuts."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from .errors import ValidationError
from .models import HourMovement
from .rules import ATTENDANCE_STATUSES, CENT, MAX_HOURS


@dataclass(frozen=True)
class PeriodoLaboral:
    """Monthly labor cycle running from the 15th of month M to the 14th of month M+1."""

    fecha_inicio: date
    fecha_fin: date

    def __post_init__(self):
        if not isinstance(self.fecha_inicio, date) or not isinstance(
            self.fecha_fin, date
        ):
            raise ValidationError(
                "Las fechas de inicio y fin del período deben ser objetos date válidos."
            )

        if self.fecha_inicio.day != 15:
            raise ValidationError(
                f"La fecha de inicio debe ser el día 15 del mes. Recibido: {self.fecha_inicio.isoformat()}."
            )

        if self.fecha_fin.day != 14:
            raise ValidationError(
                f"La fecha de fin debe ser el día 14 del mes siguiente. Recibido: {self.fecha_fin.isoformat()}."
            )

        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio."
            )

        # Verify that fecha_fin is indeed in the consecutive month
        expected_next_month = (
            1 if self.fecha_inicio.month == 12 else self.fecha_inicio.month + 1
        )
        expected_next_year = (
            self.fecha_inicio.year + 1
            if self.fecha_inicio.month == 12
            else self.fecha_inicio.year
        )
        if (
            self.fecha_fin.month != expected_next_month
            or self.fecha_fin.year != expected_next_year
        ):
            raise ValidationError(
                f"El período debe cerrar el 14 del mes inmediato siguiente ({expected_next_year}-{expected_next_month:02d}-14)."
            )

    @classmethod
    def desde_fecha(cls, fecha: date | str) -> "PeriodoLaboral":
        """Build the labor cycle that contains the given date."""
        if isinstance(fecha, str):
            try:
                parsed_fecha = date.fromisoformat(fecha)
            except ValueError:
                raise ValidationError(
                    "La fecha debe tener el formato AAAA-MM-DD."
                ) from None
        elif isinstance(fecha, date):
            parsed_fecha = fecha
        else:
            raise ValidationError("La fecha proporcionada no es válida.")

        year = parsed_fecha.year
        month = parsed_fecha.month

        if parsed_fecha.day >= 15:
            start_date = date(year, month, 15)
            next_month = 1 if month == 12 else month + 1
            next_year = year + 1 if month == 12 else year
            end_date = date(next_year, next_month, 14)
        else:
            end_date = date(year, month, 14)
            prev_month = 12 if month == 1 else month - 1
            prev_year = year - 1 if month == 1 else year
            start_date = date(prev_year, prev_month, 15)

        return cls(fecha_inicio=start_date, fecha_fin=end_date)

    def contiene(self, fecha: date | str) -> bool:
        """Check if a date falls within this period (inclusive)."""
        if isinstance(fecha, str):
            try:
                parsed = date.fromisoformat(fecha)
            except ValueError:
                return False
        else:
            parsed = fecha
        return self.fecha_inicio <= parsed <= self.fecha_fin

    def dias_totales(self) -> int:
        """Return total calendar days in this period."""
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def etiqueta(self) -> str:
        """Human-readable period label."""
        return f"{self.fecha_inicio.isoformat()} al {self.fecha_fin.isoformat()}"

    def to_dict(self) -> dict:
        return {
            "fecha_inicio": self.fecha_inicio.isoformat(),
            "fecha_fin": self.fecha_fin.isoformat(),
            "etiqueta": self.etiqueta(),
            "dias_totales": self.dias_totales(),
        }


@dataclass(frozen=True)
class RegistroJornada:
    """Attendance record for a specific day to evaluate against the expected shift."""

    fecha: date
    estado: str
    horas_trabajadas: Decimal | None = None

    def __post_init__(self):
        if not isinstance(self.fecha, date):
            raise ValidationError("La fecha de la jornada debe ser una fecha válida.")
        if self.estado not in ATTENDANCE_STATUSES:
            raise ValidationError(
                f"El estado '{self.estado}' no es un estado de asistencia válido."
            )
        if self.horas_trabajadas is not None:
            try:
                horas = Decimal(str(self.horas_trabajadas))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError(
                    "Las horas trabajadas deben ser un número válido."
                ) from None
            if not horas.is_finite() or horas < 0 or horas > MAX_HOURS:
                raise ValidationError("Las horas trabajadas no pueden ser negativas.")


@dataclass(frozen=True)
class LiquidacionPeriodo:
    """Summary of hours calculation for an employee during a monthly period."""

    empleado_id: str
    empleado_nombre: str
    periodo: PeriodoLaboral
    jornada_habitual: Decimal
    horas_esperadas: Decimal
    horas_trabajadas: Decimal
    horas_extra: Decimal
    horas_faltantes: Decimal
    saldo_neto: Decimal
    dias_presente: int
    dias_falta_sin_aviso: int
    dias_neutros: int

    def to_dict(self) -> dict:
        return {
            "empleado_id": self.empleado_id,
            "empleado_nombre": self.empleado_nombre,
            "periodo": self.periodo.to_dict(),
            "jornada_habitual": float(self.jornada_habitual),
            "horas_esperadas": float(self.horas_esperadas),
            "horas_trabajadas": float(self.horas_trabajadas),
            "horas_extra": float(self.horas_extra),
            "horas_faltantes": float(self.horas_faltantes),
            "saldo_neto": float(self.saldo_neto),
            "dias_presente": self.dias_presente,
            "dias_falta_sin_aviso": self.dias_falta_sin_aviso,
            "dias_neutros": self.dias_neutros,
        }


def calcular_corte_periodo(
    empleado_id: str,
    empleado_nombre: str,
    periodo: PeriodoLaboral,
    jornada_habitual: Decimal | float | str,
    registros: list[RegistroJornada],
) -> LiquidacionPeriodo:
    """Compute hours balance and attendance statistics according to business rules (FR-08, FR-09).

    Rules:
    - 'Presente': adds actual hours worked. Hours exceeding jornada are overtime ('a favor').
      Hours below jornada count as missing ('faltantes'). If horas_trabajadas is None,
      it defaults to the full jornada.
    - 'Falta sin aviso': deducts the daily jornada hours from the balance (adds to faltantes).
    - 'Falta con aviso', 'Médico', 'Franco', 'Vacaciones': neutral, does not penalize bank hours.
    """
    if not empleado_id or not str(empleado_id).strip():
        raise ValidationError("El identificador del empleado es obligatorio.")

    try:
        jornada = Decimal(str(jornada_habitual)).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("La jornada habitual es inválida.") from None

    if jornada <= 0 or jornada > Decimal("24.00"):
        raise ValidationError("La jornada habitual debe ser entre 0 y 24 horas.")

    horas_esperadas = Decimal("0.00")
    horas_trabajadas_total = Decimal("0.00")
    horas_extra_total = Decimal("0.00")
    horas_faltantes_total = Decimal("0.00")

    dias_presente = 0
    dias_falta_sin_aviso = 0
    dias_neutros = 0

    fechas_procesadas = set()

    for reg in registros:
        if not periodo.contiene(reg.fecha):
            raise ValidationError(
                f"El registro con fecha {reg.fecha.isoformat()} está fuera del período {periodo.etiqueta()}."
            )

        if reg.fecha in fechas_procesadas:
            raise ValidationError(
                f"Fecha duplicada en el período: {reg.fecha.isoformat()}."
            )
        fechas_procesadas.add(reg.fecha)

        estado = reg.estado

        if estado == "Presente":
            dias_presente += 1
            horas_esperadas += jornada
            reales = (
                Decimal(str(reg.horas_trabajadas)).quantize(CENT)
                if reg.horas_trabajadas is not None
                else jornada
            )
            horas_trabajadas_total += reales

            if reales > jornada:
                horas_extra_total += (reales - jornada).quantize(CENT)
            elif reales < jornada:
                horas_faltantes_total += (jornada - reales).quantize(CENT)

        elif estado == "Falta sin aviso":
            dias_falta_sin_aviso += 1
            horas_esperadas += jornada
            # Penaliza la jornada completa
            horas_faltantes_total += jornada

        else:
            # Neutros: "Falta con aviso", "Médico", "Franco", "Vacaciones"
            dias_neutros += 1

    saldo_neto = (horas_extra_total - horas_faltantes_total).quantize(CENT)

    return LiquidacionPeriodo(
        empleado_id=str(empleado_id).strip(),
        empleado_nombre=str(empleado_nombre).strip() or "Empleado",
        periodo=periodo,
        jornada_habitual=jornada,
        horas_esperadas=horas_esperadas.quantize(CENT),
        horas_trabajadas=horas_trabajadas_total.quantize(CENT),
        horas_extra=horas_extra_total.quantize(CENT),
        horas_faltantes=horas_faltantes_total.quantize(CENT),
        saldo_neto=saldo_neto,
        dias_presente=dias_presente,
        dias_falta_sin_aviso=dias_falta_sin_aviso,
        dias_neutros=dias_neutros,
    )


def generar_movimiento_corte(
    liquidacion: LiquidacionPeriodo,
    saldo_actual: Decimal | float | str = Decimal("0.00"),
    movimiento_id: str = "corte-periodo",
) -> HourMovement | None:
    """Generate a bank hour movement from a monthly cut settlement.

    - If saldo_neto > 0: ACUMULACION of excess hours.
    - If saldo_neto < 0: DEVOLUCION of missing hours (validating bank doesn't drop below 0).
    - If saldo_neto == 0: Returns None (no movement needed).
    """
    try:
        saldo = Decimal(str(saldo_actual or 0)).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("El saldo actual es inválido.") from None

    neto = liquidacion.saldo_neto

    if neto == 0:
        return None

    detalle = f"Liquidación período {liquidacion.periodo.etiqueta()}"

    if neto > 0:
        tipo = "ACUMULACION"
        horas = neto
        saldo_resultante = (saldo + horas).quantize(CENT)
    else:
        tipo = "DEVOLUCION"
        horas = abs(neto)
        if saldo < horas:
            raise ValidationError(
                f"El saldo actual ({saldo} hs) no cubre las horas faltantes a liquidar ({horas} hs)."
            )
        saldo_resultante = (saldo - horas).quantize(CENT)

    return HourMovement(
        id=movimiento_id,
        empleado_id=liquidacion.empleado_id,
        empleado_nombre=liquidacion.empleado_nombre,
        tipo=tipo,
        horas=horas,
        saldo_resultante=saldo_resultante,
        detalle=detalle,
        fecha=date.today().isoformat(),
    )
