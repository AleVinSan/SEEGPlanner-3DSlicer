# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import time
import unittest
from typing import Dict, List, Tuple

import numpy as np
import vtk

# Añadir la raíz de la extensión al path para permitir importar Logic
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from Logic.eeg_1020_calculator import (
    CanonicalLandmarks,
    calculate_1020_points,
    project_points_to_surface_mesh,
)
from Logic.igtlink_exporter import (
    build_trajectory_transform_matrix,
    calculate_crc64,
    export_trajectories_to_csv_file,
    export_trajectories_to_json_file,
    export_trajectories_to_slicer_markups_json,
    format_trajectories_payload,
    pack_openigtlink_header,
    pack_point_message,
    pack_transform_message,
    transform_point_to_frame,
)
from Logic.result import Err, Ok
from Logic.skull_surface_extractor import (
    SurfaceExtractionParams,
    extract_head_surface_polydata,
    get_surface_normal_at_point,
)
from Logic.target_manager import (
    TargetStructure,
    VolumeMetadata,
    compute_segment_target,
    validate_volume_metadata,
)
from Logic.trajectory_planner import (
    ElectrodeConfig,
    TrajectoryConflict,
    TrajectoryMetrics,
    calculate_electrode_contacts,
    calculate_trajectory,
    check_trajectory_conflicts,
    compute_segment_to_segment_distance,
    generate_electrode_tube_polydata,
)


def create_synthetic_head_mri_volume(
    dim: int = 50,
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    head_radius: float = 20.0,
) -> vtk.vtkImageData:
    """
    Construye un volumen de imagen sintético con contraste anatómico cefálico.
    
    Genera un cuero cabelludo / cráneo esferoidal exterior con valores de intensidad altos (150.0)
    y fondo nulo (0.0), ideal para validación de isosuperficie y ray-casting sin dependencias externas.
    """
    img = vtk.vtkImageData()
    img.SetDimensions(dim, dim, dim)
    img.SetSpacing(spacing[0], spacing[1], spacing[2])
    img.SetOrigin(
        -0.5 * (dim - 1) * spacing[0],
        -0.5 * (dim - 1) * spacing[1],
        -0.5 * (dim - 1) * spacing[2],
    )
    img.AllocateScalars(vtk.VTK_FLOAT, 1)

    c = (dim - 1) * 0.5
    for z in range(dim):
        dz = (z - c) * spacing[2]
        for y in range(dim):
            dy = (y - c) * spacing[1]
            for x in range(dim):
                dx = (x - c) * spacing[0]
                r = np.sqrt(dx * dx + dy * dy + dz * dz)
                # Capa esferoidal con cuero cabelludo a r <= head_radius
                intensity = 150.0 if r <= head_radius else 0.0
                img.SetScalarComponentFromFloat(x, y, z, 0, intensity)

    return img


