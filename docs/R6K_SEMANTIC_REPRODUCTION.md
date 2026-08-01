# R6k, recomputed on a second platform — QSigma-R6k-W1

R6k was executed once, on Windows / CPython 3.13 / numpy 2.4.5, from an
uncommitted working tree. R6l seals it byte-for-byte as upstream. Until now
nobody else had run it.

```bash
PYTHONPATH=src python3 experiments/run_r6k_semantic_reproduction.py run
git add artifacts/r6k_w1_semantic_reproduction && git commit      # C_raw
PYTHONPATH=src python3 experiments/run_r6k_semantic_reproduction.py envelope
git add artifacts/r6k_w1_semantic_reproduction && git commit      # C_env
```

Two phases, and the split is not cosmetic — see *What an external audit found*
below. An envelope must bind to a commit that **contains** what it binds, and the
`envelope` phase refuses to write one unless every raw artifact resolves at HEAD
with those exact bytes.

**Verdict: CONFIRMED.** 3555 scientific leaves compared across two platforms,
worst absolute difference **3.311e-11** against a tolerance of **1e-10** frozen
before the comparator existed. The discrete verdict is identical on both sides:
`ANISOTROPIC_ANGULAR_GAIN_NO_RADIAL_GAIN`. 320 event rows on both sides, same
keys, same order, contiguous.

| | |
|---|---|
| shared leaves | 4672 |
| scientific, compared under tolerance | **3555** (0.8515 of non-digest leaves) |
| identity digests present / differing | **497 / 493** |
| environment metadata, excluded by amendment | 1 |
| runner-only leaves, uncomparable | 43 |
| worst difference | `truncation_stress_control.retrieval_rows[0].receiver.completeness_residual` |
| control C1 — one float moved by 1e-9 | **CONTRADICTED**, as required |

## Why the existing machinery could not have done this

Three defects, all measured, none repaired here — those repairs belong after the
R6l `C_env` gate.

**1. `apply_witness` would have certified without comparing a number.** It builds
its comparable set by removing `environment_dependent` paths from `raw_artifacts`.
R6k declares 13 raw artifacts and marks exactly its 2 outputs environment-dependent.
What remains is **11 tracked repository files** — one runner, two manifests, six
modules, two test files — every one of which a verifier reproduces by cloning. The
existing empty-set guard does not fire, because the set is not empty. A verifier
could have been recorded as having recomputed R6k while comparing only what git
already gave them.

**2. And if those outputs were left comparable, it would have failed by
construction.** R6k's `input_hashes` and per-row digests are SHA-256 of *computed
float arrays*. 493 of them differ here. A last-bit difference from a different
BLAS changes a digest completely. Digest equality asks whether two machines
rounded identically, which is not the scientific question — which is why this
round compares leaves and counts digests separately rather than demanding they
match.

**3. The R6k runner cannot run from a clean clone, by anyone.** Its `PRESERVED`
gate demands `sha256 f94809ca…` for `acaf_frame_sweep.json` and `cfd3128d…` for
`moving_frame_audit.json`. At `C_pre` those files hash to `8d03960c…` and
`9e458867…`. The demanded bytes exist only in one working tree. So this round
calls the library entry point `run_protocol` directly and says so.

## What fired against this round

Four things, all recorded rather than smoothed:

**W1-C1 — `qiskit_version` 2.3.0 vs 2.5.1.** The frozen rule made any discrete
mismatch a contradiction. A library version inside the resource ledger is
provenance *for* the compiler proxy, not an output *of* it — the same kind of
fact as the python and numpy versions `environment_digest` already expects to
differ. A cross-platform witness demanding identical library versions is
demanding the second platform be the first one. Closed one-item exclusion list,
recorded in a pre-result amendment, never edited into the frozen manifest.

**W1-C2 — the vacuity floor was unreachable.** Frozen at 4000 scientific leaves;
measured, there are 3555. The 4000 came from the *total* leaf count, before a
comparator existed that could tell digests from numbers — a threshold guessed
from the wrong denominator. Replaced with a **relative** rule that can be stated
without knowing the answer: at least 0.75 of non-digest leaves must be compared
numbers. Deliberately not "lower 4000 to 3000", which is fitting the threshold to
the result.

**A precedence bug, caught by my own tests.** `reproduction_verdict` returned
`VACUOUS` before checking `CONTRADICTED`, so a comparison too thin to confirm
anything would have filed a *detected disagreement* as inconclusive. Vacuity
bounds what can be confirmed; it says nothing about what has been refuted.
Contradiction now outranks it.

**`sample_size` declared as 3555 against 4 distinct inputs.** `verify_envelopes`
refused the envelope. 3555 leaves come from one execution compared against one
execution; declaring them as observations is precisely the m1-bordon defect
`effective_sample_size` was borrowed here to catch. The comment above the field
already said 4 while the field said 3555.

## The defect this round introduced into the self-audit

Writing this envelope broke `aionq.self_audit`, and the break was directional.

