# 4. Requisitos funcionales (FR) — borrador

Qué debe hacer el sistema.

| Grupo | ID | El sistema debe permitir... |
|---|---|---|
| Empleados | FR-01 | Dar de alta, modificar y dar de baja empleados (nombre, fecha de nacimiento, mail, teléfono, local) |
| | FR-02 | Definir las horas que cada empleado debe trabajar por día |
| Asistencia | FR-03 | Registrar por día uno de 6 estados: presente, falta sin aviso, falta con aviso, médico, franco, vacaciones |
| | FR-04 | Registrar la hora de entrada y de salida |
| | FR-05 | Registrar el motivo en faltas con aviso y médico |
| | FR-06 | Cargar un solo día o una semana completa |
| | FR-07 | Corregir un registro dejando constancia de quién lo cambió y cuándo |
| Horas | FR-08 | Calcular el saldo de horas del período vigente del 15 al 15, aplicando las reglas de negocio |
| | FR-09 | Mostrar horas extra a favor y horas faltantes por empleado |
| Cursos | FR-10 | Registrar los cursos obligatorios |
| | FR-11 | Marcar quién completó cada curso y en qué fecha |
| | FR-12 | Listar los empleados con cursos pendientes |
| Dashboard | FR-13 | Calcular el índice de eficiencia por empleado y período |
| | FR-14 | Filtrar por período, local y empleado |
| Cumpleaños | FR-15 | Enviar un mail de saludo el día del cumpleaños |
| Acceso | FR-16 | Ingresar con usuario y contraseña, con roles (RRHH, encargado, gerencia) |
| | FR-17 | Usarse desde el navegador del celular |

## Pendiente

- Definir si los empleados tienen horario fijo o turnos rotativos (afecta FR-02 y FR-08).
- Criterios de aceptación y casos de uso (punto 2.3).
