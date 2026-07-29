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

from aionq.holevo_sandwich import (
    holevo_chi,
    pgm_analysis,
)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state

__all__ = [
    "RESCUE_MARGIN_BITS",
    "classify_rescue",
    "coherent_dilation_codeword",
    "composition_defect",
    "composition_defect_matrices",
    "density_state_diagnostics",
    "dilation_diagnostics",
    "ensemble_information",
    "halmos_dilation",
    "matched_codebooks",
    "normalised_contraction",
    "source_grid",
]


RESCUE_MARGIN_BITS = 1e-3
_TOL = 1e-10
_ROUNDOFF_FACTOR = 64.0


def _svd_defect_operators(contraction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Construct both defect roots from one SVD with a roundoff-only guard.

    Forming ``I - A* A`` first and diagonalising it turns an exact zero defect
    into a positive value of order machine epsilon; taking a square root then
    amplifies the error to order ``sqrt(eps)``.  The shared SVD preserves the
    singular-vector alignment of both roots and evaluates
    ``sqrt((1-s)(1+s))`` directly.
    """
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
        raise ValueError(
            "operator expansion exceeds the scale-aware roundoff guard"
        )
    defects = np.sqrt(np.maximum(0.0, (1.0 - cleaned) * (1.0 + cleaned)))
    right = right_h.conj().T
    d_a = right @ np.diag(defects) @ right.conj().T
    d_astar = left @ np.diag(defects) @ left.conj().T
    return d_a, d_astar


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
    """Two-sided unitarity and defect-intertwining checks."""
    a = np.asarray(contraction, dtype=complex)
    u = halmos_dilation(a, tol) if unitary is None else np.asarray(unitary, complex)
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
    """Encode one source operator as a pure Choi-vector state."""
    contraction = normalised_contraction(matrix)
    unitary = halmos_dilation(contraction, tol)
    if not dilation_diagnostics(contraction, unitary, tol=tol)["valid"]:
        raise ValueError("dilation failed its structural controls before encoding")
    dimension = unitary.shape[0]
    vector = unitary.reshape(-1, order="F") / math.sqrt(dimension)
    return np.outer(vector, vector.conj())


def density_state_diagnostics(
    state: np.ndarray,
    tol: float = _TOL,
    *,
    require_pure: bool = True,
) -> dict:
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
            and (not require_pure or abs(purity - 1.0) <= tol)
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
) -> tuple[
    list[np.ndarray],
    list[np.ndarray],
    tuple[tuple[float, float, float], ...],
    tuple[np.ndarray, ...],
]:
    """Build R6 and coherent ensembles from byte-identical source coordinates."""
    coordinates = source_grid(rho, n)
    matrices = tuple(to_sl2(swirl_point(*point)) for point in coordinates)
    r6 = [attempted_use_state(matrix)[0].astype(complex) for matrix in matrices]
    coherent = [coherent_dilation_codeword(matrix) for matrix in matrices]
    return r6, coherent, coordinates, matrices


def ensemble_information(
    states: Sequence[np.ndarray],
    *,
    tol: float = _TOL,
) -> dict:
    """Return the Holevo upper bound and PGM-achievable lower bound."""
    if not states:
        raise ValueError("at least one state is required")
    chi = float(holevo_chi(states))
    diagnostics = pgm_analysis(states, guard_tolerance=tol)
    pgm = float(diagnostics["I_PGM"])
    log_count = math.log2(len(states)) if len(states) > 1 else 0.0
    ordering = bool(pgm <= chi + tol and chi <= log_count + tol)
    return {
        "chi": chi,
        "I_PGM": pgm,
        "log2_N": log_count,
        "n_codewords": len(states),
        "state_dim": int(np.asarray(states[0]).shape[0]),
        "active_carrier_dim": int(np.asarray(states[0]).shape[0]),
        "mean_state_rank": diagnostics["mean_state_rank"],
        "pgm_support_projector_defect": diagnostics[
            "support_projector_defect"
        ],
        "pgm_minimum_raw_probability": diagnostics["minimum_raw_probability"],
        "pgm_maximum_row_sum_defect": diagnostics[
            "maximum_row_sum_defect"
        ],
        "pgm_maximum_imaginary_probability": diagnostics[
            "maximum_imaginary_probability"
        ],
        "pgm_support_cutoff": diagnostics["support_cutoff"],
        "information_ordering_holds": ordering,
        "numerically_valid": bool(
            ordering
            and diagnostics["numerical_guards_hold"]
            and diagnostics["support_projector_defect"] <= tol
            and diagnostics["minimum_raw_probability"] >= -tol
            and diagnostics["maximum_row_sum_defect"] <= tol
            and diagnostics["maximum_imaginary_probability"] <= tol
        ),
    }


def composition_defect_matrices(first: np.ndarray, second: np.ndarray) -> float:
    """Composition defect for two concrete source matrices."""
    m1 = np.asarray(first, dtype=complex)
    m2 = np.asarray(second, dtype=complex)
    u1 = halmos_dilation(normalised_contraction(m1))
    u2 = halmos_dilation(normalised_contraction(m2))
    u12 = halmos_dilation(normalised_contraction(m1 @ m2))
    return float(np.linalg.norm(u12 - u1 @ u2, "fro"))


def composition_defect(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    """Measure the pointwise dilation's failure to preserve multiplication."""
    m1 = to_sl2(swirl_point(*first))
    m2 = to_sl2(swirl_point(*second))
    return composition_defect_matrices(m1, m2)


def classify_rescue(
    rows: Iterable[dict],
    *,
    margin: float = RESCUE_MARGIN_BITS,
    large_sizes: tuple[int, int, int] = (64, 100, 256),
    expected_depths: Sequence[float] | None = None,
    expected_sizes: Sequence[int] | None = None,
) -> dict:
    """Apply the frozen R6i decision rule without fitting a threshold."""
    rows = tuple(rows)
    reasons: list[str] = []
    required_fields = {"rho", "n", "chi_improvement", "pgm_improvement"}
    keys: list[tuple[float, int]] = []
    for index, row in enumerate(rows):
        if not required_fields.issubset(row):
            reasons.append(f"row {index} is missing required fields")
            continue
        rho_value = float(row["rho"])
        size_value = float(row["n"])
        values = (
            rho_value,
            size_value,
            float(row["chi_improvement"]),
            float(row["pgm_improvement"]),
        )
        if not all(math.isfinite(value) for value in values):
            reasons.append(f"row {index} contains a nonfinite value")
            continue
        if not size_value.is_integer() or size_value <= 0.0:
            reasons.append(f"row {index} has a non-integral or nonpositive size")
            continue
        keys.append((rho_value, int(size_value)))

    if not rows:
        reasons.append("the result grid is empty")
    if len(keys) != len(set(keys)):
        reasons.append("the result grid contains duplicate depth-size keys")
    if expected_depths is not None and expected_sizes is not None:
        expected = {
            (float(rho), int(size))
            for rho in expected_depths
            for size in expected_sizes
        }
        observed = set(keys)
        if observed != expected:
            missing = sorted(expected - observed)
            extra = sorted(observed - expected)
            if missing:
                reasons.append(f"the result grid is missing keys: {missing}")
            if extra:
                reasons.append(f"the result grid has extra keys: {extra}")
    elif (expected_depths is None) != (expected_sizes is None):
        reasons.append("expected depths and sizes must be supplied together")

    if reasons:
        return {
            "verdict": "HOLD",
            "margin_bits": float(margin),
            "large_sizes": list(large_sizes),
            "rescue_depths": [],
            "grid_valid": False,
            "hold_reasons": reasons,
        }

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
        "grid_valid": True,
        "hold_reasons": [],
    }
