"""Business rules that do not depend on Flask or Firebase."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .errors import ValidationError

CENT = Decimal("0.01")
MAX_HOURS = Decimal("99999999.99")
ROLES = frozenset({"SUPERADMIN", "INVITADO"})
MOVEMENT_TYPES = frozenset({"ACUMULACION", "DEVOLUCION"})
ATTENDANCE_STATUSES = frozenset(
    {
        "Presente",
        "Franco",
        "Falta sin aviso",
        "Falta con aviso",
        "Médico",
        "Vacaciones",
    }
)


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

    if (
        not hours.is_finite()
        or hours <= 0
        or hours > MAX_HOURS
        or hours != hours.quantize(CENT)
    ):
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


def course_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("El nombre del curso es obligatorio.")
    name = value.strip()
    if len(name) > 150:
        raise ValidationError("El nombre del curso no puede superar los 150 caracteres.")
    return name


def course_description(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("La descripción del curso debe ser texto.")
    description = value.strip()
    if len(description) > 500:
        raise ValidationError("La descripción del curso no puede superar los 500 caracteres.")
    return description


def completion_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValidationError("La fecha de finalización debe tener el formato AAAA-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "La fecha de finalización debe tener el formato AAAA-MM-DD."
        ) from None
    if parsed.isoformat() != value:
        raise ValidationError("La fecha de finalización debe tener el formato AAAA-MM-DD.")
    return parsed


def course_completion_percentage(assignments):
    if not assignments:
        return Decimal("0.00")
    completed = sum(assignment.completado is True for assignment in assignments)
    return (Decimal(completed) * Decimal(100) / Decimal(len(assignments))).quantize(
        Decimal("0.01")
    )


def next_balance(current_balance, hours, kind):
    current = Decimal(str(current_balance or 0))
    balance = current + hours if kind == "ACUMULACION" else current - hours
    if balance < 0:
        raise ValidationError("La devolución supera las horas disponibles.")
    return balance.quantize(CENT)
