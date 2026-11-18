# Informe técnico y guía para la defensa

**Proyecto:** RR. HH. Asistencia y banco de horas · **Fecha:** 17 de noviembre de 2026

## Resumen

El proyecto busca reemplazar el registro manual de asistencia y banco de horas por una aplicación web. El MVP permite consultar empleados, registrar estados de asistencia y guardar acumulaciones o devoluciones de horas con su saldo resultante. La interfaz se comunica con una API Flask; el backend valida usuarios con Firebase Authentication y persiste los datos en Cloud Firestore.

El código y las pruebas principales están preparados. La publicación del backend en Cloud Run y la validación completa contra el servicio desplegado siguen pendientes de permisos y configuración de facturación del proyecto de Google Cloud.

## Problema y solución

La carga en libros y planillas obliga a hacer cálculos manuales, dificulta revisar saldos y dispersa la información. El MVP concentra empleados, asistencias y movimientos del banco de horas. Cada acumulación y devolución conserva un historial; una devolución que dejaría el saldo negativo se rechaza.

La carga de horas continúa siendo manual. El sistema no calcula todavía horas debidas a partir de horarios ni el saldo mensual del período laboral; esos comportamientos están identificados como planificados en el [SRS](04-requisitos-funcionales.md).

## Arquitectura y tecnologías

- **Interfaz:** HTML, CSS y JavaScript adaptable a celulares y computadoras.
- **Autenticación:** Firebase Authentication con correo y contraseña.
- **API:** Flask presenta rutas HTTP y verifica el token de identidad recibido del navegador.
- **Autorización:** el servidor consulta `usuarios_autorizados/{uid}` en Firestore. Solo un documento activo con rol permitido habilita la operación; las escrituras del MVP requieren `SUPERADMIN`.
- **Persistencia:** Cloud Firestore. Los movimientos del banco de horas y la actualización del saldo se guardan mediante una transacción para que ambas operaciones queden consistentes.
- **Despliegue previsto:** contenedor Docker y Gunicorn en Cloud Run, con identidad de servicio de permisos mínimos.

La separación del backend sigue dominio, aplicación, infraestructura y presentación. El dominio contiene reglas de negocio; aplicación coordina los casos de uso; infraestructura implementa Firebase/Firestore; presentación traduce las solicitudes HTTP y aplica la autenticación.

## Seguridad y datos

La demo pública almacena solo datos ficticios en el navegador. Para operar con datos reales se requiere iniciar sesión y tener una autorización activa en Firestore. El navegador no decide el rol: lo determina el backend a partir del UID verificado. Las credenciales privadas no deben subirse a GitHub.

Antes de cargar información real, deben revisarse las cuentas autorizadas, las reglas de Firestore, la identidad de ejecución y los permisos. Los datos de empleados son personales; el acceso debe limitarse a las personas que los necesitan.

## Verificación y mediciones

En la rama de pruebas del proyecto, la suite reportó **43 pruebas aprobadas y 100 % de cobertura de sentencias de `backend.rrhh`**. La cobertura incluye reglas, casos de uso, control de permisos, respuestas HTTP y adaptadores Firebase/Firestore simulados. Las pruebas usan dobles de prueba: no se conectan a la base real y por sí solas no demuestran que Cloud Run o Firestore estén funcionando en producción.

La validación pendiente del entorno desplegado debe medir:

1. **Exactitud funcional:** el saldo final coincide con el saldo inicial más acumulaciones menos devoluciones; una devolución excesiva no cambia saldo ni historial.
2. **Integridad concurrente:** dos movimientos simultáneos no pierden actualizaciones.
3. **Rendimiento:** medir el percentil 95 de consultas en una prueba con la cantidad de empleados, movimientos y usuarios definidos en el SRS. El objetivo propuesto es menos de 2 segundos; todavía no fue medido.
4. **Resultado para el usuario:** durante un piloto, comparar el tiempo para cerrar el banco de horas y la cantidad de diferencias detectadas frente al método manual. Primero hay que registrar una línea de base; no se afirma que la app ya haya reducido tiempos o errores en una organización real.

## Plan de ejecución por etapas

