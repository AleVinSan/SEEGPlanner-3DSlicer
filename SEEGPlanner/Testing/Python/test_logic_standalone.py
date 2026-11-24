# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

import os
import sys
import tempfile
import unittest

# Añadir la raíz de la extensión al path para permitir importar Logic
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from Logic.eeg_1020_calculator import CanonicalLandmarks, calculate_1020_points
from Logic.igtlink_exporter import (
    build_trajectory_transform_matrix,
    export_trajectories_to_json_file,
    format_trajectories_payload,
)
from Logic.result import Err, Ok
from Logic.trajectory_planner import calculate_trajectory


class TestSEEGPlannerStandaloneLogic(unittest.TestCase):
    """Suite de pruebas unitarias standalone para la lógica matemática y algoritmos de SEEGPlanner."""

    def setUp(self) -> None:
        """Configuración de fiduciales anatómicos sintéticos típicos de cabeza de adulto en mm (RAS)."""
        # RAS: R=Right (+), A=Anterior (+), S=Superior (+)
        self.valid_landmarks = CanonicalLandmarks(
            nasion=(0.0, 95.0, -10.0),      # Anterior
            inion=(0.0, -115.0, -35.0),    # Posterior
            lpa=(-75.0, -10.0, -40.0),     # Left (R es negativo)
            rpa=(75.0, -10.0, -40.0),      # Right (R es positivo)
        )

    def test_calculate_1020_points_success(self) -> None:
        """Verifica que el cálculo 10-20 genere todos los electrodos canónicos."""
        result = calculate_1020_points(self.valid_landmarks)
        self.assertIsInstance(result, Ok)
        points = result.value

        # Comprobar que los puntos clave existen
        expected_keys = ["Nz", "Iz", "LPA", "RPA", "Fpz", "Cz", "Pz", "Oz", "T3", "T4", "C3", "C4"]
        for key in expected_keys:
            self.assertIn(key, points)
            self.assertEqual(len(points[key]), 3)

        # Cz debe estar superior a Nasion e Inion en espacio RAS
        cz = points["Cz"]
        self.assertGreater(cz[2], self.valid_landmarks.nasion[2])
        self.assertGreater(cz[2], self.valid_landmarks.inion[2])

    def test_calculate_1020_points_invalid_degenerate(self) -> None:
        """Verifica que landmarks colapsados o demasiado cercanos retornen Err."""
        degenerate = CanonicalLandmarks(
            nasion=(0.0, 0.0, 0.0),
            inion=(0.0, 5.0, 0.0),  # A solo 5 mm
            lpa=(0.0, 0.0, 0.0),
            rpa=(0.0, 0.0, 0.0),
        )
        result = calculate_1020_points(degenerate)
        self.assertIsInstance(result, Err)

    def test_calculate_trajectory_metrics(self) -> None:
        """Verifica el cálculo de longitud, vector director y evaluación de ángulo con normal."""
        # Entrada en corteza parietal derecha, diana en hipocampo derecho
        entry = (50.0, -20.0, 40.0)
        target = (25.0, -15.0, -15.0)

        result = calculate_trajectory(
            entry_point=entry,
            target_point=target,
            name="Electrode_Hippocampus_R",
            skull_normal=(0.7, -0.1, 0.7),  # Normal apuntando oblicua-superior-derecha
            max_safe_angle_deg=35.0,
        )

        self.assertIsInstance(result, Ok)
        metrics = result.value
        self.assertEqual(metrics.name, "Electrode_Hippocampus_R")
        self.assertGreater(metrics.length_mm, 50.0)
        self.assertIsNotNone(metrics.angle_degrees)

    def test_calculate_trajectory_too_short(self) -> None:
        """Verifica que una trayectoria menor a 5 mm sea rechazada por seguridad clínica."""
        entry = (10.0, 10.0, 10.0)
        target = (11.0, 10.5, 10.2)
        result = calculate_trajectory(entry, target)
        self.assertIsInstance(result, Err)

    def test_igtlink_transform_matrix_and_payload(self) -> None:
        """Verifica la generación de la matriz de transformación 4x4 y payload exportable."""
        entry = (40.0, -10.0, 30.0)
        target = (20.0, -10.0, -10.0)
        metrics_res = calculate_trajectory(entry, target, name="Electrode_1")
        self.assertIsInstance(metrics_res, Ok)

        matrix_res = build_trajectory_transform_matrix(metrics_res.value)
        self.assertIsInstance(matrix_res, Ok)
        matrix = matrix_res.value
        self.assertEqual(len(matrix), 4)
        self.assertEqual(len(matrix[0]), 4)
        # La columna de traslación debe corresponder al punto de entrada
        self.assertAlmostEqual(matrix[0][3], entry[0])
        self.assertAlmostEqual(matrix[1][3], entry[1])
        self.assertAlmostEqual(matrix[2][3], entry[2])

        # Formateo de payload
        payload_res = format_trajectories_payload([metrics_res.value], patient_id="PATIENT_001")
        self.assertIsInstance(payload_res, Ok)
        payload = payload_res.value
        self.assertEqual(payload["electrode_count"], 1)

        # Exportación a archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            export_res = export_trajectories_to_json_file([metrics_res.value], tmp_path)
            self.assertIsInstance(export_res, Ok)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 50)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
