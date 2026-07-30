# Repository review — 2026-07-30

## Scope and provenance

This review covers `jesusvilela/hypercomplexbrain` on branch
`claude/aion-brain-architecture-27f8ji`, HEAD
`c811ad7cd0d1aad7df7d60a1c81a529d8b85e15d`, plus the explicitly uncommitted
universal-Poincaré and n-ary HB0 changes in the current working tree. It corrects
the local Antigravity review at
`C:\Users\HAL900\.gemini\antigravity-ide\brain\8a3c1f0a-92d8-4602-90f7-e09d06b69aa0\repo_review.md`.
The worktree also contains pre-existing modified generated artifacts; this
review does not attribute those unrelated changes to the present slice.

## Outcome

The repository is a large evidence-governed research harness, not an
implementation of AGI or a demonstration of cognitive advantage. Its strongest
property is executable separation between proved, axiomatized, measured,
hypothesized, semantic, and retired claims. The current HB0 slice strengthens
that separation by making Poincaré \(H^4\) the one universal geometric base
while refusing to collapse its heterogeneous fibers or its n-ary decision
field into a binary contest.

Current census:

| Object | Current count |
|---|---:|
| Python modules under `src/aionq` | 72 |
| Test files | 29 |
| Experiment scripts | 37 |
| Documentation files under `docs` | 36 |
| JSON manifests | 20 |
| Artifact directories | 24 |
| Evidence envelopes | 27 |
| Lean source files under `formal` | 2 |

## Universal hyperbolic base

The active architectural object is

\[
\mathcal O =
\left(
B=H^4_{-1},
\{F_i\}_{i\in I},
\nabla,
\mathcal C_{\ge3},
\widehat{\mathcal C}_{\mathrm{Fin}(n)},
\check g,
H,
\Lambda,
[R]
\right).
\]

This is not a choice between two global geometries:

- \(B\) is the unique shared base within one architecture instance.
- `FreeTheory` is a categorical fiber index, not the base metric.
- Fisher, local Riemannian, local Poincaré, Euclidean, quaternionic,
  split-signature, and PSD structures are typed local fibers or controls.
- The Euclidean \(R^4\) control matches \(g^H_0=4I\) at the Poincaré origin and
  is retained as a curvature ablation; it cannot replace or vote against \(B\).
- Configurable \(H^n\) objects used by dimensional tests are alternative
  architecture instances, not simultaneous universal bases.

The canonical implementation uses the future hyperboloid

\[
H^4_{-1}=\{X\in\mathbb R^{1,4}:X^\top JX=-1,\ X_0>0\},
\qquad J=\operatorname{diag}(-1,1,1,1,1),
\]

with the open unit Poincaré ball as an isometric chart. It implements stable
distance, chart conversion, exponential/logarithm maps, Levi-Civita parallel
transport, future-sheet Lorentz isometries, and finite-conditioning gates.

The deterministic structural audit reports:

| Check | Observation |
|---|---:|
| Worldlet base points | 32 |
| Pair distances reviewed | 496 |
| Ball-coordinate affine rank | 4 |
| Hyperboloid ambient rank | 5 |
| Logarithmic tangent rank | 4 |
| Local fiber geometries | 4 distinct types |
| Maximum chart round-trip defect | \(6.25\times10^{-17}\) |
| Maximum distance-model defect | \(4.38\times10^{-16}\) |

The A claim is no longer inserted directly into the registry. It starts at S
and is promoted to A only after
`artifacts/hb0_universal_base/universal_base.envelope.json` verifies against the
manifest, deterministic audit, audit producer, and relevant implementation
modules. That envelope is integrity-bound to the current working tree but is
unsigned, self-recomputed, not commit-bound, and not independently witnessed.
`Registry.promote()` now also requires the envelope's claim/tag binding to
match the requested transition and reconstructs the claim under the destination
tag invariants before mutating either the claim or its envelope ledger.

## K13 is preserved, not inverted

The historical five-node free-theory containment graph is \(K_{2,3}\):

