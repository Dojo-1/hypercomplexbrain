"""Quantum-fractal-fractional operators, implemented so they can be checked.

Attiya, Ibrahim, Hakami, Cho and Yassen, *Quantum-Fractal-Fractional Operator in
a Complex Domain*, Axioms 14(1):57, 2025, doi 10.3390/axioms14010057, defines a
family of operators on analytic functions of the unit disk by their action on
Taylor coefficients:

    Q_q^{sigma,varsigma} u(z)  =  z  +  sum_{n>=2} a_n (kappa_n)_q z^n

with ``(kappa_n)_q`` built from q-gamma functions and a fractal order
``varsigma`` alongside the fractional order ``sigma``.

WHY THIS IS HERE.  It arrived as a proposed answer to a gap this repository
recorded in `docs/FALCONER_ASSESSMENT.md`: that a Falconer-type theory has
nothing to act on because the programme produces no fractal sets and no measure
carrying a dimension.  An operator family carrying a fractal order is a
plausible place for such sets to come from.  That is a reason to *implement* it,
not a reason to believe it, and this module is the implementation.

WHAT A COEFFICIENT MULTIPLIER IS, STRUCTURALLY.  ``Q`` acts diagonally on the
Taylor basis, so it is a function of the number operator ``z d/dz`` -- which is
the generator of rotations, hence a connection Laplacian on a line bundle over
the disk.  So a QFFO is a **spectral multiplier**, and in the vocabulary of the
polycosmic proposal it is exactly a ``P_k``-shaped object: a band-weight, not a
localisation.  That is the honest bridge, and it is also the honest limit --
multipliers are diagonal, and the packet calculus the proposal wants needs
operators that are *not*.

WHAT REPRODUCES AND WHAT DOES NOT.  The paper prints a table of ``Gamma_q``
values.  This module's `q_gamma` reproduces it to **machine precision at
q = 0.5** and to 1e-8 at q = 0.7, so the convention here is the paper's.  At
q = 0.9 and q = 0.95 the printed values diverge from the computed ones by up to
2.7e-1, and four of those six exceed ``Gamma(x)`` -- the ``q -> 1`` limit that
``Gamma_q`` is defined to have.  The true ``Gamma_q`` is monotone increasing in
``q`` and approaches ``Gamma(x)`` from below, verified at
q = 0.5, 0.7, 0.9, 0.95, 0.99, 0.999.  A value above the limit is not a
precision disagreement; it is on the wrong side of a bound.

Separately, the paper concludes from its worked example that
``Q f(z) = z/(1 - mu z)`` for ``f(z) = z/(1-z)``.  A function ``z/(1-mu z)`` has
coefficients ``mu^{n-1}``, so its successive ratios are constant.  The paper's
own printed coefficients have ratios rising monotonically from 0.857 to 0.952.
The weaker statement it makes alongside -- that the coefficients are majorised by
those of ``z/(1-z)`` -- is consistent with the numbers.

Neither observation depends on reconstructing a mangled formula, which matters
because the coefficient formula could NOT be reconstructed: no reading of it
tried here reproduces the printed coefficients, and the text available to this
session had its fraction structure destroyed in transmission.  So
`multiplier` below implements the reading consistent with the paper's own
Application 1 and normalisation, and is labelled as a reading.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "q_gamma",
    "q_pochhammer_ratio",
    "PAPER_TABLE_1",
    "multiplier",
    "apply_to_coefficients",
    "MultiplierReading",
]


def q_gamma(x: float, q: float, tolerance: float = 1e-18,
            max_terms: int = 2_000_000) -> float:
    """``Gamma_q(x) = (1-q)^(1-x) prod_{n>=0} (1 - q^(n+1)) / (1 - q^(x+n))``.

    Summed in logs, and the product is carried until both ``q^(n+1)`` and
    ``q^(x+n)`` fall below ``tolerance`` rather than until a single factor looks
    close to 1.  The distinction matters near ``q = 1``, where every factor is
    individually close to 1 and the tail still contributes: a truncation rule
    that stops on one factor is exactly how a table of these values acquires
    errors of 1e-1 while looking converged.
    """
    if not 0.0 < q < 1.0:
        raise ValueError("q_gamma is defined for q in (0, 1)")
    total, index = 0.0, 0
    while True:
        numerator, denominator = q ** (index + 1), q ** (x + index)
        total += math.log1p(-numerator) - math.log1p(-denominator)
        index += 1
        if max(numerator, denominator) < tolerance or index > max_terms:
            break
    return math.exp((1.0 - x) * math.log(1.0 - q) + total)


def q_pochhammer_ratio(base: float, order: float, q: float) -> float:
    """``base^(order) = Gamma_q(base + order) / Gamma_q(base)``.

    The paper's factorial power, in the form its own Application 1 uses.  It
    also prints a second definition as a product ``prod_{j=0}^{varsigma-1}
    (base - j)(1 - q^j)``; that form is not used here, because its ``j = 0``
    factor is ``1 - q^0 = 0``, which would make every such product vanish, and
    because its index range is undefined for the non-integer ``varsigma`` used
    in every worked example (0.4 and 0.5).
    """
    return q_gamma(base + order, q) / q_gamma(base, q)


#: The paper's Table 1, transcribed: q -> (Gamma_q(2.1), Gamma_q(2.5), Gamma_q(2.9)).
#: Kept as data so the reproduction claim is checkable rather than asserted.
PAPER_TABLE_1 = {
    0.001: (1.0000995556762426, 1.0004994054811371, 1.000899855923606),
    0.1: (1.0082659793606632, 1.046066572448892, 1.088784698676843),
    0.2: (1.0147511896471197, 1.0868086641261354, 1.17558530615081),
    0.3: (1.0202506978830732, 1.1239476292023016, 1.2607967455441123),
    0.4: (1.0250805873649542, 1.1583598546562799, 1.344668018051892),
    0.5: (1.029414446594846, 1.1905936250275284, 1.427376969260213),
    0.6: (1.0333611545829302, 1.221025326199809, 1.5090582738591247),
    0.7: (1.036994746225153, 1.2499290452711966, 1.5898179667143768),
    0.8: (1.0403812870012996, 1.2775335316152772, 1.6697747269289396),
    0.9: (1.0488444513789157, 1.3128314103324294, 1.763713044723999),
    0.95: (1.1357798101736767, 1.4733614062423337, 2.058688968144806),
}


@dataclass(frozen=True)
class MultiplierReading:
    """One QFFO band-weight, with the branch of the paper it came from."""

    kind: str          # "riemann_liouville", "caputo", or "integral"
    sigma: float
    varsigma: float
    q: float

    def weight(self, n: int) -> float:
        """``(kappa_n)_q``: the factor multiplying the ``n``-th Taylor coefficient."""
        gamma_q = (lambda value: q_gamma(value, self.q))
        sigma, varsigma = self.sigma, self.varsigma
        if self.kind == "riemann_liouville":
            normalisation = gamma_q(3 - sigma) / q_pochhammer_ratio(2 - sigma,
                                                                    varsigma, self.q)
            return normalisation * gamma_q(n + 1) * q_pochhammer_ratio(
                n + 1 - sigma, varsigma, self.q) / gamma_q(n + 2 - sigma)
        if self.kind == "caputo":
            return (gamma_q(3 - sigma - varsigma) * gamma_q(n + 1 - varsigma)
                    / (gamma_q(2 - varsigma) * gamma_q(n + 2 - sigma - varsigma)))
        if self.kind == "integral":
            return (gamma_q(1 + 2 * sigma) * gamma_q(n + sigma)
                    / (gamma_q(1 + sigma) * gamma_q(n + 2 * sigma)))
        raise ValueError(f"unknown QFFO branch {self.kind!r}")


def multiplier(kind: str, sigma: float, varsigma: float, q: float,
               terms: int = 12) -> tuple:
    """The band-weights ``(kappa_1, ..., kappa_terms)``, with ``kappa_1 = 1``.

    A READING of the paper's Proposition 2, consistent with its Application 1
    and its normalisation, and not a reproduction of it: the printed
    coefficients could not be reproduced by this or by any other reading tried,
    and the source text available here had its fraction structure destroyed in
    transmission, so the failure is not attributable.
    """
    reading = MultiplierReading(kind, sigma, varsigma, q)
    return (1.0,) + tuple(reading.weight(n) for n in range(2, terms + 1))


def apply_to_coefficients(coefficients, kind: str, sigma: float,
                          varsigma: float, q: float) -> tuple:
    """Act on a normalised analytic function given by ``a_1 = 1, a_2, a_3, ...``."""
    weights = multiplier(kind, sigma, varsigma, q, terms=len(coefficients))
    return tuple(a * w for a, w in zip(coefficients, weights))
