# QΣ-R6 — The unitary price of hyperbolic depth

Preregistered at `47def35` (`manifests/qsigma_r6_unitary_price_preregistration.json`),
implemented after. Four predictions, six controls, all closed-form, all run.

```
PYTHONPATH=src python3 experiments/run_hyperbolic_qubit_cost.py
```

| | verdict |
|---|---|
| P1 depth is the bill | **SURVIVES** |
| P2 elliptic fraction | **SURVIVES** |
| P3 post-selection cost | **SURVIVES** |
| P4 echo the weave | **SURVIVES** |
| C1 encoding fidelity | PASS *(failed on first run — see below)* |
| C2 compact null | PASS |
| C3 wrong instrument | PASS |
| C4 elliptic ≠ unitary | PASS |
| C5 determinant drift | PASS |
| C6 loop closure | PASS (folded into P4) |

---

## The question, and why it is not optional

The substrate is the `Q = +1` pseudo-sphere in `ℝ^{2,2}` with `SO(2,2)` acting on
it. Quantum computation is unitary. A non-compact simple Lie group has no
faithful finite-dimensional unitary representation. `SO(2,2)` is non-compact.

So the hyperbolic directions of this substrate are not gates — not for want of a
better encoding, and not at any width. That is settled before any experiment
runs. What is *not* settled, and what this round measures, is the price.

## The identification

Map a point of `ℝ^{2,2}` to a real 2×2 matrix:

```
x  ↦  M = [[x₀ + x₂,  x₁ + x₃],
           [-x₁ + x₃, x₀ - x₂]]        det M = Q(x)  identically
```

`Q = +1` becomes `det = 1`, so **the hyperboloid *is* SL(2,ℝ)**, and `SO(2,2)₀`
acts by `M ↦ A M B⁻¹`. Not an analogy — the same object written twice.

In the swirl coordinates the TELOS archive already uses,
`x = (cosh ρ cos φ, cosh ρ sin φ, sinh ρ cos ψ, sinh ρ sin ψ)`, everything is
closed form. Those coordinates are adopted verbatim, so every result below
transfers straight back into that codebase.

---

## P1 — depth is the bill, and only depth

Over 180 grid points spanning ρ ∈ [0,3], φ and ψ over the circle:

| quantity | prediction | worst error |
|---|---|---|
| singular values | exactly `(e^ρ, e^{-ρ})` | **7.1e-15** |
| `‖M‖_F²` | exactly `2 cosh 2ρ` | < 1e-12 |
| condition number | exactly `e^{2ρ}` | < 1e-11 |
| `det M` | exactly 1 | < 1e-12 |
| orthogonal points with ρ > 0 | **none** | **0 found** |
| orthogonal points with ρ = 0 | **all 18** | all |

> **The point is a unitary if and only if ρ = 0.**

The two compact coordinates are free. φ is spin, ψ is swirl; both are phases,
both are gates, both cost nothing. The one coordinate that makes the geometry
hyperbolic rather than Euclidean is exactly and only the coordinate that cannot
be run. Depth is the bill.

This is worth sitting with, because it is the opposite of a convenient result.
The whole point of leaving flat ℝ^d was that the hyperbolic direction carries
the capacity. It is that direction, and no other, that the unitary substrate
refuses.

## P2 — the unitarily-conjugable part thins out exponentially

`tr M = 2 cosh ρ cos φ`, so the SL(2,ℝ) conjugacy class is elliptic iff
`|cos φ| < sech ρ`, and the fraction of spins that are elliptic is exactly

```
(2/π) · arcsin(sech ρ)   →   (4/π) e^{-ρ}
```

200,000 Monte Carlo draws per depth, seed 20260728:

