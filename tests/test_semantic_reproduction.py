"""Tests for the cross-platform comparator (QSigma-R6k-W1).

Most of these try to make the comparator report agreement it has not earned,
because that is the only failure mode that matters here. A comparator that says
CONTRADICTED when it should say CONFIRMED costs a round; one that says CONFIRMED
when it should say nothing manufactures a witness, and manufacturing a witness is
the single thing this repository's evidence apparatus exists to prevent.
"""

from __future__ import annotations

import json

import pytest

from aionq.semantic_reproduction import (ENVIRONMENT_METADATA_LEAVES,
                                         MINIMUM_SCIENTIFIC_BACKSTOP,
                                         MINIMUM_SCIENTIFIC_FRACTION,
                                         compare_results, flatten, leaf_kind,
                                         perturb_leaf, reproduction_verdict,
                                         structural_checks)
from aionq.self_audit import repo_root

TOL = 1e-10


def _doc(**over):
    base = {
        "schema": "r6k.v1",
        "round": "QSigma-R6k",
        "ambient_dimension": 16,
        "codewords_per_depth": 32,
        "depths": [0.1, 0.5],
        "noise_strengths": [0.0, 0.01],
        "primary_cell_count": 96,
        "decision": {"verdict": "ANISOTROPIC_ANGULAR_GAIN_NO_RADIAL_GAIN"},
        "rows": [{"margin": 0.25, "passed": True, "query_digest": "sha256:aa"},
                 {"margin": -0.5, "passed": False, "query_digest": "sha256:bb"}],
        "input_hashes": ["sha256:cc", "sha256:dd"],
        "resource_ledger": {"compiler_proxy": {"qiskit_version": "2.3.0",
                                               "gate_count": 40}},
    }
    base.update(over)
    return base


def _verdict(a, b, events=None, **kw):
    # sequence_equal is supplied explicitly: the verdict defaults a MISSING
    # population to "disagrees", which is the fail-closed direction, so a helper
    # that omits it contradicts everything. Three tests failed exactly that way
    # when the population was added.
    ev = events or {"row_count_equal": True, "key_order_equal": True,
                    "sequence_equal": True}
    return reproduction_verdict(compare_results(a, b, TOL),
                                structural_checks(a, b), ev, **kw)


# ------------------------------------------------ classification of leaves

def test_a_boolean_is_never_compared_under_a_numeric_tolerance():
    """The trap: in Python True is an int, and False is 0.

    A verdict flag flipped from False to True would sit 1.0 apart, which passes
    nothing -- but a flag flipped in a document where the comparator coerced it
    to float would be one more number in a sea of agreeing numbers. Classifying
    bool as DISCRETE before int is what stops a failed check from being averaged
    away. This is the same defect as serialising np.bool_ with default=str and
    writing the string "True" for a FAILED check.
    """
    assert leaf_kind(".rows[0].passed", True) == "discrete"
    assert leaf_kind(".rows[0].passed", False) == "discrete"
    assert leaf_kind(".rows[0].margin", 0.25) == "scientific"
    a, b = _doc(), _doc()
    b["rows"][0]["passed"] = False
    r = compare_results(a, b, TOL)
    assert r["discrete_mismatches"], "a flipped flag must be a mismatch"
    assert r["scientific_leaves_exceeding_tolerance"] == []


@pytest.mark.parametrize("path", [
    ".input_hashes[0]", ".rows[3].query_digest", ".rows[0].template_digest",
    ".manifest.sha256", ".thing_sha256",
])
def test_digest_paths_are_identity_not_science(path):
    assert leaf_kind(path, "sha256:beef") == "identity"


def test_a_sha256_value_is_identity_even_on_an_innocent_path():
    """Two independent routes, because either alone can be evaded by renaming."""
    assert leaf_kind(".some.harmless.field", "sha256:beef") == "identity"


def test_the_environment_exclusion_list_is_closed_at_exactly_one_entry():
    """Amendment W1-C1 closed it. Widening it must be a visible edit here.

    An exclusion list that can grow quietly is a tolerance that can be widened
    quietly. This pins the set so adding a second entry breaks a test rather
    than silently removing another way for the comparison to fail.
    """
    assert set(ENVIRONMENT_METADATA_LEAVES) == {
        ".resource_ledger.compiler_proxy.qiskit_version"}


