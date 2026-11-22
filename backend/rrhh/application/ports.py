"""Interfaces for external services used by the application layer."""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Protocol

from ..domain.models import (
    AttendanceRecord,
    Course,
    CourseAssignment,
    Employee,
    HourMovement,
)


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


class CourseRepository(Protocol):
    def list_courses(self) -> list[Course]: ...

    def get_course_by_id(self, course_id: str) -> Course | None: ...

    def create_course(self, name: str, description: str) -> Course: ...

    def assign(self, employee: Employee, course: Course) -> CourseAssignment: ...

    def complete(
        self,
        employee_id: str,
        course_id: str,
        completed_on: date,
    ) -> CourseAssignment: ...

    def list_for_employee(self, employee_id: str) -> list[CourseAssignment]: ...

    def list_pending(self) -> list[CourseAssignment]: ...
