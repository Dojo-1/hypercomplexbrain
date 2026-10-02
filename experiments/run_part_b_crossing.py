"""QSigma-R6k-W1 Part B: the held-out crossing, run once.

    PYTHONPATH=src python3 experiments/run_part_b_crossing.py run
    PYTHONPATH=src python3 experiments/run_part_b_crossing.py envelope \\
        --source-commit <C_exec> --raw-commit <C_raw>

Governed by manifests/qsigma_r6k_w1_partb_input_freeze.json, anchored at the
C_pre tag refs/tags/qsigma-r6k-w1-partb-prereg-v1. The outcome is decided by
the frozen function aionq.part_b_outcome.part_b_outcome and by nothing here.

Order is the whole design:
  1. the full preflight must pass 12/12 -- which includes "no output exists";
  2. the extraction is proved on SEALED data first: applied to R6l's committed
     rows at rho=0.1 it must reproduce the frozen baseline delta_p and delta_i
     exactly, or the run refuses before touching a held-out depth;
  3. the receivers are rebuilt at the five held-out depths through the fork
     R6M licensed, and the fork's held-out source inputs are compared with the
     frozen digests;
  4. 160 map rows are extracted, validated, and handed to the frozen function;
  5. the five raw outputs are written, and nothing is repaired afterwards.
"""

from __future__ import annotations

import argparse
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

from aionq import part_b_preflight as P  # noqa: E402
from aionq.common_receiver_parametric import SEALED_SOURCES  # noqa: E402
from aionq.common_receiver_substituted import (  # noqa: E402
    build_substituted_fork, substituted_source)
from aionq.part_b_outcome import (  # noqa: E402
    information_margin, part_b_outcome, passes, probability_margin)

