# Antigravity Reference — SDD Extended Behavior

This project follows **Spec-Driven Development (SDD)** with the framework **dbv-specs-ops**.

All master rules, workflows, specifications, architecture, memory and task tracking are located in the `dbv-specs-ops/` folder.
Master prompt is at [`dbv-specs-ops/docs/MASTER_PROMPT.md`](file:///Users/bvinegla/Desktop/quinto%20curso/tfgprueba/dbv-specs-ops/docs/MASTER_PROMPT.md).

## Antigravity-Specific Behavior
- **Planning Mode**: In planning phases, create artifacts both in the workspace and in session memory.
- **SDD Lifecycle**: Follow strictly the phases: `/spec` → `/plan` → `/build` → `/test` → `/code-simplify` → `/ship`.
- **Context Tracking**: Consult `dbv-specs-ops/memory.md` and keep `dbv-specs-ops/task.md` updated with progress and context snapshots.
