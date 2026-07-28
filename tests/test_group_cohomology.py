"""Cup products on H*(T^3; Z): exact integer tests, no tolerances.

Every assertion here is an equality between integers.  If any of them needed a
tolerance, the module would be doing something other than what it claims.
"""

from __future__ import annotations

import itertools
import random

import pytest

from aionq.group_cohomology import (betti_rank, coboundary, cup,
                                    degree_six_is_zero_by_dimension,
                                    fundamental_pairing, is_cocycle,
                                    triple_winding_class, winding_cochain)

RNG = random.Random(20260728)
SAMPLE = [tuple(RNG.randint(-5, 5) for _ in range(3)) for _ in range(24)]


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("winding", [-3, -1, 0, 1, 4])
def test_winding_cochain_is_a_cocycle(axis, winding):
    """A homomorphism Z^3 -> Z is automatically a 1-cocycle."""
    alpha = winding_cochain(axis, winding)
    assert is_cocycle(alpha, 1, itertools.product(SAMPLE[:8], repeat=2))


def test_coboundary_squares_to_zero():
    """d^2 = 0 on an arbitrary 1-cochain, including a non-cocycle."""
    weird = lambda g: g[0] * g[1] - 3 * g[2] ** 2        # noqa: E731
    d1 = coboundary(weird, 1)
    d2 = coboundary(d1, 2)
    for tup in itertools.product(SAMPLE[:6], repeat=3):
        assert d2(*tup) == 0


def test_cup_product_of_two_cocycles_is_a_cocycle():
    a = winding_cochain(0, 2)
    b = winding_cochain(1, 5)
    assert is_cocycle(cup(a, 1, b, 1), 2, itertools.product(SAMPLE[:6], repeat=3))


@pytest.mark.parametrize("w", [(1, 1, 1), (2, 3, 4), (3, -2, 5), (0, 7, 9),
                               (-1, -1, -1), (6, 6, 6), (12, -5, 1), (7, 0, 0)])
def test_triple_winding_class_is_exactly_the_product(w):
    """The claim the peer review demoted, on the degree where it lives."""
    assert triple_winding_class(*w) == w[0] * w[1] * w[2]


def test_triple_product_is_nonzero_when_windings_are():
    """H^3(T^3; Z) = Z is not the zero group, and the class reaches it."""
    assert triple_winding_class(1, 1, 1) == 1
    assert triple_winding_class(3, 5, 7) == 105


def test_cohomology_ranks_of_the_three_torus():
    assert [betti_rank(k) for k in range(8)] == [1, 3, 3, 1, 0, 0, 0, 0]


def test_degree_six_vanishes_but_the_cochain_does_not():
    """The distinction the word 'vanishes' elides.

    H^6(T^3; Z) = 0 because T^3 is three-dimensional.  That is true and it is a
    statement about the ambient group, not about any construction inside it.  The
    underlying 6-cochain is not zero, which is why 'the cup product vanishes'
    needs saying more carefully than it was said.
    """
    result = degree_six_is_zero_by_dimension()
    assert result["rank_H6_T3"] == 0
    assert result["rank_H3_T3"] == 1
    assert result["example_degree_six_cochain_value"] != 0


def test_the_two_degrees_are_not_the_same_computation():
    """Degree-1 classes cup to degree 3; degree-2 classes cup to degree 6.

    Winding numbers are classes in H^1(S^1; Z) = Z pulled back along the three
    projections.  c1 is a degree-2 class.  Three of the first land where the
    Dixmier-Douady class lives; three of the second land where nothing does.
    """
    assert 1 + 1 + 1 == 3 and betti_rank(3) == 1
    assert 2 + 2 + 2 == 6 and betti_rank(6) == 0
