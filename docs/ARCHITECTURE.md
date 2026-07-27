# AION-Ω^Q / QΣ-R³ᶜ

**An audited almost-all-quantum polycosmic brain.**

> **Revision note (R³).** QΣ-R killed an additive scalar and installed another.
> QΣ-R² built an atlas to replace it — and left three flattenings inside the
> atlas, plus one last monarchic scalar sitting on top of it. A second peer audit
> found all four. They are fixed in §0.6, and one of them **falsifies the
> hyperbolic base this architecture introduced one revision earlier.** Nothing is
> defended that measurement contradicts, including when the measurement is
> against the previous revision's own headline idea.

QΣ∞ asked for an architecture as close to 100% quantum as possible. This revision
does not raise that number. It makes the number *mean* something, reports what it
actually is, and then shows why no single number was ever going to carry the
question.

The single structural change:

> QΣ∞ measured quantumness by counting edges written as unitaries.
> QΣ-R measured it by what a classical simulator can be *shown* to pay.
> QΣ-R² stops measuring it with one number at all.
>
> Under the first definition the architecture is already at 1.00 and always was.
> Under the second it is at 0.088 on random cores. Under the third it is a
> section of a bundle over free theories, and the promotion gate is cognitive
> gain, not hardness.

Every number in this document is computed by `experiments/run_audit.py` and locked
by `tests/test_architecture.py`. None is asserted.

---

## 0. Why the draft could not be graded

QΣ∞ defined quantum causal residency additively:

```
Q_causal = Σ_e w_e · 1[e is realized as a quantum channel, supermap,
                       logical operation or coherent control] / Σ_e w_e
```

Fuzzing 150 random cognitive cores across width 4–12, depth 2–8 and T-density
0.00–0.25 (`experiments/acaf_sweep.py`):

```
Q_naive     : mean 1.0000   min 1.0000   max 1.0000
q_sim_upper : mean 0.0880   min 0.0000   max 0.7423
gap         : mean 0.9175
```

`Q_naive` is not merely optimistic. Its minimum equals its maximum. **It is
constant on all-unitary cores** — every such core scores 1.00, so it cannot rank
two designs, cannot detect a regression, and cannot be optimised against. 63 of
the 150 cores scored a perfect 1.00 while being *exactly* classically simulable.

*Scope of that claim:* this generator emits only H/S/T/CX and no measurements,
resets or classical control, so `Q_naive = 1` is largely guaranteed by the
generator rather than discovered by it. That is still enough to retire the
metric, because scoring unitary-notation cores was its entire purpose.

Two independent ways to reach 1.00 with zero quantum content:

| core | Q_naive | q_sim_upper |
|---|---:|---:|
| classical reversible (CX/CCX/X/SWAP) | 1.0000 | 0.0000 |
| GHZ — maximal entanglement, zero magic | 1.0000 | 0.0000 |
| random Clifford, depth 40 | 1.0000 | 0.0000 |
| Clifford + 35 T | 1.0000 | 0.9992 |
| Hadamard + Toffoli (Grover-shaped) | 1.0000 | 1.0000 |

The first is permutation embedding: classical reversible logic wearing unitary
notation. The second is Gottesman–Knill: arbitrary depth, maximal entanglement,
polynomial simulation.

The cause is not calibration. It is that **quantumness is not additive over edges**.
A sum of locally quantum-looking transitions can be globally classical.

---

## 0.5 What the peer audit corrected

Five defects, all confirmed by inspection or measurement before being fixed.

**D1 — `Q_cert` was a misnomer, and the prose contradicted the code.**
The module docstring correctly called it an upper bound on classical hardness.
The architecture document called it "the fraction of the Hilbert-space exponent a
classical simulator is *forced* to pay" — a lower-bound claim, the opposite
direction. Exhibiting a good simulation strategy bounds cost from *above*;
proving none better exists is a different and much harder problem.
**Fix:** renamed `q_sim_upper`, and the reported object is now an interval
`[q_sim_lower, q_sim_upper]` with `q_sim_lower = 0` and an explicit
`lower_justification` field reading `"none: no lower-bound technology applied"`.
`certified_residency` remains as a deprecated alias that warns.

**D2 — the metric was gameable by syntax.** `H T T† H` is exactly the identity
and scored **0.4568**. Verified before fixing.
**Fix:** a compiler portfolio (optimization levels 0–3) now runs before counting
and the minimum T-count is taken; the per-level breakdown is reported so
compiler-dependence is visible rather than hidden. All three equivalence attacks
in the sweep now score 0.0000. This is *not* a solution to circuit equivalence,
which is intractable in general — it catches what some optimiser in the portfolio
can see, and the residual is declared.

**D3 — `"rccx": 0` was wrong.** Qiskit's `RCCXGate` definition is
`H T CX T† CX T CX T† H` — four T/T† operations. Relative phase reduces T-cost
inside a larger construction; it does not make the isolated gate magic-free.
**Fix:** `"rccx": 4`, with a regression test.

**D4 — kill condition K2 was tautological.** It tested whether the clipped score
lay in `[0,1]`, which the clip itself enforces. It could never fire.
**Fix:** K2 now inspects `raw_exponent`, computed before clipping. Measured range
across the sweep: `[0.000, 0.533]`.

**D5 — `rank(G)` is not "identity capacity".** The Gram construction proves that
`rank(G)` is the dimension of the represented holonomy feature span. Calling it
identity capacity was interpretive overreach: robustness also needs spectral
conditioning, code distance, recoverability, process memory and stability under
*admissible* frame changes.
**Fix:** renamed `holonomy_span_dimension`; added `effective_rank`
(`exp` of the spectral entropy, continuous under noise) and `condition_number`.

