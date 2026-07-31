# QSigma-R6k — equal-resource hyperbolic associative retrieval

## Result

The append-once experiment returned:

```text
ANISOTROPIC_ANGULAR_GAIN_NO_RADIAL_GAIN
```

This is a differential statement about `R6i - R6` on one deterministic
finite-grid associative-retrieval protocol. It means:

- R6i clears the frozen gain threshold on the signed angular task at all five
  depths and all four depolarizing strengths;
- R6i clears it on the genuine `M ~ -M` projective task at four of five depths
  for every noise strength;
- R6i clears it on the joint depth × projective-angle task;
- R6i does not clear the radial differential threshold.

It does **not** mean the radial coordinate disappears. Both maps have identical
clean five-class radial PGM accuracy to numerical precision:

```text
R6   0.24046398782431927,  I_PGM = 0.027171334527149718 bits
R6i  0.24046398782431946,  I_PGM = 0.027171334527149100 bits
chance = 0.2
```

Their adjacent-depth mixture trace distances also agree:

```text
rho .1→.5   0.359171846653026
rho .5→1    0.145526990054384
rho 1→2     0.063004866239147
rho 2→4     0.009073925653598
```

The noncompact radial coordinate is compactifying toward the boundary in both
maps. R6i retains more compact/projective angular structure; it does not repair
that radial contraction.

## Matched experiment

Both maps receive byte-identical `SL(2,R)` source matrices and use one ambient
Hilbert dimension `D=16` (four allocated qubits):

- **R6** embeds the complete five-dimensional Bell-attempt-plus-erasure state
  passively in `C^16`;
- **R6i** uses the guarded shared-SVD Julia/Halmos block and the pure
  `|vec_F(U_A)/2>` density in `C^16`.

Ambient allowance is equal, active expressivity is not. The clean mean support
ranks are five for R6 and nine for R6i. Noise-induced rank is never counted as
representational capacity.

The source grid uses five depths
`[0.1, 0.5, 1, 2, 4]`, 32 signed codewords per depth, two equiprobable paired
query perturbations, and four global depolarizing strengths
`[0, 0.01, 0.03, 0.1]`.

The receiver is trained once on clean templates. Its PGM effects are completed
by `E_perp = I - Pi_support`; that outcome is retained as abstention/failure.
No noisy probability row is renormalized after support loss.

The volatile four-shard store is in the retrieval path: every signed template
is written, fetched by deterministic key, and only then used to derive signed,
projective, radial, and joint task mixtures. The split-signature form is not a
similarity metric.

## Retrieval surface

### True projective task

The primary angular task uses the actual `Z2` class mixture

```text
rho_[k] = (rho_k + rho_(k+16)) / 2,
```

not a half-grid choice of representatives.

| depth | noise | R6 correct | R6i correct | gain | R6 I_PGM | R6i I_PGM | gain bits |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | 0.0 | 0.134995 | 0.170873 | 0.035878 | 0.381783 | 0.620723 | 0.238941 |
| 0.5 | 0.0 | 0.151751 | 0.245992 | 0.094241 | 0.328279 | 1.138360 | 0.810081 |
| 1.0 | 0.0 | 0.155423 | 0.262430 | 0.107007 | 0.293240 | 1.208396 | 0.915157 |
| 2.0 | 0.0 | 0.155992 | 0.264960 | 0.108968 | 0.272786 | 1.173646 | 0.900861 |
| 4.0 | 0.0 | 0.156003 | 0.265008 | 0.109005 | 0.269588 | 1.164282 | 0.894694 |
| 0.5 | 0.1 | 0.138529 | 0.224908 | 0.086379 | 0.285495 | 0.937372 | 0.651877 |
| 1.0 | 0.1 | 0.141834 | 0.239703 | 0.097869 | 0.255477 | 0.998771 | 0.743295 |
| 2.0 | 0.1 | 0.142346 | 0.241980 | 0.099634 | 0.237800 | 0.972017 | 0.734217 |
| 4.0 | 0.1 | 0.142356 | 0.242023 | 0.099667 | 0.235029 | 0.964793 | 0.729765 |

The probability margin is one projective-task chance unit, `1/16=0.0625`.
Depth `0.1` retains a positive gain but does not cross that practical margin;
the other four depths do so at every noise level.

### Joint depth × projective angle

| noise | R6 correct | R6i correct | gain | R6 I_PGM | R6i I_PGM | gain bits |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.033516 | 0.053455 | 0.019939 | 0.292105 | 0.980811 | 0.688706 |
| 0.1 | 0.030555 | 0.048813 | 0.018258 | 0.253703 | 0.814224 | 0.560522 |

The 80-class probability margin is one chance unit, `1/80=0.0125`.

### Radial endpoint

At noise `0.1`, absolute correct probability remains close:

```text
R6   0.2226675890,  I_PGM = 0.0236777304 bits
R6i  0.2276675890,  I_PGM = 0.0232524345 bits
```

