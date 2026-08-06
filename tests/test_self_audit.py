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
                              iter_envelopes, manifest_pointers_resolve,
                              preregistration_ordering,
                              recognition_asymmetry, repo_root, self_audit,
                              typed_remainder_census, witness_graph)
from aionq.witness_nerve import EvidenceRank, WitnessAct, WitnessGraph, evidence_rank


# --------------------------------------------------------------- fabrication

def _envelope(tmp, name, **over):
    env = {
        "schema_version": "hypercomplexbrain.evidence.v2",
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


# The smallest envelope fields that make an independence claim mean something:
# one computed artifact that is not environment-dependent and IS among the raw
# artifacts bound. Without these the predicate reports agreement over an empty
# set. Fabricated envelopes that are supposed to reach INDEPENDENT carry them;
# the ones testing that the audit refuses inflation deliberately do not.
_COMPARABLE = {
    "computed_artifacts": ["artifacts/synthetic/result.json"],
    "environment_dependent": [".resource_ledger.compiler_proxy.qiskit_version"],
    "raw_artifacts": {"artifacts/synthetic/result.json": "sha256:" + "a" * 64},
}


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
              verification_mode="recomputed", **_COMPARABLE)
    r = independence_report(fake_root)
    assert r["by_rank"]["INDEPENDENT"] == 1
    assert r["independent_claims"][0]["verifier"] == "party-b"


def test_two_parties_with_nothing_comparable_are_not_independent(fake_root):
    """Two names and a mode word are not a second computation of anything.

    The independence predicate used to be satisfied by producer != verifier
    plus a mode string. That certifies a claim about who, never a claim about
    what: an envelope naming two parties and recording no computed artifact
    reports agreement on an empty set, and an empty set always agrees. The
    predicate now also requires a NON-EMPTY set of computed artifacts that
    survives removing the environment-dependent ones and is contained in the
    raw artifacts actually bound -- something both parties could have got
    differently and did not.
    """
    _envelope(fake_root, "hollow", producer="party-a", verifier="party-b",
              verification_mode="recomputed")
    assert independence_report(fake_root)["by_rank"]["INDEPENDENT"] == 0

    # Nor is it enough for the comparable set to be non-empty on paper: if every
    # computed artifact is declared environment-dependent, what remains after
    # the subtraction is empty and the same hollow agreement returns.
    _envelope(fake_root, "allenv", producer="party-a", verifier="party-b",
              verification_mode="recomputed",
              computed_artifacts=["artifacts/synthetic/result.json"],
              environment_dependent=["artifacts/synthetic/result.json"],
              raw_artifacts={"artifacts/synthetic/result.json": "sha256:" + "a" * 64})
    assert independence_report(fake_root)["by_rank"]["INDEPENDENT"] == 0


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


def test_no_independently_witnessed_claim_was_produced_by_this_party():
    """The Goedelian shape of the corpus, stated as an assertion.

    Every independently witnessed claim was produced by someone else, or by a
    party the envelope does not identify. None was produced by this one. The
    apparatus works; it has never been pointed back.

    This test previously asserted the producer string was neither 'claude-code'
    nor an experiments/ path, and R6k-W1 broke it -- correctly. Its reproduction
    envelope names a SCRIPT as producer, which identifies no party at all, so the
    string test could no longer tell "someone else made this" from "we made
    this". `party_kind` is the right instrument: the assertion is that no
    independent claim has a SELF producer, and ambiguous ones are named rather
    than counted as either.
    """
    from aionq.self_audit import party_kind
    r = independence_report()
    assert r["by_rank"]["INDEPENDENT"] >= 1
    for claim in r["independent_claims"]:
        assert party_kind(claim["producer"]) != "self", claim
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


# ------------------------------------------- a script path is not a party

