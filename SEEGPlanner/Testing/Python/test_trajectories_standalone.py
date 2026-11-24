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
import numpy as np

try:
    import vtk
except ImportError:
    vtk = None

# Añadir la raíz de la extensión al path para permitir importar Logic
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from Logic.result import Err, Ok
from Logic.trajectory_planner import (
    ContactPoint,
    ElectrodeConfig,
    TrajectoryConflict,
    TrajectoryMetrics,
    calculate_electrode_contacts,
    calculate_trajectory,
    check_trajectory_conflicts,
    compute_segment_to_segment_distance,
    generate_electrode_tube_polydata,
    point_to_segment_distance,
)


class TestTrajectoriesAndSafetyStandalone(unittest.TestCase):
    """Suite de pruebas unitarias standalone para modelado de electrodos, contactos y colisiones."""

    def test_electrode_config_defaults(self) -> None:
        """Verifica los valores nominales y propiedades calculadas de la configuración de electrodo."""
        cfg = ElectrodeConfig()
        self.assertEqual(cfg.diameter_mm, 0.8)
        self.assertAlmostEqual(cfg.radius_mm, 0.4)
        self.assertEqual(cfg.num_contacts, 10)
        self.assertEqual(cfg.contact_length_mm, 2.0)
        self.assertEqual(cfg.contact_spacing_mm, 1.5)
        self.assertEqual(cfg.bolt_outer_diameter_mm, 2.5)
        self.assertAlmostEqual(cfg.bolt_radius_mm, 1.25)
        self.assertEqual(cfg.bolt_length_mm, 15.0)

    def test_calculate_electrode_contacts_distribution(self) -> None:
        """Verifica la distribución geométrica precisa de los contactos a lo largo del electrodo."""
        # Diana en el origen (0,0,0), entrada a 50 mm en el eje Z (0,0,50)
        target = (0.0, 0.0, 0.0)
        entry = (0.0, 0.0, 50.0)
        cfg = ElectrodeConfig(num_contacts=5, contact_length_mm=2.0, contact_spacing_mm=1.5, tip_to_first_contact_mm=1.0)

        res = calculate_electrode_contacts(entry, target, cfg)
        self.assertIsInstance(res, Ok)
        contacts = res.value
        self.assertEqual(len(contacts), 5)

        # Contacto 1 (E01) debe situarse en tip + tip_to_first + length/2 = 1.0 + 1.0 = 2.0 mm
        c1 = contacts[0]
        self.assertEqual(c1.index, 1)
        self.assertEqual(c1.label, "E01")
        self.assertAlmostEqual(c1.distance_from_tip_mm, 2.0)
        self.assertAlmostEqual(c1.position_ras[2], 2.0)

        # Paso = 2.0 + 1.5 = 3.5 mm. Contacto 2 debe estar a 2.0 + 3.5 = 5.5 mm
        c2 = contacts[1]
        self.assertEqual(c2.index, 2)
        self.assertEqual(c2.label, "E02")
        self.assertAlmostEqual(c2.distance_from_tip_mm, 5.5)
        self.assertAlmostEqual(c2.position_ras[2], 5.5)

    def test_calculate_electrode_contacts_short_trajectory(self) -> None:
        """Verifica que trayectorias menores a 5 mm sean rechazadas."""
        res = calculate_electrode_contacts((0.0, 0.0, 2.0), (0.0, 0.0, 0.0))
        self.assertIsInstance(res, Err)

    def test_point_to_segment_distance(self) -> None:
        """Verifica la distancia euclídea mínima entre un punto y un segmento 3D."""
        p_start = (0.0, 0.0, 0.0)
        p_end = (0.0, 0.0, 10.0)

        # Punto perpendicular al punto medio a distancia 4 mm
        pt = (4.0, 0.0, 5.0)
        d = point_to_segment_distance(pt, p_start, p_end)
        self.assertAlmostEqual(d, 4.0)

        # Punto más allá del extremo distal
        pt_beyond = (0.0, 0.0, 15.0)
        d_beyond = point_to_segment_distance(pt_beyond, p_start, p_end)
        self.assertAlmostEqual(d_beyond, 5.0)

    def test_segment_to_segment_distance_parallel(self) -> None:
        """Verifica el cálculo de distancia entre segmentos paralelos."""
        s1_a, s1_b = (0.0, 0.0, 0.0), (0.0, 0.0, 20.0)
        s2_a, s2_b = (6.0, 0.0, 0.0), (6.0, 0.0, 20.0)
        dist = compute_segment_to_segment_distance(s1_a, s1_b, s2_a, s2_b)
        self.assertAlmostEqual(dist, 6.0)

    def test_segment_to_segment_distance_collinear_separated(self) -> None:
        """Verifica la distancia entre segmentos colineales no superpuestos."""
        s1_a, s1_b = (0.0, 0.0, 0.0), (0.0, 0.0, 10.0)
        s2_a, s2_b = (0.0, 0.0, 15.0), (0.0, 0.0, 25.0)
        dist = compute_segment_to_segment_distance(s1_a, s1_b, s2_a, s2_b)
        self.assertAlmostEqual(dist, 5.0)

    def test_segment_to_segment_distance_skew(self) -> None:
        """Verifica la distancia mínima entre segmentos alabeadas ortogonales."""
        s1_a, s1_b = (0.0, -10.0, 0.0), (0.0, 10.0, 0.0)
        s2_a, s2_b = (-10.0, 0.0, 3.5), (10.0, 0.0, 3.5)
        dist = compute_segment_to_segment_distance(s1_a, s1_b, s2_a, s2_b)
        self.assertAlmostEqual(dist, 3.5)

    def test_segment_to_segment_distance_crossing(self) -> None:
        """Verifica que dos segmentos que se intersectan tengan distancia cero."""
        s1_a, s1_b = (0.0, -10.0, 0.0), (0.0, 10.0, 0.0)
        s2_a, s2_b = (-10.0, 0.0, 0.0), (10.0, 0.0, 0.0)
        dist = compute_segment_to_segment_distance(s1_a, s1_b, s2_a, s2_b)
        self.assertAlmostEqual(dist, 0.0)

    def test_check_trajectory_conflicts_skull_collision(self) -> None:
        """Verifica la detección de pernos demasiado cercanos en la superficie ósea (< 10 mm)."""
        t1 = calculate_trajectory(
            entry_point=(0.0, 0.0, 50.0),
            target_point=(0.0, 0.0, 0.0),
            name="Electrode_1",
        ).value

        # Entrada a 7 mm de Electrode_1 (peligro de choque de cabezas de perno)
        t2 = calculate_trajectory(
            entry_point=(7.0, 0.0, 50.0),
            target_point=(15.0, 0.0, 0.0),
            name="Electrode_2",
        ).value

        conflicts_res = check_trajectory_conflicts([t1, t2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0)
        self.assertIsInstance(conflicts_res, Ok)
        conflicts = conflicts_res.value
        self.assertTrue(any(c.conflict_type == "SKULL_ENTRY_COLLISION" for c in conflicts))
        skull_c = next(c for c in conflicts if c.conflict_type == "SKULL_ENTRY_COLLISION")
        self.assertAlmostEqual(skull_c.min_distance_mm, 7.0)

    def test_check_trajectory_conflicts_intracranial_proximity(self) -> None:
        """Verifica la detección de proximidad intracraneal profunda (< 3 mm) aun con entradas separadas."""
        # Entradas separadas por 20 mm en cráneo (seguras en superficie)
        # pero que convergen a dianas a 1.2 mm en hipocampo profundo
        t1 = calculate_trajectory(
            entry_point=(0.0, 10.0, 50.0),
            target_point=(0.0, 0.0, 0.0),
            name="Electrode_A",
        ).value

        t2 = calculate_trajectory(
            entry_point=(0.0, -10.0, 50.0),
            target_point=(0.0, 1.2, 0.0),
            name="Electrode_B",
        ).value

        conflicts_res = check_trajectory_conflicts([t1, t2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0)
        self.assertIsInstance(conflicts_res, Ok)
        conflicts = conflicts_res.value
        self.assertTrue(any(c.conflict_type == "INTRACRANIAL_PROXIMITY" for c in conflicts))
        intra_c = next(c for c in conflicts if c.conflict_type == "INTRACRANIAL_PROXIMITY")
        self.assertLess(intra_c.min_distance_mm, 3.0)
        self.assertTrue(intra_c.is_critical)

    def test_check_trajectory_conflicts_safe_all(self) -> None:
        """Verifica que electrodos paralelos bien espaciados (> 15 mm) no generen conflictos."""
        t1 = calculate_trajectory(
            entry_point=(0.0, 0.0, 50.0),
            target_point=(0.0, 0.0, 0.0),
            name="Electrode_L1",
        ).value

        t2 = calculate_trajectory(
            entry_point=(15.0, 0.0, 50.0),
            target_point=(15.0, 0.0, 0.0),
            name="Electrode_L2",
        ).value

        conflicts_res = check_trajectory_conflicts([t1, t2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0)
        self.assertIsInstance(conflicts_res, Ok)
        self.assertEqual(len(conflicts_res.value), 0)

    @unittest.skipUnless(vtk is not None, "Requiere VTK para generación de mallas")
    def test_generate_electrode_tube_polydata(self) -> None:
        """Verifica la generación de la malla poligonal VTK combinada (electrodo + perno guía)."""
        entry = (20.0, 30.0, 60.0)
        target = (10.0, 10.0, 10.0)
        res = generate_electrode_tube_polydata(entry, target, ElectrodeConfig(), radial_resolution=12)
        self.assertIsInstance(res, Ok)
        poly = res.value
        self.assertIsNotNone(poly)
        self.assertGreater(poly.GetNumberOfPoints(), 20)
        self.assertGreater(poly.GetNumberOfCells(), 10)
        # Comprobar que contiene normales asociadas
        normals = poly.GetPointData().GetNormals()
        self.assertIsNotNone(normals)


if __name__ == "__main__":
    unittest.main()

