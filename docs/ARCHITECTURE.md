# AION-Ω^Q / QΣ-R³ᶜ

**An audited almost-all-quantum polycosmic brain.**

> **HB0 universal-base reinstatement.** The K13 measurement below remains
> correct and remains historical evidence: the five-node free-theory
> \(K_{2,3}\) graph does not earn curvature from tree-likeness. Its former
> conclusion was too broad. This revision declares a conditioned Poincaré
> \(H^n\) atlas as the repository-wide base under
> `AXIOM-HB0-UNIVERSAL_POINCARE_BASE`. `FreeTheory` is a categorical fiber/index,
> local metrics remain heterogeneous, and a tangent-matched Euclidean base
> control remains mandatory. The new A-tag is a design contract, not a
> retroactive positive K13 result. Its structural surrogate is test-covered and
> promoted through a hashed working-tree envelope; that envelope is unsigned,
> self-recomputed, and neither commit-bound nor independently witnessed.

> **Revision note (R³).** QΣ-R killed an additive scalar and installed another.
> QΣ-R² built an atlas to replace it — and left three flattenings inside the
> atlas, plus one last monarchic scalar sitting on top of it. A second peer audit
> found all four. They are fixed in §0.6; historically, D10 then overgeneralized
> a failed tree-likeness warrant into retirement of every hyperbolic base. The
> HB0 axiom above supersedes that policy without rewriting the K13 measurement.

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
q_sim_upper : mean 0.0825   min 0.0000   max 0.5329
gap         : mean 0.9175
```

> **Correction (QΣ-R1a).** This block read `mean 0.0880  max 0.7423` while the
> `gap` beside it read `0.9175`. Those cannot both hold: `gap = Q_naive −
> q_sim_upper` and `Q_naive` is identically 1.00, so a gap of 0.9175 *is* a mean
> of 0.0825. The document was carrying two numbers from two different runs and
> asserting both. The figures above are the current measurement; the `gap` was
> the one that was right. Re-measured on the same seed with the contraction
> strategy disabled and enabled, these numbers are **identical** — the drift
> predates it and 0 of the 150 cores move. Nothing on this page is safe merely
> because the page says every number in it is computed.

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

### 0.1 The replacement inherited the defect

`Q_naive` was retired for scoring 1.00 on cores that were exactly classically
simulable. `q_sim_upper` was built to fix that by pricing what a simulator
pays — and it does, for the two failure modes above. But it prices magic
*wherever it sits* and never asks what the magic is connected to. So:

| core (n = 12) | width | two strategies | four strategies |
|---|---:|---:|---:|
| product of single-qubit chains (H,T alternating, **no 2-qubit gate at all**) | 1 | **1.0000** | 0.1667 |
| shallow 1D local, full T-density | 3 | 0.4568 | 0.3333 |
| k disconnected 2-qubit blocks | 3 | 0.2284 | 0.2284 |
| free-fermion, T-saturated (T-count 6286) | 14 | **1.0000** | **0.0000** |
| free-fermion + **one** SWAP (control) | 14 | 1.0000 | 1.0000 |
| all-to-all magic (control: genuinely hard) | 28 | 0.6852 | 0.6852 |

The first row is `Q_naive`'s defect wearing a different coat. A circuit of *n
independent single-qubit chains* is a product state at every step and is
simulable in linear time — and the two-strategy portfolio called it **1.00,
maximally quantum**. Worse, `tests/test_architecture.py` contained a test
asserting exactly that saturation, so the suite pinned the wrong answer as
correct. The witness circuit in `test_residency_scales_with_t_count` had no
entangling gate; it now carries a CX ladder, and the product case is a separate
test that fails if the metric ever calls it quantum again.

The missing strategy was structural. §2's portfolio was a minimum over
*compilations*, all priced by the same stabilizer-rank model — not a minimum
over *strategies*. `aionq.contraction` adds tensor-network contraction in a
constructed elimination ordering at cost `2^(width+1)`, so a core is charged for
how its magic is **connected**, not merely for how much of it there is. The
control row is the point: all-to-all magic has width 28 at n = 12 and is not
made one bit cheaper.

### 0.2 The free-fermion row is the one that should worry you

The fourth row is worse than the first, and it is the reason this section exists
rather than a changelog entry.

`T = diag(1, e^{iπ/4})` is a **Z-rotation**, and `Z_k = −i c_{2k−1} c_{2k}` is
quadratic in Majorana modes. So T is a perfectly good free-fermion operation,
and a nearest-neighbour matchgate circuit can be *saturated* with magic and
remain exactly solvable in polynomial time. The measured core carries **T-count
6286** and **contraction width 14** on 12 qubits. Stabilizer rank sees only the
magic. Contraction sees only the width. Basis permutation needs the core never
to leave the computational basis, which it does immediately. All three agree the
core is maximally hard — `q_sim_upper = 1.0000`, *"no implemented strategy
simulates this core below dense cost"* — and all three are wrong, because
free-fermion structure is invisible to every one of them.

Stabilizer rank can therefore be driven **arbitrarily** wrong on this family by
adding magic that costs the real simulator nothing. That is not a loose bound;
it is a bound with no relationship to the quantity it estimates.

The control row is what makes the strategy trustworthy rather than merely
generous. Matchgates on next-nearest neighbours — equivalently, matchgates plus
SWAP — are **universal for quantum computation**. One SWAP appended to the same
core takes it from 0.0000 back to 1.0000, at identical contraction width.
`aionq.matchgate` therefore refuses far more than the theorem requires: gates
must be on adjacent indices in the circuit's own ordering with no routing
allowed; two-qubit gates must have the parity-block form `G(A,B)` with
`det A = det B` (which is exactly what rejects SWAP at `det A = +1, det B = −1`,
CZ at `−1, +1`, and RZZ, whose generator is quartic in Majoranas); and
one-qubit gates must be **diagonal**, so H and X are refused outright rather
than reasoned about through their Jordan–Wigner strings. A matchgate circuit
written with Hadamards is missed and charged by another strategy — a weaker
bound, never a wrong one.

### 0.3 Limits of this round

This changes **0 of the 150** random cores in the sweep above — that generator's
T-density is low enough that stabilizer rank always wins, and it emits no
matchgates at all. Both structural strategies are exercised by the K4 family
table, not by the random fuzz. Everything above rests on **constructed**
families chosen because they exhibit the defect; that is legitimate adversarial
method and it is not a random sample, so no claim is made about how often real
cognitive cores land in these regimes.

The QΣ-R1a gate's three named families are now covered. **The lesson is not that
the list is finished.** Each of the three was a case where the portfolio was not
loosely wrong but unrelated to the truth, and the list was written by the same
people who wrote the portfolio. What the fourth strategy proves is that the
third one's coverage claim was worth exactly as much as the second's.

### 0.35 Moving-frame review: `q_sim_upper` sees the wire names

S5 built the instrument for this and S4 is why it exists — the round that
retired a headline claim as **basis-dependent**. `aionq.movingframe` states the
distinction: a measurement is *orbit-collapsed* when it is constant on the frame
orbit and sees the object, *orbit-resolving* when it varies and is reporting
frame coordinates. An orbit-resolving measurement "is not therefore wrong. It is
**mistyped**."

For circuits the frame is the **qubit labelling** and the group is `S_n` acting
by relabelling. Nothing physical moves: the same gates act on the same wires,
only the names change. Measured on a 10-qubit free-fermion core:

| frame | `q_sim_upper` | bounding |
|---|---:|---|
| identity | **0.0000** | free_fermion |
| swap the names of wires 0 and 1 | **0.9000** | contraction |
| reversal | **0.0000** | free_fermion |

**Orbit spread 0.9 on a scale of [0, 1], from renaming two wires.** Classifying
each strategy separately, with loop closure and equivariance both exactly zero
so the action is sound and nothing carries hidden state:

| quantity | verdict | spread |
|---|---|---:|
| stabilizer T-count | orbit-collapsed | 0 |
| contraction width | orbit-collapsed | 0 |
| **matchgate validity** | **orbit-resolving** | **1.0** |
| **`q_sim_upper`** | **orbit-resolving** | **0.625** |

The cause is the free-fermion path, whose adjacency test reads the labelling — a
minimum over strategies inherits the worst typing of its members. It is *not* a
defect in that strategy: matchgates on non-adjacent qubits really are universal,
so refusing them is right. The defect is the **type**.

The reversal row shows this is structure, not noise. Reversal preserves the path
graph's adjacency, so the free-fermion path survives it and the value does not
move: `q_sim_upper` is **orbit-collapsed on the stabiliser of the interaction
structure** and jumps outside it.

What survives: a classical simulator may relabel before simulating, so the value
in *any* frame is a cost some simulator can really pay — **every frame gives a
valid upper bound**. What is forbidden is calling one frame's value a property of
the core, or comparing two cores whose numbers were taken in arbitrary and
different frames. `ResidencyReport.frame_typed` now records this.

> **The sampling defect, recorded because it nearly buried the finding.** The
> first attempt drew 24 uniformly random permutations of ten qubits and reported
> orbit spread **zero** for the family whose true spread is 0.9 — because none of
> the 24 was the identity, and the identity is the frame where the free-fermion
> path applies. An orbit sample that cannot reach the frame where the quantity
> differs measures nothing. `orbit_frames` now always includes the identity and
> one adjacent transposition. That is the same defect this document records in a
> residency witness, a K3 attack, a projection freeze, a saturation equivalence
> and two guards — now a seventh time, in the instrument built to audit the
> other six.

### 0.36 A frame group you can walk in full: `GF(GF(2,2), GF(2,2))`

§0.35 left a real weakness and said so: the orbit of a 16-qubit circuit under
relabelling is `S₁₆`, of order 2.1×10¹³, sampled with four to six frames. Zero
spread over six random points of a group that size is consistent with luck.

Build the tower instead —

```
GF(2) < GF(4) = GF(2)[x]/(x²+x+1) < GF(16) = GF(4)[y]/(y²+y+ω)
```

— a degree-2 extension of a degree-2 extension, verified as a field
exhaustively rather than trusted: every non-zero element invertible,
associative on all 4096 triples, element orders {1,3,5,15}, 8 generators, GF(4)
a closed subfield. Label the 16 qubits by GF(16) and field structure becomes
frame structure: `AGL(1,16) = {x ↦ ax+b}` is a subgroup of `S₁₆` of order **240**
— small enough to enumerate completely, with a nested ladder of subgroups
inside it and the Frobenius lift `x↦x²` generating `Gal(GF(16)/GF(2))`.

This is the characteristic-2 analogue of `cayley_dickson.associator_ladder`,
which measures how badly associativity fails at each rung of the doubling tower
over ℝ. Here the rungs are frame subgroups and the failure measured is loss of
invariance: **at which rung does a measurement stop seeing the object?**

| rung | \|G\| | contraction width | matchgate certificate |
|---|---:|---:|---|
| T2 (translations by span{1}) | 2 | collapsed | **1/2** |
| T4 (translations by GF(4)) | 4 | collapsed | 1/4 |
| T16 (all translations) | 16 | collapsed | 2/16 |
| M3 = GF(4)\* | 3 | collapsed | 1/3 |
| M15 = GF(16)\* | 15 | collapsed | 1/15 |
| Frobenius | 4 | collapsed | 1/4 |
| **AGL(1,16)** | **240** | **collapsed** | **2/240** |

Two results, and the ladder is what separates them.

**Contraction width is orbit-collapsed on the entire affine group.** Zero spread
over six random frames was consistent with luck; zero spread over all 240 is a
fact about the group. That upgrades §0.35's caveat from a suspicion to a
measurement.

**The free-fermion certificate survives exactly two of 240 frames** — and they
are the identity and `b = 15`, which is XOR with all-ones, i.e. `x ↦ 15 − x`:
the **reversal**. So its stabiliser is `Aut(P₁₆)`, the automorphism group of the
very path graph the gates were laid on, of order 2 and **index 120**. The
certificate does not merely depend on the labelling; it depends on it maximally,
surviving only the symmetry of the 1D chain itself. And it already fails on
**T2** — a two-element group is enough to break it.

`q_sim_upper` inherits this, resolving on the 4-element `T4` rung with spread
`0.3125`. A review reporting only *"some things are frame-dependent"* would have
lost the distinction between a quantity that survives 240 relabellings and one
that dies under a single translation. That distinction is the whole content.

### Lifting to the full spin group, and 3-XOR orthogonality

`AGL(1,16)` is only the *semilinear* frame group. Forgetting the field
multiplication and keeping the GF(2)-vector-space structure gives the strictly
larger

```
AGL(4,2) = GF(2)^4 : GL(4,2),   |G| = 16 x 20160 = 322,560
```

a factor of **1344** more frames, and the largest linear frame group on 16
labels short of `S_16`. It cannot be walked — and does not need to be.
Invariance under a group is invariance under its **generators**, so sixteen
checks (4 translations, 12 transvections) settle all 322,560 elements *exactly*.
That is the one exhaustive claim in this session available without an exhaustive
computation.

| measurement | generators breaking it | verdict on all 322,560 frames |
|---|---:|---|
| contraction width | **0 / 16** | **invariant** |
| free-fermion certificate | **16 / 16** | broken by every elementary move |

Contraction width survives the lift. The certificate is not merely
small-stabiliser — *every one* of the sixteen elementary moves destroys it,
which is sharper than the index-120 statement and is maximal fragility.

**3-XOR orthogonality** — triples with `a ⊕ b ⊕ c = 0` on the 15 non-zero labels
— is the line structure of `PG(3,2)`: **35 lines, 7 through every point**, the
characteristic-2 orthogonality the Fano plane carries one dimension lower and
that `fano_algebra` already uses for the octonions. It splits the frame group
cleanly:

- linear maps **preserve** it — `M(a⊕b⊕c) = Ma ⊕ Mb ⊕ Mc`, so a vanishing sum stays vanishing;
- translations **destroy** it — `(a⊕t) ⊕ (b⊕t) ⊕ (c⊕t) = a⊕b⊕c⊕t = t ≠ 0`.

So 3-XOR orthogonality is a `GL(4,2)` invariant and **not** an `AGL(4,2)` one:
the relation is anchored at the origin, and translations move the origin. It is
exactly the structure that tells the linear half of the frame group from the
affine half — and the first measurement in this session that distinguishes them.

> A correction made in passing: the first run reported *"every generator
> preserves the 35 lines: False"* and that read as a finding. It was a
> mis-grouping — linear maps must preserve the relation, and it is the four
> translations alone that break it. Separating the parts turns a wrong
> aggregate into the actual structure.

### 0.4 `q_sim_upper = 1.00` is a shrug in the units of a measurement

That left a diagnosis with no instrument: a missing strategy is arbitrarily
wrong on whatever it was for, and gives *no signal about where*. The signal was
there the whole time.

`q_sim_upper == 1.0` holds exactly when `log2_sim_cost ≥ n`, which holds exactly
when **nothing in the portfolio simulated the core below brute force**. These are
upper bounds, so a bound at the ceiling is the *absence* of a bound. 1.00
therefore never means "measured maximally quantum" — it always means "no
applicable strategy," and it was being averaged in with real measurements.

Both QΣ-R1a defects sat at exactly 1.00 before they were found. `ResidencyReport`
now records `bounding_strategy` and `informative`, and the retrodiction is run as
a test rather than asserted: with the two structural strategies disabled — the
portfolio's state when both defects were live — both defective families saturate
and the genuinely hard control does not.

The flag marks **absence of information, not presence of hardness**. A universal
circuit saturates too, and correctly: the portfolio has nothing to say about it
either. The free-fermion core scored 1.00 while poly-time; adding one SWAP makes
it universal and it scores 1.00 again. *The number cannot tell those apart.*
That is the finding, and no amount of care in reading it would have helped —
they are the same number.

And one more thing falls out of recording the winner. Across all 150 random
cores:

```
saturated (no strategy beat dense): 0/150
bounding strategy: stabilizer_rank 150
```

**Every single number in the headline sweep is a stabilizer-rank number.** The
other three strategies never win there. So `mean 0.0825` is not a portfolio
result with three strategies corroborating it; it is one algorithm's output with
three inactive strategies standing next to it, and a fifth strategy aimed at
that regime could move all 150 at once. The corpus is a monoculture, which is
precisely the condition under which the two defects above were possible.

### 0.5 The portfolio has no redundancy

There is no ground truth to check `q_sim_upper` against — computing the true
simulation cost *is* the problem the metric approximates. So the only available
evidence that a bound is not an artefact of one algorithm is that a **different**
algorithm, pricing a different structural property, lands in the same place.

`experiments/strategy_disagreement.py` builds a generator designed to break the
monoculture, interpolating over magic density, locality and matchgate fraction.
It works — the winner moves from stabilizer rank to contraction (61%), basis
permutation (8%) and free-fermion (3%). Then it asks what happens where several
strategies *can* apply. Over 216 cores:

| | |
|---|---:|
| cores with **no** applicable strategy (saturated) | 6 (2.8%) |
| cores with exactly **one** applicable strategy | 131 (60.6%) |
| **cores with no second opinion at all** | **137 (63.4%)** |
| cores with two strategies within 1.0 bit | 2 (0.9%) |
| cores with two strategies within 2.0 bits | 13 (6.0%) |
| median margin where a runner-up exists | **3.20 bits** |

Nearly two thirds of cores have a bound with nothing to compare it against.
Where a runner-up does exist it disagrees by a median of 3.2 bits — a factor of
**9** in simulation cost. Only one core in 216 has two strategies within half a
bit of each other.

This is not a fixable shortfall; it follows from the construction. A minimum
over upper bounds is dominated by whichever bound is best, and two
differently-motivated bounds have no reason to coincide — the free-fermion path
is the extreme case, since a single non-matchgate gate deletes it entirely, so
it can never approach another strategy continuously. Wherever it applies it wins
by 4 bits; wherever it does not it contributes nothing.

The consequence is the sharp form of remainder 1:

> **A defect in the winning strategy is undetectable from inside the portfolio.**
> For 63% of cores there is nothing else to check against, and where there is,
> it is an order of magnitude away.

That is not a hypothetical. It is the mechanism by which both §0.1 and §0.2
defects survived: each was a core where one strategy was unopposed, and it was
wrong, and nothing in the portfolio was positioned to notice.

### 0.6 The metric is a function of the notation, not of the operator

§0.5 predicts that a defect in the winning strategy goes unnoticed. Here is one
that was, found by looking where the saturation flag fires.

Both of these circuits implement **exactly the same operator** — the identity on
six qubits:

| notation | gates | `q_sim_upper` | `bounding_strategy` |
|---|---:|---:|---|
| Clifford+T | 378 | **0.0000** | stabilizer_rank |
| qiskit's full gate set | 36 | **1.0000** | **dense** |

Written one way the metric says the core is exactly free. Written the other way
it says no strategy can simulate it below brute force. `q_sim_upper` is
therefore not a function of the operator; it is a function of how the operator
is *written* — and resisting exactly that is the metric's stated purpose (§0:
*"resists gaming by syntax and cannot be inflated by notation"*).

The K3 equivalence attacks pass all three of their cases, because the compiler
portfolio cancels them. This one it does not see: `U` followed by `U†` for a
random six-qubit `U`, with no local cancellation at any optimisation level, in
a gate set the structural strategies also cannot penetrate. All four strategies
fail together — every one either refuses the core or fails to beat dense — which
is §0.5's "no second opinion" in its most literal form.

**But the saturation flag fires on it.** That is the one piece of *predictive*
value the §0.4 instrument has shown: it was derived from two defects already
known, and it independently marks a third that the adversarial suite passes
over. So K3 now distinguishes two failures that were being scored the same:

```
H T Tdg H                                    q_sim_upper=0.0000  ok
entangle, 4 cancelling T pairs, disentangle  q_sim_upper=0.0000  ok
H CCX CCX H                                  q_sim_upper=0.0000  ok
U U-dagger, rich basis (6q)                  q_sim_upper=1.0000  GAMED but SATURATED
```

A wrong answer the metric flags is not the same failure as a wrong answer it
states confidently. The defect is real and is not fixed here — circuit
equivalence is intractable in general, and the repository has said so since
§0.5's first draft. What changed is that it is no longer silent.

### 0.7 A suite reports whether its witnesses fail, never whether they reach

Six defects in this round share one shape: a guard whose witness could not reach
the case it asserted. `test_residency_scales_with_t_count` witnessed T-scaling
on a circuit with no entangling gate. The K3 attacks missed a whole class of
identity. The projection freeze listed seven of ten keys. The saturation
equivalence was never evaluated at n = 0. And two were in this round's own new
code, including a matrix conjugation that was a no-op on every input, guarded by
two examples symmetric under exactly the operation it performed.

The suite passed through all six. It was always going to: it reports whether its
witnesses *fail*, never whether its witnesses *reach*.

`experiments/mutation_probe.py` is the instrument, and it is the same move §0.4
made for missing strategies. Break one line — flip a comparison, negate a
condition, replace a returned constant — and run that module's own tests. If
they still pass, nothing distinguishes the mutated code from the real code.

It was validated against a known defect before being trusted: with the dead
conjugation temporarily restored, the probe independently flagged it. Pointed at
this round's two new modules:

| | mutants | killed | survived | kill rate |
|---|---:|---:|---:|---:|
| before | 23 | 12 | 11 | **52.2%** |
| after | 23 | 22 | 1 | **95.7%** |

Nearly half the lines in the newest, most carefully reviewed modules in the
repository were unguarded. The most alarming was `width + 1` in the contraction
charge — the entire cost convention — which could become `width + 0` with every
test still green, because every assertion about it was an inequality loose
enough to absorb an off-by-one.

**The one surviving mutant is equivalent, not a gap.** `<` versus `<=` on
`|det A − det B| < _ATOL` differ only at exact equality, and `np.linalg.det`
never returns that value: four constructions all land one ulp above at
`1.0000000000000007e-09`. Distinguishing an equivalent mutant from a real gap is
the difference between an instrument and a to-do list, and a test now asserts
the boundary stays unreachable — so if a future numpy makes it reachable, the
mutant stops being equivalent and the suite says so.

Two limits. The probe covers **two modules**; the rest of the repository is
unmeasured, and five of the six defects above live in files it does not touch —
so 95.7% is not a property of the suite. And the probe had two defects of its own
before its first number meant anything: it mutated type annotations into
`SyntaxError`s, which inflate the kill rate, and string literals, which deflate
it. Both were found by reading its output. The instrument built to find unreached
guards has no instrument finding *its* unreached guards, and that regress is not
closed here.

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

**Historical D10 — the tree-likeness warrant failed.** On this \(K_{2,3}\)
1-skeleton, δ/diameter = 0.5 falsifies the premise that the free-theory graph is
tree-like. At R3 that result was overgeneralized into retirement of every
Poincaré base. The HB0 A-contract supersedes that broad policy: it declares an
independent universal atlas and does not identify graph distance with its
metric. The frozen placement also gives lower distortion to the hyperbolic
instrument (5.29 vs 6.64), so the old matched-Euclidean kill condition was
**not** met; K13 supports only the narrower failure of the tree-likeness
justification.

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
| D14b | D10 (hyperbolic base retired) | `atlas.py` module docstring still asserted *"Its base is hyperbolic, not Euclidean"* with the full justification | historically rewritten to no assigned geometry; the HB0 universal-base axiom later supersedes that policy with an explicit A-tagged atlas while preserving δ/diam = 0.5 |
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

- `q_causal` remains retired and unmeasured. QΣ-R3B-0 calibrates four observable
  coordinates of the cone, but four constrained coordinates remain explicitly
  missing and the registered outcome is therefore `HOLD`.
- A free-conversion metric `d(F_i,F_j) = −log sup p_succ` is still unmeasured.
  Therefore the universal Poincaré base is A-tagged architectural structure,
  not an M-tagged claim that free-theory conversion induces its metric.
- The base category is still one axis (resource theory). The full
  `Task × Interface × ResourceTheory × Compiler × Noise × Frame` is not built.
- QΣ-R³B (the full four-cell causal organ test) remains specified and not run;
  R3B-0 is only its synthetic identity-versus-dephasing instrument calibration.

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
until a free-theory fiber/index specification is named.** Each Reality Cell now carries
`(free_states, free_operations, admissible_group, monotone)`, and resource claims
do not transport outside the admissible group.

**(c) Universal Poincaré base, declared rather than inferred.** The shared
architectural base is now \(B=H^n_{-\kappa}\). Free theories are categorical
fiber/index labels placed in that atlas; Fisher, Riemannian, Euclidean,
quaternionic, split-signature, and PSD structures are not identified with the
base metric. A separate \(R^n\) control matches the Poincaré tangent metric at
the origin.

The old argument below was made against a **synthetic complete binary tree**.
K13 then showed that the live free-theory graph is not such a tree
(Gromov δ/diameter = 0.5). That kills the empirical justification, not the
new A-tagged coordinate contract. The historical worst-case distortions remain:

| depth | nodes | hyperbolic | euclidean | advantage |
|---:|---:|---:|---:|---:|
| 1 | 3 | 1.00 | 1.00 | 1.00× |
| 2 | 7 | 2.04 | 2.08 | **1.02×** |
| 4 | 31 | 4.67 | 7.55 | 1.62× |
| 6 | 127 | 13.35 | 30.03 | 2.25× |

**Honest reading:** the table measures a synthetic tree, while K13 measures one
fixed placement of the five-node free-theory graph. Neither establishes a
free-conversion metric. The live `base_distance` now evaluates the declared
universal atlas; `experimental_poincare_instrument` remains a deprecated alias,
and the frozen K13 placement continues to reproduce its original 5.29/6.64
distortions without being reused as the live \(H^4\) placement.

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
| K13 | the free-theory graph empirically earns hyperbolic curvature from tree-likeness | Euclidean matches it on the frozen live-hierarchy placement | **tree-likeness premise falsified; original matched-control kill not met** — δ/diam = 0.5, while distortion is 5.29 hyperbolic vs 6.64 Euclidean; preserved separately from the HB0 A-tagged universal atlas |
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

`AXIOM-HB0-UNIVERSAL_POINCARE_BASE` is the additional HB0 A-object:
constructors, Hⁿ coverage, chart invariants, cage identity and the
tangent-matched Euclidean control are checked. Negative curvature is declared,
not inferred from K13. The structural envelope verifies against the current
working tree but is not commit-bound or independently witnessed.

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
| HB0 universal base | conditioned \(H^n\) atlas, H⁴ default, typed Euclidean base control, live Atlas/HB-0 placement; K13 frozen separately | structurally implemented as `AXIOM-HB0-UNIVERSAL_POINCARE_BASE`; hashed working-tree envelope verifies, while independent witnessing and task benefit remain absent |
| QΣ-R1a | adversarial suite: representation, simulator-portfolio, interface attacks | ✅ all three named families covered — tensor-network and low-treewidth by `aionq.contraction`, matchgate/free-fermion by `aionq.matchgate`, exercised by the K4 table. Closing them exposed §0.1–§0.2: the two-strategy portfolio scored a product of single-qubit chains at 1.00 and a poly-time free-fermion core at 1.00, and the suite pinned the first |
| Σ∞-S3 | §16 exp. 1: sheaf obstruction localisation, 8 coordinate systems, 300 trials; plus the QΣ query claim | ✅ 128 tests; sheaf clause survives, hypercomplex clause killed, octonionic clause ill-posed |
| S4-G100 | Reversible Recognition Chamber: aperture, ordered roles, nest gate, 10 preregistered gates | ✅ 193 tests; 6/10 gates fail, chamber retired, S3 claim superseded as basis-dependent |
| S5 | moving-frame orbit audit; basis-free Laplacian instrument | ✅ 208 tests; exactly orbit-collapsed AND strongest (0.964 vs 0.776) |
| S6 | ACAF adversarial sweep: 950 instances, 4 families; falsified a P-tagged claim and fixed the instrument | ✅ 211 tests; invariance 950/950 after fix, accuracy scoped by topology |
| QΣ-R4 | Witnessed Reproducibility Membrane: fail-closed portfolio, evidence envelopes, portable RSS, cross-platform CI | ✅ 242 tests on **Linux only**; 20/20 attacks behave as specified; **48 of 81** prior claims carry no envelope |
| S7 | adjudicating an external corrections audit of the source archive: its checkable claims re-run here, its central verdict sharpened | ✅ 222 tests; 3/3 replications exact, `[R] = ‖H¹‖` retired in **both** regimes |
| QΣ-R3A | measured free-conversion metric; re-test base geometry against it | not started |
| QΣ-R3B-0 | frozen four-cell identity/dephasing calibration; paired seed-cluster vector uncertainty | implemented with a mandatory `HOLD`: 4/8 axes unmeasured, audit strength zero, no advantage claim |
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

   QΣ-R1a is the first time this was collected on rather than merely stated, and
   the lesson was sharper than expected. Adding two strategies did not shave a
   few percent off a frontier — it took one family from **1.00 to 0.17** and
   another from **1.00 to 0.00**, because what was missing was not a better
   algorithm for a hard problem but the only implemented algorithms that could
   see *structure* at all. The exposure is therefore not symmetric: a metric
   missing a strategy is not uniformly optimistic, it is arbitrarily wrong on
   whatever that strategy was for, and it gives no signal at all about where.

   The free-fermion case shows how far that goes. `q_sim_upper` can be driven to
   any value on a matchgate core by padding it with T gates the real simulator
   never pays for. A number that an adversary can set to 1.00 on a poly-time
   circuit is not a loose upper bound on hardness; on that family it is not a
   bound on hardness at all. All three families the gate named are now covered —
   and the list was written by the same people who wrote the portfolio, so its
   completion is evidence about the list, not about the frontier.

   §0.5 gives this its final form, and it is worse than "exposed to refutation
   from outside". **The portfolio cannot refute itself.** 63% of cores have one
   applicable strategy and no second opinion; where a runner-up exists it
   disagrees by a median factor of 9. So a wrong strategy is not caught by the
   others — there are no others, and the two defects above are what that looks
   like in practice. Every `q_sim_upper` should be read as *"the best bound one
   named algorithm could produce"*, and `bounding_strategy` now says which.
2. **Measured-high does not mean thinks-better.** Nothing here connects `Q_cert` to
   any cognitive performance. The architecture is now auditable; it is not yet
   justified.
3. **The self cannot close.** By C7 this is not a temporary limitation but a physical
   one. The brain's identity signature is estimable only from outside it. The
   architecture is complete only as a two-party object — core plus external witness —
   and no version of it will ever be complete alone.

Point 3 is the same remainder the draft named Gödelian, now with a sharper reason and
a copy count attached.

---

## 8.1 The three are one, computed

They read as three debts, and point 3 as the philosophical one. They are one
debt. `aionq.closure.architecture_closure()` evaluates all three against the
live repository:

| remainder | blocker | measured |
|---|---|---|
| 1. classical frontier | agreement between strategies is one party checking its own arithmetic | evidence rank **NONE** |
| 2. thinks-better | `promote()` requires `audit ≥ 1.0`; audit strength is `0.0` | **HOLD**, audit deficit 1.0 |
| 3. self cannot close | no internal act rises above ATTESTED | `closable_from_inside: False` |

> **The architecture is not incomplete in three ways. It is incomplete in one
> way, three times.**

The sharpest instance is point 1, and it retires a question rather than
answering it. QΣ-R1a spent a round building a generator to find cores where two
simulation strategies agree, then reported that the agreeing region is
essentially empty — 63% of cores have no second opinion at all, and where one
exists it disagrees by a median factor of 9. **The prior question was never
asked: would agreement have counted?** Modelled as witness acts, no. The four
strategies are four *methods* of one party — one author, one repository, one
process — so `producer == verifier`, `WitnessAct.rank` is 0, and
`evidence_rank` is `NONE` even when every ordered pair is granted a full
`recomputed` act, the highest mode `MODE_RANK` offers. The corroboration that
round went looking for would not have counted had it been found.

Point 2 is the one that matters for the goal, and it is not blocked only by its
four unmeasured coordinates. `promote()` treats audit as **not tradeable against
effect size**: measuring `sample_efficiency`, `neg_energy`, `neg_latency` and
`recovery` would leave the gate shut, because `audit_strength = 0.0` against a
threshold of `1.0`. So the step from *auditable* to *justified* does not run
through more measurement. It runs through an external auditor.

This is falsifiable, which is the only reason it is worth stating. Each item
names the event that closes it — a bound computed elsewhere, an external audit,
a recomputation received — and every one is an act this repository cannot
perform for itself. Relabel the same twelve portfolio acts to distinct parties
and the rank rises to `INDEPENDENT` immediately; it is the shared party that
costs the evidence, not the modelling.

A small accident of QΣ-R1a is the cleanest illustration. The mutation probe
corrupted the module it was measuring, leaving `informative` inverted in the
working tree. Every internal check stayed green — the suite passed, because the
mutation was one no test could kill. It was caught by `git status`: a tool
outside the instrument, answerable to nobody in it. That is remainder 3 in
miniature, and it was not staged.

---

## 8.2 The geometry was already there, unnamed

`witness_nerve.py` is named for the **nerve of a cover**, and behaves like one.
Parties are the patches; an act between two of them is a 1-simplex; evidence is
a **connection**, transporting a claim's rank from producer to verifier.

Read that way, the Gödelian gap stops being a limitation and becomes a dimension
count. The self-audit says every predicate expressible about the repository's own
artifacts is decidable *here* — every section is locally defined. What is missing
is a gluing condition, and gluing conditions live on **overlaps**. With one party
the cover has one patch, and `party_nerve` computes what follows:

```
parties=1  self_loops=12  edges=0  triangles=0  dimension=0  χ=1
```

> The obstruction to closing the self is not that H¹ is non-zero.
> **It is that the complex has no degree-1 part in which an obstruction could
> live.**

That is why quality cannot help. Quality is a property of the fibre — the mode,
the care, the number of strategies — and the problem is the **base**. A
self-loop is not a low-quality edge; it is not an edge. Relabel the same twelve
acts to distinct parties and an edge appears immediately, so nothing about the
modelling forces dimension 0.

The attestation-cycle theorem is a **flatness** statement in this reading. A
cycle of attestations is a loop in the nerve, and its holonomy is zero once any
attestation exists: transport around the loop returns you to ATTESTED, never
accumulating. Only `recomputed` edges carry non-trivial transport. The repository
proved flatness of the evidence connection and recorded it as an inequality. The
correction it survived — that the *first* attestation is not free, holonomy 1
from the empty graph — is the statement that an attestation is not nothing, it is
**bounded**.

### `HOLD` is a stratum, not a refusal

The advantage cone `K` is a region in the 8-dimensional outcome space: a product
of per-coordinate half-spaces. The R3B-0 effect vector has four finite
coordinates and four NaN, so it is neither inside `K` nor outside it. It lies on
a **stratum of codimension 4** where `K`'s inequalities are not evaluable.
`AdvantageCone.contains` returns False there — correctly, since a point that
cannot be shown inside must not be treated as inside — but *False* and *outside*
are different geometric statements, and only one of them is a scientific result.

Because the constraints are per-coordinate and **uncoupled**, `K` is a product,
so the projection onto the measured coordinates is *exact* rather than an
approximation. The conditional question is therefore well posed, and answering it
separates a scientific failure from a missing audit:

| axis | effect | margin | slack |
|---|---:|---:|---:|
| accuracy | 0.4956 | 0.20 | **+0.2956** |
| generalization | 0.5215 | 0.20 | **+0.3215** |
| robustness | 0.5053 | 0.20 | **+0.3053** |
| calibration | 0.2500 | 0.10 | **+0.1500** |

The organ's measured cognitive effect is **interior to the projected cone on
every axis**, by roughly a factor of 2.5. Every one of the four unmeasured axes
is merely `no_worse` — none demands an improvement. And it is still not
promotable, because `audit_strength` is `0.0` against a threshold of `1.0`, and
`promote()` refuses to trade audit against effect size.

So the sharpest form of §8.1 is not an abstraction:

> **The four-cell organ shows a cognitive effect well inside its pre-registered
> admissible region, and cannot be promoted — because there is no second party
> to witness it.** Remainder 3 is what holds remainder 2 shut, with numbers.

### 8.3 Two of the four coordinates were derivable, not measurable

QΣ-R3B-0 recorded `neg_energy` and `neg_latency` as missing, and gave reasons
that are refusals rather than absences: *operation counts are parity
diagnostics, not an energy measurement; protocol depth is a parity diagnostic,
not a latency measurement.* Both are correct about the **quantity**. But the
cone does not ask for energy — it asks for a **difference** in energy between
two arms, and a difference can vanish for reasons that survive every naming of
the quantity.

> **Theorem (parity-derived vanishing).** Let `P(arm)` be the resource profile.
> Let `C` be any cost function of the form `C(arm) = f(P(arm))`. If
> `P(target) = P(control)` then `Δ_C = 0` exactly, for every such `f`.
> *Proof.* `f` is a function. ∎

All the content is in the premise, so the premise is re-checked rather than
assumed: `resource_parity` holds on **32 of 32** seed clusters, certifying equal
trials, copies, memory calls, POVM outcomes and side registers — and a schedule
and uniform-draw stream that are *shared*, not merely matched. One failing seed
refuses the whole derivation and returns nothing, not a zero with a caveat.

Codimension **4 → 2**. `sample_efficiency` and `recovery` remain, and neither is
derivable this way: they are properties of behaviour under conditions the
protocol never creates — a learning curve it does not run, an interruption it
does not apply. Closing those needs new protocol, not new reasoning.

Three things this does **not** do. It does not pose the membership question —
two constrained coordinates are still NaN. It does not measure energy or latency;
no hardware ran, and the claim is about a difference under a class of models. And
it excludes, by construction, any cost model that **prices coherence itself** —
the arms differ in *what* they do while consuming the same amount, so a model
charging differently for a coherent operation than a dephasing one at equal
counts is not a function of the profile. That exclusion is why `neg_energy` is
the weaker of the two; `neg_latency` is stronger, because a latency model
separating arms that share a schedule would have to depend on something other
than when operations occur.

A derived zero and a measured zero are not the same object. This one is exact
and assumption-bearing; a measurement would be uncertain and assumption-free.
The cone cannot tell them apart, which is a fact about the cone — and the reason
`cone_stratum` keeps derived coordinates **off by default**.

---

## 8.3b What this programme currently knows

Every instrument here measures a deficiency — unwitnessed claims, unreached
guards, missing strategies, absent audits. None reports the positive quantity.
A session can drive the correction count from 41 to 67 and never once ask what
is *standing*. `aionq.knowledge_ledger` asks.

**93 claims. 26 retired.**

| tag | | count |
|---|---|---:|
| **R** | RETIRED | **26** |
| P | PROVED | 25 |
| M | MEASURED | 25 |
| A | AXIOMATIZED | 7 |
| H | HYPOTHESIS | 5 |
| S | SEMANTIC | 5 |

Retirement is the **largest single category** — the programme demotes claims at
very nearly the rate it proves them. Whether that is unusual rigour or claims
arriving faster than support, the ledger alone cannot say; but it is the
dominant movement, and no round-level audit can see it.

### Evidence coverage is one claim

Of **57** live claims at an evidence-requiring tag (P/A/M), exactly **one**
carries a verified envelope:

```
AXIOM-HB0-UNIVERSAL_POINCARE_BASE
```

The single evidenced claim in the programme is the **axiom** — the tag whose own
definition is *"passes via an explicit axiom or a weaker surrogate check"* — and
§0's HB0 note already records that its envelope is *"unsigned, self-recomputed,
and neither commit-bound nor independently witnessed."* **Zero PROVED and zero
MEASURED claims carry an envelope.** Coverage: **1.8%**.

> **A reading error worth recording, because it inverts the ledger.**
> `registry.unwitnessed()` returns claims *at an evidence-requiring tag* with no
> envelope, so HYPOTHESIS and SEMANTIC claims never appear in it. Their absence
> means the question does not apply — a metaphor cannot carry an envelope.
> Reading it as *witnessed* turns 1-of-57 into an apparent 11-of-67: a sixfold
> overstatement, in the one direction that flatters the programme. It was caught
> because the first table produced looked backwards — hypotheses and metaphors
> at 100%, proofs and measurements at 0%.

### The gap is widening

This is a derivative rather than a level, and it is the one that matters. §7
records the QΣ-R4 baseline: **48 of 81** claims carrying no envelope. It is now
**56 of 93**.

> **12 claims added since R4; 8 of them arrived bare.** Two thirds of new claims
> come with no envelope, so coverage moved the wrong way while the corpus grew.

A large deficit that is closing is a programme in progress. A smaller deficit
that is widening is not.

And the scale cuts both ways: **one** verified envelope on any PROVED or
MEASURED claim would *double* the programme's evidence coverage. That is how
little it would take to register the first real movement — and it is the thing
no amount of further auditing produces.

---

## 8.4 The code composes; the evidence does not

Every round here is audited from inside itself. That is the right scale for a
wrong tolerance and the wrong scale for one question: **if this is wrong, what
else is wrong?**

The answer travels along the **import** graph, because a result computed by a
module that imports another inherits that module's correctness. Two graphs,
measured by `aionq.dependency_closure`:

| | edges |
|---|---:|
| code — local `aionq` imports | **114** across 77 modules |
| evidence — cross-round artifact references, envelopes included | **2** |
| artifacts declaring an `upstream` key | **0** |

**24 of 26** rounds reference nothing at all, and the two that do are
`r6l → r6k` and `r7 → r6_unitary_price`. The names promise a descent — unitary
price → operational information → Hopf layer → Holevo sandwich → carrier
telemetry → capacity ceiling → translation → equal-resource → common receiver →
source information → movement — and the artifacts do not compose in anything
like that shape. The mechanism exists and works in those two places; its absence
elsewhere is informative, not accidental.

> **Correction.** This table first read *60 edges across 59 modules* and *4
> genuine scientific edges*. Both were wrong, and reviewing the instrument that
> produced them found three defects. The module graph scanned only the top level
> and missed **24 modules** under `hb0/` and `recognition/`, and dropped
> `from . import (…)` entirely. The evidence scan matched bare directory names,
> so it counted `"3-manifold"` in a sentence about cohomology as a reference to
> the `manifold` round, and `"r40_complete"` as a reference to `r4` — two of its
> four edges did not exist. It also *skipped envelopes*, which was the worse
> mistake: an envelope is precisely where this repository records provenance
> binding, so the scan looked for composition everywhere except the file whose
> job is to record it. Including them adds one edge, already visible in the
> result. Both errors moved the published figures in the direction that made the
> finding look **weaker**, which is why they survived.

### The asymmetry this exposes

Blast radius — what would inherit a defect — is computable, and it was never
computed:

| module | blast radius | depends on | kind |
|---|---:|---:|---|
| `evidence` | 27 | 0 | source |
| **`governance`** | **21** | **1** | **transmitter** |
| `carriers` | 11 | 2 | transmitter |
| **`hyperbolic_qubit`** | **11** | **0** | **source** |
| `cayley_dickson` | 10 | 0 | source |
| `holevo_sandwich` | 7 | 0 | source |
| `common_receiver_reservoir` | **0** | 5 | leaf |

Two facts fall out, and neither was known before looking.

**The R6l square-root defect was contained.** `_principal_psd_sqrt` lives in
`common_receiver_reservoir`, which nothing imports — blast radius **zero**. A
full round went into that defect, and its containment was never established; it
was assumed by not being asked about.

**The load sits on modules nobody audited.** `hyperbolic_qubit` reaches eleven
modules across R6e, R6f, R6h, R6k, R6l, R7, R8, ohnium and Part B, and it
carries the HB0 axiom this document already marks as *structurally implemented,
independent witnessing absent*.

The top of the ranking splits in two, and the distinction matters more than the
order. **Sources** (`depends_on = 0`) can only *originate* a defect.
**Transmitters** (`depends_on > 0`, large radius) can *inherit* one and then fan
it out — the worse position, because they are reachable. `governance` is the
sharpest target on the page: radius 21, and it depends on something.

> **Correction.** The first version of this table asserted that every module at
> the top has `depends_on = 0` — "they are foundations; they cannot inherit a
> defect, only originate one." That was measured on the graph missing 24
> modules. `governance` moved from **sixth to second** when the graph was
> fixed, so the published ranking was wrong in its **order**, not only its
> magnitudes, and the "all foundations" reading was wrong outright. The test
> asserting it failed the moment the graph was corrected, which is the only
> reason this paragraph exists.

So attention had been going to the module with blast radius 0 while the modules
with blast radius 7 and 10 went unexamined, and no instrument was positioned to
say so. This one is not a repair — writing `upstream` keys into sealed artifacts
would be editing results after the fact, which the provenance discipline
forbids. It makes the omission visible and ranks the surface by leverage.

## 8.5 Imported material, and the difference between a label and an instrument

A Lean 4 archive was supplied by the repository owner and vendored at
`formal/leanmath/`. It formalises the Cayley–Dickson tower, a finite Dirac
operator, a connection Laplacian, halting statements over the octonions, and a
five-carrier *hardness holonomy* whose thesis is that hardness is the structured
failure of return accumulated under transport through representation,
self-reference, algebraic transformation, relational composition and semantic
verification.

**It is not evidence, and this section does not soften that.** The full record
is `manifests/leanmath_import_v1.json`; the reader's summary is
`formal/LEANMATH_PROVENANCE.md`; the measuring is `src/aionq/lean_census.py`,
re-run by `tests/test_leanmath_vendor.py` on every suite.

### What could be measured, and what could not

The archive's own pinned toolchain, `leanprover/lean4:v4.32.0-rc1`, **is**
installed here now. That was the first correction: the import was initially
recorded as unverifiable because no `lean` was on `PATH`, when in fact `elan`
was present with an empty toolchain directory and the pinned toolchain installed
in minutes. Accepting an unverifiability is a decision, and it cost two findings
that were sitting one command away.

| | |
|---|---|
| internal imports / resolving within the archive | 20 / **3** |
| `lake build` possible here | **no** |
| files lexing under the pinned toolchain | **9 of 11** |
| bytes that cannot lex | 148 941 (**39%**) |
| `sorry` by `grep` / in a proof body | 16 / **1** |

Lexing is not verification. Mathlib is not vendored and thirteen of the
archive's own modules are missing from it, so no theorem here has been
elaborated and none has been seen by the Lean kernel. Two files are worse than
unchecked: `TuringHalting_Master.lean` (opener at line 69) and
`TuringHalting_Hyperdim.lean` (opener at line 9) carry unterminated block
comments, reported by Lean itself at end of file and independently by a
pure-Python nesting counter that agrees on all eleven files. Thirty-three
theorem declarations sit inside those comments, including both entries the
archive's README lists as Key Theorems. **The part of the archive that speaks
most directly about hardness is the part that does not parse.**

### Why this belongs in an architecture document

Three of the archive's own statements about itself are stale, and each is stale
in a way this repository has met before.

Its placeholder note names two sites in `CD.lean` that hold no placeholder,
misses by fourteen lines on two more, and omits the only live one — a ledger
maintained by transcription, drifted from the artifact it describes. Its
`CLAUDE.md` asserts *"All theorems are verified (lake build passes)"*, which is
almost certainly true of the larger tree these files were cut from and cannot be
true here, because here they cannot be built at all: a verification claim
travels with its build, not with its files. And that `CLAUDE.md` would have been
loaded as **this** repository's project instructions by any agent working under
the vendored directory, carrying that build claim in with it. It was renamed to
`IMPORTED_CLAUDE.md`, bytes untouched. *Imported material may be read; it may
not instruct.*

None of that is a criticism of the archive's mathematics, which has not been
evaluated and cannot be from here. It is the same lesson §8.4 reaches from the
other side: prose about an artifact outlives the artifact. Every number in the
table above is computed and asserted; the paragraph you are reading is not
evidence for any of them.

### What it offers the open problem, stated as an obligation and not a result

§2 measures `q_sim_upper` as a minimum over strategies, and this round measured
the shape of that minimum over the frame group AGL(1,16): a **step, not a
saddle**. `matchgate_plan` charges 0 on the free-fermion class and switches off
one gate outside it; `contraction_plan` charges by elimination width; the
minimum is orbit-collapsed on all 240 affine frames. No member of the portfolio
emits a **graded** certificate — a number that degrades continuously with
distance from a tractable class rather than falling off it.

Each of the archive's five carriers is defined by a *residual* rather than by a
predicate: self-identification defect, non-reconstructible evidential remainder,
commutator/associator residue, frustration/irregularity/status shift,
proof/execution mismatch. A residual is graded by construction, and the
hypercomplex one is nearest to something computable here —
`src/aionq/cayley_dickson.py` already measures the associator along the doubling
tower and already calls its output *a ladder of controlled failure types*.

That is a vocabulary, not a bridge. `AlgebraicHolonomy` is over `Fin 8 → ℝ` with
the octonion product; `matchgate_plan` is over 4×4 complex matrices with a
parity-block condition. They are not over the same objects, and the archive's
own header says the obligation before this repository's does: *"Two holonomies
are NOT asserted equal before interpretation."* A matchgate detector returning a
**distance** to the free-fermion class is buildable here today, needs no Lean and
no import, and would be the portfolio's first graded member. Whether it deserves
the name holonomy is a question that must be answered after building it, not by
naming it one — and it is not this round's, because a new strategy changes
`q_sim_upper` and that is not a labelling task.

## 8.6 The step had a shape: the portfolio's first graded member

§8.5 closed by naming what the strategy portfolio lacks. This section supplies
it, as a diagnostic and explicitly not as a certificate.

### The gap, restated as a measurement

Every member of the portfolio behind `q_sim_upper` is all-or-nothing.
`matchgate_plan` charges 0 on the free-fermion class and switches off one gate
outside it; `basis_permutation` and `stabilizer_rank` have the same shape; only
`contraction` varies at all. Walked exhaustively over the 240 affine frames of
AGL(1,16), the minimum takes at most two values — the hardness landscape over
the frame group is a **step, not a saddle**. A step has no gradient to read.

`src/aionq/matchgate_defect.py` replaces the free-fermion bit with four
residuals, one per reason `matchgate_plan` refuses *metrically*: `parity` (the
off-block part of `U`), `determinant` (`|det A − det B|`), `locality`
(`max(0, |i−j|−1)`), `diagonal` (the off-diagonal part of a one-qubit gate).
Anything the plan refuses *categorically* — a measurement, a reset, control flow,
a three-qubit gate — is marked inapplicable and given no number. A measurement is
not far from free fermions; it is outside the class the question is about.

### Three measurements

**The cliff is a function.** `RZZ(t)` has `det A = e^{−it}` and `det B = e^{+it}`.
The certificate holds on exactly the two points `t ∈ {0, π}` of the entire
continuum; the determinant residual is `2|sin t|` — exact to 1e-12 at all
seventeen sampled angles, maximal at `t = π/2`. SWAP, the gate that lifts
matchgates to universality, sits at residual 2, the maximum the constraint
attains. The boolean was never describing a wall. It was thresholding a function
that already existed.

**Over the frame orbit, 2 values become 36.** All 240 frames of AGL(1,16),
walked in full on a 16-qubit T-saturated matchgate ladder:

| | boolean certificate | graded residual |
|---|---|---|
| distinct values over the orbit | **2** | **36** |
| frames in the zero / true set | 2 | 2 (the same two) |
| stabiliser order | 2 | 2 |
| range | {false, true} | [0, 212] |

Same stabiliser, same zero set — the identity and the reversal, `Aut` of the path
graph the gates were laid on, index 120 — and eighteen times the resolution. The
residual agrees with the bit about which frames are certifiable and additionally
ranks the 238 that are not.

**All of the frame-dependence is one residual.** `parity`, `determinant` and
`diagonal` each take exactly **one** value across all 240 frames; `locality`
carries all 36 levels by itself. This is structural, not a coincidence:
`relabel` reuses each instruction's operation unchanged, so a relabelling moves
which wires a gate sits on and never the gate. Any residual computed from a gate
matrix is constant on the *entire* frame group — checked on the sixteen
generators of AGL(4,2), which decide all 322 560 of its elements.

So the free-fermion certificate's frame sensitivity is, exactly and only, a
**routing** quantity. That is a statement about what the certificate measures,
and it was obtained without touching the bound the certificate feeds.

### What this is not, asserted mechanically

`matchgate_plan` is sound because a theorem says the exactly-free-fermion case is
poly-time simulable. **There is no theorem here bounding simulation cost by a
small nonzero defect**, and this round does not supply one. A circuit at defect
1e-3 is not "almost poly-time simulable"; it is a circuit whose certificate does
not apply, at a measured distance from one whose does.

`q_sim_upper` therefore does not consult this module and must not — an upper
bound that read a quantity with no cost theorem behind it would stop being an
upper bound. That separation is the module's whole safety argument, so it is not
left to discipline:
`tests/test_matchgate_defect.py::test_the_bound_does_not_consult_this_module`
fails if any module under `src/aionq` imports it.

Nor is the step finding superseded. The bound's landscape over the frame group is
still a step, because nothing was wired in. What is now established is that the
flatness was a property of the **thresholding**, not of the underlying geometry —
the same orbit carries 36 levels the moment something looks at it without a
threshold. The gap between a distance and a certificate is the open problem, and
it is exactly as open as it was; what changed is that the distance now exists and
is measured. Full record: `manifests/qsigma_r1b_graded_matchgate_residual_finding.json`.

## 8.7 The census: one strategy of four sees the wire names

§8.6 gave one predicate a graded decomposition. The template that produced it
generalises — *decompose a refusal into residuals, then ask which residuals the
group moves* — and this section runs it across the whole portfolio, exhaustively
over all 240 affine frames of AGL(1,16).

| strategy | shape | distinct values over 240 frames |
|---|---|---|
| `stabilizer_rank` | already graded (`α·T`), never refuses | **1** |
| `basis_permutation` | boolean; class is monomial unitaries, dim **4** of 16 | **1** |
| `contraction` | graded width; refuses only categorically | **1** |
| `free_fermion` | boolean; class is dim **7** of 16 | **2** |
| `q_sim_upper` | min over the four | **2**, range [0, 0.25] |

**Exactly one strategy is frame-resolving.** `stabilizer_rank` charges a T-count,
`basis_permutation` reads gate matrices, `contraction` reads a graph invariant —
none of the three can see a wire name. `free_fermion` alone imposes a condition
on wire *adjacency*. Attribution, not correlation: freeze `free_fermion` at its
identity-frame value and the metric is constant across all 240 frames.

Combined with §8.6, where only the `locality` residual moved inside
`free_fermion`, **the mistyping that started this line is now localised to a
single scalar, and that scalar is routing.**

One negative result is worth its own line. `contraction`'s elimination width is
computed by a min-degree heuristic whose tie-break is *by qubit index* — a frame
coordinate. It could have leaked frame-dependence into a graph invariant.
Measured over all 240 frames: constant at 4.0. It does not leak, and that was
checked rather than assumed.

### Why the finite group had to give a step

A relabelling group acts by permutation, so its orbit through a point is a
finite set of isolated points. There is no direction to transport along, no
escape rate, and no dimension that can grow — a union of 240 copies of a
`d`-dimensional variety is `d`-dimensional. **The step measured over AGL(1,16)
is a fact about finite group actions, not a fact about hardness.** That corrects
the emphasis of §8.6's headline without touching its arithmetic.

### The continuous group, where the geometry is

Transport a gate along `G(s) = G0·exp(i s H)`. `src/aionq/transport_fiber.py`
measures what happens, on both threshold classes:

| | matchgate class | monomial class |
|---|---|---|
| ambient (`U(4)`) | 16 | 16 |
| tangent dimension | **7** | **4** |
| codimension | 9 | 12 |
| escape order, 216 directions | **1.000** | **1.000** |
| directions of order ≥ 2 | **0** | **0** |

The 7 is arithmetic, not fitted: block-diagonal in the parity split is
`U(2)×U(2)` = 8, and `det A = det B` is one real condition. The Jacobian's
singular spectrum is `{2, √2 ×8, ~1e-16 ×7}` — a gap of nine orders, so the rank
is a measurement and not a tolerance in costume.

Containment along a fiber is **exact, not osculating**: both classes are groups,
so `exp(i s H)` stays inside for every `s`, verified out to `s = 10`. A fiber has
zero transverse thickness and the dichotomy is sharp with nothing in between.

**What this licenses.** The constraint map is a *submersion* at every point
tested — surjective differential, uniform first-order escape, no direction in
which the class curves back. That is precisely the non-degeneracy hypothesis
that Kakeya- and Falconer-type estimates assume; here it is verified rather than
assumed. **What it does not license** is any incidence, dimension or measure
estimate: verifying a hypothesis is not proving a theorem that uses it, and none
is invoked. The defining functions *are* polynomials — 16 linear and 2 quadratic
— so a partitioning argument has the right raw material. Having the right raw
material is not having an argument.

Full record: `manifests/qsigma_r1c_transport_fiber_finding.json`. The related
plausibility question — whether a Falconer theory over information manifolds
could attach to any of this — is assessed, and largely answered *no, not yet*, in
`docs/FALCONER_ASSESSMENT.md`.

## 8.8 The indices were a chart: the certificate stated covariantly

The instruments of §8.6–8.7 work and are written in coordinates. `_OFF_BLOCK` is
a literal list of eight matrix positions; `is_matchgate_matrix` slices rows
`{0,3}` and `{1,2}`; the module is hard-wired to `4×4` and cannot be asked about
three qubits. Those index lists are the chart of two structures that have names.

**The parity blocks are a ℤ₂ grading.** With `P = Z^⊗n`, every operator splits as
`U± = (U ± PUP)/2`, and the eight forbidden entries are exactly the coordinates
of `U₋`. So `parity defect = ‖(U − PUP)/2‖_F` — measured equal to the index form
*exactly*, difference `0.0`.

**The matchgate condition is Majorana covariance.** `U` is free-fermion iff
`U c_k U† ∈ span{c₁…c_{2n}}`. That one invariant condition subsumes *both* index
residuals. `CZ` is the case that shows it: `CZ` preserves the grading, so its
parity defect is 0 and the index version needs a second determinant test to
reject it — the covariant version rejects it in the one number.

### The number that was never a measurement

§8.7 reported tangent dimension **7 of 16** as a numerical Jacobian rank. In
Majorana terms the Gaussian algebra is the quadratic monomials `c_j c_k` plus
the phase, so

```
dim = C(2n,2) + 1 = n(2n−1) + 1
```

which is `7` at `n=2` and `16` at `n=3` — both confirmed against the rank, gaps
`8.7e9` and `4.3e9`. The 7 was `so(4) ⊕ u(1)` seen through a chart. That is a
*downgrade* of §8.7's claim and it is recorded as one: the prediction is the
fact, the rank was its shadow, and the Jacobian's real value is that it returns
the answer the algebra already knows — which licenses trusting it where the
algebra is silent, a smaller claim than the one §8.7 made.

### The frame group, finally named

Qubit relabelling permutes Majorana **pairs**, so `S_n ⊂ O(2n)`. The frame group
of the fermionic frame bundle is `O(2n)` — continuous, dimension `n(2n−1)`. At
`n = 16` that is a **496-dimensional** group in which `S_16` is 2.1e13 isolated
points, and `AGL(1,16)` is 240 of them. §8.7 said a finite group cannot produce
a dimension phenomenon; this says which continuous group it is a subgroup *of*,
which was the missing half.

### The instrument defect this earned

The first covariant version was still coordinate-dependent — not in its formula,
in its **aggregator**. Taking `max` over the individual mode residuals is a
maximum over a *basis*, and a maximum over a basis does not survive rotating the
basis: measured deviation **1.2e-1** under random `O(4)` frames, on a quantity
presented as invariant. Summing squares is the Hilbert–Schmidt norm of a linear
map and measures **1.3e-15**.

> Writing a formula without indices does not make it invariant if the reduction
> that turns it into a number still reads them.

Eighth occurrence of the recurring pattern, and the first inside a module written
specifically to avoid it.

### The coincidence that is not one

The covariant defect subsumes `parity` and `determinant` but **not** `locality` —
and that is correct, not a gap. Locality is a statement about which wires a gate
sits on; it is not a property of the operator at all. So the index-dependence of
the *code* and the frame-dependence of the *quantity* coincide exactly: the three
residuals expressible invariantly are the three that are orbit-collapsed, and the
one expressible only in indices is the one that is orbit-resolving.

### The transverse sphere is not round

At a point of the class (codimension 9, so the direction sphere is `S⁸`), 3000
sampled unit directions give escape **order** 1 everywhere but escape **rate**
ranging `[0.466, 1.877]` — a factor of **4.03**. The class does not sit in a
round cone. The level sets of that rate on `S⁸` are the object a tessellation or
partitioning argument would act on, and this is the first time they have been
measured. No partition, incidence bound or consequence is claimed; an
anisotropic function on a sphere is raw material.

Full record: `manifests/qsigma_r1d_covariant_certificate_finding.json`.

## 8.9 BLIND: the third thing an invariance claim can be

A device was proposed for this repository as its first formal foothold: on a
finite mesh with a discretised connection Laplacian, the eigensections form a
Parseval frame, and a gauge transformation conjugates the frame operator, so the
frame bounds are gauge-invariant.

It is true. It is also **empty**, and the proof shows why: it never touches the
connection. An orthonormal basis is a Parseval frame with `A = B = 1`; the
spectral theorem supplies one for any Hermitian matrix; unitary conjugation
preserves spectra. So the conclusion holds for the zero connection, for a random
Hermitian matrix, and for a connection that is not gauge-equivalent to anything
in sight.

Measured on a 12-vertex ring with three chords and an `SU(2)` fiber, against the
control the device lacked — a **shuffled** connection, which permutes which edge
carries which transport and so changes the holonomies:

| observable | gauge change | shuffled connection | |
|---|---|---|---|
| frame bounds `(A,B)` | `(1,1)` | `(1,1)` | **BLIND** |
| spectrum | 3.6e-15 | **3.6e-01** | discriminating |
| holonomy traces | 8.3e-16 | **1.60** | discriminating |
| localisation (IPR) | 3.5e-16 | **5.8e-02** | discriminating |

### The type

`movingframe` classifies a measurement as **ORBIT-COLLAPSED** — constant on the
frame orbit, therefore seeing the object — or **ORBIT-RESOLVING** — varying on
it, therefore mistyped. This whole programme has treated collapse as the good
case. It is not sufficient. There is a third:

> **BLIND** — collapsed on the frame orbit *and* collapsed under a perturbation
> that is not a frame change. Invariant because it has no content, not because
> it has found the object.

**A claim of invariance is only informative relative to something the invariant
is supposed to fail on.** Without that control, perfect invariance and blindness
are the same measurement. This is the recurring pattern of this repository — a
guard whose witness cannot reach the case it asserts — appearing for the first
time inside a proposed *theorem* rather than inside code.

### Turned back on this repository

§8.6–8.8 reported quantities as orbit-collapsed and stopped there. The control
was never run. It has now been, retroactively, on the three strategies §8.7
called collapsed: `stabilizer_rank`, `contraction` and `free_fermion` all move
under a change of circuit, so **none of them is blind and those findings stand**.
That is the outcome, not the point. The point is that it was asserted for three
rounds and only measured when someone else's theorem exhibited the failure.

### What survives of the device

Its conclusion is not wrong and not useless — it is simply not about
connections. Replace the frame bounds with the spectrum, the holonomy conjugacy
classes, or the eigensection localisation and the same gauge-covariance
statement becomes a real one, because all three can fail. The holonomies are the
sharpest: they are the *complete* gauge-invariant content of a connection on a
graph, and the frame bounds see none of it. Localisation is the one to build on,
because it is the only one of the three that is a step toward a packet.

Full record: `manifests/qsigma_r1f_blind_invariance_finding.json`.

## 8.10 Stirring the network: two places to apply a multiplier, and they are opposite

§8.8 established what a QFFO is — a coefficient multiplier, hence a function of
the number operator, hence a spectral band weight — and concluded it could supply
a `P_k` and no set with a dimension. Placed instead **on the Majorana network**
rather than on the disk, it has two readings that sound alike and are opposite.

A Gaussian unitary is `exp(iH)` with `H = (i/4) Σ A_jk c_j c_k`, `A` real
antisymmetric.

**Single-particle.** Weight the spectrum of `A`. The result is another real
antisymmetric matrix, so another Gaussian unitary — *exactly*, for any weights
whatever. This is transport **along the fiber**, and it is not achieved by
standing still: displacement up to **0.40** with the free-fermion defect never
leaving **4e-15**. Checked with adversarial weights (negative, zero, 10³, random)
because the containment is structural and must survive weights chosen to break it.

**Many-body.** Weight the spectrum of `H` itself. Quadraticity is not preserved;
the result leaves the class by an amount that grows with the displacement.

| branch | displacement | free-fermion defect |
|---|---|---|
| single-particle | 0.1796 | **2.9e-15** |
| many-body | 0.1986 | **1.02** |

Nearly the same distance travelled; fifteen orders of magnitude apart in whether
the certificate survives. **The difference is the direction of the excitation,
not its size** — which is what makes this a fiber/transverse split rather than a
statement about magnitude. And `q` is a knob on how far off: defect 1.02 at
`q = 0.5`, 3.27 at `q = 0.9`, monotone.

This is the transverse departure §8.6–8.7 recorded the portfolio as lacking:
parameterised, generated by an operator carrying a fractal order rather than by a
random kick, and measured by an invariant. The single-particle branch supplies
the complement — a way to stir the network hard while staying provably
simulable, which is what an ablation control needs.

### The correction this earned before the module existed

The first version built the generator as `Σ A_jk c_j c_k` and Hermitised. For
`j ≠ k` the Majorana product `c_j c_k` is **anti**-Hermitian, so symmetrising
annihilated it exactly: every Hamiltonian was zero, every unitary was the
identity, and **both branches reported defect `0.000e+00`**. A clean dichotomy
was one step from being recorded from a measurement of the identity operator. The
missing factor of `i` is the whole difference, and the only thing that looked
wrong was that the zero was *exact* rather than `1e-16`.

Full record: `manifests/qsigma_r1g_majorana_excitation_finding.json`.

## 8.11 Adjacency is the encoding: a remainder withdrawn

§8.10 closed with a **planarity remainder**: that `matchgate_plan`'s
nearest-neighbour condition is a *one-dimensional* restriction where free-fermion
tractability — Kasteleyn, FKT — needs only **planarity**, which Euler's formula
supplies and which is strictly weaker; so the certified path plausibly refuses
free-fermion circuits on planar but non-linear layouts.

**That remainder is wrong and is withdrawn here.**

| placement | certified | `gaussian_defect` |
|---|---|---|
| iSWAP on (0,1) | ✓ | **0.0000** |
| iSWAP on (1,2) | ✓ | **0.0000** |
| iSWAP on (0,2) | ✗ | **6.9282** |
| RXX(0.7) on (0,1) | ✓ | 0.0000 |
| RXX(0.7) on (0,2) | ✗ | 3.6442 |

The **same matrix** is free-fermion on adjacent qubits and not free-fermion one
qubit further apart. Nothing about the gate changed — the Jordan–Wigner string of
the qubit it jumped did. So `matchgate_plan` is not imposing a relaxable layout
convention; it is **enforcing the encoding**, and its locality condition is
correct rather than conservative.

The remainder reasoned about the gate *layout* while the constraint lives in the
*encoding* — and it was written in the same round that introduced the covariant
defect capable of settling it, and was not settled with it.

### Where the real gap is: arity, not locality

A 3-qubit unitary built from a quadratic Majorana generator has defect
**2.8e-15** and is refused with *"acts on 3 qubits"*. The certificate is
**semantic in locality and syntactic in arity**: it recognises presentations, not
operations. A poly-time-simulable unitary priced as hard for how it was written
down. Safe direction for a bound, wrong direction for a measurement. Recorded,
not repaired — accepting multi-qubit gates means deciding Gaussianity inside a
bound-feeding instrument, which is not a labelling change.

### What adjacency costs, in closed form

A generator `c_j c_k` is directly expressible as a same-or-adjacent-qubit gate
iff `|j//2 − k//2| ≤ 1`. Counting: `n` same-qubit pairs plus `4(n−1)` adjacent
pairs.

