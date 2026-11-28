"""Tests for computer vision attendance processing pipeline and business rules."""

import os
import unittest
from datetime import date
from decimal import Decimal

import cv2
import numpy as np

from backend.rrhh.domain.period import PeriodoLaboral, calcular_corte_periodo
from backend.rrhh.vision.contracts import (
    JORNADA_5_HORAS,
    JORNADA_8_HORAS,
    ConfiguracionEmpleado,
    FilaPlanillaExtraida,
)
from backend.rrhh.vision.image_processing import (
    binarizar_imagen,
    calcular_densidad_tinta,
    clasificar_celda_marcada,
    corregir_perspectiva,
    densidad_celda_limpia,
    detectar_esquinas_hoja,
    detectar_posiciones_lineas,
    extraer_lineas_grilla,
    ordenar_puntos,
    recortar_celdas,
)
from backend.rrhh.vision.service import (
    ServicioAsistenciaVision,
    calcular_horas_trabajadas,
)


class VisionContractsAndProcessingTests(unittest.TestCase):
    def test_configuracion_empleado_validates_inputs(self):
        emp = ConfiguracionEmpleado(
            legajo="20740",
            nombre="Alancay Aldo",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,  # Domingo
        )
        self.assertEqual(emp.legajo, "20740")
        self.assertEqual(emp.jornada_horas, Decimal("8.0"))

        with self.assertRaises(ValueError):
            ConfiguracionEmpleado(legajo="", nombre="Juan")
        with self.assertRaises(ValueError):
            ConfiguracionEmpleado(legajo="1", nombre="")
        with self.assertRaises(ValueError):
            ConfiguracionEmpleado(legajo="1", nombre="Juan", jornada_horas=Decimal(-1))
        with self.assertRaises(ValueError):
            ConfiguracionEmpleado(legajo="1", nombre="Juan", dia_franco_semanal=7)

    def test_ordenar_puntos_clockwise(self):
        pts = np.array([[200, 200], [0, 0], [200, 0], [0, 200]], dtype="float32")
        ordenados = ordenar_puntos(pts)
        np.testing.assert_array_equal(ordenados[0], [0, 0])  # top-left
        np.testing.assert_array_equal(ordenados[1], [200, 0])  # top-right
        np.testing.assert_array_equal(ordenados[2], [200, 200])  # bottom-right
        np.testing.assert_array_equal(ordenados[3], [0, 200])  # bottom-left

    def test_corregir_perspectiva_and_binarizar_with_synthetic_image(self):
        # Crear imagen sintética con fondo blanco y un rectángulo torcido
        img = np.ones((400, 300, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (20, 20), (280, 380), (0, 0, 0), 2)

        warped = corregir_perspectiva(img, ancho_destino=200, alto_destino=300)
        self.assertEqual(warped.shape[:2], (300, 200))

        binarizada_otsu = binarizar_imagen(warped, metodo="otsu")
        self.assertEqual(binarizada_otsu.shape, (300, 200))

        binarizada_adap = binarizar_imagen(warped, metodo="adaptativo")
        self.assertEqual(binarizada_adap.shape, (300, 200))

        with self.assertRaises(ValueError):
            corregir_perspectiva(None)
        with self.assertRaises(ValueError):
            binarizar_imagen(np.array([]))

    def test_extraer_lineas_grilla_detects_table_structure(self):
        # Imagen con cuadrícula sintética
        grid = np.zeros((200, 200), dtype=np.uint8)
        # Líneas horizontales
        grid[50, :] = 255
        grid[100, :] = 255
        grid[150, :] = 255
        # Líneas verticales
        grid[:, 40] = 255
        grid[:, 100] = 255
        grid[:, 160] = 255

        lineas_h, lineas_v = extraer_lineas_grilla(grid, escala_h=5, escala_v=5)
        self.assertGreater(np.count_nonzero(lineas_h), 0)
        self.assertGreater(np.count_nonzero(lineas_v), 0)

    def test_calcular_densidad_tinta_and_clasificar_celda(self):
        # Celda blanca vacía
        celda_vacia = np.zeros((50, 100), dtype=np.uint8)
        densidad_vacia = calcular_densidad_tinta(celda_vacia)
        self.assertEqual(densidad_vacia, 0.0)
        self.assertFalse(clasificar_celda_marcada(densidad_vacia))

        # Celda con trazo de firma (píxeles blancos en máscara invertida)
        celda_firma = np.zeros((50, 100), dtype=np.uint8)
        cv2.line(celda_firma, (10, 25), (90, 25), 255, 3)
        cv2.line(celda_firma, (30, 10), (70, 40), 255, 2)
        densidad_firma = calcular_densidad_tinta(celda_firma)
        self.assertGreater(densidad_firma, 0.02)
        self.assertTrue(clasificar_celda_marcada(densidad_firma))

        # Celda vacía edge-cases
        self.assertEqual(calcular_densidad_tinta(np.array([])), 0.0)


class VisionPipelineStepsTests(unittest.TestCase):
    """Pruebas sintéticas de los pasos 1 a 4 del pipeline (limpieza, extracción y decisión)."""

    def _hoja_sintetica(self):
        img = np.full((500, 400, 3), 230, dtype=np.uint8)
        cv2.rectangle(img, (40, 50), (340, 430), (20, 20, 20), 3)
        return img

    def test_detectar_esquinas_hoja_finds_four_corners(self):
        esquinas = detectar_esquinas_hoja(self._hoja_sintetica())
        self.assertIsNotNone(esquinas)
        self.assertEqual(esquinas.shape, (4, 2))
        np.testing.assert_allclose(esquinas[0], [40, 50], atol=6)  # superior-izquierda
        np.testing.assert_allclose(esquinas[2], [340, 430], atol=6)  # inferior-derecha

    def test_detectar_esquinas_hoja_returns_none_without_sheet(self):
        self.assertIsNone(detectar_esquinas_hoja(np.full((200, 200, 3), 128, np.uint8)))
        with self.assertRaises(ValueError):
            detectar_esquinas_hoja(np.array([]))

    def test_corregir_perspectiva_uses_real_sheet_proportion(self):
        img = self._hoja_sintetica()
        esquinas = np.array(
            [[40, 50], [340, 50], [340, 430], [40, 430]], dtype="float32"
        )
        salida = corregir_perspectiva(img, esquinas=esquinas)
        self.assertEqual(salida.shape[:2], (380, 300))  # alto x ancho de la hoja real

    def test_corregir_perspectiva_raises_when_no_sheet_detected(self):
        blanco = np.full((200, 200, 3), 255, np.uint8)
        with self.assertRaises(ValueError):
            corregir_perspectiva(blanco)

    def test_binarizar_normalizado_removes_gradient_shadow(self):
        # Fondo con sombra en degradé y una línea oscura fina
        gradiente = np.tile(np.linspace(60, 220, 300, dtype=np.uint8), (200, 1))
        cv2.line(gradiente, (0, 100), (299, 100), 0, 3)
        binaria = binarizar_imagen(gradiente, metodo="normalizado")
        self.assertEqual(binaria.shape, (200, 300))
        self.assertTrue(set(np.unique(binaria)).issubset({0, 255}))
        # La línea queda marcada y el fondo casi no
        self.assertGreater(np.count_nonzero(binaria[98:103]), 0)
        self.assertLess(np.count_nonzero(binaria[:90]) / binaria[:90].size, 0.05)

    def test_detectar_posiciones_lineas_returns_grid_positions(self):
        mascara = np.zeros((200, 300), np.uint8)
        for y in (30, 80, 130):
            mascara[y, :] = 255
        for x in (50, 150, 250):
            mascara[:, x] = 255
        self.assertEqual(detectar_posiciones_lineas(mascara, eje=0), [30, 80, 130])
        self.assertEqual(detectar_posiciones_lineas(mascara, eje=1), [50, 150, 250])
        self.assertEqual(
            detectar_posiciones_lineas(np.zeros((10, 10), np.uint8), eje=0), []
        )
        self.assertEqual(detectar_posiciones_lineas(np.array([]), eje=0), [])

    def test_detectar_posiciones_lineas_merges_thick_lines(self):
        mascara = np.zeros((100, 100), np.uint8)
        mascara[40:43, :] = 255  # línea de 3 px: un solo renglón detectado
        self.assertEqual(detectar_posiciones_lineas(mascara, eje=0), [41])

    def test_recortar_celdas_grid_shape_and_margin(self):
        binaria = np.full((120, 200), 255, np.uint8)
        filas = recortar_celdas(
            binaria, ys=[0, 40, 80, 120], xs=[0, 100, 200], margen=4
        )
        self.assertEqual(len(filas), 3)
        self.assertEqual(len(filas[0]), 2)
        self.assertEqual(filas[0][0].shape, (32, 92))

    def test_densidad_celda_limpia_ignores_isolated_dots(self):
        self.assertEqual(densidad_celda_limpia(np.array([])), 0.0)
        celda = np.zeros((40, 80), np.uint8)
        celda[20, 40] = 255  # punto aislado: ruido
        self.assertEqual(densidad_celda_limpia(celda), 0.0)
        cv2.line(celda, (10, 20), (70, 20), 255, 4)  # trazo real de firma
        self.assertGreater(densidad_celda_limpia(celda), 0.05)


class VisionAttendanceServiceBusinessRuleTests(unittest.TestCase):
    def setUp(self):
        self.servicio = ServicioAsistenciaVision()
        self.fecha_laboral = date(2026, 11, 5)  # Jueves (weekday = 3)
        self.fecha_domingo = date(2026, 11, 8)  # Domingo (weekday = 6)

    def test_calcular_horas_trabajadas(self):
        # Jornada normal 8h
        self.assertEqual(calcular_horas_trabajadas("07:00", "15:00"), Decimal("8.00"))
        # Jornada fraccional
        self.assertEqual(calcular_horas_trabajadas("06:50", "15:27"), Decimal("8.62"))
        # Cruce de medianoche
        self.assertEqual(calcular_horas_trabajadas("22:00", "06:00"), Decimal("8.00"))
        # Valores inválidos o incompletos
        self.assertIsNone(calcular_horas_trabajadas(None, "15:00"))
        self.assertIsNone(calcular_horas_trabajadas("07:00", None))
        self.assertIsNone(calcular_horas_trabajadas("invalid", "15:00"))

    def test_jornada_8_horas_presente_con_horas_extra(self):
        emp_8h = ConfiguracionEmpleado(
            legajo="20740",
            nombre="Alancay Aldo",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        )
        fila = FilaPlanillaExtraida(
            numero_fila=1,
            legajo="20740",
            nombre="Alancay Aldo",
            densidad_firma=0.08,
            tiene_firma=True,
            tiene_entrada=True,
            tiene_salida=True,
            hora_entrada="13:00",
            hora_salida="22:30",  # 9.5 horas trabajadas
        )

        resultado = self.servicio.clasificar_fila(fila, emp_8h, self.fecha_laboral)
        self.assertEqual(resultado.estado, "Presente")
        self.assertEqual(resultado.horas_trabajadas, Decimal("9.50"))
        self.assertEqual(resultado.horas_jornada, Decimal("8.0"))
        self.assertEqual(resultado.diferencia_banco_horas, Decimal("1.50"))
        self.assertFalse(resultado.olvido_salida)
        self.assertIn("+1.50h", resultado.observaciones)

    def test_jornada_5_horas_presente_con_horas_faltantes(self):
        emp_5h = ConfiguracionEmpleado(
            legajo="414770",
            nombre="Cañete Romina",
            jornada_horas=JORNADA_5_HORAS,
            dia_franco_semanal=6,
        )
        fila = FilaPlanillaExtraida(
            numero_fila=2,
            legajo="414770",
            nombre="Cañete Romina",
            densidad_firma=0.05,
            tiene_firma=True,
            tiene_entrada=True,
            tiene_salida=True,
            hora_entrada="10:00",
            hora_salida="14:00",  # 4 horas trabajadas (esperaba 5)
        )

        resultado = self.servicio.clasificar_fila(fila, emp_5h, self.fecha_laboral)
        self.assertEqual(resultado.estado, "Presente")
        self.assertEqual(resultado.horas_trabajadas, Decimal("4.00"))
        self.assertEqual(resultado.horas_jornada, Decimal("5.0"))
        self.assertEqual(resultado.diferencia_banco_horas, Decimal("-1.00"))
        self.assertIn("-1.00h", resultado.observaciones)

    def test_regla_olvido_salida_se_computa_como_presente(self):
        """Regla: si tienen al menos la entrada están presentes y se olvidan la salida."""
        emp = ConfiguracionEmpleado(
            legajo="55939",
            nombre="Obregon Diego",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        )
        fila = FilaPlanillaExtraida(
            numero_fila=3,
            legajo="55939",
            nombre="Obregon Diego",
            densidad_firma=0.03,
            tiene_firma=True,
            tiene_entrada=True,
            tiene_salida=False,
            hora_entrada="06:42",
            hora_salida=None,  # Se olvidó de fichar la salida
        )

        resultado = self.servicio.clasificar_fila(fila, emp, self.fecha_laboral)
        self.assertEqual(resultado.estado, "Presente")
        self.assertTrue(resultado.olvido_salida)
        self.assertEqual(resultado.horas_trabajadas, Decimal("8.0"))
        self.assertEqual(resultado.diferencia_banco_horas, Decimal("0.00"))
        self.assertIn("Fichaje de salida no registrado", resultado.observaciones)

    def test_regla_franco_semanal_es_neutral_y_no_penaliza(self):
        """Regla: todos tienen un franco por semana de lunes a domingo."""
        emp = ConfiguracionEmpleado(
            legajo="21097",
            nombre="Barrientos Silvia",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,  # Domingo es su franco
        )
        fila_vacia = FilaPlanillaExtraida(
            numero_fila=4,
            legajo="21097",
            nombre="Barrientos Silvia",
            densidad_firma=0.0,
            tiene_firma=False,
            tiene_entrada=False,
            tiene_salida=False,
            hora_entrada=None,
            hora_salida=None,
        )

        # En su día de franco (domingo) -> Estado Franco (neutral)
        resultado_franco = self.servicio.clasificar_fila(
            fila_vacia, emp, self.fecha_domingo
        )
        self.assertEqual(resultado_franco.estado, "Franco")
        self.assertEqual(resultado_franco.horas_trabajadas, Decimal("0.00"))
        self.assertEqual(resultado_franco.diferencia_banco_horas, Decimal("0.00"))
        self.assertIn("Franco semanal", resultado_franco.observaciones)

    def test_falta_sin_aviso_descuenta_jornada_completa(self):
        emp_8h = ConfiguracionEmpleado(
            legajo="63365",
            nombre="Barrios Gonzalo",
            jornada_horas=JORNADA_8_HORAS,
            dia_franco_semanal=6,
        )
        fila_vacia = FilaPlanillaExtraida(
            numero_fila=5,
            legajo="63365",
            nombre="Barrios Gonzalo",
            densidad_firma=0.0,
            tiene_firma=False,
            tiene_entrada=False,
            tiene_salida=False,
        )

        # Jueves (día laborable habitual) -> Falta sin aviso (-8.0h)
        resultado = self.servicio.clasificar_fila(
            fila_vacia, emp_8h, self.fecha_laboral
        )
        self.assertEqual(resultado.estado, "Falta sin aviso")
        self.assertEqual(resultado.horas_trabajadas, Decimal("0.00"))
        self.assertEqual(resultado.diferencia_banco_horas, Decimal("-8.00"))

    def test_integracion_con_corte_de_periodo(self):
        emp = ConfiguracionEmpleado(
            legajo="1",
            nombre="Juan Perez",
            jornada_horas=JORNADA_8_HORAS,
        )
        fila = FilaPlanillaExtraida(
            numero_fila=1,
            legajo="1",
            nombre="Juan Perez",
            densidad_firma=0.04,
            tiene_firma=True,
            tiene_entrada=True,
            tiene_salida=True,
            hora_entrada="08:00",
            hora_salida="17:00",  # 9h (+1h)
        )
        resultado = self.servicio.clasificar_fila(fila, emp, self.fecha_laboral)
        registros = self.servicio.convertir_a_registros_jornada(
            [resultado], self.fecha_laboral
        )

        periodo = PeriodoLaboral.desde_fecha(self.fecha_laboral)
        liquidacion = calcular_corte_periodo(
            empleado_id="1",
            empleado_nombre="Juan Perez",
            periodo=periodo,
            jornada_habitual=Decimal("8.0"),
            registros=registros,
        )
        self.assertEqual(liquidacion.horas_extra, Decimal("1.00"))
        self.assertEqual(liquidacion.saldo_neto, Decimal("1.00"))
        self.assertEqual(liquidacion.dias_presente, 1)


class RealImageAttendanceSheetTests(unittest.TestCase):
    def test_processes_real_user_uploaded_sheet_if_available(self):
        real_img_path = (
            "C:/Users/Gaby/.gemini/antigravity/brain/97d2ee91-b3e7-4d07-8a7b-287a79f34555"
            "/.user_uploaded/media_1795307584497_fc91c018.jpg"
        )
        if not os.path.exists(real_img_path):
            self.skipTest("Imagen real no presente en este entorno.")

        img = cv2.imread(real_img_path)
        self.assertIsNotNone(img)

        # 1. Corrección de perspectiva
        warped = corregir_perspectiva(img, ancho_destino=768, alto_destino=1024)
        self.assertEqual(warped.shape, (1024, 768, 3))

        # 2. Binarización
        binarizada = binarizar_imagen(warped)
        self.assertEqual(binarizada.shape, (1024, 768))

        # 3. Detección de grilla
        lineas_h, lineas_v = extraer_lineas_grilla(binarizada)
        self.assertGreater(np.count_nonzero(lineas_h), 1000)
        self.assertGreater(np.count_nonzero(lineas_v), 1000)


if __name__ == "__main__":
    unittest.main()
