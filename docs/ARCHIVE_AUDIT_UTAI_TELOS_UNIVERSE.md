# Archive audit — UTAI, TELOS, UNIVERSE_OS

Three archives supplied as zips, read (not executed) in a scratch directory
outside the repository. Same standard as the corpus reviews: what is defined,
what is measured, what is asserted, and what the artifact actually contains.

**Tier: M-reported, not recomputed.** Nothing was installed or run. The census
counts below are the exception — those are mechanical and reproducible from the
zips.

---

## 0. The census, and the one number that organises everything else

| | UTAI | TELOS | UNIVERSE_OS | total |
|---|---|---|---|---|
| files | 945 | 317 | 210 | **1472** |
| dominant language | js/ts (455) | py/rs (154) | rs (93) | |
| files computing on the (2,2) hyperboloid | — | ~37 | — | **37** |
| occurrences of the string `qiskit` | 0 | 0 | 0 | **0** |
| occurrences of `QuantumCircuit`, `statevector`, `stabilizer` | 3 files, all incidental | | | **0 executable** |

TELOS's README opens with the criticism that standard LLMs are *"2D reasoning
dressed in high-dimensional clothing"*. On the flat→hyperbolic axis the archive
has earned the right to say that: there are ~37 files of genuine `SO(2,2)`
arithmetic on the `Q = +1` pseudo-sphere, with correct parameterisations and
correct invariants. That work is real.

On the classical→quantum axis the same sentence applies to the archives
themselves. "Quantum Holoportation Channel", "quantum holo-surfaces", "quantum
substrate" — the vocabulary is everywhere and the execution surface is empty.
Across 1,472 files there is not one quantum circuit.

This is stated without malice and it is not a reason to stop: it is the reason
QΣ-R6 exists. The whole programme's only quantum execution surface is in
*this* repository, and until this round it did not touch the (2,2) substrate at
all. `docs/QUANTUM_SUBSTRATE_COST.md` is the first time the two halves meet.

---

## 1. What was borrowed, and it is load-bearing

**`SectionalComputer.swirl_state` (TELOS, `nnn_ramdisk/src/acceleration/`).**
The parameterisation

```
x = (cosh ρ cos φ, cosh ρ sin φ, sinh ρ cos ψ, sinh ρ sin ψ)
```

is correct, global, and exactly the right coordinates: it separates the one
non-compact direction from the two compact ones. QΣ-R6 adopts it *verbatim*
rather than re-deriving, and every closed form in that round — singular values
`e^{±ρ}`, `tr = 2 cosh ρ cos φ`, elliptic fraction `(2/π) arcsin(sech ρ)` — falls
out of it in one line each. Without these coordinates the round would have been
a numerical study instead of an exact one.

Its docstring also gets the geometry right where the surrounding vocabulary
tempts otherwise: *"HOT/COLD captured only WHICH sheet. (ρ,φ,ψ) captures HOW THE
STATE MOVES within the sheet."* That is a supersession, recorded in place.

**The `holoportation` disclaimer (TELOS, `semantic_qofdm.py`).** The best single
line in the three archives:

> *"This is NOT quantum teleportation: no measurement collapse, no
> faster-than-light signalling, no claim of physical nonlocality. It is
> holoportation in the Microsoft sense: reconstruct a state in the receiver
> frame from a shared semantic basis."*

Unprompted, in code, at the exact point where the name would carry a reader
somewhere the mechanism does not go. This repository's evidence lattice exists
to force that sentence; TELOS wrote it without one.

