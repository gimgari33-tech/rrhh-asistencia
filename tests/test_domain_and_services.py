"""Tests for domain validation and application use cases."""

import unittest
from decimal import Decimal
from unittest.mock import Mock

from backend.rrhh.application.errors import (
    AuthenticationError,
    AuthorizationError,
    ServiceUnavailableError,
)
from backend.rrhh.application.services import (
    AccessService,
    AttendanceService,
    EmployeeService,
    HoursService,
)
from backend.rrhh.domain.errors import NotFoundError, ValidationError
from backend.rrhh.domain.models import (
    AttendanceRecord,
    AuthorizedUser,
    Employee,
    HourMovement,
)
from backend.rrhh.domain.rules import (
    attendance_date,
    attendance_status,
    employee_name,
    movement_detail,
    movement_type,
    next_balance,
    positive_hours,
)


class DomainRuleTests(unittest.TestCase):
    def test_employee_name_is_trimmed_and_rejects_invalid_values(self):
        self.assertEqual(employee_name("  Ana Pérez "), "Ana Pérez")
        for value in (None, "", "   ", "x" * 101):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                employee_name(value)

    def test_positive_hours_accepts_cents_and_rejects_invalid_values(self):
        self.assertEqual(positive_hours("2.50"), Decimal("2.50"))
        for value in (
            None,
            "not a number",
            "NaN",
            "Infinity",
            0,
            -1,
            "1.001",
            "100000000",
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                positive_hours(value)

    def test_movement_type_normalizes_case_and_rejects_unknown_type(self):
        self.assertEqual(movement_type("acumulacion"), "ACUMULACION")
        self.assertEqual(movement_type("DEVOLUCION"), "DEVOLUCION")
        with self.assertRaises(ValidationError):
            movement_type("TRANSFERENCIA")

    def test_movement_detail_trims_and_limits_text(self):
        self.assertEqual(movement_detail("  Horas extra "), "Horas extra")
        self.assertEqual(movement_detail(""), "")
        with self.assertRaises(ValidationError):
            movement_detail(None)
        with self.assertRaises(ValidationError):
            movement_detail("x" * 251)

    def test_attendance_date_requires_iso_calendar_date(self):
        self.assertEqual(attendance_date("2024-02-29"), "2024-02-29")
        for value in (None, "2026-02-30", "17/11/2026", "2026-1-2", "20261117"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                attendance_date(value)

    def test_attendance_status_is_from_the_allowed_set(self):
        self.assertEqual(attendance_status("Presente"), "Presente")
        with self.assertRaises(ValidationError):
            attendance_status("Ausente")
        with self.assertRaises(ValidationError):
            attendance_status(None)

    def test_next_balance_accumulates_and_prevents_negative_result(self):
        self.assertEqual(
            next_balance(Decimal("4.25"), Decimal("1.50"), "ACUMULACION"),
            Decimal("5.75"),
        )
        self.assertEqual(
            next_balance(Decimal("4.25"), Decimal("1.25"), "DEVOLUCION"),
            Decimal("3.00"),
        )
        with self.assertRaises(ValidationError):
            next_balance(Decimal(1), Decimal(2), "DEVOLUCION")


class ApplicationServiceTests(unittest.TestCase):
    def test_access_service_returns_user_from_verified_token_and_active_role(self):
        identity = Mock()
        identity.verify_id_token.return_value = {
            "uid": "user-1",
            "email": "rrhh@example.test",
            "name": "Nombre del token",
        }
        authorization = Mock()
        authorization.get_by_uid.return_value = {
            "activo": True,
            "rol": "superadmin",
            "nombre": "Nombre de Firestore",
        }

        user = AccessService(identity, authorization).authenticate("signed-token")

        self.assertEqual(
            user,
            AuthorizedUser(
                "user-1", "rrhh@example.test", "Nombre de Firestore", "SUPERADMIN"
            ),
        )
        authorization.get_by_uid.assert_called_once_with("user-1")

    def test_access_service_rejects_missing_uid_in_verified_token(self):
        identity = Mock()
        identity.verify_id_token.return_value = {"email": "x@example.test"}
        authorization = Mock()

        with self.assertRaises(AuthenticationError):
            AccessService(identity, authorization).authenticate("token")
        authorization.get_by_uid.assert_not_called()

    def test_access_service_rejects_inactive_missing_and_unknown_roles(self):
        identity = Mock()
        identity.verify_id_token.return_value = {"uid": "user-1"}
        authorization = Mock()
        service = AccessService(identity, authorization)

        for document in (
            None,
            {"activo": False, "rol": "SUPERADMIN"},
            {"activo": True, "rol": "AUDITOR"},
        ):
            with self.subTest(document=document):
                authorization.get_by_uid.return_value = document
                with self.assertRaises(AuthorizationError):
                    service.authenticate("token")

    def test_access_service_preserves_auth_errors_and_maps_unknown_identity_errors(
        self,
    ):
        identity = Mock()
        authorization = Mock()
        service = AccessService(identity, authorization)

        identity.verify_id_token.side_effect = AuthenticationError("invalid")
        with self.assertRaises(AuthenticationError):
            service.authenticate("token")

        identity.verify_id_token.side_effect = ServiceUnavailableError("offline")
        with self.assertRaises(ServiceUnavailableError):
            service.authenticate("token")

        identity.verify_id_token.side_effect = RuntimeError("unexpected")
        with self.assertRaises(ServiceUnavailableError):
            service.authenticate("token")

    def test_employee_service_lists_and_normalizes_new_employee_name(self):
        employee = Employee(id="employee-1", nombre="Ana Pérez")
        repository = Mock()
        repository.list_with_balances.return_value = [employee]
        repository.create.return_value = employee
        service = EmployeeService(repository)

        self.assertEqual(service.list(), [employee])
        self.assertEqual(service.create(" Ana Pérez "), employee)
        repository.create.assert_called_once_with("Ana Pérez")
        with self.assertRaises(ValidationError):
            service.create(" ")

    def test_hours_service_normalizes_movement_before_persisting(self):
        movement = HourMovement(
            id="movement-1",
            empleado_id="employee-1",
            empleado_nombre="Ana Pérez",
            tipo="ACUMULACION",
            horas=Decimal("2.50"),
            saldo_resultante=Decimal("2.50"),
            detalle="Horas extra",
        )
        repository = Mock()
        repository.list_recent.return_value = [movement]
        repository.create_movement.return_value = movement
        service = HoursService(repository)

        self.assertEqual(service.list_recent(), [movement])
        self.assertEqual(
            service.create(" employee-1 ", "acumulacion", "2.50", " Horas extra "),
            movement,
        )
        repository.create_movement.assert_called_once_with(
            "employee-1", "ACUMULACION", Decimal("2.50"), "Horas extra"
        )
        with self.assertRaises(ValidationError):
            service.create("", "ACUMULACION", 2, "")

    def test_attendance_service_validates_employee_and_attendance_data(self):
        employee = Employee(id="employee-1", nombre="Ana Pérez")
        record = AttendanceRecord(
            id="attendance-1",
            empleado_id="employee-1",
            empleado_nombre="Ana Pérez",
            estado="Presente",
            fecha="2026-11-17",
        )
        employees = Mock()
        employees.get_by_id.return_value = employee
        attendance = Mock()
        attendance.list_recent.return_value = [record]
        attendance.create.return_value = record
        service = AttendanceService(employees, attendance)

        self.assertEqual(service.list_recent(), [record])
        self.assertEqual(
            service.create(" employee-1 ", "Presente", "2026-11-17"), record
        )
        attendance.create.assert_called_once_with(
            "employee-1", "Ana Pérez", "Presente", "2026-11-17"
        )

        with self.assertRaises(ValidationError):
            service.create("", "Presente", "2026-11-17")
        with self.assertRaises(ValidationError):
            service.create("employee-1", "Ausente", "2026-11-17")
        with self.assertRaises(ValidationError):
            service.create("employee-1", "Presente", "fecha-inválida")

        employees.get_by_id.return_value = None
        with self.assertRaises(NotFoundError):
            service.create("employee-2", "Presente", "2026-11-17")


if __name__ == "__main__":
    unittest.main()
