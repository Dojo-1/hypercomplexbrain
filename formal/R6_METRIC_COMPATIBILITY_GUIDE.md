# R6: a stretched coordinate need not be a stretched world

**Status:** scoped formal proof targets. Consult the latest pinned Lean build
before citing them as kernel-checked. These are 2D real linear maps and
symmetric forms, not quantum resource or heterogeneous Worldlet theorems.

Suppose a map \(T:X\to Y\) carries forms \(g_X,g_Y\). Its *actual*
form-valued metric defect is

\[
D_T=T^\mathsf{T}g_YT-g_X.
\]

A new coordinate description uses \(F:X'\to X\) and \(G:Y'\to Y\).
If the resulting map \(T':X'\to Y'\) makes the square commute
(\(GT'=TF\)), we must carry both metrics into the new charts:

\[
g'_X=F^\mathsf{T}g_X F,\qquad
g'_Y=G^\mathsf{T}g_Y G.
\]

The full symmetric form—not only its value on one input—then obeys

\[
D_{T'}(g'_X,g'_Y)=F^\mathsf{T}D_T(g_X,g_Y)F.
\]

That is algebraic covariance. **To call the new description an equivalent
coordinate chart, the coordinate map must also be invertible.**

For a human example take the *same physical identity transformation*,
but describe its source through \(F=\operatorname{diag}(2,\tfrac12)\).
The new linear expression becomes \(T'=F\), with

\[
g'_X=\operatorname{diag}(4,\tfrac14),\qquad g'_Y=I.
\]

Then \(D_{T'}=0\). If we incorrectly impose Euclidean \(I\) on the new
source as well, we instead obtain \(D_{T'}=\operatorname{diag}(3,-3/4)\).
It is a true defect **for that different contract**, not evidence of
distortion under the properly transported original metric.

The earlier result saying a nonzero Cartan boost is not an isometry
remains true when **the Euclidean metric is fixed**. It is not a
prohibition on using non-orthogonal coordinates with a correspondingly
transformed metric.

**Negative control:** a singular projection can pull a nonzero form
back to zero, losing an entire direction. Accordingly a valid inverse
is needed to infer zero original defect from zero transformed defect.
The new formalization certifies an explicit inverse for the example.

This does **not** confer physical units, positivity, a global atlas,
connection, quantum implementation, energy cost, cognitive improvement,
or semantic equivalence between Worldlets.

**Falsifiers:** a properly commuting square whose transported defect
fails covariance; a purported invertible chart that collapses a
direction; or a mismatched-metric example being promoted to a
statement about physical distortion of the original geometry.
