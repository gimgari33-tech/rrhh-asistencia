"""API regression tests with fake identity and repositories."""

import unittest
from decimal import Decimal
from typing import ClassVar
from unittest.mock import patch

from backend.rrhh import create_app
from backend.rrhh.application.errors import AuthenticationError, ServiceUnavailableError
from backend.rrhh.domain.errors import NotFoundError
from backend.rrhh.domain.models import (
    AttendanceRecord,
    Course,
    CourseAssignment,
    Employee,
    HourMovement,
)
from backend.rrhh.domain.rules import next_balance


class FakeStore:
    def __init__(self):
        self.authorized_users = {
            "admin-uid": {
                "activo": True,
                "rol": "SUPERADMIN",
                "nombre": "Admin de prueba",
            },
            "guest-uid": {
                "activo": True,
                "rol": "INVITADO",
                "nombre": "Invitado de prueba",
            },
            "disabled-uid": {"activo": False, "rol": "SUPERADMIN"},
        }
        self.employees = {}
        self.balances = {}
        self.movements = []
        self.attendance = []
        self.next_employee_id = 1
        self.courses = {}
        self.course_assignments = {}
        self.next_course_id = 1


class FakeIdentityProvider:
    TOKENS: ClassVar[dict[str, dict[str, str]]] = {
        "admin-token": {"uid": "admin-uid", "email": "admin@example.test"},
        "guest-token": {"uid": "guest-uid", "email": "guest@example.test"},
        "disabled-token": {"uid": "disabled-uid", "email": "disabled@example.test"},
    }

    def verify_id_token(self, token):
        if token == "service-down":
            raise ServiceUnavailableError("Firebase no disponible.")
        if token not in self.TOKENS:
            raise AuthenticationError("Token de prueba inválido.")
        return self.TOKENS[token]


class FakeAuthorizationRepository:
    def __init__(self, store):
        self.store = store

    def get_by_uid(self, uid):
        return self.store.authorized_users.get(uid)


class FakeEmployeeRepository:
    def __init__(self, store):
        self.store = store

    def list_with_balances(self):
        return [
            Employee(
                id=employee.id,
                nombre=employee.nombre,
                creado_en=employee.creado_en,
                saldo_horas=self.store.balances.get(employee.id, Decimal("0.00")),
            )
            for employee in self.store.employees.values()
        ]

    def get_by_id(self, employee_id):
        return self.store.employees.get(employee_id)

    def create(self, name):
        employee_id = f"employee-{self.store.next_employee_id}"
        self.store.next_employee_id += 1
        employee = Employee(id=employee_id, nombre=name)
        self.store.employees[employee_id] = employee
        self.store.balances[employee_id] = Decimal("0.00")
        return employee


class FakeHoursRepository:
    def __init__(self, store):
        self.store = store

    def list_recent(self, limit=100):
        return list(reversed(self.store.movements[-limit:]))

    def create_movement(self, employee_id, kind, hours, detail):
        employee = self.store.employees.get(employee_id)
        if employee is None:
            raise NotFoundError("Empleado no encontrado.")

        balance = next_balance(self.store.balances.get(employee_id, 0), hours, kind)
        self.store.balances[employee_id] = balance
        movement = HourMovement(
            id=f"movement-{len(self.store.movements) + 1}",
            empleado_id=employee_id,
            empleado_nombre=employee.nombre,
            tipo=kind,
            horas=hours,
            saldo_resultante=balance,
            detalle=detail,
        )
        self.store.movements.append(movement)
        return movement


class FakeAttendanceRepository:
    def __init__(self, store):
        self.store = store

    def list_recent(self, limit=100):
        return list(reversed(self.store.attendance[-limit:]))

    def create(self, employee_id, employee_name, status, day):
        record = AttendanceRecord(
            id=f"attendance-{len(self.store.attendance) + 1}",
            empleado_id=employee_id,
            empleado_nombre=employee_name,
            estado=status,
            fecha=day,
        )
        self.store.attendance.append(record)
        return record


