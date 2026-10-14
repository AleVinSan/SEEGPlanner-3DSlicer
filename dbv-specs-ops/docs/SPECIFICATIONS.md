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
  - Carga fluida de imágenes de resonancia magnética cerebral (formatos DICOM y NIfTI / NRRD).
  - Configuración de visualización ortogonal 2D (Axial, Sagital, Coronal) y reconstrucción volumétrica 3D.
- [ ] **RF-02: Segmentación Asistida/Automática de Estructuras Diana** `[CONFIRMADO]`
  - Integración o acoplamiento con herramientas de segmentación cerebral (e.g., SynthSeg / TotalSegmentator o atlas de Slicer Segment Editor).
  - Generación de modelos de superficie 3D de las dianas cerebrales para cálculo de distancias y visualización.
- [ ] **RF-03: Mapeo Geométrico del Sistema EEG 10-20** `[CONFIRMADO]`
  - Entrada interactiva de referencias anatómicas canónicas: Nasion (Nz), Inion (Iz), Tragus/Preauricular izquierdo (LPA) y derecho (RPA).
  - Algoritmo de cálculo sobre la malla o contorno de la cabeza: arcos sagital, coronal y circunferencial según proporciones del 10% y 20%.
  - Marcado visual de los nodos del sistema 10-20 (Fp1, Fp2, Fz, Cz, Pz, Oz, T3/T7, T4/T8, etc.) como `vtkMRMLMarkupsFiducialNode`.
- [ ] **RF-04: Cálculo y Trazado de Trayectorias de Electrodos** `[CONFIRMADO]`
  - Definición de pares entrada-diana (Entry point - Target point).
  - Representación tridimensional de los electrodos como tubos o líneas 3D con calibre milimétrico ajustable.
  - Cálculo analítico de métricas: longitud total de trayectoria intra y extracraneal, vector director y ángulos en espacio estereotáctico.
- [ ] **RF-05: Validación de Seguridad Quirúrgica y Ángulo Óseo** `[CONFIRMADO]`
  - Cálculo del ángulo de incidencia respecto a la normal de la superficie ósea/craneal en el punto de inserción (para asegurar estabilidad de los pernos o pernos guía, típicamente < 30° respecto a la normal).
  - Alerta visual en caso de trayectorias demasiado oblícuas o colisiones con estructuras críticas.
- [ ] **RF-06: Interfaz Gráfica (GUI) en 3D Slicer** `[CONFIRMADO]`
  - Panel integrado en la barra de herramientas de 3D Slicer desarrollado con Qt (`qMRMLWidget`).
  - Flujo guiado por pestañas o pasos: 1) Carga de datos, 2) Fiduciales anatómicos y 10-20, 3) Dianas, 4) Trayectorias, 5) Exportación.
- [ ] **RF-07: Exportación de Datos a Neuronavegación** `[CONFIRMADO]`
  - Comunicación mediante protocolo OpenIGTLink (soporte de mensajes `TRANSFORM`, `POINT` / `FIDUCIAL`) hacia neuronavegadores o simuladores quirúrgicos.
  - Exportación local de metadatos de trayectoria en formatos abiertos (JSON, CSV, Markups JSON).
- [ ] **RF-08: Banco de Pruebas y Validación** `[CONFIRMADO]`
  - Verificación sobre imágenes MRI cerebrales anonimizadas procedentes de repositorios abiertos (e.g. OASIS, OpenNeuro, Slicer Sample Data).

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

- [x] ¿Versión de 3D Slicer disponible en el equipo de desarrollo? -> **Confirmado: 3D Slicer v5.12.4**.
- [x] ¿Origen de las imágenes para pruebas? -> **Confirmado: Repositorios abiertos de MRI cerebral anonimizadas**.
- [ ] ¿Se prefiere que el módulo genere una superficie del cráneo automáticamente mediante umbralización (thresholding/marching cubes) o a partir de una segmentación ya cargada por el usuario? `[PENDIENTE]`
- [ ] ¿Qué nomenclatura estándar de electrodos se adoptará para nombrar los canales de registro SEEG (nombres clásicos de electrodos A, B, C... o según punto 10-20 de entrada)? `[PENDIENTE]`

---

## 🧪 7. Criterios de Evaluación y Aceptación

- [ ] **Precisión de posicionamiento 10-20:** El algoritmo calcula las posiciones estándar en menos de 3 segundos con un error geométrico relativo coherente con la literatura internacional (Jurcak et al.).
- [ ] **Cálculo de trayectorias:** El trazado 3D refleja con precisión submilimétrica la diana y el punto de entrada, reportando longitud y ángulo óseo exactos.
- [ ] **Pruebas automáticas (Slicer Self-Test):** La suite de pruebas integrada en `SEEGPlannerTest` se ejecuta en el entorno de pruebas de Slicer sin arrojar excepciones ni memory leaks en los nodos MRML.