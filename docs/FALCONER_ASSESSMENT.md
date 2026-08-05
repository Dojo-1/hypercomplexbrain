# Is a generalized Falconer theory over information manifolds plausible?

**This document is an assessment, not a result.** Nothing in it is measured,
nothing in it is a claim of this repository, and no number here enters any
ledger. It is written down because the question was asked and because a
plausibility judgement that stays in conversation cannot later be checked
against what actually happened. Every confidence level below is stated
explicitly, and where I am reasoning from memory of the literature rather than
from something I have re-derived, I say so.

## The question

Falconer's distance conjecture: if `E ⊂ R^d` is compact with Hausdorff dimension
`dim E > d/2`, then the distance set `Δ(E) = { |x − y| : x, y ∈ E }` has positive
Lebesgue measure. The generalization asked about replaces `R^d` with an
information manifold and `|x − y|` with an information divergence.

## Short answer

**Locally, plausible and largely already covered by existing machinery.
Globally, and in the cases this programme would actually care about, I expect it
to fail — and to fail at exactly the place where this repository has already
measured a failure for unrelated reasons.**

Three claims below, at three different confidence levels.

---

## 1. The non-degeneracy hypothesis translates, and translates *cleanly*

Confidence: **high** for the computation, **medium** for the claim that it is the
right hypothesis.

Falconer-type results generalize well beyond Euclidean distance. The standard
route replaces `|x − y|` with a function `Φ(x, y)` satisfying a **Phong–Stein
rotational curvature** condition — non-degeneracy of the mixed Hessian
`∂²Φ/∂x∂y`, together with a determinant condition on the bordered matrix. Under
that hypothesis, distance-set results for `Φ` follow by the same Mattila-integral
and decay-of-spherical-means arguments used in the Euclidean case. (Erdoğan;
Iosevich and collaborators; Greenleaf–Iosevich–Liu–Palsson for the
`Φ`-configuration versions. I am recalling the shape of this literature, not
citing checked statements.)

Now put a Bregman divergence in for `Φ`:

```
D_φ(x ‖ y) = φ(x) − φ(y) − ⟨∇φ(y), x − y⟩
```

Its mixed Hessian is

```
∂²D/∂x∂y = −∇²φ(y)
```

which is a one-line computation and is worth stating plainly:

> **The Phong–Stein non-degeneracy hypothesis for a Bregman divergence is
> exactly strict convexity of its potential — that is, exactly
> positive-definiteness of the Fisher information metric.**

That is a genuinely clean correspondence. The hypothesis a Falconer-type
theorem needs is not an extra technical assumption bolted onto information
geometry; it *is* the condition that makes the manifold an information manifold
in the first place. For Fisher–Rao geodesic distance the same holds locally by
comparison: on a compact patch where the Fisher metric is uniformly definite,
the geodesic distance is a smooth non-degenerate `Φ`.

So: on a compact patch of a finite-dimensional statistical manifold with
uniformly positive-definite Fisher metric, a Falconer statement of the form
*`dim E > d/2` ⟹ the divergence set has positive measure* is plausible, and I
would expect it to be provable with existing machinery rather than new ideas.
The threshold `d/2` should be the model dimension.

**Caveat I will not paper over.** A Bregman divergence is not symmetric and not
a metric, so "the distance set" is already a different object — `D(x‖y)` and
`D(y‖x)` generate different sets, and the pinned versions differ from the
unpinned ones. Whether the standard machinery survives that asymmetry is not
something I can assert; the mixed-Hessian computation is symmetric-agnostic, but
the geometric arguments downstream may not be.

## 2. It breaks where the interesting sets live

Confidence: **high** that the degeneracy is real, **medium** that it is fatal.

The hypothesis above requires the Fisher metric to be uniformly definite. On the
manifolds anyone actually cares about, it is not — and specifically, it fails on
the boundary:

- On the probability simplex, the Fisher metric blows up as a coordinate → 0.
  The interesting sets — sparse distributions, deterministic limits, anything
  near a vertex — live precisely there.
- In the quantum case the Bures / quantum-Fisher metric is **degenerate on
  rank-deficient states**, i.e. on the entire boundary of state space, which is
  where pure states, low-rank effects and every extremal object sit.

