"""Quasi-equivalence, and why the dichotomy needed an axis R1X never varied.

R1X built the measure of a restricted covariance's symplectic values, found it
carried nothing its own scalar did not, and blamed a free step budget.  The
budget was real and it was not the mechanism.  The mechanism is that a
DICHOTOMY IS A STATEMENT ABOUT A LIMIT, and R1X held the register at eight
qubits while varying how long the storm ran.  A family that takes no limit
cannot exhibit one.

THE WRONG THEOREM, NAMED SO IT IS NOT REACHED FOR AGAIN.  Feldman-Hajek gives
the equivalent-or-mutually-singular dichotomy for Gaussian MEASURES on a Hilbert
space.  It does not apply: there is no Gaussian measure behind a fermionic
covariance, because the Grassmann integral is not a measure.  Using it here
would be borrowing a theorem's authority across a category it does not cover,
which is the defect this repository spent a morning auditing elsewhere.

THE RIGHT ONE IS ALREADY IN THE RIGHT CATEGORY.  Fermionic Gaussian states are
quasi-free states of the CAR algebra.  For gauge-invariant quasi-free states
with one-particle density operators ``A`` and ``B``, Powers-Stormer and Araki
give quasi-equivalence exactly when ``sqrt(A) - sqrt(B)`` and
``sqrt(1-A) - sqrt(1-B)`` are Hilbert-Schmidt.  Against the Fock vacuum
``A = 0`` that reduces to ``B`` trace-class -- finite expected particle number --
and the only alternative is disjointness.  Nothing in between.  It is empty in
finite dimensions, which is precisely why a fixed-``n`` testbed could not show
it.

THE BRIDGE IS ARITHMETIC.  Occupation of mode ``k`` is ``(1 - nu_k) / 2``.  Once
the storm has driven every semi-axis to ``0`` or ``1`` -- R1X measured 81 of 84 --
the total occupation is half the zero count, and the entanglement entropy in
bits IS that count.  So

    quasi-equivalent to vacuum  <=>  S bounded
    disjoint                    <=>  S -> infinity

The dichotomy asked for is area law against volume law, and
`supercable.covariance_entropy` has been computing its order parameter since
R1J.  It is also why every entropy in R1X's table was 0, 1, 2 or 3, which that
round observed and left unexplained.

AND IT MAKES R1X's DEFECT EXACT.  Its Lebesgue weight is a FRACTION.  Bounded
and linear-in-``m`` are the two sides of the dichotomy and dividing by ``m`` maps
them to the same place.  The quantity carrying the dichotomy is the COUNT.

WHAT THIS MODULE MAY NOT CONCLUDE.  Finite data cannot decide a dichotomy about
a limit: every finite prefix is consistent with both sides.  Everything here
measures a GROWTH LAW and reports which side that growth is consistent with.
No function in this file returns a verdict about quasi-equivalence, and the
preregistration forbids one.
"""

from __future__ import annotations

import numpy as np

from .lebesgue import spectral_measure
from .supercable import (covariance_entropy, covariance_storm,
                         gaussian_purity_defect, vacuum_covariance,
                         _orthogonal_from_generator)

__all__ = [
    "occupation",
    "zero_count",
    "is_degenerate",
    "herald_family",
    "zero_count_growth",
    "growth_verdict",
    "QUBIT_GRID",
    "FAMILIES",
]

DEGENERACY_TOL = 1e-9
QUBIT_GRID = (4, 6, 8, 12, 16, 24, 32)
FAMILIES = ("ALL_PAIRS", "NEIGHBOUR", "RANDOM_MATCHING",
            "BLOCKED_M3", "BLOCKED_FROBENIUS")
BOUNDED_SLOPE = 0.05
DIVERGENT_SLOPE = 0.25


def occupation(atoms) -> float:
    """Expected particle number of the restriction: ``sum_k (1 - nu_k) / 2``.

    The quantity Araki's criterion is about.  Trace-class against the vacuum
    means this stays finite as the one-particle space grows.
    """
    return float(np.sum((1.0 - np.asarray(atoms, dtype=float)) / 2.0))


def is_degenerate(atoms, tol: float = DEGENERACY_TOL) -> bool:
    """Is every semi-axis at ``0`` or ``1``?  The bridge identity's precondition."""
    atoms = np.asarray(atoms, dtype=float)
    return bool(np.all((atoms < tol) | (atoms > 1.0 - tol)))


def zero_count(atoms, tol: float = DEGENERACY_TOL) -> int:
    """``#{k : nu_k = 0}``.  The COUNT, deliberately not divided by anything.

    R1X reported the fraction of PURE axes.  Bounded and linear-in-``m`` zero
    counts are the two sides of the dichotomy, and normalising by ``m`` sends
    both to the same number.  This is the same information R1X had, kept in the
    form that can still tell them apart.
    """
    return int(np.count_nonzero(np.asarray(atoms, dtype=float) < tol))


