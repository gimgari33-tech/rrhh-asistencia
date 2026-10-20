# 1. Canvas: problema, solución y métricas clave

## Problema

- El control de asistencia se hace en un libro manual en el local y es lento.
- Es difícil calcular horas extra y faltantes dentro del período del 15 al 15.
- No hay una vista clara de quién cumple y quién no.
- Es difícil saber quién hizo los cursos obligatorios.
- Los datos de los empleados están dispersos (Excel, papel, mails).

## Solución

Una app web, usable desde el celular, con base de datos de empleados que permite:

- Registrar el estado diario de cada empleado.
- Calcular automáticamente el saldo de horas del período.
- Controlar los cursos obligatorios.
- Mostrar un dashboard de eficiencia.
- Enviar un saludo automático de cumpleaños.

## Métricas clave

| Métrica | Cálculo | Dato necesario |
|---|---|---|
| Asistencia | días presente ÷ días que debía trabajar | estado de cada día |
| Puntualidad | días que llegó a horario ÷ días presente | hora de entrada |
| Cursos | cursos obligatorios hechos ÷ cursos asignados | tabla de cursos |
| Saldo de horas | horas trabajadas − horas debidas (período 15 al 15) | entradas, salidas y horas debidas |
| Eficiencia | combinación ponderada de asistencia, puntualidad y cursos (40/30/30) | las tres anteriores |
