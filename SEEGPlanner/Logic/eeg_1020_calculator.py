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
from typing import Any, Dict, Tuple

import numpy as np

try:
    import vtk
except ImportError:
    vtk = None

from .result import Err, Ok, Result

Point3D = Tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class CanonicalLandmarks:
    """Coordenadas tridimensionales de los 4 fiduciales anatómicos básicos en espacio RAS."""
    nasion: Point3D
    inion: Point3D
    lpa: Point3D
    rpa: Point3D


def _validate_point(pt: Point3D, name: str) -> str | None:
    """Valida que un punto contenga 3 componentes numéricas finitas."""
    validation_error: str | None = None
    if len(pt) != 3:
        validation_error = f"El fiducial {name} debe contener exactamente 3 coordenadas (RAS)."
    elif not all(math.isfinite(coord) for coord in pt):
        validation_error = f"El fiducial {name} contiene valores numéricos no válidos o infinitos."
    return validation_error


def _arc_interpolation(
    start: np.ndarray,
    end: np.ndarray,
    center: np.ndarray,
    fraction: float,
) -> np.ndarray:
    """Interpola sobre el arco angular definido por start y end respecto a un centro común."""
    v_start = start - center
    v_end = end - center
    r_start = float(np.linalg.norm(v_start))
    r_end = float(np.linalg.norm(v_end))
    radius = (1.0 - fraction) * r_start + fraction * r_end

    u_start = v_start / (r_start + 1e-12)
    u_end = v_end / (r_end + 1e-12)

    dot = float(np.clip(np.dot(u_start, u_end), -1.0, 1.0))
    omega = math.acos(dot)

    if omega < 1e-6:
        interpolated = center + v_start
    else:
        sin_omega = math.sin(omega)
        u_interp = (
            math.sin((1.0 - fraction) * omega) / sin_omega * u_start
            + math.sin(fraction * omega) / sin_omega * u_end
        )
        u_interp = u_interp / (float(np.linalg.norm(u_interp)) + 1e-12)
        interpolated = center + radius * u_interp

    return interpolated


def calculate_1020_points(landmarks: CanonicalLandmarks) -> Result[Dict[str, Point3D]]:
    """
    Calcula las posiciones espaciales 3D del sistema EEG 10-20 estándar a partir de los 4 fiduciales canónicos.
    
    Aplica la regla de un solo return y Guard Clauses defensivas.
    """
    # Guard clauses para validación de puntos anatómicos
    for pt, name in [
        (landmarks.nasion, "Nasion"),
        (landmarks.inion, "Inion"),
        (landmarks.lpa, "LPA"),
        (landmarks.rpa, "RPA"),
    ]:
        err_msg = _validate_point(pt, name)
        if err_msg is not None:
            return Err(err_msg)

    p_nz = np.array(landmarks.nasion, dtype=np.float64)
    p_iz = np.array(landmarks.inion, dtype=np.float64)
    p_lpa = np.array(landmarks.lpa, dtype=np.float64)
    p_rpa = np.array(landmarks.rpa, dtype=np.float64)

    # Validar distancias mínimas para evitar geometrías degeneradas
    dist_sagittal = float(np.linalg.norm(p_iz - p_nz))
    dist_coronal = float(np.linalg.norm(p_rpa - p_lpa))
    if dist_sagittal < 20.0 or dist_coronal < 20.0:
        return Err(
            "Distancia insuficiente entre fiduciales anatómicos de referencia.",
            f"Sagital: {dist_sagittal:.1f} mm, Coronal: {dist_coronal:.1f} mm.",
        )

    # Centro geométrico de la cabeza para el modelo esférico/elipsoidal
    mid_sagittal = (p_nz + p_iz) * 0.5
    mid_coronal = (p_lpa + p_rpa) * 0.5
    center = (mid_sagittal + mid_coronal) * 0.5

    # 1. Línea Sagital (Nasion -> Inion)
    # Fpz (10%), Fz (30%), Cz (50%), Pz (70%), Oz (90%)
    p_fpz = _arc_interpolation(p_nz, p_iz, center, 0.10)
    p_fz = _arc_interpolation(p_nz, p_iz, center, 0.30)
    p_cz_sag = _arc_interpolation(p_nz, p_iz, center, 0.50)
    p_pz = _arc_interpolation(p_nz, p_iz, center, 0.70)
    p_oz = _arc_interpolation(p_nz, p_iz, center, 0.90)

    # 2. Línea Coronal (LPA -> Cz -> RPA)
    # T3/T7 (10%), C3 (30%), Cz (50%), C4 (70%), T4/T8 (90%)
    p_t3 = _arc_interpolation(p_lpa, p_cz_sag, center, 0.20)
    p_c3 = _arc_interpolation(p_lpa, p_cz_sag, center, 0.60)
    p_c4 = _arc_interpolation(p_rpa, p_cz_sag, center, 0.60)
    p_t4 = _arc_interpolation(p_rpa, p_cz_sag, center, 0.20)

    # 3. Arco Circunferencial anterior (Fpz -> T3 / T4)
    # Fp1 (50% entre Fpz y T3 sobre el plano horizontal), Fp2, F7, F8
    p_fp1 = _arc_interpolation(p_fpz, p_t3, center, 0.25)
    p_f7 = _arc_interpolation(p_fpz, p_t3, center, 0.50)
    p_fp2 = _arc_interpolation(p_fpz, p_t4, center, 0.25)
    p_f8 = _arc_interpolation(p_fpz, p_t4, center, 0.50)

    # 4. Arco Circunferencial posterior (Oz -> T3 / T4)
    # O1, O2, T5/P7, T6/P8
    p_o1 = _arc_interpolation(p_oz, p_t3, center, 0.25)
    p_t5 = _arc_interpolation(p_oz, p_t3, center, 0.50)
    p_o2 = _arc_interpolation(p_oz, p_t4, center, 0.25)
    p_t6 = _arc_interpolation(p_oz, p_t4, center, 0.50)

    # 5. Puntos intermedios (F3, F4, P3, P4)
    p_f3 = _arc_interpolation(p_f7, p_fz, center, 0.50)
    p_f4 = _arc_interpolation(p_f8, p_fz, center, 0.50)
    p_p3 = _arc_interpolation(p_t5, p_pz, center, 0.50)
    p_p4 = _arc_interpolation(p_t6, p_pz, center, 0.50)

    def _to_tuple(arr: np.ndarray) -> Point3D:
        return (float(arr[0]), float(arr[1]), float(arr[2]))

    eeg_points: Dict[str, Point3D] = {
        "Nz": landmarks.nasion,
        "Iz": landmarks.inion,
        "LPA": landmarks.lpa,
        "RPA": landmarks.rpa,
        "Fpz": _to_tuple(p_fpz),
        "Fz": _to_tuple(p_fz),
        "Cz": _to_tuple(p_cz_sag),
        "Pz": _to_tuple(p_pz),
        "Oz": _to_tuple(p_oz),
        "T3": _to_tuple(p_t3),
        "C3": _to_tuple(p_c3),
        "C4": _to_tuple(p_c4),
        "T4": _to_tuple(p_t4),
        "Fp1": _to_tuple(p_fp1),
        "F7": _to_tuple(p_f7),
        "Fp2": _to_tuple(p_fp2),
        "F8": _to_tuple(p_f8),
        "O1": _to_tuple(p_o1),
        "T5": _to_tuple(p_t5),
        "O2": _to_tuple(p_o2),
        "T6": _to_tuple(p_t6),
        "F3": _to_tuple(p_f3),
        "F4": _to_tuple(p_f4),
        "P3": _to_tuple(p_p3),
        "P4": _to_tuple(p_p4),
    }

    resultado: Result[Dict[str, Point3D]] = Ok(eeg_points)
    return resultado