```
reachable(n) = 5n − 4          exact, verified for n = 2..19
fraction     = (5n − 4) / (n(2n − 1))  ~  5/(2n)
```

`n=2`: 100% · `n=4`: 57.1% · `n=8`: 30.0% · **`n=16`: 15.3%**

The directly expressible slice of `so(2n)` vanishes as `n` grows — **but it
generates**: the 11 reachable generators at `n=3` Lie-generate all 15 dimensions
of `so(6)`, the 16 at `n=4` all 28 of `so(8)`, by explicit bracketing (with a
control: same-qubit generators alone close on strictly less, so the instrument
can report failure). **Adjacency costs depth, not expressiveness.**

### This is the locality residual, algebraically

§8.6 measured that of four residuals exactly one moves under the frame group, and
it is `locality`. §8.7 measured that of four strategies exactly one is
frame-resolving, and it is the one imposing adjacency. Here is why: adjacency
selects a `5/(2n)` slice of `so(2n)`, and **which** slice depends on the qubit
labelling. The residual written in indices is frame-dependent because the
structure it refers to genuinely is.

### Where Euler still belongs

Not at the gate layout — at the **encoding**. Jordan–Wigner is a
one-dimensional fermion-to-qubit encoding and its strings are what make
non-adjacent gates non-Gaussian. Encodings with two-dimensional locality
structure exist, and under one of those the reachable slice would be set by a
planar mode graph rather than by a line — which is where a Kasteleyn or
Euler-characteristic argument would actually apply. **H.** None is implemented,
none was evaluated, and nothing above is evidence about one. That is the
corrected *location* of the idea, not a result about it.

