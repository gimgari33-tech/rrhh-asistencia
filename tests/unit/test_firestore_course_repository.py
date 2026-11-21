import unittest
from datetime import date

from backend.rrhh.domain.errors import NotFoundError
from backend.rrhh.domain.models import Employee
from backend.rrhh.infrastructure.firestore_repositories import (
    FirestoreCourseRepository,
)


class FakeSnapshot:
    def __init__(self, reference):
        self.reference = reference
        self.id = reference.id
        self.exists = self.id in reference._collection.documents

    def to_dict(self):
        data = self.reference._collection.documents.get(self.id)
        return dict(data) if data is not None else None


class FakeReference:
    def __init__(self, collection, document_id):
        self._collection = collection
        self.id = document_id

    def get(self):
        return FakeSnapshot(self)

    def set(self, data, merge=False):
        if merge:
            current = self._collection.documents.get(self.id, {})
            self._collection.documents[self.id] = {**current, **data}
        else:
            self._collection.documents[self.id] = dict(data)

    def collection(self, name):
        return self._collection.database.subcollection(
            self._collection.name, self.id, name
        )


class FakeQuery:
    def __init__(self, collection, filter_value=None):
        self.collection = collection
        self.filter_value = filter_value

    def stream(self):
        snapshots = [
            FakeSnapshot(FakeReference(self.collection, document_id))
            for document_id in self.collection.documents
        ]
        if self.filter_value is None:
            return snapshots
        field, operator, value = self.filter_value
        if operator != "==":
            raise AssertionError("The fake only supports equality filters.")
        return [
            snapshot
            for snapshot in snapshots
            if (snapshot.to_dict() or {}).get(field) == value
        ]


class FakeCollection:
    def __init__(self, database, name):
        self.database = database
        self.name = name
        self.documents = {}

    def document(self, document_id=None):
        if document_id is None:
            document_id = self.database.next_document_id()
        return FakeReference(self, document_id)

    def order_by(self, field):
        del field
        return self

    def where(self, field, operator, value):
        return FakeQuery(self, (field, operator, value))

    def stream(self):
        return FakeQuery(self).stream()


class FakeDatabase:
    def __init__(self):
        self.collections = {}
        self.subcollections = {}
        self.document_sequence = 0

    def collection(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection(self, name)
        return self.collections[name]

    def subcollection(self, parent_collection, parent_id, name):
        key = (parent_collection, parent_id, name)
        if key not in self.subcollections:
            self.subcollections[key] = FakeCollection(self, name)
        return self.subcollections[key]

    def next_document_id(self):
        self.document_sequence += 1
        return f"generated-{self.document_sequence}"


class FakeFirebaseRuntime:
    def __init__(self, database):
        self._database = database

    def database(self):
        return self._database


class FirestoreCourseRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.database.collection("empleados").document("employee-1").set(
            {"nombre": "Ana Pérez"}
        )
        self.repository = FirestoreCourseRepository(FakeFirebaseRuntime(self.database))

    def test_course_assignment_is_idempotent_and_completion_removes_pending_course(
        self,
    ):
        course = self.repository.create_course(
            "Seguridad e higiene", "Capacitación anual"
        )
        employee = Employee(id="employee-1", nombre="Ana Pérez")

        first_assignment = self.repository.assign(employee, course)
        second_assignment = self.repository.assign(employee, course)
        pending_before = self.repository.list_pending()
        completed = self.repository.complete(
            employee.id,
            course.id,
            date(2026, 11, 20),
        )

        self.assertEqual(first_assignment.id, course.id)
        self.assertEqual(second_assignment, first_assignment)
        self.assertEqual(len(pending_before), 1)
        self.assertTrue(completed.completado)
        self.assertEqual(completed.fecha_completacion, date(2026, 11, 20))
        self.assertEqual(self.repository.list_pending(), [])
        self.assertEqual(len(self.repository.list_courses()), 1)
        self.assertEqual(self.repository.get_course_by_id(course.id), course)
        self.assertEqual(
            self.repository.list_for_employee(employee.id)[0].fecha_completacion,
            date(2026, 11, 20),
        )

    def test_completion_requires_an_existing_assignment(self):
        with self.assertRaises(NotFoundError):
            self.repository.complete("employee-1", "missing-course", date.today())


if __name__ == "__main__":
    unittest.main()
