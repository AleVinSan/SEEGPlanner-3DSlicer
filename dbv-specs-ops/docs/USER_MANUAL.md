# 📖 Manual de Usuario Clínico: SEEGPlanner (3D Slicer)

> **Trabajo de Fin de Grado:** Grado en Ingeniería de la Salud — Universidad de Málaga (UMA)  
> **Título:** *Desarrollo de una herramienta en 3D Slicer para la planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía*  
> **Autora:** Alejandra Viñegla Sánchez  
> **Tutores:** Víctor Manuel Smith Fernández, David Bueno Vallejo  
> **Versión:** 1.0.0 (Release Candidate)  
> **Framework:** dbv-specs-ops SDD v2.9.0  

---

## 📑 Índice del Manual

1. [Introducción y Justificación Clínica](#1-introducción-y-justificación-clínica)
2. [Requisitos del Sistema e Instalación](#2-requisitos-del-sistema-e-instalación)
3. [Flujo Quirúrgico Guiado en 5 Pasos](#3-flujo-quirúrgico-guiado-en-5-pasos)
   - [Paso 1: Datos de Paciente y Resonancia Magnética](#paso-1-datos-de-paciente-y-resonancia-magnética)
   - [Paso 2: Geometría Cefálica y Mapeo EEG 10-20](#paso-2-geometría-cefálica-y-mapeo-eeg-10-20)
   - [Paso 3: Localización de Dianas Cerebrales Profundas](#paso-3-localización-de-dianas-cerebrales-profundas)
   - [Paso 4: Cuadro de Mandos Clínico y Seguridad Multi-Electrodo](#paso-4-cuadro-de-mandos-clínico-y-seguridad-multi-electrodo)
   - [Paso 5: Exportación Quirúrgica y Transmisión OpenIGTLink](#paso-5-exportación-quirúrgica-y-transmisión-openigtlink)
4. [Semáforo Visual y Criterios de Seguridad](#4-semáforo-visual-y-criterios-de-seguridad)
5. [Guía de Resolución de Incidencias (Troubleshooting)](#5-guía-de-resolución-de-incidencias-troubleshooting)

---

## 1. Introducción y Justificación Clínica

La **estereoelectroencefalografía (SEEG)** es una técnica quirúrgica mínimamente invasiva esencial para delimitar la zona epileptógena en pacientes con **epilepsia farmacorresistente** candidatos a resección cerebral curativa.

### Objetivos Clínicos de SEEGPlanner
1. **Reducción del Riesgo Hemorrágico:** La implantación de múltiples electrodos intracraneales conlleva un riesgo hemorrágico vascular de aproximadamente el $1\%$. SEEGPlanner asiste al equipo neuroquirúrgico mediante verificación continua en 3D de trayectorias, distancias de seguridad parenquimatosa y holguras entre electrodos.
2. **Conexión Electrofisiológica Preoperatoria (EEG 10-20):** Los focos epileptogénicos se sospechan inicialmente a partir del electroencefalograma convencional de superficie. SEEGPlanner proyecta automáticamente las 21 posiciones de la rejilla estándar internacional EEG 10-20 sobre el cuero cabelludo real del paciente, estableciendo una correspondencia directa entre los canales de registro eléctrico y los puntos de entrada craneales.
3. **Estabilidad Biomecánica del Perno Óseo (Anchor Bolt):** Cada electrodo se fija al cráneo mediante un tornillo perno hueco roscado al hueso. Si la perforación es muy oblicua ($> 30^\circ$), el perno pierde agarre y la broca puede resbalar. SEEGPlanner calcula en tiempo real el ángulo entre el vector director de inserción y la normal exterior de la superficie ósea.
4. **Interoperabilidad Abierta y Quirófano Digital:** El software elimina la dependencia de costosas estaciones comerciales cerradas, permitiendo exportar el plan a formatos abiertos (JSON, CSV, Markups) o transmitirlo en tiempo real mediante el protocolo estándar **OpenIGTLink** a neuronavegadores (Medtronic StealthStation, Brainlab, ROSA).

---

## 2. Requisitos del Sistema e Instalación

### Requisitos Mínimos
* **Plataforma:** 3D Slicer versión 5.12.3 o superior (v5.12.4 recomendada).
* **Sistema Operativo:** macOS (Apple Silicon / Intel), Windows 10/11 (64-bit), o Linux (Ubuntu 20.04+).
* **Hardware:** 8 GB RAM (16 GB recomendado para volúmenes 3D de alta resolución), procesador multi-núcleo de 64 bits y tarjeta gráfica compatible con OpenGL 3.2+.

### Instalación de la Extensión en 3D Slicer
1. Abra **3D Slicer**.
2. Vaya al menú superior: **Edit** $\to$ **Application Settings** $\to$ **Modules**.
3. En la sección **Additional module paths**, pulse **Add** y seleccione la carpeta `SEEGPlanner/` del repositorio.
4. Reinicie 3D Slicer cuando se le solicite.
5. Acceda a la extensión desde el selector de módulos: **Modules** $\to$ **Stereotaxy** $\to$ **SEEGPlanner**.

---

## 3. Flujo Quirúrgico Guiado en 5 Pasos

La interfaz de `SEEGPlanner` está estructurada en un flujo de trabajo secuencial en 5 secciones colapsables (`ctkCollapsibleButton`), concebido para replicar la toma de decisiones clínicas preoperatorias:

```
┌────────────────────────────────────────────────────────┐
│  SEEGPlanner: Planificación Estereotáctica Quirúrgica  │
├────────────────────────────────────────────────────────┤
│  [1] Datos de Paciente & MRI                           │
│  [2] Geometría Cefálica & EEG 10-20                    │
│  [3] Dianas Cerebrales & Parámetros de Electrodo       │
│  [4] Cuadro de Mandos Clínico & Seguridad Multi-Elec.  │
│  [5] Exportación Quirúrgica & OpenIGTLink              │
└────────────────────────────────────────────────────────┘
```

---

### Paso 1: Datos de Paciente y Resonancia Magnética

Esta sección asegura el control de calidad radiológico previo a cualquier trazado estereotáctico.

1. **Selección del Volumen MRI:** En el menú desplegable `Volumen MRI (T1/T2):`, seleccione el nodo `vtkMRMLScalarVolumeNode` del paciente cargado en la escena (DICOM, NIfTI o NRRD).
2. **Tarjeta Diagnóstica de Calidad de Vóxel:**
   * El sistema analiza automáticamente las dimensiones de la matriz y el espaciado tridimensional ($\Delta x, \Delta y, \Delta z$).
   * *Criterio Estereotáctico:* Si la resolución espacial es $\le 1.5$ mm en todos los ejes, se muestra el indicador en verde (**Óptimo para cirugía estereotáctica**). Si supera $1.5$ mm, se emite una advertencia en ámbar indicando que la resolución puede reducir la precisión en dianas milimétricas.
3. **Recentrado 2D:** Pulse el botón **Centrar Vistas en Volumen** para alinear automáticamente los tres cortes ortogonales de Slicer (Axial, Sagital y Coronal) con el centro geométrico de la anatomía del paciente.

---

### Paso 2: Geometría Cefálica y Mapeo EEG 10-20

En este paso se reconstruye la superficie tridimensional de la cabeza y se calcula la disposición de los electrodos de superficie según el estándar internacional EEG 10-20.

1. **Referencias Anatómicas Canónicas:**
   * Para calibrar el sistema se requieren 4 puntos de referencia: **Nasion** ($N_z$), **Inion** ($I_z$), **Preauricular Izquierdo** ($LPA$) y **Preauricular Derecho** ($RPA$).
   * *Opción A (Asistente Rápido):* Pulse **Crear Plantilla Canónica** para insertar los 4 puntos con etiquetas oficiales y posiciones de partida.
   * *Opción B (Modo Interactivo):* Pulse los botones individuales (**Situar Nasion**, **Situar Inion**, **Situar LPA**, **Situar RPA**) y haga clic directamente sobre el corte tomográfico o la vista 3D.
2. **Generación de la Superficie 3D de la Cabeza:**
   * Pulse **Generar Superficie 3D**.
   * El algoritmo ejecuta un pipeline de isosuperficie acelerado (*Flying Edges* / *Marching Cubes*), seguido de un filtrado de conectividad (descartando soportes de camilla o bobinas de RM) y un suavizado de ventana sinc.
   * Se crea automáticamente el nodo `Head_Surface` renderizado en tono piel quirúrgico con un $70\%$ de opacidad, calculando sus normales de superficie orientadas al exterior.
3. **Cálculo y Proyección de la Rejilla 10-20:**
   * Asegúrese de marcar la casilla **Proyectar sobre Superficie 3D** (recomendado).
   * Pulse **Calcular Rejilla EEG 10-20**.
   * El algoritmo traza los arcos sagital, coronal y circunferencial y proyecta cada uno de los 21 electrodos sobre la malla cutánea real mediante trazado de rayos acelerado (`vtkOBBTree`).
   * Los 21 electrodos se crean en el nodo `EEG_1020_Grid` listados como esferas 3D identificadas (Fpz, Fz, Cz, Pz, Oz, C3, C4, T3, T4, etc.).

---

### Paso 3: Localización de Dianas Cerebrales Profundas

Permite vincular las estructuras neuroanatómicas candidatas a monitorización con el planificador.

1. **Carga de la Segmentación:**
   * En `Segmentación de Dianas (Segment Editor / SynthSeg):`, seleccione el nodo `vtkMRMLSegmentationNode` del paciente (generado mediante *Segment Editor*, *SynthSeg*, *TotalSegmentator* o atlas).
2. **Extracción Automática de Dianas:**
   * Pulse el botón **Extraer Dianas Anatómicas**.
   * El algoritmo analiza cada estructura cerebral segmentada (hipocampo, amígdala, ínsula, corteza perilesional) y computa:
     * El centroide tridimensional ponderado en espacio RAS.
     * El volumen total en $\text{mm}^3$.
     * **Verificación de Contención Volumétrica:** Si una estructura tiene forma cóncava (como el hipocampo en forma de 'C') y su centroide geométrico medio cae fuera del tejido (p. ej., en el ventrículo lateral), el algoritmo proyecta de forma segura el punto al vóxel interior más cercano y lo marca con estado *"Ajustado"*.
   * Se genera el nodo de marcas `SEEG_Targets`, y la tabla muestra el inventario de dianas.
3. **Parámetros del Electrodo y Perno Guía:**
   * *Diámetro del Electrodo:* Típico $0.8$ mm (calibres $0.6$ a $1.2$ mm).
   * *Número de Contactos:* 5 a 18 anillos cilíndricos de registro (típico: 8 a 15).
   * *Longitud de Contacto:* $2.0$ mm.
   * *Espaciado Aislante Inter-Contacto:* $1.5$ mm.
   * *Longitud del Perno Guía Óseo:* $15.0$ mm (diámetro exterior: $2.5$ mm).
   * Marque la casilla **Generar Modelo 3D Tubular y Perno** para activar la visualización volumétrica de seguridad.

---

### Paso 4: Cuadro de Mandos Clínico y Seguridad Multi-Electrodo

Es el centro operativo de la planificación quirúrgica. Permite trazar electrodos, auditar su seguridad biomecánica y gestionar el plan completo.

```
┌────────────────────────────────────────────────────────────────────────┐
│ CUADRO DE MANDOS DE TRAYECTORIAS SEEG                                  │
├──────────────┬─────────┬────────┬──────────┬──────────┬────────┬───────┤
│ ID Electrodo │ Entrada │ Diana  │ Longitud │ Ángulo   │ Cont.  │ Estado│
├──────────────┼─────────┼────────┼──────────┼──────────┼────────┼───────┤
│ SEEG_Elec_01 │ C4      │ Hipoc. │ 48.2 mm  │ 12.4°    │ 10     │ OK 🟢 │
│ SEEG_Elec_02 │ T3      │ Amígd. │ 41.5 mm  │ 34.2°    │ 8      │ ADV 🟡│
│ SEEG_Elec_03 │ T4      │ Insula │ 39.1 mm  │ 11.0°    │ 8      │ ERR 🔴│
└──────────────┴─────────┴────────┴──────────┴──────────┴────────┴───────┤
│ [ Recentrar Vistas en Electrodo ]   [ Eliminar Electrodo Seleccionado] │
│ [ Evaluar Conflictos Multi-Electrodo (Colisiones y Pernos)           ] │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Cálculo de una Nueva Trayectoria:**
   * En `Punto de Entrada:`, seleccione el fiducial del electrodo EEG 10-20 deseado (o cualquier punto craneal).
   * En `Punto Diana:`, seleccione la diana anatómica en `SEEG_Targets`.
   * En `Identificador Electrodo:`, asigne el nombre clínico (ej. `SEEG_Elec_01`).
   * Pulse **Calcular y Añadir Trayectoria**.
   * El electrodo se modela en 3D:
     * Como eje lineal estereotáctico en `vtkMRMLMarkupsLineNode`.
     * Como modelo 3D tubular con perno guía coaxial en `vtkMRMLModelNode`.
     * Se distribuyen analíticamente sus contactos de registro (E01 a En) desde la punta diana hacia la superficie.
2. **Navegación Visual Interactiva:**
   * Al hacer clic en cualquier fila de la tabla `trajectoriesTableWidget`, se activa la trayectoria seleccionada.
   * El visor desplegable inferior `contactsTableWidget` lista de inmediato todos los contactos del electrodo, indicando:
     * *Índice y Etiqueta:* E01 (distal / más profundo), E02, E03...
     * *Posición RAS:* $(X, Y, Z)$ en milímetros.
     * *Distancia a la Punta:* Milímetros exactos desde la diana.
   * Pulse **Recentrar Vistas en Electrodo Seleccionado** para que los cortes axial, sagital y coronal hagan un *JumpSlice* al punto medio de la trayectoria.
3. **Eliminación Sincronizada del Plan:**
   * Si una trayectoria no es óptima, selecciónela en la tabla y pulse **Eliminar Trayectoria Seleccionada**.
   * *Garantía de Integridad:* El software purga atómicamente la trayectoria de la memoria y elimina sus nodos gráficos asociados (`_Line` y `_Model`) en `slicer.mrmlScene`, impidiendo que queden nodos huérfanos o artefactos fantasma en la escena.
4. **Auditoría Global de Conflictos Multi-Electrodo:**
   * Con dos o más electrodos en el plan, pulse **Evaluar Conflictos Multi-Electrodo**.
   * El algoritmo analiza analíticamente todos los pares únicos $\mathcal{O}(N^2)$ mediante distancia continua segmento-segmento 3D y reporta:
     * Si los pernos de anclaje colisionan en el cráneo ($< 10.0$ mm).
     * Si las trayectorias convergen peligrosamente en el parénquima cerebral ($< 3.0$ mm).

---

### Paso 5: Exportación Quirúrgica y Transmisión OpenIGTLink

Permite trasladar el plan validado al quirófano digital o guardarlo para el historial clínico.

1. **Identificador del Paciente:** Introduzca el código anonimizado del caso clínico (ej. `PAT_EPI_2026_01`).
2. **Selección del Sistema de Coordenadas:**
   * **RAS (3D Slicer / Nativo):** $X \to$ Derecha, $Y \to$ Anterior, $Z \to$ Superior.
   * **LPS (DICOM / Robótica / ROSA / StealthStation / Brainlab):** $X \to$ Izquierda ($-X_{\text{RAS}}$), $Y \to$ Posterior ($-Y_{\text{RAS}}$), $Z \to$ Superior ($Z_{\text{RAS}}$).
3. **Exportación a Archivo Local:**
   * Seleccione el formato en el desplegable:
     * *JSON Estructurado (*.json):* Metadatos completos, matrices 4x4 y desglose de contactos.
     * *CSV Quirúrgico Resumen (*.csv):* 1 fila por electrodo para hojas de cálculo de quirófano y marcos Leksell/CRW.
     * *CSV Detallado con Contactos (*.csv):* Desglose fila por fila con coordenadas 3D de cada anillo E01..En.
     * *Slicer Markups JSON (*.mrk.json):* Archivo oficial de Slicer que se puede reimportar arrastrando y soltando sobre la ventana.
   * Pulse **Exportar Plan a Archivo** y elija la ruta de destino.
4. **Transmisión en Red OpenIGTLink en Tiempo Real:**
   * Introduzca la IP del servidor del neuronavegador (por defecto `127.0.0.1` para simulador local o la IP de red hospitalaria de la estación quirúrgica).
   * Introduzca el puerto OpenIGTLink (estándar: `18944`).
   * Pulse **Transmitir a Neuronavegador (OpenIGTLink)**.
   * *Seguridad:* La conexión utiliza sockets no bloqueantes con timeout estricto de 2.0 s. Si la estación no responde, la interfaz muestra el error sin congelar jamás la aplicación. Si conecta con éxito, transmite los mensajes `TRANSFORM` y `POINT` con cabeceras de 58 bytes y CRC-64 ECMA-182.

---

## 4. Semáforo Visual y Criterios de Seguridad

El cuadro de mandos asigna a cada electrodo y al plan global un estado semafórico inequívoco:

| Color | Estado | Criterio Clínico / Biomecánico | Acción Recomendada |
| :---: | :---: | :--- | :--- |
| 🟢 | **Óptimo (Verde)** | Ángulo con la normal ósea $< 30^\circ$, sin proximidad parenquimatosa crítica ($> 3$ mm) y holgura entre pernos $\ge 10$ mm. | Trayectoria aprobada para ejecución quirúrgica. |
| 🟡 | **Alerta (Ámbar)** | Inserción oblicua moderada ($30^\circ \le \theta < 45^\circ$) o proximidad entre pernos óseos entre 5.0 y 10.0 mm. | Revisar punto de entrada. Considerar mover ligeramente el fiducial EEG 10-20 o el perno adyacente. |
| 🔴 | **Crítico (Rojo)** | Ángulo inestable $\theta \ge 45^\circ$, colisión mecánica directa de pernos ($< 5.0$ mm) o cruce parenquimatoso crítico ($< 1.5$ mm). | **Trayectoria no segura.** Prohibida la implantación sin rediseñar el punto de entrada o la diana. |

---

## 5. Guía de Resolución de Incidencias (Troubleshooting)

### 1. El volumen MRI reporta "Calidad subóptima"
* **Causa:** El espaciado de vóxel supera $1.5$ mm en alguno de los ejes anatómicos.
* **Solución:** Si dispone de una adquisición volumétrica 3D T1 de corte fino ($1.0$ mm isótropo), cárguela en su lugar. Si es el único estudio disponible, puede continuar la planificación teniendo en cuenta que la precisión en cortes gruesos tiene mayor incertidumbre.

### 2. La superficie 3D de la cabeza incluye artefactos de la camilla
* **Causa:** Elementos metálicos o soportes de la antena de RM tienen intensidad similar a la piel.
* **Solución:** El filtro de conectividad descarta automáticamente componentes desconectadas. Si el soporte toca la piel, ajuste el parámetro `threshold_ratio` a un valor superior (ej. $0.20$ o $0.25$) en la lógica o utilice *Segment Editor* para aislar la cabeza antes de extraer la superficie.

### 3. El centroide de la diana cae en el ventrículo en el hipocampo
* **Causa:** Morfología cóncava natural del lóbulo temporal medial.
* **Solución:** SEEGPlanner detecta activamente si el centroide geométrico medio cae fuera de la máscara binaria y lo desplaza automáticamente al vóxel de parénquima interior más cercano. En la tabla aparecerá indicado como *"Ajustado"*.

### 4. Error al transmitir por OpenIGTLink ("Conexión rehusada" o "Timeout")
* **Causa:** El servidor de neuronavegación no está en ejecución, la dirección IP es incorrecta o un cortafuegos hospitalario bloquea el puerto 18944.
* **Solución:**
  1. Compruebe que la estación de destino tiene activado el módulo OpenIGTLink en modo servidor (`Server: ON`).
  2. Verifique la IP con la orden `ping <IP>`.
  3. Asegúrese de que el puerto configurado (ej. 18944) coincide en ambos extremos.
  4. Como alternativa inmediata, exporte el plan a archivo **Slicer Markups JSON (.mrk.json)** o **CSV** y cárguelo manualmente en el neuronavegador.

---

> 🛠️ **SEEGPlanner** — Desarrollado por **Alejandra Viñegla Sánchez**  
> Grado en Ingeniería de la Salud · Universidad de Málaga (UMA) · 2026