Full record: `manifests/qsigma_r1h_mode_locality_finding.json`.

## 8.12 The second axis: the departure was algebraic, not dynamical

§8.10 recorded the QFFO many-body excitation as supplying *"the parameterised
transverse departure the portfolio lacks"* — free-fermion defect rising from
3e-15 to 1.02. That is true on one axis and empty on the other, and the other is
the one that bears on hardness.

**A spectral multiplier `f(H)` has the same eigenvectors as `H`.** Same
eigenvectors means the same conserved quantities, so `f(H)` is exactly as
integrable as `H` was. It leaves the free-fermion class *algebraically* while
changing nothing about the dynamics.

The instrument that sees this is the level-spacing **ratio statistic**
`⟨r⟩ = ⟨min(sₙ,sₙ₊₁)/max(sₙ,sₙ₊₁)⟩` — needs no unfolding, which is what lets a
many-body spectrum and the ordinates of the Riemann zeta zeros be compared in
the same units of nothing. Measured at `n = 10`, even-parity sector, 512 levels:

| spectrum | ⟨r⟩ |
|---|---|
| free-fermion (quadratic Majorana) | **0.3090** |
| QFFO-excited `f(H)`, same eigenvectors | **0.3086** ← moves by 4e-4 |
| quadratic + quartic, `g = 0.05` | 0.4905 |
| quadratic + quartic, `g = 0.2` | 0.5976 |
| quadratic + quartic, `g = 1.0` | **0.5955** |
| Poisson reference | 0.3853 |
| GUE reference (800×800) | 0.5929 |
| **Riemann zeta zeros, first 400, measured** | **0.6166** |

