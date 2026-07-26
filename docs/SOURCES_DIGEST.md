# Source digest

Distilled from materials supplied 2026-07-25. **The originals are deliberately not
committed** — this file is the retained reading, not a copy. Each entry records
what the source is, what transferred into this repository, and what did not.

| source | kind | size | status |
|---|---|---:|---|
| Manifold Research Atlas v0.1 | consolidation of Rounds 30–185 | 6.2k words | **load-bearing** — see §1 |
| manifold_latest_latest_latest | raw dialogue corpus | 238k words | context; sampled, not ingested whole |
| manifold_files.zip | 22 Lean, 3 md, 1 py, 3 theses | 40 files | context; see §3 |
| Luca–Ouaknine–Worrell, *Transcendence of Hecke–Mahler series* | external, Bull. LMS 2025 | 9 pp | **external reference**, not this programme's result |
| Barannikov, *Arnold's symplectization of Picard–Lefschetz theory* | external, HSE colloquium 2019 | 11 pp | **external reference**; braid/Stokes relevance noted §4 |
| *Formalización … unidad neuronal dendro-somática* | architecture paper (ES) | 15 pp | §5 |
| 3 HTML visualisations | rendered artifacts | ~250 words each | presentation layer, no claims |

---

## 1. The Atlas — what transferred

The Atlas is the single most useful item, because it is a *governance* document
rather than a claims document, and it names an open bridge this repository is in
a position to close:

> **Epistemic governance** — Pre-registration, evidence tiers, matched nulls,
> Anti-Löb demotion, frozen ledger. *Open bridge: **institutionalize as
> executable CI policy**.*

That is now `src/aionq/governance.py`, enforced by tests. Three specifics
transferred, each fixing a real defect here.

### 1.1 The **A** tier — the category this repo was missing

This repository's ledger used P / M / H / S / R. The Atlas uses P / **A** / M /
H / S / R:

> **A — AXIOMATIZED.** Compiles because a bridge is an explicit axiom, or because
> the formalization encodes a **weaker surrogate**. *Never describe as the
> external mathematical claim being proved.*

Applying it honestly moved **five claims out of M/P and into A** — including the
headline metric:

| claim | was | now | the surrogate actually checked |
|---|---|---|---|
| `q_sim_upper` resists gaming | implied M | **A** | a compiler portfolio at opt 0–3, strictly weaker than circuit equivalence |
| `α_BG = 0.2284` gives simulation cost | implied P | **A** | an *asymptotic* exponent applied at finite t |
| breath period follows from Bennett pebbling | implied P | **A** | an ad-hoc interpolation `horizon^(log2 3/f)`, not Bennett's theorem |
| self-tomography copy count | implied M | **A** | worst-case `d²/ε²`; true complexity is rank-dependent |
| section-only holonomy defect = ∞ | claimed M | **A** | follows from *this module's* transport rule; with a real `d_conv` the loss would be partial |

This is the most valuable thing the Atlas did to this repository: it revealed
that several numbers in the README rest on surrogates, not measurements. The
qualitative results survive; the tier does not.

### 1.2 Typed remainders

Atlas formal queue, item 5:

> Give `[R]` a type every time it appears: cohomology class, empirical residual,
> scalar constant, or semantic remainder. **Prohibit untyped transport between
> them.**

This repository carried `Transport.remainder` as a bare string — precisely the
untyped case. Now `governance.Remainder` carries a `RemainderKind` and
`transport_to` raises `UntypedTransportError` across kinds.

### 1.3 Preservation over overwrite

> A corrected object receives a new version, **not an overwritten history**.
> ID scheme: `MATH-R142-ρSTAR`, `LEAN-R151-GATE`, `EXP-R183-G3`, `RET-R180-…`.

The self-review two commits ago rewrote docstrings *in place*, destroying the
record of what the claim used to say. `Claim` now carries
`supersedes` / `superseded_by` and `Registry.supersede()` refuses to delete.
Six retired claims are preserved as `RET-*` rather than removed.

### 1.4 The publication gate

> A paper may cite only P, A, M and H objects with their tags visible. S objects
> may appear in motivation or design. R objects may appear **only** in
> correction history.

