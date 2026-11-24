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
import socket
import struct
import time
from dataclasses import asdict
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from .result import Err, Ok, Result
from .trajectory_planner import ContactPoint, TrajectoryMetrics

# Tabla precalculada para CRC-64 ECMA-182 (polinomio 0x42F0E1EBA9EA3693, no invertido)
_CRC64_POLY = 0x42F0E1EBA9EA3693


def _build_crc64_table() -> List[int]:
    """Genera la tabla de búsqueda para cálculo rápido de CRC-64 ECMA-182."""
    table: List[int] = []
    for i in range(256):
        curr = i << 56
        for _ in range(8):
            if curr & 0x8000000000000000:
                curr = ((curr << 1) ^ _CRC64_POLY) & 0xFFFFFFFFFFFFFFFF
            else:
                curr = (curr << 1) & 0xFFFFFFFFFFFFFFFF
        table.append(curr)
    return table


_CRC64_TABLE: List[int] = _build_crc64_table()


def calculate_crc64(data: bytes, initial_crc: int = 0) -> int:
    """Calcula el checksum CRC-64 según el estándar ECMA-182 requerido por OpenIGTLink."""
    crc = initial_crc & 0xFFFFFFFFFFFFFFFF
    for byte in data:
        idx = ((crc >> 56) ^ byte) & 0xFF
        crc = (_CRC64_TABLE[idx] ^ (crc << 8)) & 0xFFFFFFFFFFFFFFFF
    return crc


def transform_point_to_frame(
    point: Tuple[float, float, float] | Sequence[float],
    target_frame: str = "RAS",
) -> Tuple[float, float, float]:
    """
    Convierte coordenadas tridimensionales entre el marco RAS (Slicer) y LPS (DICOM/Robots).
    
    En LPS: X_lps = -X_ras, Y_lps = -Y_ras, Z_lps = Z_ras.
    """
    frame = target_frame.strip().upper()
    if frame == "LPS":
        converted = (-float(point[0]), -float(point[1]), float(point[2]))
    else:
        converted = (float(point[0]), float(point[1]), float(point[2]))
    return converted


