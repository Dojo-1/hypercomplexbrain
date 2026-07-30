# HB-0 hyperbolic quantum base · QB1

## Object

QB1 adds a physical density shadow over the declared universal Poincaré base
without identifying their geometries. For

\[
x=r\,u\in B^4,\qquad
z(u)=(u_0+i u_1,\;u_2+i u_3)\in S^3\subset\mathbb C^2,
\]

the fixed-width encoding is

\[
\rho_x=(1-r)|f\rangle\langle f|
\oplus r|z\rangle\langle z|\in\mathcal D(\mathbb C^3).
\]

Its image is the open cone over \(\mathbb{CP}^1\). QB1 is an encoding/quotient
map, not yet a quantum bundle connection or Levi-Civita spin transport.

At \(r=0\), the directional block has zero weight and the state is the unique
flag state. No direction is selected at the origin.

## What survives

The ball radius is an observable:

\[
r=\operatorname{Tr}(P_{\rm qubit}\rho_x),\qquad
d_H(0,x)=2R\,\operatorname{artanh}r.
\]

Trace distance from the encoded origin is exactly \(r\). Thus the infinite
hyperbolic radial ray remains recoverable at every finite point but is
compactified into a bounded quantum distance.

## Exact remainder: the Hopf phase

For every phase \(\theta\),

\[
z\mapsto e^{i\theta}z
\quad\Longrightarrow\quad
|z\rangle\langle z|
\mapsto
|z\rangle\langle z|.
\]

The corresponding points of \(H^4\) are generally distinct. The encoding
therefore factors through

\[
S^3\longrightarrow\mathbb{CP}^1\simeq S^2
\]

and has one generic differential kernel. The implementation computes the
Jacobian analytically, reports its numerical rank cutoff, and retains a centered
finite-difference Jacobian only as an independent control. It records the lost
direction as `[R]_hopf_phase`; it does not call the map injective.

## Transportable subgroup

`HopfUnitaryChart` implements an origin-preserving \(U(2)\) subgroup:

\[
z\mapsto Uz,\qquad
\rho\mapsto
\operatorname{diag}(1,U)\rho\operatorname{diag}(1,U)^\dagger.
\]

Its realification is orthogonal on \(\mathbb R^4\), so it preserves both
Poincaré distance and the origin-tangent-matched Euclidean control distance.
The density encoding intertwines the two actions exactly.

This does not provide a finite-dimensional unitary representation of the full
noncompact isometry group of \(H^4\). General Lorentz translations remain
outside QB1.

## Metric separation

Every pair report retains five independent observations:

- Poincaré distance;
- tangent-matched Euclidean-control distance;
- quantum trace distance;
- root fidelity;
- Bures distance.

They are never summed, averaged, or ranked as one scalar. A fixed qutrit
dephasing control checks the trace-distance and fidelity data-processing
directions.

## Evidence boundary

QB1 establishes deterministic properties of one declared encoding. It does not
establish quantum capacity, hardware feasibility, noise robustness, quantum
advantage, better memory, cognition, consciousness, or AGI.

Construction and inverse recovery are bound to the exact canonical
`UNIVERSAL_POINCARE_BASE` and its tangent-matched Euclidean control. Raw qutrit
input is accepted by the inverse only after checking the open radial interval,
zero flag–spin coherence, and a spin block of rank at most one.

The preregistration JSON records the intended design, but its temporal
“frozen-before-implementation” status is not independently witnessed. QB1 has
no terminal evidence envelope or governed promotion; the tests below are
implementation verification, not an independent experimental result.

## Verification

```powershell
python -m pytest tests/test_hb0_quantum_base.py -q
python -m pytest tests/test_hb0_hyperbolic.py `
  tests/test_hb0_quantum_base.py `
  tests/test_quantum_channel_geometry.py -q
```
