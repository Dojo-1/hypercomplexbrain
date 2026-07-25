# hypercomplexbrain — AION-Ω^Q / QΣ-R³ʙ

An audited almost-all-quantum polycosmic brain architecture, and the harness that
grades it.

The architecture is in **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

## The correction, four times

**First:** QΣ∞ measured quantumness by counting edges written as unitaries. That
metric returns **1.0000 for every all-unitary core** — min equals max across 150
random cognitive cores, so it cannot rank two designs or detect a regression.

```
                                          Q_naive   q_sim_upper
classical reversible core                  1.0000     0.0000
GHZ (maximal entanglement, zero magic)     1.0000     0.0000
random Clifford, depth 40                  1.0000     0.0000
Clifford + 35 T                            1.0000     0.9992
Hadamard + Toffoli (Grover-shaped)         1.0000     1.0000
```

**Second:** replacing it with `Q_cert` repeated the same error one level up — one
scalar swapped for another. Peer audit found five concrete defects (see
[§0.5](docs/ARCHITECTURE.md)), including that `H T T† H` is exactly the identity
and scored **0.4568**. All fixed. The scalar is retired in favour of an eight-
coordinate **Quantum Necessity Atlas**:

- **interval-valued** — `[q_sim_lower, q_sim_upper]`, because exhibiting a good
  simulation bounds cost from *above*; proving none better exists is a different
  problem. `q_sim_lower = 0` until someone supplies one.
- **a section of a bundle** — a resource monotone is defined only over a named
  free theory. Same state, different answers: |+⟩ scores **1.0000** over
  classical-reversible and **0.0000** over stabilizer.
- **transport before comparison** — sections over different free theories raise
  rather than compare. 1.2 bits of magic is not 0.9 bits of entanglement merely
  because both are floats. `transport_to()` declares what is preserved,
  transformed, lost, and why.
- **promotion is a cone, not a scalar** — a pre-registered region over eight
  outcome dimensions. A Clifford fault-tolerant memory has `q_sim_upper = 0` and
  is *not* "zero quantum"; a padded identity circuit is hard-ish to simulate and
  does no work.

**Third:** a second audit found three flattenings still inside the atlas and one
monarchic scalar on top of it — and the fix **falsifies this project's own
hyperbolic base**. Measured on the live free-theory structure (a diamond DAG, not
a tree): **Gromov δ/diameter = 0.5, the maximum possible for any metric space.**
The Poincaré base does not earn its curvature on the structure it actually
carries, and is retired. The earlier 1.02×/2.25× figures described a *synthetic*
binary tree, not this base.

**Fourth:** coordinates are now typed (`Bits >= Strength` raises; a `Monotone`
cannot exist without a declared free theory), and transport holonomy is measured.
Carrying a section around a loop of free theories and back gives defect **∞** —
it does not return. Carrying the *state* around the same loop gives defect
**exactly 0.0**. A monotone is computed *from* a state, not carried *by* a
section: **an organ that keeps only its own summary statistics has a
path-dependent self-image.**

## What this buys

Results the draft architecture stated as targets, now decided by measurement:

- **Coherentization is not a residency gain.** Measured gain is 5.2% of advertised,
  and is bought by spending more magic, not by new capability.
- **Exhalation is forced**, by ancilla accounting and Bennett pebbling — not chosen
  by taste. The breath period is computable. It is *entropy export*, though, and
  measurement is only one of seven channels for it.
- **Entanglement is not quantumness** and is not even frame-invariant (0 bits in one
  frame, 1 bit in another, same situation).
- **The fusion grammar is coherent and order-sensitive**: pentagon and hexagon hold
  to 1e-16 while the associator is 1.11.
- **`rank(G)` is the holonomy span dimension**, not "identity capacity" — five
  loops, span three. Robustness also needs `effective_rank` and conditioning.
- **Self-knowledge is bounded but not impossible.** An earlier claim that
  no-cloning made self-tomography impossible was too broad and is retired:
  syndrome extraction reads a protected register, extracts 2 bits, and leaves the
  logical state at fidelity **exactly 1.000000**. The architecture depends on
  this. Löb and no-cloning obstruct different closures; neither supersedes the
  other.

And one budget the draft never wrote down: `q_sim_upper ≥ 0.95` costs **4.16 non-Clifford
operations per logical qubit per episode** — about 830 magic states and ~10⁵ coherent
episodes on a 200-logical-qubit machine.

## Run it

```bash
pip install qiskit numpy scipy pytest

python3 experiments/run_audit.py      # every claim, computed
python3 experiments/acaf_sweep.py     # 150-core falsification sweep
python3 -m pytest tests/ -q           # 67 tests
```

## Layout

```
src/aionq/
  atlas.py          Quantum Necessity Atlas: intervals, free-theory bundle, transport
  advantage.py      causal advantage cone: promotion is a region, not a scalar
  stack.py          typed quantities; transport holonomy around free-theory loops
  residency.py      simulation-cost interval (one coordinate of the atlas)
  coherentize.py    Stinespring coherentization and what it actually buys
  budget.py         coherence budget, forced breath schedule, magic budget
  process.py        process tensors and measurable temporal memory
  fusion.py         Fibonacci fusion grammar, pentagon/hexagon verification
  identity.py       polyholonomic identity, Gram PSD theorem, frame invariance
  selfknowledge.py  bounds on self-knowledge, and the syndrome counterexample
  qrf.py            quantum reference frames
  governance.py     P/A/M/H/S/R evidence lattice as executable CI policy
experiments/        audit and ACAF sweep
tests/              one test per falsifiable claim
docs/ARCHITECTURE.md
```

## Status

`q_sim_upper` is an **upper bound on classical hardness** built from the simulation
strategies implemented here (basis-permutation, stabilizer, stabilizer rank), and it
is **compiler-dependent** by construction: a compiler portfolio defeats the
cancellation attacks in the sweep, but circuit equivalence is intractable in general,
so residual gaming vectors exist. A better classical algorithm lowers the bound.
That direction is correct: it can only be revised downward by classical progress,
never inflated by notation.

Nothing here connects any coordinate to cognitive performance. The advantage cone
is the right *shape* to receive an answer; no experiment has produced one, and
`promote()` now returns HOLD rather than falling back to a scalar when no cone is
supplied. The base is still a containment graph rather than a measured
free-conversion metric, so no geometry is assigned to it. The base category is
still one axis where it should be six. The architecture is auditable; it is not
justified.

The evidence lattice (P/A/M/H/S/R) is enforced in code: an A-tagged claim cannot
exist without stating its surrogate, an H-tagged claim cannot exist without a kill
condition, retired claims cannot be cited in results, and corrections supersede
rather than overwrite. Applying the **A** tier moved five claims — including
`q_sim_upper` — out of P/M, because their checks are weaker than the claims they
support. See [`docs/SOURCES_DIGEST.md`](docs/SOURCES_DIGEST.md).

Not a consciousness claim, not an AGI claim, not a completed proof.
