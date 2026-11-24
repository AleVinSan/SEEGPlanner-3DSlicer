# 📋 Especificaciones: SEEGPlanner (Extensión 3D Slicer)

> **Proyecto:** Desarrollo de una herramienta en 3D Slicer para la planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía.
> **Autora:** Alejandra Viñegla Sánchez
> **Tutores:** Víctor Manuel Smith Fernández, David Bueno Vallejo
> **Fase:** `/spec` (Especificación)
> **Estado:** Validado
> **Última Revisión:** 2026-10-14

---

## 🎯 1. Contexto y Objetivos

- **Problema:** `[CONFIRMADO]` La estereoelectroencefalografía (SEEG) es una técnica neuroquirúrgica mínimamente invasiva esencial para delimitar la zona epileptógena en pacientes con epilepsia farmacorresistente candidatos a resección quirúrgica. Sin embargo, conlleva riesgos clínicos graves, principalmente hemorragias por lesión vascular (incidencia ~1% de pacientes). En la práctica clínica, la planificación de trayectorias se realiza de forma manual en estaciones de neuronavegación comerciales propietarias y costosas, resultando en un proceso lento, subjetivo y dependiente del especialista. Además, existe una desconexión metodológica entre los datos electrofisiológicos preoperatorios (mapeo según el estándar EEG 10-20) y los sistemas de posicionamiento tridimensional.
- **Objetivo General (Éxito):** `[CONFIRMADO]` Desarrollar un módulo/extensión libre, modular y reproducible en **3D Slicer** que automatice y asista la planificación prequirúrgica de trayectorias de electrodos intracraneales SEEG, uniendo las posiciones estándar del sistema EEG 10-20 sobre la cabeza del paciente con las estructuras diana cerebrales profundas, garantizando parámetros de seguridad y permitiendo exportar las trayectorias hacia neuronavegadores de quirófano mediante protocolos abiertos como OpenIGTLink.

---

## 👥 2. Usuarios y Escenarios

- **Perfil de Usuario:** `[CONFIRMADO]` Neurocirujanos, neurólogos/epileptólogos e ingenieros biomédicos / de la salud involucrados en la planificación prequirúrgica de epilepsia.
- **Escenarios Clave:**
  - *Escenario 1 (Segmentación de Dianas):* `[CONFIRMADO]` El especialista carga una resonancia magnética (MRI T1/T2) del paciente y el sistema localiza/delimita automáticamente las estructuras anatómicas diana (hipocampo, amígdala, cortex insular, etc.) sin requerir delineación manual voxel a voxel.
  - *Escenario 2 (Fiduciales y Mapeo 10-20):* `[CONFIRMADO]` El usuario define o valida cuatro puntos de referencia anatómicos básicos en la cabeza (Nasion, Inion, LPA - preauricular izquierdo, RPA - preauricular derecho) y el sistema proyecta automáticamente la rejilla internacional de electrodos EEG 10-20 sobre la superficie cutánea/craneal del paciente como potenciales puntos de entrada quirúrgica.
  - *Escenario 3 (Cálculo de Trayectoria y Verificación de Seguridad):* `[CONFIRMADO]` El cirujano selecciona un punto de entrada (electrodo 10-20) y una diana anatómica profunda; el módulo traza la trayectoria en 3D, evalúa la longitud, el ángulo de entrada en el hueso craneal (garantizando perpendicularidad para la fijación estable de los tornillos guía) y verifica la distancia mínima a zonas vasculares críticas para prevenir hemorragias.
  - *Escenario 4 (Exportación Quirúrgica):* `[CONFIRMADO]` El plan final validado es transmitido a la estación de neuronavegación del quirófano a través de OpenIGTLink en tiempo real o exportado a archivos estandarizados (Fiducials / Markups / JSON).

---

## ✨ 3. Funcionalidades Principales (Requisitos del Software)

### Requisitos Funcionales (RF)