| ρ | empirical | analytic | z | (4/π)e^{-ρ} |
|---|---|---|---|---|
| 0.0 | 1.000000 | 1.000000 | 0.00 | — |
| 0.25 | 0.842240 | 0.842477 | 0.29 | 0.9916 |
| 0.5 | 0.694075 | 0.694180 | 0.10 | 0.7723 |
| 1.0 | 0.446500 | 0.448834 | 2.10 | 0.4684 |
| 2.0 | 0.170405 | 0.171274 | 1.03 | 0.1723 |
| 3.0 | 0.062615 | 0.063339 | 1.33 | 0.0634 |

Worst z = 2.10 across ten depths. The prediction was written down before the
code existed and is matched without a fitted parameter.

**But elliptic is not unitary** (control C4). At ρ = 1.5, φ = π/2 the element is
as elliptic as it gets — trace exactly 0 — and its condition number is `e³ ≈
20.09`. It is *conjugate* to a rotation, and the conjugating element is itself
hyperbolic, so the change of basis is not one a quantum computer performs for
free. Reading the trace classification as an implementability test would be the
round's most available mistake, so it is asserted as a test.

## P3 — the average is not the story, and neither is the worst case

Block-encode `M` as a 2-qubit orthogonal dilation, post-select the ancilla on
|0⟩. Measured through Qiskit's statevector, worst error **1.1e-16**:

| | closed form | at ρ=1 |
|---|---|---|
| Haar-average over inputs | `(1 + e^{-4ρ})/2` | 0.509 |
| worst-case direction, L steps | `e^{-4Lρ}` | `e^{-4L}` |

The average-case cost **saturates at 1/2** and is not exponential. The
exponential lives in the worst case and in the subnormalisation: L composed
steps at depth ρ contract the contracting singular direction by `e^{-4Lρ}`, and
the shot count grows to match. At ρ = 0.8, L = 4 that is 8.4e-6.

Quoting either number alone misleads, in opposite directions. Reporting only the
average makes hyperbolic transport look nearly free; reporting only the worst
case makes it look impossible. Both are in the artifact and both are asserted in
`test_average_case_saturates_and_worst_case_does_not`.

## P4 — echo the weave, but know what the echo buys

Over 200 closed loops built from the four boost generators and their exact
inverse words: **200/200** have net depth ρ = 0 and net element exactly
orthogonal — success probability exactly 1, no ancilla, no post-selection.

The same loops with their intermediate states materialised still pay at every
step: median 0.311, minimum 8.4e-5 over the first four steps.

> **A loop that returns to the compact subgroup is free — but only if the net
> element may be compiled directly. It is not free if the intermediate states
> must exist.**

That is a design constraint on the architecture, not a free win, and it is
sharper than the slogan it comes from. Spin echo and dynamical decoupling say
"arrange the drive so the net evolution is trivial". Here the reason is
representation-theoretic rather than noise-theoretic: the net element is
*compilable* because it is compact, while every prefix of the word is not. Any
scheduler that wants the saving has to be allowed to look at the whole word
before emitting a circuit — a reservoir that streams its state through each
intermediate point cannot claim it.

This is where the Fano weave from S8 becomes a scheduling question rather than a
decoration: an `S(2,3,7)` design over the seven boost directions is a candidate
for arranging words whose products land back in the compact subgroup. R6 does
not test that, and it is not claimed.

---

## C3 — the wrong instrument, run on purpose

Round S8 left signature (2,2) unimplemented and typed the remainder as *"the
SU(1,1) generators are unbounded, so the Frobenius norm and the rank argument
need re-deriving"*.

**The first clause is false, and the correction matters more than the fact.**

All six `so(2,2)` generators have Frobenius norm exactly `√2` — compact and
non-compact alike:

```
J01  J23  K02  K03  K12  K13   →   1.41421356…  for every one
```

A norm that assigns the *same number* to a rotation generator and a boost
generator is not an instrument that can separate them. And the generators are
not unbounded; they are fixed matrices with entries in {0, ±1}.

What is unbounded is the **group**:

