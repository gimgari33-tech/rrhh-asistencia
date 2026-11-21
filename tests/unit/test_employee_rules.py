"""Unit tests for employee values and validation rules."""

import unittest

from backend.rrhh.domain.errors import ValidationError
from backend.rrhh.domain.rules import employee_name


class EmployeeNameTests(unittest.TestCase):
    def test_trims_surrounding_whitespace(self):
        self.assertEqual(employee_name("  Ana Pérez  "), "Ana Pérez")

    def test_accepts_name_at_maximum_length(self):
        name = "A" * 100
        self.assertEqual(employee_name(name), name)

    def test_rejects_empty_and_whitespace_only_names(self):
        for value in ("", "   ", "\t\n"):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                employee_name(value)

    def test_rejects_non_text_and_names_over_100_characters(self):
        for value in (None, 123, "A" * 101):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                employee_name(value)


if __name__ == "__main__":
    unittest.main()
