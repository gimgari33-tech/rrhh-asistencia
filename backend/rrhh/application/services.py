"""Use cases that coordinate domain rules and repository ports."""

from ..domain.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from ..domain.models import AttendanceRecord, AuthorizedUser, Employee, HourMovement
from ..domain.rules import (
    ROLES,
    attendance_date,
    attendance_status,
    employee_name,
    movement_detail,
    movement_type,
    positive_hours,
)
from .ports import (
    AttendanceRepository,
    AuthorizationRepository,
    EmployeeRepository,
    HoursRepository,
    IdentityProvider,
)


class AccessService:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        authorization_repository: AuthorizationRepository,
    ):
        self._identity_provider = identity_provider
        self._authorization_repository = authorization_repository

    def authenticate(self, token: str) -> AuthorizedUser:
        try:
            decoded = self._identity_provider.verify_id_token(token)
        except AuthenticationError:
            raise
        except ServiceUnavailableError:
            raise
        except Exception as error:
            raise ServiceUnavailableError("No se pudo validar la sesión en este momento.") from error

        uid = decoded.get("uid")
        if not isinstance(uid, str) or not uid:
            raise AuthenticationError("La sesión no identifica a un usuario.")

        access = self._authorization_repository.get_by_uid(uid)
        if not access or access.get("activo") is not True:
            raise AuthorizationError("Tu cuenta no está habilitada para esta aplicación.")

        role = str(access.get("rol") or "INVITADO").upper()
        if role not in ROLES:
            raise AuthorizationError("El rol asignado a tu cuenta no es válido.")

        email = decoded.get("email")
        display_name = access.get("nombre") or decoded.get("name") or email or "Usuario"
        return AuthorizedUser(uid, str(email or ""), str(display_name), role)


class EmployeeService:
    def __init__(self, repository: EmployeeRepository):
        self._repository = repository

    def list(self) -> list[Employee]:
        return self._repository.list_with_balances()

    def create(self, name: object) -> Employee:
        return self._repository.create(employee_name(name))


class HoursService:
    def __init__(self, repository: HoursRepository):
        self._repository = repository

    def list_recent(self) -> list[HourMovement]:
        return self._repository.list_recent()

    def create(
        self,
        employee_id: object,
        kind: object,
        hours: object,
        detail: object,
    ) -> HourMovement:
        normalized_employee_id = str(employee_id or "").strip()
        if not normalized_employee_id:
            raise ValidationError("Debe indicar un empleado.")
        return self._repository.create_movement(
            normalized_employee_id,
            movement_type(kind),
            positive_hours(hours),
            movement_detail(detail),
        )


class AttendanceService:
    def __init__(
        self,
        employee_repository: EmployeeRepository,
        attendance_repository: AttendanceRepository,
    ):
        self._employee_repository = employee_repository
        self._attendance_repository = attendance_repository

    def list_recent(self) -> list[AttendanceRecord]:
        return self._attendance_repository.list_recent()

    def create(
        self,
        employee_id: object,
        status: object,
        day: object,
    ) -> AttendanceRecord:
        normalized_employee_id = str(employee_id or "").strip()
        if not normalized_employee_id:
            raise ValidationError("Debe indicar un empleado.")
        normalized_status = attendance_status(status)
        normalized_day = attendance_date(day)
        employee = self._employee_repository.get_by_id(normalized_employee_id)
        if employee is None:
            raise NotFoundError("Empleado no encontrado.")
        return self._attendance_repository.create(
            employee.id,
            employee.nombre,
            normalized_status,
            normalized_day,
        )
