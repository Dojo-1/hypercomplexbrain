# QΣ-R8 — Dual-Carrier Quantum Hyperbolic Movement

**Status:** bounded deterministic result (`M` evidence tier), locally
reproduced, not independently witnessed.

## Result

The R8 slice places source hyperbolic growth and fixed-width operational
information in one AION movement trace without pretending they are the same
scalar.

- The source carrier is the absolute Cartan pseudo-volume on real
  `SL(2,R)`. Its slab volume has exact exponent two.
- The operational carrier is the existing five-dimensional Bell-erasure
  density family. It is measured with trace distance, root fidelity, Bures
  geometry, SLD quantum Fisher information (QFI), and finite-ensemble
  information.
- The bridge is the projective coordinate `q = exp(-2*rho)` plus a
  normalization cocycle. At every finite `rho`, exact tomography can recover
  `q`; fixed additive-`rho` sensitivity is attenuated rather than literally
  erased.
- The exact loss on the declared determinant-one real source is global sign:
  `M` and `-M` produce the same density.

The frozen run completed with **12/12 controls**, and H1 survived. This is a
result about one finite path and one attempted-use instrument. It is not a
channel-capacity theorem, a hardware result, or a quantum-advantage claim.

## Two fibers and one typed seam

```text
Source Worldlet
  M(rho,phi,psi) in SL(2,R)
  absolute pseudo-volume
             |
             | Tendril:
             | A = M / ||M||2
             | q = exp(-2*rho)
             | failure cost retained
             v
Operational Worldlet
  5 x 5 Bell-erasure density
  trace / fidelity / Bures / QFI / bits
```

The source and operational Worldlets carry different `Geometry` values and
different algebra regimes. The Tendril records preserved, transformed, lost,
cost, typed remainder, and absent-return fields. A gluing guard rejects a
source section paired with an unrelated operational section.

`QuantumMovementOmniTool` is an S-tier telemetry and routing facade. Its
`weave` and `deweave` events are append-only governance events, not physical
quantum inverses. The unsupported `materialized_prefix` mode is refused until
it can be backed by explicit `compose_word` telemetry.

`OHM` here means the proposed **Ohnium** architecture. The associated
`A/U/M` labels may acknowledge Om/AUM's three phonetic phases, but R8 does not
model a chant, meditation practice, or spiritual claim as a quantum operator.
Ohnium observability requires its own typed phase operators and evidence trace;
those are outside this completed R8 instrument.

## Governing relations

For the frozen source chart:

```text
singular(M) = (exp(rho), exp(-rho))
singular(A) = (1, q)
q           = exp(-2*rho)
p_Bell      = (1 + q^2) / 2
p_worst     = q^2
```

The attempted-use SLD QFI is

```text
J_(rho,phi,psi) =
  diag(
    8 / (exp(4*rho) - 1),
    (1 + exp(-2*rho))^2,
    (1 - exp(-2*rho))^2
  ).
```

In the compactified radial coordinate:

```text
J_(q,phi,psi) = diag(2/(1-q^2), (1+q)^2, (1-q)^2).
```

The radial `rho` component has high-depth log slope `-4`, while the `q`
coordinate remains regular near zero. The total attempted-use parameter
volume before the projective quotient is finite:

```text
integral sqrt(det J) d(rho) d(phi) d(psi) = sqrt(2) * pi^3
                                           = 43.84949699997263.
```

The pullback volume-form distortion is

```text
8*sqrt(2)*exp(-4*rho) / sqrt(1-exp(-4*rho)).
```

It is a typed distortion between volume forms—not a distance, information
rate, or capacity ratio.

## Weave, deweave, and movement

The frozen threshold is trace distance `0.05`.

| event | motion | trace distance | routing |
|---:|---|---:|---|
| 0 | initial observation | — | weave |
| 1 | radial | 0.1908703610 | weave |
| 2 | radial | 0.1491508917 | weave |
| 3 | radial | 0.0631772791 | weave |
| 4 | radial | 0.0080012009 | deweave |
| 5 | radial | 0.0010731538 | deweave |
| 6 | high-depth radial | 0.0001646873 | deweave |
| 7 | `rho=6` angular | 0.1722442619 | weave |
| 8 | `rho=6` angular | 0.1722422122 | weave |

H1 required both a high-depth fixed-angle radial deweave and a `rho=6`
boundary angular weave. The witnessed indices were `6` and `[7, 8]`,
respectively.

This separates two statements that a radial-only scalar view would collapse:

1. additive-`rho` sensitivity becomes weak at high depth;
2. angular movement on the same boundary layer can remain operationally
   distinguishable.

## Cocycle and physical echo

For normalized products:

```text
kappa(X,Y) = log||X||2 + log||Y||2 - log||XY||2 >= 0
A_X A_Y   = exp(-kappa) A_XY
eta        = exp(-2*kappa_word)
p_stream   = eta * p_direct.
```