OUT = ROOT / "artifacts" / "r6k_w1_part_b"
#: Attempt 2 builds receivers through the R6N substituted fork. R6M's fork failed
#: closed here in attempt 1 on its one-decimal store key; R6N repaired that by
#: one declared span and licensed the result bitwise at the sealed grid.
LICENCE = ROOT / "artifacts" / "r6n_substituted_fork" / "licence.json"
UPSTREAM_LICENCE = ROOT / "artifacts" / "r6m_parametric_equivalence" / "equivalence.json"
ATTEMPT = 2
PREVIOUS_ATTEMPTS = ["manifests/qsigma_r6k_w1_partb_execution_attempt_1.json"]
R6L_RESULT = ROOT / "artifacts" / "r6l_common_receiver" / "common_receiver_reservoir.json"
TASK = "projective_fixed_depth"
RUN_COMMAND = "PYTHONPATH=src python3 experiments/run_part_b_crossing.py run"
#: A margin this close to zero could change sign under a last-ulp libm
#: difference between the freezing platform and this one. Reported, never used.
PLATFORM_SENSITIVITY = 1e-12


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _render(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"



def extract_map_rows(retrieval_rows, depth_coords, noise_coords, digest) -> list:
    """The 160 frozen-order map rows from one protocol run's retrieval rows.

    Pinned by the freeze's baseline cells, not chosen here: both are
    projective_fixed_depth with 16 classes on a receiver SHARED by R6 and R6i,
    i.e. the pooled map-blind PGM. Refuses if any cell is missing, duplicated,
    or if a depth's receiver is not the same object for both maps.
    """
    index = {}
    for row in retrieval_rows:
        if row["task"] != TASK:
            continue
        key = (row["map"], row["depth_index"], row["eta_index"], row["epsilon_index"])
        if key in index:
            raise RuntimeError(f"duplicate {TASK} cell {key}")
        index[key] = row

    out = []
    for map_name in P.MAPS:
        for depth_index, rho_decimal, _ in depth_coords:
            for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in noise_coords:
                row = index[(map_name, depth_index, eta_index, epsilon_index)]
                if (row["rho_decimal"], row["eta_decimal"], row["epsilon_decimal"]) != (
                        rho_decimal, eta_decimal, epsilon_decimal):
                    raise RuntimeError(f"cell labels disagree at {map_name} {depth_index}")
                if row["classes"] != 16:
                    raise RuntimeError("the pooled projective receiver must have 16 classes")
                out.append({
                    "schema_version": P.MAP_ROW_SCHEMA,
                    "effective_protocol_digest": digest,
                    "map": map_name,
                    "depth_index": depth_index,
                    "rho_decimal": rho_decimal,
                    "eta_index": eta_index,
                    "eta_decimal": eta_decimal,
                    "epsilon_index": epsilon_index,
                    "epsilon_decimal": epsilon_decimal,
                    "correct_probability": float(row["metrics"]["correct_probability"]),
                    "mutual_information_bits": float(row["metrics"]["mutual_information_bits"]),
                })
    for depth_index, _, _ in depth_coords:
        receivers = {index[(m, depth_index, 0, 0)]["protocol_receiver_id"] for m in P.MAPS}
        if len(receivers) != 1:
            raise RuntimeError(f"depth {depth_index}: receiver is not map-blind")
    return out


def prove_extraction_on_sealed_data() -> dict:
    """Step 2. The same extraction, on R6l's committed rows, must hit the frozen
    baseline exactly. A wrong task, map, receiver or field would miss it."""
    rows = json.loads(R6L_RESULT.read_text(encoding="utf-8"))["retrieval_rows"]
    sealed_depths = ((0, "0.1", 0.1),)
    clean = tuple(c for c in P.NOISE_COORDS if c[0] == 0 and c[3] == 0)
    got = extract_map_rows(rows, sealed_depths, clean, P.EFFECTIVE_PROTOCOL_DIGEST)
    r6, r6i = got
    delta_p = r6i["correct_probability"] - r6["correct_probability"]
    delta_i = r6i["mutual_information_bits"] - r6["mutual_information_bits"]
    ok = delta_p == P.BASELINE["delta_p"] and delta_i == P.BASELINE["delta_i"]
    if not ok:
        raise SystemExit(f"extraction does not reproduce the frozen baseline: {delta_p!r} {delta_i!r}")
    return {"delta_p": delta_p, "delta_i": delta_i, "reproduces_frozen_baseline_bitwise": ok}


def run() -> int:
    started = time.time()
    preflight = P.validate_repository_preflight(ROOT)                       # step 1
    if not all(preflight.values()):
        raise SystemExit(f"preflight did not pass: {preflight}")
    c_pre = subprocess.run(["git", "rev-parse", P.PREREG_TAG_REF], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()
    runner_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True, check=True).stdout.strip()

    baseline_proof = prove_extraction_on_sealed_data()                      # step 2

    grid = tuple((decimal, value) for _, decimal, value in P.HELD_OUT_DEPTH_COORDS)
    fork = build_substituted_fork(grid, licence=LICENCE)                     # step 3
    # Attempt 1's lesson, made a gate: exercise the STORE path, with a reservoir,
    # before anything is computed. reservoir=None skips it, which is how
    # attempt 1's pre-run check passed while the run could not. Metric-free.
    _probe = fork.common_receiver
    fork.equal_resource.build_map_tasks("R6", _probe._ProtocolReservoir(
        _probe.plan_protocol(P.EFFECTIVE_PROTOCOL_DIGEST), _probe.HashChainedEventLedger()))
    fork = build_substituted_fork(grid, licence=LICENCE)                     # fresh, unprobed
    rebuilt = P.rebuild_source_input_digests()
    _, diagnostics = fork.equal_resource.build_map_tasks("R6")
    source_inputs = {
        "coordinate_payload": {"frozen": P.SOURCE_INPUT_DIGESTS["coordinate_payload"],
                               "fork": diagnostics["source_coordinate_digest"]},
        "perturbed_coordinate_payload": {"frozen": P.SOURCE_INPUT_DIGESTS["perturbed_coordinate_payload"],
                                         "fork": diagnostics["perturbed_coordinate_digest"]},
        "source_matrix_payload": {"frozen_other_platform": P.SOURCE_INPUT_DIGESTS["source_matrix_payload"],
                                  "frozen_construction_this_platform": rebuilt["source_matrix_payload"],
                                  "fork": diagnostics["source_matrix_digest"],
                                  "status": "computed, compared and REPORTED, never used to refuse -- "
                                            "a digest of libm's last bit, per the preflight's portable gate"},
    }
    for name in ("coordinate_payload", "perturbed_coordinate_payload"):
        if source_inputs[name]["frozen"] != source_inputs[name]["fork"]:
            raise SystemExit(f"fork's held-out {name} is not the frozen input")
    if diagnostics["source_matrix_digest"] != rebuilt["source_matrix_payload"]:
        raise SystemExit("fork's source matrices are not the frozen construction on this platform")

    t0 = time.time()
    crr = fork.common_receiver
    plan = crr.plan_protocol(P.EFFECTIVE_PROTOCOL_DIGEST)
    protocol_run = crr.execute_protocol(plan)
    compute_seconds = time.time() - t0
    report = protocol_run.report

    map_rows = extract_map_rows(report["retrieval_rows"], P.HELD_OUT_DEPTH_COORDS,
                                P.NOISE_COORDS, P.EFFECTIVE_PROTOCOL_DIGEST)   # step 4
    P.validate_map_rows(map_rows)
    cells = P.pair_map_rows(map_rows)
    outcome = part_b_outcome(map_rows)

    margins = []
    for cell in cells:
        m_p, m_i = probability_margin(cell["delta_p"]), information_margin(cell["delta_i"])
        margins.append({"rho_decimal": cell["rho_decimal"], "eta_decimal": cell["eta_decimal"],
                        "epsilon_decimal": cell["epsilon_decimal"],
                        "probability_margin": m_p, "information_margin": m_i,
                        "probability_passes": passes(m_p), "information_passes": passes(m_i)})
    smallest = min(min(abs(m["probability_margin"]), abs(m["information_margin"])) for m in margins)
    sensitive = [m for m in margins
                 if min(abs(m["probability_margin"]), abs(m["information_margin"])) < PLATFORM_SENSITIVITY]

    projective = [s for s in report["receiver_summaries"] if s["task"] == TASK]
    if sorted(s["rho_decimal"] for s in projective) != sorted(d for d, _ in grid):
        raise SystemExit("a projective receiver was not rebuilt at every held-out depth")

    # step 5. EVERY payload is rendered in memory before ANY file is written: the
    # preflight refuses to run while any output exists, so a crash half way through
    # writing would leave a surface that blocks every rerun for good.
    staged = {}
    staged["map_rows.json"] = _render(map_rows)
    staged["crossing.json"] = _render({
        "schema": "hypercomplexbrain.part-b-crossing.v1",
        "round": "QSigma-R6k-W1", "part": "B",
        "outcome": outcome,
        "decided_by": "aionq.part_b_outcome.part_b_outcome(map_rows), sealed by digest in the input freeze",
        "differential_cells": cells,
        "margins": margins,
        "platform_sensitivity": {
            "threshold": PLATFORM_SENSITIVITY,
            "smallest_absolute_margin": smallest,
            "cells_within_threshold": sensitive,
            "reading": ("the source matrices were frozen on another platform and differ here in the "
                        "last ulp; a margin within this threshold could change sign between them"),
        },
        "effective_protocol_digest": P.EFFECTIVE_PROTOCOL_DIGEST,
        "c_pre": c_pre, "runner_commit": runner_commit,
    })
    staged["receiver_resource_receipt.json"] = _render({
        "schema": "hypercomplexbrain.part-b-receiver-receipt.v1",
        "task": TASK, "construction": "one map-blind pooled PGM rebuilt independently at each held-out depth",
        "rebuilt_at": [s["rho_decimal"] for s in projective],
        "original_depth_receivers_reused": False,
        "receivers": projective,
    })
    staged["events.jsonl"] = "".join(
        json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        for event in protocol_run.events)
    staged["execution_receipt.json"] = _render({
        "schema": "hypercomplexbrain.part-b-execution-receipt.v1",
        "command": RUN_COMMAND,
        "attempt": ATTEMPT,
        "previous_attempts": PREVIOUS_ATTEMPTS,
        "preflight": preflight,
        "c_pre": c_pre, "prereg_tag": P.PREREG_TAG_REF, "runner_commit": runner_commit,
        "extraction_proved_on_sealed_baseline": baseline_proof,
        "licence": {"path": LICENCE.relative_to(ROOT).as_posix(), "digest": _sha(LICENCE),
                    "verdict": json.loads(LICENCE.read_text(encoding="utf-8"))["verdict"]},
        "upstream_licence": {"path": UPSTREAM_LICENCE.relative_to(ROOT).as_posix(),
                             "digest": _sha(UPSTREAM_LICENCE),
                             "verdict": json.loads(UPSTREAM_LICENCE.read_text(encoding="utf-8"))["verdict"]},
        "substitution": {k: v for k, v in substituted_source()[1].items()},
        "fork": {"grid": [d for d, _ in grid],
                 "sealed_sources": {n: s for n, (_, s) in SEALED_SOURCES.items()}},
        "source_inputs": source_inputs,
        "protocol_digest_label": {
            "value": P.EFFECTIVE_PROTOCOL_DIGEST,
            "why": ("plan_protocol only format-checks its digest and hashes it into cell ids; at R6l's "
                    "sealed grid the metrics were shown bitwise identical under R6l's and Part B's "
                    "digests. Part B's is used because R6l's protocol never covered these depths."),
        },
        "retrieval_rows_computed": len(report["retrieval_rows"]),
        "map_rows": len(map_rows), "differential_cells": len(cells),
        "event_count": len(protocol_run.events), "ledger_root": report["ledger_root"],
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
        "seconds": {"protocol": round(compute_seconds, 1), "total": round(time.time() - started, 1)},
    })
    if sorted(staged) != sorted(Path(p).name for p in P.RAW_OUTPUT_PATHS):
        raise SystemExit(f"staged outputs {sorted(staged)} are not the frozen raw surface")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in staged.items():
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"outcome": outcome.get("outcome"), "reason": outcome.get("reason"),
                      "smallest_absolute_margin": smallest,
                      "platform_sensitive_cells": len(sensitive)}, indent=1))
    return 0


