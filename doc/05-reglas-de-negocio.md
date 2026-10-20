# 5. Reglas de negocio

Las reglas de negocio son políticas de la empresa que el sistema debe respetar.

## Período laboral

El mes vigente va del **15 de un mes al 14 del mes siguiente** (período del 15 al 15).

## Estados diarios

| Estado | ¿Baja el índice de asistencia? | ¿Cómo afecta el saldo de horas? |
|---|---|---|
| Presente | No | Suma las horas trabajadas (las extra quedan a favor) |
| Falta sin aviso | Sí | Descuenta las horas del día |
| Falta con aviso | Sí | Neutro: no se penaliza y no se compensa con horas extra |
| Médico (falta justificada) | No | Neutro |
| Franco | No | Neutro |
| Vacaciones | No | Neutro |

## Índice de eficiencia

- Asistencia = días presente ÷ días que debía trabajar. Franco, vacaciones y médico no cuentan como días que debía trabajar. La falta con aviso sí cuenta.
- Puntualidad = días que llegó a horario ÷ días presente.
- Cursos = cursos obligatorios completados ÷ cursos obligatorios asignados.
- Eficiencia = 40 % asistencia + 30 % puntualidad + 30 % cursos (pesos a confirmar).
