"""Fusion-category hypercomplexity, with the coherence laws actually checked.

The draft correctly replaces literal octonionic matrix multiplication with a
braided fusion category: nonassociativity becomes an explicit change of fusion
basis (an F-move) rather than a failure of matrix algebra.  It then lists
"pentagon and hexagon coherence" as a requirement.

A requirement that is never evaluated is decoration.  This module implements the
Fibonacci category -- the smallest non-abelian anyon model, universal for quantum
computation by braiding alone -- and *verifies* the pentagon and hexagon
identities numerically.  Any learned or hand-designed F/R data proposed for the
architecture must pass :func:`verify_coherence` or be rejected.

Labels: 0 = vacuum (1), 1 = tau.  Fusion: tau x tau = 1 + tau.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

import numpy as np

__all__ = ["PHI", "fusion_allowed", "f_symbol", "r_symbol",
           "pentagon_defect", "hexagon_defect", "verify_coherence",
           "CoherenceReport", "associator_defect"]

PHI = (1.0 + math.sqrt(5.0)) / 2.0

VACUUM, TAU = 0, 1
LABELS = (VACUUM, TAU)


def fusion_allowed(a: int, b: int, c: int) -> bool:
    """N^c_{ab} != 0 for the Fibonacci fusion rules."""
    if a == VACUUM:
        return c == b
    if b == VACUUM:
        return c == a
    return True  # tau x tau = 1 + tau contains both labels


def f_symbol(a: int, b: int, c: int, d: int, e: int, f: int) -> complex:
    """F^{abc}_d [e, f].

    ``e`` labels the (ab)c fusion channel, ``f`` labels the a(bc) channel.
    Returns 0 when either channel is disallowed.
    """
    if not (fusion_allowed(a, b, e) and fusion_allowed(e, c, d)):
        return 0.0
    if not (fusion_allowed(b, c, f) and fusion_allowed(a, f, d)):
        return 0.0

    if a == b == c == d == TAU:
        mat = np.array([[1.0 / PHI, 1.0 / math.sqrt(PHI)],
                        [1.0 / math.sqrt(PHI), -1.0 / PHI]], dtype=complex)
        return complex(mat[e, f])

    # Every F-symbol involving the vacuum is trivial.
    return 1.0 + 0.0j


def r_symbol(a: int, b: int, c: int) -> complex:
    """R^{ab}_c : braiding phase for fusing a and b into channel c."""
    if not fusion_allowed(a, b, c):
        return 0.0
    if a == TAU and b == TAU:
        return cmath.exp(-4j * math.pi / 5) if c == VACUUM else cmath.exp(3j * math.pi / 5)
    return 1.0 + 0.0j


def pentagon_defect() -> float:
    """Maximum violation of the pentagon identity over all label assignments.

    Pentagon:
        F^{fcd}_e[g,l] . F^{abl}_e[f,h]
            = sum_k F^{abc}_g[f,k] . F^{akd}_e[g,h] . F^{bcd}_h[k,l]
    """
    worst = 0.0
    for a in LABELS:
        for b in LABELS:
            for c in LABELS:
                for d in LABELS:
                    for e in LABELS:
                        for f in LABELS:
                            for g in LABELS:
                                for h in LABELS:
                                    for l in LABELS:
                                        lhs = (f_symbol(f, c, d, e, g, l)
                                               * f_symbol(a, b, l, e, f, h))
                                        rhs = sum(
                                            f_symbol(a, b, c, g, f, k)
                                            * f_symbol(a, k, d, e, g, h)
                                            * f_symbol(b, c, d, h, k, l)
                                            for k in LABELS
                                        )
                                        worst = max(worst, abs(lhs - rhs))
    return worst


def hexagon_defect() -> float:
    """Maximum violation of the hexagon identity over all label assignments.

    Hexagon:
        R^{ca}_g . F^{acb}_d[g,f] . R^{cb}_f
            = sum_e F^{cab}_d[g,e] . R^{ce}_d . F^{abc}_d[e,f]
    """
    worst = 0.0
    for a in LABELS:
        for b in LABELS:
            for c in LABELS:
                for d in LABELS:
                    for f in LABELS:
                        for g in LABELS:
                            lhs = (r_symbol(c, a, g)
                                   * f_symbol(a, c, b, d, g, f)
                                   * r_symbol(c, b, f))
                            rhs = sum(
                                f_symbol(c, a, b, d, g, e)
                                * r_symbol(c, e, d)
                                * f_symbol(a, b, c, d, e, f)
                                for e in LABELS
                            )
                            worst = max(worst, abs(lhs - rhs))
    return worst


def associator_defect() -> float:
    """How far (ab)c and a(bc) differ -- the quantity the octonions were reaching for.

    In the Fibonacci category this is the off-diagonal weight of the F-matrix:
    strictly nonzero, so composition order carries information, yet fully
    coherent, so the ambiguity never becomes inconsistency.  That combination is
    exactly what literal octonionic matrix multiplication could not deliver.
    """
    mat = np.array([[f_symbol(TAU, TAU, TAU, TAU, e, f) for f in LABELS]
                    for e in LABELS])
    off = mat - np.diag(np.diag(mat))
    return float(np.linalg.norm(off))


@dataclass
class CoherenceReport:
    pentagon: float
    hexagon: float
    associator: float
    tolerance: float

    @property
    def coherent(self) -> bool:
        return self.pentagon < self.tolerance and self.hexagon < self.tolerance

    @property
    def nontrivial(self) -> bool:
        """Coherent but not associative -- the useful regime."""
        return self.coherent and self.associator > 1e-6

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"pentagon defect  : {self.pentagon:.3e}",
            f"hexagon defect   : {self.hexagon:.3e}",
            f"associator norm  : {self.associator:.6f}",
            f"coherent         : {self.coherent}",
            f"order-sensitive  : {self.nontrivial}",
        ])


def verify_coherence(tolerance: float = 1e-10) -> CoherenceReport:
    """Check that the fusion grammar is coherent and genuinely non-associative."""
    return CoherenceReport(
        pentagon=pentagon_defect(),
        hexagon=hexagon_defect(),
        associator=associator_defect(),
        tolerance=tolerance,
    )
