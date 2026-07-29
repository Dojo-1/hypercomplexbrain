# Review — HB-0 polycosmic kernel (PR #1, `gpt/polycosmic-hb0-kernel`)

20 commits, 3,214 insertions, 6 modules, 31 tests, a 367-line manifest and a
self-audit. Reviewed against this repository's own standard, and cross-checked
against the R6 arc's verified operators.

**Verdict: the honesty machinery is real and enforced.** The one defect I thought
I had found was my own test being wrong, twice. That correction is the most
important thing in this review and it goes first.

---

## 0. My own error, before anything else

I twice concluded the manifest's no-advantage rule was **decorative**, and I was
twice wrong.

- **First attempt.** My tamper helper recursed into lists by building
  `{i: x for i, x in enumerate(v)}` — a *copy*. Mutating it changed nothing, so
  I validated an untampered manifest and read the pass as "not enforced."
- **Second attempt.** I fixed the tamper, located `advantage_claim` by real path,
  flipped it, and tested for an **exception**. None came, and I again read that
  as "not enforced." But `validate_hb0_manifest` is a *report-returning*
  validator: `check()` appends to an error list and the function returns
  `HB0ManifestReport(ok=..., errors=...)`. Testing for a raise asked the wrong
  question.

Checked properly:

```
clean manifest              ok=True   checks_run=154  errors=()
advantage_claim -> True     ok=False  errors=('HB-0 may not promote a quantum advantage claim',)
simulator_only  -> False    ok=False  errors=('quantum transport must be marked simulator-only',)
```

**Both honesty flags are machine-checked.** A manifest that claims quantum
advantage fails validation. That is materially better than documenting the
constraint in prose, and I nearly reported the opposite.

This is the same failure class this repository keeps hitting, now aimed at
someone else's work: *a detector that fires for the wrong reason*. In R6e a
mis-specified fault injection made a working detector look broken; here a
mis-specified tamper made a working validator look decorative. The lesson is the
same — when a check reports "no problem", verify the check can report a problem
at all before believing it.

## 1. What I verified independently

Their numbers, recomputed here rather than read from their report:

| claim | independent check | result |
|---|---|---|
| teleportation is exact | worst **branch** fidelity over 200 random inputs | **1.000000000000000** |
| Bell resource is maximally entangled | `bell_entropy_bits` deviation from 1 | **1.1e-16** |
| tunnelling is unitary | worst probability outside [0,1] over 200 draws | **0.000e+00** |
| manifest is well-formed | `checks_run` on the clean manifest | **154, zero errors** |
| tests are non-trivial | `assert True` / `is not None` count in 31 tests | **0** |

I checked the *per-branch* fidelity, not just `average_fidelity`. A teleportation
implementation can average to 1 while individual correction branches are wrong;
all four branches are exactly 1 here.

## 2. What is genuinely good

**The no-advantage rule is a validator rule, not a sentence.** `manifest.py:146`
plus the enforcement above. `transport.py` carries `advantage_claim: bool = False`
as a dataclass *field default*, so a report cannot be constructed without it.

**A Euclidean capacity-matched control is required by the manifest.** Six
controls are mandatory including `euclidean_capacity_matched` and
`hypercomplex_fixed_graph` — dimension-matched control discipline enforced at the
schema level, which is exactly what the manifold-round contract demands.

**The self-audit names its own non-closure.** `[R]_competence` — *"no matched-control
result yet establishes that HB-0 thinks better"*, tagged H/S. And on recognition:
*"an executable hypothesis, not a measured social-cognition result."* The
sixteen-quality matrix labels entries **structural** rather than measured. That is
the right posture and it is rare.

**`FlatCollapseError`** — a named exception for forcing a heterogeneous object
into one promotion scalar. The scalar-collapse failure that cost S8 a round is
here a type error.

## 3. Where it meets the R6 arc — consistency, not conflict

HB-0's transport achieves fidelity exactly 1. R6f says the SL(2,ℝ) encoding caps
at 1 bit against SU(2)'s 2. Those are not in tension, and R6h's ε makes the
reason precise:

```
SU(2)   -> density matrix    eps = 0.000000   flattened
SL(2,R) -> density matrix    eps = 0.767777   resonant
```

HB-0's teleportation is unitary + measurement + correction on a maximally
entangled resource: no erasure branch, `p = 1`, fidelity exactly 1. **That is the
compact regime**, where ε = 0 — nothing is lost because the source has no
unprojected depth to lose. Their exactness and my ceiling are the same fact from
two sides. Their transport is exact *because* it never touches the non-compact
direction where the cost lives.

That is a real cross-module consistency check between two independently built
surfaces, and it passes.

## 4. What I would still ask for

Not defects — the open edges, stated as questions.

1. **`average_fidelity` returns 0.999999999999999 while every branch is exactly
   1.0.** A floating-point artifact of the averaging, harmless, but a test
   asserting `== 1.0` on the average would be fragile where one on the branches
   would not.
2. **The sixteen qualities are a declared coordinate set, not sixteen derived
   operators.** `QUALITY_ORDER` is validated for completeness (`set(qualities) ==
   set(QUALITY_ORDER)`), which checks that all sixteen are *present*, not that
   each is *computed from something*. The self-audit already says "structural"
   for most, so this is agreement rather than criticism — but the gap between
   "declared" and "instrumented" is where the manifold-round contract's ban on
   inventing mind-qualities bites, and it is worth keeping visible.
3. **`[R]_id` measures one operation on one carrier.** The audit says so. Worth
   restating because a zero there will read as "identity verified" to anyone who
   skims.
4. **No envelope.** HB-0 ships a manifest, tests, CI and a smoke run, but no
   `EvidenceEnvelope` — so `verify_envelopes` does not see it and its results are
   not bound to a command and a digest the way every R6 result is. That is the
   one piece of this repository's machinery it does not yet use.

## 5. Incidental

The merge changed `src/aionq/evidence.py` (four lines, `encoding="utf-8"` on
`write_text`/`read_text`). That correctly turned `METHOD-R4-EFFECTIVE_SAMPLE_SIZE`
red, because that envelope binds its claim to the file's hash. Inspected before
re-binding: `effective_sample_size` is byte-identical between the two commits, so
the claim survives and only the hash moved. Rebound at `ad9a43f` with the
supersession recorded in the artifact.

**Scope of this review:** I read the source, ran their smoke, recomputed their
quantum results, and adversarially tested their validator. I did not review
`core.py`'s governance dynamics or `kernel.py`'s event loop line by line, and I
did not evaluate whether the architecture is a good architecture — only whether
its claims match its code.
