# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

from .eeg_1020_calculator import (
    CanonicalLandmarks,
    calculate_1020_points,
    project_points_to_surface_mesh,
)
from .igtlink_exporter import (
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
    transmit_openigtlink_trajectories,
)
from .result import Err, Ok, Result
from .skull_surface_extractor import (
    SurfaceExtractionParams,
    extract_head_surface_polydata,
    get_surface_normal_at_point,
)
from .target_manager import (
    TargetStructure,
    VolumeMetadata,
    compute_segment_target,
    validate_volume_metadata,
)
from .trajectory_planner import (
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

__all__ = [
    "Result",
    "Ok",
    "Err",
    "CanonicalLandmarks",
    "calculate_1020_points",
    "project_points_to_surface_mesh",
    "ElectrodeConfig",
    "ContactPoint",
    "TrajectoryConflict",
    "TrajectoryMetrics",
    "calculate_trajectory",
    "calculate_electrode_contacts",
    "point_to_segment_distance",
    "compute_segment_to_segment_distance",
    "check_trajectory_conflicts",
    "generate_electrode_tube_polydata",
    "VolumeMetadata",
    "TargetStructure",
    "validate_volume_metadata",
    "compute_segment_target",
    "SurfaceExtractionParams",
    "extract_head_surface_polydata",
    "get_surface_normal_at_point",
    "build_trajectory_transform_matrix",
    "format_trajectories_payload",
    "export_trajectories_to_json_file",
    "export_trajectories_to_csv_file",
    "export_trajectories_to_slicer_markups_json",
    "calculate_crc64",
    "transform_point_to_frame",
    "pack_openigtlink_header",
    "pack_transform_message",
    "pack_point_message",
    "transmit_openigtlink_trajectories",
]
