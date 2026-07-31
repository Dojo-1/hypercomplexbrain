#!/usr/bin/env python3
"""Run the hash-frozen QSigma-R6k equal-resource reservoir protocol once.

    python experiments/run_equal_resource_reservoir.py

The output is append-once.  This runner refuses to overwrite a result, envelope,
or JSONL trace, refuses a changed preregistration, and checks that the two
pre-existing modified S4/G100 artifacts remain byte-identical before and after
the experiment.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.equal_resource_reservoir import (
    AMBIENT_DIM,
    CODEWORDS_PER_DEPTH,
    DEPTHS,
    NOISE_STRENGTHS,
    build_map_tasks,
    classify_protocol,
    run_protocol,
    validate_protocol_grid,
)
from aionq.evidence import (
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    verify,
)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "qsigma_r6k_equal_resource_reservoir_preregistration.json"
CORRECTION = ROOT / "manifests" / "qsigma_r6k_equal_resource_reservoir_method_correction.json"
OUT = ROOT / "artifacts" / "r6k_equal_resource_reservoir"
RESULT = OUT / "equal_resource_reservoir.json"
ENVELOPE = OUT / "equal_resource_reservoir.envelope.json"
EVENTS = OUT / "events.jsonl"

EXPECTED_MANIFEST_SHA256 = "c633d4fbbfa9a639bfe6a75857f583654be252118cebc8627f0db0c8feef7d3b"
EXPECTED_CORRECTION_SHA256 = "aaa26bbd1cd5db9e222848734aa8d0e51e586be656a002598e3e3346c1f333ee"
PRESERVED = {
    ROOT / "artifacts" / "s4_g100" / "summaries" / "acaf_frame_sweep.json": (
        "f94809ca6b3df2c8991155cdbfae06f5125996739651a720fb23f6898e254529"
    ),
    ROOT / "artifacts" / "s4_g100" / "summaries" / "moving_frame_audit.json": (
        "cfd3128d5af7563b95debed4b6dd2f833df0adb5b19b2756d805f50becb02eca"
    ),
}

BOUND_INPUT_PATHS = (
    MANIFEST,
    CORRECTION,
    Path(__file__).resolve(),
    ROOT / "src" / "aionq" / "coherent_dilation.py",
    ROOT / "src" / "aionq" / "equal_resource_reservoir.py",
    ROOT / "src" / "aionq" / "hyperbolic_qubit.py",
    ROOT / "src" / "aionq" / "quantum_channel_geometry.py",
    ROOT / "src" / "aionq" / "holevo_sandwich.py",
    ROOT / "src" / "aionq" / "evidence.py",
    ROOT / "tests" / "test_coherent_dilation.py",
    ROOT / "tests" / "test_equal_resource_reservoir.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _preserved_checks() -> dict[str, bool]:
    return {
        path.relative_to(ROOT).as_posix(): _sha256(path) == expected
        for path, expected in PRESERVED.items()
    }


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_once(path: Path, payload: object) -> None:
    data = _canonical_bytes(payload)  # force finite/JSON validation before create
    with path.open("xb") as handle:
        handle.write(data)


def _refuse_existing_outputs() -> None:
    if OUT.exists():
        raise FileExistsError(
            "append-once R6k output directory already exists: "
            f"{OUT.relative_to(ROOT).as_posix()}"
        )


def _manifest_contract_checks() -> dict[str, bool]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    correction = json.loads(CORRECTION.read_text(encoding="utf-8"))
    return {
        "ambient_dimension_matches_module": (
            manifest["matched_resources"]["ambient_dimension"] == AMBIENT_DIM
        ),
        "depths_match_module": tuple(
            manifest["frozen_source_grid"]["depths"]
        ) == DEPTHS,
        "codeword_count_matches_module": (
            manifest["frozen_source_grid"]["signed_codewords_per_depth"]
            == CODEWORDS_PER_DEPTH
        ),
        "noise_strengths_match_module": tuple(
            manifest["noise"]["strengths"]
        ) == NOISE_STRENGTHS,
        "correction_binds_original_manifest": (
            correction["superseded_protocol_component"]["sha256"]
            == "sha256:" + EXPECTED_MANIFEST_SHA256
        ),
        "correction_requires_pre_result_status": (
            correction["outcome_status"]["primary_result_visible"] is False
        ),
    }


def _validate_event_trace(report: dict) -> dict[str, bool]:
    lines = EVENTS.read_text(encoding="utf-8").splitlines()

    def reject_constant(value: str):
        raise ValueError(f"nonfinite JSON constant {value}")

    events = [json.loads(line, parse_constant=reject_constant) for line in lines]
    expected_count = report["reservoir"]["event_count"]
    keys = [event.get("key") for event in events]
    sequences = [event.get("sequence") for event in events]
    digests = [event.get("state_digest") for event in events]
    return {
        "event_trace_exists": EVENTS.is_file(),
        "event_trace_line_count_matches": len(events) == expected_count == 320,
        "event_sequences_contiguous": sequences == list(range(expected_count)),
        "event_keys_unique": len(keys) == len(set(keys)) == expected_count,
        "event_state_digests_present": all(
            isinstance(value, str)
            and value.startswith("sha256:")
            and len(value) == 71
            for value in digests
        ),
        "event_semantic_digest_matches_report": (
            _canonical_digest(events) == report["reservoir"]["event_digest"]
        ),
    }


def main() -> int:
    _refuse_existing_outputs()
    manifest_hash = _sha256(MANIFEST)
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(
            "R6k preregistration changed after its final hash freeze: "
            f"expected {EXPECTED_MANIFEST_SHA256}, found {manifest_hash}"
        )
    correction_hash = _sha256(CORRECTION)
    if correction_hash != EXPECTED_CORRECTION_SHA256:
        raise RuntimeError(
            "R6k method correction changed after its hash freeze: "
            f"expected {EXPECTED_CORRECTION_SHA256}, found {correction_hash}"
        )
    contract_checks = _manifest_contract_checks()
    if not all(contract_checks.values()):
        raise RuntimeError(f"manifest/module contract mismatch: {contract_checks}")
    before = _preserved_checks()
    if not all(before.values()):
        raise RuntimeError(f"pre-existing dirty-file guard failed before run: {before}")

    # Pure preflight digest: no event or result file is created here.
    _, preflight_source = build_map_tasks("R6", reservoir=None)
    bound_before = {
        path.relative_to(ROOT).as_posix(): file_digest(path)
        for path in BOUND_INPUT_PATHS
    }
    OUT.mkdir(parents=True, exist_ok=False)
    report = run_protocol(EVENTS)

    bound_after = {
        path.relative_to(ROOT).as_posix(): file_digest(path)
        for path in BOUND_INPUT_PATHS
    }
    after = _preserved_checks()
    event_checks = _validate_event_trace(report)
    primary_grid = validate_protocol_grid(report["retrieval_rows"])
    source_after = report["source_diagnostics"]["R6"]
    operational_checks = {
        "manifest_sha256_matches_frozen_value": (
            _sha256(MANIFEST) == EXPECTED_MANIFEST_SHA256
        ),
        "method_correction_sha256_matches_frozen_value": (
            _sha256(CORRECTION) == EXPECTED_CORRECTION_SHA256
        ),
        **contract_checks,
        "pre_existing_dirty_files_unchanged_before_run": all(before.values()),
        "pre_existing_dirty_files_unchanged_after_run": all(after.values()),
        "source_grid_digest_before_after_equal": (
            preflight_source["source_matrix_digest"]
            == source_after["source_matrix_digest"]
            and preflight_source["source_coordinate_digest"]
            == source_after["source_coordinate_digest"]
            and preflight_source["perturbed_coordinate_digest"]
            == source_after["perturbed_coordinate_digest"]
        ),
        "direct_dependency_digests_stable": bound_before == bound_after,
        "exact_primary_grid_revalidated_by_runner": primary_grid["valid"],
        **event_checks,
        "input_cells_are_distinct": (
            len(report["input_hashes"]) == len(set(report["input_hashes"]))
        ),
        "sample_cell_count_is_116": (
            len(report["input_hashes"]) == 116
            and report["primary_cell_count"] == 96
            and report["truncation_control_cell_count"] == 20
        ),
    }
    report["checks"].update(operational_checks)
    report["decision"] = classify_protocol(
        report["retrieval_rows"],
        report["checks"],
        report["resource_ledger"]["resource_envelope"],
    )
    report["preregistration"] = {
        "path": MANIFEST.relative_to(ROOT).as_posix(),
        "sha256": "sha256:" + manifest_hash,
        "history_witnessed": False,
        "outcome_blind": False,
        "note": (
            "Hash-frozen before implementation/run, but exploratory audit "
            "results were visible and disclosed before the final freeze."
        ),
    }
    report["method_correction"] = {
        "path": CORRECTION.relative_to(ROOT).as_posix(),
        "sha256": "sha256:" + correction_hash,
        "status": "pre-result correction bound by the append-once runner",
    }
    report["execution_binding"] = {
        "base_head": current_commit(ROOT),
        "working_tree_commit_bound": False,
        "primary_cell_count": report["primary_cell_count"],
        "truncation_control_cell_count": report["truncation_control_cell_count"],
        "effective_input_count": len(report["input_hashes"]),
        "event_rows": report["reservoir"]["event_count"],
        "source_grid_digest_before_after_equal": operational_checks[
            "source_grid_digest_before_after_equal"
        ],
        "excluded_dirty_file_digests_before_after_equal": (
            all(before.values()) and all(after.values())
        ),
        "json_finite": True,
    }
    report["provenance"] = {
        "commit_sha": "",
        "commit_binding": "uncommitted working-tree execution",
        "independent_witness": False,
        "producer": "experiments/run_equal_resource_reservoir.py",
    }
    report["architecture_or_hardware_claim_authorized"] = False

    _write_once(RESULT, report)

    raw_artifacts = dict(bound_before)
    raw_artifacts[RESULT.relative_to(ROOT).as_posix()] = file_digest(RESULT)
    raw_artifacts[EVENTS.relative_to(ROOT).as_posix()] = file_digest(EVENTS)
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6K-EQUAL_RESOURCE_RESERVOIR",
        evidence_tag="M",
        command="python experiments/run_equal_resource_reservoir.py",
        observed_result={
            "sample_size": len(report["input_hashes"]),
            "primary_cell_count": report["primary_cell_count"],
            "truncation_control_cell_count": report[
                "truncation_control_cell_count"
            ],
            "verdict": report["decision"]["verdict"],
            "signed_survival": report["decision"]["signed_survival"],
            "projective_angular_survival": report["decision"][
                "projective_angular_survival"
            ],
            "radial_survival": report["decision"]["radial_survival"],
            "joint_depth_projective_survival": report["decision"][
                "joint_depth_projective_survival"
            ],
            "all_controls_pass": all(report["checks"].values()),
        },
        commit_sha="",
        working_directory=".",
        platform=sys.platform,
        environment=environment_digest(),
        input_hashes=report["input_hashes"],
        seeds=[],
        raw_artifacts=raw_artifacts,
        environment_dependent=[
            RESULT.relative_to(ROOT).as_posix(),
            EVENTS.relative_to(ROOT).as_posix(),
        ],
        uncertainty={
            "kind": "deterministic finite-grid self-recomputation",
            "confidence_interval": None,
            "independent_replication": False,
            "base_head": current_commit(ROOT),
            "working_tree_commit_bound": False,
            "source_binding": (
                "Every direct source, test, runner, manifest, result, and event "
                "artifact is hashed; none of the R6k files exists in base HEAD."
            ),
        },
        producer="experiments/run_equal_resource_reservoir.py",
        verifier="",
        signature_status="unsigned",
        verification_mode="not_requested",
        typed_remainders=report["typed_remainders"] + [
            {
                "kind": "preregistration_remainder",
                "statement": (
                    "The final manifest was hash-frozen but not committed or "
                    "independently timestamped; pilot outcomes were visible."
                ),
            },
            {
                "kind": "publication_remainder",
                "statement": (
                    "No architecture, hardware, temporal-reservoir, or advantage "
                    "claim is authorized by this envelope."
                ),
            },
            {
                "kind": "uncommitted_source_binding",
                "statement": (
                    "The envelope intentionally has an empty commit_sha. Its "
                    "R6k implementation binding is to live file digests, not "
                    "to the base Git commit."
                ),
            },
        ],
    )
    _write_once(ENVELOPE, envelope.to_dict())
    verification = verify(envelope, repo_root=ROOT, check_commit=False)
    if not verification.ok:
        raise RuntimeError(f"new R6k envelope failed local verification: {verification}")

    summary = {
        "verdict": report["decision"]["verdict"],
        "signed_survival": report["decision"]["signed_survival"],
        "projective_angular_survival": report["decision"][
            "projective_angular_survival"
        ],
        "radial_survival": report["decision"]["radial_survival"],
        "joint_depth_projective_survival": report["decision"][
            "joint_depth_projective_survival"
        ],
        "checks": report["checks"],
        "effective_sample_size": verification.effective_n,
        "independent": verification.independent,
        "result": RESULT.relative_to(ROOT).as_posix(),
    }
    print(json.dumps(summary, allow_nan=False, indent=2, sort_keys=True))
    return 0 if report["decision"]["verdict"] != "HOLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
