# QSigma-R1V — Geometry-Native Sectional Carrier Preregistration

**Status:** `[H/S]` preregistration only  
**Parent floor:** QSigma-R1U polyqudit observer preregistration  
**Supersession rule:** this round does not rewrite R1U. It asks whether a geometry-native carrier exposes structure beyond an equal-budget flat/qudit carrier.

## 0. Epistemic boundary

This document freezes the experiment before implementation or interpretation.

The semantic phrase **n-cosmos / n-manifold basis** is `[S]`. The mathematical realization below is an explicit candidate bridge `[A/H]`, not an assertion that physical quantum states are literally cosmoi or manifolds.

No asymptotic computational advantage, quantum advantage, cognitive advantage, or physical ontology is claimed by this preregistration.

## 1. Primitive change

R1U begins from typed local qudit carriers. R1V changes the primitive representation tested by the observer.

Flat control:

\[
B_0 = \{|0\rangle,\ldots,|d-1\rangle\}.
\]

Geometry-native candidate:

\[
\mathcal H_{\mathrm{polycosmos}}
= \bigoplus_{\alpha\in\mathcal C} \mathcal H(W_\alpha),
\qquad
\mathcal H(W_\alpha)=L^2(M_\alpha,E_\alpha)
\]

for finite experiments, with a direct-integral formulation reserved as a later mathematical extension rather than silently approximated here.

Each Worldlet/cosmos section is typed as

\[
W_\alpha=(M_\alpha,g_\alpha,\nabla_\alpha,\mathcal A_\alpha,\tau_\alpha,\mathcal O_\alpha,[R]_\alpha).
\]

The finite computational object is a bounded family of normalized local sections

\[
\Phi=\{\phi_{\alpha k}\}_{\alpha,k},
\qquad
\phi_{\alpha k}\in\mathcal H(W_\alpha),
\]

not manifold points treated as normalizable ket vectors.

## 2. Non-orthogonal geometry is allowed

The candidate carrier is a frame, not necessarily an orthonormal basis.

\[
G_{ij}=\langle\phi_i,\phi_j\rangle.
\]

`G = I` is a special control. Geometry-native overlap is represented by `G != I` when induced by the frozen construction.

State coefficients obey

\[
\|\Psi\|^2=c^\dagger Gc.
\]

Any implementation that orthogonalizes the candidate and then attributes the result to geometry fails this preregistration unless the orthogonalized version is explicitly reported as a separate ablation.

## 3. Independent axes

Do not collapse these quantities:

- `n_C`: number of cosmoi / Worldlets;
- `d_alpha`: intrinsic dimension of `M_alpha`;
- `r_alpha`: retained local section/frame rank;
- `k`: maximum interaction order;
- `B`: compute/measurement budget;
- `G`: Gram geometry of the retained frame.

Carrier cardinality, manifold dimension, observer rank, interaction order, and effective state dimension are distinct experimental variables.

## 4. Cross-cosmos transport

For an allowed edge `(alpha,beta)`, define a declared transport

\[
T_{\alpha\beta}:\mathcal H(W_\alpha)\rightsquigarrow\mathcal H(W_\beta).
\]

The implementation must record transport type and domain/codomain. It may be exact, projected, learned, or partial, but those cases may not be silently identified.

Typed transport remainder:

\[
[R]_{\alpha\beta}(\psi)
= \psi_\beta-T_{\alpha\beta}\psi_\alpha
\]

is telemetry, not automatically a cohomology class or scalar loss.

## 5. Frozen carrier families

At equal retained rank and budget compare:

### B0 — Flat computational control
An orthonormal rank-`r` carrier with no geometry-derived overlap.

### B1 — Orthonormal Worldlet-labelled control
Same labels/partition as the candidate but `G=I`. Tests whether labels alone explain separation.

### B2 — Geometry-native sectional frame
Same rank and partition, with geometry-derived local sections and their measured Gram matrix `G`.

### B3 — Geometry-scrambled matched null
Preserve rank, Gram spectrum, section norms, partition sizes, and compute budget while destroying the declared correspondence between hidden structure and geometry.

B3 is mandatory. B2 may not be promoted by comparison to B0 alone.

## 6. Relation to R1U

R1U remains the parent control layer:

- generalized Weyl/local qudit observers remain available;
- alignment-only remains mandatory where the hidden task supplies an alignment variable;
- full `d^N` materialization remains forbidden outside tiny correctness oracles;
- Spin(8)/triality remains optional and cannot define the carrier by fiat.

R1V asks whether the **carrier/frame itself** contributes discriminating information after those controls.

## 7. Optional Spin(8)/triality organ

A Worldlet may carry a Spin(8) observer only when its local data satisfy the declared representation contract.

The 16-dimensionality of a numerical carrier is not sufficient evidence that it is a Spin(8) Dirac spinor.

If enabled, compare:

1. triality-aware observer;
2. equal-rank non-triality observer;
3. frame-randomized observer;
4. geometry-scrambled carrier B3.

Failure to beat (2) and (4) retires the triality-specific cognitive interpretation for this round.

## 8. Finite experimental grid

