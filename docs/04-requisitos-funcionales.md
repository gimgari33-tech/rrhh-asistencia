# SRS: requisitos del sistema

**Proyecto:** RR. HH. Asistencia y banco de horas · **Versión:** 1.0 · **Actualizado:** 17 de noviembre de 2026

Este documento especifica el comportamiento esperado del sistema y cómo aceptarlo. El estado indica lo que existe hoy en el MVP; un requisito planificado describe una función acordada para una etapa posterior, no una función disponible actualmente.

## Alcance actual del MVP

El MVP permite iniciar sesión con Firebase Authentication, autorizar cuentas activas mediante su rol en Firestore, crear y consultar empleados por nombre, registrar estados diarios de asistencia, y acumular o devolver horas con historial y saldo. Las devoluciones que exceden el saldo se rechazan.

La edición y baja de empleados, los horarios, el cálculo automático del período laboral, los cursos, el índice de eficiencia y los saludos de cumpleaños todavía no están implementados. La demo pública usa datos ficticios del navegador; para trabajar con Firestore hace falta desplegar el backend.

### Estados

- **Implementado:** está disponible en el MVP actual.
- **Parcial:** hay una parte disponible y queda una diferencia descrita en el estado.
- **Planificado:** todavía no está disponible.

## Requisitos funcionales y criterios de aceptación

Cada criterio sigue el formato **Dado / Cuando / Entonces** y puede verificarse manualmente o mediante una prueba automatizada.

