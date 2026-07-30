"""Shared finite-carrier validation used by geometry and HB-0."""

from __future__ import annotations

from typing import Any
import math

import numpy as np

from .governance import GovernanceError


class CarrierMismatch(TypeError):
    """Raised when transport or comparison lacks a declared common carrier."""


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise GovernanceError(f"{name} must be finite, got {value!r}")
    return value


def _as_vector(value: Any, name: str = "value") -> np.ndarray:
    out = np.asarray(value, dtype=float)
    if out.ndim != 1:
        raise GovernanceError(f"{name} must be a one-dimensional carrier")
    if not np.all(np.isfinite(out)):
        raise GovernanceError(f"{name} contains a non-finite coordinate")
    return out.copy()
