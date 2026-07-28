"""QSigma-R5: adversarial tests for the asynchronous witness weave."""

from __future__ import annotations

import hashlib
import json
import random
import threading
from pathlib import Path

import pytest

from aionq.evidence import EvidenceEnvelope, file_digest, load_envelope, save_envelope
from aionq.witness import VerificationMode, WitnessError
from aionq.witness_batch import (BatchEvent, append_event, batch_status,
                                 dispatch_batch, fold_journal, ingest_response,
                                 load_journal, reconcile_handles,
                                 render_witness_markdown)
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


def _legacy_handles(root: Path, handles) -> Path:
    path = root / "legacy-dispatch.json"
    path.write_text(json.dumps({
        "schema": "hypercomplexbrain.review_batch.v1",
        "handles": handles,
    }, indent=2))
    return path


def _transport(payload):
    def call(endpoint, body, headers):
        payload.setdefault("calls", []).append(json.loads(body))
        return payload["response"]
    return call


def _handle_ref(url: str) -> str:
    return "sha256:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def _write_response(
    path: Path,
    *,
    task_id: str,
    claim_id: str,
    conversation_url: str,
    response: dict,
    attempt: int = 1,
    batch_id: str = "test-batch",
) -> None:
    path.write_text(json.dumps({
        "schema": "hypercomplexbrain.witness_response.v1",
        "batch_id": batch_id,
        "task_id": task_id,
        "claim_id": claim_id,
        "attempt": attempt,
        "conversation_ref": _handle_ref(conversation_url),
        "response": response,
    }))


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
    assert state["conversation_ref"] == _handle_ref(
        "https://chatgpt.com/c/pending-one"
    )
    assert "conversation_url" not in state
    assert not state["independent"]
    assert "pending-one" not in (tmp_path / "events.jsonl").read_text()


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


def test_legacy_handle_reconciliation_is_idempotent_and_prevents_redispatch(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-LEGACY")
    manifest = _manifest(tmp_path, [
        _task("legacy", "CLAIM-LEGACY", envelope, mode="reviewed")
    ])
    source = _legacy_handles(tmp_path, [{
        "claim_id": "CLAIM-LEGACY",
        "conversation_url": "https://chatgpt.com/c/legacy-handle",
        "status": "pending",
    }])

    first = reconcile_handles(manifest, source, root=tmp_path)
    assert first.imported == ["legacy"]
    assert not first.idempotent
    line_count = len((tmp_path / "events.jsonl").read_text().splitlines())

    second = reconcile_handles(manifest, source, root=tmp_path)
    assert second.idempotent == ["legacy"]
    assert not second.imported
    assert len((tmp_path / "events.jsonl").read_text().splitlines()) == line_count

    state = batch_status(manifest, root=tmp_path)["tasks"][0]
    assert state["attempt"] == 1
    assert state["state"] == VerificationMode.PENDING
    assert state["conversation_ref"] == _handle_ref(
        "https://chatgpt.com/c/legacy-handle"
    )
    assert "legacy-handle" not in (tmp_path / "events.jsonl").read_text()

    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/must-not-run"}}
    report = dispatch_batch(
        manifest,
        root=tmp_path,
        transport=_transport(exchange),
    )
    assert not exchange["calls"]
    assert "pending handle already exists" in report.skipped["legacy"]


def test_reconciliation_rejects_bad_or_conflicting_handles_before_append(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-CONFLICT")
    manifest = _manifest(tmp_path, [
        _task("conflict", "CLAIM-CONFLICT", envelope, mode="reviewed")
    ])
    bad = _legacy_handles(tmp_path, [{
        "claim_id": "CLAIM-CONFLICT",
        "conversation_url": "http://example.com/not-a-chat",
        "status": "pending",
    }])
    with pytest.raises(ValueError, match="conversation_url"):
        reconcile_handles(manifest, bad, root=tmp_path)
    assert not (tmp_path / "events.jsonl").exists()

    good = _legacy_handles(tmp_path, [{
        "claim_id": "CLAIM-CONFLICT",
        "conversation_url": "https://chatgpt.com/c/first",
        "status": "pending",
    }])
    reconcile_handles(manifest, good, root=tmp_path)
    conflicting = _legacy_handles(tmp_path, [{
        "claim_id": "CLAIM-CONFLICT",
        "conversation_url": "https://chatgpt.com/c/second",
        "status": "pending",
    }])
    with pytest.raises(WitnessError, match="conflicting handle"):
        reconcile_handles(manifest, conflicting, root=tmp_path)


def test_dry_run_and_allowlist_make_no_writes_or_network_calls(tmp_path):
    envelope_a, _ = _make_envelope(tmp_path, "CLAIM-A")
    envelope_b, _ = _make_envelope(tmp_path, "CLAIM-B")
    manifest = _manifest(tmp_path, [
        _task("allowed", "CLAIM-A", envelope_a),
        _task("not-authorized", "CLAIM-B", envelope_b),
    ])
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/must-not-run"}}

    report = dispatch_batch(
        manifest,
        root=tmp_path,
        allowed_task_ids=["allowed"],
        dry_run=True,
        transport=_transport(exchange),
    )
    assert report.dry_run
    assert report.would_submit == ["allowed"]
    assert not report.submitted
    assert report.skipped["not-authorized"] == (
        "not authorized by dispatch allowlist"
    )
    assert not exchange["calls"]
    assert not (tmp_path / "events.jsonl").exists()
    assert not (tmp_path / "events.jsonl.lock").exists()


def test_envelope_terminal_state_is_a_dispatch_safety_floor(tmp_path):
    envelope_path, _ = _make_envelope(tmp_path, "CLAIM-OLD-DECLINE")
    envelope = load_envelope(envelope_path)
    envelope.verification_mode = VerificationMode.DECLINED
    save_envelope(envelope, envelope_path)
    manifest = _manifest(tmp_path, [
        _task("old-decline", "CLAIM-OLD-DECLINE", envelope_path, mode="reviewed")
    ])
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/must-not-run"}}

    report = dispatch_batch(
        manifest,
        root=tmp_path,
        transport=_transport(exchange),
    )
    assert not exchange["calls"]
    assert "explicit retry" in report.skipped["old-decline"]


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
    assert "reconcile it before any retry" in report.skipped["uncertain"]


def test_transport_unapplied_is_zero_rank_and_cannot_be_retried(
    tmp_path,
    monkeypatch,
):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-UNAPPLIED")
    manifest = _manifest(tmp_path, [
        _task("unapplied", "CLAIM-UNAPPLIED", envelope)
    ])
    exchange = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/unapplied",
    }}

    def fail_save(*_args, **_kwargs):
        raise OSError("simulated envelope write failure")

    monkeypatch.setattr("aionq.witness_batch.save_envelope", fail_save)
    first = dispatch_batch(
        manifest,
        root=tmp_path,
        transport=_transport(exchange),
    )
    assert len(exchange["calls"]) == 1
    assert "simulated envelope write failure" in first.failed["unapplied"]

    state = batch_status(manifest, root=tmp_path)["tasks"][0]
    assert state["state"] == "transport_unapplied"
    assert state["conversation_ref"] == _handle_ref(
        "https://chatgpt.com/c/unapplied"
    )
    markdown = render_witness_markdown(manifest, root=tmp_path)
    assert "transport_unapplied" in markdown
    assert "rank=NONE" in markdown

    second = dispatch_batch(
        manifest,
        root=tmp_path,
        retry_task_ids=["unapplied"],
        transport=_transport(exchange),
    )
    assert len(exchange["calls"]) == 1
    assert "uncertain transport boundary" in second.skipped["unapplied"]


