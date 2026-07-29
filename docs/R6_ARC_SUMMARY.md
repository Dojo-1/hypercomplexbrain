# The R6 arc, closed

Seven rounds, one question, answered. This is the ledger of what was established,
what was corrected, and what is still open.

**The question.** The programme's substrate is the `Q = +1` pseudo-sphere in
`ℝ^{2,2}`. Its measure grows exponentially with depth. Quantum computation is
unitary. Does the exponential representational capacity survive a unitary
realization?

**The answer.** No. Two independent instruments, four failed rescue attempts.

---

## The chain

| round | result | tier |
|---|---|---|
| **R6** | depth is the only coordinate that is not a gate; the point is unitary **iff ρ = 0** | P |
| **R6b** | depth is **compactified**, not deleted: `q = e^{−2ρ}`; radial QFI decays as `8e^{−4ρ}` | P/M |
| **R6c** | the split **is** the Cartan decomposition; compact motion is isometric | P |
| **R6d** | at the boundary **one bit** reaches the receiver | M |
| **R6e** | the trace is observable, with three detectors and their nulls | M |
| **R6f** | capacity **does not survive**: 1 bit against a compact baseline's 2 | M |
| **R6f+** | 1 bit is the **optimum**, not the probe; and neither width nor parallelism beats it | M |

### The mechanism, in one line each

- `σ(M) = (e^ρ, e^{−ρ})` → `σ(A) = (1, q)`. The unbounded ray becomes `[0,1]`.
- `J = diag(8/(e^{4ρ}−1), (1+q)², (1−q)²)`. Radial vanishes; the two angular
  directions saturate at 1.
- Those two angles are the **K factors** of `M = R(α)·diag(e^ρ,e^{−ρ})·R(β)`.
  They act by local unitaries, change no singular value, and are free. The A
  factor moves between unitary orbits, and that is what costs.
- `χ = p̄·S(σ̂) ≤ 2p̄ = 1 + e^{−4ρ} → 1 bit`, with **N absent from the bound**.

## Four ways it could have been rescued, and none works

| rescue | result |
|---|---|
| **more codewords** — pack 100 instead of 8 | `χ = 1.000000` at both, while `log₂N` goes 3 → 6.644 |
| **a better probe** — sweep entanglement `λ` | Bell (`λ=½`) is the **maximum**; χ falls monotonically off it |
| **more width** — ancilla `d = 2 … 8`, state dim 5 → 17 | `χ = 1.000000000`, spread **4.4e-16**. `rank(A) = 2` caps it |
| **parallel use** — `k = 1, 2, 3` | `χ/k` constant to **5.6e-16**. Exactly additive |

The last is the one that had to be *measured* rather than assumed: Holevo
information is famously **not** additive in general, so super-additivity was a
live possibility. It does not occur here.

And the normalisation choice is not the culprit either — spectral against
Frobenius give identical χ to 1e-14.

## The control that makes "1 bit" mean something

The matched compact baseline: same probe, same dimension, same codebook sizes,
but `SU(2)` instead of `SL(2,ℝ)` — so every element is unitary, `p ≡ 1`, and
there is no erasure branch.

```
compact      SU(2)      χ → 2 bits   (1.994 at N = 256)
non-compact  SL(2,ℝ)    χ → 1 bit    (1.000000 at every N)
```

**Exactly half**, and the half is `p̄ → ½` — the weight the erasure flag takes at
depth. *That* is the unitary realization cost, stated as a number.

## What I got wrong, and what caught it

Seven corrections, each caught by something built to catch it:

1. **`√` of rounding noise** — `√(I−AAᵀ)` is exactly 0 at ρ=0, so `eigh` returns
   ±1e-16 and `√(1e-16) = 1e-8`. Injected 4.2e-9 of ancilla leakage *in the
   regime the round called free*. **C1 voided the round**, as preregistered; the
   probability-level control C2 passed the broken build.
2. **"simple" for "semisimple"** — `so(2,2) = sl(2,ℝ)⊕sl(2,ℝ)` has two ideals.
   The theorem survives; the word stood wrong for three commits. *(External.)*
3. **"hyperbolic" for a Lorentzian space** — `g = diag(−1, cosh²ρ, −sinh²ρ)`,
   signature (1,2). The measure was right; the name was not. *(External.)*
4. **κ summed over adjacent pairs** — it is a 2-cocycle and telescopes over
   **prefixes**. Off by 1.2e-2 until fixed; prediction T4 existed for this.
5. **A mis-specified fault injection** — two depth-2 steps at ±1 *compound*, so
   `κ = 0` and nothing leaked. The empty confusion-matrix row was the detector
   being **right**. Fixed the fault, not the threshold.
6. **A real-rotation "SU(2)" baseline** — a one-parameter family, which returned
   a spurious ceiling of 1 bit that *accidentally matched* the non-compact side
   and would have erased the entire contrast.
7. **`2p` printed for `2p̄`** — appeared to violate the ceiling at every non-Bell
   probe. It did not; `p` and `p̄` differ by up to 0.4 here.

Two further claims of mine were **narrowed rather than confirmed**:

- R6d's "a fixed-depth codebook has an uninformative flag" is true only for the
  **Bell probe**. The real condition is equal `pᵢ`, which equal depth delivers
  only when `p = tr(AᵀA)/2` is orientation-independent. Off Bell the flag reports
  **orientation**, up to 0.395 bits.
- R6f's "χ increases with depth" was **withdrawn** — an artifact of one random
  codebook. The grid control dips before it rises. Convergence survived;
  monotonicity did not.

## Cross-party agreement

Three results now reproduce across two machines with no shared code:

| quantity | agreement |
|---|---|
| `operational_success_probability` vs `p_bell(ρ)` | **5.6e-16** over 120 frames |
| Fano ranks | **(7, 21, 28)** both sides |
| their R8 `χ = 1.682661` vs this N-independent ceiling | sits on it exactly at ρ = 0.095439 |

## Still open — and this is the real one

Everything above is a property of **the R6 fixed-width Bell encoding**, not of
hyperbolic geometry. What has been ruled out is beating that ceiling by *more
codewords, a better probe, more width, or parallel use*.

What has **not** been ruled out is a structurally different **map** from
`SL(2,ℝ)` into a fixed-width state — one that is not "normalise by the operator
norm and post-select". Such a map would have to evade the rank-2 bottleneck, and
nothing here shows that impossible. That is the next genuine round, and it needs
a new encoding rather than another sweep of this one.

Also unclosed: `I_acc` remains a bracket `[I_PGM, χ]` rather than a number, and
the truncation branch of the representation remainder — encoding an
infinite-dimensional unitary rep on finite qubits and paying in truncation error
instead of post-selection — has never been measured.

## Not claimed

No quantum advantage — the R6 preregistration made asserting one a kill
condition. No coding theorem, no regularisation, no asymptotic capacity. No
hardware: exact linear algebra and statevector simulation throughout, no device
and no noise model. No cognition.
