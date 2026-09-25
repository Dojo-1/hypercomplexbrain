"""QSigma-R6M: run the depth-parametric fork at R6l's own five depths.

    PYTHONPATH=src python3 experiments/run_r6m_parametric_equivalence.py

Evaluates NO held-out depth. build_fork refuses them without a licence, and
this runner never passes one.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.common_receiver_parametric import (  # noqa: E402
    SEALED_GRID, SEALED_SOURCES, build_fork, equivalence_evidence,
    equivalence_verdict, exercise_the_frozen_rule, run_fork)
from aionq.semantic_reproduction import perturb_leaf  # noqa: E402

MANIFEST = ROOT / "manifests/qsigma_r6m_parametric_receiver_equivalence_preregistration.json"
R6L = ROOT / "artifacts/r6l_common_receiver"
OUT = ROOT / "artifacts/r6m_parametric_equivalence/equivalence.json"

#: R6k-W1's committed comparator tolerance, "never widened". R6M introduces none.
TOLERANCE = 1e-10
#: R6k-W1's control C1: one scientific leaf moved by this must come back failing.
PERTURBATION = 1e-9


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_references(scope: dict) -> dict:
    """INVALID's precondition, checked by bytes rather than by trust."""
    commits = {role: scope[key] for role, key in (
        ("raw", "reference_raw_commit"), ("source", "reference_source_commit"),
        ("envelope", "reference_envelope_commit"))}
    resolved = {role: _git("cat-file", "-t", sha).stdout.strip() == b"commit"
                for role, sha in commits.items()}

    sources = {}
    for name, (path, expected) in SEALED_SOURCES.items():
        relative = path.relative_to(ROOT).as_posix()
        at_commit = _sha(_git("show", f"{commits['source']}:{relative}").stdout)
        sources[relative] = {"worktree": _sha(path.read_bytes()) == expected,
                             "at_source_commit": at_commit == expected}

    envelope_path = R6L / "common_receiver_reservoir.envelope.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    bound = {}
    for relative, digest in envelope["raw_artifacts"].items():
        blob = _git("show", f"{commits['raw']}:{relative}").stdout
        bound[relative] = bool(blob) and _sha(blob) == digest.split(":")[-1]

    reference_rows = R6L / "common_receiver_reservoir.json"
    rows_relative = reference_rows.relative_to(ROOT).as_posix()
    rows_at_raw = _sha(_git("show", f"{commits['raw']}:{rows_relative}").stdout)
    rows_ok = _sha(reference_rows.read_bytes()) == rows_at_raw

    envelope_at_seal = _sha(_git("show", f"{commits['envelope']}:"
                                 f"{envelope_path.relative_to(ROOT).as_posix()}").stdout)
    verified = (all(resolved.values())
                and all(v["worktree"] and v["at_source_commit"] for v in sources.values())
                and bound and all(bound.values()) and rows_ok)
    return {
        "verified": verified,
        "commits_resolve": resolved,
        "sealed_sources": sources,
        "envelope_bound_artifacts": len(bound),
        "envelope_bound_artifacts_verified_at_raw_commit": sum(bound.values()),
        "reference_rows_byte_identical_to_raw_commit": rows_ok,
        "envelope_bytes_identical_to_seal_commit": _sha(envelope_path.read_bytes()) == envelope_at_seal,
        "envelope_reading": ("verified THROUGH WHAT IT BINDS, per the pre-run note; its own bytes carry "
                             "the evidence.v1 -> v2 schema migration from a677880"),
    }


