# HB-0 binary decision wall — edge instrument

## Scope

`WallObservation` is an oriented **1-face instrument**. It compares two local
sections \(C,S\) on one declared real carrier. It is not the global HB-0
decision object; the n-ary object is
[`HypercomplexDecisionField`](HB0_HYPERCOMPLEX_DECISION_FIELD.md).

The positive-semidefinite instrument \(g\) defines a kernel wall

\[
\mathfrak D_g=\{(C,S): C-S\ne0,\ C-S\in\ker g\}.
\]

The implementation detects membership through the kernel projector:

\[
\|(I-P_{\ker g})(C-S)\|
\le \epsilon\max(1,\|C-S\|).
\]

This avoids comparing \(\|g(C-S)\|\) with an eigenvalue cutoff, which mixes
scales and can misclassify small positive eigenvalues.

Resolved edge reports carry no remainder. Exact ties, instrument-kernel walls,
and declared-order incomparability emit `[R]_wall`.

## Transported decision order

An orthogonal coframe \(A\) declares the local componentwise decision cone:

\[
K_A=\{v:A v\ge0\}.
\]

For a chart \(Q\),

\[
\delta'=Q\delta,\qquad
g'=QgQ^\top,\qquad
A'=AQ^\top.
\]

Therefore \(A'\delta'=A\delta\), so edge labels and Pareto incomparability do
not change under rotations or reflections. In particular, \(Q=-I\) cannot turn
the same transported section from `CONTINUE` into `STOP`.

## Sheaf-style gluing

Every section is transported before comparison. The atlas checks every pair,
not a reference star:

\[
\max_{i<j}
\left\{
\|\delta_i-\delta_j\|_2,\,
\|g_i-g_j\|_F,\,
\|A_i-A_j\|_F
\right\}
\le\epsilon.
\]

Decision labels must also agree. Failed field or decision coherence forces
`HOLD` and emits `[R]_wall_gluing`; successful gluing emits no unresolved
coherence remainder.

## Finite adiabatic certificate

`trace_wall_breath` consumes `WallPathSample(parameter, observation)` and an
explicit `FiniteAdiabaticCriterion`. For each adjacent sample it measures
divided-difference rates of:

- the decision difference;
- the PSD instrument;
- its kernel projector;
- the transported decision coframe.

With declared section scale \(D\), metric scale \(M\), positive-band gap
\(\gamma_i\), and path parameter \(s\),

\[
\rho_i=\frac1{\Delta s_i}\max\left(
\frac{\|\Delta\delta_i\|}{D},
\frac{\|\Delta g_i\|_2}{M},
\|\Delta P_{\ker,i}\|_2,
\|\Delta A_i\|_2
\right),
\]

\[
\Gamma_i=\frac{\min(\gamma_i,\gamma_{i+1})}{M},
\qquad
\mathcal A_i=\frac{\rho_i}{\Gamma_i^2}.
\]

Certification requires a declared gap floor, a declared load ceiling, constant
positive kernel nullity, and a genuine metric-kernel witness inside every
resolved edge reversal. A Pareto `HOLD` or ordinary tie does not count as a
metric-wall visit. This is a finite governance certificate, not a physical
adiabatic theorem.

## Explicit exclusions

- no global n-ary decision from `CONTINUE`/`STOP` edge labels;
- no identification of PSD kernel degeneration with a split-signature null
  cone;
- no P/NP, cognition, consciousness, AGI, cohomology, quantum, or hardware
  advantage claim.

## Verification

```powershell
python -m pytest tests/test_hb0_wall.py -q
python -m pytest tests/test_hb0_wall.py tests/test_hb0_decision_field.py -q
```
