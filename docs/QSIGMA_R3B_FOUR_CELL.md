# QΣ-R3B-0 — Four-Cell Delayed Phase-Memory Calibration

**Status:** preregistered synthetic instrument calibration; no result is
asserted by this document.

**Frozen manifest:**
[`manifests/qsigma_r3b_four_cell_calibration_preregistration.json`](../manifests/qsigma_r3b_four_cell_calibration_preregistration.json)

**Preregistration commit:**
`aa2bf291d8733161b66fe317b4dd812db7800020`

The manifest was committed before any result runner was executed. Its phases,
seeds, frames, margins, uncertainty procedure, controls, and stop conditions
are therefore fixed before observing an output. Method scaffolding may be
implemented after the freeze, but an implementation must conform to this
contract rather than revise the contract around its result.

R3B-0 is a positive-control calibration of a four-role measurement instrument.
It compares a coherent identity-memory channel with complete
computational-basis dephasing under a matched, one-copy protocol. The
registered decision is **HOLD**, even if the observed positive-control
coordinates separate cleanly.

## The four cells

The instrument is the ordered composition

```text
SELF -> OTHER -> MEMORY -> AUDITOR.
```

Each cell has one typed responsibility:

| Cell | Frozen operator | Role in the instrument |
|---|---|---|
| `SELF` | `|psi_phi> = (|0> + exp(i phi)|1>)/sqrt(2)` | Prepare the equatorial reference state. |
| `OTHER` | `r in {same, orthogonal}`; `orthogonal` sends `phi -> phi + pi` | Select the relation to the reference without changing the protocol width. |
| `MEMORY` | target `I(rho)=rho`; control `D_z(rho)=P0 rho P0 + P1 rho P1` | Preserve phase coherence in the target arm or remove it completely in the matched control arm. |
| `AUDITOR` | `{Pi_phi, I-Pi_phi}`, where `Pi_phi=|psi_phi><psi_phi|`; a click predicts `same` | Read the relation with one fixed reference-relative two-outcome POVM. |

All four cells are required. Removing any one is not an alternative
implementation of the same test; it must produce a typed refusal or `HOLD`.

Writing

```text
P0 = |0><0|,
P1 = |1><1|,
rho_phi = |psi_phi><psi_phi|,
```

the frozen analytic contract is

```text
Tr(Pi_phi I(rho_phi))              = 1
Tr(Pi_phi I(rho_(phi+pi)))         = 0
Tr(Pi_phi D_z(rho_phi))            = 1/2
Tr(Pi_phi D_z(rho_(phi+pi)))       = 1/2.
```

Thus the identity channel retains the same/orthogonal phase relation, while
complete dephasing removes the information used by this particular auditor.
This is an analytic positive control for the instrument, not a comparison
with an optimized classical strategy and not an advantage result.

Every accepted state and channel output must be a `2 x 2` Hermitian,
positive-semidefinite, trace-one density matrix. Every POVM element must obey
the corresponding operator contract.

## Common-frame covariance

The registered frames are

```text
I, H, S, H@S.
```

A valid common-frame trial transports the complete local experiment. For a
registered unitary `U`, this means transporting

```text
rho              -> U rho U†
Pj               -> U Pj U†             for j in {0,1}
|psi_phi>         -> U |psi_phi>
Pi_phi            -> U Pi_phi U†.
```

The dephasing basis, state, reference, and POVM therefore move covariantly.
The four analytic click probabilities must remain unchanged.

Applying a frame to only the state or only the POVM is an adversarial
**basis attack**, not another valid chart of the same trial. The instrument
must detect that mismatch rather than average it into the baseline.

## Exact frozen schedule

The calibration phases are

```text
0, pi/2, pi, 3*pi/2.
```

The disjoint held-out phases are

```text
pi/4, 3*pi/4, 5*pi/4, 7*pi/4.
```

Each seed crosses:

```text
8 phases
x 2 relations
x 4 common frames
x 8 repetitions
= 512 trials per arm.
```

The metric partitions are exact:

