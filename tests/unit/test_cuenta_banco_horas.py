"""Tests for the rich time-bank aggregate and its invariants."""

import unittest
from decimal import Decimal

from backend.rrhh.domain.errors import SaldoInsuficienteError, ValidationError
from backend.rrhh.domain.models import (
    CuentaBancoHoras,
    Horas,
    TipoMovimiento,
)


class HorasValueObjectTests(unittest.TestCase):
    def test_normalizes_decimal_values_without_losing_precision(self):
        self.assertEqual(Horas("2.50").valor, Decimal("2.50"))

    def test_rejects_negative_non_finite_and_over_precision_values(self):
        for value in ("-0.01", "NaN", "Infinity", "1.005"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Horas(value)

    def test_rejects_zero_as_a_movement_amount(self):
        with self.assertRaises(ValidationError):
            Horas.positiva("0.00")


class CuentaBancoHorasTests(unittest.TestCase):
    def setUp(self):
        self.account = CuentaBancoHoras("employee-1", Horas("4.00"))

    def test_credit_updates_balance_and_returns_a_movement(self):
        movement = self.account.acreditar_horas(Horas("2.50"), "Horas extra")

        self.assertEqual(self.account.saldo_actual, Horas("6.50"))
        self.assertEqual(movement.tipo, TipoMovimiento.ACUMULACION)
        self.assertEqual(movement.horas, Horas("2.50"))
        self.assertEqual(movement.saldo_resultante, Horas("6.50"))
        self.assertEqual(movement.detalle, "Horas extra")
        self.assertEqual(self.account.movimientos, (movement,))

    def test_debit_updates_balance_and_returns_a_movement(self):
        movement = self.account.debitar_horas(Horas("1.25"), "Compensación")

        self.assertEqual(self.account.saldo_actual, Horas("2.75"))
        self.assertEqual(movement.tipo, TipoMovimiento.DEVOLUCION)
        self.assertEqual(movement.saldo_resultante, Horas("2.75"))

    def test_insufficient_balance_raises_without_mutating_account(self):
        with self.assertRaises(SaldoInsuficienteError):
            self.account.debitar_horas(Horas("4.01"), "Exceso")

        self.assertEqual(self.account.saldo_actual, Horas("4.00"))
        self.assertEqual(self.account.movimientos, ())

    def test_balance_cannot_be_assigned_from_outside(self):
        with self.assertRaises(AttributeError):
            self.account.saldo_actual = Horas("0.00")

    def test_rejects_an_empty_employee_identifier(self):
        with self.assertRaises(ValidationError):
            CuentaBancoHoras("   ")


if __name__ == "__main__":
    unittest.main()
