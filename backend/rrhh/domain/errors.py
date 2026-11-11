"""Errors and validation outcomes owned by the business domain."""


class DomainError(Exception):
    """Base class for expected business-rule failures."""


class ValidationError(DomainError):
    """A supplied value violates a business rule."""


class NotFoundError(DomainError):
    """A requested domain object does not exist."""