def herald_family(name: str, qubits: int, seed: int = 0) -> tuple:
    """Pair families that exist at every ``n``.

    ``SUBGROUP_LADDER`` is a structure on sixteen GF(16) labels and does not
    extend to sixty-four modes, so a scaling round cannot use it.  The BLOCKED
    families tile the mode line into blocks of sixteen and run a rung inside
    each -- a tessellation of the register, which is R1Y's object at scale --
    with no herald crossing a block boundary.
    """
    modes = 2 * qubits
    if name == "ALL_PAIRS":
        return tuple((a, b) for a in range(modes) for b in range(a + 1, modes))
    if name == "NEIGHBOUR":
        return tuple((j, j + 1) for j in range(modes - 1))
    if name == "RANDOM_MATCHING":
        order = np.random.default_rng(seed).permutation(modes)
        return tuple((int(order[2 * i]), int(order[2 * i + 1]))
                     for i in range(modes // 2))
    if name.startswith("BLOCKED_"):
        from .pond import rung_pairs

        rung = name.split("_", 1)[1]
        inside = rung_pairs(rung)
        out = []
        for base in range(0, modes, 16):
            if base + 16 > modes:
                break
            out.extend((base + a, base + b) for a, b in inside)
        if not out:                      # register smaller than one block
            return tuple((j, j + 1) for j in range(modes - 1))
        return tuple(out)
    raise ValueError(f"unknown herald family {name!r}; known: {FAMILIES}")


def _prepared(qubits: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(2 * qubits, 2 * qubits))
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    return rotation @ vacuum_covariance(qubits) @ rotation.T


def zero_count_growth(family: str, qubit_grid=QUBIT_GRID, steps: int = 400,
                      seeds=(7, 13, 29), prepared_seed: int = 0) -> list:
    """The zero count against register size, for one herald family.

    Purity is carried on every row.  Heralds are projective so the GLOBAL state
    stays pure and all of ITS semi-axes stay at one; the dichotomy lives
    entirely in the restriction.  A global purity drift would mean the zero
    count is reading numerical error, which is why the gate is not optional.
    """
    rows = []
    for qubits in qubit_grid:
        prepared = _prepared(qubits, prepared_seed)
        pairs = herald_family(family, qubits, prepared_seed)
        split = qubits // 2
        left = list(range(2 * split))
        for seed in seeds:
            storm = covariance_storm(pairs, qubits, steps=steps, seed=seed,
                                     split=split, prepared=prepared)
            atoms = spectral_measure(storm["covariance"], left)
            rows.append({
                "family": family,
                "qubits": qubits,
                "m": split,
                "seed": seed,
                "zero_count": zero_count(atoms),
                "occupation": occupation(atoms),
                "entropy": float(covariance_entropy(storm["covariance"], left)),
                "degenerate": is_degenerate(atoms),
                "purity_defect": float(gaussian_purity_defect(storm["covariance"])),
            })
    return rows


def growth_verdict(rows, bounded_slope: float = BOUNDED_SLOPE,
                   divergent_slope: float = DIVERGENT_SLOPE) -> dict:
    """Least squares of zero count against ``m``, and which side it is consistent with.

    NOT a verdict about quasi-equivalence.  Finite data cannot decide a
    dichotomy about a limit -- every finite prefix is consistent with both sides
    -- so this reports the growth law and the side that growth would imply IF it
    persisted.  The preregistration forbids the stronger reading and this
    docstring is where a future reader is told so.

    The band between the two frozen slopes is INDETERMINATE and is reported as
    such.  R1X froze a verdict function whose regions overlapped and eight of
    fifteen cells satisfied both; here the two conditions are disjoint by
    construction and the gap between them is named rather than filled.
    """
    ms = np.array([row["m"] for row in rows], dtype=float)
    counts = np.array([row["zero_count"] for row in rows], dtype=float)
    slope, intercept = np.polyfit(ms, counts, 1)

    smallest, largest = float(counts.min()), float(counts.max())
    flat = largest <= 2.0 * max(smallest, 1e-12)
    if slope < bounded_slope and flat:
        verdict = "BOUNDED"
    elif slope > divergent_slope:
        verdict = "DIVERGENT"
    else:
        verdict = "INDETERMINATE"
    return {
        "family": rows[0]["family"] if rows else None,
        "slope": float(slope),
        "intercept": float(intercept),
        "min_zero_count": smallest,
        "max_zero_count": largest,
        "verdict": verdict,
        "consistent_with": {"BOUNDED": "quasi-equivalence to the vacuum",
                            "DIVERGENT": "disjointness",
                            "INDETERMINATE": "neither side at this scale"}[verdict],
        "not_a_claim": "finite n cannot decide a dichotomy about a limit",
    }
