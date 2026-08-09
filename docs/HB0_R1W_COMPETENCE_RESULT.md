# HB-0 R1W — bounded polycosmic competence result

**Status:** MEASURED / self-attested. Combined promotion gate failed.

R1W executes the frozen competence preregistration over synthetic latent-state tracking, mutual-recognition coordination, and delayed correction. It does not alter the HB-0 ontology and it does not count as an R1V geometry-native-carrier result.

## Execution

- N in {16, 32, 64}
- latent dimension 4
- 20 deterministic seeds per N
- 48 tracking ticks, chart drift at tick 24
- calibration ticks {0, 8, 16, 32, 40}
- observation noise sigma=0.05
- controls: FLAT_POOLED, SHUFFLED_TYPED, ONE_CLOCK_LOCAL
- focused standalone regression harness: `4 passed in 0.12s`
- max generated-chart orthogonality defect: `1.11e-15`
- max noiseless calibration round-trip defect: `1.33e-15`

The local numeric execution was performed in a standalone container because the private repository is not mounted into that runtime. The committed repository test separately asserts that the runner is connected to the merged `aionq.hb0.kernel.build_hb0` 32-Worldlet runtime; repo/CI execution remains the integration witness.

## H1 — latent-state tracking under chart drift: PASS

| N | HB0_TYPED NRMSE | FLAT_POOLED | SHUFFLED_TYPED | paired diff vs best control | bootstrap 95% UCB |
|---:|---:|---:|---:|---:|---:|
| 16 | 0.582942 | 0.793727 | 0.890511 | -0.196973 | -0.145088 |
| 32 | 0.562663 | 0.766461 | 0.874623 | -0.195092 | -0.153744 |
| 64 | 0.564449 | 0.785691 | 0.890714 | -0.209325 | -0.183129 |

At N=32 and N=64 the paired bootstrap upper confidence bound is below the frozen `-0.05` threshold. Matrix-vector multiply counts are identical to the best tracking controls (1536 at N=32, 3072 at N=64).

**M / bounded:** the typed per-Worldlet transport calibration materially improves reconstruction on this constructed chart-drift family versus one pooled chart and versus a correspondence-shuffled typed null.

## H2 — mutual-recognition coordination: PASS

At N=32:

- HB0_TYPED shared-state NRMSE: `0.035146`
- FLAT_POOLED shared-state NRMSE: `0.563119`
- paired mean difference: `-0.527973`
- bootstrap 95% UCB: `-0.426186`
- HB0_TYPED private leakage: `0.0`
- FLAT_POOLED private leakage: `0.695170`
- maximum viewpoint-swap asymmetry: `0.0`

The frozen coordination gate passes. The typed protocol reconstructs the shared coordinates while its declared non-absorption mask prevents the private coordinate from being transmitted.

**Boundary:** the private mask is part of the designed protocol, so this is evidence that the protocol enforces the declared separation on the synthetic task, not evidence of emergent social cognition.

## H3 — delayed correction: FAIL

- HB0_TYPED final error: `0.0`
- ONE_CLOCK_LOCAL final error: `0.159260`
- paired mean difference: `-0.159260`
- bootstrap 95% UCB: `-0.159260`
- HB0_TYPED premature slow-overwrite rate: `0.0`
- ONE_CLOCK_LOCAL premature slow-overwrite rate: `0.0`

The final-error component separates cleanly, but the preregistered gate additionally required the one-clock control's premature slow-overwrite rate to exceed HB0 by at least `0.20`. It did not: both observed rates are zero under the frozen overwrite definition.

No post-hoc threshold change is permitted. H3 fails.

## Promotion verdict

```text
H1_tracking    = true
H2_coordination = true
H3_correction  = false
compute_ok     = true
promotion_pass = false
```

Therefore the combined claim **"typed polycosmic protocol adds bounded synthetic competence value" is NOT promoted** in R1W.

The strongest surviving statements are component-level `[M]` measurements for typed chart-drift recovery and the declared mutual-recognition/non-absorption protocol. The multi-clock correction interpretation remains `[H]` because its frozen discriminator failed even though final error improved.

## Remainders

- `[R]_task`: the constructed orthogonal-chart tasks may favor typed local transport.
- `[R]_competence`: no external cognitive benchmark has been run.
- `[R]_integration`: local numeric execution was standalone; repo/CI integration is a separate witness.
- `[R]_witness`: producer and verifier are not independent.
- `[R]_quantum`: no physical quantum substrate is used here.

## Reproduce

```bash
python experiments/run_hb0_r1w_competence.py > artifacts/hb0_r1w_competence.json
python -m pytest tests/test_hb0_r1w_competence.py -q
```

The committed seed-level CSV and compact JSON summary preserve the measured evidence without converting the two positive component results into a combined cognitive-performance claim.
