# RRHH Asistencia

Aplicación web para registrar asistencia y consultar el banco de horas acumuladas por empleado. La interfaz funciona en celular y escritorio.

## Funciones disponibles

- Registrar asistencia por empleado, fecha y estado.
- Crear empleados con banco de horas inicial en cero.
- Consultar el saldo acumulado de cada empleado y el total disponible.
- Agregar horas al banco con un detalle opcional.
- Registrar devoluciones, descontando las horas del saldo.
- Consultar el historial con el saldo resultante de cada movimiento.
- Probar la aplicación en modo demo con nombres ficticios y datos guardados solo en el navegador.

Las horas se guardan con hasta dos decimales. El sistema rechaza devoluciones superiores al saldo disponible. La carga de horas es manual; no se calcula automáticamente a partir de asistencia hasta definir los horarios y reglas de jornada.

## Probar

Abrí `index.html` o visitá la página publicada en GitHub Pages. Elegí **Probar demo pública**. La demo no usa ni modifica datos reales; los cambios quedan en el almacenamiento local del navegador.

## Backend y base de datos en la nube

La interfaz usa Firebase Authentication para iniciar sesión y envía el token de identidad a una API Flask. El backend verifica ese token con Firebase Admin SDK y lee y escribe en Cloud Firestore del proyecto `empleados-cbf0b`. La base estándar `(default)` está en `southamerica-east1` (São Paulo). No se aceptan roles enviados por el navegador.

### Acceso por usuario

Habilitá Email/Password en Firebase Authentication y creá las cuentas que correspondan. Después, desde Firebase Console, creá `usuarios_autorizados/{uid}` con estos campos:

- `activo`: booleano `true`.
- `rol`: `SUPERADMIN` para administrar o `INVITADO` para consultar.
- `nombre`: nombre para mostrar (opcional).

El UID debe coincidir con el ID del documento. Los usuarios invitados solo pueden leer; las escrituras requieren `SUPERADMIN`. Las reglas de `firestore.rules` también aplican esos permisos a accesos directos desde el cliente. Para publicar cambios en las reglas, usá Firebase CLI:

```sh
firebase deploy --only firestore:rules --project empleados-cbf0b
```

### Ejecutar localmente

Se necesita Python 3.12 o posterior y una identidad de Google con permiso `roles/datastore.user` en el proyecto. Para desarrollo local, configurá Application Default Credentials con Google Cloud CLI o indicá la ruta de una clave de servicio guardada fuera del repositorio; nunca subas esa clave a GitHub.

```sh
python -m pip install -r requirements.txt
gcloud auth application-default login
python app.py
```

Abrí `http://127.0.0.1:5000`. La API y la interfaz se sirven desde Flask en el mismo origen. GitHub Pages sigue funcionando como demo local con datos ficticios; sus rutas estáticas no ejecutan el backend.

### Publicar el backend en Cloud Run

El `Dockerfile` permite servir la interfaz y la API desde el mismo servicio. Configurá la cuenta de servicio de Cloud Run con el rol `roles/datastore.user` y desplegá:

```sh
gcloud run deploy rrhh-asistencia \
  --source . \
  --region southamerica-east1 \
  --project empleados-cbf0b \
  --allow-unauthenticated
```

Cloud Run acepta las solicitudes al servicio; la API protege los datos verificando Firebase Authentication y `usuarios_autorizados`. Al terminar el despliegue, agregá el dominio `run.app` del servicio a los dominios autorizados de Firebase Authentication.

No cargues datos reales de empleados hasta crear las cuentas autorizadas y revisar quién tendrá acceso. Nunca agregues claves de cuenta de servicio ni datos personales reales al repositorio.

### Colecciones de Firestore

- `empleados/{empleadoId}`: nombre y fecha de creación.
- `bancos_horas/{empleadoId}`: saldo actual de horas.
- `movimientos_banco_horas/{movimientoId}`: empleado, tipo, horas, detalle, fecha y saldo resultante.
- `asistencia/{registroId}`: empleado, fecha, estado y fecha de carga.

Cada acumulación o devolución actualiza el saldo y crea el movimiento en una transacción de Firestore. La demo pública usa empleados ficticios y `localStorage`, sin conexión a Firestore.

## Documentación funcional

- [Canvas](docs/01-canvas.md)
- [Stakeholders](docs/02-stakeholders.md)
- [Alcance del MVP](docs/03-alcance-mvp.md)
- [Requisitos funcionales](docs/04-requisitos-funcionales.md)
- [Reglas de negocio](docs/05-reglas-de-negocio.md)

## Privacidad

El repositorio no debe contener datos personales de empleados, planillas médicas, exportaciones de Firestore ni claves privadas o de cuenta de servicio. La configuración web de Firebase es pública; el backend verifica la identidad y el rol antes de acceder a Firestore.