def test_a_script_path_is_not_a_party_identity():
    """The defect R6k-W1 introduced into this module, and then had to repair.

    `_is_self` read any `experiments/` producer as this agent, reasoning that a
    script in this tree ran here. R6k falsified it: the identical script produced
    R6k on one machine and its reproduction on another, so one string names two
    parties.

    The damage was directional, which is why it mattered. The producer read as
    self and the verifier `claude-code-linux` read as other, so a recomputation
    this agent PERFORMED was counted as one it RECEIVED, and `mutual` went True
    on a relation with nothing coming back. An audit that refuses inflated
    evidence inflated its own headline number from an artifact it had just
    written.
    """
    from aionq.self_audit import party_kind
    assert party_kind("experiments/run_equal_resource_reservoir.py") == "ambiguous"
    assert party_kind("some_runner.py") == "ambiguous"
    assert party_kind("") == "ambiguous"
    assert party_kind("claude-code") == "self"
    assert party_kind("claude-code-linux") == "self"      # prefix, not equality
    assert party_kind("gpt/polycosmic-hb0-kernel") == "other"
    assert party_kind("codex-gpt5.6") == "other"


def test_an_ambiguous_party_never_reaches_mutual(fake_root):
    """Counted, never directed. `mutual` must not be reachable through it."""
    _envelope(fake_root, "scriptmade", producer="experiments/run_thing.py",
              verifier="claude-code-linux", verification_mode="recomputed")
    r = recognition_asymmetry(fake_root)
    assert r["recomputations_of_ambiguous_party"] == 1
    assert r["recomputations_performed_on_others"] == 0
    assert r["recomputations_received_from_others"] == 0
    assert r["mutual"] is False


def test_mutual_still_reachable_when_both_parties_are_named(fake_root):
    """The complementary case, or the test above only proves the counter is dead."""
    _envelope(fake_root, "outward", producer="other-agent",
              verifier="claude-code", verification_mode="recomputed")
    _envelope(fake_root, "inward", producer="claude-code",
              verifier="other-agent", verification_mode="recomputed")
    r = recognition_asymmetry(fake_root)
    assert r["mutual"] is True


def test_an_ambiguous_party_cannot_reach_independent(fake_root):
    """Found externally on the published W1 branch.

    The same act was excluded from the recognition counts as ambiguous AND
    counted as raising the independent total 1 -> 2. That is two positions at
    once: refusing to say who performed it, while treating it as proof that
    somebody else checked the claim. Independence needs two IDENTIFIED parties;
    a recomputation with an unidentified one is capped at REVIEWED, because the
    second computation genuinely happened and its author is unestablished.
    """
    _envelope(fake_root, "scriptclaim", producer="experiments/run_thing.py",
              verifier="claude-code-linux", verification_mode="recomputed")
    r = independence_report(fake_root)
    assert r["by_rank"]["INDEPENDENT"] == 0
    assert r["by_rank"]["REVIEWED"] == 1


def test_two_named_parties_still_reach_independent(fake_root):
    """Or the cap above is just a way of never certifying anything."""
    _envelope(fake_root, "namedclaim", producer="gpt/some-branch",
              verifier="claude-code", verification_mode="recomputed",
              **_COMPARABLE)
    assert independence_report(fake_root)["by_rank"]["INDEPENDENT"] == 1


def test_event_ledgers_are_pinned_to_lf():
    """A CRLF checkout breaks every committed-blob digest binding a .jsonl.

    Measured on Windows against the published W1 branch: `*.jsonl` had no rule,
    inherited `text=auto`, and the event ledger's digest failed on that platform
    only. An evidence chain that holds on one operating system is not an
    evidence chain.
    """
    attrs = (repo_root() / ".gitattributes").read_text(encoding="utf-8")
    assert "*.jsonl text eol=lf" in attrs


def test_ordering_distinguishes_pending_from_violated(tmp_path):
    """"Not yet implemented" and "implemented first" are different facts.

    The rule demanded at least one file created after the manifest, so a
    preregistration whose experiment has not run yet scored identically to one
    whose implementation predated it. Found by running the rule against a
    manifest of this round that legitimately has no implementation yet.
    """
    run = _git_repo(tmp_path, frozen_clock="2026-01-01T00:00:00 +0000")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "future_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "files_expected_to_change": ["not_written_yet.py"],
    }), encoding="utf-8")
    run("git", "add", "manifests")
    run("git", "commit", "-qm", "manifest for work not yet done")
    r = preregistration_ordering(tmp_path)
    assert r["rows"][0]["ordering_status"] == "pending"
    assert r["ordering_violated"] == 0
    assert r["all_checkable_hold"] is True, "pending is not a failure"


