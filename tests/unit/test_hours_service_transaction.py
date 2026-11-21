"""Tests that the use case applies its command to a transactional aggregate."""

import unittest
from decimal import Decimal

from backend.rrhh.application.services import HoursService
from backend.rrhh.domain.errors import SaldoInsuficienteError
from backend.rrhh.domain.models import CuentaBancoHoras, TipoMovimiento


class InMemoryTransactionalHoursRepository:
    def __init__(self, account):
        self.account = account
        self.employee_id = None

    def transact_account(self, employee_id, operation):
        self.employee_id = employee_id
        return operation(self.account)


class HoursServiceTransactionTests(unittest.TestCase):
    def test_service_commands_domain_aggregate_inside_repository_transaction(self):
        account = CuentaBancoHoras("employee-1")
        repository = InMemoryTransactionalHoursRepository(account)
        service = HoursService(repository)

        movement = service.create(" employee-1 ", "ACUMULACION", "2.50", "Turno")

        self.assertEqual(repository.employee_id, "employee-1")
        self.assertEqual(account.saldo_actual.valor, Decimal("2.50"))
        self.assertEqual(movement.tipo, TipoMovimiento.ACUMULACION)

    def test_service_preserves_domain_errors_from_transaction(self):
        account = CuentaBancoHoras("employee-1")
        repository = InMemoryTransactionalHoursRepository(account)
        service = HoursService(repository)

        with self.assertRaisesRegex(SaldoInsuficienteError, "supera las horas"):
            service.create("employee-1", "DEVOLUCION", "1.00", "Exceso")

        self.assertEqual(account.saldo_actual.valor, Decimal("0.00"))
        self.assertEqual(account.movimientos, ())


if __name__ == "__main__":
    unittest.main()
