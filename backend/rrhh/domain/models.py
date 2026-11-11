"""Small domain objects shared by use cases and adapters."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AuthorizedUser:
    uid: str
    email: str
    nombre: str
    rol: str

    def to_dict(self):
        return {"uid": self.uid, "email": self.email, "nombre": self.nombre, "rol": self.rol}


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
