# 🎨 Sistema de Diseño: SEEGPlanner (3D Slicer Extension)

> **Fase:** `/spec` (Especificación Visual y Tokens de UI)  
> **Estado:** Validado  
> **Fecha:** 2026-11-05  
> **Aplica a:** Extensión desktop integrada en 3D Slicer (PythonQt, CTK, MRML)  

---

> 📐 Basado en el estándar de diseño biomédico de 3D Slicer y el estándar **[design.md](https://github.com/google-labs-code/design.md)**.

---

```yaml
version: "1.0.0"
name: "SEEGPlanner"
description: "Interfaz quirúrgica estereotáctica para 3D Slicer orientada a planificación guiada de electrodos SEEG, evaluación de seguridad ósea y control de colisiones."

# COLORES Y SEMÁFORO CLÍNICO
colors:
  primary:      "#2b5b84"   # Azul Slicer / Neurocirugía institucional
  secondary:    "#5c3b88"   # Púrpura para segmentación de dianas cerebrales
  accent:       "#2b7a4b"   # Verde esmeralda para acciones principales y estado seguro
  neutral:      "#f4f6f8"   # Fondo base neutro de paneles
  surface:      "#ffffff"   # Fondo de tarjetas y tablas Qt
  on-primary:   "#ffffff"   # Texto sobre primario
  on-surface:   "#212529"   # Texto principal de lectura clínica
  on-neutral:   "#6c757d"   # Texto secundario o notas técnicas
  error:        "#c0392b"   # Rojo carmesí: colisiones críticas (< 1.5 mm) o fallos
  warning:      "#d39e00"   # Ámbar/Mostaza: desviación de perno > 30° o distancias límite
  success:      "#1e7e34"   # Verde quirúrgico: trayectoria segura y perpendicular
  info:         "#17a2b8"   # Azul celeste: información estereotáctica

# MODO OSCURO (Dark Slicer Theme)
dark:
  primary:      "#3d7ea6"
  secondary:    "#7c52b3"
  accent:       "#38a169"
  neutral:      "#1f232a"
  surface:      "#2b303c"
  on-primary:   "#ffffff"
  on-surface:   "#e2e8f0"
  on-neutral:   "#a0aec0"
  error:        "#e53e3e"
  warning:      "#dd6b20"
  success:      "#48bb78"

# TIPOGRAFÍA (Fuentes nativas de Slicer y Qt Desktop)
typography:
  heading:
    fontFamily: "Segoe UI, -apple-system, Roboto, sans-serif"
    fontSize:   1.15rem
    fontWeight: 700
    lineHeight: 1.3
  subheading:
    fontFamily: "Segoe UI, -apple-system, Roboto, sans-serif"
    fontSize:   0.95rem
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Segoe UI, -apple-system, Roboto, sans-serif"
    fontSize:   0.85rem
    fontWeight: 400
    lineHeight: 1.4
  monospace:
    fontFamily: "SFMono-Regular, Menlo, Monaco, Consolas, monospace"
    fontSize:   0.80rem

# BORDES Y RADIOS
rounded:
  none: 0px
  sm:   3px
  md:   5px
  lg:   8px

# ESPACIADO
spacing:
  xs:  2px
  sm:  4px
  md:  8px
  lg:  12px
  xl:  16px

# COMPONENTES Y WIDGETS CLÍNICOS
components:
  step-header:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    borderRadius: "{rounded.sm}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    fontWeight: 600
  button-danger:
    backgroundColor: "{colors.error}"
    textColor: "#ffffff"
  badge-safe:
    backgroundColor: "#d4edda"
    textColor: "{colors.success}"
    border: "1px solid #c3e6cb"
  badge-warning:
    backgroundColor: "#fff3cd"
    textColor: "{colors.warning}"
    border: "1px solid #ffeeba"
  badge-critical:
    backgroundColor: "#f8d7da"
    textColor: "{colors.error}"
    border: "1px solid #f5c6cb"
```

---

## 🧭 Jerarquía Visual del Panel de Control (4 Pasos Clínicos)

```text
┌──────────────────────────────────────────────────────────────┐
│  SEEGPlanner — Planificación Estereotáctica Quirúrgica       │
├──────────────────────────────────────────────────────────────┤
│  [1] Datos de Paciente & MRI              [✓ Vóxel 1.0mm]    │
│  [2] Geometría Cefálica & EEG 10-20       [✓ 21 electrodos]  │
│  [3] Dianas Cerebrales & Trayectorias     [✓ 3 dianas]       │
│  [4] Cuadro de Mandos Clínico & Seguridad [2 Activas - OK]   │
│      ├── Tabla de Electrodos Planificados                    │
│      ├── Detalle de Contactos del Electrodo Seleccionado     │
│      ├── Auditoría Global de Conflictos (Pernos y 3D)        │
│      └── Botones: Eliminar, Centrar Vista, Exportar          │
└──────────────────────────────────────────────────────────────┘
```
