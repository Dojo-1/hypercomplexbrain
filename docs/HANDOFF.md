# Handoff — collecting the Gödelian-1 review batch

Seven `reviewed` challenges were dispatched asynchronously. The container that
sent them is gone. Publishable one-way references to the handles are preserved
in the sanitized source artifact and append-only witness journal; raw handles
are deliberately excluded.

## What is pending

`artifacts/r4/review_batch/dispatch.json` holds one opaque handle reference per claim.
Each asks Gödelian-1 to attack a specific claim — chosen adversarially, each one
I would most like to be wrong about.

The validated reconciliation command imported all seven as `PENDING`, attempt
1, with source digest
`sha256:22e4540fc5f777462b78403ce389f307c5e81335db0f82ff42214dd9d52286a7`.
Re-running it is idempotent and makes no external call:

```bash
PYTHONPATH=src python3 experiments/dispatch_review_batch.py reconcile \
  artifacts/r4/review_batch/dispatch.json
```

## How to collect a verdict

Read the conversation, export a bounded response JSON, then use the journaled
ingestion path:

```bash
PYTHONPATH=src python3 experiments/dispatch_review_batch.py ingest \
  TASK_ID response.json
PYTHONPATH=src python3 experiments/dispatch_review_batch.py status
PYTHONPATH=src python3 experiments/dispatch_review_batch.py render
```

`mode` must be one of `reviewed | attested | declined`. Do **not** write
`recomputed` for a review — it is the only mode that sets `independent`, and
Gödelian-1 ran nothing. Re-ingesting the exact same response digest is
idempotent; a different terminal response for that attempt is refused.

## What a review can and cannot do

**Cannot promote anything.** `reviewed` is excluded from
`VerificationMode.INDEPENDENT_MODES` by design: argument-independence and
arithmetic-independence are different axes, and collapsing them lets a
well-argued wrong number climb the lattice.

**Can retire something.** If a review finds a real defect, that is a correction
and it supersedes — it does not overwrite. Prior statements stay in the ledger
with a pointer forward.

## Current state, computed not asserted

- `s7-deterministic-recompute`: `NOT_REQUESTED`;
- `r4-benchmark-review`: historical `DECLINED`;
- seven adversarial reviews: `PENDING`, attempt 1;
- every pending/declined/not-requested claim has evidence rank `NONE`;
- **zero envelopes independently witnessed**.

The generated state is
`artifacts/witness_batches/godelian-review-v1/WITNESS_NERVE.md`.

## The one blocker worth fixing first

Gödelian-1's container blocks GitHub (`CONNECT 403`), so it cannot obtain the
source and cannot `recompute`. Adding the first-party **GitHub connector** to the
workspace agent removes that without standing up a custom MCP server. Then
`EXP-S7-AUDIT_REPLICATION` is the right first recomputation target: it is fully
deterministic, so a digest match would be the first genuine independent witness
here, and a mismatch would be a real disagreement rather than a different CPU.

Before any trigger, run `dispatch --dry-run`. The CLI enforces
`manifests/godelian_dispatch_request.json` as a task allowlist. No live dispatch
is implied by this handoff.
