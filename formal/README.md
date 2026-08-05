# Formalisation surfaces

## Status at 2026-07-30: **MIXED**

This checkout tracks two Lean files of its own, plus a vendored archive that is
not evidence and is documented separately in
[`LEANMATH_PROVENANCE.md`](LEANMATH_PROVENANCE.md):

| file | dependency surface | observed command | current result |
|---|---|---|---|
| `OhniumObservatory.lean` | Lean core/prelude only | `lean formal/OhniumObservatory.lean` | **accepted**, exit `0`, under local unpinned Lean `4.32.2` |
| `RecognitionChamber.lean` | Mathlib | `lean formal/RecognitionChamber.lean` | **not compiled**, exit `1`: `unknown module prefix 'Mathlib'` |
| `leanmath/` (11 files, imported) | Mathlib **and** 13 modules that are not in the archive | see `LEANMATH_PROVENANCE.md` | **not built and not buildable**; 9 of 11 lex, 2 do not parse at all |

**Correction, 2026-08-05.** The sentence above this table used to read "`lean`,
`lake` and `elan` are present on `PATH`". In this container only `elan` was
present, with an empty `toolchains/` directory, so nothing could run at all —
the claim described a different machine and had been carried forward unchecked.
The pinned toolchain `leanprover/lean4:v4.32.0-rc1` has since been installed
here (commit `b4812ae`) and used to lex the vendored archive; it is *not* on
`PATH` by default and lives at `~/.elan/bin/lean`. The repository still has no
`lean-toolchain`, `lakefile.lean`, `lakefile.toml` or `lake-manifest.json` **of
its own**, so the successful Ohnium check is a direct local kernel check, not a
pinned reproducible project build. (`formal/leanmath/lakefile.toml` and
`formal/leanmath/lean-toolchain` belong to the imported archive and configure a
package named `leanmath` that is not this repository's.)

`RecognitionChamber.lean` has not been checked successfully. It also contains
a `sorry` in the finite-depletion target, so merely resolving Mathlib would not
make it a closed proof artifact. The three P-tagged S4 claims
(`MATH-S4-LOOP_ZERO`, `MATH-S4-GAUGE_INVARIANCE`, `MODEL-S4-BORDON_CEILING`)
continue to rest on exact numerical checks in `tests/test_s4_g100.py` and their
stated mathematical assumptions; they must not be cited as Lean-verified.

To make the Recognition surface reproducible, add a pinned Lean/Mathlib project,
close all admitted obligations, run `lake build`, and bind the result to a
`ProofEnvelope`.

## Ohnium scope

The accepted Ohnium file proves only a three-step A/U/M cadence, the exact
cardinalities `40` and `7 + 21 = 28`, and a conjunction whose return/accounting
properties are explicit hypotheses. It does not formalize the Hopf map, QFI,
adiabatic or quantum dynamics, cognition, or a physical observatory.

## RecognitionChamber theorem targets

| target | statement | status |
|---|---|---|
| **P1** | `0 ≤ loopDefect T x` for any pseudo-metric | trivial from `dist_nonneg`; exercised by 200 seeded random transports |
| **P2** | `T.backward (T.forward x) = x → loopDefect T x = 0` | trivial from `dist_self`; exercised by identity, exact permutation inverse, orthogonal gauge round trip — all return `0.0` exactly, not approximately |
| **P3** | `loopDefect (conj G T) (G x) = loopDefect T x` for isometric `G` | the one with content; verified numerically to `1e-12` on a *deliberately lossy* probe, and the chamber's output is bit-identical under an orthogonal gauge change |
| **P4** | `d > ρ → ∃ t, level t ≤ 0` for constant refill and draw | model target; the current source contains `sorry`, so this obligation is open |
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
