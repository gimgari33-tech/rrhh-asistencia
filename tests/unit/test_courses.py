import unittest
from datetime import date
from decimal import Decimal

from backend.rrhh.application.services import CourseService
from backend.rrhh.domain.errors import NotFoundError, ValidationError
from backend.rrhh.domain.models import Course, CourseAssignment, Employee
from backend.rrhh.domain.rules import course_completion_percentage


def make_assignment(completed=False, completed_on=None):
    return CourseAssignment(
        id="course-1",
        empleado_id="employee-1",
        empleado_nombre="Ana Pérez",
        curso_id="course-1",
        curso_nombre="Seguridad e higiene",
        completado=completed,
        fecha_completacion=completed_on,
    )


class CourseModelTests(unittest.TestCase):
    def test_course_normalizes_name_and_description(self):
        course = Course(
            id="course-1",
            nombre="  Seguridad e higiene  ",
            descripcion="  Capacitación anual  ",
        )

        self.assertEqual(course.nombre, "Seguridad e higiene")
        self.assertEqual(course.descripcion, "Capacitación anual")

    def test_assignment_marks_completion_with_a_calendar_date(self):
        assignment = make_assignment().marcar_completado("2026-11-20")

        self.assertTrue(assignment.completado)
        self.assertEqual(assignment.fecha_completacion, date(2026, 11, 20))
        self.assertEqual(assignment.to_dict()["fecha_completacion"], "2026-11-20")

    def test_completed_assignment_requires_a_date(self):
        with self.assertRaises(ValidationError):
            make_assignment(completed=True)

    def test_pending_assignment_cannot_have_a_completion_date(self):
        with self.assertRaises(ValidationError):
            make_assignment(completed_on=date(2026, 11, 20))

    def test_invalid_completion_date_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_assignment().marcar_completado("20-11-2026")

    def test_course_completion_percentage_handles_empty_partial_and_full_lists(self):
        pending = make_assignment()
        completed = make_assignment(completed=True, completed_on=date(2026, 11, 20))

        self.assertEqual(course_completion_percentage([]), Decimal("0.00"))
        self.assertEqual(
            course_completion_percentage([completed, pending]), Decimal("50.00")
        )
        self.assertEqual(course_completion_percentage([completed]), Decimal("100.00"))


class FakeEmployeeRepository:
    def __init__(self):
        self.employees = {"employee-1": Employee(id="employee-1", nombre="Ana Pérez")}

    def get_by_id(self, employee_id):
        return self.employees.get(employee_id)


class FakeCourseRepository:
    def __init__(self):
        self.courses = {"course-1": Course("course-1", "Seguridad e higiene")}
        self.assignments = {}

    def get_course_by_id(self, course_id):
        return self.courses.get(course_id)

    def list_courses(self):
        return list(self.courses.values())

    def create_course(self, name, description):
        course = Course("course-2", name, description)
        self.courses[course.id] = course
        return course

    def assign(self, employee, course):
        assignment = make_assignment()
        self.assignments[(employee.id, course.id)] = assignment
        return assignment

    def complete(self, employee_id, course_id, completed_on):
        assignment = self.assignments.get((employee_id, course_id))
        if assignment is None:
            raise NotFoundError("Curso no asignado.")
        completed = assignment.marcar_completado(completed_on)
        self.assignments[(employee_id, course_id)] = completed
        return completed

    def list_for_employee(self, employee_id):
        return [
            assignment
            for (assigned_employee_id, _), assignment in self.assignments.items()
            if assigned_employee_id == employee_id
        ]

    def list_pending(self):
        return [
            assignment
            for assignment in self.assignments.values()
            if not assignment.completado
        ]


class CourseServiceTests(unittest.TestCase):
    def test_assign_use_case_connects_employee_and_course(self):
        service = CourseService(FakeEmployeeRepository(), FakeCourseRepository())

        assignment = service.assign("employee-1", "course-1")

        self.assertEqual(assignment.empleado_id, "employee-1")
        self.assertEqual(assignment.curso_id, "course-1")

    def test_assign_rejects_nonexistent_employee(self):
        service = CourseService(FakeEmployeeRepository(), FakeCourseRepository())

        with self.assertRaises(NotFoundError):
            service.assign("missing-employee", "course-1")

    def test_assign_rejects_nonexistent_course(self):
        service = CourseService(FakeEmployeeRepository(), FakeCourseRepository())

        with self.assertRaises(NotFoundError):
            service.assign("employee-1", "missing-course")

    def test_create_course_applies_domain_validation(self):
        service = CourseService(FakeEmployeeRepository(), FakeCourseRepository())

        course = service.create("  Primeros auxilios  ", "  Capacitación anual  ")

        self.assertEqual(course.nombre, "Primeros auxilios")
        self.assertEqual(course.descripcion, "Capacitación anual")

    def test_complete_use_case_records_the_validated_completion_date(self):
        service = CourseService(FakeEmployeeRepository(), FakeCourseRepository())
        service.assign("employee-1", "course-1")

        assignment = service.complete("employee-1", "course-1", "2026-11-20")

        self.assertTrue(assignment.completado)
        self.assertEqual(assignment.fecha_completacion, date(2026, 11, 20))


if __name__ == "__main__":
    unittest.main()
