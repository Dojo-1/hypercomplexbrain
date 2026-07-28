# S8 algebra-valued Fano decoder

## Outcome

The preregistered local decoder slice passed its four primary gates and the two
executed attack checks recorded in the artifact.  The result is narrower than a
communications receiver: it establishes identifiability in an explicit
linearized `so(8)` observation model.

Preregistration: `manifests/s8_algebra_decoder_preregistration.json`  
Implementation: `src/aionq/fano_decoder.py`  
Experiment: `experiments/run_fano_decoder.py`  
Artifact: `artifacts/s8_decoder/fano_decoder.json`  
Tests: `tests/test_fano_decoder.py`

The preregistration was committed as `bbe1ac4` before the implementation was
executed.

## The carrier is algebra-valued

For an `8 x 8` real skew-symmetric matrix `A`, define

```text
vec_so8(A)[i,j] = sqrt(2) A[i,j],  i < j.
```

This gives 28 coordinates and preserves the Frobenius inner product:

```text
vec_so8(A) · vec_so8(B) = trace(A^T B).
```

The observation is therefore the whole Lie-algebra element, not its norm.
Seven normalized channel generators form `S in R^(28x7)`.  Their twenty-one
normalized pairwise commutators form `C in R^(28x21)`.  The tested model is

```text
y = S a + C b + epsilon.
```

The decoder is the Moore-Penrose least-squares inverse of `B = [S C]`.

## Preregistered measurements

| Gate | Measurement | Result |
|---|---:|---|
| signal rank | `rank(S)` | `7` |
| crosstalk rank | `rank(C)` | `21` |
| joint rank | `rank([S C])` | `28` |
| signal/crosstalk overlap | `max abs(S^T C)` | `4.2283e-17` (numerical) |
| joint condition number | `cond([S C])` | `2.44949` |
| noiseless recovery | max coefficient error, 256 samples | `1.1657e-14` |
| rank-deficient control | ranks `(S,C,[S C])` | `(5,10,15)` |
| rank-deficient control | unit coefficient alias observation distance | `3.2756e-16` |

At coordinate-noise levels `1e-4`, `1e-3`, `1e-2`, and `1e-1`, the empirical
combined coefficient RMSE was `1.001019` times the analytic least-squares
prediction at every level.  The repeated ratio is expected because the same
preregistered standard-noise draw was scaled across levels.

The preregistered random-support control used 1,000 systems at seed `20260727`.
It is matched only on selecting seven distinct 3-subsets; it is **not**
conditioned on signal rank.  Persisting the joint contingency exposes the
confound:

| `rank(S)` | `rank(C)` | count |
|---:|---:|---:|
| 5 | 10 | 32 |
| 6 | 15 | 479 |
| 7 | 21 | 489 |

Across all 1,000 sampled controls,

```text
rank(C) = choose(rank(S), 2)
rank([S C]) = rank(S) + rank(C)
```

had zero observed mismatches.  Consequently the `489/1000` full-crosstalk-rank
count is exactly the `489/1000` full-signal-rank count.  It does **not**
demonstrate that Fano uniquely “buys” 21 crosstalk modes.  The Fano basis itself
still passes the preregistered `7/21/28` identifiability gate; the correction is
to the comparative interpretation of the relaxed control.

### Post-hoc conditioning observation

Conditioning was inspected after seeing that rank was confounded, so it is
labelled `POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED` in the artifact and is not a
new primary result.  Among the 489 full-rank random-support controls, joint
condition numbers had minimum/median/maximum
`7.41903 / 29.1602 / 43.1467`; none was at or below the Fano value `2.44949`.
This sampled conditioning separation is the design-specific difference visible
here, but it requires a separately preregistered replication before promotion.

## What the rank means

For Fano, all 28 local coefficients are identifiable under the declared linear
model.  Signal and crosstalk can also be decoded separately because the measured
cross Gram passes the numerical orthogonality gate.  No symbolic proof of exact
orthogonality is claimed by this floating-point experiment.

The rank-deficient control supplies the adversarial counterpart.  Its
signal rank also falls from 7 to 5 while crosstalk rank falls from 21 to 10.
It therefore demonstrates a genuine coefficient alias, but not an isolated
crosstalk defect in an otherwise matched signal system.  Its crosstalk matrix
has a nonzero null vector `n`, so

```text
C b = C (b + n)
```

for two coefficient vectors one unit apart.

The scalar-collapse attack is separate: it now compares two **raw,
unnormalized** Fano commutators, identifies their channel pairs, reproduces the
legacy norm `16/9 = 1.777...`, and records their nonzero 28-coordinate distance.
Equal norms are therefore not an artefact of normalizing every decoder column
to unit length.

## Boundaries

This slice does **not** establish:

- recovery from an ordered finite-angle noncommutative group product;
- bit/symbol error rate, bandwidth, channel capacity, or hardware performance;
- superiority over a matched Walsh-Hadamard receiver;
- a split-signature `(2,2)` result—`SU(1,1)` needs a separately bounded
  observation and noise model;
- quantum advantage;
- consciousness, sentience, AGI, or “best cognitive performance.”

The result is a compact, testable piece of linear algebra: a well-conditioned
`7 + 21 = 28` coordinate system in the chosen compact `so(8)` representation.
The artifact also records Python, NumPy, and the NumPy bit generator because
exact seeded random-control counts are runtime-version context, not timeless
constants.

## Reproduce

```powershell
python -m pytest tests/test_fano_decoder.py -q
python experiments/run_fano_decoder.py
```

The experiment exits nonzero if any preregistered gate fails and writes JSON
with `allow_nan=False`, so invalid numerical values cannot silently enter the
artifact.
