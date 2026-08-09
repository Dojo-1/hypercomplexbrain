# QSigma-R1U — Polyqudit observer execution result

**Status:** MEASURED / self-attested. Preregistered promotion gate failed.

This execution implements the frozen R1U contract without changing its promotion threshold or matched controls. A construction bug found on the first local run allowed planted relations to overwrite one another; it was corrected before interpretation by making planted order-2 relations disjoint. The frozen hypothesis, tested dimensions, seeds, controls, and thresholds were unchanged.

## Executed scope

- d in {2,3,4,5,7}
- N in {8,16,32}
- 8 deterministic seeds per (d,N): 120 measured points total
- bounded order k=2 local generalized-Weyl sections; no global su(d^N) materialization
- matched controls: random allocation, scalar Weyl norm, equal-rank random orthogonal feature, alignment-only oracle
- frame audit: identity/cyclic symbol relabelling plus adversarial reflection with transformed secret

Focused regression tests: `4 passed`.

## Primary result

| d | mean algebra recall | mean alignment recall | mean delta vs best control | bootstrap 95% LCB | max frame spread |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.364583 | 0.364583 | -0.041667 | -0.104167 | 0.0e+00 |
| 3 | 0.385417 | 0.385417 | -0.062500 | -0.125000 | 0.0e+00 |
| 4 | 0.531250 | 0.531250 | -0.020833 | -0.052083 | 0.0e+00 |
| 5 | 0.656250 | 0.656250 | -0.020833 | -0.062500 | 0.0e+00 |
| 7 | 0.645833 | 0.645833 | -0.010417 | -0.031250 | 0.0e+00 |

No d value satisfies the preregistered lower-95%-confidence-bound threshold of +0.05. `promotion_ds = []`; therefore `promotion_pass = false`.

The algebra-aware and alignment-only observers have identical mean recall at every tested d. The algebra-aware score therefore adds no localization discriminator beyond the hidden-relation alignment statistic on this synthetic construction. Because the verdict is against the *best* matched control, occasional negative deltas arise when another control ties or exceeds the same finite-sample recall.

## Strongest surviving claim

**M / self-attested:** on the finite synthetic modular-neighbour localization family tested here, a bounded k=2 generalized-Weyl observer is frame-stable under the declared transformations and uses local O(N) sections, but it does not improve recall@budget over the preregistered alignment-only control. The stronger R1U discrimination hypothesis is killed for this round.

## What is retired by this round

- **R:** that the tested generalized-Weyl observer supplies localization information beyond alignment/transversality on this construction.
- **R:** promotion of this implementation as evidence for cognition-per-compute advantage.

This does not retire generalized qudit observability in other tasks, nor the separately preregistered R1V geometry-native carrier experiment. It only closes the frozen R1U claim tested here.

## Resource / scaling boundary

Peak Python-traced memory in the bounded run was 334302 bytes and wall time was 0.367 s in the recorded environment. These are finite implementation measurements, not asymptotic results.

## Typed remainder

- `[R]_carrier`: no physical qudit noise/hardware model.
- `[R]_observer`: only the planted order-2 modular relation is represented.
- `[R]_transport`: only the declared finite frame transforms were audited.
- `[R]_scaling`: N <= 32; no asymptotic conclusion.
- `[R]_cognition`: localization is not cognitive performance.
- `[R]_witness`: producer and verifier are not independent.

## Reproduce

```bash
python experiments/run_qsigma_r1u_polyqudit_observer.py > artifacts/qsigma_r1u_polyqudit_observer.json
python -m pytest tests/test_qsigma_r1u_polyqudit_observer.py -q
```
