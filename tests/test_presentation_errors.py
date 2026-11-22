"""HTTP status mapping tests for expected and unexpected failures."""

import unittest

from flask import Flask

from backend.rrhh.application.errors import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ServiceUnavailableError,
)
from backend.rrhh.domain.errors import DomainError, NotFoundError, ValidationError
from backend.rrhh.presentation.errors import error_response


class ErrorResponseTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)

    def test_maps_authentication_and_authorization_errors(self):
        self.assertEqual(self.status_for(AuthenticationError("invalid")), 401)
        self.assertEqual(self.status_for(AuthorizationError("forbidden")), 403)

    def test_maps_not_found_and_validation_errors(self):
        self.assertEqual(self.status_for(NotFoundError("missing")), 404)
        self.assertEqual(self.status_for(ValidationError("invalid")), 400)

    def test_maps_unavailable_and_unclassified_errors(self):
        self.assertEqual(self.status_for(ServiceUnavailableError("offline")), 503)
        self.assertEqual(self.status_for(ApplicationError("application")), 500)
        self.assertEqual(self.status_for(DomainError("domain")), 500)
        self.assertEqual(self.status_for(RuntimeError("unexpected")), 500)

    def status_for(self, error):
        with self.app.app_context():
            response, status = error_response(error)
        self.assertEqual(response.get_json(), {"error": str(error)})
        return status


if __name__ == "__main__":
    unittest.main()
