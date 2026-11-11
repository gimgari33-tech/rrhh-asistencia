# RR. HH. Asistencia

Aplicación web para registrar asistencia y administrar el banco de horas del personal. La interfaz se adapta a celulares y computadoras; el modo conectado usa Flask, Firebase Authentication y Cloud Firestore.

## Estado del proyecto

- **Demo pública:** [gimgari33-tech.github.io/rrhh-asistencia](https://gimgari33-tech.github.io/rrhh-asistencia/). Funciona con datos ficticios guardados en el navegador.
- **Backend:** API Flask preparada para ejecutarse localmente o en Cloud Run.
- **Base de datos:** Cloud Firestore, proyecto `empleados-cbf0b`, región `southamerica-east1` (São Paulo).
- **Arquitectura:** backend organizado en dominio, aplicación, infraestructura y presentación. Ver [docs/arquitectura.md](docs/arquitectura.md).

GitHub Pages publica archivos estáticos y por eso ofrece únicamente la demo. Para usar datos en Firestore se necesita ejecutar el backend y completar la configuración de identidad y permisos descrita abajo.

## Funciones del MVP

- Registrar asistencia por empleado, fecha y estado.
- Crear empleados con banco de horas inicial en cero.
- Consultar saldos e historial de movimientos.
- Acumular horas y registrar devoluciones con detalle.
- Rechazar devoluciones que superen el saldo disponible.
- Probar la demo sin modificar datos reales.

La carga de horas es manual. El cálculo automático por jornada o período queda sujeto a las reglas de negocio pendientes de definición.

## Estructura

```text
backend/rrhh/
  domain/          reglas y modelos del negocio
  application/     casos de uso e interfaces (puertos)
  infrastructure/  Firebase Admin y adaptadores Firestore
  presentation/    rutas HTTP, autenticación y frontend
static/
  css/             estilos
  js/              interfaz y configuración web de Firebase
docs/              alcance, requisitos y arquitectura
app.py             fábrica Flask y punto de entrada WSGI
```

## Ejecutar el backend localmente

Se necesita Python 3.12 o posterior, Google Cloud CLI y una identidad con `roles/datastore.user` en el proyecto.

1. Crear y activar un entorno virtual:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Instalar dependencias e iniciar sesión para Application Default Credentials:

   ```sh
   python -m pip install -r requirements.txt
   gcloud auth application-default login
   ```

3. Iniciar Flask:

   ```sh
   python app.py
   ```

4. Abrir `http://127.0.0.1:5000` y elegir **Probar demo pública** o iniciar sesión con una cuenta habilitada.

La API y la interfaz conectada se sirven desde el mismo origen. No guardes claves de cuentas de servicio dentro del repositorio. Si necesitas usar una clave local, guardala fuera de la carpeta del proyecto y configurá `GOOGLE_APPLICATION_CREDENTIALS` en tu entorno.

## Configurar Firebase Authentication y roles

1. Habilitar el proveedor **Email/Password** en Firebase Authentication y crear las cuentas necesarias.
2. Para cada cuenta autorizada, crear `usuarios_autorizados/{uid}` en Firestore. El ID del documento debe ser el UID de Firebase Authentication y debe incluir:

   | Campo | Tipo | Valor |
   |---|---|---|
   | `activo` | booleano | `true` |
   | `rol` | texto | `SUPERADMIN` o `INVITADO` |
   | `nombre` | texto | opcional |

3. Asignar a la identidad de ejecución del backend el rol `roles/datastore.user`.
4. Después de publicar Cloud Run, agregar el dominio `run.app` del servicio a los dominios autorizados de Firebase Authentication.

El servidor valida el token de Firebase Authentication y consulta el rol autorizado en Firestore. No confía en roles enviados por el navegador. `INVITADO` puede leer; las operaciones de escritura requieren `SUPERADMIN`. Las reglas de [firestore.rules](firestore.rules) protegen también el acceso directo desde clientes Firebase.

Para publicar cambios en las reglas:

```sh
firebase deploy --only firestore:rules --project empleados-cbf0b
```

## Desplegar en Cloud Run

El repositorio incluye un `Dockerfile` para construir la imagen con Gunicorn. Configurá primero la cuenta de servicio de Cloud Run con `roles/datastore.user` y luego ejecutá:

```sh
gcloud run deploy rrhh-asistencia \
  --source . \
  --region southamerica-east1 \
  --project empleados-cbf0b \
  --allow-unauthenticated
```

Cloud Run recibe solicitudes públicas, pero los endpoints de datos requieren un token Firebase válido y una cuenta habilitada. No cargues datos reales hasta revisar los usuarios autorizados.

## API

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/health` | público, estado del servicio |
| `GET` | `/api/auth/me` | usuario habilitado |
| `GET` | `/api/employees` | usuario habilitado |
| `POST` | `/api/employees` | `SUPERADMIN` |
| `GET` | `/api/movements` | usuario habilitado |
| `POST` | `/api/movements` | `SUPERADMIN` |
| `GET` | `/api/attendance` | usuario habilitado |
| `POST` | `/api/attendance` | `SUPERADMIN` |

## Colecciones de Firestore

- `usuarios_autorizados/{uid}`: habilitación y rol de acceso.
- `empleados/{empleadoId}`: nombre y fecha de creación.
- `bancos_horas/{empleadoId}`: saldo actual.
- `movimientos_banco_horas/{movimientoId}`: tipo, horas, detalle y saldo resultante.
- `asistencia/{registroId}`: empleado, estado, fecha y fecha de carga.

Cada acumulación o devolución actualiza el saldo y crea el movimiento dentro de una transacción de Firestore.

## Documentación funcional

- [Canvas](docs/01-canvas.md)
- [Stakeholders](docs/02-stakeholders.md)
- [Alcance del MVP](docs/03-alcance-mvp.md)
- [Requisitos funcionales](docs/04-requisitos-funcionales.md)
- [Reglas de negocio](docs/05-reglas-de-negocio.md)
- [Arquitectura](docs/arquitectura.md)
- [Contribuir](CONTRIBUTING.md)

## Privacidad y seguridad

No agregues datos personales de empleados, planillas médicas, exportaciones de Firestore, contraseñas ni claves privadas al repositorio. La configuración web de Firebase es pública; los permisos efectivos dependen de la autenticación, la autorización del backend y las reglas de Firestore.