| Etapa | Trabajo | Criterio para avanzar | Riesgo principal |
|---|---|---|---|
| 1. Definición y MVP | Canvas, SRS, reglas, empleados, asistencia y movimientos del banco de horas. | Criterios funcionales acordados y pruebas del flujo principal aprobadas. | Reglas de horarios o roles aún no confirmadas. |
| 2. Revisión y calidad | Trabajar en ramas y PRs, revisión antes de integrar, cobertura y Ruff. | PR aprobado, suite verde, cobertura mínima de 85 % y Ruff sin hallazgos. | Integrar cambios sin revisión o con pruebas incompletas. |
| 3. Publicación piloto | Resolver permisos de Google Cloud, habilitar Cloud Run, asignar identidad, desplegar y probar autenticación/Firestore con datos ficticios. | Flujo de inicio de sesión y escrituras validados en el servicio desplegado; mediciones de rendimiento registradas. | Facturación/IAM pendientes y exposición de datos reales antes de validar. |
| 4. Automatización asistida | Prototipos OCR y NLP con aprobación humana antes de guardar. | Comparar propuestas con etiquetas revisadas por personas y medir errores. | Letra ilegible o clasificación incorrecta. |
| 5. Evaluación predictiva | Explorar ML solo cuando exista un conjunto histórico suficiente y autorizado. | Métrica acordada, evaluación separada de entrenamiento y revisión de sesgos. | Pocos datos o uso del resultado como sanción automática. |

## Riesgos y mitigaciones

- **Despliegue bloqueado:** la última revisión del proyecto de Google Cloud indicó que faltaba vincular facturación y que la cuenta usada no podía habilitar Cloud Run. El titular/administrador debe resolverlo; no se considera desplegado hasta completar la prueba real.
- **Acceso indebido a datos:** exigir tokens válidos y autorización activa, limitar escrituras por rol y revisar reglas antes del piloto.
- **Saldo incorrecto por escrituras simultáneas:** mantener la transacción de Firestore y verificar el caso concurrente en un entorno desplegado.
- **Errores de OCR o NLP:** estos componentes no deben escribir directamente; una persona revisa y confirma cada propuesta.
- **Roles de negocio no alineados:** confirmar la matriz RR. HH./encargado/gerencia antes de crear permisos distintos a `SUPERADMIN` e `INVITADO`.
- **Automatización predictiva injusta:** ML no está implementado; no debe usarse para sanciones y requiere evaluación con datos suficientes y revisión humana.

## OCR, NLP y ML

Estas técnicas son posibles etapas futuras; no forman parte del MVP actual.

- **OCR:** tomar una foto o escaneo del libro, corregir inclinación y recortar la tabla, extraer texto/horarios y mostrar una propuesta para que RR. HH. la confirme. La métrica sería exactitud por campo (empleado, fecha, entrada, salida) sobre ejemplos etiquetados y revisados; los casos de baja confianza deben volver a carga manual.
- **NLP:** analizar avisos de ausencia recibidos por correo para proponer empleado, fecha y motivo. El sistema debe mostrar el correo de origen y pedir confirmación antes de registrar una falta.
- **ML:** explorar patrones históricos para estimar ausencias futuras solo después de acumular datos suficientes y revisar calidad, sesgos y permisos. La predicción sería informativa, no una decisión automática sobre personas.

## Posible ingreso económico

La experiencia puede servir para postular a puestos iniciales de desarrollo web, QA o automatización mostrando el proyecto, la arquitectura, las pruebas y la defensa técnica. Otra hipótesis comercial sería ofrecer a pequeños negocios una implementación y capacitación inicial, con soporte mensual opcional.

Es una propuesta para validar, no un ingreso asegurado. Antes de cobrar por el producto habría que entrevistar posibles usuarios, comprobar que necesitan resolver este problema, definir soporte y costos de operación, y agregar aislamiento entre empresas, copias de seguridad, gestión de incidentes y condiciones de privacidad. El MVP actual está configurado para un único proyecto/organización y no debe venderse como un servicio multiempresa listo.

## Respuestas para la defensa

### ¿Qué problema resuelve el banco de horas y cómo lo verificaste?

“Resuelve el seguimiento manual de las horas acumuladas y ya compensadas por empleado. Cada movimiento guarda tipo, cantidad, detalle, fecha y saldo resultante. Verifiqué el caso con pruebas automatizadas: acumular 8,5 horas y devolver 2 deja 6,5; una devolución mayor al saldo se rechaza sin modificarlo. Las pruebas del backend usan datos simulados; todavía falta probar el mismo flujo contra Cloud Run y Firestore desplegados.”

### ¿Por qué no usaste PRs?

“Al principio trabajé directamente en `main`, por eso no había una revisión previa a la integración. La devolución me marcó esa falta. Ahora separé las tareas en ramas y abrí PRs para el SRS, la cobertura y Ruff. Los dejé abiertos para revisión y no los voy a fusionar hasta que un docente o compañero los apruebe.”