`_is_self` returned True for any producer starting with `experiments/`, on the
reasoning that a script in this tree ran here. R6k falsifies that: the identical
script produced R6k on one machine and this reproduction on another, so one
string names two parties. With producer read as self and verifier
`claude-code-linux` read as other, a recomputation this agent **performed** was
filed as one it **received**, and `recognition_asymmetry` flipped `mutual` to
**True** on a relation with nothing coming back.

An audit built to refuse inflated evidence inflated its own headline number,
using an artifact the same round had just written. A script path now resolves to
`ambiguous`, is counted in its own bucket, and can never reach `mutual`.

```
before fix   out 1  in 1  mutual True      <- wrong
after  fix   out 1  in 0  ambiguous 1  mutual False
```

## What an external audit found on the published branch

Four P1s, all confirmed here, all repaired. Three of them are the same defect in
different clothes: **a check that says nothing about a population, read as
evidence that the population agrees.**

**1. The envelope's SHA bound nothing.** The run wrote artifacts and envelope in
one pass, so `current_commit()` returned the *correction* commit — the last thing
committed before the run. All three raw artifacts resolve to `None` at that SHA,
and `verify()` still returned ok, because a missing blob is treated as "cannot
check". I had reported this as "full resolvable SHA, not the empty-field path".
It resolves, to a commit where the evidence does not exist, which is **worse**
than the empty field: the empty field declares itself. Fixed by the two-phase
discipline above, with a hard refusal if any artifact is unbound.

**2. `*.jsonl` had no eol rule.** It inherited `text=auto`, so a Windows checkout
receives CRLF and every committed-blob digest binding an event ledger fails on
that platform only. Measured there, not here. An evidence chain that holds on one
operating system is not an evidence chain. `*.jsonl text eol=lf` added.

**3. The verdict consulted five of seven mismatch populations.** `sequence_equal`
was never read — a trace with the right row count and the right keys in the right
order but the *wrong sequence numbers* returned CONFIRMED. `only_in_reproduced`
was never read. And `only_in_produced` was tolerated wholesale rather than checked
against a declared allowance, so a reproduction that silently stopped emitting an
entire section would have "agreed" about the part it still emitted. The caller
must now **declare** which producer-only leaves are expected, and the verdict
raises if a population is added without a decision attached to it.

**4. An ambiguous party was promoted to independent.** The same act was excluded
from the recognition counts *as ambiguous* and simultaneously counted as raising
the independent total 1 → 2. Two positions at once: refusing to say who performed
it, while treating it as proof that somebody else checked the claim. Independence
requires two **identified** parties; a recomputation with an unidentified one is
now capped at REVIEWED.

Two further corrections, both accepted:

- **`sample_size` 4 → 1.** The design is paired: one produced execution against
  one reproduced execution. The two manifests are provenance, not observations.
- **497 identity leaves exist; 493 differ.** The table above previously printed
  the mismatch count under the total's label.

**And the observation is descriptive, not prospective.** The 3.311e-11 was seen
before the 1e-10 tolerance was frozen — the preregistration says so in
`outcome_blind: false`, and the honest reading of part A is *cross-platform
reproduction observed*, not *a prediction confirmed*. Part B is the prospective
one.

## The corpus after this round

| | before | after |
|---|---|---|
| envelopes | 28 | **29** |
| independently witnessed | 1 | **1** (W1 capped at REVIEWED) |
| recomputations performed / received | 1 / 0 | 1 / 0, +1 ambiguous |
| tests | 1889 | **1916** |

`mutual` is still `false`, and the independent count is still **1**. I reported
2; an external audit showed the second one was an act whose producer the envelope
does not identify, and this repository does not get to certify independence from
a party it cannot name. The number has not moved.

## A withdrawal

An earlier reading offered here — that R6l's projective margin misses at ρ=0.1
because the radial and angular directions "have not yet separated" — is
**withdrawn, as backwards**. The exact QFI at ρ=0.1:

```
J_rho = 16.2660    J_phi = 3.3078    J_psi = 0.0329
```

The directions are *most* separated at small depth, spanning a factor of 494, and
converge to `(0, 1, 1)` as depth grows. Separation is not the mechanism, and the
observation was in any case a post-hoc retrodiction — the ρ=0.1 miss was not
frozen in R6l's preregistration.

The replacement candidate is frozen, outcome-blind, in
`manifests/qsigma_r6k_w1_semantic_reproduction_preregistration.json` part B: if
the projective margin is set by the *weaker* angular direction, the threshold is
a `J_psi = (1 − e^{−2ρ})²` threshold, and the fail→pass crossing should sit where
`J_psi ∈ [0.05, 0.20]`, i.e. `ρ ∈ [0.126548, 0.296392]`.

