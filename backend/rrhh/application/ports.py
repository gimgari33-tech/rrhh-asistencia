"""Interfaces for external services used by the application layer."""

from decimal import Decimal
from typing import Mapping, Protocol

from ..domain.models import AttendanceRecord, Employee, HourMovement


class IdentityProvider(Protocol):
    def verify_id_token(self, token: str) -> Mapping[str, object]: ...


class AuthorizationRepository(Protocol):
    def get_by_uid(self, uid: str) -> Mapping[str, object] | None: ...


class EmployeeRepository(Protocol):
    def list_with_balances(self) -> list[Employee]: ...

    def get_by_id(self, employee_id: str) -> Employee | None: ...

    def create(self, name: str) -> Employee: ...


class HoursRepository(Protocol):
    def list_recent(self, limit: int = 100) -> list[HourMovement]: ...

    def create_movement(
        self,
        employee_id: str,
        kind: str,
        hours: Decimal,
        detail: str,
    ) -> HourMovement: ...


class AttendanceRepository(Protocol):
    def list_recent(self, limit: int = 100) -> list[AttendanceRecord]: ...

    def create(
        self,
        employee_id: str,
        employee_name: str,
        status: str,
        attendance_day: str,
    ) -> AttendanceRecord: ...
