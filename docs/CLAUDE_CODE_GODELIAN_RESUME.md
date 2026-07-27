# QSigma-R5 — Godelian asynchronous witness resume protocol

This is a direct Claude Code prompt for resuming the interrupted witness batch without
creating duplicate remote runs.

## Frozen evidence floor

- Repository: `jesusvilela/hypercomplexbrain`
- Branch: `claude/aion-brain-architecture-27f8ji`
- Last observed head when this protocol was written: `9e476a508ee74cea7bd114a3648bd450cf821aca`
- Dispatch request commit: `b2f391b3b3b3165fee89b9d6d301aef2fa3b6b21`
- Batch: `godelian-review-v1`
- Requested tasks:
  - `s7-deterministic-recompute`
  - `r4-benchmark-review`

At this floor, the repository contains no committed
`artifacts/witness_batches/godelian-review-v1/events.jsonl`, `runner_outcome.json`,
or `WITNESS_NERVE.md`. The deterministic S7 envelope still reads
`verification_mode = not_requested`; the R4 benchmark envelope retains the earlier
`declined` attempt. Therefore no new terminal witness, pending handle, or runner outcome is
durably established yet.

## Non-negotiable invariant

**Do not retrigger the batch until the prior GitHub Actions run is reconciled.**

The workspace-agent trigger does not advertise an idempotency key. A missing local handle does
not prove that the remote request was never accepted. Duplicate dispatch would corrupt the
append-only witness history and spend a verifier run without justification.

## Step 1 — Inspect, do not edit

Run:

```bash
git status --short
git rev-parse HEAD
git log --oneline -12

gh run list \
  --workflow godelian-witness-batch.yml \
  --branch claude/aion-brain-architecture-27f8ji \
  --limit 20 \
  --json databaseId,event,status,conclusion,headSha,createdAt,updatedAt,url
```

Locate the run whose `headSha` is the dispatch request commit or its immediate trigger lineage.
Do not infer absence from an empty local artifact directory.

## Step 2 — Reconcile exactly one of five states

### A. No workflow run exists

Record a durable `runner_not_started` diagnostic before changing anything. Check:

```bash
gh workflow list
gh secret list
gh api repos/jesusvilela/hypercomplexbrain/actions/permissions
```

Only secret **names** may be displayed. Never print a secret value. Determine whether Actions
were disabled, the workflow was unavailable on the default branch, the path trigger did not
match, or the repository token lacked permissions. Fix the runner cause, but do not dispatch
again without an explicit new request ID and user authorization.

### B. A run exists and failed before remote dispatch

Inspect:

```bash
gh run view RUN_ID --json status,conclusion,jobs,url
gh run view RUN_ID --log-failed
```

Download artifacts if any. Record the exact failing step and whether a network side effect could
have occurred. A failure before `Dispatch the bounded asynchronous batch` is safe to retry only
after the cause is fixed and a new explicit request is committed.

### C. A run may have dispatched but failed before committing handles

This is the dangerous uncertainty state. Download the Actions artifact:

```bash
gh run download RUN_ID --dir /tmp/godelian-run-RUN_ID
find /tmp/godelian-run-RUN_ID -maxdepth 4 -type f -print
```

Search for `dispatch_report.json`, `events.jsonl`, envelopes, conversation URLs, and runner
outcome. If a returned handle exists, recover it into the append-only journal and commit it.
**Do not make a second network request.** If no artifact settles whether the endpoint accepted
the request, record `dispatch_unknown`; only a user-authorized explicit retry attempt may proceed.

### D. Handles were returned and are pending

Commit the journal and folded status immediately. `PENDING` carries evidence rank zero. The
conversation URL is execution state, not proof. Do not retry, promote, or interpret.

### E. A terminal response exists

Export it as JSON and ingest exactly once:

```bash
PYTHONPATH=src python3 experiments/dispatch_review_batch.py ingest TASK_ID response.json
PYTHONPATH=src python3 experiments/dispatch_review_batch.py status
PYTHONPATH=src python3 experiments/dispatch_review_batch.py render
python -m pytest tests/test_witness_batch.py -q
python -m pytest -q
```

Preserve contradictions. Never average or retry them away.

## Step 3 — Commit the reconciliation, not a desired story

The commit must include only the state actually observed:

- runner diagnostic;
- recovered append-only events;
- folded status;
- witness-nerve view;
- changed envelopes, if a terminal response was validly ingested;
- exact commands and raw artifact hashes.

Do not claim independent witnessing merely because a runner started or a conversation exists.

## Optional second transport: OpenAI Batch API

Do not implement this until the workspace-agent run is reconciled. If a fallback is still needed,
preregister it as a separate transport inside QSigma-R5 rather than silently replacing
Godelian-1.

Required design constraints:

1. Use the official Batch API with `/v1/responses` only for independent, self-contained tasks.
2. A Platform key does **not** imply access to the ChatGPT GitHub connector. Materialize the
   required source in the GitHub Actions checkout, bind each file to a SHA-256 digest, and include
   only the bounded source bundle needed by the task.
3. Keep `OPENAI_API_KEY` only in GitHub Secrets. Never persist request authorization, prompts
   containing secrets, or raw keys.
4. Use stable `custom_id = batch_id/task_id/attempt` values and checkpoint the OpenAI input file
   ID and batch ID immediately after creation.
5. The append-only repository journal remains authoritative. API conversation or response state
   is execution memory, not evidence.
6. Store terminal outputs as raw artifacts, then pass them through the same explicit ingestion,
   independence, digest, environment-dependence, and witness-nerve rules.
7. Batch completion, model agreement, or fluent prose does not promote a claim. Only a valid
   `reviewed`, `recomputed`, or `contradicted` response bound to artifacts can change evidence
   rank.
8. Add fake-client tests before any live call. Do not spend a live API request to make a test pass.

## Stop rule

Stop after reconciliation and, only if separately authorized, the bounded fallback transport.
Do not begin QTau-Germinal, add another cognitive organ, or convert the witness relation into a
scalar score.
