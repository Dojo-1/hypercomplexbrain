# Review of the wider architecture corpus

Four repositories from the same account, read against this repository's own
standard: what is defined, what is argued, what is measured, what is merely
suggested. Public repos only — the private ones are unread and are listed as
such at the end.

The cross-cutting finding first, because it is the useful one: **no single repo
has the whole discipline, and between them they have all of it.**

| repo | has | lacks |
|---|---|---|
| λSAT | claims tiered P/M/S, explicit NOT-claimed list, **DRAT external certification** | kill conditions; nothing is pre-committed to die |
| connection_laplacian_lean | a real compiled artifact, sorry-free, axiom-free | (unverified beyond its README) |
| IGBundle-LLM | running code, geometric metrics, a released model | the benchmark that would detect its own claim |
| Trasgo | a working codec, cross-scale results table | a discrimination measure for its central signal |
| **hypercomplexbrain** | kill conditions, 26 retirements, supersession | **an external witness — which λSAT already has** |

---

## 1. λSAT — the most disciplined repo in the account

`PUBLIC_RESEARCH_CLAIMS.md` is a three-tier registry — PROVEN / MEASURED /
SPECULATIVE — with an explicit **"NOT claimed"** section that names P vs NP,
general SAT algorithms, and universal superiority over CDCL. It states the
scope of its own advantage without being asked:

> "The frames win on **structured** instances ... and are correctly silent on
> structureless critical instances, where CDCL is irreplaceable."

That is the sentence most research repositories cannot write.

### The thing worth borrowing, and I should have borrowed it

λSAT verifies its own verdicts: **model replay for SAT, DRAT proofs for UNSAT.**
A DRAT proof is checked by `drat-trim` — a separate tool, written by other
people, that recomputes rather than agrees.

That is precisely `VerificationMode.RECOMPUTED` from Round R4-D: producer ≠
verifier, and the verifier performs a second computation that can disagree. I
built that machinery from scratch today and reported that this repository had
**zero** instances of it. λSAT has had a working one the whole time.

It also states its own degradation honestly:

> "Without them, the frame verdicts remain sound on their own, but the
> CDCL-fallback certification degrades to best-effort"

A named trusted-computing-base dependency. That belongs in this repo's envelope
schema and is not currently there.

### Two things to push back on

**The headline number is measured on a benchmark built to suit it.**

> "middleware 40/40 · PAR-2 0.06 s · 40/40 certified, vs Kissat 35/40 (5.36 s)"

n = 40, on a "counting-and-parity-inclusive mix (not the competition set)" —
i.e. a mix selected to contain exactly the structure the frames target. The repo
*says so*, which is the important part. But a ~90× PAR-2 ratio will be quoted
without the qualifier by anyone who reads it quickly, and the qualifier is the
whole claim.

The cleaner result is one row lower and gets less emphasis:

> "26/40 decided by a sound frame with no solver"

That is a *structural* statement — 65% of that mix is decidable without search —
and it does not depend on a timing comparison at all. It is the stronger claim
and it should be the headline.

**No kill conditions.** The registry can correct a claim but nothing is
pre-committed to die. This repository has 26 R-tagged retirements precisely
because it wrote the conditions before the results. λSAT's implicit rule —
"every candidate hardness invariant must survive an input→invariant→action→
benchmark contract" — is close, but a contract that disqualifies without
declaring is not a retirement, and the record of what was believed and when is
what supersession preserves.

---

## 2. connection_laplacian_lean — the one artifact this repo needs

README reports 14 formalised modules, Lean 4.11.0 pinned, `lakefile.lean` +
`lake-manifest.json` + CI, **sorry-free and free of user-introduced axioms** in
the verified spine. Theorems on ℤ/2 connection-Laplacian kernel-dimension theory
on finite graphs.

That is the same object as the Theorem verified numerically in this session —
`ker L_U ≅ Fix(Hol)`, checked at 0/0, 2/2, 2/2 for generic SU(2), scalar stub
and pure gauge. A formal version already exists.

It is also the only candidate in the account for a `ProofEnvelope` with
`build_status: "built"`. R4-D built that check and it has **never had an
instance**; every P-tag here rests on prose or numerics.