| Partition | Factor cells | Trials per arm per seed |
|---|---:|---:|
| Calibration accuracy | 4 calibration phases × 2 relations × identity frame × 8 repetitions | 64 |
| Held-out generalization | 4 held-out phases × 2 relations × identity frame × 8 repetitions | 64 |
| Common-frame robustness | 8 phases × 2 relations × 3 non-identity frames × 8 repetitions | 384 |
| Calibration utility | All registered factors | 512 |

The seeds are the consecutive integers `73001` through `73032`. Target and
control use the same factor schedule and the same common uniform variates
within each seed. Both arms have:

```text
copies per trial       = 1
memory calls per trial = 1
POVM outcomes          = 2
side registers         = 0.
```

These are parity constraints. They prevent one arm from receiving a wider
operational protocol; they are not measurements of energy, latency, or sample
efficiency.

## Vector outcome and observation mask

The fixed outcome coordinate order is

```text
Y = (
  accuracy,
  generalization,
  robustness,
  sample_efficiency,
  calibration,
  neg_energy,
  neg_latency,
  recovery
).
```

Only four coordinates are measured:

```text
observed mask = (
  true,   # accuracy
  true,   # generalization
  true,   # robustness
  false,  # sample_efficiency
  true,   # calibration
  false,  # neg_energy
  false,  # neg_latency
  false   # recovery
).
```

Their frozen meanings are:

- `accuracy`: balanced correct-decision rate on calibration phases in the
  identity frame;
- `generalization`: balanced correct-decision rate on the disjoint held-out
  phases in the identity frame;
- `robustness`: balanced correct-decision rate over all phases under `H`, `S`,
  and `H@S`;
- `calibration`: mean proper Brier utility
  `1-(p_correct-observed_correct)^2` over all 512 trials.

The other four coordinates are genuinely absent:

- no learning curve or sample-to-threshold experiment measures
  `sample_efficiency`;
- operation-count parity is not an energy measurement, so `neg_energy` is
  missing;
- protocol-depth parity is not a latency measurement, so `neg_latency` is
  missing;
- no interruption-and-recovery intervention measures `recovery`.

Missing values are encoded as `NaN` together with the explicit mask. They may
not be imputed, replaced by parity counters, scalarized, or silently treated as
passing. Converting the eight-coordinate outcome to a scalar is a typed
refusal.

## Paired seed-cluster uncertainty

The experimental unit for uncertainty is the **seed cluster**, not an
individual shot. For seed `s`, the paired effect is

```text
Delta Y_s = Y_target,s - Y_control,s.
```

Target and control records stay paired because they share the factor schedule
and uniform variates. One bootstrap draw samples the 32 seed-cluster indices
with replacement and carries every coordinate of each selected
`Delta Y_s` together. This preserves:

- target/control pairing within a seed;
- dependence among the observed outcome coordinates;
- the registered missing-value mask;
- the seed as the uncertainty unit.

The frozen procedure uses:

```text
bootstrap draws        = 20,000
bootstrap seed         = 314159
promotion sampling seed = 271828
interval               = percentile 99% per observed coordinate.
```

Reporting 16,384 trials per arm across all seeds does not turn the run into
16,384 independent experimental units. There are 32 synthetic replication
clusters, and they are not independent laboratories or real-world samples.

## Advantage cone and mandatory HOLD

The preregistered cone is `K_R3B0_CALIBRATION`, with coordinate constraints:

| Coordinate | Constraint | Margin or tolerance |
|---|---|---:|
| `accuracy` | improve | `0.20` |
| `generalization` | improve | `0.20` |
| `robustness` | improve | `0.20` |
| `sample_efficiency` | no worse | `0.02` |
| `calibration` | improve | `0.10` |
| `neg_energy` | no worse | `0.02` |
| `neg_latency` | no worse | `0.02` |
| `recovery` | no worse | `0.02` |

The posterior cone gate uses `alpha = 0.01`, so its probability threshold is
`0.99`. That probability is only one gate. Promotion additionally requires
audit strength at least `1.0`, compute parity, and no violated safety or
resource constraint.

