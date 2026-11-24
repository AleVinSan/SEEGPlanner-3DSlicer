# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SEEGPlanner)

# --------------------------------------------------------------------------
# Configuración del módulo ScriptedLoadableModule para 3D Slicer
# --------------------------------------------------------------------------

set(MODULE_NAME "SEEGPlanner")
set(MODULE_TITLE "SEEG Planner")

set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  Logic/__init__.py
  Logic/result.py
  Logic/eeg_1020_calculator.py
  Logic/trajectory_planner.py
  Logic/target_manager.py
  Logic/skull_surface_extractor.py
  Logic/igtlink_exporter.py
)

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
)

# Integración con macros de CMake de 3D Slicer si se compila con el Extension Manager
if(DEFINED Slicer_SOURCE_DIR)
  slicerMacroBuildScriptedModule(
    NAME ${MODULE_NAME}
    TITLE ${MODULE_TITLE}
    SCRIPTS ${MODULE_PYTHON_SCRIPTS}
    RESOURCES ${MODULE_PYTHON_RESOURCES}
    WITH_GENERIC_TESTS
  )
endif()
