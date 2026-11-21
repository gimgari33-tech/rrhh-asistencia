"""Small domain objects shared by use cases and adapters."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .errors import ValidationError
from .rules import completion_date, course_description, course_name


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


@dataclass(frozen=True)
class Course:
    id: str
    nombre: str
    descripcion: str = ""
    creado_en: str = ""

    def __post_init__(self):
        if not str(self.id or "").strip():
            raise ValidationError("El curso debe tener un identificador.")
        object.__setattr__(self, "nombre", course_name(self.nombre))
        object.__setattr__(self, "descripcion", course_description(self.descripcion))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "creado_en": self.creado_en,
        }


@dataclass(frozen=True)
class CourseAssignment:
    id: str
    empleado_id: str
    empleado_nombre: str
    curso_id: str
    curso_nombre: str
    completado: bool = False
    fecha_completacion: date | None = None

    def __post_init__(self):
        if not str(self.empleado_id or "").strip() or not str(self.curso_id or "").strip():
            raise ValidationError("La asignación debe identificar al empleado y al curso.")
        if not isinstance(self.completado, bool):
            raise ValidationError("El estado de completitud del curso debe ser booleano.")
        if self.completado and self.fecha_completacion is None:
            raise ValidationError("La fecha es obligatoria para un curso completado.")
        if not self.completado and self.fecha_completacion is not None:
            raise ValidationError("Un curso pendiente no puede tener fecha de finalización.")
        if self.fecha_completacion is not None:
            object.__setattr__(
                self,
                "fecha_completacion",
                completion_date(self.fecha_completacion),
            )

    def marcar_completado(self, completed_on):
        if self.completado:
            return self
        return CourseAssignment(
            id=self.id,
            empleado_id=self.empleado_id,
            empleado_nombre=self.empleado_nombre,
            curso_id=self.curso_id,
            curso_nombre=self.curso_nombre,
            completado=True,
            fecha_completacion=completion_date(completed_on),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "empleado_id": self.empleado_id,
            "empleado_nombre": self.empleado_nombre,
            "curso_id": self.curso_id,
            "curso_nombre": self.curso_nombre,
            "completado": self.completado,
            "fecha_completacion": (
                self.fecha_completacion.isoformat()
                if self.fecha_completacion is not None
                else None
            ),
        }
