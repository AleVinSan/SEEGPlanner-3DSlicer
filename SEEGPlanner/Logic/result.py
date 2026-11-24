# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class Ok(Generic[T]):
    """Representa una operación exitosa que contiene un valor."""
    value: T


@dataclass(slots=True, frozen=True)
class Err:
    """Representa una operación fallida con mensaje descriptivo y causa opcional."""
    message: str
    cause: str | None = None


# Tipo discriminado Result para manejo tipado de éxito o error
Result = Union[Ok[T], Err]