def test_concurrent_dispatch_observes_reservation_before_transport_returns(
    tmp_path,
):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-CONCURRENT")
    manifest = _manifest(tmp_path, [
        _task("concurrent", "CLAIM-CONCURRENT", envelope)
    ])
    entered = threading.Event()
    release = threading.Event()
    calls: list[dict] = []

    def transport(_endpoint, body, _headers):
        calls.append(json.loads(body))
        entered.set()
        assert release.wait(5)
        return {"conversation_url": "https://chatgpt.com/c/concurrent"}

    first_result: list = []

    def first_dispatch():
        first_result.append(dispatch_batch(
            manifest,
            root=tmp_path,
            transport=transport,
        ))

    worker = threading.Thread(target=first_dispatch)
    worker.start()
    assert entered.wait(5)
    second = dispatch_batch(manifest, root=tmp_path, transport=transport)
    release.set()
    worker.join(5)

    assert not worker.is_alive()
    assert len(calls) == 1
    assert first_result[0].pending == ["concurrent"]
    assert "uncertain transport boundary" in second.skipped["concurrent"]


@pytest.mark.parametrize(
    ("task_id", "claim_id", "initial_state", "initial_ordinal"),
    [
        ("started", "CLAIM-STARTED", "dispatch_started", 10),
        (
            "unapplied",
            "CLAIM-UNAPPLIED-PENDING",
            "transport_unapplied",
            20,
        ),
    ],
)
def test_reconcile_recovers_pending_transport_boundaries(
    tmp_path,
    task_id,
    claim_id,
    initial_state,
    initial_ordinal,
):
    envelope, _ = _make_envelope(tmp_path, claim_id)
    manifest = _manifest(
        tmp_path,
        [_task(task_id, claim_id, envelope, mode="reviewed")],
        batch_id=f"batch-{task_id}",
    )
    url = f"https://chatgpt.com/c/{task_id}-recovered"
    details = (
        {}
        if initial_state == "dispatch_started"
        else {
            "declared_mode": VerificationMode.PENDING,
            "conversation_ref": _handle_ref(url),
        }
    )
    append_event(tmp_path / "events.jsonl", BatchEvent(
        f"batch-{task_id}",
        task_id,
        claim_id,
        1,
        initial_ordinal,
        initial_state,
        initial_state,
        details,
    ))
    source = _legacy_handles(tmp_path, [{
        "claim_id": claim_id,
        "conversation_url": url,
        "status": "pending",
    }])

    result = reconcile_handles(manifest, source, root=tmp_path)
    assert result.imported == [task_id]
    state = batch_status(manifest, root=tmp_path)["tasks"][0]
    assert state["state"] == VerificationMode.PENDING
    assert state["conversation_ref"] == _handle_ref(url)


