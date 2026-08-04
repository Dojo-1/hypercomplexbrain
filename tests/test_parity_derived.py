"""Two cone coordinates derived from parity, and what the derivation refuses.

Preregistered in `manifests/qsigma_r3b1_parity_derived_axes_preregistration.json`,
committed before `aionq.parity_derived` existed.

The theorem is trivial -- if `f` is a function and its argument is the same on
both arms, its value is the same on both arms -- so every one of these tests is
really about the premise, the exclusions, or the refusal. A derivation whose
content is entirely in its premise must fail loudly when the premise is absent,
or it is a way of writing zero.
"""

from __future__ import annotations

import json

import pytest

from aionq.parity_derived import (PARITY_DERIVED_AXES, derive_parity_axes,
                                  ParityDerivation)
from aionq.self_audit import repo_root
from aionq.witness_geometry import cone_stratum


def test_the_premise_holds_on_every_seed():
    """The derivation is refused unless parity holds everywhere, so this is
    the load-bearing check and not a formality."""
    derivation = derive_parity_axes(repo_root())
    assert derivation.premise_holds
    assert derivation.seeds_checked == 32
    assert derivation.seeds_failing == ()


def test_both_axes_are_derived_at_an_exact_zero():
    derivation = derive_parity_axes(repo_root())
    assert set(derivation.derived) == set(PARITY_DERIVED_AXES)
    for axis, entry in derivation.derived.items():
        assert entry["delta"] == 0.0
        assert entry["exact"] is True
        assert "all cost models" in entry["quantified_over"]


def test_a_single_failing_seed_refuses_the_whole_derivation(tmp_path):
    """The falsifier, and the reason this is a derivation rather than a habit.

    One seed without verified parity removes the premise, and the correct
    output is then nothing -- not a zero with a caveat. A zero that survived a
    broken premise would be a way of writing zero.
    """
    root = repo_root()
    artifact = json.loads(
        (root / "artifacts/r3b_four_cell/four_cell_calibration.json")
        .read_text(encoding="utf-8"))
    artifact["seed_clusters"][7]["controls"]["resource_parity"] = False

    staged = tmp_path / "artifacts" / "r3b_four_cell"
    staged.mkdir(parents=True)
    (staged / "four_cell_calibration.json").write_text(
        json.dumps(artifact), encoding="utf-8")

    derivation = derive_parity_axes(tmp_path)
    assert not derivation.premise_holds
    assert derivation.derived == {}
    assert derivation.axes_closed == 0
    assert 73008 in derivation.seeds_failing or derivation.seeds_failing
    assert "premise" in derivation.refused


def test_the_excluded_models_are_stated_whether_or_not_the_premise_holds():
    """The exclusion is a property of the argument, not of the data.

    A cost model that prices coherence itself is not a function of the resource
    profile, and the arms differ in exactly that way. Reporting the derivation
    without the exclusion would overstate it.
    """
    derivation = derive_parity_axes(repo_root())
    assert derivation.excluded_models
    assert any("coherence" in note for note in derivation.excluded_models)


# ------------------------------------------------------- effect on the stratum

def test_the_derivation_lowers_the_codimension_from_four_to_two():
    before = cone_stratum(repo_root(), include_derived=False)
    after = cone_stratum(repo_root(), include_derived=True)
    assert before.codimension == 4
    assert after.codimension == 2
    assert set(after.unmeasured) == {"sample_efficiency", "recovery"}
    assert after.detail["derived_axes"] == ("neg_energy", "neg_latency")


def test_it_does_not_pose_the_membership_question():
    """The honest bound, preregistered before the run.

    Two constrained coordinates remain NaN, so the cone's inequalities are
    still not evaluable and HOLD is still the registered outcome. Closing two
    of four is progress and is not a verdict.
    """
    after = cone_stratum(repo_root(), include_derived=True)
    assert not after.posed
    assert after.detail["registered_outcome"] == "HOLD"


def test_the_derived_axes_are_off_by_default():
    """A derived coordinate and a measured one are different objects.

    Mixing them should require asking, so that no caller acquires two
    coordinates it did not know were reasoned rather than observed.
    """
    default = cone_stratum(repo_root())
    assert default.codimension == 4
    assert default.detail["derived_axes"] == ()


def test_the_derived_zero_satisfies_the_no_worse_constraint_with_full_slack():
    after = cone_stratum(repo_root(), include_derived=True)
    for axis in PARITY_DERIVED_AXES:
        assert after.slack[axis] == pytest.approx(0.02)   # 0 + tolerance
    assert after.projected_inside


def test_promotion_is_still_impossible_and_for_an_unrelated_reason():
    """Closing coordinates cannot reach the audit.

    `promote()` refuses to trade audit against effect size, so even a fully
    posed, comfortably interior effect vector yields HOLD while audit strength
    is zero. This test exists so that progress on the stratum is never read as
    progress toward promotion.
    """
    after = cone_stratum(repo_root(), include_derived=True)
    assert after.detail["audit_strength"] == 0.0
    assert after.detail["audit_threshold"] == 1.0
    assert after.projected_inside          # and still
    assert after.detail["registered_outcome"] == "HOLD"
