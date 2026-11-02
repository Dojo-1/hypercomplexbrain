# R6: one real orthogonal dilation, one precise postselection cost

**Status:** Formalization target. Check the [native Lean CI](../.github/workflows/lean.yml)
for the current commit before citing these statements as kernel-checked.

The earlier [R6 compactness obstruction](R6Compact.lean) says the *real* Cartan
boost is an isometry only at radial depth zero. This extension asks a smaller,
constructive question: can its operator-norm-normalized version be embedded as
one block of a finite **real orthogonal** transformation, and what is the
resulting measurement-conditioned probability?

## The mathematical object

For nonnegative radial depth ρ,

\[
B_\rho=\begin{pmatrix} e^\rho & 0\\0&e^{-\rho}\end{pmatrix},
\quad
K_\rho=e^{-\rho}B_\rho=
\begin{pmatrix}1&0\\0&k\end{pmatrix},
\quad k=e^{-2\rho}, \quad s=\sqrt{1-k^2}.
\]

For real system coordinates \((x,y)\) and two-dimensional real ancilla
coordinates \((a,b)\), define

\[
U_\rho(x,y,a,b)=(x,\;ky+sb,\;-a,\;sy-kb).
\]

One can check \(k^2+s^2=1\), so

\[
\|U_\rho(v,w)\|^2=\|v\|^2+\|w\|^2.
\]

With a zero ancilla, the first two output coordinates are \(K_\rho v\).
For \(\|v\|=1\), the probability weight of selecting that ancilla block is

\[
p_\rho(v)=\|K_\rho v\|^2
=x^2+e^{-4\rho}y^2,\quad
e^{-4\rho}\le p_\rho(v)\le1.
\]

The minimum is **attained** at \(v=(0,1)\), the maximum at \(v=(1,0)\).
The depth-zero control is \(K_0=I\). These statements are exact for the
**specified** normalization and ancilla measurement.

## Why this is interesting, and what it does not prove

- This provides a finite real orthogonal dilation. Such a real matrix also
  defines a complex unitary matrix, but the Lean source proves only the real
  squared-norm identity and the block equations.
- The bound is an *attainable probability range for this encoding*, not an
  information-theoretic lower bound for every possible quantum representation.
- A normalized filter is generally **not** a deterministic unitary gate on the
  system alone. Calling it a gate without its ancilla/postselection semantics
  would conceal the implementation cost.
- Neither hardware transpilation nor actual QPU observations are part of this
  formalization. No cognitive advantage follows.
- Composition, changing Cartan frames, and input averages are separate
  questions. In particular the worst-case probability for a sequence cannot
  be inferred from a per-step bound without specifying intermediate states,
  adaptations, measurements, and the normalization contract.

## Reader's route

1. Read [R6Compact](R6Compact.lean), then [R6Dilation](R6Dilation.lean).
2. Confirm the named theorems are included in [ProofAudit](ProofAudit.lean).
3. Read the compiled CI axiom report. No \`sorryAx\` may be present.
4. Compare the encoding convention against the [original numerical
   study](../docs/QUANTUM_SUBSTRATE_COST.md); investigate discrepancies rather
   than silently adjusting either one.

**Kill condition:** If the dilation does not preserve total squared norm for
every input, or the contracting-axis success weight differs from
\(e^{-4\rho}\), the corresponding formal claim must not be promoted. A
successful Lean build establishes the formal statements as written; it does
not independently establish the physical interpretation.
