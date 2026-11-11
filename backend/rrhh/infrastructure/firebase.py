"""Firebase Admin SDK runtime, kept behind infrastructure adapters."""

from threading import Lock

import firebase_admin
from firebase_admin import firestore as admin_firestore


class FirebaseRuntime:
    def __init__(self, project_id):
        self._project_id = project_id
        self._app = None
        self._database = None
        self._lock = Lock()

    def app(self):
        if self._app is not None:
            return self._app
        with self._lock:
            if self._app is not None:
                return self._app
            try:
                self._app = firebase_admin.get_app()
            except ValueError:
                self._app = firebase_admin.initialize_app(
                    options={"projectId": self._project_id}
                )
            return self._app

    def database(self):
        if self._database is not None:
            return self._database
        firebase_app = self.app()
        with self._lock:
            if self._database is None:
                self._database = admin_firestore.client(app=firebase_app)
            return self._database
