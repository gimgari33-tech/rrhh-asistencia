# RRHH Asistencia

Aplicación web (usable desde el celular) para que RRHH controle la asistencia, las horas trabajadas, los cursos obligatorios y la eficiencia de los empleados, con un período laboral del **15 al 15** de cada mes.

> Proyecto académico — Prácticas profesionales / Proyecto integrador.

## Problema

Hoy la asistencia se anota en un libro manual en el local y las ausencias llegan por mail. Calcular horas extra y faltantes, controlar los cursos obligatorios y saber quién cumple es lento y propenso a errores.

## Solución (MVP)

- Base de datos de empleados.
- Carga diaria o semanal de 6 estados: presente, falta sin aviso, falta con aviso, médico, franco y vacaciones, con hora de entrada y salida.
- Saldo de horas del período 15 al 15.
- Control de cursos obligatorios (quién los hizo y quién no).
- Dashboard con el índice de eficiencia por empleado.
- Saludo de cumpleaños por mail.

## Índice de eficiencia

Eficiencia = asistencia + puntualidad + cursos obligatorios (pesos propuestos: 40 % / 30 % / 30 %). Es una ayuda para decidir, no una sanción automática.

## Documentación

| Punto | Documento |
|---|---|
| 1. Canvas | [docs/01-canvas.md](docs/01-canvas.md) |
| 2. Stakeholders y propuesta de valor | [docs/02-stakeholders.md](docs/02-stakeholders.md) |
| 3. Alcance del MVP | [docs/03-alcance-mvp.md](docs/03-alcance-mvp.md) |
| 4. Requisitos funcionales | [docs/04-requisitos-funcionales.md](docs/04-requisitos-funcionales.md) |
| 5. Reglas de negocio | [docs/05-reglas-de-negocio.md](docs/05-reglas-de-negocio.md) |

## Tecnología prevista

Python + Streamlit (interfaz web), SQLite (base de datos), arquitectura limpia en 4 capas. Detalle en etapas siguientes.

## Estado

- [x] Canvas
- [x] Stakeholders y propuesta de valor
- [x] Alcance del MVP
- [x] Requisitos funcionales (borrador)
- [ ] Requisitos no funcionales
- [ ] Criterios de aceptación y casos de uso
- [ ] Arquitectura limpia
- [ ] Roadmap técnico
- [ ] Scrum: user stories, backlog y sprints

## Datos y privacidad

Este repositorio **no contiene datos reales de empleados** ni credenciales. Los datos personales están regulados por la Ley 25.326 (Argentina).
