# SEEGPlanner (3D Slicer Extension)

[![Release](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/alejandravs/SEEGPlanner-3DSlicer/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/3D%20Slicer-v5.12%2B-green.svg)](https://www.slicer.org/)
[![Tests](https://img.shields.io/badge/tests-49%20passed%20(100%25)-brightgreen.svg)](SEEGPlanner/Testing/Python/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![UMA](https://img.shields.io/badge/UMA-Ingenier%C3%ADa%20de%20la%20Salud-purple.svg)](https://www.uma.es/)

> **Herramienta en 3D Slicer para la planificación asistida de cirugía de electrodos cerebrales profundos en estéreo-electroencefalografía (SEEG)**  
> **Autora:** Alejandra Viñegla Sánchez  
> **Tutores:** Dr. Víctor Manuel Smith Fernández, Dr. David Bueno Vallejo  
> **Institución:** Grado en Ingeniería de la Salud · Escuela Técnica Superior de Ingeniería de Telecomunicación / Informática · Universidad de Málaga (UMA)  
> **Licencia:** MIT (compatible con la licencia BSD de 3D Slicer)  
> **Framework de Desarrollo:** [dbv-specs-ops SDD v2.9.0](https://github.com/davidbuenov/dbv-specs-ops)

---

## 📖 Descripción General

**SEEGPlanner** es una extensión de código abierto desarrollada para la plataforma médica **3D Slicer** (v5.12+) concebida para asistir a neurocirujanos y epileptólogos en la planificación prequirúrgica de electrodos intracraneales de registro en pacientes diagnosticados con **epilepsia farmacorresistente**.

En el tratamiento de la epilepsia refractaria, la estéreo-electroencefalografía (SEEG) constituye el estándar de referencia para delimitar tridimensionalmente la *zona epileptógena (ZE)* antes de una resección curativa. No obstante, las estaciones comerciales actuales presentan elevados costes de licenciamiento, formatos propietarios cerrados y desconexión entre la topografía electroencefalográfica convencional y la anatomía neuroquirúrgica tridimensional.

SEEGPlanner resuelve estas limitaciones proporcionando un flujo de trabajo clínico estructurado en **5 pasos quirúrgicos secuenciales**, integrando:
- Control de calidad de resonancia magnética cerebral (MRI) en coordenadas estereotácticas.
- Extracción de la superficie craneal y proyección anatómica milimétrica del estándar electrofisiológico internacional **EEG 10-20**.
- Identificación y extracción de centroides de estructuras diana cerebrales profundas con protección activa frente a concavidades ventriculares.
- Cálculo paramétrico de trayectorias, distribución de anillos de registro, modelado 3D tubular del electrodo junto al perno guía de titanio y evaluación analítica continua de seguridad y colisiones multi-electrodo en $\mathcal{O}(1)$.
- Cuadro de mandos interactivo con semáforo de seguridad en tiempo real y recentrado automático de planos 2D/3D.
- Exportación estereotáctica multi-formato a estándares abiertos (JSON, CSV, Slicer Markups JSON v1.0.0) y transmisión de datos a quirófano mediante el protocolo médico binario **OpenIGTLink** (v1/v2) nativo en Python.

---

## 🏥 Flujo de Trabajo Clínico (5 Pasos Quirúrgicos)

La interfaz gráfica del módulo (`SEEGPlannerWidget`) organiza el procedimiento asistencial en 5 secciones desplegables guiadas:

```mermaid
flowchart LR
    P1["Paso 1: Validación MRI"] --> P2["Paso 2: Rejilla 10-20"]
    P2 --> P3["Paso 3: Dianas Quirúrgicas"]
    P3 --> P4["Paso 4: Trayectorias & Seguridad"]
    P4 --> P5["Paso 5: Exportación & OpenIGTLink"]
```

### 1. Validación Neuroanatómica MRI
- **Inspección de Vóxel:** Evaluación estereotáctica del volumen T1/T2 (dimensiones matriciales, orientación y verificación de resolución diagnóstica submilimétrica o isotrópica $\le 1.5$ mm).
- **Alineación Ortogonal:** Recentrado y ajuste automático de las ventanas axiales, coronales y sagitales sobre el campo de visión cerebral.

### 2. Superficie Craneal y Rejilla EEG 10-20
- **Asistente de Fiduciales Anatómicos:** Colocación guiada de los 4 puntos craneales canónicos: Nasion ($Nz$), Inion ($Iz$), Preauricular Izquierdo ($LPA$) y Preauricular Derecho ($RPA$).
- **Extracción de Isosuperficie Cefálica:** Generación de malla poligonal mediante `vtkFlyingEdges3D` (con respaldo en `vtkMarchingCubes`), filtrado de componentes no conexos (`vtkPolyDataConnectivityFilter`), suavizado anti-aliasing sinc y orientación determinística de vectores normales hacia el exterior.
- **Proyección por Trazado de Rayos (*Ray-Casting*):** Mapeo de los 21 canales electroencefalográficos estándar 10-20 sobre la convexidad cutánea del paciente mediante aceleración espacial jerárquica con `vtkOBBTree`.

### 3. Localización de Estructuras Diana Cerebrales
- **Extracción de Segmentaciones:** Conexión directa con nodos `vtkMRMLSegmentationNode` procedentes de segmentadores automáticos (FreeSurfer, FastSurfer, TotalSegmentator) o delineación manual.
- **Centroide Robusto ante Concavidades:** Cálculo del centro de masa anatómico con comprobación estricta de inclusión. Si la geometría es cóncava (p. ej. hipocampo o corteza insular) y el centroide promedio cae en líquido cefalorraquídeo ventricular, el algoritmo lo proyecta automáticamente al vóxel parenquimatoso interior más cercano.

### 4. Trazado de Trayectorias y Verificación de Seguridad
- **Cálculo Estereotáctico:** Definición de vector director tridimensional, longitud de inserción milimétrica y orientación.
- **Distribución de Contactos de Registro:** Disposición distal a proximal de contactos de platino-iridio (diámetro 0.8 mm, 2.0 mm de longitud, paso de 1.5 o 3.5 mm) según especificaciones de fabricantes líderes (DIXI Medical, PMT Corporation).
- **Modelado 3D de Perno Guía y Electrodo:** Creación de malla poligonal combinada con `vtkTubeFilter` (tubo parenquimatoso y tornillo óseo coaxial de $2.5$ mm de diámetro y $15$ mm de longitud).
- **Verificación Biomecánica de Inserción Ósea:** Evaluación del ángulo respecto a la normal del cráneo para prevenir el resbalamiento del fresado ($\theta < 30^\circ$: verde; $\theta \ge 30^\circ$: ámbar).
- **Detección Analítica de Colisiones:** Algoritmo continuo exacto de distancia mínima entre segmentos 3D en $\mathcal{O}(1)$ para detectar conflictos de pernos óseos ($< 10.0$ mm) y proximidad parenquimatosa ($< 3.0$ mm).
- **Cuadro de Mandos Central:** Tabla interactiva con semáforo de seguridad, sub-tabla detallada de contactos, recentrado ortogonal dinámico y eliminación limpia de nodos MRML sin dejar elementos huérfanos.

### 5. Exportación Quirúrgica y Conector OpenIGTLink
- **Formatos Abiertos:** Exportación a JSON estructurado, CSV quirúrgico (resumen por electrodo y desglosado por contacto) y Slicer Markups JSON oficial (`.mrk.json` v1.0.0).
- **Sistemas de Coordenadas Médicas:** Transformación matemática paramétrica entre el espacio nativo de Slicer (RAS: Right-Anterior-Superior) y el estándar médico/robótico (LPS: Left-Posterior-Superior utilizado por DICOM, robots ROSA y estaciones Brainlab/Medtronic).
- **Protocolo OpenIGTLink Nativo:** Implementación pura en Python sin dependencias binarias externas; cálculo de checksum CRC-64 ECMA-182, empaquetado binario de cabecera (58 bytes) y mensajes de tipo `TRANSFORM` y `POINT`.
- **Transmisión de Red Segura:** Cliente con sockets no bloqueantes y timeout estricto ($\le 2.0$ s) que garantiza la fluidez total de la interfaz gráfica ante desconexiones.

---

## 🚀 Inicio Rápido

### Requisitos del Sistema
- **Sistema Operativo:** macOS (Apple Silicon / Intel), Linux (Ubuntu 20.04+, Debian, Fedora) o Windows 10/11 (64-bit).
- **3D Slicer:** Versión 5.12.0 o superior (validado en v5.12.3 y v5.12.4).
- **Python:** 3.12+ (incluido de forma embebida en 3D Slicer).

### Opción A: Ejecución Directa mediante Scripts Multiplataforma

El repositorio incluye lanzadores automatizados que localizan la instalación de 3D Slicer e inician la sesión con el módulo precargado:

- **macOS / Linux:**
  ```bash
  chmod +x start.sh stop.sh
  ./start.sh
  ```
  *(Para detener las instancias activas de Slicer: `./stop.sh`)*

- **Windows:**
  ```cmd
  start.cmd
  ```
  *(Para detener las instancias activas de Slicer: `stop.cmd`)*

### Opción B: Instalación Manual en 3D Slicer (Modo Desarrollador)

1. Iniciar **3D Slicer**.
2. Acceder al menú: **Edit** > **Application Settings** > **Modules**.
3. En la sección **Additional module paths**, hacer clic en **Add** y seleccionar el directorio del módulo:
   ```text
   /ruta/al/proyecto/SEEGPlanner/
   ```
4. Confirmar con **OK** y reiniciar 3D Slicer cuando la aplicación lo solicite.
5. El módulo se encontrará disponible en el selector de categorías de Slicer:
   ```text
   Modules > Neurosurgery > SEEG Planner
   ```

---

## 🧪 Pruebas Automatizadas y Validación

El proyecto cuenta con una suite completa de **49 pruebas automatizadas** que garantizan la robustez numérica, la exactitud geométrica y la estabilidad del sistema:

| Módulo de Pruebas | Fichero | Tests | Cobertura / Objetivo |
| :--- | :--- | :---: | :--- |
| **Lógica Base y Result** | `test_logic_standalone.py` | 5 | Patrón `Result` (`Ok`/`Err`), tipos y cálculo trigonométrico |
| **Gestión de Dianas** | `test_targets_standalone.py` | 6 | Metadatos de vóxel, centroides RAS y protección ante concavidades |
| **Superficie y 10-20** | `test_surface_standalone.py` | 6 | Extracción con FlyingEdges3D, normales exteriores y trazado de rayos |
| **Trayectorias y Seguridad** | `test_trajectories_standalone.py` | 12 | Distribución de contactos, tubo VTK, distancia segmento 3D y colisiones |
| **Cuadro de Mandos / UI** | `test_ui_logic_standalone.py` | 6 | Lógica de la tabla interactiva, semáforo, recentrado y purga de nodos |
| **Exportación & OpenIGTLink**| `test_export_standalone.py` | 11 | CRC-64 ECMA-182, cabecera de 58 bytes, RAS vs LPS y sockets de red |
| **Pipeline de Validación E2E**| `test_validation_pipeline.py` | 3 | Flujo quirúrgico completo, benchmarks de latencia y precisión submilimétrica |
| **Total Suite** | | **49** | **100% de tests pasando** |

### Ejecución de Pruebas Unitarias Standalone (Entorno Slicer Python)
```bash
# En macOS:
PYTHONHOME=/Applications/Slicer.app/Contents/lib/Python \
PYTHONPATH=/Applications/Slicer.app/Contents/bin/Python:/Applications/Slicer.app/Contents/lib/Slicer-5.12:/Applications/Slicer.app/Contents/lib/Python/lib/python3.12:/Applications/Slicer.app/Contents/lib/Python/lib/python3.12/lib-dynload:/Applications/Slicer.app/Contents/lib/Python/lib/python3.12/site-packages \
DYLD_LIBRARY_PATH=/Applications/Slicer.app/Contents/bin:/Applications/Slicer.app/Contents/lib/Slicer-5.12:/Applications/Slicer.app/Contents/lib/Python/lib \
/Applications/Slicer.app/Contents/bin/python-real -m unittest discover -s SEEGPlanner/Testing/Python -p "test_*.py"
```

### Ejecución de Pruebas Integradas dentro de la Escena de 3D Slicer
```bash
/Applications/Slicer.app/Contents/MacOS/Slicer --no-splash --testing --python-script "SEEGPlanner/Testing/Python/run_slicer_test.py"
```

---

## 📂 Estructura del Repositorio

```text
.
├── LICENSE                                    # Licencia oficial de código abierto (MIT)
├── README.md                                  # Documentación principal del proyecto (este archivo)
├── ReferenciaTecnica.md                       # Documento técnico maestro del estudiante y bitácora
├── start.sh / stop.sh                         # Scripts de ejecución rápida para macOS y Linux
├── start.cmd / stop.cmd                       # Scripts de ejecución rápida para Windows
├── SEEGPlanner/                               # Código fuente de la extensión para 3D Slicer
│   ├── CMakeLists.txt                         # Descriptor de compilación y empaquetado para Slicer
│   ├── SEEGPlanner.py                         # Módulo principal (UI Qt/CTK, Logic MRML y SEEGPlannerTest)
│   ├── README.md                              # Documentación técnica interna de la extensión
│   ├── Resources/
│   │   └── Icons/
│   │       └── SEEGPlanner.png                # Icono institucional del módulo (vectorial rasterizado)
│   ├── Logic/                                 # Lógica algorítmica desacoplada (Zero-GUI)
│   │   ├── __init__.py                        # Exportador del paquete lógico
│   │   ├── result.py                          # Patrón Result estricto (Ok[T], Err)
│   │   ├── target_manager.py                  # Detección y corrección de dianas anatómicas
│   │   ├── skull_surface_extractor.py         # Extracción de isosuperficie craneal y normales
│   │   ├── eeg_1020_calculator.py             # Algoritmo de mapeo 10-20 y ray-casting (OBBTree)
│   │   ├── trajectory_planner.py              # Cálculo de trayectorias, mallas VTK y colisiones
│   │   └── igtlink_exporter.py                # Serializadores JSON/CSV/Markups y protocolo OpenIGTLink
│   └── Testing/
│       └── Python/                            # Banco de pruebas automatizadas
│           ├── run_slicer_test.py             # Lanzador de pruebas headless en 3D Slicer
│           ├── test_logic_standalone.py       # Tests de lógica matemática base
│           ├── test_targets_standalone.py     # Tests de dianas y metadatos de volumen
│           ├── test_surface_standalone.py     # Tests de extracción de cráneo y trazado de rayos
│           ├── test_trajectories_standalone.py# Tests de trayectorias, contactos y colisiones
│           ├── test_ui_logic_standalone.py    # Tests de lógica del cuadro de mandos clínico
│           ├── test_export_standalone.py      # Tests de exportadores y protocolo OpenIGTLink
│           └── test_validation_pipeline.py    # Pipeline de validación clínica end-to-end
└── dbv-specs-ops/                             # Framework de Especificaciones y Operaciones (SDD v2.9.0)
    ├── project.config.md                      # Ficha de identidad y configuración del proyecto
    ├── CHANGELOG.md                           # Registro histórico de versiones y cambios (v1.0.0)
    ├── walkthrough.md                         # Resumen del recorrido funcional y guía de evaluación
    ├── task.md                                # Cuaderno de bitácora y backlog del proyecto
    ├── memory.md                              # Memoria persistente cualitativa y Decisiones de Arquitectura (ADR)
    ├── implementation_plan.md                 # Planes de implementación técnica por fases
    └── docs/                                  # Documentación técnica, clínica y académica
        ├── SPECIFICATIONS.md                  # Especificaciones funcionales y requisitos clínicos (SRS)
        ├── ARCHITECTURE.md                    # Arquitectura de software y decisiones de ingeniería
        ├── DESIGN.md                          # Guía de estilo visual y componentes clínicos
        ├── USER_MANUAL.md                     # Manual de Usuario Clínico paso a paso para quirófano
        └── MEMORIA_TFG_ESTRUCTURA.md          # Estructura oficial de la Memoria Académica del TFG (UMA)
```

---

## 📚 Documentación Técnica y Académica

El proyecto cuenta con documentación técnica exhaustiva para usuarios clínicos, desarrolladores y el tribunal evaluador:

- 📖 **[Manual de Usuario Clínico (USER_MANUAL.md)](dbv-specs-ops/docs/USER_MANUAL.md):** Guía paso a paso ilustrada con el procedimiento quirúrgico, código semafórico de seguridad y resolución de incidencias en quirófano.
- 🎓 **[Estructura de la Memoria del TFG (MEMORIA_TFG_ESTRUCTURA.md)](dbv-specs-ops/docs/MEMORIA_TFG_ESTRUCTURA.md):** Memoria académica formal ajustada a la normativa de la Universidad de Málaga (Grado en Ingeniería de la Salud), con formulación matemática, comparativa comercial frente a ROSA/Surgiplan y guión de defensa ante el tribunal.
- 📝 **[Recorrido y Guía de Evaluación (walkthrough.md)](dbv-specs-ops/walkthrough.md):** Resumen integral de la entrega v1.0.0 y pautas para la inspección y verificación del software.
- 🔬 **[Referencia Técnica Maestro (ReferenciaTecnica.md)](ReferenciaTecnica.md):** Bitácora técnica y fundamentos científicos del proyecto.
- 📋 **[Especificaciones del Sistema (SPECIFICATIONS.md)](dbv-specs-ops/docs/SPECIFICATIONS.md):** Requisitos funcionales (RF) y no funcionales (RNF) formales.
- 🏛️ **[Arquitectura de Software (ARCHITECTURE.md)](dbv-specs-ops/docs/ARCHITECTURE.md):** Patrones de diseño, separación de responsabilidades y flujo de datos MRML.

---

## 👥 Créditos y Agradecimientos

- **Autora:** Alejandra Viñegla Sánchez (`alejandravs`) — Estudiante del Grado en Ingeniería de la Salud, Universidad de Málaga.
- **Tutor Principal:** Dr. Víctor Manuel Smith Fernández — Departamento de Ingeniería de Comunicaciones, Universidad de Málaga.
- **Cotutor y Metodología:** Dr. David Bueno Vallejo — Departamento de Lenguajes y Ciencias de la Computación, Universidad de Málaga.
- **Agradecimientos:** A la comunidad internacional de **3D Slicer** y del consorcio **NA-MIC** (National Alliance for Medical Image Computing) por proporcionar una plataforma abierta excepcional para la investigación biomédica y la cirugía guiada por imagen.

---

> 🛠️ Proyecto desarrollado siguiendo la metodología **Spec-Driven Development (SDD)** con el framework **[dbv-specs-ops](https://github.com/davidbuenov/dbv-specs-ops)**, creado por [David Bueno Vallejo](https://github.com/davidbuenov) — libre y gratuito.
