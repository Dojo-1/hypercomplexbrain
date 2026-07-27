"""Asynchronous witness weaving over the existing Godelian-1 protocol.

The live witness endpoint is a trigger, not a blocking verifier: it returns a
``conversation_url`` and the actual verdict may arrive later.  This module makes
that latency explicit.  It provides a bounded concurrent dispatcher, an
append-only journal, deterministic state folding, explicit response ingestion,
and a GitHub-renderable witness-nerve view.

It deliberately does *not* pretend to poll a verdict.  No supported verdict API
is exposed by the current protocol.  Agent memory and the returned conversation
URL are useful execution state; the journal and evidence envelopes are the
persistent evidence state.

The principal invariants are:

* ``pending`` is transport state and has evidence rank zero;
* a task attempt is never retried implicitly;
* a duplicate manifest entry never causes a duplicate network request;
* a bearer token, prompt, or request header is never persisted;
* an environment-dependent artifact cannot become independent by digest match;
* contradictory recomputation is retained, never averaged or retried away.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .evidence import EvidenceEnvelope, file_digest, load_envelope, save_envelope
from .witness import (GODELIAN_1_ENDPOINT, TOKEN_ENV_VARS, VerificationMode,
                      WitnessError, WitnessResponse, apply_witness, build_request,
                      parse_response, request_witness)
from .witness_nerve import EvidenceRank, WitnessAct, WitnessGraph, evidence_rank

__all__ = [
    "BatchTask",
    "BatchManifest",
    "BatchEvent",
    "TaskSnapshot",
    "DispatchReport",
    "load_batch_manifest",
    "load_journal",
    "append_event",
    "fold_journal",
    "dispatch_batch",
    "ingest_response",
    "batch_status",
    "render_witness_markdown",
    "write_witness_markdown",
]

SCHEMA = "hypercomplexbrain.witness_batch.v1"
TERMINAL_STATES = frozenset({
    VerificationMode.ATTESTED,
    VerificationMode.REVIEWED,
    VerificationMode.RECOMPUTED,
    VerificationMode.CONTRADICTED,
    VerificationMode.DECLINED,
})
NON_RETRYABLE_STATES = frozenset({VerificationMode.PENDING})
RETRYABLE_STATES = frozenset({
    "failed",
    "dispatch_unknown",
    VerificationMode.DECLINED,
    VerificationMode.CONTRADICTED,
})


@dataclass(frozen=True)
class BatchTask:
    task_id: str
    claim_id: str
    envelope: str
    requested_mode: str
    source: dict[str, Any] = field(default_factory=dict)
    requires: list[str] = field(default_factory=list)
    notes: str = ""
    verifier: str = "godelian-1"

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id cannot be empty")
        if not self.claim_id.strip():
            raise ValueError("claim_id cannot be empty")
        if self.requested_mode not in {
            VerificationMode.RECOMPUTED,
            VerificationMode.REVIEWED,
        }:
            raise ValueError(
                "requested_mode must be 'recomputed' or 'reviewed', got "
                f"{self.requested_mode!r}")


@dataclass(frozen=True)
class BatchManifest:
    batch_id: str
    repository: str
    ref: str
    journal: str
    tasks: tuple[BatchTask, ...]
    max_workers: int = 2
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema {self.schema!r} != {SCHEMA!r}")
        if not self.batch_id.strip():
            raise ValueError("batch_id cannot be empty")
        if not 1 <= self.max_workers <= 8:
            raise ValueError("max_workers must lie in [1, 8]")


@dataclass(frozen=True)
class BatchEvent:
    batch_id: str
    task_id: str
    claim_id: str
    attempt: int
    ordinal: int
    kind: str
    state: str
    details: dict[str, Any] = field(default_factory=dict)
    stateful: bool = True
    timestamp: str = ""
    event_id: str = ""
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload["timestamp"]:
            payload["timestamp"] = _utc_now()
        if not payload["event_id"]:
            payload["event_id"] = str(uuid.uuid4())
        return payload


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    claim_id: str
    attempt: int
    state: str
    ordinal: int
    conversation_url: str = ""
    event_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES


@dataclass
class DispatchReport:
    batch_id: str
    journal: str
    submitted: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    terminal: dict[str, str] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"ok": self.ok}


@dataclass(frozen=True)
class _ModeAwareRequest:
    """A request wrapper accepted by :func:`request_witness`.

    ``request_witness`` only requires a ``to_prompt`` method.  Keeping this
    wrapper here avoids widening the already-tested single-envelope protocol.
    """

    base: Any
    batch_id: str
    task: BatchTask
    attempt: int

    def to_prompt(self) -> str:
        payload = json.loads(self.base.to_prompt())
        payload["protocol"] = "hypercomplexbrain.witness_batch.v1"
        payload["batch"] = {
            "batch_id": self.batch_id,
            "task_id": self.task.task_id,
            "attempt": self.attempt,
            "requested_mode": self.task.requested_mode,
        }
        payload["source"] = self.task.source or payload.get("source", {})
        payload["requires"] = list(self.task.requires or payload.get("requires", []))
        payload["task_notes"] = self.task.notes

        acquisition = (
            "Use the connected GitHub connector to read the private repository at "
            "the stated commit/ref. Do not spend the run attempting unauthenticated "
            "git clone first. If the connector or a required file is unavailable, "
            "return mode 'declined' with the exact blocker. "
        )
        if self.task.requested_mode == VerificationMode.REVIEWED:
            payload["instruction"] = (
                acquisition
                + "Review the argument, implementation, controls, and evidence "
                  "direction. Do not claim that you recomputed the result unless "
                  "you actually ran the recorded command and produced artifacts. "
                  "Return mode 'reviewed' with concrete findings, or 'declined'."
            )
        else:
            payload["instruction"] = (
                acquisition
                + "Run the recorded command in an independently materialized copy "
                  "of the stated commit. Report SHA-256 digests for every comparable "
                  "artifact. Do not copy the producer digests. Return 'recomputed' "
                  "only after execution; otherwise return 'declined'."
            )
        return json.dumps(payload, indent=2, sort_keys=True)


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _known_secret_values() -> tuple[str, ...]:
    return tuple(
        value for name in TOKEN_ENV_VARS
        if (value := os.environ.get(name, "").strip())
    )


def _redact(value: Any) -> Any:
    """Remove token-shaped keys and exact in-process secret values before writes."""
    secrets = _known_secret_values()
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            lower = str(key).lower()
            if any(word in lower for word in ("authorization", "bearer", "api_key", "token")):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = _redact(item)
        return out
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted
    return value


def load_batch_manifest(path: str | Path) -> BatchManifest:
    data = json.loads(Path(path).read_text())
    tasks = tuple(BatchTask(**task) for task in data.get("tasks", ()))
    return BatchManifest(
        schema=data.get("schema", ""),
        batch_id=data["batch_id"],
        repository=data.get("repository", "jesusvilela/hypercomplexbrain"),
        ref=data.get("ref", ""),
        journal=data["journal"],
        max_workers=int(data.get("max_workers", 2)),
        tasks=tasks,
    )


def load_journal(path: str | Path) -> list[BatchEvent]:
    path = Path(path)
    if not path.exists():
        return []
    events: list[BatchEvent] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        if data.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{line_number}: unsupported schema")
        known = {name for name in BatchEvent.__dataclass_fields__}
        events.append(BatchEvent(**{k: v for k, v in data.items() if k in known}))
    return events


def append_event(path: str | Path, event: BatchEvent,
                 lock: threading.Lock | None = None) -> dict[str, Any]:
    path = Path(path)
    payload = _redact(event.to_dict())
    encoded = json.dumps(payload, sort_keys=True) + "\n"

    def write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())

    if lock is None:
        write()
    else:
        with lock:
            write()
    return payload


def fold_journal(events: Iterable[BatchEvent]) -> dict[str, TaskSnapshot]:
    """Fold an append-only event set into one snapshot per task.

    Ordering is by ``(attempt, ordinal)`` rather than file position, so shuffling
    independent journal lines cannot change state.  Two stateful events at the
    same coordinate with different states are corruption, not a tie to resolve.
    """
    by_task: dict[str, list[BatchEvent]] = {}
    for event in events:
        if event.stateful:
            by_task.setdefault(event.task_id, []).append(event)

    snapshots: dict[str, TaskSnapshot] = {}
    for task_id, task_events in by_task.items():
        coordinates: dict[tuple[int, int], BatchEvent] = {}
        for event in task_events:
            key = (event.attempt, event.ordinal)
            prior = coordinates.get(key)
            if prior is not None and (
                prior.state != event.state or prior.details != event.details
            ):
                raise ValueError(
                    f"conflicting stateful events for {task_id} at {key}: "
                    f"{prior.state!r} vs {event.state!r}")
            coordinates[key] = event
        latest = coordinates[max(coordinates)]
        snapshots[task_id] = TaskSnapshot(
            task_id=latest.task_id,
            claim_id=latest.claim_id,
            attempt=latest.attempt,
            state=latest.state,
            ordinal=latest.ordinal,
            conversation_url=str(latest.details.get("conversation_url", "")),
            event_id=latest.event_id,
            details=dict(latest.details),
        )
    return snapshots


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _deduplicate_tasks(tasks: Iterable[BatchTask]) -> tuple[list[BatchTask], list[BatchTask]]:
    unique: list[BatchTask] = []
    duplicates: list[BatchTask] = []
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            duplicates.append(task)
        else:
            seen.add(task.task_id)
            unique.append(task)
    return unique, duplicates


def _next_attempt(snapshot: TaskSnapshot | None, explicit_retry: bool) -> tuple[int | None, str]:
    if snapshot is None:
        return 1, "new"
    if snapshot.state == VerificationMode.PENDING:
        return None, "pending handle already exists; pending is never retried implicitly"
    if snapshot.state in {
        VerificationMode.RECOMPUTED,
        VerificationMode.REVIEWED,
        VerificationMode.ATTESTED,
    }:
        return None, f"terminal state {snapshot.state!r} already recorded"
    if snapshot.state in RETRYABLE_STATES:
        if explicit_retry:
            return snapshot.attempt + 1, f"explicit retry after {snapshot.state}"
        return None, f"state {snapshot.state!r} requires an explicit retry"
    if snapshot.state == "dispatch_started":
        if explicit_retry:
            return snapshot.attempt + 1, "explicit retry after uncertain dispatch boundary"
        return None, "dispatch outcome unknown; reconcile before retrying"
    return None, f"state {snapshot.state!r} is not dispatchable"


def _dispatch_one(*, manifest: BatchManifest, task: BatchTask, attempt: int,
                  root: Path, journal: Path, endpoint: str,
                  transport: Callable | None, lock: threading.Lock) -> tuple[str, str, bool, list[str]]:
    envelope_path = _resolve(root, task.envelope)
    envelope = load_envelope(envelope_path)
    if not isinstance(envelope, EvidenceEnvelope):
        raise WitnessError(f"{task.envelope} is not an EvidenceEnvelope")
    if envelope.claim_id != task.claim_id:
        raise WitnessError(
            f"task {task.task_id}: manifest claim {task.claim_id!r} != "
            f"envelope claim {envelope.claim_id!r}")

    append_event(journal, BatchEvent(
        batch_id=manifest.batch_id,
        task_id=task.task_id,
        claim_id=task.claim_id,
        attempt=attempt,
        ordinal=10,
        kind="dispatch_started",
        state="dispatch_started",
        details={"requested_mode": task.requested_mode},
    ), lock)

    base = build_request(envelope, repository=manifest.repository,
                         source=task.source)
    request = _ModeAwareRequest(base, manifest.batch_id, task, attempt)
    response = request_witness(request, endpoint=endpoint, transport=transport)

    # Persist the transport handle *before* mutating the envelope.  If the process
    # stops after the trigger accepted the task, the journal still knows that a
    # remote run may exist and will not dispatch another one automatically.
    response_summary = {
        "mode": response.mode,
        "conversation_url": response.conversation_url,
        "verifier_identity": response.verifier_identity,
        "environment": response.environment,
        "notes": response.notes,
        "artifacts": response.artifacts,
        "observed_result_digest": _json_digest(response.observed_result),
    }
    append_event(journal, BatchEvent(
        batch_id=manifest.batch_id,
        task_id=task.task_id,
        claim_id=task.claim_id,
        attempt=attempt,
        ordinal=20,
        kind="transport_returned",
        state=response.mode,
        details=response_summary,
    ), lock)

    envelope, verification = apply_witness(envelope, response)
    save_envelope(envelope, envelope_path)
    append_event(journal, BatchEvent(
        batch_id=manifest.batch_id,
        task_id=task.task_id,
        claim_id=task.claim_id,
        attempt=attempt,
        ordinal=30,
        kind="response_applied",
        state=envelope.verification_mode,
        details={
            "conversation_url": envelope.witness_conversation_url,
            "independent": verification.independent,
            "verification_ok": verification.ok,
            "failures": verification.failures,
            "warnings": verification.warnings,
        },
    ), lock)
    return task.task_id, envelope.verification_mode, verification.ok, verification.failures


def dispatch_batch(manifest_path: str | Path, *, root: str | Path = ".",
                   journal_path: str | Path | None = None,
                   workers: int | None = None,
                   retry_task_ids: Iterable[str] = (),
                   endpoint: str = GODELIAN_1_ENDPOINT,
                   transport: Callable | None = None) -> DispatchReport:
    root = Path(root).resolve()
    manifest = load_batch_manifest(_resolve(root, manifest_path))
    journal = _resolve(root, journal_path or manifest.journal)
    retry = set(retry_task_ids)
    current = fold_journal(load_journal(journal))
    unique, duplicates = _deduplicate_tasks(manifest.tasks)
    report = DispatchReport(manifest.batch_id, str(journal.relative_to(root)))
    lock = threading.Lock()

    for duplicate in duplicates:
        report.skipped[duplicate.task_id] = "duplicate manifest entry"
        append_event(journal, BatchEvent(
            batch_id=manifest.batch_id,
            task_id=duplicate.task_id,
            claim_id=duplicate.claim_id,
            attempt=max(1, current.get(duplicate.task_id, TaskSnapshot(
                duplicate.task_id, duplicate.claim_id, 0, "none", 0)).attempt),
            ordinal=0,
            kind="duplicate_skipped",
            state="skipped",
            details={"reason": "duplicate manifest entry"},
            stateful=False,
        ), lock)

    dispatchable: list[tuple[BatchTask, int]] = []
    for task in unique:
        attempt, reason = _next_attempt(current.get(task.task_id), task.task_id in retry)
        if attempt is None:
            report.skipped[task.task_id] = reason
            continue
        dispatchable.append((task, attempt))
        report.submitted.append(task.task_id)

    pool_size = min(workers or manifest.max_workers, manifest.max_workers, 8)
    if not dispatchable:
        return report

    with ThreadPoolExecutor(max_workers=pool_size,
                            thread_name_prefix="witness-weave") as executor:
        futures = {
            executor.submit(
                _dispatch_one,
                manifest=manifest,
                task=task,
                attempt=attempt,
                root=root,
                journal=journal,
                endpoint=endpoint,
                transport=transport,
                lock=lock,
            ): task
            for task, attempt in dispatchable
        }
        for future in as_completed(futures):
            task = futures[future]
            try:
                task_id, state, ok, failures = future.result()
            except Exception as exc:
                # KeyboardInterrupt/SystemExit are BaseException and deliberately
                # propagate. Ordinary transport/program errors are journalled.
                message = f"{type(exc).__name__}: {exc}"
                report.failed[task.task_id] = message
                snapshot = fold_journal(load_journal(journal)).get(task.task_id)
                attempt = snapshot.attempt if snapshot else 1
                append_event(journal, BatchEvent(
                    batch_id=manifest.batch_id,
                    task_id=task.task_id,
                    claim_id=task.claim_id,
                    attempt=attempt,
                    ordinal=25,
                    kind="dispatch_failed",
                    state="failed",
                    details={"error": message},
                ), lock)
                continue
            if state == VerificationMode.PENDING:
                report.pending.append(task_id)
            elif state in TERMINAL_STATES:
                report.terminal[task_id] = state
            if not ok:
                report.failed[task_id] = "; ".join(failures) or "verification failed"
    return report


def _task_by_id(manifest: BatchManifest, task_id: str) -> BatchTask:
    matches = [task for task in manifest.tasks if task.task_id == task_id]
    if not matches:
        raise KeyError(f"unknown task_id {task_id!r}")
    return matches[0]


def ingest_response(manifest_path: str | Path, task_id: str,
                    response_path: str | Path, *, root: str | Path = ".",
                    journal_path: str | Path | None = None) -> dict[str, Any]:
    """Apply one explicit terminal response to a pending task.

    There is no hidden poller.  A response exported from the agent conversation
    is supplied as JSON and ingested exactly once.  A second, different terminal
    response for the same attempt is refused rather than allowed to overwrite a
    contradiction.
    """
    root = Path(root).resolve()
    manifest = load_batch_manifest(_resolve(root, manifest_path))
    task = _task_by_id(manifest, task_id)
    journal = _resolve(root, journal_path or manifest.journal)
    events = load_journal(journal)
    snapshot = fold_journal(events).get(task_id)
    if snapshot is None:
        raise WitnessError(f"task {task_id!r} has never been dispatched")
    if snapshot.state in TERMINAL_STATES:
        raise WitnessError(
            f"task {task_id!r} already has terminal state {snapshot.state!r}; "
            "create an explicit retry attempt rather than overwriting it")

    response_file = _resolve(root, response_path)
    response_digest = file_digest(response_file)
    for event in events:
        if (event.task_id == task_id
                and event.attempt == snapshot.attempt
                and event.kind == "response_ingested"
                and event.details.get("response_digest") == response_digest):
            return {"task_id": task_id, "state": event.state,
                    "idempotent": True, "event_id": event.event_id}

    response = parse_response(json.loads(response_file.read_text()))
    if response.mode == VerificationMode.PENDING:
        raise WitnessError("an ingested response must be terminal, not pending")
    if not response.conversation_url:
        response.conversation_url = snapshot.conversation_url

    envelope_path = _resolve(root, task.envelope)
    envelope = load_envelope(envelope_path)
    if not isinstance(envelope, EvidenceEnvelope):
        raise WitnessError(f"{task.envelope} is not an EvidenceEnvelope")
    envelope, verification = apply_witness(envelope, response)
    save_envelope(envelope, envelope_path)
    payload = append_event(journal, BatchEvent(
        batch_id=manifest.batch_id,
        task_id=task.task_id,
        claim_id=task.claim_id,
        attempt=snapshot.attempt,
        ordinal=40,
        kind="response_ingested",
        state=envelope.verification_mode,
        details={
            "response_digest": response_digest,
            "conversation_url": envelope.witness_conversation_url,
            "independent": verification.independent,
            "verification_ok": verification.ok,
            "failures": verification.failures,
            "warnings": verification.warnings,
        },
    ))
    return {
        "task_id": task_id,
        "state": envelope.verification_mode,
        "independent": verification.independent,
        "verification_ok": verification.ok,
        "failures": verification.failures,
        "warnings": verification.warnings,
        "event_id": payload["event_id"],
        "idempotent": False,
    }


def batch_status(manifest_path: str | Path, *, root: str | Path = ".",
                 journal_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    manifest = load_batch_manifest(_resolve(root, manifest_path))
    journal = _resolve(root, journal_path or manifest.journal)
    snapshots = fold_journal(load_journal(journal))
    rows: list[dict[str, Any]] = []
    for task in manifest.tasks:
        snapshot = snapshots.get(task.task_id)
        envelope = load_envelope(_resolve(root, task.envelope))
        state = snapshot.state if snapshot else envelope.verification_mode
        rows.append({
            "task_id": task.task_id,
            "claim_id": task.claim_id,
            "requested_mode": task.requested_mode,
            "attempt": snapshot.attempt if snapshot else 0,
            "state": state,
            "conversation_url": snapshot.conversation_url if snapshot else
                                envelope.witness_conversation_url,
            "independent": bool(envelope.independent),
        })
    return {"batch_id": manifest.batch_id, "journal": str(journal), "tasks": rows}


def _rank_name(rank: int) -> str:
    return {
        EvidenceRank.NONE: "NONE",
        EvidenceRank.ATTESTED: "ATTESTED",
        EvidenceRank.REVIEWED: "REVIEWED",
        EvidenceRank.INDEPENDENT: "INDEPENDENT",
    }.get(rank, f"UNKNOWN({rank})")


def render_witness_markdown(manifest_path: str | Path, *, root: str | Path = ".",
                            journal_path: str | Path | None = None) -> str:
    """Render the actual folded state, never the desired state, as Mermaid."""
    root = Path(root).resolve()
    manifest = load_batch_manifest(_resolve(root, manifest_path))
    journal = _resolve(root, journal_path or manifest.journal)
    snapshots = fold_journal(load_journal(journal))
    graph = WitnessGraph()
    rows: list[dict[str, Any]] = []

    for task in manifest.tasks:
        envelope = load_envelope(_resolve(root, task.envelope))
        snapshot = snapshots.get(task.task_id)
        mode = snapshot.state if snapshot else envelope.verification_mode
        verifier = envelope.verifier or task.verifier
        graph.add(WitnessAct(task.claim_id, envelope.producer or "producer",
                             verifier, mode if mode in {
                                 VerificationMode.ATTESTED,
                                 VerificationMode.REVIEWED,
                                 VerificationMode.RECOMPUTED,
                                 VerificationMode.CONTRADICTED,
                                 VerificationMode.DECLINED,
                                 VerificationMode.PENDING,
                                 VerificationMode.NOT_REQUESTED,
                             } else VerificationMode.DECLINED))
        rank = evidence_rank(graph, task.claim_id)
        rows.append({
            "task": task,
            "mode": mode,
            "rank": _rank_name(rank),
            "conversation_url": snapshot.conversation_url if snapshot else
                                envelope.witness_conversation_url,
        })

    lines = [
        f"# Witness weave: `{manifest.batch_id}`",
        "",
        "This view is generated from the append-only journal and current evidence "
        "envelopes. Dashed edges are transport-only states and carry no evidence.",
        "",
        "```mermaid",
        "flowchart LR",
        "  G[\"Godelian-1\"]",
    ]
    for index, row in enumerate(rows, start=1):
        task = row["task"]
        producer = f"P{index}"
        claim = f"C{index}"
        label = row["mode"].upper()
        lines.append(f"  {producer}[\"{task.task_id}\"]")
        lines.append(f"  {claim}{{\"{task.claim_id}\\nrank={row['rank']}\"}}")
        lines.append(f"  {producer} --> {claim}")
        arrow = "-.->" if row["mode"] in {
            VerificationMode.PENDING,
            VerificationMode.NOT_REQUESTED,
            VerificationMode.DECLINED,
        } else "-->"
        lines.append(f"  {claim} {arrow}|{label}| G")
    lines += ["```", "", "| Task | Claim | Requested | State | Evidence rank | Handle |",
              "|---|---|---:|---|---|---|"]
    for row in rows:
        task = row["task"]
        handle = row["conversation_url"] or "—"
        lines.append(
            f"| `{task.task_id}` | `{task.claim_id}` | {task.requested_mode} | "
            f"{row['mode']} | {row['rank']} | {handle} |")
    lines += [
        "",
        "## Reading rule",
        "",
        "`PENDING`, `DECLINED`, and `NOT_REQUESTED` remain rank `NONE`. "
        "Attestations are bounded at `ATTESTED`; reviews reach `REVIEWED`; only "
        "a matching recomputation of comparable deterministic artifacts reaches "
        "`INDEPENDENT`. Ranks are maxima of direct acts, never sums over parties.",
        "",
    ]
    return "\n".join(lines)


def write_witness_markdown(manifest_path: str | Path, output: str | Path, *,
                           root: str | Path = ".",
                           journal_path: str | Path | None = None) -> Path:
    root = Path(root).resolve()
    destination = _resolve(root, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_witness_markdown(
        manifest_path, root=root, journal_path=journal_path))
    return destination
