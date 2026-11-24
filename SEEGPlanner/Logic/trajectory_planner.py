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
from typing import Any, List, Sequence, Tuple

import numpy as np

try:
    import vtk
except ImportError:
    vtk = None

from .result import Err, Ok, Result

Point3D = Tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class ElectrodeConfig:
    """Configuración geométrica y especificaciones clínicas del electrodo SEEG y perno guía."""
    diameter_mm: float = 0.8               # Diámetro nominal del electrodo (calibre típico 0.8 mm)
    num_contacts: int = 10                 # Número de anillos de registro (típico: 5 a 18)
    contact_length_mm: float = 2.0         # Longitud activa de cada contacto metálico (mm)
    contact_spacing_mm: float = 1.5        # Espaciado aislante entre contactos consecutivos (mm)
    tip_to_first_contact_mm: float = 1.0   # Distancia distal desde la punta diana al primer contacto
    bolt_outer_diameter_mm: float = 2.5    # Diámetro externo del perno de anclaje craneal (mm)
    bolt_length_mm: float = 15.0           # Longitud del perno guía en el anclaje óseo (mm)

    @property
    def radius_mm(self) -> float:
        """Radio nominal del electrodo en mm."""
        return self.diameter_mm / 2.0

    @property
    def bolt_radius_mm(self) -> float:
        """Radio externo del perno guía de inserción en mm."""
        return self.bolt_outer_diameter_mm / 2.0


@dataclass(slots=True, frozen=True)
class ContactPoint:
    """Punto de registro electrofisiológico milimétrico sobre el eje del electrodo."""
    index: int                             # Índice del contacto (1 = más profundo / diana)
    label: str                             # Etiqueta clínica (ej. 'E01', 'E02')
    position_ras: Point3D                  # Coordenadas espaciales 3D en espacio RAS
    distance_from_tip_mm: float            # Distancia euclídea desde la punta distal (mm)


@dataclass(slots=True, frozen=True)
class TrajectoryConflict:
    """Conflicto geométrico de proximidad o colisión entre dos trayectorias planificadas."""
    electrode_a: str                       # Nombre de la primera trayectoria
    electrode_b: str                       # Nombre de la segunda trayectoria
    conflict_type: str                     # 'SKULL_ENTRY_COLLISION' o 'INTRACRANIAL_PROXIMITY'
    min_distance_mm: float                 # Distancia euclídea mínima detectada (mm)
    is_critical: bool                      # Verdadero si la colisión es inaceptable quirúrgicamente
    description: str                       # Mensaje clínico descriptivo


@dataclass(slots=True, frozen=True)
class TrajectoryMetrics:
    """Métricas estereotácticas y de seguridad de una trayectoria SEEG calculada."""
    name: str
    entry_point: Point3D
    target_point: Point3D
    length_mm: float
    director_vector: Point3D
    angle_degrees: float | None
    is_safe: bool
    status_message: str
    contacts: Tuple[ContactPoint, ...] = ()
    config: ElectrodeConfig | None = None


def _validate_coords(point: Point3D, name: str) -> str | None:
    """Valida que un punto 3D posea valores reales finitos."""
    err: str | None = None
    if len(point) != 3:
        err = f"El punto {name} debe contener exactamente 3 coordenadas (x, y, z)."
    elif not all(math.isfinite(val) for val in point):
        err = f"El punto {name} contiene valores numéricos inválidos o infinitos."
    return err


