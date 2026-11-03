# When a Worldlet loses a direction

*Positive metrics, injective tendrils and the difference between representing a world and silently erasing part of it.*

**Research conception and direction:** Jesús Vilela Jato (Dojo-1).
Formalization includes AI assistance. Attribution and licensing:
[CC BY 4.0](../LICENSE), subject to the [provenance notice](../ATTRIBUTION.md).

## We have earned one more mathematical distinction

In the earlier heterogeneous Worldlet formalization, each local geometry
contained a *symmetric bilinear form*. Symmetry alone does **not** mean
that the form measures squared length: it may be indefinite or degenerate.

A new, explicitly named contract requires

\[
g(v,v)>0 \quad\text{for every nonzero }v.
\]

This is strict positive definiteness. It is not silently assigned to
every Worldlet, and is carried as a proof in the new positive Worldlet type.

## Which tendrils preserve a positive local metric?

Take a genuine linear map between possibly different local carriers:

\[
T:V_X\longrightarrow V_Y.
\]

For a *strictly positive* target bilinear form \(g_Y\), define

\[
(T^\ast g_Y)(u,v)=g_Y(Tu,Tv).
\]

The central result is exact:

\[
\boxed{T^\ast g_Y\text{ is strictly positive}
\iff T\text{ is injective}.}
\]

**Why:** if a nonzero vector is carried into a nonzero target vector,
the positive target metric gives it a positive reading. But if a nonzero
source vector lies in the kernel of T, its pullback reading must be
zero, which contradicts strict positivity.

Unlike a statement about an invertible square matrix, this theorem
works even when the source and target dimensions differ.

## Two counterexamples worth remembering

First, a zero tendril from one coordinate to two coordinates destroys
every source direction. No choice of target bilinear form can give its
pullback a strictly positive metric.

Second, an injective identity map cannot rescue a *zero target metric*:
its pullback is still zero. The target positivity hypothesis is
load-bearing, not a formality.

A positive **semidefinite** target, however, remains nonnegative after
any linear pullback, even through a projection that loses directions.
Nonnegativity is weaker than strict positivity.

## How this changes our software contract

The new positive Worldlet structure wraps the prior unrestricted
Worldlet and adds a proof of strict positivity. A typed positive
rechart can only be constructed from a positive target and an explicit
injectivity certificate for the tendril.

Even then, **it is not equivalence**. For example, an injective map
from two to three dimensions can preserve every quadratic measurement
on the source while leaving the third *target* direction inaccessible.

If a source metric is positive and the declared form-valued transport
defect is zero, the transport must be injective. With a positive target
as well, exact matching makes the source positive precisely when T
is injective.

## What has not been proved

These are theorems about real bilinear forms and linear maps. The
contracts do not include physical units, temporal synchronization,
smoothness, semantic faithfulness, quantum hardware, energy expenditure
or an artificial brain with demonstrated cognition.

**Falsifiers:** an injective tendril into a positive target whose
pullback is not strictly positive; a noninjective tendril whose
pullback is strictly positive; or a claim of positivity after
discarding the target positivity premise.

[Lean source](PositiveWorldletMetric.lean) ·
[Axiom inventory](ProofAudit.lean) ·
[Mixed-dimensional numerical checks](../tests/test_worldlet_metric_positivity.py).

A green exact-commit Lean gate supports the encoded theorem (**P**).
Finite matrix checks are bounded observations (**M**).
Larger Worldlet and cognition interpretations remain open (**H/S**).
