"""QSigma-R6O: the reproduction's rule, references and binding.

The recomputation itself is NOT asserted here. It runs in its own CI job per
platform, so that a platform whose numbers move past 1e-10 reads OUTCOME_ONLY
in that job and does not redden the correctness suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aionq import part_b_reproduction as R

ROOT = Path(__file__).resolve().parent.parent


def test_frozen_rule_is_exercised_clean():
    receipt = R.exercise_the_frozen_rule()
    assert receipt["clean"] is True


@pytest.mark.parametrize("change, verdict", [
    ({}, "REPRODUCED"),
    ({"numbers_within_tolerance": False}, "OUTCOME_ONLY"),
    ({"decision_identical": False}, "NOT_REPRODUCED"),
    ({"decision_identical": False, "numbers_within_tolerance": False}, "NOT_REPRODUCED"),
    ({"computed": False}, "INVALID"),
    ({"references_verified": False}, "INVALID"),
])
def test_verdict_on_witnesses(change, verdict):
    base = {"references_verified": True, "computed": True,
            "decision_identical": True, "numbers_within_tolerance": True}
    assert R.reproduction_verdict({**base, **change}) == verdict


def test_truthy_non_booleans_do_not_reach_reproduced():
    assert R.reproduction_verdict({"references_verified": 1, "computed": "yes",
                                   "decision_identical": True,
                                   "numbers_within_tolerance": True}) == "INVALID"


def test_tolerance_is_part_b_committed_tolerance():
    assert R.TOLERANCE == 1e-10


def test_live_references_verify():
    refs = R.references(ROOT)
    assert refs == {"map_rows_at_c_raw": True, "crossing_at_c_raw": True,
                    "r6n_licence_verified": True,
                    "extraction_is_the_one_that_ran": True, "verified": True}


def test_extraction_binding_detects_an_edit():
    runner = (ROOT / "experiments/run_part_b_crossing.py").read_text(encoding="utf-8")
    edited = runner.replace("def extract_map_rows(", "def extract_map_rows(  ", 1)
    assert edited != runner
    executed = R._function_source(R._blob(ROOT, R.C_EXEC, "experiments/run_part_b_crossing.py")
                                  .decode("utf-8"), "extract_map_rows")
    assert executed == R._function_source(runner, "extract_map_rows")
    assert executed != R._function_source(edited, "extract_map_rows")


def test_reproduce_takes_no_knobs():
    import inspect
    params = inspect.signature(R.reproduce).parameters
    assert list(params) == ["root"]
    assert params["root"].default is inspect.Parameter.empty
