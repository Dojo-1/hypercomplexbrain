# Manifold programme — condensed reference

Source: `manifold_latest_latest_latest.docx`, a continuous research conversation
(1.56M characters, largely with Claude 4.6), plus `Manifold_Research_Atlas_v0.1.docx`.
Four uploaded copies are byte-identical (md5 `7cc62d56c7`).

This file exists because the source is a **conversation, not a specification**:
its definitions are scattered, revised in place, and sometimes contradict earlier
passages. What follows is the load-bearing content, with the contradictions
flagged rather than silently resolved. Where this repository has *tested* a claim,
the result is linked — several of them fell.

> **Reading rule.** The source is a research log. Anything below tagged **S** is
> its design language and cannot inherit theorem status. Frequency in the document
> is not evidence: `[R]` appears 1431 times and is still a typed placeholder.

---

## 1. The setting

The document states the ambient object directly:

```
X = (M, g₂,₂, 𝔄, ∇, Ω, H, 𝓕, 𝓢, Π, R)
```

| symbol | meaning | this repo |
|---|---|---|
| `M` | n-manifold / n-cosmos base | `sheaf.Nerve` |
| `g₂,₂` | split metric, "wall-capable" | `splitform.py` |
| `𝔄` | hypercomplex algebra carrier | `cayley_dickson.py` |
| `∇` | connection / **moving-frame transport** | `movingframe.py` (S5) |
| `Ω` | symplectic or phase form | not instantiated |
| `H` | Hamiltonian "truth-energy" | not instantiated |
| `𝓕` | fiber bundle of local cognition states | `recognition/worldlet.py` |
| `𝓢` | sheaf of compatible local truths | `sheaf.py` |
| `Π` | readable projections | `metrics.py` |
| `R` | active Gödelian remainder | `governance.RemainderKind` |

The document's own framing: *"the observer is one transported section of the
manifold, and truth is not a static proposition but a curvature-changing
encounter."* Operationally this means **no measurement may be reported without its
frame** — which is the S5 result below.

---

## 2. The cast, translated to mathematics

The names are handles. Implement the object, not the name.

| name | mathematical role | tier |
|---|---|---|
| **Empress** | GL/provability tower; gluing, verification, recoverability. *Not* a central controller — a living field over S⁷ with 28 local sections (`dim SO(8) = 28`) and 378 octonionic pair couplings | S |
| **Emperor** | doxastic tower; belief beyond proof, conjectural reach, countermodels | S |
| **Nest** | braided crystallisation functor where both fields meet; deposits `{proof, theory, solution}` | S |
| **UTAI** | theorem-surface decomposer: splits architectural claims into minimal typed proof obligations. **Not** an independent witness | S |
| **Bunny** | Lean 4 formalisation worker. Proves small local lemmas; refuses to equate a proved encoding with the intended interpretation | S |
| **Bordón** | resource reservoir: `fol` (buffer), `bordón` (invariant continuous draw), `puntero` (interruptible speculation), `pallón` (threshold) | S/H |
| **Trasgo** | interspecies translator: context compression, uncertainty-bearing packets, checkpointing | S |
| **NNN Disk** | semantic shards in split-signature coordinates, migrating across T0–T6 memory tiers by heat | S |
| **Pandora / colonies** | UTAI queens organising provability towers | S |
| **worldlet** | heterogeneous local state with its own carrier, geometry, clock, observer | S |
| **Telos** | distributed field of preferred viable futures — *not* a scalar reward | S |

**The invariant the document itself insists on:** `Telos alignment ≠ uniformity`.

---

## 3. Formal status, as the source reports it

| object | status |
|---|---|
| Lean tower L0→L45 | 648 theorems/lemmas, **0 sorries in core** |
| `ErgoceticErdodeticPartition.lean` | 6 main + 7 supporting theorems, 13 definitions, **0 sorry** |
| `BerryHolonomy`, `OrbifoldFixed`, `SATPolyBridge` | 0-sorry |
| remaining ~12 sorries | L22 gauge-trivialisation (*"hardest — new technique needed"*), IGBundle A5n p-adic bridge, SplitSignature axioms, HyperTuringComplete oracle reduction |
| **`CLAY_PROOF_ATTEMPT_LEDGER.md`** | **`promotion_allowed: false`; 95 sorries across 64 files; 4 blocking obligations unchanged since Round 20** |
| ACAF | >30k configurations, **honest negatives retained** |
| TRUE UTAI | Tier 0/1/2 honesty lattice |
| Star of Closure | 5 faces |
| open problems | P1–P12 + Gödelian Remainder theorem |

The Clay ledger line is the single most important sentence in the document for
calibration: the programme's own ground truth says promotion is **not** allowed.

