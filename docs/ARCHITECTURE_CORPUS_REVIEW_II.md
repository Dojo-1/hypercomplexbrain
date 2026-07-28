# Review of the wider architecture corpus — II

Companion to `ARCHITECTURE_CORPUS_REVIEW.md`. The first pass read four public
READMEs. This one goes after the things a README cannot settle: what the CI
actually runs, what the dependency manifest actually pins, and which of the
account's claims have a verifier that is not a person.

The first review's headline was that no single repo has the whole discipline.
That still holds. This pass changes which repo is at the top of the list, and
it changes it because of a mistake I made and caught.

---

## 0. What was checked, and at what tier

| artifact | how read | tier |
|---|---|---|
| `connection_laplacian_lean/.github/workflows/lake-build.yml` | raw file, verbatim | **checkable** |
| `connection_laplacian_lean/lake-manifest.json` | raw file, verbatim | **checkable** |
| `connection_laplacian_lean/BUILD.md`, `README.md` | raw files | reported |
| that repo's Actions page | rendered HTML | reported |
| `aigit`, `QuantumNNSNR` READMEs | rendered HTML | reported |
| every private repo below | **not read** — 404 unauthenticated | none |

Nothing here was cloned, built, or executed. The manifest and workflow claims
in §2–§3 are the only ones another party can check without network access to a
private repo, because the file contents are quoted. Everything else is
**M-reported, not recomputed**, same tag as the first review.

---

## 1. The correction: I nearly mis-filed the account's strongest artifact from
its language tag

Going into this pass I had `connection_laplacian_lean` queued as a
claim-to-artifact mismatch, on this reasoning: the repository is named for a
*Lean* formalisation, and GitHub language-tags it **Python**. Same shape as a
badge that doesn't match its artifact.

The reasoning was wrong, and reading the repository reversed it. It is a Lean 4
formalisation: a 15-file verified spine from `Basic.lean` through
`L17_TracesAndLipschitz.lean`, named theorems including
`cover_charpoly_eq_scalar_times_mobius`, `signedLaplacianMobius_posSemidef` and
`numBalancedComponents_monotone_remove_nonwrap_nonbridge`, maintained
`sorry`-free and free of user-introduced axioms. The Python is in `findings/` —
numerical fuzzers and negators. The language tag is a **byte count**, and
mathlib-dependent Lean projects are small in bytes while their Python
cross-checks are not.

This is the recurring failure of this whole programme, running in the inverted
direction. The usual form is *the right shape with the old comparison still
inside it*. Here it was the right instrument — check claims against artifacts —
pointed at the wrong observable. A language tag is not an artifact. It is
listing metadata, and listing metadata generates hypotheses, never findings.

I record it because the first review's "Not read" section still contains
inferences drawn from repository *descriptions*, and those inferences are of
exactly the type just invalidated. They should be read as questions.

## 2. That repo already draws the P/M line, in its own words

> "The `findings/` directory holds only the Python numerical cross-checks cited
> by the paper. They are empirical validations of the formal theorems, not
> theorems themselves."

That is `PROVEN` vs `MEASURED`, written independently, in a repository that has
never heard of this ledger. It is also the sentence the IGBundle-LLM and Trasgo
READMEs are missing, and it costs one paragraph.

Its `findings/` layout is a second thing worth taking:

```
round2/fuzzer   round3/negator   round4/negator_fuzzy   round5   round6/{stage2_fuzzer_A,stage6_fuzzer_B}
```

Adversarial searches run **against theorems that are already machine-proved**.
This repository's adversarial tests attack *implementations* — the equivalence
attacks, the matched controls, the representation attacks. Attacking a proved
statement is a different move: the search cannot succeed, so what it measures
is whether the statement means what its author thinks it means. That is a gap
here and it is cheap to close.

## 3. The green build **is** the pinned build. The documented build is not.

`lake-manifest.json` pins mathlib at rev `20c73142afa995ac9c8fb80a9bb585a55ca38308`
(`inputRev: "v4.11.0"`), alongside pinned revs for batteries, Qq, aesop,
ProofWidgets4, Cli and importGraph. `lean-toolchain` pins Lean 4.11.0.

CI runs, verbatim:

```yaml
      - name: Get Mathlib cache
        run: lake exe cache get || true

      - name: Build
        run: lake build
```

No `lake update`. So the green `lake build` runs on GitHub's runner really do
rebuild the committed pin — the workflow and the manifest agree, and there are
green runs on `main` and on the `claude/…` and `copilot/…` branches.

`BUILD.md` documents:

```bash
lake update
lake build
```

`lake update` re-resolves every dependency's `inputRev` and **rewrites the
committed manifest**. Several of those `inputRev` values are `main` or
`master`. The documented procedure's first step discards the property the
repository took care to establish; a reader following BUILD.md is not building
what CI built, and on a bad day is not building at all.

The fix is a deletion and an addition:

```bash
lake exe cache get   # was missing; without it the first build is ~an hour
lake build           # on the committed manifest, as CI does
```

That is the cheapest high-value patch anywhere in the corpus: one line of
documentation standing between a reader and a reproducible machine-checked
proof.

One detail worth defending rather than flagging: `|| true` on `lake exe cache
get` is correct. A cache miss must not fail a build that is about to do the
work anyway. It is the one `|| true` in the corpus that is not hiding a
failure.

## 4. What that green build is, in R4-D vocabulary