Two further claims were **over-broad and are retired**, with counterexamples now
in the test suite:

**D6 — "self-tomography is impossible" is false.** Stabilizer syndrome extraction
reads a protected register, extracts 2 bits about which error occurred, and
leaves the logical state at fidelity **exactly 1.000000** for every error
location. The architecture *depends* on this — a blanket ban on self-measurement
would forbid its own homeostasis. Löb and no-cloning are not weaker and stronger
versions of one theorem; they obstruct different closures. The surviving claim is
bounded: *a single unknown quantum self cannot obtain a complete, non-disturbing
classical description of itself from one specimen.*

**D7 — "magic is the resource that survives frame change" is unqualified.** Magic
is defined relative to a free theory. Under a non-Clifford frame change a
stabilizer state can become a magic state. Replacing entanglement with magic
without naming the free theory just trades one unqualified resource for another.
See §1.

Also corrected: the ACAF generator emits only H/S/T/CX with no measurements,
resets or classical control, so `Q_naive = 1` is largely *guaranteed by the
generator* rather than discovered by it. The honest claim is that `Q_naive` is
constant on all-unitary cores — still enough to retire it, since scoring
unitary-notation cores was its entire purpose.

---

## 0.6 The second audit: flattenings inside the atlas

The R² atlas claimed to be a bundle and then behaved like a vector space. Four
defects, all confirmed against the running code before being fixed.

**D8 — `dominates()` compared different fibers with no transport.** Confirmed:
a section carrying 1.2 bits of *magic* over the stabilizer theory returned
`dominates() == True` against 0.9 bits of *entanglement* over the separable
theory. The monotones measure different things; they were commensurable only
because both are Python floats. That is precisely the flattening the bundle was
introduced to prevent.
**Fix:** `dominates()` now raises `IncomparableFibersError` across base points,
and `transport_to()` returns a typed account —
`(preserved, transformed, lost, remainder, evidence)`. Transporting a stabilizer
section to the separable chart preserves `q_phys, q_process, q_logical, q_sim,
q_audit`, **loses** `q_resource` and `q_causal`, and says why: `q_resource` must
be recomputed as entanglement entropy, and `q_causal` is task- and
control-relative so it does not travel with the base.

**D9 — the top free theory was semantically inverted.** `UNIVERSAL` declared
`free_states="none"`, `free_operations="none"` — and `resource_over` returned
`0.0`. If nothing is free then *almost everything* is a resource. The containment
order also demands this node be the **largest** free set, since free sets grow
upward (stabilizer states are a subset of all states).
**Fix:** renamed `ALL_FREE` with `free_states="all states"`, for which every
monotone correctly vanishes; `MINIMAL_FREE` added as the explicit opposite
orientation so the inversion cannot recur. Measured: GHZ scores **0.0000** over
`all-free` and **0.5000** over `minimal-free`.

**D10 — the hyperbolic base was validated against a tree it does not have.**
`hierarchy_distortion` measures a synthetic *complete binary tree*. The live
free-theory structure is not that: `classical-reversible` sits below three
separate parents, so the Hasse diagram is a **diamond DAG**. Measured on the real
structure (`compare_embeddings_on_real_hierarchy`):

| quantity | value |
|---|---:|
| nodes | 5 |
| diameter | 2.0 |
| Gromov δ | 1.0 |
| **δ / diameter** | **0.5** |
| tree-like | **False** |
| hyperbolic distortion | 5.29 |
| Euclidean distortion | 6.64 |

**δ/diameter = 0.5 is the maximum possible for any metric space.** The live base
is maximally non-tree-like, so hyperbolic embedding is not indicated for it.

> **K13 is falsified on the real base.** The Poincaré base — introduced in R² as
> the answer to "don't flatten to a Euclidean scalar" — does not earn its
> curvature on the structure it actually has to carry. It is retired here and
> kept only as a hypothesis for deeper hierarchies, where it must be re-earned by
> measurement of an actual conversion metric rather than by depth labels.

The 1.02×/2.25× figures in §1 remain correct *about the synthetic tree* and are
now labelled as such. They were never evidence about this architecture's base.

**D11 — `q_causal > 0` was the last monarch.** The atlas escaped one scalar and
left another sovereign over it. Cognitive benefit is not one axis: an organ may
improve generalisation and robustness while worsening latency, energy,
calibration and recovery. Collapsing that to one number picks a weighting in
secret.
**Fix:** `aionq.advantage` replaces the gate with a **pre-registered advantage
cone** over eight outcome dimensions:

```
Promote_τ(O)  iff  Pr( ΔY_τ ∈ K_τ ) ≥ 1 − α
              and  audit ≥ η
              and  compute parity holds
              and  no safety or resource constraint is violated
```

Measured behaviour — five cases, one promotion, four refusals for four *different*
reasons:

| case | Pr(ΔY ∈ K) | verdict | blocker |
|---|---:|---|---|
| genuine relational gain | 0.982 | **PROMOTE** | — |
| same gain, bought with latency | 0.000 | HOLD | effect outside cone |
| gain below pre-registered margin | 0.108 | HOLD | effect size |
| gain without compute parity | 0.976 | HOLD | parity not established |
| gain without external audit | 0.976 | HOLD | audit strength |

**A single `q_causal > 0` would have promoted all five.** Effect size, latency
cost, parity and audit are not tradeable against one another by a weighting
chosen after the fact. The cone must be declared before the experiment; choosing
it afterwards is the same failure as choosing the scalar afterwards.

