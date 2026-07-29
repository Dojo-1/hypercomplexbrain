# QΣ-R6i — Coherent-dilation result

## Outcome

**Corrected frozen verdict: `RESCUE_FOR_THIS_MAP`.**

Across the complete preregistered grid of 6 depths × 6 codebook sizes
(36 rows), the coherent Julia/Halmos point encoding exceeds the matched R6
post-selected encoding in both preregistered information metrics. At every
depth, the improvement is greater than the frozen \(10^{-3}\)-bit margin at
each of \(N=64,100,256\). All 17 recorded structural and numerical controls
are true.

This is a rescue of **one specified finite-dimensional point encoding on one
frozen family of finite ensembles**. It is not a rescue theorem for arbitrary
fixed-width encodings. It does not make hyperbolic source volume operationally
unbounded: the candidate still occupies a fixed 16-dimensional Hilbert
carrier, so its Holevo information is bounded by \(\log_2 16=4\) bits. The
measured large-depth value is approximately 3 bits.

The result therefore corrects the scope of the earlier one-bit statement:

> The \(1+e^{-4\rho}\to1\)-bit ceiling is valid for the exact R6
> normalize-and-post-select map. It is not a general ceiling on all
> fixed-width maps of the same source.

The frozen protocol is in
[`qsigma_r6i_coherent_dilation_preregistration.json`](../manifests/qsigma_r6i_coherent_dilation_preregistration.json);
the outcome-visible method correction is in
[`qsigma_r6i_coherent_dilation_correction.json`](../manifests/qsigma_r6i_coherent_dilation_correction.json);
and the corrected measurements are in
[`coherent_dilation.json`](../artifacts/r6i_coherent_dilation/coherent_dilation.json).

## The tested map

For each source matrix \(M\in\mathrm{SL}(2,\mathbb R)\), the implementation
first forms the contraction

\[
A=\frac{M}{\lVert M\rVert_2}.
\]

One shared SVD constructs the two positive defect roots

\[
D_A=(I-A^\dagger A)^{1/2},
\qquad
D_{A^\ast}=(I-AA^\dagger)^{1/2},
\]

and the canonical positive-root Julia/Halmos completion

\[
U_A=
\begin{bmatrix}
A&D_{A^\ast}\\
D_A&-A^\dagger
\end{bmatrix}.
\]

The emitted codeword is the pure density state

\[
\rho_A^{H}
=
\left|\frac{\operatorname{vec}(U_A)}{2}\right\rangle
\left\langle\frac{\operatorname{vec}(U_A)}{2}\right|
\in\mathbb C^{16\times16}.
\]

R6 and R6i use byte-identical source coordinates, source-matrix digests, and
uniform priors. The implementation is
[`coherent_dilation.py`](../src/aionq/coherent_dilation.py).

## Frozen measurements

The primary quantities are:

- \(\chi\), the Holevo information of each finite ensemble;
- \(I_{\mathrm{PGM}}\), the mutual information achieved by the
  pretty-good measurement;
- their candidate-minus-R6 differences.

At \(N=256\), the complete-grid values are:

| \(\rho\) | full \(\chi\): R6 → R6i (\(\Delta\)) | full \(I_{\mathrm{PGM}}\): R6 → R6i (\(\Delta\)) |
|---:|---:|---:|
| 0.1 | 0.901726 → 1.877169 (+0.975444) | 0.385945 → 1.039740 (+0.653795) |
| 0.5 | 0.948679 → 2.800091 (+1.851412) | 0.330793 → 2.020039 (+1.689246) |
| 1.0 | 0.992052 → 2.973495 (+1.981442) | 0.295118 → 2.155958 (+1.860840) |
| 2.0 | 0.999852 → 2.999516 (+1.999664) | 0.274409 → 2.121924 (+1.847515) |
| 4.0 | 1.000000 → 3.000000 (+2.000000) | 0.271177 → 2.111487 (+1.840310) |
| 8.0 | 1.000000 → 3.000000 (+2.000000) | 0.271117 → 2.111280 (+1.840164) |

Every density codeword is pure, but the support rank of the ensemble mean is
5 for R6 and 9 for R6i across these rows. The ambient active density
dimensions are respectively 5 and 16. The passive-padding control shows that
adding unused zero coordinates does not change either information metric; it
does **not** make the two active carriers dimension-matched.

## Exact central-sign alias

