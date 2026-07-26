# S4-G100 — Reversible Recognition Chamber: specification

**Evidence floor: H.** Nothing here is a claim about intelligence, consciousness,
quantum advantage or asymptotic speedup.

## The question

> Can a controlled aperture plus ordered exploratory/verification operations
> reveal useful hidden structure beyond deterministic, static-ensemble and
> equal-entropy stochastic controls, while preserving round-trip and gauge
> stability under matched resource budgets?

Host: the surviving S3 real/matrix sheaf environment. Task: localise hidden
defective overlaps from cycle holonomy alone, where **no overlap is locally
anomalous** — the sheaf is built as an exact coboundary and the defect swaps a
transition for another from the same distribution, so only the loop reveals it.

## Governing constraints carried forward

| constraint | source |
|---|---|
| hypercomplex coordinates are not automatically superior | `RET-S3-HYPERCOMPLEX_DIAGNOSIS` |
| no octonionic flat-sheaf construction | `RET-S3-OCTONIONIC_SHEAF` |
| promotion is a region, never a weighted scalar | `RET-R3-SCALAR_PROMOTION` |
| a dimension-matched real representation stays the control | S3 |
| every `[R]` is typed | Manifold Atlas formal queue |

The primary representation is `real_matrix`. The manifest validator **refuses**
an octonionic or sedenion regime in a flat-sheaf role, so the S3 finding is a
structural constraint rather than a note.

## Semantic handles and what they denote

| handle | operator | tier |
|---|---|---|
| Emperor | `roles.Explorer` — proposes, cannot promote | S |
| Empress | `roles.Verifier` — six-component tuple, no final truth | S |
| Nest | `nest.nest_decision` — preregistered region, dominance | S |
| Bordón | `budget.BordonBudget` over `aionq.bordon` | P inside the model |
| Bunny / UTAI | `formal/` theorem targets — **not compiled** | — |

## The object

**Worldlets** keep their own carriers; they are not coerced into one coordinate
system. Four roles, four genuinely distinct geometries:

| worldlet | role | carrier | geometry |
|---|---|---|---|
| `W_evidence` | local evidence carrier | orthogonal transitions | `orthogonal_group_frobenius` |
| `W_memory` | candidate memory | `F_2^E` supports | `hamming_f2` |
| `W_explore` | exploratory | aperture box | `bounded_box_l1` |
| `W_audit` | auditor | evidence lattice | `discrete_partial_order` |

**Tendrils** are typed and bidirectional. Six of them; each declares
preserved / transformed / lost and carries a typed remainder. Two are declared
exactly reversible (`T_evidence_to_audit`, the invariant channel; and
`T_explore_to_evidence`, the orthogonal gauge) and both measure loop defect
`0.0` exactly. A tendril with no return map must state why, or construction
fails.

**Three clocks** at different rates: `fast_candidate` (1), `meso_consolidation`
(4), `slow_evidence` (16). The slow clock is funded from the invariant channel
and is never throttled.

**Two hyperedges**, each joining three worldlets: `H_deposit_gate` (a deposit
needs candidate + evidence + external witness; no pair suffices) and
`H_aperture_update` (dispersion and explained fraction jointly; either alone is
noise).

## The aperture

Three dials, never one "openness" scalar: `tau` unresolved lifetime, `kappa`
branch width, `beta` crystallisation barrier — with declared bounds and per-change
provenance. Three controllers as mutual ablations: `Fixed`, `Random` (matched
walk, ignores every signal), `Adaptive`.

## Resource model

Invariant channel (provenance, identity continuity, correction history, audit
logging, raw evidence) is the bordón; speculative channel (candidate generation,
alternate frames, sweeps) is the puntero. Throttle order is fixed: narrow branch
width → shorten lifetimes → **preserve evidence** → record the intervention. No
code path reduces the invariant draw; that is the structural form of "never
sacrificed", and `invariant_draw ≤ refill_rate` is enforced by the validator.

## The five conditions on one code path

`C0` deterministic · `C2` static ensemble · `C3` adaptive unordered ·
`C4` explore→verify · `C5` verify→explore. They differ only in three switches:
which controller is installed, whether the explorer sees the verifier's belief,
and the order of the two roles. If each had its own loop a difference would be
unattributable.

## Two defects found during development, recorded not smoothed

1. **Absorbing state.** Feeding the raw belief back as the proposal distribution
   makes zero absorbing. The first run collapsed onto five overlaps with all
   three true defects at probability exactly 0 — AUROC 0.250, *below chance*.
   Fixed with a declared exploration floor, counted as a parameter. C4/C5
   therefore carry **one more parameter** than C2/C3, and that is reported.
2. **Under-identifying objective.** The verifier first scored candidates by
   uncovered obstruction mass — a set cover, under which any small set meeting
   every basis cycle scores perfectly. It discards the strongest signal: a
   low-mass cycle *exonerates* its overlaps. Replaced with a non-negative
   least-squares fit.

Both were found before preregistration, which is the legitimate window.

## Reproduction

```
PYTHONPATH=src python3 -m pytest tests/ -q                    # 193 tests
PYTHONPATH=src python3 experiments/run_s4_g100.py             # primary, ~105 s
PYTHONPATH=src python3 experiments/run_s4_g100.py --quick     # 3 seeds, ~32 s
PYTHONPATH=src python3 experiments/run_s4_basis_attack.py     # S3 basis attack
PYTHONPATH=src python3 -c "from aionq.recognition import *; \
  print(validate_manifest(load_manifest('manifests/s4_g100_architecture.json')))"
```
