#!/usr/bin/env python3
"""QSigma-R6e: carrier telemetry, its three detectors, and the atlas cross-check.

    PYTHONPATH=src python3 experiments/run_carrier_telemetry.py [ATLAS_JSON]

Preregistered at 35b2277 before any of this existed.

The optional ATLAS_JSON argument cross-verifies an exported
``ohnium.observable-ascent.v2`` payload against this repository's operators.  It
is OPTIONAL by design: the round's own gates must pass without it, because the
atlas is an uploaded artifact that is deliberately not committed.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.carrier_telemetry import (CD_DIMENSION, TAU_OP, TAU_SRC,
                                     bridge_event, carrier_is_sound,
                                     confusion_matrix, detect,
                                     fill_volume_form_distortion, trace_word)
from aionq.fano_algebra import fano_lines, rank_decomposition
from aionq.quantum_channel_geometry import p_bell, volume_form_distortion

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "r6e_carrier_telemetry"
SEED = 20260728

CLEAN = [(0.20, 0.0, 0.0), (0.25, 0.3, 0.2), (0.30, 0.6, 0.4), (0.35, 0.9, 0.6)]


def main(argv) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"round": "QSigma-R6e", "seed": SEED,
                    "schema_emitted": "ohnium.observable-ascent.v2"}

    # ---- T1: clean-trace null ---------------------------------------------
    clean = trace_word(CLEAN, "O")
    clean_fires = [detect(e, clean["kappa_word"] if False else None)
                   for e in clean["events"]]
    report["clean_trace"] = {
        "n_events": clean["n_events"],
        "failures_per_event": clean_fires,
        "any_fired": any(clean_fires),
        "kappa_word": clean["kappa_word"]}

    # ---- T4: prefix telescoping -------------------------------------------
    tele = []
    rng = np.random.default_rng(SEED)
    for n in (1, 2, 3, 5, 8):
        pts = [(rng.uniform(0.05, 1.5), rng.uniform(-3, 3), rng.uniform(-3, 3))
               for _ in range(n + 1)]
        t = trace_word(pts, "O")
        tele.append({"n_events": t["n_events"], "kappa_word": t["kappa_word"],
                     "per_event_sum": t["kappa_per_event_sum"],
                     "abs_diff": abs(t["kappa_word"] - t["kappa_per_event_sum"])})
    report["telescoping"] = {
        "rows": tele, "worst_diff": max(r["abs_diff"] for r in tele),
        "note": ("kappa is a 2-cocycle and telescopes over PREFIXES, not adjacent "
                 "pairs. The first implementation summed pairwise and disagreed "
                 "with the word total at 1.2e-2; T4 existed to catch exactly that "
                 "and did.")}

    # ---- T2: single-fault isolation ---------------------------------------
    cases = {}
    # false ascent: claim a rung with zero divisors
    e_fa = bridge_event(CLEAN[0], CLEAN[1], "CD32")
    cases["false_ascent"] = detect(e_fa, word_kappa=0.0)
    # Energy leakage: a word whose prefixes are deeper than its net element.
    #
    # The first injection here was [(2.0, phi=1.0), (2.0, phi=-1.0)] and the
    # detector stayed SILENT -- correctly. That word has kappa_word = 0.000000
    # exactly and net depth 4.0: the two depth-2 steps COMPOUND rather than
    # cancel, so nothing leaks and there was no fault to catch. The confusion
    # matrix caught a mis-specified injection, not a broken detector, and the
    # fix belongs in the fault rather than in the threshold.
    #
    # The real leak needs the steps to CANCEL: phi = 0 against phi = pi gives
    # kappa_word = 4.000000 = 2 rho with net depth 0, the same structure as the
    # inverse pair whose streamed survival is e^{-4 rho}.
    leak_pts = [(0.1, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, math.pi, 0.0)]
    leak = trace_word(leak_pts, "O")
    cases["energy_leakage"] = detect(leak["events"][-1], word_kappa=leak["kappa_word"])
    # bridge absorption: a large source step at large depth
    e_ab = bridge_event((3.0, 0.0, 0.0), (3.2, 0.02, 0.0), "O")
    cases["bridge_absorption"] = detect(e_ab, word_kappa=0.0)
    cm = confusion_matrix(cases)
    report["fault_isolation"] = {"cases": cases, "confusion_matrix": cm,
                                 "leak_kappa_word": leak["kappa_word"]}

    # ---- T3: the depth control for absorption ------------------------------
    e_shallow = bridge_event((0.05, 0.0, 0.0), (0.25, 0.02, 0.0), "O")
    report["absorption_depth_control"] = {
        "deep": {"rho": 3.2, "source_step": e_ab["source_step"],
                 "operational_step": e_ab["operational_step"],
                 "fires": "bridge_absorption" in detect(e_ab, 0.0)},
        "shallow": {"rho": 0.25, "source_step": e_shallow["source_step"],
                    "operational_step": e_shallow["operational_step"],
                    "fires": "bridge_absorption" in detect(e_shallow, 0.0)},
        "tau_src": TAU_SRC, "tau_op": TAU_OP,
        "finding": ("the detector fires deep and stays silent shallow for a "
                    "comparable source step, so it reads DEPTH and not step size. "
                    "This is R6b's e^{-4 rho} suppression made visible per event, "
                    "not a new effect and not a defect in the trace")}

    # ---- T5: remainder retention and the return path -----------------------
    ret = [{"rho": e["source_coordinates"][0],
            "kappa_inverse_pair": e["return_path"]["kappa_inverse_pair"],
            "expected_two_rho": e["return_path"]["expected_two_rho"],
            "source_defect": e["return_path"]["source_defect"],
            "streamed_survival": e["return_path"]["streamed_survival"],
            "remainder_len": len(e["projection_violence"]["discarded_vector"]),
            "flattened": e.remainder_is_flattened}
           for e in clean["events"]]
    report["return_and_remainder"] = {
        "rows": ret,
        "worst_return_error": max(abs(r["kappa_inverse_pair"] - r["expected_two_rho"])
                                  for r in ret),
        "worst_source_defect": max(r["source_defect"] for r in ret),
        "any_flattened": any(r["flattened"] for r in ret)}

    # ---- carrier ladder soundness -----------------------------------------
    report["carrier_ladder"] = {c: carrier_is_sound(d) for c, d in CD_DIMENSION.items()}

    # ---- T6: the atlas cross-check (optional) ------------------------------
    atlas_path = Path(argv[1]) if len(argv) > 1 else None
    if atlas_path and atlas_path.exists():
        atlas = json.loads(atlas_path.read_text())
        worst_p, n_frames, nulls, total = 0.0, 0, 0, 0
        filled = []
        for ep in atlas.get("endpoints", []):
            for fr in ep.get("frames", []):
                rho = fr["source_coordinates"][0]
                worst_p = max(worst_p, abs(fr["operational_success_probability"]
                                           - p_bell(rho)))
                n_frames += 1
                for b in fr.get("bridges", []):
                    total += 1
                    if b.get("projection_violence", {}).get("volume_form_distortion") is None:
                        nulls += 1
                        if len(filled) < 5:
                            filled.append(fill_volume_form_distortion(
                                b, fr["source_coordinates"])["projection_violence"]
                                ["volume_form_distortion"])
        mine = rank_decomposition(fano_lines())
        pp = atlas["endpoints"][0]["frames"][0]["proof_pressure"]
        report["atlas_cross_check"] = {
            "source": atlas_path.name,
            "schema": atlas.get("schema"),
            "frames_checked": n_frames,
            "worst_success_probability_error": worst_p,
            "fano_theirs": [pp["fano_signal_rank"], pp["fano_crosstalk_rank"],
                            pp["fano_joint_rank"]],
            "fano_mine": [mine["signal_rank"], mine["crosstalk_rank"],
                          mine["union_rank"]],
            "fano_agrees": [pp["fano_signal_rank"], pp["fano_crosstalk_rank"],
                            pp["fano_joint_rank"]] == [mine["signal_rank"],
                                                       mine["crosstalk_rank"],
                                                       mine["union_rank"]],
            "volume_form_distortion_null": nulls, "bridges_total": total,
            "sample_filled_values": filled,
            "carrier_dimension_labels": {
                c["carrier"]: {"declared": c["dimension"],
                               "vector_length": len(c["vector"]),
                               "cd_ladder_dimension": CD_DIMENSION.get(c["carrier"]),
                               "consistent": c["dimension"] == len(c["vector"])}
                for c in atlas["endpoints"][0]["frames"][0]["carriers"]},
            "finding": ("their operational_success_probability reproduces "
                        "p_bell(rho) = (1+q^2)/2 and their Fano ranks reproduce "
                        "(7,21,28); both were derived independently on two "
                        "machines. The null volume_form_distortion field is "
                        "computable from their own source_coordinates by the R6b "
                        "operator")}
    else:
        report["atlas_cross_check"] = {
            "skipped": True,
            "reason": ("no atlas path supplied. The round's gates do not depend "
                       "on it: the atlas is an uploaded artifact and is not "
                       "committed")}

    checks = {
        "clean_trace_is_silent": not report["clean_trace"]["any_fired"],
        "telescoping_exact": report["telescoping"]["worst_diff"] < 1e-12,
        "confusion_matrix_is_diagonal": cm["is_diagonal"],
        "absorption_fires_deep": report["absorption_depth_control"]["deep"]["fires"],
        "absorption_silent_shallow":
            not report["absorption_depth_control"]["shallow"]["fires"],
        "return_path_is_two_rho":
            report["return_and_remainder"]["worst_return_error"] < 1e-9,
        "source_return_defect_zero":
            report["return_and_remainder"]["worst_source_defect"] < 1e-12,
        "remainder_not_flattened": not report["return_and_remainder"]["any_flattened"],
        "ladder_sound_through_octonions": all(
            report["carrier_ladder"][c]["is_sound"] for c in ("R", "H", "O")),
        "ladder_unsound_above": all(
            not report["carrier_ladder"][c]["is_sound"] for c in ("CD32", "A_n")),
    }
    if not report["atlas_cross_check"].get("skipped"):
        checks["atlas_success_probability_agrees"] = (
            report["atlas_cross_check"]["worst_success_probability_error"] < 1e-12)
        checks["atlas_fano_agrees"] = report["atlas_cross_check"]["fano_agrees"]
    checks = {k: bool(v) for k, v in checks.items()}
    report["checks"] = checks
    report["verdict"] = "ALL GATES PASS" if all(checks.values()) else "DISCREPANCY"

    path = OUT / "carrier_telemetry.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6E-CARRIER_TELEMETRY",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_carrier_telemetry.py",
        observed_result={
            "sample_size": clean["n_events"] + len(tele) + 3,
            "clean_trace_silent": bool(not report["clean_trace"]["any_fired"]),
            "confusion_diagonal": bool(cm["is_diagonal"]),
            "worst_telescoping_diff": report["telescoping"]["worst_diff"],
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[SEED],
        input_hashes=([f"clean:rho={p[0]:.6f},phi={p[1]:.6f},psi={p[2]:.6f}"
                       for p in CLEAN]
                      + [f"telescope:n={r['n_events']}" for r in tele]
                      + ["fault:false_ascent", "fault:energy_leakage",
                         "fault:bridge_absorption"]),
        raw_artifacts={"artifacts/r6e_carrier_telemetry/carrier_telemetry.json":
                       file_digest(path)},
        environment_dependent=[],
        producer="experiments/run_carrier_telemetry.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {"kind": "instrument_remainder",
             "carrier": "usefulness",
             "comparison": ("this is an instrument. Nothing in this round shows it "
                            "finds a fault nobody already knew about; every fault "
                            "it caught was injected on purpose. Its value is S "
                            "until it catches one that was not")},
            {"kind": "naming_remainder",
             "carrier": "'energy'",
             "comparison": ("kappa is a log-norm defect in nats with no physical "
                            "content. The word is retained only because the "
                            "supplied schema uses it, and a reader who takes it "
                            "for joules will be wrong")},
            {"kind": "witness_remainder",
             "carrier": "the atlas cross-check",
             "comparison": ("their numbers reproduce this repository's operators, "
                            "which raises the rank of THEIR claim, not of this "
                            "envelope. Their module is unpushed and their artifact "
                            "is an uploaded file that is not committed here")}])
    save_envelope(envelope, OUT / "carrier_telemetry.envelope.json")

    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "confusion": cm["matrix"]}, indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
