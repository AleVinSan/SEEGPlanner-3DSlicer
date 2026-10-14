# 🪪 Project Config

> This file is read automatically by the AI at session start.
> Follows dbv-specs-ops SDD framework v2.9.0.

---

## Project Identity

- **Name:** SEEGPlanner-3DSlicer (SEEGPlanner)
- **Description:** Herramienta en 3D Slicer para la planificación de cirugía de electrodos cerebrales en estéreo-electroencefalografía (SEEG)
- **Author:** Alejandra Viñegla Sánchez
- **Tutors:** Víctor Manuel Smith Fernández (Tutor), David Bueno Vallejo (Cotutor)
- **Institution:** Grado en Ingeniería de la Salud · Universidad de Málaga (UMA)
- **License:** MIT / Apache-2.0 (compatible con 3D Slicer BSD-style)
- **Languages:** Python 3 (entorno embebido de 3D Slicer)
- **Technologies / Stack:** 3D Slicer (v5.12.4), MRML, VTK, ITK, PythonQt, CTK, OpenIGTLink (`OpenIGTLinkIF` / `pyigtl`), NumPy, SciPy
- **Agent Readiness (Web):** Not Applicable (extensión nativa desktop para 3D Slicer)
- **Framework Version:** 2.9.0

---

## Model Routing Guidelines

| Development Phase | Required Reasoning Complexity | Recommended Model Class | Example Models |
| --- | --- | --- | --- |
| `/spec` (Specifications) | Very High | Advanced Reasoning / Frontier Models | Gemini 3.1 Pro, Claude Opus 5 |
| `/plan` (Planning / Architecture) | Very High | Advanced Reasoning / Frontier Models | Gemini 3.1 Pro, Claude Opus 5 |
| `/build` (Code Implementation) | Medium | Fast, high-accuracy coding models | Gemini 3.5 Flash, Claude Sonnet 5 |
| `/test` (Conventional Tests / Evals) | Medium-Low | Fast & cheap models | Gemini 2.5 Flash-Lite, Claude Haiku 5 |
| `/code-simplify` (Security & Refactor) | High | Security-conscious reasoning models | Gemini 3.1 Pro, Claude Sonnet 5 |
| `/ship` (Documentation, Changelog) | Low | Fast, text-optimized models | Gemini 2.5 Flash-Lite, Claude Haiku 5 |

---

## File Header Template

```python
# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================
```

---

> 🛠️ Framework SDD creado por **[David Bueno Vallejo](https://github.com/davidbuenov)** — libre y gratuito · [dbv-specs-ops](https://github.com/davidbuenov/dbv-specs-ops)
