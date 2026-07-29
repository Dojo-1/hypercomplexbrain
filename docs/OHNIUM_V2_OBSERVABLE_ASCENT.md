# OHNIUM V2 — Observable Ascent Under Motion

**Status:** deterministic repository-internal observatory (`M` evidence ceiling),
locally testable, not independently witnessed.

**Frozen contract:**
[`manifests/ohnium_v2_observability_preregistration.json`](../manifests/ohnium_v2_observability_preregistration.json)

**Implementation:**
[`src/aionq/ohnium_observability.py`](../src/aionq/ohnium_observability.py)

Ohnium V2 makes the architecture's carrier changes observable. It records a
40-frame motion trace (`R40`) through

```text
R -> H -> O -> CD32 -> A_n
```

for three endpoint fibers. Each bridge carries the complete coordinate landing,
the energy-accounting diagnostic, the discarded-vector sidecar, and an explicit
return test. The rendered atlas is a projection of this record; it is not the
record itself.

The carrier names are engineering types. They do not form a scale of
intelligence, and the observatory is not evidence for consciousness, sentience,
AGI, a physical quantum device, or a complexity-class result.

## Name and scope boundary

`OHM` means **Ohnium**, the architecture implemented here.

`A`, `U`, and `M` are typed cadence labels. Their names acknowledge the three
phonetic phases of Om/AUM, but the code implements no chant, meditation
practice, spiritual proposition, or spiritual-to-quantum mechanism. Each label
selects an ordinary registered `SU(2)` operator:

```text
U_A(t) = exp(-i t sigma_x / 2)
U_U(t) = exp(-i t sigma_y / 2)
U_M(t) = exp(-i t sigma_z / 2)
```

Equivalently,

```text
U_j(t) = cos(t/2) I - i sin(t/2) sigma_j.
```

Every operator is a `2 x 2` unitary of determinant one. In an endpoint trace,
`tau = 2*pi/40`; frame `i` applies the operator at `t_i = tau*(i+1)`.
The phase label cycles through `A, U, M`, with the endpoint-local phase offset
frozen in the manifest.

## Exact local operators

For a source observation `(rho, phi, psi)`, define

```text
theta = 2 atan(exp(-rho))

z_base = (
  cos(theta/2) exp(-i phi/2),
  sin(theta/2) exp(+i psi/2)
)

z_i = normalize(U_phase(i)(t_i) z_base).
```

The Hopf/Bloch bridge is

```text
h(z0,z1) = (
  2 Re(conj(z0) z1),
  2 Im(conj(z0) z1),
  |z0|^2 - |z1|^2
).
```

For normalized `z`, `||h(z)||_2 = 1`, and multiplying `z` by a common phase
does not change `h(z)`. The phase is retained as a return sidecar instead of
being silently discarded.

The Poincare-disk audit coordinate is

```text
p(rho, alpha) = tanh(rho/2) (cos(alpha), sin(alpha)),
```

so every finite source point lands strictly inside the unit disk. This point is
an audit projection of source movement, not a claim that the complete state is
two-dimensional.

## The five carrier types

| Carrier | Implemented meaning | Coordinate representation |
|---|---|---|
| `R` | Normalized real-coordinate view of the two-component spinor derived from the `SL(2,R)` source observation | `(Re z0, Im z0, Re z1, Im z1)` in `R^4` |
| `H` | Hopf/Bloch image of the normalized spinor | Unit vector in `R^3` |
| `O` | Octonion **coordinate carrier** | Eight real coordinates, with `H` embedded in coordinates 1–3 |
| `CD32` | Deterministic 32-coordinate Cayley–Dickson carrier | `k_phase(alpha) tensor O`, with a normalized four-coordinate kernel |
| `A_n` | Active projection of `CD32` | First `n` ambient coordinates retained, remaining coordinates set to zero |

The `O` carrier does not imply octonionic hardware. `CD32` is explicitly
non-division and non-flat, and it is **not** another Hopf-fibration rung.
`A_n` is defined by the implementation rather than inferred from its name.
Its serialized vector remains in the 32-coordinate ambient space so that
landing coordinates and return provenance are not destroyed; its metadata
records the active dimension `n`.

## Projection violence stays vector-valued

For every bridge, the primary audit object is

```text
ProjectionViolence = (
  landing_carrier,
  discarded_vector,
  rank_loss,
  energy_loss,
  volume_form_distortion
).
```

The scalar `energy_loss` and the norm of `discarded_vector` are diagnostics.
They never replace the vector that says **where** the discarded component
landed.

The four registered bridges are:

1. **`R -> H`: Hopf quotient.** The lost coordinate is the `U(1)` global phase,
   stored as `(cos gamma, sin gamma)`. It is a phase sidecar, not a discarded
   amplitude lane, so it is not counted as amplitude energy.