\[
\delta=1,\qquad
\operatorname{diameter}=2,\qquad
\frac{\delta}{\operatorname{diameter}}=0.5.
\]

The frozen placement gives hyperbolic distortion
`5.289745803610123` and Euclidean distortion `6.635501481435628`. Therefore:

1. K13 still falsifies the old claim that this graph empirically earns
   negative curvature from tree-likeness.
2. It did not satisfy the old matched-control kill condition in which
   hyperbolic distortion had to be no better than Euclidean distortion.
3. It neither proves nor retires the universal \(H^4\) contract, because graph
   distance and the declared atlas metric are different typed objects.

## N-ary anti-flattening review

`HypercomplexDecisionField` represents complete simplices with
\(3\le n\le8\), rather than assembling a global answer from binary comparisons.
Its load-bearing objects are:

- Helmert-centered contrast spaces for every higher cell;
- rank-loss and PSD wall projectors indexed independently by `(cell, channel)`;
- Cayley–Dickson quaternion products and an oriented ternary
  \(\Omega_{ijk}\) channel;
- exterior/Plücker coordinates for every base cell of arity
  \(3\le k\le p+1\);
- every unitary Fourier sector \(k\in\operatorname{Fin}(n)\), with inverse
  reconstruction and Parseval checks;
- typed double-overlap defects and an explicit triple Čech cocycle;
- separate adiabatic budgets for base, fiber, operator, projector, quality,
  Hamiltonian, rank, frontier, and evidence channels.

Pairwise distances and Pareto relations survive only as projections. A binary
wall has `global_decision_permitted = false`; a unique Pareto projection is
named `PARETO_SINGLETON_CANDIDATE`, not a winner. The global decision flag is
always false until a typed n-ary policy and runtime evidence resolver exist.

The unavoidable \(R^4\) quaternion carrier limit is also explicit: cells with
more than five alternatives have intrinsic contrast nullity and emit
`[R]_intrinsic_cell_collapse`. More alternatives are not silently compressed
into four coordinates and then reported as fully resolved.

## Sixteen-coordinate mind field without a scalar mind score

The cognitive vocabulary in HB0 is an engineering field, not a sentience
claim. Its eight requested coordinates

```text
grounding, self_reflection, godelian_identity, other_recognition,
mutual_resonance, adiabatic_patience, ergocetic_exploration,
erdodetic_return
```

are paired with eight conjugate coordinates for embodiment, temporal
polyphony, contextual composition, local/global literacy, holoportive
reconstruction, metaplasticity, judicial correction, and remainder
stewardship. Each coordinate has a separately testable operator and evidence
obligation. `MindQualityField.weighted_sum()` fails with
`FlatCollapseError`; viability is componentwise or Pareto, never a weighted
binary verdict.

The same separation is preserved in dynamics. The delivery Hamiltonian is a
six-component envelope for compute, coherence, identity, absorption,
exploration credit, and integration credit. Fast, mesoscopic, and slow clocks
are distinct. Recognition retains two directional scores, viewpoint-swap
defect, return fidelity, and absorption pressure. Holoportation reports its
null-space information loss rather than treating boundary agreement as global
reconstruction.

The teleportation and two-level tunnelling operators remain simulator-only
controls. Their reports explicitly set `advantage_claim = false`; they do not
establish hardware transport, quantum advantage, cognition, consciousness, or
general intelligence.

## QB1/QB2 quantum fibers: useful shadows with explicit ceilings

QB1 embeds a ball point \(x=r u\) into the qutrit density

\[
\rho_x=(1-r)|0\rangle\langle0|\oplus
       r\,|z(u)\rangle\langle z(u)|.
\]

It retains radius and finite hyperbolic depth but quotients the global
\(U(1)\) Hopf phase. The implementation now requires the exact canonical
Poincaré and tangent-matched Euclidean specifications; inverse recovery
rejects arbitrary qutrit states outside this open rank-one Hopf cone. This is
a typed density shadow, not an isometric replacement for \(H^4\).

