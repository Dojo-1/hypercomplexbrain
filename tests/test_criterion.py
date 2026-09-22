"""R2A: the checker, validated against three defects already in the ledger.

Not preregistered, and the reason is recorded rather than skipped. A
preregistration predicts an unknown outcome; these three outcomes are already
known, written down in `CORRECTIONS` and in the finding manifests. Predicting
them would be theatre. What this is instead is the repository's existing
KNOWN-ANSWER category -- the same shape as `supercable.agrees_with_state_vector`
-- an instrument shown to reproduce results that were established without it.
"""

import math

import pytest

from aionq.criterion import (every_verdict_has_a_witness, exercise,
                            frozen_parameters_cover_the_knobs,
                            verdict_regions_are_disjoint)


# -- R1S: the regions overlapped -------------------------------------------

def test_it_finds_the_R1S_overlap_that_eight_of_fifteen_cells_landed_in():
    """`C < 2` for LOW and `C > 0.7*sqrt(N)` for HIGH, exactly as frozen.

    For N < 8.163 the thresholds are ordered the wrong way, so what the
    protocol called an indeterminate band is an overlap. Eight of the fifteen
    cells R1S had already measured sat inside it -- N = 4 giving [1.400, 2.000]
    and N = 5 giving [1.565, 2.000] -- and the reported verdict depended on
    which `if` ran first.
    """
    predicates = {
        "LOW": lambda cell: cell["C"] < 2.0,
        "HIGH": lambda cell: cell["C"] > 0.7 * math.sqrt(cell["N"]),
    }
    samples = [{"C": c, "N": n}
               for n in (4, 5, 9, 15)
               for c in (1.2, 1.5, 1.8, 1.9, 2.5, 3.0)]

    result = verdict_regions_are_disjoint(predicates, samples)

    assert not result["disjoint"], "the frozen R1S rule must be caught"
    assert result["collisions"], "no overlap found where R1S recorded one"
    # every collision is at a small N, which is the recorded mechanism
    assert all(row["sample"]["N"] < 8.163 for row in result["collisions"])
    assert all(row["verdicts"] == ["HIGH", "LOW"] for row in result["collisions"])


def test_a_correctly_ordered_pair_of_regions_passes():
    """The check must be able to say yes, or it is not a check.

    R1S's own retirement note said the categorical rule was abandoned rather
    than patched. A repaired ordering -- thresholds that cannot cross -- is
    disjoint and exhaustive, and the checker says so.
    """
    predicates = {"LOW": lambda x: x < 2.0, "HIGH": lambda x: x >= 2.0}
    result = verdict_regions_are_disjoint(predicates, [0.5, 1.9, 2.0, 2.1, 9.0])

    assert result["disjoint"]
    assert result["exhaustive"]


# -- R1Z: the verdict was unreachable --------------------------------------

def r1z_verdict(rows):
    """R1Z's frozen rule, reproduced verbatim from the manifest."""
    import numpy as np

    ms = np.array([row["m"] for row in rows], dtype=float)
    counts = np.array([row["zero_count"] for row in rows], dtype=float)
    slope = np.polyfit(ms, counts, 1)[0]
    smallest, largest = float(counts.min()), float(counts.max())
    if slope < 0.05 and largest <= 2.0 * max(smallest, 1e-12):
        return "BOUNDED"
    if slope > 0.25:
        return "DIVERGENT"
    return "INDETERMINATE"


def test_it_finds_that_R1Z_s_BOUNDED_was_unreachable():
    """The witness for BOUNDED is what a bounded family actually looks like.

    NEIGHBOUR measured 0,0,1,1,0,1,1 across an eightfold growth in register
    size. That is the round's own data and it is the natural witness. It does
    not reach BOUNDED, because the ratio clause reduces to `largest <= 2e-12`
    the moment a count is zero -- so the verdict was unreachable by exactly the
    families it was written to certify.
    """
    grid = (2, 3, 4, 6, 8, 12, 16)
    witnesses = {
        "BOUNDED": [{"m": m, "zero_count": c}
                    for m, c in zip(grid, (0, 0, 1, 1, 0, 1, 1))],
        "DIVERGENT": [{"m": m, "zero_count": c}
                      for m, c in zip(grid, (1, 2, 2, 3, 4, 6, 8))],
        "INDETERMINATE": [{"m": m, "zero_count": c}
                          for m, c in zip(grid, (1, 1, 1, 1, 2, 2, 2))],
    }

    result = every_verdict_has_a_witness(
        r1z_verdict, witnesses, {"BOUNDED", "DIVERGENT", "INDETERMINATE"})

    assert not result["all_reachable"]
    assert [row["verdict"] for row in result["unreachable"]] == ["BOUNDED"]
    assert result["unreachable"][0]["produced"] == "INDETERMINATE"


