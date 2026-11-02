# R6 — The geometry that a single number cannot remember

**Scope:** A pair of real two-dimensional coordinate carriers; declared
symmetric bilinear forms; explicit 2×2 real linear maps. This is a
strictly stronger *formal diagnostic* than a scalar, not proof that
every use of it is a physical Riemannian metric.

Let source and target have coefficient matrices

\[
g_X=\begin{pmatrix}a_X&b_X\\b_X&c_X\end{pmatrix},\qquad
g_Y=\begin{pmatrix}a_Y&b_Y\\b_Y&c_Y\end{pmatrix},
\]
and let \(T:X\to Y\) have a declared real 2×2 matrix. Define the
**metric-pullback defect** (in source coordinates)

\[
D_T=T^\mathsf{T}g_Y T-g_X.
\]

It is a symmetric form, not the state-dependent number
\(\Delta_T(v)=v^\mathsf{T}D_Tv\). The latter is one evaluation that can
vanish without the form vanishing.

## A counterexample anyone can reconstruct

For \(g_X=g_Y=I\) and \(T=\mathrm{diag}(2,\tfrac12)\):

\[
D_T=\begin{pmatrix}3&0\\0&-\tfrac34\end{pmatrix}.
\]

The vector \(v=(1,2)\) has the same squared norm before and after T:
\(5=5\), so \(\Delta_T(v)=0\). Nevertheless \(D_T\ne0\), and its
coordinate axes exhibit simultaneous expansion and contraction.

This refutes the proposed promotion from **zero scalar on one
input** to **isometric transport**.

## The compatibility contract is load-bearing

For \(T:X\to Y\) and \(S:Y\to Z\), using the same intermediate form
\(g_Y\) on both legs,

\[
D_{S\circ T}^{X,Z}
=D_T^{X,Y}+T^\mathsf{T}D_S^{Y,Z}T.
\]

This is a **form-valued** identity, not merely a calculation for one
state. If the target form of T (\(g_Y^{out}\)) differs from the source
form of S (\(g_Y^{in}\)), the exact missing term is

\[
T^\mathsf{T}(g_Y^{in}-g_Y^{out})T.
\]

We explicitly prove the corrected identity. Declaring the two
intermediate metrics equal without checking their units, coordinate
convention and carrier identification is an A-tagged *assumption*,
not a theorem.

## What stays open

The code models arbitrary symmetric forms. It does **not** require
positive definiteness, and therefore its input forms are not all
Riemannian metrics. Nor does it formalize tensor fields on manifolds,
arbitrary-dimensional bundles, moving connections, categorical
Worldlet transport, quantum capacity, entanglement, cognitive
performance, or a universal energetic expense.

The numerical controls use independent NumPy matrix multiplication,
positive-definite samples, the zero-scalar counterexample, and a
deliberate mismatched-intermediate-metric negative control.

**Kill conditions:** pullback evaluation, full form-valued
composition, or its mismatch correction fails; or the zero-scalar
counterexample is mistakenly described as an isometry. A green
Lean build supports only the stated polynomial identities.