def build_trajectory_transform_matrix(
    trajectory: TrajectoryMetrics,
    coordinate_system: str = "RAS",
) -> Result[List[List[float]]]:
    """
    Genera la matriz homogénea 4x4 de transformación estereotáctica para un electrodo.
    
    Alinea el eje Z local con la dirección de penetración (desde la entrada hacia la diana),
    fijando el origen en el punto de inserción craneal. Admite marcos RAS y LPS.
    """
    if trajectory is None:
        return Err("La métrica de trayectoria suministrada es nula.")

    entry_t = transform_point_to_frame(trajectory.entry_point, coordinate_system)
    target_t = transform_point_to_frame(trajectory.target_point, coordinate_system)

    entry = np.array(entry_t, dtype=np.float64)
    target = np.array(target_t, dtype=np.float64)

    v_dir = target - entry
    length = float(np.linalg.norm(v_dir))

    if length < 1e-6:
        return Err("No se puede generar matriz para trayectoria con longitud nula o submilimétrica.")

    # Vector Z: Dirección de inserción hacia la diana
    z_axis = v_dir / length

    # Base ortonormal con vector de referencia temporal
    ref = np.array([0.0, 0.0, 1.0]) if abs(z_axis[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    x_axis = np.cross(ref, z_axis)
    x_axis = x_axis / float(np.linalg.norm(x_axis))
    y_axis = np.cross(z_axis, x_axis)
    y_axis = y_axis / float(np.linalg.norm(y_axis))

    # Matriz 4x4 (rotación 3x3 y traslación en la 4ª columna)
    matrix: List[List[float]] = [
        [float(x_axis[0]), float(y_axis[0]), float(z_axis[0]), float(entry[0])],
        [float(x_axis[1]), float(y_axis[1]), float(z_axis[1]), float(entry[1])],
        [float(x_axis[2]), float(y_axis[2]), float(z_axis[2]), float(entry[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]

    resultado: Result[List[List[float]]] = Ok(matrix)
    return resultado


def format_trajectories_payload(
    trajectories: Sequence[TrajectoryMetrics],
    patient_id: str = "ANONYMIZED_PATIENT",
    coordinate_system: str = "RAS",
) -> Result[Dict[str, Any]]:
    """
    Formatea las métricas completas de trayectorias a un diccionario serializable estandarizado.
    
    Aplica conversión al sistema de coordenadas especificado (RAS o LPS) y estructura
    los contactos de registro y matrices estereotácticas.
    """
    if not trajectories:
        return Err("La lista de trayectorias a exportar está vacía.")

    coord_sys = coordinate_system.strip().upper()
    if coord_sys not in ("RAS", "LPS"):
        coord_sys = "RAS"

    serialized_list: List[Dict[str, Any]] = []
    for traj in trajectories:
        matrix_res = build_trajectory_transform_matrix(traj, coordinate_system=coord_sys)
        matrix_data = matrix_res.value if isinstance(matrix_res, Ok) else None

        entry_conv = transform_point_to_frame(traj.entry_point, coord_sys)
        target_conv = transform_point_to_frame(traj.target_point, coord_sys)

        contacts_list: List[Dict[str, Any]] = []
        for c in traj.contacts:
            c_pos = transform_point_to_frame(c.position_ras, coord_sys)
            contacts_list.append({
                "index": c.index,
                "label": c.label,
                "distance_from_tip_mm": c.distance_from_tip_mm,
                "position": [round(c_pos[0], 3), round(c_pos[1], 3), round(c_pos[2], 3)],
            })

        traj_item: Dict[str, Any] = {
            "name": traj.name,
            "entry_point": [round(entry_conv[0], 3), round(entry_conv[1], 3), round(entry_conv[2], 3)],
            "target_point": [round(target_conv[0], 3), round(target_conv[1], 3), round(target_conv[2], 3)],
            "length_mm": round(traj.length_mm, 2),
            "angle_degrees": round(traj.angle_degrees, 2) if traj.angle_degrees is not None else None,
            "is_safe": traj.is_safe,
            "status_message": traj.status_message,
            "electrode_config": asdict(traj.config) if traj.config is not None else None,
            "contacts_count": len(contacts_list),
            "contacts": contacts_list,
            "transform_matrix_4x4": matrix_data,
        }
        serialized_list.append(traj_item)

    payload: Dict[str, Any] = {
        "protocol": "OpenIGTLink_Compatible",
        "schema_version": "1.0",
        "patient_id": patient_id,
        "coordinate_system": coord_sys,
        "electrode_count": len(trajectories),
        "export_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trajectories": serialized_list,
    }

    resultado: Result[Dict[str, Any]] = Ok(payload)
    return resultado


def export_trajectories_to_json_file(
    trajectories: Sequence[TrajectoryMetrics],
    output_filepath: str,
    patient_id: str = "ANONYMIZED_PATIENT",
    coordinate_system: str = "RAS",
) -> Result[str]:
    """Exporta el plan quirúrgico estereotáctico completo a un archivo JSON formateado."""
    if not output_filepath:
        return Err("Ruta de archivo de salida no especificada.")

    payload_res = format_trajectories_payload(
        trajectories,
        patient_id=patient_id,
        coordinate_system=coordinate_system,
    )
    if isinstance(payload_res, Err):
        return Err(payload_res.message, payload_res.cause)

    try:
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(payload_res.value, f, indent=2, ensure_ascii=False)
        resultado: Result[str] = Ok(f"Plan quirúrgico exportado correctamente a JSON: '{output_filepath}'.")
    except OSError as os_err:
        resultado = Err(f"Error de E/S al escribir archivo JSON: {os_err}")

    return resultado


def export_trajectories_to_csv_file(
    trajectories: Sequence[TrajectoryMetrics],
    output_filepath: str,
    coordinate_system: str = "RAS",
    include_contact_rows: bool = False,
) -> Result[str]:
    """
    Exporta las trayectorias a formato tabular CSV para hojas clínicas y robots estereotácticos.
    
    Admite modo resumen (1 fila por electrodo) o modo detallado con desglose de contactos.
    """
    if not output_filepath:
        return Err("Ruta de archivo CSV de salida no especificada.")

    if not trajectories:
        return Err("La lista de trayectorias a exportar en CSV está vacía.")

    coord_sys = coordinate_system.strip().upper()
    if coord_sys not in ("RAS", "LPS"):
        coord_sys = "RAS"

    try:
        with open(output_filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not include_contact_rows:
                # Cabecera resumen
                writer.writerow([
                    "Electrode_Name",
                    "Coordinate_System",
                    "Entry_X_mm",
                    "Entry_Y_mm",
                    "Entry_Z_mm",
                    "Target_X_mm",
                    "Target_Y_mm",
                    "Target_Z_mm",
                    "Length_mm",
                    "Skull_Angle_deg",
                    "Is_Safe",
                    "Num_Contacts",
                    "Status_Message",
                ])

                for traj in trajectories:
                    entry = transform_point_to_frame(traj.entry_point, coord_sys)
                    target = transform_point_to_frame(traj.target_point, coord_sys)
                    writer.writerow([
                        traj.name,
                        coord_sys,
                        f"{entry[0]:.3f}",
                        f"{entry[1]:.3f}",
                        f"{entry[2]:.3f}",
                        f"{target[0]:.3f}",
                        f"{target[1]:.3f}",
                        f"{target[2]:.3f}",
                        f"{traj.length_mm:.2f}",
                        f"{traj.angle_degrees:.2f}" if traj.angle_degrees is not None else "N/A",
                        "SAFE" if traj.is_safe else "ALERT",
                        len(traj.contacts),
                        traj.status_message,
                    ])
            else:
                # Cabecera detallada con contactos
                writer.writerow([
                    "Electrode_Name",
                    "Coordinate_System",
                    "Entry_X_mm",
                    "Entry_Y_mm",
                    "Entry_Z_mm",
                    "Target_X_mm",
                    "Target_Y_mm",
                    "Target_Z_mm",
                    "Length_mm",
                    "Skull_Angle_deg",
                    "Is_Safe",
                    "Contact_Index",
                    "Contact_Label",
                    "Dist_From_Tip_mm",
                    "Contact_X_mm",
                    "Contact_Y_mm",
                    "Contact_Z_mm",
                ])

                for traj in trajectories:
                    entry = transform_point_to_frame(traj.entry_point, coord_sys)
                    target = transform_point_to_frame(traj.target_point, coord_sys)
                    for c in traj.contacts:
                        c_pos = transform_point_to_frame(c.position_ras, coord_sys)
                        writer.writerow([
                            traj.name,
                            coord_sys,
                            f"{entry[0]:.3f}",
                            f"{entry[1]:.3f}",
                            f"{entry[2]:.3f}",
                            f"{target[0]:.3f}",
                            f"{target[1]:.3f}",
                            f"{target[2]:.3f}",
                            f"{traj.length_mm:.2f}",
                            f"{traj.angle_degrees:.2f}" if traj.angle_degrees is not None else "N/A",
                            "SAFE" if traj.is_safe else "ALERT",
                            c.index,
                            c.label,
                            f"{c.distance_from_tip_mm:.2f}",
                            f"{c_pos[0]:.3f}",
                            f"{c_pos[1]:.3f}",
                            f"{c_pos[2]:.3f}",
                        ])

        resultado: Result[str] = Ok(f"Plan quirúrgico exportado correctamente a CSV: '{output_filepath}'.")
    except OSError as os_err:
        resultado = Err(f"Error de E/S al escribir archivo CSV: {os_err}")

    return resultado


def export_trajectories_to_slicer_markups_json(
    trajectories: Sequence[TrajectoryMetrics],
    output_filepath: str,
    coordinate_system: str = "RAS",
) -> Result[str]:
    """
    Exporta las trayectorias al formato oficial Markups JSON v1.0.0 de 3D Slicer (.mrk.json).
    
    Genera nodos Line para cada electrodo y nodos Fiducial para sus contactos de registro,
    permitiendo la reimportación nativa arrastrando y soltando el archivo en Slicer.
    """
    if not output_filepath:
        return Err("Ruta de archivo Markups JSON no especificada.")

    if not trajectories:
        return Err("La lista de trayectorias a exportar está vacía.")

    coord_sys = coordinate_system.strip().upper()
    if coord_sys not in ("RAS", "LPS"):
        coord_sys = "RAS"

    markups_list: List[Dict[str, Any]] = []

    for traj in trajectories:
        entry = transform_point_to_frame(traj.entry_point, coord_sys)
        target = transform_point_to_frame(traj.target_point, coord_sys)

        line_color = [0.18, 0.80, 0.44] if traj.is_safe else [0.91, 0.30, 0.24]

        # 1. Markup de tipo Line para la trayectoria
        line_markup: Dict[str, Any] = {
            "type": "Line",
            "coordinateSystem": coord_sys,
            "coordinateUnits": "mm",
            "locked": False,
            "labelFormat": f"{traj.name}-%d",
            "controlPoints": [
                {
                    "id": "1",
                    "label": f"{traj.name}_Entry",
                    "description": "Punto de inserción craneal",
                    "position": [round(entry[0], 3), round(entry[1], 3), round(entry[2], 3)],
                    "selected": True,
                    "locked": False,
                    "visibility": True,
                    "positionStatus": "defined",
                },
                {
                    "id": "2",
                    "label": f"{traj.name}_Target",
                    "description": "Punto diana cerebral",
                    "position": [round(target[0], 3), round(target[1], 3), round(target[2], 3)],
                    "selected": True,
                    "locked": False,
                    "visibility": True,
                    "positionStatus": "defined",
                },
            ],
            "measurements": [
                {
                    "name": "length",
                    "enabled": True,
                    "value": round(traj.length_mm, 2),
                    "units": "mm",
                }
            ],
            "display": {
                "visibility": True,
                "opacity": 1.0,
                "color": line_color,
                "selectedColor": line_color,
                "propertiesLabelVisibility": True,
                "pointLabelsVisibility": True,
                "textScale": 2.5,
                "glyphType": "Sphere3D",
                "glyphScale": 2.0,
            },
        }
        markups_list.append(line_markup)

        # 2. Markup de tipo Fiducial para los contactos de registro
        if traj.contacts:
            fid_control_points: List[Dict[str, Any]] = []
            for c in traj.contacts:
                c_pos = transform_point_to_frame(c.position_ras, coord_sys)
                fid_control_points.append({
                    "id": str(c.index),
                    "label": f"{traj.name}_{c.label}",
                    "description": f"Contacto {c.label} a {c.distance_from_tip_mm:.1f} mm de la punta",
                    "position": [round(c_pos[0], 3), round(c_pos[1], 3), round(c_pos[2], 3)],
                    "selected": True,
                    "locked": False,
                    "visibility": True,
                    "positionStatus": "defined",
                })

            contacts_markup: Dict[str, Any] = {
                "type": "Fiducial",
                "coordinateSystem": coord_sys,
                "coordinateUnits": "mm",
                "locked": False,
                "labelFormat": f"{traj.name}-Contact-%d",
                "controlPoints": fid_control_points,
                "display": {
                    "visibility": True,
                    "opacity": 0.85,
                    "color": [0.2, 0.6, 0.9],
                    "selectedColor": [0.2, 0.6, 0.9],
                    "propertiesLabelVisibility": False,
                    "pointLabelsVisibility": True,
                    "textScale": 1.8,
                    "glyphType": "Sphere3D",
                    "glyphScale": 1.2,
                },
            }
            markups_list.append(contacts_markup)

    markups_doc: Dict[str, Any] = {
        "@schema": "https://raw.githubusercontent.com/slicer/slicer/master/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.0.json#",
        "markups": markups_list,
    }

    try:
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(markups_doc, f, indent=2, ensure_ascii=False)
        resultado: Result[str] = Ok(f"Plan quirúrgico exportado a Markups JSON: '{output_filepath}'.")
    except OSError as os_err:
        resultado = Err(f"Error de E/S al escribir archivo Markups JSON: {os_err}")

    return resultado


# -----------------------------------------------------------------------------
# Protocolo Binario OpenIGTLink (Cabecera estándar de 58 bytes y serialización)
# -----------------------------------------------------------------------------

def pack_openigtlink_header(
    msg_type: str,
    device_name: str,
    body_bytes: bytes,
    timestamp: float | None = None,
    version: int = 1,
) -> bytes:
    """
    Empaqueta la cabecera canónica de 58 bytes de OpenIGTLink en formato big-endian.
    
    Formato: Version(H, 2B), Type(12s), DeviceName(20s), TimeSec(I, 4B),
             TimeFrac(I, 4B), BodySize(Q, 8B), CRC64(Q, 8B).
    """
    ts = timestamp if timestamp is not None else time.time()
    time_sec = int(ts)
    time_frac = int((ts - time_sec) * 1e6)  # Microsegundos

    type_bytes = msg_type.encode("ascii", errors="replace")[:12].ljust(12, b"\x00")
    device_bytes = device_name.encode("ascii", errors="replace")[:20].ljust(20, b"\x00")
    body_size = len(body_bytes)
    crc = calculate_crc64(body_bytes)

    header = struct.pack(
        ">H12s20sIIQQ",
        version,
        type_bytes,
        device_bytes,
        time_sec,
        time_frac,
        body_size,
        crc,
    )
    return header


def pack_transform_message(
    trajectory: TrajectoryMetrics,
    coordinate_system: str = "RAS",
) -> Result[bytes]:
    """
    Genera un mensaje binario OpenIGTLink TRANSFORM completo (cabecera + payload 3x4).
    
    El payload son 12 números de coma flotante de 32 bits (48 bytes) ordenados por columnas.
    """
    mat_res = build_trajectory_transform_matrix(trajectory, coordinate_system=coordinate_system)
    if isinstance(mat_res, Err):
        return Err(mat_res.message, mat_res.cause)

    m = mat_res.value
    # Orden de OpenIGTLink: R11, R21, R31, R12, R22, R32, R13, R23, R33, Tx, Ty, Tz
    body = struct.pack(
        ">12f",
        float(m[0][0]), float(m[1][0]), float(m[2][0]),
        float(m[0][1]), float(m[1][1]), float(m[2][1]),
        float(m[0][2]), float(m[1][2]), float(m[2][2]),
        float(m[0][3]), float(m[1][3]), float(m[2][3]),
    )

    header = pack_openigtlink_header(
        msg_type="TRANSFORM",
        device_name=trajectory.name,
        body_bytes=body,
    )
    resultado: Result[bytes] = Ok(header + body)
    return resultado


def pack_point_message(
    trajectory: TrajectoryMetrics,
    coordinate_system: str = "RAS",
) -> Result[bytes]:
    """
    Genera un mensaje binario OpenIGTLink POINT con entrada, diana y todos los contactos.
    
    Cada elemento tiene 136 bytes: Name(64s), Group(32s), RGBA(4B), Pos(3f), Radius(f), Owner(20s).
    """
    coord_sys = coordinate_system.strip().upper()
    points_to_pack: List[Tuple[str, str, Tuple[float, float, float], float, Tuple[int, int, int, int]]] = []

    # 1. Punto de entrada
    entry = transform_point_to_frame(trajectory.entry_point, coord_sys)
    points_to_pack.append((
        f"{trajectory.name}_Entry",
        "ENTRY",
        entry,
        1.25,
        (255, 128, 0, 255),
    ))

    # 2. Punto diana
    target = transform_point_to_frame(trajectory.target_point, coord_sys)
    points_to_pack.append((
        f"{trajectory.name}_Target",
        "TARGET",
        target,
        1.5,
        (0, 255, 128, 255),
    ))

    # 3. Contactos
    for c in trajectory.contacts:
        c_pos = transform_point_to_frame(c.position_ras, coord_sys)
        points_to_pack.append((
            f"{trajectory.name}_{c.label}",
            "CONTACT",
            c_pos,
            0.4,
            (50, 150, 255, 255),
        ))

    body_chunks: List[bytes] = []
    owner_bytes = b"SEEGPlanner".ljust(20, b"\x00")

    for name_str, group_str, pos_t, radius, rgba in points_to_pack:
        n_bytes = name_str.encode("ascii", errors="replace")[:64].ljust(64, b"\x00")
        g_bytes = group_str.encode("ascii", errors="replace")[:32].ljust(32, b"\x00")
        pt_bytes = struct.pack(
            ">64s32s4B3ff20s",
            n_bytes,
            g_bytes,
            rgba[0], rgba[1], rgba[2], rgba[3],
            float(pos_t[0]), float(pos_t[1]), float(pos_t[2]),
            float(radius),
            owner_bytes,
        )
        body_chunks.append(pt_bytes)

    body = b"".join(body_chunks)
    header = pack_openigtlink_header(
        msg_type="POINT",
        device_name=trajectory.name,
        body_bytes=body,
    )
    resultado: Result[bytes] = Ok(header + body)
    return resultado


def transmit_openigtlink_trajectories(
    trajectories: Sequence[TrajectoryMetrics],
    host: str = "127.0.0.1",
    port: int = 18944,
    timeout_sec: float = 2.0,
    coordinate_system: str = "RAS",
) -> Result[Dict[str, int]]:
    """
    Transmite las trayectorias y contactos a un servidor OpenIGTLink mediante un socket no bloqueante.
    
    Envía mensajes TRANSFORM para cada electrodo y mensajes POINT para coordenadas anatómicas.
    Captura de forma segura cualquier fallo de conexión o timeout sin bloquear la aplicación.
    """
    if not trajectories:
        return Err("No hay trayectorias para transmitir por OpenIGTLink.")

    packets_to_send: List[bytes] = []
    transform_count = 0
    point_count = 0

    for traj in trajectories:
        # Generar TRANSFORM
        t_res = pack_transform_message(traj, coordinate_system=coordinate_system)
        if isinstance(t_res, Ok):
            packets_to_send.append(t_res.value)
            transform_count += 1

        # Generar POINT
        p_res = pack_point_message(traj, coordinate_system=coordinate_system)
        if isinstance(p_res, Ok):
            packets_to_send.append(p_res.value)
            point_count += 1

    total_bytes = sum(len(pkt) for pkt in packets_to_send)

    # Conexión TCP con timeout defensivo
    sock = None
    try:
        sock = socket.create_connection((host, int(port)), timeout=float(timeout_sec))
        for pkt in packets_to_send:
            sock.sendall(pkt)

        stats: Dict[str, int] = {
            "transforms_sent": transform_count,
            "points_sent": point_count,
            "total_bytes_sent": total_bytes,
        }
        resultado: Result[Dict[str, int]] = Ok(stats)
    except socket.timeout:
        resultado = Err(
            f"Tiempo de espera agotado ({timeout_sec:.1f} s) al conectar con el servidor OpenIGTLink en {host}:{port}."
        )
    except (ConnectionRefusedError, OSError) as net_err:
        resultado = Err(
            f"No se pudo establecer conexión con el servidor OpenIGTLink en {host}:{port}: {net_err}."
        )
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    return resultado
