"""Split forms: the same hyperbolic structure over R and over F_2.

Context
-------
The NN Disk architecture ("substrate-independent hyperbolic semantic memory
fabric") was offered as possibly pertinent here on the grounds that it is
"based in GF(2) in a (2,2) approach".

Inspection does not support the literal reading.  That codebase contains no
GF(2): its geometric plane uses the **real** quadratic form

    Q(x) = x0^2 + x1^2 - x2^2 - x3^2

with SO(2,2) acting on the Q = +1 pseudo-sphere.  Signature (2,2) over R and the
two-element field F_2 are different objects, and conflating them is the kind of
borrowing this repository's evidence lattice exists to prevent.

But there is a precise shared structure underneath, and it is not a loose
analogy.  It is the same classification concept:

    A quadratic form is SPLIT (equivalently HYPERBOLIC) when it decomposes as an
    orthogonal sum of hyperbolic planes -- 2-dimensional pieces carrying a basis
    e, f with q(e) = q(f) = 0 and <e, f> = 1.

Over **R**: signature (2,2) *is* the split form in dimension 4.
    x0^2 - x2^2 = (x0 + x2)(x0 - x2) is a hyperbolic plane, and so is
    x1^2 - x3^2.  So Q = H_R (+) H_R exactly.  SO(2,2) is the split orthogonal
    group.  That is what NN Disk computes on.

Over **F_2**: the stabilizer formalism's phase space F_2^{2n}, carrying the
symplectic form <(x|z), (x'|z')> = x.z' + z.x' (mod 2), is an orthogonal sum of
n hyperbolic planes -- one per qubit, spanned by X_i and Z_i.  That is what
:mod:`aionq.visibility` computes ranks in.

So both architectures are hyperbolic in the *same algebraic sense*, over
different fields.  The shared object is the split form, not GF(2).

Why this is useful here, not just tidy
--------------------------------------
Finding the hyperbolic planes of a stabilizer code's phase space is exactly how
one finds its logical qubits.  A symplectic (Darboux) basis adapted to the
stabilizer group hands back the logical operator pairs Xbar_i, Zbar_i with
<Xbar_i, Zbar_j> = delta_ij.  Minimising weight over the resulting logical coset
gives the code distance -- which Round V1 needed and did not have, having taken
d on trust from the code's name.

So the split-form view converts a structural observation into an instrument
this repository was missing.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

__all__ = ["symplectic_product", "is_hyperbolic_pair", "symplectic_basis",
           "logical_pairs", "code_distance", "real_split_planes",
           "SplitFormReport", "analyse_split_form"]


def symplectic_product(u: np.ndarray, v: np.ndarray) -> int:
    """<(x|z), (x'|z')> = x.z' + z.x'  (mod 2).

    Zero exactly when the two Paulis commute.  This is the F_2 form whose
    hyperbolic planes are the individual qubits.
    """
    u = np.asarray(u, dtype=np.uint8)
    v = np.asarray(v, dtype=np.uint8)
    n = u.size // 2
    return int((u[:n] @ v[n:] + u[n:] @ v[:n]) % 2)


def is_hyperbolic_pair(e: np.ndarray, f: np.ndarray) -> bool:
    """A hyperbolic plane: two isotropic vectors pairing to 1."""
    return symplectic_product(e, f) == 1


def _reduce(v: np.ndarray, basis) -> np.ndarray:
    """Reduce v against an echelon basis over F_2."""
    cur = np.asarray(v, dtype=np.uint8).copy()
    for b in basis:
        lead = np.flatnonzero(b)
        if lead.size and cur[lead[0]]:
            cur = cur ^ b
    return cur


def _independent(rows) -> list:
    """Row-echelon basis over F_2."""
    basis: list[np.ndarray] = []
    for r in rows:
        red = _reduce(r, basis)
        if red.any():
            basis.append(red)
            basis.sort(key=lambda b: int(np.flatnonzero(b)[0]))
    return basis


def symplectic_basis(vectors) -> list:
    """Decompose the span of `vectors` into hyperbolic planes over F_2.

    Returns a list of (e, f) pairs with <e, f> = 1 and every pair orthogonal to
    every other -- a Darboux basis of the symplectic part -- followed by a list
    of radical vectors (those orthogonal to everything, which carry no plane).

    This is the F_2 analogue of writing the real (2,2) form as H (+) H.
    """
    pool = [np.asarray(v, dtype=np.uint8).copy() for v in vectors if np.any(v)]
    planes, radical = [], []

    while pool:
        e = pool.pop(0)
        partner_idx = next((i for i, w in enumerate(pool)
                            if symplectic_product(e, w) == 1), None)
        if partner_idx is None:
            radical.append(e)
            continue
        f = pool.pop(partner_idx)
        planes.append((e, f))
        # Project the rest onto the complement of this plane.
        pool = [w ^ (symplectic_product(w, f) * e) ^ (symplectic_product(w, e) * f)
                for w in pool]
        pool = [w for w in pool if np.any(w)]
    return planes, radical


def logical_pairs(stabilizer_labels) -> list:
    """Logical operator pairs of a stabilizer CODE, from its check generators.

    Given the s = n - k independent checks of an [[n, k, d]] code, returns k
    pairs (Xbar, Zbar) as symplectic vectors: a basis of the centraliser modulo
    the stabilizer, decomposed into hyperbolic planes.
    """
    from .visibility import generators_from_labels
    n, checks = generators_from_labels(list(stabilizer_labels))
    check_basis = _independent(list(checks))

    # Centraliser: all v with <v, s> = 0 for every check s.  Solve over F_2 by
    # enumerating a basis of the null space of the check matrix under the form.
    dim = 2 * n
    swapped = np.zeros((len(check_basis), dim), dtype=np.uint8)
    for i, s in enumerate(check_basis):
        swapped[i, :n] = s[n:]
        swapped[i, n:] = s[:n]

    null: list[np.ndarray] = []
    pivots: dict[int, np.ndarray] = {}
    mat = swapped.copy()
    row = 0
    pivot_cols = []
    for col in range(dim):
        sel = next((r for r in range(row, mat.shape[0]) if mat[r, col]), None)
        if sel is None:
            continue
        mat[[row, sel]] = mat[[sel, row]]
        for r in range(mat.shape[0]):
            if r != row and mat[r, col]:
                mat[r] ^= mat[row]
        pivots[col] = mat[row]
        pivot_cols.append(col)
        row += 1
    free_cols = [c for c in range(dim) if c not in pivot_cols]
    for fc in free_cols:
        v = np.zeros(dim, dtype=np.uint8)
        v[fc] = 1
        for pc in pivot_cols:
            if pivots[pc][fc]:
                v[pc] = 1
        null.append(v)

    # Quotient the centraliser by the stabilizer, then split into planes.
    quotient = [_reduce(v, check_basis) for v in null]
    quotient = [v for v in quotient if np.any(v)]
    planes, _radical = symplectic_basis(quotient)
    return planes


def _weight(v: np.ndarray) -> int:
    n = v.size // 2
    return int(np.count_nonzero(v[:n] | v[n:]))


def code_distance(stabilizer_labels, max_logical: int | None = None) -> int:
    """Exact distance: minimum weight over all nontrivial logical operators.

    Enumerates the logical cosets (logical span x stabilizer span) and takes the
    minimum weight.  Exact and exponential in n - k; fine for the small codes
    used here, and it removes the need to take d on trust from a code's name.
    """
    from .visibility import generators_from_labels
    n, checks = generators_from_labels(list(stabilizer_labels))
    check_basis = _independent(list(checks))
    planes = logical_pairs(stabilizer_labels)
    logical_vecs = [v for pair in planes for v in pair]
    if not logical_vecs:
        return 0

    best = n
    s = len(check_basis)
    for lmask in range(1, 1 << len(logical_vecs)):
        lv = np.zeros(2 * n, dtype=np.uint8)
        for i in range(len(logical_vecs)):
            if lmask >> i & 1:
                lv = lv ^ logical_vecs[i]
        for smask in range(1 << s):
            v = lv.copy()
            for i in range(s):
                if smask >> i & 1:
                    v = v ^ check_basis[i]
            w = _weight(v)
            if 0 < w < best:
                best = w
    return best


def real_split_planes() -> dict:
    """The real (2,2) form as an orthogonal sum of two hyperbolic planes.

    Q(x) = x0^2 + x1^2 - x2^2 - x3^2 with the change of basis
    u = x0 + x2, v = x0 - x2, s = x1 + x3, t = x1 - x3 becomes uv + st: two
    hyperbolic planes.  This is what makes SO(2,2) *the split* orthogonal group,
    and it is the exact real counterpart of the F_2 decomposition above.
    """
    g = np.diag([1.0, 1.0, -1.0, -1.0])
    basis = np.array([[1, 0, 1, 0],       # u = x0 + x2
                      [1, 0, -1, 0],      # v = x0 - x2
                      [0, 1, 0, 1],       # s = x1 + x3
                      [0, 1, 0, -1]], dtype=float)
    gram = basis @ g @ basis.T
    return {
        "signature": (2, 2),
        "gram_in_split_basis": gram,
        "is_two_hyperbolic_planes": bool(
            np.allclose(np.diag(gram), 0.0)
            and abs(gram[0, 1]) > 0 and abs(gram[2, 3]) > 0
            and np.allclose(gram[:2, 2:], 0.0)),
    }


@dataclass
class SplitFormReport:
    n_qubits: int
    planes: int
    radical: int
    logical_qubits: int
    distance: int
    min_logical_weights: tuple = field(default_factory=tuple)

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"n={self.n_qubits}  hyperbolic planes={self.planes}  "
                f"radical={self.radical}  k={self.logical_qubits}  d={self.distance}")


def analyse_split_form(stabilizer_labels) -> SplitFormReport:
    """Full split-form analysis of a stabilizer code."""
    from .visibility import generators_from_labels
    n, checks = generators_from_labels(list(stabilizer_labels))
    planes, radical = symplectic_basis(list(checks))
    logical = logical_pairs(stabilizer_labels)
    return SplitFormReport(
        n_qubits=n,
        planes=len(planes),
        radical=len(radical),
        logical_qubits=len(logical),
        distance=code_distance(stabilizer_labels),
        min_logical_weights=tuple(sorted(_weight(v) for pair in logical for v in pair)),
    )