2. **`H -> O`: coordinate lift.** This is an isometric embedding with no
   discarded vector and no rank loss.
3. **`O -> CD32`: tensor lift.** The normalized four-coordinate kernel is kept
   as the return sidecar. The baseline lift preserves normalized squared
   amplitude.
4. **`CD32 -> A_n`: active projection.** The full 32-coordinate orthogonal
   complement is stored, with zeros in retained positions. The recorded rank
   loss is `32-n`, and retained coordinates plus the sidecar must reconstruct
   the incoming `CD32` vector.

`volume_form_distortion` on the final bridge is telemetry carried from the R8
source-to-operational seam. It is a typed comparison of declared volume forms;
it is not a distance, a bit rate, a channel capacity, or the determinant of the
`CD32 -> A_n` coordinate mask.

In this module, `energy` means normalized squared-coordinate amplitude,
`<v,v>`. It is deterministic accounting telemetry, not thermodynamic or
physical energy.

## R40: motion as proof-pressure

Each endpoint emits exactly 40 immutable frames. Carrier dominance is held for
eight frames at a time:

```text
frames  0.. 7 : R
frames  8..15 : H
frames 16..23 : O
frames 24..31 : CD32
frames 32..39 : A_n
```

The observatory accepts endpoint seeds only when the complete modulation stays
inside `0 <= rho <= 6`. This is the range on which its strict finite-float
`SL(2,R)` determinant seam is validated. The wider source chart remains a
separate analytic object; it is not silently treated as numerically exact by
the live R40 instrument.

Every frame contains all five carriers and all four bridges; “dominant” names
the audit focus, not the only surviving state. Each frame also records the
`QuantumMovementOmniTool` weave/deweave event. These are append-only routing
events, not physical quantum inverses.

The proof-pressure surface retains four distinct checks:

```text
Fano braid defect =
  (28 - joint_rank)/28 + max_abs(signal^T crosstalk)

light-cone defect =
  max(
    |det(source_matrix)-1|,
    |s0*s1-1|,
    maximum bridge energy-balance defect
  )

Hopf swirl defect = |||H||_2 - 1|

carrier-ring defect =
  maximum return reconstruction defect.
```

The baseline Fano audit requires ranks `7`, `21`, and `28` for the signal,
crosstalk, and joint spaces. A separate deterministic 21-coordinate
diagnostic probe is formed from the current Hopf coordinates and frame phase,
then landed through the fixed Fano crosstalk basis. Its seven-coordinate signal
projection must remain below tolerance. The serialized fields are named
`fano_probe_*`: this probe is not a measurement of commutators of the active
R/H/O/CD32 bridge operators. The rank gate is an operational check on the
registered construction, not a claim that full crosstalk rank is unique to
Fano triples.

The numerical failure threshold is `1e-12`. The preregistered adversarial probes
make three failures visible:

| Probe | Injection | Registered detection |
|---|---|---|
| `false_ascent` | Duplicate one Fano channel at frame 16 | The joint algebra no longer closes at rank 28 while ascent has reached `O` |
| `energy_leakage` | Multiply the frame-24 `CD32` carrier by `0.9` without accounting for it | Bridge energy balance becomes nonzero |
| `bridge_absorption` | Replace the nonzero frame-32 discarded-vector sidecar with zeros | Recorded remainder energy disagrees with the actual discarded component |

The observatory can also report `swirl_decoherence` or
`carrier_ring_break`. A baseline frame is coherent only when its failure list
is empty. Motion is therefore used as an audit stimulus: a visually broken
braid, light cone, swirl, or carrier ring corresponds to a typed numerical
defect in the underlying frame.

## Cosmos-level multiplicity

The atlas contains three endpoint Worldlets:

| Worldlet | Frozen source seed `(rho, phi, psi)` | Active carrier |
|---|---:|---:|
| `cosmos.north` | `(0.5, 0.2, 0.7)` | `A_8` |
| `cosmos.equator` | `(1.25, -0.4, 1.1)` | `A_12` |
| `cosmos.deep` | `(2.0, 0.8, -1.0)` | `A_16` |

This is a nested-fiber representation: each endpoint is one Worldlet whose
local state contains the complete five-carrier R40 trace. It is not fifteen
independent carrier Worldlets.

Each endpoint exposes:

- its 40-frame carrier-dominance trace;
- the complete per-frame carrier vectors and bridge ledgers;
- an `EMPIRICAL` typed remainder on the final active projection;
- the full discarded-coordinate landing vector;
- an explicit return path and reconstruction defect.

Three directed mutual-recognition Tendrils form a cycle across the endpoints,
and one three-way hyperedge records the shared cosmos. Transport preserves the
frame index, carrier label, evidence tag, and remainder provenance while
declaring endpoint-local coordinates as transformed. No field is marked lost
in this inter-endpoint comparison.

