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


def test_the_recorded_ci_run_reproduced_part_b_on_all_six_pairs():
    # The record is not the CI's word: every verdict is re-derived from its own
    # evidence flags, every outcome is compared with the committed one, and
    # every number is re-checked against the tolerance that was frozen.
    import json

    record = json.loads((ROOT / "artifacts/r6o_part_b_reproduction/reproduction.json")
                        .read_text(encoding="utf-8"))
    committed = json.loads((ROOT / "artifacts/r6k_w1_part_b/crossing.json")
                           .read_text(encoding="utf-8"))["outcome"]
    assert record["tolerance"] == R.TOLERANCE
    assert record["jobs_expected"] == record["jobs_ran"] == record["jobs_green"] == 6
    pairs = {(j["os"], j["python"]) for j in record["jobs"]}
    assert pairs == {(o, p) for o in ("ubuntu-latest", "windows-latest", "macos-latest")
                     for p in ("3.11", "3.12")}
    for job in record["jobs"]:
        report = job["report"]
        assert job["job_conclusion"] == "success"
        assert job["artifact_zip_sha256_downloaded"] == job["artifact_zip_sha256_recorded_by_github"]
        assert report["references"]["verified"] is True
        assert R.reproduction_verdict(report["evidence"]) == report["verdict"] == job["verdict"] == "REPRODUCED"
        assert report["outcome"] == committed
        assert report["flags_differing"] == 0
        numbers = report["numbers"]
        assert numbers["scientific_leaves_compared"] == 800
        assert numbers["exceeding_tolerance"] == numbers["discrete_mismatches"] == 0
        assert numbers["worst_absolute_difference"] <= R.TOLERANCE
    assert record["all_reproduced"] is True
