"""Application errors independent of the HTTP transport."""


class ApplicationError(Exception):
    """Base class for expected application-service failures."""


class AuthenticationError(ApplicationError):
    """The supplied identity token is missing, invalid, or expired."""


class AuthorizationError(ApplicationError):
    """The authenticated user is not allowed to perform the operation."""


class ServiceUnavailableError(ApplicationError):
    """An external service required by the use case is unavailable."""
