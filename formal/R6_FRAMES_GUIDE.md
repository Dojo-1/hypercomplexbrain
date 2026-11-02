# R6 under orthogonal moving frames: what remains true?

**Status:** Scoped theorem targets. Check the current [Lean proof
gate](../.github/workflows/lean.yml) for the exact revision before treating
the statements as kernel-checked.

The earlier [R6 dilation](R6_DILATION_GUIDE.md) works in a fixed
two-dimensional real Cartan basis. But AION's Worldlets need not be displayed
in the same local coordinates. What survives when we change a frame?

## The short answer

An *orthogonal* change of frame is free in the mathematics because it is
an invertible **linear** map preserving squared Euclidean norm. A
non-orthogonal boost is not free. Treating the two as interchangeable
would erase precisely the R6 cost we wanted to measure.

Let F and G be arbitrary orthogonal linear frame maps. Define the
represented filter

\[
K_{\rho}^{F,G}=G\, K_\rho\,F^{-1},
\qquad K_\rho=\operatorname{diag}(1,e^{-2\rho}),\quad \rho\ge0.
\]

For a normalized input v, the sharp interval survives:

\[
e^{-4\rho}\le \|K_{\rho}^{F,G}v\|^2\le1.
\]

Both endpoints still occur, but the corresponding inputs are **F(0,1)**
and **F(1,0)**, not necessarily the bare coordinate axes.

For a *joint* ambient orthogonal frame change H,

\[
K_{\rho}^{FH,GH}(Hv)=H(K_{\rho}^{F,G}v).
\]

Here \`FH\` means **apply F, then H** (function-composition order H∘F).
Consequently,

\[
\|K_{\rho}^{FH,GH}(Hv)\|^2=\|K_{\rho}^{F,G}v\|^2.
\]

The input vector must transform **together with** its frame. Keep the input
fixed while rotating the contracting axis and the acceptance weight can
change. That is physical alignment, not a gauge inconsistency.

## Why the types matter

The Lean \`OrthogonalFrame\` contains an actual
\`LinearEquiv ℝ (ℝ × ℝ) (ℝ × ℝ)\` plus a norm-preservation proof. It is not
an arbitrary reversible function, and not a license to classify the
noncompact Cartan boost as an isometry.

The negative-control theorem says a nonzero \`boost ρ\` cannot have the
same action as any certified \`OrthogonalFrame\`. This prevents a
representation change from making noncompact depth disappear by fiat.

## Matched implementation control

The numerical tests construct independent input/output real planar rotations
and check the existing Python \`block_encode\` routine against the
frame-transported normalized R6 filter. They also test the transformation
of all three objects (state, input frame, output frame) under a common
ambient rotation and a counterexample when only the frame changes.

## Explicit boundaries

The new assertions do **not** include \`SO(2,2)\` general transport,
non-orthogonal sheaf gluing, time-dependent Berry connections,
adiabatic dynamics, quantum hardware, or any universal lower bound for
all possible block encodings. Those still have separate typed
remainders.

**Kill condition:** if a common orthogonal change of coordinates alters
the correctly transformed acceptance weight, or the input-frame extremal
axes lose the sharp \`e^{-4ρ}\`/1 values, reject the covariance claim.
Do not repair by clipping measured probabilities.
