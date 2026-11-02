# Different worlds, declared bridges

*An accessible guide to the typed heterogeneous Worldlet formalization.*

**Research conception and direction:** Jesús Vilela Jato (Dojo-1);
AI-assisted formalization and review. Repository-controlled original material:
[CC BY 4.0](../LICENSE), subject to the repository's
[attribution and third-party rights notice](../ATTRIBUTION.md).

## What changes from R6?

The previous R6 theorems often began with two-dimensional real coordinates.
That is an excellent microscope, but not a whole ecology of local worlds.

A local mathematical **Worldlet** now has its *own* coordinate carrier
\(V_\iota=\iota\to\mathbb R\) and a certified **symmetric bilinear form**
\(g_\iota:V_\iota\times V_\iota\to\mathbb R\). A transport, or **tendril**,
\(T:V_\iota\to V_\kappa\), is a genuine *linear* map.
The types \(\iota\) and \(\kappa\) need not agree.

A 2-dimensional Worldlet can communicate with a 3-dimensional Worldlet,
which can in turn communicate with a 4-dimensional Worldlet. Each retains
its own local geometric observation.

The transport defect belongs to the **source Worldlet**:

\[
D_T(u,v)=g_\kappa(Tu,Tv)-g_\iota(u,v).
\]

It is a complete bilinear-form observation in the declared carriers,
not a single norm difference measured on one chosen vector.

## What survives composition?

For \(T:V_\iota\to V_\kappa\) and
\(S:V_\kappa\to V_\lambda\), under one shared intermediate metric
\(g_\kappa\),

\[
D_{S\circ T}=D_T+T^*D_S.
\]

That is a form-valued identity. If the first leg thinks the intermediate
metric is \(g_\kappa^\mathrm{out}\), while the second uses a different
\(g_\kappa^\mathrm{in}\), the missing term is not ignored:

\[
D_{S\circ T}
=D_T^\mathrm{out}+T^*D_S^\mathrm{in}
+T^*(g_\kappa^\mathrm{in}-g_\kappa^\mathrm{out}).
\]

No equality of metrics, units, or semantics is smuggled into the overlap.

## Are these genuinely different geometries?

The Lean definitions use **actual bilinear forms**, with an explicit
symmetry proof. The 2→3→4 composition is checked at the type level;
it cannot be accidentally rewritten as composition of a single
2-dimensional operator.

But these forms are not necessarily positive definite or nondegenerate.
A transport that discards a direction may pull back a metric into a
degenerate one. A pullback Worldlet is therefore **not** automatically
equivalent to its target.

A *surjective* source chart is enough to reflect equality of bilinear
forms from their pullbacks. Without that faithfulness condition, a
zero remainder after projection need not mean the original remainder
was zero. This is a mathematical constraint, not an optimization flag.

## What is absent?

There is no model here of physical units, changing clocks, a
fiberwise connection, semantic translation quality, sheaf or gerbe
gluing, nonassociative algebra, quantum hardware, or intelligence.
Those are separate, typed extensions rather than consequences of
the word “Worldlet.”

This module generalizes the **carrier and form contract**, not the
observed capabilities of AION.

**Falsifiers:** a 2→3→4 composition whose entire form remainder fails
the stated identity; an intermediate metric mismatch without its
correction; or a singular chart being promoted to a reversible
equivalence.

## Follow the proof

- [Typed Lean definitions and theorem statements](HeterogeneousWorldlet.lean)
- [Explicit axioms and all native proof roots](ProofAudit.lean)
- [Earlier metric-compatibility guide](R6_METRIC_COMPATIBILITY_GUIDE.md)
- [Python adversarial controls](../tests/test_heterogeneous_worldlet_metrics.py)

All proof claims are conditional on the pinned Lean CI for the exact
commit. Numerical tests are bounded sanity checks, not independent
scientific validation.
