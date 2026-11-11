"""Business rules that do not depend on Flask or Firebase."""

from datetime import date
from decimal import Decimal, InvalidOperation

from .errors import ValidationError


CENT = Decimal("0.01")
MAX_HOURS = Decimal("99999999.99")
ROLES = frozenset({"SUPERADMIN", "INVITADO"})
MOVEMENT_TYPES = frozenset({"ACUMULACION", "DEVOLUCION"})
ATTENDANCE_STATUSES = frozenset({
    "Presente",
    "Franco",
    "Falta sin aviso",
    "Falta con aviso",
    "Médico",
    "Vacaciones",
})


def employee_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("El nombre del empleado es obligatorio.")
    name = value.strip()
    if len(name) > 100:
        raise ValidationError("El nombre no puede superar los 100 caracteres.")
    return name


def positive_hours(value):
    try:
        hours = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("La cantidad de horas es inválida.") from None

    if not hours.is_finite() or hours <= 0 or hours > MAX_HOURS or hours != hours.quantize(CENT):
        raise ValidationError("Ingresá horas positivas, con hasta dos decimales.")
    return hours


def movement_type(value):
    kind = str(value or "").upper()
    if kind not in MOVEMENT_TYPES:
        raise ValidationError("El tipo debe ser ACUMULACION o DEVOLUCION.")
    return kind


def movement_detail(value):
    if not isinstance(value, str):
        raise ValidationError("El detalle debe ser texto.")
    detail = value.strip()
    if len(detail) > 250:
        raise ValidationError("El detalle no puede superar los 250 caracteres.")
    return detail


def attendance_date(value):
    if not isinstance(value, str):
        raise ValidationError("La fecha debe tener el formato AAAA-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValidationError("La fecha debe tener el formato AAAA-MM-DD.") from None
    if parsed.isoformat() != value:
        raise ValidationError("La fecha debe tener el formato AAAA-MM-DD.")
    return value


def attendance_status(value):
    if not isinstance(value, str) or value not in ATTENDANCE_STATUSES:
        raise ValidationError("El estado de asistencia no es válido.")
    return value


def next_balance(current_balance, hours, kind):
    current = Decimal(str(current_balance or 0))
    balance = current + hours if kind == "ACUMULACION" else current - hours
    if balance < 0:
        raise ValidationError("La devolución supera las horas disponibles.")
    return balance.quantize(CENT)
