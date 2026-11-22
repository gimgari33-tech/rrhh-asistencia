"""Unit tests for monthly labor period value objects, settlement, and bank hours cut."""

import unittest
from datetime import date
from decimal import Decimal

from backend.rrhh.domain.errors import ValidationError
from backend.rrhh.domain.period import (
    PeriodoLaboral,
    RegistroJornada,
    calcular_corte_periodo,
    generar_movimiento_corte,
)


class PeriodoLaboralTests(unittest.TestCase):
    def test_creates_valid_period(self):
        periodo = PeriodoLaboral(date(2026, 10, 15), date(2026, 11, 14))
        self.assertEqual(periodo.fecha_inicio, date(2026, 10, 15))
        self.assertEqual(periodo.fecha_fin, date(2026, 11, 14))
        self.assertEqual(periodo.dias_totales(), 31)
        self.assertEqual(periodo.etiqueta(), "2026-10-15 al 2026-11-14")
        self.assertIn("fecha_inicio", periodo.to_dict())

    def test_validates_year_boundary_period(self):
        periodo = PeriodoLaboral(date(2026, 12, 15), date(2027, 1, 14))
        self.assertEqual(periodo.dias_totales(), 31)
        self.assertTrue(periodo.contiene("2026-12-31"))
        self.assertTrue(periodo.contiene("2027-01-01"))

    def test_rejects_invalid_period_dates(self):
        with self.assertRaises(ValidationError):
            PeriodoLaboral(date(2026, 10, 10), date(2026, 11, 14))  # Start not 15
        with self.assertRaises(ValidationError):
            PeriodoLaboral(date(2026, 10, 15), date(2026, 11, 15))  # End not 14
        with self.assertRaises(ValidationError):
            PeriodoLaboral(date(2026, 10, 15), date(2026, 10, 14))  # End before start
        with self.assertRaises(ValidationError):
            PeriodoLaboral(
                date(2026, 10, 15), date(2026, 12, 14)
            )  # Not consecutive month
        with self.assertRaises(ValidationError):
            PeriodoLaboral("2026-10-15", "2026-11-14")  # Non-date objects

    def test_desde_fecha_computes_correct_period(self):
        # Day >= 15
        p1 = PeriodoLaboral.desde_fecha(date(2026, 10, 15))
        self.assertEqual(p1.fecha_inicio, date(2026, 10, 15))
        self.assertEqual(p1.fecha_fin, date(2026, 11, 14))

        p2 = PeriodoLaboral.desde_fecha("2026-10-25")
        self.assertEqual(p2.fecha_inicio, date(2026, 10, 15))
        self.assertEqual(p2.fecha_fin, date(2026, 11, 14))

        # Day < 15
        p3 = PeriodoLaboral.desde_fecha(date(2026, 11, 14))
        self.assertEqual(p3.fecha_inicio, date(2026, 10, 15))
        self.assertEqual(p3.fecha_fin, date(2026, 11, 14))

        p4 = PeriodoLaboral.desde_fecha("2026-11-01")
        self.assertEqual(p4.fecha_inicio, date(2026, 10, 15))
        self.assertEqual(p4.fecha_fin, date(2026, 11, 14))

        # Year boundary
        p5 = PeriodoLaboral.desde_fecha("2027-01-05")
        self.assertEqual(p5.fecha_inicio, date(2026, 12, 15))
        self.assertEqual(p5.fecha_fin, date(2027, 1, 14))

    def test_desde_fecha_rejects_invalid_inputs(self):
        with self.assertRaises(ValidationError):
            PeriodoLaboral.desde_fecha("not-a-date")
        with self.assertRaises(ValidationError):
            PeriodoLaboral.desde_fecha(12345)

    def test_contiene_checks_boundaries(self):
        periodo = PeriodoLaboral(date(2026, 10, 15), date(2026, 11, 14))
        self.assertTrue(periodo.contiene(date(2026, 10, 15)))
        self.assertTrue(periodo.contiene(date(2026, 11, 14)))
        self.assertTrue(periodo.contiene("2026-10-31"))
        self.assertFalse(periodo.contiene(date(2026, 10, 14)))
        self.assertFalse(periodo.contiene("2026-11-15"))
        self.assertFalse(periodo.contiene("invalid"))


class RegistroJornadaTests(unittest.TestCase):
    def test_creates_valid_record(self):
        reg = RegistroJornada(date(2026, 10, 20), "Presente", Decimal("8.50"))
        self.assertEqual(reg.fecha, date(2026, 10, 20))
        self.assertEqual(reg.estado, "Presente")
        self.assertEqual(reg.horas_trabajadas, Decimal("8.50"))

    def test_rejects_invalid_record(self):
        with self.assertRaises(ValidationError):
            RegistroJornada("2026-10-20", "Presente")
        with self.assertRaises(ValidationError):
            RegistroJornada(date(2026, 10, 20), "EstadoInexistente")
        with self.assertRaises(ValidationError):
            RegistroJornada(date(2026, 10, 20), "Presente", "not-a-number")
        with self.assertRaises(ValidationError):
            RegistroJornada(date(2026, 10, 20), "Presente", Decimal("-1.00"))


