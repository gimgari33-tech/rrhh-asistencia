"""Unit tests for exact hour and bank movement calculations."""

import unittest
from decimal import Decimal

from backend.rrhh.domain.errors import ValidationError
from backend.rrhh.domain.rules import movement_type, next_balance, positive_hours


class PositiveHoursTests(unittest.TestCase):
    def test_accepts_positive_hours_with_two_decimal_places(self):
        self.assertEqual(positive_hours("2.50"), Decimal("2.50"))
        self.assertEqual(positive_hours("0.01"), Decimal("0.01"))

    def test_rejects_non_positive_invalid_and_over_precision_values(self):
        invalid_values = ("0", "-1", "not-a-number", "1.234", "NaN", "Infinity")
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                positive_hours(value)

    def test_rejects_values_above_the_supported_maximum(self):
        with self.assertRaises(ValidationError):
            positive_hours("100000000.00")


class MovementRulesTests(unittest.TestCase):
    def test_normalizes_only_supported_movement_types(self):
        self.assertEqual(movement_type("acumulacion"), "ACUMULACION")
        self.assertEqual(movement_type("DEVOLUCION"), "DEVOLUCION")
        for value in ("otro", "", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                movement_type(value)

    def test_accumulation_adds_exact_decimal_hours(self):
        balance = next_balance(
            Decimal("0.00"), positive_hours("2.50"), movement_type("ACUMULACION")
        )
        self.assertEqual(balance, Decimal("2.50"))

    def test_refund_subtracts_exact_decimal_hours(self):
        balance = next_balance(
            Decimal("5.00"), positive_hours("2.50"), movement_type("DEVOLUCION")
        )
        self.assertEqual(balance, Decimal("2.50"))

    def test_refund_cannot_make_the_balance_negative(self):
        with self.assertRaisesRegex(ValidationError, "supera las horas disponibles"):
            next_balance(
                Decimal("2.00"),
                positive_hours("3.00"),
                movement_type("DEVOLUCION"),
            )


if __name__ == "__main__":
    unittest.main()
