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
from typing import List, Sequence, Tuple

import numpy as np

from .result import Err, Ok, Result

Point3D = Tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class VolumeMetadata:
    """Metadatos clínicos y espaciales extraídos de un volumen MRI (vtkMRMLScalarVolumeNode)."""
    dimensions: Tuple[int, int, int]
    spacing_mm: Point3D
    voxel_volume_mm3: float
    is_stereotaxy_optimal: bool
    quality_notes: str


@dataclass(slots=True, frozen=True)
class TargetStructure:
    """Estructura anatómica diana cerebral procesada a partir de segmentación clínica."""
    segment_id: str
    name: str
    centroid_ras: Point3D
    contained_point_ras: Point3D
    volume_mm3: float
    voxel_count: int
    is_centroid_inside_mask: bool
    bounding_box_ras: Tuple[Point3D, Point3D]


def validate_volume_metadata(
    dimensions: Sequence[int],
    spacing_mm: Sequence[float],
    max_optimal_spacing: float = 1.5,
) -> Result[VolumeMetadata]:
    """
    Evalúa la resolución espacial y calibración de un volumen MRI cerebral para estereotaxia SEEG.
    
    Aplica Guard Clauses estrictas y un único flujo de salida.
    """
    if len(dimensions) != 3 or any(d <= 0 for d in dimensions):
        return Err("Las dimensiones del volumen MRI deben ser 3 enteros estrictamente positivos.")

    if len(spacing_mm) != 3 or any(not math.isfinite(s) or s <= 0.0 for s in spacing_mm):
        return Err("El espaciado de vóxeles (spacing) debe contener 3 valores numéricos positivos finitos.")

    dim_tuple: Tuple[int, int, int] = (int(dimensions[0]), int(dimensions[1]), int(dimensions[2]))
    spc_tuple: Point3D = (float(spacing_mm[0]), float(spacing_mm[1]), float(spacing_mm[2]))

    vox_volume = spc_tuple[0] * spc_tuple[1] * spc_tuple[2]

    # Criterio estereotáctico: para guiar electrodos intracraneales milimétricos,
    # el espaciado en cualquier eje no debe superar típicamente 1.5 mm.
    max_axis_spacing = max(spc_tuple)
    is_optimal = max_axis_spacing <= max_optimal_spacing

    if is_optimal:
        quality_msg = (
            f"Resolución óptima para estereotaxia (espaciado máx: {max_axis_spacing:.2f} mm)."
        )
    else:
        quality_msg = (
            f"Alerta: Espaciado anisotrópico o grueso ({max_axis_spacing:.2f} mm > {max_optimal_spacing:.2f} mm). "
            "Podría reducirse la precisión del blanco anatómico."
        )

    metadata = VolumeMetadata(
        dimensions=dim_tuple,
        spacing_mm=spc_tuple,
        voxel_volume_mm3=round(vox_volume, 3),
        is_stereotaxy_optimal=is_optimal,
        quality_notes=quality_msg,
    )

    resultado: Result[VolumeMetadata] = Ok(metadata)
    return resultado