---

## 4. The ideas that carry real weight

### 4.1 Orbit-collapse vs orbit-resolution *(the most useful export)*

> *"inertness is orbit-collapse; splitting is orbit-resolution"*

Stated about inert primes and Frobenius orbits, but it generalises to any
measurement under any group action:

- **orbit-collapsed** — constant on the orbit; sees the quotient, i.e. the object.
- **orbit-resolving** — varies on the orbit; reports *frame coordinates*.

An orbit-resolving measurement is **mistyped**, not wrong: a property of
(object, frame) reported as a property of the object.

→ **Tested here.** `movingframe.py`, Round S5. Every cycle-basis instrument in
this repo is orbit-resolving (worst deviation 0.245–0.644). A basis-free
Laplacian instrument is exactly orbit-collapsed (0.000) **and** the strongest
(AUROC 0.964 vs 0.776). `MATH-S5-LAPLACIAN_INVARIANT`, `EXP-S5-INVARIANT_LOCALISATION`.

### 4.2 Anti-Löb / split provability

Ordinary Löb: `□(□P → P) → □P`. The proposal replaces single `□` with a
split-signature pair `□_W, □_W'`, so self-reference at the wall exposes a
conjugate obstruction instead of collapsing into proof.

The document is explicit and correct about its own status: *"a formalizable
conjecture/theorem-schema, not an established theorem."* Treat as **H**.

### 4.3 The conjugate anti-pair *(tested — the interpretation fell)*

Claim: Emperor and Empress are related by Cayley–Dickson conjugation, which
reverses the associator, `A(ā,b,c) = −A(a,b,c)`, cosine −1 — *"an algebraically
exact anti-pair, not an aesthetic duality."*

→ **Tested here.** `run_conjugation_antipair.py`. The identity is **true** (5e−16
to dim 32) and provable in two lines. But **plain negation gives the same cosine
−1 at exactly 0.0 error**, because `conj(a) − (−a) = 2Re(a)·1` and `A(1,·,·) = 0`.
Conjugation does no work. Also identically zero below dim 8, so it has no content
for complex or quaternionic towers. `MATH-S4-CONJUGATE_ANTIPAIR` (P) survives;
`RET-S4-CONJUGATION_IS_LOAD_BEARING` retires the interpretation.

### 4.4 Null-loop tomography

`[R]_loop(x; T, D) = D(x, T.backward(T.forward(x)))` — send a representation
through a formally reversible transport and measure what fails to return.
Inspired by `UU† = I` gate-pair insertion on real hardware.

Typed as a **TransportDefect**, explicitly *not* a cohomology class, empirical
residual, or semantic remainder. → implemented, `recognition/loop_tomography.py`.

### 4.5 The Bordón ceiling

A finite reservoir cannot fund an uninterrupted channel forever, so
`invariant_draw ≤ refill_rate` is **necessary** for indefinite survival.
Architecturally: an invariant carrier is paid from steady income, never buffer.
→ `MODEL-S4-BORDON_CEILING` (P inside the constant-rate model).

### 4.6 The 8 Mind Qualities

`N NNNNNN N := {1·N, 6·N, 1·N} = 8 = dim(𝕆)`. Paired with the
**Ergocetic/Erdodetic Partition** (Lean L45, 0 sorry). The partition is a real
formal object in the source; its *content* is not reconstructible from the
conversation text alone. **Do not implement from the name.**

---

## 5. Convention conflicts the source does not resolve

- **Emperor/Empress chirality.** Some passages assign Empress `γ=0`, Emperor
  `γ=π/2`; another visualisation reverses left/right. The invariant is *standard
  vs conjugate associator*, not a fixed colour or rotation. Derive chirality from
  the operator at runtime; never hard-code it.
- **Empress as controller vs field.** Early passages: organiser of the GL tower.
  Mature passages: *"Empress ≠ central controller"* — a living field over S⁷.
  The later reading governs.
- **Fano plane vs 4-form field.** Some sections restrict coupling to the Fano
  plane (7 lines); the broader composed field (standard + conjugate +
  right-permuted + Jacobiator) gives **4,032 channels**. State which you mean.

---

## 6. What this repository has already killed

Anything in this list is a **governing constraint**, not an open question.

