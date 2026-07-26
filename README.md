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
- **Respiration is reservoir dynamics**, not a scheduled interruption. From the
  Bordón (Galician gaita) architecture: a *fol* reservoir decouples intake from
  expenditure and a *bordón* drone is never interrupted. Sharp consequence:
  `drone_ceiling = refill_rate` — an uninterrupted channel is fundable only out
  of steady income, never out of buffer, at any capacity.
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
python3 experiments/run_visibility.py # Round V1: coupling field vs code distance
python3 experiments/run_replication.py # Round V2: depth, intervals, distributions
python3 experiments/run_sentinel.py   # Round S1: Sigma-inf sentinel vs its kill condition
python3 experiments/run_stokes.py     # Round S2: Stokes router vs its kill condition
python3 experiments/run_sheaf.py      # Round S3: sheaf obstruction localisation + query claim
python3 experiments/run_s4_g100.py    # Round S4-G100: recognition chamber vs its gates
python3 experiments/run_s4_basis_attack.py  # S4: is the S3 claim basis-invariant?
python3 experiments/run_moving_frame.py     # S5: moving-frame orbit audit + invariant instrument
python3 -m pytest tests/ -q           # 193 tests
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
  quantities.py     typed coordinates: units, uncertainty, base-relativity
  bordon.py         Bordon respiration: reservoir dynamics, drone ceiling
  visibility.py     coupling field g_r: structure invisible to depth-r probes
  cayley_dickson.py associator failure ladder as an observability atlas
  statistics.py     bootstrap intervals; measurements that carry their uncertainty
  splitform.py      split forms over R and F_2; logical pairs; computed distance
  sentinel.py       sparse expanding-gap novelty diagnostic (RETIRED: see S1)
  stokes.py         Stokes matrices, braid action, basis-mutation router (S2)
  sheaf.py          cellular sheaves of worldlets; eight localisation instruments
  interference.py   holonomy oracle: b classical queries against 1 quantum one
  recognition/      S4-G100 chamber: worldlets, tendrils, aperture, nest, budget
  movingframe.py    frame bundle action; orbit-collapse vs orbit-resolution
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

Round S3 is the first pre-registered Σ∞ prediction to **survive** its kill
condition: sheaf holonomy localises hidden cycle obstructions at AUROC 0.797
against 0.511 for shuffled overlaps and 0.508 for topology alone, at equal
dimension, equal arithmetic and an identical attribution rule (n = 300,
Δ = +0.286 [+0.258, +0.316]). The same round kills the hypercomplex clause by a
*tie* — quaternionic coordinates are exactly identical to a dimension-matched
real sheaf on their home ground and lose 0.231 off it — and finds the octonionic
clause **ill-posed**: above dimension 4 a vertex gauge induces no flat
connection, so a clean sheaf already carries holonomy on every cycle and there is
nothing for a defect to stand out against. Unit octonions are a Moufang loop, not
a group.

The one genuine quantum separation here is proved and bounded: reading a cycle
obstruction class costs exactly `b = E − V + C` classical queries against exactly
1 quantum query. Building the coherent oracle from classical data costs `E`
accesses, which exceeds `b` on every instance tested; recovering the class is not
localising the defect, and the decoding step that follows is unchanged for both
parties.

Round S4-G100 built the Reversible Recognition Chamber, preregistered ten gates,
and **failed six of them**. On five held-out nerve families the chamber is worse
than the closed-form S3 localiser it was built to improve on (pooled ΔAUROC
−0.033, winning 20 of 50 instances), and its apparent advantage tracks
budget-to-search-space ratio rather than adaptivity or ordering. The declared
expectation on record was a negative result, and that is what the held-out
families produced.

Two things came out of it that matter more than the failure. The **dominance
region caught what a weighted score would have passed**: the ordered-flow gate
clears +0.033 while the method sits 0.033 *below* baseline, so any aggregate
containing that component could have carried the round on a measurement of the
chamber against itself. And the mandatory attack suite exposed a defect in a
**prior** claim — Round S3's headline was measured inside one arbitrary
fundamental cycle basis, and under an admissible worldlet relabelling it retains
its direction but only 20% of its effect size (+0.269 → +0.055). Every
localisation number on this host is a basis-relative quantity.
`EXP-S3-SHEAF_LOCALISATION` is superseded, its original text preserved.

Round S5 closed the bridge S4 left open. A moving-frame audit -- a *path* through
the frame bundle (worldlet relabelling x edge reordering x orthogonal gauge,
composed as a genuine group) rather than a single attack -- classifies every
instrument as **orbit-collapsed** (constant on the orbit: it sees the object) or
**orbit-resolving** (varies: it reports frame coordinates). Every cycle-basis
instrument is orbit-resolving, with worst deviations from 0.245 to 0.644.

A basis-free replacement -- per-overlap Dirichlet energy of the sheaf Laplacian's
lowest eigenspace, which never mentions a cycle basis -- is **exactly**
orbit-collapsed, worst deviation 0.000, sitting with the topological control. It
is also the strongest instrument: **AUROC 0.964 against 0.776**, and its contrast
against matched controls retains **96%** of its magnitude across an admissible
frame change where the S3 instrument retained 20%. Invariance did not cost
accuracy here; it bought accuracy.

Two integrity gates ran first and are the reason to trust it: equivariance of the
group action (8e-16) and loop closure (exactly 0, no hidden state). The first
implementation failed equivariance with *infinity* -- it re-sorted edges, which is
a canonicalisation rather than a group operation -- and the gate correctly
invalidated every orbit statistic built on it before any of them were reported.

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
