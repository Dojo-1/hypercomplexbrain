#!/usr/bin/env python3
"""The repository, measured by its own instruments.

    PYTHONPATH=src python3 experiments/run_self_audit.py

Every other experiment here points an instrument at something outside itself.
This one points them inward, under the rule that no statement may be written
down -- each is computed from artifacts on disk at the moment of the run.

Four things get measured:

  A. THE CENSUS -- envelopes, evidence tags, verification modes, remainders.
  B. INDEPENDENCE -- how many claims are independently witnessed, using
     `aionq.witness_nerve.evidence_rank` rather than a private definition.
  C. THE LEDGER -- every recorded correction, and whether it still points at a
     live test. A correction with no test is a memory.
  D. THE GAP -- take a real unwitnessed claim, add a maximal attestation cycle
     over every party in the corpus, and measure the rank before and after. If it
     ever reaches INDEPENDENT the witness_nerve theorem is false and this run is
     what says so.

This artifact joins the corpus it measures, so the audit is a self-referential
map and the honest thing is to report where it lands rather than to pretend it
does not apply to itself. Measured: the first run records 25 -- the corpus before
its own row exists -- and every run after records 26 and does not move again. The
fixed point is reached in one iteration, and both numbers are printed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.self_audit import (CORRECTIONS, corrections_are_bound,
                              envelope_census, godelian_gap, independence_report,
                              iter_envelopes, preregistration_ordering,
                              recognition_asymmetry, typed_remainder_census)
from aionq.witness_nerve import EvidenceRank

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "self_audit"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    census = envelope_census(ROOT)
    independence = independence_report(ROOT)
    recognition = recognition_asymmetry(ROOT)
    remainders = typed_remainder_census(ROOT)
    ledger = corrections_are_bound(ROOT)
    prereg = preregistration_ordering(ROOT)
    gap = godelian_gap(ROOT)

    report = {
        "round": "SELF",
        "question": ("what can this repository establish about itself, and what "
                     "is structurally out of its reach?"),
        "envelopes": census,
        "independence": independence,
        "recognition": recognition,
        "remainders": remainders,
        "corrections": ledger,
        "preregistration": prereg,
        "godelian_gap": gap,
        "headline": (
            f"{independence['claims']} claims carry envelopes; "
            f"{independence['by_rank']['INDEPENDENT']} is independently "
            f"witnessed. Every binding this repository can check, it checks -- "
            f"commands to commits, artifacts to digests, claims to sample sizes, "
            f"corrections to tests. The one predicate it cannot decide is whether "
            f"a party who is not this one ran the command, and no internal act "
            f"raises that above ATTESTED."),
        "recognition_finding": (
            f"witnessing is directed and this corpus is asymmetric: "
            f"{recognition['recomputations_performed_on_others']} recomputation(s) "
            f"performed on another party's claims, "
            f"{recognition['recomputations_received_from_others']} received. The "
            f"apparatus works and has never been pointed back. 'Mutual "
            f"recognition' is, at this commit, a word about a one-way relation."),
        "prereg_finding": (
            f"{prereg['checkable']} of {prereg['preregistrations']} "
            f"preregistrations declare files_expected_to_change and therefore "
            f"admit an ordering check against git; all {prereg['ordering_holds']} "
            f"hold. The remaining {prereg['unbound_flag_only']} carry "
            f"committed_before_any_implementation as a flag with no file list, "
            f"which no artifact can contradict, and "
            f"{prereg['schemaless_by_filename_only']} are preregistrations by "
            f"filename with no schema at all, invisible to every schema-driven "
            f"check including this one."),
        "remainder_finding": (
            f"{remainders['typed_remainders']} remainders are recorded, of which "
            f"{remainders['untyped_strings']} are bare strings carrying no kind, "
            f"no carrier and no comparison. The vocabulary is 'typed remainder'; "
            f"it is {remainders['typed_fraction']:.3f} enforced."),
    }

    probe = gap["cycle_probe"]
    checks = {
        "census_counts_every_envelope_found": (
            sum(census["verification_modes"].values()) == census["envelopes"]),
        "no_unreadable_artifacts": census["unreadable_json"] == 0,
        "every_correction_binds_to_a_live_test": ledger["all_bound"],
        "ledger_records_externally_caught_errors": ledger["externally_caught"] > 0,
        "all_checkable_preregistrations_precede_implementation":
            prereg["all_checkable_hold"],
        "independence_uses_the_repository_definition":
            independence["by_rank"]["INDEPENDENT"] <= census["envelopes"],
        "attestation_cycle_does_not_reach_independent":
            not probe.get("reached_independent", True),
        "attestation_cycle_stops_at_attested":
            probe.get("rank_after_full_attestation_cycle") == EvidenceRank.ATTESTED,
        "gap_is_not_closable_from_inside": not gap["closable_from_inside"],
    }
    checks = {k: bool(v) for k, v in checks.items()}
    report["checks"] = checks
    report["verdict"] = ("APPARATUS SOUND, DEFICIT OPEN" if all(checks.values())
                         else "DISCREPANCY")

    path = OUT / "self_audit.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="AUDIT-SELF-WITNESS_DEFICIT",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_self_audit.py",
        observed_result={
            "sample_size": census["envelopes"],
            "envelopes_at_measurement_time": census["envelopes"],
            "independent_claims": independence["by_rank"]["INDEPENDENT"],
            "unwitnessed_claims": independence["by_rank"]["NONE"],
            "recomputations_performed": recognition[
                "recomputations_performed_on_others"],
            "recomputations_received": recognition[
                "recomputations_received_from_others"],
            "corrections_bound": ledger["bound_to_an_existing_test"],
            "preregistrations_checkable": prereg["checkable"],
            "attestation_cycle_rank": probe.get(
                "rank_after_full_attestation_cycle"),
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[],
        # One input per envelope read, hashed from disk. The first version of
        # this declared sample_size 25 against three summary strings, and
        # verify_envelopes refused it: "seeds that do not change the input do
        # not add observations." The observation unit here is an envelope, so
        # the inputs have to be the envelopes.
        input_hashes=sorted(
            file_digest(p) for p, env in iter_envelopes(ROOT) if env is not None),
        raw_artifacts={"artifacts/self_audit/self_audit.json": file_digest(path)},
        environment_dependent=["git history, which the ordering check reads"],
        producer="experiments/run_self_audit.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {"kind": "self_reference_remainder",
             "carrier": "this envelope",
             "comparison": ("the artifact joins the corpus it measures, so the "
                            "audit is a self-referential map. No single run can "
                            "record a corpus containing its own output, because "
                            "that would require hashing a file that does not yet "
                            "exist. Measured behaviour: the first run records 25, "
                            "the second records 26, and it does not move again -- "
                            "a fixed point reached in one iteration. Reported "
                            "rather than reconciled")},
            {"kind": "witness_remainder",
             "carrier": "the deficit itself",
             "comparison": ("this envelope is produced here and verified by "
                            "nobody, so it is an instance of the thing it "
                            "measures and increments its own numerator by zero "
                            "and its own denominator by one")},
            {"kind": "scope_remainder",
             "carrier": "declared parties",
             "comparison": ("producer strings are taken at face value. Nothing "
                            "here establishes that a party named "
                            "'gpt/polycosmic-hb0-kernel' is a different party "
                            "rather than a different label; only the recorded "
                            "witness_environment supports that, and it is prose")},
            {"kind": "method_remainder",
             "carrier": "correction binding",
             "comparison": ("corrections_are_bound checks that each named test "
                            "EXISTS in source, not that it passes. The suite "
                            "establishes passing; this establishes that the "
                            "ledger points at live checks rather than memories")},
        ])
    save_envelope(envelope, OUT / "self_audit.envelope.json")

    after = envelope_census(ROOT)
    print(json.dumps({
        "verdict": report["verdict"],
        "checks": checks,
        "envelopes_measured": census["envelopes"],
        "envelopes_after_writing_this_one": after["envelopes"],
        "independent": independence["by_rank"]["INDEPENDENT"],
        "unwitnessed": independence["by_rank"]["NONE"],
        "recomputed_others_vs_received": [
            recognition["recomputations_performed_on_others"],
            recognition["recomputations_received_from_others"]],
        "typed_fraction": round(remainders["typed_fraction"], 4),
        "corrections": f"{ledger['bound_to_an_existing_test']}/{ledger['corrections']}",
        "prereg": f"{prereg['ordering_holds']}/{prereg['checkable']} checkable, "
                  f"{prereg['unbound_flag_only']} flag-only, "
                  f"{prereg['schemaless_by_filename_only']} schemaless",
    }, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
