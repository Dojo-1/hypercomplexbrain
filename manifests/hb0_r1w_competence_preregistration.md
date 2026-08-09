# HB-0 R1W — Polycosmic competence preregistration

**Status:** H / frozen preregistration. No result is claimed by this file.

**Parent floor:** merged HB-0 typed polycosmic kernel and the measured R1U correction. R1W does not reopen retired R1U generalized-Weyl localization claims and does not count as an R1V carrier result.

## Question

Does typed local transport plus reciprocal recognition plus multi-clock correction improve synthetic drift recovery and delayed correction over capacity/compute-matched controls when all methods receive the same observations and calibration events?

## Active object

Use the existing HB-0 32-Worldlet topology: four identity regimes (somatic, episodic, social, prospective), three clocks (fast, meso, slow), heterogeneous local charts, return-capable tendrils, gerbe/coherence telemetry, and an evidence/governance boundary.

No claim of sentience, consciousness, AGI, quantum advantage, hardware advantage, or asymptotic complexity is in scope.

## Frozen task families

1. **Latent-state tracking under chart drift.** A 4-D latent process is observed through N independently generated orthogonal local charts with noise. Calibration pairs are supplied identically to all methods. At the frozen drift time, local charts rotate again. Score post-drift latent reconstruction.
2. **Mutual-recognition coordination.** Two partially incompatible observer coalitions see overlapping shared coordinates and private coordinates. Score shared-state recovery together with private-information leakage and viewpoint-swap asymmetry.
3. **Delayed correction.** A false provisional commitment is injected, followed later by a reliable correction. Score final correction retention and premature slow-identity overwrite.

The synthetic generators are independent of HB-0 implementation code; seeds and formulas are fixed in the runner.

## Methods / controls

- **HB0_TYPED:** local per-Worldlet transport calibration, reciprocal return maps, non-absorption/private-coordinate mask, and fast/meso/slow correction policy.
- **FLAT_POOLED:** one pooled orthogonal chart, ordinary averaging, one clock.
- **SHUFFLED_TYPED:** same number and shape of local maps as HB0_TYPED but Worldlet-to-map correspondence is permuted after calibration.
- **ONE_CLOCK_LOCAL:** correct local maps but all update channels use the same clock; tests whether transport alone explains delayed-correction performance.

All methods receive the same raw observations, calibration pairs, seeds, evaluation horizons, and downstream sample budget. Matrix-vector multiply counts are recorded as the primary compute proxy; wall time and peak traced memory are secondary telemetry.

## Grid

- worldlets N = {16, 32, 64};
- latent dimension d = 4;
- seeds = 0..19;
- tracking horizon = 48 steps; drift at step 24; calibration every 8 steps;
- observation noise sigma = 0.05;
- coordination shared dimensions = 2, private dimensions per side = 1;
- correction delay = 8 fast ticks.

## Primary component metrics

No weighted scalar promotion score.

- tracking post-drift normalized RMSE (lower is better);
- tracking return/round-trip defect (lower);
- coordination shared RMSE (lower);
- coordination private leakage (lower);
- coordination viewpoint-swap asymmetry (lower);
- delayed-correction final absolute error (lower);
- premature slow-identity overwrite rate (lower);
- matrix-vector multiply count, wall time, peak memory.

## Frozen predictions

H1: HB0_TYPED has lower post-drift tracking RMSE than both FLAT_POOLED and SHUFFLED_TYPED.

H2: HB0_TYPED has lower shared RMSE than FLAT_POOLED while keeping private leakage <= FLAT_POOLED and viewpoint-swap asymmetry <= 0.05.

H3: HB0_TYPED has lower delayed-correction final error and lower premature slow overwrite than ONE_CLOCK_LOCAL.

## Promotion gate

Promote only the narrow statement **"typed polycosmic protocol adds bounded synthetic competence value" [M]** if all conditions hold:

1. H1: paired bootstrap 95% upper confidence bound for HB0_TYPED minus the best matched control tracking RMSE is < -0.05 at N=32 and N=64;
2. H2: paired bootstrap 95% upper confidence bound for shared-RMSE difference vs FLAT_POOLED is < 0, private leakage is not worse by > 0.02, and viewpoint-swap asymmetry <= 0.05 at N=32;
3. H3: paired bootstrap 95% upper confidence bound for final-error difference vs ONE_CLOCK_LOCAL is < 0 and premature slow overwrite is lower by at least 0.20 absolute;
4. no correctness invariant fails and compute proxy for HB0_TYPED is <= 2.5x the best matched control on the same task.

Failure of any required gate kills the combined promotion. Component-level measured separations may still be reported without promotion.

## Correctness invariants

- every generated local chart is orthogonal within 1e-10;
- every returned local-to-latent-to-local calibration round trip has defect <= 1e-10 before noise;
- no private coordinate is directly supplied to the opposite coalition in HB0_TYPED;
- seeds and raw task instances are shared exactly across methods;
- method selection does not alter the data generator;
- JSON output forbids NaN/Infinity.

## Kill conditions

- tracking gain disappears against SHUFFLED_TYPED or FLAT_POOLED;
- coordination gain requires private leakage or viewpoint asymmetry above frozen thresholds;
- delayed-correction gain disappears against ONE_CLOCK_LOCAL;
- compute ratio exceeds 2.5x;
- any method receives privileged target labels or additional calibration events;
- any correctness invariant fails.

## Evidence / remainder

- P/A: finite linear algebra identities and explicit simulator contracts.
- M: only bounded seed-level measurements after execution.
- H: transfer to real cognition or external tasks.
- S: Worldlet, polycosmic identity, mutual-resonance and mind-quality interpretation.
- [R]_task: synthetic generators may favor structured transport.
- [R]_competence: no external cognitive benchmark.
- [R]_witness: producer and verifier are not independent.
- [R]_quantum: no physical quantum substrate is used in this round.

## Stop rule

R1W ends after the frozen four-method comparison, tests, seed-level artifact, bounded resource report, and promotion/kill decision are recorded. No new ontology, hardware lift, consciousness claim, or quantum-advantage claim is added inside this round.
