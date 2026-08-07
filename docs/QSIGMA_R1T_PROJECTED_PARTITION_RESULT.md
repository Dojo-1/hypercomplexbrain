# QSigma-R1T — Coherent partitions of a projected Simon superposition

**Status:** MEASURED / self-attested.  No independent witness.

**Frozen preregistration:** `f5a98eb3c05f048f230b643b49c31916e188d1b4`

**Implementation head used for the bounded run:** `cf38347c53fa7f3350f55d185efc67097f44de0e`

**Raw artifact commit:** `4316c14912d75c1375b454650197f72acc1d11b9`

This round was frozen before implementation.  It tests one finite claim only: after projecting an exact Simon coset-entangled substrate onto a 16-amplitude wavefunction, coherent support partitions reveal whether the partition respects or cuts the hidden translation pairs.  It does **not** test quantum speedup, circuit advantage, arbitrary manifolds, or the wider Hypercomplex Brain ontology.

## Object

Fix `n=4`, hidden translation `s=1`, and the exact substrate

\[
|\Psi_s\rangle = \frac14\sum_{x\in\mathbb F_2^4}|x\rangle|[x]_s\rangle,
\qquad [x]_s=\{x,x\oplus s\}.
\]

For each of eight deterministic complex quotient-register projection vectors, project the second register and renormalize:

\[
|\psi_\chi\rangle = \Pi_\chi |\Psi_s\rangle.
\]

The projection construction preserves the Simon pair equality

\[
\psi_\chi(x)=\psi_\chi(x\oplus s).
\]

A four-cell, four-label partition `P={C_alpha}` is kept coherent.  Each sector is support-restricted,

\[
|\psi_\alpha\rangle=P_\alpha|\psi_\chi\rangle,
\]

Walsh-transformed separately, and then accounted for with both diagonal sector power and off-diagonal sector interference.

The forbidden Simon subspace is

\[
\{y:y\cdot s=1\}.
\]

The primary quantities are

\[
L_{global}=\sum_{y\cdot s=1}|W\psi(y)|^2,
\]

\[
L_{sector}=\sum_\alpha\sum_{y\cdot s=1}|W\psi_\alpha(y)|^2,
\]

and the off-diagonal forbidden interference

\[
I_{off}=\sum_{\alpha\ne\beta}\sum_{y\cdot s=1}
W\psi_\alpha(y)\overline{W\psi_\beta(y)}.
\]

The closure check is

\[
L_{global}=L_{sector}+\operatorname{Re}I_{off}.
\]

## Frozen controls

All controls have exactly four cells of four labels and receive the same projected state.

- **FIELD-ALIGNED** — additive GF(4) cosets whose subspace contains `s`.
- **ALIGNED-RANDOM** — random non-field partitions built from complete `{x,x XOR s}` pairs.
- **FIELD-TRANSVERSE** — the four other GF(4)-scaled two-dimensional additive subspaces, none containing `s`.
- **TRANSVERSE-RANDOM** — random partitions forced to split every hidden pair.
- **RELABELLED-FIELD** — random relabellings of the aligned field partition while state and secret remain fixed.

The field partitions are generated from the repository's existing `gf16_mul`; no expected measurement is hard-coded into their construction.

## Execution

Local bounded execution used Python 3.13.5 / NumPy 2.3.5 on Linux.

Focused regression harness:

```text
4 passed in 0.06s
```

Eight projection seeds and eight stochastic control seeds produced 232 raw observations.

Projection gate:

```text
max explicit-vs-direct projection defect = 0
max hidden-pair symmetry defect           = 0
```

All preregistered numerical gates passed.

## Result

| family | n | pair-cut range | median sector forbidden mass | median off-diagonal forbidden interference | max closure defect |
|---|---:|---:|---:|---:|---:|
| FIELD-ALIGNED | 8 | 0 | 0 | 0 | 0 |
| ALIGNED-RANDOM | 64 | 0 | 0 | 0 | 0 |
| FIELD-TRANSVERSE | 32 | 1 | 0.5 | -0.5 | 1.67e-16 |
| TRANSVERSE-RANDOM | 64 | 1 | 0.5 | -0.5 | 1.67e-16 |
| RELABELLED-FIELD | 64 | 0.375–1 | 0.4417495 | -0.4417495 | 1.11e-16 |