- [ ] **RF-01: Carga y Gestión de Volúmenes Neuroanatómicos** `[CONFIRMADO]`
  - Carga y verificación de imágenes de resonancia magnética cerebral (formatos DICOM, NIfTI y NRRD) como `vtkMRMLScalarVolumeNode`.
  - Validación de metadatos clínicos: espaciado de vóxeles (voxel spacing, idealmente $\le 1.5$ mm para cirugía estereotáctica), orientación del espacio del paciente (RAS) y dimensiones volumétricas.
  - Ajuste y recentrado automático de vistas ortogonales 2D (Axial, Sagital, Coronal) sobre el volumen de referencia.
- [ ] **RF-02: Segmentación y Gestión de Estructuras Diana Cerebrales** `[CONFIRMADO]`
  - Integración con nodos de segmentación `vtkMRMLSegmentationNode` (procedentes de `Segment Editor`, `SynthSeg`, `TotalSegmentator` o atlas neuroanatómicos).
  - Algoritmo de cálculo de centroides tridimensionales ponderados en espacio RAS ($C_{\text{RAS}}$) para cada segmento de diana (hipocampo, amígdala, ínsula, cortex temporal/frontal).
  - Cálculo de métricas morfométricas del segmento: volumen total en $\text{mm}^3$ y caja delimitadora (*bounding box*).
  - Generación y marcado automático de dianas quirúrgicas en la escena médica como `vtkMRMLMarkupsFiducialNode` vinculadas directamente al selector de dianas del planificador de trayectorias.
- [ ] **RF-03: Mapeo Geométrico del Sistema EEG 10-20 sobre la Superficie Craneal** `[CONFIRMADO]`
  - Captura y ajuste interactivo de referencias anatómicas canónicas: Nasion (Nz), Inion (Iz), Preauricular izquierdo (LPA) y Preauricular derecho (RPA) sobre el visor 3D o cortes ortogonales.
  - Extracción automática de la superficie cutánea/craneal (`vtkMRMLModelNode` con `vtkPolyData`) mediante umbralización adaptativa y algoritmos de isosuperficie (*Flying Edges* / *Marching Cubes*), con cálculo de normales de superficie orientadas al exterior.
  - Algoritmo de cálculo de arcos sagital, coronal y circunferencial según estándar 10-20 y proyección por trazado de rayos (ray-casting) sobre la malla tridimensional del paciente.
  - Generación del conjunto completo de electrodos 10-20 como `vtkMRMLMarkupsFiducialNode` (Fpz, Fz, Cz, Pz, Oz, Fp1, Fp2, F7, F3, F4, F8, T3, C3, C4, T4, T5, P3, P4, T6, O1, O2) listos como candidatos a puntos de entrada quirúrgicos.
- [ ] **RF-04: Cálculo y Trazado de Trayectorias de Electrodos con Calibre 3D y Contactos** `[CONFIRMADO]`
  - Definición y emparejamiento interactivo de pares Entrada (punto 10-20 o fiducial craneal) y Diana (centroide anatómico en `SEEG_Targets`).
  - Representación tridimensional dual en 3D Slicer: eje estereotáctico central (`vtkMRMLMarkupsLineNode`) y modelo tubular 3D volumétrico (`vtkMRMLModelNode` mediante `vtkTubeFilter`) con calibre milimétrico ajustable (diámetro nominal 0.8 mm, radio 0.4 mm).
  - Cálculo y modelado de contactos de registro electrofisiológico: distribución analítica de contactos cilíndricos a lo largo del electrodo desde la punta diana (8 a 18 contactos con longitud y espaciado milimétrico configurable, ej. 2.0 mm longitud, 1.5 mm espacio inter-contacto).
  - Cálculo de métricas estereotácticas completas: longitud total de trayectoria ($L$), vector unitario director ($\mathbf{u}$), coordenadas RAS de entrada/diana y profundidad de penetración.
