# HB0-T1 — Atomic active-tendril transaction

## Result

HB0-T1 turns one declared HB-0 profunctor tendril into a staged,
governed transaction over real finite-dimensional carriers:

```text
u  = F_t(x)
y* = Retract_Y(y + alpha * permeability_Y * (u - y))
```

The target is written only after endpoint, carrier, shape, finiteness,
return-map, matched-control, and governance checks succeed. An exception
restores every worldlet, identity section, budget field, tick, and tendril
ledger entry from the pre-transaction snapshot.

This is a bounded simulator result, not evidence of task competence,
cognitive advantage, quantum advantage, consciousness, or AGI.

## Frozen probe

The preregistration is
[`manifests/hb0_active_tendril_preregistration.json`](../manifests/hb0_active_tendril_preregistration.json).
It froze:

- seeds `0..7`;
- tendril `T_00`;
- declared target `W_somatic_01`;
- matched shuffled target `W_somatic_02`;
- coupling `0.5`;
- caller-supplied compute authorization `0.1`;
- active, disabled, and shuffled-target modes.

The implementation commit was frozen before the primary execution. No
parameter was changed after observing the result.

## Observation surface

Each transaction retains the full vectors rather than replacing them with a
single magnitude:

- source coordinates;
- transported output;
- backward round trip;
- target before, staged target, and target after;
- proposed and committed delta vectors;
- alignment residuals;
- typed round-trip remainder `[R]_transport`;
- cost, viability gates, and governance reasons.

The norm fields are supplementary summaries of these algebra-valued/vector
observations.

## Measured outcome

The single frozen execution produced:

| Quantity | Result |
|---|---:|
| Seeds | 8 |
| Passed controls | 13 / 13 |
| Minimum committed-delta norm | 0.011853503762084007 |
| Maximum committed-delta norm | 0.07453476581517547 |
| Minimum alignment reduction | 0.011853503762084008 |
| Maximum active round-trip defect | <= 1e-12 |

For every seed:

- active mode changed exactly `W_somatic_01`;
- disabled mode evaluated the same chart and cost but changed no worldlet;
- shuffled mode left `W_somatic_01` bit-identical and changed exactly
  `W_somatic_02`;
- missing compute authorization rejected the transaction;
- a complex output was rejected without discarding its imaginary component;
- same-seed kernels produced identical reports and post-transaction state;
- identity sections remained bit-identical because consolidation was outside
  this slice.

Raw evidence:

- [`artifacts/hb0_active_tendril/active_tendril.json`](../artifacts/hb0_active_tendril/active_tendril.json)
- [`artifacts/hb0_active_tendril/active_tendril.envelope.json`](../artifacts/hb0_active_tendril/active_tendril.envelope.json)

The envelope binds the preregistration, implementation, runner, tests, input
digests, and raw result. Local digest verification passes with effective
sample size 8. It is unsigned and has not been independently recomputed.

## Evidence boundary and remaining work

What HB0-T1 establishes is narrow: in this deterministic simulator and frozen
sample, one real-carrier correspondence can land a vector update on its
selected endpoint under explicit authorization and exact exception rollback.

It does not establish:

- phase-preserving complex or hypercomplex transport;
- identity-section consolidation after a worldlet update;
- atomicity of the older global `PolycosmicKernel.step()` path;
- a symmetric inter-worldlet distance contract;
- a corrected tunnelling observable;
- held-out task improvement or any general cognitive interpretation.

Those are independent slices and must receive their own preregistration and
controls.

## Reproduction

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_hb0_tendril_transaction.py tests/test_hb0.py -q
python experiments/run_hb0_tendril_transaction.py
```

Expected focused test result: `43 passed`.
