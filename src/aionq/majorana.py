"""The same certificate without coordinates, and the number it turns into a derivation.

`matchgate_defect` works, and it is written in indices.  ``_OFF_BLOCK`` is a
literal list of eight matrix positions; ``is_matchgate_matrix`` reads its two
blocks by slicing rows ``{0,3}`` and ``{1,2}``; the whole module is hard-wired to
``4 x 4`` and cannot be asked about three qubits.  Those index lists are the
coordinate shadow of two structures that have names.

**The parity blocks are a Z2 grading.**  With ``P = Z^(x)n`` the fermionic parity,
every operator splits as ``U = U+ + U-`` with ``U+- = (U +- P U P)/2``, and the
eight forbidden entries are exactly the coordinates of ``U-``.  So

    parity defect  =  || (U - P U P) / 2 ||_F

with no index anywhere.  Measured: equal to the index version to 0.0 exactly,
not approximately, on every gate tested.

**The matchgate condition is Majorana covariance.**  Under Jordan-Wigner the
mode operators are ``c_{2k} = Z..Z X I..``, ``c_{2k+1} = Z..Z Y I..``, and a
unitary is a free-fermion (Gaussian) operation exactly when conjugation keeps
them in their own span:

    U c_k U*  in  span{c_1, ..., c_2n}   for every k.

That single condition subsumes BOTH residuals of the index version.  ``CZ`` has
parity defect 0 -- it preserves the grading -- and is not a matchgate; the index
version needs a second, separate determinant test to catch it, and the covariant
version catches it in the one number.  Measured on the zoo: ``RXX``, ``iSWAP``
give 0; ``CNOT`` gives ``2*sqrt(3)``; ``SWAP`` and ``CZ`` give 4.

WHAT THE COORDINATE-FREE FORM BUYS, CONCRETELY.

*It generalises.*  The index test is 2-qubit only.  This one is written for any
``n`` and was run at ``n = 3``.

*It turns a measurement into a derivation.*  ``transport_fiber`` measured the
tangent dimension of the certified class as a numerical rank: 7 inside 16.  In
Majorana terms the Gaussian algebra is spanned by the quadratic monomials
``c_j c_k`` plus the phase, so

    dim  =  C(2n, 2) + 1  =  n(2n-1) + 1

which is ``7`` at ``n = 2`` and ``16`` at ``n = 3``.  Both confirmed against the
Jacobian rank.  The 7 was never a measurement; it was ``so(4) (+) u(1)`` seen
through a coordinate chart.

*It names the frame group.*  Qubit relabelling -- the group this repository has
been walking, ``S_n`` inside ``AGL(1,16)`` -- is the subgroup of ``O(2n)`` that
permutes Majorana PAIRS.  The full frame group of the fermionic frame bundle is
``O(2n)``, continuous, of dimension ``n(2n-1)``.  At ``n = 16`` that is a
496-dimensional group in which ``S_16`` is 2.1e13 isolated points.  So the
finite-group step measured in R1B/R1C is what a discrete subgroup of a Lie group
can see, and no more.

A WARNING THIS MODULE EARNED.  The first covariant version was still
coordinate-dependent, and not in its formula -- in its AGGREGATOR.  Taking
``max`` over the individual ``c_k`` residuals is a maximum over a basis, and a
maximum over a basis does not survive rotating the basis: measured deviation
1.2e-1 under random ``O(4)`` frames, on a quantity presented as invariant.
Summing squares instead is invariant, and measures 1.3e-15.  The lesson is the
one this repository keeps relearning in new costumes: writing a formula without
indices does not make it invariant if the reduction that turns it into a number
still reads them.
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np

__all__ = [
    "parity_operator",
    "majorana_operators",
    "graded_parts",
    "parity_defect",
    "gaussian_defect",
    "gaussian_dimension",
    "is_gaussian",
]

_I = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)


def _kron(*factors) -> np.ndarray:
    out = np.array([[1.0 + 0j]])
    for factor in factors:
        out = np.kron(out, factor)
    return out


def parity_operator(n: int) -> np.ndarray:
    """``P = Z^(x)n``, the fermionic parity whose eigenspaces are the blocks."""
    return _kron(*([_Z] * n))


def majorana_operators(n: int) -> tuple:
    """The ``2n`` Majorana modes under Jordan-Wigner, Hermitian and unitary.

    ``c_{2k} = Z...Z X I...I`` and ``c_{2k+1} = Z...Z Y I...I`` with ``k`` leading
    ``Z``s.  They satisfy ``{c_j, c_k} = 2 delta_jk``, so each squares to the
    identity and any two distinct ones anticommute -- which is what makes their
    span a well-defined ``2n``-dimensional subspace of operator space, and hence
    makes "stays in the span" a coordinate-free question.
    """
    out = []
    for site in range(n):
        for pauli in (_X, _Y):
            out.append(_kron(*([_Z] * site + [pauli] + [_I] * (n - site - 1))))
    return tuple(out)


def graded_parts(matrix, parity=None) -> tuple:
    """Split ``U`` into its parity-even and parity-odd parts under the Z2 grading."""
    matrix = np.asarray(matrix)
    if parity is None:
        parity = parity_operator(int(round(math.log2(matrix.shape[0]))))
    conjugated = parity @ matrix @ parity
    return (matrix + conjugated) / 2.0, (matrix - conjugated) / 2.0


def parity_defect(matrix, parity=None) -> float:
    """``||U-||_F``: how much ``U`` mixes the two parity sectors.

    The index-free form of `matchgate_defect.matrix_parity_defect`, and equal to
    it exactly -- the eight coordinates that function sums are precisely the
    nonzero entries of the odd part.
    """
    return float(np.linalg.norm(graded_parts(matrix, parity)[1], "fro"))


def gaussian_defect(matrix, modes=None) -> float:
    """How far ``U`` is from mapping the Majorana span into itself.

    ``sqrt( sum_k || (1 - Pi) U c_k U* ||_F^2 )`` where ``Pi`` projects operator
    space onto ``span{c_j}``.  Zero exactly on the free-fermion group.

    The aggregator is a sum of squares and that is not a stylistic choice.  Under
    a rotation ``c -> R c`` of the Majorana frame the individual residuals mix
    among themselves, so ``max`` over them is not invariant -- measured, it moves
    by 1.2e-1 under random ``O(4)`` frames -- while the sum of their squares is
    the Hilbert-Schmidt norm of a linear map and is invariant, measured to
    1.3e-15.
    """
    matrix = np.asarray(matrix)
    if modes is None:
        modes = majorana_operators(int(round(math.log2(matrix.shape[0]))))
    scale = float(matrix.shape[0])          # tr(c* c) = 2**n for every mode
    total = 0.0
    for mode in modes:
        moved = matrix @ mode @ matrix.conj().T
        projected = sum((np.trace(other.conj().T @ moved) / scale) * other
                        for other in modes)
        total += float(np.linalg.norm(moved - projected, "fro")) ** 2
    return math.sqrt(total)


def is_gaussian(matrix, tolerance: float = 1e-9) -> bool:
    """The free-fermion certificate, stated without reference to a basis."""
    return gaussian_defect(matrix) <= tolerance


def gaussian_dimension(n: int) -> dict:
    """``dim = C(2n,2) + 1``, derived from the algebra rather than fitted.

    The Gaussian unitaries are generated by Hamiltonians quadratic in Majoranas.
    The quadratic monomials ``c_j c_k`` with ``j < k`` span ``so(2n)``, of
    dimension ``C(2n,2)``, and the identity contributes the global phase.  There
    is nothing to measure: `transport_fiber` reported tangent dimension 7 at
    ``n = 2`` and 16 at ``n = 3``, and those are ``C(4,2)+1`` and ``C(6,2)+1``.
    """
    quadratic = len(list(combinations(range(2 * n), 2)))
    return {
        "modes": 2 * n,
        "quadratic": quadratic,
        "dimension": quadratic + 1,
        "ambient": 4 ** n,
        "codimension": 4 ** n - quadratic - 1,
        "frame_group": f"O({2 * n})",
        "frame_group_dimension": quadratic,
    }
