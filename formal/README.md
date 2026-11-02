# Formalization: what is actually checked

The public AION repository has two **distinct** formalization surfaces. Do not
merge their evidence levels.

## Native AION proof target

`formal/` now has its own Lake project; the **pinned toolchain** is Lean
`v4.27.0`, with Mathlib specified by Git commit
`a3a10db0e9d66acbebf76c5e6a135066525ac900` (Mathlib `v4.27.0`).
The [dedicated workflow](../.github/workflows/lean.yml) builds the import
closure, prints the exported proofs' axioms, and fails on admitted proofs. This
workflow, **not** Python's green CI, determines the formal build status.
Its most recent run must be checked before claiming kernel verification.
Until that run is green, treat this as an *attempted hardening patch*, not a
proof certificate.

| Native file | Claimed scope, conditional on successful Lean build | Excluded interpretation |
|---|---|---|
| [`OhniumObservatory.lean`](OhniumObservatory.lean) | 3-cycle A/U/M, exact list counts, conditional round-trip/accounting conjunction | Quantum observatory, quantum hardware, QFI, cognition |
| [`RecognitionChamber.lean`](RecognitionChamber.lean) | Round-trip metric defect under an isometry, discrete reservoir depletion in the constant-rate model, formal authorization restriction | Worldlet-cycle basis invariance, neurobiological respiration, independent review |
| [`R6Compact.lean`](R6Compact.lean) | Nonzero real Cartan radial stretch does not preserve squared Euclidean norm on every pair | Full `SL(2,R)`/quantum-gate representation theory, postselection cost, quantum advantage |
| [`R6Dilation.lean`](R6Dilation.lean) | Explicit finite real norm-preserving dilation of the operator-norm-normalized boost; sharp state-dependent `e^(-4ρ)` block-selection weight | Universal quantum lower bounds, QPU deployment, multi-step costs, cognitive advantage |
| [`R6Frames.lean`](R6Frames.lean) | Covariance and sharp success bounds under linear norm-preserving input/output frame changes, with a noncompact-boost exclusion | Arbitrary non-orthogonal transports, an adiabatic theorem, universal resource necessity |
| [`R6Remainder.lean`](R6Remainder.lean) | Signed real squared-norm transport remainder, cocycle with intermediate state, frame covariance, closed-boost-loop counterexample | Physical energy, semantic loss, universal quantum cost, or Worldlet gluing |
| [`R6MetricDefect.lean`](R6MetricDefect.lean) | Symmetric 2D quadratic-form pullback defects, tensor-level composition/mismatch accounting, and a zero-scalar/nonzero-form counterexample | Positive definiteness in arbitrary cases, heterogeneous Worldlet metrics, universal quantum or cognitive cost |

To reproduce on a machine with Git, `elan`, and Lean's required build tools:

```bash
cd formal
lake exe cache get
lake build
lake env lean ProofAudit.lean
```

Do not cite formal declarations solely because their names sound like the
architectural claim. Each is limited by its *actual type*, hypotheses and
carrier. The [audit entry point](ProofAudit.lean) makes those exact declarations
reviewable. Imported axioms and trusted kernel primitives must be distinguished
from new postulates. A Lean kernel proof does not certify its interpretation.

For an illustrated conceptual explanation and explicit exclusions, see the
[human guide to the R6 dilation](R6_DILATION_GUIDE.md).

The [moving-frame companion](R6_FRAMES_GUIDE.md) explains the joint-change
condition, exact endpoints, and the non-isometric negative control.

The [signed-remainder guide](R6_REMAINDER_GUIDE.md) explains why a closed
route does not certify that each intermediate transport was isometric.

The [metric-pullback guide](R6_METRIC_DEFECT_GUIDE.md) distinguishes an
anisotropic geometric observation from a one-state scalar remainder.

## Imported historical LeanMath material (quarantined)

[`leanmath/`](leanmath/) contains 11 imported Lean files, not imported by the
native `AionFormal` library. Its dependencies were incomplete at import time:
13 modules absent, two files with unterminated comments, and one live `sorry`.
A `lakefile.toml` inside `leanmath/` is **not** a build definition for AION's
native proof target.

See [`LEANMATH_PROVENANCE.md`](LEANMATH_PROVENANCE.md) for the byte-based census
and [`leanmath/README.md`](leanmath/README.md) for the original, *unverified*
historical claims. The original import remains preserved; making native Lean
green does not promote any LeanMath declaration.

Before promoting historical material: reconstruct its original dependency tree,
fix parse failures *upstream*, pin an exact toolchain and complete Mathlib
closure, remove all admits, build the entire intended module, and check the
formal statements for fidelity to the intended mathematical claims.

## Remaining substantive open bridge

R6Compact addresses the **diagonal real source obstruction**; R6Dilation
constructs one exact, state-dependent normalized encoding. Neither proves
a universal lower bound across all encodings.
A future separately preregistered formalization should define a bona fide
matrix/operator representation, prove the full compact-vs-noncompact statement
under explicit hypotheses, and connect any dilation/postselection bound to the
precise implemented map. Hardware and cognitive advantage require additional
empirical controls and cannot be promoted by these theorems alone.
