#!/usr/bin/env python3
"""Adjudicate one demotion in the external peer review of "The Sheaf of Becoming".

The review demoted Theorem 3 -- ``delta = w1 w2 w3`` for a Dixmier-Douady class on
T^3 -- on the stated ground that "the cup product c1 u c1 u c1 in H^6(T^3) = 0
(vanishes)".

Three checks, all exact integer arithmetic, all with the answer forced by the
algebra before the code runs.  This is proof-checking, not measurement, so there
is nothing here a preregistration could protect against.

    A.  H^6(T^3; Z) really is 0, and the reason is dimension, not the windings.
    B.  H^3(T^3; Z) is Z, and the triple cup product of the three DEGREE-1
        winding classes pairs with the fundamental class to give exactly w1w2w3.
    C.  A degree-6 COCHAIN built from degree-2 cochains is generally nonzero even
        though its class is zero -- so "vanishes" is doing two jobs in one word.

Conclusion the checks support: the demotion is computed in the wrong degree.
Whether Theorem 3 holds for the construction the review actually has in hand is a
separate question that neither this script nor the review's stated argument
settles.

    PYTHONPATH=src python3 experiments/run_dd_class_degree_audit.py
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.group_cohomology import (betti_rank, cup,
                                    degree_six_is_zero_by_dimension,
                                    fundamental_pairing, is_cocycle,
                                    triple_winding_class, winding_cochain)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "dd_class_audit"
SEED = 20260728

WINDINGS = [(1, 1, 1), (1, 1, 0), (2, 3, 4), (3, -2, 5), (-1, -1, -1),
            (0, 7, 9), (7, 0, 0), (6, 6, 6), (12, -5, 1), (-3, 4, -8)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    sample = [tuple(rng.randint(-6, 6) for _ in range(3)) for _ in range(40)]

    # A -- the review's own statement, verified, together with its reason.
    ranks = {f"H^{k}": betti_rank(k) for k in range(8)}

    # B -- the degree the Dixmier-Douady class actually lives in.
    rows, mismatches = [], []
    for w1, w2, w3 in WINDINGS:
        a1, a2, a3 = (winding_cochain(0, w1), winding_cochain(1, w2),
                      winding_cochain(2, w3))
        cocycle_ok = all(is_cocycle(a, 1, itertools.product(sample[:10], repeat=2))
                         for a in (a1, a2, a3))
        triple = cup(cup(a1, 1, a2, 1), 2, a3, 1)
        triple_ok = is_cocycle(triple, 3, itertools.product(sample[:6], repeat=4))
        measured = fundamental_pairing(triple)
        predicted = w1 * w2 * w3
        if measured != predicted or not cocycle_ok or not triple_ok:
            mismatches.append({"windings": [w1, w2, w3], "measured": measured,
                               "predicted": predicted})
        rows.append({"windings": [w1, w2, w3], "dd_class": measured,
                     "w1w2w3": predicted, "generators_are_cocycles": cocycle_ok,
                     "triple_is_cocycle": triple_ok,
                     "agrees": measured == predicted})

    # C -- the word "vanishes", disambiguated.
    degree_six = degree_six_is_zero_by_dimension()

    report = {
        "subject": "peer review of 'The Sheaf of Becoming' v2, Thm 3 demotion",
        "quoted_reason_for_demotion":
            "the cup product c1 u c1 u c1 in H^6(T^3) = 0 (vanishes)",
        "A_cohomology_ranks": ranks,
        "A_verdict": ("the quoted statement is TRUE: H^6(T^3;Z)=0, because T^3 is "
                      "a closed 3-manifold and cohomology vanishes above the "
                      "dimension. It is true for a reason unrelated to windings, "
                      "gerbes, or the construction under review."),
        "B_triple_winding_products": rows,
        "B_mismatches": mismatches,
        "B_verdict": ("the Dixmier-Douady class lives in H^3(T^3;Z)=Z, where the "
                      "triple cup product of three DEGREE-1 winding classes pairs "
                      "with the fundamental class to give exactly w1w2w3. Winding "
                      "numbers are degree one; c1 is degree two. The demotion is "
                      "computed in the wrong degree."),
        "C_cochain_versus_class": degree_six,
        "C_verdict": ("'vanishes' conflates a zero CLASS with a zero COCHAIN. The "
                      "degree-6 cochain evaluates to 1 on a basis tuple; its class "
                      "is nevertheless zero because the group it would live in is."),
        "conclusion": ("The stated ground for the demotion cannot be the ground. "
                       "Whether Thm 3 holds for the review's actual construction "
                       "is NOT settled here -- that construction is not in hand, "
                       "and the structural claim (HRR binding is a Cech cocycle) "
                       "was never in dispute."),
        "tier": ("P -- exact integer arithmetic, answer forced by the algebra and "
                 "known before the run; this is proof-checking, not evidence"),
    }
    ok = not mismatches and ranks["H^6"] == 0 and ranks["H^3"] == 1
    report["verdict"] = "SETTLED" if ok else "INCONCLUSIVE"

    path = OUT / "dd_class_degree_audit.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="MATH-R6-DD_CLASS_DEGREE",
        evidence_tag="P",
        command="PYTHONPATH=src python3 experiments/run_dd_class_degree_audit.py",
        observed_result={
            # One observation per winding triple actually evaluated.  The
            # cohomology ranks are not observations; they are the same theorem
            # stated seven times, and counting them would inflate.
            "sample_size": len(WINDINGS),
            "mismatches": len(mismatches),
            "rank_H3": ranks["H^3"],
            "rank_H6": ranks["H^6"],
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[SEED],
        input_hashes=[f"windings:{w1},{w2},{w3}" for w1, w2, w3 in WINDINGS],
        raw_artifacts={"artifacts/dd_class_audit/dd_class_degree_audit.json":
                       file_digest(path)},
        environment_dependent=[],
        producer="experiments/run_dd_class_degree_audit.py",
        verifier="",
        typed_remainders=[{
            "kind": "scope_remainder",
            "carrier": "the reviewed construction itself",
            "comparison": ("this settles the DEGREE, not the theorem. The review's "
                           "HRR encoder, its imposed cyclic order, and its measured "
                           "phase winding are not in this repository. Thm 3's "
                           "quantitative claim could still fail for reasons the "
                           "quoted argument does not give")}])
    save_envelope(envelope, OUT / "dd_class_degree_audit.envelope.json")

    print(json.dumps({"verdict": report["verdict"], "ranks": ranks,
                      "mismatches": len(mismatches)}, indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