def calculate_electrode_contacts(
    entry_point: Point3D,
    target_point: Point3D,
    config: ElectrodeConfig | None = None,
) -> Result[Tuple[ContactPoint, ...]]:
    """
    Calcula analíticamente la distribución espacial de los contactos de registro electrofisiológico
    a lo largo del eje del electrodo, comenzando en la punta diana (contacto 1) hacia la entrada craneal.
    
    Aplica Guard Clauses defensivas y la regla de un solo return.
    """
    err_entry = _validate_coords(entry_point, "Entrada (Entry Point)")
    if err_entry is not None:
        return Err(err_entry)

    err_target = _validate_coords(target_point, "Diana (Target Point)")
    if err_target is not None:
        return Err(err_target)

    cfg = config or ElectrodeConfig()
    p_entry = np.array(entry_point, dtype=np.float64)
    p_target = np.array(target_point, dtype=np.float64)

    diff_vector = p_entry - p_target
    length = float(np.linalg.norm(diff_vector))

    if length < 5.0:
        return Err(f"Longitud de trayectoria insuficiente ({length:.2f} mm) para calcular contactos.")

    # Vector unitario director apuntando desde la diana (punta distal) hacia la entrada craneal
    u_vector = diff_vector / length

    contacts_list: List[ContactPoint] = []
    # Paso entre centros de contactos contiguos: longitud del contacto + espaciado aislante
    pitch = cfg.contact_length_mm + cfg.contact_spacing_mm

    for i in range(cfg.num_contacts):
        dist_from_tip = cfg.tip_to_first_contact_mm + (i * pitch) + (cfg.contact_length_mm / 2.0)
        if dist_from_tip > length:
            # Los contactos restantes quedarían extracraneales
            break

        contact_pos = p_target + u_vector * dist_from_tip
        pos_tuple: Point3D = (
            round(float(contact_pos[0]), 2),
            round(float(contact_pos[1]), 2),
            round(float(contact_pos[2]), 2),
        )
        c_point = ContactPoint(
            index=i + 1,
            label=f"E{i + 1:02d}",
            position_ras=pos_tuple,
            distance_from_tip_mm=round(dist_from_tip, 2),
        )
        contacts_list.append(c_point)

    resultado: Result[Tuple[ContactPoint, ...]] = Ok(tuple(contacts_list))
    return resultado


def point_to_segment_distance(
    point: Point3D | np.ndarray,
    seg_start: Point3D | np.ndarray,
    seg_end: Point3D | np.ndarray,
) -> float:
    """Calcula la distancia euclídea mínima entre un punto y un segmento 3D en el espacio."""
    pt = np.array(point, dtype=np.float64)
    p = np.array(seg_start, dtype=np.float64)
    q = np.array(seg_end, dtype=np.float64)
    v = q - p
    len_sq = float(np.dot(v, v))

    if len_sq < 1e-12:
        return float(np.linalg.norm(pt - p))

    t = max(0.0, min(1.0, float(np.dot(pt - p, v)) / len_sq))
    proj = p + t * v
    min_dist = float(np.linalg.norm(pt - proj))
    return min_dist


def compute_segment_to_segment_distance(
    p1: Point3D,
    q1: Point3D,
    p2: Point3D,
    q2: Point3D,
) -> float:
    """
    Calcula analíticamente la distancia euclídea mínima exacta entre dos segmentos finitos 3D:
    Segmento 1 [p1 -> q1] y Segmento 2 [p2 -> q2].
    
    Resuelve el sistema de distancias sin aproximaciones numéricas, tratando rigurosamente
    casos ortogonales, oblicuos, colineales y paralelos.
    """
    pt1, qt1, pt2, qt2 = (
        np.array(p1, dtype=np.float64),
        np.array(q1, dtype=np.float64),
        np.array(p2, dtype=np.float64),
        np.array(q2, dtype=np.float64),
    )
    d1 = qt1 - pt1
    d2 = qt2 - pt2
    r = pt1 - pt2
    a = float(np.dot(d1, d1))
    b = float(np.dot(d1, d2))
    c = float(np.dot(d2, d2))
    d = float(np.dot(d1, r))
    e = float(np.dot(d2, r))
    denom = a * c - b * b

    # Casos degenerados: uno o ambos segmentos son puntos singulares
    if a < 1e-12 and c < 1e-12:
        return float(np.linalg.norm(pt1 - pt2))
    if a < 1e-12:
        return point_to_segment_distance(pt1, pt2, qt2)
    if c < 1e-12:
        return point_to_segment_distance(pt2, pt1, qt1)

    # Caso paralelo o colineal: la distancia mínima es el mínimo de las 4 proyecciones de extremos
    if denom < 1e-12:
        min_parallel = min(
            point_to_segment_distance(pt1, pt2, qt2),
            point_to_segment_distance(qt1, pt2, qt2),
            point_to_segment_distance(pt2, pt1, qt1),
            point_to_segment_distance(qt2, pt1, qt1),
        )
        return min_parallel

    # Caso general no paralelo
    s = max(0.0, min(1.0, (b * e - c * d) / denom))
    t = (b * s + e) / c
    if t < 0.0:
        t = 0.0
        s = max(0.0, min(1.0, -d / a))
    elif t > 1.0:
        t = 1.0
        s = max(0.0, min(1.0, (b - d) / a))

    c1 = pt1 + s * d1
    c2 = pt2 + t * d2
    min_dist = float(np.linalg.norm(c1 - c2))
    return min_dist