class FakeCourseRepository:
    def __init__(self, store):
        self.store = store

    def list_courses(self):
        return list(self.store.courses.values())

    def get_course_by_id(self, course_id):
        return self.store.courses.get(course_id)

    def create_course(self, name, description):
        course_id = f"course-{self.store.next_course_id}"
        self.store.next_course_id += 1
        course = Course(id=course_id, nombre=name, descripcion=description)
        self.store.courses[course_id] = course
        return course

    def assign(self, employee, course):
        key = (employee.id, course.id)
        if key not in self.store.course_assignments:
            self.store.course_assignments[key] = CourseAssignment(
                id=course.id,
                empleado_id=employee.id,
                empleado_nombre=employee.nombre,
                curso_id=course.id,
                curso_nombre=course.nombre,
            )
        return self.store.course_assignments[key]

    def complete(self, employee_id, course_id, completed_on):
        assignment = self.store.course_assignments.get((employee_id, course_id))
        if assignment is None:
            raise NotFoundError("El curso no está asignado a este empleado.")
        completed = assignment.marcar_completado(completed_on)
        self.store.course_assignments[(employee_id, course_id)] = completed
        return completed

    def list_for_employee(self, employee_id):
        return [
            assignment
            for (
                assigned_employee_id,
                _,
            ), assignment in self.store.course_assignments.items()
            if assigned_employee_id == employee_id
        ]

    def list_pending(self):
        return [
            assignment
            for assignment in self.store.course_assignments.values()
            if not assignment.completado
        ]


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        employee_repository = FakeEmployeeRepository(self.store)
        patches = (
            patch("backend.rrhh.FirebaseRuntime", return_value=object()),
            patch(
                "backend.rrhh.FirebaseIdentityProvider",
                return_value=FakeIdentityProvider(),
            ),
            patch(
                "backend.rrhh.FirestoreAuthorizationRepository",
                return_value=FakeAuthorizationRepository(self.store),
            ),
            patch(
                "backend.rrhh.FirestoreEmployeeRepository",
                return_value=employee_repository,
            ),
            patch(
                "backend.rrhh.FirestoreHoursRepository",
                return_value=FakeHoursRepository(self.store),
            ),
            patch(
                "backend.rrhh.FirestoreAttendanceRepository",
                return_value=FakeAttendanceRepository(self.store),
            ),
            patch(
                "backend.rrhh.FirestoreCourseRepository",
                return_value=FakeCourseRepository(self.store),
            ),
        )
        for active_patch in patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}"}

    def test_health_endpoint_is_public(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_api_requires_a_valid_firebase_token_and_active_user(self):
        missing_token = self.client.get("/api/employees")
        invalid_token = self.client.get(
            "/api/employees", headers=self.headers("invalid-token")
        )
        disabled_user = self.client.get(
            "/api/employees", headers=self.headers("disabled-token")
        )
        unavailable = self.client.get(
            "/api/auth/me", headers=self.headers("service-down")
        )

        self.assertEqual(missing_token.status_code, 401)
        self.assertEqual(invalid_token.status_code, 401)
        self.assertEqual(disabled_user.status_code, 403)
        self.assertEqual(unavailable.status_code, 503)

    def test_guest_cannot_escalate_role_with_a_request_header(self):
        profile = self.client.get("/api/auth/me", headers=self.headers("guest-token"))
        readable_employees = self.client.get(
            "/api/employees", headers=self.headers("guest-token")
        )
        readable_movements = self.client.get(
            "/api/movements", headers=self.headers("guest-token")
        )
        readable_attendance = self.client.get(
            "/api/attendance", headers=self.headers("guest-token")
        )
        response = self.client.post(
            "/api/employees",
            json={"nombre": "No autorizado"},
            headers={
                **self.headers("guest-token"),
                "X-Role": "SUPERADMIN",
            },
        )

        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.get_json()["rol"], "INVITADO")
        self.assertEqual(readable_employees.status_code, 200)
        self.assertEqual(readable_movements.status_code, 200)
        self.assertEqual(readable_attendance.status_code, 200)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.employees, {})

    def test_admin_employee_hours_and_attendance_flow(self):
        headers = self.headers("admin-token")
        employee_response = self.client.post(
            "/api/employees", json={"nombre": "Ana Pérez"}, headers=headers
        )

        self.assertEqual(employee_response.status_code, 201)
        employee = employee_response.get_json()
        self.assertEqual(employee["nombre"], "Ana Pérez")
        self.assertEqual(employee["saldo_horas"], 0.0)

        accumulation = self.client.post(
            "/api/movements",
            json={
                "empleado_id": employee["id"],
                "tipo": "ACUMULACION",
                "horas": 8.5,
                "detalle": "Horas extra",
            },
            headers=headers,
        )
        refund = self.client.post(
            "/api/movements",
            json={
                "empleado_id": employee["id"],
                "tipo": "DEVOLUCION",
                "horas": 2,
                "detalle": "Compensación",
            },
            headers=headers,
        )

        self.assertEqual(accumulation.status_code, 201)
        self.assertEqual(accumulation.get_json()["saldo_resultante"], 8.5)
        self.assertEqual(refund.status_code, 201)
        self.assertEqual(refund.get_json()["saldo_resultante"], 6.5)

        refreshed_employee = self.client.get(
            "/api/employees", headers=headers
        ).get_json()[0]
        self.assertEqual(refreshed_employee["saldo_horas"], 6.5)

        attendance = self.client.post(
            "/api/attendance",
            json={
                "empleado_id": employee["id"],
                "estado": "Presente",
                "fecha": "2026-11-15",
            },
            headers=headers,
        )
        self.assertEqual(attendance.status_code, 201)
        self.assertEqual(attendance.get_json()["empleado_nombre"], "Ana Pérez")

    def test_invalid_movement_is_rejected(self):
        headers = self.headers("admin-token")
        employee = self.client.post(
            "/api/employees", json={"nombre": "Ana Pérez"}, headers=headers
        ).get_json()

        response = self.client.post(
            "/api/movements",
            json={
                "empleado_id": employee["id"],
                "tipo": "DEVOLUCION",
                "horas": 1,
                "detalle": "Supera el saldo",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("supera", response.get_json()["error"])

    def test_admin_can_assign_complete_and_list_pending_courses(self):
        headers = self.headers("admin-token")
        employee = self.client.post(
            "/api/employees", json={"nombre": "Ana Pérez"}, headers=headers
        ).get_json()
        course_response = self.client.post(
            "/api/courses",
            json={
                "nombre": "Seguridad e higiene",
                "descripcion": "Capacitación anual",
            },
            headers=headers,
        )
        course = course_response.get_json()
        listed_courses = self.client.get("/api/courses", headers=headers).get_json()
        assignment_response = self.client.post(
            f"/api/employees/{employee['id']}/courses",
            json={"curso_id": course["id"]},
            headers=headers,
        )
        pending_before = self.client.get(
            "/api/courses/pending", headers=headers
        ).get_json()
        employee_courses_before = self.client.get(
            f"/api/employees/{employee['id']}/courses", headers=headers
        ).get_json()

        complete_response = self.client.post(
            f"/api/employees/{employee['id']}/courses/{course['id']}/complete",
            json={"fecha_completacion": "2026-11-20"},
            headers=headers,
        )
        pending_after = self.client.get(
            "/api/courses/pending", headers=headers
        ).get_json()
        employee_courses_after = self.client.get(
            f"/api/employees/{employee['id']}/courses", headers=headers
        ).get_json()

        self.assertEqual(course_response.status_code, 201)
        self.assertEqual(listed_courses[0]["id"], course["id"])
        self.assertEqual(assignment_response.status_code, 201)
        self.assertEqual(assignment_response.get_json()["completado"], False)
        self.assertEqual(len(pending_before), 1)
        self.assertEqual(employee_courses_before["porcentaje_completado"], 0.0)
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(
            complete_response.get_json()["fecha_completacion"], "2026-11-20"
        )
        self.assertEqual(pending_after, [])
        self.assertEqual(employee_courses_after["porcentaje_completado"], 100.0)

    def test_course_mutations_require_superadmin_and_completion_requires_assignment(
        self,
    ):
        guest_headers = self.headers("guest-token")
        employee = self.client.post(
            "/api/employees",
            json={"nombre": "Ana Pérez"},
            headers=self.headers("admin-token"),
        ).get_json()
        course = self.client.post(
            "/api/courses",
            json={"nombre": "Seguridad e higiene"},
            headers=self.headers("admin-token"),
        ).get_json()

        create_for_guest = self.client.post(
            "/api/courses", json={"nombre": "No autorizado"}, headers=guest_headers
        )
        assign_for_guest = self.client.post(
            f"/api/employees/{employee['id']}/courses",
            json={"curso_id": course["id"]},
            headers=guest_headers,
        )
        complete_unassigned = self.client.post(
            f"/api/employees/{employee['id']}/courses/{course['id']}/complete",
            json={"fecha_completacion": "2026-11-20"},
            headers=self.headers("admin-token"),
        )

        self.assertEqual(create_for_guest.status_code, 403)
        self.assertEqual(assign_for_guest.status_code, 403)
        self.assertEqual(complete_unassigned.status_code, 404)

    def test_api_rejects_malformed_movement_and_attendance_payloads(self):
        headers = self.headers("admin-token")

        movement = self.client.post("/api/movements", headers=headers)
        attendance = self.client.post("/api/attendance", headers=headers)

        self.assertEqual(movement.status_code, 400)
        self.assertEqual(attendance.status_code, 400)

    def test_api_returns_not_found_for_movement_of_unknown_employee(self):
        response = self.client.post(
            "/api/movements",
            json={
                "empleado_id": "missing-employee",
                "tipo": "ACUMULACION",
                "horas": 1,
                "detalle": "Prueba",
            },
            headers=self.headers("admin-token"),
        )

        self.assertEqual(response.status_code, 404)

    def test_web_serves_index_and_allowlisted_assets_only(self):
        index = self.client.get("/")
        stylesheet = self.client.get("/static/css/styles.css")
        private_file = self.client.get("/requirements.txt")

        self.assertEqual(index.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(private_file.status_code, 404)


if __name__ == "__main__":
    unittest.main()