class CortePeriodoServiceTests(unittest.TestCase):
    def setUp(self):
        self.periodo = PeriodoLaboral(date(2026, 10, 15), date(2026, 11, 14))

    def test_validates_inputs(self):
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("", "Ana", self.periodo, 8, [])
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("emp-1", "Ana", self.periodo, "invalid", [])
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("emp-1", "Ana", self.periodo, -5, [])
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("emp-1", "Ana", self.periodo, 25, [])

    def test_rejects_records_outside_period_or_duplicates(self):
        reg_outside = RegistroJornada(date(2026, 10, 10), "Presente")
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, [reg_outside])

        reg1 = RegistroJornada(date(2026, 10, 16), "Presente")
        reg2 = RegistroJornada(date(2026, 10, 16), "Franco")
        with self.assertRaises(ValidationError):
            calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, [reg1, reg2])

    def test_presente_normal_hours_produces_zero_balance(self):
        registros = [
            RegistroJornada(date(2026, 10, 15), "Presente", Decimal("8.00")),
            RegistroJornada(date(2026, 10, 16), "Presente", None),  # Default to jornada
        ]
        res = calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, registros)
        self.assertEqual(res.horas_esperadas, Decimal("16.00"))
        self.assertEqual(res.horas_trabajadas, Decimal("16.00"))
        self.assertEqual(res.horas_extra, Decimal("0.00"))
        self.assertEqual(res.horas_faltantes, Decimal("0.00"))
        self.assertEqual(res.saldo_neto, Decimal("0.00"))
        self.assertEqual(res.dias_presente, 2)
        self.assertIsNone(generar_movimiento_corte(res, Decimal("5.00")))

    def test_presente_with_overtime_produces_positive_net_balance(self):
        registros = [
            RegistroJornada(date(2026, 10, 15), "Presente", Decimal("10.50")),  # +2.50
            RegistroJornada(date(2026, 10, 16), "Presente", Decimal("9.00")),  # +1.00
        ]
        res = calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, registros)
        self.assertEqual(res.horas_extra, Decimal("3.50"))
        self.assertEqual(res.horas_faltantes, Decimal("0.00"))
        self.assertEqual(res.saldo_neto, Decimal("3.50"))

        movimiento = generar_movimiento_corte(res, Decimal("10.00"))
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.tipo, "ACUMULACION")
        self.assertEqual(movimiento.horas, Decimal("3.50"))
        self.assertEqual(movimiento.saldo_resultante, Decimal("13.50"))

    def test_falta_sin_aviso_and_undertime_produces_missing_hours(self):
        registros = [
            RegistroJornada(date(2026, 10, 15), "Presente", Decimal("6.00")),  # -2.00
            RegistroJornada(date(2026, 10, 16), "Falta sin aviso"),  # -8.00
        ]
        res = calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, registros)
        self.assertEqual(res.horas_extra, Decimal("0.00"))
        self.assertEqual(res.horas_faltantes, Decimal("10.00"))
        self.assertEqual(res.saldo_neto, Decimal("-10.00"))
        self.assertEqual(res.dias_falta_sin_aviso, 1)

        movimiento = generar_movimiento_corte(res, Decimal("15.00"))
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.tipo, "DEVOLUCION")
        self.assertEqual(movimiento.horas, Decimal("10.00"))
        self.assertEqual(movimiento.saldo_resultante, Decimal("5.00"))

    def test_devolucion_exceeding_bank_balance_raises_validation_error(self):
        registros = [
            RegistroJornada(date(2026, 10, 16), "Falta sin aviso"),  # -8.00
        ]
        res = calcular_corte_periodo("emp-1", "Ana", self.periodo, 8, registros)
        self.assertEqual(res.saldo_neto, Decimal("-8.00"))

        with self.assertRaises(ValidationError):
            generar_movimiento_corte(res, Decimal("5.00"))  # Only 5 hs available
        with self.assertRaises(ValidationError):
            generar_movimiento_corte(res, "invalid-saldo")

    def test_neutral_statuses_do_not_impact_bank_hours(self):
        registros = [
            RegistroJornada(date(2026, 10, 15), "Franco"),
            RegistroJornada(date(2026, 10, 16), "Vacaciones"),
            RegistroJornada(date(2026, 10, 17), "Médico"),
            RegistroJornada(date(2026, 10, 18), "Falta con aviso"),
        ]
        res = calcular_corte_periodo("emp-1", "Ana", self.periodo, 5, registros)
        self.assertEqual(res.horas_extra, Decimal("0.00"))
        self.assertEqual(res.horas_faltantes, Decimal("0.00"))
        self.assertEqual(res.saldo_neto, Decimal("0.00"))
        self.assertEqual(res.dias_neutros, 4)
        self.assertEqual(res.dias_presente, 0)
        self.assertEqual(res.dias_falta_sin_aviso, 0)
        self.assertIsNone(generar_movimiento_corte(res, Decimal("0.00")))

    def test_combined_scenario_with_5_hour_shift(self):
        registros = [
            RegistroJornada(
                date(2026, 10, 15), "Presente", Decimal("7.00")
            ),  # +2 hs extra
            RegistroJornada(date(2026, 10, 16), "Franco"),  # Neutro
            RegistroJornada(date(2026, 10, 17), "Presente", Decimal("5.00")),  # Normal
            RegistroJornada(date(2026, 10, 18), "Falta sin aviso"),  # -5 hs faltantes
            RegistroJornada(date(2026, 10, 19), "Falta con aviso"),  # Neutro
            RegistroJornada(date(2026, 10, 20), "Médico"),  # Neutro
        ]
        res = calcular_corte_periodo("emp-2", "Cintia", self.periodo, "5.00", registros)
        self.assertEqual(res.jornada_habitual, Decimal("5.00"))
        self.assertEqual(res.horas_extra, Decimal("2.00"))
        self.assertEqual(res.horas_faltantes, Decimal("5.00"))
        self.assertEqual(res.saldo_neto, Decimal("-3.00"))
        self.assertEqual(res.dias_presente, 2)
        self.assertEqual(res.dias_falta_sin_aviso, 1)
        self.assertEqual(res.dias_neutros, 3)

        d = res.to_dict()
        self.assertEqual(d["empleado_id"], "emp-2")
        self.assertEqual(d["saldo_neto"], -3.0)


if __name__ == "__main__":
    unittest.main()