def project_points_to_surface_mesh(
    points_dict: Dict[str, Point3D],
    head_polydata: Any,
    head_center_ras: Point3D,
    max_search_factor: float = 3.0,
) -> Result[Dict[str, Point3D]]:
    """
    Proyecta los puntos del sistema 10-20 sobre la superficie real de la cabeza (vtkPolyData)
    mediante trazado de rayos (ray-casting) desde el centro geométrico de la cabeza.
    
    Si algún rayo no intersecta o VTK no está disponible, conserva el punto analítico esférico.
    Cumple con el estándar de un solo return y Guard Clauses defensivas.
    """
    if not points_dict:
        return Err("El diccionario de puntos 10-20 a proyectar está vacío.")

    if head_polydata is None or vtk is None:
        # Fallback suave si no se proporciona superficie o no hay VTK
        resultado: Result[Dict[str, Point3D]] = Ok(dict(points_dict))
        return resultado

    if head_polydata.GetNumberOfPoints() == 0:
        return Err("La malla de superficie de la cabeza no contiene vértices.")

    try:
        # Construir árbol acelerador OBBTree para intersección rápida de rayos con polígonos
        obb_tree = vtk.vtkOBBTree()
        obb_tree.SetDataSet(head_polydata)
        obb_tree.BuildLocator()

        c_arr = np.array(head_center_ras, dtype=np.float64)
        projected_points: Dict[str, Point3D] = {}

        for name, pt in points_dict.items():
            p_arr = np.array(pt, dtype=np.float64)
            diff = p_arr - c_arr
            dist = float(np.linalg.norm(diff))

            if dist < 1e-4:
                projected_points[name] = pt
                continue

            direction = diff / dist
            p_start = c_arr
            p_end = c_arr + direction * (dist * max_search_factor)

            intersect_pts = vtk.vtkPoints()
            code = obb_tree.IntersectWithLine(list(p_start), list(p_end), intersect_pts, None)

            if intersect_pts.GetNumberOfPoints() > 0:
                # Encontrar el punto de corte más cercano a la estimación analítica
                best_point = pt
                min_delta = float("inf")
                for i in range(intersect_pts.GetNumberOfPoints()):
                    cand = intersect_pts.GetPoint(i)
                    cand_delta = math.dist(cand, pt)
                    if cand_delta < min_delta:
                        min_delta = cand_delta
                        best_point = (round(cand[0], 2), round(cand[1], 2), round(cand[2], 2))
                projected_points[name] = best_point
            else:
                # Fallback analítico si el rayo no cruza la malla
                projected_points[name] = pt

        resultado = Ok(projected_points)
    except Exception as exc:
        resultado = Err(f"Fallo durante la proyección por trazado de rayos: {exc}")

    return resultado
