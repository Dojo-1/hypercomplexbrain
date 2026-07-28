# QΣ-R6b — Why fixed-width operational information does not inherit source growth

R6 ended with an open question, stated as open: the source measure grows like
`e^{2ρ}`, the worst-case post-selection cost falls like `e^{−4ρ}`, and *whether
capacity survives the cost was not established*.

An external derivation settled it. This document records the verification, not
the derivation — **the derivation is not mine and is credited throughout.** It
was produced and published before any of this code existed, which makes it a
stronger commitment device than a preregistration I could write for myself: I
cannot have tuned to a target I did not set.

```
PYTHONPATH=src python3 experiments/run_operational_information.py   →  DERIVATION VERIFIED
```

**Nine checks pass. One constant is corrected. Two of the audit's guards correct
this repository's own vocabulary.**

---

## The answer, in one line

> Normalising `A = M/‖M‖₂` sends `σ(M) = (e^ρ, e^{−ρ})` to `σ(A) = (1, q)` with
> **`q = e^{−2ρ}`**. The unbounded radial ray is not deleted — it is
> **compactified** onto `[0,1]`.

The depth is still there: `det A = q` names it exactly. What changes is that
recovering it becomes exponentially ill-conditioned rather than impossible. The
audit is explicit about this and it is the right distinction — an earlier framing
would have said the depth is "erased", and it is not.

## The Fisher information does the accounting

Independently recomputed by central differences on the SLD, never seeing the
closed form. Worst relative error over ρ ∈ [0.3, 3.0]: **< 1e-6**; worst
off-diagonal **< 1e-8**, so the matrix really is diagonal:

```
J(ρ,φ,ψ) = diag( 8/(e^{4ρ} − 1),  (1+q)²,  (1−q)² )
```

| ρ | J_ρρ | J_φφ | J_ψψ |
|---|---|---|---|
| 0.3 | 3.448 | 2.399 | 0.204 |
| 1.0 | 0.1493 | 1.289 | 0.748 |
| 2.0 | 0.002685 | 1.037 | 0.964 |
| 3.0 | 0.0000491 | 1.005 | 0.995 |

**`J_ρρ → 8e^{−4ρ}`.** That is R6's post-selection cost exponent, reached from a
completely different direction — one a block-encoding survival probability, the
other a Fisher information. Two independent routes to the same exponent is the
substance of the claim, and neither was derived from the other.

Meanwhile both angular entries saturate at 1. So the operational manifold does
not grow with the source: **it flattens onto a 2-torus boundary** carrying two
angular coordinates and a finite inward direction.

## The volume is a constant — and the constant is corrected

```
∫ √det J  dρ dφ dψ  =  √2 · π³  ≈  43.849
```

The audit reported **2π³ ≈ 62.013**. The ratio is exactly **1/√2**, which is what
writing `√8` as `4` instead of `2√2` produces. `det J = 8q²(1−q²)`, so
`√det J = 2√2 · q√(1−q²)`, and substituting `dρ = −dq/2q` gives
`√2 ∫₀¹ √(1−q²) dq = √2·π/4`, times `(2π)²`.

Verified two ways: symbolic substitution and numerical quadrature agree to 1e-8.

**Closed at R6c.** That value is *before the projective quotient*, which the
derivation flagged and left open. `ω(A) = ω(−A)` **exactly** — 0.0, not 1e-16,
because `|v⟩⟨v|` is quadratic in `v` — so the operational space is
`PSL(2,ℝ) = SL(2,ℝ)/{±1}` and the volume halves:

```
operational Fisher volume  =  √2 π³ / 2  =  π³/√2  ≈  21.925
```

**The correction does not touch the argument.** What matters is that the integral
*converges* while the source measure diverges — a finite operational volume
against `√|det g| = cosh ρ sinh ρ ~ e^{2ρ}/2`. The distortion ratio
`√det J / √|det g_src| → 8√2 e^{−4ρ}` is a precise, measurable version of what
this programme has been calling "projection violence".

## Source reversibility is not operational reversibility

`κ(X,Y) = log‖X‖ + log‖Y‖ − log‖XY‖ ≥ 0` — verified nonnegative over 300 random
draws, with

- `A_X A_Y = e^{−κ(X,Y)} A_XY` to **4.4e-16**
- the exact 2-cocycle law `κ(X,Y) + κ(XY,Z) = κ(Y,Z) + κ(X,YZ)` to **1.3e-15**

and, for an inverse pair, `κ(M⁻¹, M) = 2ρ` **exactly**:

| | source | operational |
|---|---|---|
| return defect | `M⁻¹M = I`, exactly 0 | — |
| streamed survival | — | `e^{−4ρ}` |
| direct compilation | — | 1 |

Undoing a movement costs exactly what making it cost. This is R6's P4 — echoing
is free only if the net element may be compiled directly — but re-derived as an
**algebraic identity** rather than measured. That is a real strengthening: P4 was
200 sampled loops; this is a proof.

## Two guards that correct this repository

Both are the auditor's, both are now checkable rather than asserted, and both
land on my own text.

**1. `so(2,2)` is semisimple, not simple.** `hyperbolic_qubit.py` stated the
obstruction as *"a non-compact **simple** Lie group has no faithful
finite-dimensional unitary representation"*. `so(2,2) = sl(2,ℝ) ⊕ sl(2,ℝ)` has two
ideals. The theorem survives verbatim under **semisimple** — a connected
semisimple Lie group with a faithful finite-dimensional unitary rep must be
compact — so R6's conclusion is unaffected. But a wrong word in a theorem
statement is not a small thing, and it stood for three commits.

