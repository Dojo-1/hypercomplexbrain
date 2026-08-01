#!/usr/bin/env python3
"""QSigma-R6k-W1: recompute R6k on a second platform and compare by meaning.

    PYTHONPATH=src python3 experiments/run_r6k_semantic_reproduction.py

R6k was executed once, on Windows / CPython 3.13 / numpy 2.4.5, from an
uncommitted working tree.  R6l seals it byte-for-byte as upstream.  It has never
been recomputed by a second party, and the repository's own witness machinery
cannot honestly promote it -- three measured reasons are recorded in the
preregistration and none of them is repaired here.

What this runner does NOT do, deliberately:

  * it does not invoke ``experiments/run_equal_resource_reservoir.py``.  That
    runner's PRESERVED gate demands S4/G100 bytes that do not exist at C_pre, so
    it cannot run from a clean clone by anyone, including its author.  This calls
    the library entry point ``run_protocol`` directly and says so.
  * it does not modify any R6k artifact.  R6l pins their hashes.
  * it does not touch ``witness.py`` or ``evidence.py``.  Those repairs belong
    after the R6l C_env gate.
  * it records its own claim, ``WITNESS-R6K-SEMANTIC_REPRODUCTION``.  It does not
    edit R6k's envelope to say it has been witnessed.

Two phases, because an envelope must bind to a commit that CONTAINS what it
binds.  The first version wrote result, comparison and envelope in one run, and
``current_commit()`` returned the correction commit -- the last thing committed
before the run.  Every raw artifact resolved to None at that SHA.  An external
audit caught it: the envelope looked bound and was not, which is worse than the
empty-``commit_sha`` path it was written to avoid, because the empty field at
least declares itself.

    PYTHONPATH=src python3 experiments/run_r6k_semantic_reproduction.py run
    git add artifacts/... && git commit           # C_raw
    PYTHONPATH=src python3 experiments/run_r6k_semantic_reproduction.py envelope
    git add artifacts/...envelope.json && git commit

The ``envelope`` phase FAILS if any raw artifact is absent from HEAD or differs
from its committed bytes.  That is the check whose absence produced the defect.

Controls, from the preregistration:

  C1  a copy of the reproduction with ONE scientific float moved by 1e-9 must
      come back CONTRADICTED.  A comparator that cannot fail has established
      nothing.
  C2  the number of scientific leaves actually compared is reported, and
      CONFIRMED is unreachable unless they are most of the non-digest leaves.
  C3  digest leaves are counted, not dropped from the denominator.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.equal_resource_reservoir import run_protocol
from aionq.evidence import (EvidenceEnvelope, current_commit,
                            environment_digest, file_digest, save_envelope,
                            _committed_file_digest)
from aionq.semantic_reproduction import (ENVIRONMENT_METADATA_LEAVES,
                                         MINIMUM_SCIENTIFIC_BACKSTOP,
                                         MINIMUM_SCIENTIFIC_FRACTION,
                                         compare_event_traces, compare_results,
                                         perturb_leaf, reproduction_verdict,
                                         structural_checks)

ROOT = Path(__file__).resolve().parent.parent
R6K = ROOT / "artifacts" / "r6k_equal_resource_reservoir"
OUT = ROOT / "artifacts" / "r6k_w1_semantic_reproduction"
PREREG = ROOT / "manifests" / "qsigma_r6k_w1_semantic_reproduction_preregistration.json"
CORRECTION = ROOT / "manifests" / "qsigma_r6k_w1_semantic_reproduction_method_correction.json"
PARTB = ROOT / "manifests" / "qsigma_r6k_w1_partb_interval_correction.json"
TOLERANCE = 1e-10
PERTURBATION = 1e-9

#: Amendment: `reproduction_verdict` now demands the caller DECLARE which
#: producer-only leaves are expected, instead of tolerating them wholesale.
#: These are the sections `run_equal_resource_reservoir.py` adds and the library
#: entry point cannot emit; anything outside them contradicts.
ALLOWED_ONLY_IN_PRODUCED_PREFIXES = (
    ".checks.", ".execution_binding.", ".preregistration.", ".provenance.",
    ".method_correction.", ".architecture_or_hardware_claim_authorized",
)


#: Typed remainders for the claim, hoisted to module level so the envelope
#: phase can attach them without re-running the comparison.
TYPED_REMAINDERS = [
    {"kind": "witness_remainder",
     "carrier": "what agreement here establishes",
     "comparison": ("semantic agreement of one protocol across two "
                    "platforms, computed by a second party in an "
                    "environment the first did not prepare. NOT that the "
                    "protocol is correct, NOT that R6i's differential is "
                    "real, NOT that R6k's own runner is reproducible")},
    {"kind": "method_remainder",
     "carrier": "the 22 runner checks",
     "comparison": ("R6k's committed result carries 43 leaves this "
                    "reproduction cannot emit, 22 of them boolean checks "
                    "about the PRODUCING working tree -- preserved file "
                    "hashes, manifest freeze, dirty-file stability. A "
                    "second platform cannot verify those after the fact "
                    "at all. They are reported as uncomparable and are "
                    "not counted as agreement")},
    {"kind": "instrument_remainder",
     "carrier": "digest equality",
     "comparison": ("493 identity leaves differ. R6k's input_hashes and "
                    "per-row digests are SHA-256 of computed float "
                    "arrays, so a last-bit difference from a different "
                    "BLAS changes them completely. apply_witness compares "
                    "exactly this population by digest, which is why it "
                    "could never have confirmed R6k across platforms -- "
                    "while the 11 files it WOULD have compared are all "
                    "tracked repository files a verifier gets by cloning")},
    {"kind": "naming_remainder",
     "carrier": "producer identity",
     "comparison": ("the producer string names a SCRIPT, not a party. The "
                    "same script produced R6k on Windows and this "
                    "reproduction on Linux; only the environment digest "
                    "distinguishes them. aionq.self_audit treats any "
                    "experiments/ producer as self, so this act will not "
                    "register in recognition_asymmetry until that is "
                    "fixed -- deliberately not fixed in this round")},
    {"kind": "scope_remainder",
     "carrier": "one execution",
     "comparison": ("one run against one run. No seed sweep, no repeated "
                    "execution on either platform, so run-to-run variation "
                    "within a platform is unmeasured and the 3.3e-11 "
                    "cannot be attributed to the platform difference "
                    "rather than to the arithmetic being deterministic")},
]

def _allowed(path: str) -> bool:
    return path.startswith(ALLOWED_ONLY_IN_PRODUCED_PREFIXES)


def phase_run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    produced = json.loads(
        (R6K / "equal_resource_reservoir.json").read_text(encoding="utf-8"))

    # ---- the second execution ----------------------------------------------
    events_path = OUT / "events.jsonl"
    if events_path.exists():
        events_path.unlink()
    reproduced = run_protocol(event_path=events_path)
    result_path = OUT / "reproduction.json"
    result_path.write_text(
        json.dumps(reproduced, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # ---- the comparison ----------------------------------------------------
    comparison = compare_results(produced, reproduced, TOLERANCE)
    structural = structural_checks(produced, reproduced)
    events = compare_event_traces(R6K / "events.jsonl", events_path)
    allowed = [p for p in comparison["only_in_produced"] if _allowed(p)]
    verdict = reproduction_verdict(comparison, structural, events,
                                   allowed_only_in_produced=allowed)

    # ---- C1: the comparator must be able to fail ---------------------------
    probe_path = comparison["worst_difference_path"]
    perturbed = perturb_leaf(reproduced, probe_path, PERTURBATION)
    c1_comparison = compare_results(produced, perturbed, TOLERANCE)
    c1_verdict = reproduction_verdict(c1_comparison, structural, events,
                                      allowed_only_in_produced=allowed)

    controls = {
        "C1_perturbed_copy_is_contradicted":
            c1_verdict["verdict"] == "CONTRADICTED",
        "C1_perturbation_actually_changed_the_document":
            perturbed != reproduced,
        "C1_perturbed_leaf_exceeds_tolerance":
            probe_path in c1_comparison["scientific_leaves_exceeding_tolerance"],
        "C2_enough_scientific_leaves_compared": verdict["enough_compared"],
        "C3_identity_leaves_counted_not_dropped":
            comparison["identity_leaves"] > 0,
        "every_producer_only_leaf_is_a_declared_runner_section":
            all(_allowed(p) for p in comparison["only_in_produced"]),
        "reproduction_emitted_no_leaf_the_producer_lacks":
            not comparison["only_in_reproduced"],
        "event_sequences_agree": events["sequence_equal"],
        "environment_exclusion_list_is_closed":
            set(ENVIRONMENT_METADATA_LEAVES)
            == {".resource_ledger.compiler_proxy.qiskit_version"},
        "no_r6k_artifact_was_written":
            not any(p.parent == R6K for p in (result_path, events_path)),
    }
    controls = {k: bool(v) for k, v in controls.items()}

    report = {
        "round": "QSigma-R6k-W1",
        "claim": "WITNESS-R6K-SEMANTIC_REPRODUCTION",
        "question": ("does R6k's numerical content reproduce on a second "
                     "platform under a tolerance frozen before the comparator "
                     "existed, and does its discrete verdict survive?"),
        "producer_of_record": "experiments/run_equal_resource_reservoir.py",
        "verifier": "claude-code-linux",
        "entry_point_used": "aionq.equal_resource_reservoir.run_protocol",
        "entry_point_reason": (
            "the R6k runner's PRESERVED gate demands S4/G100 sha256 f94809ca... "
            "and cfd3128d..., while at C_pre those files hash to 8d03960c... and "
            "9e458867... on a clean checkout. The runner is not executable from "
            "origin by anyone; the protocol is."),
        "tolerance": TOLERANCE,
        "comparison": comparison,
        "structural": structural,
        "events": events,
        "verdict_detail": verdict,
        "control_C1": {
            "perturbed_path": probe_path,
            "perturbation": PERTURBATION,
            "verdict": c1_verdict["verdict"],
        },
        "controls": controls,
        "verdict": verdict["verdict"],
        "headline": (
            f"{verdict['scientific_leaves_compared']} scientific leaves compared "
            f"across two platforms; worst absolute difference "
            f"{comparison['worst_absolute_difference']:.3e} against a frozen "
            f"tolerance of {TOLERANCE:.0e}. The discrete verdict is identical on "
            f"both sides. {comparison['identity_mismatches']} digest leaves "
            f"differ and are excluded by preregistration, because R6k's digests "
            f"are SHA-256 of computed float arrays and therefore ask whether two "
            f"machines rounded identically rather than whether they agree."),
        "not_claimed": (
            "this establishes semantic agreement of one protocol across two "
            "platforms. It does not establish that the protocol is correct, that "
            "R6i's differential is real, that R6k's 22 runner checks hold, or "
            "that the R6k runner is reproducible -- it is measurably not."),
    }
    comparison_path = OUT / "comparison.json"
    comparison_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "verdict": report["verdict"],
        "controls": controls,
        "scientific_leaves_compared": verdict["scientific_leaves_compared"],
        "non_digest_leaves": verdict["non_digest_leaves"],
        "scientific_fraction": round(verdict["scientific_fraction"], 4),
        "worst_absolute_difference": comparison["worst_absolute_difference"],
        "worst_difference_path": comparison["worst_difference_path"],
        "discrete_mismatches": comparison["discrete_mismatches"],
        "identity_mismatches_excluded": comparison["identity_mismatches"],
        "environment_mismatches_excluded": comparison["environment_mismatches"],
        "runner_only_leaves": len(comparison["only_in_produced"]),
        "events": events,
        "C1_verdict": c1_verdict["verdict"],
        "identity_leaves_total": comparison["identity_leaves"],
        "next": "commit these artifacts, then run the `envelope` phase",
    }, indent=2))
    return 0 if (report["verdict"] == "CONFIRMED"
                 and all(controls.values())) else 1


def phase_envelope() -> int:
    """Bind the claim to a commit that CONTAINS the artifacts it binds.

    Every raw artifact must resolve at HEAD and match its committed bytes. The
    published first attempt recorded a SHA at which all three resolved to None,
    and `verify` reported ok because a missing blob is treated as "cannot
    check". A SHA that binds nothing is worse than no SHA at all: it reads as
    provenance.
    """
    report = json.loads((OUT / "comparison.json").read_text(encoding="utf-8"))
    commit = current_commit()
    raw = {
        "artifacts/r6k_w1_semantic_reproduction/reproduction.json":
            OUT / "reproduction.json",
        "artifacts/r6k_w1_semantic_reproduction/events.jsonl":
            OUT / "events.jsonl",
        "artifacts/r6k_w1_semantic_reproduction/comparison.json":
            OUT / "comparison.json",
    }
    binding = {}
    for rel, path in raw.items():
        on_disk = file_digest(path)
        at_commit = _committed_file_digest(rel, commit, ROOT)
        binding[rel] = {"on_disk": on_disk, "at_commit": at_commit,
                        "bound": at_commit is not None and at_commit == on_disk}
    unbound = [r for r, b in binding.items() if not b["bound"]]
    if unbound:
        print(json.dumps({
            "phase": "envelope", "commit": commit, "FAILED": True,
            "reason": ("raw artifacts are not present at HEAD with these bytes; "
                       "commit them first, then rerun this phase"),
            "unbound": unbound, "binding": binding}, indent=2))
        return 1

    comparison = report["comparison"]
    verdict = report["verdict_detail"]
    envelope = EvidenceEnvelope(
        claim_id="WITNESS-R6K-SEMANTIC_REPRODUCTION",
        evidence_tag="M",
        command=("PYTHONPATH=src python3 experiments/"
                 "run_r6k_semantic_reproduction.py run  (then: envelope)"),
        observed_result={
            # ONE produced run against ONE reproduced run. The 3555 leaves are
            # measurements of a single paired comparison, not 3555 observations,
            # and the manifests are provenance rather than samples -- an
            # external audit corrected an earlier value of 4 to this.
            "sample_size": 1,
            "design": "paired: one produced execution against one reproduced execution",
            "scientific_leaves_compared": comparison["scientific_leaves_compared"],
            "worst_absolute_difference": comparison["worst_absolute_difference"],
            "worst_difference_path": comparison["worst_difference_path"],
            "tolerance": report["tolerance"],
            "discrete_verdict_matches": report["structural"]["rows"]["verdict"]["equal"],
            "event_rows": report["events"]["reproduced_rows"],
            "identity_leaves_total": comparison["identity_leaves"],
            "identity_leaves_differing": comparison["identity_mismatches"],
            "runner_only_leaves_uncomparable": len(comparison["only_in_produced"]),
            "rules_bound_to": {
                "preregistration": file_digest(PREREG),
                "method_correction": file_digest(CORRECTION),
                "part_b_interval_correction": file_digest(PARTB),
            },
            "verdict": report["verdict"],
        },
        commit_sha=commit,
        environment=environment_digest(),
        seeds=[],
        # The inputs of a paired comparison are the two documents of the party
        # of record. The manifests are provenance and were wrongly counted as
        # observations in the published version.
        input_hashes=[
            file_digest(R6K / "equal_resource_reservoir.json"),
            file_digest(R6K / "events.jsonl"),
        ],
        raw_artifacts={rel: binding[rel]["on_disk"] for rel in raw},
        environment_dependent=[],
        producer="experiments/run_equal_resource_reservoir.py",
        verifier="claude-code-linux",
        verification_mode="recomputed",
        typed_remainders=TYPED_REMAINDERS)
    save_envelope(envelope, OUT / "reproduction.envelope.json")
    print(json.dumps({"phase": "envelope", "commit": commit,
                      "all_raw_artifacts_bound_at_this_commit": True,
                      "binding": {k: v["bound"] for k, v in binding.items()},
                      "sample_size": 1,
                      "verdict": report["verdict"]}, indent=2))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    phase = argv[0] if argv else "run"
    if phase == "run":
        return phase_run()
    if phase == "envelope":
        return phase_envelope()
    print("usage: run_r6k_semantic_reproduction.py [run|envelope]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