A quartic term carries the spectrum from the integrable end to the Wigner–Dyson
end, landing where the zeta zeros are — Montgomery–Odlyzko, measured here rather
than cited. The QFFO carries it 0.0004.

### Why it cannot, mechanistically

Two reasons, and the second surfaced by fixing an overflow. A function of `H`
shares its eigenbasis, so no reweighting of eigenvalues changes what is
conserved. And **the QFFO weights saturate**: at `σ=0.4, ς=0.3, q=0.5` the Caputo
branch gives `0.77473093` at `n=10` and `0.77441397` at *both* `n=100` and
`n=2048` — identical to eight decimals. On a 512-level spectrum the multiplier is
a constant times a transient in the first twenty, and `⟨r⟩` is scale-invariant by
construction. The null result is structural, not a matter of parameters.

### Two axes, kept apart

| | what it asks |
|---|---|
| `gaussian_defect` | **algebraic** — is the operator quadratic in the Majoranas? |
| `⟨r⟩` | **dynamical** — do the levels repel? |

QFFO excitation moves the first, not the second. A quartic term moves both.
§8.10 reported one and generalised to the other.

### The step that makes the measurement valid

A Majorana Hamiltonian commutes with `P = Z^⊗n`, so its spectrum is two
interleaved sequences. Statistics taken across an unresolved symmetry look
Poissonian *for any dynamics*, because independent sequences do not repel.
Measured: a strongly chaotic Hamiltonian reads near-GUE inside one parity sector
and collapses toward Poisson across both. Skipping the sector split is the
standard way to measure integrability that is not there.

