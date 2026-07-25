# AION-Ω^Q / QΣ-R

**An audited almost-all-quantum polycosmic brain.**

QΣ∞ asked for an architecture as close to 100% quantum as possible. This revision
does not raise that number. It makes the number *mean* something, and then reports
what it actually is.

The single structural change:

> QΣ∞ measured quantumness by counting edges written as unitaries.
> QΣ-R measures it by what a classical simulator is forced to pay.
>
> Under the first definition the architecture is already at 1.00 and always was.
> Under the second it is at 0.088 on random cores, and the gap is the design work.

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
Q_naive : mean 1.0000   min 1.0000   max 1.0000
Q_cert  : mean 0.0880   min 0.0000   max 0.7423
gap     : mean 0.9120
```

`Q_naive` is not merely optimistic. Its minimum equals its maximum. **It is a
constant function of the architecture** — every core built out of unitaries scores
1.00, so it cannot rank two designs, cannot detect a regression, and cannot be
optimised against. 63 of the 150 cores scored a perfect 1.00 while being *exactly*
classically simulable.

Two independent ways to reach 1.00 with zero quantum content:

| core | Q_naive | Q_cert |
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

## 1. The corrected primitive: certified residency

Let `C_sim` be the best known classical cost of simulating the causal core, and `n`
the logical qubits it spans, so dense simulation costs `2^n`. Define

```
Q_cert = log2(C_sim) / n         clipped to [0,1]
```

**Q_cert is the fraction of the Hilbert-space exponent a classical simulator is
forced to pay.** A classical simulator picks the cheapest available strategy, so
`C_sim` is a *minimum* over strategies — basis-permutation, stabilizer, stabilizer
rank. Implemented in `src/aionq/residency.py`:

```
permutation core            →  Q_cert ≈ 0
Clifford core, any depth    →  Q_cert ≈ 0
Clifford + t non-Clifford   →  Q_cert = α·t/n,   α = 0.2284  (Bravyi–Gosset)
generic core                →  Q_cert = 1
```

Three properties the draft metric lacked:

- **Non-gameable.** Rewriting a classical process in unitary notation moves nothing.
- **Global.** Computed on the whole core; simulation strategy validity is checked
  across the circuit, not per gate.
- **Falsifiable downward.** A better classical algorithm lowers `C_sim` and therefore
  lowers `Q_cert`. The metric can only ever be revised *down* by classical progress,
  never inflated by notation. That asymmetry is the point.

### 1.1 What 100% actually costs

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

## 2. Corrections to the eight subsystems

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

## 3. The architecture that survives

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

## 4. Falsification programme

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

Two of the draft's own components are falsified by its own stated standards (K3, K9)
and one is demoted for lack of evidence (K8). That is the programme working.

---

## 5. Evidence ledger

**P — mathematically established.** Stinespring dilation; Gottesman–Knill; Bravyi–Gosset
stabilizer rank; stabilizer Rényi entropy as a magic monotone; Bennett reversible
pebbling; no-cloning and no-deleting; state-tomography copy complexity; process
tensors and their Choi representation; Fibonacci F/R symbols and the pentagon/hexagon
equations; Gram-matrix positivity; quantum reference-frame transformations;
no-programming theorem.

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

**R — retired.** Additive `Q_causal`; entanglement as a quantumness measure;
coherentization as a residency gain; breathing as an aesthetic choice; the external
membrane as a governance choice; indefinite causal order as a primitive; identity
capacity as a count of holonomies.

---

## 6. Phased programme

| phase | content | gate |
|---|---|---|
| QΣ-R0 | this repository: metric, audit, falsification harness | ✅ 22/22 tests |
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

## 7. The remainder

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
