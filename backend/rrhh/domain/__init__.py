"""Domain layer models, rules, and period calculations."""

from .errors import DomainError, NotFoundError, ValidationError
from .models import AttendanceRecord, AuthorizedUser, Employee, HourMovement
from .period import (
    LiquidacionPeriodo,
    PeriodoLaboral,
    RegistroJornada,
    calcular_corte_periodo,
    generar_movimiento_corte,
)
from .rules import (
    ATTENDANCE_STATUSES,
    MOVEMENT_TYPES,
    ROLES,
    attendance_date,
    attendance_status,
    employee_name,
    movement_detail,
    movement_type,
    next_balance,
    positive_hours,
)

__all__ = [
    "ATTENDANCE_STATUSES",
    "MOVEMENT_TYPES",
    "ROLES",
    "AttendanceRecord",
    "AuthorizedUser",
    "DomainError",
    "Employee",
    "HourMovement",
    "LiquidacionPeriodo",
    "NotFoundError",
    "PeriodoLaboral",
    "RegistroJornada",
    "ValidationError",
    "attendance_date",
    "attendance_status",
    "calcular_corte_periodo",
    "employee_name",
    "generar_movimiento_corte",
    "movement_detail",
    "movement_type",
    "next_balance",
    "positive_hours",
]