For every row,

\[
L_{global}=0
\]

within the recorded arithmetic tolerance; in this run it is numerically exactly zero.

The fully aligned partitions preserve the Simon constraint **inside every coherent sector**:

\[
L_{sector}=0.
\]

This is true for both the GF(4)-derived partition and the matched random aligned partitions.  Therefore the experiment provides no field-specific advantage.

The fully transverse partitions destroy the constraint sector-wise:

\[
L_{sector}=\frac12,
\]

but the global Simon constraint is reconstructed entirely by cross-sector interference:

\[
\operatorname{Re}I_{off}=-\frac12,
\qquad
L_{global}=\frac12-\frac12=0.
\]

This occurs for both field-derived transverse partitions and forced-transverse random partitions.

The relabelling attack gives the useful intermediate case.  Once the original field partition is relabelled while `s` and the state are fixed, hidden-pair cut fraction ranges from `0.375` to `1.0` and sector forbidden mass ranges from `0.1281979` to `0.5`.  The interference term cancels it row by row.  Because the projected pair amplitudes are nonuniform, unweighted pair-cut fraction is not by itself a complete predictor of leakage; amplitude carried by the cut pairs matters.  This is an interpretation of the measured rows, not a newly preregistered scalar law.

## Strongest surviving claim

**M / self-attested:** on this exact 16-state projected Simon testbed, coherent sector-resolved Walsh interference distinguishes partitions that preserve hidden translation pairs from partitions that split them.  A global Simon constraint can be absent from every transverse sector separately and exist only in the off-diagonal interference between sectors.

That is the finite experimental content of the round.

## What did not survive as a stronger interpretation

The field geometry is **not** the cause of zero leakage.  `FIELD-ALIGNED` and `ALIGNED-RANDOM` are identical on the preregistered signal.  Likewise, `FIELD-TRANSVERSE` and `TRANSVERSE-RANDOM` both give the same `0.5/-0.5` decomposition when every hidden pair is split.

Accordingly, the data support **alignment/transversality to the hidden translation**, not “GF(16) geometry is better”.  The field structure supplied a principled family containing both aligned and transverse members; it did not earn a performance promotion.

## CI status: inherited obstruction, not R1T evidence

GitHub Actions ran for the branch, but the matrix does not reach the correctness suite.  Installation succeeds and the workflow fails at its existing package-import step; all subsequent correctness tests are skipped.

This same failure is present on the branch base commit `a090939cb72519d2b0af49fafc4e772d71740f56`, before any R1T file existed.  Therefore it is recorded as an inherited CI/package-import obstruction and is outside this frozen round.  No cross-platform reproduction claim is made.

R1T does not patch the workflow or package import, because doing so after seeing the experimental result would mix unrelated repair work into the preregistered object.

## Evidence ledger

- **P relative to the finite code object:** support partitions are disjoint/exhaustive; Walsh transform and interference accounting are exact definitions in the implementation.
- **M:** the 232 recorded finite observations and focused local test execution.
- **H -> M, narrowly:** sector-resolved forbidden mass tracks whether hidden pairs are preserved versus fully split on the preregistered controls.
- **R / forbidden:** any field-specific superiority interpretation from this round.
- **Not independently witnessed:** producer and verifier remain the same GPT development line.

## Typed remainder

- `[R]_projection` — the projection is an exact selected bra; physical postselection cost/noise is not modeled.
- `[R]_partition` — only finite 16-label combinatorial partitions are tested.
- `[R]_measurement` — sector labels remain coherent; explicit decohering measurement is outside scope.
- `[R]_witness` — no independent recomputation.
- `[R]_CI-import` — repository-wide package import currently prevents the matrix correctness suite from running and predates R1T.

## Stop rule

The preregistered R1T object is complete.  No hyper-Walsh, sheaf, adiabatic, holoportation, higher-cosmos, or hardware lift is added inside this round.  Any such extension requires a new preregistration with its own nulls and kill conditions.