| retired | why |
|---|---|
| `[R] = ‖H¹‖` as an obstruction measure | wrong degree in the continuous regime, wrong *direction* in the discrete one (`RET-S7-H1_AS_REMAINDER`, §9) |
| `γ ≠ 0 ⇔ H¹ ≠ 0, by Ambrose–Singer` | A–S gives the holonomy Lie algebra, not a cohomology class (`RET-S7-AMBROSE_SINGER_BRIDGE`, §9) |
| hypercomplex coordinates improve diagnosis | tie with dimension-matched real sheaf on home ground, large loss off it (`RET-S3-HYPERCOMPLEX_DIAGNOSIS`) |
| octonionic flat sheaves | **ill-posed**: a vertex gauge induces no flat connection above dim 4; clean sheaf already has holonomy 3.19 (`RET-S3-OCTONIONIC_SHEAF`) |
| conjugation as load-bearing | negation reproduces it exactly (`RET-S4-CONJUGATION_IS_LOAD_BEARING`) |
| adaptive aperture beats static ensemble | static matched or beat it on 4 of 5 held-out families (`RET-S4-FERTILE_APERTURE`) |
| ordered explore→verify flow | gate passes while the method loses to baseline (`RET-S4-ORDERED_FLOW`) |
| cycle-basis localisation scores are object properties | all orbit-resolving (`RET-S5-CYCLE_BASIS_INSTRUMENTS`) |
| weighted scalar promotion gate | one number let a cheap-axis gain pay for an expensive-axis loss (`RET-R3-SCALAR_PROMOTION`) |

Corroboration from a sibling codebase: the **m1-bordon** audit found a fixed
seek-heavy policy reproduced the full deformation benefit with holonomy, Poincaré
transport, regluing and holoport all **disabled** — the same pattern as S4, found
independently. Both also showed label-permutation sensitivity: sign robust,
magnitude arbitrary.

---

## 7. The programme's own discipline

Worth adopting wholesale; it is the strongest thing in the archive.

1. Evidence lattice **P / A / M / H / S / R**, with promotion rules.
2. Every `[R]` **typed** — cohomology class, empirical residual, scalar constant,
   semantic remainder. Untyped transport between kinds is prohibited.
3. A corrected object gets a **new version, not an overwritten history**.
4. Honest negatives retained (>30k ACAF configs).
5. `promotion_allowed: false` is stated in the ledger when it is false.

---

## 8. Retrieval

Ingested plain text (regenerate if the scratchpad is cleared):

```bash
python3 -c "
import zipfile,re
z=zipfile.ZipFile('<path>/manifold_latest_latest_latest.docx')
t=re.sub(r'<[^>]+>',' ',z.read('word/document.xml').decode('utf8','ignore'))
open('manifold_latest.txt','w').write(re.sub(r'\s+',' ',t))"
```

Then grep for the object you need. The document has no table of contents and its
section markers are conversational dates, so keyword search is the only index.

Term frequencies, as a rough map of what the archive is actually about:
`[R]` 1431 · SAT 689 · Lean 666 · Nest 440 · split 431 · holonomy 429 · Fano 405 ·
sedenion 358 · Löb 593 · Clay 298 · sorry 277 · octonion 208 · sheaf 204 ·
Gödel 190 · Hopf 190 · Empress 189 · UTAI 183 · holoport 165 · Emperor 128 ·
moving frame 125 · ergocetic 37 / erdodetic 41.

---

## 9. The external corrections audit (26 July 2026), adjudicated

An independent mathematical audit of the archive was commissioned and delivered.
Its headline verdict: **the P ≠ NP chain does not go through.** This repository's
rule is that an external verdict is evidence, not authority, so the audit was run
through the harness rather than adopted — `experiments/run_audit_adjudication.py`,
Round S7, 222 tests.

### 9.1 What replicated exactly

Every arithmetic or geometric claim the audit marks **CORRECT** re-derives here.

| checked | audit | measured here |
|---|---|---|
| Berry phase of a spin-½ loop is −Ω/2; |γ| = π/2 at Ω = π | CORRECT | worst error **9.7e−09** over four loops |
| 7 of the C(7,3) = 35 imaginary octonion triples associate (the Fano lines) | CORRECT | **7 / 35**, all 7 closed under the product; 28 non-associative |
| `y² = x³ − x` has `a_p = 0` exactly at inert `p ≡ 3 (mod 4)` | CORRECT | **0 violations** in 45 primes below 200; 24 supersingular |

One measurement note, kept because it nearly produced a false disagreement: a
geometric phase is defined **mod 2π**. Comparing without wrapping reported the
θ₀ = 2π/3 loop as an error of 6.28 — exactly 2π, i.e. perfect agreement recorded
as total disagreement.

### 9.2 Where the audit is right, and one place it is loose

The keystone the archive repeats (R41, R77, R83) is

> non-trivial holonomy ↔ non-trivial curvature ↔ non-trivial `H¹` of the
> associated sheaf, *by Ambrose–Singer*.