Every frozen codebook size is even. Its source grid contains exact central
sign pairs

\[
M_{k+N/2}=-M_k.
\]

R6 maps each pair to the same density state. It therefore discards the
projective sign exactly. The canonical coherent completion does not. If the
singular values of \(A\) are \((1,q)\), with \(q=e^{-2\rho}\), then

\[
\left\langle
\frac{\operatorname{vec}(U_A)}2,
\frac{\operatorname{vec}(U_{-A})}2
\right\rangle=-q^2,
\qquad
F(\rho_A^H,\rho_{-A}^H)=q^4=e^{-8\rho}.
\]

Thus part of the measured gain is an identified mechanism: R6 aliases
\(M\) and \(-M\), whereas this completion increasingly separates them.
Calling the gain a generic fixed-width capacity effect would erase that
mechanism.

After the first outcome was visible, the correction ledger introduced a
**post-hoc, decision-inert sign-quotiented half-grid diagnostic**. At \(N=256\):

| \(\rho\) | half-grid \(\chi\): R6 → R6i (\(\Delta\)) | half-grid \(I_{\mathrm{PGM}}\): R6 → R6i (\(\Delta\)) |
|---:|---:|---:|
| 0.1 | 0.901726 → 1.478932 (+0.577207) | 0.385945 → 0.911221 (+0.525276) |
| 0.5 | 0.948679 → 2.065982 (+1.117303) | 0.330793 → 1.543685 (+1.212892) |
| 1.0 | 0.992052 → 2.211936 (+1.219884) | 0.295118 → 1.666656 (+1.371538) |
| 2.0 | 0.999852 → 2.250171 (+1.250320) | 0.274409 → 1.654731 (+1.380322) |
| 4.0 | 1.000000 → 2.253919 (+1.253919) | 0.271177 → 1.649012 (+1.377835) |
| 8.0 | 1.000000 → 2.253983 (+1.253983) | 0.271117 → 1.648897 (+1.377780) |

The residual separation after quotienting the exact sign pairs is useful
exploratory evidence that the sign bit is not the whole finite-grid result.
Because this diagnostic was added after the primary outcome, it cannot alter
or independently confirm the preregistered verdict.

## Controls and correction trace

The corrected execution passes:

- left and right unitarity;
- defect intertwining;
- density-state Hermiticity, trace, positivity, and purity;
- byte-identical coordinate and source-matrix matching;
- source-order permutation invariance;
- common-global-unitary invariance;
- passive-padding invariance for both encodings;
- the R6 analytic ceiling;
- exact R6 central-sign alias and coherent sign-overlap identities;
- PGM raw-probability, row-normalisation, support-projector, imaginary-part,
  and information-ordering guards;
- measured composition defects and the identity known answer.

Representative worst residuals are

\[
\begin{aligned}
\max\lVert U^\dagger U-I\rVert_F&=3.24\times10^{-15},\\
\max\lVert UU^\dagger-I\rVert_F&=3.20\times10^{-15},\\
\max\lVert AD_A-D_{A^\ast}A\rVert_F&=6.96\times10^{-16},\\
\max\text{(invariance residual)}&=1.33\times10^{-15}.
\end{aligned}
\]

Attempt 1 used separate eigendecompositions of the defect matrices and the
experiment tolerance as a repair threshold. That method could both amplify a
roundoff-scale zero through a square root and erase a genuine small defect.
The attempt was preserved as
[`coherent_dilation.attempt1_eigh.json`](../artifacts/r6i_coherent_dilation/coherent_dilation.attempt1_eigh.json)
and marked invalid before scientific lock.

Attempt 2 uses one shared SVD and a scale-aware machine-roundoff guard. Relative
to the preserved first artifact, the maximum absolute change over the four
primary metric fields is \(3.997\times10^{-15}\); the verdict is unchanged.
This numerical agreement does not rehabilitate the first method. It shows
that the corrected computation independently lands on the same finite-grid
values within floating-point noise.

## Point encoding, not representation

The completion is unitary pointwise but is not multiplicative. In particular,
the identity known-answer defect is

\[
\delta(I,I)=\lVert U_I-U_IU_I\rVert_F
=2\sqrt2
=2.8284271247461903.
\]

Three preregistered generic source-pair defects are

\[
2.8357260248,\qquad
2.8383010110,\qquad
2.7673128184.
\]