R3B-0 freezes:

```text
audit strength    = 0.0
registered outcome = HOLD.
```

The final decision therefore remains `HOLD` for three independent reasons:

1. four cone-constrained coordinates are unmeasured;
2. audit strength is zero;
3. the round is calibration-only.

A constrained missing coordinate blocks promotion even when every observed
coordinate exceeds its margin. A positive-control cone probability may be
reported as instrument telemetry, but it cannot override the registered
decision.

The implementation must also leave the retired `q_causal` scalar untouched.
No R3B value may be written into it, and no vector result may be promoted
through it.

## Registered controls

The manifest freezes thirteen controls:

1. density, channel-output, and POVM validity;
2. the exact analytic probabilities `1`, `0`, `1/2`, and `1/2`;
3. disjoint calibration and held-out phase sets;
4. common-frame covariance;
5. arm parity for copies, calls, outcomes, schedule, and random variates;
6. deterministic replay for every seed;
7. typed refusal or `HOLD` under each single-role ablation;
8. detection of an untransported-POVM basis attack;
9. refusal to scalarize the outcome vector;
10. joint resampling of paired seed clusters;
11. promotion blocking on any constrained missing coordinate;
12. no write or promotion through `q_causal`;
13. reporting a positive-control cone probability without changing the final
    `HOLD`.

Changing a phase, seed, frame, margin, alpha, sample count, or control after
inspecting an output kills the registered run. So does unequal arm resourcing,
imputation, a failed covariance/basis-attack control, or language that upgrades
calibration into an advantage claim.

## Evidence ceiling and explicit non-claims

The strongest evidence permitted by this slice is:

> Under the frozen synthetic schedule, the repository-internal implementation
> reproduces the registered analytic identities and emits paired,
> seed-clustered calibration measurements with an explicit four-of-eight
> observation mask.

Even a perfectly matching run does **not** establish:

- quantum advantage or a separation from an optimized classical protocol;
- causal advantage or a causal intervention on an external system;
- cognitive ability, memory superiority on real data, consciousness,
  sentience, AGI, or mutual recognition in a person;
- physical quantum memory, quantum hardware performance, energy use, or
  latency;
- statistical independence across laboratories;
- external or independent reproduction;
- a result about `P=NP`, `P!=NP`, or any Millennium Prize problem.

The words `SELF`, `OTHER`, `MEMORY`, and `AUDITOR` are typed engineering roles
inside this instrument. They are not claims that the software is a subject or
possesses a mind.

## Verification and publication boundary

From the repository worktree, validate the frozen manifest and implementation
without generating a result:

```powershell
python -m json.tool `
  manifests/qsigma_r3b_four_cell_calibration_preregistration.json *> $null

$env:PYTHONPATH = "src"
python -m pytest tests/test_four_cell.py -q
```

Run the broader regression suite before accepting a producer commit:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```

The result runner is a later publication step. It may be invoked only after
the manifest, source, tests, runner, and this document are committed together
as a clean producer state, and only in a copy without a pre-existing result
artifact:

```powershell
$env:PYTHONPATH = "src"
python experiments/run_four_cell_calibration.py
```

The runner enforces both conditions: every producer input must exist at `HEAD`,
the entire worktree must be clean immediately before computation and again
before writing, and existing result/envelope paths are never overwritten. This
prevents a dirty filesystem implementation from borrowing the producer
commit's identity.

After generation, verify all repository evidence envelopes:

```powershell
$env:PYTHONPATH = "src"
python -m aionq.verify_envelopes artifacts
```

Publication follows a two-commit boundary:

1. the producer commit contains the frozen manifest, implementation, tests,
   runner, and documentation;
2. a second artifact-only commit contains
   `artifacts/r3b_four_cell/four_cell_calibration.json` and its evidence
   envelope, each bound to the producer commit.

Only explicitly named repository files may be hashed or staged. Local
Downloads, Codex attachments, credentials, personal documents, and unrelated
media remain outside the evidence and Git boundary.

(c) Jesús Vilela Jato, all rights reserved. 21/05/2026
