"""Guarded Julia/Halmos point encoding for the R6i comparison.

For a contraction ``A`` the Julia/Halmos block

    U_A = [[A, D_Astar], [D_A, -A*]]

is unitary.  Vectorising that block gives one pure density state in ``C^16``
for the two-dimensional R6 contraction.  This is a point encoding, not a group
representation: ``U_normalize(MN)`` generally differs from ``U_M U_N``.

The two defect roots are built from one SVD.  That shared construction matters
at singular value one, where separately diagonalising ``I-A*A`` and ``I-AA*``
can turn machine roundoff into a spurious defect of order ``sqrt(eps)`` and can
break the required intertwining relation.

Adapted from the corrected local R6i instrument at commit ``52b86da``.  No
previous R6i result artifact is imported by this module.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "coherent_dilation_codeword",
    "composition_defect_matrices",
    "density_state_diagnostics",
    "dilation_diagnostics",
    "halmos_dilation",
    "normalised_contraction",
]

_TOL = 1e-10
_ROUNDOFF_FACTOR = 64.0


def _svd_defect_operators(contraction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(D_A, D_Astar)`` from one singular-vector frame."""

    a = np.asarray(contraction, dtype=complex)
    left, singular_values, right_h = np.linalg.svd(a, full_matrices=True)
    scale = max(1.0, float(np.max(singular_values, initial=0.0)))
    roundoff = (
        _ROUNDOFF_FACTOR
        * np.finfo(float).eps
        * max(1, a.shape[0])
        * scale
    )
    if np.any(singular_values > 1.0 + roundoff):
        raise ValueError(
            "operator is not a contraction: "
            f"||A||_2={float(np.max(singular_values))}"
        )

    cleaned = np.asarray(singular_values, dtype=float).copy()
    cleaned[np.abs(cleaned - 1.0) <= roundoff] = 1.0
    if np.any(cleaned > 1.0):
        raise ValueError("operator expansion exceeds the roundoff guard")
    defects = np.sqrt(np.maximum(0.0, (1.0 - cleaned) * (1.0 + cleaned)))
    right = right_h.conj().T
    d_a = right @ np.diag(defects) @ right.conj().T
    d_astar = left @ np.diag(defects) @ left.conj().T
    return d_a, d_astar


def normalised_contraction(matrix: np.ndarray) -> np.ndarray:
    """Normalize a finite nonzero square matrix by its spectral norm."""

    source = np.asarray(matrix, dtype=complex)
    if source.ndim != 2 or source.shape[0] != source.shape[1]:
        raise ValueError("the source operator must be square")
    if not np.all(np.isfinite(source)):
        raise ValueError("the source operator must be finite")
    scale = float(np.linalg.norm(source, 2))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("the source operator must have positive finite norm")
    return source / scale


def halmos_dilation(contraction: np.ndarray, tol: float = _TOL) -> np.ndarray:
    """Return the guarded Julia/Halmos block of a square contraction."""

    a = np.asarray(contraction, dtype=complex)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("the contraction must be square")
    if not math.isfinite(tol) or tol <= 0.0:
        raise ValueError("validation tolerance must be positive and finite")
    d_a, d_astar = _svd_defect_operators(a)
    return np.block([[a, d_astar], [d_a, -a.conj().T]])


def dilation_diagnostics(
    contraction: np.ndarray,
    unitary: np.ndarray | None = None,
    *,
    tol: float = _TOL,
) -> dict:
    """Measure two-sided unitarity and defect intertwining without repair."""

    a = np.asarray(contraction, dtype=complex)
    u = halmos_dilation(a, tol) if unitary is None else np.asarray(unitary, complex)
    if u.shape != (2 * a.shape[0], 2 * a.shape[0]):
        raise ValueError("unitary has the wrong shape for this contraction")
    n = a.shape[0]
    identity = np.eye(2 * n, dtype=complex)
    d_astar = u[:n, n:]
    d_a = u[n:, :n]
    left = float(np.linalg.norm(u.conj().T @ u - identity, "fro"))
    right = float(np.linalg.norm(u @ u.conj().T - identity, "fro"))
    intertwining = float(np.linalg.norm(a @ d_a - d_astar @ a, "fro"))
    return {
        "left_unitarity_residual": left,
        "right_unitarity_residual": right,
        "intertwining_residual": intertwining,
        "valid": bool(max(left, right, intertwining) <= tol),
    }


def coherent_dilation_codeword(matrix: np.ndarray, tol: float = _TOL) -> np.ndarray:
    """Encode one source operator as ``|vec(U_A)/sqrt(dim U_A)><...|``."""

    contraction = normalised_contraction(matrix)
    unitary = halmos_dilation(contraction, tol)
    diagnostics = dilation_diagnostics(contraction, unitary, tol=tol)
    if not diagnostics["valid"]:
        raise ValueError("dilation failed structural controls before encoding")
    dimension = unitary.shape[0]
    vector = unitary.reshape(-1, order="F") / math.sqrt(dimension)
    return np.outer(vector, vector.conj())


def density_state_diagnostics(
    state: np.ndarray,
    tol: float = _TOL,
    *,
    require_pure: bool = False,
) -> dict:
    """Return trace, Hermiticity, positivity, and optional-purity controls."""

    rho = np.asarray(state, dtype=complex)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        return {"shape": list(rho.shape), "valid": False}
    hermiticity = float(np.linalg.norm(rho - rho.conj().T, "fro"))
    hermitian = (rho + rho.conj().T) / 2.0
    eigenvalues = np.linalg.eigvalsh(hermitian)
    trace = complex(np.trace(rho))
    purity = float(np.real(np.trace(rho @ rho)))
    finite = bool(np.all(np.isfinite(rho)))
    return {
        "shape": list(rho.shape),
        "finite": finite,
        "hermiticity_residual": hermiticity,
        "trace_real": float(np.real(trace)),
        "trace_imag": float(np.imag(trace)),
        "minimum_eigenvalue": float(np.min(np.real(eigenvalues))),
        "purity": purity,
        "rank": int(np.sum(np.real(eigenvalues) > tol)),
        "valid": bool(
            finite
            and hermiticity <= tol
            and abs(trace - 1.0) <= tol
            and float(np.min(np.real(eigenvalues))) >= -tol
            and (not require_pure or abs(purity - 1.0) <= tol)
        ),
    }


def composition_defect_matrices(first: np.ndarray, second: np.ndarray) -> float:
    """Return ``||U_normalize(MN)-U_normalize(M)U_normalize(N)||_F``."""

    m1 = np.asarray(first, dtype=complex)
    m2 = np.asarray(second, dtype=complex)
    u1 = halmos_dilation(normalised_contraction(m1))
    u2 = halmos_dilation(normalised_contraction(m2))
    u12 = halmos_dilation(normalised_contraction(m1 @ m2))
    return float(np.linalg.norm(u12 - u1 @ u2, "fro"))
