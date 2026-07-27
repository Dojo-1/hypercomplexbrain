"""QSigma-R5: adversarial tests for the asynchronous witness weave."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from aionq.evidence import EvidenceEnvelope, file_digest, load_envelope, save_envelope
from aionq.witness import VerificationMode, WitnessError
from aionq.witness_batch import (BatchEvent, append_event, batch_status,
                                 dispatch_batch, fold_journal, ingest_response,
                                 load_journal, render_witness_markdown)
from aionq.witness_nerve import (EvidenceRank, WitnessAct, WitnessGraph,
                                 evidence_rank)


def _make_envelope(root: Path, claim_id: str, *, environment_dependent=False):
    artifact = root / f"{claim_id}.artifact.json"
    artifact.write_text(json.dumps({"claim": claim_id, "value": 7}, sort_keys=True))
    envelope_path = root / f"{claim_id}.envelope.json"
    envelope = EvidenceEnvelope(
        claim_id=claim_id,
        evidence_tag="M",
        command="python3 deterministic_example.py",
        observed_result={"sample_size": 1, "value": 7},
        input_hashes=["input:one"],
        seeds=[1],
        raw_artifacts={str(artifact): file_digest(artifact)},
        environment_dependent=[str(artifact)] if environment_dependent else [],
        producer=f"producer:{claim_id}",
        verifier="",
    )
    save_envelope(envelope, envelope_path)
    return envelope_path, artifact


def _manifest(root: Path, tasks, *, batch_id="test-batch") -> Path:
    path = root / "manifest.json"
    path.write_text(json.dumps({
        "schema": "hypercomplexbrain.witness_batch.v1",
        "batch_id": batch_id,
        "repository": "jesusvilela/hypercomplexbrain",
        "ref": "test-ref",
        "journal": str(root / "events.jsonl"),
        "max_workers": 4,
        "tasks": tasks,
    }, indent=2))
    return path


def _task(task_id, claim_id, envelope, mode="recomputed"):
    return {
        "task_id": task_id,
        "claim_id": claim_id,
        "envelope": str(envelope),
        "requested_mode": mode,
        "source": {"provider": "test GitHub connector", "ref": "test-ref"},
        "requires": ["python3"],
        "notes": "test task",
        "verifier": "godelian-1",
    }


def _transport(payload):
    def call(endpoint, body, headers):
        payload.setdefault("calls", []).append(json.loads(body))
        return payload["response"]
    return call


def test_duplicate_tasks_cause_one_request_and_pending_is_not_redispatched(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-DUP")
    task = _task("same", "CLAIM-DUP", envelope)
    manifest = _manifest(tmp_path, [task, dict(task)])
    exchange = {
        "calls": [],
        "response": {"conversation_url": "https://chatgpt.com/c/pending-one"},
    }

    first = dispatch_batch(manifest, root=tmp_path,
                           transport=_transport(exchange), workers=4)
    assert len(exchange["calls"]) == 1
    assert first.pending == ["same"]
    assert first.skipped["same"] == "duplicate manifest entry"

    second = dispatch_batch(manifest, root=tmp_path,
                            transport=_transport(exchange), workers=4)
    assert len(exchange["calls"]) == 1
    assert "pending handle already exists" in second.skipped["same"]

    state = batch_status(manifest, root=tmp_path)["tasks"][0]
    assert state["state"] == VerificationMode.PENDING
    assert state["conversation_url"].endswith("pending-one")
    assert not state["independent"]


def test_pending_transport_has_zero_evidence_rank_and_visualisation_says_so(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-PENDING")
    manifest = _manifest(tmp_path, [
        _task("pending", "CLAIM-PENDING", envelope)
    ])
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/pending-two"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange))

    markdown = render_witness_markdown(manifest, root=tmp_path)
    assert "PENDING" in markdown
    assert "rank=NONE" in markdown
    assert "INDEPENDENT" not in markdown.split("```mermaid", 1)[1].split("```", 1)[0]


def test_journal_fold_is_invariant_to_line_order():
    events = [
        BatchEvent("b", "a", "ca", 1, 10, "dispatch_started", "dispatch_started"),
        BatchEvent("b", "z", "cz", 1, 10, "dispatch_started", "dispatch_started"),
        BatchEvent("b", "a", "ca", 1, 20, "transport_returned", "pending",
                   {"conversation_url": "u:a"}),
        BatchEvent("b", "z", "cz", 1, 20, "transport_returned", "reviewed"),
        BatchEvent("b", "a", "ca", 1, 30, "response_applied", "pending",
                   {"conversation_url": "u:a"}),
    ]
    expected = fold_journal(events)
    random.Random(7).shuffle(events)
    assert fold_journal(events) == expected


def test_conflicting_events_at_one_coordinate_are_refused():
    events = [
        BatchEvent("b", "a", "c", 1, 20, "x", "pending"),
        BatchEvent("b", "a", "c", 1, 20, "y", "reviewed"),
    ]
    with pytest.raises(ValueError, match="conflicting stateful events"):
        fold_journal(events)


def test_token_never_enters_the_persisted_journal(tmp_path, monkeypatch):
    secret = "sk-sentinel-never-persist"
    monkeypatch.setenv("GODELIAN_AGENT_TOKEN", secret)
    envelope, _ = _make_envelope(tmp_path, "CLAIM-SECRET")
    manifest = _manifest(tmp_path, [
        _task("secret", "CLAIM-SECRET", envelope)
    ])
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/no-secret"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange))
    assert secret not in (tmp_path / "events.jsonl").read_text()


def test_declined_task_retries_only_when_explicitly_named(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-RETRY")
    manifest = _manifest(tmp_path, [
        _task("retry", "CLAIM-RETRY", envelope, mode="reviewed")
    ])
    exchange = {"calls": [], "response": {
        "mode": "declined", "notes": "connector unavailable"}}

    dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange))
    assert len(exchange["calls"]) == 1
    skipped = dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange))
    assert len(exchange["calls"]) == 1
    assert "explicit retry" in skipped.skipped["retry"]

    dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange),
                   retry_task_ids=["retry"])
    assert len(exchange["calls"]) == 2
    events = load_journal(tmp_path / "events.jsonl")
    assert max(event.attempt for event in events if event.task_id == "retry") == 2


def test_uncertain_dispatch_boundary_is_not_replayed_automatically(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-UNCERTAIN")
    manifest = _manifest(tmp_path, [
        _task("uncertain", "CLAIM-UNCERTAIN", envelope)
    ])
    append_event(tmp_path / "events.jsonl", BatchEvent(
        "test-batch", "uncertain", "CLAIM-UNCERTAIN", 1, 10,
        "dispatch_started", "dispatch_started"))
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/should-not-run"}}
    report = dispatch_batch(manifest, root=tmp_path, transport=_transport(exchange))
    assert not exchange["calls"]
    assert "reconcile before retrying" in report.skipped["uncertain"]


def test_ingested_matching_recomputation_becomes_independent(tmp_path):
    envelope_path, artifact = _make_envelope(tmp_path, "CLAIM-MATCH")
    manifest = _manifest(tmp_path, [
        _task("match", "CLAIM-MATCH", envelope_path)
    ])
    pending = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/match"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(pending))

    response = tmp_path / "match-response.json"
    response.write_text(json.dumps({
        "mode": "recomputed",
        "artifacts": {str(artifact): file_digest(artifact)},
        "environment": "independent test sandbox",
        "notes": "ran the command",
    }))
    result = ingest_response(manifest, "match", response, root=tmp_path)
    assert result["state"] == VerificationMode.RECOMPUTED
    assert result["independent"]
    assert result["verification_ok"]
    assert load_envelope(envelope_path).independent


def test_ingested_digest_disagreement_is_preserved_as_contradiction(tmp_path):
    envelope_path, _ = _make_envelope(tmp_path, "CLAIM-DIFFER")
    manifest = _manifest(tmp_path, [
        _task("differ", "CLAIM-DIFFER", envelope_path)
    ])
    pending = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/differ"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(pending))

    response = tmp_path / "different-response.json"
    response.write_text(json.dumps({
        "mode": "recomputed",
        "artifacts": {str(tmp_path / "CLAIM-DIFFER.artifact.json"):
                      "sha256:" + "0" * 64},
    }))
    result = ingest_response(manifest, "differ", response, root=tmp_path)
    assert result["state"] == VerificationMode.CONTRADICTED
    assert not result["verification_ok"]
    envelope = load_envelope(envelope_path)
    assert any(r["kind"] == "empirical_residual"
               for r in envelope.typed_remainders)

    with pytest.raises(WitnessError, match="terminal state"):
        ingest_response(manifest, "differ", response, root=tmp_path)


def test_environment_dependent_recompute_degrades_to_reviewed(tmp_path):
    envelope_path, artifact = _make_envelope(
        tmp_path, "CLAIM-ENV", environment_dependent=True)
    manifest = _manifest(tmp_path, [
        _task("env", "CLAIM-ENV", envelope_path)
    ])
    pending = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/env"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(pending))

    response = tmp_path / "env-response.json"
    response.write_text(json.dumps({
        "mode": "recomputed",
        "artifacts": {str(artifact): "sha256:" + "1" * 64},
        "environment": "different CPU and BLAS",
        "notes": "timings reproduced in shape, not byte-for-byte",
    }))
    result = ingest_response(manifest, "env", response, root=tmp_path)
    assert result["state"] == VerificationMode.REVIEWED
    assert not result["independent"]
    assert result["verification_ok"]


@pytest.mark.parametrize("parties", list(range(2, 65)))
def test_acaf_attestation_rings_never_manufacture_independence(parties):
    graph = WitnessGraph()
    names = [f"p{i}" for i in range(parties)]
    for index, producer in enumerate(names):
        graph.add(WitnessAct("CLAIM-RING", producer,
                             names[(index + 1) % parties], "attested"))
        # Duplicate attestations are deliberately allowed; evidence is a max.
        graph.add(WitnessAct("CLAIM-RING", producer,
                             names[(index + 1) % parties], "attested"))
    assert evidence_rank(graph, "CLAIM-RING") == EvidenceRank.ATTESTED
    assert evidence_rank(graph, "CLAIM-RING") < EvidenceRank.INDEPENDENT


def test_one_direct_recomputation_outranks_a_large_attestation_ecology():
    graph = WitnessGraph([
        WitnessAct("CLAIM-RING", "origin", f"attester-{index}", "attested")
        for index in range(100)
    ])
    graph.add(WitnessAct("CLAIM-RING", "origin", "recomputer", "recomputed"))
    assert evidence_rank(graph, "CLAIM-RING") == EvidenceRank.INDEPENDENT
