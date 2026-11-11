# Guía para contribuir

## Antes de cambiar el código

- Leé [README.md](README.md) y [docs/arquitectura.md](docs/arquitectura.md).
- Confirmá si el cambio afecta la demo estática, la API, las reglas de Firestore o más de una parte.
- Usá datos ficticios. Nunca incluyas datos reales de empleados o credenciales.

## Dónde ubicar los cambios

- Reglas y modelos independientes de servicios: `backend/rrhh/domain/`.
- Casos de uso y contratos: `backend/rrhh/application/`.
- Integraciones Firebase/Firestore: `backend/rrhh/infrastructure/`.
- HTTP, permisos por endpoint y respuestas JSON: `backend/rrhh/presentation/`.
- Interfaz y estilos: `static/` e `index.html`.
- Alcance, requisitos y decisiones: `docs/`.

Las reglas del dominio no deben importar Flask ni Firebase. Las operaciones que cambian el banco de horas deben conservar la transacción que actualiza el saldo y registra el movimiento.

## Commits y pull requests

Usá mensajes breves que describan el cambio, por ejemplo:

- `feat: add attendance filters`
- `fix: reject invalid hour balances`
- `refactor: separate Firestore repositories`
- `docs: clarify Cloud Run setup`

En un pull request, incluí el problema que resuelve, las áreas afectadas y cualquier cambio de esquema o permisos de Firestore. No adjuntes capturas con datos personales ni claves.
