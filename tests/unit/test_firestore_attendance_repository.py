import unittest
from hashlib import sha256

from backend.rrhh.domain.models import AttendanceRecord
from backend.rrhh.infrastructure.firestore_repositories import (
    FirestoreAttendanceRepository,
)


class FakeReference:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.id = document_id


class FakeSnapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self.id = reference.id
        self._data = data

    def to_dict(self):
        return dict(self._data)


class FakeQuery:
    def __init__(self, collection, field, operator, value):
        self.collection = collection
        self.filter = (field, operator, value)

    def stream(self):
        field, operator, value = self.filter
        if operator != "==":
            raise AssertionError("The fake only supports equality filters.")
        return [
            FakeSnapshot(FakeReference(self.collection, document_id), data)
            for document_id, data in self.collection.documents.items()
            if data.get(field) == value
        ]


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self.queries = []

    def where(self, field, operator, value):
        query = FakeQuery(self, field, operator, value)
        self.queries.append(query.filter)
        return query

    def document(self, document_id):
        return FakeReference(self, document_id)


class FakeBatch:
    def __init__(self):
        self.writes = []
        self.committed = False

    def set(self, reference, data):
        self.writes.append(("set", reference, dict(data)))

    def delete(self, reference):
        self.writes.append(("delete", reference, None))

    def commit(self):
        for operation, reference, data in self.writes:
            if operation == "set":
                reference.collection.documents[reference.id] = data
            else:
                reference.collection.documents.pop(reference.id, None)
        self.committed = True


class FakeDatabase:
    def __init__(self):
        self.attendance = FakeCollection()
        self.active_batch = None

    def collection(self, name):
        if name != "asistencia":
            raise AssertionError("Unexpected collection: " + name)
        return self.attendance

    def batch(self):
        self.active_batch = FakeBatch()
        return self.active_batch


class FakeFirebaseRuntime:
    def __init__(self, database):
        self._database = database

    def database(self):
        return self._database


class FirestoreAttendanceRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.database.attendance.documents = {
            "attendance-old": {
                "empleadoId": "employee-1",
                "empleadoNombre": "Nombre anterior",
                "estado": "Presente",
                "fecha": "2026-11-20",
                "creadoEn": "created-at-original",
            },
            "attendance-duplicate": {
                "empleadoId": "employee-1",
                "empleadoNombre": "Nombre anterior",
                "estado": "Presente",
                "fecha": "2026-11-20",
            },
            "attendance-other-day": {
                "empleadoId": "employee-1",
                "empleadoNombre": "Ana",
                "estado": "Franco",
                "fecha": "2026-11-19",
            },
        }
        self.repository = FirestoreAttendanceRepository(
            FakeFirebaseRuntime(self.database)
        )

    def test_save_day_updates_existing_rows_and_creates_stable_new_row(self):
        records = self.repository.save_day(
            [
                AttendanceRecord(
                    id="",
                    empleado_id="employee-1",
                    empleado_nombre="Ana",
                    estado="Franco",
                    fecha="2026-11-20",
                ),
                AttendanceRecord(
                    id="",
                    empleado_id="employee-2",
                    empleado_nombre="Luis",
                    estado="Presente",
                    fecha="2026-11-20",
                ),
            ]
        )

        saved = self.database.attendance.documents
        new_document_id = sha256(b"employee-2:2026-11-20").hexdigest()
        self.assertEqual(records[0].id, "attendance-old")
        self.assertEqual(records[1].id, new_document_id)
        self.assertEqual(saved["attendance-old"]["estado"], "Franco")
        self.assertEqual(saved["attendance-old"]["creadoEn"], "created-at-original")
        self.assertNotIn("attendance-duplicate", saved)
        self.assertEqual(saved[new_document_id]["empleadoNombre"], "Luis")
        self.assertEqual(saved["attendance-other-day"]["estado"], "Franco")
        self.assertEqual(
            self.database.attendance.queries, [("fecha", "==", "2026-11-20")]
        )
        self.assertTrue(self.database.active_batch.committed)

    def test_empty_day_does_not_make_a_firestore_request(self):
        class RuntimeWithoutDatabase:
            def database(self):
                raise AssertionError("An empty batch should not reach Firestore.")

        repository = FirestoreAttendanceRepository(RuntimeWithoutDatabase())

        self.assertEqual(repository.save_day([]), [])


if __name__ == "__main__":
    unittest.main()