Producer ≠ verifier, and the verifier performs a second computation that is
able to disagree. The Lean kernel, running on a machine the author does not
own, re-derives every theorem in the spine from source. That is
`VerificationMode.RECOMPUTED`, and it is only the **second** instance of it in
the account — λSAT's `drat-trim` is the first.

The two are not interchangeable, and an `external_checker` schema has to
accommodate both:

| | λSAT / drat-trim | connection_laplacian_lean / lake |
|---|---|---|
| scope | per-instance certificate | the entire theorem spine |
| TCB | tiny — one C checker | large — Lean kernel + mathlib at a pinned rev |
| what a pass means | *this* UNSAT verdict is sound | *these statements* follow from mathlib's axioms |
| failure mode | certificate rejected | build red |

This kills the single-string `external_checker` field the first review
proposed. The field needs at least `tool`, `version`, `pinned_inputs_digest`
and a `tcb_note`, because "checked by Lean 4.11.0 + mathlib
`20c73142…`" and "checked by drat-trim" are not the same strength of claim and
must not serialise to the same shape.

## 5. Four independent witness membranes, none importing another

| repo | mechanism | what it witnesses |
|---|---|---|
| lambda-sat-solver | DRAT + model replay | *verdicts* — recomputed per instance |
| connection_laplacian_lean | `lake build` in CI + adversarial negators | *statements* — recomputed wholesale, then attacked |
| aigit | `.semantic/provenance.jsonl`, `--agent/--model/--prompt` | *producers* — who and what made the change |
| **hypercomplexbrain** | `EvidenceEnvelope`, witness nerve | *the relation between the other three* |

Convergent evolution inside one account. None of the four imports another; each
was built as if the problem were new. That is itself the finding: the need for
a witness membrane is not a stylistic preference of this repository, it is what
this account's work keeps independently rediscovering the moment a claim has to
survive contact with someone else.

## 6. The pattern this repository should copy for the Gödelian batch

`connection_laplacian_lean` has `claude/peer-review-*` and `copilot/*` branches
with merged PRs and green runs. Multiple agents review each other's work in
that repository, in production, today.

By `witness_nerve.py`'s theorem, agents reviewing agents is the attestation
cycle: every `producer != verifier` check passes and the loop can compute
nothing. What keeps that repository's graph honest is that `lake build` is an
edge in it, and `lake build` is not an agent. The kernel does not attest; it
recomputes, and it can say no.

The direct consequence for the batch now pending with Gödelian-1: **a Gödelian
review is `reviewed` (rank 2) and cannot become `recomputed` (rank 3) by being
detailed, confident, or correct.** Rank 3 requires something mechanical to
re-execute. The batch is worth running for what rank 2 is worth — a critic who
can disagree about meaning — and the ingestion path should refuse to promote it
further no matter what the response text says about having "verified" anything.

`connection_laplacian_lean` is therefore the right first real `ProofEnvelope`,
and the reason is now sharper than the first review's: not because it has a
build, but because its build is the only verifier in the account that is
neither this author nor a language model.

## 7. The visibility asymmetry, read as data

Nine public source repositories. 632 stars given, 1–2 received, 13 followers.
The account has built four mechanisms for establishing that a claim was checked
by someone else, and is itself almost entirely unchecked by anyone else.

The exception is the single place where the verifier is a machine rather than a
person: CI. Which is the argument for machine witnesses, stated by the shape of
the account rather than by anyone's preference. A recomputation does not need
an audience.

## 8. QuantumNNSNR — one number short of falsifiable

Public, Python, Qiskit + scikit-learn: simulate QPSK with noise, compute
per-packet SNR, threshold it into two classes, train a VQC, test it. The README
gives the full method and no result — no accuracy, no threshold value, no
dataset sizes, no noise parameters, no baseline.

The baseline is the problem, not the missing accuracy. The label is a threshold
on a scalar that is computed from the input; logistic regression on that scalar
achieves ~100% by construction. Any VQC number below that is a negative result
and any number at it is not evidence of quantum anything. As written the
experiment cannot fail, which means it also cannot succeed. Reporting the
classical baseline alongside would settle it in an afternoon.

## 9. Not read — and no inferences drawn

The following returned **HTTP 404 unauthenticated**, i.e. private:
`-lang.s1`, `nnn-hyperbolic-ramdisk`, `nnn-hyperbolic-ramdisk_v2`,
`np-completeness-bunny-utai-study`, `Geodesic-Resonance-Descent`,
`dialogue-atlas`, `hypercomplex-math-thesis`, `manifold`, `Topos-Trasgo`,
`braintop`, `METACOG`, `TELOS`, `LLM-in-concave-manifolds`,
`-SAT_Research_Canary`.

Per §1, their descriptions are not evidence about their contents. Two open
questions that only `add_repo` can answer, stated as questions:

- Does `nnn-hyperbolic-ramdisk` implement a (+,+,−,−) metric, and if so does it
  handle the unboundedness of the SU(1,1) generators — the exact obstacle that
  left the (2,2) half of Round S8 unimplemented? Both the Frobenius-norm and
  the rank arguments need re-deriving in split signature, and if that repo has
  done it, S8 does not need to.
- Does `-lang.s1` contain a specification of `T_Σ_n_geom` that names its own
  kill conditions? It is the most recently updated repository in the account
  after this one.

Neither question is answered here, and neither should be answered from a
description.
