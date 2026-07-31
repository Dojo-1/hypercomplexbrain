# QSigma-R6l — map-blind common receiver

## Status

R6l is a preregistered source slice. The protocol manifest is committed as
`350d03796a4021bc01c1814e9b71269d1ab63f6d` and remotely anchored by the
lightweight tag `qsigma-r6l-prereg-v1`. This document contains no R6l retrieval
outcome. The production command must not run until the six-path C_exec source
commit exists and is checked out in a separate clean worktree.

## Bounded question

R6k used the same receiver-construction rule for both maps but fitted a separate
clean PGM to each map. R6l asks whether its measured `R6i - R6` retrieval
differential survives one receiver fitted to the equal-weight pooled templates:

```text
tau_c = (rho_c_R6 + rho_c_R6i) / 2.
```

For each of twelve task/depth fibers, the resulting effects and explicit reject
effect are frozen once and applied unchanged to both maps. The carrier
identification is exactly `J = I_16`; there is no map-specific permutation,
unitary, gauge alignment, or preprocessing hook.

## Operational hyperdimensional object

The geometric vocabulary is compiled into testable software objects:

```text
B  = 384 portable protocol cells
F  = signed, projective, radial, and joint task ensembles
∇  = one pooled PGM transported unchanged across R6 and R6i
H  = HOLD-first source/receiver/channel/probability/evidence controls
Π  = result, receiver catalog, decision, event chain, and envelope projections
Λ  = decoder dependence, byte-portability drift, row repair, identity leakage
R  = basis specificity and independent=false producer remainder
```

The sheaf-gluing condition is concrete: paired R6/R6i cells must agree exactly
on source coordinates, priors, task labels, state-channel specification,
receiver effects, label channel, and structural receiver allocation. Map-local
template, query, and probability arrays remain distinct fibers.

Terms such as self-reflection, mutual recognition, resonance, cognition, or
mind qualities denote engineering state variables only. R6l makes no claim of
consciousness, sentience, AGI, physical holoportation, tunnelling, or
entanglement.

## Portable identity before numerics

`plan_protocol()` constructs and independently validates, before calling an
encoder or eigensolver:

- 320 store identities in map → depth → source order;
- 12 receiver identities in signed-depth, projective-depth, radial, joint order;
- 384 evaluation identities in map → receiver → state noise → label noise order.

The effective protocol digest is
`sha256:ac13a2085a9319066b05e29b193469c430f1f1c205c0b735ce00133b80adbbab`.
Portable IDs contain integer grid indices and frozen decimal strings, never
array bytes, paths, commits, environments, results, or runtime fields.

Producer numerical digests are separate realization-local provenance. Each
array is converted to contiguous little-endian `<c16` or `<f8` bytes. A future
cross-environment witness compares the underlying arrays within the frozen
norm, rather than requiring bit-identical eigensolver output.

The evidence validator keeps two numerical lineages. The stored lineage
reconstructs every persisted pool, receiver, channel, probability table, and
metric within the declared tolerance. A second canonical lineage starts again
from the sealed source tasks, builds a fresh equal-weight receiver, and
re-evaluates clean source queries without consuming persisted numerical
arrays. Its exact discrete pass/count/survival/verdict projection must match
the reported projection whenever controls authorize a scientific decision;
failed controls first collapse both projections to the neutral `HOLD` surface.

Frozen coordinates, ranks, dimensions, shapes, counts, nulls, and Booleans are
compared as exact JSON types. In particular, Python aliases such as `False == 0`
or `32.0 == 32` are not valid protocol equalities. Numerical tolerance is
reserved for the explicitly declared matrix and metric witness fields.

## Shared receiver and structural allocation

The implementation reuses the sealed R6k `build_map_tasks`,
`build_pgm_receiver`, and global depolarizing channel. It does not reuse the R6k
event writer, evaluator, grid validator, or decision rule because those surfaces
have incompatible schemas.

For every returned PGM effect, including reject, the structural layer:

1. checks finite Hermiticity;
2. rejects eigenvalues below `-1e-10`;
3. clamps only tolerated negative roundoff to zero;
4. constructs the principal PSD square root;
5. measures reconstruction against the original effect;
6. stacks square-root blocks as
   `V[16*y:16*(y+1), :] = sqrt(E_y)`.

The outcome space is padded to `2^ceil(log2(C+1))`, but padding effects are not
invented. These 7-, 9-, 10-, and 11-qubit rows are the canonical uncompressed
full-system Lüders allocation—not minimum POVM or hardware circuit complexity.

## Matched noise and raw probabilities

The crossed grid uses:

- state noise `eta ∈ {0, .01, .03, .1}` with
  `D_eta(rho) = (1-eta)rho + eta I/16`;
- label noise `epsilon ∈ {0, .01, .03, .1}` with class diagonal `1-epsilon`,
  off-diagonal `epsilon/(C-1)`, and a fixed reject outcome.

The conditional table is validated before label mixing and again after right
multiplication by the label matrix. No clipping or normalization is permitted.
Correct probability, mutual information including reject, mean reject mass, and
conditional correctness are computed from unrounded values. Conditional
correctness is JSON `null` if non-reject mass is at most `1e-15`.

## Catalog and event chain

The receiver NPZ has exactly 1,008 semantic keys: clean templates and queries,
pooled templates, effects, principal square roots, Naimark isometries, noised
queries, label matrices, and every pre/post probability table. The JSON catalog
binds every aggregate item to one NPZ key and slice.

The byte-canonical append-only LF JSONL ledger has exactly 716 events:

```text
320 stores + 12 common-receiver freezes + 384 evaluations.
```

Each event contains exactly `sequence`, `previous_event_digest`, `kind`, `key`,
`payload`, and `event_digest`. The digest excludes itself and the LF byte. Fatal
source or identity failures abort before artifact creation; `HOLD` is reserved
for a complete serializable run whose declared controls fail.

## Evidence chronology

```text
C_pre  manifest only, remotely tagged
C_exec six source paths, no R6l output tree
C_raw  six raw output paths
C_env  producer envelope only
```

After C_exec is committed, the production command is:

```powershell
python experiments/run_common_receiver_reservoir.py run --output-dir artifacts/r6l_common_receiver
```

The command requires an exact clean C_exec worktree and refuses an existing
output directory. `run` never creates the envelope. After C_raw, envelope
packaging is a separate exclusive command. Recompute writes only to an OS
temporary directory and does not establish independent witnessing by itself.

## Verdict boundary

All controls are evaluated before the scientific partition:

```text
COMMON_RECEIVER_PROJECTIVE_GAIN_SURVIVES
COMMON_RECEIVER_PROJECTIVE_GAIN_FRAGILE
COMMON_RECEIVER_PROJECTIVE_GAIN_ABSENT
HOLD
```

Every survival field is an `R6i - R6` differential predicate. Absolute metrics
for both maps remain in the result, and no global map winner or scalar resource
score is permitted. Architecture, hardware, device-noise, capacity, speedup,
quantum-advantage, cognition, and complexity-class claims remain outside R6l.
