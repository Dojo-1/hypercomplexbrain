# R6 signed transport remainders — why a closed loop can mislead

**Evidence floor:** bounded Lean theorem targets; consult the exact-commit
[Lean gate](../.github/workflows/lean.yml) before claiming kernel verification.
The carrier is the real 2D Euclidean quadratic form, not an arbitrary Worldlet.

## One observation, two directions of change

For a particular input v and transport T, record

\[
\Delta_T(v)=\|T(v)\|^2-\|v\|^2.
\]

Retain both \(\Delta_T^+=\max(\Delta_T,0)\) and
\(\Delta_T^-=\max(-\Delta_T,0)\). A \`SignedNormRemainder\`
stores the before/after squared norms, these nonnegative parts,
and a proof of the signed balance \(\Delta_T=\Delta_T^+-\Delta_T^-\).

This is an intentionally **partial** diagnostic. It cannot measure every
change in geometry, information, memory, or the meaning of a world.

## The intermediate-state rule

For composable maps S and T, **without** assuming linearity,

\[
\Delta_{S\circ T}(v)=\Delta_T(v)+\Delta_S(Tv).
\]

The second defect must be evaluated at the *actual intermediate state*.
The positive and negative parts do not generally add separately.

If \(B_\rho=\mathrm{diag}(e^\rho,e^{-\rho})\) and \(\rho>0\),

\[
\Delta_{B_\rho}(1,0)=e^{2\rho}-1>0,\qquad
\Delta_{B_\rho}(0,1)=e^{-2\rho}-1<0.
\]

Yet \(B_{-\rho}B_\rho=I\). Its round-trip defect is zero
even though the outward step is non-isometric. This exact
counterexample warns against promoting *closure* to *cost-free traversal*.

## What survives a frame change

For certified **orthogonal linear** frames F and G, let
\(T^{F,G}=G T F^{-1}\). Then the input must be transported too:

\[
\Delta_{T^{F,G}}(Fv)=\Delta_T(v).
\]

Both nonnegative parts are preserved. But non-orthogonal changes do
not inherit this guarantee. Their mismatch must be recorded rather
than dismissed as a harmless coordinate change.

## Exclusions and falsification

The squared-norm remainder is not a measure of physical work,
quantum channel capacity, entropy production, information loss,
semantic incompleteness, or cohomological obstruction. It does
not guarantee an advantage for quantum hardware or cognition.

**Kill the model** if the intermediate-state identity fails,
either signed component becomes negative, orthogonal covariance
fails for the properly transported input, or the closed boost loop
is incorrectly classified as locally cost-free.

The next bounded question is how to transport this diagnostic
across *different* local metrics without conflating norm choices.