On the frozen three-factor word:

```text
kappa_word = 1.5404404120852284
eta        = 0.045918792448470636
p_direct   = 0.5160606109058252
p_stream   = 0.02369688008301555
cocycle identity defect = 4.44e-16.
```

`echo_transport(M)` composes `M` with its matrix inverse and reports both
source return and attempted-use survival. The source and conditional state can
return while the streamed attempt probability remains costed. Its expected
survival is derived from the cocycle for every accepted invertible matrix;
the familiar `exp(-4*rho)` specialization is used only on the declared
determinant-one Cartan source.

## Operational information bracket

The nine distinct density codewords on the frozen path give:

| instrument | bits per attempted use |
|---|---:|
| PGM mutual information | 0.1288531963 |
| Holevo information | 0.2498123648 |
| oracle-erasure upper instrument | 1.6826610087 |
| `log2(9)` catalogue ceiling | 3.1699250014 |

The required ordering holds:

```text
PGM <= Holevo <= oracle-erasure <= log2(N).
```

The ambient source slab through `rho=6` is
`803152.83326961 absolute-pseudo-volume`. It is not the volume sampled by the
path and cannot be compared, added, averaged, or ranked against the bit
quantities.

## Controls and adversarial corrections

The completed controls cover:

- exact R6/R7 binding and density validity;
- dense versus closed pair geometry;
- analytic versus finite-difference Bures QFI;
- the rank-changing `rho=0` boundary;
- `q` compactification and total QFI volume;
- normalization cocycle and streamed-word accounting;
- source echo versus attempted survival;
- depolarizing-channel data processing;
- common compact `SO(2)` frame invariance and matched `SU(2)` control;
- typed AION gluing;
- append-only weave/deweave governance;
- evidence and finite-information ordering.

The independent code audit found four defects before the artifact was
accepted: an overgeneral echo formula, a metadata-only prefix mode, an
unguarded source/quantum seam, and unstable extreme-coordinate formulas. All
were corrected without changing the frozen path, threshold, tolerance,
prediction, or H1 rule.

The first runner invocation then stopped before creating an artifact because
its serializer referenced a nonexistent R7 metric field. The serializer was
bound to the actual `InformationMetrics` schema, preflighted without writes,
and the unchanged frozen run completed. This failed attempt remains recorded
in `.agent/notes.md`.

## Evidence boundary

The run establishes executable relations for the declared finite family. It
does not establish:

- an optimized classical or quantum channel capacity;
- an infinite-dimensional bosonic-channel theorem;
- a thermodynamic, memory, or hardware advantage;
- a proof about cognition, consciousness, general intelligence, `P=NP`, or
  `P!=NP`;
- an independently reproduced result.

Parameter-independent CPTP postprocessing is treated through data-processing
controls: the frozen depolarizing channel contracted trace distance, increased
root fidelity, and did not exceed the input QFI beyond the preregistered
numerical allowance.

## Provenance and reproduction

Preregistration SHA-256:

```text
409344240b5042c72f7ca3b4102a50c991595784a88ca7c018cf7fac46490d62
```

Deterministic result SHA-256:

```text
1f78b35c0ee7a2f385a52956ca3b5a1fee60f3f6c239cb0d6a4fdf7892e84599
```

Publication uses the same two-commit boundary as R7: source, manifest, tests,
and runner are frozen first; the runner then records that producer commit in
the envelope, and a second commit adds only the generated JSON and envelope.
The envelope digest is therefore commit-dependent. The local envelope is
hash-verifiable but not independently witnessed.

Verification:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_quantum_movement.py -q
python -m pytest tests/test_hyperbolic_qubit.py `
  tests/test_qsigma_r7_information.py `
  tests/test_s4_g100.py `
  tests/test_quantum_movement.py -q
```

The append-once target runner is executable only in a clean copy that does not
already contain `artifacts/r8_quantum_movement/`:

```powershell
python experiments/run_quantum_movement.py
```

Primary mathematical context:

- Caves, *Reframing SU(1,1) interferometry*:
  <https://arxiv.org/abs/1912.12530>
- Escher et al., *General framework for estimating the ultimate precision
  limit in noisy quantum-enhanced metrology*:
  <https://arxiv.org/abs/1201.1693>
- Alipour and Rezakhani, *Extended convexity of quantum Fisher information in
  quantum metrology*:
  <https://arxiv.org/abs/1403.8033>
- Pérez-García et al., *Contractivity of positive and trace-preserving maps
  under Lp norms*:
  <https://arxiv.org/abs/math-ph/0601063>
- Holevo, *The capacity of the quantum channel with general signal states*:
  <https://arxiv.org/abs/quant-ph/9611023>
- Holevo and Werner, *Evaluating capacities of bosonic Gaussian channels*:
  <https://arxiv.org/abs/quant-ph/9912067>