One numerical caveat, recorded rather than tuned away: `⟨r⟩` is exactly
affine-invariant in exact arithmetic and only conditionally so in floating point,
losing about `ε·T/d` for gaps `d` at height `T`. Harmless for zeta ordinates near
`10⁶` (gaps of order 1, so ~1e-10); not harmless much higher.

Full record: `manifests/qsigma_r1i_spectral_axis_finding.json`.

## 8.13 The braid is real and does nothing: a moving fishnet is still free

Exchanging two Majorana modes is `σ_k(θ) = exp(θ c_k c_{k+1})` — **quadratic in
the Majoranas**. So every braid generator, every word in them, and the whole
θ-family lands inside the Gaussian group.

**The topology is entirely real.** The braid relation
`s_k s_{k+1} s_k = s_{k+1} s_k s_{k+1}` holds with exact difference `6.28e-16`
and phase `+1.000000` on all five adjacent triples — *on the nose*, not
projectively, so the representation is genuine and there is no 2-cocycle to
record. Far generators commute exactly. Adjacent ones do **not** (commutator norm
> 0.5), so satisfying the relation is not a statement about scalars.

**And it is invisible to hardness.**

| operation | free-fermion defect |
|---|---|
| `σ_k(π/4)`, k = 0,1,2 | **0.000e+00** |
| 60-letter random braid word | **5.8e-15** |
| θ ∈ {0.1, π/8, π/4, 1.0, 2.5} | **0.000e+00** |
| Floquet drive, 1 period | 1.7e-13 |
| Floquet drive, 7 periods | 4.6e-13 |
| **quartic interaction** | **6.4e+01** |

