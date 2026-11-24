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
import socket
import struct
import sys
import tempfile
import threading
import unittest
from typing import List

# Añadir la raíz de la extensión al path para permitir importar Logic
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSION_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

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
    transmit_openigtlink_trajectories,
)
from Logic.result import Err, Ok
from Logic.trajectory_planner import (
    ElectrodeConfig,
    TrajectoryMetrics,
    calculate_trajectory,
)


class MockOpenIGTLinkServer:
    """Servidor TCP local de prueba que recibe y valida paquetes OpenIGTLink."""

    def __init__(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", 0))
        self.host, self.port = self.server_socket.getsockname()
        self.server_socket.listen(1)
        self.received_data = bytearray()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        self.server_socket.settimeout(2.0)
        try:
            client, _ = self.server_socket.accept()
            client.settimeout(2.0)
            while self.running:
                chunk = client.recv(4096)
                if not chunk:
                    break
                self.received_data.extend(chunk)
            client.close()
        except socket.timeout:
            pass
        except Exception:
            pass

    def stop(self) -> None:
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)


class TestExportStandalone(unittest.TestCase):
    """Suite de pruebas unitarias standalone para exportación estereotáctica y OpenIGTLink."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.cfg = ElectrodeConfig(diameter_mm=0.8, num_contacts=8)

        # Trayectoria sintética 1
        self.t1 = calculate_trajectory(
            entry_point=(20.0, 30.0, 40.0),
            target_point=(5.0, 10.0, 0.0),
            name="SEEG_E1",
            skull_normal=(0.577, 0.577, 0.577),
            config=self.cfg,
        ).value

        # Trayectoria sintética 2
        self.t2 = calculate_trajectory(
            entry_point=(-25.0, 35.0, 45.0),
            target_point=(-10.0, 15.0, 5.0),
            name="SEEG_E2",
            skull_normal=(-0.577, 0.577, 0.577),
            config=self.cfg,
        ).value

        self.trajectories: List[TrajectoryMetrics] = [self.t1, self.t2]

    def tearDown(self) -> None:
        # Limpieza de archivos temporales
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except OSError:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def test_crc64_calculation_canonical(self) -> None:
        """Verifica el cálculo de CRC-64 ECMA-182 frente a vectores de prueba oficiales."""
        # 1. Cadena vacía
        self.assertEqual(calculate_crc64(b""), 0)

        # 2. Vector canónico '123456789'
        expected = 0x6C40DF5F0B497347
        self.assertEqual(calculate_crc64(b"123456789"), expected)

    def test_transform_point_to_frame_conversions(self) -> None:
        """Verifica la conversión determinística de coordenadas entre marcos RAS y LPS."""
        pt = (12.5, -34.0, 56.2)

        # En RAS (sin cambio)
        ras_pt = transform_point_to_frame(pt, "RAS")
        self.assertAlmostEqual(ras_pt[0], 12.5)
        self.assertAlmostEqual(ras_pt[1], -34.0)
        self.assertAlmostEqual(ras_pt[2], 56.2)

        # En LPS (inversión de X e Y)
        lps_pt = transform_point_to_frame(pt, "LPS")
        self.assertAlmostEqual(lps_pt[0], -12.5)
        self.assertAlmostEqual(lps_pt[1], 34.0)
        self.assertAlmostEqual(lps_pt[2], 56.2)

    def test_build_trajectory_transform_matrix(self) -> None:
        """Verifica las propiedades matemáticas de la matriz 4x4 (traslación y rotación)."""
        res_ras = build_trajectory_transform_matrix(self.t1, "RAS")
        self.assertIsInstance(res_ras, Ok)
        m_ras = res_ras.value
        self.assertEqual(len(m_ras), 4)
        self.assertEqual(len(m_ras[0]), 4)

        # Origen = punto de entrada en RAS
        self.assertAlmostEqual(m_ras[0][3], 20.0)
        self.assertAlmostEqual(m_ras[1][3], 30.0)
        self.assertAlmostEqual(m_ras[2][3], 40.0)

        # Matriz en LPS
        res_lps = build_trajectory_transform_matrix(self.t1, "LPS")
        self.assertIsInstance(res_lps, Ok)
        m_lps = res_lps.value
        self.assertAlmostEqual(m_lps[0][3], -20.0)
        self.assertAlmostEqual(m_lps[1][3], -30.0)
        self.assertAlmostEqual(m_lps[2][3], 40.0)

    def test_format_trajectories_payload(self) -> None:
        """Verifica la serialización estructurada de metadatos, parámetros y contactos."""
        res = format_trajectories_payload(self.trajectories, patient_id="PAT_TEST_01", coordinate_system="RAS")
        self.assertIsInstance(res, Ok)
        data = res.value

        self.assertEqual(data["protocol"], "OpenIGTLink_Compatible")
        self.assertEqual(data["patient_id"], "PAT_TEST_01")
        self.assertEqual(data["coordinate_system"], "RAS")
        self.assertEqual(data["electrode_count"], 2)
        self.assertEqual(len(data["trajectories"]), 2)

        traj0 = data["trajectories"][0]
        self.assertEqual(traj0["name"], "SEEG_E1")
        self.assertEqual(traj0["contacts_count"], 8)
        self.assertEqual(len(traj0["contacts"]), 8)
        self.assertEqual(traj0["contacts"][0]["label"], "E01")
        self.assertIn("transform_matrix_4x4", traj0)

    def test_export_trajectories_to_json_file(self) -> None:
        """Verifica la exportación física a disco y relectura de un archivo JSON."""
        json_path = os.path.join(self.temp_dir, "plan_test.json")
        res = export_trajectories_to_json_file(self.trajectories, json_path, patient_id="ANON_123")
        self.assertIsInstance(res, Ok)
        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        self.assertEqual(loaded["patient_id"], "ANON_123")
        self.assertEqual(loaded["electrode_count"], 2)

    def test_export_trajectories_to_csv_file(self) -> None:
        """Verifica la exportación a CSV tanto en formato resumen como detallado."""
        # 1. Resumen
        csv_summary = os.path.join(self.temp_dir, "plan_summary.csv")
        res_sum = export_trajectories_to_csv_file(self.trajectories, csv_summary, include_contact_rows=False)
        self.assertIsInstance(res_sum, Ok)
        self.assertTrue(os.path.exists(csv_summary))

        with open(csv_summary, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 3)  # 1 cabecera + 2 electrodos
        self.assertEqual(rows[0][0], "Electrode_Name")

        # 2. Detallado con contactos
        csv_detailed = os.path.join(self.temp_dir, "plan_detailed.csv")
        res_det = export_trajectories_to_csv_file(self.trajectories, csv_detailed, include_contact_rows=True)
        self.assertIsInstance(res_det, Ok)
        with open(csv_detailed, "r", encoding="utf-8") as f:
            rows_det = list(csv.reader(f))
        # 1 cabecera + 2 electrodos * 8 contactos = 17 filas
        self.assertEqual(len(rows_det), 1 + 2 * 8)
        self.assertEqual(rows_det[1][12], "E01")

    def test_export_trajectories_to_slicer_markups_json(self) -> None:
        """Verifica que el archivo Markups JSON cumpla estrictamente el esquema v1.0.0 de Slicer."""
        mrk_path = os.path.join(self.temp_dir, "SEEG_Plan.mrk.json")
        res = export_trajectories_to_slicer_markups_json(self.trajectories, mrk_path, coordinate_system="RAS")
        self.assertIsInstance(res, Ok)
        self.assertTrue(os.path.exists(mrk_path))

        with open(mrk_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        self.assertIn("@schema", doc)
        self.assertIn("markups", doc)
        # 2 electrodos -> 2 Markups Line + 2 Markups Fiducial (contactos) = 4 markups
        self.assertEqual(len(doc["markups"]), 4)

        line_markup = doc["markups"][0]
        self.assertEqual(line_markup["type"], "Line")
        self.assertEqual(line_markup["coordinateSystem"], "RAS")
        self.assertEqual(len(line_markup["controlPoints"]), 2)

        fid_markup = doc["markups"][1]
        self.assertEqual(fid_markup["type"], "Fiducial")
        self.assertEqual(len(fid_markup["controlPoints"]), 8)

    def test_openigtlink_header_and_payload_packing(self) -> None:
        """Verifica el empaquetado binario de cabecera de 58 bytes y mensajes TRANSFORM y POINT."""
        # 1. Cabecera
        dummy_body = b"OPENIGTLINK_TEST_PAYLOAD"
        header = pack_openigtlink_header("TEST_MSG", "DEVICE_01", dummy_body)
        self.assertEqual(len(header), 58)

        version, type_b, dev_b, t_sec, t_frac, body_sz, crc = struct.unpack(">H12s20sIIQQ", header)
        self.assertEqual(version, 1)
        self.assertEqual(type_b.split(b"\x00")[0], b"TEST_MSG")
        self.assertEqual(dev_b.split(b"\x00")[0], b"DEVICE_01")
        self.assertEqual(body_sz, len(dummy_body))
        self.assertEqual(crc, calculate_crc64(dummy_body))

        # 2. Mensaje TRANSFORM (58B cabecera + 48B matriz = 106B)
        t_res = pack_transform_message(self.t1, "RAS")
        self.assertIsInstance(t_res, Ok)
        self.assertEqual(len(t_res.value), 58 + 48)

        # 3. Mensaje POINT (58B cabecera + (2 + 8)*136B = 58 + 1360 = 1418B)
        p_res = pack_point_message(self.t1, "RAS")
        self.assertIsInstance(p_res, Ok)
        self.assertEqual(len(p_res.value), 58 + 10 * 136)

    def test_transmit_openigtlink_trajectories_timeout(self) -> None:
        """Verifica que intentar conectar a un puerto cerrado o inalcanzable no congele el sistema."""
        # Puerto local reservado no abierto
        res = transmit_openigtlink_trajectories(
            self.trajectories,
            host="127.0.0.1",
            port=59999,
            timeout_sec=0.2,
        )
        self.assertIsInstance(res, Err)
        self.assertIn("127.0.0.1:59999", res.message)

    def test_transmit_openigtlink_trajectories_mock_socket(self) -> None:
        """Verifica la transmisión OpenIGTLink completa mockeando el socket."""
        from unittest.mock import MagicMock, patch

        mock_socket = MagicMock()
        sent_chunks: List[bytes] = []
        mock_socket.sendall.side_effect = lambda data: sent_chunks.append(data)

        with patch("socket.create_connection", return_value=mock_socket) as mock_connect:
            res = transmit_openigtlink_trajectories(
                self.trajectories,
                host="192.168.1.100",
                port=18944,
                timeout_sec=1.5,
                coordinate_system="RAS",
            )
            mock_connect.assert_called_once_with(("192.168.1.100", 18944), timeout=1.5)
            self.assertIsInstance(res, Ok)
            stats = res.value
            self.assertEqual(stats["transforms_sent"], 2)
            self.assertEqual(stats["points_sent"], 2)
            self.assertEqual(len(sent_chunks), 4)  # 2 transforms + 2 points
            mock_socket.close.assert_called_once()

    def test_transmit_openigtlink_trajectories_mock_server(self) -> None:
        """Verifica la transmisión contra un servidor TCP si el entorno permite loopback."""
        try:
            server = MockOpenIGTLinkServer()
        except OSError as e:
            if "Operation not permitted" in str(e) or "Permission denied" in str(e):
                self.skipTest("Loopback network restricted by environment sandbox.")
                return
            raise

        try:
            res = transmit_openigtlink_trajectories(
                self.trajectories,
                host=server.host,
                port=server.port,
                timeout_sec=1.0,
                coordinate_system="RAS",
            )
            if isinstance(res, Err) and ("Operation not permitted" in res.message or "Permission denied" in res.message):
                self.skipTest("Network connect restricted by environment sandbox.")
                return
            self.assertIsInstance(res, Ok)
            stats = res.value
            self.assertEqual(stats["transforms_sent"], 2)
            self.assertEqual(stats["points_sent"], 2)
            self.assertGreater(stats["total_bytes_sent"], 1000)

            # Dar un breve instante para que el servidor complete la lectura del socket
            server.thread.join(timeout=0.3)
            self.assertGreaterEqual(len(server.received_data), stats["total_bytes_sent"])
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
