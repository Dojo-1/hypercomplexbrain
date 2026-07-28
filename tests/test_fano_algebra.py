"""Tests for the S8 crosstalk decomposition, which existed only as prose.

These exist because three commits asserted these numbers in comment blocks and
added no executable lines. A test is the cheapest thing that would have caught
that: prose cannot fail.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from aionq.fano_algebra import (SO8_DIM, alternating_drive, channel_generator,
                                commutator, diamond_holonomy, fano_lines,
                                frobenius_inner, random_rank_census,
                                rank_decomposition, signal_crosstalk_projection,
                                wilson_interval)

FANO = fano_lines()
GENS = [channel_generator(t) for t in FANO]


def test_fano_is_the_steiner_system():
    assert len(FANO) == 7
    pairs = {p for t in FANO for p in itertools.combinations(sorted(t), 2)}
    assert len(pairs) == 21
    for a, b in itertools.combinations(FANO, 2):
        assert len(set(a) & set(b)) == 1


def test_generators_are_antisymmetric():
    """Channel generators must live in so(8) or none of the rest means anything."""
    for G in GENS:
        assert np.max(np.abs(G + G.T)) < 1e-12


def test_generator_uses_the_whole_line_not_its_first_element():
    """Regression on the S8 bug that made two channels identical.

    Using ``triple[0]`` alone, lines sharing a first element collapse to the same
    generator, their commutator is zero, and the design scores perfect separation
    by having fewer channels. Distinct lines must give distinct generators.
    """
    for a, b in itertools.combinations(range(7), 2):
        assert np.max(np.abs(GENS[a] - GENS[b])) > 1e-6


# ------------------------------------------------------- orthogonality (generic)

def test_crosstalk_is_orthogonal_to_the_signal_space():
    result = signal_crosstalk_projection(FANO)
    assert result["n_products"] == 7 * 21
    assert result["worst_normalised_inner"] < 1e-12


def test_orthogonality_is_generic_not_a_design_property():
    """The control that stopped this being claimed as a Fano result.

    Random triple systems are orthogonal too. Whatever the design buys, it is not
    this -- and 5e-17 across 147 inner products looks exactly like a theorem.
    """
    rng = np.random.default_rng(4)
    all_triples = list(itertools.combinations(range(1, 8), 3))
    for _ in range(25):
        idx = rng.choice(len(all_triples), size=7, replace=False)
        cand = [all_triples[i] for i in idx]
        assert signal_crosstalk_projection(cand)["worst_normalised_inner"] < 1e-12


# --------------------------------------------------------------- rank (specific)

def test_the_algebra_splits_seven_plus_twentyone():
    r = rank_decomposition(FANO)
    assert (r["signal_rank"], r["crosstalk_rank"], r["union_rank"]) == (7, 21, 28)
    assert r["union_rank"] == SO8_DIM
    assert r["splits_the_algebra"]


def test_union_rank_is_the_claim_not_the_arithmetic():
    """7 + 21 = 28 is arithmetic; rank(union) = 28 is the assertion.

    They agree only if the two spans meet trivially. Asserted separately so a
    future change cannot satisfy the sum while the spans overlap.
    """
    r = rank_decomposition(FANO)
    assert r["signal_rank"] + r["crosstalk_rank"] == r["union_rank"]


def test_random_systems_are_rank_deficient_in_the_median():
    census = random_rank_census(200, seed=11)
    assert census["median_rank"] < 21
    assert census["max_rank"] <= 21
    assert 0.3 < census["full_rank_fraction"] < 0.7


def test_497_and_489_are_the_same_measurement():
    """The reported disagreement between this repo and an external audit.

    Both are inside the Wilson interval of a fresh run. The lesson is in the
    reporting, not the arithmetic: a Monte Carlo proportion quoted as a bare
    integer with no interval and no seed will look like it disagrees with itself.
    """
    census = random_rank_census(1000, seed=20260728)
    lo, hi = census["wilson_95"]
    assert lo <= 0.497 <= hi
    assert lo <= 0.489 <= hi
    assert lo <= census["full_rank_fraction"] <= hi


def test_wilson_interval_brackets_the_point_estimate():
    lo, hi = wilson_interval(498, 1000)
    assert lo < 0.498 < hi
    assert 0.05 < hi - lo < 0.10


# ------------------------------------------------------------------ instruments

@pytest.mark.parametrize("theta,digits", [(0.05, 3), (0.01, 4), (0.001, 6)])
def test_diamond_holonomy_converges_as_first_order_in_theta(theta, digits):
    """The 'agrees to six figures' claim, with the angle it needs.

    The group-commutator estimate carries an O(theta) BCH remainder, so six
    figures needs theta ~ 1e-3. The original addendum recorded no theta, which is
    why the claim was uncheckable rather than wrong.
    """
    exact = float(np.linalg.norm(commutator(GENS[0], GENS[1])))
    measured = diamond_holonomy(GENS[0], GENS[1], theta)
    assert abs(measured - exact) / exact < 10.0 ** (-digits)


def test_alternating_drive_is_linear_to_leading_order_and_bends_down():
    """Linear accumulation, with the curvature that must accompany it.

    ||U^N - I|| is a CHORD on a curve of linearly growing arc length, so the
    per-cycle value must fall below the leading order and must fall MONOTONICALLY.
    A flat per-cycle would mean the chord equalled the arc, which is impossible.
    """
    exact = float(np.linalg.norm(commutator(GENS[0], GENS[1])))
    theta = 0.05
    per_cycle = [alternating_drive(GENS[0], GENS[1], theta, n)["per_cycle"]
                 for n in (1, 2, 4, 8, 16, 32, 64)]
    leading = theta ** 2 * exact
    assert abs(per_cycle[0] - leading) / leading < 1e-3
    assert per_cycle == sorted(per_cycle, reverse=True)
    assert (max(per_cycle) - min(per_cycle)) / max(per_cycle) < 1e-3


def test_commuting_pair_emits_nothing():
    """The null has to be exact or the signal means nothing."""
    A = np.zeros((8, 8))
    A[1, 2], A[2, 1] = 1.0, -1.0
    B = np.zeros((8, 8))
    B[3, 4], B[4, 3] = 1.0, -1.0
    assert np.max(np.abs(commutator(A, B))) < 1e-14
    assert alternating_drive(A, B, 0.05, 64)["total"] < 1e-12


def test_frobenius_inner_is_symmetric_and_positive_definite():
    assert frobenius_inner(GENS[0], GENS[1]) == pytest.approx(
        frobenius_inner(GENS[1], GENS[0]))
    assert frobenius_inner(GENS[0], GENS[0]) > 0
