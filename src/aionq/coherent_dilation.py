"""A fixed-width coherent alternative to the R6 post-selection map.

For a contraction ``A`` the Julia/Halmos block

    U_A = [[A, D_{A*}], [D_A, -A*]]

is unitary, where ``D_A = sqrt(I - A* A)`` and
``D_{A*} = sqrt(I - A A*)``.  Vectorising ``U_A`` therefore gives a normalized
state in ``C^16`` for the 2x2 R6 contraction.

This module does not call the pointwise dilation a representation.  In
particular, ``U_{A B}`` need not equal ``U_A U_B``.  The composition defect is
reported explicitly so a state-encoding result cannot be promoted into a
finite-dimensional unitary representation of ``SL(2,R)``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np

from aionq.capacity_ceiling import sl2_codeword
from aionq.holevo_sandwich import holevo_chi, pgm_mutual_information
from aionq.hyperbolic_qubit import swirl_point, to_sl2

__all__ = [
    "RESCUE_MARGIN_BITS",
    "classify_rescue",
    "coherent_dilation_codeword",
    "composition_defect",
    "density_state_diagnostics",
    "ensemble_information",
    "halmos_dilation",
    "matched_codebooks",
    "normalised_contraction",
    "source_grid",
]


RESCUE_MARGIN_BITS = 1e-3
_TOL = 1e-10


def _positive_sqrt(matrix: np.ndarray, tol: float = _TOL) -> np.ndarray:
    """Positive-semidefinite square root with a rounding-only negative guard."""
    hermitian = (np.asarray(matrix, dtype=complex)
                 + np.asarray(matrix, dtype=complex).conj().T) / 2.0
    values, vectors = np.linalg.eigh(hermitian)
    minimum = float(np.min(np.real(values)))
    if minimum < -tol:
        raise ValueError(f"defect operator is not positive semidefinite: {minimum}")
    # Spectral normalization makes one singular value exactly one, hence one
    # defect eigenvalue exactly zero.  Eigensolvers can return a positive
    # O(machine-epsilon) value there; taking its square root would amplify that
    # rounding noise to O(1e-8), the same failure mode caught in R6.
    positive = np.where(np.real(values) > tol, np.real(values), 0.0)
    roots = np.sqrt(positive)
    return vectors @ np.diag(roots) @ vectors.conj().T


def normalised_contraction(matrix: np.ndarray) -> np.ndarray:
    """Normalize a nonzero square matrix by its spectral norm."""
    source = np.asarray(matrix, dtype=complex)
    if source.ndim != 2 or source.shape[0] != source.shape[1]:
        raise ValueError("the source operator must be square")
    scale = float(np.linalg.norm(source, 2))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("the source operator must have positive finite norm")
    return source / scale


def halmos_dilation(contraction: np.ndarray, tol: float = _TOL) -> np.ndarray:
    """Return the Julia/Halmos unitary dilation of a square contraction."""
    a = np.asarray(contraction, dtype=complex)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("the contraction must be square")
    spectral_norm = float(np.linalg.norm(a, 2))
    if spectral_norm > 1.0 + tol:
        raise ValueError(f"operator is not a contraction: ||A||_2={spectral_norm}")
    eye = np.eye(a.shape[0], dtype=complex)
    d_a = _positive_sqrt(eye - a.conj().T @ a, tol)
    d_astar = _positive_sqrt(eye - a @ a.conj().T, tol)
    return np.block([[a, d_astar], [d_a, -a.conj().T]])


def coherent_dilation_codeword(matrix: np.ndarray, tol: float = _TOL) -> np.ndarray:
    """Encode one source operator as a pure Choi-vector state."""
    unitary = halmos_dilation(normalised_contraction(matrix), tol)
    dimension = unitary.shape[0]
    vector = unitary.reshape(-1, order="F") / math.sqrt(dimension)
    return np.outer(vector, vector.conj())


def density_state_diagnostics(state: np.ndarray, tol: float = _TOL) -> dict:
    """Numerical density-state controls without silently repairing the state."""
    rho = np.asarray(state, dtype=complex)
    hermiticity = float(np.linalg.norm(rho - rho.conj().T, "fro"))
    eigenvalues = np.linalg.eigvalsh((rho + rho.conj().T) / 2.0)
    trace = complex(np.trace(rho))
    purity = float(np.real(np.trace(rho @ rho)))
    return {
        "shape": list(rho.shape),
        "hermiticity_residual": hermiticity,
        "trace_real": float(np.real(trace)),
        "trace_imag": float(np.imag(trace)),
        "minimum_eigenvalue": float(np.min(np.real(eigenvalues))),
        "purity": purity,
        "valid": bool(
            rho.ndim == 2
            and rho.shape[0] == rho.shape[1]
            and hermiticity <= tol
            and abs(trace - 1.0) <= tol
            and float(np.min(np.real(eigenvalues))) >= -tol
            and abs(purity - 1.0) <= tol
        ),
    }


def source_grid(rho: float, n: int) -> tuple[tuple[float, float, float], ...]:
    """The frozen deterministic source grid shared by both encodings."""
    if n < 1:
        raise ValueError("n must be positive")
    return tuple(
        (float(rho), 2.0 * math.pi * k / n, 2.0 * math.pi * ((3 * k) % n) / n)
        for k in range(n)
    )


def matched_codebooks(
    rho: float,
    n: int,
) -> tuple[list[np.ndarray], list[np.ndarray], tuple[tuple[float, float, float], ...]]:
    """Build R6 and coherent ensembles from byte-identical source coordinates."""
    coordinates = source_grid(rho, n)
    matrices = [to_sl2(swirl_point(*point)) for point in coordinates]
    r6 = [sl2_codeword(*point) for point in coordinates]
    coherent = [coherent_dilation_codeword(matrix) for matrix in matrices]
    return r6, coherent, coordinates


def ensemble_information(states: Sequence[np.ndarray]) -> dict:
    """Return the Holevo upper bound and PGM-achievable lower bound."""
    return {
        "chi": float(holevo_chi(states)),
        "I_PGM": float(pgm_mutual_information(states)),
        "n_codewords": len(states),
        "state_dim": int(np.asarray(states[0]).shape[0]) if states else 0,
    }


def composition_defect(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    """Measure the pointwise dilation's failure to preserve multiplication."""
    m1 = to_sl2(swirl_point(*first))
    m2 = to_sl2(swirl_point(*second))
    u1 = halmos_dilation(normalised_contraction(m1))
    u2 = halmos_dilation(normalised_contraction(m2))
    u12 = halmos_dilation(normalised_contraction(m1 @ m2))
    return float(np.linalg.norm(u12 - u1 @ u2, "fro"))


def classify_rescue(
    rows: Iterable[dict],
    *,
    margin: float = RESCUE_MARGIN_BITS,
    large_sizes: tuple[int, int, int] = (64, 100, 256),
) -> dict:
    """Apply the frozen R6i decision rule without fitting a threshold."""
    rows = tuple(rows)
    rescue_depths = []
    for rho in sorted({float(row["rho"]) for row in rows}):
        at_depth = {int(row["n"]): row for row in rows if float(row["rho"]) == rho}
        if all(
            size in at_depth
            and float(at_depth[size]["chi_improvement"]) > margin
            and float(at_depth[size]["pgm_improvement"]) > margin
            for size in large_sizes
        ):
            rescue_depths.append(rho)

    no_rescue = all(
        float(row["chi_improvement"]) <= margin
        and float(row["pgm_improvement"]) <= margin
        for row in rows
    )
    if rescue_depths:
        verdict = "RESCUE_FOR_THIS_MAP"
    elif no_rescue:
        verdict = "NO_RESCUE_FOR_THIS_MAP"
    else:
        verdict = "HOLD"
    return {
        "verdict": verdict,
        "margin_bits": float(margin),
        "large_sizes": list(large_sizes),
        "rescue_depths": rescue_depths,
    }
