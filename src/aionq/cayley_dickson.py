"""The Cayley-Dickson failure ladder, as an observability atlas.

The Manifold Research Atlas records a failure taxonomy with specific reported
associator norms:

    R    dim  1   ||A|| = 0        no associator failure
    C    dim  2   ||A|| = 0        phase; commutative, associative
    H    dim  4   ||A|| = 0        noncommutative but associative
    O    dim  8   ||A|| ~ 0.359    first associator failure
    S16  dim 16   ||A|| ~ 1.356    associator failure + zero divisors
    T32  dim 32   ||A|| ~ 1.4      deeper failure (reported sample)

and attaches a mature correction that this repository already reached
independently:

    The Cayley-Dickson tower is a ladder of controlled *failure types*, not a
    monotone ladder of intelligence or solver power.

This module implements the doubling construction and *attempts to replicate the
reported norms*.  Replication is the point: these are someone else's numbers,
and a measurement that reproduces them is evidence, while one that does not is a
finding.  The normalisation is not specified in the source, so
:func:`associator_ladder` reports several so the comparison is not tuned to fit.

Zero divisors are checked separately: they are the qualitative transition at
dim 16, and unlike the associator norm their presence is a yes/no fact that does
not depend on any normalisation choice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["cd_multiply", "cd_conjugate", "associator", "associator_ladder",
           "find_zero_divisor", "LadderRow", "ATLAS_REPORTED"]

# Reported in the Manifold Research Atlas, section 6.4.  Targets for replication,
# not assumptions.
ATLAS_REPORTED = {1: 0.0, 2: 0.0, 4: 0.0, 8: 0.359, 16: 1.356, 32: 1.4}


def cd_conjugate(x: np.ndarray) -> np.ndarray:
    """Cayley-Dickson conjugate: negate every imaginary component."""
    out = -np.asarray(x, dtype=float).copy()
    out[0] = -out[0]
    return out


def cd_multiply(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Cayley-Dickson product, recursively defined.

    (a, b)(c, d) = (a c - d* b,  d a + b c*)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = x.shape[0]
    if n == 1:
        return x * y
    h = n // 2
    a, b = x[:h], x[h:]
    c, d = y[:h], y[h:]
    left = cd_multiply(a, c) - cd_multiply(cd_conjugate(d), b)
    right = cd_multiply(d, a) + cd_multiply(b, cd_conjugate(c))
    return np.concatenate([left, right])


def associator(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    """[x, y, z] = (xy)z - x(yz).  Zero exactly when the algebra is associative."""
    return cd_multiply(cd_multiply(x, y), z) - cd_multiply(x, cd_multiply(y, z))


def _random_unit(dim: int, rng) -> np.ndarray:
    v = rng.normal(size=dim)
    return v / np.linalg.norm(v)


@dataclass
class LadderRow:
    """One rung: measured associator statistics and zero-divisor status."""

    dim: int
    mean_norm: float          # E||[x,y,z]|| over random unit triples
    rms_norm: float           # sqrt(E||[x,y,z]||^2)
    max_norm: float
    mean_over_sqrt2: float    # a common alternative normalisation
    has_zero_divisors: bool
    reported: float | None = None

    @property
    def associative(self) -> bool:
        return self.max_norm < 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        rep = "-" if self.reported is None else f"{self.reported:.3f}"
        return (f"dim {self.dim:>3}  mean {self.mean_norm:>6.3f}  rms {self.rms_norm:>6.3f}  "
                f"max {self.max_norm:>6.3f}  mean/sqrt2 {self.mean_over_sqrt2:>6.3f}  "
                f"zero-div {str(self.has_zero_divisors):>5}  atlas {rep}")


def associator_ladder(dims=(1, 2, 4, 8, 16, 32), samples: int = 4000,
                      seed: int = 0) -> list:
    """Measure associator failure at each rung of the tower.

    Several normalisations are reported because the source does not state which
    one its figures use.  Choosing the one that matches after seeing the data
    would be fitting, so all are shown and the reader compares.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for dim in dims:
        norms = np.empty(samples)
        for i in range(samples):
            x, y, z = (_random_unit(dim, rng) for _ in range(3))
            norms[i] = np.linalg.norm(associator(x, y, z))
        rows.append(LadderRow(
            dim=dim,
            mean_norm=float(norms.mean()),
            rms_norm=float(np.sqrt((norms ** 2).mean())),
            max_norm=float(norms.max()),
            mean_over_sqrt2=float(norms.mean() / np.sqrt(2)),
            has_zero_divisors=find_zero_divisor(dim, rng=rng) is not None,
            reported=ATLAS_REPORTED.get(dim),
        ))
    return rows


def find_zero_divisor(dim: int, tries: int = 4000, tol: float = 1e-9, rng=None):
    """Search for nonzero x, y with xy = 0.

    Sedenions and above have zero divisors; division algebras (dim <= 8) do not.
    In S16 the standard construction uses a pair from the 84 known zero-divisor
    planes; here a structured search over basis-pair combinations is used, which
    finds one when it exists and returns None otherwise.
    """
    if dim < 16:
        return None
    rng = rng or np.random.default_rng(0)

    def e(i):
        v = np.zeros(dim)
        v[i] = 1.0
        return v

    # Zero divisors in S16 take the form (e_i + e_j)(e_k + e_l) = 0 for
    # particular index quadruples.  Scan pairs of such sums.
    for i in range(1, dim):
        for j in range(i + 1, dim):
            a = e(i) + e(j)
            for k in range(1, dim):
                for l in range(k + 1, dim):
                    b = e(k) + e(l)
                    if np.linalg.norm(cd_multiply(a, b)) < tol:
                        return (a, b)
    return None