QB2 lifts Levi-Civita transport into the positive-chiral \(SU(2)_+\) factor.
The negative chirality is an explicit remainder and the compact qubit fiber is
not presented as the noncompact base. Its optional Qiskit boundary consumes a
typed path tied to the canonical base, rather than accepting an unrelated list
of unitary matrices.

Both QB1 and QB2 remain local structural experiments. Their JSON files describe
preregistration intent, but there is no terminal evidence envelope or
independent witness for either slice. The QB2 flat-loop result is a programmed
ablation, and its curvature-span check evaluates the declared connection
formula rather than independently deriving \(F=dA+A\wedge A\). Those facts cap
the results below a governed measured/proved promotion.

## UTAI mathematical cross-check

The external corpus `H:\NP Completeness Bunny UTAI study` contributed
operational obligations, not borrowed theorem status:

- `L21_SectoralDecomposition.lean` proves an invertible Fourier block
  decomposition retaining all \(\operatorname{Fin}(n)\) sectors.
- `L22_HolonomyAnnihilators.lean` relates each sectoral kernel to holonomy
  annihilators.
- `L24_ZModRecognition.lean` sums sectoral kernel dimensions over the cover.
- The finite Čech harness requires pairwise coboundary compatibility and a
  triple cocycle.

Observed verification on 2026-07-30:

```text
lake build ConnectionLaplacian.L21_SectoralDecomposition \
  ConnectionLaplacian.L22_HolonomyAnnihilators \
  ConnectionLaplacian.L24_ZModRecognition
Build completed successfully under Lean 4.11.0 (lint warnings only).

python .\studies\cech_cover_gluing_harness.py
controlled: 76/76 PASS
adversarial: 29/29 caught
```

A whole-project UTAI `lake build` is not green: it fails at
`L47_FanoBerryKnotTower.lean` with elaboration, unsolved-goal, identifier, and
definition errors. No global UTAI proof status is inferred from the three
successful strata.

## Verification of this repository

Windows full suite, using a writable repository-local pytest temporary root:

```text
python -m pytest tests -q \
  --basetemp=.agent/pytest-hypercomplex-terminal-full-final \
  -p no:cacheprovider

1833 passed in 184.60s
```

The earlier Antigravity result, `1642 passed, 52 errors`, was not a green test
run even though its errors were environmental. With the temp-root issue
removed, the current worktree is green.

Evidence integrity:

```text
PYTHONPATH=src python -m aionq.verify_envelopes artifacts
27/27 envelopes verified
```

Only one envelope is independently recomputed. The new universal-base envelope
is valid but self-recomputed, so the independence count remains one.
Historical envelopes now check the live path first and may fall back only to
the immutable blob at their recorded Git commit; such a fallback emits a
warning instead of silently rebinding evidence to current code. The R4
effective-sample-size envelope's stale pre-rebind commit pointer was corrected
to its documented rebind commit `ad9a43f`, where both declared source hashes
match exactly. The HB0 envelope has an empty commit field and therefore cannot
use this historical fallback.

Local formal surface under Lean 4.32.2:

| Target | Result |
|---|---|
| `formal/OhniumObservatory.lean` | exit 0 |
| `formal/RecognitionChamber.lean` | exit 1: Mathlib unavailable |

`RecognitionChamber.lean` also contains one `sorry` at line 126. Therefore the
repository has one locally checked standalone Lean file and one incomplete,
dependency-blocked target—not three uncompiled files and not a fully compiled
formal surface.

## Remaining failure spectrum

The main open obligations are:

1. No experiment connects the architecture to improved cognitive task
   performance.
2. The universal Poincaré base is an A-tagged coordinate contract, not an
   empirically selected optimum.
3. The new base envelope lacks a commit binding and an independent witness.
4. The n-ary field deliberately cannot issue a global decision until its
   policy and evidence resolver are supplied.
5. The local formal surface and the whole UTAI corpus are not globally green.
6. `governance.py` remains a 1,431-line, 90,304-byte concentration of policy
   and claim data and is a maintenance boundary worth decomposing separately.

No consciousness, sentience, AGI, quantum advantage, or cognitive-superiority
claim follows from the implemented geometry.