| ρ | ‖exp(ρ K₀₂)‖_F | ‖exp(ρ J₀₁)‖_F |
|---|---|---|
| 0.0 | 2.000 | 2.000 |
| 1.0 | 3.086 | 2.000 |
| 2.0 | 7.524 | 2.000 |
| 3.0 | 20.135 | 2.000 |

So at the algebra level the norm cannot distinguish the two kinds, and at the
group level it diverges for boosts and is constant for rotations — it reports
rapidity and nothing else.

This is the ninth appearance of the same failure in this programme: **the
correct shape with the old comparison still inside it.** S8 carried a norm that
works on a compact group into a non-compact one and, finding it useless,
concluded the *geometry* was blocked. The geometry was fine. The instrument was
imported. The invariant that survives the move is `|tr|` against 2 — bounded,
basis-independent, and it classifies rather than ranks.

The S8 typed remainder is therefore superseded, not deleted:

> ~~SU(1,1) generators are unbounded; Frobenius norm and rank argument need
> re-deriving.~~
> **Superseded by R6/C3.** The generators are bounded and mutually
> indistinguishable by norm. The unboundedness is in the group. The replacement
> invariant is the conjugacy class.

## C1 — the control that voided the round, and what it caught

**The first run of this round failed C1 and was void.** Not Qiskit's fault, and
not the encoding's — mine.

The dilation needs `√(I − AAᵀ)`. At ρ = 0 that matrix is exactly zero, so `eigh`
returns eigenvalues of ±1e-16 for it. Square root is not Lipschitz at the
origin: `√(1e-16) = 1e-8`. Taking the root of clipped rounding noise did not
produce a small error, it produced one **eight orders of magnitude larger than
the noise that caused it**, in the off-diagonal blocks — spurious ancilla
leakage of 4.2e-9, sitting exactly in the regime the round claims is free.

Two things about how it was caught:

- **C1 works at the amplitude level, at 1e-12.** C2, which checks the same
  regime at the probability level with a 1e-10 threshold, passed the broken
  build — because leakage enters a probability squared, and `(1e-8)² = 1e-16`
  disappears under it. The strict amplitude control is the one that earned its
  place.
- **It was preregistered as round-voiding.** The prediction verdicts on that
  first run all read SURVIVES. Had C1 been advisory, the round would have
  shipped with a numerically corrupt encoding underneath four correct-looking
  results.

The fix is a floor at `16 ε` on the eigenvalues before the root, justified by
`‖A‖₂ = 1` making the matrix O(1) and `eigh` accurate to ~ε.
`test_zero_depth_encoding_has_no_leakage` pins it at the amplitude level.

---

## What this does and does not license

**Established (P, tested):** the exact algebra — singular values, trace formula,
elliptic fraction, both post-selection closed forms, loop closure.

**Measured (M, this machine only):** the Qiskit probabilities and the Monte
Carlo fractions. `EXP-R6-UNITARY_PRICE`, n_eff = 180, `independent = False`.
Deterministic and environment-independent, so it is a genuine candidate for
external recomputation — a digest mismatch would be a real disagreement rather
than a different CPU.

**Speculative (S):** the echo design principle. Nothing was built with it.

**Not claimed, and one of them is a kill condition:**

- No quantum **advantage**. The preregistration lists asserting one as a kill
  condition on the round's own honesty. This measures a cost.
- **The truncation branch is untouched.** A non-compact group has no faithful
  finite-dimensional unitary rep, but it has infinite-dimensional ones. Encoding
  those on finite qubits pays in *truncation error* instead of post-selection.
  R6 prices only the non-unitary branch. Which branch is cheaper is open, and it
  is carried as a typed remainder rather than omitted.
- **Whether the capacity survives the cost.** A hyperbolic ball of radius r has
  exponential volume in r; this round finds an exponential cost in the same r.
  Whether they cancel, and with what constant, is *not* established here. No
  reservoir was built and none was measured. Anyone quoting R6 as either
  vindication or refutation of hyperbolic memory is quoting past the artifact.
- No hardware. Exact linear algebra and statevector simulation, no device, no
  noise model.
