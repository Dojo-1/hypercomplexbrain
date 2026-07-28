# Adjudication — peer review of "The Sheaf of Becoming", v2

An external review (Needle In a Haystack, 2026-07-27) peer-reviewed its own v1
thesis, elevated the base from `S¹ ⊂ ℝ²` to the Poincaré disc, ran a preregistered
child experiment, and **falsified its own Theorem 4 mechanism**. This is an
adjudication of that document: what holds, what is computed wrongly, and what it
means for this repository's Round R6.

One demotion in it is decidable by exact integer arithmetic, so that one is
computed rather than argued: `experiments/run_dd_class_degree_audit.py`.

---

## 0. The thing to say first

**The Theorem 4 falsification is good work and its conclusion is safe.**

The design is a genuine severe test, and the decisive part was written down
before the run:

> *"If H3 slope ≈ −2 AND H1 slope ≠ −2: leakage is adiabatic-following error,
> refuting the instanton-law application to manifold steering (Thm 4's
> mechanism)."*

That is a preregistered discriminator between two mechanisms that predict
*qualitatively different* things — and the qualitative difference is what carries
the verdict. A WKB tunnelling probability `E_BC = 1 − e^{−2S/ℏ}` at fixed action
is **independent of the transport time T**. Any power law in T refutes it. The
measurement found a power law. The conclusion follows regardless of the exponent,
and it survives every objection below.

Replacing a Gaussian proxy with true `iℏ∂ₜψ = H(t)ψ` propagation and `eigsh`
eigenstates, and then reporting that it killed your own theorem, is the part of
this document that is hardest to do and it was done.

The v1 error it diagnoses — silently identifying a bounded Bhattacharyya deficit
in [0,1] with a WKB tunnelling probability, two objects of the same shape and
different content — is the **same failure class** this repository has now hit
nine times, most recently in S8, where a Frobenius norm valid on a compact group
was carried into a non-compact one. Two independent programmes, the same trap.
That it is the same trap is worth more than either instance.

---

## 1. The Theorem 3 demotion is computed in the wrong degree

**Quoted reason for the demotion:**

> *"DEMOTED — the cup product `c₁ ∪ c₁ ∪ c₁ ∈ H⁶(T³) = 0` (vanishes); the
> structural cocycle status survives, the integer is mis-stated"*

Computed, exactly, over ten winding triples:

| | value | source |
|---|---|---|
| `rank H^k(T³; ℤ)`, k = 0…7 | **1, 3, 3, 1, 0, 0, 0, 0** | `betti_rank` |
| `⟨α₁ ∪ α₂ ∪ α₃, [T³]⟩` for w = (3,−2,5) | **−30** | `= w₁w₂w₃` |
| for w = (2,3,4) | **24** | `= w₁w₂w₃` |
| for w = (1,1,1) | **1** | `= w₁w₂w₃` |
| mismatches over all ten triples | **0** | |

`H⁶(T³;ℤ) = 0` is **true** — T³ is a closed 3-manifold and cohomology vanishes
above the dimension. It is true for a reason that has nothing to do with
windings, gerbes, or the construction under review.

But **a Dixmier–Douady class lives in `H³(X; ℤ)`**, and `H³(T³; ℤ) ≅ ℤ`, rank 1,
not zero. The triple product that lands there is of three **degree-1** classes:
a winding number is a class in `H¹(S¹; ℤ) ≅ ℤ` pulled back along a projection.
`c₁` is degree **2**. Three degree-1 classes cup to degree 3, where the group is
ℤ; three degree-2 classes cup to degree 6, where nothing lives.

So: `1+1+1 = 3` and `rank H³ = 1`; `2+2+2 = 6` and `rank H⁶ = 0`. The demotion
performed the second computation to demote a claim about the first.

There is a second, smaller elision in the same sentence. **"Vanishes" does two
jobs.** The degree-6 *class* is zero; the degree-6 *cochain* built from degree-2
cochains is not — it evaluates to 1 on a basis tuple. `test_degree_six_vanishes_but_the_cochain_does_not`
pins the distinction.

