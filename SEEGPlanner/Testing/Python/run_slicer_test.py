# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

import os
import sys

# Asegurar importación de SEEGPlanner
module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

try:
    import slicer
    print(f"[INFO] 3D Slicer versión detectada: {slicer.app.applicationVersion}")
    import SEEGPlanner

    test = SEEGPlanner.SEEGPlannerTest()
    print("[INFO] Ejecutando SEEGPlannerTest...")
    test.runTest()
    print(">>> SLICER_TEST_SUCCESSFUL <<<")
    slicer.app.exit(0)
except Exception as e:
    print(f"[ERROR] Fallo durante la ejecución del test: {e}")
    import traceback
    traceback.print_exc()
    if "slicer" in locals() and hasattr(slicer, "app"):
        slicer.app.exit(1)
    else:
        sys.exit(1)
