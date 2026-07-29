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

---

## Addendum — R6i is aimed at exactly the right door, and I cannot check it yet

An external round (**R6i**, `codex/r6h-heldout-translation`, commit `95f5ec7`)
reports **χ rising 1.000 → 3.000 bits** at ρ=8, N=256, with 17/17 controls
passing and the verdict `RESCUE_FOR_THIS_MAP`. It uses a **16-dimensional point
encoding** against R6's 5-dimensional carrier.

That is precisely the open door this summary named: *"a structurally different
map from `SL(2,ℝ)` into a fixed-width state — one that is not 'normalise by the
operator norm and post-select'."* Attacking it is the right move and the claim is
credited to them.

**I cannot verify it.** The branch is not on the remote — checked with
`git ls-remote`, and their own report says *"Nothing was pushed."* So the number
below is theirs, unverified here, and is marked as such.

### The comparison it needs, set up in advance

Three bits from sixteen dimensions against one bit from five is not a comparison
until width is divided out:

| encoding | carrier | χ | log₂ dim | **bits per log₂-dim** |
|---|---|---|---|---|
| R6, one use | 5 | 1.000 | 2.322 | **0.4307** |
| R6, two uses | 25 | 2.000 | 4.644 | **0.4307** |
| R6i *(reported, unverified)* | 16 | 3.000 | 4.000 | **0.7500** |

The R6 encoding sits at 0.4307 at both widths **exactly** — because χ is exactly
additive over parallel uses and so is log-dimension, which is what makes this the
right yardstick. On it, R6i is **1.741× more efficient**. That is a real gain and
not width alone.

### The single number that settles it

`holevo_ceiling_general(D, p̄) = p̄ · log₂ D`:

```
p_bar = 1.00  ->  ceiling 4.000  ->  3.000 consistent
p_bar = 0.75  ->  ceiling 3.000  ->  3.000 consistent, exactly saturating
p_bar = 0.50  ->  ceiling 2.000  ->  3.000 EXCEEDS its own ceiling
```

So **report `p̄`**. A value near 1 means the encoding has no erasure branch —
which is exactly the structural change R6f named as the way out, and the rescue
is real, bought by removing post-selection rather than by adding width. A value
near ½ would mean a post-selected encoding reporting more bits than its own
success weight permits, and that would need explaining before it counts.

Their own caveats are the right ones and I would not soften them: this is *"not a
representation, capacity theorem, or quantum-advantage claim"*, and the gain
*"partly restores the exact M ↔ −M sign alias discarded by R6"* — that alias is
R6c's projective quotient, worth at most **1 bit**, so it cannot by itself
account for a 2-bit rise. The remaining gain needs its own account, and `p̄` is
where to look for it.

Also unpushed and unverifiable here: **HB0-T1** (`codex/hb0-active-tendril`,
`dcd756a`/`2ec7fd8`/`9a8ed65`) — 13 controls, 43 tests, 27/27 envelopes reported.
