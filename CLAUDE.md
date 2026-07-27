# Claude Code Project Instructions

Read `docs/CLAUDE_CODE_CO_DEVELOPMENT.md` as the standing evidence and correction contract, then treat `manifests/qsigma_r5_witness_weave_preregistration.json` as the active round.

Before editing:

1. Inspect the live repository and current HEAD; do not trust summaries over artifacts.
2. Load only the task-relevant installed skill entrypoints, validating each before use.
3. Confirm that the QSigma-R5 preregistration predates the implementation commits.
4. Preserve `P/A/M/H/S/R`, typed remainders, supersession history, and the stop rule.
5. Work only on the asynchronous Godelian-1 batch, append-only journal, response-ingestion path, adversarial tests, and witness-nerve visualization.
6. Do not begin QTau-Germinal, add another cognitive organ, or claim independent witnessing in this round.
7. Do not claim cross-platform success without actual green jobs on that platform.
8. Never write `GODELIAN_AGENT_TOKEN`, `AGENT_ACCESS_TOKEN`, an OpenAI API key, a request Authorization header, or a prompt containing one into the repository, logs, envelopes, or command history.
9. The workspace-agent trigger is asynchronous. `PENDING` plus a `conversation_url` is a transport state, not a verdict and not evidence.
10. Do not invent a polling API. Use explicit response JSON ingestion until a supported connector exists.
11. Do not open a pull request unless explicitly requested.

Implementation surfaces:

- `src/aionq/witness_batch.py`
- `experiments/dispatch_review_batch.py`
- `manifests/godelian_review_batch_v1.json`
- `tests/test_witness_batch.py`
- `docs/WITNESS_WEAVE.md`

Required verification before any success claim:

```bash
python -m pip install -e .
python -m pytest tests/test_witness_batch.py -q
python -m pytest -q
PYTHONPATH=src python3 experiments/dispatch_review_batch.py status
PYTHONPATH=src python3 experiments/dispatch_review_batch.py render
```

Do not trigger the live batch merely to make a test pass. Trigger it only when the token is available in the shell environment and the user has authorized the live run. At completion, return exact commands, environments, raw artifact paths and hashes, test counts, journal state, conversation handles, envelope status, remaining typed remainders, and final commit SHA.
