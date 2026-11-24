@echo off
REM =============================================================================
REM SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
REM Copyright (c) 2026 Alejandra Viñegla Sánchez
REM Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
REM Licensed under the MIT License.
REM Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
REM =============================================================================

echo [INFO] Cerrando 3D Slicer...
taskkill /F /IM Slicer.exe 2>nul
