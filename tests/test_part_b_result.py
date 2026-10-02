"""QSigma-R6k-W1 Part B: the result, and the state of its gate after execution.

Executed once successfully, as attempt 2, after attempt 1 failed closed before
any metric. Chain: C_exec e96fa24 -> C_raw de60129 -> C_env 140dbe8, each the
direct child of the last. Preregistration anchor C_pre d0650f0, tag on origin.
"""

import json
import subprocess

import pytest

from aionq import part_b_preflight as P
from aionq.part_b_outcome import part_b_outcome
from aionq.self_audit import repo_root

OUT = repo_root() / "artifacts" / "r6k_w1_part_b"
C_EXEC, C_RAW, C_ENV = ("e96fa243d3044aa2ef4c99377443c5524d150842",
                        "de60129f7520672f6391ddd69d9f68bb3082a7b0",
                        "140dbe8f870f47aac1734e89770f741f0a588b4e")


def _git(*args):
    return subprocess.run(["git", *args], cwd=repo_root(), capture_output=True, text=True)


def _crossing():
    return json.loads((OUT / "crossing.json").read_text(encoding="utf-8"))


# -- the gate after execution: one cause, and nothing else broken ------------

def test_the_preflight_now_refuses_for_exactly_one_reason():
    with pytest.raises(P.PartBPreflightError, match="output path already exists before execution"):
        P.validate_repository_preflight(repo_root())


def test_every_other_preregistration_gate_still_holds_after_execution():
    """The strict-xfail on the frozen preflight test must not hide a second fault."""
    root = repo_root()
    assert P.validate_preregistration_tag(root) == "d0650f02c67ac82e846120d931e1b81b6fe8dde2"
    P._load_and_validate_manifest(root)
    P.validate_scientific_dependencies(root)
    rebuilt = P.rebuild_source_input_digests()
    for name in ("coordinate_payload", "perturbed_coordinate_payload"):
        assert rebuilt[name] == P.SOURCE_INPUT_DIGESTS[name]


# -- the result ---------------------------------------------------------------

def test_the_outcome_is_invalid_under_k9():
    outcome = _crossing()["outcome"]
    assert outcome["outcome"] == "INVALID"
    assert outcome["reason"] == "K9: clean and noisy coordinates disagree about the crossing"
    assert outcome["clean_first_pass"] == 0.25
    assert len(outcome["disagreements"]) == 15, "every noisy coordinate disagrees"
    assert set(outcome["disagreements"].values()) == {0.3, 0.4}, "and every one crosses LATER"


def test_the_outcome_rederives_from_the_committed_map_rows_by_the_frozen_function():
    """The recorded verdict is not the runner's word; the frozen function says it."""
    rows = json.loads((OUT / "map_rows.json").read_text(encoding="utf-8"))
    P.validate_map_rows(rows)
    assert part_b_outcome(rows) == _crossing()["outcome"]


def test_the_verdict_does_not_depend_on_the_platform_last_bit():
    sensitivity = _crossing()["platform_sensitivity"]
    assert sensitivity["cells_within_threshold"] == []
    assert sensitivity["smallest_absolute_margin"] > 1e-6


# -- the chain ----------------------------------------------------------------

def test_source_raw_envelope_is_a_direct_chain():
    assert _git("rev-parse", f"{C_RAW}^").stdout.strip() == C_EXEC
    assert _git("rev-parse", f"{C_ENV}^").stdout.strip() == C_RAW
    assert _git("merge-base", "--is-ancestor", "d0650f02c67ac82e846120d931e1b81b6fe8dde2", C_EXEC).returncode == 0


def test_the_envelope_binds_the_raw_bytes_at_c_raw():
    import hashlib
    envelope = json.loads((OUT / "crossing.envelope.json").read_text(encoding="utf-8"))
    assert envelope["artifact_commit_sha"] == C_RAW and envelope["source_commit_sha"] == C_EXEC
    assert sorted(envelope["raw_artifacts"]) == sorted(P.RAW_OUTPUT_PATHS)
    for path, digest in envelope["raw_artifacts"].items():
        blob = subprocess.run(["git", "show", f"{C_RAW}:{path}"], cwd=repo_root(),
                              capture_output=True).stdout
        assert "sha256:" + hashlib.sha256(blob).hexdigest() == digest, path
    # `independent` is a property and is never serialised, so assert its inputs:
    # same development line, no verifier, no verification requested.
    assert envelope["verifier"] == "" and envelope["verification_mode"] == "not_requested"