- [ ] **RF-05: Validación de Seguridad Quirúrgica, Ángulo Óseo y Conflicto entre Pernos** `[CONFIRMADO]`
  - Validación de estabilidad biomecánica de inserción ósea: cálculo del ángulo de desviación respecto a la normal exterior del cráneo en el punto de entrada ($\theta = \arccos(|\mathbf{u} \cdot \mathbf{n}_{\text{cráneo}}|) \le 30^\circ$). Alerta en caso de $\theta > 30^\circ$ por riesgo de deslizamiento de la broca quirúrgica o inestabilidad del perno de anclaje (*anchor bolt*).
  - Modelado geométrico del perno guía craneal: collarín/cilindro exterior coaxial de fijación ósea (diámetro externo 2.5 mm, longitud 15 mm) en el punto de entrada.
  - Verificación de distancia de seguridad entre múltiples electrodos (*conflict detection*): cálculo de distancia euclídea mínima entre pernos en superficie craneal ($d_{\text{entry}} \ge 10$ mm) y distancia mínima entre segmentos de trayectoria 3D ($d_{\text{inter}} \ge 3$ mm) para evitar colisiones mecánicas y artefactos de registro.
  - Indicadores visuales y semáforo de seguridad (verde = óptimo; amarillo = alerta moderada; rojo = crítico por ángulo o proximidad peligrosa).
- [ ] **RF-06: Interfaz Gráfica Avanzada (GUI) y Cuadro de Mandos Clínico en 3D Slicer** `[CONFIRMADO]`
  - Panel integrado en la barra de módulos de 3D Slicer desarrollado con componentes nativos de Qt/CTK (`qMRMLWidget`, `ctkCollapsibleButton`, `QTableWidget`).
  - Flujo quirúrgico guiado estructurado en 4 secciones secuenciales con estado visible:
    1. *Datos de Paciente & MRI*: Inspección de resolución de vóxel, volumen y centrado ortogonal 2D.
    2. *Geometría Cefálica & EEG 10-20*: Asistente de captura de fiduciales canónicos (Nz, Iz, LPA, RPA), generación de superficie 3D semitransparente y proyección por ray-casting.
    3. *Dianas Anatómicas & Parámetros de Electrodo*: Selector de segmentación, tabla de centroides, controles de calibre (0.4 - 2.5 mm), número de contactos (4 - 18) y longitud de perno guía (5 - 30 mm).
    4. *Cuadro de Mandos Clínico & Seguridad Multi-Electrodo*: Dashboard central de gestión del plan quirúrgico.
  - Tabla interactiva de electrodos planificados: columnas estructuradas (ID, Entrada, Diana, Longitud mm, Ángulo con normal ósea, Contactos y Estado semafórico).
  - Sincronización y navegación interactiva: selección de fila para centrar vistas ortogonales 2D y destacar el electrodo en la vista 3D.
  - Desglose detallado de contactos de registro: sub-tabla o visor de coordenadas RAS y distancia a la punta para el electrodo activo.
  - Gestión del plan: eliminación de trayectorias con eliminación limpia de sus correspondientes nodos `vtkMRMLMarkupsLineNode` y `vtkMRMLModelNode` en la escena médica, y botón de auditoría global de conflictos espaciales.
