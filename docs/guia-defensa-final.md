# Guía de Defensa Oral · Proyecto Integrador (PP - 3.ᵉʳ Año)
**Estudiante:** Gabriela  
**Carrera:** Tecnicatura Superior en Ciencia de Datos e Inteligencia Artificial (Res. 2730/22)  
**Proyecto:** Sistema de RRHH, Banco de Horas y Digitalización de Asistencia por Imágenes  

---

## 🎯 1. Estado de las 3 Prioridades de la Devolución

| Criterio | Exigencia de Cátedra | Estado Actual en el Proyecto |
|---|---|---|
| **N1 · SRS y Criterios** | Formato Dado/Cuando/Entonces para cada FR, 3 requisitos no funcionales medibles y 2 casos de uso con actores. | **100 % CUMPLIDO.** Documentado en [PR #10](https://github.com/gimgari33-tech/rrhh-asistencia/pull/10) (`docs/04-requisitos-funcionales.md`): criterios para FR-01 a FR-20, NFR-01 a NFR-03 y UC-01/UC-02. |
| **N2 · Flujo Git y PRs** | No commitear directo a `main`. Trabajar en ramas (`feat/...`), abrir PRs, etiquetar al docente (`@datamaq-automation`) y no mergear sin revisión. | **100 % CUMPLIDO.** Ramas independientes y PRs abiertos (#10, #13, #17, #18, #19, #20, #21, #25) con commits atómicos y trazables. |
| **N3 · Tests y Cobertura** | Subir de 74 % a 85 % de cobertura y tener al menos 10 tests (antes había 3). | **100 % CUMPLIDO (NIVEL MÁXIMO).** Se pasó de 3 a **72 pruebas unitarias e integración**, alcanzando un **99 % de cobertura de código** (`coverage report`). |

---

## 🗣️ 2. Respuestas a las Preguntas de la Defensa Oral

### Pregunta 1: ¿Qué problema resuelve el banco de horas y cómo lo verificaste?
> **Respuesta sugerida para la defensa:**  
> “El banco de horas resuelve el descontrol y la falta de trazabilidad en el seguimiento manual de horas acumuladas y compensadas en la empresa, donde coexisten jornadas de 8 y 5 horas y francos semanales rotativos. Cada movimiento registra fecha, tipo (acumulación o devolución), cantidad, detalle y el saldo resultante en una transacción atómica que nunca permite saldos negativos (invariante de dominio).  
> Lo verifiqué mediante una suite de pruebas automatizadas: por ejemplo, acumular 8.5 horas y devolver 2 deja 6.5; si se intenta una devolución que supere el saldo disponible, el sistema la rechaza inmediatamente sin alterar el historial. Además, implementé el corte de período mensual (del 15 al 14) que calcula automáticamente horas extra a favor o faltantes según los registros diarios reales.”

### Pregunta 2: ¿Por qué no usaste PRs al principio y cómo lo corregiste?
> **Respuesta sugerida para la defensa:**  
> “Al inicio del desarrollo, al ser un proyecto individual de prototipado rápido, commiteaba directo a `main` buscando avanzar con la funcionalidad.  
> A partir de la devolución pedagógica de la cátedra, comprendí que en la industria el Pull Request es la herramienta fundamental de calidad para que otra persona detecte errores antes de producción. Corregí el flujo por completo: configuré un pipeline de Integración Continua con GitHub Actions (`ci.yml`), separé cada funcionalidad en una rama dedicada (`feat/` o `test/`), y abrí Pull Requests con descripción detallada y mención al docente, sin mergear directo a `main`.”

---

## 💼 3. Puntos Clave de la Rúbrica (N1, N2 y N3)

### N1 · Definición y Monetización (Generación de Ingreso)
* **Salida Laboral / Relación de Dependencia:** Demuestra capacidades completas de desarrollo backend con Clean Architecture, testing unitario con alta cobertura, CI/CD con GitHub Actions y visión artificial con OpenCV.
* **Comercialización / Servicios Independientes:** Se puede ofrecer como un servicio SaaS modular para pequeños comercios, gastronómicos o talleres con personal rotativo, cobrando una tarifa mensual por empleado activo para automatizar el cálculo de horas y la digitalización de planillas en papel.

### N2 · Progreso de Ejecución y Visión Artificial (PDI)
* **Técnica implementada:** Procesamiento Digital de Imágenes (OpenCV).
  1. *Corrección de perspectiva:* Homografía cuadrilátera de 4 puntos (`warpPerspective`) para enderezar fotos de planillas de asistencia tomadas torcidas con el celular.
  2. *Limpieza de sombras:* Binarización adaptativa e inversión mediante método de Otsu.
  3. *Detección de grilla:* Morfología matemática (kernels rectangulares) para aislar filas y celdas.
  4. *Toma de decisión:* Conteo de densidad de píxeles oscuros (tinta de lapicera) respecto a un umbral para clasificar **Presente** vs. **Ausente (Falta sin aviso)** y alimentar automáticamente el Banco de Horas.

### N3 · Calidad de Código, Linters y Mediciones
* **Linters:** Se utilizó Ruff. Los 8 errores iniciales fueron corregidos; `ruff check .` y `ruff format --check .` presentan **0 errores**.
* **Medición que valida que el sistema funciona:**
  1. **Cobertura de tests:** 99 % sobre el backend (`backend.rrhh`).
  2. **Tasa de acierto del modelo de visión:** *pendiente de medición.* La foto del 05/11 no permite medirla: la hoja no muestra sus 4 bordes y la grilla no se separa en 6 columnas, así que las densidades de esa foto eran valores tipeados y no un resultado del pipeline. Se medirá con 2 o 3 fotos nuevas y su CSV de verdad (`scripts/procesar_planilla_demo.py --verdad`), con exactitud, precisión y recall de Ausente.
  3. **Integridad del corte de ciclo:** Comprobación matemática en `calcular_corte_periodo` de que la suma de horas extra menos faltantes coincide exactamente con el saldo neto resultante.

---

## 📅 4. Planificación por Etapas del Proyecto

1. **Etapa 1 (Definición y Canvas):** Modelo de negocio Canvas, stakeholders, requisitos funcionales preliminares y MVP en Flask.
2. **Etapa 2 (Clean Architecture y Dominio Rico):** Desacoplamiento en capas (`domain`, `application`, `infrastructure`, `presentation`), Agregado `CuentaBancoHoras`, patrón Strategy y ciclo mensual del 15 al 14.
3. **Etapa 3 (Visión Artificial y Planilla Masiva):** Rediseño hacia planilla diaria por excepción y pipeline de visión (PDI) para digitalizar la hoja física en papel.
4. **Etapa 4 (Calidad, CI y Documentación de Defensa):** Pipeline de GitHub Actions, suite de 72 tests con 99 % de cobertura, informe técnico y guía de examen final.
