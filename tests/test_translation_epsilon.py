"""The translation law, run as a test of itself (QSigma-R6h)."""

from __future__ import annotations

import pytest

from aionq.translation_epsilon import (CARRIER_TERMS, TAU, TRANSLATION_TERMS,
                                       classify_translation, cosmos_lift_chain,
                                       epsilon_split, flattened_translation,
                                       lift_is_valid, sl2_translation,
                                       su2_translation)


# ------------------------------------------------- the law tests the law

def test_compact_source_is_flattened_because_it_has_no_remainder():
    """epsilon = 0 is a statement about the SOURCE, not a compliment.

    A translation can only fail to lose remainder if there was none to lose.
    SU(2) is compact: p = 1 identically, no erasure branch, source exhausted by
    the target. If this came out nonzero the measure would not be reading
    remainder at all.
    """
    r = su2_translation()
    assert r["split"]["translation_epsilon"] == pytest.approx(0.0, abs=1e-12)
    assert r["classification"] == "flattened"


def test_non_compact_source_is_not_flattened():
    r = sl2_translation()
    assert r["split"]["translation_epsilon"] > 1e-6
    assert r["classification"] != "flattened"


def test_the_trichotomy_separates_all_three_cases():
    cases = [su2_translation(), sl2_translation(), flattened_translation()]
    assert {c["classification"] for c in cases} == {
        "flattened", "resonant", "disconnected"}


# ------------------------------------- the correction the round had to make

def test_the_verbatim_seven_term_sum_does_not_discriminate():
    """The preregistered E2 failed, and pinning that matters.

    On the verbatim sum SL(2,R) scores 3.434 and classifies DISCONNECTED -- the
    working encoding this programme is built on, called unusable. Three terms are
    carrier constants, not translation defects, and offsets added to every
    candidate cannot separate candidates.
    """
    r = sl2_translation()
    assert r["naive_classification"] == "disconnected"
    assert r["classification"] == "resonant"
    assert r["split"]["carrier_offset"] > r["split"]["translation_epsilon"]


def test_carrier_terms_are_constant_across_translations():
    """Which is exactly why they cannot classify."""
    a = sl2_translation()["components"]
    b = flattened_translation()["components"]
    assert a["associator_defect"] == pytest.approx(b["associator_defect"])
    assert a["curvature_mismatch"] == pytest.approx(b["curvature_mismatch"])


def test_translation_terms_do_vary():
    a = sl2_translation()["split"]["translation_epsilon"]
    b = flattened_translation()["split"]["translation_epsilon"]
    assert b > 5 * a


def test_the_threshold_was_not_tuned():
    """tau stays at 1.0. Raising it until the answer came out right is the
    failure this repository has refused twice already."""
    assert TAU == 1.0
    assert classify_translation(0.0) == "flattened"
    assert classify_translation(0.5) == "resonant"
    assert classify_translation(1.5) == "disconnected"


def test_terms_are_partitioned_without_overlap_or_omission():
    assert not (set(CARRIER_TERMS) & set(TRANSLATION_TERMS))
    comps = sl2_translation()["components"]
    assert set(comps) == set(CARRIER_TERMS) | set(TRANSLATION_TERMS)
    sp = epsilon_split(comps)
    assert sp["carrier_offset"] + sp["translation_epsilon"] == pytest.approx(
        sp["naive_total"], abs=1e-12)


# ------------------------------------------------------------ cosmos lifts

def test_lifts_are_valid_through_the_octonions():
    for a, b in ((1, 2), (2, 4), (4, 8)):
        assert lift_is_valid(a, b)["valid_lift"]


def test_lift_to_cd32_is_false_ascent():
    """The skill's 'recursive flattening' with a computed cause, reusing R6c."""
    r = lift_is_valid(8, 32)
    assert not r["valid_lift"]
    assert r["target_has_zero_divisors"]
    assert not r["target_is_division_algebra"]


def test_lift_chain_has_exactly_one_invalid_step():
    c = cosmos_lift_chain()
    assert c["n_valid"] == 3
    assert c["first_invalid"]["to_dim"] == 32