A Floquet operator built from quadratic Hamiltonians is a product of Gaussian
unitaries, hence Gaussian — **the moving fishnet cannot leave the class**, at any
period, for any number of periods. Checked at seven as well as one, because
*"stays free for a while"* and *"stays free"* are different claims.

Everything that looks like it should matter — topology, motion, deformation —
leaves the class exactly where it was. **The one thing that leaves it is an
interaction.** This is the measured content of the statement that Majorana
braiding alone is not universal for quantum computation.

### A third blind instrument, and a correction to its own control

The obvious way to ask whether a driven system is chaotic reads its
quasi-energies. Quasi-energies are **angles**, and angles wrap:

| period | wraps `‖H‖T/π` | integrable | chaotic | separation |
|---|---|---|---|---|
| ≤ 0.1 | ≤ 0.83 | 0.3348 | 0.5742 | **+0.2394** |
| 0.30 | 2.50 | 0.3448 | 0.4158 | +0.0710 |
| 0.70 | 5.83 | 0.4349 | 0.3842 | **−0.0507** |

Past the threshold the statistic does not saturate — it **inverts**. At 5.8 wraps
the integrable system reads *more chaotic* than the chaotic one. An instrument
that inverts is worse than one that goes blind, because its output still looks
like a reading. A first measurement reported **0.43** for a driven free-fermion
fishnet and was one step from being recorded as partial chaos.
`quasi_energy_statistic` now refuses above one wrap.

