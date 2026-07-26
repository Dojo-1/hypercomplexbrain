# Claude Code Co-Development Membrane

This file is a direct execution prompt and operating contract for the next joint round.
It is intentionally narrower than the full AION vision: close the witness/reproducibility
membrane before adding another cognitive organ or ontology layer.

## Roles

- **Claude Code:** local execution cortex: inspect the repository, edit files, run the full
  matrix, benchmark, capture raw artifacts, and commit only what actually ran.
- **External research auditor:** architecture, mathematical typing, adversarial review,
  evidence promotion, and cross-agent correction. Claude's prose is not evidence; commits,
  raw outputs, environments, and independent checks are evidence candidates.

## Skills to load locally

Load the installed skills whose entrypoints actually exist. Do not assume a skill is valid
from its directory name alone.

1. `manifold-research-bootstrap` — evidence lattice and correction history.
2. `recursive-research-auditor` — claim/artifact map, representation attacks, stop rule.
3. `hypercomplex-learning-towers` — non-flattening translation and typed remainder.
4. `thinking-with-jesus-vilela` — peer-research stance and multi-angle epistemics.
5. `acaf-fuzzer` — adversarial parameter-space sweeps.
6. Where present and valid: `hamiltonian-mind-governance`,
   `nnn-sectional-accelerator`, `slang-s1-interpreter`, and `utai-hyperdim-prover`.

For every loaded skill, record: path, declared name, description, content hash, and why it is
relevant. If two skills conflict, preserve source evidence, correction history, typed remainder,
and the narrower task-specific execution rule.

---

# Direct prompt: QSigma-R4 — Witnessed Reproducibility Membrane

Work in `jesusvilela/hypercomplexbrain` on branch
`claude/aion-brain-architecture-27f8ji`.

## Evidence floor

Use `P/A/M/H/S/R` consistently. Freeze every original claim before repairing it. Preserve
supersession history. Passing tests validates encoded behaviour, not the intended external
interpretation.

## Scope

Do **not** add a new brain organ, gerbe layer, quantum-telos ontology, or scalar summary.
Implement the smallest membrane that binds claims to independent, reproducible artifacts.

Before editing, write a preregistration manifest containing:

- exact object and claims;
- intended invariants;
- files expected to change;
- controls and representation attacks;
- resource budget;
- kill conditions;
- stop condition;
- promotion rule.

## R4-A — Fail-closed simulation portfolio

Audit `src/aionq/residency.py` and all callers.

1. Replace broad exception swallowing where a narrower expected exception exists.
2. Preserve per-path status:
   - `valid`;
   - `unsupported_representation`;
   - `opaque_instruction`;
   - `transpile_failed`;
   - `unexpected_error`.
3. A path with an opaque or unpriced instruction is invalid as an upper-bound candidate.
4. An invalid path must never lower `q_sim_upper`.
5. Unexpected errors must propagate or be explicitly surfaced in the report; never convert
   them silently into a scientific result.
6. If no valid path survives, report the upper bound as unknown, with a typed remainder.
7. Add analytic, metamorphic, and adversarial tests, including an injected opaque gate and a
   deliberately failing compiler path.

Kill condition: any opaque or failed path can make the reported simulation bound smaller.

## R4-B — Separate cache correctness from performance

For the quaternion basis/cache:

1. Add a deterministic functional test proving exactly one construction followed by reuse.
2. Restore all global state after tests.
3. Remove wall-clock thresholds from the ordinary correctness suite.
4. Add a benchmark harness measuring:
   - sheaf baseline;
   - quaternion cached;
   - quaternion uncached.
5. Include warm-up, randomized condition order, multiple batches, medians, bootstrap
   intervals, raw timings, Python/NumPy/BLAS/CPU/platform metadata, commit SHA, and JSON output.
6. Treat `17.2x` and `27.8x` as historical environment-specific measurements, not constants.

Kill condition: the documented cache claim cannot be reconstructed from a raw benchmark
artifact and environment envelope.

## R4-C — Portable resource accounting

1. Normalize `ru_maxrss` units across Linux and macOS.
2. Treat Windows RSS as unavailable unless a portable provider is explicitly installed.
3. Distinguish:
   - Python allocation peak from `tracemalloc`;
   - current RSS;
   - process-lifetime maximum RSS;
   - isolated per-condition process peak.
4. Rename fields so units and temporal scope are explicit.
5. For attributable RSS, execute the condition in an isolated subprocess.
6. Add platform-specific behavioural tests without pretending one OS emulation proves the
   others.

Kill condition: the same physical memory use can be reported with a silent 1024x unit error,
or an earlier condition's lifetime peak is attributed to a later condition.

## R4-D — External EvidenceEnvelope

Create a machine-readable artifact such as:

```text
EvidenceEnvelope {
  schema_version
  claim_id
  evidence_tag
  commit_sha
  command
  working_directory
  platform
  environment_hash
  dependency_lock_hash
  input_hashes
  seeds
  raw_artifact_hashes
  observed_result
  uncertainty
  verifier_identity
  timestamp
  signature_status
  typed_remainders
}
```

Requirements:

1. Governance consumes envelopes; registry prose is not its own evidence.
2. `M`, `A`, or `P` promotion requires an envelope appropriate to the tag.
3. A registry edit without a matching new artifact cannot promote a claim.
4. Corrupt hashes, missing artifacts, mismatched commits, and altered commands must fail.
5. Preserve old claims and envelopes; supersede, never overwrite.
6. Separate producer, verifier, and promoter roles in code and metadata.
7. Add a proof-envelope variant for formal artifacts, including theorem name, prover version,
   dependency hashes, axiom inventory, build command, and artifact hash.

Kill condition: copying a prose result into JSON passes as independent witnessing.

## R4-E — CI and cross-platform matrix

Add CI for supported Python versions on Linux, Windows, and macOS. The matrix must:

- install the package using the real `src/` layout;
- run the correctness suite;
- validate evidence envelopes;
- run benchmark smoke tests without enforcing machine-specific speed ratios;
- upload raw evidence/benchmark artifacts;
- expose platform-specific skips explicitly.

Do not report cross-platform success until each platform has an actual green job.

## R4-F — Registry/external-audit round trip

Trace and test:

```text
requirement -> formal object -> implementation -> test -> raw measurement
-> evidence envelope -> registry status -> published claim -> requirement
```

Report every lossy edge and its typed remainder. Add at least one historical regression case
where a formerly promoted claim is rejected by the new membrane.

## Required output

Return:

1. preregistration manifest;
2. files changed and why;
3. exact commands and versions;
4. test counts per platform actually run;
5. benchmark distributions, not only point estimates;
6. evidence-envelope examples and hashes;
7. claims promoted, held, narrowed, or retired;
8. failures and unresolved typed remainders;
9. final commit SHA.

Do not claim independent reproduction unless the verifier is genuinely independent in code
path, environment, data, assumptions, or authorship. Do not open a PR unless explicitly asked.

## Stop rule

Stop after R4. Do not begin QTau-Germinal, UTAI, lambda-sat, higher gerbes, quantum
holoportation, or another architecture lift in the same round. The next scope begins only after
an external audit of the R4 commit and its raw artifacts.
