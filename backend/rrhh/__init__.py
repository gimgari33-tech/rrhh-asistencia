"""Application factory and dependency wiring for RRHH Asistencia."""

from flask import Flask, jsonify

from .application.services import (
    AccessService,
    AttendanceService,
    EmployeeService,
    HoursService,
)
from .config import Config
from .domain.errors import ApplicationError
from .infrastructure.firebase import FirebaseRuntime
from .infrastructure.firebase_identity import FirebaseIdentityProvider
from .infrastructure.firestore_repositories import (
    FirestoreAttendanceRepository,
    FirestoreAuthorizationRepository,
    FirestoreEmployeeRepository,
    FirestoreHoursRepository,
)
from .presentation.api import api
from .presentation.web import web


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    firebase_runtime = FirebaseRuntime(app.config["FIREBASE_PROJECT_ID"])
    employee_repository = FirestoreEmployeeRepository(firebase_runtime)
    app.extensions["rrhh_services"] = {
        "access": AccessService(
            FirebaseIdentityProvider(firebase_runtime),
            FirestoreAuthorizationRepository(firebase_runtime),
        ),
        "employees": EmployeeService(employee_repository),
        "hours": HoursService(FirestoreHoursRepository(firebase_runtime)),
        "attendance": AttendanceService(
            employee_repository,
            FirestoreAttendanceRepository(firebase_runtime),
        ),
    }

    @app.errorhandler(ApplicationError)
    def handle_application_error(error):
        return jsonify({"error": str(error)}), error.status_code

    app.register_blueprint(api)
    app.register_blueprint(web)
    return app
