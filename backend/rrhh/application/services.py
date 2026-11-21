"""Use cases that coordinate domain rules and repository ports."""

from ..domain.errors import NotFoundError, ValidationError
from ..domain.models import (
    AttendanceRecord,
    AuthorizedUser,
    Employee,
    Horas,
    HourMovement,
    TipoMovimiento,
)
from ..domain.rules import (
    ROLES,
    attendance_date,
    attendance_status,
    employee_name,
    movement_detail,
    positive_hours,
)
from .errors import AuthenticationError, AuthorizationError, ServiceUnavailableError
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
        movement_kind = TipoMovimiento.parse(kind)
        movement_hours = Horas.positiva(positive_hours(hours))
        movement_detail_value = movement_detail(detail)

        def apply_movement(account):
            if movement_kind is TipoMovimiento.ACUMULACION:
                return account.acreditar_horas(movement_hours, movement_detail_value)
            return account.debitar_horas(movement_hours, movement_detail_value)

        return self._repository.transact_account(normalized_employee_id, apply_movement)


class AttendanceService:
    MAX_BATCH_SIZE = 200

    def __init__(
        self,
        employee_repository: EmployeeRepository,
        attendance_repository: AttendanceRepository,
    ):
        self._employee_repository = employee_repository
        self._attendance_repository = attendance_repository

    def list_recent(self) -> list[AttendanceRecord]:
        return self._attendance_repository.list_recent()

    def list_for_day(self, day: object) -> list[AttendanceRecord]:
        return self._attendance_repository.list_for_day(attendance_date(day))

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

    def create_many(self, day: object, entries: object) -> list[AttendanceRecord]:
        normalized_day = attendance_date(day)
        if not isinstance(entries, list) or not entries:
            raise ValidationError("Debe incluir al menos una asistencia.")
        if len(entries) > self.MAX_BATCH_SIZE:
            raise ValidationError(
                f"No se pueden guardar más de {self.MAX_BATCH_SIZE} asistencias por jornada."
            )

        records = []
        seen_employee_ids = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValidationError("Cada asistencia debe ser un objeto válido.")
            employee_id = str(entry.get("empleado_id") or "").strip()
            if not employee_id:
                raise ValidationError("Cada asistencia debe indicar un empleado.")
            if employee_id in seen_employee_ids:
                raise ValidationError("No repitas un empleado en la misma jornada.")
            seen_employee_ids.add(employee_id)

            employee = self._employee_repository.get_by_id(employee_id)
            if employee is None:
                raise NotFoundError("Empleado no encontrado.")
            records.append(
                AttendanceRecord(
                    id="",
                    empleado_id=employee.id,
                    empleado_nombre=employee.nombre,
                    estado=attendance_status(entry.get("estado")),
                    fecha=normalized_day,
                )
            )
        return self._attendance_repository.save_day(records)
