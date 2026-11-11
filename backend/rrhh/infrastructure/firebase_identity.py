"""Firebase Authentication adapter for verifying browser ID tokens."""

import firebase_admin.auth as firebase_auth
from firebase_admin.exceptions import FirebaseError

from ..application.errors import AuthenticationError, ServiceUnavailableError


class FirebaseIdentityProvider:
    def __init__(self, firebase_runtime):
        self._firebase_runtime = firebase_runtime

    def verify_id_token(self, token):
        try:
            firebase_app = self._firebase_runtime.app()
        except Exception as error:
            raise ServiceUnavailableError(
                "El backend no está configurado para acceder a Firebase."
            ) from error

        try:
            return firebase_auth.verify_id_token(token, app=firebase_app)
        except (FirebaseError, ValueError) as error:
            raise AuthenticationError(
                "La sesión no es válida o venció. Volvé a iniciar sesión."
            ) from error
