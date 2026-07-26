# S4-G100 — results

**Preregistered** at `manifests/s4_g100_preregistration.json`, commit `611e4ee`,
before the experiment produced a single primary number. The declared expectation
on record was a **negative result**.

> Six of ten gates fail. `HYP-S4-FERTILE_APERTURE` and `HYP-S4-ORDERED_FLOW` are
> retired. A negative result is a valid completion of this round.

## Held-out families — mean AUROC, 10 seeds each

None of these seeds or families was touched during development, except
`ring_small` which shares the tuning family's *spec* but not its seeds.

| family | E | β₁ | budget as % of search space | **C0** | C2 | C3 | **C4** | C5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ring_small | 13 | 5 | 23.44% | 0.642 | 0.627 | 0.670 | 0.660 | 0.615 |
| ring_medium | 24 | 9 | 0.13% | **0.683** | 0.551 | 0.511 | 0.625 | 0.604 |
| ring_large | 36 | 13 | 0.0006% | **0.627** | 0.562 | 0.494 | 0.527 | 0.563 |
| random_nerve | 20 | 9 | 0.42% | **0.740** | 0.661 | 0.578 | 0.708 | 0.648 |
| grid_nerve | 28 | 13 | 0.01% | 0.703 | 0.744 | 0.710 | **0.773** | 0.722 |

## The preregistered gates

| gate | threshold | observed | |
|---|---|---:|:--|
| `delta_auroc_vs_c0` | ≥ +0.03 | **−0.033** | FAIL |
| `delta_auroc_vs_best_control` | ≥ +0.02 | **−0.009** | FAIL |
| `delta_brier_vs_c0` | ≤ +0.005 | −0.012 | PASS |
| `mean_loop_defect` | ≤ 1e−10 | 8.9e−16 | PASS |
| `p99_loop_defect` | ≤ 1e−8 | 2.2e−15 | PASS |
| `instability` | ≤ 0.01 | **0.285** | FAIL |
| `wall_ratio` | ≤ 2.0× | **194×** | FAIL |
| `memory_ratio` | ≤ 1.5× | **86×** | FAIL |
| `seed_wins` | ≥ 8/10 | **20/50** | FAIL |
| `ordered_flow_margin` | ≥ +0.01 | +0.033 | PASS |

Deposit: **Conjecture [H]**. Effect region not dominated.

## Three findings, and they do not agree

### 1. The ordered-flow gate passes while the method loses

C4 beats `max(C3, C5)` by **+0.033**, clearing its preregistered +0.01 — and is
still **0.033 below** the deterministic baseline it exists to improve on.
Ordering recovers ground the chamber itself gave away; it adds none.

This is the clearest argument in the round for the dominance region. A weighted
score containing `ordered_flow_margin` could have passed the whole round on a
component that measures the chamber against *itself*. `RET-R3-SCALAR_PROMOTION`
retired exactly that failure mode, and the replacement caught it.

The caveat that cuts the other way: C4 and C5 carry **one more parameter** than
C3, and +0.033 is within what one parameter can buy. The margin is reported, not
believed.

### 2. The advantage is a budget-to-search-space artifact

The chamber wins only where 256 evaluations sample a large fraction of the
candidate space: `ring_small` at 23.4% sampled gives C4−C0 = **+0.018**;
`ring_large` at 0.0006% gives **−0.100**. `grid_nerve` is the exception
(+0.070 at 0.01%) and is not explained by coverage — recorded as unexplained
rather than smoothed into the trend.

Adaptivity has nothing to adapt to when sampling is near-exhaustive, and not
enough budget to matter when it is not. `EXP-S4-SCALE_DEPENDENCE`.

### 3. A control I nearly omitted changed the reading

The instability figure of 0.285 is meaningless without asking whether the
**baseline** is stable. It is not:

| attack | chamber worst \|Δ\| | **C0 worst \|Δ\|** |
|---|---:|---:|
| vertex relabel | 0.285 | 0.200 |
| alternate cycle basis | 0.210 | 0.086 |
| canonicalisation | 0.193 | 0.102 |
| edge permutation | 0.093 | 0.085 |
| **orthogonal gauge** | **0.000** | **0.000** |

So part of the instability is **inherited from the host**, not caused by the
chamber. The chamber is still worse on every axis, and there is a sharper
asymmetry in the signs: the chamber degrades in **one direction** under every
attack, while the baseline moves both ways. That is the signature of an apparent
advantage that exists only in one privileged representation.

Orthogonal gauge change leaves both **exactly** unchanged, which is P3 holding
numerically. It is the one invariance in this round that is real.

## The correction to a prior claim

That control exposed a defect in Round S3's headline measurement, so it was
chased rather than left open. `experiments/run_s4_basis_attack.py`, 300 trials on
S3's own instance family:

| instrument | as published | after relabelling | shift |
|---|---:|---:|---:|
| **sheaf** | 0.789 [0.776, 0.802] | **0.551** [0.526, 0.576] | **−0.238** |
| shuffled | 0.520 | 0.496 | −0.025 |
| graph | 0.515 | 0.496 | −0.020 |

The contrast the claim actually asserts:

| contrast | as published | after relabelling |
|---|---|---|
| sheaf − shuffled | +0.269 [+0.238, +0.298], d = 1.45 | **+0.055** [+0.019, +0.092], d = 0.24 |
| sheaf − graph | +0.274 [+0.246, +0.300], d = 1.63 | **+0.055** [+0.021, +0.090], d = 0.26 |

**Direction survives; 20% of the magnitude survives.** A fundamental cycle basis
is an arbitrary choice of spanning tree — short cycles concentrate blame, long
ones dilute it — and relabelling worldlets grows a different tree. The controls
barely move, so the instability is specific to the instrument that *uses* the
basis. That is exactly why Round S3 could not see it: the whole comparison ran
inside one basis.

`EXP-S3-SHEAF_LOCALISATION` is **superseded**, not retired, by
`EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT`. Its original text stays in the
ledger with a pointer forward.

## Other preregistered checks

- **Loop defects**: mean 8.9e−16, p99 2.2e−15, against gates of 1e−10 and 1e−8.
  The two edges declared exactly reversible are exactly reversible.
- **F7** (does an ordinary confidence margin do the aperture's job?): Spearman
  +0.47, +0.54, −0.36, −0.10, +0.27 across families. No consistent signal
  **either way** — F7 is neither met nor refuted, and is left open rather than
  resolved in the direction that would flatter the round.
- **Structured perturbation fields** (C6) vs **matched-spectrum surrogates**
  (C7): no separation survives; `HYP-S4-STRUCTURED_PERTURBATION` is unsupported.
- **Witness independence**: `correlated` on all four axes — code, assumptions,
  data, authoring model. No S4 deposit is independent verification, and the gate
  caps deposits accordingly rather than leaving it to a reader.
- **Resource parity fails honestly**: 194× wall and 86× memory. The baseline is
  nearly free, which makes the ratio harsh — but it was preregistered at 2.0×
  and 1.5× knowing that, and it stands.
