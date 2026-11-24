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
import unittest
from typing import List

# Añadir la raíz de la extensión al path para permitir importar Logic y SEEGPlanner
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from Logic.result import Err, Ok
from Logic.trajectory_planner import (
    ContactPoint,
    ElectrodeConfig,
    TrajectoryMetrics,
    calculate_trajectory,
)
from SEEGPlanner import SEEGPlannerLogic


class TestClinicalDashboardAndUILogic(unittest.TestCase):
    """Suite de pruebas unitarias standalone para la lógica del cuadro de mandos clínico y ciclo de vida."""

    def setUp(self) -> None:
        """Inicializa la lógica desacoplada y crea trayectorias sintéticas para las pruebas."""
        self.logic = SEEGPlannerLogic()
        self.cfg = ElectrodeConfig(diameter_mm=0.8, num_contacts=10)

        # Trayectoria 1: Segura (perpendicular en eje Z)
        self.t1 = calculate_trajectory(
            entry_point=(0.0, 0.0, 50.0),
            target_point=(0.0, 0.0, 0.0),
            name="SEEG_Elec_01",
            skull_normal=(0.0, 0.0, 1.0),
            max_safe_angle_deg=30.0,
            config=self.cfg,
        ).value

        # Trayectoria 2: Alerta (ángulo oblicuo de 45° con normal)
        self.t2 = calculate_trajectory(
            entry_point=(35.0, 0.0, 35.0),
            target_point=(0.0, 0.0, 0.0),
            name="SEEG_Elec_02",
            skull_normal=(0.0, 0.0, 1.0),
            max_safe_angle_deg=30.0,
            config=self.cfg,
        ).value

    def test_remove_planned_trajectory_by_index_success(self) -> None:
        """Verifica que la eliminación de una trayectoria por índice retire el elemento correcto."""
        trajectories: List[TrajectoryMetrics] = [self.t1, self.t2]

        # Eliminar el primer electrodo (índice 0)
        res = self.logic.removePlannedTrajectoryByIndex(0, trajectories)
        self.assertIsInstance(res, Ok)
        self.assertEqual(res.value.name, "SEEG_Elec_01")
        self.assertEqual(len(trajectories), 1)
        self.assertEqual(trajectories[0].name, "SEEG_Elec_02")

    def test_remove_planned_trajectory_by_index_out_of_bounds(self) -> None:
        """Verifica que índices inválidos retornen Err sin alterar la colección."""
        trajectories: List[TrajectoryMetrics] = [self.t1]

        # Índice negativo
        res_neg = self.logic.removePlannedTrajectoryByIndex(-1, trajectories)
        self.assertIsInstance(res_neg, Err)

        # Índice mayor o igual a la longitud
        res_high = self.logic.removePlannedTrajectoryByIndex(5, trajectories)
        self.assertIsInstance(res_high, Err)
        self.assertEqual(len(trajectories), 1)

    def test_focus_trajectory_in_views_midpoint(self) -> None:
        """Verifica el cálculo del punto medio tridimensional para navegación visual."""
        res = self.logic.focusTrajectoryInViews(self.t1)
        self.assertIsInstance(res, Ok)
        # En entorno sin Slicer GUI, debe retornar mensaje de simulación o confirmación
        self.assertTrue("centrad" in res.value.lower())

    def test_focus_trajectory_in_views_none_guard(self) -> None:
        """Verifica la guarda ante trayectorias nulas."""
        res = self.logic.focusTrajectoryInViews(None)
        self.assertIsInstance(res, Err)

    def test_dashboard_metrics_formatting(self) -> None:
        """Verifica que las métricas formateadas para las columnas del cuadro de mandos sean precisas."""
        # Comprobar estado de la trayectoria segura
        self.assertTrue(self.t1.is_safe)
        self.assertEqual(self.t1.length_mm, 50.0)
        self.assertAlmostEqual(self.t1.angle_degrees or 0.0, 0.0, places=1)
        self.assertEqual(len(self.t1.contacts), 10)

        # Comprobar estado de la trayectoria en alerta
        self.assertFalse(self.t2.is_safe)
        self.assertGreater(self.t2.angle_degrees or 0.0, 30.0)
        self.assertIn("Alerta", self.t2.status_message)

    def test_contacts_inspection_table_data(self) -> None:
        """Verifica que los contactos expongan las coordenadas y distancias requeridas para la sub-tabla."""
        contacts = self.t1.contacts
        self.assertEqual(len(contacts), 10)

        first_c = contacts[0]
        self.assertEqual(first_c.label, "E01")
        self.assertGreater(first_c.distance_from_tip_mm, 0.0)
        self.assertEqual(len(first_c.position_ras), 3)

        last_c = contacts[-1]
        self.assertEqual(last_c.label, "E10")
        self.assertGreater(last_c.distance_from_tip_mm, first_c.distance_from_tip_mm)


if __name__ == "__main__":
    unittest.main()