| ID | Requisito | Estado | Criterio de aceptación |
|---|---|---|---|
| FR-01 | Permitir que RR. HH. cree, modifique y dé de baja la ficha de un empleado con nombre, fecha de nacimiento, correo, teléfono y local. La baja conserva el historial. | Parcial: el MVP crea y consulta empleados por nombre. | **Dado** un usuario de RR. HH. autorizado y datos válidos, **cuando** crea, modifica o da de baja una ficha, **entonces** el cambio queda guardado y puede consultarse; una ficha dada de baja no aparece en nuevas cargas, pero sus registros históricos se conservan. |
| FR-02 | Definir las horas que cada empleado debe trabajar por día según su jornada o turno. | Planificado. | **Dado** una jornada válida, **cuando** RR. HH. la asigna a un empleado, **entonces** el sistema guarda las horas y vigencia; rechaza una duración nula o negativa. |
| FR-03 | Registrar por empleado y fecha uno de los estados: Presente, Falta sin aviso, Falta con aviso, Médico, Franco o Vacaciones. | Implementado para carga diaria. | **Dado** un empleado existente, **cuando** un usuario autorizado registra una fecha y uno de los seis estados, **entonces** la asistencia queda guardada y aparece en el historial; un estado distinto se rechaza. |
| FR-04 | Registrar la hora de entrada y salida cuando el estado requiere asistencia trabajada. | Planificado. | **Dado** el estado Presente, **cuando** el usuario informa horas válidas de entrada y salida, **entonces** el sistema guarda ambas; rechaza una salida anterior a la entrada. Los estados sin jornada no requieren esas horas. |
| FR-05 | Guardar el motivo en las faltas con aviso y las ausencias por enfermedad. | Planificado. | **Dado** el estado Falta con aviso o Médico, **cuando** se confirma el registro con un motivo, **entonces** el motivo queda asociado; si falta, el sistema solicita completarlo. |
| FR-06 | Cargar asistencia para un día o una semana completa. | Parcial: el MVP carga un día por vez. | **Dado** uno o varios empleados y fechas dentro de una semana, **cuando** el usuario confirma la carga, **entonces** se guardan los registros válidos de cada fecha y el sistema identifica los errores sin duplicar registros. |
| FR-07 | Permitir corregir una asistencia conservando quién la cambió, cuándo y el valor anterior. | Planificado. | **Dado** un registro existente, **cuando** un usuario con permiso lo corrige, **entonces** se actualiza el dato y queda una auditoría con usuario, fecha, valor anterior y valor nuevo. |
| FR-08 | Calcular el saldo de horas del período laboral, desde el día 15 inclusive hasta el día 15 del mes siguiente exclusivo, según las reglas del negocio. | Planificado: el saldo actual es un banco acumulado y la carga es manual. | **Dado** las asistencias, jornadas y movimientos de un período, **cuando** se consulta el saldo, **entonces** el cálculo incluye las fechas desde el 15 hasta el 14 inclusive y aplica las reglas publicadas en `docs/05-reglas-de-negocio.md`. |
| FR-09 | Mostrar por empleado las horas extra a favor y las horas faltantes del período. | Parcial: el MVP muestra saldo acumulado, sin cómputo automático de faltantes. | **Dado** un período calculado, **cuando** se consulta un empleado, **entonces** se muestran por separado el crédito de horas y el déficit; un valor cero se presenta como cero, no como dato ausente. |
| FR-10 | Registrar cursos obligatorios con nombre y vigencia. | Planificado. | **Dado** un curso con nombre y fecha de vigencia válidos, **cuando** RR. HH. lo registra, **entonces** aparece en el catálogo y puede asignarse a empleados. |
| FR-11 | Registrar qué empleado completó cada curso y en qué fecha. | Planificado. | **Dado** un empleado y un curso asignado, **cuando** se registra su finalización con fecha válida, **entonces** el historial muestra curso, empleado y fecha. |
| FR-12 | Listar empleados que todavía tienen cursos obligatorios pendientes. | Planificado. | **Dado** cursos asignados y sus finalizaciones, **cuando** RR. HH. consulta pendientes, **entonces** cada empleado sin completar un curso vigente aparece una sola vez por curso pendiente. |
| FR-13 | Calcular el índice de eficiencia por empleado y período con asistencia, puntualidad y cursos. | Planificado. | **Dado** datos completos del período, **cuando** se consulta el índice, **entonces** se muestra `40 % asistencia + 30 % puntualidad + 30 % cursos`; si un componente no tiene datos, se informa “Sin datos” y no se presenta como cero. |
| FR-14 | Filtrar información por período, local y empleado. | Parcial: el MVP permite filtrar movimientos por empleado. | **Dado** registros de más de un período, local o empleado, **cuando** se seleccionan filtros, **entonces** solo se muestran los registros coincidentes; al quitar los filtros se vuelve a mostrar el conjunto completo autorizado. |
| FR-15 | Enviar un saludo por correo el día del cumpleaños del empleado. | Planificado. | **Dado** un empleado con fecha de nacimiento y correo válidos, **cuando** llega su cumpleaños, **entonces** el sistema envía un único saludo ese día y deja constancia del resultado del envío. |
| FR-16 | Autenticar usuarios y aplicar permisos según el rol de RR. HH., encargado o gerencia. | Parcial: Firebase Authentication y autorización Firestore están; el MVP usa `SUPERADMIN` e `INVITADO`. | **Dado** un usuario autenticado, **cuando** consulta o modifica datos, **entonces** el servidor obtiene su rol de `usuarios_autorizados/{uid}` y permite solo las operaciones asignadas a ese rol; una cuenta inactiva o sin permiso recibe rechazo. |
| FR-17 | Permitir el uso desde navegadores de celulares y computadoras. | Implementado en la interfaz adaptable; pendiente revisión visual documentada. | **Dado** un navegador con ancho de pantalla desde 360 px, **cuando** se abre cada pantalla del MVP, **entonces** se puede navegar, leer y completar formularios sin desplazamiento horizontal de la página. |
| FR-18 | Mostrar el saldo de horas disponibles por empleado. | Implementado para el saldo acumulado del MVP. | **Dado** un empleado con saldo y movimientos, **cuando** un usuario autorizado abre el banco de horas, **entonces** se muestra el saldo vigente y coincide con el saldo resultante del último movimiento. |
| FR-19 | Registrar acumulaciones y devoluciones con fecha, detalle y saldo resultante. | Parcial: se guardan movimientos, fecha y saldo; el detalle puede quedar vacío. | **Dado** un usuario con permiso, empleado y cantidad válida, **cuando** registra una acumulación o devolución, **entonces** se guarda el tipo, la fecha, el detalle y el saldo resultante junto con el movimiento. |
| FR-20 | Rechazar una devolución que supere el saldo disponible. | Implementado con transacción de Firestore. | **Dado** un saldo menor que la devolución solicitada, **cuando** se registra la devolución, **entonces** el sistema la rechaza, mantiene el saldo anterior y no crea un movimiento de devolución. |

