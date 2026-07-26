# S4-G100 — recursive research audit

## 1. Exact frozen claim

> A controlled aperture plus ordered exploratory/verification operations reveals
> useful hidden structure beyond deterministic, static-ensemble and
> equal-entropy stochastic controls, while preserving round-trip and gauge
> stability under matched resource budgets.

Frozen at `manifests/s4_g100_preregistration.json`, commit `611e4ee`. Evidence
floor **H**.

## 2. Scope and forbidden promotions

Forbidden and not attempted: AGI, consciousness, quantum advantage, asymptotic
advantage, hypercomplex superiority, octonionic flat sheaves, weighted scalar
promotion, optimality. Baseline freeze at `artifacts/s4_g100/summaries/baseline_freeze.json`
(HEAD `745e480`, clean tree, 128/128 passing, 48 claims).

## 3. Claim → artifact map

| claim | artifact | test |
|---|---|---|
| `DEF-S4-LOOP_DEFECT` | `loop_tomography.py::loop_defect` | `test_property_loop_defect_is_nonnegative` |
| `MATH-S4-LOOP_ZERO` | same | `test_exact_permutation_inverse_has_zero_loop_defect` |
| `MATH-S4-GAUGE_INVARIANCE` | `gauge_conjugate` | `test_isometric_coordinate_change_preserves_the_loop_defect` |
| `MODEL-S4-BORDON_CEILING` | `budget.py::depletion_time` | `test_invariant_draw_above_refill_depletes_in_finite_time` |
| `MATH-S4-NO_SELF_PROMOTION` | `nest.py::nest_decision` | `test_a_claim_cannot_promote_itself` |
| `EXP-S4-CHAMBER_KILLED` | `run_s4_g100.py` | `artifacts/s4_g100/raw/*.json` |
| `EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT` | `run_s4_basis_attack.py` | `s4_basis_attack.json` |

## 4. Intended specification vs 5. actual live code path

Three divergences were found; all three are in the code, not only here.

1. **Intended**: the explorer proposes from the verifier's belief.
   **Actual, first version**: it did, with no floor, making zero absorbing — the
   run collapsed to AUROC 0.250, *below chance*, with all true defects at
   probability exactly 0. **Now**: a declared exploration floor, counted as a
   parameter. The asymmetry (C4/C5 carry 6 params, C2/C3 carry 5) is reported in
   the preregistration and in the results.
2. **Intended**: the verifier scores how well a candidate explains the
   obstruction. **Actual, first version**: a set cover, under which any small set
   meeting every basis cycle scored perfectly — under-identifying, and it
   discarded the fact that a *low-mass* cycle exonerates its overlaps.
   **Now**: non-negative least squares.
3. **Intended**: equal compute. **Actual, first version**: the order-defect probe
   was charged to the method's budget, handicapping exactly the two conditions
   under test. **Now**: a separate instrument ledger.

Divergences 1 and 2 were found before preregistration. Divergence 3 was found
while wiring parity and is the reason the parity section names the instrument
cost separately.

## 6. What each test actually establishes

- **Analytic known-answer** (8 tests): the expected value is fixed by
  mathematics, not by the implementation. These are the only tests here that
  escape author correlation.
- **Structural** (10): the manifest validator is not a rubber stamp — 14
  parametrised mutations, all caught.
- **Metamorphic** (5): one asserts a **failure** (relabel non-invariance) so that
  a later change which accidentally fixes it cannot pass silently.
- **Property-based** (6): hand-rolled with fixed seeds. `hypothesis` is absent;
  these are randomised checks and are **not** a shrinking fuzzer.
- **Historical regression** (6): S3 negatives cannot be revived.

**These tests are correlated evidence.** They were authored from the same
narrative as the code. They establish that the implementation does what its
author believed; they do not establish that the belief was right.

## 7. Raw metrics and units

AUROC (rank statistic, ties averaged, computed on **raw** scores). Brier
(normalised scores; the map is rank-preserving so it cannot change AUROC).
Loop defect (Frobenius / Hamming / Euclidean, carrier named, raw before
clipping). Wall seconds (`perf_counter`), peak KiB (`tracemalloc`), max RSS
(`getrusage`) — `psutil` absent. Per-seed values in `artifacts/s4_g100/raw/`.

## 8–9. Matched baselines and parity

C0 deterministic, C1 equal-entropy perturbation, C2 static ensemble, C3 adaptive
unordered, C5 reversed flow, C7 matched-spectrum surrogates, plus a matched
random-walk aperture controller and shuffled role labels. 256 candidate
evaluations for every chamber condition; identical nerve, cycle basis and
transitions; zero tuning budget on held-out data. **Parity fails and is reported
as a failure**: 194× wall, 86× memory.

