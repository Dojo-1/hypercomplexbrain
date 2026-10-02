"""Three findings from external review of 140dbe8, each reproduced before fixing.

P1a  a licence guard trusted labels: a two-field JSON {"round": "QSigma-R6N",
     "verdict": "LICENSED"} unlocked held-out depths. R6M's guard had the same
     defect with one field -- found while reproducing the first.
P1b  equivalence completeness checked only that both sides were NON-EMPTY, so
     two matching one-row prefixes returned EQUIVALENT_ON_SEALED_GRID.
P1c  the Part B envelope phase verified and then saved unconditionally, exit 0.

None touched a committed result: R6M and R6N compared 384/384, Part B ran under
the committed R6N licence, and its envelope verifies. Pinned below too.
"""

import hashlib
import json
import sys

import pytest

import aionq.common_receiver_parametric as R6M
import aionq.common_receiver_substituted as R6N
from aionq.part_b_preflight import HELD_OUT_DEPTH_COORDS
from aionq.self_audit import repo_root

ROOT = repo_root()
HELD = tuple((d, v) for _, d, v in HELD_OUT_DEPTH_COORDS)
R6M_PATH = ROOT / "artifacts/r6m_parametric_equivalence/equivalence.json"
R6N_PATH = ROOT / "artifacts/r6n_substituted_fork/licence.json"


def _write(tmp_path, name, obj):
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


# -- P1a: evidence, not labels -----------------------------------------------

def test_forged_label_only_licences_are_refused(tmp_path):
    with pytest.raises(PermissionError, match="not the committed R6N licence"):
        R6N.build_substituted_fork(HELD, licence=_write(
            tmp_path, "r6n.json", {"round": "QSigma-R6N", "verdict": "LICENSED"}))
    with pytest.raises(PermissionError, match="not the committed R6M licence"):
        R6M.build_fork(HELD, licence=_write(
            tmp_path, "r6m.json", {"verdict": "EQUIVALENT_ON_SEALED_GRID"}))


def test_the_committed_licences_are_accepted():
    R6N.verify_r6n_licence(R6N_PATH)
    R6M.verify_r6m_licence(R6M_PATH)


@pytest.mark.parametrize("tamper", [
    lambda r: r["C3"]["control_unrepaired_fork_on_decoy"].update(failed=False),
    lambda r: r["evidence"].update(C2_equivalence_on_sealed_grid=False),
    lambda r: r["substitution"].update(executed_sha256="0" * 64),
    lambda r: r["C2"]["vs_committed_rows"].update(rows=[1, 1]),
])
def test_the_r6n_evidence_checks_fire_on_their_own(tmp_path, monkeypatch, tamper):
    """The digest pin would refuse these first, so it is pointed at the tampered
    file to prove the semantic layer refuses them independently. A check that
    has never fired has not been tested."""
    record = json.loads(R6N_PATH.read_text(encoding="utf-8"))
    tamper(record)
    path = _write(tmp_path, "tampered.json", record)
    monkeypatch.setattr(R6N, "R6N_LICENCE_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(PermissionError, match="evidence does not license"):
        R6N.verify_r6n_licence(path)


def test_the_r6n_licence_binds_the_bytes_being_executed(monkeypatch):
    """If the substitution executed changed, the licence no longer covers it."""
    monkeypatch.setattr(R6N, "SUBSTITUTION_NEW", "rho={_R6N_DEPTH_DECIMAL[rho]!s}")
    with pytest.raises(PermissionError, match="evidence does not license"):
        R6N.verify_r6n_licence(R6N_PATH)


@pytest.mark.parametrize("tamper", [
    lambda r: r["evidence"].update(fork_rows=1),
    lambda r: r["evidence"].update(discrete_agree=False),
    lambda r: r.update(verdict="NOT_EQUIVALENT"),
])
def test_the_r6m_evidence_checks_fire_on_their_own(tmp_path, monkeypatch, tamper):
    record = json.loads(R6M_PATH.read_text(encoding="utf-8"))
    tamper(record)
    path = _write(tmp_path, "tampered.json", record)
    monkeypatch.setattr(R6M, "R6M_LICENCE_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(PermissionError, match="evidence does not support"):
        R6M.verify_r6m_licence(path)


# -- P1b: the full population or nothing -------------------------------------

def _verdict(a, b):
    return R6M.equivalence_verdict(R6M.equivalence_evidence(
        a, b, tolerance=1e-10, references_verified=True, criterion_receipt_clean=True))


def test_incomplete_comparisons_are_invalid_not_equivalent():
    rows = json.loads((ROOT / "artifacts/r6l_common_receiver/common_receiver_reservoir.json")
                      .read_text(encoding="utf-8"))["retrieval_rows"]
    assert len(rows) == R6M.EXPECTED_ROWS == 384
    assert _verdict(rows[:1], rows[:1]) == "INVALID"
    assert _verdict(rows[:383], rows[:383]) == "INVALID"
    assert _verdict(rows, rows[:383]) == "INVALID"
    assert _verdict(rows, rows) == "EQUIVALENT_ON_SEALED_GRID"


# -- P1c: a rejected envelope is not published --------------------------------

def _runner():
    sys.path.insert(0, str(ROOT / "experiments"))
    import run_part_b_crossing
    return run_part_b_crossing


class _Result:
    def __init__(self, ok):
        self.ok = ok

    def __str__(self):
        return "VERIFIED" if self.ok else "FAILED"


def test_a_rejected_envelope_writes_nothing_and_exits_nonzero(tmp_path):
    from aionq.evidence import load_envelope
    env = load_envelope(ROOT / "artifacts/r6k_w1_part_b/crossing.envelope.json")
    target = tmp_path / "out.envelope.json"
    with pytest.raises(SystemExit) as exit_info:
        _runner().publish_envelope(env, target, lambda e: _Result(False))
    assert "nothing written" in str(exit_info.value)
    assert not target.exists()


def test_an_accepted_envelope_is_written(tmp_path):
    from aionq.evidence import load_envelope
    env = load_envelope(ROOT / "artifacts/r6k_w1_part_b/crossing.envelope.json")
    target = tmp_path / "out.envelope.json"
    _runner().publish_envelope(env, target, lambda e: _Result(True))
    assert target.exists()


# -- none of the three touched a committed result -----------------------------

def test_no_committed_result_depended_on_any_of_the_three():
    r6m = json.loads(R6M_PATH.read_text(encoding="utf-8"))
    r6n = json.loads(R6N_PATH.read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / "artifacts/r6k_w1_part_b/execution_receipt.json")
                         .read_text(encoding="utf-8"))
    assert (r6m["evidence"]["committed_rows"], r6m["evidence"]["fork_rows"]) == (384, 384)
    assert r6n["C2"]["vs_committed_rows"]["rows"] == [384, 384]
    assert receipt["licence"]["digest"] == "sha256:" + R6N.R6N_LICENCE_SHA256
    from aionq.evidence import load_envelope, verify
    assert verify(load_envelope(ROOT / "artifacts/r6k_w1_part_b/crossing.envelope.json")).ok