### D12 — the coordinates were untyped

Fractions, bits, resource monotones, simulation intervals and audit strengths
were stored as bare floats and compared coordinatewise. Nothing prevented
comparing 0.9 bits of process memory against 0.9 of audit strength.
**Fix:** `aionq.stack` types them. `Bits >= Strength` raises; `Monotone` refuses
to exist without a declared free theory; `Monotone(base="stabilizer") >=
Monotone(base="separable")` raises; `Fraction` is range-checked. The illegal
comparison is now a `TypeError`, not a matter of discipline.

### D13 — transport holonomy was never measured

R³ added `transport_to` and never asked whether a section carried around a
*loop* of free theories returns. It does not, and the reason is exact.

Loop: `stabilizer → all-free → separable → classical-reversible → stabilizer`,
carrying a T-state organ.

| mode | start | end | defect | holonomy |
|---|---:|---:|---:|---|
| section-only | 0.415000 | NaN | **∞** | non-trivial (lossy) |
| state-anchored | 0.415037 | 0.415037 | **0.0** | trivial (returns) |

Section-only transport loses `q_resource` and `q_causal` permanently; 5 of 8
coordinates survive. State-anchored transport recomputes the monotone at each
chart and closes exactly, with the profile
`0.4150 → 0.0000 → 0.0000 → 1.0000 → 0.4150`.

The asymmetry has one cause: **a resource monotone is computed *from* a state,
not carried *by* a section.** Discard the state and keep the number, and the
number cannot survive a change of base — there is nothing left to recompute it
from.

> **An organ that keeps only its own summary statistics has a path-dependent
> self-image: what it believes about itself depends on the route it took through
> its own assumptions. Path-independent self-assessment requires retaining the
> state the assessments were computed from.**

That is the architecture's self-reflection result stated as a measurement rather
than a metaphor, and it is the one place where the Gödelian framing earns a
number instead of a gesture.

### D14 — self-review: three fixes that were only half-applied

A review of this repository against its own ledger found three places where a
correction was *documented* as done and only *partly* done. All three are the
same failure: the fix was applied to the code path and not to the claim, or to
the claim and not to the code path.

| # | claimed fixed | actually still present | now |
|---|---|---|---|
| D14a | D1 (`Q_cert` overclaim) | `residency.py` module docstring still read *"Q_cert is the fraction of the Hilbert-space exponent that a classical simulator is **actually forced to pay**"* — the exact lower-bound phrasing D1 retired | rewritten to `q_sim_upper`, upper-bound-only, compiler-dependence stated |
| D14b | D10 (hyperbolic base retired) | `atlas.py` module docstring still asserted *"Its base is hyperbolic, not Euclidean"* with the full justification | rewritten: **no geometry is assigned**; δ/diam = 0.5 recorded; `poincare_distance` retained as instrument, not commitment |
| D14c | D11 (scalar promotion retired) | `advantage.py` was added **in parallel and never wired in**. `QuantumNecessityAtlas.promote()` still ran `q_causal > threshold` — the retired monarch was the live code path | `promote()` now requires a posterior and a cone, delegates to `aionq.advantage.promote`, and returns **HOLD** without one |

D14c was the substantive one: the previous revision announced the scalar gate's
retirement and shipped it still running. `promote()` no longer falls back to a
scalar, because a stored `q_causal` float is an assertion, not an effect measured
against a matched control. Both demonstration organs in §1 now correctly HOLD.

Also fixed: `coherentize.py` claimed coherentization *"does not move Q_cert at
all"*, contradicted by this repository's own measurement of **+0.019**; stale
`Q_cert` naming in `budget.py`, `qrf.py` and `residency.py` note strings; an
`if/else` in `classify_instruction` whose two branches were identical; dead
`_BASIS_LEAVING`, `BasePoint` and `del c, s`; and a README that still claimed
*"the coordinates are still untyped floats"* two commits after they were typed.

### Still not done

- `q_causal` remains unmeasured. The cone is the right *shape* to receive an
  answer; no experiment has produced one.
- The base metric is still a containment graph, not a measured free-conversion
  metric `d(F_i,F_j) = −log sup p_succ`. Until that is measured, no geometry —
  hyperbolic, Euclidean or otherwise — should be assigned to the base.
- The base category is still one axis (resource theory). The full
  `Task × Interface × ResourceTheory × Compiler × Noise × Frame` is not built.
- QΣ-R³B (the four-cell causal organ test) is specified and not run.

---

## 1. The Quantum Necessity Atlas: quantumness is not a scalar

The deepest audit finding is that QΣ-R repeated the original error one level up.
Four inequivalent things were being collapsed onto one axis:

```
classical simulation upper bound
    ≠ certified quantum necessity
    ≠ physical quantum residency
    ≠ cognitive advantage
```

Two organs the scalar orders wrongly, both computed in `experiments/run_audit.py`:

| organ | q_phys | q_logical | q_sim | q_causal | verdict |
|---|---:|---:|---|---:|---|
| Clifford fault-tolerant memory | 1.00 | 1.00 | [0.00, 0.00] | 0.40* | **HOLD** |
| syntactically magic identity circuit | 0.20 | 0.00 | [0.00, 0.68] | 0.00* | **HOLD** |

\* asserted, not measured. Since D14c both correctly HOLD: `promote()` requires a
pre-registered cone and no longer falls back to a stored scalar. The point of the
table is the *coordinates* — a Clifford memory with `q_sim_upper = 0` is not
"zero quantum" — not the verdicts, which were an artifact of the retired gate.

