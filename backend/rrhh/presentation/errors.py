"""Translate domain and application failures into HTTP responses."""

from flask import jsonify

from ..application.errors import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ServiceUnavailableError,
)
from ..domain.errors import DomainError, NotFoundError, ValidationError


def error_response(error):
    if isinstance(error, AuthenticationError):
        status = 401
    elif isinstance(error, AuthorizationError):
        status = 403
    elif isinstance(error, NotFoundError):
        status = 404
    elif isinstance(error, ValidationError):
        status = 400
    elif isinstance(error, ServiceUnavailableError):
        status = 503
    elif isinstance(error, (ApplicationError, DomainError)):
        status = 500
    else:
        status = 500
    return jsonify({"error": str(error)}), status
