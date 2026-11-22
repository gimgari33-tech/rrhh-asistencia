"""Unit tests for attendance dates and the closed status catalogue."""

import unittest

from backend.rrhh.domain.errors import ValidationError
from backend.rrhh.domain.rules import (
    ATTENDANCE_STATUSES,
    attendance_date,
    attendance_status,
)


class AttendanceDateTests(unittest.TestCase):
    def test_accepts_iso_calendar_date(self):
        self.assertEqual(attendance_date("2026-11-15"), "2026-11-15")

    def test_rejects_invalid_or_non_canonical_dates(self):
        invalid_values = ("2026-02-31", "11/15/2026", "2026-1-5", "", 20261115, None)
        for value in invalid_values:
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                attendance_date(value)


class AttendanceStatusTests(unittest.TestCase):
    def test_accepts_all_six_supported_statuses(self):
        for value in ATTENDANCE_STATUSES:
            with self.subTest(value=value):
                self.assertEqual(attendance_status(value), value)
        self.assertEqual(len(ATTENDANCE_STATUSES), 6)

    def test_rejects_statuses_outside_the_closed_catalogue(self):
        for value in ("presente", "Ausente", "", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                attendance_status(value)


if __name__ == "__main__":
    unittest.main()
