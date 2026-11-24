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

# Añadir la raíz de la extensión al path para permitir importar Logic
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from Logic.result import Err, Ok
from Logic.target_manager import (
    TargetStructure,
    VolumeMetadata,
    compute_segment_target,
    validate_volume_metadata,
)


class TestTargetManagerStandalone(unittest.TestCase):
    """Suite de pruebas unitarias standalone para el módulo target_manager."""

    def setUp(self) -> None:
        """Matriz homogénea IJK a RAS de identidad escalada con 1mm de espaciado y origen centrado."""
        self.ijk_to_ras = np.array([
            [1.0, 0.0, 0.0, -50.0],
            [0.0, 1.0, 0.0, -50.0],
            [0.0, 0.0, 1.0, -50.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

    def test_validate_volume_metadata_optimal(self) -> None:
        """Verifica que volúmenes con espaciado <= 1.5mm se consideren óptimos para estereotaxia."""
        result = validate_volume_metadata(
            dimensions=(256, 256, 176),
            spacing_mm=(1.0, 1.0, 1.0),
        )
        self.assertIsInstance(result, Ok)
        meta = result.value
        self.assertTrue(meta.is_stereotaxy_optimal)
        self.assertEqual(meta.voxel_volume_mm3, 1.0)

    def test_validate_volume_metadata_warning(self) -> None:
        """Verifica que volúmenes con espaciado grueso emitan nota de advertencia."""
        result = validate_volume_metadata(
            dimensions=(128, 128, 60),
            spacing_mm=(1.0, 1.0, 2.5),
        )
        self.assertIsInstance(result, Ok)
        meta = result.value
        self.assertFalse(meta.is_stereotaxy_optimal)
        self.assertIn("Alerta", meta.quality_notes)

    def test_validate_volume_metadata_invalid(self) -> None:
        """Verifica que dimensiones o espaciados no válidos retornen Err."""
        res_dim = validate_volume_metadata(dimensions=(-1, 10, 10), spacing_mm=(1.0, 1.0, 1.0))
        self.assertIsInstance(res_dim, Err)

        res_spc = validate_volume_metadata(dimensions=(10, 10, 10), spacing_mm=(1.0, 0.0, 1.0))
        self.assertIsInstance(res_spc, Err)

    def test_compute_segment_target_convex(self) -> None:
        """Verifica el cálculo de centroide en una estructura elipsoidal simétrica (simulando amígdala)."""
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        # Centro en IJK: i=50, j=50, k=50 -> en RAS: (0.0, 0.0, 0.0)
        # Esfera de radio 5 vóxeles
        z, y, x = np.ogrid[:100, :100, :100]
        dist_from_center = (x - 50) ** 2 + (y - 50) ** 2 + (z - 50) ** 2
        mask[dist_from_center <= 25] = 1

        result = compute_segment_target(
            segment_id="Segment_Amygdala_R",
            segment_name="Amygdala_Right",
            binary_mask=mask,
            ijk_to_ras_matrix=self.ijk_to_ras,
        )

        self.assertIsInstance(result, Ok)
        target = result.value
        self.assertEqual(target.name, "Amygdala_Right")
        self.assertTrue(target.is_centroid_inside_mask)
        # El centroide RAS debe coincidir con el centro (0.0, 0.0, 0.0)
        self.assertAlmostEqual(target.centroid_ras[0], 0.0, places=1)
        self.assertAlmostEqual(target.centroid_ras[1], 0.0, places=1)
        self.assertAlmostEqual(target.centroid_ras[2], 0.0, places=1)
        self.assertGreater(target.volume_mm3, 400.0)

    def test_compute_segment_target_non_convex(self) -> None:
        """Verifica que en geometrías cóncavas donde el centroide cae fuera, se proyecte a un vóxel contenido."""
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        # Crear estructura en forma de "U" o dos bloques separados simétricos
        # Bloque 1: x entre 20 y 30, y=50, z=50
        # Bloque 2: x entre 70 y 80, y=50, z=50
        # El centro de masa caerá en x=50, donde mask es 0 (vacío)
        mask[50, 50, 20:30] = 1
        mask[50, 50, 70:80] = 1

        result = compute_segment_target(
            segment_id="Segment_Cortex_Temporal",
            segment_name="Cortex_Temporal_Curved",
            binary_mask=mask,
            ijk_to_ras_matrix=self.ijk_to_ras,
        )

        self.assertIsInstance(result, Ok)
        target = result.value
        self.assertFalse(target.is_centroid_inside_mask)
        # El centroide geométrico medio cae en x=49.5 (aprox 0.0 en RAS)
        # Pero el punto contenido debe pertenecer a uno de los dos bloques (x <= 30 o x >= 70 en IJK)
        # En RAS: x = i - 50 -> -50 + 29 = -21 o -50 + 70 = +20
        self.assertNotEqual(target.centroid_ras, target.contained_point_ras)
        self.assertTrue(target.contained_point_ras[0] <= -20.0 or target.contained_point_ras[0] >= 20.0)

    def test_compute_segment_target_empty_mask(self) -> None:
        """Verifica que una máscara vacía devuelva Err."""
        empty_mask = np.zeros((50, 50, 50), dtype=np.uint8)
        result = compute_segment_target(
            segment_id="Empty_Seg",
            segment_name="Empty_Hippocampus",
            binary_mask=empty_mask,
            ijk_to_ras_matrix=self.ijk_to_ras,
        )
        self.assertIsInstance(result, Err)


if __name__ == "__main__":
    unittest.main()