R6i has a small `+0.005` correct-probability difference because its larger
clean support produces less complement abstention under global depolarization;
its mutual information is slightly lower. This is not radial rescue.

## Cost vector

The two maps use the same guarded `4×4` Halmos core. With Qiskit 2.3.0,
`basis_gates=[u,cx]`, optimization level 3, and seed 11:

| encoder proxy | u | cx | measure | depth |
|---|---:|---:|---:|---:|
| shared core | 6 | 2 | 0 | 5 |
| R6 | 7 | 3 | 1 | 8 |
| R6i | 8 | 4 | 0 | 7 |

The complete state controls pass:

```text
R6i declared-codeword density residual  4.23e-16
R6 success/erasure density residual     5.87e-17
shared-core operator residual           2.84e-15
```

R6i uses one additional active qubit, one additional Bell-pair preparation,
and one additional compiled CX. R6 alone incurs measurement, postselection,
and common-erasure coarse graining. Its Bell-average expected attempts approach
two at depth, while its worst-direction attempts grow as `exp(4 rho)` and reach
about `8.89e6` at `rho=4`.

The one-shot R6 erasure state already charges failure; it is not multiplied by
the success probability again. R6 common-erasure coarse graining and the PGM
receiver synthesis are explicitly unpriced. These compiler numbers are not
hardware costs, and the cost vector has no Pareto winner.

R6i remains a point map, not a representation:

```text
identity composition defect  2 sqrt(2) = 2.8284271247461903
generic composition defect                 2.835726024833748
```

## Exact truncation wall

R6T is a non-competing `SU(1,1)/U(1)` lowest-weight control. For cutoff four,

```text
tau = tanh(rho)^8
rho_trunc = |P4 psi><P4 psi| + tau |e><e|.
```

The exact trace distance from that flagged mixed state to the infinite pure
orbit is

```text
D = (tau + sqrt(4 tau - 3 tau^2)) / 2,
```

not merely `sqrt(tau)`.

| depth | worst perturbed D | within 0.05 | required D for 0.05 | infinite mean photons | cutoff max photons |
|---:|---:|:---:|---:|---:|---:|
| 0.1 | 0.000144 | yes | 4 | 0.0201 | 6 |
| 0.5 | 0.049920 | yes | 16 | 0.5431 | 6 |
| 1.0 | 0.387373 | no | 144 | 2.7622 | 6 |
| 2.0 | 0.947940 | no | 6,889 | 26.3082 | 6 |
| 4.0 | 0.999973 | no | 20,250,000 | 1,489.4792 | 6 |

So the matched `D=16` truncation control reaches its declared wall immediately
after depth `0.5`. Any apparent deep hard-wall retrieval would be dominated by
truncation reflection, not evidence that a finite unitary representation has
captured the source geometry.

## Evidence boundary

- 96 primary R6/R6i cells and 20 R6T cells; 116 distinct bound inputs.
- 320 append-only reservoir events with contiguous sequence and unique keys.
- All 34 protocol, numerical, source, event, dependency, and preservation
  checks pass.
- The local evidence envelope verifies with `n_eff=116`.
- The result is self-recomputed, unsigned, commit-unbound, and not independently
  witnessed. Every direct source, test, runner, manifest, event, and result file
  is hash-bound instead.
- Pilot calculations were visible before the final protocol hash; this is not
  an outcome-blind replication.

Primary artifacts:

- `artifacts/r6k_equal_resource_reservoir/equal_resource_reservoir.json`
- `artifacts/r6k_equal_resource_reservoir/equal_resource_reservoir.envelope.json`
- `artifacts/r6k_equal_resource_reservoir/events.jsonl`

The append-once runner intentionally refuses to execute again in this checkout.
Verify the stored envelope with:

```powershell
$env:PYTHONPATH='src'
python -m aionq.verify_envelopes artifacts\r6k_equal_resource_reservoir
```

## Literature boundary

The design was informed by work that treats reservoir performance as an
operational memory/information question, distinguishes Hilbert-space size from
information spreading, and shows that noise effects are channel-dependent:

- [Characterizing the memory capacity of transmon qubit reservoirs](https://arxiv.org/abs/2004.08240)
- [Benchmarking the role of particle statistics in Quantum Reservoir Computing](https://arxiv.org/abs/2302.07164)
- [Taking advantage of noise in quantum reservoir computing](https://arxiv.org/abs/2301.06814)
- [Dissipation as a resource for Quantum Reservoir Computing](https://arxiv.org/abs/2212.12078)
- [HypRAG: Hyperbolic Dense Retrieval for Retrieval Augmented Generation](https://arxiv.org/abs/2602.07739)

Those papers do not turn this associative benchmark into temporal QRC. No
architecture, device, FPGA, quantum-advantage, cognition, consciousness,
sentience, AGI, or complexity-class claim follows from this result.
