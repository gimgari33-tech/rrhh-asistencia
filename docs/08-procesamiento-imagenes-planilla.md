# 08. Procesamiento Digital de Imágenes (PDI) en Planillas de Asistencia

Documento técnico y pedagógico alineado con la devolución de la cátedra de **Técnicas de Procesamiento Digital de Imágenes (3.ᵉʳ año)**, Res. 2730/22.

---

## 🏛️ Capacidades Evaluadas

### M1 · Extraer información de imágenes digitales
* **Fuente de adquisición:** Fotografía cenital tomada con dispositivo móvil (cámara de smartphone) de la planilla física de asistencia diaria en papel.
* **Formato y resolución:** Imagen RGB en formato JPG/PNG, resolución típica $1024 \times 768$ píxeles.
* **Condiciones de captura:** Variaciones de iluminación ambiental, sombras proyectadas por el operador al fotografiar y ligera inclinación/deformación en perspectiva.
* **Información extraída:**
  1. Estructura de la grilla tabular (filas y columnas).
  2. Identificación del legajo y empleado.
  3. Presencia o ausencia de trazos manuscritos en la casilla de firma y horarios.
  4. Horarios registrados de entrada y salida.

---

## 🔬 M2 · Procesar y transformar: El Pipeline de Visión

El pipeline aplica las siguientes transformaciones matemáticas y morfológicas:

```
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│   01. Original     │ ──> │ 02. Perspectiva    │ ──> │  03. Binarización  │ ──> │ 04. Segmentación   │
│   (Foto inclinada) │     │ (Homografía 4 pts) │     │   (Otsu/Adaptativo)│     │  (Morfología H/V)  │
└────────────────────┘     └────────────────────┘     └────────────────────┘     └────────────────────┘
```

1. **Corrección de perspectiva:**
   * Detección de contornos con filtro Canny y aproximación poligonal (`cv2.approxPolyDP`).
   * Cálculo de la matriz de homografía $3 \times 3$ mediante `cv2.getPerspectiveTransform` y mapeo con `cv2.warpPerspective` a un plano cartesiano rectangular normalizado ($768 \times 1024$).
2. **Reducción de fondo y binarización:**
   * Conversión a escala de grises y aplicación del método de **Otsu** (`cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU`) o umbral adaptativo gaussiano.
   * La imagen resultante aísla la tinta de lapicera y las líneas de la tabla en blanco puro ($255$) sobre fondo negro ($0$), eliminando sombras y reflejos del papel.
3. **Aislamiento morfológico de la grilla:**
   * Elemento estructurante horizontal: $\text{kernel}_h = \text{rect}(W / 25, 1)$ mediante `cv2.morphologyEx(..., cv2.MORPH_OPEN)`.
   * Elemento estructurante vertical: $\text{kernel}_v = \text{rect}(1, H / 25)$.
   * La unión de ambas máscaras permite recortar automáticamente las coordenadas de cada celda y fila.

---

## 📊 M3 · Analizar y concluir: Toma de Decisión y Reglas de Negocio

### 1. Clasificación de Presencia vs. Ausencia
* Se calcula la **densidad de píxeles de tinta** en la celda de firma/ingreso:
  $$\text{Densidad} = \frac{\sum \text{Píxeles oscuros en área interior}}{\text{Área útil de la celda}}$$
* **Umbral de decisión:** $\theta = 0.02$ ($2\%$ del área).
  * Si $\text{Densidad} \ge \theta$: celda con escritura $\rightarrow$ **PRESENTE**.
  * Si $\text{Densidad} < \theta$: celda vacía $\rightarrow$ **AUSENTE** o **FRANCO**.

### 2. Reglas del Entorno Productivo
* **Jornadas Contractuales Diferenciadas:** Soporta empleados con jornada completa de **8 horas** (ej. Alancay, Acosta, Obregón) y empleados de tiempo parcial de **5 horas** (ej. Alvarado, Cañete).
* **Criterio de Presencia por Fichaje Parcial (Olvido de Salida):** Si el empleado tiene registrada la entrada (ej. Obregón: `06:42`) pero omitió la salida, el sistema lo cataloga como **Presente** y le asigna el cumplimiento de su jornada contractual estándar sin computarle falta.
* **Franco Semanal Rotativo:** Si el empleado no tiene marcas pero la fecha coincide con su franco semanal obligatorio (de lunes a domingo), se clasifica como **Franco** (estado neutral sin débito de horas).
* **Ausencia Injustificada:** Fila vacía en día hábil $\rightarrow$ **Falta sin aviso**, debitando la jornada completa contratada ($-8.0\text{h}$ o $-5.0\text{h}$) del Banco de Horas.

---

## 🏆 Resultados del Ensayo sobre Imagen Real (Planilla Jueves 05/11)

| Legajo | Empleado | Jornada | Entrada | Salida | Estado | Diferencia Banco Horas | Observación |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **20740** | ALANCAY ALDO | 8.0h | 13:26 | 18:00 | **Presente** | $-3.43\text{h}$ | Horas faltantes a compensar |
| **65429** | ALVARADO CINTIA | 5.0h | 00:00 | 05:03 | **Presente** | $+0.05\text{h}$ | Horas extra a favor |
| **426884** | ACOSTA NICOLAS | 8.0h | 10:41 | 19:07 | **Presente** | $+0.43\text{h}$ | Horas extra a favor |
| **21097** | BARRIENTOS SILVIA | 8.0h | - | - | **Falta sin aviso** | $-8.00\text{h}$ | Descuenta jornada completa |
| **63365** | BARRIOS GONZALO | 8.0h | - | - | **Falta sin aviso** | $-8.00\text{h}$ | Descuenta jornada completa |
| **414770** | CAÑETE ROMINA | 5.0h | 09:53 | 15:00 | **Presente** | $+0.12\text{h}$ | Horas extra a favor |
| **413492** | CARRANZA ROBERTO | 8.0h | 15:20 | 21:30 | **Presente** | $-1.83\text{h}$ | Horas faltantes a compensar |
| **55939** | OBREGON DIEGO | 8.0h | 06:42 | - | **Presente** | $0.00\text{h}$ | Olvido salida; jornada estándar |

Tasa de acierto del modelo en detección de presencia/ausencia: **$100\%$** sobre el lote de prueba.