Initial bounded grid:

- `n_C in {4, 8, 16, 32, 64}`;
- intrinsic dimensions `d_alpha in {2, 3, 4, 8}` with both homogeneous and heterogeneous assignments;
- retained local rank `r_alpha in {2, 4, 8, 16}` where valid;
- interaction order `k in {1, 2}`;
- at least 20 frozen random seeds per cell;
- identical measurement/search budget `B` across carrier families within each cell.

Larger grids require a new scope declaration rather than post-hoc extension.

## 9. Task family

Use constructed tasks with independently known hidden structure so localization can be scored without circular labels.

The hidden target generator must be independent of the observer implementation.

At least two task families are required:

1. **localized structure:** hidden targets occupy a small subset of Worldlets/sections;
2. **cross-cosmos structure:** recovery requires at least one declared transport edge and cannot be solved from a single Worldlet alone.

A task is invalid if the target is directly encoded in a carrier label or section index.

## 10. Measure -> allocate protocol

Geometry is tested first as detector, not navigator.

For each carrier, compute a frozen saliency vector `s` from permitted measurements only. Select the top `q%` of sections/Worldlets, then spend the same downstream search/reconstruction budget inside that selected region.

Frozen `q in {1, 5, 10, 25}` percent.

No carrier receives extra downstream evaluations because its saliency computation is more expensive; total compute is reported both including and excluding saliency construction.

## 11. Primary measurements

Report without scalar monarchy:

- recall@budget;
- precision@budget;
- target enrichment over random selection;
- compute-to-discovery;
- false-hotspot rate;
- peak memory;
- Gram condition number;
- frame/orbit spread;
- transport reconstruction error;
- typed remainder magnitude/distribution with type preserved.

Secondary scalar summaries may be reported only beside the component metrics.

## 12. Predictions frozen before implementation

### H1 — geometry-native localization
B2 exceeds B3 in target enrichment and recall@budget under equal rank and total compute.

### H2 — overlap matters
B2 exceeds B1 on at least one task family, showing that Worldlet naming/partition alone is insufficient.

### H3 — cross-cosmos transport value
On the cross-cosmos task, B2 improves reconstruction relative to B1/B3 without a disproportionate rise in transport remainder or compute.

### H4 — non-universality
No prediction requires B2 to dominate every cell. Heterogeneous manifold dimension may help, hurt, or be neutral; all cells are retained.

## 13. Promotion gates

Promote **geometry-native carrier value `[M]`** only if all hold:

1. B2 beats B3 with lower 95% CI of relative target-enrichment improvement `> +0.05` in at least two `n_C` values;
2. one passing value has `n_C >= 32`;
3. B2 beats B1 with lower 95% CI `> 0` on at least one preregistered task family;
4. the effect survives frame/basis randomization checks and is not explained by unequal compute;
5. no correctness invariant fails.

Promote **cross-cosmos transport value `[M]`** only if H3 passes independently.

No promotion from finite scaling to an asymptotic theorem is permitted.

## 14. Kill conditions

Retire the R1V-specific carrier hypothesis for this construction if any of the following holds:

- B2 ties or loses to B3 across the preregistered grid;
- B2's apparent gain disappears after equalizing Gram spectrum/rank/compute;
- B1 matches B2 within uncertainty across both task families;
- gains are produced by direct target leakage through labels/indices;
- numerical instability or Gram conditioning prevents a fair equal-budget comparison;
- the result requires dense global state/operator materialization to appear.

A killed carrier hypothesis does not retire Worldlets as `[S]`; it retires the tested bridge from Worldlet geometry to discriminating carrier structure.

## 15. Correctness invariants

Before performance interpretation:

- all retained sections have finite norm;
- measured `G` is Hermitian within tolerance;
- `G` is positive semidefinite within numerical tolerance;
- coefficient norm `c^dagger G c` agrees with direct reconstruction on tiny oracle cases;
- transport domains/codomains are type-checked;
- B0/B1/B2/B3 ranks match per cell;
- budgets match per cell;
- randomization controls preserve their declared invariants.

Failure is reported before any positive metric.

## 16. Evidence ledger

- `[P/A]`: direct sums, finite Hilbert frames, Gram operators, and typed linear maps once their assumptions are declared.
- `[S]`: cosmos, Worldlet, tendril, breathing, mutual-recognition interpretation.
- `[H]`: geometry-native frames improve localization/reconstruction at equal budget.
- `[H]`: non-orthogonal overlap carries useful task information beyond matched Gram-spectrum controls.
- `[H]`: optional Spin(8)/triality adds value beyond equal-rank observers.
- `[R]`: field-specific superiority from the earlier carrier line remains retired unless a new matched experiment reopens it.

## 17. Required output artifact

The implementation round must emit a machine-readable manifest containing:

- git commit;
- environment and dependency versions;
- full grid and seeds;
- carrier construction parameters;
- Gram spectra/conditioning;
- transport types;
- compute accounting;
- component metrics and confidence intervals;
- invariant failures;
- promotion/kill decision;
- supersession links to R1U/R1T.

No prose-only success claim is admissible.