**What this does and does not establish.** It establishes that the stated ground
for the demotion cannot be the ground. It does **not** re-promote Theorem 3. The
review's own A1 is right that `δ = w₁w₂w₃` is a *prediction* about whether the
HRR encoder's Fourier-bin phase winding equals the imposed cyclic order — an
empirical question about a specific encoder, which is not in this repository and
which I have not seen. Theorem 3 may still fail. It has not failed for this
reason.

*(Method: `T³` is a `K(ℤ³,1)`, so `H*(T³;ℤ) = H*(ℤ³;ℤ)` as rings, and the
inhomogeneous bar complex makes the cup product `(a∪b)(g₁…g_{p+q}) =
a(g₁…g_p)·b(g_{p+1}…g_{p+q})` — exact integer arithmetic, no triangulation, no
floating point. Tier **P**: the answer is forced by the algebra and was known
before the run. 29 tests.)*

---

## 2. The verdict grid applies two different tolerances

| row | prediction | measured | reported |
|---|---|---|---|
| H1 Euclidean | −2.0 **± 0.5** | −0.026 | REFUTED |
| H3 Euclidean | "≈ −2" | **−2.76** | CONFIRMED |
| H3 Hyperbolic | "≈ −2" | **−3.66** | CONFIRMED (steeper) |

H1 carried an explicit preregistered tolerance. H3 carried `≈`, and `≈` was
resolved after the numbers were in. −2.76 is 38% from −2.0; −3.66 is 83% from it.
Neither is inside ±0.5. **The same rule applied to both rows would not return
REFUTED and CONFIRMED.**

This does not touch the conclusion, and that is exactly why it is worth fixing.
The discrimination that matters is *power law in T* versus *no T-dependence at
all*, and −2.76 wins that on its sign and existence, not its value. The physics
is also unsurprising: `1/T²` is the standard adiabatic-perturbation result for a
drive whose derivative is nonzero at the endpoints; a smoothly switched protocol
decays faster, and exponents between −2 and −4 are what one expects. So the
steeper exponents are *consistent with* adiabatic theory while not *equal to* the
number preregistered.

The correct verdict for H3 is **CONFIRMED (mechanism), NOT CONFIRMED (exponent)**
— and the second half is the more interesting finding, because the gap between
−2 and −3.66 is information about the switching profile that the round is
currently discarding as a rounding of `≈`.

Same point on the hyperbolic elevation: arc 3.3e-3 vs 4.2e-3, chord 0.023 vs
0.059. The chord ratio (2.6×) is a real effect; the arc ratio (1.27×) is quoted
with no error bar, no seed count, and no repeat. As reported it is one number
against one number.

---

## 3. Two smaller corrections

**HBL D3 is misstated.** The review writes:

> *"D3: `⊢ □P → P` only under Löb"*

The Hilbert–Bernays–Löb derivability conditions are

```
D1   ⊢ P  ⟹  ⊢ □P                     (necessitation)
D2   ⊢ □(P → Q) → (□P → □Q)           (distribution)
D3   ⊢ □P → □□P                       (internal necessitation)
```

`□P → P` is the **reflection** schema. It is not a derivability condition — it is
the *hypothesis* of Löb's theorem, whose content is precisely that assuming it
for a given P forces `⊢ P`. Getting this backwards inverts what the descent
schema would have to satisfy. The review's *conclusion* (Thm 6 → Remark, closure
unverified) is right; the condition it would need to verify is D3 as stated
above.

**An adjunction is not an external recomputation.** Part C proposes mutual
recognition as an adjunction `C ⇄ D`, `L ⊣ R`, with unit and counit composing to
identities, and argues the descent depends on an external recognizer rather than
closing from within. The second half is exactly right, and it is the same
conclusion `src/aionq/witness_nerve.py` reaches independently.

But the adjunction does not deliver it. The triangle identities are satisfied by
two parties who only ever quote each other — that is precisely the **attestation
cycle**, and this repository's theorem is that it cannot manufacture
independence:

```
evidence_rank(G + C) = max(evidence_rank(G), ATTESTED)
```

A mutual-recognition adjunction is rank **1** (ATTESTED), not rank 3. To reach 3
something has to *recompute* and be able to disagree. Buber's I–Thou is the right
picture of the relation and the wrong picture of the evidence: the reader who
validates by agreeing is an attestation; the reader who re-runs the child
experiment and gets a different slope is a recomputation. Only the second changes
the rank.