- [ ] **RF-07: Exportación de Datos a Neuronavegación y Formatos Quirúrgicos Abiertos** `[CONFIRMADO]`
  - **RF-07.1 (Exportación JSON Estructurado):**
    - Serialización completa del plan quirúrgico a archivo JSON estandarizado con metadatos del paciente, fecha/hora, versión de esquema y sistema de coordenadas (RAS / LPS configurable).
    - Inclusión por cada electrodo de: nombre, puntos 3D de entrada y diana, longitud total en mm, ángulo con la normal ósea, bandera de seguridad, lista de conflictos detectados, configuración de electrodo y perno (diámetros y longitudes), detalle completo de contactos de registro (etiqueta E01..En, distancia distal y coordenadas RAS/LPS) y matriz de transformación homogénea 4x4.
  - **RF-07.2 (Exportación Tabular CSV Quirúrgico):**
    - Generación de archivo CSV para integración directa con hojas de planificación quirúrgica y sistemas robóticos/estereotácticos (Leksell, CRW, ROSA).
    - Columnas estándar: `Electrode,Entry_R,Entry_A,Entry_S,Target_R,Target_A,Target_S,Length_mm,Angle_deg,Safe,NumContacts,Contacts_Summary`.
    - Modo detallado opcional con desglose fila por fila de cada contacto: `Electrode,Contact_Index,Contact_Label,Dist_Tip_mm,Coord_R,Coord_A,Coord_S`.
  - **RF-07.3 (Exportación a Markups JSON Canónico de 3D Slicer):**
    - Generación de archivos `.mrk.json` conformes con el esquema oficial Markups v1.0.0 de 3D Slicer (`vtkMRMLMarkupsLineNode` para trayectorias y `vtkMRMLMarkupsFiducialNode` para contactos).
    - Permite la importación y visualización inmediata del plan quirúrgico en cualquier estación de 3D Slicer estándar arrastrando y soltando el archivo.
  - **RF-07.4 (Conector de Red Abierto OpenIGTLink):**
    - Empaquetado binario estricto conforme a la especificación de protocolo OpenIGTLink (cabecera de 58 bytes big-endian con CRC64 ECMA-182).
    - Soporte de mensajes `TRANSFORM` (matriz 4x4) y `POINT` (coordenadas de entrada, diana y contactos).
    - Cliente de red puro en Python mediante sockets no bloqueantes con timeout configurable (evitando bloqueos de la interfaz de usuario en caso de desconexión).
    - Interoperabilidad opcional con el módulo `OpenIGTLinkIF` de 3D Slicer si está disponible en la sesión activa.
  - **RF-07.5 (Interfaz de Usuario de Exportación):**
    - Controles interactivos en `SEEGPlannerWidget`: selector de formato, selector de convención de coordenadas (RAS / LPS), selector de archivo de salida y botones de exportación a disco y transmisión en red por OpenIGTLink con retroalimentación inmediata de éxito o error.
- [ ] **RF-08: Banco de Pruebas, Validación Cuantitativa, Manual de Usuario y Memoria del TFG** `[CONFIRMADO]`
  - **RF-08.1 (Validación sobre Datasets de Resonancia Magnética Cerebral):**
    - Protocolo de prueba y validación end-to-end sobre volúmenes cerebrales reales y de referencia anatómica (espaciado $\le 1.5$ mm): verificación de resolución diagnóstica, extracción de centroides diana protegidos ante concavidades ventriculares, generación de superficie craneal con normales exteriores, proyección de rejilla 10-20 con aceleración `vtkOBBTree`, planificación multi-electrodo con pernos y contactos, auditoría de conflictos y exportación multi-formato con transmisión OpenIGTLink.
  - **RF-08.2 (Evaluación Cuantitativa de Precisión, Repetibilidad y Rendimiento):**
    - Benchmarks y análisis cuantitativo de precisión geométrica (error de longitud $< 0.05$ mm, error de ángulo óseo $< 0.1^\circ$), repetibilidad determinística de centroides volumétricos ($100\%$ de contención en tejido diana) y tiempos de cómputo clínicos ($\le 2.0$ s en extracción de superficie, $\le 1.0$ s en proyección 10-20, $\le 50$ ms en evaluación de colisiones multi-electrodo).
  - **RF-08.3 (Manual de Usuario Clínico Paso a Paso):**
    - Redacción de guía de usuario integral (`docs/USER_MANUAL.md`) detallando paso a paso el flujo de trabajo en 3D Slicer con los 5 pasos quirúrgicos, descripción de controles, interpretación del semáforo visual (verde, ámbar, rojo) y resolución de incidencias.
  - **RF-08.4 (Estructura Canónica y Material de la Memoria del TFG):**
    - Redacción de la memoria técnica y estructura académica (`docs/MEMORIA_TFG_ESTRUCTURA.md`) conforme a las directrices oficiales de Trabajos de Fin de Grado de la Escuela Técnica Superior de Ingeniería de Telecomunicación / Grado en Ingeniería de la Salud de la Universidad de Málaga (UMA). Incluye resumen bilingüe, capítulos del 1 al 6 con justificación médica, fundamentos matemáticos, diseño software, resultados experimentales y conclusiones.