A Clifford FT memory is not "zero quantum". It is genuinely quantum tissue whose
current dynamics happen to admit an efficient classical description. A padded
identity circuit is hard-ish to simulate and does no work. **Neither dominates
the other** — the atlas is a partial order, not a ranking.

The replacement object has eight coordinates and three structural features, each
forced by a specific defect rather than chosen for ornament:

**(a) Interval-valued, not point-valued** — because upper and lower bounds are
different problems (D1).

**(b) A section of a bundle, not a vector.** Resource monotones are defined only
over a named free theory, so `q_resource` is a fiber over a base of free
theories. Measured (`aionq.atlas.resource_over`):

| state | over classical-reversible | over stabilizer | over separable |
|---|---:|---:|---:|
| \|+⟩ | 1.0000 | 0.0000 | — |
| T-state | 1.0000 | 0.4150 | — |
| GHZ₃ | 1.0000 | 0.0000 | 1.0000 |

Same state, different answers. **"How quantum is it" is not a well-posed question
until a base point is named.** Each Reality Cell now carries
`(free_states, free_operations, admissible_group, monotone)`, and resource claims
do not transport outside the admissible group.

**(c) No assigned base geometry** — *this was the hyperbolic base, and it is
retired.* The argument below was made against a **synthetic complete binary
tree**, then tested against the structure the base actually has and failed
(§0.6 D10: Gromov δ/diameter = 0.5 on the live diamond DAG). The table is kept
because it is the evidence that retired the hypothesis, not because the
hypothesis stands. Worst-case distortion against a synthetic tree metric:

| depth | nodes | hyperbolic | euclidean | advantage |
|---:|---:|---:|---:|---:|
| 1 | 3 | 1.00 | 1.00 | 1.00× |
| 2 | 7 | 2.04 | 2.08 | **1.02×** |
| 4 | 31 | 4.67 | 7.55 | 1.62× |
| 6 | 127 | 13.35 | 30.03 | 2.25× |

**Honest reading: the table above measures a synthetic tree, not this base.** On
the real structure the hyperbolic hypothesis is falsified outright (§0.6 D10), and
`base_distance` has been renamed `experimental_poincare_instrument` and made to
emit a warning so the retired geometry cannot be used as a live default. A curved
base that is not earning its curvature is decoration, and decoration is what this
programme is for removing — including when the decoration is its own.

**The promotion gate is a pre-registered advantage cone** over the outcome vector
(§0.6 D11), evaluated against a matched free-theory control. `q_causal > 0` as a
*scalar* gate is retired — it silently chose a weighting and promoted gains bought
entirely with latency. Hardness never promotes on its own either. This is the
bridge from "hard to simulate" to "helps cognition", and it is the coordinate the
architecture still cannot fill in.

---

## 2. One coordinate: the simulation-cost interval

Let `C_sim` be the best known classical cost of simulating the causal core, and `n`
the logical qubits it spans, so dense simulation costs `2^n`. Define

```
Q_cert = log2(C_sim) / n         clipped to [0,1]
```

**`q_sim_upper` is the fraction of the Hilbert-space exponent that the best
simulation strategy implemented here is known to pay.** It is an upper bound on
classical hardness, never a certificate of it. A classical simulator picks the cheapest available strategy, so
`C_sim` is a *minimum* over strategies — basis-permutation, stabilizer, stabilizer
rank. Implemented in `src/aionq/residency.py`:

```
permutation core            →  Q_cert ≈ 0
Clifford core, any depth    →  Q_cert ≈ 0
Clifford + t non-Clifford   →  Q_cert = α·t/n,   α = 0.2284  (Bravyi–Gosset)
generic core                →  Q_cert = 1
```

Three properties the draft metric lacked:

- **Resistant, not non-gameable.** Rewriting a classical process in unitary
  notation moves nothing, and the compiler portfolio defeats the cancellation
  attacks in the sweep. Circuit equivalence is intractable in general, so
  residual gaming vectors exist and the score is compiler-dependent by
  construction.
- **Global.** Computed on the whole core; simulation strategy validity is checked
  across the circuit, not per gate.
- **Falsifiable downward.** A better classical algorithm lowers `C_sim` and therefore
  lowers `Q_cert`. The metric can only ever be revised *down* by classical progress,
  never inflated by notation. That asymmetry is the point.

### 2.1 What 100% actually costs

`Q_cert = α·t/n` inverts to a hardware budget the draft never wrote down:

```
Q_cert ≥ 0.95  requires  t ≥ 4.16 · n  non-Clifford operations per coherent episode
```

For a 200-logical-qubit machine with a 10⁸-operation budget (`aionq.budget.magic_budget`):

| configuration | non-Clifford ops / episode | coherent episodes |
|---|---:|---:|
| 200 logical, Q_cert ≥ 0.95 | 832 | ~120,000 |
| 200 logical, Q_cert ≥ 0.50 | 438 | ~228,000 |
| 12 logical module, Q_cert ≥ 0.95 | 50 | ~2,000 |

So an almost-all-quantum brain on a Starling-class machine gets on the order of
**10⁵ coherent cognitive episodes**, each ~830 distilled magic states. That is the
real meaning of "as close to 100% quantum as possible": not a posture, a magic-state
throughput problem. Both figures are upper bounds — they assume every quoted
operation is spent on distillation.

---

## 3. Corrections to the eight subsystems

### C1 — Coherentization relocates classicality; it does not remove it