## Requisitos no funcionales

Los objetivos medibles siguientes son criterios para validar el sistema; el despliegue público y la prueba de carga todavía están pendientes.

| ID | Categoría | Requisito medible | Verificación |
|---|---|---|---|
| NFR-01 | Rendimiento | Con 200 empleados, hasta 10.000 movimientos y 10 usuarios concurrentes, al menos el 95 % de las consultas de lectura del MVP debe responder en menos de 2 segundos desde la región configurada. | Prueba de carga contra un entorno desplegado en `southamerica-east1`; medir percentil 95. |
| NFR-02 | Seguridad | Toda ruta de datos debe validar un token de Firebase Authentication y un documento de autorización activo; toda escritura requiere rol permitido. Ningún secreto de servicio ni contraseña se guarda en Git. | Pruebas automáticas de acceso sin token, cuenta inactiva y rol sin permiso; revisión de secretos antes del merge. |
| NFR-03 | Escalabilidad e integridad | El MVP debe soportar 10 sesiones concurrentes y 200 empleados sin perder actualizaciones de saldo; las operaciones concurrentes del banco de horas deben conservar la consistencia mediante transacciones. | Prueba concurrente de movimientos y validación de saldo e historial en Firestore; configuración de Cloud Run con escalado desde cero y un máximo de 5 instancias. |

## Casos de uso

### UC-01: Consultar el banco de horas

- **Actores:** RR. HH., encargado o gerencia con cuenta habilitada. En el MVP los roles disponibles son `SUPERADMIN` (escritura y lectura) e `INVITADO` (solo lectura).
- **Precondición:** el usuario inició sesión con Firebase Authentication y tiene `activo: true` en `usuarios_autorizados/{uid}`.
- **Flujo principal:**
  1. El usuario inicia sesión desde la interfaz.
  2. La interfaz envía el token de Firebase al backend.
  3. El backend valida el token y la autorización en Firestore.
  4. El usuario abre la lista de empleados.
  5. El sistema muestra cada empleado y su saldo vigente.
- **Alternativas:** token ausente o inválido: se solicita iniciar sesión (401); usuario no habilitado: se deniega el acceso (403); Firestore no disponible: se informa un error temporal sin mostrar datos falsos (503).
- **Postcondición:** no se modifican datos; queda disponible la información correspondiente al último estado persistido.

### UC-02: Registrar una acumulación o devolución

- **Actor principal:** RR. HH. con permiso de escritura (`SUPERADMIN` en el MVP).
- **Precondiciones:** sesión válida, autorización activa, empleado existente y cantidad de horas positiva con hasta dos decimales.
- **Flujo principal:**
  1. RR. HH. selecciona un empleado y el tipo de movimiento.
  2. Ingresa las horas y el detalle.
  3. El backend valida token, rol, empleado, tipo y cantidad.
  4. Firestore actualiza el saldo y registra el movimiento en una transacción.
  5. La interfaz muestra el saldo resultante.
- **Alternativas:** datos inválidos: no se modifica el saldo y se explica el error; devolución mayor que el saldo: se rechaza sin crear movimiento; sesión sin permiso: se devuelve 401 o 403; Firestore no disponible: se devuelve 503 sin confirmar la operación.
- **Postcondición:** si la operación se acepta, el saldo y su movimiento quedan persistidos juntos; si se rechaza, ambos permanecen sin cambios.

## Decisiones de negocio pendientes

- Confirmar si los horarios son fijos o rotativos y cómo calcular horas debidas (afecta FR-02 y FR-08).
- Confirmar si `15 al 15` significa día 15 inclusive hasta el día 14 inclusive del mes siguiente; este SRS lo interpreta así.
- Definir la matriz final de permisos para RR. HH., encargado y gerencia (FR-16); los roles técnicos actuales son `SUPERADMIN` e `INVITADO`.
- Definir si el detalle del movimiento será obligatorio (FR-19).
- Confirmar los límites de rendimiento y concurrencia con el docente o la organización antes de la prueba de carga.
