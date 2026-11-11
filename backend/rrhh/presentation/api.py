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