The draft's central move — replace measurement-driven classical control with
Stinespring dilation — is sound physics. It is not a residency gain. Audited on a
4-qubit dynamic core with two measure-and-feedforward branches:

```
Q_naive : 0.6364 → 1.0000   (+0.3636)
Q_cert  : 0.1713 → 0.1903   (+0.0190)
ancillas retained : +2
T-count : 3 → 5
```

The certified gain is **5.2% of what the draft metric advertises**, and even that is
purchased by spending *more* non-Clifford resource (controlled-T costs ~3T where bare
T costs 1T), not by acquiring new capability. Coherentization buys **counterfactual
retention**, which is a real and different good — the branch stays available for
interference. It does not buy quantum residency.

This settles the draft's open theorem target "quantum residency monotonicity":
**coherentization is not monotone in any meaningful sense.** Deploy it where
interference between deferred branches is actually used; elsewhere it is a tax.

### C2 — Exhalation is forced, not chosen

The draft motivates breathing by cognitive metaphor. It does not need the metaphor.

1. Coherent control means deferring measurement.
2. Every deferred decision retains its branch record; no-deleting forbids overwrite.
3. A brain with budget `B` and working set `n_data` can defer at most `B − n_data`
   decisions.
4. Reclaiming space without measuring requires uncomputation, priced by Bennett's
   reversible pebble game: `k` pebbles reach `2^k` steps at `3^k` operations.
5. Cognition is not reversible — abstraction discards — so some branches cannot be
   uncomputed at any price and *must* be measured.

Computed schedules (`aionq.budget`):

| configuration | horizon | forced exhale | time overhead |
|---|---:|---:|---:|
| Kookaburra-class, 12 logical / 6 data | 6 | every 20 decisions | 5.77× |
| 100 logical / 40 data | 60 | every 200 decisions | 22.18× |
| Starling 200 / 120, 8-way policy | 26 | every 52 decisions | 1.00× |
| Starling 200 / 120, fully reversible | 26 | never (allocation-bound) | 1.00× |
| 64 / 56, near-reversible | 8 | every 160 decisions | 19.53× |

**The breath period is set by the pebbling budget.** Inhalation past the coherent
horizon does not make the brain more quantum; it makes it unable to allocate. The
draft's `b(t)` vector survives — but `b_boundary` and `b_memory` are now constrained
variables, not free ones.

### C3 — Entanglement is not quantum residency, and is not even frame-invariant

GHZ on 8 qubits: maximal bipartite entanglement **1.0000 bits**, stabilizer Rényi
magic **1.28×10⁻¹⁵**, `Q_cert` **0.0000**.

Worse for its use as an architectural invariant, entanglement is frame-relative.
Under the Z₂ translation frame change `S_{A→B}: |x⟩_B|y⟩_C → |−x⟩_A|y−x⟩_C`
(`aionq.qrf`):

```
entanglement seen from A : 0.0000 bits
entanglement seen from B : 1.0000 bits
```

Same physical situation. So entanglement cannot be a target, a metric, or an
identity invariant. The draft's ACAF axis "entanglement depth" is retired; the
resource that survives frame change is **magic**, and that is what `Q_cert` counts.
Weaving remains valuable — it is how organs couple — but it is not evidence of
quantumness.

### C4 — Hypercomplexity: coherent *and* order-sensitive, verified

The draft's replacement of literal octonionic matrix multiplication by a braided
fusion category is correct, and its coherence requirement is now *evaluated* rather
than stated. Fibonacci category (`aionq.fusion`):

```
pentagon defect  : 1.110e-16
hexagon defect   : 3.140e-16
associator norm  : 1.111786
coherent         : True
order-sensitive  : True
```

Pentagon and hexagon hold to machine precision **while the associator is nonzero**.
Composition order carries information without becoming inconsistent — exactly the
combination literal octonionic matrix algebra cannot deliver, because there
nonassociativity is an error rather than a basis change. Any learned or hand-designed
F/R data proposed for the architecture must pass `verify_coherence()` or be rejected.

The Cayley–Dickson tower is retained strictly as an *observability atlas* (ℂ phase,
ℍ frames, 𝕆 associator patterns, 𝕊 zero-divisor diagnostics), never as a carrier.

### C5 — Identity capacity is rank, not count

The draft posed "prove G is PSD" as a theorem target. It is two lines. Write
`ρ = Σ_k p_k |k⟩⟨k|`; then

```
G_rs = Tr(ρ H_r† H_s) = Σ_k ⟨v_r^k | v_s^k⟩,    v_r^k = √p_k · H_r|k⟩
```

so `G` is the Gram matrix of the family `{v_r}` — Hermitian PSD, with rank equal to
`dim span{v_r}`. Verified: hermitian defect 3.8×10⁻¹⁶, min eigenvalue −4.1×10⁻¹⁶,
frame-change defect 3.0×10⁻¹⁵.

The consequence the draft missed: **5 holonomies supplied, identity capacity 3.**
Duplicated loops add nothing. A brain accumulating a thousand holonomies at
`rank(G) = 3` has three distinguishable identity structures and 997 restatements.
`rank(G)`, not the count of loops, is the identity capacity — and it is the quantity
to maximise under a resource budget.

Frame invariance of `G` under `H_r → U H_r U†`, `ρ → U ρ U†` is what lets identity
survive code deformation and substrate migration. That is checkable, and checked.

### C6 — Process memory: measurable, and often zero

Non-Markovianity as the mutual information `N = I(o₁ : i₁,f)` in the process
tensor's Choi state (`aionq.process`):