def summarise(evidence: dict) -> dict:
    comparison = evidence["comparison"]
    return {key: evidence[key] for key in evidence if key != "comparison"} | {
        "comparison": {
            "tolerance": comparison["tolerance"],
            "shared_leaves": comparison["shared_leaves"],
            "scientific_leaves_compared": comparison["scientific_leaves_compared"],
            "worst_absolute_difference": comparison["worst_absolute_difference"],
            "worst_difference_path": comparison["worst_difference_path"],
            "scientific_leaves_exceeding_tolerance": len(comparison["scientific_leaves_exceeding_tolerance"]),
            "discrete_mismatches": len(comparison["discrete_mismatches"]),
            "discrete_mismatch_examples": comparison["discrete_mismatches"][:5],
            "identity_leaves": comparison["identity_leaves"],
            "identity_mismatches": comparison["identity_mismatches"],
            "only_in_committed": comparison["only_in_produced"][:10],
            "only_in_fork": comparison["only_in_reproduced"][:10],
            "non_finite_leaves": comparison["non_finite_leaves"],
        }}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scope = manifest["scope"]
    started = time.time()

    references = verify_references(scope)
    receipt = exercise_the_frozen_rule(scope["sealed_reference_depths"], None)
    if [d for d, _ in SEALED_GRID] != scope["sealed_reference_depths"]:
        raise SystemExit("the grid the fork runs is not the grid the manifest froze")

    committed_report = json.loads((R6L / "common_receiver_reservoir.json").read_text(encoding="utf-8"))
    committed_rows = committed_report["retrieval_rows"]
    digest = committed_report["effective_protocol_digest"]

    # ---- the round -----------------------------------------------------
    t0 = time.time()
    fork = build_fork(SEALED_GRID)
    fork_report = run_fork(fork, effective_protocol_digest=digest)
    fork_seconds = time.time() - t0
    evidence = equivalence_evidence(
        committed_rows, fork_report["retrieval_rows"], tolerance=TOLERANCE,
        references_verified=references["verified"],
        criterion_receipt_clean=receipt["clean"])
    verdict = equivalence_verdict(evidence)

    # ---- post-freeze controls: inform the reading, never the verdict -----
    # R6k-W1's C1: move one scientific leaf by 1e-9 and require NOT_EQUIVALENT.
    # Without it, EQUIVALENT could mean the comparison compared nothing.
    ordered = sorted(fork_report["retrieval_rows"], key=lambda r: str(r["protocol_cell_id"]))
    probe_path = ".retrieval_rows[0].metrics.correct_probability"
    perturbed = perturb_leaf({"retrieval_rows": ordered}, probe_path, PERTURBATION)["retrieval_rows"]
    perturbed_evidence = equivalence_evidence(
        committed_rows, perturbed, tolerance=TOLERANCE,
        references_verified=references["verified"], criterion_receipt_clean=receipt["clean"])
    c_perturbation = {
        "path": probe_path, "delta": PERTURBATION,
        "verdict": equivalence_verdict(perturbed_evidence),
        "detected": equivalence_verdict(perturbed_evidence) == "NOT_EQUIVALENT",
    }

    import aionq.common_receiver_reservoir as sealed
    t1 = time.time()
    sealed_report = sealed.execute_protocol(sealed.plan_protocol(digest)).report
    sealed_seconds = time.time() - t1
    platform_evidence = equivalence_evidence(
        committed_rows, sealed_report["retrieval_rows"], tolerance=TOLERANCE,
        references_verified=references["verified"], criterion_receipt_clean=receipt["clean"])
    fork_vs_fresh = equivalence_evidence(
        sealed_report["retrieval_rows"], fork_report["retrieval_rows"], tolerance=0.0,
        references_verified=True, criterion_receipt_clean=True)

    result = {
        "schema": "hypercomplexbrain.r6m-equivalence.v1",
        "round": "QSigma-R6M",
        "verdict": verdict,
        "preregistration": MANIFEST.relative_to(ROOT).as_posix(),
        "grid": [d for d, _ in SEALED_GRID],
        "held_out_depths_evaluated": [],
        "tolerance": TOLERANCE,
        "references": references,
        "criterion_receipt": {"clean": receipt["clean"],
                              "declaration_valid": receipt["declaration_valid"],
                              "skipped": receipt["skipped"],
                              "disjointness_samples": receipt["disjointness"]["samples"],
                              "knobs": receipt["parameters"]["knobs"]},
        "evidence": summarise(evidence),
        "post_freeze_controls": {
            "note": "inform the reading of the verdict and can never change it",
            "C_perturbation": c_perturbation,
            "C_platform_sealed_fresh_vs_committed": {
                "verdict_it_would_get": equivalence_verdict(platform_evidence),
                "evidence": summarise(platform_evidence)},
            "C_fork_vs_sealed_fresh_bitwise": {
                "tolerance": 0.0,
                "worst_absolute_difference": fork_vs_fresh["comparison"]["worst_absolute_difference"],
                "scientific_leaves_compared": fork_vs_fresh["comparison"]["scientific_leaves_compared"],
                "identity_mismatches": fork_vs_fresh["comparison"]["identity_mismatches"],
                "discrete_mismatches": len(fork_vs_fresh["comparison"]["discrete_mismatches"])},
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "seconds": {"fork": round(fork_seconds, 1), "sealed_fresh": round(sealed_seconds, 1),
                    "total": round(time.time() - started, 1)},
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "seconds": result["seconds"],
                      "C_perturbation_detected": c_perturbation["detected"],
                      "C_platform": result["post_freeze_controls"]["C_platform_sealed_fresh_vs_committed"]["verdict_it_would_get"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
