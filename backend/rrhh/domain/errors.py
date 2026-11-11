"""Errors that represent expected application outcomes."""


class ApplicationError(Exception):
    """Base error translated to a safe HTTP response by the API layer."""

    status_code = 500


class AuthenticationError(ApplicationError):
    status_code = 401


class AuthorizationError(ApplicationError):
    status_code = 403


class ValidationError(ApplicationError):
    status_code = 400


class NotFoundError(ApplicationError):
    status_code = 404


class ServiceUnavailableError(ApplicationError):
    status_code = 503