The control that caught it needed correcting in turn. From two data points it
concluded folding pushes the statistic toward Poisson. Across eight seeds and
three periods: mean shift **−0.016**, std **0.082**, sixteen down and eight up,
worst magnitude **0.161** against a signal of **0.212**. Folding is a
**scramble, not a bias** — 76% of the signal, in an unpredictable direction,
which is *worse* than a bias because a bias could be subtracted.

Not claimed: that braiding is useless (it is free-fermion, which is exactly why
it is robust *and* why it is not universal alone); that no braiding scheme can be
hard (richer fusion rules are not tested); or anything about heralded
post-selected operations, which are a strictly larger class and the obvious next
thing.

Full record: `manifests/qsigma_r1j_braid_null_finding.json`.

## 8.14 The pond and the rain: heralding is not the magic

Everything up to here measured **operators**. A state has a description too, and
for a fermionic Gaussian state it is small: `Γ_jk = (i/2)⟨[c_j, c_k]⟩`, a real
antisymmetric `2n × 2n` matrix standing in for `2ⁿ` amplitudes. That is the
**field** side of the duality. Every correlator follows from it by Wick's
theorem, so the **membrane** — the instrument that says whether a state is still
Gaussian — is the failure of that identity at order four:

`wick_defect(ψ) = max_{a<b<c<d} |⟨c_a c_b c_c c_d⟩ + (Γ_ab Γ_cd − Γ_ac Γ_bd + Γ_ad Γ_bc)|`

| | Wick defect | probability |
|---|---|---|
| vacuum | 0.000e+00 | — |
| after a Gaussian unitary | 3.2e-16 | — |
| after a braid | 3.3e-16 | — |
| **heralded quadratic parity**, 3 pairs × 2 outcomes | **4.4e-16** | 0.135 – 0.865 |
| **heralded quartic parity**, 3 sets × 2 outcomes | **0.183 – 0.647** | 0.439 – 0.561 |
| quartic unitary kick | 1.5e-01 | — |

**Heralding is not the magic; the degree of the measured observable is.**
Post-selecting a quadratic parity — the standard fermionic parity measurement, at
either outcome — leaves the pond exactly flat. Post-selecting a *quartic* parity
disturbs it by up to 0.65, at *more* balanced probabilities. So the separation is
degree, not rarity. That settles the question §8.13 left open.

Note the instrument choice: `Γ² = −I` would have certified the non-Gaussian
state, because every state has a well-formed `Γ`. The defect must be evaluated at
an order the description does not already fix, which is four.

### Weave and de-weave

| loop | `‖L − I‖` | `gaussian_defect` | `wick_defect` | `‖Lψ − ψ‖` |
|---|---|---|---|---|
| reversed order | **8.1e-16** | 1.7e-15 | 2.2e-16 | 0 |
| **same order** | **5.29** | 2.2e-15 | 2.0e-17 | **0.93** |

De-weaving in the same order rather than the reverse does not close the loop, and
the open loop moves the state by **0.93 of a possible 2** while *every* hardness
instrument reads machine zero on it. The loop is **hardness-collapsed and
state-resolving** — the `movingframe` distinction appearing at the level of a
physical process rather than a coordinate. De-weaving in the wrong order is real,
physical, and undetectable by any measurement of hardness in this repository.

### The correction this earned, and it is the second of its kind

`herald_parity` first built its observable by *symmetrising* a Majorana product
instead of phasing it by `i^{k(k−1)/2}`. For `k = 2` the product is
**anti**-Hermitian, so symmetrising annihilated it: every projector became `I/2`,
all six quadratic heralds fired at probability **exactly 0.25**, and the
"post-selected" state was the input. The headline was, for one round, supported by
a measurement of the identity operator.

It survives the fix. But this is the **second missing factor of `i`** this
session (§8.10 was the first), and the Hermiticity assertion written to catch it
*passed* — because the zero matrix is Hermitian. The guard is now on the
spectrum: a parity observable must square to the identity, which zero does not.
The tell was `probability_range = [0.25, 0.25]`, six identical values.

Full record: `manifests/qsigma_r1k_pond_and_rain_finding.json`.

## 8.15 The storm: a sink toward stabiliser states, and two near-misses

§8.14 heralded one parity at a time. The storm is the compounding version — 200
sequential heralds, optionally **adaptive** (each measurement chosen from the
record of outcomes so far), which is the one route by which a disturbance could
accumulate rather than reset.