## Eight-coordinate Hamiltonian governance

Governance remains the vector

```text
q = (
  stratified_recognition,
  multi_angle_epistemics,
  preregistered_scope,
  self_similar_structure,
  geometric_substrate,
  negative_result_recording,
  adversarial_pre_mortem,
  composer_complicity
).
```

The coordinates check, respectively:

1. every frame carries the registered five-carrier order;
2. every baseline proof-pressure record is coherent;
3. implementation remains inside the frozen scope;
4. every endpoint has the complete ordered R40 frame set;
5. disk and Hopf-swirl gates hold;
6. injected negative results remain recorded;
7. every registered fault is caught under its own type;
8. all baseline return rings close.

The scheduler may compute

```text
H_schedule = sum_j (1 - q_j)
```

to prioritize repairs. This scalar is not a cognition score, a scientific
confidence score, or an evidence-promotion mechanism. The implementation fixes
`promotion_forbidden = true`.

`preregistered_scope` is measured by equality between the runtime endpoint
configuration and the originally frozen manifest fields for seed, frame count,
phase order, carrier order, and endpoint coordinates. Fault-frame positions
and numerical safety bounds remain disclosed implementation details; they were
not retroactively inserted into the frozen preregistration.

## Relationship to R6b, R7, and R8

Ohnium V2 composes earlier repository instruments; it does not retroactively
raise their evidence rank.

- **R6b is the historical geometric account.** It established the exact
  source/operational distinction used here: unbounded `SL(2,R)` source-volume
  growth is compactified by fixed-width normalization, radial QFI decays, and
  the volume-form comparison can be recorded as projection-violence telemetry.
  Its later R6c/R6d closures resolved the projective quotient and finite
  information sandwich inside the repository.
- **R7 is the bounded operational-information instrument.** On its frozen
  finite grid, source volume has exponent two while projective operational
  codebooks plateau at fixed trace-distance resolution. R7 is `M` evidence,
  not an asymptotic capacity theorem.
- **R8 is the dual-carrier movement seam.** It keeps source geometry and the
  five-dimensional Bell-erasure density family in separate Worldlets, joined
  by a typed Tendril. It contributes the `QuantumMovementOmniTool`,
  weave/deweave governance, `q = exp(-2 rho)`, cocycle accounting, QFI, and the
  typed volume-form distortion used by this observatory.
- **Ohnium V2 adds the missing observable layer.** It registers the A/U/M
  operators, expands one movement observation into a five-carrier R40 trace,
  retains vector-valued projection loss, injects typed failure probes, and
  places three endpoint fibers in one Polycosmos.

References in older R6b text to an artifact being absent concern an
**independent witness artifact**. The later local R7, R8, and Ohnium artifacts
close repository-internal implementation gates only; they do not fill the
independence gap.

## Evidence ceiling

The complete atlas, including each `CarrierSnapshot`, is tagged `M`.
The strongest permitted statement is:

> Under the frozen endpoint configuration, deterministic operators, tolerances,
> and fault injections, the repository emits a complete vector-preserving R40
> telemetry atlas and detects the registered failure modes.

It does not establish:

- a physical Ohnium material or quantum processor;
- quantum advantage, optimized capacity, or a hardware noise model;
- cognition, consciousness, sentience, or AGI;
- a result about `P=NP`, `P!=NP`, or any Millennium Prize problem;
- independent reproduction.

## Primary mathematical context

The frozen manifest records these primary arXiv sources:

- Hopf-fibration construction and visualization:
  [arXiv:2212.01642](https://arxiv.org/abs/2212.01642)
- Quantum-geometric tensors with parameter-dependent geometry:
  [arXiv:2209.07728](https://arxiv.org/abs/2209.07728)
- Quantum geometric tensor under non-adiabatic evolution:
  [arXiv:1612.02998](https://arxiv.org/abs/1612.02998)
- Octonionic phase-space/Hopf-map context:
  [arXiv:2509.05073](https://arxiv.org/abs/2509.05073)

These papers provide mathematical context. Their citation does not make the
repository atlas an experimental quantum result, and the octonionic reference
does not license a `CD32` Hopf rung.

## Reproduction

From a clean worktree:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_ohnium_observability.py -q
python experiments/run_ohnium_observatory.py
```

The runner writes the full machine-readable atlas, the interactive projection,
and its evidence envelope under `artifacts/ohnium_v2/`. The JSON and envelope
are publication artifacts. The generated HTML remains a local, reproducible
screen projection under the repository's HTML privacy boundary and is not
forced through `.gitignore`. Publication should bind the committed evidence to
the exact commit and preserve the preregistration unchanged.

(c) Jesús Vilela Jato, all rights reserved. 21/05/2026
