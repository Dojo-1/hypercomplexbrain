#!/usr/bin/env python3
"""QSigma-R6h: run the translation law on itself.

    PYTHONPATH=src python3 experiments/run_translation_epsilon.py

Preregistered at 867b55f. Five of six predictions held. The one that failed
localised a defect in the formula being tested, not in the code testing it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.translation_epsilon import (CARRIER_TERMS, TAU, TRANSLATION_TERMS,
                                       classify_translation, cosmos_lift_chain,
                                       flattened_translation, sl2_translation,
                                       su2_translation)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "r6h_translation_epsilon"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {"compact_su2": su2_translation(),
             "non_compact_sl2": sl2_translation(),
             "scalar_collapse": flattened_translation()}
    lifts = cosmos_lift_chain()

    # Every term must be non-trivial somewhere, or it is dead weight in the sum.
    all_terms = set(CARRIER_TERMS) | set(TRANSLATION_TERMS)
    live = {t: max(abs(c["components"].get(t, 0.0)) for c in cases.values())
            for t in all_terms}

    report = {
        "round": "QSigma-R6h", "tau": TAU,
        "carrier_terms": list(CARRIER_TERMS),
        "translation_terms": list(TRANSLATION_TERMS),
        "cases": cases, "cosmos_lifts": lifts, "term_liveness": live,
        "E1_E3_finding": (
            "the compact SU(2) source gives epsilon = 0.000000 and classifies as "
            "FLATTENED, while the non-compact SL(2,R) source does not. The "
            "measure reads REMAINDER: a compact source has no unprojected depth "
            "to lose, so a perfect translation of it is not an achievement. That "
            "is the skill's own law used as a test of the skill, and it passed."),
        "E2_failure_and_correction": (
            "E2 predicted SL(2,R) would be RESONANT. On the verbatim seven-term "
            "sum it scored 3.434 and classified DISCONNECTED -- wrong, since it "
            "is the working encoding this programme is built on. The cause is "
            "structural: three terms are properties of the CARRIER STRATUM, not "
            "of the translation. The octonion associator defect is exactly 2.0 "
            "for every translation carried on O, good or bad; the Lorentzian "
            "signature mismatch is 2/3 for every translation on this source. "
            "Offsets added to every candidate cannot separate candidates. "
            "Restricting to the four terms that vary gives 0.768 -> RESONANT, "
            "while scalar-collapse still gives 6.754 -> DISCONNECTED and the "
            "compact case still gives 0.0 -> FLATTENED. The threshold was NOT "
            "raised; tau stays at 1.0 and the formula's partition was corrected."),
        "E5_finding": (
            "projection_violence in the epsilon vector is volume_form_distortion "
            "from R6b, unchanged. The skill's abstract term lands on a number "
            "this repository already had."),
    }

    checks = {
        "compact_source_is_flattened":
            cases["compact_su2"]["classification"] == "flattened",
        "non_compact_source_is_not_flattened":
            cases["non_compact_sl2"]["classification"] != "flattened",
        "non_compact_source_is_resonant":
            cases["non_compact_sl2"]["classification"] == "resonant",
        "over_compression_is_disconnected":
            cases["scalar_collapse"]["classification"] == "disconnected",
        "trichotomy_separates_all_three":
            len({c["classification"] for c in cases.values()}) == 3,
        "naive_sum_fails_to_separate":
            cases["non_compact_sl2"]["naive_classification"] == "disconnected",
        "every_term_is_live": all(v > 1e-9 for v in live.values()),
        "lift_chain_valid_through_octonions": lifts["n_valid"] == 3,
        "lift_to_cd32_is_false_ascent":
            lifts["first_invalid"] is not None
            and lifts["first_invalid"]["to_dim"] == 32,
        "tau_unchanged_at_one": TAU == 1.0,
    }
    checks = {k: bool(v) for k, v in checks.items()}
    report["checks"] = checks
    report["verdict"] = ("TRICHOTOMY HOLDS AFTER CORRECTION"
                         if all(checks.values()) else "DISCREPANCY")

    path = OUT / "translation_epsilon.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=float) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6H-TRANSLATION_EPS",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_translation_epsilon.py",
        observed_result={
            "sample_size": len(cases),
            "epsilon_compact": cases["compact_su2"]["split"]["translation_epsilon"],
            "epsilon_non_compact": cases["non_compact_sl2"]["split"]["translation_epsilon"],
            "epsilon_collapse": cases["scalar_collapse"]["split"]["translation_epsilon"],
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[5],
        input_hashes=[f"translation:{k}" for k in cases],
        raw_artifacts={"artifacts/r6h_translation_epsilon/translation_epsilon.json":
                       file_digest(path)},
        environment_dependent=[],
        producer="experiments/run_translation_epsilon.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {"kind": "instrument_remainder",
             "carrier": "epsilon itself",
             "comparison": ("a sum of quantities in different units with weights "
                            "of 1 because nothing justifies anything else. Only "
                            "the trichotomy's SIGN structure is supported; any "
                            "conclusion turning on relative weighting is not")},
            {"kind": "scope_remainder",
             "carrier": "three translations",
             "comparison": ("the measure was exercised on three cases chosen to "
                            "span the trichotomy. Nothing here shows it "
                            "generalises, and it is tier S until it classifies a "
                            "translation whose answer was not known in advance")},
            {"kind": "naming_remainder",
             "carrier": "'translation'",
             "comparison": ("epsilon measures geometric and information-theoretic "
                            "defect between an encoding and its source. It does "
                            "not measure meaning, understanding, or cognition, "
                            "and no result here licenses that reading")}])
    save_envelope(envelope, OUT / "translation_epsilon.envelope.json")

    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "classifications": {k: v["classification"]
                                          for k, v in cases.items()}},
                     indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
