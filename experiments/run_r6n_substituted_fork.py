"""QSigma-R6N: license the substituted fork, then rehearse it on a decoy grid.

    PYTHONPATH=src python3 experiments/run_r6n_substituted_fork.py

Evaluates NO held-out depth. The decoy grid is neither sealed nor held-out,
and its metrics are recorded by digest and finiteness only.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.common_receiver_parametric import (  # noqa: E402
    SEALED_GRID, SEALED_SOURCES, build_fork, equivalence_evidence, equivalence_verdict)
from aionq.common_receiver_substituted import (  # noqa: E402
    DECOY_GRID, build_substituted_fork, exercise_the_frozen_rule, licence_verdict,
    substituted_source)

MANIFEST = ROOT / "manifests/qsigma_r6n_substituted_fork_preregistration.json"
R6L = ROOT / "artifacts/r6l_common_receiver/common_receiver_reservoir.json"
R6M = ROOT / "artifacts/r6m_parametric_equivalence/equivalence.json"
OUT = ROOT / "artifacts/r6n_substituted_fork/licence.json"
TOLERANCE = 1e-10
R6L_DIGEST = "sha256:ac13a2085a9319066b05e29b193469c430f1f1c205c0b735ce00133b80adbbab"
STORE_KEY_ERROR = "reservoir key differs from the portable store identity"


def _git_blob(commit: str, relative: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT,
                          capture_output=True).stdout


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def references() -> dict:
    sources = {name: _sha(path.read_bytes()) == expected
               for name, (path, expected) in SEALED_SOURCES.items()}
    rows = _sha(R6L.read_bytes()) == _sha(_git_blob("1421ec2eb966eaaf9af78d9ffc1ea727429b9a18",
                                                      R6L.relative_to(ROOT).as_posix()))
    r6m = (_sha(R6M.read_bytes()) == _sha(_git_blob("499b115", R6M.relative_to(ROOT).as_posix()))
           and json.loads(R6M.read_text(encoding="utf-8"))["verdict"] == "EQUIVALENT_ON_SEALED_GRID")
    return {"sealed_sources": sources, "r6l_rows_at_raw_commit": rows,
            "r6m_licence_as_committed_and_equivalent": r6m,
            "verified": all(sources.values()) and rows and r6m}


def main() -> int:
    started = time.time()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    refs = references()
    try:
        _, substitution = substituted_source()
        exactly_once = substitution["occurrences_of_old"] == 1
    except Exception as error:                        # target missing or duplicated
        substitution, exactly_once = {"error": str(error)}, False

    # C4 first: the rule is exercised before any real comparison exists.
    receipt = exercise_the_frozen_rule([d for d, _ in SEALED_GRID], None)
    c4 = bool(receipt["clean"])

    c1 = bool(exactly_once and substitution.get("only_difference"))

    # C2: sealed grid, against the committed rows AND bitwise against the sealed module fresh.
    committed = json.loads(R6L.read_text(encoding="utf-8"))["retrieval_rows"]
    sub = build_substituted_fork(SEALED_GRID).common_receiver
    sub_rows = sub.execute_protocol(sub.plan_protocol(R6L_DIGEST)).report["retrieval_rows"]
    import aionq.common_receiver_reservoir as sealed
    fresh_rows = sealed.execute_protocol(sealed.plan_protocol(R6L_DIGEST)).report["retrieval_rows"]
    vs_committed = equivalence_evidence(committed, sub_rows, tolerance=TOLERANCE,
                                        references_verified=refs["verified"],
                                        criterion_receipt_clean=c4)
    vs_fresh = equivalence_evidence(fresh_rows, sub_rows, tolerance=0.0,
                                    references_verified=True, criterion_receipt_clean=True)
    c2 = (equivalence_verdict(vs_committed) == "EQUIVALENT_ON_SEALED_GRID"
          and equivalence_verdict(vs_fresh) == "EQUIVALENT_ON_SEALED_GRID"
          and vs_fresh["comparison"]["worst_absolute_difference"] == 0.0
          and vs_fresh["comparison"]["identity_mismatches"] == 0)

    # C3 control: the UNREPAIRED fork must fail on the decoy grid.
    unrepaired = build_fork(DECOY_GRID).common_receiver
    try:
        unrepaired.execute_protocol(unrepaired.plan_protocol(R6L_DIGEST))
        control = {"failed": False, "error": None}
    except ValueError as error:
        control = {"failed": STORE_KEY_ERROR in str(error), "error": str(error)}

    # C3: the substituted fork must complete on the decoy grid, correctly labelled.
    decoy_fork = build_substituted_fork(DECOY_GRID).common_receiver
    try:
        decoy_run = decoy_fork.execute_protocol(decoy_fork.plan_protocol(R6L_DIGEST))
        rows = decoy_run.report["retrieval_rows"]
        labels = {r["rho_decimal"] for r in rows if r["rho_decimal"] is not None}
        indices = {r["depth_index"] for r in rows if r["depth_index"] is not None}
        finite = all(math.isfinite(v) for r in rows for v in r["metrics"].values()
                     if isinstance(v, (int, float)) and not isinstance(v, bool))
        stores = sum(1 for e in decoy_run.events if e.get("kind") == "store")
        rehearsal = {
            "completed": True, "rows": len(rows),
            "rho_decimal_labels": sorted(labels), "depth_indices": sorted(indices),
            "stores": stores, "all_metrics_finite": finite,
            "rows_digest": "sha256:" + _sha(json.dumps(rows, sort_keys=True, allow_nan=False).encode()),
            "numbers_are_meaningless": True,
        }
        rehearsal_ok = (len(rows) == 384 and labels == {d for d, _ in DECOY_GRID}
                        and indices == {0, 1, 2, 3, 4} and stores == 320 and finite)
    except Exception as error:
        rehearsal = {"completed": False, "error": f"{type(error).__name__}: {error}"}
        rehearsal_ok = False
    c3 = bool(control["failed"] and rehearsal_ok)

    evidence = {"references_verified": refs["verified"],
                "substitution_target_exactly_once": exactly_once,
                "C1_substitution_exact": c1, "C2_equivalence_on_sealed_grid": c2,
                "C3_decoy_rehearsal": c3, "C4_criterion_receipt": c4}
    verdict = licence_verdict(evidence)

    def brief(e):
        c = e["comparison"]
        return {"rows": [e["committed_rows"], e["fork_rows"]],
                "scientific_leaves_compared": c["scientific_leaves_compared"],
                "worst_absolute_difference": c["worst_absolute_difference"],
                "discrete_mismatches": len(c["discrete_mismatches"]),
                "identity_mismatches": c["identity_mismatches"],
                "only_in_either": len(c["only_in_produced"]) + len(c["only_in_reproduced"])}

    result = {
        "schema": "hypercomplexbrain.r6n-licence.v1", "round": "QSigma-R6N", "verdict": verdict,
        "preregistration": MANIFEST.relative_to(ROOT).as_posix(),
        "held_out_depths_evaluated": [],
        "evidence": evidence, "references": refs, "substitution": substitution,
        "criterion_receipt": {"clean": receipt["clean"], "declaration_valid": receipt["declaration_valid"],
                              "skipped": receipt["skipped"],
                              "disjointness_samples": receipt["disjointness"]["samples"],
                              "knobs": receipt["parameters"]["knobs"]},
        "C2": {"vs_committed_rows": brief(vs_committed), "vs_sealed_fresh_bitwise": brief(vs_fresh)},
        "C3": {"control_unrepaired_fork_on_decoy": control, "rehearsal": rehearsal,
               "decoy_grid": [d for d, _ in DECOY_GRID]},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "seconds": round(time.time() - started, 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, **evidence, "seconds": result["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
