# Claude Code Project Instructions

Read `docs/CLAUDE_CODE_CO_DEVELOPMENT.md` as the standing evidence and correction contract.

**Active round: none.** R6M is reported: `EQUIVALENT_ON_SEALED_GRID`, and its
artifact `artifacts/r6m_parametric_equivalence/equivalence.json` is the licence
`aionq.common_receiver_parametric.build_fork` requires before it will evaluate
any held-out Part B depth. Part B is preregistered -- `manifests/qsigma_r6k_w1_partb_input_freeze.json`
is its input freeze, with every field that once read PENDING now filled -- and
remains UNEXECUTED. (This file said "unpreregistered as a run" for one commit;
that was written without reading the freeze, and was wrong.) Its pre-execution
gate needs `refs/tags/qsigma-r6k-w1-partb-prereg-v1` on origin at C_pre =
`d0650f0`. This environment's git relay refuses tag pushes (HTTP 403), so the
tag must be pushed from elsewhere; nothing in the repository needs to change. The next round must be preregistered before its implementation
commit, and its frozen criterion exercised with `aionq.criterion.exercise`
before it runs -- see below.

This line previously pointed at `manifests/qsigma_r5_witness_weave_preregistration.json`
as the active round for twenty-plus rounds after R5 finished. A standing
instruction that names a round which has closed is the same defect as a
manifest pointer into a test that does not exist: it fails silently, because
nothing executes it.

Before editing:

1. Inspect the live repository and current HEAD; do not trust summaries over artifacts.
2. Load only the task-relevant installed skill entrypoints, validating each before use.
3. Confirm that the active round's preregistration predates its implementation commits (`self_audit.preregistration_ordering` measures this against git, not against the manifest's own flag).
4. Preserve `P/A/M/H/S/R`, typed remainders, supersession history, and the stop rule.
5. Before running any round, exercise its frozen criterion with
   `aionq.criterion.exercise`: every verdict needs a witness that reaches it,
   the regions must be disjoint, and every defaulted keyword of the entry point
   must carry a value in the manifest. Four rounds -- R1S, R1X, R1Y, R1Z --
   were decided by their own frozen rules rather than by what they measured,
   and every one of those defects was visible with no measurement at all.
6. Do not begin QTau-Germinal, add another cognitive organ, or claim independent witnessing in this round.
7. Do not claim cross-platform success without actual green jobs on that platform.
8. Never write `GODELIAN_AGENT_TOKEN`, `AGENT_ACCESS_TOKEN`, an OpenAI API key, a request Authorization header, or a prompt containing one into the repository, logs, envelopes, or command history.
9. The workspace-agent trigger is asynchronous. `PENDING` plus a `conversation_url` is a transport state, not a verdict and not evidence.
10. Do not invent a polling API. Use explicit response JSON ingestion until a supported connector exists.
11. Do not open a pull request unless explicitly requested.

Implementation surfaces are set by the active round's manifest
(`files_expected_to_change`), not by this file. The R5 witness-weave surfaces
that used to be listed here are finished work; naming them as live sent every
session to the wrong five files.

Required verification before any success claim:

```bash
python -m pip install -e .
python -m pytest -q                      # see the last commit message for the current count
```

The full suite takes about twelve minutes. Run the active round's own test file
first for a fast signal, then the whole suite before any success claim -- this
line has twice had a change pass its own tests and break another module.

Do not trigger the live batch merely to make a test pass. Trigger it only when the token is available in the shell environment and the user has authorized the live run. At completion, return exact commands, environments, raw artifact paths and hashes, test counts, journal state, conversation handles, envelope status, remaining typed remainders, and final commit SHA.