This is not a technicality I am inventing to be cautious. **This repository has
already measured it biting, from a completely different direction.** The R6l
square-root portability defect (`manifests/qsigma_r6l_square_root_portability_finding.json`)
is exactly this: every R6l effect is rank-deficient, so every one carries
eigenvalues whose true value is 0 and whose computed value is anything in
`[−ε, +ε]`; the square root of such an eigenvalue is known only to `√ε ≈ 1e-8`,
and two conforming LAPACK builds are entitled to disagree by that much. That
`√ε` is the *same* degeneracy — the metric losing definiteness at the boundary —
showing up as a numerical instability instead of as a failed hypothesis.

A theory whose hypothesis holds only in the interior, on a space whose interesting
subsets accumulate on the boundary, is a theory that is true and not useful. I
would want to see a boundary-adapted formulation before believing otherwise.

## 3. There is nothing here for it to act on yet

Confidence: **high**. This is about this repository, not about the mathematics.

A Falconer statement is a statement about **fractal sets** — its whole content is
a dimension threshold. This programme currently produces no fractal sets of
anything. Every family in it is a finite parameterised sweep: finite circuit
corpora, finite frame groups, finite depth ladders. The `R1C` measurement
(`manifests/qsigma_r1c_transport_fiber_finding.json`) makes this concrete from
the other side — the frame group is finite, so its orbits are finite point sets,
and no dimension can grow under a finite union. That is *why* the hardness
landscape over `AGL(1,16)` came out a step.

So the honest status is: **plausible mathematics, currently unattached.** Not
false, not vacuous — unattached. Two things would attach it, and only two that I
can see:

1. **A continuum of directions.** The continuous frame group is where the
   geometry is. `R1C` measured its local structure: the matchgate class is a
   7-dimensional subgroup of the 16-dimensional `U(4)`, codimension 9, with escape
   order exactly 1 in all 216 directions tested and no direction of order ≥ 2. So
   the constraint map is a submersion — the transversality a Kakeya/Furstenberg
   argument would need is *present and verified*. What is missing is a family of
   fibers rich enough for an incidence question to be non-trivial. A single
   subgroup and its cosets is not a Kakeya configuration; a Kakeya configuration
   needs fibers pointing in a continuum of directions arranged so their union is
   small.
2. **A measure on circuit space with a dimension.** Falconer needs `dim E`. This
   repository has no measure on circuit families for which a Hausdorff dimension
   is defined, let alone computed.

## What I would actually do, if this line were pursued

Not "prove a Falconer theorem". The honest first step is much smaller and is
already half-built:

- The certified classes are **real algebraic varieties**, cut out by polynomials
  in the gate entries — 16 linear and 2 quadratic for the matchgate class, and
  `n·C(n,2)` quadratics for the monomial class. That is the correct raw material
  for polynomial partitioning, which is the technique the question gestures at.
- The right first question is **not** a dimension estimate but an **incidence**
  one, which is finitary and therefore answerable here: given `N` gates sampled
  from a family and the `7`-dimensional fibers through them, how many
  fiber-variety incidences can occur? That is a Guth–Katz-shaped question, it
  needs no fractal sets, and a partitioning polynomial for it can be constructed
  explicitly because the variety's defining polynomials are already written down.
- Only if that produces a non-trivial bound does a continuum/dimension version
  become worth formulating.

## Summary

| claim | verdict | confidence |
|---|---|---|
| Phong–Stein non-degeneracy ↔ positive-definite Fisher metric | clean, one-line correspondence | high on the computation |
| Local Falconer on a compact definite patch | plausible, likely existing machinery | medium |
| Survives the boundary degeneracy | **doubtful** — and the repository has already measured that degeneracy biting | medium-high that it is a real obstruction |
| Attaches to anything measured in this programme today | **no** — no fractal sets, no measure with a dimension | high |
| Transversality hypothesis holds where measured | **yes**, verified: submersion, escape order 1, 0 directions of order ≥ 2 | high, but only at `n = 2` |

The one thing I would push back on in the framing: replacing straight tubes with
hyperbolic transport fibers is the right instinct, and `R1C` shows the fibers
exist and are exact rather than osculating. But the reason the finite-group
measurement gave a step is not that the tubes were straight. It is that there
were 240 of them. Curvature is not what a finite set is missing.
