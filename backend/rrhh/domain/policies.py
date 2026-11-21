"""Compensation strategies for converting worked hours into bank credits."""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Protocol

from .rules import positive_hours

CENT = Decimal("0.01")


class PoliticaCompensacion(Protocol):
    """Contract for a policy that converts base hours into credited hours."""

    def calcular_credito(self, horas_base: Decimal) -> Decimal: ...


def _apply_factor(horas_base, factor):
    base = positive_hours(horas_base)
    credited = (base * factor).quantize(CENT, rounding=ROUND_HALF_EVEN)
    return positive_hours(credited)


class CompensacionSimple:
    """One hour worked produces one hour in the bank."""

    def calcular_credito(self, horas_base: Decimal) -> Decimal:
        return positive_hours(horas_base)


class CompensacionDiaHabilExtra:
    """Example 1.5x policy for an extra-hour weekday shift."""

    FACTOR = Decimal("1.5")

    def calcular_credito(self, horas_base: Decimal) -> Decimal:
        return _apply_factor(horas_base, self.FACTOR)


class CompensacionFeriadoFinDeSemana:
    """Example 2x policy for weekend or holiday hours."""

    FACTOR = Decimal("2.0")

    def calcular_credito(self, horas_base: Decimal) -> Decimal:
        return _apply_factor(horas_base, self.FACTOR)
