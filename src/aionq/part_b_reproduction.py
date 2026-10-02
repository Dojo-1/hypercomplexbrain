"""QSigma-R6O: recompute Part B on another platform and compare, in two layers.

Part B was computed once, on one Linux container. tests/test_part_b_result.py
re-applies the frozen outcome function to the COMMITTED map rows, which shows
the function is portable and says nothing about whether the COMPUTATION
reproduces. This module recomputes all 160 map rows through the licensed R6N
fork and judges two things separately:

    decision   the outcome dictionary, and all 80 cells' probability and
               information pass flags -- exactly
    numbers    every map row under aionq.semantic_reproduction.compare_results
               at 1e-10, R6k-W1's committed tolerance, never widened

because a platform's linear algebra can move a number without moving a flag,
and a single verdict would hide which had happened:

    REPRODUCED      decision identical and numbers within tolerance
    OUTCOME_ONLY    decision identical, numbers not
    NOT_REPRODUCED  the decision differs
    INVALID         a reference fails byte verification, the licence is
                    refused, or the computation raises

Nothing is written under artifacts/r6k_w1_part_b/. The extraction is the one
that ran: its source is compared with the runner blob at C_exec, so a later
edit to the runner cannot silently change what is being reproduced.
"""

from __future__ import annotations

import ast
import importlib.util
import itertools
import json
import platform
import subprocess
from pathlib import Path

from . import part_b_preflight as P
from .common_receiver_substituted import build_substituted_fork, verify_r6n_licence
from .part_b_outcome import information_margin, part_b_outcome, passes, probability_margin

__all__ = ["C_RAW", "C_EXEC", "TOLERANCE", "VERDICTS", "reproduce",
           "reproduction_verdict", "exercise_the_frozen_rule"]

C_RAW = "de60129f7520672f6391ddd69d9f68bb3082a7b0"
C_EXEC = "e96fa243d3044aa2ef4c99377443c5524d150842"
TOLERANCE = 1e-10
VERDICTS = ("REPRODUCED", "OUTCOME_ONLY", "NOT_REPRODUCED", "INVALID")

_OUT = "artifacts/r6k_w1_part_b"
_RUNNER = "experiments/run_part_b_crossing.py"
_LICENCE = "artifacts/r6n_substituted_fork/licence.json"


def _blob(root: Path, commit: str, relative: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                            capture_output=True)
    return result.stdout if result.returncode == 0 else b""


def _function_source(text: str, name: str) -> str | None:
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node)
    return None


