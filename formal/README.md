# Formalisation surface — S4-G100

## Status: **NOT COMPILED**

There is no Lean, `lake` or `elan` on `PATH` in this environment, and no
`lakefile` or toolchain pin exists in this repository. `RecognitionChamber.lean`
has therefore **never been checked by a kernel**. It is a set of theorem
statements written in Lean 4 syntax, not a verification.

Nothing in `docs/`, `README.md` or `aionq.governance` claims Lean verification
for any S4 result. The three P-tagged S4 claims
(`MATH-S4-LOOP_ZERO`, `MATH-S4-GAUGE_INVARIANCE`, `MODEL-S4-BORDON_CEILING`)
rest on **exact numerical checks** in `tests/test_s4_g100.py` plus two-line
arguments, and each records in its `assumptions` that the Lean statement is
present and uncompiled. That is the honest tier: they are P because the
mathematics is a definitional consequence, not because a proof assistant agreed.

To check them, install a Lean 4 toolchain with Mathlib and run `lake build`. If
the file does not compile, that is a finding about this file and should be
recorded as a correction — not quietly fixed.

## What each target says, and what it does not

| target | statement | status |
|---|---|---|
| **P1** | `0 ≤ loopDefect T x` for any pseudo-metric | trivial from `dist_nonneg`; exercised by 200 seeded random transports |
| **P2** | `T.backward (T.forward x) = x → loopDefect T x = 0` | trivial from `dist_self`; exercised by identity, exact permutation inverse, orthogonal gauge round trip — all return `0.0` exactly, not approximately |
| **P3** | `loopDefect (conj G T) (G x) = loopDefect T x` for isometric `G` | the one with content; verified numerically to `1e-12` on a *deliberately lossy* probe, and the chamber's output is bit-identical under an orthogonal gauge change |
| **P4** | `d > ρ → ∃ t, level t ≤ 0` for constant refill and draw | a model consequence; says nothing about any physical system |
| **P5** | authorising nodes inside the generating dependency closure cannot promote | enforced in `nest.py` *before* any numeric gate is consulted |

### What is deliberately not attempted

No target here asserts intelligence, usefulness of a nonzero order defect,
optimality of an aperture, consciousness, or general cognitive superiority. P4 is
a statement **inside the constant-rate reservoir model** and is not a claim about
respiration, cognition or any physical brain. P3 is the only target whose failure
would change a reported number; P1 and P2 are definitional and are listed because
a formalisation surface that omits its trivial obligations is not a surface.

### The gap this leaves

P3 as stated quantifies over isometries of the *carrier*. The chamber's measured
instability under worldlet relabelling (0.285 worst-case AUROC shift) is **not** a
counterexample to P3: relabelling is not an isometry of the carrier, it is a
change of the fundamental cycle basis, which changes the transport pair itself
rather than conjugating it. Stating P3 does not close that gap, and no theorem
here covers basis change. That is the smallest open bridge left by this round.
