# 🧠 SEEGPlanner — 3D Slicer Extension

Herramienta de código abierto para la planificación asistida de trayectorias de electrodos intracraneales en cirugía de **estéreo-electroencefalografía (SEEG)** para pacientes con epilepsia farmacorresistente.

---

## 🚀 Guía de Instalación y Carga en 3D Slicer (Modo Desarrollador)

Para cargar y probar el módulo directamente en 3D Slicer (versión >= 5.12.3) sin necesidad de empaquetar:

1. **Abrir 3D Slicer**.
2. Ir a **Edit** > **Application Settings** (o pulsar `Cmd + ,` en macOS / `Ctrl + ,` en Windows/Linux).
3. Seleccionar la pestaña **Modules** en el menú lateral izquierdo.
4. En la sección **Additional module paths**, hacer clic en el botón **Add**.
5. Navegar y seleccionar la carpeta del módulo:
   ```text
   /Users/bvinegla/Desktop/quinto curso/tfgprueba/SEEGPlanner
   ```
6. Pulsar **OK** y reiniciar 3D Slicer cuando la aplicación lo solicite.
7. Una vez reiniciado, el módulo estará disponible en el selector de módulos bajo la categoría:
   ```text
   Modules > Neurosurgery > SEEG Planner
   ```

---

## 🛠️ Ejecución de Pruebas Automatizadas

### 1. Pruebas Unitarias Standalone (fuera de Slicer)
Se pueden ejecutar directamente con Python 3 estándar:
```bash
python3 SEEGPlanner/Testing/Python/test_logic_standalone.py
```

### 2. Pruebas Integradas dentro de 3D Slicer
Para validar la interacción con la escena médica MRML en modo desatendido:
```bash
/Applications/Slicer.app/Contents/MacOS/Slicer --no-splash --testing --python-script "SEEGPlanner/Testing/Python/run_slicer_test.py"
```

---

## 📂 Arquitectura del Módulo

- **`SEEGPlanner.py`**: Clase controladora `ScriptedLoadableModule`, interfaz `SEEGPlannerWidget` y orquestador `SEEGPlannerLogic`.
- **`Logic/`**:
  - `result.py`: Tipado estricto `Ok[T]` y `Err` (patrón Result).
  - `eeg_1020_calculator.py`: Algoritmo de mapeo geométrico y arcos esféricos del sistema EEG 10-20.
  - `trajectory_planner.py`: Cálculo analítico de vectores directores, longitud y validación de seguridad de ángulo óseo.
  - `igtlink_exporter.py`: Generador de matrices 4x4 y payloads compatibles con OpenIGTLink.
- **`Testing/`**: Pruebas unitarias standalone y scripts de verificación para Slicer.
