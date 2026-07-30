# HB-0 n-ary hypercomplex decision field

## Primary object

The global object is a complete simplex of \(3\le n\le8\) alternatives over the
declared universal hyperbolic base. Each vertex carries:

\[
\sigma_i=(b_i,h_i,q_i,H_i,E_i),
\]

where:

- \(b_i\in H^p\) is its point in the shared atlas;
- \(h_i\in\mathbb H\) is a quaternion fiber value;
- \(q_i\in[0,1]^{16}\) is the named quality field;
- \(H_i\) is the vector Hamiltonian envelope;
- \(E_i\) is a typed, citable evidence descriptor.

Quaternion fibers use an explicit `trivial_product` connection in this slice.
That declaration is load-bearing: direct quaternion subtraction is valid in the
shared trivialization, while base motion is measured independently in \(H^p\).

Quaternion coordinates are not ordered. Quality benefits, Hamiltonian costs,
and credits use their own componentwise partial orders. No weighted sum exists.
An `EvidenceBinding` validates claim identity, tag, digest syntax and declared
mode, but it does not resolve the artifact. It therefore cannot authorize a
global decision.

## N-ary degeneration

For a face \(I\) of arity \(k\), let \(S_I\in\mathbb R^{k\times4}\) contain its
quaternion coordinates and let \(H_k\) be an orthonormal Helmert basis for the
zero-sum alternative contrasts:

\[
H_k^\top H_k=I,\qquad H_k^\top\mathbf1=0.
\]

The intrinsic contrast matrix is

\[
D_I=S_I^\top H_k.
\]

For every named observation channel \(O_c\), the field preserves the rank loss
as a vector indexed by channels:

\[
\delta_I^c
=
\operatorname{rank}(D_I)
-
\operatorname{rank}(O_cD_I).
\]

No channel compensates another. The action-space wall projector is

\[
\Pi_I^c=H_kV_I P_{\ker(O_cD_IV_I)}V_I^\top H_k^\top,
\]

where \(V_I\) spans the numerically active intrinsic contrast space at one
shared singular cutoff. This construction is PSD and idempotent by
construction; its rank and witness count must both equal \(\delta_I^c\).
Observation operators are contractions, so gain cannot manufacture rank.
For \(k>5\), the contrast carrier has dimension \(k-1>4\), so one quaternion
fiber necessarily has intrinsic nullity. The report emits
`[R]_intrinsic_cell_collapse`; a full observation channel cannot erase this
carrier limitation.

This detects genuinely higher cells. For

\[
h_a=0,\qquad h_b=1,\qquad h_c=2+j,
\qquad O=\operatorname{diag}(1,0,0,0),
\]

every edge changes its real coordinate and is observable, but the ternary
contrast \((1,-2,1)\) produces \(j\in\ker O\). Thus the full 2-cell loses rank
\(2\to1\) while none of its edges is a wall.

`WallObservation` is retained only through `restrict_binary_face()`, which
returns `global_decision_permitted = false`.

## Load-bearing hypercomplex channel

Relations use actual Cayley-Dickson quaternion multiplication:

\[
K_{ij}=h_i\overline{h_j}.
\]

For each oriented triple, the field also records

\[
\Omega_{ijk}
=
(h_i-h_k)\overline{(h_j-h_k)}
-
(h_j-h_k)\overline{(h_i-h_k)}.
\]

Under common unit-quaternion transport \(h\mapsto uh\), both channels transform
by conjugation \(z\mapsto uz\bar u\). Quaternion associativity makes the chart
composition valid. Octonions remain a bracketed diagnostic; they are not used
as flat sheaf transitions, and sedenions are not treated as invertible
transport.

## Hyperbolic higher cells

Pairwise hyperbolic distances are preserved as edge shadows. For every face of
arity \(3\le k\le p+1\), all \(k\times k\) minors of the hyperboloid-lift matrix
are retained as Plücker coordinates of its exterior \(k\)-vector. At top arity
\(p+1\), this becomes the oriented determinant. Thus a ternary face over H⁴
still has a genuine base-cell object instead of being reduced to its three
edges. Mirror triangles can have identical edge lengths and different exterior
coordinates.

## Complete `Fin(n)` sector decomposition

The declared `sector_order` is a full cyclic labeling of the alternatives.
The unitary discrete Fourier transform preserves every sector
\(k\in\operatorname{Fin}(n)\):

\[
\widehat h_k=\frac1{\sqrt n}\sum_{j=0}^{n-1}
e^{-2\pi i kj/n}h_j.
\]

The report carries all intrinsic and observed sector coefficients plus inverse
reconstruction and Parseval defects. No mean, single sector, binary edge, or
argmax is substituted for this family. This is the executable anti-flattening
invariant adapted from the sectoral decomposition in the external UTAI study;
it does not claim that this finite DFT is its connection-Laplacian theorem.

## Frontier and Hamiltonian governance

As a diagnostic projection, one alternative Pareto-dominates another only if it is:

- no worse in all sixteen quality benefits;
- no more costly in compute, coherence, identity, and absorption;
- no worse in exploration and integration credits;
- strictly better in at least one declared component.

Pareto dominance produces only `pareto_projection`; it is not a global verdict.
The result is one of:

- `INFEASIBLE`;
- `PARETO_SINGLETON_CANDIDATE`;
- `OPEN_MULTISECTION`.

`global_decision_permitted` is always false in this slice. Even a singleton
Pareto projection remains only a candidate because no explicit n-ary decision
policy or runtime evidence resolver has been registered. Observation loss,
intrinsic quaternion-carrier collapse, unresolved bindings and missing policy
remain separate blockers. Irreducibility is indexed by `(cell, channel)`, so a
binary wall in one channel cannot erase a ternary obstruction in another.

## Sheaf gluing

`QuaternionFieldChart` combines:

- an optional future-sheet Lorentz isometry on the base;
- associative left multiplication by a unit quaternion on the fiber;
- contragredient transport of every observation operator.

`glue_decision_fields` compares complete fields on every overlap and keeps
separate defect channels for base, fiber, quality values, quality obligations
and kill conditions, Hamiltonian, typed evidence, connection/coframe,
operators, `Fin(n)` sectors, and cell structure. Continuous channels have
separate typed tolerances; policy/evidence/connection/sector-order/cell
structure must agree exactly. For three or more charts, transition matrices
also satisfy an explicit Čech-style triple cocycle gate. Fields may be
reindexed by alternative/channel name. `glued` is the conjunction of these
separate gates; there is no universal defect score.

## N-ary adiabatic transport

`trace_hypercomplex_field_path()` certifies a finite path only when separate
budgets pass for:

- base speed and quaternion-orientation rate;
- quality and Hamiltonian speeds;
- fiber, operator, and projector loads divided by squared positive gaps;
- intrinsic rank, observed rank, and wall-rank stability;
- frontier/status, evidence, obligations, and kill-condition stability.

The report contains no binary decision label. Slow and fast parameterizations
of the same geometric change are tested separately.

## Evidence boundary

This slice proves executable representation and invariance properties. It does
not establish better cognition, AGI, consciousness, quantum advantage,
hyperbolic task advantage, or superiority over dimension-matched real controls.

## Verification

```powershell
python -m pytest tests/test_hb0_decision_field.py `
  tests/test_hb0_hyperbolic.py `
  tests/test_hb0_wall.py -q
```