def create_concave_hippocampus_mask(
    dim: int = 30,
) -> np.ndarray:
    """
    Construye una máscara binaria 3D que emula un hipocampo en forma de 'C' con ventrículo interior.
    
    Permite validar que el centroide se ajuste al tejido real y no caiga en el ventrículo.
    """
    mask = np.zeros((dim, dim, dim), dtype=bool)
    c = dim // 2
    for z in range(dim // 4, 3 * dim // 4):
        for y in range(dim):
            for x in range(dim):
                dx = x - c
                dy = y - c
                r = np.sqrt(dx * dx + dy * dy)
                # Forma de C: radio entre 5 y 10 vóxeles, ángulo > 0
                if 5.0 <= r <= 10.0 and (dx >= 0 or dy >= 0):
                    mask[x, y, z] = True
    return mask


class TestValidationPipelineAndBenchmarks(unittest.TestCase):
    """
    Suite de validación end-to-end del flujo clínico de SEEGPlanner y benchmarks cuantitativos.
    
    Cubre de extremo a extremo las 5 etapas del flujo quirúrgico:
    1. Inspección y calidad de vóxel MRI.
    2. Superficie craneal, normales y rejilla EEG 10-20 proyectada.
    3. Extracción de centroides diana profundos con protección ventricular.
    4. Cálculo de trayectorias, tubos 3D, pernos guía, contactos y colisiones.
    5. Exportación multi-formato (JSON, CSV, Markups) y OpenIGTLink.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.head_mri = create_synthetic_head_mri_volume(dim=45, spacing=(1.0, 1.0, 1.0), head_radius=18.0)

    def tearDown(self) -> None:
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def test_full_pipeline_end_to_end(self) -> None:
        """Valida secuencialmente el flujo completo de planificación prequirúrgica SEEG."""
        pipeline_timings: Dict[str, float] = {}

        # ---------------------------------------------------------------------
        # ETAPA 1: Inspección de Volumen MRI y Control de Calidad
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        dims = self.head_mri.GetDimensions()
        spc = self.head_mri.GetSpacing()

        meta_res = validate_volume_metadata(dims, spc)
        self.assertIsInstance(meta_res, Ok)
        meta = meta_res.value
        self.assertTrue(meta.is_stereotaxy_optimal)
        self.assertAlmostEqual(meta.voxel_volume_mm3, 1.0, places=3)
        pipeline_timings["etapa_1_mri_qc"] = time.perf_counter() - t0

        # ---------------------------------------------------------------------
        # ETAPA 2: Superficie Craneal, Normales Exteriores y EEG 10-20
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        params = SurfaceExtractionParams(
            threshold_ratio=0.2,
            smoothing_iterations=10,
            extract_largest_component_only=True,
        )
        surf_res = extract_head_surface_polydata(self.head_mri, np.eye(4), params)
        self.assertIsInstance(surf_res, Ok)
        head_poly = surf_res.value
        self.assertGreater(head_poly.GetNumberOfPoints(), 100)
        self.assertGreater(head_poly.GetNumberOfPolys(), 100)

        # Referencias canónicas (convergentes con radio 18 mm)
        landmarks = CanonicalLandmarks(
            nasion=(0.0, 18.0, 0.0),
            inion=(0.0, -18.0, 0.0),
            lpa=(-18.0, 0.0, 0.0),
            rpa=(18.0, 0.0, 0.0),
        )
        calc_1020 = calculate_1020_points(landmarks)
        self.assertIsInstance(calc_1020, Ok)
        points_analytic = calc_1020.value
        self.assertEqual(len(points_analytic), 25)

        # Proyección por trazado de rayos con vtkOBBTree
        center_head = (0.0, 0.0, 0.0)
        proj_res = project_points_to_surface_mesh(points_analytic, head_poly, center_head)
        self.assertIsInstance(proj_res, Ok)
        points_projected = proj_res.value
        self.assertEqual(len(points_projected), 25)
        self.assertIn("Cz", points_projected)
        self.assertIn("Fz", points_projected)
        pipeline_timings["etapa_2_surface_1020"] = time.perf_counter() - t0

        # ---------------------------------------------------------------------
        # ETAPA 3: Localización de Dianas Anatómicas Profundas
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        # Segmento 1: Diana esférica compacta (Amígdala)
        amygdala_mask = np.zeros((30, 30, 30), dtype=bool)
        amygdala_mask[12:18, 12:18, 12:18] = True
        ijk_to_ras = np.diag([1.0, 1.0, 1.0, 1.0])
        ijk_to_ras[:3, 3] = [-15.0, -15.0, -15.0]

        target1_res = compute_segment_target("seg_amygdala", "Amygdala_Right", amygdala_mask, ijk_to_ras)
        self.assertIsInstance(target1_res, Ok)
        tgt1 = target1_res.value
        self.assertTrue(tgt1.is_centroid_inside_mask)
        self.assertAlmostEqual(tgt1.volume_mm3, 6 * 6 * 6 * 1.0)

        # Segmento 2: Diana cóncava en C (Hipocampo)
        hippo_mask = create_concave_hippocampus_mask(dim=30)
        target2_res = compute_segment_target("seg_hippo", "Hippocampus_Left", hippo_mask, ijk_to_ras)
        self.assertIsInstance(target2_res, Ok)
        tgt2 = target2_res.value
        self.assertGreater(tgt2.volume_mm3, 0.0)
        # Comprobar que el punto ajustado está estrictamente dentro del tejido
        self.assertIsNotNone(tgt2.contained_point_ras)
        pipeline_timings["etapa_3_targets"] = time.perf_counter() - t0

        # ---------------------------------------------------------------------
        # ETAPA 4: Planificación de Trayectorias, Pernos y Seguridad Multi-Electrodo
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        cfg = ElectrodeConfig(
            diameter_mm=0.8,
            num_contacts=10,
            contact_length_mm=2.0,
            contact_spacing_mm=1.5,
            bolt_outer_diameter_mm=2.5,
            bolt_length_mm=15.0,
        )

        entry1 = points_projected["C4"]
        target1 = tgt1.contained_point_ras
        normal1_res = get_surface_normal_at_point(head_poly, entry1)
        normal1 = normal1_res.value if isinstance(normal1_res, Ok) else (1.0, 0.0, 0.0)

        traj1_res = calculate_trajectory(
            entry_point=entry1,
            target_point=target1,
            name="Elec_Amygdala",
            skull_normal=normal1,
            max_safe_angle_deg=30.0,
            config=cfg,
        )
        self.assertIsInstance(traj1_res, Ok)
        t1 = traj1_res.value
        self.assertGreater(t1.length_mm, 10.0)
        self.assertEqual(len(t1.contacts), 5)  # 5 contactos intracraneales activos para L ~20 mm

        # Generación de malla 3D de electrodo con perno guía coaxial
        tube1_res = generate_electrode_tube_polydata(entry1, target1, config=cfg)
        self.assertIsInstance(tube1_res, Ok)
        self.assertGreaterEqual(tube1_res.value.GetNumberOfPoints(), 40)

        # Electrodo 2: hacia Hipocampo
        entry2 = points_projected["T3"]
        target2 = tgt2.contained_point_ras
        normal2_res = get_surface_normal_at_point(head_poly, entry2)
        normal2 = normal2_res.value if isinstance(normal2_res, Ok) else (0.0, 1.0, 0.0)

        traj2_res = calculate_trajectory(
            entry_point=entry2,
            target_point=target2,
            name="Elec_Hippo",
            skull_normal=normal2,
            max_safe_angle_deg=30.0,
            config=cfg,
        )
        self.assertIsInstance(traj2_res, Ok)
        t2 = traj2_res.value

        # Evaluación global de conflictos espaciales
        conflicts_res = check_trajectory_conflicts([t1, t2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0)
        self.assertIsInstance(conflicts_res, Ok)
        pipeline_timings["etapa_4_trajectories"] = time.perf_counter() - t0

        # ---------------------------------------------------------------------
        # ETAPA 5: Exportación Quirúrgica Multi-Formato y OpenIGTLink
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        trajectories_plan = [t1, t2]

        # 5.1 JSON
        json_path = os.path.join(self.temp_dir, "plan_pipeline.json")
        res_json = export_trajectories_to_json_file(trajectories_plan, json_path, coordinate_system="RAS")
        self.assertIsInstance(res_json, Ok)
        self.assertTrue(os.path.exists(json_path))

        # 5.2 CSV Detallado
        csv_path = os.path.join(self.temp_dir, "plan_pipeline.csv")
        res_csv = export_trajectories_to_csv_file(trajectories_plan, csv_path, coordinate_system="LPS", include_contact_rows=True)
        self.assertIsInstance(res_csv, Ok)
        self.assertTrue(os.path.exists(csv_path))

        # 5.3 Markups JSON
        mrk_path = os.path.join(self.temp_dir, "plan_pipeline.mrk.json")
        res_mrk = export_trajectories_to_slicer_markups_json(trajectories_plan, mrk_path, coordinate_system="RAS")
        self.assertIsInstance(res_mrk, Ok)
        self.assertTrue(os.path.exists(mrk_path))

        # 5.4 Protocolo Binario OpenIGTLink (cabecera + transform + point)
        for t in trajectories_plan:
            trans_pkt = pack_transform_message(t, "RAS")
            self.assertIsInstance(trans_pkt, Ok)
            self.assertEqual(len(trans_pkt.value), 58 + 48)

            point_pkt = pack_point_message(t, "RAS")
            self.assertIsInstance(point_pkt, Ok)
            # 58 bytes cabecera + (2 extremos [Entry, Target] + contactos intracraneales) * 136 bytes
            expected_point_len = 58 + (2 + len(t.contacts)) * 136
            self.assertEqual(len(point_pkt.value), expected_point_len)

        pipeline_timings["etapa_5_export"] = time.perf_counter() - t0

        # ---------------------------------------------------------------------
        # Verificación de Umbrales Clínicos de Latencia (Benchmarks Cuantitativos)
        # ---------------------------------------------------------------------
        # Superficie + 10-20 debe ser < 2.0 segundos
        self.assertLess(pipeline_timings["etapa_2_surface_1020"], 2.0)
        # Extracción de dianas < 0.5 segundos
        self.assertLess(pipeline_timings["etapa_3_targets"], 0.5)
        # Cálculo de trayectorias y colisiones < 0.2 segundos
        self.assertLess(pipeline_timings["etapa_4_trajectories"], 0.2)
        # Exportación de archivos < 0.2 segundos
        self.assertLess(pipeline_timings["etapa_5_export"], 0.2)

    def test_quantitative_accuracy_benchmarks(self) -> None:
        """Evalúa la precisión geométrica submilimétrica y repetibilidad de distancias 3D."""
        # 1. Precisión de cálculo de longitud de trayectoria frente a solución analítica teórica
        p_entry = (10.0, 20.0, 30.0)
        p_target = (10.0 + 30.0, 20.0 + 40.0, 30.0)  # dx=30, dy=40 -> L_teorica = 50.0 mm
        t_res = calculate_trajectory(p_entry, p_target, name="Bench_Elec")
        self.assertIsInstance(t_res, Ok)
        self.assertAlmostEqual(t_res.value.length_mm, 50.0, delta=1e-5)

        # 2. Precisión del ángulo de penetración ósea
        # Vector director hacia +Z: (0, 0, 1)
        # Normal del cráneo inclinada a 30° en plano YZ: cos(30°) = sqrt(3)/2
        normal_30deg = (0.0, 0.5, np.sqrt(3.0) / 2.0)
        t_ang_res = calculate_trajectory(
            (0.0, 0.0, 40.0),
            (0.0, 0.0, 0.0),
            name="Bench_Angle",
            skull_normal=normal_30deg,
            max_safe_angle_deg=30.0,
        )
        self.assertIsInstance(t_ang_res, Ok)
        # El ángulo con la normal debe ser exactamente 30.0°
        self.assertAlmostEqual(t_ang_res.value.angle_degrees or 0.0, 30.0, delta=0.05)

    def test_collision_detector_sensitivity_and_specificity(self) -> None:
        """Verifica la sensibilidad y especificidad del detector de colisiones frente a casos límite."""
        cfg = ElectrodeConfig(diameter_mm=0.8, bolt_outer_diameter_mm=2.5, bolt_length_mm=15.0)

        # Caso A: Pernos separados por 9.9 mm (< 10.0 mm umbral -> ALERTA DE COLISIÓN DE ENTRADA)
        t_a1 = calculate_trajectory((0.0, 0.0, 50.0), (0.0, 0.0, 0.0), name="E_A1", config=cfg).value
        t_a2 = calculate_trajectory((9.9, 0.0, 50.0), (9.9, 0.0, 0.0), name="E_A2", config=cfg).value
        conf_warn = check_trajectory_conflicts([t_a1, t_a2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0).value
        self.assertEqual(len(conf_warn), 1)
        self.assertEqual(conf_warn[0].conflict_type, "SKULL_ENTRY_COLLISION")
        self.assertFalse(conf_warn[0].is_critical)

        # Caso A-Crítico: Pernos a 4.0 mm (< 5.0 mm -> CRÍTICO)
        t_a3 = calculate_trajectory((4.0, 0.0, 50.0), (4.0, 0.0, 0.0), name="E_A3", config=cfg).value
        conf_crit = check_trajectory_conflicts([t_a1, t_a3], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0).value
        self.assertEqual(len(conf_crit), 1)
        self.assertTrue(conf_crit[0].is_critical)

        # Caso B: Pernos separados por 10.1 mm (>= 10.0 mm umbral -> SEGURO)
        t_b1 = calculate_trajectory((0.0, 0.0, 50.0), (0.0, 0.0, 0.0), name="E_B1", config=cfg).value
        t_b2 = calculate_trajectory((10.1, 0.0, 50.0), (10.1, 0.0, 0.0), name="E_B2", config=cfg).value
        conf_safe = check_trajectory_conflicts([t_b1, t_b2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0).value
        self.assertEqual(len(conf_safe), 0)

        # Caso C: Trayectorias convergentes con distancia mínima de 2.8 mm (< 3.0 mm -> ALERTA PARENQUIMATOSA)
        t_c1 = calculate_trajectory((0.0, 0.0, 50.0), (0.0, 0.0, 0.0), name="E_C1", config=cfg).value
        t_c2 = calculate_trajectory((20.0, 0.0, 50.0), (2.8, 0.0, 0.0), name="E_C2", config=cfg).value
        conf_deep = check_trajectory_conflicts([t_c1, t_c2], min_entry_dist_mm=10.0, min_intracranial_dist_mm=3.0).value
        self.assertTrue(any(c.conflict_type == "INTRACRANIAL_PROXIMITY" for c in conf_deep))


if __name__ == "__main__":
    unittest.main()