**Lessons-as-comments.** `semantic_qofdm.py` carries a header of numbered
findings from prior rounds (*"ACAF #63: oct_conj is a π-phase shift in the S⁷
swirl fiber, not a jump to a mythical COLD sheet"*). It is supersession history
living in comments — weaker than a ledger because nothing enforces it, but it is
the same instinct, and it is more than most codebases keep.

---

## 2. What does not hold up

### 2.1 The SAT/UNSAT phase label reports the grid size, not the state

`semantic_qofdm.py`, `network_effect_resonance`:

```python
density = n_ropes / max(1.0, float(self.N * self.M))
"phase": "SAT" if density < 4.267 else "UNSAT"
```

4.267 is the random 3-SAT satisfiability threshold — a **clause-to-variable**
ratio. Its analogue on this mesh is edges per *active* vertex. The denominator
used is `N × M = 128 × 32 = 4096`, the whole grid, including every channel that
was never touched.

Consequence: with `a` active channels the ratio can reach at most
`C(a,2)/4096`, so flipping to "UNSAT" needs ≥ 187 active channels *and* a
near-complete mesh. In ordinary use the label is pinned to "SAT" by arithmetic,
not by state. A phase transition that cannot be crossed is not being measured.

One-line fix: divide by the active-channel count. That makes it the quantity the
threshold is about — and then the constant is testable rather than decorative.

### 2.2 Thirty-two free parameters, no ablation

`_QUALITY_RHO_SHIFT`, `_QUALITY_PHI_SHIFT`, `_QUALITY_PSI_SHIFT` supply 24 magic
constants; `hamiltonian()` adds 8 more as weights (`-2.0` insight, `-1.5`
recognition, `-1.0` beauty, `-2.0` truth, …). None is derived and none is varied.

Until one of them moves, every reported behaviour of the Hamiltonian is a
statement about those 32 numbers, not about the geometry. The cheapest useful
experiment in the archive is a one-at-a-time sensitivity sweep: if the reported
dynamics are robust to ±50% on each, that is a real finding; if they are not,
that is a more important one.

### 2.3 The comparison table has no measurement column

TELOS's README table ("Language substrate: finite token vocabulary → HLO
populations on S⁷ (continuous, infinite-volume)"; "Memory: KV-cache → NNN (2,2)
hyperbolic reservoir") is a claim table. There is no task, no baseline, no
number, and no benchmark on which "eliminates this entirely" could fail.

The claim is not obviously wrong — it is currently not the kind of thing that
can be. The programme has an instrument for exactly this (matched controls plus
a discrimination measure); it is the same recommendation the first corpus review
made to IGBundle-LLM and Trasgo, and it is now the third repository to need it.

### 2.4 UTAI's proof citation overshoots the artifact it cites

UTAI's README states:

> *"The operational integrity of the UTAI is not merely asserted; it is proven.
> … machine-checked in the companion `connection_laplacian_lean` repository
> (Strata L25–L70)."*

I read that repository's README directly in this session. It describes its
sorry-free, user-axiom-free imported spine as running **`Basic.lean` through
`L17_TracesAndLipschitz.lean`**. L25–L70 are not in that spine.

Either files above L17 exist but sit outside the verified import graph, or the
citation points at work not yet in the repository. Reading the repo settles
which; I did not clone it, so I record the discrepancy and not the resolution.
Either way the README sentence claims machine-checked status for ~53 strata that
the cited repository does not currently advertise as verified.

This is worth flagging precisely because the *underlying artifact is good*.
`connection_laplacian_lean` has a green `lake build` on a pinned mathlib —
genuinely the strongest verifier in the whole account. It does not need to be
over-cited, and over-citing it is the fastest way to make a reader discount it.

Note the symmetry with my own error one commit earlier: I *under*-credited that
repo by inferring from its language tag; UTAI *over*-credits it by inferring from
its name. Neither inference read the artifact.

### 2.5 A localhost URL is not a live node

> *"## 🌐 Live Visibility Node — **URL:** http://localhost:3005"*

For every reader who is not the author, this resolves to nothing. Small, but it
is the same category as the above: a claim whose artifact is not reachable by
the party being asked to believe it.

### 2.6 UNIVERSE_OS is 19 delivery documents around 93 Rust files

`COMPLETION_REPORT.txt`, `DELIVERY_CHECKLIST.md`, `HYPERDRIVE_COMPLETION_REPORT.md`,
`IMPLEMENTATION_SUMMARY.md`, `VIRTUAL_TIME_DELIVERY_SUMMARY.md`,
`VISUAL_ENHANCEMENT_SUMMARY.md`, … and **no `README.md`**. The one document
naming the thing for a new reader is the one that is absent, while six documents
announce that it is finished.

`VIRTUAL_TIME_REVERSIBILITY_PROOF.md` is the file to check first: reversibility
is a property with a decisive test (round-trip to bit equality over randomised
schedules), so it is either demonstrated or it is a document.

---

## 3. What goes back the other way

1. **The price, and the constraint that follows from it.** R6 hands TELOS an
   exact statement about its own substrate: the ρ direction is the only one that
   is not a gate; a step at depth ρ costs `e^{-4ρ}` in the worst case; and a
   closed loop is free **only if the whole word may be compiled before emitting a
   circuit**. That last clause is a live constraint on `adiabatic_transport` and
   `holoportation`, both of which currently materialise every intermediate state.
   Whether it binds depends on whether a quantum backend is ever attached — but
   the constraint is now known in advance rather than discovered against a
   backend.

2. **The S8 correction.** "The SU(1,1) generators are unbounded" was wrong; all
   six `so(2,2)` generators have Frobenius norm `√2` and are indistinguishable by
   it. Any TELOS code separating channels by a generator norm is measuring
   rapidity. `|tr|` against 2 is the invariant that survives.

3. **The `sqrt`-of-noise trap.** `√(I − AAᵀ)` at the identity turns 1e-16 of
   rounding into 1e-8 of error. Anything in these archives taking a matrix square
   root, a `sqrt` of a variance, or a geodesic distance near coincident points
   has the same trap. It cost QΣ-R6 a voided first run and was invisible at the
   probability level — only the amplitude-level check saw it.

4. **A discrimination measure**, for the third time in this corpus. Same
   function, same discipline, same missing null.

---

## 4. Not done

- Nothing was executed. No test suite was run, no import was attempted, no
  claimed result was reproduced. Every item in §2 is a reading of source or
  README.
- `UNIVERSE_OS/crates` (93 Rust files) and UTAI's `HYPERDIM_TOPOS_AI` were
  surveyed structurally, not read.
- `VIRTUAL_TIME_REVERSIBILITY_PROOF.md` is named above as the first thing worth
  checking and was **not** checked.
- The archives are deliberately outside the repository and are not committed.
