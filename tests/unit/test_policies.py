"""Tests for compensation strategies and their aggregate integration."""

import unittest
from decimal import Decimal

from backend.rrhh.domain.errors import ValidationError
from backend.rrhh.domain.models import CuentaBancoHoras, Horas
from backend.rrhh.domain.policies import (
    CompensacionDiaHabilExtra,
    CompensacionFeriadoFinDeSemana,
    CompensacionSimple,
)


class CompensationPolicyTests(unittest.TestCase):
    def test_simple_policy_credits_one_to_one(self):
        self.assertEqual(
            CompensacionSimple().calcular_credito(Decimal("4.00")),
            Decimal("4.00"),
        )

    def test_weekday_extra_policy_credits_one_and_a_half(self):
        self.assertEqual(
            CompensacionDiaHabilExtra().calcular_credito(Decimal("4.00")),
            Decimal("6.00"),
        )

    def test_weekend_holiday_policy_credits_double(self):
        self.assertEqual(
            CompensacionFeriadoFinDeSemana().calcular_credito(Decimal("4.00")),
            Decimal("8.00"),
        )

    def test_policy_rounds_to_cents_with_explicit_half_even_rule(self):
        policy = CompensacionDiaHabilExtra()

        self.assertEqual(policy.calcular_credito(Decimal("0.01")), Decimal("0.02"))
        self.assertEqual(policy.calcular_credito(Decimal("0.03")), Decimal("0.04"))

    def test_policies_reject_non_positive_or_invalid_hours(self):
        for value in (Decimal(0), Decimal(-1), Decimal("NaN")):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                CompensacionDiaHabilExtra().calcular_credito(value)

    def test_account_uses_policy_before_crediting_balance(self):
        account = CuentaBancoHoras("employee-1")

        movement = account.acreditar_horas(
            Horas("4.00"),
            "Sábado",
            CompensacionFeriadoFinDeSemana(),
        )

        self.assertEqual(movement.horas, Horas("8.00"))
        self.assertEqual(account.saldo_actual, Horas("8.00"))


if __name__ == "__main__":
    unittest.main()