---

## 🚫 4. Fuera de Alcance (Out of Scope)

- `[CONFIRMADO]` **Navegación intraoperatoria con hardware propietario:** El plugin no controla directamente cámaras ópticas de tracking de quirófano (Polaris, etc.); la comunicación con ellos se delega a las estaciones de neuronavegación o al módulo `SlicerIGT` / `OpenIGTLinkIF`.
- `[CONFIRMADO]` **Diagnóstico automatizado de la zona epileptógena:** El software asiste en la planificación de la trayectoria física; la indicación clínica de qué zonas deben ser monitorizadas corresponde exclusivamente al criterio médico.
- `[CONFIRMADO]` **Actuación robótica autónoma directa:** No se envía control cinemático directo a brazos robóticos (e.g., ROSA), únicamente las coordenadas y vectores de trayectoria estereotáctica validados.

---

## ⚠️ 5. Riesgos y Mitigación

- **Riesgo 1: Variabilidad anatómica y colocación de fiduciales 10-20.**
  - *Mitigación:* Permitir al especialista un ajuste manual fino por arrastre de los fiduciales proyectados si la aproximación esférica/malla inicial tiene ligeras discrepancias morfológicas.
- **Riesgo 2: Dependencias externas complejas (modelos pesados de Deep Learning).**
  - *Mitigación:* Diseñar el núcleo del plugin desacoplado: permitir utilizar segmentaciones precomputadas de Slicer, o integrar modelos ligeros sin bloquear la instalación básica del módulo.
- **Riesgo 3: Compatibilidad de versiones de 3D Slicer.**
  - *Mitigación:* Desarrollar sobre la API moderna de Slicer (v5.12.4 / 5.x), utilizando la API canónica `slicer.vtkMRMLMarkupsFiducialNode` y `slicer.vtkMRMLMarkupsLineNode`.

---

## ❓ 6. Preguntas Abiertas

- [x] ¿Versión de 3D Slicer disponible en el equipo de desarrollo? -> **Confirmado: 3D Slicer v5.12.4 (v5.12.3 local compatible)**.
- [x] ¿Origen de las imágenes para pruebas? -> **Confirmado: Repositorios abiertos de MRI cerebral anonimizadas**.
- [x] ¿Se prefiere que el módulo genere una superficie del cráneo automáticamente mediante umbralización (thresholding/marching cubes) o a partir de una segmentación ya cargada por el usuario? -> **Confirmado: Se implementa extracción automática de superficie mediante umbralización adaptativa y Flying Edges/Marching Cubes, permitiendo opcionalmente utilizar un modelo poligonal preexistente.**
- [ ] ¿Qué nomenclatura estándar de electrodos se adoptará para nombrar los canales de registro SEEG (nombres clásicos de electrodos A, B, C... o según punto 10-20 de entrada)? `[PENDIENTE]`

---

## 🧪 7. Criterios de Evaluación y Aceptación

- [ ] **Precisión de posicionamiento 10-20:** El algoritmo calcula las posiciones estándar en menos de 3 segundos con un error geométrico relativo coherente con la literatura internacional (Jurcak et al.).
- [ ] **Cálculo de trayectorias:** El trazado 3D refleja con precisión submilimétrica la diana y el punto de entrada, reportando longitud y ángulo óseo exactos.
- [ ] **Pruebas automáticas (Slicer Self-Test):** La suite de pruebas integrada en `SEEGPlannerTest` se ejecuta en el entorno de pruebas de Slicer sin arrojar excepciones ni memory leaks en los nodos MRML.