def compute_segment_target(
    segment_id: str,
    segment_name: str,
    binary_mask: np.ndarray,
    ijk_to_ras_matrix: Sequence[Sequence[float]] | np.ndarray,
) -> Result[TargetStructure]:
    """
    Calcula el centroide analítico tridimensional ponderado en espacio RAS de una estructura diana.
    
    Verifica si el centroide geométrico cae dentro del parénquima de la diana.
    Si la morfología es no convexa y el centroide cae fuera, localiza el vóxel
    interno más cercano para garantizar un punto de abordaje seguro.
    """
    if binary_mask is None or binary_mask.ndim != 3:
        return Err(f"La máscara binaria del segmento '{segment_name}' debe ser una matriz tridimensional.")

    # Convertir matriz de transformación homogénea 4x4
    mat = np.array(ijk_to_ras_matrix, dtype=np.float64)
    if mat.shape != (4, 4):
        return Err("La matriz IJK to RAS debe tener dimensiones homogéneas 4x4.")

    active_indices = np.argwhere(binary_mask > 0)
    voxel_count = int(active_indices.shape[0])

    if voxel_count == 0:
        return Err(f"El segmento diana '{segment_name}' está vacío (0 vóxeles activos).")

    # Centro de masa en índices continuos IJK
    # active_indices devuelve filas [k, j, i] según orden estándar de numpy (z, y, x)
    mean_k = float(np.mean(active_indices[:, 0]))
    mean_j = float(np.mean(active_indices[:, 1]))
    mean_i = float(np.mean(active_indices[:, 2]))

    # Índices IJK continuos: (i, j, k) -> (x, y, z)
    ijk_centroid = np.array([mean_i, mean_j, mean_k, 1.0], dtype=np.float64)
    ras_centroid_vec = mat @ ijk_centroid
    centroid_ras: Point3D = (
        round(float(ras_centroid_vec[0]), 2),
        round(float(ras_centroid_vec[1]), 2),
        round(float(ras_centroid_vec[2]), 2),
    )

    # Comprobar si el vóxel entero más próximo al centroide está contenido en la máscara
    nearest_k = int(round(mean_k))
    nearest_j = int(round(mean_j))
    nearest_i = int(round(mean_i))

    # Clamping de límites
    shape = binary_mask.shape
    nearest_k = min(shape[0] - 1, max(0, nearest_k))
    nearest_j = min(shape[1] - 1, max(0, nearest_j))
    nearest_i = min(shape[2] - 1, max(0, nearest_i))

    is_inside = bool(binary_mask[nearest_k, nearest_j, nearest_i] > 0)

    if is_inside:
        contained_ras = centroid_ras
    else:
        # En estructuras no convexas (ej. cola del hipocampo o corteza temporal en C),
        # proyectar al vóxel activo más cercano al centroide para evitar caer en ventrículo
        diffs = active_indices - np.array([mean_k, mean_j, mean_i])
        distances_sq = diffs[:, 0] ** 2 + diffs[:, 1] ** 2 + diffs[:, 2] ** 2
        min_idx = int(np.argmin(distances_sq))
        best_k, best_j, best_i = active_indices[min_idx]

        ijk_contained = np.array([float(best_i), float(best_j), float(best_k), 1.0], dtype=np.float64)
        ras_contained_vec = mat @ ijk_contained
        contained_ras = (
            round(float(ras_contained_vec[0]), 2),
            round(float(ras_contained_vec[1]), 2),
            round(float(ras_contained_vec[2]), 2),
        )

    # Cálculo de volumen en mm3
    # Extraer factores de escala de la matriz homogénea (norma euclídea de las primeras 3 columnas)
    col0_scale = float(np.linalg.norm(mat[:3, 0]))
    col1_scale = float(np.linalg.norm(mat[:3, 1]))
    col2_scale = float(np.linalg.norm(mat[:3, 2]))
    voxel_vol = col0_scale * col1_scale * col2_scale
    total_volume_mm3 = round(voxel_count * voxel_vol, 2)

    # Bounding box en espacio RAS
    min_k, min_j, min_i = np.min(active_indices, axis=0)
    max_k, max_j, max_i = np.max(active_indices, axis=0)
    ras_min = mat @ np.array([float(min_i), float(min_j), float(min_k), 1.0])
    ras_max = mat @ np.array([float(max_i), float(max_j), float(max_k), 1.0])

    bbox_min: Point3D = (round(float(ras_min[0]), 2), round(float(ras_min[1]), 2), round(float(ras_min[2]), 2))
    bbox_max: Point3D = (round(float(ras_max[0]), 2), round(float(ras_max[1]), 2), round(float(ras_max[2]), 2))

    structure = TargetStructure(
        segment_id=segment_id,
        name=segment_name,
        centroid_ras=centroid_ras,
        contained_point_ras=contained_ras,
        volume_mm3=total_volume_mm3,
        voxel_count=voxel_count,
        is_centroid_inside_mask=is_inside,
        bounding_box_ras=(bbox_min, bbox_max),
    )

    resultado: Result[TargetStructure] = Ok(structure)
    return resultado
