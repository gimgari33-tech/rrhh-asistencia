"""HTTP authentication boundary for protected API routes."""

from functools import wraps

from flask import current_app, g, jsonify, request

from ..domain.errors import ApplicationError, AuthorizationError


def require_authorized_user(required_role=None):
    def decorate(view_function):
        @wraps(view_function)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            scheme, separator, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not separator or not token.strip():
                return jsonify({"error": "Iniciá sesión para continuar."}), 401

            services = current_app.extensions["rrhh_services"]
            try:
                user = services["access"].authenticate(token.strip())
            except ApplicationError as error:
                return jsonify({"error": str(error)}), error.status_code

            if required_role and user.rol != required_role:
                error = AuthorizationError("No tenés permisos para realizar esta acción.")
                return jsonify({"error": str(error)}), error.status_code

            g.current_user = user
            return view_function(*args, **kwargs)

        return wrapped

    return decorate
