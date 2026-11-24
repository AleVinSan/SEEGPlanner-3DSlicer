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

from Logic.eeg_1020_calculator import project_points_to_surface_mesh
from Logic.result import Err, Ok
from Logic.skull_surface_extractor import (
    SurfaceExtractionParams,
    extract_head_surface_polydata,
    get_surface_normal_at_point,
)


class TestSurfaceAndProjectionStandalone(unittest.TestCase):
    """Suite de pruebas unitarias standalone para extracción de superficie y proyección 10-20."""

    def setUp(self) -> None:
        """Crea geometrías sintéticas para validación si VTK está disponible."""
        self.has_vtk = vtk is not None
        if self.has_vtk:
            # Esfera sintética centrada en el origen con radio 100 mm (escala cabeza humana)
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(0.0, 0.0, 0.0)
            sphere.SetRadius(100.0)
            sphere.SetThetaResolution(36)
            sphere.SetPhiResolution(36)
            sphere.Update()
            self.synthetic_sphere_polydata = sphere.GetOutput()
        else:
            self.synthetic_sphere_polydata = None

    def test_surface_extraction_params(self) -> None:
        """Verifica que los parámetros por defecto de extracción sean consistentes."""
        params = SurfaceExtractionParams()
        self.assertEqual(params.threshold_ratio, 0.15)
        self.assertEqual(params.smoothing_iterations, 15)
        self.assertTrue(params.extract_largest_component_only)

    def test_project_points_to_surface_fallback_when_none(self) -> None:
        """Verifica que si no hay superficie, se devuelvan los puntos analíticos sin error."""
        points = {"Cz": (0.0, 0.0, 85.0), "Fpz": (0.0, 80.0, 0.0)}
        res = project_points_to_surface_mesh(points, None, head_center_ras=(0.0, 0.0, 0.0))
        self.assertIsInstance(res, Ok)
        self.assertEqual(res.value, points)

    def test_project_points_empty_dict(self) -> None:
        """Verifica que un diccionario vacío devuelva Err."""
        res = project_points_to_surface_mesh({}, self.synthetic_sphere_polydata, (0.0, 0.0, 0.0))
        self.assertIsInstance(res, Err)

    @unittest.skipUnless(vtk is not None, "Requiere VTK para ejecución")
    def test_project_points_to_sphere_surface(self) -> None:
        """Verifica que puntos analíticos sub-superficiales se proyecten al radio exacto de la esfera."""
        # Punto inicial a 80 mm del centro en el eje Z; la esfera tiene radio 100 mm
        points = {
            "Cz": (0.0, 0.0, 80.0),
            "Fpz": (0.0, 75.0, 0.0),
            "LPA": (-70.0, 0.0, 0.0),
        }
        res = project_points_to_surface_mesh(
            points,
            self.synthetic_sphere_polydata,
            head_center_ras=(0.0, 0.0, 0.0),
        )
        self.assertIsInstance(res, Ok)
        proj = res.value

        # Cz debe haberse proyectado a Z ~= 100 mm
        cz_proj = proj["Cz"]
        self.assertAlmostEqual(cz_proj[0], 0.0, places=1)
        self.assertAlmostEqual(cz_proj[1], 0.0, places=1)
        self.assertAlmostEqual(cz_proj[2], 100.0, delta=1.0)

        # Fpz debe haberse proyectado a Y ~= 100 mm
        fpz_proj = proj["Fpz"]
        self.assertAlmostEqual(fpz_proj[1], 100.0, delta=1.0)

    @unittest.skipUnless(vtk is not None, "Requiere VTK para ejecución")
    def test_get_surface_normal_at_point(self) -> None:
        """Verifica que la normal exterior calculada en la esfera coincida con el vector radial."""
        # En una esfera centrada en (0,0,0), la normal en (0, 0, 100) debe ser (0, 0, 1)
        res_z = get_surface_normal_at_point(self.synthetic_sphere_polydata, (0.0, 0.0, 100.0))
        self.assertIsInstance(res_z, Ok)
        norm_z = res_z.value
        self.assertAlmostEqual(norm_z[0], 0.0, places=2)
        self.assertAlmostEqual(norm_z[1], 0.0, places=2)
        self.assertAlmostEqual(norm_z[2], 1.0, delta=0.05)

        # En (100, 0, 0), la normal debe ser (1, 0, 0)
        res_x = get_surface_normal_at_point(self.synthetic_sphere_polydata, (100.0, 0.0, 0.0))
        self.assertIsInstance(res_x, Ok)
        norm_x = res_x.value
        self.assertAlmostEqual(norm_x[0], 1.0, delta=0.05)

    @unittest.skipUnless(vtk is not None, "Requiere VTK para ejecución")
    def test_extract_head_surface_polydata_synthetic(self) -> None:
        """Verifica la extracción de isosuperficie desde una imagen sintética 3D."""
        img = vtk.vtkImageData()
        img.SetDimensions(40, 40, 40)
        img.AllocateScalars(vtk.VTK_FLOAT, 1)

        # Rellenar con esfera sintética de intensidad
        for z in range(40):
            for y in range(40):
                for x in range(40):
                    r_sq = (x - 20) ** 2 + (y - 20) ** 2 + (z - 20) ** 2
                    val = 100.0 if r_sq <= 100 else 0.0
                    img.SetScalarComponentFromFloat(x, y, z, 0, val)

        ijk_to_ras = [
            [1.0, 0.0, 0.0, -20.0],
            [0.0, 1.0, 0.0, -20.0],
            [0.0, 0.0, 1.0, -20.0],
            [0.0, 0.0, 0.0, 1.0],
        ]

        res = extract_head_surface_polydata(
            imageData=img,
            ijk_to_ras_matrix=ijk_to_ras,
            params=SurfaceExtractionParams(threshold_ratio=0.5, smoothing_iterations=5),
        )
        self.assertIsInstance(res, Ok)
        poly = res.value
        self.assertGreater(poly.GetNumberOfPoints(), 100)
        self.assertGreater(poly.GetNumberOfCells(), 100)


if __name__ == "__main__":
    unittest.main()