**The field predicts every particle event.** `p(+1) = (1 + Γ_ab)/2`, checked
against the exact amplitude calculation over all 28 mode pairs: worst
disagreement **2.2e-16**. So the entire storm — outcomes and all — is samplable
from `O(n²)` numbers. *There is no magic in what we collect either.*

**200 heralds never leave the class**, adaptive or not: worst Wick defect
**4.4e-16** and **6.7e-16** respectively, at every checkpoint. Sampling is honest
rather than post-selected — outcomes are drawn at the probability the field
predicts — so these are trajectories the experiment would actually produce.

**Where the storm goes.** Under Jordan–Wigner `i c_a c_b` is a Pauli string, so a
storm of quadratic parity heralds is *repeated Pauli measurement* — which drives
any state into the **stabiliser set**. The signature is that entropy stops being
a generic real number:

| heralds | entropy | support |
|---|---|---|
| 0 | 1.7168 | 32 |
| 5 | 1.4424 | 32 |
| 20 | **2.0000** | 16 |
| 100 | **1.0000** | 16 |
| 200 | **2.0000** | 16 |

Integers, and powers of two. The storm is a **sink**, and what it sinks to is a
stabiliser state. Gaussianity never moves; the entropy does.

### Two near-misses, both caught, in one round

**The positive control was vacuous.** A quartic herald on a post-storm `n = 4`
state fired at probability **1.000** — the state was already an eigenvector, so
the projection did nothing and the Wick defect read `1.1e-16`. Reported without
the probability, that is *"even a quartic herald cannot disturb a post-storm
state"*, which is false. **The tell is the probability, not the defect**, and a
control that cannot fire is not a control.

**Then the replacement reading was also wrong** — and wrong twice: it was one
seed, and it was `n = 4`. Across twelve seeds at `n = 4` only **1 of 36** quartic
heralds is vacuous. Across six seeds at `n = 6`, **every** post-storm state is
taken to Wick defect **1.0** by some quartic herald; at `n = 4` only 3 of 12
seeds are. The size dependence is about how *often*, not about *whether*.

Two successive readings of the same experiment were both artifacts of a single
small case. That is the sharpest methodological point of this round: catching a
bad control is not the same as having a good one, and the corrected reading needs
its own control just as much as the original did.

Full record: `manifests/qsigma_r1l_storm_finding.json`.

## 8.16 The testbed as a field: 16 modes = |GF(16)|

§8.15 ran storms at `n = 4` and `n = 6` — sizes, not geometries. At `n = 8` there
are **16 Majorana modes, and 16 = |GF(16)| = |GF(GF(2,2), GF(2,2))|**. So the
mode set is not an arbitrary index range: it carries the field structure
`gf_frames` already built, and the herald family becomes a *coordinate on a known
group* rather than a nuisance parameter.

Reaching `n = 8` needed the instruments fixed first. The Majoranas are Hermitian,
so `⟨c_j c_k⟩ = (c_jψ)†(c_kψ)` and `⟨c_a c_b c_c c_d⟩ = (c_b c_a ψ)†(c_c c_d ψ)`.
Precomputing the pair-vectors makes every correlator one inner product —
identical to the direct form to `0.0`, and `n = 8` goes from unreachable to
**0.25 s** (the pond test file from 480 s to 24 s).

### The sink depends on the rung, not on the number of pairs

Same prepared state (entropy 2.2792), same 200 heralds; only the rung varies:

| rung | pairs | final entropy | support |
|---|---|---|---|
| **T2** | 8 | **0.0000** | **1** |
| T4 | 24 | 0.0000 | 8 |
| FROBENIUS | 19 | 0.0000 | 16 |
| **M3** | **15** | **1.0000** | **128** |
| T16 | 120 | 2.0000 | 64 |
| M15 | 105 | 2.0000 | 64 |
| AGL | 120 | 2.0000 | 64 |

**`M3` has fifteen pairs and leaves the state *less* collapsed than `FROBENIUS`,
which has nineteen.** `T2` — the perfect matching, since `x ↦ x+1` is
fixed-point-free and its 8 pairs partition the 16 modes — drives the state to a
**single basis state**. The algebraic structure of the herald family decides
where the storm stops; its size does not.

Every rung leaves the Wick defect at machine zero. The storm stays Gaussian on
all seven; only the destination differs. **This measurement does not exist on an
unstructured index range** — there, the herald family is either "random pairs" or
"all pairs", with nothing between them to vary.

### The 2-flats

The 140 quadruples whose GF(16) labels XOR to zero — the 2-flats of `AG(4,2)`,
the characteristic-2 orthogonality `pg32_lines` uses one dimension lower —
against the 1680 generic quadruples, as quartic heralds:

| after storm on | 2-flat mean | generic mean |
|---|---|---|
| **T2** | **1.0000** | 0.6400 |
| M3 | 0.6379 | 0.6529 |
| AGL | 0.7200 | 0.7200 |

The field structure of the *quartic* sets shows an effect at exactly one rung —
the one whose *quadratic* family is also field-structured enough to collapse the
state to a basis state. **Suggestive, not established**: 25 samples per pool, one
seed, no error bars. Recorded because it is the first place in this arc where the
quartic index structure mattered at all.

Not claimed: any bearing on hardness. Every storm stays Gaussian; what varies is
entanglement and support, which are state properties and not simulation costs.

Full record: `manifests/qsigma_r1m_gf_ladder_storm_finding.json`.

## 8.17 The limit is the subfield tower, and the breaks are seven

§8.16 reported **endpoints**, and endpoints hide the crossing. Traced densely —
entropy at every herald, not at five checkpoints — the picture is sharper and one
of §8.16's claims does not survive.

### There is no omni rung: the ladder saturates at its middle

The union of all seven rungs is **120 pairs — exactly what `T16` alone gives**,
because translations by the 15 nonzero field elements already realise every
unordered pair `{x, x+t}`. So `T16`, `AGL` and any union are the *same* herald
family. An "all at once" storm is not a new object. The distinctions live in the
**small** rungs: T2 (8), M3 (15), FROBENIUS (19), T4 (24), M15 (105).

### The limit is the tower

`T2`, `T4`, `T16` are translation by `GF(2)`, `GF(4)`, `GF(16)` — the subfield
tower itself, nested as pair sets. Final entropy over **five seeds**:

| rung | seeds | verdict |
|---|---|---|
| **T2** = GF(2) | 0, 0, 0, 0, 0 | **collapses, 5/5** |
| **T4** = GF(4) | 0, 0, 0, 0, 0 | **collapses, 5/5** |
| **FROBENIUS** | 0, 0, 0, 0, 0 | **collapses, 5/5** |
| T16 = GF(16) | 3.0, 1.0, 1.0, 2.0, 1.0 | never |
| M3 | 2.0, 1.5, 1.0, 2.7, 1.0 | never |
| M15 | 2.0, 2.0, **0.0**, 2.0, 2.0 | once |

**Translation by a proper subfield collapses the state; translation by the whole
field never does. The break in the tower is between `GF(4)` and `GF(16)`.** The
Frobenius lift `x ↦ x²` sits with the proper subfields — consistent with its
being the generator of `Gal(GF(16)/GF(2))`, whose fixed field is the smallest.

### The symmetry-breaking moments

| rung | steps at which entropy moves | count |
|---|---|---|
| T2 | 1, 2, 3, 4, 6, 8, 10 | **7** |
| T4 | 1, 2, 4, 5, 6, 8, 10 | **7** |
| FROBENIUS | 1, 4, 6, 8, 15, 16, 25 | **7** |
| T16 / M3 / M15 / AGL | spread throughout | 48 / 56 / 48 / 48 |

**Seven breaks or forty-plus, with nothing between.** The collapsing rungs move
exactly seven times, all inside the first ten to twenty-five heralds, then are
frozen for the remaining 125 steps. The others never stop. That is the liminal
structure the endpoint table hid: a short finite sequence of breaks and then a
fixed point, versus an orbit that keeps wandering. Both end somewhere; only one
*arrives*.

### The boundary is first-order at the state level too

Escape order **1.0000** in every quartic direction, 2-flat and generic alike —
matching §8.7's operator-level result. So the 2-flat effect §8.16 recorded is
about where the state **ends up** after a collapse, not about how the boundary is
crossed.

### Correction to §8.16

That section published a seven-row table of endpoint entropies and supports as
though each were a property of its rung. **They are one draw.** `T16` ranges 1.0
to 3.0 across seeds and `M15` reaches the collapsed value once. What survives is
the collapse/no-collapse dichotomy and which rungs fall on which side — including
§8.16's non-monotonicity, since FROBENIUS robustly collapses and M3 robustly does
not despite having fewer pairs. The specific numbers do not survive.

§8.16's own remainder named this risk exactly — *"the non-monotonicity rests on a
single run of each; a seed scan would establish whether the ordering is stable;
it was not performed"* — and the scan has now been performed.

Full record: `manifests/qsigma_r1n_liminal_tower_finding.json`.

## 8.18 Breathing: the dichotomy was one point of a continuum

§8.17 reported *"seven breaks or forty-plus, with nothing between"*. That was one
point of a one-parameter family, and the family fills the gap.

A **partial** herald is `K± = cos α·Π₊ + sin α·Π₋` (α = 0 projective, α = π/4 no
measurement). It is **still exactly Gaussian at every strength** — `M = i c_a c_b`
has `M² = 1`, so `a + bM ∝ exp(tM)`, the exponential of a quadratic. Measured
Wick defect 4.3e-16 to 5.3e-16 across the whole range.

| α/(π/4) | breaks at 150 steps |
|---|---|
| 0.00 | **7** |
| 0.20 | 37 |
| 0.40 | 63 |
| 0.60 | 148 |

### And they differ in kind, not in rate

| steps | final entropy at α/(π/4) = 0.8 |
|---|---|
| 150 | 8.386e-01 |
| 300 | 6.767e-03 |
| 600 | **2.183e-06** |
| 1000 | **1.484e-08** |

The weak case decays toward zero **asymptotically and never arrives**. The
projective case reaches *exactly* zero in seven steps and freezes. The `α → 0`
limit is a decay whose rate diverges until the process becomes finite.

**Two corrections to the same sweep.** First, an apparent threshold between
α = 0.6 and 0.8 — that was the 150-step budget. Then, the fix to *that*: I read
the 600-step value as `0.0000` and recorded *"slows the collapse but does not
prevent it"*. It was **2.183e-06 printed at four decimals**. "Slower arrival" and
"never arrives" are different claims about the same numbers, and only display
precision separated them. Building the log-scale view is what caught it.

### The variable is closure, not size

| family | pairs | final S |
|---|---|---|
| T2, closed | 8 | **0.0** |
| T2 + 6 arbitrary | 14 | 2.0 |
| M15 complement | **15** | 2.45 |

Six extra pairs destroy the collapse outright — no gradual threshold. And M15's
complement has **fifteen** pairs, nearly twice T2's, and fails where T2 succeeds.
Every complement tested fails. **What collapses a state is the pair family being
closed under a subgroup**; a complement is exactly what is not closed, and
contamination breaks closure at the first added pair.

Closure is **necessary and not sufficient**: M3 and M15 are closed orbits and do
not collapse. So §8.17's open question sharpens from *"why do these three
collapse"* to *"what distinguishes T2, T4 and FROBENIUS from M3 and M15 among the
closed families"* — a better question, still unanswered.

Interactive view of all of it:
[the herald storm on GF(16)](https://claude.ai/code/artifact/869e880e-9367-4931-9ddc-efeff7edb637).
Full record: `manifests/qsigma_r1o_breathing_continuum_finding.json`.