## 10. Representation attacks

Ten required, ten run. Orthogonal gauge: **exactly 0.000** on both arms. Vertex
relabel: chamber 0.285, baseline 0.200. Alternate cycle basis: 0.210 / 0.086.
Canonicalisation: 0.193 / 0.102. Edge permutation: 0.093 / 0.085. Exact loops:
0.0. Equivalent encodings: 0.0. Shuffled role labels: no change to any number.
Matched surrogates: no separation from structured fields.

**The chamber's belief is demoted to a representation-sensitive diagnostic**
(`RET-S4-CHAMBER_INVARIANT`), and so is the absolute AUROC of the S3 instrument.

## 11. Independent-witness status: **CORRELATED**

Explorer, verifier, formalizer and auditor share **code, assumptions, data and
authoring model** — all four axes. `independent_witness_status` returns this from
the role table rather than letting a document assert independence, and the
deposit gate caps every S4 deposit at MeasuredPattern because of it. Nothing in
this round is independently verified.

## 12. Requirement → result round-trip

| edge | preserved | transformed | lost | remainder |
|---|---|---|---|---|
| requirement → mathematical object | "hidden structure", "matched budgets" | prose → sheaf localisation on a nerve | *which* structure, and "useful" for what | **semantic**: usefulness is never defined |
| object → representation | cycle obstruction masses | O(4) transitions → real masses | the coboundary component | **cohomology**: `F_2^E` mod the cut space |
| representation → implementation | additive fit model | masses → NNLS on a candidate support | co-occurrence, once projected to a per-overlap belief | **empirical**: fit residual |
| implementation → test | contracts (count, bounds, nonnegativity) | code → assertions | everything the author did not think to assert | **semantic**: author-correlated coverage |
| test → measurement | seeds, budgets | assertions → AUROC/Brier/defect | per-instance structure, once pooled | **empirical**: pooled variance |
| measurement → interpretation | gate outcomes | numbers → PASS/FAIL | margins, once a tag is issued | **semantic**: what the tag omits |
| **interpretation → original requirement** | the negative answer | "6/10 gates fail" → "aperture and ordering do not reveal structure **on this host**" | any statement about other hosts | **semantic: "useful hidden structure" was never operationalised beyond AUROC on one synthetic task** |

**The round trip does not close.** The final remainder is the same one the first
edge introduced: *useful* was never defined independently of the metric chosen to
measure it. A negative result on AUROC is not a negative result on usefulness,
and this round cannot distinguish them. That is the largest gap here — larger
than any individual gate failure.

## 13. Corrections and retirements

Four retirements (`RET-S4-FERTILE_APERTURE`, `RET-S4-ORDERED_FLOW`,
`RET-S4-OPTIMAL_COGNITION`, `RET-S4-CHAMBER_INVARIANT`) and one **supersession of
a prior round's claim** (`EXP-S3-SHEAF_LOCALISATION` →
`EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT`), with the original text preserved.

## 14. Strongest surviving result

That the **dominance region caught what a weighted score would have passed**. The
ordered-flow gate passes at +0.033 while the method is 0.033 *below* the baseline
it exists to improve. Any aggregate containing that component could have carried
the round on a measurement of the chamber against itself.
`RET-R3-SCALAR_PROMOTION` retired that failure mode in an earlier round; this is
the first time the replacement has demonstrably earned its place.

## 15. Most damaging obstruction

**The host is not representation-invariant, and neither instrument was checked
for it before.** A fundamental cycle basis is an arbitrary spanning tree. Both
the chamber (0.285) and the S3 baseline (0.200) move under relabelling; the S3
headline effect retains only 20% of its magnitude. Every localisation number this
repository has reported on this host is a **basis-relative** quantity. The
direction survives; the effect sizes do not transport.

This was invisible to Round S3 because that comparison ran entirely inside one
basis — the same mechanism as every prior defect in this repository: *the correct
shape, with the old comparison still inside it.*

## 16. One bounded next experiment

**Make the localisation instrument basis-invariant, then re-measure S3.**

Replace the fundamental-cycle-basis blame-spreading with a quantity defined on
the full cycle space rather than an arbitrary basis — the natural candidate is a
sheaf-Laplacian effective-resistance weighting, which is a spectral invariant and
cannot depend on which spanning tree was grown. Preregister: the corrected
instrument's AUROC must be invariant under relabelling to within 0.01, and its
contrast against shuffled/graph controls must be re-measured from scratch.

Kill condition: if the basis-invariant instrument's contrast is not significantly
positive, `EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT` retires entirely and Round
S3's surviving clause goes with it.

Nothing else — no new fauna, no higher Cayley–Dickson levels, no physical quantum
claims, no morphogenesis, no visualisation. **The stop condition remains active.**