**2. The source is Lorentzian, not hyperbolic 3-space.** The induced metric on
the `Q = +1` pseudo-sphere is

```
g = diag(−1, cosh²ρ, −sinh²ρ)        signature (1, 2)
```

One positive eigenvalue, two negative. This is an **AdS₃-like Cartan geometry**,
not positive-definite `H³`, whose signature would be (3,0).
`induced_metric_signature` asserts it at every tested depth.

Everything this programme has called "hyperbolic volume" was the
*pseudo-Riemannian* volume of a Lorentzian manifold. **The measure was right**
(`cosh ρ sinh ρ`, growing as `e^{2ρ}`); the name was not. The R6 peer-review doc
has been corrected in place, including a stronger correction it prompted: that
section wrote "number of distinguishable states" where it had only measured
*source measure* — which is precisely the conflation this round dissolves.

## Also verified

- `p_Bell = (1+q²)/2`, saturating at 1/2 — R6's average-case result, another route.
- Conditional concurrence `C = sech(2ρ)`, exact at every ρ. **Probe-specific**: a
  property of the fixed Bell bipartition, not an invariant of the architecture.
  Recorded with that caveat because the number is seductive.
- Trace distance `½[√((p_A+p_B)² − 4|c|²) + |p_A−p_B|]` and root fidelity
  `|c| + √((1−p_A)(1−p_B))` against dense linear algebra over 200 random codeword
  pairs, worst error < 1e-10, with Fuchs–van de Graaf holding on every pair.

## What this does not license

- **No capacity claim.** One-shot, one use, one probe. No coding theorem, no
  asymptotics, no advantage.
- **No witness rank.** This repository *recomputed* an external party's
  derivation, which would raise the rank of **their** envelope — and their
  artifact is not here. `EXP-R6B-OPERATIONAL_INFO` is `not_requested`,
  `independent = False`, and the recomputation is recorded as a typed remainder.
  The direction of the witness relation matters and is easy to get backwards.
- **The probe is not the architecture.** A different bipartition gives different
  numbers. The compactification argument does not depend on the Bell probe; the
  entanglement diagnostic does.

## The three gates, closed at R6d

`PYTHONPATH=src python3 experiments/run_holevo_sandwich.py` → **ALL GATES PASS**
(14 checks, 29 tests).

**A. The sandwich holds**, `I_PGM ≤ I_acc ≤ χ ≤ log₂N`, at every depth. `I_acc`
is a supremum over all POVMs and is deliberately **not estimated** — it is
reported as the bracket `[I_PGM, χ]`, because an estimate of it would be the one
number in the round that could be quietly tuned.

**The flag decomposition is exact** (residual < 1e-12):

```
χ  =  p̄·S(σ̂)  +  [ h₂(p̄) − ⟨h₂(pᵢ)⟩ ]
      success branch      the flag itself
```

The bracket is a Jensen gap, nonnegative because `h₂` is concave, and **exactly
zero when every codeword sits at one depth**. So in a fixed-depth codebook the
erasure flag carries *no* information and all of χ lives in the success branch
weighted by survival. It becomes informative only when depths differ — and then
it reports the *depth spread*, not the message. Both directions are asserted;
otherwise the identity is vacuous.

**B. Data processing holds** over 12 random CPTP maps (Kraus completeness exact
to 6.7e-16 by Stinespring construction): χ contracts, trace distance contracts,
fidelity does not decrease. Note the test *not* run: `I_PGM(Φ(ensemble)) ≤
I_PGM(ensemble)` is **not implied** — the PGM is chosen for whichever ensemble it
is handed, so a better measurement on a worse ensemble can beat a worse one on a
better ensemble. The implied statement, and the one checked, is
`I_PGM(Φ(ensemble)) ≤ χ(ensemble)`.

**C. The boundary limit converges, and one claim died on the way.**

The first random codebook showed χ *rising* with depth, which looked like a
finding: deeper is more informative. **The control killed it.** A deterministic
evenly-spaced codebook dips from 0.901726 at ρ=0.1 to 0.898532 at ρ=0.25 before
rising, and two of five random seeds converge from *above*. "χ increases with
depth" is withdrawn as an artifact of one draw, and
`test_chi_is_not_monotone_in_depth` pins the counterexample so it cannot quietly
come back.

What survives is stronger than what did not, and it has a closed form. At
infinite depth `A` becomes rank one, so `|v⟩` becomes a **product** state of norm²
= ½. Hence `p̄ → ½`, every `S(ωᵢ) → h₂(½) = 1` bit, and by the decomposition:

> **χ → ½·S(σ̂) ≤ 1 bit.**

The grid codebook's product states average to the maximally mixed state on `ℂ⁴`,
so `S(σ̂) = 2` and **χ = 1.000000000 bit exactly**, with a tail spread of 6.2e-15
over ρ ∈ [8, 16].

**The channel does not die at depth.** It converges to a boundary channel worth
at most one bit per use, carried entirely by the two angular coordinates — which
is exactly what R6b's saturating angular Fisher information predicted, now at the
level of a codebook rather than a metric.

## Still open

The naming point stands: `Tendril.deweave()` means governance retirement, not
`M⁻¹`, and a physical inverse needs its own name. And `I_acc` itself remains a
bracket, not a number.