def test_a_pre_existing_modification_target_is_not_a_violation(tmp_path):
    """`files_expected_to_change` says CHANGE, not create.

    A first draft of the three-state rule scored any pre-existing declared file
    as a violation, which turned R4 and R5 red for naming modules they went on
    to edit. Only a file created in the manifest's own commit violates.
    """
    run = _git_repo(tmp_path, frozen_clock="2026-01-01T00:00:00 +0000")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "existing.py").write_text("x = 1\n", encoding="utf-8")
    run("git", "add", "existing.py")
    run("git", "commit", "-qm", "a module that already exists")
    (tmp_path / "manifests" / "m_preregistration.json").write_text(json.dumps({
        "schema": "hypercomplexbrain.preregistration.v1",
        "files_expected_to_change": ["existing.py", "new.py"],
    }), encoding="utf-8")
    run("git", "add", "manifests")
    run("git", "commit", "-qm", "manifest")
    (tmp_path / "new.py").write_text("y = 2\n", encoding="utf-8")
    run("git", "add", "new.py")
    run("git", "commit", "-qm", "implementation after the manifest")
    row = preregistration_ordering(tmp_path)["rows"][0]
    assert row["files_predating_manifest"] == 1
    assert row["files_created_after_manifest"] == 1
    assert row["ordering_status"] == "holds"


# ---------------------------------------- manifests must point at live things

def test_every_manifest_pointer_resolves_to_a_test_that_exists():
    """The guard that did not exist for sixteen rounds.

    `executable_form` is the field that turns a manifest's statement into
    something a reader can run, and nothing checked that those pointers landed
    anywhere. Seventy of them across fifteen manifests, and the gap surfaced for
    the dullest possible reason: R1R renamed a test whose old name asserted a
    claim R1Q had withdrawn, and the manifest citing it went stale in the same
    commit.

    A manifest is not executed, so a pointer into nothing fails silently and
    forever. That is this repository's recurring defect in its purest form -- a
    guard whose witness cannot reach the case it asserts -- except that here
    there was no guard at all.
    """
    result = manifest_pointers_resolve()

    assert result["pointers"] > 60, "the extractor stopped seeing pointers"
    assert result["unresolved"] == []
    assert result["all_resolve"]


def test_the_pointer_check_can_actually_fail(tmp_path):
    """Because a check that has never reported a problem has not been tested.

    A fabricated corpus with one manifest naming a test that was never written.
    If this passes, the check above is decoration.
    """
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text(
        "def test_that_exists():\n    pass\n", encoding="utf-8")
    (tmp_path / "manifests" / "good.json").write_text(json.dumps(
        {"executable_form": "tests/test_real.py::test_that_exists"}), encoding="utf-8")
    (tmp_path / "manifests" / "bad.json").write_text(json.dumps(
        {"nested": {"executable_form": "tests/test_real.py::test_that_never_was"}}),
        encoding="utf-8")

    result = manifest_pointers_resolve(tmp_path)

    assert result["pointers"] == 2
    assert result["resolved"] == 1
    assert not result["all_resolve"]
    assert result["unresolved"][0]["manifest"] == "bad.json"


def test_supersession_is_recorded_in_both_directions():
    """A reader who arrives at the old manifest first must be told.

    The repository's convention was forward-only: a new manifest lists what it
    `supersedes` and the superseded file says nothing. So R1M could be found on
    its own, stating a withdrawn claim as a finding, with no signal that R1Q had
    retracted it. R1R makes the link bidirectional and this test keeps it that
    way -- every manifest named in someone's `supersedes` must carry a matching
    `supersession.superseded_by` pointing back.
    """
    root = repo_root()
    claimed = {}
    for path in sorted((root / "manifests").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        targets = document.get("supersedes")
        for target in ([targets] if isinstance(targets, str) else targets or []):
            if target.startswith("manifests/"):
                claimed.setdefault(target, []).append(f"manifests/{path.name}")

    assert claimed, "no manifest declares a supersession at all"

    missing = []
    for target, superseders in claimed.items():
        document = json.loads((root / target).read_text(encoding="utf-8"))
        back = (document.get("supersession") or {}).get("superseded_by")
        if back not in superseders:
            missing.append((target, back, superseders))

    assert missing == [], f"one-directional supersession: {missing}"