def check_trajectory_conflicts(
    trajectories: Sequence[TrajectoryMetrics],
    min_entry_dist_mm: float = 10.0,
    min_intracranial_dist_mm: float = 3.0,
) -> Result[Tuple[TrajectoryConflict, ...]]:
    """
    Comprueba de forma exhaustiva los conflictos espaciales entre todos los pares únicos de electrodos:
    1. Conflicto en entrada craneal (pernos óseos a distancia < min_entry_dist_mm).
    2. Proximidad crítica o colisión intracraneal en 3D (< min_intracranial_dist_mm).
    
    Aplica Guard Clauses y un único return final.
    """
    if len(trajectories) < 2:
        resultado: Result[Tuple[TrajectoryConflict, ...]] = Ok(())
        return resultado

    conflicts: List[TrajectoryConflict] = []

    for i in range(len(trajectories)):
        for j in range(i + 1, len(trajectories)):
            traj_a = trajectories[i]
            traj_b = trajectories[j]

            # 1. Distancia euclídea entre puntos de inserción craneal
            p_entry_a = np.array(traj_a.entry_point, dtype=np.float64)
            p_entry_b = np.array(traj_b.entry_point, dtype=np.float64)
            entry_dist = float(np.linalg.norm(p_entry_a - p_entry_b))

            if entry_dist < min_entry_dist_mm:
                is_crit = entry_dist < 5.0
                desc = (
                    f"Colisión de pernos en cráneo entre '{traj_a.name}' y '{traj_b.name}': "
                    f"distancia de entrada ({entry_dist:.1f} mm) < umbral seguro ({min_entry_dist_mm:.1f} mm)."
                )
                conflicts.append(
                    TrajectoryConflict(
                        electrode_a=traj_a.name,
                        electrode_b=traj_b.name,
                        conflict_type="SKULL_ENTRY_COLLISION",
                        min_distance_mm=round(entry_dist, 2),
                        is_critical=is_crit,
                        description=desc,
                    )
                )

            # 2. Distancia euclídea mínima entre segmentos continuos 3D
            inter_dist = compute_segment_to_segment_distance(
                traj_a.entry_point,
                traj_a.target_point,
                traj_b.entry_point,
                traj_b.target_point,
            )

            if inter_dist < min_intracranial_dist_mm:
                is_crit = inter_dist < 1.5
                desc = (
                    f"Proximidad intracraneal excesiva entre '{traj_a.name}' y '{traj_b.name}': "
                    f"distancia mínima 3D ({inter_dist:.1f} mm) < umbral seguro ({min_intracranial_dist_mm:.1f} mm)."
                )
                conflicts.append(
                    TrajectoryConflict(
                        electrode_a=traj_a.name,
                        electrode_b=traj_b.name,
                        conflict_type="INTRACRANIAL_PROXIMITY",
                        min_distance_mm=round(inter_dist, 2),
                        is_critical=is_crit,
                        description=desc,
                    )
                )

    resultado = Ok(tuple(conflicts))
    return resultado


