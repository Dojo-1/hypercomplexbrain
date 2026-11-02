"""Stable publication rights metadata without freezing editorial wording.

The license/citation boundary is part of the public research contract.
Only invariant links and rights metadata are checked; do not turn tests into
a copy-editing constraint on README prose.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cc_by_4_full_license_is_committed():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Creative Commons Attribution 4.0 International" in text
    assert "Section 3" in text and "Attribution" in text
    assert "Section 8" in text


def test_practical_author_and_license_notices_exist():
    notice = (ROOT / "ATTRIBUTION.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Jesús Vilela Jato" in notice
    assert "https://creativecommons.org/licenses/by/4.0/" in notice
    assert "Other human contributors" in notice
    assert "third-party materials" in notice.lower()
    assert "AI assistance" in notice

    assert "cff-version: 1.2.0" in citation
    assert "family-names: \"Vilela Jato\"" in citation
    assert "given-names: \"Jesús\"" in citation
    assert 'license: "CC-BY-4.0"' in citation

    for path in ["LICENSE", "ATTRIBUTION.md", "CITATION.cff"]:
        assert (ROOT / path).is_file()
        assert f"]({path})" in readme

    assert "independent" in readme.lower()
    assert "quantum advantage" in readme.lower()