def test_the_resource_ledger_is_not_wholesale_excluded():
    """Only the version string. The integers next to it must still be compared."""
    assert leaf_kind(".resource_ledger.compiler_proxy.gate_count", 40) == "scientific"
    a, b = _doc(), _doc()
    b["resource_ledger"]["compiler_proxy"]["gate_count"] = 41
    r = compare_results(a, b, TOL)
    assert ".resource_ledger.compiler_proxy.gate_count" in \
        r["scientific_leaves_exceeding_tolerance"]


# --------------------------------------------- can the comparator report a problem?

def test_identical_documents_agree_exactly():
    r = compare_results(_doc(), _doc(), TOL)
    assert r["worst_absolute_difference"] == 0.0
    assert r["scientific_leaves_exceeding_tolerance"] == []
    assert r["discrete_mismatches"] == []


def test_one_float_past_the_tolerance_contradicts():
    a = _doc()
    b = perturb_leaf(a, ".rows[0].margin", 1e-9)
    assert _verdict(a, b)["verdict"] == "CONTRADICTED"


def test_one_float_inside_the_tolerance_does_not():
    a = _doc()
    b = perturb_leaf(a, ".rows[0].margin", 1e-12)
    assert _verdict(a, b, minimum_fraction=0.0, backstop=1)["verdict"] == "CONFIRMED"


def test_perturb_leaf_actually_mutates_the_copy_it_returns():
    """Regression on a tamper helper that recursed into a COPY.

    An earlier helper in this repository built ``{i: x for i, x in enumerate(v)}``
    to walk into lists, mutated that dict, and changed nothing -- so it validated
    an untampered document and the passing result read as "the check is
    decorative" when the check was fine. Twice. The tamper must be shown to bite
    before any conclusion is drawn from a tampered run.
    """
    a = _doc()
    b = perturb_leaf(a, ".rows[1].margin", 1e-3)
    assert b != a
    assert b["rows"][1]["margin"] != a["rows"][1]["margin"]
    assert a["rows"][1]["margin"] == -0.5, "the original must be untouched"


def test_a_changed_verdict_cannot_be_diluted_by_agreeing_floats():
    """Structural fields are checked by name, not by scan.

    4000 leaves agreeing to 1e-11 must not drown one changed verdict string. The
    structural check exists precisely so the load-bearing field cannot pass by
    being outvoted.
    """
    a = _doc()
    b = _doc(decision={"verdict": "SOMETHING_ELSE"})
    st = structural_checks(a, b)
    assert st["all_equal"] is False
    assert st["rows"]["verdict"]["equal"] is False
    assert _verdict(a, b)["verdict"] == "CONTRADICTED"


def test_a_reordered_list_is_a_mismatch_not_a_match():
    """Order is part of the claim for a retrieval grid and an event trace."""
    a = _doc()
    b = _doc(rows=list(reversed(_doc()["rows"])))
    assert _verdict(a, b)["verdict"] == "CONTRADICTED"


def test_keys_missing_from_one_side_are_reported_not_treated_as_agreement():
    """R6k's committed result carries 43 leaves the library cannot emit.

    A comparator that silently intersected would report perfect agreement while
    never looking at them. They must appear in the report.
    """
    a = _doc(extra_runner_check=True)
    b = _doc()
    r = compare_results(a, b, TOL)
    assert ".extra_runner_check" in r["only_in_produced"]
    assert r["only_in_reproduced"] == []


# ----------------------------------------------------- vacuity is not agreement

def test_a_comparison_with_almost_no_science_is_vacuous_not_confirmed():
    """The defect this whole round exists to avoid reproducing.

    apply_witness would compare R6k against a verifier by hashing eleven tracked
    repository files and zero computed outputs, and record independence. A
    comparison that agreed on nothing measurable has not disagreed; it has
    established nothing, and VACUOUS is a distinct outcome for exactly that.
    """
    doc = {"schema": "x", "input_hashes": ["sha256:%02x" % i for i in range(50)],
           "one_number": 1.0}
    v = _verdict(doc, dict(doc))
    assert v["verdict"] == "VACUOUS"
    assert v["enough_compared"] is False
    assert v["scientific_leaves_compared"] == 1


def test_vacuous_outranks_nothing_and_is_not_a_pass():
    doc = {"input_hashes": ["sha256:a"], "n": 1.0}
    assert _verdict(doc, dict(doc))["verdict"] != "CONFIRMED"


