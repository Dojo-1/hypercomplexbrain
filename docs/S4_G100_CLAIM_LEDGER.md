# S4-G100 — claim ledger

Extends `aionq.governance`; no parallel ledger exists. Ledger went 48 → 65 claims.

## P — proved or definitionally closed

| id | statement | rests on |
|---|---|---|
| `DEF-S4-LOOP_DEFECT` | the round-trip defect is a **TransportDefect**: nonnegative, typed with carrier and comparison, raw before clipping. Not a cohomology class, not a semantic remainder, not a scalar obstruction constant | type system + `loop_tomography.py` |
| `MATH-S4-LOOP_ZERO` | an exact left inverse gives **exactly** 0 | exact numerical checks; Lean statement present, **uncompiled** |
| `MATH-S4-GAUGE_INVARIANCE` | invariant under conjugation by an isometry | verified to 1e−12 on a deliberately lossy probe; chamber output bit-identical under orthogonal gauge |
| `MODEL-S4-BORDON_CEILING` | indefinite invariant survival requires `d ≤ ρ` | a consequence **inside the constant-rate model**, not a measurement |
| `MATH-S4-NO_SELF_PROMOTION` | authorisation from inside the generating closure is not authorisation | enforced before any numeric gate is read |

Each P claim records in its `assumptions` that the Lean file is uncompiled. They
are P because the mathematics is definitional, **not** because a proof assistant
agreed. No Lean, `lake` or `elan` exists in this environment.

## M — measured

| id | statement | n | interval |
|---|---|---:|---|
| `EXP-S4-CHAMBER_KILLED` | chamber is worse than the deterministic baseline on held-out families; 6/10 gates fail | 50 | −0.033 pooled |
| `EXP-S4-SCALE_DEPENDENCE` | the advantage tracks budget-to-search-space ratio, not adaptivity | 50 | [−0.100, +0.018] |
| `EXP-S4-ORDERED_FLOW_MARGIN` | the ordering gate passes (+0.033) while the method loses | 50 | +0.033 |
| `EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT` | S3's contrast survives relabelling in direction, retains 20% of magnitude | 300 | [+0.019, +0.092] |

All four carry the same limitation: **witnesses are correlated** — explorer,
verifier and auditor share code, assumptions, data and authoring model. These are
measured patterns, not independent verification.

## H — hypotheses that remain open

`HYP-S4-STRUCTURED_PERTURBATION` is unsupported but not killed: C6 vs C7 showed
no separation, and no separation is not a demonstrated absence at this n.
`BRIDGE-S3-COHERENT_ORACLE`, `BRIDGE-R3-QCAUSAL`, `BRIDGE-R1-RANK_ROBUSTNESS`,
`MODEL-R4-BORDON` carry forward unchanged.

## S — semantic handles, load-bearing nowhere

`SEM-S4-EMPEROR`, `SEM-S4-EMPRESS`, `SEM-S4-NEST`. Each names the operator it
denotes and nothing more.

## R — retired this round

| id | retired claim | why |
|---|---|---|
| `RET-S4-FERTILE_APERTURE` | an adaptive aperture reveals structure a static ensemble does not | killed on F1: C2 matches or beats it on 4 of 5 families; also fails against its matched random-walk ablation |
| `RET-S4-ORDERED_FLOW` | explore-then-verify improves localisation | the gate passes while the method loses 0.033 to the baseline; the +0.033 margin is within what its one extra parameter buys |
| `RET-S4-OPTIMAL_COGNITION` | the architecture is already optimal / improves cognition | retired **pre-emptively at the start of the round** and never supported |
| `RET-S4-CHAMBER_INVARIANT` | the chamber's belief is intrinsic to the sheaf | demoted to a representation-sensitive diagnostic: 0.285 under relabelling, 0.210 under alternate basis |

## Superseded, not overwritten

`EXP-S3-SHEAF_LOCALISATION` → `EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT`.

The original statement stays in the ledger verbatim with a forward pointer. It
was not edited to match the newer number, because that would destroy the record
of what was claimed and when. This is the Atlas artifact contract: *a corrected
object receives a new version, not an overwritten history.*

## What no S4 claim asserts

No claim here asserts intelligence, consciousness, quantum advantage, asymptotic
computational advantage, hypercomplex superiority, optimality, or any connection
between a coordinate and cognitive performance. The chamber loses to a closed-form
baseline on its own host under matched budgets, and that is the result.