| S–E coupling | N (bits) | verdict |
|---:|---:|---|
| 0.000 | 0.000000 | Markovian — Tendril lift buys nothing |
| 0.100 | 0.005516 | memory present |
| 0.500 | 0.252346 | memory present |
| 1.571 | 2.000000 | memory present |

The lift from channels to process tensors is justified **per edge, by measurement**.
An edge at `N = 0` gets a channel; paying process-tensor cost there is waste. This
converts the draft's blanket "Tendrils become process tensors" into a budgeted
decision with a test attached.

### C7 — The quantum Gödel bound: no-cloning is sharper than Löb

The draft places the Anti-Löb membrane outside the core and justifies it logically.
That is the *weaker* argument, and it leaves the impression that a cleverer design
might one day internalise it.

It cannot be internalised, for physical reasons. Estimating an unknown state requires
many identical copies; no-cloning forbids the system from manufacturing them from
itself. Any internal measurement of the identity register disturbs it
(`aionq.selfknowledge`):

| measurement strength | self-knowledge | identity fidelity |
|---:|---:|---:|
| 0.00 | 0.0000 bits | 1.0000 |
| 0.50 | 0.1074 bits | 0.9268 |
| 1.00 | 0.3113 bits | 0.7500 |

A 6-qubit identity register needs **40,960,000 copies** to certify to ε = 0.01.

> **Self-knowledge and self-preservation are complementary.**
> Löb says self-certification is unsound. No-cloning says self-tomography is
> *impossible*.

So the identity signature `J_t` is not a quantity the brain can read off itself. It
is estimable only by an external party, or by a past self that has already paid the
disturbance. The external evidence membrane is therefore not a governance
concession — it is a physical boundary, and it is the correct quantum lift of
Anti-Löb.

### C8 — Indefinite causal order, demoted

Quantum switches are real and experimentally realised, but their established
advantages are narrow (channel discrimination, communication complexity). Nothing in
the draft's cognitive argument requires them. They are demoted from architectural
primitive to **probe with a kill condition**: a causal witness must show a definite-order
mixture cannot reproduce the gain at matched resources. Until that is measured,
superposed causal order is not part of the load-bearing design.

---

## 4. The architecture that survives

```
B = (R, P, W, F, I, M, C, H, E, [R])
```

unchanged in shape from QΣ∞, with the semantics corrected:

| component | QΣ∞ | QΣ-R |
|---|---|---|
| R  Reality Cells | encoded, state-identified | identified by (code, algebra, frame, process); **capacity = rank(G)** |
| P  Tendrils | all lifted to process tensors | lifted **iff** measured `N > 0` |
| W  weave fabric | entanglement as quantumness | coupling mechanism; **not** a residency metric |
| F  fusion grammar | coherence required | coherence **verified**; pentagon/hexagon gated |
| I  identity | holonomy hierarchy | Gram PSD theorem; rank-limited; frame-invariant |
| M  morphogenesis | free code deformation | bounded by magic budget and no-programming |
| C  coherent control | maximise everywhere | deploy where interference is used; else a tax |
| H  homeostasis | breathing as aesthetic | breathing **forced** by Bennett/ancilla accounting |
| E  evidence membrane | external by governance | external by **no-cloning** |
| [R] active remainder | typed | typed, and now includes the classical-simulation frontier |

The governing thesis is unchanged and is strengthened by being priced: the brain
changes the subsystem decomposition, observable algebra, reference frame, code space
and process geometry through which its next local reality becomes operationally
defined. What is new is that each such change now has a cost in magic, ancillas and
episodes, and a test that says whether it bought anything.

### The honest ceiling

QΣ∞ concluded the honest maximum is "nearly 100% internal quantum causality plus an
external witness membrane." That is right in shape and wrong in magnitude. Corrected:

```
Internal causal core   : Q_cert ≤ 1 is attainable in principle, and costs
                         ~4.16 non-Clifford operations per logical qubit
                         per coherent episode.
Coherent horizon       : finite and small; exhalation is forced.
Self-knowledge         : strictly bounded by no-cloning, not by policy.
Evidence promotion     : externally anchored, permanently.
```

"As close to 100% quantum as possible" is therefore a **throughput target under a
magic budget with a forced breath cycle**, not an asymptote to approach by writing
more of the system in unitary notation.

---

## 5. Falsification programme

Kill conditions. Each names the matched control that would retire the component.

| # | claim | kill condition | status |
|---|---|---|---|
| K1 | `Q_cert` corrects a real defect | `Q_naive` and `Q_cert` agree across the sweep | **survived** (mean gap 0.912) |
| K2 | `Q_cert` is sound | any score outside [0,1], or above dense-simulation cost | **survived** |
| K3 | coherentization buys residency | certified gain matches advertised gain | **falsified** (5.2%) |
| K4 | process-tensor lift is needed | matched Markovian model at equal dimension and cost | per-edge, measured |
| K5 | fusion grammar is coherent | pentagon or hexagon defect above tolerance | **survived** (1e-16) |
| K6 | identity is rank-limited | duplicated holonomies raise capacity | **survived** |
| K7 | breathing is forced | a coherent core with unbounded horizon at finite hardware | **survived** |
| K8 | indefinite order helps | randomized definite-order mixture matches at equal resources | **untested — demoted** |
| K9 | entanglement measures quantumness | a frame-invariant entanglement-based residency measure exists | **falsified** (C3) |
| K10 | the metric resists equivalence attacks | an identity circuit scores > 0 | **survived after fix** (was 0.4568, now 0.0000) |
| K11 | the raw exponent is sound | pre-clip exponent negative or non-finite | **survived** (range [0.000, 0.533]) |
| K12 | self-measurement is impossible | a non-disturbing informative self-measurement exists | **falsified** — syndrome extraction, fidelity 1.000000 |
| K13 | the hyperbolic base earns its curvature | Euclidean matches it on the live hierarchy | **FALSIFIED on the real base** — δ/diam = 0.5, maximally non-tree-like |
| K15 | fibers are comparable without transport | a cross-fiber comparison succeeds | **falsified**, now raises |
| K16 | promotion is one-dimensional | one scalar reproduces the cone's five verdicts | **falsified** — 1 promote, 4 distinct refusals |
| K17 | coordinates are commensurable | bits and audit-strength compare without error | **falsified**, now raises |
| K18 | transport holonomy is trivial | section-only loop returns to its start | **falsified** — defect ∞ vs 0.0 state-anchored |
| K19 | the scalar promotion gate is retired | `promote()` still promotes from a stored float | **was live until D14c**; now HOLD without a cone |
| K14 | resource content is base-independent | same state, same monotone, different free theories | **falsified** (§1) |

