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

## Conectar Firebase para uso interno

La app puede usar Firebase Authentication y Firestore. Para habilitarlo:

1. Copiá `firebase-config.example.js` como `firebase-config.js`.
2. Reemplazá los valores de ejemplo por la configuración web de tu proyecto Firebase.
3. Habilitá Firebase Authentication con correo y contraseña.
4. Configurá reglas de Firestore que permitan acceso solo a usuarios autorizados.

`firebase-config.js` está excluido de Git para evitar publicar la configuración local. Nunca agregues claves de cuenta de servicio ni datos reales de empleados al repositorio.

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

El repositorio no debe contener datos personales de empleados, planillas médicas, exportaciones de Firestore ni configuraciones locales. Los archivos de datos y `firebase-config.js` están ignorados por Git.