def _load_runner(root: Path):
    spec = importlib.util.spec_from_file_location("_r6o_part_b_runner", root / _RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def references(root: Path) -> dict:
    """Every input this comparison leans on, checked by bytes or by evidence."""
    rows_ok = (root / _OUT / "map_rows.json").read_bytes() == _blob(root, C_RAW, f"{_OUT}/map_rows.json")
    crossing_ok = (root / _OUT / "crossing.json").read_bytes() == _blob(root, C_RAW, f"{_OUT}/crossing.json")
    try:
        verify_r6n_licence(root / _LICENCE)
        licence_ok = True
    except PermissionError:
        licence_ok = False
    executed = _function_source(_blob(root, C_EXEC, _RUNNER).decode("utf-8"), "extract_map_rows")
    live = _function_source((root / _RUNNER).read_text(encoding="utf-8"), "extract_map_rows")
    extraction_ok = executed is not None and executed == live
    return {"map_rows_at_c_raw": rows_ok, "crossing_at_c_raw": crossing_ok,
            "r6n_licence_verified": licence_ok, "extraction_is_the_one_that_ran": extraction_ok,
            "verified": rows_ok and crossing_ok and licence_ok and extraction_ok}


def _flags(map_rows) -> list:
    return [(passes(probability_margin(c["delta_p"])), passes(information_margin(c["delta_i"])))
            for c in P.pair_map_rows(map_rows)]


def reproduction_verdict(evidence: dict) -> str:
    if not (evidence.get("references_verified") is True and evidence.get("computed") is True):
        return "INVALID"
    if evidence.get("decision_identical") is not True:
        return "NOT_REPRODUCED"
    if evidence.get("numbers_within_tolerance") is True:
        return "REPRODUCED"
    return "OUTCOME_ONLY"


def reproduce(root) -> dict:
    """Recompute, compare, and return the full report. Writes nothing."""
    import numpy as np

    from .semantic_reproduction import compare_results

    root = Path(root)
    report = {"round": "QSigma-R6O",
              "platform": {"system": platform.system(), "machine": platform.machine(),
                           "platform": platform.platform(), "python": platform.python_version(),
                           "numpy": np.__version__}}
    refs = references(root)
    report["references"] = refs
    evidence = {"references_verified": refs["verified"], "computed": False,
                "decision_identical": False, "numbers_within_tolerance": False}
    if not refs["verified"]:
        report.update(evidence=evidence, verdict=reproduction_verdict(evidence))
        return report

    try:
        grid = tuple((decimal, value) for _, decimal, value in P.HELD_OUT_DEPTH_COORDS)
        fork = build_substituted_fork(grid, licence=root / _LICENCE)
        crr = fork.common_receiver
        run = crr.execute_protocol(crr.plan_protocol(P.EFFECTIVE_PROTOCOL_DIGEST))
        rows = _load_runner(root).extract_map_rows(
            run.report["retrieval_rows"], P.HELD_OUT_DEPTH_COORDS, P.NOISE_COORDS,
            P.EFFECTIVE_PROTOCOL_DIGEST)
        P.validate_map_rows(rows)
        outcome = part_b_outcome(rows)
        evidence["computed"] = True
    except Exception as error:                                   # recorded, never swallowed
        report.update(evidence=evidence, error=f"{type(error).__name__}: {error}",
                      verdict=reproduction_verdict(evidence))
        return report

    committed_rows = json.loads((root / _OUT / "map_rows.json").read_text(encoding="utf-8"))
    committed_outcome = json.loads((root / _OUT / "crossing.json").read_text(encoding="utf-8"))["outcome"]
    flags_here, flags_committed = _flags(rows), _flags(committed_rows)
    evidence["decision_identical"] = (outcome == committed_outcome and flags_here == flags_committed)

    comparison = compare_results({"map_rows": committed_rows}, {"map_rows": rows}, TOLERANCE)
    evidence["numbers_within_tolerance"] = (
        len(rows) == len(committed_rows) == 160
        and not comparison["discrete_mismatches"]
        and comparison["scientific_leaves_compared"] > 0
        and not comparison["scientific_leaves_exceeding_tolerance"]
        and not comparison["non_finite_leaves"]
        and not comparison["only_in_produced"] and not comparison["only_in_reproduced"])

    margins = [abs(m) for c in P.pair_map_rows(rows)
               for m in (probability_margin(c["delta_p"]), information_margin(c["delta_i"]))]
    report.update(
        evidence=evidence,
        verdict=reproduction_verdict(evidence),
        outcome=outcome,
        flags_differing=sum(a != b for a, b in zip(flags_here, flags_committed)),
        numbers={"tolerance": TOLERANCE,
                 "scientific_leaves_compared": comparison["scientific_leaves_compared"],
                 "worst_absolute_difference": comparison["worst_absolute_difference"],
                 "worst_difference_path": comparison["worst_difference_path"],
                 "exceeding_tolerance": len(comparison["scientific_leaves_exceeding_tolerance"]),
                 "discrete_mismatches": len(comparison["discrete_mismatches"])},
        smallest_absolute_margin=min(margins),
    )
    return report


def exercise_the_frozen_rule() -> dict:
    """R2A on R6O's rule before any platform runs it."""
    from .criterion import exercise

    flags = ("references_verified", "computed", "decision_identical", "numbers_within_tolerance")
    base = dict.fromkeys(flags, True)
    ok = lambda e: e["references_verified"] and e["computed"]
    return exercise(
        verdict_fn=reproduction_verdict,
        witnesses={"REPRODUCED": base,
                   "OUTCOME_ONLY": {**base, "numbers_within_tolerance": False},
                   "NOT_REPRODUCED": {**base, "decision_identical": False},
                   "INVALID": {**base, "computed": False}},
        declared_verdicts=VERDICTS,
        predicates={"INVALID": lambda e: not ok(e),
                    "NOT_REPRODUCED": lambda e: ok(e) and not e["decision_identical"],
                    "OUTCOME_ONLY": lambda e: ok(e) and e["decision_identical"] and not e["numbers_within_tolerance"],
                    "REPRODUCED": lambda e: ok(e) and e["decision_identical"] and e["numbers_within_tolerance"]},
        samples=[dict(zip(flags, bits)) for bits in itertools.product((False, True), repeat=len(flags))],
        entrypoint=reproduce, frozen={},
        required_checks=("coverage", "disjointness", "parameters"),
    )
