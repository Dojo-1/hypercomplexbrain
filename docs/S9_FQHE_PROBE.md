# S9 Fractional Quantum Hall Probe

**Status:** preregistered at commit `91777d9`; the numerical instrument is
implemented and test-covered, while the primary many-body measurement has not
yet run at this checkpoint.

S9 is a controls-first numerical probe of one fixed finite-size interacting
Hofstadter system. It asks whether the two lowest many-body levels form an
isolated rank-two bundle over boundary-twist space and, only if they do, whether
the determinant line of that bundle has Chern number of magnitude one. The
derived label `C/2` is a bundle-normalized finite-size response. It is not a
direct Hall-transport measurement.

The complete immutable specification is
[`manifests/s9_fqhe_preregistration.json`](../manifests/s9_fqhe_preregistration.json).
That manifest, rather than this explanatory note, is authoritative for parameter
values, thresholds, seeds, execution order, and kill conditions.

## 1. Fixed operational model

The target is three hard-core bosons on a periodic `6 x 4` square lattice:

```text
sites                 24
flux per plaquette    alpha = 1/4
total flux quanta     N_phi = 6
particle number       N_b = 3
filling               nu = N_b / N_phi = 1/2
Hilbert dimension     choose(24, 3) = 2024
```

The hard-core constraint is exact: basis states are three-site occupation
bitstrings, so double occupation is absent by construction. With `t = 1`, the
Hamiltonian at twists `(theta_x, theta_y)` is

```text
H = -t sum_(x,y) [
      exp(-i 2 pi alpha y + i theta_x 1[x=Lx-1])
        b†_(x+1 mod Lx,y) b_(x,y)
    + exp(+i theta_y 1[y=Ly-1])
        b†_(x,y+1 mod Ly) b_(x,y)
    + h.c.
]
```

This Landau-gauge convention has positive-oriented plaquette phase
`+2 pi alpha`. Boundary twists occur only on bonds that cross the corresponding
periodic boundary. The same convention is used by the integer-Hall control, so
the control fixes the sign orientation for the target.

At each point on the preregistered `7 x 7` and conditional `9 x 9` twist meshes,
the solver requests the three lowest eigenpairs. The first two eigenvectors form
the candidate frame

```text
Psi(i,j) = [psi_0(i,j), psi_1(i,j)].
```

The third level supplies the separation from the rest of the spectrum. The
candidate bundle is admitted only when its eigensolver, orthonormality,
spectral-isolation, and neighbor-overlap gates all pass.

