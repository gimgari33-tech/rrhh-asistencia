"""Flask routes: translate HTTP payloads to application use cases."""

from flask import Blueprint, current_app, g, jsonify, request

from .auth import require_authorized_user

api = Blueprint("api", __name__, url_prefix="/api")


def _services():
    return current_app.extensions["rrhh_services"]


@api.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@api.get("/auth/me")
@require_authorized_user()
def current_user():
    return jsonify(g.current_user.to_dict()), 200


@api.get("/employees")
@require_authorized_user()
def get_employees():
    employees = _services()["employees"].list()
    return jsonify([employee.to_dict() for employee in employees]), 200


@api.post("/employees")
@require_authorized_user("SUPERADMIN")
def create_employee():
    payload = request.get_json(silent=True)
    name = payload.get("nombre") if isinstance(payload, dict) else None
    employee = _services()["employees"].create(name)
    return jsonify(employee.to_dict()), 201


@api.get("/movements")
@require_authorized_user()
def get_movements():
    movements = _services()["hours"].list_recent()
    return jsonify([movement.to_dict() for movement in movements]), 200


@api.post("/movements")
@require_authorized_user("SUPERADMIN")
def create_movement():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "El movimiento enviado no es válido."}), 400

    movement = _services()["hours"].create(
        payload.get("empleado_id"),
        payload.get("tipo"),
        payload.get("horas"),
        payload.get("detalle", ""),
    )
    return jsonify(movement.to_dict()), 201


@api.get("/attendance")
@require_authorized_user()
def get_attendance():
    records = _services()["attendance"].list_recent()
    return jsonify([record.to_dict() for record in records]), 200


@api.post("/attendance")
@require_authorized_user("SUPERADMIN")
def create_attendance():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "La asistencia enviada no es válida."}), 400

    record = _services()["attendance"].create(
        payload.get("empleado_id"),
        payload.get("estado"),
        payload.get("fecha"),
    )
    return jsonify(record.to_dict()), 201


@api.get("/courses")
@require_authorized_user()
def get_courses():
    courses = _services()["courses"].list_courses()
    return jsonify([course.to_dict() for course in courses]), 200


@api.post("/courses")
@require_authorized_user("SUPERADMIN")
def create_course():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "El curso enviado no es válido."}), 400
    course = _services()["courses"].create(
        payload.get("nombre"), payload.get("descripcion", "")
    )
    return jsonify(course.to_dict()), 201


@api.get("/courses/pending")
@require_authorized_user()
def get_pending_courses():
    assignments = _services()["courses"].list_pending()
    return jsonify([assignment.to_dict() for assignment in assignments]), 200


@api.post("/employees/<employee_id>/courses")
@require_authorized_user("SUPERADMIN")
def assign_course(employee_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "La asignación enviada no es válida."}), 400
    assignment = _services()["courses"].assign(employee_id, payload.get("curso_id"))
    return jsonify(assignment.to_dict()), 201


@api.get("/employees/<employee_id>/courses")
@require_authorized_user()
def get_employee_courses(employee_id):
    course_service = _services()["courses"]
    assignments = course_service.list_for_employee(employee_id)
    pending = [assignment for assignment in assignments if not assignment.completado]
    return jsonify(
        {
            "empleado_id": employee_id,
            "asignaciones": [assignment.to_dict() for assignment in assignments],
            "pendientes": [assignment.to_dict() for assignment in pending],
            "porcentaje_completado": course_service.completion_percentage(assignments),
        }
    ), 200


@api.post("/employees/<employee_id>/courses/<course_id>/complete")
@require_authorized_user("SUPERADMIN")
def complete_employee_course(employee_id, course_id):
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return jsonify({"error": "La fecha de finalización enviada no es válida."}), 400
    assignment = _services()["courses"].complete(
        employee_id,
        course_id,
        payload.get("fecha_completacion"),
    )
    return jsonify(assignment.to_dict()), 200
