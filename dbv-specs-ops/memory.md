# 🧠 Memory & Context — SEEGPlanner

> **Frontera de uso (Memory vs. Tasks):**
> - `task.md` → progreso **operativo**: checklist de tareas, Snapshot de Contexto (el paso exacto siguiente), y estado de la sesión.
> - `memory.md` → contexto **cualitativo y temático**: conocimiento persistente, decisiones técnicas profundas, lecciones, y el área del producto en foco.
>
> *Instrucción para la IA: Consulta este archivo al inicio de cada sesión para recuperar el hilo técnico.*

---

## 🎯 Contexto Activo

- **Proyecto:** SEEGPlanner (Extensión para 3D Slicer para planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía).
- **Autora:** Alejandra Viñegla Sánchez (Grado en Ingeniería de la Salud, UMA).
- **Tutores:** Víctor Manuel Smith Fernández, David Bueno Vallejo.
- **Estado actual del desarrollo:** Adopción a `dbv-specs-ops` finalizada. Especificaciones (`SPECIFICATIONS.md`) y Arquitectura (`ARCHITECTURE.md`) formalizadas. Iniciando Fase 2 (Estructura base de la extensión de 3D Slicer).
- **Foco inmediato:** Crear la estructura de extensión para 3D Slicer (`SEEGPlanner/`) con clase principal, widget Qt y lógica base probada en Slicer v5.12.4.

---

## 🏗️ Log de Decisiones Técnicas (ADR Ligero)

- **2026-10-14 — Elección de plataforma base (3D Slicer v5.12.4):** Se adopta 3D Slicer por ser el entorno biomédico de código abierto líder en investigación e intervencionismo guiado por imagen, dotado de soporte nativo para visualización 3D (VTK), procesamiento médico (ITK) y escena médica estándar (MRML).
- **2026-10-14 — Tipo de módulo (ScriptedLoadableModule en Python 3):** Se opta por un módulo programado en Python frente a C++ compilado para permitir máxima agilidad de desarrollo, facilidad de mantenimiento e integración con ecosistema científico (NumPy, SciPy) sin requerir compilación compleja en la máquina del usuario.
- **2026-10-14 — Protocolo de comunicación (OpenIGTLink):** Para el envío de datos de trayectoria a quirófano y neuronavegadores comerciales/abiertos, se fija OpenIGTLink (mediante `OpenIGTLinkIF` / `pyigtl`) por ser el estándar abierto internacional de referencia en robótica médica y neuronavegación.
- **2026-10-14 — Marco de referencia electrofisiológico (Sistema EEG 10-20):** Se formaliza el uso de los 4 fiduciales anatómicos de referencia (Nasion, Inion, LPA, RPA) para calcular de forma analítica/geodésica sobre la superficie del cuero cabelludo las coordenadas de los electrodos 10-20 como potenciales puntos de entrada óseos.
- **2026-10-14 — Adopción de SDD (dbv-specs-ops v2.9.0):** El desarrollo se estructura estrictamente mediante las 6 fases de ingeniería asistida por IA (`/spec` → `/plan` → `/build` → `/test` → `/code-simplify` → `/ship`) para asegurar calidad y trazabilidad exigidas en un TFG de Ingeniería de la Salud.

---

## ⚠️ Lecciones Aprendidas / Errores Evitados

- **[Aislamiento del Framework]**: Todos los archivos de control SDD se mantienen dentro del subdirectorio `dbv-specs-ops/`, manteniendo la raíz del espacio de trabajo limpia para el código de la extensión de 3D Slicer.
- **[Compatibilidad con Slicer MRML]**: Todas las líneas de trayectoria y puntos fiduciales deben modelarse utilizando la API moderna de Markups de Slicer (`vtkMRMLMarkupsFiducialNode`, `vtkMRMLMarkupsLineNode`), evitando clases obsoletas de versiones antiguas de Slicer.

---

## 🗺️ Mapa de Relaciones del Módulo

- `SEEGPlanner.py`: Punto de entrada de la extensión (`SEEGPlannerWidget` para la UI y `SEEGPlannerLogic` para orquestación de operaciones).
- `Logic/eeg_1020_calculator.py`: Algoritmo matemático para cálculo de puntos 10-20 a partir de Nz, Iz, LPA, RPA sobre la malla craneal.
- `Logic/trajectory_planner.py`: Cálculo de vectores de inserción, longitud, verificación de seguridad de ángulo óseo y colisiones.
- `Logic/igtlink_exporter.py`: Conector de comunicación OpenIGTLink y exportación a formatos estándar.
- `Testing/Python/SEEGPlannerTest.py`: Suite de tests ejecutables desde la interfaz de pruebas de Slicer.
