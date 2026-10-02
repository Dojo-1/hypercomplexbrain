"""Fail-closed corpus-catalog checks for the envelope verifier."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import aionq.verify_envelopes as verifier


def _row(path: object = "artifacts/example/example.envelope.json",
         claim_id: object = "CLAIM-EXAMPLE") -> dict:
    return {"path": path, "claim_id": claim_id}


def _catalog(rows, *, root: object = "artifacts", **extra) -> dict:
    payload = {
        "schema": verifier.CATALOG_SCHEMA,
        "root": root,
        "envelopes": rows,
    }
    payload.update(extra)
    return payload


def _write_catalog(repo: Path, payload: object) -> Path:
    path = repo / verifier.CATALOG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_envelope(repo: Path, relative: str, claim_id: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "claim_id": claim_id,
        "evidence_tag": "M",
        "command": "run-example",
        "observed_result": {},
    }), encoding="utf-8")
    return path


@pytest.mark.parametrize("raw", ["{", "null", "[]", "42", '"catalog"'])
def test_malformed_null_and_nonobject_catalogs_are_failures_not_exceptions(
    tmp_path,
    raw,
):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    catalog = tmp_path / verifier.CATALOG
    catalog.parent.mkdir()
    catalog.write_text(raw, encoding="utf-8")

    failures = verifier._catalog_failures([], catalog, artifacts)

    assert failures
    assert any("catalog" in failure for failure in failures)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_schema"])
def test_catalog_top_level_schema_is_exact(tmp_path, mutation):
    payload = _catalog([_row()])
    if mutation == "missing":
        del payload["root"]
    elif mutation == "extra":
        payload["comment"] = "not part of the denominator schema"
    else:
        payload["schema"] = "hypercomplexbrain.evidence_catalog.v999"
    catalog = _write_catalog(tmp_path, payload)

    failures = verifier._catalog_failures(
        [], catalog, tmp_path / "artifacts"
    )

    assert failures
    if mutation in {"missing", "extra"}:
        assert any("top-level fields differ" in failure for failure in failures)
    else:
        assert any("schema must be" in failure for failure in failures)


@pytest.mark.parametrize("root", [None, 7, "", ".", "artifact", "Artifacts"])
def test_catalog_root_is_exactly_artifacts(tmp_path, root):
    catalog = _write_catalog(tmp_path, _catalog([_row()], root=root))

    failures = verifier._catalog_failures(
        [], catalog, tmp_path / "artifacts"
    )

    assert any("root must be the string 'artifacts'" in failure for failure in failures)


@pytest.mark.parametrize("field,bad", [
    ("path", None),
    ("path", 7),
    ("path", ""),
    ("path", " artifacts/example.envelope.json"),
    ("claim_id", None),
    ("claim_id", 7),
    ("claim_id", ""),
    ("claim_id", " CLAIM"),
])
def test_catalog_row_values_are_typed_nonempty_strings_without_coercion(
    tmp_path,
    field,
    bad,
):
    row = _row()
    row[field] = bad
    catalog = _write_catalog(tmp_path, _catalog([row]))

    failures = verifier._catalog_failures(
        [], catalog, tmp_path / "artifacts"
    )

    assert any(f"{field} must be a nonempty string" in failure for failure in failures)


@pytest.mark.parametrize("bad", [
    "/artifacts/example.envelope.json",
    "../artifacts/example.envelope.json",
    "artifacts/../example.envelope.json",
    "artifacts\\example.envelope.json",
    "elsewhere/example.envelope.json",
    "C:/artifacts/example.envelope.json",
    "artifacts//example.envelope.json",
])
def test_catalog_paths_are_canonical_relative_paths_below_artifacts(tmp_path, bad):
    catalog = _write_catalog(tmp_path, _catalog([_row(path=bad)]))

    failures = verifier._catalog_failures(
        [], catalog, tmp_path / "artifacts"
    )

    assert any("canonical relative path below artifacts" in failure
               for failure in failures)


def test_catalog_enforces_unique_paths_and_one_canonical_envelope_per_claim(tmp_path):
    catalog = _write_catalog(tmp_path, _catalog([
        _row("artifacts/a.envelope.json", "CLAIM-A"),
        _row("artifacts/a.envelope.json", "CLAIM-B"),
        _row("artifacts/b.envelope.json", "CLAIM-A"),
    ]))

    failures = verifier._catalog_failures(
        [], catalog, tmp_path / "artifacts"
    )

    assert "evidence catalog contains duplicate paths" in failures
    assert any("one canonical envelope per claim" in failure for failure in failures)


def test_catalog_detects_two_files_reusing_one_claim_id(tmp_path):
    artifacts = tmp_path / "artifacts"
    first = _write_envelope(
        tmp_path, "artifacts/a.envelope.json", "CLAIM-A"
    )
    second = _write_envelope(
        tmp_path, "artifacts/b.envelope.json", "CLAIM-A"
    )
    catalog = _write_catalog(tmp_path, _catalog([
        _row("artifacts/a.envelope.json", "CLAIM-A"),
        _row("artifacts/b.envelope.json", "CLAIM-B"),
    ]))

    failures = verifier._catalog_failures(
        [first, second], catalog, artifacts
    )

    assert any("one canonical envelope per claim" in failure for failure in failures)


def test_catalog_function_accepts_absolute_envelope_paths(tmp_path):
    artifacts = tmp_path / "artifacts"
    envelope = _write_envelope(
        tmp_path, "artifacts/example/example.envelope.json", "CLAIM-EXAMPLE"
    )
    catalog = _write_catalog(tmp_path, _catalog([_row()]))

    failures = verifier._catalog_failures(
        [envelope.resolve()], catalog.resolve(), artifacts.resolve()
    )

    assert failures == []


def test_cli_function_supports_an_absolute_artifacts_root(
    tmp_path,
    monkeypatch,
    capsys,
):
    artifacts = tmp_path / "artifacts"
    _write_envelope(
        tmp_path, "artifacts/example/example.envelope.json", "CLAIM-EXAMPLE"
    )
    _write_catalog(tmp_path, _catalog([_row()]))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    seen_roots = []

    def fake_verify(_envelope, repo_root):
        seen_roots.append(Path(repo_root))
        return SimpleNamespace(
            ok=True, effective_n=1, independent=False, failures=[], warnings=[]
        )

    monkeypatch.setattr(verifier, "verify", fake_verify)

    assert verifier.main([str(artifacts.resolve())]) == 0
    assert seen_roots == [tmp_path.resolve()]
    assert "1/1 envelopes verified" in capsys.readouterr().out


def test_cli_catalog_failure_reports_denominator_failure_not_verified_corpus(
    tmp_path,
    monkeypatch,
    capsys,
):
    artifacts = tmp_path / "artifacts"
    _write_envelope(
        tmp_path, "artifacts/example/example.envelope.json", "CLAIM-EXAMPLE"
    )
    catalog = tmp_path / verifier.CATALOG
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text("null", encoding="utf-8")
    monkeypatch.setattr(
        verifier,
        "verify",
        lambda _envelope, repo_root: SimpleNamespace(
            ok=True, effective_n=1, independent=False, failures=[], warnings=[]
        ),
    )

    assert verifier.main([str(artifacts.resolve())]) == 1
    output = capsys.readouterr().out
    assert "FAIL evidence corpus/denominator failed" in output
    assert "not a corpus verification result" in output
    assert "1/1 envelopes verified" not in output


def test_cli_rejects_a_non_artifacts_scan_root(tmp_path, monkeypatch, capsys):
    evidence = tmp_path / "evidence"
    _write_envelope(tmp_path, "evidence/example.envelope.json", "CLAIM-EXAMPLE")
    _write_catalog(tmp_path, _catalog([_row("artifacts/example.envelope.json")]))
    monkeypatch.setattr(
        verifier,
        "verify",
        lambda _envelope, repo_root: SimpleNamespace(
            ok=True, effective_n=1, independent=False, failures=[], warnings=[]
        ),
    )

    assert verifier.main([str(evidence.resolve())]) == 1
    output = capsys.readouterr().out
    assert "scan root must be the artifacts directory" in output
    assert "corpus/denominator failed" in output


def test_live_corpus_catalogs_every_committed_envelope():
    # Every test above runs on a synthetic tree. CI's envelope step was red
    # from 140dbe8 to its repair because the Part B envelope was committed
    # without a catalog row, and nothing in the suite looked at the live
    # corpus -- so the suite was green while the step was not.
    root = Path(__file__).resolve().parent.parent
    artifacts = root / "artifacts"
    envelopes = sorted(artifacts.rglob("*.envelope.json"))
    assert envelopes
    failures = verifier._catalog_failures(
        envelopes, root / verifier.CATALOG, artifacts
    )
    assert failures == []
