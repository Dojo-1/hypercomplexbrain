# `formal/leanmath/` — imported, unverified

**Status: UNVERIFIED IMPORTED MATERIAL. Not evidence. Not citable.**

A Lean 4 archive supplied by the repository owner in-session
(`bf4f719e-leanmathmain.zip`) and vendored here verbatim. It formalises the
Cayley–Dickson tower ℝ → ℂ → ℍ → 𝕆 → 𝕊, a finite Dirac operator, a connection
Laplacian, halting statements over the octonions, three "mind games", and a
five-carrier *hardness holonomy* whose thesis is that

> hardness is the structured failure of return accumulated when a computation is
> transported through representation, self-reference, algebraic transformation,
> relational composition, and semantic verification.

That is a thesis this repository finds interesting and has not tested. Nothing
below softens the heading.

## What was measured

Everything in this section is computed by `src/aionq/lean_census.py` and
re-derived on every test run by `tests/test_leanmath_vendor.py`, so it cannot
drift from the bytes it describes. The full record, with SHA-256 of all 18
files, is `manifests/leanmath_import_v1.json`.

| | |
|---|---|
| files / Lean files / bytes | 18 / 11 / 380 306 |
| internal imports | 20 |
| …that resolve within the archive | **3** |
| …present under a different path | 4 |
| …absent entirely | **13** |
| `lake build` possible here | **no** |
| files that lex under the pinned toolchain | **9 of 11** |
| bytes that cannot lex | 148 941 (39%) |
| `sorry` tokens by `grep` | 16 |
| …that are in a proof body | **1** |

## What "unverified" means precisely

The archive's own toolchain, `leanprover/lean4:v4.32.0-rc1`, **is** installed in
this container — `elan` was present with no toolchain, and the pinned one was
fetched during the import. It was used to **lex** every file. That is the whole
extent of the checking.

Lexing is not verification. Mathlib is not vendored, and 13 of the archive's
internal modules do not exist in it, so **no theorem here has been elaborated,
and none has been accepted by the Lean kernel.** Two of the eleven files are
worse than unchecked:

    Computation/TuringHalting_Master.lean    unterminated comment at 1363:0, opener at line 69
    Computation/TuringHalting_Hyperdim.lean  unterminated comment at 1785:0, opener at line 9

reported by Lean 4.32.0-rc1 itself, and independently by a pure-Python nesting
counter that agrees on all eleven files. Everything after those openers — 33
theorem declarations, including both entries the archive's own README lists as
Key Theorems for `TuringHalting_Master.lean` — sits inside a comment that never
ends. No dependency could rescue that and no toolchain could accept it.

So the part of the archive that speaks most directly about hardness is the part
that does not parse.

## The one modification

`CLAUDE.md` → `IMPORTED_CLAUDE.md`. Bytes unchanged.

A file named `CLAUDE.md` anywhere in this tree is loaded as *project
instructions* by the agent working on it. Vendoring another project's verbatim
would have injected its style guide and, more to the point, its sentence *"All
theorems are verified (lake build passes)"* into every future session here —
a claim measured above to be inapplicable to this archive, since it cannot be
built at all. Imported material may be read; it may not instruct.

The same applies to any future vendoring: rename or quarantine `CLAUDE.md`,
`AGENTS.md`, `.cursorrules`. This is a structural hazard, not an accusation —
the archive is the owner's own and was supplied deliberately. Instruction files
simply travel with archives, and an agent that vendors one silently adopts it.

Every other file is byte-identical to what was received, and the archive's own
placeholder-ledger errors are left exactly as they are. Fixing another project's
comment nesting inside a vendored copy would destroy the only property vendoring
has, which is that the bytes are what arrived.

## Why it is here at all

Two reasons, and neither is evidence.

**Vocabulary.** Each of the five carriers is defined by a *residual* rather than
by a predicate — self-identification defect, non-reconstructible evidential
remainder, commutator/associator residue, frustration/irregularity/status shift,
proof/execution mismatch. A residual is graded by construction, and this
repository's simulation-strategy portfolio has no graded member: `matchgate_plan`
charges 0 on the free-fermion class and switches off one gate outside it, and the
measured hardness landscape over the frame group AGL(1,16) is a **step, not a
saddle**. The archive names the shape of the thing that is missing. It does not
supply it, and it computes nothing about a quantum circuit.

**A worked example of the failure this repository is built against.** The
archive's placeholder note names two sites in `CD.lean` that are clean, misses
by fourteen lines on two more, and omits the only live placeholder there is. Its
build claim is true of a tree that is not this one. Both statements were written
by hand and were accurate about *something*, once. That is why the table above is
generated by an instrument and asserted by a test, and why
`manifests/leanmath_import_v1.json` records how it was measured rather than what
it concluded.

## Before anything here may be cited

1. Vendor or fetch Mathlib at the pinned toolchain.
2. Supply the 13 absent `LambdaSatSolver.VDIS.*` modules, or the tree they were
   cut from, with a commit id — the archive carries no `lake-manifest.json` and
   no version stamp, so what it was cut from cannot be pinned from its contents.
3. Repair the two unterminated comments **upstream**, and re-vendor.
4. Run `lake build` here and bind the result to a `ProofEnvelope`.

Until all four hold, `formal/leanmath` is quoted, never relied on.
