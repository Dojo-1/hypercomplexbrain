"""Verify every committed EvidenceEnvelope.  Exit 1 if any fails.

R4-E.  This is the CI-facing half of the membrane: without it, envelopes are
files nobody reads, which is the ceremonial outcome the round preregistered as
its kill condition.

    python -m aionq.verify_envelopes artifacts
"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath

from .evidence import load_envelope, verify

CATALOG = Path("manifests/evidence_envelope_catalog.json")
CATALOG_SCHEMA = "hypercomplexbrain.evidence_catalog.v1"
CATALOG_ROOT = "artifacts"
CATALOG_FIELDS = frozenset({"schema", "root", "envelopes"})
CATALOG_ROW_FIELDS = frozenset({"path", "claim_id"})


def _catalog_failures(
    paths: list[Path],
    catalog_path: Path = CATALOG,
    artifact_root: Path = Path(CATALOG_ROOT),
) -> list[str]:
    """Detect denominator drift without trusting or coercing catalog values.

    The catalog defines one canonical path for one canonical claim.  Both sides
    are unique: two rows may not name the same path, and a claim may not acquire
    multiple canonical envelopes.  Historical or superseded evidence therefore
    needs its own claim ID rather than a second row for the same claim.

    This function is deliberately total over catalog bytes and decoded JSON.
    A malformed, null, scalar, or otherwise mistyped catalog is a corpus failure,
    never an exception that bypasses the denominator check.
    """

    catalog_path = Path(catalog_path)
    artifact_root = Path(artifact_root)
    try:
        if not catalog_path.is_file():
            return [f"evidence catalog missing: {catalog_path}"]
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"evidence catalog unreadable: {exc}"]

    if type(payload) is not dict:
        return ["evidence catalog must be one JSON object"]

    failures: list[str] = []
    payload_fields = set(payload)
    if payload_fields != CATALOG_FIELDS:
        failures.append(
            "evidence catalog top-level fields differ: "
            f"missing={sorted(CATALOG_FIELDS - payload_fields)}, "
            f"extra={sorted(payload_fields - CATALOG_FIELDS)}"
        )
    if payload.get("schema") != CATALOG_SCHEMA:
        failures.append(f"evidence catalog schema must be {CATALOG_SCHEMA!r}")
    if type(payload.get("root")) is not str or payload.get("root") != CATALOG_ROOT:
        failures.append("evidence catalog root must be the string 'artifacts'")

    rows = payload.get("envelopes")
    if type(rows) is not list or not rows:
        failures.append("evidence catalog envelopes must be a nonempty JSON list")
        return failures

    expected_paths: list[str] = []
    expected_claims: list[str] = []
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != CATALOG_ROW_FIELDS:
            failures.append(
                f"evidence catalog row {index} must have exactly path and claim_id"
            )
            continue

        relative = row["path"]
        claim_id = row["claim_id"]
        if type(relative) is not str or not relative or relative.strip() != relative:
            failures.append(
                f"evidence catalog row {index} path must be a nonempty string"
            )
            continue
        if type(claim_id) is not str or not claim_id or claim_id.strip() != claim_id:
            failures.append(
                f"evidence catalog row {index} claim_id must be a nonempty string"
            )
            continue

        portable = PurePosixPath(relative)
        if (
            "\\" in relative
            or portable.is_absolute()
            or not portable.parts
            or ".." in portable.parts
            or portable.as_posix() != relative
            or portable.parts[0] != CATALOG_ROOT
        ):
            failures.append(
                f"evidence catalog row {index} path must be a canonical relative "
                "path below artifacts"
            )
            continue

        expected_paths.append(relative)
        expected_claims.append(claim_id)

    if len(expected_paths) != len(set(expected_paths)):
        failures.append("evidence catalog contains duplicate paths")
    if len(expected_claims) != len(set(expected_claims)):
        failures.append(
            "evidence catalog contains duplicate claim IDs; one canonical "
            "envelope per claim is required"
        )

    try:
        resolved_root = artifact_root.resolve()
        repo_root = resolved_root.parent
    except OSError as exc:
        failures.append(f"artifact root cannot be resolved: {exc}")
        return failures

    actual_paths: list[str] = []
    actual_by_relative: dict[str, Path] = {}
    for path in paths:
        path = Path(path)
        try:
            resolved = path.resolve()
            resolved.relative_to(resolved_root)
            relative = resolved.relative_to(repo_root).as_posix()
        except (OSError, ValueError) as exc:
            failures.append(f"discovered envelope lies outside catalog root: {path}: {exc}")
            continue
        actual_paths.append(relative)
        actual_by_relative[relative] = path

    if len(actual_paths) != len(set(actual_paths)):
        failures.append("discovered envelope paths are not unique")
    missing = sorted(set(expected_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected_paths))
    if missing:
        failures.append("catalogued envelopes missing: " + ", ".join(missing))
    if extra:
        failures.append("uncatalogued envelopes present: " + ", ".join(extra))
    expected_by_path = dict(zip(expected_paths, expected_claims))
    actual_claims: list[str] = []
    for relative in sorted(set(actual_paths) & set(expected_by_path)):
        path = actual_by_relative[relative]
        try:
            claim_id = load_envelope(path).claim_id
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            failures.append(f"catalogued envelope unreadable {relative}: {exc}")
            continue
        actual_claims.append(claim_id)
        if claim_id != expected_by_path[relative]:
            failures.append(
                f"catalog claim mismatch for {relative}: "
                f"{claim_id!r} != {expected_by_path[relative]!r}")
    if len(actual_claims) != len(set(actual_claims)):
        failures.append(
            "discovered envelopes reuse a claim ID; one canonical envelope per "
            "claim is required"
        )
    return failures


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path("artifacts")
    resolved_root = root.resolve()
    repo_root = resolved_root.parent
    paths = sorted(resolved_root.rglob("*.envelope.json"))

    catalog_failures: list[str] = []
    if resolved_root.name != CATALOG_ROOT:
        catalog_failures.append("envelope scan root must be the artifacts directory")
    catalog_path = repo_root / CATALOG
    catalog_failures.extend(
        _catalog_failures(paths, catalog_path=catalog_path, artifact_root=resolved_root)
    )
    if not paths:
        catalog_failures.append(
            f"no envelopes under {resolved_root} -- evidence denominator is zero"
        )
    for failure in catalog_failures:
        print(f"FAIL catalog: {failure}")

    failed = 0
    for path in paths:
        result = verify(load_envelope(path), repo_root=repo_root)
        mark = "ok  " if result.ok else "FAIL"
        print(f"{mark} {path}  n_eff={result.effective_n} "
              f"independent={result.independent}")
        for f in result.failures:
            print(f"       FAIL  {f}")
        for w in result.warnings:
            print(f"       warn  {w}")
        failed += not result.ok

    passed = len(paths) - failed
    if catalog_failures:
        print(
            "\nFAIL evidence corpus/denominator failed: "
            f"{len(catalog_failures)} catalog issue(s); individual envelope "
            f"checks passed {passed}/{len(paths)} (not a corpus verification result)"
        )
    else:
        print(f"\n{passed}/{len(paths)} envelopes verified")
    return 1 if failed or catalog_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
