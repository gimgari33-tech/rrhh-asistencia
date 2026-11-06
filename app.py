import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from uuid import uuid4

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import firestore as admin_firestore
from firebase_admin.exceptions import FirebaseError
from flask import Flask, abort, current_app, g, jsonify, request, send_from_directory
from google.cloud import firestore as google_firestore


BASE_DIR = Path(__file__).resolve().parent
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "empleados-cbf0b")
CENT = Decimal("0.01")
MAX_HOURS = Decimal("99999999.99")
ROLES = {"SUPERADMIN", "INVITADO"}
ATTENDANCE_STATUSES = {
    "Presente",
    "Franco",
    "Falta sin aviso",
    "Falta con aviso",
    "Médico",
    "Vacaciones",
}
PUBLIC_ASSETS = {"app.js", "styles.css", "firebase-config.js"}


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(options={"projectId": FIREBASE_PROJECT_ID})


def get_db():
    database = current_app.extensions.get("rrhh_firestore")
    if database is None:
        database = admin_firestore.client(app=get_firebase_app())
        current_app.extensions["rrhh_firestore"] = database
    return database


def response_error(message, status):
    return jsonify({"error": message}), status


def serialize_datetime(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return ""


def decimal_hours(value):
    try:
        hours = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("La cantidad de horas es inválida.")

    if not hours.is_finite() or hours <= 0 or hours > MAX_HOURS or hours != hours.quantize(CENT):
        raise ValueError("Ingresá horas positivas, con hasta dos decimales.")
    return hours


def require_authorized_user(required_role=None):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            scheme, separator, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not separator or not token.strip():
                return response_error("Iniciá sesión para continuar.", 401)

            try:
                firebase_app = get_firebase_app()
            except Exception:
                current_app.logger.exception("Firebase Admin no pudo inicializarse.")
                return response_error("El backend no está configurado para acceder a Firebase.", 503)

            try:
                decoded_token = firebase_auth.verify_id_token(token.strip(), app=firebase_app)
            except (FirebaseError, ValueError):
                return response_error("La sesión no es válida o venció. Volvé a iniciar sesión.", 401)

            uid = decoded_token.get("uid")
            if not uid:
                return response_error("La sesión no identifica a un usuario.", 401)

            try:
                access_snapshot = get_db().collection("usuarios_autorizados").document(uid).get()
            except Exception:
                current_app.logger.exception("No se pudo consultar la lista de usuarios autorizados.")
                return response_error("No se pudo verificar el acceso en este momento.", 503)

            if not access_snapshot.exists:
                return response_error("Tu cuenta no está habilitada para esta aplicación.", 403)

            access = access_snapshot.to_dict() or {}
            if access.get("activo") is not True:
                return response_error("Tu cuenta no está habilitada para esta aplicación.", 403)

            role = str(access.get("rol") or "INVITADO").upper()
            if role not in ROLES:
                return response_error("El rol asignado a tu cuenta no es válido.", 403)
            if required_role and role != required_role:
                return response_error("No tenés permisos para realizar esta acción.", 403)

            g.current_user = {
                "uid": uid,
                "email": decoded_token.get("email", ""),
                "nombre": access.get("nombre") or decoded_token.get("name") or decoded_token.get("email", "Usuario"),
                "rol": role,
            }
            return view_function(*args, **kwargs)

        return wrapped

    return decorator


def create_app():
    app = Flask(__name__, static_folder=None)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/api/auth/me")
    @require_authorized_user()
    def current_user():
        return jsonify(g.current_user), 200

    @app.get("/api/employees")
    @require_authorized_user()
    def get_employees():
        try:
            database = get_db()
            employees = []
            for employee_snapshot in database.collection("empleados").order_by("nombre").stream():
                employee = employee_snapshot.to_dict() or {}
                bank_snapshot = database.collection("bancos_horas").document(employee_snapshot.id).get()
                bank = bank_snapshot.to_dict() if bank_snapshot.exists else {}
                employees.append({
                    "id": employee_snapshot.id,
                    "nombre": employee.get("nombre", ""),
                    "creado_en": serialize_datetime(employee.get("creadoEn")),
                    "saldo_horas": float((bank or {}).get("saldoHoras", 0) or 0),
                })
            return jsonify(employees), 200
        except Exception:
            current_app.logger.exception("No se pudieron cargar los empleados desde Firestore.")
            return response_error("No se pudieron cargar los empleados.", 503)

    @app.post("/api/employees")
    @require_authorized_user("SUPERADMIN")
    def create_employee():
        payload = request.get_json(silent=True)
        name_value = payload.get("nombre") if isinstance(payload, dict) else None
        if not isinstance(name_value, str):
            return response_error("El nombre del empleado es obligatorio.", 400)
        name = name_value.strip()
        if not name:
            return response_error("El nombre del empleado es obligatorio.", 400)
        if len(name) > 100:
            return response_error("El nombre no puede superar los 100 caracteres.", 400)

        try:
            database = get_db()
            employee_ref = database.collection("empleados").document()
            bank_ref = database.collection("bancos_horas").document(employee_ref.id)
            batch = database.batch()
            batch.set(employee_ref, {
                "nombre": name,
                "creadoEn": admin_firestore.SERVER_TIMESTAMP,
            })
            batch.set(bank_ref, {
                "empleadoId": employee_ref.id,
                "saldoHoras": 0,
                "actualizadoEn": admin_firestore.SERVER_TIMESTAMP,
            })
            batch.commit()
            return jsonify({
                "id": employee_ref.id,
                "nombre": name,
                "saldo_horas": 0,
            }), 201
        except Exception:
            current_app.logger.exception("No se pudo crear el empleado en Firestore.")
            return response_error("No se pudo agregar el empleado.", 503)

    @app.get("/api/movements")
    @require_authorized_user()
    def get_movements():
        try:
            query = get_db().collection("movimientos_banco_horas")
            snapshots = query.order_by("fecha", direction=google_firestore.Query.DESCENDING).limit(100).stream()
            movements = []
            for snapshot in snapshots:
                movement = snapshot.to_dict() or {}
                movements.append({
                    "id": snapshot.id,
                    "empleado_id": movement.get("empleadoId", ""),
                    "empleado_nombre": movement.get("empleadoNombre", ""),
                    "tipo": movement.get("tipo", ""),
                    "horas": float(movement.get("horas", 0) or 0),
                    "saldo_resultante": float(movement.get("saldoResultante", 0) or 0),
                    "detalle": movement.get("detalle", "") or "",
                    "fecha": serialize_datetime(movement.get("fecha")),
                })
            return jsonify(movements), 200
        except Exception:
            current_app.logger.exception("No se pudieron cargar los movimientos desde Firestore.")
            return response_error("No se pudieron cargar los movimientos.", 503)

    @app.post("/api/movements")
    @require_authorized_user("SUPERADMIN")
    def create_movement():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return response_error("El movimiento enviado no es válido.", 400)

        employee_id = str(payload.get("empleado_id") or "").strip()
        kind = str(payload.get("tipo") or "").upper()
        detail_value = payload.get("detalle", "")
        if not isinstance(detail_value, str):
            return response_error("El detalle debe ser texto.", 400)
        detail = detail_value.strip()
        if not employee_id:
            return response_error("Debe indicar un empleado.", 400)
        if kind not in {"ACUMULACION", "DEVOLUCION"}:
            return response_error("El tipo debe ser ACUMULACION o DEVOLUCION.", 400)
        if len(detail) > 250:
            return response_error("El detalle no puede superar los 250 caracteres.", 400)
        try:
            hours = decimal_hours(payload.get("horas"))
        except ValueError as error:
            return response_error(str(error), 400)

        try:
            database = get_db()
            employee_ref = database.collection("empleados").document(employee_id)
            bank_ref = database.collection("bancos_horas").document(employee_id)
            movement_ref = database.collection("movimientos_banco_horas").document(str(uuid4()))
            transaction = database.transaction()

            @google_firestore.transactional
            def save_movement(active_transaction):
                employee_snapshot = employee_ref.get(transaction=active_transaction)
                if not employee_snapshot.exists:
                    raise LookupError("Empleado no encontrado.")
                bank_snapshot = bank_ref.get(transaction=active_transaction)
                bank = bank_snapshot.to_dict() if bank_snapshot.exists else {}
                current_balance = Decimal(str((bank or {}).get("saldoHoras", 0) or 0))
                next_balance = current_balance + hours if kind == "ACUMULACION" else current_balance - hours
                if next_balance < 0:
                    raise ValueError("La devolución supera las horas disponibles.")
                next_balance = next_balance.quantize(CENT)
                employee = employee_snapshot.to_dict() or {}

                active_transaction.set(bank_ref, {
                    "empleadoId": employee_id,
                    "saldoHoras": float(next_balance),
                    "actualizadoEn": admin_firestore.SERVER_TIMESTAMP,
                }, merge=True)
                active_transaction.set(movement_ref, {
                    "empleadoId": employee_id,
                    "empleadoNombre": employee.get("nombre", ""),
                    "tipo": kind,
                    "horas": float(hours),
                    "saldoResultante": float(next_balance),
                    "detalle": detail,
                    "fecha": admin_firestore.SERVER_TIMESTAMP,
                })
                return float(next_balance)

            resulting_balance = save_movement(transaction)
            return jsonify({
                "id": movement_ref.id,
                "empleado_id": employee_id,
                "tipo": kind,
                "horas": float(hours),
                "saldo_resultante": resulting_balance,
                "detalle": detail,
            }), 201
        except LookupError as error:
            return response_error(str(error), 404)
        except ValueError as error:
            return response_error(str(error), 400)
        except Exception:
            current_app.logger.exception("No se pudo registrar el movimiento en Firestore.")
            return response_error("No se pudo registrar el movimiento.", 503)

    @app.get("/api/attendance")
    @require_authorized_user()
    def get_attendance():
        try:
            query = get_db().collection("asistencia")
            snapshots = query.order_by("creadoEn", direction=google_firestore.Query.DESCENDING).limit(100).stream()
            attendance = []
            for snapshot in snapshots:
                entry = snapshot.to_dict() or {}
                attendance.append({
                    "id": snapshot.id,
                    "empleado_id": entry.get("empleadoId", ""),
                    "empleado_nombre": entry.get("empleadoNombre", ""),
                    "estado": entry.get("estado", ""),
                    "fecha": entry.get("fecha", ""),
                    "creado_en": serialize_datetime(entry.get("creadoEn")),
                })
            return jsonify(attendance), 200
        except Exception:
            current_app.logger.exception("No se pudieron cargar las asistencias desde Firestore.")
            return response_error("No se pudieron cargar las asistencias.", 503)

    @app.post("/api/attendance")
    @require_authorized_user("SUPERADMIN")
    def create_attendance():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return response_error("La asistencia enviada no es válida.", 400)

        employee_id = str(payload.get("empleado_id") or "").strip()
        status = payload.get("estado")
        date_value = payload.get("fecha")
        if not employee_id:
            return response_error("Debe indicar un empleado.", 400)
        if not isinstance(status, str) or status not in ATTENDANCE_STATUSES:
            return response_error("El estado de asistencia no es válido.", 400)
        try:
            date.fromisoformat(str(date_value))
        except (TypeError, ValueError):
            return response_error("La fecha debe tener el formato AAAA-MM-DD.", 400)

        try:
            database = get_db()
            employee_ref = database.collection("empleados").document(employee_id)
            employee_snapshot = employee_ref.get()
            if not employee_snapshot.exists:
                return response_error("Empleado no encontrado.", 404)
            employee = employee_snapshot.to_dict() or {}
            attendance_ref = database.collection("asistencia").document()
            attendance_ref.set({
                "empleadoId": employee_id,
                "empleadoNombre": employee.get("nombre", ""),
                "estado": status,
                "fecha": str(date_value),
                "creadoEn": admin_firestore.SERVER_TIMESTAMP,
            })
            return jsonify({
                "id": attendance_ref.id,
                "empleado_id": employee_id,
                "empleado_nombre": employee.get("nombre", ""),
                "estado": status,
                "fecha": str(date_value),
            }), 201
        except Exception:
            current_app.logger.exception("No se pudo registrar la asistencia en Firestore.")
            return response_error("No se pudo guardar la asistencia.", 503)

    @app.get("/")
    def serve_index():
        return send_from_directory(BASE_DIR, "index.html")

    @app.get("/<path:asset>")
    def serve_asset(asset):
        if asset not in PUBLIC_ASSETS:
            abort(404)
        return send_from_directory(BASE_DIR, asset)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
