"""Environment-backed application configuration."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Config:
    PROJECT_ROOT = PROJECT_ROOT
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "empleados-cbf0b")
    JSON_AS_ASCII = False
