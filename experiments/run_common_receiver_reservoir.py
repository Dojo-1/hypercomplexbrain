#!/usr/bin/env python3
"""Lifecycle runner for the frozen QSigma-R6l common-receiver experiment.

Commands are deliberately separated:

* ``run`` requires a clean C_exec commit and writes raw scientific artifacts;
* ``envelope`` requires the later clean C_raw commit and writes only the
  producer envelope;
* ``recompute`` regenerates into an OS temporary directory and compares
  semantic surfaces without modifying the reference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

sys.path.insert(0, "src")

from aionq.common_receiver_reservoir import (
    C_PRE_SHA,
    EFFECTIVE_PROTOCOL_DIGEST,
    MANIFEST_SHA256,
    PROVENANCE_CONTROL_NAMES,
    SCIENTIFIC_CONTROL_NAMES,
    HashChainedEventLedger,
    _BINDING_FIELDS,
    _evaluate_probability_tables,
    _effect_rank,
    _expected_npz_schema,
    _mutual_information,
    _principal_psd_sqrt,
    _validate_probability_table,
    build_common_receiver_bundle,
    build_label_channel,
    classify_protocol,
    canonical_bytes,
    canonical_digest,
    execute_protocol,
    plan_protocol,
    validate_catalog_artifact,
    validate_event_chain,
    validate_result_grid,
)
from aionq.evidence import EvidenceEnvelope, environment_digest, verify
from aionq.equal_resource_reservoir import build_map_tasks, build_pgm_receiver, depolarize

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "qsigma_r6l_common_receiver_preregistration.json"
FREEZE_RECEIPT = ROOT / "manifests" / "qsigma_r6l_common_receiver_freeze_receipt.json"
DEFAULT_OUT = ROOT / "artifacts" / "r6l_common_receiver"
TAG_REF = "refs/tags/qsigma-r6l-prereg-v1"
RUN_COMMAND = (
    "python experiments/run_common_receiver_reservoir.py run "
    "--output-dir artifacts/r6l_common_receiver"
)
RECOMPUTE_COMMAND = (
    "python experiments/run_common_receiver_reservoir.py recompute "
    "--reference-dir artifacts/r6l_common_receiver"
)

SOURCE_PATHS = (
    ".gitattributes",
    "manifests/qsigma_r6l_common_receiver_preregistration.json",
    "manifests/qsigma_r6l_common_receiver_freeze_receipt.json",
    "src/aionq/common_receiver_reservoir.py",
    "tests/test_common_receiver_reservoir.py",
    "experiments/run_common_receiver_reservoir.py",
    "docs/QSIGMA_R6L_COMMON_RECEIVER.md",
)
C_EXEC_DELTA_PATHS = tuple(
    path
    for path in SOURCE_PATHS
    if path != "manifests/qsigma_r6l_common_receiver_preregistration.json"
)
OUTPUT_PATHS = (
    "artifacts/r6l_common_receiver/common_receiver_reservoir.json",
    "artifacts/r6l_common_receiver/common_receivers.json",
    "artifacts/r6l_common_receiver/common_receivers.npz",
    "artifacts/r6l_common_receiver/decision.json",
    "artifacts/r6l_common_receiver/events.jsonl",
    "artifacts/r6l_common_receiver/run_receipt.json",
)
DECLARED_RAW_PATHS = SOURCE_PATHS + OUTPUT_PATHS
ENVELOPE_PATH = "artifacts/r6l_common_receiver/common_receiver_reservoir.envelope.json"
RUNNER_CONTROL_NAMES = PROVENANCE_CONTROL_NAMES
RESULT_FIELDS = frozenset({
    "schema_version", "round", "experiment_kind", "effective_protocol_digest",
    "ambient_dimension", "state_noise_strengths",
    "receiver_label_noise_strengths", "sample_size", "sample_unit",
    "input_hashes", "source_diagnostics", "receiver_summaries",
    "retrieval_rows", "grid_validation", "catalog_validation",
    "event_validation", "ledger_root", "event_count", "checks", "decision",
    "global_winner", "architecture_or_hardware_claim_authorized",
    "typed_remainders", "artifact_bindings",
})
DECISION_ARTIFACT_FIELDS = frozenset({
    "schema_version", "ledger_root", "result_sha256", "decision",
})
RUN_RECEIPT_FIELDS = frozenset({
    "schema_version", "preregistration_commit_sha", "source_commit_sha",
    "manifest_sha256", "freeze_receipt_sha256", "effective_protocol_digest",
    "source_hashes_before", "source_hashes_after", "source_hashes_stable",
    "output_hashes", "protocol_grid_digest", "sample_size", "event_count",
    "ledger_root", "environment", "commands", "controls",
})
OBSERVED_RESULT_FIELDS = frozenset({
    "sample_size", "sample_unit", "all_controls_pass", "verdict",
    "signed_survival", "projective_survival", "radial_survival",
    "joint_survival", "clean_projective_passing_depth_count", "ledger_root",
})
LOCAL_ARRAY_BINDING_FIELDS = frozenset({
    "clean_map_template_digest", "pooled_template_digest",
    "common_receiver_digest", "perturbed_query_digest",
    "state_noised_query_digest", "pre_label_probability_digest",
    "post_label_probability_digest", "receiver_label_matrix_digest",
    "structural_receiver_cost_digest",
})
SEMANTIC_BINDING_FIELDS = frozenset(_BINDING_FIELDS) - LOCAL_ARRAY_BINDING_FIELDS
EXPERIMENT_KIND = "deterministic one-shot associative retrieval with a common receiver"
SAMPLE_UNIT = (
    "distinct deterministic map/task/depth/state-noise/label-noise protocol "
    "cells; not trials, replicates, seeds, or inferential observations"
)
TYPED_REMAINDERS = [
    {
        "kind": "decoder_remainder",
        "statement": (
            "The conclusion is specific to the frozen shared computational basis "
            "and pooled PGM."
        ),
    },
    {
        "kind": "capacity_remainder",
        "statement": (
            "This finite-grid retrieval is not temporal memory capacity or an "
            "asymptotic coding theorem."
        ),
    },
    {
        "kind": "noise_remainder",
        "statement": (
            "The two frozen channels are controlled stresses, not a device noise model."
        ),
    },
    {
        "kind": "resource_remainder",
        "statement": (
            "The canonical full-system Lueders dilation is a structural allocation, "
            "not minimum circuit complexity."
        ),
    },
    {
        "kind": "independence_remainder",
        "statement": (
            "A producer run remains independent=false until a separate semantic "
            "recomputation sidecar passes."
        ),
    },
]


def _require_json_exact(observed: object, expected: object, *, name: str) -> None:
    """Require exact JSON structure and scalar types, not Python ``==`` aliases."""

    if canonical_bytes(observed) != canonical_bytes(expected):
        raise ValueError(f"{name} differs in JSON value or type")


_DECISION_NUMERIC_FIELDS = frozenset({
    "correct_probability", "mutual_information_bits", "mean_reject_probability",
})


def _decision_discrete_projection(decision: Mapping[str, object]) -> dict:
    """Project a decision to the exact, non-tolerant preregistered surface."""

    collections = {"paired_differential_cells", "radial_cells", "joint_cells"}
    projected = {
        key: value for key, value in decision.items() if key not in collections
    }
    for field in sorted(collections):
        rows = decision.get(field)
        if not isinstance(rows, list):
            raise TypeError(f"decision {field} must be a list")
        projected[field] = [
            {
                key: value
                for key, value in row.items()
                if key not in _DECISION_NUMERIC_FIELDS
            }
            for row in rows
        ]
    return projected


def _run_git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=text,
        timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return result.stdout


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _git_blob(commit: str, relative_path: str) -> bytes:
    return _run_git("cat-file", "blob", f"{commit}:{relative_path}", text=False)


def _git_blob_digest(commit: str, relative_path: str) -> str:
    return _sha256_bytes(_git_blob(commit, relative_path))


def _strict_pairs(pairs: Sequence[tuple[str, object]]) -> dict:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _reject_constant(value: str):
    raise ValueError(f"nonfinite JSON constant {value}")


def _load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_pairs,
        parse_constant=_reject_constant,
    )


def _pretty_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json_once(path: Path, value: object) -> None:
    data = _pretty_json_bytes(value)
    with path.open("xb") as handle:
        handle.write(data)


def _write_npz_once(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    with path.open("xb") as handle:
        np.savez(handle, **arrays)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _assert_exact_output_path(path: Path) -> None:
    if path.resolve() != DEFAULT_OUT.resolve():
        raise ValueError(
            "production output must be exactly artifacts/r6l_common_receiver"
        )


def _manifest_and_receipt() -> tuple[dict, dict]:
    manifest = _load_json(MANIFEST)
    receipt = _load_json(FREEZE_RECEIPT)
    if _file_digest(MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("live preregistration bytes differ from the frozen digest")
    if _git_blob_digest(C_PRE_SHA, _relative(MANIFEST)) != MANIFEST_SHA256:
        raise RuntimeError("C_pre manifest blob differs from the frozen digest")
    if set(receipt) != {
        "schema_version", "round", "repository", "branch",
        "baseline_commit_sha", "correction_inventory", "preregistration",
        "effective_protocol", "remote_anchor", "derivation_commands",
        "pre_implementation_observation",
    }:
        raise RuntimeError("freeze receipt outer field set is not closed")
    if (
        receipt.get("schema_version") != "hypercomplexbrain.r6l-freeze-receipt.v1"
        or receipt.get("round") != "QSigma-R6l"
        or receipt.get("repository") != "jesusvilela/hypercomplexbrain"
        or receipt.get("branch") != "claude/aion-brain-architecture-27f8ji"
        or receipt.get("baseline_commit_sha")
        != manifest["baseline"]["r6k_publication_commit"]
        or receipt.get("correction_inventory") != []
    ):
        raise RuntimeError("freeze receipt fixed metadata differs")
    preregistration = receipt.get("preregistration", {})
    if set(preregistration) != {
        "path", "commit_sha", "first_add_commit_sha", "manifest_sha256",
        "hash_source", "worktree_sha256_at_receipt_creation",
        "git_blob_equals_worktree", "c_pre_changed_paths",
    }:
        raise RuntimeError("freeze receipt preregistration field set differs")
    expected_preregistration = {
        "path": _relative(MANIFEST),
        "commit_sha": C_PRE_SHA,
        "first_add_commit_sha": C_PRE_SHA,
        "manifest_sha256": MANIFEST_SHA256,
        "hash_source": f"exact Git blob {C_PRE_SHA}:{_relative(MANIFEST)}",
        "worktree_sha256_at_receipt_creation": MANIFEST_SHA256,
        "git_blob_equals_worktree": True,
        "c_pre_changed_paths": [_relative(MANIFEST)],
    }
    try:
        _require_json_exact(
            preregistration,
            expected_preregistration,
            name="freeze receipt preregistration binding",
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if _changed_paths(f"{C_PRE_SHA}^", C_PRE_SHA) != [_relative(MANIFEST)]:
        raise RuntimeError("C_pre is not the manifest-only commit")
    if str(_run_git("rev-parse", f"{C_PRE_SHA}^")).strip() != manifest[
        "baseline"
    ]["r6k_publication_commit"]:
        raise RuntimeError("C_pre parent is not the declared R6k baseline")
    first_adds = [
        line for line in str(
            _run_git(
                "log", "--diff-filter=A", "--format=%H", "--", _relative(MANIFEST)
            )
        ).splitlines()
        if line
    ]
    if first_adds != [C_PRE_SHA]:
        raise RuntimeError("manifest first-add history differs from C_pre")
    effective = receipt.get("effective_protocol", {})
    if set(effective) != {"object", "canonical_json", "digest"}:
        raise RuntimeError("freeze receipt effective-protocol fields differ")
    if canonical_digest(effective.get("object")) != EFFECTIVE_PROTOCOL_DIGEST:
        raise RuntimeError("freeze receipt effective-protocol object is invalid")
    if effective.get("digest") != EFFECTIVE_PROTOCOL_DIGEST:
        raise RuntimeError("freeze receipt effective-protocol digest is invalid")
    if effective.get("canonical_json") != canonical_bytes(
        effective.get("object")
    ).decode("utf-8"):
        raise RuntimeError("freeze receipt effective-protocol JSON differs")
    remote = receipt.get("remote_anchor", {})
    expected_remote = {
        "remote": "origin",
        "repository_url": "https://github.com/jesusvilela/hypercomplexbrain.git",
        "ref": TAG_REF,
        "kind": "lightweight direct commit ref",
        "resolved_commit_sha": C_PRE_SHA,
        "commit_url": (
            "https://github.com/jesusvilela/hypercomplexbrain/commit/" + C_PRE_SHA
        ),
        "same_party_public_history_anchor": True,
        "independent_timestamp_or_witness": False,
    }
    try:
        _require_json_exact(remote, expected_remote, name="freeze receipt remote anchor")
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    observation = receipt.get("pre_implementation_observation", {})
    expected_observation = {
        "r6l_output_directory_absent": True,
        "pooled_common_receiver_outcomes_run": False,
        "implementation_present": False,
        "statement": (
            "The manifest was committed and remotely anchored before this C_exec "
            "implementation began. This same-party receipt does not claim "
            "independent witnessing."
        ),
    }
    try:
        _require_json_exact(
            observation,
            expected_observation,
            name="freeze receipt pre-implementation observation",
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    expected_commands = [
        "git log --diff-filter=A --format=%H -- " + _relative(MANIFEST),
        f"git diff-tree --no-commit-id --name-only -r {C_PRE_SHA}",
        f"git cat-file blob {C_PRE_SHA}:{_relative(MANIFEST)}",
        f"git ls-remote origin {TAG_REF}",
        "Get-FileHash manifests/qsigma_r6l_common_receiver_preregistration.json "
        "-Algorithm SHA256",
    ]
    try:
        _require_json_exact(
            receipt.get("derivation_commands"),
            expected_commands,
            name="freeze receipt derivation commands",
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return manifest, receipt


def _remote_tag_target() -> str:
    output = _run_git("ls-remote", "origin", TAG_REF)
    lines = [line for line in str(output).splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("remote preregistration tag is absent or ambiguous")
    sha, ref = lines[0].split("\t", 1)
    if ref != TAG_REF:
        raise RuntimeError("remote preregistration ref differs")
    return sha


def _changed_paths(parent: str, child: str) -> list[str]:
    output = _run_git("diff", "--name-only", parent, child, "--")
    return [line.strip().replace("\\", "/") for line in str(output).splitlines() if line]


def _tree_has_path(commit: str, path: str) -> bool:
    return bool(str(_run_git("ls-tree", "-r", "--name-only", commit, "--", path)).strip())


def _source_preflight(output_dir: Path) -> tuple[str, dict[str, str], dict[str, bool]]:
    """Fail before mkdir or numerical construction if C_exec is not exact."""

    _assert_exact_output_path(output_dir)
    manifest, receipt = _manifest_and_receipt()
    head = str(_run_git("rev-parse", "HEAD")).strip()
    parent_line = str(_run_git("rev-list", "--parents", "-n", "1", head)).split()
    parent = parent_line[1] if len(parent_line) == 2 else ""
    status = str(_run_git("status", "--porcelain=v1", "--untracked-files=all"))
    expected_delta = sorted(C_EXEC_DELTA_PATHS)
    actual_delta = sorted(_changed_paths(C_PRE_SHA, head))
    upstream = manifest["baseline"]["normative_upstream_sha256"]
    upstream_valid = all(
        _git_blob_digest(
            manifest["baseline"]["r6k_publication_commit"], relative
        ) == expected
        and _file_digest(ROOT / relative) == expected
        for relative, expected in upstream.items()
    )
    dependency_paths = tuple(dict.fromkeys(SOURCE_PATHS + tuple(upstream)))
    source_hashes = {
        relative: _file_digest(ROOT / relative) for relative in dependency_paths
    }
    source_blobs_equal = all(
        source_hashes[relative] == _git_blob_digest(head, relative)
        for relative in SOURCE_PATHS
    )
    attribute_output = _run_git(
        "check-attr", "-z", "text", "eol", "--",
        ".gitattributes", "artifacts/r6l_common_receiver/events.jsonl",
        text=False,
    )
    attribute_parts = bytes(attribute_output).split(b"\0")
    triples = {
        tuple(part.decode("utf-8") for part in attribute_parts[index:index + 3])
        for index in range(0, len(attribute_parts) - 2, 3)
    }
    controls = {
        "manifest_blob_matches_frozen_sha256": (
            receipt["preregistration"]["manifest_sha256"] == MANIFEST_SHA256
        ),
        "freeze_receipt_matches_effective_protocol": (
            receipt["effective_protocol"]["digest"] == EFFECTIVE_PROTOCOL_DIGEST
        ),
        "c_pre_is_remote_anchored": _remote_tag_target() == C_PRE_SHA,
        "c_exec_is_direct_manifest_descendant": parent == C_PRE_SHA,
        "c_exec_has_exact_six_path_delta": actual_delta == expected_delta,
        "c_exec_tree_has_no_r6l_outputs": not _tree_has_path(
            head, "artifacts/r6l_common_receiver"
        ),
        "clean_source_worktree": status == "",
        "exact_output_path_absent_before_run": not output_dir.exists(),
        "upstream_blobs_match_preregistration": upstream_valid,
        "source_worktree_matches_c_exec_blobs": source_blobs_equal,
        "r6l_event_path_has_exact_lf_attribute": (
            (".gitattributes", "text", "set") in triples
            and (".gitattributes", "eol", "lf") in triples
            and (
                "artifacts/r6l_common_receiver/events.jsonl", "text", "set"
            ) in triples
            and (
                "artifacts/r6l_common_receiver/events.jsonl", "eol", "lf"
            ) in triples
        ),
    }
    if set(controls) != set(RUNNER_CONTROL_NAMES) or not all(
        value is True for value in controls.values()
    ):
        raise RuntimeError(f"C_exec preflight failed before numerics: {controls}")
    return head, source_hashes, controls


def _scientific_paths(out: Path) -> dict[str, Path]:
    return {
        "result": out / "common_receiver_reservoir.json",
        "catalog": out / "common_receivers.json",
        "npz": out / "common_receivers.npz",
        "decision": out / "decision.json",
        "events": out / "events.jsonl",
        "receipt": out / "run_receipt.json",
        "envelope": out / "common_receiver_reservoir.envelope.json",
    }


def _produce_scientific_surfaces(
    out: Path,
    *,
    source_commit: str,
    source_hashes_before: Mapping[str, str],
    runner_controls: Mapping[str, bool],
    write_receipt: bool,
) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    paths = _scientific_paths(out)
    plan = plan_protocol()
    with HashChainedEventLedger(paths["events"]) as ledger:
        run = execute_protocol(
            plan,
            ledger=ledger,
            additional_controls=runner_controls,
        )
    _write_npz_once(paths["npz"], run.arrays)
    catalog = dict(run.catalog)
    catalog["npz_sha256"] = _file_digest(paths["npz"])
    _write_json_once(paths["catalog"], catalog)
    report = dict(run.report)
    report["artifact_bindings"] = {
        "events_sha256": _file_digest(paths["events"]),
        "npz_sha256": _file_digest(paths["npz"]),
        "catalog_sha256": _file_digest(paths["catalog"]),
    }
    _write_json_once(paths["result"], report)
    decision_record = {
        "schema_version": "hypercomplexbrain.r6l-decision-artifact.v1",
        "ledger_root": run.report["ledger_root"],
        "result_sha256": _file_digest(paths["result"]),
        "decision": run.decision,
    }
    _write_json_once(paths["decision"], decision_record)
    if write_receipt:
        output_hashes = {
            _relative(paths[name]): _file_digest(paths[name])
            for name in ("events", "npz", "catalog", "result", "decision")
        }
    else:
        output_hashes = {
            paths[name].name: _file_digest(paths[name])
            for name in ("events", "npz", "catalog", "result", "decision")
        }
    source_hashes_after = {
        relative: _file_digest(ROOT / relative) for relative in source_hashes_before
    }
    if source_hashes_after != dict(source_hashes_before):
        raise RuntimeError("source dependency bytes changed during execution")
    if write_receipt:
        receipt = {
            "schema_version": "hypercomplexbrain.r6l-run-receipt.v1",
            "preregistration_commit_sha": C_PRE_SHA,
            "source_commit_sha": source_commit,
            "manifest_sha256": MANIFEST_SHA256,
            "freeze_receipt_sha256": _file_digest(FREEZE_RECEIPT),
            "effective_protocol_digest": EFFECTIVE_PROTOCOL_DIGEST,
            "source_hashes_before": dict(source_hashes_before),
            "source_hashes_after": source_hashes_after,
            "source_hashes_stable": True,
            "output_hashes": output_hashes,
            "protocol_grid_digest": canonical_digest(run.report["input_hashes"]),
            "sample_size": 384,
            "event_count": 716,
            "ledger_root": run.report["ledger_root"],
            "environment": environment_digest(),
            "commands": {
                "run": RUN_COMMAND,
                "recompute": RECOMPUTE_COMMAND,
                "envelope_template": (
                    "python experiments/run_common_receiver_reservoir.py envelope "
                    "--artifact-dir artifacts/r6l_common_receiver --raw-commit C_RAW_SHA "
                    "--source-commit C_EXEC_SHA --prereg-commit C_PRE_SHA"
                ),
            },
            "controls": run.report["checks"],
        }
        _write_json_once(paths["receipt"], receipt)
        output_hashes[_relative(paths["receipt"])] = _file_digest(paths["receipt"])
        status_paths = {
            line[3:].strip().replace("\\", "/")
            for line in str(
                _run_git("status", "--porcelain=v1", "--untracked-files=all")
            ).splitlines()
            if len(line) >= 4
        }
        if status_paths != set(OUTPUT_PATHS):
            raise RuntimeError(
                "post-run worktree contains changes outside the six frozen outputs"
            )
        _validate_raw_surfaces(
            out,
            source_commit=source_commit,
            raw_commit=None,
            require_receipt=True,
        )
    return {
        "run": run,
        "paths": paths,
        "output_hashes": output_hashes,
    }


def run_command(output_dir: Path) -> int:
    source_commit, source_hashes, controls = _source_preflight(output_dir)
    produced = _produce_scientific_surfaces(
        output_dir,
        source_commit=source_commit,
        source_hashes_before=source_hashes,
        runner_controls=controls,
        write_receipt=True,
    )
    run = produced["run"]
    summary = {
        "verdict": run.decision["verdict"],
        "sample_size": 384,
        "event_count": 716,
        "ledger_root": run.report["ledger_root"],
        "checks_pass": all(value is True for value in run.report["checks"].values()),
        "independent": False,
        "output_dir": _relative(output_dir),
    }
    print(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))
    return 0 if run.decision["verdict"] != "HOLD" else 1


def _load_event_file(path: Path) -> tuple[list[dict], dict]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("event file contains BOM or CR bytes")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ValueError("event file must have one final LF and no blank line")
    lines = raw.splitlines(keepends=True)
    events: list[dict] = []
    for index, line in enumerate(lines):
        if not line.endswith(b"\n"):
            raise ValueError(f"event line {index} lacks LF")
        event = json.loads(
            line[:-1].decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
        if line != canonical_bytes(event) + b"\n":
            raise ValueError(f"event line {index} is not canonical")
        events.append(event)
    validation = validate_event_chain(events)
    if not validation["valid"]:
        raise ValueError(f"event chain invalid: {validation}")
    return events, validation


def _load_npz_exact(path: Path) -> dict[str, np.ndarray]:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("NPZ archive contains duplicate members")
    with np.load(path, allow_pickle=False) as loaded:
        arrays = {key: np.asarray(loaded[key]) for key in loaded.files}
    if set(names) != {f"{key}.npy" for key in arrays} or any(
        "/" in name or "\\" in name for name in names
    ):
        raise ValueError("NPZ member names do not exactly encode the array keys")
    if any(array.dtype.hasobject for array in arrays.values()):
        raise ValueError("NPZ archive contains object dtype")
    return arrays


def _require_sha256(value: object, *, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise ValueError(f"{name} is not a canonical lowercase SHA-256 string")
    return value


def _validate_numerical_surface(
    *,
    plan,
    arrays: Mapping[str, np.ndarray],
    catalog: Mapping[str, object],
    rows: Sequence[Mapping[str, object]],
    receiver_summaries: Sequence[Mapping[str, object]],
    reported_source_diagnostics: Mapping[str, object],
    controls: Mapping[str, bool],
) -> dict:
    """Rebuild stored lineage and an independent canonical decision lineage."""

    digest_by_key: dict[str, str] = {}
    for digest, entry in catalog["aggregate_locators"].items():
        for locator in entry["items"]:
            key = locator["npz_key"]
            previous = digest_by_key.setdefault(key, digest)
            if previous != digest:
                raise ValueError(f"one NPZ key is split across aggregates: {key}")

    maximum_matrix = 0.0
    maximum_scalar = 0.0

    def compare_matrix(first: np.ndarray, second: np.ndarray, *, name: str) -> None:
        nonlocal maximum_matrix
        delta = float(np.linalg.norm(np.asarray(first) - np.asarray(second), "fro"))
        maximum_matrix = max(maximum_matrix, delta)
        if delta > 1e-10:
            raise ValueError(f"numerical reconstruction differs for {name}: {delta}")

    def compare_scalar(first: object, second: object, *, name: str) -> None:
        nonlocal maximum_scalar
        delta = _compare_numeric(first, second)
        maximum_scalar = max(maximum_scalar, delta)
        if delta > 1e-10:  # pragma: no cover - _compare_numeric already raises
            raise ValueError(f"numeric reconstruction differs for {name}: {delta}")

    rows_by_cell = {row["protocol_cell_id"]: row for row in rows}
    canonical_metrics_by_cell: dict[str, dict] = {}
    summaries_by_receiver = {
        row["protocol_receiver_id"]: row for row in receiver_summaries
    }
    effects_by_receiver: dict[int, tuple[np.ndarray, ...]] = {}
    canonical_bundles_by_receiver: dict[int, object] = {}
    source_tasks: dict[str, tuple] = {}
    rebuilt_source_diagnostics: dict[str, dict] = {}
    for map_name in ("R6", "R6i"):
        tasks, diagnostics = build_map_tasks(map_name)
        source_tasks[map_name] = tasks
        rebuilt_source_diagnostics[map_name] = diagnostics
    if set(reported_source_diagnostics) != {"R6", "R6i"}:
        raise ValueError("reported source-diagnostic map set differs")
    source_digest_fields = {
        "source_matrix_digest", "source_coordinate_digest",
        "perturbed_coordinate_digest",
    }
    for map_name in ("R6", "R6i"):
        reported = reported_source_diagnostics[map_name]
        rebuilt = rebuilt_source_diagnostics[map_name]
        if set(reported) != set(rebuilt):
            raise ValueError(f"source-diagnostic fields differ for {map_name}")
        for field, expected in rebuilt.items():
            if field in source_digest_fields:
                _require_sha256(reported[field], name=f"reported {map_name} {field}")
                _require_sha256(expected, name=f"rebuilt {map_name} {field}")
            elif field == "maximum_central_pair_residual":
                compare_scalar(
                    reported[field], expected,
                    name=f"{map_name} source diagnostic {field}",
                )
            else:
                _require_json_exact(
                    reported[field],
                    expected,
                    name=f"source diagnostic {map_name} {field}",
                )
    for field in source_digest_fields:
        reported_equal = (
            reported_source_diagnostics["R6"][field]
            == reported_source_diagnostics["R6i"][field]
        )
        rebuilt_equal = (
            rebuilt_source_diagnostics["R6"][field]
            == rebuilt_source_diagnostics["R6i"][field]
        )
        if reported_equal is not rebuilt_equal:
            raise ValueError(f"source diagnostic equality predicate differs: {field}")

    for spec in plan.receivers:
        token = f"r{spec.receiver_index:02d}"
        summary = summaries_by_receiver[spec.protocol_receiver_id]
        clean = {
            map_name: arrays[f"{token}__{map_name}__clean_templates"]
            for map_name in ("R6", "R6i")
        }
        for map_name in ("R6", "R6i"):
            matches = [
                task for task in source_tasks[map_name]
                if task.name == spec.task and task.depth == spec.depth
            ]
            if len(matches) != 1:
                raise ValueError(f"sealed source task is ambiguous for {token} {map_name}")
            task = matches[0]
            for index, (observed, expected) in enumerate(
                zip(clean[map_name], task.templates)
            ):
                compare_matrix(
                    observed,
                    expected,
                    name=f"{token} {map_name} clean template {index}",
                )
            clean_queries = arrays[f"{token}__{map_name}__clean_queries"]
            for index, (observed, expected) in enumerate(
                zip(clean_queries, task.queries)
            ):
                compare_matrix(
                    observed,
                    expected,
                    name=f"{token} {map_name} clean query {index}",
                )
        canonical_bundles_by_receiver[spec.receiver_index] = (
            build_common_receiver_bundle(spec, source_tasks)
        )
        pooled = arrays[f"{token}__pooled_templates"]
        exact_pool = 0.5 * clean["R6"] + 0.5 * clean["R6i"]
        if not np.array_equal(pooled, exact_pool):
            raise ValueError(f"pooled templates are not the exact half sum for {token}")
        rebuilt = build_pgm_receiver(tuple(pooled), tol=1e-10)
        rebuilt_effects = rebuilt.effects + (rebuilt.reject_effect,)
        stored_effects = tuple(arrays[f"{token}__receiver_effects"])
        if len(stored_effects) != spec.classes + 1:
            raise ValueError(f"receiver effect count differs for {token}")
        for index, (stored, expected) in enumerate(zip(stored_effects, rebuilt_effects)):
            compare_matrix(stored, expected, name=f"{token} effect {index}")
        effects_by_receiver[spec.receiver_index] = stored_effects

        stored_roots = tuple(arrays[f"{token}__sqrt_effects"])
        ranks: list[int] = []
        reconstruction: list[float] = []
        for index, (effect, stored_root) in enumerate(zip(stored_effects, stored_roots)):
            root, _residual, values = _principal_psd_sqrt(effect)
            compare_matrix(stored_root, root, name=f"{token} square root {index}")
            ranks.append(_effect_rank(values))
            reconstruction.append(float(np.linalg.norm(stored_root @ stored_root - effect, "fro")))
        _require_json_exact(
            summary["effect_ranks"], ranks, name=f"receiver effect ranks {token}"
        )
        structural_object = catalog["aggregate_locators"][
            summary["structural_receiver_cost_digest"]
        ]["aggregate_object"]
        _require_json_exact(
            structural_object["effect_ranks"],
            ranks,
            name=f"structural aggregate effect ranks {token}",
        )
        _require_json_exact(
            summary["support_rank"],
            rebuilt.diagnostics["clean_mean_support_rank"],
            name=f"receiver support rank {token}",
        )

        isometry = arrays[f"{token}__naimark_isometry"]
        for index, root in enumerate(stored_roots):
            block = isometry[16 * index:16 * (index + 1)]
            compare_matrix(block, root, name=f"{token} Naimark block {index}")
        if np.any(isometry[16 * len(stored_roots):] != 0.0):
            raise ValueError(f"Naimark padding blocks are nonzero for {token}")
        isometry_residual = float(
            np.linalg.norm(isometry.conj().T @ isometry - np.eye(16), 2)
        )
        expected_residuals = {
            "completeness_spectral": rebuilt.diagnostics["completeness_residual"],
            "support_projector_spectral": rebuilt.diagnostics[
                "support_projector_residual"
            ],
            "isometry_spectral": isometry_residual,
            "maximum_effect_reconstruction_fro": max(reconstruction, default=0.0),
        }
        for field, expected in expected_residuals.items():
            compare_scalar(summary["residuals"][field], expected, name=f"{token} {field}")

        expected_summary_digests = {
            "pooled_template_digest": digest_by_key[f"{token}__pooled_templates"],
            "common_receiver_digest": digest_by_key[f"{token}__receiver_effects"],
            "structural_receiver_cost_digest": digest_by_key[f"{token}__sqrt_effects"],
        }
        for field, expected in expected_summary_digests.items():
            if summary[field] != expected:
                raise ValueError(f"receiver summary binding differs: {token} {field}")
        if digest_by_key[f"{token}__sqrt_effects"] != digest_by_key[
            f"{token}__naimark_isometry"
        ]:
            raise ValueError(f"structural receiver aggregate is split for {token}")
        for map_name in ("R6", "R6i"):
            if summary["clean_map_template_digests"][map_name] != digest_by_key[
                f"{token}__{map_name}__clean_templates"
            ]:
                raise ValueError(f"clean-template summary binding differs for {token}")
        prior_object = catalog["semantic_objects"][
            summary["prior_and_perturbation_definition_digest"]
        ]
        if prior_object.get("protocol_receiver_id") != spec.protocol_receiver_id:
            raise ValueError(f"receiver prior-definition binding differs for {token}")

    for cell in plan.cells:
        spec = cell.receiver
        token = f"r{spec.receiver_index:02d}"
        row = rows_by_cell[cell.protocol_cell_id]
        bindings = row["producer_array_bindings"]
        clean_query_key = f"{token}__{cell.map_name}__clean_queries"
        noised_key = (
            f"{token}__{cell.map_name}__e{cell.eta_index:02d}"
            "__state_noised_queries"
        )
        label_key = f"{token}__l{cell.epsilon_index:02d}__label_matrix"
        prefix = (
            f"{token}__{cell.map_name}__e{cell.eta_index:02d}"
            f"__l{cell.epsilon_index:02d}"
        )
        pre_key = f"{prefix}__pre_label_probabilities"
        post_key = f"{prefix}__post_label_probabilities"
        expected_bindings = {
            "clean_map_template_digest": digest_by_key[
                f"{token}__{cell.map_name}__clean_templates"
            ],
            "pooled_template_digest": digest_by_key[f"{token}__pooled_templates"],
            "common_receiver_digest": digest_by_key[f"{token}__receiver_effects"],
            "perturbed_query_digest": digest_by_key[clean_query_key],
            "state_noised_query_digest": digest_by_key[noised_key],
            "pre_label_probability_digest": digest_by_key[pre_key],
            "post_label_probability_digest": digest_by_key[post_key],
            "receiver_label_matrix_digest": digest_by_key[label_key],
            "structural_receiver_cost_digest": digest_by_key[
                f"{token}__sqrt_effects"
            ],
        }
        for field, expected in expected_bindings.items():
            if bindings[field] != expected:
                raise ValueError(f"cell aggregate binding differs: {cell.protocol_cell_id} {field}")

        state_object = catalog["semantic_objects"][bindings["state_channel_digest"]]
        expected_state_object = {
            "schema_version": "hypercomplexbrain.r6l-channel.v1",
            "kind": "global_depolarization",
            "dimension": 16,
            "eta_index": cell.eta_index,
            "eta_decimal": cell.eta_decimal,
            "definition": "(1-eta)*rho+eta*I/16",
        }
        _require_json_exact(
            state_object,
            expected_state_object,
            name="cell state-channel semantic binding",
        )
        label_object = catalog["semantic_objects"][
            bindings["receiver_label_channel_digest"]
        ]
        expected_label_object = {
            "schema_version": "hypercomplexbrain.r6l-channel.v1",
            "kind": "symmetric_class_label_confusion",
            "classes": spec.classes,
            "epsilon_index": cell.epsilon_index,
            "epsilon_decimal": cell.epsilon_decimal,
            "reject_rule": "fixed",
            "definition": "diag=1-epsilon;offdiag=epsilon/(C-1)",
        }
        _require_json_exact(
            label_object,
            expected_label_object,
            name="cell label-channel semantic binding",
        )
        prior_object = catalog["semantic_objects"][
            bindings["prior_and_perturbation_definition_digest"]
        ]
        if prior_object.get("protocol_receiver_id") != spec.protocol_receiver_id:
            raise ValueError("cell prior-definition semantic binding differs")

        clean_queries = arrays[clean_query_key]
        noised_queries = arrays[noised_key]
        expected_noised = np.stack([
            depolarize(query, cell.eta) for query in clean_queries
        ])
        for index, (observed, expected) in enumerate(
            zip(noised_queries, expected_noised)
        ):
            compare_matrix(
                observed, expected, name=f"{noised_key} slice {index}"
            )
        label_matrix = arrays[label_key]
        expected_label_matrix = build_label_channel(spec.classes, cell.epsilon)
        if not np.array_equal(label_matrix, expected_label_matrix):
            raise ValueError(f"stored label matrix differs from its exact channel: {label_key}")
        if (
            np.max(np.abs(np.sum(label_matrix, axis=1) - 1.0)) > 1e-12
            or np.any(label_matrix[:spec.classes, spec.classes] != 0.0)
            or np.any(label_matrix[spec.classes, :spec.classes] != 0.0)
            or label_matrix[spec.classes, spec.classes] != 1.0
        ):
            raise ValueError(f"stored label matrix violates stochastic/reject controls: {label_key}")
        effects = effects_by_receiver[spec.receiver_index]
        calculated = np.empty((spec.classes, spec.classes + 1), dtype=complex)
        for input_index, state in enumerate(noised_queries):
            for outcome_index, effect in enumerate(effects):
                calculated[input_index, outcome_index] = np.trace(effect @ state)
        pre, pre_diagnostics = _validate_probability_table(
            calculated, expected_rows=spec.classes
        )
        post, post_diagnostics = _validate_probability_table(
            pre @ label_matrix, expected_rows=spec.classes
        )
        compare_matrix(arrays[pre_key], pre, name=pre_key)
        compare_matrix(arrays[post_key], post, name=post_key)
        correct = float(np.mean(np.diag(post[:, :spec.classes])))
        reject = float(np.mean(post[:, -1]))
        nonreject = 1.0 - reject
        expected_metrics = {
            "correct_probability": correct,
            "mutual_information_bits": _mutual_information(post),
            "mean_reject_probability": reject,
            "conditional_correct_probability_given_nonreject": (
                correct / nonreject if nonreject > 1e-15 else None
            ),
            "minimum_pre_label_probability": pre_diagnostics["minimum"],
            "maximum_pre_label_probability": pre_diagnostics["maximum"],
            "minimum_post_label_probability": post_diagnostics["minimum"],
            "maximum_post_label_probability": post_diagnostics["maximum"],
            "maximum_pre_label_row_sum_defect": pre_diagnostics["row_sum_defect"],
            "maximum_post_label_row_sum_defect": post_diagnostics["row_sum_defect"],
            "maximum_pre_label_imaginary_residual": pre_diagnostics[
                "imaginary_residual"
            ],
            "maximum_post_label_imaginary_residual": post_diagnostics[
                "imaginary_residual"
            ],
        }
        _require_json_exact(
            row["validation"],
            {"pre_label_valid": True, "post_label_valid": True},
            name="cell probability validation",
        )
        for field, expected in expected_metrics.items():
            compare_scalar(row["metrics"][field], expected, name=f"cell metric {field}")

        canonical_bundle = canonical_bundles_by_receiver[spec.receiver_index]
        canonical_queries = tuple(
            depolarize(query, cell.eta)
            for query in canonical_bundle.tasks[cell.map_name].queries
        )
        canonical_label = build_label_channel(spec.classes, cell.epsilon)
        _canonical_pre, _canonical_post, canonical_metrics, canonical_validation = (
            _evaluate_probability_tables(
                canonical_bundle,
                canonical_queries,
                canonical_label,
            )
        )
        _require_json_exact(
            canonical_validation,
            {"pre_label_valid": True, "post_label_valid": True},
            name="canonical probability validation",
        )
        canonical_metrics_by_cell[cell.protocol_cell_id] = canonical_metrics

    canonical_rows = [
        {
            **row,
            "metrics": canonical_metrics_by_cell[row["protocol_cell_id"]],
        }
        for row in rows
    ]
    reported_decision = classify_protocol(rows, controls, plan=plan)
    canonical_decision = classify_protocol(canonical_rows, controls, plan=plan)
    _require_json_exact(
        _decision_discrete_projection(reported_decision),
        _decision_discrete_projection(canonical_decision),
        name="canonical/report discrete decision projection",
    )

    return {
        "valid": True,
        "canonical_discrete_decision_matches": True,
        "maximum_matrix_frobenius_deviation": maximum_matrix,
        "maximum_scalar_absolute_deviation": maximum_scalar,
    }


def _validate_raw_surfaces(
    artifact_dir: Path,
    *,
    source_commit: str,
    raw_commit: str | None,
    require_receipt: bool,
) -> dict:
    """Validate every local and cross-file binding before evidence use."""

    paths = _scientific_paths(artifact_dir)
    required_names = ["result", "catalog", "npz", "decision", "events"]
    if require_receipt:
        required_names.append("receipt")
    if not all(paths[name].is_file() for name in required_names):
        raise FileNotFoundError("R6l raw artifact surface is incomplete")

    plan = plan_protocol()
    result = _load_json(paths["result"])
    catalog = _load_json(paths["catalog"])
    decision_record = _load_json(paths["decision"])
    events, event_validation = _load_event_file(paths["events"])
    arrays = _load_npz_exact(paths["npz"])
    if set(result) != RESULT_FIELDS:
        raise ValueError("result outer field set is not closed")
    if result.get("schema_version") != "hypercomplexbrain.r6l-common-receiver.v1":
        raise ValueError("result schema version differs")
    expected_header = {
        "round": "QSigma-R6l",
        "experiment_kind": EXPERIMENT_KIND,
        "effective_protocol_digest": EFFECTIVE_PROTOCOL_DIGEST,
        "ambient_dimension": 16,
        "state_noise_strengths": [0.0, 0.01, 0.03, 0.1],
        "receiver_label_noise_strengths": [0.0, 0.01, 0.03, 0.1],
        "sample_size": 384,
        "sample_unit": SAMPLE_UNIT,
        "event_count": 716,
        "global_winner": None,
        "architecture_or_hardware_claim_authorized": False,
        "typed_remainders": TYPED_REMAINDERS,
    }
    for field, expected in expected_header.items():
        _require_json_exact(
            result.get(field), expected, name=f"result frozen field {field}"
        )
    expected_ids = [cell.protocol_cell_id for cell in plan.cells]
    if result.get("input_hashes") != expected_ids:
        raise ValueError("result input hashes differ from portable cell order")

    rows = result.get("retrieval_rows")
    if not isinstance(rows, list):
        raise TypeError("result retrieval rows must be a list")
    grid_validation = validate_result_grid(rows, plan)
    if not grid_validation["valid"]:
        raise ValueError("result grid validation failed")
    try:
        _require_json_exact(
            result.get("grid_validation"),
            grid_validation,
            name="cached result grid validation",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("result grid validation is invalid or stale")
    if set(result.get("checks", {})) != set(SCIENTIFIC_CONTROL_NAMES) | set(
        PROVENANCE_CONTROL_NAMES
    ) or not all(type(value) is bool for value in result["checks"].values()):
        raise ValueError("result control field set/types differ")

    catalog_validation = validate_catalog_artifact(
        catalog,
        arrays,
        npz_sha256=_file_digest(paths["npz"]),
        plan=plan,
    )
    if not catalog_validation["valid"]:
        raise ValueError(f"catalog/NPZ surface failed: {catalog_validation}")
    _require_json_exact(
        result.get("catalog_validation"),
        catalog_validation,
        name="cached result catalog validation",
    )
    _require_json_exact(
        result.get("event_validation"),
        event_validation,
        name="cached result event validation",
    )
    if result.get("ledger_root") != event_validation["ledger_root"]:
        raise ValueError("result ledger root differs from the event bytes")

    receiver_events = [
        event["payload"] for event in events if event["kind"] == "common_receiver_freeze"
    ]
    evaluation_events = [
        event["payload"] for event in events if event["kind"] == "evaluation"
    ]
    _require_json_exact(
        result.get("receiver_summaries"),
        receiver_events,
        name="receiver summaries versus freeze events",
    )
    expected_evaluations = []
    for row in rows:
        payload = {key: value for key, value in row.items() if key != "identity"}
        payload["schema_version"] = "hypercomplexbrain.r6l-event-evaluation.v1"
        expected_evaluations.append(payload)
    _require_json_exact(
        evaluation_events,
        expected_evaluations,
        name="evaluation events versus result rows",
    )

    aggregate_refs: set[str] = set()
    semantic_refs: set[str] = set()
    for summary in receiver_events:
        aggregate_refs.update(summary["clean_map_template_digests"].values())
        aggregate_refs.update({
            summary["pooled_template_digest"],
            summary["common_receiver_digest"],
            summary["structural_receiver_cost_digest"],
        })
        semantic_refs.add(summary["prior_and_perturbation_definition_digest"])
    for row in rows:
        bindings = row["producer_array_bindings"]
        aggregate_refs.update(bindings[field] for field in LOCAL_ARRAY_BINDING_FIELDS)
        semantic_refs.update(bindings[field] for field in SEMANTIC_BINDING_FIELDS)
    if aggregate_refs != set(catalog["aggregate_locators"]):
        raise ValueError("catalog aggregate keys differ from producer bindings")
    if semantic_refs != set(catalog["semantic_objects"]):
        raise ValueError("catalog semantic keys differ from producer bindings")

    numerical_validation = _validate_numerical_surface(
        plan=plan,
        arrays=arrays,
        catalog=catalog,
        rows=rows,
        receiver_summaries=receiver_events,
        reported_source_diagnostics=result["source_diagnostics"],
        controls=result["checks"],
    )
    source_diagnostics = result["source_diagnostics"]
    expected_source_checks = {
        "source_matrices_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_matrix_digest"]
            == source_diagnostics["R6i"]["source_matrix_digest"]
        ),
        "source_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_coordinate_digest"]
            == source_diagnostics["R6i"]["source_coordinate_digest"]
        ),
        "perturbed_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["perturbed_coordinate_digest"]
            == source_diagnostics["R6i"]["perturbed_coordinate_digest"]
        ),
    }
    if any(result["checks"][name] is not value for name, value in expected_source_checks.items()):
        raise ValueError("source-diagnostic controls differ from regenerated diagnostics")
    legitimately_variable_controls = set(expected_source_checks)
    for name in (
        set(SCIENTIFIC_CONTROL_NAMES)
        | set(PROVENANCE_CONTROL_NAMES)
    ) - legitimately_variable_controls:
        if result["checks"][name] is not True:
            raise ValueError(f"independently reconstructed control failed: {name}")

    store_events = [event["payload"] for event in events if event["kind"] == "store"]
    for payload in store_events:
        key = (
            f"r{payload['depth_index']:02d}__{payload['map']}__clean_templates"
        )
        state = np.ascontiguousarray(
            arrays[key][payload["source_index"]], dtype="<c16"
        )
        digest = _sha256_bytes(state.tobytes())
        if payload["stored_template_digest"] != digest:
            raise ValueError("store event digest does not resolve to its catalog slice")

    fresh_decision = classify_protocol(rows, result["checks"], plan=plan)
    _require_json_exact(
        result.get("decision"),
        fresh_decision,
        name="cached result decision versus fresh classification",
    )
    if set(decision_record) != DECISION_ARTIFACT_FIELDS:
        raise ValueError("decision artifact field set is not closed")
    if (
        decision_record.get("schema_version")
        != "hypercomplexbrain.r6l-decision-artifact.v1"
        or decision_record.get("ledger_root") != result["ledger_root"]
        or decision_record.get("result_sha256") != _file_digest(paths["result"])
    ):
        raise ValueError("decision artifact cross-binding differs")
    _require_json_exact(
        decision_record.get("decision"),
        fresh_decision,
        name="decision artifact decision",
    )

    expected_artifact_bindings = {
        "events_sha256": _file_digest(paths["events"]),
        "npz_sha256": _file_digest(paths["npz"]),
        "catalog_sha256": _file_digest(paths["catalog"]),
    }
    _require_json_exact(
        result.get("artifact_bindings"),
        expected_artifact_bindings,
        name="result artifact bindings",
    )

    receipt = None
    if require_receipt:
        receipt = _load_json(paths["receipt"])
        if set(receipt) != RUN_RECEIPT_FIELDS:
            raise ValueError("run receipt field set is not closed")
        manifest, _freeze = _manifest_and_receipt()
        dependencies = tuple(dict.fromkeys(
            SOURCE_PATHS + tuple(manifest["baseline"]["normative_upstream_sha256"])
        ))
        before = receipt.get("source_hashes_before")
        after = receipt.get("source_hashes_after")
        expected_receipt_fields = {
            "schema_version": "hypercomplexbrain.r6l-run-receipt.v1",
            "preregistration_commit_sha": C_PRE_SHA,
            "source_commit_sha": source_commit,
            "manifest_sha256": MANIFEST_SHA256,
            "freeze_receipt_sha256": _file_digest(FREEZE_RECEIPT),
            "effective_protocol_digest": EFFECTIVE_PROTOCOL_DIGEST,
            "source_hashes_stable": True,
            "sample_size": 384,
            "event_count": 716,
            "ledger_root": result["ledger_root"],
            "protocol_grid_digest": canonical_digest(expected_ids),
            "controls": result["checks"],
        }
        for field, expected in expected_receipt_fields.items():
            _require_json_exact(
                receipt.get(field), expected, name=f"run receipt field {field}"
            )
        if (
            not isinstance(before, dict)
            or not isinstance(after, dict)
            or set(before) != set(dependencies)
        ):
            raise ValueError("run receipt frozen bindings differ")
        _require_json_exact(
            before, after, name="run receipt before/after source hashes"
        )
        for relative, digest in before.items():
            _require_sha256(digest, name=f"receipt dependency {relative}")
            if digest != _file_digest(ROOT / relative):
                raise ValueError(f"live dependency differs from run receipt: {relative}")
            if digest != _git_blob_digest(source_commit, relative):
                raise ValueError(f"C_exec dependency differs from run receipt: {relative}")
        for relative, expected in manifest["baseline"][
            "normative_upstream_sha256"
        ].items():
            if before[relative] != expected:
                raise ValueError(f"normative upstream digest differs: {relative}")
        expected_output_hashes = {
            _relative(paths[name]): _file_digest(paths[name])
            for name in ("events", "npz", "catalog", "result", "decision")
        }
        _require_json_exact(
            receipt.get("output_hashes"),
            expected_output_hashes,
            name="run receipt output hashes",
        )
        expected_commands = {
            "run": RUN_COMMAND,
            "recompute": RECOMPUTE_COMMAND,
            "envelope_template": (
                "python experiments/run_common_receiver_reservoir.py envelope "
                "--artifact-dir artifacts/r6l_common_receiver --raw-commit C_RAW_SHA "
                "--source-commit C_EXEC_SHA --prereg-commit C_PRE_SHA"
            ),
        }
        _require_json_exact(
            receipt.get("commands"), expected_commands, name="run receipt commands"
        )
        environment = receipt.get("environment")
        if not isinstance(environment, dict) or set(environment) != {
            "fields", "digest",
        }:
            raise ValueError("run receipt environment field set differs")
        environment_fields = environment.get("fields")
        if (
            not isinstance(environment_fields, dict)
            or set(environment_fields) != {"python", "platform", "machine", "numpy"}
            or not all(isinstance(value, str) for value in environment_fields.values())
        ):
            raise ValueError("run receipt environment fields/types differ")
        expected_environment_digest = _sha256_bytes(
            json.dumps(environment_fields, sort_keys=True).encode("utf-8")
        )
        if environment.get("digest") != expected_environment_digest:
            raise ValueError("run receipt environment digest differs")

    if raw_commit is not None:
        for name in required_names:
            relative = _relative(paths[name])
            if _git_blob_digest(raw_commit, relative) != _file_digest(paths[name]):
                raise ValueError(f"raw commit blob differs from live {relative}")

    return {
        "plan": plan,
        "result": result,
        "catalog": catalog,
        "arrays": arrays,
        "decision_record": decision_record,
        "events": events,
        "event_validation": event_validation,
        "catalog_validation": catalog_validation,
        "numerical_validation": numerical_validation,
        "receipt": receipt,
    }


def _compare_numeric(first: object, second: object, *, tol: float = 1e-10) -> float:
    if first is None or second is None:
        if first is not second:
            raise ValueError("null/numeric mismatch")
        return 0.0
    left = float(first)
    right = float(second)
    if not np.isfinite(left) or not np.isfinite(right):
        raise ValueError("nonfinite comparison value")
    delta = abs(left - right)
    if delta > tol:
        raise ValueError(f"numeric deviation {delta} exceeds {tol}")
    return delta


_TOLERANT_TREE_PATH_SUFFIXES = (
    ".correct_probability",
    ".mutual_information_bits",
    ".mean_reject_probability",
    ".maximum_central_pair_residual",
)


def _compare_tree(first: object, second: object, *, path: str = "") -> tuple[float, int]:
    """Compare JSON trees with tolerance only on preregistered numeric witnesses."""

    if isinstance(first, dict) or isinstance(second, dict):
        if not isinstance(first, dict) or not isinstance(second, dict):
            raise ValueError(f"mapping/type mismatch at {path}")
        if set(first) != set(second):
            raise ValueError(f"field set differs at {path}")
        maximum = 0.0
        count = 0
        for key in sorted(first):
            delta, additions = _compare_tree(
                first[key], second[key], path=f"{path}.{key}"
            )
            maximum = max(maximum, delta)
            count += additions
        return maximum, count
    if isinstance(first, list) or isinstance(second, list):
        if not isinstance(first, list) or not isinstance(second, list):
            raise ValueError(f"list/type mismatch at {path}")
        if len(first) != len(second):
            raise ValueError(f"list length differs at {path}")
        maximum = 0.0
        count = 0
        for index, (left, right) in enumerate(zip(first, second)):
            delta, additions = _compare_tree(
                left, right, path=f"{path}[{index}]"
            )
            maximum = max(maximum, delta)
            count += additions
        return maximum, count
    if type(first) is float or type(second) is float:
        if path.endswith(_TOLERANT_TREE_PATH_SUFFIXES):
            if type(first) not in (int, float) or type(second) not in (int, float):
                raise ValueError(f"numeric/type mismatch at {path}")
            return _compare_numeric(first, second), 1
        if type(first) is not type(second) or first != second:
            raise ValueError(f"exact numeric value/type differs at {path}")
        return 0.0, 0
    if type(first) is not type(second) or first != second:
        raise ValueError(f"exact value differs at {path}")
    return 0.0, 0


def _strip_array_digests(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "<producer-local-array-digest>"
            if key == "array_digest"
            else _strip_array_digests(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_strip_array_digests(item) for item in value]
    return value


def _catalog_projection(catalog: Mapping[str, object]) -> dict:
    aggregate_projection: dict[str, object] = {}
    for entry in catalog["aggregate_locators"].values():
        signature = canonical_bytes([
            {"npz_key": item["npz_key"], "slice": item["slice"]}
            for item in entry["items"]
        ]).decode("utf-8")
        if signature in aggregate_projection:
            raise ValueError("catalog has duplicate aggregate locator signatures")
        aggregate_projection[signature] = _strip_array_digests(entry)
    arrays = {
        key: {
            field: value
            for field, value in metadata.items()
            if field != "array_digest"
        }
        for key, metadata in catalog["arrays"].items()
    }
    return {
        "schema_version": catalog["schema_version"],
        "npz_key_count": catalog["npz_key_count"],
        "arrays": arrays,
        "aggregates_by_locator": aggregate_projection,
        "semantic_objects": catalog["semantic_objects"],
    }


def _event_projection_and_scalars(event: Mapping[str, object]) -> tuple[dict, dict[str, object]]:
    payload = json.loads(canonical_bytes(event["payload"]).decode("utf-8"))
    scalars: dict[str, object] = {}
    if event["kind"] == "store":
        payload["stored_template_digest"] = "<producer-local-array-digest>"
    elif event["kind"] == "common_receiver_freeze":
        for map_name in payload["clean_map_template_digests"]:
            payload["clean_map_template_digests"][map_name] = (
                "<producer-local-array-digest>"
            )
        for field in (
            "pooled_template_digest", "common_receiver_digest",
            "structural_receiver_cost_digest",
        ):
            payload[field] = "<producer-local-array-digest>"
        for field, value in payload["residuals"].items():
            scalars[f"residuals.{field}"] = value
            payload["residuals"][field] = "<numeric>"
    elif event["kind"] == "evaluation":
        for field in LOCAL_ARRAY_BINDING_FIELDS:
            payload["producer_array_bindings"][field] = (
                "<producer-local-array-digest>"
            )
        for field, value in payload["metrics"].items():
            if value is not None:
                scalars[f"metrics.{field}"] = value
                payload["metrics"][field] = "<numeric>"
    return {
        "sequence": event["sequence"],
        "kind": event["kind"],
        "key": event["key"],
        "payload": payload,
    }, scalars


def _semantic_compare(
    reference: Path,
    candidate: Path,
    *,
    source_commit: str,
    raw_commit: str,
    producer_envelope_sha256: str,
) -> dict:
    reference_surface = _validate_raw_surfaces(
        reference,
        source_commit=source_commit,
        raw_commit=raw_commit,
        require_receipt=True,
    )
    candidate_surface = _validate_raw_surfaces(
        candidate,
        source_commit=source_commit,
        raw_commit=None,
        require_receipt=False,
    )
    plan = reference_surface["plan"]
    ref_arrays = reference_surface["arrays"]
    new_arrays = candidate_surface["arrays"]
    schema = _expected_npz_schema(plan)
    maximum_matrix = 0.0
    matrix_count = 0
    stacked_roles = {
        "clean_templates", "clean_queries", "pooled_templates",
        "receiver_effects", "sqrt_effects", "state_noised_queries",
    }
    for key in sorted(schema):
        first = ref_arrays[key]
        second = new_arrays[key]
        items = zip(first, second) if schema[key]["role"] in stacked_roles else (
            (first, second),
        )
        for left, right in items:
            delta = float(np.linalg.norm(left - right, "fro"))
            maximum_matrix = max(maximum_matrix, delta)
            matrix_count += 1
            if delta > 1e-10:
                raise ValueError(f"matrix-item deviation for {key}: {delta}")

    ref_catalog_projection = _catalog_projection(reference_surface["catalog"])
    new_catalog_projection = _catalog_projection(candidate_surface["catalog"])
    _require_json_exact(
        ref_catalog_projection,
        new_catalog_projection,
        name="catalog semantic/locator projection",
    )

    ref_events = reference_surface["events"]
    new_events = candidate_surface["events"]
    maximum_scalar = 0.0
    scalar_count = 0
    for index, (first, second) in enumerate(zip(ref_events, new_events)):
        first_projection, first_scalars = _event_projection_and_scalars(first)
        second_projection, second_scalars = _event_projection_and_scalars(second)
        _require_json_exact(
            first_projection,
            second_projection,
            name=f"event semantic fields at sequence {index}",
        )
        if set(first_scalars) != set(second_scalars):
            raise ValueError(f"event numeric field set differs at sequence {index}")
        for field in sorted(first_scalars):
            delta = _compare_numeric(first_scalars[field], second_scalars[field])
            maximum_scalar = max(maximum_scalar, delta)
            scalar_count += 1

    ref_decision = reference_surface["decision_record"]["decision"]
    new_decision = candidate_surface["decision_record"]["decision"]
    delta, additions = _compare_tree(ref_decision, new_decision, path="decision")
    maximum_scalar = max(maximum_scalar, delta)
    scalar_count += additions

    ref_result = dict(reference_surface["result"])
    new_result = dict(candidate_surface["result"])
    for value in (ref_result, new_result):
        value.pop("receiver_summaries")
        value.pop("retrieval_rows")
        value.pop("decision")
        value.pop("artifact_bindings")
        value["ledger_root"] = "<producer-local-ledger-root>"
        value["event_validation"] = dict(value["event_validation"])
        value["event_validation"]["ledger_root"] = "<producer-local-ledger-root>"
        value["source_diagnostics"] = json.loads(
            canonical_bytes(value["source_diagnostics"]).decode("utf-8")
        )
        for map_value in value["source_diagnostics"].values():
            for field in (
                "source_matrix_digest", "source_coordinate_digest",
                "perturbed_coordinate_digest",
            ):
                map_value[field] = "<producer-local-numerical-digest>"
    delta, additions = _compare_tree(ref_result, new_result, path="result")
    maximum_scalar = max(maximum_scalar, delta)
    scalar_count += additions

    return {
        "schema_version": "hypercomplexbrain.r6l-recompute-receipt.v1",
        "producer_envelope_sha256": producer_envelope_sha256,
        "producer_commit_sha": raw_commit,
        "source_commit_sha": source_commit,
        "preregistration_commit_sha": C_PRE_SHA,
        "reference_ledger_root": reference_surface["event_validation"]["ledger_root"],
        "regenerated_ledger_root": candidate_surface["event_validation"]["ledger_root"],
        "exact_protocol_cells": 384,
        "exact_event_keys": 716,
        "compared_npz_arrays": 1008,
        "compared_matrix_items": matrix_count,
        "compared_scalar_fields": scalar_count,
        "maximum_scalar_absolute_deviation": maximum_scalar,
        "maximum_matrix_frobenius_deviation": maximum_matrix,
        "surface_checks": {
            "reference_raw_valid": True,
            "regenerated_raw_valid": True,
            "catalog_projection_equal": True,
            "events_semantically_equal": True,
            "decision_semantically_equal": True,
            "result_semantically_equal": True,
        },
        "semantic_recomputation_passed": True,
        "claim_level_independence": False,
        "note": "This local command is a comparator, not an independent witness sidecar.",
    }


def recompute_command(reference_dir: Path) -> int:
    reference = reference_dir.resolve()
    if reference != DEFAULT_OUT.resolve() or not reference.is_dir():
        raise ValueError("reference directory must be the complete R6l artifact directory")
    envelope_path = _scientific_paths(reference)["envelope"]
    if not envelope_path.is_file():
        raise FileNotFoundError("recompute requires the committed producer envelope")
    if str(_run_git("status", "--porcelain=v1", "--untracked-files=all")) != "":
        raise RuntimeError("recompute requires a clean evidence worktree")
    envelope = _load_json(envelope_path)
    raw_commit = str(envelope.get("commit_sha", ""))
    source_commit = str(envelope.get("source_commit_sha", ""))
    if envelope.get("preregistration_commit_sha") != C_PRE_SHA:
        raise ValueError("producer envelope does not bind C_pre")
    head = str(_run_git("rev-parse", "HEAD")).strip()
    if str(_run_git("rev-parse", f"{head}^")).strip() != raw_commit:
        raise RuntimeError("recompute requires the direct C_env child of C_raw")
    if sorted(_changed_paths(raw_commit, head)) != [ENVELOPE_PATH]:
        raise RuntimeError("C_env is not an envelope-only commit")
    if (
        str(_run_git("rev-parse", f"{raw_commit}^")).strip() != source_commit
        or str(_run_git("rev-parse", f"{source_commit}^")).strip() != C_PRE_SHA
    ):
        raise RuntimeError("producer C_pre/C_exec/C_raw chronology differs")
    if sorted(_changed_paths(C_PRE_SHA, source_commit)) != sorted(C_EXEC_DELTA_PATHS):
        raise RuntimeError("recorded C_exec path delta differs")
    if sorted(_changed_paths(source_commit, raw_commit)) != sorted(OUTPUT_PATHS):
        raise RuntimeError("recorded C_raw path delta differs")
    raw_surface = _validate_raw_surfaces(
        reference,
        source_commit=source_commit,
        raw_commit=raw_commit,
        require_receipt=True,
    )
    _validate_r6l_envelope_dict(
        envelope,
        raw_commit=raw_commit,
        source_commit=source_commit,
        raw_surface=raw_surface,
    )
    before = {
        _relative(path): _file_digest(path)
        for path in reference.rglob("*") if path.is_file()
    }
    source_hashes = raw_surface["receipt"]["source_hashes_before"]
    controls = {
        name: raw_surface["result"]["checks"][name]
        for name in PROVENANCE_CONTROL_NAMES
    }
    if not all(value is True for value in controls.values()):
        raise RuntimeError("recorded producer provenance controls did not all pass")
    with tempfile.TemporaryDirectory(prefix="r6l-recompute-") as temporary:
        candidate = Path(temporary) / "r6l_common_receiver"
        _produce_scientific_surfaces(
            candidate,
            source_commit=source_commit,
            source_hashes_before=source_hashes,
            runner_controls=controls,
            write_receipt=False,
        )
        receipt = _semantic_compare(
            reference,
            candidate,
            source_commit=source_commit,
            raw_commit=raw_commit,
            producer_envelope_sha256=_file_digest(envelope_path),
        )
    after = {
        _relative(path): _file_digest(path)
        for path in reference.rglob("*") if path.is_file()
    }
    if before != after:
        raise RuntimeError("reference artifacts changed during recomputation")
    receipt["recompute_command"] = RECOMPUTE_COMMAND
    receipt["producer_environment"] = raw_surface["receipt"]["environment"]
    receipt["recompute_environment"] = environment_digest()
    print(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False))
    return 0


def _validate_r6l_envelope_dict(
    payload: Mapping[str, object],
    *,
    raw_commit: str,
    source_commit: str,
    raw_surface: Mapping[str, object],
) -> None:
    extension_fields = {
        "source_commit_sha",
        "preregistration_commit_sha",
        "preregistration_remote_ref",
        "preregistration_remote_url",
        "recompute_command",
        "packaging_command",
        "independent",
    }
    expected_fields = set(EvidenceEnvelope.__dataclass_fields__) | extension_fields
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise ValueError("R6l envelope field set is not closed")
    result = raw_surface["result"]
    receipt = raw_surface["receipt"]
    decision = result["decision"]
    expected_observed = {
        "sample_size": 384,
        "sample_unit": result["sample_unit"],
        "all_controls_pass": decision["controls_pass"],
        "verdict": decision["verdict"],
        "signed_survival": decision["signed_survival"],
        "projective_survival": decision["projective_survival"],
        "radial_survival": decision["radial_survival"],
        "joint_survival": decision["joint_survival"],
        "clean_projective_passing_depth_count": decision[
            "clean_projective_passing_depth_count"
        ],
        "ledger_root": result["ledger_root"],
    }
    expected_packaging = (
        "python experiments/run_common_receiver_reservoir.py envelope "
        "--artifact-dir artifacts/r6l_common_receiver "
        f"--raw-commit {raw_commit} --source-commit {source_commit} "
        f"--prereg-commit {C_PRE_SHA}"
    )
    exact_values = {
        "schema_version": "hypercomplexbrain.evidence.v1",
        "claim_id": "EXP-R6L-COMMON-RECEIVER",
        "evidence_tag": "M",
        "command": RUN_COMMAND,
        "observed_result": expected_observed,
        "commit_sha": raw_commit,
        "working_directory": ".",
        "platform": receipt["environment"]["fields"]["platform"],
        "environment": receipt["environment"],
        "input_hashes": result["input_hashes"],
        "seeds": [],
        "environment_dependent": [],
        "uncertainty": {
            "kind": "deterministic finite-grid producer run",
            "confidence_interval": None,
            "independent_replication": False,
            "source_commit_sha": source_commit,
            "preregistration_commit_sha": C_PRE_SHA,
        },
        "producer": "experiments/run_common_receiver_reservoir.py",
        "verifier": "",
        "timestamp": "",
        "signature_status": "unsigned",
        "typed_remainders": result["typed_remainders"],
        "verification_mode": "not_requested",
        "witness_environment": "",
        "witness_notes": "",
        "witness_conversation_url": "",
        "source_commit_sha": source_commit,
        "preregistration_commit_sha": C_PRE_SHA,
        "preregistration_remote_ref": TAG_REF,
        "preregistration_remote_url": (
            "https://github.com/jesusvilela/hypercomplexbrain/commit/" + C_PRE_SHA
        ),
        "recompute_command": RECOMPUTE_COMMAND,
        "packaging_command": expected_packaging,
        "independent": False,
    }
    for field, expected in exact_values.items():
        _require_json_exact(
            payload.get(field), expected, name=f"R6l envelope field {field}"
        )
    if set(payload["observed_result"]) != OBSERVED_RESULT_FIELDS:
        raise ValueError("R6l observed-result field set is not closed")
    manifest = _load_json(MANIFEST)
    expected_paths = set(DECLARED_RAW_PATHS) | set(
        manifest["baseline"]["normative_upstream_sha256"]
    )
    raw_artifacts = payload.get("raw_artifacts")
    if not isinstance(raw_artifacts, dict) or set(raw_artifacts) != expected_paths:
        raise ValueError("R6l raw artifact map is not the frozen 27-path union")
    for relative, digest in raw_artifacts.items():
        _require_sha256(digest, name=f"envelope raw artifact {relative}")
        if digest != _file_digest(ROOT / relative):
            raise ValueError(f"envelope raw artifact differs from live bytes: {relative}")
        if digest != _git_blob_digest(raw_commit, relative):
            raise ValueError(f"envelope raw artifact differs from C_raw: {relative}")


def envelope_command(
    artifact_dir: Path,
    *,
    raw_commit: str,
    source_commit: str,
    prereg_commit: str,
) -> int:
    artifact_dir = artifact_dir.resolve()
    if artifact_dir != DEFAULT_OUT.resolve():
        raise ValueError("artifact directory must be the frozen R6l path")
    if prereg_commit != C_PRE_SHA:
        raise ValueError("provided preregistration commit differs from C_pre")
    head = str(_run_git("rev-parse", "HEAD")).strip()
    if head != raw_commit:
        raise RuntimeError("envelope phase requires HEAD exactly at C_raw")
    if str(_run_git("status", "--porcelain=v1", "--untracked-files=all")) != "":
        raise RuntimeError("envelope phase requires a clean C_raw worktree")
    raw_parent = str(_run_git("rev-parse", f"{raw_commit}^")).strip()
    source_parent = str(_run_git("rev-parse", f"{source_commit}^")).strip()
    if raw_parent != source_commit or source_parent != C_PRE_SHA:
        raise RuntimeError("C_pre/C_exec/C_raw are not direct chronological commits")
    if sorted(_changed_paths(C_PRE_SHA, source_commit)) != sorted(C_EXEC_DELTA_PATHS):
        raise RuntimeError("C_exec path delta differs from the frozen six paths")
    if sorted(_changed_paths(source_commit, raw_commit)) != sorted(OUTPUT_PATHS):
        raise RuntimeError("C_raw path delta differs from the frozen six outputs")
    paths = _scientific_paths(artifact_dir)
    if paths["envelope"].exists() or _tree_has_path(raw_commit, ENVELOPE_PATH):
        raise FileExistsError("producer envelope already exists in filesystem or C_raw")
    raw_surface = _validate_raw_surfaces(
        artifact_dir,
        source_commit=source_commit,
        raw_commit=raw_commit,
        require_receipt=True,
    )
    result = raw_surface["result"]
    run_receipt = raw_surface["receipt"]

    manifest = _load_json(MANIFEST)
    all_paths = list(DECLARED_RAW_PATHS) + list(
        manifest["baseline"]["normative_upstream_sha256"]
    )
    raw_artifacts: dict[str, str] = {}
    for relative in all_paths:
        blob_digest = _git_blob_digest(raw_commit, relative)
        live_digest = _file_digest(ROOT / relative)
        if blob_digest != live_digest:
            raise RuntimeError(f"C_raw blob/worktree mismatch for {relative}")
        raw_artifacts[relative] = blob_digest
    for relative, expected in manifest["baseline"]["normative_upstream_sha256"].items():
        if raw_artifacts[relative] != expected:
            raise RuntimeError(f"upstream digest drift at C_raw for {relative}")
    before = dict(raw_artifacts)
    packaging_command = (
        "python experiments/run_common_receiver_reservoir.py envelope "
        "--artifact-dir artifacts/r6l_common_receiver "
        f"--raw-commit {raw_commit} --source-commit {source_commit} "
        f"--prereg-commit {prereg_commit}"
    )
    decision = result["decision"]
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6L-COMMON-RECEIVER",
        evidence_tag="M",
        command=RUN_COMMAND,
        observed_result={
            "sample_size": 384,
            "sample_unit": result["sample_unit"],
            "all_controls_pass": decision["controls_pass"],
            "verdict": decision["verdict"],
            "signed_survival": decision["signed_survival"],
            "projective_survival": decision["projective_survival"],
            "radial_survival": decision["radial_survival"],
            "joint_survival": decision["joint_survival"],
            "clean_projective_passing_depth_count": decision[
                "clean_projective_passing_depth_count"
            ],
            "ledger_root": result["ledger_root"],
        },
        commit_sha=raw_commit,
        working_directory=".",
        platform=run_receipt["environment"]["fields"]["platform"],
        environment=run_receipt["environment"],
        input_hashes=result["input_hashes"],
        seeds=[],
        raw_artifacts=raw_artifacts,
        environment_dependent=[],
        uncertainty={
            "kind": "deterministic finite-grid producer run",
            "confidence_interval": None,
            "independent_replication": False,
            "source_commit_sha": source_commit,
            "preregistration_commit_sha": prereg_commit,
        },
        producer="experiments/run_common_receiver_reservoir.py",
        verifier="",
        timestamp="",
        signature_status="unsigned",
        verification_mode="not_requested",
        typed_remainders=result["typed_remainders"],
    )
    payload = envelope.to_dict()
    payload.update({
        "source_commit_sha": source_commit,
        "preregistration_commit_sha": prereg_commit,
        "preregistration_remote_ref": TAG_REF,
        "preregistration_remote_url": (
            "https://github.com/jesusvilela/hypercomplexbrain/commit/" + C_PRE_SHA
        ),
        "recompute_command": RECOMPUTE_COMMAND,
        "packaging_command": packaging_command,
        "independent": False,
    })
    _validate_r6l_envelope_dict(
        payload,
        raw_commit=raw_commit,
        source_commit=source_commit,
        raw_surface=raw_surface,
    )
    verification = verify(envelope, repo_root=ROOT, check_commit=True)
    if not verification.ok or verification.effective_n != 384 or verification.independent:
        raise RuntimeError(f"generic evidence verification failed: {verification}")
    _write_json_once(paths["envelope"], payload)
    try:
        _require_json_exact(
            _load_json(paths["envelope"]),
            payload,
            name="written producer envelope round trip",
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    status_paths = {
        line[3:].strip().replace("\\", "/")
        for line in str(
            _run_git("status", "--porcelain=v1", "--untracked-files=all")
        ).splitlines()
        if len(line) >= 4
    }
    if status_paths != {ENVELOPE_PATH}:
        raise RuntimeError("post-envelope worktree differs from the one-envelope delta")
    after = {
        relative: _file_digest(ROOT / relative) for relative in raw_artifacts
    }
    if before != after:
        raise RuntimeError("raw artifact bytes changed during envelope packaging")
    print(json.dumps({
        "envelope": _relative(paths["envelope"]),
        "commit_sha": raw_commit,
        "source_commit_sha": source_commit,
        "preregistration_commit_sha": prereg_commit,
        "effective_sample_size": verification.effective_n,
        "independent": False,
    }, sort_keys=True, indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output-dir", type=Path, required=True)
    envelope_parser = subparsers.add_parser("envelope")
    envelope_parser.add_argument("--artifact-dir", type=Path, required=True)
    envelope_parser.add_argument("--raw-commit", required=True)
    envelope_parser.add_argument("--source-commit", required=True)
    envelope_parser.add_argument("--prereg-commit", required=True)
    recompute_parser = subparsers.add_parser("recompute")
    recompute_parser.add_argument("--reference-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        return run_command((ROOT / args.output_dir).resolve())
    if args.command == "envelope":
        return envelope_command(
            (ROOT / args.artifact_dir).resolve(),
            raw_commit=args.raw_commit,
            source_commit=args.source_commit,
            prereg_commit=args.prereg_commit,
        )
    if args.command == "recompute":
        return recompute_command((ROOT / args.reference_dir).resolve())
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
