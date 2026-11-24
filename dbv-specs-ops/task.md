# Backlog - SEEGPlanner (3D Slicer Extension)

> **Proyecto:** Desarrollo de una herramienta en 3D Slicer para la planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía.
> **Autora:** Alejandra Viñegla Sánchez
> **Tutores:** Víctor Manuel Smith Fernández, David Bueno Vallejo
> **Framework:** dbv-specs-ops SDD v2.9.0
> **Horas estimadas:** 296 h

---

## Contexto del Proyecto (Context Snapshot)

- **Objetivo:** Desarrollar el módulo modular y abierto en 3D Slicer para la planificación automatizada y cálculo de trayectorias de electrodos en cirugía SEEG integrando el estándar EEG 10-20, verificación de seguridad y exportación OpenIGTLink.
- **Estado actual:** PROYECTO TFG Y FASE 8 COMPLETADOS AL 100% (Módulo SEEGPlanner para 3D Slicer completamente desarrollado y validado: control de calidad MRI estereotáctico, extracción de superficie craneal con normales exteriores y proyección por ray-casting del estándar EEG 10-20, localización de dianas anatómicas profundas con protección ventricular, modelado paramétrico 3D de electrodos con perno guía coaxial, algoritmo analítico continuo de detección de colisiones segmento-segmento 3D en $\mathcal{O}(1)$, cuadro de mandos clínico interactivo con semáforo de seguridad en tiempo real, exportación multi-formato abierta a JSON/CSV/Markups, protocolo binario OpenIGTLink v1/v2 para neuronavegadores, suite de validación end-to-end con 49 tests unitarios pasando al 100%, Manual de Usuario clínico paso a paso y Memoria Oficial de TFG estructurada conforme a la normativa de la UMA).
- **Última decisión técnica:** Validación cuantitativa mediante generador anatómico determinístico offline, benchmarks numéricos de precisión submilimétrica, manual de usuario guiado en 5 pasos quirúrgicos y estructura canónica de la memoria del TFG con guión de defensa ante el tribunal.
- **Próximo paso:** Cierre y entrega formal del proyecto (`/ship`).

---

## Checklist de Tareas del TFG (296 Horas)

### Fase 1: Revisión de la bibliografía y requisitos del software (35 h)
- [x] Análisis del anteproyecto y marco clínico de la SEEG y epilepsia farmacorresistente.
- [x] Configuración del framework SDD `dbv-specs-ops` en el repositorio.
- [x] Redacción y validación de especificaciones formales en `dbv-specs-ops/docs/SPECIFICATIONS.md`.
- [x] Diseño preliminar de arquitectura técnica en `dbv-specs-ops/docs/ARCHITECTURE.md`.

### Fase 2: Preparación del entorno de trabajo en 3D Slicer (35 h)
- [x] Creación de la estructura de directorios y plantilla base de la extensión `SEEGPlanner/`.
- [x] Implementación de `SEEGPlanner.py` con las clases base de Slicer (`ScriptedLoadableModule`, `ScriptedLoadableModuleWidget`, `ScriptedLoadableModuleLogic`).
- [x] Verificación de carga en 3D Slicer v5.12.3/v5.12.4 en modo desarrollador.
- [x] Creación de suite inicial de test autoejecutable (`SEEGPlannerTest` y `test_logic_standalone.py`).

### Fase 3: Localización de las zonas diana cerebrales (35 h)
- [x] Tarea 3.1: Submódulo `SEEGPlanner/Logic/target_manager.py` (estructuras de datos, validación de resolución MRI y cálculo analítico de centroides ponderados en RAS).
- [x] Tarea 3.2: Métodos orquestadores en `SEEGPlannerLogic` (`validateAndAlignVolume` para centrado de vistas 2D y `extractTargetsFromSegmentationNode` para marcado de fiduciales).
- [x] Tarea 3.3: Componentes de interfaz en `SEEGPlannerWidget` (inspección de resolución de vóxel, selector de `vtkMRMLSegmentationNode`, tabla resumen de dianas y botón de extracción).
- [x] Tarea 3.4: Suite de pruebas unitarias standalone (`test_targets_standalone.py`) y prueba integrada en 3D Slicer (`SEEGPlannerTest`).

### Fase 4: Mapeo del sistema EEG 10-20 sobre la cabeza (40 h)
- [x] Tarea 4.1: Submódulo `SEEGPlanner/Logic/skull_surface_extractor.py` (extracción de superficie cutánea con FlyingEdges3D, filtrado de conectividad y cálculo de normales exteriores).
- [x] Tarea 4.2: Algoritmo de proyección por trazado de rayos (*ray-casting*) sobre la malla poligonal en `SEEGPlanner/Logic/eeg_1020_calculator.py`.
- [x] Tarea 4.3: Métodos orquestadores en `SEEGPlannerLogic` (`generateHeadSurfaceModel` y `computeAndProject1020Grid`).
- [x] Tarea 4.4: Interfaz de usuario en `SEEGPlannerWidget` (asistente de colocación de fiduciales anatómicos, generador de superficie cutánea y opciones de proyección).
- [x] Tarea 4.5: Suite de pruebas unitarias standalone (`test_surface_standalone.py`) y prueba integrada en 3D Slicer (`SEEGPlannerTest`).