Two of the draft's own components are falsified by its own stated standards (K3, K9)
and one is demoted for lack of evidence (K8). That is the programme working.

---

## 6. Evidence ledger

> **Lattice updated (R³ᵈ).** This ledger used P/M/H/S/R. The Manifold Research
> Atlas v0.1 uses P/**A**/M/H/S/R, where **A — AXIOMATIZED** marks an artifact
> that passes because a bridge is an axiom or because the check is a *weaker
> surrogate* than the claim. Applying that tier honestly moved five claims out of
> P/M, including the headline metric. The lattice is now enforced in code by
> `aionq.governance`, and the full retagging is in
> [`SOURCES_DIGEST.md`](SOURCES_DIGEST.md).

**A — Axiomatized: passes a surrogate weaker than the claim.**
`q_sim_upper`'s gaming-resistance (a compiler portfolio is not circuit
equivalence); `α_BG = 0.2284` (an asymptotic exponent used at finite t); the
forced breath period (an ad-hoc interpolation, not Bennett's theorem); the
self-tomography copy count (worst-case `d²/ε²`, not rank-dependent truth); and
the section-only holonomy defect of ∞ (an artifact of this module's transport
rule, which nulls base-relative coordinates because no free-conversion map is
implemented). In every case the qualitative result survives and the tier does
not.

**P — mathematically established.** Stinespring dilation; Gottesman–Knill; Bravyi–Gosset
stabilizer rank; stabilizer Rényi entropy as a magic monotone; Bennett reversible
pebbling; no-cloning and no-deleting; state-tomography copy complexity; process
tensors and their Choi representation; Fibonacci F/R symbols and the pentagon/hexagon
equations; Gram-matrix positivity; quantum reference-frame transformations;
no-programming theorem. **Added in Round S3:** no multiplicative character
detects a commutator obstruction (every `L_q` lies in SO(4), whose abelianisation
is trivial); a vertex gauge induces a flat connection **iff** left multiplication
is a homomorphism, which holds exactly through Cayley–Dickson dimension 4; and in
the holonomy-oracle model a cycle obstruction class costs exactly `b = E − V + C`
classical queries against exactly 1 quantum query — bounded by the fact that
*building* the coherent oracle costs `E` classical accesses.

**M — machine-verified in this repository.** Every table above; 22 tests in
`tests/test_architecture.py`; the 150-core ACAF sweep. Qiskit 2.5.1 confirmed to
expose `generate_preset_clifford_t_pass_manager`, `generate_preset_pbc_pass_manager`,
`Store`, and `Stinespring` — the draft's tooling claims check out.

**H — architectural hypotheses, untested.** That `rank(G)` predicts identity
robustness under drift; that maximising `Q_cert` improves any cognitive task at all;
that reality-factorization morphogenesis improves transfer; that fusion-order
sensitivity improves compositional generalisation. **None of these is supported by
evidence here.** This repository shows the architecture can be *measured*, not that
measuring it high makes it *think better*. That gap is the largest one remaining.

**S — generative language.** Reality Cell, breathing cosmos, polycosmic weave,
cognitive gerbe, quantum identity ecology. Retained as scaffolding, load-bearing
nowhere.

**R — retired (Round QΣ-R4).** The governance registry establishes the evidence
status of its claims (it establishes that a hand-authored file agrees with
itself; promotion to P/A/M now requires an `EvidenceEnvelope` that verifies
against the filesystem, so a registry edit is no longer evidence); and
`formal/RecognitionChamber.lean` states P1–P5 (the file was always honestly
labelled uncompiled, but nothing refused to count it — a `ProofEnvelope` with
`build_status != "built"` now is refused, and one that *does* build but rests on
an axiom is flagged, which is the Wall-Sheaf failure mode as a check rather than
as a memory).

**R — retired (Round S7, against an external corrections audit).** The Gödelian
remainder is measured by the norm of a first cohomology class, `[R] = ‖H¹‖`
(retired in *both* regimes: in the continuous Berry setting the obstruction is a
degree-two Chern class and the archive's own simply-connected base forces
`H¹ = 0`; in the discrete graph setting, where the degree is right and where
this repository actually works, rank-nullity forces
`dim H¹ = dim H⁰ + (β₁ − 1)·d`, so `‖H¹‖` is *largest where nothing is wrong* —
measured 12 on a fully flat sheaf against 8 on a fully obstructed one over the
same nerve); and `γ ≠ 0 ⇔ H¹ ≠ 0, by Ambrose–Singer` (retired: Ambrose–Singer
determines the holonomy *Lie algebra*, hence only the identity component, and
mentions no sheaf and no cohomology of the base — a counterexample is exhibited
on this repository's own object, where a nerve has no 2-cells so curvature is
identically zero while holonomy is a generic orthogonal matrix).

**R — retired.** An adaptive aperture reveals structure a static ensemble does
not (Round S4: the static ensemble matches or beats it on four of five held-out
families); Explore-then-verify ordering improves localisation (Round S4: the gate
passes while the method loses to the baseline); The Reversible Recognition
Chamber architecture is already optimal (retired pre-emptively and never
supported); The chamber's per-overlap belief is intrinsic to the sheaf (Round S4:
demoted to a representation-sensitive diagnostic); Hypercomplex coordinates
improve obstruction diagnosis (Round S3:
they *tie* with a dimension-matched real sheaf on their home ground and lose
badly off it); Octonionic fibers give a sheaf-cohomological obstruction theory
(Round S3: ill-posed — above dimension 4 a vertex gauge induces no flat
connection, so the clean sheaf already has holonomy 3.19 on every cycle);
additive `Q_causal`; the name and point-valued form of `Q_cert`;
"self-tomography is impossible"; "magic is the frame-invariant resource";
`rank(G)` as "identity capacity"; exhalation as necessarily measurement;
entanglement as a quantumness measure;
coherentization as a residency gain; breathing as an aesthetic choice; the external
membrane as a governance choice; indefinite causal order as a primitive; identity
capacity as a count of holonomies.