def generate_electrode_tube_polydata(
    entry_point: Point3D,
    target_point: Point3D,
    config: ElectrodeConfig | None = None,
    radial_resolution: int = 12,
) -> Result[Any]:
    """
    Genera una malla poligonal 3D (vtkPolyData) unificada que contiene:
    1. El tubo cilíndrico del electrodo con su calibre nominal exacto (ej. 0.8 mm de diámetro).
    2. El collarín cilíndrico del perno guía en el punto de inserción craneal.
    
    Aplica Guard Clauses y la regla de un solo return final.
    """
    if vtk is None:
        return Err("La biblioteca VTK no está disponible en este entorno.")

    err_entry = _validate_coords(entry_point, "Entrada (Entry Point)")
    if err_entry is not None:
        return Err(err_entry)

    err_target = _validate_coords(target_point, "Diana (Target Point)")
    if err_target is not None:
        return Err(err_target)

    cfg = config or ElectrodeConfig()
    p_entry = np.array(entry_point, dtype=np.float64)
    p_target = np.array(target_point, dtype=np.float64)

    diff = p_target - p_entry
    length = float(np.linalg.norm(diff))

    if length < 5.0:
        return Err(f"Longitud de trayectoria insuficiente ({length:.2f} mm) para generar modelo tubular.")

    try:
        # 1. Malla tubular del electrodo desde entrada hasta diana
        line_electrode = vtk.vtkLineSource()
        line_electrode.SetPoint1(list(entry_point))
        line_electrode.SetPoint2(list(target_point))
        line_electrode.Update()

        tube_electrode = vtk.vtkTubeFilter()
        tube_electrode.SetInputConnection(line_electrode.GetOutputPort())
        tube_electrode.SetRadius(cfg.radius_mm)
        tube_electrode.SetNumberOfSides(radial_resolution)
        tube_electrode.CappingOn()
        tube_electrode.Update()

        # 2. Malla cilíndrica del perno guía en el punto de entrada craneal
        u_dir = diff / length
        half_bolt = cfg.bolt_length_mm / 2.0
        bolt_start = p_entry - u_dir * half_bolt
        bolt_end = p_entry + u_dir * half_bolt

        line_bolt = vtk.vtkLineSource()
        line_bolt.SetPoint1(float(bolt_start[0]), float(bolt_start[1]), float(bolt_start[2]))
        line_bolt.SetPoint2(float(bolt_end[0]), float(bolt_end[1]), float(bolt_end[2]))
        line_bolt.Update()

        tube_bolt = vtk.vtkTubeFilter()
        tube_bolt.SetInputConnection(line_bolt.GetOutputPort())
        tube_bolt.SetRadius(cfg.bolt_radius_mm)
        tube_bolt.SetNumberOfSides(radial_resolution)
        tube_bolt.CappingOn()
        tube_bolt.Update()

        # 3. Fusión limpia de geometrías en un único vtkPolyData
        append_filter = vtk.vtkAppendPolyData()
        append_filter.AddInputData(tube_electrode.GetOutput())
        append_filter.AddInputData(tube_bolt.GetOutput())
        append_filter.Update()

        clean_filter = vtk.vtkCleanPolyData()
        clean_filter.SetInputConnection(append_filter.GetOutputPort())
        clean_filter.Update()

        norm_filter = vtk.vtkPolyDataNormals()
        norm_filter.SetInputConnection(clean_filter.GetOutputPort())
        norm_filter.ComputePointNormalsOn()
        norm_filter.ComputeCellNormalsOff()
        norm_filter.AutoOrientNormalsOn()
        norm_filter.ConsistencyOn()
        norm_filter.SplittingOff()
        norm_filter.Update()

        out_poly = norm_filter.GetOutput()
        resultado: Result[Any] = Ok(out_poly)
    except Exception as exc:
        resultado = Err(f"Error generando malla tubular de electrodo en VTK: {exc}")

    return resultado


