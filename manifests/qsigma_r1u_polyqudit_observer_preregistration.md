# QSigma-R1U — Polyqudit observer scaling

**Status:** H / frozen preregistration. No result is claimed by this file.

**Parent floor:** QSigma-R1T. R1T measured a finite 16-state Simon projection and retained alignment/transversality to hidden translation while retiring field-specific superiority. This round must not reopen the retired field-superiority claim without a new discriminator.

## Question

Can a bounded-order generalized-qudit observer localize hidden algebraic structure across increasing local dimension and system size better than compute-matched structure-agnostic controls, without constructing the full global operator algebra?

## Carrier

For sites i=1..N, permit local dimensions d_i >= 2 and define only the formal carrier

H = tensor_i C^(d_i).

Dense materialization of H or End(H) is forbidden by default. Implementations must operate through bounded-order local sections.

Homogeneous test families use d in {2,3,4,5,7} and N chosen so that matched methods receive the same observation and compute budget.

## Local observer language

For homogeneous d define generalized Weyl generators

X_d |j> = |j+1 mod d>,
Z_d |j> = omega^j |j>, omega = exp(2*pi*i/d).

The observer may retain single-site Weyl coordinates and selected interaction sections of order <= k. It must not enumerate su(d^N).

The observer type is therefore parameterized independently by:

- physical/local carrier dimension d,
- number of sites N,
- observer rank/basis budget r,
- interaction order k,
- compute budget B.

No equality among these quantities is assumed.

## Spin(8) / triality boundary

Spin(8), 8_v, 8_s and 8_c are an OPTIONAL observer organ for compatible 8-dimensional local/mesoscopic sections. They are not the universal carrier and are not inferred from a 16-dimensional state merely by dimension matching.

Any triality experiment must compare against an equal-budget ordinary observer and report transport/remainder explicitly.

## Frozen prediction

At equal observation and compute budget, if algebra-aware measurement contains useful information beyond alignment/transversality alone, then at least one non-binary d family will show a preregistered positive improvement in localization quality over all structure-agnostic matched controls, and that improvement will persist under allowed frame relabellings.

Primary effect: delta_recall_at_budget = recall_algebra - max(recall_matched_controls).

Promotion threshold: the lower 95% bootstrap confidence bound for delta_recall_at_budget must exceed +0.05 on at least two distinct d values, including at least one d > 3, with no preregistered frame-invariance failure.

This threshold is a research gate, not a universal effect-size theorem.

## Nulls and matched controls

Freeze before implementation:

1. random allocation at the same selected fraction q;
2. scalar local-energy/norm saliency using the same raw observations;
3. structure-agnostic random orthogonal features with the same retained dimension r;
4. alignment oracle/control exposing only the hidden-relation preservation statistic available to the experiment;
5. where Spin(8) is activated, an equal-rank non-triality orthogonal observer;
6. dense exact computation only at tiny sizes as a correctness oracle, never as the scalable baseline.

The alignment-only control is mandatory because R1T already showed that alignment/transversality, not field identity, explained its measured separation.

## Measurements

For each (d,N,k,r,B) record:

- recall@budget and precision@budget for independently planted/verifiable targets;
- compute-to-discovery;
- false-hotspot rate;
- peak memory;
- wall-clock time;
- retained-section count;
- frame-orbit spread;
- reconstruction/closure defect where an exact tiny-size oracle exists;
- typed unrepresented remainder [R]_observer.

Do not collapse the primary verdict to a weighted scalar.

## Scaling range

Stage A correctness: tiny carriers where dense exact checks are feasible.

Stage B discrimination: d in {2,3,4,5,7}, multiple N values, >= 8 deterministic seeds per point.

Stage C scaling: increase N until either the bounded-order method demonstrates sub-global memory growth over the tested range or the resource gate fails. No asymptotic complexity claim follows from finite scaling.

## Frame test

Every claimed object-level measurement must be classified as orbit-collapsed or orbit-resolving under its declared relabelling/frame group. Identity and at least one adversarial generator must always be included; purely random orbit sampling is insufficient.

## Kill conditions

The stronger hypothesis is killed for this round if any of the following holds:

- algebra-aware delta_recall_at_budget fails the promotion threshold;
- the gain disappears against the alignment-only control;
- a claimed invariant has frame-orbit spread above numerical tolerance without being explicitly typed orbit-resolving;
- memory requires materializing O(d^(2N)) global operator coordinates beyond tiny oracle sizes;
- performance gain is explained by a larger observation or compute budget;
- Spin(8)/triality adds no discriminator over its equal-rank control.

A killed Spin(8) subclaim does not kill the general polyqudit observer, and vice versa.

## Evidence policy

- P: exact algebraic identities only, with assumptions stated.
- A: imposed representation choices and finite surrogates.
- M: bounded runs with seeds, environment, controls and uncertainty.
- H: scalable localization/cognition-per-compute advantage.
- S: Polyqudit Worldlet and adaptive observer-organ interpretation.
- R: preserve every killed interpretation and its superseding evidence.

## Typed remainder

- [R]_carrier: physical realization/noise model outside the formal carrier.
- [R]_observer: structure not represented at bounded interaction order k and rank r.
- [R]_transport: information lost or changed under observer/frame transport.
- [R]_scaling: finite tested range versus asymptotic behavior.
- [R]_cognition: no cognitive-performance implication follows from localization alone.
- [R]_witness: self-generated results remain non-independent until separately reproduced.

## Stop rule

R1U ends after the frozen polyqudit observer, matched controls, frame audit and finite scaling report are executed. No hardware, consciousness, AGI, quantum-advantage, higher-cosmos, or universal Spin(8) claim may be added inside this round.