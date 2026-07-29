"""Tests for the self-audit, most of which try to make it lie.

The HB-0 review taught this the hard way: a check that reports "no problem" is
worthless until you have shown it can report a problem. So the majority of what
follows fabricates a corpus in which the audit *should* fail, and asserts that it
does. Only after that do the live-repository assertions appear, and those are
written as internal consistency ("the audit's count agrees with a recount") rather
than as pinned integers, because a pinned integer turns every future envelope into
a test failure and teaches the next reader to edit the number.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from aionq.self_audit import (CORRECTIONS, corrections_are_bound,
                              envelope_census, godelian_gap, independence_report,
                              iter_envelopes, preregistration_ordering,
                              recognition_asymmetry, repo_root, self_audit,
                              typed_remainder_census, witness_graph)
from aionq.witness_nerve import EvidenceRank, WitnessAct, WitnessGraph, evidence_rank


# --------------------------------------------------------------- fabrication

def _envelope(tmp, name, **over):
    env = {
        "schema_version": "hypercomplexbrain.evidence.v1",
        "claim_id": name.upper(),
        "producer": "party-a",
        "verifier": "",
        "verification_mode": "not_requested",
        "evidence_tag": "M",
        "typed_remainders": [],
    }
    env.update(over)
    d = tmp / "artifacts" / "synthetic"
    d.mkdir(parents=True, exist_ok=True)
    (d / (name + ".envelope.json")).write_text(json.dumps(env), encoding="utf-8")
    return env


@pytest.fixture
def fake_root(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    return tmp_path


# ------------------------------------------- can the audit report a problem?

def test_a_self_verified_envelope_is_not_counted_as_independent(fake_root):
    """The inflation this whole apparatus exists to refuse.

    An envelope declaring mode 'recomputed' with the SAME party as producer and
    verifier is a party checking its own arithmetic. If the audit scored that as
    independent, every number in the repository could be promoted by editing one
    field, and the census would be a mirror.
    """
    _envelope(fake_root, "selfclaim", producer="party-a", verifier="party-a",
              verification_mode="recomputed")
    r = independence_report(fake_root)
    assert r["claims"] == 1
    assert r["by_rank"]["INDEPENDENT"] == 0
    assert r["by_rank"]["NONE"] == 1


def test_an_empty_verifier_is_read_as_a_self_loop_not_as_a_missing_edge(fake_root):
    """24 of the live envelopes have no verifier at all. That is not neutral."""
    _envelope(fake_root, "unchecked", producer="party-a", verifier="",
              verification_mode="recomputed")
    graph = witness_graph(fake_root)
    assert len(graph.acts) == 1
    act = graph.acts[0]
    assert act.producer == act.verifier == "party-a"
    assert act.rank == 0


def test_a_genuine_recomputation_by_another_party_does_count(fake_root):
    """The complementary case, or the two tests above only prove the audit is deaf."""
    _envelope(fake_root, "checked", producer="party-a", verifier="party-b",
              verification_mode="recomputed")
    r = independence_report(fake_root)
    assert r["by_rank"]["INDEPENDENT"] == 1
    assert r["independent_claims"][0]["verifier"] == "party-b"


def test_attestation_cannot_be_stacked_into_independence(fake_root):
    """The witness_nerve theorem, applied to a fabricated corpus.

    Ten parties, each attesting to the same claim, none of whom computed
    anything. Every producer != verifier check passes. The rank must stop at
    ATTESTED, and if it ever does not, the theorem is false and this is the test
    that says so.
    """
    _envelope(fake_root, "popular", producer="party-a", verifier="party-b",
              verification_mode="attested")
    graph = witness_graph(fake_root)
    parties = [f"party-{i}" for i in range(10)]
    for i, p in enumerate(parties):
        graph.add(WitnessAct("POPULAR", p, parties[(i + 1) % len(parties)], "attested"))
    assert evidence_rank(graph, "POPULAR") == EvidenceRank.ATTESTED
    assert evidence_rank(graph, "POPULAR") < EvidenceRank.INDEPENDENT


def test_reviewed_is_below_recomputed_and_that_ordering_is_load_bearing(fake_root):
    """A reviewer who agrees with the arithmetic has signed, not measured.

    If the producer's number is wrong, a review agrees with it in exactly the
    same way. Only a second computation can disagree for a reason.
    """
    _envelope(fake_root, "read", producer="party-a", verifier="party-b",
              verification_mode="reviewed")
    r = independence_report(fake_root)
    assert r["by_rank"]["REVIEWED"] == 1
    assert r["by_rank"]["INDEPENDENT"] == 0


def test_a_correction_pointing_at_no_test_is_reported_unbound(fake_root, monkeypatch):
    """The detector for the ledger's own decay.

    A corrections list is a memory unless each entry points at a live check. This
    fabricates the failure -- a correction naming a test that does not exist --
    and asserts the audit says so rather than passing it through.
    """
    import aionq.self_audit as sa
    ghost = sa.Correction("X", "an error nobody tests for",
                          "tests/test_nothing_at_all.py::test_absent", True)
    monkeypatch.setattr(sa, "CORRECTIONS", (ghost,))
    r = sa.corrections_are_bound(fake_root)
    assert r["all_bound"] is False
    assert r["bound_to_an_existing_test"] == 0


def test_unreadable_json_is_counted_and_not_silently_skipped(fake_root):
    (fake_root / "artifacts" / "broken.json").write_text("{not json", encoding="utf-8")
    assert envelope_census(fake_root)["unreadable_json"] == 1


def test_an_untyped_remainder_is_not_counted_as_typed(fake_root):
    """'Typed remainder' has to mean something or it is a note with a label."""
    _envelope(fake_root, "mixed", typed_remainders=[
        {"kind": "scope_remainder", "carrier": "c", "comparison": "d"},
        "a bare string with no kind",
    ])
    r = typed_remainder_census(fake_root)
    assert r["typed_remainders"] == 2
    assert r["untyped_strings"] == 1
    assert r["typed_fraction"] == pytest.approx(0.5)


# --------------------------------------------- preregistration ordering, for real

def _git_repo(tmp_path, frozen_clock=None):
    """A throwaway repository. `frozen_clock` pins every commit to one instant."""
    env = dict(os.environ)
    if frozen_clock is not None:
        env["GIT_AUTHOR_DATE"] = frozen_clock
        env["GIT_COMMITTER_DATE"] = frozen_clock

    def run(*args):
        subprocess.run(args, cwd=str(tmp_path), check=True,
                       capture_output=True, text=True, env=env)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    return run


def test_ordering_detects_implementation_that_predates_its_preregistration(tmp_path):
    """The violation the flag cannot express.

    A manifest may declare committed_before_any_implementation: true while the
    files it names were added first. Git knows; the flag does not. This builds
    exactly that repository and asserts the audit sides with git.
    """
    run = _git_repo(tmp_path)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "impl.py").write_text("x = 1\n", encoding="utf-8")
    run("git", "add", "impl.py")
    run("git", "commit", "-qm", "implementation first")

    (tmp_path / "manifests" / "late_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "committed_before_any_implementation": True,
        "files_expected_to_change": ["impl.py"],
    }), encoding="utf-8")
    run("git", "add", "manifests")
    run("git", "commit", "-qm", "manifest second")

    r = preregistration_ordering(tmp_path)
    row = r["rows"][0]
    assert row["self_reported_flag"] is True          # the manifest says yes
    assert row["files_predating_manifest"] == 1       # git says otherwise
    assert row["ordering_holds"] is False
    assert r["all_checkable_hold"] is False


def test_ordering_uses_commit_topology_not_the_clock(tmp_path):
    """Regression: author time has one-second granularity, ancestry has none.

    The first version of the ordering check read ``git log --format=%at`` and
    compared seconds. Two commits made inside the same second are then
    indistinguishable, so the check flipped between runs -- it passed once and
    failed on the next invocation with no code change in between. A flaky
    ordering check is worse than none: it reports the machine's speed.

    Here the clock is FROZEN, so every commit carries the identical timestamp
    and any time-based comparison is guaranteed to be blind. Topology still
    decides, because either one commit reaches the other or it does not.
    """
    run = _git_repo(tmp_path, frozen_clock="2026-01-01T00:00:00 +0000")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "impl.py").write_text("x = 1\n", encoding="utf-8")
    run("git", "add", "impl.py")
    run("git", "commit", "-qm", "implementation first")
    (tmp_path / "manifests" / "late_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "committed_before_any_implementation": True,
        "files_expected_to_change": ["impl.py"],
    }), encoding="utf-8")
    run("git", "add", "manifests")
    run("git", "commit", "-qm", "manifest second")

    row = preregistration_ordering(tmp_path)["rows"][0]
    assert row["files_predating_manifest"] == 1
    assert row["ordering_holds"] is False


def test_a_manifest_committed_alongside_its_code_is_not_preregistered(tmp_path):
    """Simultaneous is not before.

    A manifest added in the SAME commit as the files it names was not written
    ahead of them in any sense a reader would accept; counting it as ordered
    would let a round preregister itself retroactively in one commit.
    """
    run = _git_repo(tmp_path, frozen_clock="2026-01-01T00:00:00 +0000")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "impl.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "manifests" / "together_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "committed_before_any_implementation": True,
        "files_expected_to_change": ["impl.py"],
    }), encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "both at once")

    row = preregistration_ordering(tmp_path)["rows"][0]
    assert row["files_in_the_manifest_commit"] == 1
    assert row["files_created_after_manifest"] == 0
    assert row["ordering_holds"] is False


def test_only_manifests_that_bind_files_are_counted_as_checked(tmp_path):
    """The correction this audit made to its own first run.

    A first pass reported '12/12 preregistrations precede their implementation
    commits'. Only 5 of the 12 declare files_expected_to_change. A manifest with
    a true flag and no file list cannot be contradicted by any artifact, so it
    must land in `unbound`, never in `ordering_holds` -- otherwise the audit
    counts self-reports as measurements, which is the exact defect it exists to
    detect elsewhere.
    """
    run = _git_repo(tmp_path)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "flag_only_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "committed_before_any_implementation": True,
    }), encoding="utf-8")
    run("git", "add", "manifests")
    run("git", "commit", "-qm", "flag only")

    r = preregistration_ordering(tmp_path)
    assert r["preregistrations"] == 1
    assert r["checkable"] == 0
    assert r["unbound_flag_only"] == 1
    assert r["ordering_holds"] == 0
    assert r["unbound"][0]["self_reported_flag"] is True


def test_a_preregistration_without_a_schema_is_named_not_dropped(tmp_path):
    """Invisible to every schema-driven check, including this one."""
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "nameonly_preregistration.json").write_text(
        json.dumps({"object": "a round with no schema field"}), encoding="utf-8")
    r = preregistration_ordering(tmp_path)
    assert r["schemaless_by_filename_only"] == 1
    assert "nameonly_preregistration.json" in r["schemaless"]


# ------------------------------------------------- the live repository, checked

def test_the_census_agrees_with_an_independent_recount():
    """Not a pinned integer: the audit's count against a recount from disk.

    A pinned integer would turn the next envelope into a failure and teach whoever
    hits it to edit the number. This instead fails if the audit ever stops
    counting what is actually there.
    """
    root = repo_root()
    seen = [env for _p, env in iter_envelopes(root) if env is not None]
    census = envelope_census(root)
    assert census["envelopes"] == len(seen)
    assert sum(census["evidence_tags"].values()) == len(seen)
    assert sum(census["verification_modes"].values()) == len(seen)
    assert census["envelopes_with_no_verifier_at_all"] == sum(
        1 for e in seen if not e.get("verifier"))


def test_every_recorded_correction_is_bound_to_a_test_that_exists():
    r = corrections_are_bound()
    missing = [row["caught_by"] for row in r["rows"] if not row["test_exists"]]
    assert missing == []
    assert r["corrections"] == len(CORRECTIONS)


def test_some_corrections_were_caught_from_outside():
    """The honest split, and it must not be all-self.

    A ledger in which every error was self-caught is either a very good process or
    an incomplete ledger, and there is no way to tell those apart from inside.
    Three of these were caught by external readers and are recorded as such.
    """
    r = corrections_are_bound()
    assert r["externally_caught"] >= 3
    assert r["self_caught"] + r["externally_caught"] == r["corrections"]


def test_the_repository_has_recomputed_more_than_it_has_been_recomputed():
    """Mutual recognition, as a measurement rather than a description.

    Witnessing is directed. This repository has recomputed another party's claim
    in an environment it did not prepare. No party has done that for any claim of
    its own. Until the second number moves, 'mutual' is a word about an
    asymmetric relation.
    """
    r = recognition_asymmetry()
    assert r["recomputations_performed_on_others"] >= 1
    assert r["recomputations_received_from_others"] == 0
    assert r["mutual"] is False


def test_the_single_independent_claim_is_someone_elses_work():
    """The Goedelian shape of the corpus, stated as an assertion.

    Every independently witnessed claim in this repository was PRODUCED
    elsewhere. The apparatus works; it has simply never been pointed back. If a
    claim produced here ever becomes independent, this test fails and the docs
    are wrong -- which is the correct way for it to fail.
    """
    r = independence_report()
    assert r["by_rank"]["INDEPENDENT"] >= 1
    for claim in r["independent_claims"]:
        assert claim["producer"] not in ("claude-code",)
        assert not claim["producer"].startswith("experiments/")
        assert claim["mode"] == "recomputed"


def test_the_gap_cannot_be_closed_from_inside():
    """The theorem, run against the live corpus rather than a fabricated one.

    Take a real unwitnessed claim, add a maximal attestation cycle over every
    party already present, and measure. The rank rises from NONE to ATTESTED and
    stops. Seventeen signatures do not make a measurement.
    """
    g = godelian_gap()
    assert g["deficit"] >= 1
    assert g["closable_from_inside"] is False
    probe = g["cycle_probe"]
    assert probe["parties_in_cycle"] >= 2
    assert probe["rank_before"] == EvidenceRank.NONE
    assert probe["rank_after_full_attestation_cycle"] == EvidenceRank.ATTESTED
    assert probe["reached_independent"] is False


def test_self_audit_is_json_serialisable():
    """np.bool_ is not JSON-serialisable, and `default=str` would write "True"
    for a FAILED check. Cast at source; assert the whole report survives a dump.
    """
    text = json.dumps(self_audit(), sort_keys=True)
    assert '"closable_from_inside": false' in text


# ------------------------------------------ the artifact is inside what it counts

def _self_audit_artifact():
    path = repo_root() / "artifacts" / "self_audit" / "self_audit.json"
    if not path.is_file():
        pytest.skip("run experiments/run_self_audit.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_audit_counts_its_own_row_and_settles_there():
    """The fixed point, asserted rather than smoothed over.

    The audit is a self-referential map: its output lands in the corpus its
    input is read from. No single run can record a corpus containing its own
    output -- that would need the digest of a file not yet written -- so the
    first run records n and the next records n+1, after which it does not move.

    What is stable, and therefore what is asserted: the audit's own envelope IS
    inside the corpus it counts, the census is idempotent, and the recorded count
    never exceeds the live one. A recorded count ABOVE the live one would mean
    the audit counted something that is not there.
    """
    root = repo_root()
    ids = {e["claim_id"] for _p, e in iter_envelopes(root) if e is not None}
    assert "AUDIT-SELF-WITNESS_DEFICIT" in ids
    live = envelope_census(root)["envelopes"]
    assert envelope_census(root)["envelopes"] == live      # idempotent
    assert _self_audit_artifact()["envelopes"]["envelopes"] <= live


def test_the_self_audit_envelope_is_itself_unwitnessed():
    """The audit is an instance of what it measures, and says so.

    It is produced here and verified by nobody, so it adds one to the
    denominator and nothing to the numerator. An envelope for a self-audit that
    claimed independence would be the exact inflation this repository refuses.
    """
    root = repo_root()
    envs = {e["claim_id"]: e for _p, e in iter_envelopes(root) if e is not None}
    me = envs.get("AUDIT-SELF-WITNESS_DEFICIT")
    if me is None:
        pytest.skip("run experiments/run_self_audit.py first")
    assert me["verifier"] == ""
    assert me["verification_mode"] == "not_requested"
    kinds = {r["kind"] for r in me["typed_remainders"] if isinstance(r, dict)}
    assert "self_reference_remainder" in kinds