Interacting Harper-Hofstadter hard-core bosons are a literature-supported setting
in which a bosonic `nu=1/2` fractional-Hall phase can occur, but that prior result
does not determine the outcome at this exact finite parameter point
([Gerster et al.](https://arxiv.org/abs/1705.06515)). Finite geometries require
their own diagnostics and cautions
([Rosson et al.](https://arxiv.org/abs/1901.03595));
the broader fractional-Chern-insulator and finite Hofstadter contexts are given
by [Regnault and Bernevig](https://arxiv.org/abs/1105.4867) and
[Scaffidi and Simon](https://arxiv.org/abs/1407.1321).

## 2. Rank-two determinant-link instrument

S9 uses the gauge-invariant discretized Chern construction and its non-Abelian
extension described by
[Fukui, Hatsugai, and Suzuki](https://arxiv.org/abs/cond-mat/0503172).
It does not assign separate Abelian Berry phases to the two low-energy
eigenvectors. Such an assignment would be unstable under a local change of basis
inside a nearly degenerate two-dimensional space.

For each directed mesh edge, form the rank-two overlap

```text
M_mu(i,j) = Psi(i,j)† Psi(i+mu,j).
```

If `M = U Sigma V†` is its singular-value decomposition, the unitary polar factor
is `Q = U V†`. The determinant link is

```text
link_mu(i,j) = det(Q) / |det(Q)|.
```

The oriented plaquette phase and total lattice Chern number are

```text
F(i,j) = Arg[
    Ux(i,j)
    Uy(i+1,j)
    conj(Ux(i,j+1))
    conj(Uy(i,j))
]

C = sum_(i,j) F(i,j) / (2 pi).
```

Taking the determinant projects the `U(2)` parallel transport of the rank-two
bundle to the `U(1)` connection on its determinant line. A local frame
transformation `Psi(i,j) -> Psi(i,j) V(i,j)` must therefore leave the final
Chern number invariant. S9 tests this directly with 32 preregistered independent
local `U(2)` frame fields on each completed target mesh.

The instrument is accepted only when every neighbor overlap is invertible above
the declared floor, every plaquette phase stays away from the principal-argument
branch cut, and the raw Chern sum lies within the preregistered tolerance of an
integer. An integer-looking output is not self-authenticating.

## 3. Controls precede the target

Execution is fail-closed and ordered:

1. **Static construction integrity.** Check basis cardinality and occupation,
   Hermiticity, `2 pi` twist periodicity, and every directed plaquette flux.
2. **Atomic zero-Chern control.** At `t = 0`, distinct on-site energies give a
   unique twist-independent product state. Its rank-one Chern number must be zero
   on both meshes.
3. **One-particle representation control.** At the three declared twists, the
   complete `N_b = 1` hard-core many-body spectrum must equal the `24 x 24`
   single-particle Hofstadter spectrum.
4. **Integer-Hall orientation control.** The six states in the lowest
   single-particle Hofstadter band form an occupied rank-six bundle. It must be
   isolated and have `|C_IQH| = 1` on both meshes, with one common sign.
5. **Target `7 x 7`.** Run only if all four control stages pass.
6. **Target `9 x 9`.** Run without parameter changes only if the coarse target
   passes all solver, isolation, overlap, branch, and integrality gates.
7. **Local-frame attack.** Recompute the determinant-link instrument for all 32
   local `U(2)` frame scrambles without re-diagonalizing.

If a control fails, the S9 instrument is `VOID`; a target result must not be
emitted. If the rank-two bundle is not isolated, no Chern value is divided by
two. A timeout or memory-limit breach is `INCONCLUSIVE_RESOURCE_LIMIT`, not
evidence for or against the physical hypothesis.

The exact numerical gates are `S9-G1` through `S9-G11`, and the control gates are
`S9-C1` through `S9-C3`, in the preregistration manifest. They cover:

- `1e-12`-scale construction checks;
- eigenpair residual and frame-orthonormality checks;
- an isolated-bundle requirement `Delta > max(1e-6, 100 r_max)` and
  `W/Delta < 1`;
- minimum neighbor-overlap singular value `>= 1e-6`;
- branch-cut margin `max |F(i,j)| < pi - 1e-3`;
- Chern integrality and exact rounded agreement between meshes;
- invariance under all 32 local-frame attacks.

No lattice, filling, flux, mesh, seed, solver tolerance, gap definition, or gate
threshold may be tuned after observing a failure in this round.

## 4. Curvature degree and the graph-sheaf boundary

The S9 Chern instrument concerns Berry curvature on the two-dimensional boundary-
twist torus. The rank-two eigenspaces define a vector bundle over
`T^2_(theta_x,theta_y)`, and its determinant line has a first Chern class

```text
c_1(det E) in H^2(T^2; Z).
```

The curvature representative is a degree-two differential form. The lattice
plaquette phases approximate its integral over two-cells in twist space.

This object is not the repository's flat graph-sheaf monodromy. A graph or
one-dimensional nerve has path transport and cycle holonomy, but no two-cells on
which this Berry-curvature integral could live. Nontrivial global monodromy can
exist for a flat connection, and a nonzero sheaf `H^1` can reflect ordinary cycle
space rather than curvature. Conversely, a nonzero curvature or Chern class is
not interchangeable with a sheaf-cohomology `H^1` class.

Accordingly, S9 makes no biconditional of the form

```text
nontrivial holonomy <-> nontrivial curvature <-> nontrivial sheaf H^1.
```

That statement is false in this generality. Differential-geometric results that
relate curvature to the holonomy Lie algebra address the identity component under
their own hypotheses; they do not identify global holonomy with arbitrary sheaf
cohomology. S9 uses only the degree-two Berry/Chern construction defined above.

## 5. Commands

After the implementation files named by the preregistration are present, run the
focused verification first:

```powershell
python -m pytest -q tests/test_fqhe.py --basetemp=.agent/pytest-s9-fqhe
```

Then run the controls-first probe:

```powershell
python experiments/run_fqhe_probe.py
```

The runner is expected to write:

```text
artifacts/s9_fqhe/fqhe_probe.json
artifacts/s9_fqhe/fqhe_probe.envelope.json
```

Validate the focused and repository-wide contracts after artifact generation:

```powershell
python -m pytest -q tests/test_fqhe.py --basetemp=.agent/pytest-s9-fqhe-postrun
python -m pytest -q --basetemp=.agent/pytest-s9-full
```

These commands are the intended execution surface, not a report that they have
already passed. The result document must preserve controls before target outcomes,
the full gate ledger, raw and rounded Chern values, mesh-local numerical
diagnostics, seeds, environment, and runtime provenance.

## 6. Interpretation ceiling

If every control and target gate passes, S9 supports only this statement:

> At the preregistered finite `6 x 4` hard-core-boson Hofstadter point, the two
> lowest states form a numerically isolated rank-two bundle over the tested twist
> meshes whose determinant line has total Chern magnitude one, invariant under the
> preregistered local-frame attacks.

Under those conditions, `C/2` is a finite-size bundle-normalized response label
with magnitude `1/2`. Even a complete pass does **not** establish:

- a thermodynamic or continuum fractional quantum Hall phase;
- a measured Hall conductance or charge pump;
- fractional quasiparticle charge, quasihole counting, or anyon statistics;
- braiding, Fibonacci anyons, or topological quantum computation;
- robustness under perturbations, finite-size scaling, or hardware behavior;
- quantum speedup, quantum advantage, or cognitive performance;
- an empirical bridge to the repository's architectural metaphors.

Failure also has narrow meaning. It retires this preregistered parameter point or
voids this instrument, according to the failed gate. It does not prove that the
underlying phase is absent elsewhere. The remaining thermodynamic and transport
questions stay typed as a separate finite-size topological remainder.
