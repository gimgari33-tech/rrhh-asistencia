"""Small domain objects shared by use cases and adapters."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from .errors import SaldoInsuficienteError, ValidationError
from .rules import movement_detail

CENT = Decimal("0.01")
MAX_HOURS = Decimal("99999999.99")


class TipoMovimiento(str, Enum):
    """Supported operations on an employee time bank."""

    ACUMULACION = "ACUMULACION"
    DEVOLUCION = "DEVOLUCION"

    @classmethod
    def parse(cls, value):
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value or "").upper())
        except ValueError:
            raise ValidationError(
                "El tipo debe ser ACUMULACION o DEVOLUCION."
            ) from None


@dataclass(frozen=True)
class Horas:
    """Non-negative hours with at most two decimal places."""

    valor: Decimal

    def __post_init__(self):
        try:
            value = Decimal(str(self.valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("La cantidad de horas es inválida.") from None

        if not value.is_finite() or value < 0 or value > MAX_HOURS:
            raise ValidationError("Las horas deben ser finitas y no negativas.")
        try:
            has_valid_precision = value == value.quantize(CENT)
        except InvalidOperation:
            has_valid_precision = False
        if not has_valid_precision:
            raise ValidationError("Las horas admiten hasta dos decimales.")
        object.__setattr__(self, "valor", value)

    @classmethod
    def from_value(cls, value):
        return value if isinstance(value, cls) else cls(value)

    @classmethod
    def positiva(cls, value):
        hours = cls.from_value(value)
        if hours.valor <= 0:
            raise ValidationError("Las horas del movimiento deben ser positivas.")
        return hours


@dataclass(frozen=True)
class MovimientoHora:
    """Domain result produced by a time-bank operation."""

    tipo: TipoMovimiento
    horas: Horas
    saldo_resultante: Horas
    detalle: str


class CuentaBancoHoras:
    """Aggregate root that protects a time bank's non-negative balance."""

    def __init__(self, empleado_id, saldo_actual=Decimal("0.00")):
        normalized_id = str(empleado_id or "").strip()
        if not normalized_id:
            raise ValidationError("La cuenta debe identificar a un empleado.")
        self._empleado_id = normalized_id
        self._saldo_actual = Horas.from_value(saldo_actual)
        self._movimientos = []

    @property
    def empleado_id(self):
        return self._empleado_id

    @property
    def saldo_actual(self):
        return self._saldo_actual

    @property
    def movimientos(self):
        return tuple(self._movimientos)

    def acreditar_horas(self, horas, motivo="", politica=None):
        amount = Horas.positiva(horas)
        if politica is None:
            from .policies import CompensacionSimple

            politica = CompensacionSimple()
        credited_hours = Horas.positiva(politica.calcular_credito(amount.valor))
        detail = movement_detail(motivo)
        balance = Horas(self._saldo_actual.valor + credited_hours.valor)
        return self._registrar(
            TipoMovimiento.ACUMULACION, credited_hours, balance, detail
        )

    def debitar_horas(self, horas, motivo=""):
        amount = Horas.positiva(horas)
        detail = movement_detail(motivo)
        if amount.valor > self._saldo_actual.valor:
            raise SaldoInsuficienteError(
                "La devolución supera las horas disponibles. "
                f"Saldo: {self._saldo_actual.valor} h; devolución: {amount.valor} h."
            )
        balance = Horas(self._saldo_actual.valor - amount.valor)
        return self._registrar(TipoMovimiento.DEVOLUCION, amount, balance, detail)

    def _registrar(self, kind, amount, balance, detail):
        movement = MovimientoHora(
            tipo=kind,
            horas=amount,
            saldo_resultante=balance,
            detalle=detail,
        )
        self._saldo_actual = balance
        self._movimientos.append(movement)
        return movement


@dataclass(frozen=True)
class AuthorizedUser:
    uid: str
    email: str
    nombre: str
    rol: str

    def to_dict(self):
        return {
            "uid": self.uid,
            "email": self.email,
            "nombre": self.nombre,
            "rol": self.rol,
        }


@dataclass(frozen=True)
class Employee:
    id: str
    nombre: str
    creado_en: str = ""
    saldo_horas: Decimal = Decimal("0.00")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "creado_en": self.creado_en,
            "saldo_horas": float(self.saldo_horas),
        }


@dataclass(frozen=True)
class HourMovement:
    id: str
    empleado_id: str
    empleado_nombre: str
    tipo: str
    horas: Decimal
    saldo_resultante: Decimal
    detalle: str
    fecha: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "empleado_id": self.empleado_id,
            "empleado_nombre": self.empleado_nombre,
            "tipo": self.tipo,
            "horas": float(self.horas),
            "saldo_resultante": float(self.saldo_resultante),
            "detalle": self.detalle,
            "fecha": self.fecha,
        }


@dataclass(frozen=True)
class AttendanceRecord:
    id: str
    empleado_id: str
    empleado_nombre: str
    estado: str
    fecha: str
    creado_en: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "empleado_id": self.empleado_id,
            "empleado_nombre": self.empleado_nombre,
            "estado": self.estado,
            "fecha": self.fecha,
            "creado_en": self.creado_en,
        }