**Unverified.** I read the README, not the file tree. UTAI's README claimed
Lean 4.11.0 with zero `.lean` files, which is exactly why the check exists. A
real envelope needs the build, the axiom inventory and an artifact digest.

---

## 3. IGBundle-LLM — the instrument that would detect its own claim is missing

Real code, 140 commits, a released model, running eval pipelines. The geometric
metrics are computed rather than asserted, which is more than most.

**The number that should stop a reader:**

> Curvature: **−5.63** (target: **−1.0**)

reported alongside "6/6 geometric verification tests pass". A 5.6× miss on the
defining parameter of the construction, passing its own test. Either the test
checks the *sign* rather than the value — in which case it is nearly
tautological, since any hyperbolic-ish embedding is negative — or the target is
not the target. This is the same shape as the failure caught here twice today:
a test that passes while the measurement disagrees.

**The claim and the benchmark do not meet.** The adapter targets "hierarchical
and abstract reasoning". The reported benchmarks are ARC-Challenge 54.86%
("identical to base Qwen 2.5-7B"), TruthfulQA, Winogrande, GSM8K — reported as
*preserved*, not improved. There is no MATH, no dedicated logic task, no
ablation of the Geometric Steering Probe. So the one instrument that could
detect the claimed effect is the one not run, and parity on unrelated benchmarks
is being offered where a reasoning delta is claimed.

**−15% speed per step, −30% convergence steps** are asserted, not measured, and
they point in opposite directions. The net — total wall-clock to a fixed loss —
is the only figure that matters and is the one not given.

To its credit: *"IGBundle is an active research project. Results are
preliminary."*

---

## 4. Trasgo — a real system whose central signal has no discrimination measure

A working context-compression codec (§1) with a CLI, formal T8 tests over
lambda calculus, recursion and Church arithmetic, and a cross-scale results
table from 4B to 671B.

**The central claim is testable and is not tested.** Trasgo asserts that the
certainty metric *drops* when the model detects variable-capture risk,
triggering correction. That is a detector, and a detector without a
false-positive rate is unfalsifiable: a signal that drops on capture risk is
only useful if it does **not** also drop on the many cases with no risk.

The measurement is one AUROC away — score capture-risk and non-risk
substitutions, and report discrimination. This repository has that function and
it is the same one used since Round S3. Without it, "autonomous self-correction"
is a description of an event, not evidence of a mechanism.

Also asserted without data: "lossless dimensional factoring" (losslessness is
checkable by round-trip and should be a test, not an adjective), the "sharp
scale threshold" (a table with unclear methodology), and FM3 depth-collapse
onset.

---

## What I would move between them

1. **λSAT → here.** The DRAT pattern. An envelope should be able to name an
   *external checker* and record its verdict, and should record TCB
   dependencies. R4-D's `ProofEnvelope` has `axiom_inventory` but no
   `external_checker` field, and it should.
2. **Here → λSAT.** Kill conditions and supersession. Its registry is one field
   short of this repository's lattice, and the missing field is the one that
   makes a claim falsifiable rather than merely revisable.
3. **Here → IGBundle and Trasgo.** `aionq.sheaf.auroc` and the matched-control
   discipline. Both have a claimed detector and neither reports discrimination
   against a null.
4. **connection_laplacian_lean → here.** The first real `ProofEnvelope`, if the
   build verifies.

## Not read

Private and unreviewed: `nnn-hyperbolic-ramdisk_v2` (the (2,2) split-signature
reservoir, directly relevant to the unimplemented half of Round S8),
`hypercomplex-math-thesis`, `manifold`, `Topos-Trasgo`, `braintop`, `METACOG`,
`TELOS`, `Geodesic-Resonance-Descent`, `LLM-in-concave-manifolds`,
`np-completeness-bunny-utai-study`, `-SAT_Research_Canary`, `-lang.s1`.
Public and unread: `QuantumNNSNR`, `aigit`.

Everything above is read from README and claims files, not from source or
execution. That is one tier below what this repository asks of itself, and the
review is tagged accordingly: **M-reported, not recomputed.**
