#!/usr/bin/env bash
# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/SEEGPlanner"

echo "[INFO] Iniciando 3D Slicer con el módulo SEEGPlanner cargado..."

SLICER_APP="/Applications/Slicer.app/Contents/MacOS/Slicer"

if [ -f "${SLICER_APP}" ]; then
  "${SLICER_APP}" --additional-module-path "${MODULE_DIR}" "$@" &
  echo "[INFO] 3D Slicer iniciado (PID: $!)."
else
  echo "[AVISO] No se encontró Slicer en /Applications/Slicer.app."
  echo "Por favor abra 3D Slicer manualmente y agregue la ruta:"
  echo "  ${MODULE_DIR}"
fi