def test_the_floor_is_relative_so_it_can_be_stated_without_knowing_the_answer():
    """Amendment W1-C2. The absolute floor was guessed from the wrong denominator.

    4000 was taken from the total leaf count before a comparator existed that
    could separate digests from numbers, and was unreachable by construction.
    'Not vacuous' means most of what is not a digest is a compared number -- a
    property of the comparison, not of one pair of files.
    """
    assert 0.0 < MINIMUM_SCIENTIFIC_FRACTION < 1.0
    assert MINIMUM_SCIENTIFIC_BACKSTOP >= 1000
    # A document that is three-quarters discrete strings fails the fraction rule
    # however many leaves it has.
    doc = {"n%d" % i: (float(i) if i % 4 == 0 else "text%d" % i)
           for i in range(8000)}
    v = _verdict(doc, dict(doc))
    assert v["scientific_fraction"] < MINIMUM_SCIENTIFIC_FRACTION
    assert v["verdict"] == "VACUOUS"


def test_flatten_indexes_lists_rather_than_sorting_them():
    f = flatten({"a": [10, 20]})
    assert f == {".a[0]": 10, ".a[1]": 20}


# ------------------------------------------------------ the committed result

def _artifact():
    path = repo_root() / "artifacts" / "r6k_w1_semantic_reproduction" / "comparison.json"
    if not path.is_file():
        pytest.skip("run experiments/run_r6k_semantic_reproduction.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_recorded_reproduction_is_confirmed_with_its_controls_green():
    r = _artifact()
    assert r["verdict"] == "CONFIRMED"
    assert all(r["controls"].values()), r["controls"]
    assert r["control_C1"]["verdict"] == "CONTRADICTED"


def test_the_recorded_reproduction_compared_real_numbers():
    """C2 and C3 as assertions on the artifact rather than on the run."""
    r = _artifact()
    assert r["verdict_detail"]["scientific_leaves_compared"] > 3000
    assert r["verdict_detail"]["scientific_fraction"] >= MINIMUM_SCIENTIFIC_FRACTION
    assert r["comparison"]["identity_leaves"] > 400
    assert r["comparison"]["worst_absolute_difference"] < r["tolerance"]


def test_the_recorded_reproduction_left_every_r6k_artifact_alone():
    """R6l pins those hashes. This round must not have touched them."""
    r = _artifact()
    assert r["controls"]["no_r6k_artifact_was_written"] is True
    for path in r["comparison"]["only_in_produced"]:
        assert not path.startswith(".artifacts")
    assert r["producer_of_record"] == "experiments/run_equal_resource_reservoir.py"
    assert r["verifier"] == "claude-code-linux"


def test_a_contradiction_is_never_filed_as_inconclusive():
    """Precedence, which was written the wrong way round first.

    A comparison can be too thin to CONFIRM anything and still have found a real
    disagreement in what it did compare. If VACUOUS outranked CONTRADICTED, that
    disagreement would be filed as "inconclusive" -- a detected failure reported
    as an absence of evidence. Vacuity bounds what can be confirmed; it says
    nothing about what has been refuted.
    """
    a = {"n": 1.0, "flag": True}
    b = {"n": 1.0, "flag": False}
    v = _verdict(a, b)
    assert v["enough_compared"] is False        # far below the backstop
    assert v["verdict"] == "CONTRADICTED"       # and still not VACUOUS


# ------------------------------- fail closed: every population must be consulted

def test_a_wrong_event_sequence_is_not_agreement():
    """Found externally on the published branch.

    The verdict read row count and key order and never read `sequence_equal`, so
    a trace with the right number of rows carrying the right keys in the right
    order but the WRONG sequence numbers returned CONFIRMED. A comparison that
    says nothing about a population is not evidence that the population agrees.
    """
    a = b = _doc()
    ev = {"row_count_equal": True, "key_order_equal": True, "sequence_equal": False}
    v = reproduction_verdict(compare_results(a, b, TOL), structural_checks(a, b),
                             ev, minimum_fraction=0.0, backstop=1)
    assert v["verdict"] == "CONTRADICTED"
    assert "event_sequence_differs" in v["contradiction_reasons"]


def test_a_leaf_the_producer_never_had_is_not_agreement():
    """`only_in_reproduced` was never read either."""
    a = _doc()
    b = _doc(invented_by_the_reproduction=1.0)
    v = _verdict(a, b, minimum_fraction=0.0, backstop=1)
    assert v["verdict"] == "CONTRADICTED"
    assert "leaves_only_in_reproduced" in v["contradiction_reasons"]


def test_producer_only_leaves_must_be_declared_not_merely_tolerated():
    """43 uncomparable leaves were accepted wholesale.

    A reproduction that silently stopped emitting an entire section would then
    have "agreed" with the producer about the part it still emitted. The caller
    must now declare which producer-only leaves are expected; anything else
    contradicts.
    """
    a = _doc(**{"checks": {"a_runner_check": True}, "silently_dropped": 3.0})
    b = _doc()
    undeclared = _verdict(a, b, minimum_fraction=0.0, backstop=1)
    assert undeclared["verdict"] == "CONTRADICTED"
    assert "undeclared_leaves_only_in_produced" in undeclared["contradiction_reasons"]

    declared = reproduction_verdict(
        compare_results(a, b, TOL), structural_checks(a, b),
        {"row_count_equal": True, "key_order_equal": True, "sequence_equal": True},
        minimum_fraction=0.0, backstop=1,
        allowed_only_in_produced=[".checks.a_runner_check", ".silently_dropped"])
    assert declared["verdict"] == "CONFIRMED"


def test_every_mismatch_population_is_consulted_by_the_verdict():
    """The guard against this defect recurring.

    Adding a population to compare_results without deciding what it means must
    raise, not default to agreement. This asserts the guard is wired, by naming
    the same set the verdict checks itself against.
    """
    from aionq.semantic_reproduction import _MISMATCH_POPULATIONS
    assert "only_in_reproduced" in _MISMATCH_POPULATIONS
    assert "identity_mismatches" in _MISMATCH_POPULATIONS
    keys = set(compare_results(_doc(), _doc(), TOL))
    assert _MISMATCH_POPULATIONS <= keys | {"only_in_produced", "only_in_reproduced"}


def test_the_recorded_reproduction_reports_total_identity_leaves_not_only_mismatches():
    """497 identity leaves exist; 493 of them differ. Both are reported."""
    r = _artifact()
    assert r["comparison"]["identity_leaves"] == 497
    assert r["comparison"]["identity_mismatches"] == 493


def test_the_envelope_binds_to_a_commit_that_contains_its_artifacts():
    """The P1 an external audit found on the published branch.

    Every raw artifact an envelope declares must exist at the commit the
    envelope names, with those exact bytes. The first W1 envelope named a commit
    at which all three resolved to None, and `verify` still returned ok, because
    a missing blob is read as "cannot check" rather than as a failure.
    """
    import json as _json
    from pathlib import Path
    from aionq.evidence import _committed_file_digest, load_envelope
    root = repo_root()
    path = root / "artifacts" / "r6k_w1_semantic_reproduction" / "reproduction.envelope.json"
    if not path.is_file():
        pytest.skip("run the `envelope` phase first")
    env = load_envelope(path)
    assert len(env.commit_sha) >= 7
    for rel, declared in env.raw_artifacts.items():
        at_commit = _committed_file_digest(rel, env.commit_sha, root)
        assert at_commit is not None, f"{rel} does not exist at {env.commit_sha[:8]}"
        assert at_commit == declared, rel


def test_the_envelope_declares_a_paired_sample_of_one():
    """3555 leaves are measurements of ONE paired comparison, not observations.

    The published version declared 4, counting the two manifests that fixed the
    rules as if they were samples. Manifests are provenance.
    """
    from aionq.evidence import load_envelope
    path = repo_root() / "artifacts" / "r6k_w1_semantic_reproduction" / "reproduction.envelope.json"
    if not path.is_file():
        pytest.skip("run the `envelope` phase first")
    env = load_envelope(path)
    assert env.observed_result["sample_size"] == 1
    assert "paired" in env.observed_result["design"]


def test_part_b_states_one_interval_not_two():
    """B1 and B2 were joined by 'equivalently' and are not equivalent.

    rho in (0.15, 0.30)  ->  J_psi in (0.067175, 0.203571)
    J_psi in [0.05, 0.20] ->  rho  in [0.126548, 0.296392]

    A crossing at rho = 0.13 satisfies one and fails the other, so 'the
    prediction held' could be decided after seeing the result. The amendment
    supersedes B1 and keeps J_psi as the sole primary statement.
    """
    import json as _json
    import math as _math
    path = (repo_root() / "manifests"
            / "qsigma_r6k_w1_partb_interval_correction.json")
    doc = _json.loads(path.read_text(encoding="utf-8"))
    assert doc["corrected_prediction"]["B1"].startswith("SUPERSEDED")
    lo, hi = 0.126548, 0.296392
    assert _math.isclose((1 - _math.exp(-2 * lo)) ** 2, 0.05, abs_tol=1e-6)
    assert _math.isclose((1 - _math.exp(-2 * hi)) ** 2, 0.20, abs_tol=1e-6)
    # the intervals genuinely differ, which is the whole finding
    assert lo < 0.15 and hi < 0.30