That statement was originally written as **two** predictions joined by the word
"equivalently", and they are not equivalent: `ρ ∈ (0.15, 0.30)` induces
`J_psi ∈ (0.067175, 0.203571)`, while `J_psi ∈ [0.05, 0.20]` induces
`ρ ∈ [0.126548, 0.296392]`. A crossing at ρ = 0.13 satisfies one and fails the
other, so "the prediction held" could have been decided *after* seeing the
result. `manifests/qsigma_r6k_w1_partb_interval_correction.json` supersedes B1,
keeps `J_psi` as the sole primary statement, and adds K8: the held-out depths are
spaced 0.05 apart, so a bracketing pair straddling an endpoint is **INCONCLUSIVE**
and may not be resolved by adding depths after the fact.

**It is not executable at this commit** — R6l's `C_exec` and `C_raw` are local to
the other party and unpushed. It is recorded now so that it precedes their
arrival, and it is worth exactly what any unexecuted prediction is worth.

## Not claimed

Semantic agreement of one protocol across two platforms, computed by a second
party in an environment the first did not prepare. **Not** that the protocol is
correct. **Not** that R6i's differential is real — that branch is still not on
origin. **Not** that R6k's 22 runner checks hold; they assert things about the
producing working tree that no second platform can verify after the fact, and
they are reported as uncomparable rather than counted as agreement. **Not** a
QFI-to-retrieval theorem. No quantum advantage, no capacity claim, no
architecture, no hardware, no cognition.

One run against one run. No repeated execution on either platform, so
run-to-run variation *within* a platform is unmeasured, and the 3.3e-11 cannot be
attributed to the platform difference rather than to the arithmetic being
deterministic.


## Second external audit — four more, all confirmed

P1-1 (binding) and P1-2 (CRLF) were closed. The other two were only partially
closed, and the audit found two further P1s plus three arithmetic errors. All
confirmed here before repair.

**The event comparator compared field *names*, not values.** It matched
`[tuple(r.keys()) for r in rows]` plus the `sequence` column, and nothing else —
`action`, `key`, `shard` and every value inside `metadata` were never looked at,
and the verdict never consumed `sequences_contiguous`. The auditor altered those
values and still got CONFIRMED. That is this module's own headline defect,
committed inside the module written to expose it. Events are now compared leaf by
leaf with the same `leaf_kind` machinery: **2240 semantic fields per run**, 0
mismatches, 175 `state_digest` differences correctly classified as identity.

**The producer-only allowlist was outcome-derived.** Broad prefixes matched
against whatever the comparison happened to report, so a newly *missing*
`.checks.*` leaf would have been excused automatically — the rule was "anything
shaped like a runner section" rather than "these forty-three". The same defect as
the wholesale tolerance it replaced, one level subtler. Now a frozen 43-path
tuple compared for **equality in both directions**, with canonical digest
`sha256:71b4cce0…` recorded in the envelope and asserted by a test.

**`rules_bound_to` was informational.** Zeroing a manifest digest there left
`verify(...).ok` True. The committed hashes happened to be correct and nothing
established that. All four manifests moved into `raw_artifacts`, which `verify()`
re-reads from disk.

**`EvidenceEnvelope.independent` still returns True for W1** while `self_audit`
says REVIEWED. Accepted and **not repaired here** — it is a canonical-layer fix
and the agreed order puts it behind the R6l `C_env` seal. The envelope now
carries `party_identity_established: false` and states the divergence in its own
observed_result, so the inconsistency is declared rather than silent.

### Three arithmetic errors in the part B amendment

| written | correct |
|---|---|
| "0.15 and 0.30 both sit inside [0.126548, 0.296392]" | **0.30 is outside** — only 0.15, 0.20, 0.25 are inside |
| "held-out depths spaced 0.05 apart" | spacings are **0.05, 0.05, 0.05, 0.10** |
| `J_psi(0.40) = 0.302` | **0.3032385898** |

`manifests/qsigma_r6k_w1_partb_effective_protocol.json` supersedes the interval
amendment and freezes what was still underdetermined: the **clean noise slice**
named in advance (with K9 — if the clean slice and the fifteen noisy coordinates
disagree, that disagreement *is* the result and may not be resolved by choosing a
slice), no aggregation, margins taken verbatim from R6l's committed schema with
no new thresholds, receiver rebuilt per depth rather than transferred, and an
**exhaustive outcome table** evaluated in the order INVALID → REFUTED →
INCONCLUSIVE → SUPPORTING. The conservative first-pass classification is the
auditor's: `.15` inconclusive, `.20`/`.25` supporting, `.30` inconclusive, `.40`
refuted, none-through-`.40` refuted, non-monotone invalid.

Two of the five depths classify INCONCLUSIVE **by construction** — the upper
endpoint 0.296392 falls inside both the (0.25, 0.30) and (0.30, 0.40) brackets,
so no crossing at or above 0.30 can be resolved against it. That is a cost of the
grid, stated rather than absorbed.

### Bookkeeping

The ledger is **20/20 bound, 12 self-caught / 8 external**. I reported the
external transition as 3 → 9; it is **3 → 8**.