def publish_envelope(env, path: Path, verify_fn):
    """Verify, and write ONLY if verification passed.

    The first version verified, then saved unconditionally and returned 0, so a
    rejected envelope was published as if it had passed. Found by external
    review. A failure now writes nothing and exits non-zero.
    """
    from aionq.evidence import save_envelope

    result = verify_fn(env)
    if getattr(result, "ok", False) is not True:
        raise SystemExit(f"envelope verification FAILED; nothing written:\n{result}")
    save_envelope(env, path)
    return result


def envelope(source_commit: str, raw_commit: str) -> int:
    from aionq.evidence import EvidenceEnvelope, environment_digest, verify

    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout

    if git("rev-parse", f"{raw_commit}^").strip() != source_commit:
        raise SystemExit("C_raw must be the direct child of C_exec")
    raw = {}
    for path in P.RAW_OUTPUT_PATHS:
        blob = subprocess.run(["git", "show", f"{raw_commit}:{path}"], cwd=ROOT,
                              capture_output=True, check=True).stdout
        digest = "sha256:" + hashlib.sha256(blob).hexdigest()
        if digest != _sha(ROOT / path):
            raise SystemExit(f"{path} differs from its bytes at C_raw")
        raw[path] = digest
    crossing = json.loads((OUT / "crossing.json").read_text(encoding="utf-8"))
    receipt = json.loads((OUT / "execution_receipt.json").read_text(encoding="utf-8"))
    env = EvidenceEnvelope(
        claim_id="EXP-R6K-W1-PART-B-CROSSING", evidence_tag="M", command=RUN_COMMAND,
        observed_result={"outcome": crossing["outcome"]["outcome"],
                         "reason": crossing["outcome"].get("reason"),
                         "smallest_absolute_margin": crossing["platform_sensitivity"]["smallest_absolute_margin"],
                         "ledger_root": receipt["ledger_root"]},
        schema_version="hypercomplexbrain.evidence.v2",
        artifact_commit_sha=raw_commit, commit_sha=raw_commit,
        source_commit_sha=source_commit, preregistration_commit_sha=receipt["c_pre"],
        working_directory=".", platform=platform.platform(), environment=environment_digest(),
        raw_artifacts=raw, producer="experiments/run_part_b_crossing.py", verifier="",
        # timings and platform strings: a faithful recomputation elsewhere differs
        environment_dependent=["artifacts/r6k_w1_part_b/execution_receipt.json"],
        uncertainty={"kind": "deterministic one-shot producer run", "confidence_interval": None,
                     "independent_replication": False},
        typed_remainders=[
            {"kind": "platform_remainder", "statement": "margins computed on this platform from source matrices that differ in the last ulp from the freezing platform's; see crossing.json platform_sensitivity"},
            {"kind": "extrapolation_remainder", "statement": "the fork is licensed by equivalence at R6l's five depths only; at held-out depths the sealed implementation is undefined"},
            {"kind": "independence_remainder", "statement": "producer and verifier are the same development line; independent=false until a separate recomputation passes"},
            {"kind": "substitution_remainder", "statement": "receivers were built by the R6N fork, which executes the sealed bytes with one declared span changed (the store key's depth format); licensed bitwise at the sealed grid"},
            {"kind": "attempt_remainder", "statement": "this is attempt 2; attempt 1 failed closed before any metric (manifests/qsigma_r6k_w1_partb_execution_attempt_1.json)"},
        ],
    )
    result = publish_envelope(env, OUT / "crossing.envelope.json",
                              lambda candidate: verify(candidate, repo_root=ROOT))
    print(json.dumps({"envelope": "written", "verify": getattr(result, "status", str(result))}, indent=1))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="phase", required=True)
    sub.add_parser("run")
    env = sub.add_parser("envelope")
    env.add_argument("--source-commit", required=True)
    env.add_argument("--raw-commit", required=True)
    args = parser.parse_args(argv)
    return run() if args.phase == "run" else envelope(args.source_commit, args.raw_commit)


if __name__ == "__main__":
    raise SystemExit(main())
