# QΣ-R7 — Source Volume Is Not Operational Information

**Status:** bounded computational result (`M` evidence tier), locally reproduced,
not independently witnessed.

## Question

Does the exact exponential volume growth of the `Q = +1` source
(`SL(2,R)` in Cartan coordinates) survive the existing R6 fixed-width block
encoding as operationally distinguishable one-shot information at fixed
trace-distance resolution?

The answer on the preregistered finite instrument is **no**. Source volume
grows with exponent two, while the operational projective codebooks plateau on
the frozen grid. This is a bounded result about this encoding and receiver. It
is not an asymptotic channel-capacity theorem and not a quantum-advantage
claim.

## Geometry and instrument

For coordinates `(rho, phi, psi)`, the source metric is

```text
diag(-1, cosh(rho)^2, -sinh(rho)^2).
```

Taking the absolute pseudo-volume density gives the exact slab volumes

```text
V(R)             = 2*pi^2*sinh(R)^2,
V_projective(R)  =   pi^2*sinh(R)^2,
```

so both source descriptions have exponent two. The projective quotient accounts
for the operational identification `M ~ -M`.

The split form is indefinite. Distinct null-separated points exist, so it is
explicitly rejected as a retrieval or packing distance. Operational separation
is instead measured after R6 normalization:

```text
A = M / ||M||_2
|v_A> = (I tensor A)|Phi+>
rho_M = |v_A><v_A| direct-sum (1-p_M)|fail><fail|.
```

The common orthogonal failure symbol charges the postselection cost. The
instrument retains no free arbitrary-precision classical normalization scale.
Dense `5 x 5` trace distance is used for quotienting and packing.

## Frozen experiment

The parent preregistration fixes:

- `rho = [0, 0.5, 1, 2, 3, 4, 6]`;
- an `8 x 8` angular grid at each radius;
- `epsilon = [0.05, 0.10, 0.20]`;
- four deterministic greedy orders;
- Bell-probe codewords, an erasure-aware pretty-good measurement, the Holevo
  bound, and an oracle-erasure bound;
- a matched `SU(2)` compact control;
- the high-depth natural-log slope gate
  `(log N(6) - log N(4))/2 <= 0.25`.

Parent preregistration SHA-256:

```text
839a2bf5208c73163c888ed6934db6f1de4b3bc7e42ffc615151ebe1f498f2ec
```

A method-only clarification was frozen before the main run. It changed no grid,
threshold, prediction, or verdict rule.

```text
d4e1f737131e35e20861f81adf32f2c53b63dd7a9556a821ea08cad4cbaf62bc
```

## Result

The raw grid contains 448 source descriptions. Projective operational
deduplication leaves 196 codewords; 252 descriptions are aliases.

| epsilon | N at R=4 | N at R=6 | high-depth slope |
|---:|---:|---:|---:|
| 0.05 | 100 | 100 | 0.000000 |
| 0.10 | 68 | 68 | 0.000000 |
| 0.20 | 52 | 52 | 0.000000 |

At `R = 6`, the operational information instruments remain finite and obey the
preregistered information sandwiches:

| epsilon | N | PGM information (bits) | Holevo (bits) | oracle-erasure (bits) |
|---:|---:|---:|---:|---:|
| 0.05 | 100 | 0.446237 | 1.069697 | 3.646640 |
| 0.10 | 68 | 0.456562 | 1.066664 | 3.482112 |
| 0.20 | 52 | 0.482308 | 1.119570 | 3.256350 |

The matched compact control retains larger codebooks and higher measured
information at the same radius:

| epsilon | N | PGM information (bits) | Holevo (bits) |
|---:|---:|---:|---:|
| 0.05 | 392 | 0.696666 | 1.875907 |
| 0.10 | 328 | 0.708254 | 1.926586 |
| 0.20 | 232 | 0.722600 | 1.994505 |

`N * p_min` is recorded only as a catalogue-count proxy. It is not bits per
attempted shot and is never used as capacity evidence.

## Interpretation boundary

The experiment separates three objects that must not be collapsed:

1. **Source geometry:** exact exponent-two volume growth.
2. **Operational state space:** a compact, projective family after fixed-width
   normalization and failure accounting.
3. **Information per attempted use:** receiver-dependent finite quantities
   bounded by Holevo and oracle-erasure instruments.

The finite-grid plateau supports the preregistered bounded conclusion. The
compact closure of the normalized fixed-width family supplies the exact reason
that fixed positive-resolution packing cannot acquire the source's unbounded
radial exponent. The run does not establish the asymptotic capacity of a
different multi-use channel, a noise-tolerant coding theorem, or an advantage
over compact encodings.

## Reproduction

```powershell
python -m pytest tests/test_qsigma_r7_information.py -q
python -m pytest tests/test_qsigma_r7_information.py tests/test_hyperbolic_qubit.py tests/test_evidence.py -q
python experiments/run_qsigma_r7_information.py
```

Verified focused result:

```text
27 passed
827 passed
status: COMPLETED
information inequality failures: 0
independent witness: false
```

Result artifact SHA-256:

```text
d8d40d3045ee5e84c256a23e95942078ffee96946acda3b9ed20be851f1d8a49
```

Publication uses a two-commit producer/artifact sequence. The first commit
freezes source, manifest, tests, and runner; recomputation at that commit writes
an envelope whose `commit_sha` names the exact producer tree. A second commit
adds only the generated JSON and envelope. The envelope locally hash-verifies
but is not independently witnessed.
