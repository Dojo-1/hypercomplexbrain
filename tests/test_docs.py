"""Documentation must respect the evidence ledger and its supersessions.

The repository accumulated a *revision superposition*: §0.6 retired an
empirical inference from free-theory tree-likeness, while HB0 later reinstated a
Poincaré atlas as an A-tagged architectural contract.  The scalar promotion
gate remains retired. Prose drifts out of step with code silently, so the ledger
is checked mechanically here.

Rule: a retired phrase may appear only in a section that is explicitly
historical (a correction ledger, a falsification table, an evidence ledger), or
on a line that marks it as retired.
"""

from __future__ import annotations

import pathlib
import re

import pytest

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Present-tense assertions of claims this repository has retired.
RETIRED_PHRASES = [
    "The promotion gate is `q_causal > 0`",
    "the free-theory graph empirically proves the Poincaré metric",
    "the coordinates are still untyped floats",
    "Q_cert is the fraction",
    "self-tomography is impossible",
]

# Markers that make a line or section historical rather than assertive.
HISTORICAL_MARKERS = (
    "retire", "Retire", "RETIRED", "falsif", "Falsif", "FALSIFIED",
    "was ", "were ", "formerly", "Formerly", "no longer", "used to",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "K1",
    "correction", "Correction", "ledger", "Ledger", "*this was",
)

HISTORICAL_SECTIONS = (
    "What the peer audit corrected",
    "The second audit",
    "self-review",
    "Falsification programme",
    "Evidence ledger",
    "The remainder",
)


def _sections(text: str):
    """Split markdown into (heading, body) pairs."""
    parts = re.split(r"^(#{1,4} .*)$", text, flags=re.M)
    out, heading = [], "(preamble)"
    for chunk in parts:
        if chunk.startswith("#"):
            heading = chunk.strip("# ").strip()
        else:
            out.append((heading, chunk))
    return out


def _offending_lines(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    bad = []
    for heading, body in _sections(text):
        if any(h.lower() in heading.lower() for h in HISTORICAL_SECTIONS):
            continue
        for i, line in enumerate(body.splitlines()):
            for phrase in RETIRED_PHRASES:
                if phrase in line and not any(m in line for m in HISTORICAL_MARKERS):
                    bad.append(f"{path.name} [{heading}]: {line.strip()[:110]}")
    return bad


@pytest.mark.parametrize("doc", ["ARCHITECTURE.md", "SOURCES_DIGEST.md"])
def test_docs_do_not_assert_retired_claims(doc):
    bad = _offending_lines(DOCS / doc)
    assert not bad, "retired claims asserted as current:\n" + "\n".join(bad)


def test_readme_does_not_assert_retired_claims():
    bad = _offending_lines(ROOT / "README.md")
    assert not bad, "retired claims asserted as current:\n" + "\n".join(bad)


def test_every_registered_retired_claim_is_in_the_ledger():
    """Each RET-* claim must be discussed somewhere in the architecture doc."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from aionq.governance import registry, EvidenceTag
    text = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    missing = [c.id for c in registry.by_tag(EvidenceTag.RETIRED)
               if not any(w in text for w in c.statement.split()[:3])]
    assert not missing, f"retired claims absent from the ledger: {missing}"