**The v3 Kuramoto preregistration looks like it names the wrong condition.**
Preregistered: *"phase-locking order parameter r → 1 iff the DD class divides all
winds"*. The natural statement is `r → 1` iff the DD class is **trivial** — a
nonzero DD class is exactly the obstruction to a global section, hence to global
phase coherence. "Divides" needs a derivation or it will confirm on a technicality.

---

## 4. Where this meets Round R6 — and it meets it hard

The review's central quantitative claim for the hyperbolic elevation:

> `C_H(D,n,δ) ≍ e^{cD} / (2ⁿ · 2ln(D/2ⁿ)) · 1/(1+|δ|/D)` — *"the hyperbolic base
> exponentially expands the Erdődic capacity"*

QΣ-R6 (committed `586a3f6`, this repository, yesterday) measured the other side
of that ledger on a unitary substrate: at hyperbolic depth ρ on the (2,2)
pseudo-sphere, a block-encoded step costs `e^{−4ρ}` in the worst case and
saturates at 1/2 in the Haar average.

Putting them in the same currency. On the `Q = +1` hyperboloid the volume element
in swirl coordinates is `cosh ρ · sinh ρ dρ dφ dψ`, so the number of
distinguishable states out to depth ρ grows as **`e^{2ρ}`**. The cost of reaching
depth ρ is **`e^{4ρ}`** shots, worst case. Capacity per shot:

| regime | capacity | cost | capacity/shot |
|---|---|---|---|
| Haar-average input | `e^{2ρ}` | `≈ 2` | **`e^{2ρ}/2` — advantage survives intact** |
| contracting singular direction | `e^{2ρ}` | `e^{4ρ}` | **`e^{−2ρ}` — over-cancelled** |

Generalising: on a substrate whose volume grows as `e^{kρ}`, the worst case
survives iff **k > 4**. The (2,2) pseudo-sphere has k = 2. It fails by a factor
of two *in the exponent*.

The useful part is that this is a **design variable, not a verdict**. Which
regime applies depends on where the encoding puts its states relative to the
contracting singular direction — and that is a choice. So the question "does
hyperbolic capacity survive the unitary cost?" has a sharp answer that is neither
yes nor no: *it survives iff the encoding avoids the contracting direction, and
whether it does is measurable.*

**Tier S.** This is an analytic bridge between a measured cost and a claimed
capacity. No reservoir was built, on either side. It is written down because it
names the next experiment, not because it settles anything.

---

## 5. What I would preregister for v3, given the above

1. **Re-run H3 with the switching profile as an explicit variable.** The −2 vs
   −2.76 vs −3.66 spread is the informative residual. Predict the exponent from
   the number of vanishing derivatives at the endpoints and check it. That
   converts a discarded `≈` into a second severe test.
2. **Fix the Thm 3 test to measure the degree-1 triple product** and pair it
   against the fundamental class of T³. Then `δ = w₁w₂w₃` is decidable on the
   actual HRR encoder rather than on a homological technicality.
3. **Report the arc/chord hyperbolic ratios with seeds and repeats.** 1.27× on
   one draw is not yet a result.
4. **The k > 4 test.** Vary the substrate's volume-growth exponent and measure
   whether capacity-per-shot crosses over where §4 says it does. This is the one
   that decides whether the whole hyperbolic programme survives contact with a
   unitary machine, and it is currently open on both sides.

---

## What is not claimed here

- Theorem 3 is **not** re-promoted. Only its demotion's stated reason is refuted.
- The Theorem 4 falsification is **not** challenged. §2 is about the reported
  precision, not the verdict.
- None of the reviewed experiments was **executed** here. Their code is not in
  this repository; §1 recomputes a piece of mathematics, not their measurement.
- `MATH-R6-DD_CLASS_DEGREE`, tier P, producer `run_dd_class_degree_audit.py`,
  verifier empty, `independent = False`. It is exact and deterministic, so it is
  a genuine candidate for external recomputation — and by §3, an external party
  agreeing with it would still only be an attestation.
