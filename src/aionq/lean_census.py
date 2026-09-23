"""A census of the vendored Lean sources, computed rather than transcribed.

`formal/leanmath/` holds an archive supplied by the repository owner: a Lean 4
formalisation of the Cayley-Dickson tower, a finite Dirac operator, a connection
Laplacian, halting statements over the octonions, and a five-carrier
"hardness holonomy" file.  Nothing in it is checked here.  There is no Lean
toolchain with the pinned `v4.32.0-rc1` and no vendored Mathlib, and -- the part
that matters more -- **17 of the 20 internal modules the archive imports are not
in the archive**, so `lake build` could not succeed on it under any toolchain.

That makes the archive imported unverified material, and this repository's whole
discipline is that unverified material must be *labelled* by an instrument, not
by a sentence in a README that drifts.  Hence this module.  Everything the
manifest and the docs say about the archive is derived here from the bytes, so
a claim about it cannot outlive the file it describes.

Two things it measures are findings in their own right, both about the archive's
own self-description:

* `HardnessHolonomy.lean` names the surviving placeholders as "CD.lean:363,366;
  TuringHalting_Master.lean:362,393".  Measured: `CD.lean` has **no** placeholder
  in any proof body, `TuringHalting_Master.lean`'s two are at 376 and 407, and
  `ConnectionLaplacian.lean:789` carries a third that the note does not mention.
  The archive's placeholder ledger is stale in both directions at once.

* `IMPORTED_CLAUDE.md` (renamed on import, see `PROVENANCE.md`) states "All
  theorems are verified (lake build passes)".  That cannot be a statement about
  this archive, because this archive cannot be built.  It is a statement about
  the larger `LambdaSatSolver` tree these files were extracted from, and it does
  not transfer.

Comment- and string-aware scanning is the whole reason this is code and not a
`grep`: `grep -c sorry` counts 16 across the tree, of which **3** are in a proof
body.  The other 13 are prose about placeholders, including the sentence that
claims there are none.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "LEANMATH_ROOT",
    "MODULE_PREFIX",
    "strip_noncode",
    "lean_sources",
    "module_name",
    "imports",
    "resolve_imports",
    "code_placeholders",
    "comment_balance",
    "digests",
    "census",
]

#: Where the archive was vendored.  Resolved from this file so a moved checkout
#: does not silently census an empty directory.
LEANMATH_ROOT = Path(__file__).resolve().parents[2] / "formal" / "leanmath"

#: The namespace the archive's own `import` lines assume.  The archive is laid
#: out as if it were the *contents* of `LambdaSatSolver/VDIS/`, but its
#: `lakefile.toml` declares the package `leanmath`, so even the modules that are
#: present do not sit where their importers look for them.
MODULE_PREFIX = "LambdaSatSolver.VDIS."


def strip_noncode(text: str) -> str:
    """Blank out Lean comments and string literals, preserving every offset.

    Returns a string of the same length as ``text`` in which comment and string
    characters have become spaces and newlines are kept, so a match found in the
    result has the line and column it had in the source.  Lean 4 block comments
    ``/- ... -/`` nest, and ``/-! ... -/`` doc comments are the same token with a
    marker, so a depth counter is required rather than a regex.
    """
    out = list(text)
    index, length, depth = 0, len(text), 0
    while index < length:
        char = text[index]
        if depth:
            if text.startswith("/-", index):
                depth += 1
                out[index] = out[index + 1] = " "
                index += 2
                continue
            if text.startswith("-/", index):
                depth -= 1
                out[index] = out[index + 1] = " "
                index += 2
                continue
            if char != "\n":
                out[index] = " "
            index += 1
            continue
        if text.startswith("/-", index):
            depth = 1
            out[index] = out[index + 1] = " "
            index += 2
            continue
        if text.startswith("--", index):
            while index < length and text[index] != "\n":
                out[index] = " "
                index += 1
            continue
        if char == '"':
            out[index] = " "
            index += 1
            while index < length:
                if text[index] == "\\" and index + 1 < length:
                    out[index] = out[index + 1] = " "
                    index += 2
                    continue
                closing = text[index] == '"'
                if text[index] != "\n":
                    out[index] = " "
                index += 1
                if closing:
                    break
            continue
        index += 1
    return "".join(out)


def lean_sources(root: Path = LEANMATH_ROOT) -> tuple:
    """Every vendored `.lean` file, as paths relative to the archive root."""
    return tuple(sorted(path.relative_to(root)
                        for path in root.rglob("*.lean")))


def module_name(relative: Path) -> str:
    """The module name a file would carry if the root were `LambdaSatSolver/VDIS`."""
    return MODULE_PREFIX + ".".join(relative.with_suffix("").parts)


def imports(path: Path) -> tuple:
    """Every `import` of an internal module, in file order.

    `import Mathlib` is excluded: it names an external dependency, which is a
    different kind of absence from a module the archive claims as its own.
    """
    found = re.findall(r"^import\s+(LambdaSatSolver\S*)\s*$",
                       strip_noncode(path.read_text(encoding="utf-8")),
                       flags=re.MULTILINE)
    return tuple(found)


@dataclass(frozen=True)
class ImportStatus:
    """One internal import, and whether the archive can satisfy it."""

    module: str
    #: "resolves" -- a file sits at exactly the imported path;
    #: "basename_only" -- a file of that name exists at a *different* path, so
    #: the content is present but the import as written still fails;
    #: "absent" -- no file of that name anywhere in the archive.
    status: str
    candidates: tuple = ()
    importers: tuple = ()


def resolve_imports(root: Path = LEANMATH_ROOT) -> tuple:
    """Decide each internal import against the files actually vendored."""
    sources = lean_sources(root)
    exact = {module_name(relative): relative for relative in sources}
    by_stem: dict = {}
    for relative in sources:
        by_stem.setdefault(relative.stem, []).append(relative.as_posix())

    importers: dict = {}
    for relative in sources:
        for module in imports(root / relative):
            importers.setdefault(module, []).append(relative.as_posix())

    out = []
    for module in sorted(importers):
        candidates = tuple(sorted(by_stem.get(module.rsplit(".", 1)[-1], ())))
        if module in exact:
            status = "resolves"
        elif candidates:
            status = "basename_only"
        else:
            status = "absent"
        out.append(ImportStatus(module=module, status=status,
                                candidates=candidates,
                                importers=tuple(sorted(importers[module]))))
    return tuple(out)


def code_placeholders(root: Path = LEANMATH_ROOT) -> dict:
    """Line numbers of `sorry`/`admit`/`axiom` that are in code, not in prose.

    Keyed by relative path; only files with at least one hit appear.  A `sorry`
    inside a comment is documentation about a placeholder and is not one, and
    this archive contains four times more of the former than of the latter.
    """
    pattern = re.compile(r"\b(sorry|admit|axiom)\b")
    out: dict = {}
    for relative in lean_sources(root):
        code = strip_noncode((root / relative).read_text(encoding="utf-8"))
        hits = tuple(sorted(
            (code[:match.start()].count("\n") + 1, match.group(1))
            for match in pattern.finditer(code)))
        if hits:
            out[relative.as_posix()] = hits
    return out


def comment_balance(root: Path = LEANMATH_ROOT) -> dict:
    """Files whose block comments never close, and where each opener sits.

    This is the sharpest thing the census measures, because it is the one thing
    that no missing dependency could excuse.  Lean 4's ``/- ... -/`` nests, and
    ``/-!`` and ``/--`` are the same token with a marker, so an unmatched opener
    swallows the rest of the file -- code, theorems, placeholders and all -- into
    a comment that never ends.

    Measured: two of eleven files, `TuringHalting_Master.lean` (opener at line
    69) and `TuringHalting_Hyperdim.lean` (opener at line 9), are unterminated.
    That is 149 KB, 39% of the archive's bytes, that cannot lex.  The verdict is
    not inferred from this counter alone: Lean 4.32.0-rc1 -- the archive's own
    pinned toolchain -- reports `unterminated comment` at end of file for exactly
    these two and no others.  See `manifests/leanmath_import_v1.json`.

    The consequence for the placeholder census is worth stating plainly.  The two
    `sorry` tokens at `TuringHalting_Master.lean:376,407` look like live
    placeholders to `grep`, and the archive's own note gestures at them.  As the
    file actually lexes they are inside a comment, along with every theorem after
    line 69.  They are not placeholders in proofs; there are no proofs there.
    """
    out: dict = {}
    opener = re.compile(r"/-|-/")
    for relative in lean_sources(root):
        text = (root / relative).read_text(encoding="utf-8")
        depth, opened = 0, []
        for match in opener.finditer(text):
            if match.group(0) == "/-":
                depth += 1
                opened.append(text[:match.start()].count("\n") + 1)
            elif depth:
                depth -= 1
                opened.pop()
        if depth:
            out[relative.as_posix()] = {
                "unclosed": depth,
                "opened_at": tuple(opened),
            }
    return out


def digests(root: Path = LEANMATH_ROOT) -> dict:
    """SHA-256 of every vendored file, `.lean` or not, keyed by relative path."""
    return {
        path.relative_to(root).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def census(root: Path = LEANMATH_ROOT) -> dict:
    """The whole measurement, in the shape the manifest records."""
    resolution = resolve_imports(root)
    placeholders = code_placeholders(root)
    unbalanced = comment_balance(root)
    return {
        "root": root.relative_to(root.parents[1]).as_posix(),
        "files": len(digests(root)),
        "lean_files": len(lean_sources(root)),
        "bytes": sum(path.stat().st_size
                     for path in root.rglob("*") if path.is_file()),
        "internal_imports": len(resolution),
        "imports_by_status": {
            status: sum(1 for entry in resolution if entry.status == status)
            for status in ("resolves", "basename_only", "absent")
        },
        "buildable": all(entry.status == "resolves" for entry in resolution),
        "code_placeholders": sum(len(hits) for hits in placeholders.values()),
        "code_placeholder_sites": placeholders,
        "unterminated_comments": unbalanced,
        "lexable_files": len(lean_sources(root)) - len(unbalanced),
        "unlexable_bytes": sum((root / name).stat().st_size
                               for name in unbalanced),
        "digests": digests(root),
    }
