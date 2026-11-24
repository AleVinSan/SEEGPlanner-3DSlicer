#!/usr/bin/env bash
# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

echo "[INFO] Deteniendo instancias en ejecución de 3D Slicer..."
pkill -f "Slicer" 2>/dev/null && echo "[OK] Instancias finalizadas." || echo "[INFO] No se encontraron procesos activos de Slicer."