---

## 7. Phased programme

| phase | content | gate |
|---|---|---|
| QΣ-R0 | metric, audit, falsification harness | ✅ superseded |
| QΣ-R0.5 | peer audit fixes; atlas replaces the scalar | ✅ 38/38 tests, 3/3 attacks defeated |
| QΣ-R0.6 | second audit: transport, orientation, real-base geometry, advantage cone | ✅ 48/48 tests |
| QΣ-R0.7 | typed quantities; transport holonomy measured | ✅ 57/57 tests |
| QΣ-R0.8 | self-review: half-applied fixes completed; cone wired into `promote()` | ✅ 59/59 tests |
| QΣ-R1a | adversarial suite: representation, simulator-portfolio, interface attacks | tensor-network / matchgate / low-treewidth families not yet covered |
| Σ∞-S3 | §16 exp. 1: sheaf obstruction localisation, 8 coordinate systems, 300 trials; plus the QΣ query claim | ✅ 128 tests; sheaf clause survives, hypercomplex clause killed, octonionic clause ill-posed |
| S4-G100 | Reversible Recognition Chamber: aperture, ordered roles, nest gate, 10 preregistered gates | ✅ 193 tests; 6/10 gates fail, chamber retired, S3 claim superseded as basis-dependent |
| S5 | moving-frame orbit audit; basis-free Laplacian instrument | ✅ 208 tests; exactly orbit-collapsed AND strongest (0.964 vs 0.776) |
| S6 | ACAF adversarial sweep: 950 instances, 4 families; falsified a P-tagged claim and fixed the instrument | ✅ 211 tests; invariance 950/950 after fix, accuracy scoped by topology |
| QΣ-R4 | Witnessed Reproducibility Membrane: fail-closed portfolio, evidence envelopes, portable RSS, cross-platform CI | ✅ 242 tests on **Linux only**; 20/20 attacks behave as specified; **48 of 81** prior claims carry no envelope |
| S7 | adjudicating an external corrections audit of the source archive: its checkable claims re-run here, its central verdict sharpened | ✅ 222 tests; 3/3 replications exact, `[R] = ‖H¹‖` retired in **both** regimes |
| QΣ-R3A | measured free-conversion metric; re-test base geometry against it | not started |
| QΣ-R3B | four-cell causal organ (self/other/memory/auditor), ΔY with uncertainty | specified, not run |
| QΣ-R1 | four-cell organ (self/other/memory/auditor) at measured `Q_cert` | `Q_cert > 0.5` on hardware-sized cores |
| QΣ-R2 | per-edge process-tensor budgeting from measured `N` | beats matched Markovian control |
| QΣ-R3 | fusion cortex with gated F/R data | coherence gate + order-sensitivity gain |
| QΣ-R4 | breathing tissue under measured pebbling budget | horizon matches predicted schedule |
| QΣ-R5 | multi-frame ecology, frame-covariant identity | `rank(G)` preserved across frame change |
| QΣ-R6 | modular polycosmos over logical links | identity survives module migration |

QΣ-R1 onward requires logical qubits that do not currently exist at the needed scale.
Roadmap statements about Kookaburra and Starling are goals, not delivered capability,
and nothing here should be read as assuming otherwise.

---

## 8. The remainder

`[R]` is non-empty and three parts of it are load-bearing:

1. **The classical frontier is not closed.** `Q_cert` is an upper bound built from the
   simulation strategies implemented here. A better classical algorithm lowers every
   number in this document. This is a feature: the metric is exposed to refutation
   from outside.
2. **Measured-high does not mean thinks-better.** Nothing here connects `Q_cert` to
   any cognitive performance. The architecture is now auditable; it is not yet
   justified.
3. **The self cannot close.** By C7 this is not a temporary limitation but a physical
   one. The brain's identity signature is estimable only from outside it. The
   architecture is complete only as a two-party object — core plus external witness —
   and no version of it will ever be complete alone.

Point 3 is the same remainder the draft named Gödelian, now with a sharper reason and
a copy count attached.