Consequently, \(M\mapsto U_{M/\lVert M\rVert_2}\) is a point encoding, not a
finite-dimensional unitary representation of \(\mathrm{SL}(2,\mathbb R)\).
The generic defect also contains the nonmultiplicativity introduced by
spectral normalisation.

The selected positive-root completion is canonical and deterministic for the
implemented rule, but unitary dilations have completion-gauge freedom. A
source-dependent completion gauge can itself carry labels. The common-unitary
control proves invariance under one global gauge change; it does not establish
invariance across arbitrary source-dependent completions.

## Evidence boundary

The legitimate statement is:

> On the frozen finite ensembles, this canonical coherent-dilation point map
> retains substantially more Holevo and PGM information than the matched R6
> normalize-and-post-select map, including after a post-hoc quotient of R6's
> exact central-sign aliases.

The following statements are **not** established:

- **Exact accessible information.** \(I_{\mathrm{PGM}}\) is the information
  achieved by one specified measurement, not the optimum over all
  measurements.
- **Channel or asymptotic capacity.** \(\chi\) is an ensemble upper bound here;
  there is no coding theorem, regularisation, energy constraint, or
  infinite-block analysis.
- **Dimension-matched superiority.** The active carriers are 5 and 16
  dimensional and their ensemble-mean support ranks are 5 and 9.
- **Quantum advantage.** There is no classical matched-resource baseline or
  operational task establishing advantage.
- **A representation theorem.** The exact and generic composition defects are
  nonzero.
- **Hardware, physical, or cognitive realization.** No device, noise model,
  cognition, consciousness, or AGI claim is part of this round.
- **Recovery of growing hyperbolic volume.** The output remains finite-width
  and finite-information even though it avoids R6's particular one-bit
  collapse.

## R6h status carried forward

R6h's preregistered seven-term translation law is **falsified / `HOLD`**, not
confirmed. Its verbatim sum classified the working non-compact R6 translation
as disconnected (\(\epsilon=3.434\)), contradicting the preregistered resonant
prediction. The later four-term carrier/translation split
(\(\epsilon_{\mathrm{translation}}=0.768\)) was selected after seeing that
failure. It is an exploratory calibration, not a confirmed trichotomy. It is
not used as a primary R6i gate.

## Other R6 claims narrowed by the audit

The one-bit derivation survives for the exact R6 map, but several surrounding
interpretations do not survive independent controls:

- The reported packing counts are fixed-sample greedy lower bounds computed
  separately in expanding balls. Their observed decrease cannot establish
  non-growth of the true packing number; sample dilution can manufacture that
  pattern.
- Spectral and Frobenius normalisation agree at the chosen deep point
  \(\rho=8\), but not globally. Their Holevo values differ by about \(0.362\)
  bits at \(\rho=0.1\).
- The width sweep adds zero coordinates around the same active rank-two probe.
  It establishes passive-padding invariance, not that active wider encodings
  are useless. R6i is a concrete counterexample to that broader wording.
- The parallel sweep uses a complete Cartesian product of product states and
  product priors, making additivity analytic for that construction. It does
  not test entangled codebooks or regularised Holevo capacity.
- Bell-probe optimality was checked over six members of one Schmidt family,
  not over every possible probe.

These are scope corrections, not a rejection of the valid
\(1+e^{-4\rho}\) ceiling for the exact post-selected R6 encoding.

## HB-0 status carried forward

The focused HB-0 implementation tests pass, but its present kernel remains an
architecture catalogue rather than a demonstrated causal coupled system:

- `PolycosmicKernel.step()` is not transactionally atomic under exceptions.
- Tendril outputs are observed but not applied to target subsystems, and
  identity sections are not refreshed by those observations.
- The vector adapter forces real floating-point state and can discard complex
  phase.
- Governance budgets can self-authorise measured increases, weakening the
  claimed gate.
- A disconnected identity ecology can still pass, `distance_to()` is
  asymmetric despite its name, and the tunnelling value is final occupancy
  rather than a transfer-probability estimate.

No HB-0 code was changed in R6i. The smallest honest next vertical slice is one
atomic active-tendril transaction with disabled and shuffled-target controls,
rollback on failure, and a measured target-state delta.

## Provenance

This note reports the locally generated, digest-bound artifact and its
preserved correction trace. Remote GitHub CI did not execute because the
account's billing/spending gate prevented jobs from starting; remote CI is
therefore not part of the evidence for this result.