def test_response_wrapper_binds_task_claim_attempt_and_handle(tmp_path):
    envelope, _ = _make_envelope(tmp_path, "CLAIM-BOUND")
    manifest = _manifest(tmp_path, [
        _task("bound", "CLAIM-BOUND", envelope, mode="reviewed")
    ])
    pending_url = "https://chatgpt.com/c/bound"
    dispatch_batch(
        manifest,
        root=tmp_path,
        transport=_transport({
            "calls": [],
            "response": {"conversation_url": pending_url},
        }),
    )

    base = {
        "schema": "hypercomplexbrain.witness_response.v1",
        "batch_id": "test-batch",
        "task_id": "bound",
        "claim_id": "CLAIM-BOUND",
        "attempt": 1,
        "conversation_ref": _handle_ref(pending_url),
        "response": {"mode": "reviewed", "notes": "bounded response"},
    }
    mutations = (
        ("batch_id", "wrong-batch", "batch_id"),
        ("task_id", "wrong-task", "task_id"),
        ("claim_id", "WRONG-CLAIM", "claim_id"),
        ("attempt", 2, "attempt"),
        (
            "conversation_ref",
            _handle_ref("https://chatgpt.com/c/wrong"),
            "handle reference",
        ),
    )
    for index, (field, value, match) in enumerate(mutations):
        wrapper = dict(base)
        wrapper[field] = value
        path = tmp_path / f"bad-wrapper-{index}.json"
        path.write_text(json.dumps(wrapper), encoding="utf-8")
        with pytest.raises((ValueError, WitnessError), match=match):
            ingest_response(manifest, "bound", path, root=tmp_path)


def test_nested_conversation_handles_are_redacted_from_event_details(tmp_path):
    raw_url = "https://chatgpt.com/c/private-nested-handle"
    append_event(tmp_path / "events.jsonl", BatchEvent(
        "test-batch",
        "nested",
        "CLAIM-NESTED",
        1,
        10,
        "diagnostic",
        "diagnostic",
        {
            "notes": f"transport returned {raw_url}",
            "nested": [{"message": raw_url}],
        },
        stateful=False,
    ))
    persisted = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert raw_url not in persisted
    assert _handle_ref(raw_url) in persisted


def test_ingested_matching_recomputation_becomes_independent(tmp_path):
    envelope_path, artifact = _make_envelope(tmp_path, "CLAIM-MATCH")
    manifest = _manifest(tmp_path, [
        _task("match", "CLAIM-MATCH", envelope_path)
    ])
    pending = {"calls": [], "response": {
        "conversation_url": "https://chatgpt.com/c/match"}}
    dispatch_batch(manifest, root=tmp_path, transport=_transport(pending))

    response = tmp_path / "match-response.json"
    _write_response(
        response,
        task_id="match",
        claim_id="CLAIM-MATCH",
        conversation_url="https://chatgpt.com/c/match",
        response={
            "mode": "recomputed",
            "artifacts": {str(artifact): file_digest(artifact)},
            "environment": "independent test sandbox",
            "notes": "ran the command",
        },
    )
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
    _write_response(
        response,
        task_id="differ",
        claim_id="CLAIM-DIFFER",
        conversation_url="https://chatgpt.com/c/differ",
        response={
            "mode": "recomputed",
            "artifacts": {
                str(tmp_path / "CLAIM-DIFFER.artifact.json"):
                "sha256:" + "0" * 64,
            },
        },
    )
    result = ingest_response(manifest, "differ", response, root=tmp_path)
    assert result["state"] == VerificationMode.CONTRADICTED
    assert not result["verification_ok"]
    envelope = load_envelope(envelope_path)
    assert any(r["kind"] == "empirical_residual"
               for r in envelope.typed_remainders)

    repeated = ingest_response(manifest, "differ", response, root=tmp_path)
    assert repeated["idempotent"]
    assert repeated["state"] == VerificationMode.CONTRADICTED

    other = tmp_path / "other-response.json"
    _write_response(
        other,
        task_id="differ",
        claim_id="CLAIM-DIFFER",
        conversation_url="https://chatgpt.com/c/differ",
        response={
            "mode": "reviewed",
            "notes": "different terminal payload",
        },
    )
    with pytest.raises(WitnessError, match="terminal state"):
        ingest_response(manifest, "differ", other, root=tmp_path)


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
    _write_response(
        response,
        task_id="env",
        claim_id="CLAIM-ENV",
        conversation_url="https://chatgpt.com/c/env",
        response={
            "mode": "recomputed",
            "artifacts": {str(artifact): "sha256:" + "1" * 64},
            "environment": "different CPU and BLAS",
            "notes": "timings reproduced in shape, not byte-for-byte",
        },
    )
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