Implemented as `Registry.cite(id, section=...)`, tested.

### 1.5 Independent corroboration of the holonomy result

The Atlas describes the programme's own dynamics:

> The source itself eventually recognizes this lifecycle and treats **correction
> as holonomy**: the programme returns to the same obstruction with a changed
> frame and a richer invariant.

That was reached independently here, and measured: section-only transport around
a free-theory loop is lossy, state-anchored transport closes exactly. The two
readings connect — *the correction ledger is the retained state that makes the
loop close.* A programme that keeps only its conclusions has a path-dependent
self-image; one that keeps its corrections does not. This is the one place where
the Atlas's semantics and this repository's measurement agree without either
being fitted to the other.

---

## 2. What did **not** transfer, and why

- **ρ★ ≈ 0.135**, the substrate-stable carrier density (σ-Evolve R107–R142). A
  measured constant of the SAT programme, not of this architecture. No bridge is
  claimed and none is implied.
- **Clay / P≠NP material.** The Atlas is explicit: *"No proof of P≠NP or P=NP. No
  Millennium problem is solved."* The Lean packages in the zip are recorded as
  compiling with explicit axiom boundaries — which is exactly A-tier. Nothing
  from that branch is cited here.
- **The sedenion Euler-product / RH branch.** Retired in the Atlas's own ledger
  (R94–R103: *"Euler product is not ζ; functional equation fails"*). Not used.