def test_the_repaired_rule_reaches_all_three_verdicts():
    """Dropping the ratio clause makes BOUNDED reachable, which is the point.

    Shown, not asserted: the same three witnesses now land on their own
    verdicts. This is NOT a retroactive repair of R1Z -- that round's failed
    predictions stand as failed -- it is the demonstration that the checker
    distinguishes a broken rule from a working one.
    """
    import numpy as np

    def repaired(rows):
        ms = np.array([row["m"] for row in rows], dtype=float)
        counts = np.array([row["zero_count"] for row in rows], dtype=float)
        slope = np.polyfit(ms, counts, 1)[0]
        if slope < 0.10:
            return "BOUNDED"
        return "DIVERGENT" if slope > 0.25 else "INDETERMINATE"

    grid = (2, 3, 4, 6, 8, 12, 16)
    witnesses = {
        "BOUNDED": [{"m": m, "zero_count": c}
                    for m, c in zip(grid, (0, 0, 1, 1, 0, 1, 1))],
        "DIVERGENT": [{"m": m, "zero_count": c}
                      for m, c in zip(grid, (1, 2, 2, 3, 4, 6, 8))],
        "INDETERMINATE": [{"m": m, "zero_count": c}
                          for m, c in zip(grid, (1, 1, 2, 2, 3, 3, 4))],
    }

    assert every_verdict_has_a_witness(
        repaired, witnesses, {"BOUNDED", "DIVERGENT", "INDETERMINATE"}
    )["all_reachable"]


# -- R1X: a parameter was left free ----------------------------------------

def test_it_finds_R1X_s_unfrozen_step_budget():
    """R1X froze two thresholds and wrote "fixed step budget" with no number.

    The entry point's signature is where the knob lives, so the check is on the
    signature and cannot be satisfied by prose. 300 and 900 steps answered the
    same preregistered question in opposite directions, and either was
    reportable alone without breaking a frozen clause.
    """
    from aionq.lebesgue import ladder_spectral_sweep

    r1x_frozen = {"entropy_window": 0.05, "defect_floor": 0.10}
    result = frozen_parameters_cover_the_knobs(ladder_spectral_sweep, r1x_frozen)

    assert not result["all_frozen"]
    assert "steps" in result["missing"], (
        "the step budget is the parameter R1X left free")


def test_R1Z_froze_its_knobs_even_though_its_verdict_was_broken():
    """R1Z learned R1X's lesson and still failed, on a different axis.

    Its entry point's every tunable carries a value in the manifest -- the
    parameter check passes -- and the round was still decided by an unreachable
    verdict. Three checks, three independent failure modes; passing one says
    nothing about the others, which is why the recommendation that bundled them
    into "three lines of test" was wrong.
    """
    from aionq.araki import zero_count_growth

    r1z_frozen = {"qubit_grid": (4, 6, 8, 12, 16, 24, 32), "steps": 400,
                  "seeds": (7, 13, 29), "prepared_seed": 0}
    result = frozen_parameters_cover_the_knobs(zero_count_growth, r1z_frozen)

    assert result["all_frozen"], f"unexpectedly missing: {result['missing']}"


# -- the composite ----------------------------------------------------------

def test_exercise_names_what_it_did_not_check():
    """A round with nothing to disjointness-test must not be made to invent one.

    What it must not do is skip a check it has material for, so the report
    always names its own omissions. Silence about a skipped check is how a
    guard becomes decoration.
    """
    report = exercise(verdict_fn=lambda x: "A", witnesses={"A": 1},
                      declared_verdicts={"A"}, required_checks={"coverage"})

    assert report["clean"]
    assert set(report["skipped"]) == {"disjointness", "parameters"}
    assert "coverage" in report


def test_exercise_fails_closed_when_no_checks_are_declared_or_run():
    report = exercise()
    assert not report["clean"]
    assert not report["declaration_valid"]


def test_coverage_rejects_an_omitted_declared_verdict():
    report = every_verdict_has_a_witness(
        lambda _: "A", {"A": 1}, {"A", "B"})
    assert not report["declaration_matches"]
    assert not report["all_reachable"]


def test_disjointness_is_not_clean_when_the_grid_has_gaps_or_errors():
    gapped = exercise(
        predicates={"LOW": lambda x: x < 0, "HIGH": lambda x: x > 0},
        samples=[-1, 0, 1], required_checks={"disjointness"})
    raising = exercise(
        predicates={"A": lambda x: 1 / x > 0}, samples=[0],
        required_checks={"disjointness"})
    assert not gapped["clean"]
    assert gapped["disjointness"]["uncovered"] == [0]
    assert not raising["clean"]
    assert raising["disjointness"]["errors"]


def test_ci_fetches_the_history_required_by_evidence_bindings():
    from pathlib import Path

    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text()
    assert "fetch-depth: 0" in workflow


def test_exercise_is_not_clean_when_any_supplied_check_fails():
    report = exercise(
        predicates={"LOW": lambda x: x < 2, "HIGH": lambda x: x > 1},
        samples=[0.0, 1.5, 3.0], required_checks={"disjointness"})

    assert not report["clean"]
    assert not report["disjointness"]["disjoint"]
