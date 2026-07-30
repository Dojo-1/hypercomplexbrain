# Universal Poincaré base

## Status and scope

`aionq.hyperbolic.PoincareBallBase` defines the repository-wide geometric
substrate

\[
B=H^n_{-\kappa},\qquad \kappa>0.
\]

The default is the conditioned `AION-universal-H4` atlas. This is an
**A-tagged architectural axiom**, not a measurement that the free-theory graph
has negative curvature. The historical K13 result remains intact: its
five-node \(K_{2,3}\) containment graph has
\(\delta/\operatorname{diameter}=0.5\), so the old tree-likeness justification
failed. `embed_hierarchy()` is frozen to reproduce that result;
`place_free_theories_on_universal_base()` is the separate live placement.
The claim is registered as `AXIOM-HB0-UNIVERSAL_POINCARE_BASE`. Its structural
surrogate is test-covered and promoted through a hashed working-tree envelope.
That envelope is unsigned, self-recomputed, and neither commit-bound nor
independently witnessed; the A tag is not external or empirical evidence.

Here “universal” means one unique shared base inside an architecture instance.
H⁴ is the canonical repository specification. Configurable Hⁿ instances used
for dimensional tests are mutually incompatible alternatives, not simultaneous
universal bases.

Universal base does not mean universal local metric. Free theories remain a
categorical index, and Poincaré, Fisher, Riemannian, Euclidean, quaternionic,
split-signature, and PSD structures remain typed fiber or control data over
\(B\).

## Definition

Let \(R=1/\sqrt\kappa\) and

\[
J=\operatorname{diag}(-1,+1,\ldots,+1).
\]

The canonical model is the future hyperboloid

\[
H^n_{-\kappa}
=
\{X\in\mathbb R^{1,n}:X^\top JX=-R^2,\ X_0>0\}.
\]

Its tangent metric is positive definite:

\[
T_XH=\{V:X^\top JV=0\},\qquad g_X(V,W)=V^\top JW.
\]

The open Poincaré ball is an isometric chart:

\[
\iota(x)=
\left(
R\frac{1+\|x\|^2}{1-\|x\|^2},
\frac{2Rx}{1-\|x\|^2}
\right),
\qquad
g_x=\frac{4R^2}{(1-\|x\|^2)^2}I.
\]

Distance uses the stable form

\[
d(x,y)=2R\,\operatorname{asinh}
\frac{\|x-y\|}
{\sqrt{(1-\|x\|^2)(1-\|y\|^2)}}.
\]

## Numerical domain

The mathematical object is unbounded; its `float64` implementation is not.
Curvature, Lorentz transforms, hyperboloid points, tangent operations,
exponential steps, and radial points are accepted only when their residuals and
conditioning are finite and certifiable. Derived `NaN`/`Inf`, cancellation
outside budget, unrepresentable rapidity, and extreme radii fail closed.
Arrays are bytes-backed so a validated isometry or point cannot be made
writeable after construction.

The schema `aionq.poincare-universal-base.v2` serializes curvature, scope,
signatures, tolerance, chart, and numerical domain. The retired local v1 schema
does not silently migrate.

## Operators and review

The implementation provides:

- ball ↔ hyperboloid charts;
- distance, exponential and logarithm maps;
- Levi-Civita parallel transport;
- future-sheet Lorentz isometries;
- radial coordinates;
- dimensionless invariant review.

`PoincareBallBase.review()` checks boundary margin, tangent positivity, chart
round trips, shell constraint, distance agreement, and isometry invariance.
`PolycosmicKernel.review_universal_base()` additionally checks:

- every worldlet has one immutable base point;
- logarithmic tangent vectors span the declared \(n\) dimensions;
- hyperboloid lifts span the \((n+1)\)-dimensional ambient carrier;
- all cages preserve the same `base_id`;
- local fiber geometries remain heterogeneous;
- the Euclidean base control is present.

Affine rank in ball coordinates is reported only as a chart diagnostic; it is
not an invariant gate.

## Euclidean ablation

`EuclideanBaseControl` uses the same dimension and scale \(2R\), hence at the
origin

\[
g^{E}=4R^2I=g^{H}_0.
\]

It is a curvature ablation, not a local Euclidean worldlet standing in for one.
Hyperbolic and Euclidean distances remain separate observations; neither may
compensate another channel.

## Required type separation

| Object | Signature / role |
|---|---|
| \(H^n\) tangent metric | Riemannian \((n,0)\), universal distance geometry |
| ambient \(J\) | Lorentz \((n,1)\), hyperboloid realization |
| repository \(Q_{2,2}\) | split form \((2,2)\), independent fiber |
| \(O^\top O\succeq0\) | possibly singular observation instrument |
| a \(Q_{2,2}\)-null vector | isotropic; generally not in \(\ker(O^\top O)\) |

Tests explicitly reject an \(SO(2,2)\) map that is not Lorentz for
\(\mathbb R^{1,3}\), and distinguish split-isotropic vectors from PSD kernels.

## Verification

```powershell
python -m pytest tests/test_hb0_hyperbolic.py tests/test_hb0.py -q
python -m pytest tests/test_architecture.py -q
```
