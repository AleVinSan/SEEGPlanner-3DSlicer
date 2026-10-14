# Backlog - SEEGPlanner (3D Slicer Extension)

> **Proyecto:** Desarrollo de una herramienta en 3D Slicer para la planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía.
> **Autora:** Alejandra Viñegla Sánchez
> **Tutores:** Víctor Manuel Smith Fernández, David Bueno Vallejo
> **Framework:** dbv-specs-ops SDD v2.9.0
> **Horas estimadas:** 296 h

---

## Contexto del Proyecto (Context Snapshot)

- **Objetivo:** Desarrollar el módulo modular y abierto en 3D Slicer para la planificación automatizada y cálculo de trayectorias de electrodos en cirugía SEEG integrando el estándar EEG 10-20, verificación de seguridad y exportación OpenIGTLink.
- **Estado actual:** FASE 1 COMPLETADA (Adopción SDD y especificaciones del anteproyecto formalizadas en `SPECIFICATIONS.md` y `ARCHITECTURE.md`).
- **Última decisión técnica:** Adoptar la arquitectura canónica `ScriptedLoadableModule` de 3D Slicer con lógica desacoplada en `Logic/` para cálculo 10-20, trayectorias y OpenIGTLink.
- **Próximo paso:** Fase 2 — Preparación del entorno de trabajo en 3D Slicer y creación del esqueleto base del módulo `SEEGPlanner`.

---

## Checklist de Tareas del TFG (296 Horas)

### Fase 1: Revisión de la bibliografía y requisitos del software (35 h)
- [x] Análisis del anteproyecto y marco clínico de la SEEG y epilepsia farmacorresistente.
- [x] Configuración del framework SDD `dbv-specs-ops` en el repositorio.
- [x] Redacción y validación de especificaciones formales en `dbv-specs-ops/docs/SPECIFICATIONS.md`.
- [x] Diseño preliminar de arquitectura técnica en `dbv-specs-ops/docs/ARCHITECTURE.md`.

### Fase 2: Preparación del entorno de trabajo en 3D Slicer (35 h)
- [ ] Creación de la estructura de directorios y plantilla base de la extensión `SEEGPlanner/`.
- [ ] Implementación de `SEEGPlanner.py` con las clases base de Slicer (`ScriptedLoadableModule`, `ScriptedLoadableModuleWidget`, `ScriptedLoadableModuleLogic`).
- [ ] Verificación de carga en 3D Slicer v5.12.4 en modo desarrollador.
- [ ] Creación de suite inicial de test autoejecutable (`SEEGPlannerTest`).

### Fase 3: Localización de las zonas diana cerebrales (35 h)
- [ ] Definición del flujo de carga de volúmenes MRI cerebrales.
- [ ] Integración con herramientas/módulos de segmentación cerebral de Slicer (e.g. Segment Editor / SynthSeg / TotalSegmentator).
- [ ] Conversión de segmentos de diana a modelos de superficie 3D y extracción de centroides diana.

### Fase 4: Mapeo del sistema EEG 10-20 sobre la cabeza (40 h)
- [ ] Creación de interfaz para captura interactiva de 4 puntos anatómicos canónicos (Nasion, Inion, LPA, RPA).
- [ ] Algoritmo de extracción de superficie cutánea/craneal a partir del volumen MRI.
- [ ] Implementación del cálculo geométrico de curvas sagitales, coronales y circunferencia según estándar 10-20.
- [ ] Proyección y marcado de los puntos de entrada 10-20 en la escena 3D como `vtkMRMLMarkupsFiducialNode`.

### Fase 5: Cálculo y trazado de las trayectorias (40 h)
- [ ] Implementación del cálculo de líneas de trayectoria (punto 10-20 a diana cerebral).
- [ ] Representación interactiva 3D de los electrodos con calibre y marcas milimétricas.
- [ ] Cálculo de métricas: longitud total, vector director y profundidad de penetración.
- [ ] Verificación del ángulo de perpendicularidad con la superficie ósea en el punto de inserción (estabilidad del perno guía).

### Fase 6: Diseño de la interfaz gráfica (36 h)
- [ ] Maquetación del panel de control guiado paso a paso con widgets nativos de Qt/CTK.
- [ ] Controles interactivos para selección de electrodos activos, inspección de métricas y ajustes.
- [ ] Tabla resumen de trayectorias planificadas con indicadores visuales de seguridad (verde/amarillo/rojo).

### Fase 7: Exportación de datos (35 h)
- [ ] Implementación del módulo de exportación de trayectorias a archivos abiertos (JSON, CSV, Markups).
- [ ] Integración con el módulo OpenIGTLink de Slicer para transmisión en tiempo real de fiduciales y transformaciones a neuronavegadores.
- [ ] Pruebas de comunicación en red simulada con protocolo OpenIGTLink.

### Fase 8: Pruebas, validación y redacción de la memoria (40 h)
- [ ] Validación con datasets de prueba de resonancias magnéticas cerebrales anonimizadas de repositorios públicos.
- [ ] Evaluación cuantitativa de precisión y repetibilidad del sistema.
- [ ] Redacción del manual de usuario paso a paso con capturas de pantalla.
- [ ] Redacción final de la Memoria del TFG.

---

## 🔄 Snapshot de Contexto (Context Snapshot)

> **Última actualización:** 2026-10-14
> **Punto exacto:** Entrevista de contexto completada. Framework configurado. Especificaciones y Arquitectura generadas.
> **Pendiente:** Creación de la plantilla base ejecutable del módulo `SEEGPlanner` para 3D Slicer.
> **Próximo paso:** Iniciar la Fase 2 del desarrollo (creación del esqueleto del plugin).