def calculate_trajectory(
    entry_point: Point3D,
    target_point: Point3D,
    name: str = "SEEG_Trajectory",
    skull_normal: Point3D | None = None,
    max_safe_angle_deg: float = 30.0,
    config: ElectrodeConfig | None = None,
) -> Result[TrajectoryMetrics]:
    """
    Calcula los parámetros estereotácticos, distribución de contactos y seguridad biomecánica
    de una trayectoria SEEG.
    
    Verifica que la diana y entrada sean válidas, calcula la distancia euclídea (longitud),
    el vector director normalizado, el ángulo de incidencia respecto a la normal del cráneo
    y las coordenadas exactas de cada contacto electrofisiológico.
    Aplica Guard Clauses y un único return final.
    """
    # Guard clauses para validación de coordenadas
    err_entry = _validate_coords(entry_point, "Entrada (Entry Point)")
    if err_entry is not None:
        return Err(err_entry)

    err_target = _validate_coords(target_point, "Diana (Target Point)")
    if err_target is not None:
        return Err(err_target)

    cfg = config or ElectrodeConfig()
    p_entry = np.array(entry_point, dtype=np.float64)
    p_target = np.array(target_point, dtype=np.float64)

    diff_vector = p_target - p_entry
    length = float(np.linalg.norm(diff_vector))

    # Guard clause para longitud mínima clínica
    if length < 5.0:
        return Err(
            f"Longitud de trayectoria insuficiente ({length:.2f} mm). "
            "El punto de entrada y la diana están prácticamente superpuestos."
        )

    director_u = diff_vector / length
    director_tuple: Point3D = (
        float(director_u[0]),
        float(director_u[1]),
        float(director_u[2]),
    )

    angle_deg: float | None = None
    is_safe: bool = True
    status_msg: str = "Trayectoria válida."

    # Evaluación del ángulo respecto a la normal craneal si se suministra
    if skull_normal is not None:
        err_normal = _validate_coords(skull_normal, "Normal de Superficie Ósea")
        if err_normal is not None:
            return Err(err_normal)

        norm_arr = np.array(skull_normal, dtype=np.float64)
        norm_mag = float(np.linalg.norm(norm_arr))

        if norm_mag < 1e-6:
            return Err("El vector normal óseo suministrado tiene magnitud nula.")

        norm_u = norm_arr / norm_mag
        # La trayectoria penetra en el cráneo (vector de entrada a diana)
        # Evaluamos el ángulo respecto a la dirección de inserción
        cos_theta = abs(float(np.dot(norm_u, director_u)))
        cos_theta = min(1.0, max(0.0, cos_theta))
        # Ángulo de desviación respecto a la perpendicular (0 deg = perfectamente perpendicular)
        deviation_angle = math.degrees(math.acos(cos_theta))
        angle_deg = round(deviation_angle, 2)

        if angle_deg > max_safe_angle_deg:
            is_safe = False
            status_msg = (
                f"Alerta: Ángulo con normal ({angle_deg:.1f}°) excede el límite seguro "
                f"({max_safe_angle_deg:.1f}°). Riesgo de deslizamiento del perno óseo."
            )
        else:
            status_msg = f"Trayectoria segura (desviación ósea: {angle_deg:.1f}°)."

    # Cálculo analítico de contactos de registro
    contacts_res = calculate_electrode_contacts(entry_point, target_point, cfg)
    contacts_tuple: Tuple[ContactPoint, ...] = contacts_res.value if isinstance(contacts_res, Ok) else ()

    metrics = TrajectoryMetrics(
        name=name,
        entry_point=entry_point,
        target_point=target_point,
        length_mm=round(length, 2),
        director_vector=director_tuple,
        angle_degrees=angle_deg,
        is_safe=is_safe,
        status_message=status_msg,
        contacts=contacts_tuple,
        config=cfg,
    )

    resultado: Result[TrajectoryMetrics] = Ok(metrics)
    return resultado
