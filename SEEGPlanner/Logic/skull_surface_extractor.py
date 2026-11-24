# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence, Tuple

import numpy as np

try:
    import vtk
except ImportError:
    vtk = None

from .result import Err, Ok, Result

Point3D = Tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class SurfaceExtractionParams:
    """Parámetros de procesamiento para extracción de la superficie cutánea o craneal."""
    threshold_ratio: float = 0.15  # Fracción de la intensidad máxima para binarización
    smoothing_iterations: int = 15
    pass_band: float = 0.1
    extract_largest_component_only: bool = True


def get_surface_normal_at_point(polydata: Any, point_ras: Point3D) -> Result[Point3D]:
    """
    Obtiene el vector normal exterior a la superficie poligonal en la coordenada RAS dada.
    
    Utiliza vtkPointLocator para encontrar el vértice más próximo y extraer su vector normal.
    """
    if vtk is None:
        return Err("La biblioteca VTK no está disponible en este entorno.")

    if polydata is None or polydata.GetNumberOfPoints() == 0:
        return Err("El modelo de superficie poligonal no contiene vértices.")

    normals_array = polydata.GetPointData().GetNormals()
    if normals_array is None:
        # Generar normales si no existen en los datos de punto
        norm_filter = vtk.vtkPolyDataNormals()
        norm_filter.SetInputData(polydata)
        norm_filter.ComputePointNormalsOn()
        norm_filter.ComputeCellNormalsOff()
        norm_filter.AutoOrientNormalsOn()
        norm_filter.ConsistencyOn()
        norm_filter.Update()
        polydata = norm_filter.GetOutput()
        normals_array = polydata.GetPointData().GetNormals()

    locator = vtk.vtkPointLocator()
    locator.SetDataSet(polydata)
    locator.BuildLocator()

    closest_point_id = locator.FindClosestPoint(list(point_ras))
    if closest_point_id < 0:
        return Err("No se encontró ningún vértice cercano en la superficie.")

    normal_tuple = normals_array.GetTuple3(closest_point_id)
    n_arr = np.array(normal_tuple, dtype=np.float64)
    norm_mag = float(np.linalg.norm(n_arr))

    if norm_mag < 1e-6:
        return Err("La normal extraída tiene magnitud nula.")

    unit_normal = n_arr / norm_mag
    res_tuple: Point3D = (
        round(float(unit_normal[0]), 4),
        round(float(unit_normal[1]), 4),
        round(float(unit_normal[2]), 4),
    )

    resultado: Result[Point3D] = Ok(res_tuple)
    return resultado


def extract_head_surface_polydata(
    imageData: Any,
    ijk_to_ras_matrix: Sequence[Sequence[float]] | np.ndarray,
    params: SurfaceExtractionParams | None = None,
) -> Result[Any]:
    """
    Extrae la malla poligonal (vtkPolyData) de la superficie de la cabeza en coordenadas RAS
    a partir de una imagen volumétrica mediante umbralización y Flying Edges/Marching Cubes.
    
    Aplica filtrado de región conexa mayoritaria para descartar artefactos exteriores.
    """
    if vtk is None:
        return Err("La biblioteca VTK no está disponible en este entorno.")

    if imageData is None:
        return Err("Los datos de imagen volumétrica (vtkImageData) son nulos.")

    cfg = params or SurfaceExtractionParams()

    scalar_range = imageData.GetScalarRange()
    min_val, max_val = scalar_range[0], scalar_range[1]

    if max_val <= min_val:
        return Err("El rango dinámico de intensidades del volumen es nulo o inválido.")

    # Umbral adaptativo: nivel mínimo para separar tejido del fondo
    threshold_value = min_val + (max_val - min_val) * cfg.threshold_ratio

    try:
        # 1. Extracción de isosuperficie (Flying Edges para alto rendimiento)
        if hasattr(vtk, "vtkFlyingEdges3D"):
            iso_filter = vtk.vtkFlyingEdges3D()
        else:
            iso_filter = vtk.vtkMarchingCubes()

        iso_filter.SetInputData(imageData)
        iso_filter.SetValue(0, threshold_value)
        iso_filter.ComputeNormalsOff()
        iso_filter.ComputeGradientsOff()
        iso_filter.Update()

        current_polydata = iso_filter.GetOutput()
        if current_polydata.GetNumberOfPoints() == 0:
            return Err("No se generaron puntos en la isosuperficie. Ajuste el umbral de extracción.")

        # 2. Transformar vértices de índices IJK a espacio de paciente RAS
        vtk_mat = vtk.vtkMatrix4x4()
        for r in range(4):
            for c in range(4):
                vtk_mat.SetElement(r, c, float(ijk_to_ras_matrix[r][c]))

        trans = vtk.vtkTransform()
        trans.SetMatrix(vtk_mat)

        trans_filter = vtk.vtkTransformPolyDataFilter()
        trans_filter.SetInputData(current_polydata)
        trans_filter.SetTransform(trans)
        trans_filter.Update()
        current_polydata = trans_filter.GetOutput()

        # 3. Filtrar conectividad para aislar la cabeza y descartar artefactos/camilla
        if cfg.extract_largest_component_only:
            conn_filter = vtk.vtkPolyDataConnectivityFilter()
            conn_filter.SetInputData(current_polydata)
            conn_filter.SetExtractionModeToLargestRegion()
            conn_filter.Update()
            current_polydata = conn_filter.GetOutput()

        # 4. Suavizado de superficie para eliminar artefactos de voxelización
        if cfg.smoothing_iterations > 0:
            smoother = vtk.vtkWindowedSincPolyDataFilter()
            smoother.SetInputData(current_polydata)
            smoother.SetNumberOfIterations(cfg.smoothing_iterations)
            smoother.SetPassBand(cfg.pass_band)
            smoother.NonManifoldSmoothingOn()
            smoother.NormalizeCoordinatesOn()
            smoother.Update()
            current_polydata = smoother.GetOutput()

        # 5. Cálculo y orientación consistente de normales exteriores
        norm_filter = vtk.vtkPolyDataNormals()
        norm_filter.SetInputData(current_polydata)
        norm_filter.ComputePointNormalsOn()
        norm_filter.ComputeCellNormalsOff()
        norm_filter.AutoOrientNormalsOn()
        norm_filter.ConsistencyOn()
        norm_filter.SplittingOff()
        norm_filter.Update()
        final_polydata = norm_filter.GetOutput()

        resultado: Result[Any] = Ok(final_polydata)
    except Exception as exc:
        resultado = Err(f"Fallo durante la extracción de isosuperficie VTK: {exc}")

    return resultado