- **Hypercomplex complexity escape.** Retired (R137–R142: *"ρ* is
  substrate-stable; retire solver-escape claim; keep observability role"*). This
  matches the treatment of the Cayley–Dickson tower here as an *observability
  atlas*, never a computational hierarchy — arrived at independently.

---

## 3. The Lean corpus

22 `.lean` files (MHRR family, Clay packages, L56–L64 wall/sheaf/hypergraph).
Not built here — this repository has no Lean toolchain and the build was not
re-verified, so their status is **reported**, not confirmed. The Atlas's own
guidance applies: *"several bridge claims remain axiomatized, weakened, or
semantically underpowered"*, and A-tier artifacts must never be described as the
external claim. Recorded, not cited.

---

## 4. The two external papers

Both are genuine external mathematics and neither is this programme's result.

- **Luca, Ouaknine & Worrell, "Transcendence of Hecke–Mahler series"** (Bull.
  LMS, 2025). Transcendence of `Σ f(⌊nθ+α⌋)β^{-n}`. No connection to this
  architecture is claimed; listing it as support would be exactly the
  cross-domain borrowing the evidence lattice exists to prevent.
- **Barannikov, "Arnold's symplectization of Picard–Lefschetz theory, braid group
  action on Stokes data, and HMS for Fano manifolds"** (HSE, 2019). The one live
  contact point is the **braid group action on Stokes data**, which is a genuine
  sibling of the braiding in `aionq.fusion` — both are braid-group
  representations on a space of composition data. That is a structural analogy
  worth recording and **not** evidence for anything here; the fusion module's
  claims rest on its own pentagon/hexagon check.

---

## 5. The dendro-somatic neuron paper

Its executive summary states the position this architecture should adopt for its
own biological language, and states it better than this repository had:

> The most defensible way to "complete" the mesh/hyperbolic/sheaf neuron
> intuition is **not to treat it as a literal biological claim**, but as a hybrid
> architecture: a biophysically plausible multicompartmental dendro-somatic core,
> plus an **optional** geometric layer for representation and regularisation.

Read across: the geometric layer is a *representation choice that must earn its
place*, not an ontology. That is the same verdict this repository reached by
measurement when it retired the Poincaré base at δ/diameter = 0.5 — the geometry
was optional, was tested, and did not earn its place on the structure it had to
carry.

---

## 5b. Bordón respiration — a better breathing model

Pointed to directly: *"breathing is better implemented in my Bordón and Bordón
Siphony architectures."* Found in the corpus as the Galician gaita geometry:

```
puntero (chanter)   visible melody        the readable projection
bordón  (drone)     continuous harmonic   resonates, never plays the melody
fol     (bag)       pressure reservoir    the remainder [R]
pallón  (reed)      threshold / wall      where pressure becomes sound
```

It is better than `budget.py`'s periodic model for three structural reasons, and
it is a *literal* breathing instrument:

1. **The fol decouples intake from expenditure.** A piper inhales while the
   melody continues. Respiration and computation are not phase-locked. The
   periodic model forces a global stop; the reservoir model fails only when the
   bag actually runs dry.
2. **The bordón is never interrupted.** The drone is the invariant carrier and
   must be exempt from the breath cycle. The periodic model has no exemption, so
   it would exhale the very continuity that defines the organ.
3. **Channels breathe at different rates.** Respiration is polyrhythmic per
   channel, not one global period.

`src/aionq/bordon.py` implements it, and the model yields one sharp consequence
the periodic model could not state:

> **`drone_ceiling = refill_rate`.** An uninterrupted channel can be funded only
> out of steady income, never out of buffer. A reservoir of capacity 10⁶ still
> cannot sustain a drone drawing 0.5 against a refill of 0.2 — collapse is only a
> matter of time, independent of capacity.

Architecturally: an organ may spend its buffer on melody, but must fund its
identity carrier out of steady income. `budget.py` is marked superseded as a
respiration model; its ancilla accounting survives as a capacity argument.

Also noted from the same source, not implemented: **L55, the Galician drone
theorem** — *"the left side reads the right side without influencing it;
`pipe_immunity` formalizes that [R]_left ≠ [R]_right — they are incompleteness
classes of different formal systems."* That is a typed-remainder statement in the
sense of §1.2, and a sharper one than this repository has: it says two remainders
may be structurally incomparable because they belong to different formal systems,
not merely to different kinds. Recorded as the next remainder-typing target.

---

## 5c. Round V1 — two more Atlas instruments, implemented and run

### The visibility probe / coupling field `g_r`

The Atlas's **surviving late positive**: *"certified global structure can be
extensively present while remaining weakly coupled to bounded local inference."*
That is a SAT statement and no bridge to it is claimed. The **instrument**
transfers, and this repository had nothing like it.

Quantum form (`src/aionq/visibility.py`), exact for stabilizer states:

```
g_r = (n − rank(S_r)) / n,     S_r = <{s ∈ S : |s| ≤ r}>
```

**A wrong first attempt, kept in the module docstring.** The obvious construction
bins Pauli *weight* and calls weight > r invisible. Measurement killed it in one
shot: `|+⟩^6` scored `g₁ = 0.891` when it must score 0, because
`⟨X₁X₂⟩ = ⟨X₁⟩⟨X₂⟩` is 1-locally *determined* despite being weight 2. Weight is
not visibility. Retired as `RET-V1-WEIGHT_IS_VISIBILITY`.

**Round V1 results** (pre-registered in `experiments/run_visibility.py`):

| prediction | verdict |
|---|---|
| P1: `g_r = 1/n` exactly for `1 < r < n` on GHZ_n, n=3..9 | **survived** |
| P2: `r* = d` on the `[[n,1,n]]` repetition family | **survived** |
| P2 generalised: `r* = d` for any stabilizer code | **FALSIFIED** |
| control: random Cliffords track n | **survived** — slope 0.310, so the result is informative |

GHZ_n hides **exactly one** stabilizer generator from every probe of depth
`r < n` — no more, no less. But Steane `[[7,1,3]]` has `r* = 4` while `d = 3`:
its weight-3 elements have GF(2) rank 4 of 7, and the weight-4 checks are needed
to complete the group. `[[5,1,3]]` gives `r* = 3 = d`, and the repetition family
gives `r* = n = d`, so the coincidence is real but not a law.

> **Corrected reading:** `r*` is the minimum *generating weight* of the
> stabilizer group. Distance is the weight of the *lightest logical operator*.
> Neither determines the other.

En route, a hand-written Steane encoder stabilized none of the Steane generators
and produced a spurious falsification. Generators are now supplied explicitly and
checked to commute — the apparent result was a circuit bug, and it is recorded
rather than quietly deleted.

Architecturally this finally makes measurable a tension flagged in round 1 and
never implemented: **high `g_r` is exactly protection and exactly inertness.** An
organ invisible to local probes cannot be locally read or acted upon.

### The Cayley–Dickson failure ladder — replication at depth (Round V2)

The Atlas reports ‖A‖: 𝕆 ≈ 0.359, 𝕊₁₆ ≈ 1.356, 𝕋₃₂ ≈ 1.4. Round V1 measured
these from a single seed with no interval; Round V2 re-ran them with 8 seeds ×
20,000 samples, exhaustive enumeration where feasible, and bootstrap intervals.

**Basis-triple convention** (the one that fits 𝕊₁₆):

| rung | measured | 95% CI | Atlas | |
|---|---:|---|---:|---|
| ℝ, ℂ, ℍ | 0 exactly | — | 0 | ✅ |
| 𝕆 (dim 8) | **1.6000** | exhaustive | 0.359 | ❌ |
| 𝕊₁₆ (dim 16) | **1.3538** | exhaustive | 1.356 | ✅ |
| 𝕋₃₂ (dim 32) | **1.1815** | [1.1719, 1.1912] | 1.400 | ❌ |

**Random-unit convention:** 1.0929 [1.0879, 1.0984] / 1.3123 [1.3096, 1.3148] /
1.3777 [1.3753, 1.3801] — misses **all three**.

> **Exactly one of the three reported nonzero values replicates, and only under
> one convention.** No single convention reproduces the ladder.

Two corrections to what Round V1 reported. The dim-32 value was called "close to
1.4" on the strength of the random-unit figure 1.377; under the convention that
actually fits 𝕊₁₆ it is **1.1815, which does not match**. And the V1 dim-8
random-unit point estimate 1.103 falls **outside** the tighter V2 interval
[1.0879, 1.0984] — a single seed was not enough.

The dim-8 and dim-16 figures are **exhaustive**, so no interval can reconcile
them: this is not a sampling question. What replicates exactly is the
**qualitative** ladder — associativity fails first at 𝕆, zero divisors appear
first at 𝕊₁₆. Reported as a question for the source, not a correction to it.

### Round V2: the control, re-measured

The V1 control slope 0.310 came from 7 group means of 6 seeds each, fitted with
no error propagation. At 200 seeds per width (n = 1,400) with the bootstrap
resampled *within* groups:

```
slope = 0.3200 per unit width  [0.3059, 0.3341] 95% CI
tracks n (CI above 0.8)?  False        distinguishable from zero?  True
repetition vs control at n=9: Δ = +4.915 [+4.870, +4.955], Cohen's d = 22.2
```

The V1 point estimate falls inside the interval, so the conclusion survives — but
it had no interval when it was used to justify the conclusion. Random-Clifford
`r*` does grow with width, just at roughly a third of the 1:1 rate, and the
separation from the repetition family is enormous rather than marginal.

---

## 5d. NN Disk — the premise corrected, and the real bridge (Round V3)

The NN Disk archive (`nnn-hyperbolic-ramdisk_v2`) was offered as possibly
pertinent on the grounds that it is *"based in GF(2) in a (2,2) approach."*

**The literal reading does not hold.** That codebase contains **no GF(2)**. Its
geometric plane uses the *real* quadratic form `Q(x) = x₀²+x₁²−x₂²−x₃²` with
SO(2,2) acting on the `Q=+1` pseudo-sphere — signature (2,2) over ℝ. GF(2) is
the two-element field. Different objects; conflating them is the borrowing this
repository's lattice exists to prevent.

**But the structure you sensed is there, and it is sharper than the wording.**
Both are **split forms** — orthogonal sums of *hyperbolic planes* — over
different fields:

| | field | decomposition | verified |
|---|---|---|---|
| NN Disk (2,2) | ℝ | `Q ≅ uv + st` — **two** hyperbolic planes | gram in split basis is block off-diagonal, exact |
| this repo's stabilizer space | F₂ | `F₂^{2n} ≅` **n** hyperbolic planes, one per qubit | n = 2,3,4 exact |

Signature (2,2) *is* the split form in dimension 4: `x₀²−x₂² = (x₀+x₂)(x₀−x₂)`
is a hyperbolic plane, and so is `x₁²−x₃²`. SO(2,2) is **the split orthogonal
group**. The stabilizer phase space is the F₂ analogue. Same classification
concept, two fields — not an analogy.

### It paid for itself immediately: a Round V1 claim was wrong

Finding the hyperbolic planes of a code's phase space is *how you find its
logical qubits* — and hence its distance. `aionq.splitform` does that, and
computing `d` instead of reading it off a name **falsified my own Round V1
result**:

| code | r* | d *computed* | r* = d? |
|---|---:|---:|---|
| repetition n = 3, 5, 7, 9 | 3, 5, 7, 9 | **1, 1, 1, 1** | ✗ |
| Steane [[7,1,3]] | 4 | 3 | ✗ |
| Perfect [[5,1,3]] | 3 | 3 | ✓ |

Round V1 scored P2 as **survived** on the repetition family. It isn't. The
bit-flip repetition code has stabilizer distance **1 for every n**: `Z₁` commutes
with every `Z_iZ_j` check and is not in the stabilizer group, so it is a weight-1
logical. `[[n,1,n]]` is the *X-distance* convention. Verified independently
before accepting.

> **`r* = d` now holds in 1 of 6 cases, and that one is a coincidence.** The
> corrected reading — `r*` is the minimum generating weight, distance is the
> lightest logical, neither determines the other — is unchanged but now rests on
> computed distances rather than on code names.

So: the stated premise was wrong, the underlying instinct was right, and acting
on it retired one of this repository's own claims.

---

## 5e. Σ∞ thesis — running its own pre-registered kill condition (Round S1)

The Σ∞ thesis (29 pp, verified against the pasted text) rates itself honestly in
its own Appendix B:

> *"Σ∞ is a falsifiable architecture specification — **H**. Becomes **M** only
> after implementation and controlled experiments."*

and §16 pre-registers four experiments **with kill conditions**. This repository
is the machine for exactly that, so Round S1 implements the most concrete new
operator — the **Transcendence Sentinel** (§13, from Luca–Ouaknine–Worrell) — and
runs the thesis's own experiment 3 against its own stated kill condition:

> *"Kill condition: conventional change-point or compression methods match the
> result under equal tuning and cost."*

Four stream classes × 120 each, all methods sharing the identical recurrence
filter and residual preprocessing:

| method | mean AUROC (target vs each other class) |
|---|---:|
| Sentinel | 0.865 |
| Change-point (CUSUM) | 0.754 |
| **Compression (gzip MDL)** | **1.000** |

> **The kill condition is met. The Sentinel is RETIRED** (`RET-S1-TRANSCENDENCE_SENTINEL`).
> A gzip ratio on the same residual separates the four classes perfectly, where
> the sentinel reaches 0.865. The module and experiment are kept so the negative
> result stays reproducible.

**A methodological catch that reversed the verdict.** The first run scored
compression at AUROC **0.000** and I nearly reported the sentinel as surviving.
But 0.000 is *perfect separation with the decision rule inverted*, not failure.
Polarity was never pre-registered for the baselines, so scoring them
one-directionally handicapped them. Giving each method its best direction — the
reading most favourable to the *null*, which is what a kill condition requires —
flips compression to 1.000 and kills the sentinel.

**A second finding, on the transport itself.** The sentinel's only residual
signal (expanding-gap vs fixed-rate, AUROC 0.595) is carried by the
*magnitude-variation* component — **not** by gap expansion. Gap expansion is the
part actually imported from Hecke–Mahler, and it fails to order individual
streams reliably: the recurrence filter smears each isolated anomaly across
several residual positions, so fixed-rate streams frequently show a *higher* gap
slope than expanding-gap ones. So even the weak surviving signal is not coming
from the imported structure. Locked by
`test_gap_expansion_alone_does_not_order_the_classes`.

This is the thesis's own governance working as designed — an S-tier transport
proposed with a kill condition, implemented, and killed. The Hecke–Mahler paper
remains what §13 says it is: an inspiration, not a transferred theorem.

---

## 5f. Σ∞ §16 experiment 4 — the Stokes-Thimble Router (Round S2)

§12 predicts the router *conditionally*: mutation helps **"only when the
transition truly changes basis."** That conditional is the real test, so two
regimes are generated — one where the latent basis mutates by a unipotent Stokes
matrix, one control where only the coefficients move.

| regime | router | mixture | Δ (router − mixture) |
|---|---:|---:|---|
| **A** basis truly mutates | 0.0169 | 0.0165 | **+0.0004 [−0.0060, +0.0065]** — not significant |
| **B** control, weights only | 5.7870 | 0.0101 | **+5.777 [+4.75, +6.91]**, d = 1.88 — fails |

Four things follow, and they don't all point the same way.

1. **The kill condition as written is met.** *"A standard gated mixture matches
   all metrics"* — on MSE in regime A, it does. `RET-S2-STOKES_ROUTER_ACCURACY`.
2. **But the comparison is not apples-to-apples.** The router reaches parity
   **zero-shot** — it never sees regime-2 labels, carrying a regime-1 fit across
   by the declared mutation — using **6 parameters against the mixture's 14**.
3. **The conditional pattern holds exactly.** It matches where the basis genuinely
   mutates and collapses to fixed-basis performance in the control, which is what
   §12 predicts and what pure extra capacity would *not* produce.
4. **Half the prediction was not tested.** §12 also predicts an *interpretability*
   gain. I measured MSE. The router does carry an auditable `MutationRecord` with
   provenance, but no interpretability metric was run, and I am not going to
   claim a result I did not measure.

The load-bearing caveat: **the mutation matrix is supplied, not learned.** The
router is told where the crossing is and what it is. So this shows a declared
basis change transfers a model zero-shot — not that a system could *find* the
crossing. That is the gap between this result and the architectural claim.

An earlier version of the script refit the router in the control but not in
regime A, which would have flattered it. Corrected to zero-shot in both.

---

## 6. Net effect on this repository

1. `src/aionq/governance.py` — evidence lattice, typed remainders, immutable
   claim IDs, supersession, publication gate. 8 tests.
2. Five claims retagged **M/P → A**, with their surrogates stated.
3. Six retired claims preserved as `RET-*` instead of deleted.
4. `docs/ARCHITECTURE.md` evidence ledger updated to the six-tier lattice.
5. `src/aionq/bordon.py` — reservoir respiration replacing the periodic breath
   model, with `drone_ceiling = refill_rate` as its one sharp consequence.
6. `src/aionq/quantities.py` — the typed coordinates moved out of `stack.py` so
   the Atlas can actually import them (D15).

Nothing in the supplied corpus changes any measurement in this repository. What
it changes is the *tier* several of those measurements are entitled to claim.

---

## 5g. Σ∞ §16 experiment 1 + the QΣ query claim — sheaf obstruction localisation (Round S3)

§16's **first** pre-registered experiment, and the one the QΣ ("Quantum
Polycosmic Sheaf Memory") proposal names as its own first experiment, are the
same experiment seen from two sides. Round S3 runs both.

> *"Construct a synthetic multi-world task with known local sections, overlap
> inconsistencies, and hidden cycle obstructions. Compare scalar, graph, sheaf,
> quaternionic, octonionic, and randomized coordinate systems on obstruction
> localization … Kill condition: any advantage disappears under dimension- and
> compute-matched controls."*

> *"Four worldlets, two overlap cycles … test whether quantum interference
> identifies a hidden cycle obstruction using fewer oracle queries or with
> greater diagnostic resolution than matched classical … baselines."*

**The object.** A nerve of worldlets; an orthogonal transition per overlap; the
holonomy round a cycle is the obstruction. The generator builds a **consistent**
sheaf first — an exact coboundary `a_ij = g_j g_i⁻¹`, so every cycle has holonomy
exactly `I` — and then swaps the transition on hidden overlaps for another drawn
from the same distribution. **No overlap is locally anomalous** (locked by
`test_no_overlap_is_locally_anomalous`: in the Q₈ regime every transition,
defective or not, is `L_q` for some `q ∈ Q₈`). Only the loop reveals the defect.

**The discipline that makes it a test.** All eight instruments receive the same
nerve, the same fundamental cycle basis, and the same crude blame-spreading rule.
Only the *coordinate system* varies. Compute is reported as a ratio, not asserted
— and that caught a real defect: the quaternionic instrument was rebuilding its
projection basis per edge, running at **131× the matrix instrument**, which would
have violated the compute half of the kill condition while the experiment was
busy checking the dimension half. Cached, it runs at 13× (the projection is
genuinely more arithmetic than a matrix product at d = 4) and the result is
unchanged.

### Localisation, 300 trials, 8 worldlets, 13 overlaps, 2 hidden defects, d = 4

| instrument | AUROC, generic O(4) | AUROC, Q₈ / order-sensitive |
|---|---:|---:|
| graph (topology only) | 0.508 [0.486, 0.531] | 0.501 [0.478, 0.525] |
| scalar (tr G / d) | 0.513 [0.488, 0.538] | 0.507 [0.483, 0.532] |
| character (det) | 0.660 [0.643, 0.676] | **0.500 [0.500, 0.500]** |
| shuffled overlaps | 0.511 [0.485, 0.537] | 0.494 [0.468, 0.520] |
| quaternion | 0.566 [0.543, 0.590] | 0.714 [0.701, 0.726] |
| octonion | 0.797 [0.785, 0.809] | 0.714 [0.701, 0.726] |
| associator channel | 0.500 [0.500, 0.500] | 0.500 [0.500, 0.500] |
| **sheaf** | **0.797 [0.785, 0.809]** | **0.714 [0.701, 0.726]** |

**(a) The sheaf clause survives.** sheaf − shuffled = **+0.286 [+0.258, +0.316]**,
d = 1.60; sheaf − graph = **+0.289 [+0.264, +0.315]**, d = 1.82, n = 300. Same
dimension, same arithmetic, same attribution — the advantage is the coordinate
system. `EXP-S3-SHEAF_LOCALISATION`. This is the first clause of a Σ∞
pre-registered prediction that has *not* been killed.

**(b) The hypercomplex clause is killed — by a tie, not a loss.** The predicted
*shape* reproduces exactly:

| | quaternion − sheaf |
|---|---:|
| generic O(4) | **−0.231 [−0.257, −0.204]**, d = 1.39 |
| Q₈, its home ground | **+0.000 [−0.018, +0.017]**, n.s. |

Projecting an O(4) transition to its nearest unit quaternion discards two of six
parameters, and it costs exactly what you would expect. On genuinely quaternionic
structure the projection is exact and the instrument is *identical* — not
approximately, the AUROC difference is 0 to machine precision, because it is
recomputing the same holonomy in isomorphic coordinates. The thesis says
hypercomplex coordinates "may improve diagnosis" there. **They do not improve
anything; they tie.** Under the thesis's own kill condition — advantage vanishes
under matched controls — that is a kill: `RET-S3-HYPERCOMPLEX_DIAGNOSIS`. What
survives is the weaker, true statement, kept because it is still worth knowing:
*they cost nothing on their home ground and a great deal off it.*

**(c) One instrument is blind for a reason no experiment could fix.** The `det`
character reads 0.500 with a **zero-width interval** in the Q₈ regime. That is
not a measurement. Every `L_q` lies in SO(4), whose abelianisation is trivial, so
`det(H) = 1` identically on defective and clean cycles alike — the injected
element is `−1 ∈ [Q₈, Q₈]`, and characters annihilate commutators. No sample
size, tuning or noise model can rescue a homomorphic scalar coordinate here.
`MATH-S3-CHARACTER_BLIND`, tagged **P**, not M. Note the contrast with the
generic column, where the same instrument reads 0.660: the abelian shadow is not
useless in general, only where the algebra forbids it.

### (d) The octonionic clause is not falsified — it is ill-posed

This is the round's sharpest finding, and it was not what I set out to measure.
I tried three times to build a "clean" octonionic sheaf to measure a defect
against, and each attempt had nonzero holonomy everywhere. The reason is
structural, and it is the whole story:

> A vertex gauge `a_ij = g_j g_i⁻¹` induces a **flat** connection — holonomy `I`
> on every cycle — **iff left multiplication is a homomorphism**, `L_a L_b = L_ab`.

Measured on clean sheaves with **no defect anywhere**:

| algebra | dim | mean ‖H − I‖_F |
|---|---:|---:|
| real | 1 | 0.000000 |
| complex | 2 | 0.000000 |
| quaternion | 4 | 0.000000 |
| **octonion** | **8** | **3.188684** |
| sedenion | 16 | 5.246638 |

Above the quaternions **there is no zero for a defect to stand out against**.
Unit octonions form a **Moufang loop, not a group**, and sheaf cohomology needs a
group; `H¹` is not defined. By Artin's theorem any two octonions still generate
an associative subalgebra, so the failure begins exactly at cycles mixing three
independent directions. `MATH-S3-NO_FLAT_ABOVE_H` (**P**);
`RET-S3-OCTONIONIC_SHEAF` (**R**).

This is a stronger objection than a failed experiment, and it cuts at the
architecture rather than at one instrument: **§16's octonionic clause cannot be
run as written.** The related C4 claim — hypercomplexity as order-sensitivity —
is untouched; order-sensitivity is a fact about *products*, and it survives. What
does not survive is octonionic *sheaf cohomology*.

### (e) The QΣ query claim: proved, and bounded three ways

The proposal asks whether quantum interference reads the obstruction in fewer
oracle queries. It does, and the answer needs no experiment.

Holonomy is linear over F₂, and its kernel is the cut space. So the observable is
exactly `b = E − V + C` bits — coboundaries are unobservable *by definition of a
cohomology class* — and:

- **classical: exactly `b`** queries. Lower bound: one bit per query against `b`
  bits of class, for deterministic and bounded-error strategies alike. Upper
  bound: query a cycle basis.
- **quantum: exactly 1.** Bernstein–Vazirani, with certainty.

`MATH-S3-BV_QUERY_SEPARATION` (**P**). Three things bound what it means, and all
three are in code so they cannot be dropped from a summary:

1. **The proposed instance is underpowered by construction.** Four worldlets, two
   overlap cycles gives `b = 2`: a factor of two, with no room for an interval.
   The separation needs cycle rank to grow — at V = 12, E = 18 it is 7×.
2. **The oracle must already be coherent.** Building it from classical worldlet
   data reads every overlap: `E` accesses, which *exceeds* `b` on every instance
   tested. Ratio with construction: **0.33×** — i.e. negative advantage.
   `oracle_construction_cost` is a function, not a footnote. The one way out is
   an architecture whose memory *is* the oracle rather than a thing built from
   reads, registered as `BRIDGE-S3-COHERENT_ORACLE` (**H**) with its kill
   condition attached.
3. **Reading the class is not localising the defect.** Interference returns
   `t = Cs`. *Which overlap* is twisted is the minimum-weight coset
   representative — syndrome decoding, NP-hard in general, and **identical for
   both parties** after the quantum step has finished. The proposal says
   "identifies a hidden cycle obstruction", which is the class; if the edge is
   what is wanted, the advantage stops one step short.

**Measured: what noise does.** One coherent query is worth `b` classical queries
only while it succeeds. Pauli-twirled depolarizing at rate p on every qubit after
each of three layers, 500 trials; crossover is the smallest p at which the
expected coherent cost `1/p_success` first exceeds `b`:

| cycle rank b | 2 | 4 | 6 | 8 | 12 |
|---|---:|---:|---:|---:|---:|
| crossover p | 0.165 | 0.170 | 0.140 | 0.125 | 0.105 |

Flat to `b = 6`, then falling — which is what the arithmetic requires, since
`1/p_success` grows exponentially in `b` while the classical cost grows only
linearly, so tolerable noise must decay like `log(b)/b`. The advantage is
**asymptotically fragile while looking comfortable at exactly the sizes a
proposal is most likely to quote**. `EXP-S3-BV_NOISE_CROSSOVER`. And the
crossover is an *upper* bound: `1/p_success` assumes a correct run can be
recognised for free, which it cannot.

### What Round S3 changes

The first Σ∞ prediction to survive its own kill condition (the sheaf clause), the
first to be killed by a *tie* rather than a loss (hypercomplex), the first
architectural clause found **ill-posed rather than false** (octonionic), and the
first quantum-advantage claim in this repository that is real, proved, and
smaller than it looks. Four findings, no two pointing the same way.
