"""The vendored Lean archive, and the labels attached to it.

`formal/leanmath/` is imported unverified material.  A label like that is worth
nothing if it is a sentence in a README, because sentences do not notice when
the thing they describe changes -- which is exactly the defect this file's
subject exhibits.  The archive's own placeholder note names two sites in
`CD.lean` that hold no placeholder, misses by fourteen lines on two more, and
omits the only live one.  It was presumably accurate when it was written.

So every number in `formal/LEANMATH_PROVENANCE.md` and in
`manifests/leanmath_import_v1.json` is re-derived here from the bytes.  If the
archive is re-vendored, repaired, or extended, these tests fail and the labels
have to be re-earned rather than silently outliving their subject.

One measurement cannot be re-derived without a Lean toolchain: the lexical
verdict.  It was produced by the archive's own pinned `lean` v4.32.0-rc1 during
the import.  What is checked here instead is that the pure-Python nesting
counter still agrees with the verdict that toolchain recorded, on every file.
Two instruments -- one written against the token grammar, one being the actual
lexer -- agreed on 11 of 11.  If the counter ever stops agreeing with the
recorded verdict, one of them has moved and the manifest is stale.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aionq import lean_census as census

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "leanmath_import_v1.json"
PROVENANCE = ROOT / "formal" / "LEANMATH_PROVENANCE.md"
GITATTRIBUTES = ROOT / ".gitattributes"

#: The verdict the pinned toolchain gave, file by file, during the import.
#: `lean --root=. <copy with import lines stripped>`, 240s budget each, no
#: timeouts.  Stripping imports can only add downstream errors; it cannot create
#: or hide a lexical one, because the lexer never consults a dependency.
TOOLCHAIN_LEX_FAILURES = {
    "Computation/TuringHalting_Master.lean": 1363,
    "Computation/TuringHalting_Hyperdim.lean": 1785,
}


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_the_archive_is_present_and_pinned_by_digest(manifest):
    """Every vendored byte is pinned, and the pinning covers every file.

    A digest table that omits a file cannot detect that file changing, so the
    two directions are asserted separately: recorded digests must match, and the
    set of recorded names must be the set of names on disk.
    """
    recorded = manifest["digests"]
    measured = census.digests()
    assert set(recorded) == set(measured), (
        "the vendored file set and the manifest's digest table have diverged")
    differing = {name for name in recorded if recorded[name] != measured[name]}
    assert not differing, f"vendored bytes changed since import: {sorted(differing)}"


def test_vendored_archive_is_checkout_opaque():
    """A byte-pinned archive cannot inherit platform newline conversion."""
    attributes = GITATTRIBUTES.read_text(encoding="utf-8")
    assert "/formal/leanmath/** -text" in attributes


def test_census_paths_are_canonical_posix_keys():
    """Manifest keys are data, not host-native display paths."""
    key_sets = (
        set(census.digests()),
        set(census.code_placeholders()),
        set(census.comment_balance()),
    )
    assert all("\\" not in key for keys in key_sets for key in keys)


def test_the_archive_cannot_be_built_here_and_the_manifest_says_so(manifest):
    """17 of 20 internal imports are unsatisfiable, so `lake build` is impossible.

    This is the load-bearing fact behind the UNVERIFIED label.  It is not a
    missing external dependency -- Mathlib's absence would be ordinary -- it is
    that the archive imports thirteen of its own modules that are not in it.
    """
    resolution = census.resolve_imports()
    by_status = {status: sum(1 for entry in resolution if entry.status == status)
                 for status in ("resolves", "basename_only", "absent")}

    assert len(resolution) == 20
    assert by_status == {"resolves": 3, "basename_only": 4, "absent": 13}
    assert not census.census()["buildable"]
    assert manifest["measurement_1_import_resolution"]["absent"] == 13
    assert manifest["evidence_rank"] == "NONE"


def test_the_five_carrier_file_is_the_least_satisfiable_of_all(manifest):
    """`HardnessHolonomy.lean` is the thesis, and 1 of its 8 imports resolves.

    Worth its own test because it is the file anyone would be tempted to cite.
    It is also the largest single source in the archive, which makes the
    temptation stronger and the gap no smaller.  And of the two dependencies
    that are present-but-misplaced, one is `TuringHalting_Master.lean` -- so
    even a reading generous enough to forgive every path hands the thesis file
    an import that does not parse.
    """
    hardness = census.imports(census.LEANMATH_ROOT / "HardnessHolonomy.lean")
    status = {entry.module: entry.status for entry in census.resolve_imports()}
    counts = {kind: sum(1 for module in hardness if status[module] == kind)
              for kind in ("resolves", "basename_only", "absent")}

    assert len(hardness) == 8
    assert counts == {"resolves": 1, "basename_only": 2, "absent": 5}
    assert status["LambdaSatSolver.VDIS.Algebra.CD"] == "resolves"

    misplaced = {entry.candidates[0] for entry in census.resolve_imports()
                 if entry.module in hardness and entry.status == "basename_only"}
    assert misplaced == {"Computation/TuringHalting_LeanLake.lean",
                         "Computation/TuringHalting_Master.lean"}
    assert misplaced & set(TOOLCHAIN_LEX_FAILURES) == {
        "Computation/TuringHalting_Master.lean"}


def test_the_python_counter_still_agrees_with_the_pinned_lexer():
    """Two independent instruments, one of them the real Lean, on all 11 files.

    The toolchain's verdict is recorded rather than recomputed (no Lean is
    required to run the suite), so what this guards is agreement: the counter
    must flag exactly the files Lean flagged, and no others.  Disagreement in
    either direction means the recorded verdict no longer describes the bytes.
    """
    unbalanced = census.comment_balance()

    assert set(unbalanced) == set(TOOLCHAIN_LEX_FAILURES), (
        "the nesting counter and the recorded toolchain verdict disagree about "
        "which files lex")
    assert unbalanced["Computation/TuringHalting_Master.lean"]["opened_at"][0] == 69
    assert unbalanced["Computation/TuringHalting_Hyperdim.lean"]["opened_at"][0] == 9


def test_the_unparseable_files_carry_the_archives_own_key_theorems():
    """The part that speaks about hardness is the part that does not parse.

    Not a stylistic observation.  `TuringHalting_Master.lean`'s two README-listed
    Key Theorems both sit after the unterminated opener at line 69, so they are
    comment text.  A reader skimming for `theorem layer_a_...` finds it; the
    lexer never does.
    """
    import re

    total = 0
    for name, opener in (("Computation/TuringHalting_Master.lean", 69),
                         ("Computation/TuringHalting_Hyperdim.lean", 9)):
        lines = (census.LEANMATH_ROOT / name).read_text(encoding="utf-8").splitlines()
        swallowed = [index for index, line in enumerate(lines, 1)
                     if index > opener and re.match(r"\s*(theorem|lemma)\b", line)]
        total += len(swallowed)
        assert swallowed, f"{name} was expected to have declarations after {opener}"

    assert total == 33

    master = (census.LEANMATH_ROOT / "Computation/TuringHalting_Master.lean"
              ).read_text(encoding="utf-8")
    for named in ("layer_a_no_nonzero_raw_fixed_point",
                  "layer_b_local_not_globally_captured"):
        assert f"theorem {named}" in master
        assert master.index(f"theorem {named}") > master.index("/-!", 0)


def test_the_archives_own_placeholder_ledger_is_stale(manifest):
    """The finding that motivated computing all of this instead of writing it.

    `HardnessHolonomy.lean:70-73` claims the surviving placeholders are
    "CD.lean:363,366; TuringHalting_Master.lean:362,393".  Measured: CD.lean has
    none at all, Master's are at 376 and 407 and are inside a comment, and
    `ConnectionLaplacian.lean:789` -- the only live one in the archive -- is not
    mentioned.  Stale in both directions at once.
    """
    placeholders = census.code_placeholders()

    assert placeholders == {"Geometry/ConnectionLaplacian.lean": ((789, "sorry"),)}
    assert "Algebra/CD.lean" not in placeholders
    assert "HardnessHolonomy.lean" not in placeholders

    note = (census.LEANMATH_ROOT / "HardnessHolonomy.lean").read_text(encoding="utf-8")
    assert "CD.lean:363,366" in note, (
        "the stale claim this test is about is no longer in the archive; "
        "re-measure and update manifests/leanmath_import_v1.json")
    assert "ConnectionLaplacian" not in note.split("-/")[0]


def test_grep_would_report_sixteen_times_as_many_placeholders_as_exist():
    """Why the census is comment-aware, quantified.

    16 occurrences of the token, 1 in a proof body.  13 are prose about
    placeholders -- including the sentence asserting there are none -- and 2 are
    inside the unterminated comment.  A naive count would have put this archive's
    placeholder burden at sixteen times its actual value.
    """
    raw = sum(text.count("sorry")
              for text in ((census.LEANMATH_ROOT / relative).read_text(encoding="utf-8")
                           for relative in census.lean_sources()))
    in_code = sum(len(hits) for hits in census.code_placeholders().values())

    assert raw == 16
    assert in_code == 1


def test_no_vendored_file_is_loaded_as_project_instructions():
    """An imported archive may be read; it must not instruct.

    `CLAUDE.md`, `AGENTS.md` and `.cursorrules` are read as instructions by the
    agents that work in this tree.  The archive shipped a `CLAUDE.md` asserting
    "All theorems are verified (lake build passes)" -- a claim about a different
    build, which the manifest measures to be impossible here.  It was renamed on
    import with its bytes untouched.  The rule generalises to future vendoring,
    so the assertion is over the whole directory rather than the one filename.
    """
    hazards = {"CLAUDE.md", "AGENTS.md", ".cursorrules", "GEMINI.md", ".clinerules"}
    found = [str(path.relative_to(ROOT))
             for path in census.LEANMATH_ROOT.rglob("*")
             if path.is_file() and path.name in hazards]

    assert not found, f"vendored instruction file(s) would be loaded as ours: {found}"
    assert (census.LEANMATH_ROOT / "IMPORTED_CLAUDE.md").exists()
    assert "lake build passes" in (
        census.LEANMATH_ROOT / "IMPORTED_CLAUDE.md").read_text(encoding="utf-8"), (
        "the renamed file no longer carries the claim the rename was for; "
        "re-check finding_2 in the manifest")


def test_the_archive_is_inert_with_respect_to_the_library():
    """Nothing under `src/aionq` imports it, and nothing could.

    Vendored Lean is data.  `lean_census` reads the files as bytes and is the
    only module that names the directory at all; if a second module ever starts
    depending on the archive, the UNVERIFIED label has stopped being honest.
    """
    import re

    reaching, importing = [], []
    for path in sorted((ROOT / "src" / "aionq").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "LEANMATH_ROOT" in text or '"leanmath"' in text:
            reaching.append(path.name)
        if re.search(r"^\s*(from\s+\S*\blean_census\b|import\s+\S*\blean_census\b)",
                     text, flags=re.MULTILINE):
            importing.append(path.name)

    assert reaching == ["lean_census.py"], (
        f"the unverified archive has acquired readers: {reaching}")
    assert not importing, (
        f"the unverified archive has acquired dependents: {importing}")


def test_native_lean_project_is_pinned_and_vendor_is_separate():
    """Test the current reproducibility contract, not a past runner's PATH.

    The archived LeanMath toolchain (v4.32.0-rc1) remains an inert historical
    input. Native AION proofs now build in their own pinned Lean/Mathlib project,
    with an independent workflow. An obsolete assertion about where one prior
    machine installed Lean must not be allowed to override that contract.
    """
    formal = ROOT / "formal"
    readme = (formal / "README.md").read_text(encoding="utf-8")
    native_toolchain = (formal / "lean-toolchain").read_text(encoding="utf-8").strip()
    lakefile = (formal / "lakefile.lean").read_text(encoding="utf-8")
    lock = json.loads((formal / "lake-manifest.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github" / "workflows" / "lean.yml").read_text(encoding="utf-8")
    vendor_toolchain = (formal / "leanmath" / "lean-toolchain").read_text(
        encoding="utf-8"
    ).strip()

    assert native_toolchain.startswith("leanprover/lean4:v")
    assert native_toolchain.split(":")[-1] in readme
    assert lock["name"] == "aionformal"
    mathlib = next(pkg for pkg in lock["packages"] if pkg["name"] == "mathlib")
    assert mathlib["type"] == "git"
    assert len(mathlib["rev"]) == 40
    assert mathlib["rev"] == mathlib["inputRev"]
    assert mathlib["rev"] in lakefile
    assert mathlib["rev"] in readme
    assert "lake build" in readme
    assert "ProofAudit.lean" in readme
    assert "lake-package-directory: formal" in workflow

    assert vendor_toolchain == "leanprover/lean4:v4.32.0-rc1"
    assert vendor_toolchain != native_toolchain
    assert "leanmath/" in readme
    assert "unverified" in readme.lower()
    assert "UNVERIFIED IMPORTED MATERIAL" in PROVENANCE.read_text(encoding="utf-8")
    assert "`lean`, `lake` and `elan` are present on `PATH`" not in readme

def test_the_provenance_note_reports_what_the_census_measures():
    """The prose and the instrument must not drift apart -- the whole point."""
    text = PROVENANCE.read_text(encoding="utf-8")
    measured = census.census()

    assert "UNVERIFIED IMPORTED MATERIAL" in text
    assert f"{measured['bytes']:_d}".replace("_", " ") in text
    assert f"{measured['unlexable_bytes']:_d}".replace("_", " ") in text
    assert str(measured["imports_by_status"]["absent"]) in text
    assert "9 of 11" in text
