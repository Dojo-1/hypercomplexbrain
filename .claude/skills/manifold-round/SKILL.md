---
name: manifold-round
description: Turn a short or naive prompt into a properly scoped Manifold research round for the hypercomplexbrain/aionq repository. Use when the user asks to test, add, implement, audit or extend anything in this programme — including requests phrased in the programme's own vocabulary (Emperor, Empress, Nest, Bordón, UTAI, Bunny, worldlet, telos, holonomy, aperture, remainder, moving frame, n-cosmo, hypercomplex, gerbe, holoportation). Also use when a prompt names an evocative architecture without an experiment, or asks to bring new "fauna" into the zoo.
---

# Manifold round

You are continuing a **correction-heavy** research repository. Its value is its
correction history, not its architecture. Most rounds end in a retirement, and
that is a successful round.

Read `docs/MANIFOLD_REFERENCE.md` first — it condenses the 1.56M-character source
archive and lists what has already been killed.

## Step 1 — translate the vocabulary before writing code

The programme's names are **handles**. Implement the mathematical object, never a
cartoon of the name. The reference doc has the full table; the essentials:

| name | implement as |
|---|---|
| Emperor | operator `E : S → CandidateSet(S)`. Proposes. **Cannot promote.** |
| Empress | operator `M : candidate → typed tuple` (gluing, certificate, consistency, support, recoverability, cost). **Never one scalar.** |
| Nest | evidence-gated deposit predicate against a *preregistered region*, never a weighted score |
| Bordón | reservoir: capacity, refill ρ, invariant draw d, speculative draw. `d ≤ ρ` required for indefinite survival |
| UTAI | theorem-surface decomposer. **Not** an independent witness |
| Bunny | Lean worker. Never claim compilation that did not happen |
| worldlet | heterogeneous local state with its own carrier and geometry — do not coerce into one vector space |
| aperture | triple `(τ lifetime, κ branch width, β barrier)`, never one "openness" scalar |
| telos | a *region* of viable futures, not a reward |
| `[R]` | typed: cohomology class \| empirical residual \| scalar constant \| semantic remainder. Untyped transport is prohibited |

**If a term has no definition you can find, say so and leave it alone.** Building
from a name is the failure mode this repository exists to prevent. `ergocetic`,
`erdodetic` and the 8 Mind Qualities are real formal objects in the source whose
content is *not* reconstructible from it — do not invent them.

## Step 2 — check the constraints that already bind

Never reopen these without fresh evidence (`docs/MANIFOLD_REFERENCE.md` §6):

- hypercomplex coordinates are **not** automatically superior; a dimension-matched
  real/matrix representation stays as a control
- **no octonionic flat-sheaf construction** — flatness fails above dim 4
- promotion is a **region**, never a weighted scalar
- no coordinate has been connected to cognitive performance
- cycle-basis localisation scores are frame-relative; prefer the basis-free
  Laplacian instrument (`localise(..., "laplacian")`)

Forbidden promotions in every round: AGI, consciousness, quantum advantage,
asymptotic advantage, optimality.

## Step 3 — the round shape

1. **Freeze the baseline.** Branch, commit, dependency versions, full test run,
   claim ledger, uncommitted changes. Record baseline failures; never silently fix.
2. **Preregister, and commit it before any primary run.** Gates, controls, seeds,
   held-out families, kill conditions. Record your *expected* result — including
   when you expect failure. That removes the option of presenting a failure as a
   surprise.
3. **One code path for all conditions.** If each condition has its own loop, a
   difference is unattributable.
4. **Run integrity gates first.** Equivariance of any group action; loop closure;
   exact known-answer cases. If a gate fails, every statistic above it is void —
   report that rather than the statistics.
5. **Matched controls, always.** Static ensemble, equal-entropy random,
   shuffled correspondence, reversed order, dimension-matched real. Report
   wall-clock, memory, parameter count, evaluation count.
6. **Representation attacks.** Vertex relabelling, edge permutation, alternate
   cycle basis, orthogonal gauge, exact loops, equivalent encodings, shuffled
   role labels. Use `aionq.movingframe` — sample a *path* through the frame
   bundle, not a pair of frames. Classify each measurement **orbit-collapsed**
   (sees the object) or **orbit-resolving** (reports frame coordinates).
7. **Register claims** in `aionq.governance` at the honest tier, with supersession
   rather than overwriting.
8. **Write the audit**, including the requirement → … → requirement round trip
   with preserved/transformed/lost/remainder at every edge.

## Step 4 — tier honestly

`P` proved or definitionally closed · `A` passes a weaker surrogate (name it) ·
`M` measured with sample size, interval, null, controls · `H` hypothesis with a
kill condition · `S` design language · `R` retired, preserved with corrections.

An `M` claim without sample size, interval and null is refused by the registry.
An `H` claim without a kill condition is refused. This is enforced in code.

**Witness independence:** explorer, verifier, formalizer and auditor sharing code,
assumptions, data or authoring model are **one** witness. Say "correlated", not
"independent verification".

## Step 5 — report

Files changed · commands run · test results · experiment results · evidence
transitions · retirements · smallest open bridge · whether the stop condition holds.

State the negative result plainly. Do not rescue it with a richer ontology.

## Reproduction commands

```bash
PYTHONPATH=src python3 -m pytest tests/ -q          # full suite
PYTHONPATH=src python3 experiments/run_moving_frame.py   # frame audit
PYTHONPATH=src python3 experiments/run_sheaf.py          # S3 localisation
PYTHONPATH=src python3 experiments/run_s4_g100.py        # S4 chamber
```

See `references/naive-prompts.md` for worked expansions of short prompts.