### Fase 5: Cálculo y trazado de las trayectorias (40 h)
- [x] Tarea 5.1: Enriquecimiento de estructuras y parámetros en `SEEGPlanner/Logic/trajectory_planner.py` (`ElectrodeConfig`, `ContactPoint`, `TrajectoryConflict`).
- [x] Tarea 5.2: Algoritmos geométricos 3D: distribución de contactos de registro y generación de mallas tubulares VTK con perno guía.
- [x] Tarea 5.3: Algoritmo analítico de distancia euclídea mínima entre segmentos 3D y comprobación de conflictos multi-electrodo.
- [x] Tarea 5.4: Métodos orquestadores en `SEEGPlannerLogic` e interfaz interactiva de trayectorias en `SEEGPlannerWidget`.
- [x] Tarea 5.5: Suite de pruebas unitarias standalone (`test_trajectories_standalone.py`) y prueba integrada en 3D Slicer (`SEEGPlannerTest`).

### Fase 6: Diseño de la interfaz gráfica avanzada y cuadro de mandos (36 h)
- [x] Tarea 6.1: Estructuración del panel guiado en 4 pasos quirúrgicos con indicadores de estado (`SEEGPlannerWidget`).
- [x] Tarea 6.2: Cuadro de mandos central y tabla interactiva de electrodos planificados con semáforo visual de seguridad.
- [x] Tarea 6.3: Visor desplegable de contactos de registro y gestión del plan (eliminación limpia de nodos MRML y recentrado 2D/3D).
- [x] Tarea 6.4: Suite de pruebas unitarias standalone (`test_ui_logic_standalone.py`) y prueba integrada en 3D Slicer (`SEEGPlannerTest`).

### Fase 7: Exportación de datos estereotácticos y conector OpenIGTLink (35 h)
- [x] Tarea 7.1: Serializadores a formatos de archivo abiertos en `Logic/igtlink_exporter.py` (JSON estructurado completo, CSV para robótica/marcos estereotácticos y Slicer Markups JSON `.mrk.json` con soporte de coordenadas RAS/LPS).
- [x] Tarea 7.2: Motor de protocolo binario OpenIGTLink v1/v2 (empaquetado big-endian de 58 bytes, checksum CRC64 ECMA-182, mensajes `TRANSFORM` y `POINT`, y cliente de socket no bloqueante con timeout estricto).
- [x] Tarea 7.3: Métodos orquestadores en `SEEGPlannerLogic` y panel de interfaz de exportación (Paso 5) en `SEEGPlannerWidget` con selectores de formato, sistema de referencia (RAS/LPS) y controles de transmisión en tiempo real.
- [x] Tarea 7.4: Suite de pruebas unitarias standalone (`test_export_standalone.py`) con servidor mock de OpenIGTLink y ampliación de `SEEGPlannerTest`.

### Fase 8: Pruebas, validación cuantitativa, manual de usuario y memoria del TFG (40 h)
- [x] Tarea 8.1: Pipeline de validación end-to-end sobre resonancia magnética cerebral en `SEEGPlanner/Testing/Python/test_validation_pipeline.py` (generador anatómico offline, dianas, 10-20, trayectorias, cuadro de mandos y exportación).
- [x] Tarea 8.2: Batería de benchmarks cuantitativos de rendimiento y precisión geométrica (error submilimétrico, sensibilidad/especificidad de colisiones y tiempos de respuesta).
- [x] Tarea 8.3: Manual de usuario clínico paso a paso en `dbv-specs-ops/docs/USER_MANUAL.md` (guía guiada de los 5 pasos quirúrgicos, tabla de códigos semafóricos y resolución de problemas).
- [x] Tarea 8.4: Estructura canónica y material técnico de la Memoria del TFG en `dbv-specs-ops/docs/MEMORIA_TFG_ESTRUCTURA.md` (formato oficial UMA / Grado en Ingeniería de la Salud con capítulos 1 a 6 y guión de defensa).

### Fase de Entrega y Cierre: Release v1.0.0 (/ship)
- [x] Actualización integral de `README.md` de la raíz con descripción de los 5 pasos quirúrgicos, badges, árbol de ficheros y enlaces a la documentación clínica y académica.
- [x] Cierre formal de `dbv-specs-ops/CHANGELOG.md` bajo la versión oficial `[1.0.0] — 2026-11-24`.
- [x] Redacción de `dbv-specs-ops/walkthrough.md` con el recorrido funcional integral y guía de evaluación para el tribunal de TFG.
- [x] Inclusión de `.Rhistory` en `.gitignore` para higiene del repositorio.
- [x] Verificación de la suite automatizada (49 tests pasando al 100% en Slicer Python).
- [x] Preparación de Git: commit `feat: release inicial SEEGPlanner v1.0.0 (TFG Ingeniería de la Salud)` y tag `v1.0.0`.

---

## 🔄 Snapshot de Contexto (Context Snapshot)

> **Última actualización:** 2026-11-24
> **Punto exacto:** PROYECTO TFG COMPLETADO Y ENTREGADO AL 100% (Versión oficial v1.0.0). Todas las fases del ciclo de vida de desarrollo de software SDD (/spec, /plan, /build, /test, /code-simplify y /ship) han sido completadas con éxito.
> **Estado del software:** Módulo `SEEGPlanner` para 3D Slicer v5.12+ completamente funcional, probado con 49 tests automatizados pasando al 100% en 1.46s, manual clínico paso a paso redactado y estructura oficial de memoria académica lista para defensa.
> **Próximo paso:** Subida al repositorio remoto (`git push origin main --tags`) y preparación de la presentación ante el tribunal evaluador.
