"""Cup products on H*(T^3; Z), because a demotion turned on a degree.

An external peer review of "The Sheaf of Becoming" demoted its Theorem 3 -- the
prediction that a Dixmier-Douady class on the 3-torus equals the product of three
winding numbers, ``delta = w1 w2 w3`` -- with this stated reason:

    "the cup product c1 u c1 u c1 in H^6(T^3) = 0 (vanishes); the structural
     cocycle status survives, the integer is mis-stated"

Both halves of that sentence are true and they are about different objects.
``H^6(T^3) = 0`` because T^3 is a closed 3-manifold and cohomology vanishes above
the dimension.  A triple product of DEGREE-2 classes does land in degree 6 and is
therefore zero.  But a Dixmier-Douady class lives in ``H^3(X; Z)``, and on the
3-torus ``H^3(T^3; Z) = Z``, which is very much not zero.  The natural triple
product landing there is of three DEGREE-1 classes -- winding numbers are degree
one, being classes in ``H^1(S^1; Z) = Z`` pulled back along the three projections.

So the demotion is computed in the wrong degree.  Whether the original Theorem 3
is right for its own construction is a separate question this module cannot
settle, since that construction is not in hand.  What it settles is that the
reason given cannot be the reason.

The computation, and why this form of it
----------------------------------------
``T^3`` is a ``K(Z^3, 1)``, so ``H*(T^3; Z) = H*(Z^3; Z)`` as rings, and group
cohomology in the inhomogeneous bar complex makes the cup product trivial to
write down exactly:

    (a u b)(g_1, ..., g_{p+q}) = a(g_1, ..., g_p) * b(g_{p+1}, ..., g_{p+q})

No triangulation, no Alexander-Whitney bookkeeping, no floating point.  Everything
below is integer arithmetic, so the results are exact rather than approximate --
which matters, because the claim at issue is that a particular integer is or is
not zero.

This is a P-tier check: the answer is forced by the algebra and was known before
the code ran.  Running it is not evidence-gathering, it is proof-checking, and it
is here so that a reader can re-derive the disagreement mechanically instead of
adjudicating between two assertions.
"""

from __future__ import annotations

import itertools
import math

__all__ = ["coboundary", "cup", "is_cocycle", "winding_cochain",
           "fundamental_pairing", "betti_rank", "triple_winding_class",
           "degree_six_is_zero_by_dimension"]

RANK = 3            # T^3 = K(Z^3, 1)


def _add(g, h):
    return tuple(a + b for a, b in zip(g, h))


def coboundary(cochain, degree: int):
    """The inhomogeneous bar-complex differential, trivial coefficients.

        (d c)(g_1..g_{n+1}) = c(g_2..g_{n+1})
                              + sum_i (-1)^i c(.., g_i + g_{i+1}, ..)
                              + (-1)^{n+1} c(g_1..g_n)

    The group is written additively because it is Z^3, so the internal
    multiplication ``g_i g_{i+1}`` of the general formula is ``g_i + g_{i+1}``.
    """

    def d(*args):
        if len(args) != degree + 1:
            raise ValueError(f"expected {degree + 1} arguments, got {len(args)}")
        total = cochain(*args[1:])
        for i in range(1, degree + 1):
            merged = args[:i - 1] + (_add(args[i - 1], args[i]),) + args[i + 1:]
            total += (-1) ** i * cochain(*merged)
        total += (-1) ** (degree + 1) * cochain(*args[:-1])
        return total

    return d


def cup(a, p: int, b, q: int):
    """Cup product of a p-cochain and a q-cochain: split the arguments."""

    def product(*args):
        if len(args) != p + q:
            raise ValueError(f"expected {p + q} arguments, got {len(args)}")
        return a(*args[:p]) * b(*args[p:])

    return product


def is_cocycle(cochain, degree: int, samples) -> bool:
    """Whether ``d cochain`` vanishes on every supplied tuple of group elements."""
    d = coboundary(cochain, degree)
    return all(d(*tup) == 0 for tup in samples)


def winding_cochain(axis: int, winding: int):
    """The degree-1 class ``w * g_axis``.

    This is a homomorphism ``Z^3 -> Z``, hence automatically a 1-cocycle, and it
    is the image of ``w`` under ``H^1(S^1; Z) = Z`` pulled back along the axis-th
    projection.  Degree ONE.  That is the whole point of the module.
    """

    def alpha(g):
        return winding * g[axis]

    return alpha


def fundamental_pairing(cochain) -> int:
    """Evaluate a 3-cocycle against the fundamental class of T^3.

    The fundamental 3-cycle of the torus is the alternating sum
    ``sum_sigma sgn(sigma) [e_{sigma(1)} | e_{sigma(2)} | e_{sigma(3)}]``, and
    pairing against it is the isomorphism ``H^3(T^3; Z) -> Z``.  So the integer
    returned IS the Dixmier-Douady class, in the normalisation where the class of
    the standard generator is 1.
    """
    basis = [tuple(1 if i == j else 0 for i in range(RANK)) for j in range(RANK)]
    total = 0
    for perm in itertools.permutations(range(RANK)):
        sign = _permutation_sign(perm)
        total += sign * cochain(*(basis[i] for i in perm))
    return total


def _permutation_sign(perm) -> int:
    sign = 1
    perm = list(perm)
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                sign = -sign
    return sign


def betti_rank(k: int, n: int = RANK) -> int:
    """rank H^k(T^n; Z) = C(n, k).  Zero above the dimension, hence H^6(T^3) = 0."""
    return math.comb(n, k) if 0 <= k <= n else 0


def triple_winding_class(w1: int, w2: int, w3: int) -> int:
    """The class of ``alpha_1 u alpha_2 u alpha_3`` in H^3(T^3; Z) = Z.

    Predicted, and the prediction is a theorem rather than a measurement:
    ``w1 * w2 * w3``.  Nonzero whenever all three windings are.
    """
    a1 = winding_cochain(0, w1)
    a2 = winding_cochain(1, w2)
    a3 = winding_cochain(2, w3)
    triple = cup(cup(a1, 1, a2, 1), 2, a3, 1)
    return fundamental_pairing(triple)


def degree_six_is_zero_by_dimension() -> dict:
    """Why the demotion's own statement is true and irrelevant.

    A triple product of degree-2 classes has degree 6.  ``H^6(T^3; Z) = 0``
    because T^3 is three-dimensional -- so the class vanishes for a reason that
    has nothing to do with the windings, the gerbe, or the construction under
    review.  Note the distinction the review's word "vanishes" elides: the
    CLASS is zero; the underlying 6-COCHAIN generally is not.
    """
    beta = lambda g, h: g[0] * h[1]                       # noqa: E731 - a 2-cochain
    six = cup(cup(beta, 2, beta, 2), 4, beta, 2)
    e0 = (1, 0, 0)
    e1 = (0, 1, 0)
    return {
        "rank_H6_T3": betti_rank(6),
        "rank_H3_T3": betti_rank(3),
        "example_degree_six_cochain_value": six(e0, e1, e0, e1, e0, e1),
        "cochain_is_identically_zero": False,
        "class_is_zero": True,
        "reason": "H^6 of a closed 3-manifold is zero above the dimension; the "
                  "cochain need not be, and the Dixmier-Douady class lives in "
                  "H^3, where rank is 1, not in H^6, where rank is 0",
    }