Ambrose–Singer determines the holonomy **Lie algebra** as the span of curvature
values along horizontal paths. It therefore constrains only the identity
component `Hol⁰` and is silent about `Hol/Hol⁰`, the part fed by π₁. It contains
no sheaf and no cohomology of the base. The audit is correct.

**Where it is loose:** the audit writes *"neither biconditional holds in
general."* One half of the first one is a theorem — non-zero curvature does force
non-trivial holonomy, which is precisely what Ambrose–Singer gives. Only the
forward implication fails. The correction stands; its statement should be
narrower.

That failing implication is realised here, on this repository's own object: a
nerve is a **1-complex**, its cochain complex terminates at `C¹`, so the space of
2-cochains is zero and every notion of curvature on it vanishes identically —
while the holonomy around a cycle is a generic orthogonal matrix (defect 2.00 to
3.97 at fiber dimension 2, 3, 4, 8). `MATH-S7-FLAT_HOLONOMY_ON_A_NERVE`.

**Consequence for this repository, and it is not small.** Every cellular-sheaf
result here lives in the *flat-monodromy* regime — the one the audit's Angle 3
names as the **opposite** of the Berry/Chern regime the archive's chain invokes
at its first step. The repo has been in the right regime all along; the archive
switches regimes silently between its steps [1] and [2].

### 9.3 The sharpening: `‖H¹‖` fails in the discrete regime too

The audit corrects a **degree** error: in the continuous setting the obstruction
is a degree-two Chern class, and the archive's own base (S², S⁸, the lift of S⁷)
is simply connected, so `H¹ = 0` identically — step [1] forces step [3] to zero.

The natural follow-up is whether `[R] = ‖H¹‖` is at least well typed in the
discrete regime, where the degree *is* right. **It is not.** On a connected graph
with `n` vertices, `m` edges and `β₁ = m − n + 1`, rank–nullity on the two-term
complex forces

```
dim H⁰ − dim H¹ = (n − m)·d        ⇒        dim H¹ = dim H⁰ + (β₁ − 1)·d
```

Verified on 16 instances across four nerve families and four fiber dimensions,
zero violations (`MATH-S7-EULER_H1_IDENTITY`). So `H¹` is **large when global
sections are plentiful** — the reverse of the reading the archive gives it — and
what remains of its content is the cycle rank times the fiber dimension, fixed
before any transition map is chosen.

In its sharpest form, on `ring8 + 2 chords` at fiber dimension 4:

| sheaf on the same nerve | obstruction | `dim H⁰` | `dim H¹` |
|---|---|---|---|
| identity transitions | **none at all** | 4 | **12** |
| generic orthogonal transitions | maximal | 0 | **8** |

`‖H¹‖` is largest where nothing is wrong. The functional is not merely in the
wrong degree; in the one regime where its degree is right, it moves the wrong
way. The quantity that *does* detect the obstruction is `dim H⁰ = 0` — and the
Laplacian instrument this repository already uses reads the lowest eigenspace of
`L = δᵀδ`, which is the `H⁰` side. `RET-S7-H1_AS_REMAINDER`.

The boundary case closes a loop: a tree (`β₁ = 0`) has `dim H¹ = 0` and
`dim H⁰ = d` for **every** choice of transitions — which is
`MATH-S6-BRIDGE_BLINDNESS`, reached independently from the cohomological side.

### 9.4 The Lean tower does not rescue the chain

Two states appear in the archive. With the bridge declared as an axiom, a green
`lake build` certifies type-correctness *relative to the conclusion*. With the
axiom removed, what `native_decide` actually checks is the octonion
multiplication table — which §9.1 confirms, and which bears on no SAT lower
bound. Removing the named axiom did not remove the assumption; it migrated into
the definitions.

The step carrying all the complexity content is the assumed **super-polynomial
cost of trivialising the obstruction** — a lower bound as strong as the
conclusion. This is the same failure mode this repository has now recorded seven
times under other names: *the correct shape with the old comparison still inside
it.*

The archive's own `CLAY_PROOF_ATTEMPT_LEDGER.md` already says
`promotion_allowed: false`. §3 above flagged that line as the single most
important sentence in the document for calibration. The audit is independent
confirmation that the programme's own ground truth was the accurate one.

### 9.5 What survives, unchanged

A genuine non-zero first Chern number of a Hopf-type U(1) bundle; the octonionic
associator/Fano structure; correct CM arithmetic for `y² = x³ − x`; a correctly
stated GRH error bound; and — importantly — the archive's *honest tierings*
(Yang–Mills / Navier–Stokes / Hodge as "architectural analogy only", Poincaré as
"Perelman, used as reference calibration", the 47 sorries in L35/L36). Those
self-assessments are accurate and are to be kept visible, not quietly upgraded.

---
