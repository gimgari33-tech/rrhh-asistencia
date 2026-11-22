"""Infrastructure adapter tests using Firestore-compatible mocks."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from backend.rrhh.application.errors import (
    ApplicationError,
    AuthenticationError,
    ServiceUnavailableError,
)
from backend.rrhh.domain.errors import DomainError, NotFoundError, ValidationError
from backend.rrhh.infrastructure.firebase import FirebaseRuntime
from backend.rrhh.infrastructure.firebase_identity import FirebaseIdentityProvider
from backend.rrhh.infrastructure.firestore_repositories import (
    FirestoreAttendanceRepository,
    FirestoreAuthorizationRepository,
    FirestoreEmployeeRepository,
    FirestoreHoursRepository,
    _run_firestore,
    _serialize_datetime,
)


def make_runtime(database):
    runtime = Mock()
    runtime.database.return_value = database
    return runtime


def make_snapshot(snapshot_id="item-1", data=None, exists=True):
    snapshot = Mock()
    snapshot.id = snapshot_id
    snapshot.exists = exists
    snapshot.to_dict.return_value = data
    return snapshot


class FirebaseRuntimeTests(unittest.TestCase):
    def test_uses_existing_admin_app_and_caches_it(self):
        existing_app = object()
        runtime = FirebaseRuntime("employees-project")

        with patch(
            "backend.rrhh.infrastructure.firebase.firebase_admin.get_app",
            return_value=existing_app,
        ) as get_app:
            self.assertIs(runtime.app(), existing_app)
            self.assertIs(runtime.app(), existing_app)

        get_app.assert_called_once_with()

    def test_initializes_admin_app_if_no_default_app_exists(self):
        initialized_app = object()
        runtime = FirebaseRuntime("employees-project")

        with (
            patch(
                "backend.rrhh.infrastructure.firebase.firebase_admin.get_app",
                side_effect=ValueError("no app"),
            ),
            patch(
                "backend.rrhh.infrastructure.firebase.firebase_admin.initialize_app",
                return_value=initialized_app,
            ) as initialize_app,
        ):
            self.assertIs(runtime.app(), initialized_app)

        initialize_app.assert_called_once_with(
            options={"projectId": "employees-project"}
        )

    def test_rechecks_for_app_after_waiting_for_initialization_lock(self):
        initialized_by_another_thread = object()
        runtime = FirebaseRuntime("employees-project")

        class LockThatInstallsApp:
            def __enter__(self):
                runtime._app = initialized_by_another_thread

            def __exit__(self, exception_type, exception, traceback):
                return False

        runtime._lock = LockThatInstallsApp()

        with patch(
            "backend.rrhh.infrastructure.firebase.firebase_admin.get_app"
        ) as get_app:
            self.assertIs(runtime.app(), initialized_by_another_thread)

        get_app.assert_not_called()

    def test_creates_firestore_client_once(self):
        app = object()
        database = object()
        runtime = FirebaseRuntime("employees-project")

        with (
            patch(
                "backend.rrhh.infrastructure.firebase.firebase_admin.get_app",
                return_value=app,
            ),
            patch(
                "backend.rrhh.infrastructure.firebase.admin_firestore.client",
                return_value=database,
            ) as make_client,
        ):
            self.assertIs(runtime.database(), database)
            self.assertIs(runtime.database(), database)

        make_client.assert_called_once_with(app=app)


class FirebaseIdentityTests(unittest.TestCase):
    def test_verifies_id_token_with_runtime_app(self):
        app = object()
        runtime = Mock()
        runtime.app.return_value = app
        decoded = {"uid": "user-1"}
        provider = FirebaseIdentityProvider(runtime)

        with patch(
            "backend.rrhh.infrastructure.firebase_identity.firebase_auth.verify_id_token",
            return_value=decoded,
        ) as verify:
            self.assertEqual(provider.verify_id_token("valid-token"), decoded)

        verify.assert_called_once_with("valid-token", app=app)

    def test_maps_firebase_token_errors_to_authentication_error(self):
        runtime = Mock()
        provider = FirebaseIdentityProvider(runtime)

        with (
            patch(
                "backend.rrhh.infrastructure.firebase_identity.firebase_auth.verify_id_token",
                side_effect=ValueError("bad token"),
            ),
            self.assertRaises(AuthenticationError),
        ):
            provider.verify_id_token("invalid-token")

    def test_maps_runtime_setup_errors_to_service_unavailable(self):
        runtime = Mock()
        runtime.app.side_effect = RuntimeError("ADC missing")
        provider = FirebaseIdentityProvider(runtime)

        with self.assertRaises(ServiceUnavailableError):
            provider.verify_id_token("any-token")


class FirestoreRepositoryTests(unittest.TestCase):
    def test_datetime_serializer_handles_datetime_string_and_empty_values(self):
        value = datetime(2026, 11, 17, 12, 30, tzinfo=UTC)

        self.assertEqual(_serialize_datetime(value), value.isoformat())
        self.assertEqual(
            _serialize_datetime("already serialized"), "already serialized"
        )
        self.assertEqual(_serialize_datetime(None), "")
        self.assertEqual(_serialize_datetime(123), "")

    def test_firestore_wrapper_preserves_expected_errors_and_maps_unknown_errors(self):
        self.assertEqual(_run_firestore(lambda: "ok", "unavailable"), "ok")
        for error in (ApplicationError("expected"), DomainError("invalid")):
            with self.subTest(error=error), self.assertRaises(type(error)):
                _run_firestore(
                    lambda error=error: (_ for _ in ()).throw(error), "unavailable"
                )

        with self.assertRaises(ServiceUnavailableError):
            _run_firestore(lambda: 1 / 0, "Firestore unavailable")

    def test_authorization_repository_returns_active_document_or_none(self):
        database = Mock()
        runtime = make_runtime(database)
        document = Mock()
        database.collection.return_value.document.return_value = document
        document.get.return_value = make_snapshot(
            data={"activo": True, "rol": "SUPERADMIN"}
        )
        repository = FirestoreAuthorizationRepository(runtime)

        self.assertEqual(
            repository.get_by_uid("user-1"),
            {"activo": True, "rol": "SUPERADMIN"},
        )

        document.get.return_value = make_snapshot(exists=False)
        self.assertIsNone(repository.get_by_uid("missing-user"))

        database.collection.side_effect = RuntimeError("network")
        with self.assertRaises(ServiceUnavailableError):
            repository.get_by_uid("user-1")

    def test_employee_repository_lists_employees_with_optional_balances(self):
        database = Mock()
        runtime = make_runtime(database)
        employee_collection = Mock()
        bank_collection = Mock()
        database.collection.side_effect = lambda name: {
            "empleados": employee_collection,
            "bancos_horas": bank_collection,
        }[name]
        first = make_snapshot(
            "employee-1",
            {
                "nombre": "Ana Pérez",
                "creadoEn": datetime(2026, 1, 1, tzinfo=UTC),
            },
        )
        second = make_snapshot("employee-2", data=None)
        employee_collection.order_by.return_value.stream.return_value = [first, second]
        bank_one = Mock()
        bank_one.get.return_value = make_snapshot(data={"saldoHoras": 3.5})
        bank_two = Mock()
        bank_two.get.return_value = make_snapshot(exists=False)
        bank_collection.document.side_effect = {
            "employee-1": bank_one,
            "employee-2": bank_two,
        }.get

        employees = FirestoreEmployeeRepository(runtime).list_with_balances()

        self.assertEqual(len(employees), 2)
        self.assertEqual(employees[0].nombre, "Ana Pérez")
        self.assertEqual(employees[0].saldo_horas, Decimal("3.5"))
        self.assertEqual(employees[1].nombre, "")
        self.assertEqual(employees[1].saldo_horas, Decimal(0))

    def test_employee_repository_gets_existing_employee_and_returns_none_if_missing(
        self,
    ):
        database = Mock()
        runtime = make_runtime(database)
        employee_collection = Mock()
        database.collection.return_value = employee_collection
        employee_collection.document.return_value.get.side_effect = [
            make_snapshot(
                "employee-1",
                {
                    "nombre": "Ana Pérez",
                    "creadoEn": "2026-11-17T10:00:00+00:00",
                },
            ),
            make_snapshot("missing", exists=False),
        ]
        repository = FirestoreEmployeeRepository(runtime)

        employee = repository.get_by_id("employee-1")
        self.assertEqual(employee.nombre, "Ana Pérez")
        self.assertEqual(employee.creado_en, "2026-11-17T10:00:00+00:00")
        self.assertIsNone(repository.get_by_id("missing"))

    def test_employee_repository_creates_employee_and_initial_bank_in_batch(self):
        database = Mock()
        runtime = make_runtime(database)
        employee_ref = Mock(id="employee-1")
        bank_ref = Mock()
        employee_collection = Mock()
        bank_collection = Mock()
        batch = Mock()
        database.collection.side_effect = lambda name: {
            "empleados": employee_collection,
            "bancos_horas": bank_collection,
        }[name]
        employee_collection.document.return_value = employee_ref
        bank_collection.document.return_value = bank_ref
        database.batch.return_value = batch

        employee = FirestoreEmployeeRepository(runtime).create("Ana Pérez")

        self.assertEqual(employee.id, "employee-1")
        self.assertEqual(employee.nombre, "Ana Pérez")
        self.assertEqual(batch.set.call_count, 2)
        batch.commit.assert_called_once_with()

    def test_hours_repository_lists_recent_movements_and_uses_defaults(self):
        database = Mock()
        runtime = make_runtime(database)
        query = Mock()
        database.collection.return_value.order_by.return_value = query
        query.limit.return_value.stream.return_value = [
            make_snapshot(
                "movement-1",
                {
                    "empleadoId": "employee-1",
                    "empleadoNombre": "Ana Pérez",
                    "tipo": "ACUMULACION",
                    "horas": 2.5,
                    "saldoResultante": 2.5,
                    "detalle": "extra",
                    "fecha": datetime(2026, 11, 17, tzinfo=UTC),
                },
            ),
            make_snapshot("movement-2", data=None),
        ]

        movements = FirestoreHoursRepository(runtime).list_recent(limit=25)

        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[0].empleado_nombre, "Ana Pérez")
        self.assertEqual(movements[0].horas, Decimal("2.5"))
        self.assertEqual(movements[1].empleado_id, "")
        self.assertEqual(movements[1].detalle, "")
        query.limit.assert_called_once_with(25)

    def test_hours_repository_writes_balance_and_movement_transactionally(self):
        database = Mock()
        runtime = make_runtime(database)
        employee_ref = Mock()
        employee_ref.get.return_value = make_snapshot(data={"nombre": "Ana Pérez"})
        bank_ref = Mock()
        bank_ref.get.return_value = make_snapshot(data={"saldoHoras": 1.5})
        movement_ref = Mock(id="movement-1")
        transaction = Mock()
        database.collection.side_effect = lambda name: {
            "empleados": Mock(document=Mock(return_value=employee_ref)),
            "bancos_horas": Mock(document=Mock(return_value=bank_ref)),
            "movimientos_banco_horas": Mock(document=Mock(return_value=movement_ref)),
        }[name]
        database.transaction.return_value = transaction

        with patch(
            "backend.rrhh.infrastructure.firestore_repositories.google_firestore.transactional",
            side_effect=lambda function: function,
        ):
            movement = FirestoreHoursRepository(runtime).create_movement(
                "employee-1", "ACUMULACION", Decimal("2.25"), "Horas extra"
            )

        self.assertEqual(movement.id, "movement-1")
        self.assertEqual(movement.empleado_nombre, "Ana Pérez")
        self.assertEqual(movement.saldo_resultante, Decimal("3.75"))
        self.assertEqual(transaction.set.call_count, 2)

    def test_hours_repository_handles_missing_employee_bank_and_negative_balance(self):
        database = Mock()
        runtime = make_runtime(database)
        employee_ref = Mock()
        bank_ref = Mock()
        movement_ref = Mock(id="movement-1")
        transaction = Mock()
        collections = {
            "empleados": Mock(document=Mock(return_value=employee_ref)),
            "bancos_horas": Mock(document=Mock(return_value=bank_ref)),
            "movimientos_banco_horas": Mock(document=Mock(return_value=movement_ref)),
        }
        database.collection.side_effect = collections.get
        database.transaction.return_value = transaction
        repository = FirestoreHoursRepository(runtime)

        employee_ref.get.return_value = make_snapshot(exists=False)
        with patch(
            "backend.rrhh.infrastructure.firestore_repositories.google_firestore.transactional",
            side_effect=lambda function: function,
        ):
            with self.assertRaises(NotFoundError):
                repository.create_movement("missing", "ACUMULACION", Decimal(1), "")

            employee_ref.get.return_value = make_snapshot(data={"nombre": "Ana"})
            bank_ref.get.return_value = make_snapshot(exists=False)
            with self.assertRaises(ValidationError):
                repository.create_movement("employee-1", "DEVOLUCION", Decimal(1), "")

        transaction.set.assert_not_called()

    def test_attendance_repository_lists_records_with_defaults(self):
        database = Mock()
        runtime = make_runtime(database)
        query = Mock()
        database.collection.return_value.order_by.return_value = query
        query.limit.return_value.stream.return_value = [
            make_snapshot(
                "attendance-1",
                {
                    "empleadoId": "employee-1",
                    "empleadoNombre": "Ana Pérez",
                    "estado": "Presente",
                    "fecha": "2026-11-17",
                    "creadoEn": datetime(2026, 11, 17, tzinfo=UTC),
                },
            ),
            make_snapshot("attendance-2", data=None),
        ]

        records = FirestoreAttendanceRepository(runtime).list_recent(limit=10)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].estado, "Presente")
        self.assertEqual(records[0].creado_en, "2026-11-17T00:00:00+00:00")
        self.assertEqual(records[1].empleado_id, "")
        self.assertEqual(records[1].fecha, "")

    def test_attendance_repository_creates_record(self):
        database = Mock()
        runtime = make_runtime(database)
        record_ref = Mock(id="attendance-1")
        database.collection.return_value.document.return_value = record_ref
        database.collection.return_value.where.return_value.stream.return_value = []
        batch = Mock()
        database.batch.return_value = batch

        record = FirestoreAttendanceRepository(runtime).create(
            "employee-1", "Ana Pérez", "Presente", "2026-11-17"
        )

        self.assertEqual(record.id, "attendance-1")
        self.assertEqual(record.empleado_nombre, "Ana Pérez")
        batch.set.assert_called_once()
        batch.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
