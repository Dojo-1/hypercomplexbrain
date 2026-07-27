# Handoff — collecting the Gödelian-1 review batch

Seven `reviewed` challenges were dispatched asynchronously. The container that
sent them is gone; the handles are here.

## What is pending

`artifacts/r4/review_batch/dispatch.json` holds one conversation URL per claim.
Each asks Gödelian-1 to attack a specific claim — chosen adversarially, each one
I would most like to be wrong about.

## How to collect a verdict

Read the conversation, then:

```python
from aionq.evidence import load_envelope, save_envelope
from aionq.witness import apply_witness, parse_response

reply = parse_response('{"mode": "reviewed", "notes": "...", "environment": "..."}')
env, result = apply_witness(load_envelope(path), reply)
save_envelope(env, path)
```

`mode` must be one of `reviewed | attested | declined`. Do **not** write
`recomputed` for a review — it is the only mode that sets `independent`, and
Gödelian-1 ran nothing.

## What a review can and cannot do

**Cannot promote anything.** `reviewed` is excluded from
`VerificationMode.INDEPENDENT_MODES` by design: argument-independence and
arithmetic-independence are different axes, and collapsing them lets a
well-argued wrong number climb the lattice.

**Can retire something.** If a review finds a real defect, that is a correction
and it supersedes — it does not overwrite. Prior statements stay in the ledger
with a pointer forward.

## Current state, computed not asserted

- 261 tests, Linux only. Windows and macOS unknown until a green CI job exists.
- Ledger 90 claims. `Registry.unwitnessed()` reports those with no envelope.
- 2/2 committed envelopes verify.
- **Zero envelopes independently witnessed.** The witness graph has one edge,
  mode `declined`, so `evidence_rank` is NONE. That is the correct place to be
  standing before anyone has checked anything.

## The one blocker worth fixing first

Gödelian-1's container blocks GitHub (`CONNECT 403`), so it cannot obtain the
source and cannot `recompute`. Adding the first-party **GitHub connector** to the
workspace agent removes that without standing up a custom MCP server. Then
`EXP-S7-AUDIT_REPLICATION` is the right first recomputation target: it is fully
deterministic, so a digest match would be the first genuine independent witness
here, and a mismatch would be a real disagreement rather than a different CPU.
