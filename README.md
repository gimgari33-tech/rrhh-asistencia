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

## Base de datos en la nube

La app usa Firebase Authentication y Cloud Firestore del proyecto `empleados-cbf0b`. La base Firestore estándar está en `southamerica-east1` (São Paulo). El archivo `firebase-config.js` contiene la configuración pública de la app web para que el sitio pueda conectarse; no contiene una clave de cuenta de servicio. Las reglas de `firestore.rules` requieren una cuenta autenticada y autorizada individualmente.

Para publicar o actualizar las reglas, instalá Firebase CLI e iniciá sesión con una cuenta autorizada:

```sh
firebase deploy --only firestore:rules --project empleados-cbf0b
```

Para habilitar a una persona, creá su cuenta en Firebase Authentication y luego, desde Firebase Console, creá `usuarios_autorizados/{uid}` con el campo booleano `activo: true`, usando el UID de esa cuenta como ID del documento. Solo los usuarios con ese documento activo pueden leer o cambiar los datos. No cargues datos reales de empleados hasta definir y revisar quiénes tendrán acceso. Nunca agregues claves de cuenta de servicio ni datos personales reales al repositorio.

### Colecciones de Firestore

- `empleados/{empleadoId}`: nombre y fecha de creación.
- `bancos_horas/{empleadoId}`: saldo actual de horas.
- `movimientos_banco_horas/{movimientoId}`: empleado, tipo, horas, detalle, fecha y saldo resultante.
- `asistencia/{registroId}`: empleado, fecha, estado y fecha de carga.

Cada acumulación o devolución actualiza el saldo y crea el movimiento dentro de una transacción. La demo pública usa empleados ficticios y `localStorage`, sin conexión a Firestore.

## Documentación funcional

- [Canvas](docs/01-canvas.md)
- [Stakeholders](docs/02-stakeholders.md)
- [Alcance del MVP](docs/03-alcance-mvp.md)
- [Requisitos funcionales](docs/04-requisitos-funcionales.md)
- [Reglas de negocio](docs/05-reglas-de-negocio.md)

## Privacidad

El repositorio no debe contener datos personales de empleados, planillas médicas, exportaciones de Firestore ni claves privadas o de cuenta de servicio. La configuración web de Firebase es pública; las reglas de Firestore limitan el acceso a usuarios autorizados individualmente.
