"""Firestore implementations of the application repository ports."""

import logging
from decimal import Decimal
from uuid import uuid4

from firebase_admin import firestore as admin_firestore
from google.cloud import firestore as google_firestore

from ..application.errors import ApplicationError, ServiceUnavailableError
from ..domain.errors import DomainError, NotFoundError
from ..domain.models import (
    AttendanceRecord,
    Course,
    CourseAssignment,
    Employee,
    HourMovement,
)
from ..domain.rules import next_balance

logger = logging.getLogger(__name__)


def _serialize_datetime(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value if isinstance(value, str) else ""


def _run_firestore(operation, message):
    try:
        return operation()
    except (ApplicationError, DomainError):
        raise
    except Exception as error:
        logger.exception("Firestore operation failed: %s", message)
        raise ServiceUnavailableError(message) from error


class FirestoreAuthorizationRepository:
    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def get_by_uid(self, uid):
        def operation():
            snapshot = (
                self._firebase_runtime.database()
                .collection("usuarios_autorizados")
                .document(uid)
                .get()
            )
            return snapshot.to_dict() if snapshot.exists else None

        return _run_firestore(
            operation, "No se pudo verificar el acceso en este momento."
        )


class FirestoreEmployeeRepository:
    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def list_with_balances(self):
        def operation():
            database = self._firebase_runtime.database()
            employees = []
            for snapshot in (
                database.collection("empleados").order_by("nombre").stream()
            ):
                employee_data = snapshot.to_dict() or {}
                bank_snapshot = (
                    database.collection("bancos_horas").document(snapshot.id).get()
                )
                bank_data = bank_snapshot.to_dict() if bank_snapshot.exists else {}
                employees.append(
                    Employee(
                        id=snapshot.id,
                        nombre=employee_data.get("nombre", ""),
                        creado_en=_serialize_datetime(employee_data.get("creadoEn")),
                        saldo_horas=Decimal(
                            str((bank_data or {}).get("saldoHoras", 0) or 0)
                        ),
                    )
                )
            return employees

        return _run_firestore(operation, "No se pudieron cargar los empleados.")

    def get_by_id(self, employee_id):
        def operation():
            snapshot = (
                self._firebase_runtime.database()
                .collection("empleados")
                .document(employee_id)
                .get()
            )
            if not snapshot.exists:
                return None
            employee_data = snapshot.to_dict() or {}
            return Employee(
                id=snapshot.id,
                nombre=employee_data.get("nombre", ""),
                creado_en=_serialize_datetime(employee_data.get("creadoEn")),
            )

        return _run_firestore(operation, "No se pudo consultar el empleado.")

    def create(self, name):
        def operation():
            database = self._firebase_runtime.database()
            employee_ref = database.collection("empleados").document()
            bank_ref = database.collection("bancos_horas").document(employee_ref.id)
            batch = database.batch()
            batch.set(
                employee_ref,
                {
                    "nombre": name,
                    "creadoEn": admin_firestore.SERVER_TIMESTAMP,
                },
            )
            batch.set(
                bank_ref,
                {
                    "empleadoId": employee_ref.id,
                    "saldoHoras": 0,
                    "actualizadoEn": admin_firestore.SERVER_TIMESTAMP,
                },
            )
            batch.commit()
            return Employee(id=employee_ref.id, nombre=name)

        return _run_firestore(operation, "No se pudo agregar el empleado.")


class FirestoreHoursRepository:
    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def list_recent(self, limit=100):
        def operation():
            query = (
                self._firebase_runtime.database()
                .collection("movimientos_banco_horas")
                .order_by("fecha", direction=google_firestore.Query.DESCENDING)
                .limit(limit)
            )
            movements = []
            for snapshot in query.stream():
                data = snapshot.to_dict() or {}
                movements.append(
                    HourMovement(
                        id=snapshot.id,
                        empleado_id=data.get("empleadoId", ""),
                        empleado_nombre=data.get("empleadoNombre", ""),
                        tipo=data.get("tipo", ""),
                        horas=Decimal(str(data.get("horas", 0) or 0)),
                        saldo_resultante=Decimal(
                            str(data.get("saldoResultante", 0) or 0)
                        ),
                        detalle=data.get("detalle", "") or "",
                        fecha=_serialize_datetime(data.get("fecha")),
                    )
                )
            return movements

        return _run_firestore(operation, "No se pudieron cargar los movimientos.")

    def create_movement(self, employee_id, kind, hours, detail):
        def operation():
            database = self._firebase_runtime.database()
            employee_ref = database.collection("empleados").document(employee_id)
            bank_ref = database.collection("bancos_horas").document(employee_id)
            movement_ref = database.collection("movimientos_banco_horas").document(
                str(uuid4())
            )
            transaction = database.transaction()

            @google_firestore.transactional
            def commit_movement(active_transaction):
                employee_snapshot = employee_ref.get(transaction=active_transaction)
                if not employee_snapshot.exists:
                    raise NotFoundError("Empleado no encontrado.")

                bank_snapshot = bank_ref.get(transaction=active_transaction)
                bank_data = bank_snapshot.to_dict() if bank_snapshot.exists else {}
                current_balance = (bank_data or {}).get("saldoHoras", 0) or 0
                resulting_balance = next_balance(current_balance, hours, kind)
                employee_data = employee_snapshot.to_dict() or {}

                active_transaction.set(
                    bank_ref,
                    {
                        "empleadoId": employee_id,
                        "saldoHoras": float(resulting_balance),
                        "actualizadoEn": admin_firestore.SERVER_TIMESTAMP,
                    },
                    merge=True,
                )
                active_transaction.set(
                    movement_ref,
                    {
                        "empleadoId": employee_id,
                        "empleadoNombre": employee_data.get("nombre", ""),
                        "tipo": kind,
                        "horas": float(hours),
                        "saldoResultante": float(resulting_balance),
                        "detalle": detail,
                        "fecha": admin_firestore.SERVER_TIMESTAMP,
                    },
                )
                return employee_data.get("nombre", ""), resulting_balance

            employee_name, resulting_balance = commit_movement(transaction)
            return HourMovement(
                id=movement_ref.id,
                empleado_id=employee_id,
                empleado_nombre=employee_name,
                tipo=kind,
                horas=hours,
                saldo_resultante=resulting_balance,
                detalle=detail,
            )

        return _run_firestore(operation, "No se pudo registrar el movimiento.")


class FirestoreAttendanceRepository:
    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def list_recent(self, limit=100):
        def operation():
            query = (
                self._firebase_runtime.database()
                .collection("asistencia")
                .order_by("creadoEn", direction=google_firestore.Query.DESCENDING)
                .limit(limit)
            )
            records = []
            for snapshot in query.stream():
                data = snapshot.to_dict() or {}
                records.append(
                    AttendanceRecord(
                        id=snapshot.id,
                        empleado_id=data.get("empleadoId", ""),
                        empleado_nombre=data.get("empleadoNombre", ""),
                        estado=data.get("estado", ""),
                        fecha=data.get("fecha", ""),
                        creado_en=_serialize_datetime(data.get("creadoEn")),
                    )
                )
            return records

        return _run_firestore(operation, "No se pudieron cargar las asistencias.")

    def create(self, employee_id, employee_name, status, attendance_day):
        def operation():
            database = self._firebase_runtime.database()
            record_ref = database.collection("asistencia").document()
            record_ref.set(
                {
                    "empleadoId": employee_id,
                    "empleadoNombre": employee_name,
                    "estado": status,
                    "fecha": attendance_day,
                    "creadoEn": admin_firestore.SERVER_TIMESTAMP,
                }
            )
            return AttendanceRecord(
                id=record_ref.id,
                empleado_id=employee_id,
                empleado_nombre=employee_name,
                estado=status,
                fecha=attendance_day,
            )

        return _run_firestore(operation, "No se pudo guardar la asistencia.")


class FirestoreCourseRepository:
    COLLECTION = "cursos"
    ASSIGNMENTS_SUBCOLLECTION = "cursos_asignados"

    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def list_courses(self):
        def operation():
            query = self._firebase_runtime.database().collection(self.COLLECTION)
            courses = []
            for snapshot in query.order_by("nombre").stream():
                data = snapshot.to_dict() or {}
                courses.append(self._course_from_snapshot(snapshot.id, data))
            return courses

        return _run_firestore(operation, "No se pudieron cargar los cursos.")

    def get_course_by_id(self, course_id):
        def operation():
            snapshot = (
                self._firebase_runtime.database()
                .collection(self.COLLECTION)
                .document(course_id)
                .get()
            )
            return (
                self._course_from_snapshot(snapshot.id, snapshot.to_dict() or {})
                if snapshot.exists
                else None
            )

        return _run_firestore(operation, "No se pudo consultar el curso.")

    def create_course(self, name, description):
        def operation():
            reference = (
                self._firebase_runtime.database()
                .collection(self.COLLECTION)
                .document()
            )
            reference.set({
                "nombre": name,
                "descripcion": description,
                "creadoEn": admin_firestore.SERVER_TIMESTAMP,
            })
            return Course(id=reference.id, nombre=name, descripcion=description)

        return _run_firestore(operation, "No se pudo crear el curso.")

    def assign(self, employee, course):
        def operation():
            database = self._firebase_runtime.database()
            employee_reference = database.collection("empleados").document(employee.id)
            employee_snapshot = employee_reference.get()
            if not employee_snapshot.exists:
                raise NotFoundError("Empleado no encontrado.")

            course_reference = database.collection(self.COLLECTION).document(course.id)
            course_snapshot = course_reference.get()
            if not course_snapshot.exists:
                raise NotFoundError("Curso no encontrado.")
            course_data = course_snapshot.to_dict() or {}
            employee_data = employee_snapshot.to_dict() or {}
            assignment_reference = employee_reference.collection(
                self.ASSIGNMENTS_SUBCOLLECTION
            ).document(course.id)
            assignment_snapshot = assignment_reference.get()
            if assignment_snapshot.exists:
                return self._assignment_from_snapshot(
                    assignment_snapshot.id,
                    assignment_snapshot.to_dict() or {},
                )

            assignment_data = {
                "empleadoId": employee.id,
                "empleadoNombre": employee_data.get("nombre", employee.nombre),
                "cursoId": course.id,
                "cursoNombre": course_data.get("nombre", course.nombre),
                "completado": False,
                "fechaCompletacion": None,
                "fechaAsignacion": admin_firestore.SERVER_TIMESTAMP,
            }
            assignment_reference.set(assignment_data)
            return self._assignment_from_snapshot(course.id, assignment_data)

        return _run_firestore(operation, "No se pudo asignar el curso.")

    def complete(self, employee_id, course_id, completed_on):
        def operation():
            assignment_reference = (
                self._firebase_runtime.database()
                .collection("empleados")
                .document(employee_id)
                .collection(self.ASSIGNMENTS_SUBCOLLECTION)
                .document(course_id)
            )
            snapshot = assignment_reference.get()
            if not snapshot.exists:
                raise NotFoundError("El curso no está asignado a este empleado.")
            assignment = self._assignment_from_snapshot(
                snapshot.id,
                snapshot.to_dict() or {},
            )
            completed_assignment = assignment.marcar_completado(completed_on)
            assignment_reference.set(
                {
                    "completado": completed_assignment.completado,
                    "fechaCompletacion": (
                        completed_assignment.fecha_completacion.isoformat()
                        if completed_assignment.fecha_completacion
                        else None
                    ),
                },
                merge=True,
            )
            return completed_assignment

        return _run_firestore(operation, "No se pudo registrar la finalización del curso.")

    def list_for_employee(self, employee_id):
        def operation():
            assignments = (
                self._firebase_runtime.database()
                .collection("empleados")
                .document(employee_id)
                .collection(self.ASSIGNMENTS_SUBCOLLECTION)
                .stream()
            )
            return [
                self._assignment_from_snapshot(
                    snapshot.id,
                    snapshot.to_dict() or {},
                )
                for snapshot in assignments
            ]

        return _run_firestore(operation, "No se pudieron cargar los cursos del empleado.")

    def list_pending(self):
        def operation():
            database = self._firebase_runtime.database()
            pending = []
            for employee_snapshot in database.collection("empleados").stream():
                assignments = (
                    employee_snapshot.reference.collection(self.ASSIGNMENTS_SUBCOLLECTION)
                    .where("completado", "==", False)
                    .stream()
                )
                pending.extend(
                    self._assignment_from_snapshot(
                        snapshot.id,
                        snapshot.to_dict() or {},
                    )
                    for snapshot in assignments
                )
            return pending

        return _run_firestore(operation, "No se pudieron consultar los cursos pendientes.")

    @staticmethod
    def _course_from_snapshot(course_id, data):
        return Course(
            id=course_id,
            nombre=data.get("nombre", ""),
            descripcion=data.get("descripcion", ""),
            creado_en=_serialize_datetime(data.get("creadoEn")),
        )

    @staticmethod
    def _assignment_from_snapshot(assignment_id, data):
        raw_completion_date = data.get("fechaCompletacion")
        return CourseAssignment(
            id=assignment_id,
            empleado_id=data.get("empleadoId", ""),
            empleado_nombre=data.get("empleadoNombre", ""),
            curso_id=data.get("cursoId", assignment_id),
            curso_nombre=data.get("cursoNombre", ""),
            completado=data.get("completado", False),
            fecha_completacion=raw_completion_date,
        )
