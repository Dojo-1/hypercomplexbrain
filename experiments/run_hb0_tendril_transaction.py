"""Frozen HB0-T1 active-tendril transaction probe.

This is a deterministic simulator calibration.  It measures whether the
declared transaction primitive lands on the routed target under matched
controls; it does not measure task competence or cognitive advantage.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.evidence import (
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
)
from aionq.hb0 import (
    CarrierMismatch,
    ChartFunctor,
    build_hb0,
)


SEEDS = tuple(range(8))
TENDRIL_ID = "T_00"
DECLARED_TARGET = "W_somatic_01"
SHUFFLED_TARGET = "W_somatic_02"
COUPLING = 0.5

OUT_DIR = ROOT / "artifacts" / "hb0_active_tendril"
RESULT = OUT_DIR / "active_tendril.json"
ENVELOPE = OUT_DIR / "active_tendril.envelope.json"
PREREG = ROOT / "manifests" / "hb0_active_tendril_preregistration.json"


def _canonical_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _snapshot(kernel) -> dict[str, np.ndarray]:
    return {
        worldlet_id: worldlet.coordinates.copy()
        for worldlet_id, worldlet in kernel.worldlets.items()
    }


def _identity_snapshot(kernel) -> dict[str, np.ndarray]:
    return {
        regime_id: regime.section.copy()
        for regime_id, regime in kernel.identity.regimes.items()
    }


def _state_digest(snapshot: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for worldlet_id in sorted(snapshot):
        digest.update(worldlet_id.encode("utf-8"))
        digest.update(np.asarray(snapshot[worldlet_id], dtype="<f8").tobytes())
    return f"sha256:{digest.hexdigest()}"


def _same_snapshot(
    before: dict[str, np.ndarray],
    kernel,
) -> bool:
    return all(
        np.array_equal(coordinates, kernel.worldlets[worldlet_id].coordinates)
        for worldlet_id, coordinates in before.items()
    )


def _same_identity(
    before: dict[str, np.ndarray],
    kernel,
) -> bool:
    return all(
        np.array_equal(section, kernel.identity.regimes[regime_id].section)
        for regime_id, section in before.items()
    )


def _changed_worldlets(
    before: dict[str, np.ndarray],
    kernel,
) -> list[str]:
    return sorted(
        worldlet_id
        for worldlet_id, coordinates in before.items()
        if not np.array_equal(
            coordinates,
            kernel.worldlets[worldlet_id].coordinates,
        )
    )


def _authorization(kernel) -> dict[str, float]:
    return {"compute": kernel.tendrils[TENDRIL_ID].cost}


def _serialise_report(report) -> dict:
    payload = asdict(report)
    payload["viability"]["gates"] = dict(report.viability.gates)
    payload["viability"]["observed"] = dict(report.viability.observed)
    return payload


def _complex_exception_control(seed: int) -> dict:
    kernel = build_hb0(seed=seed)
    tendril = kernel.tendrils[TENDRIL_ID]
    original = tendril.chart
    tendril.chart = ChartFunctor(
        id=original.id,
        source_carrier=original.source_carrier,
        target_carrier=original.target_carrier,
        forward=lambda x: x.astype(complex) + 1j * np.ones_like(x),
        backward=original.backward,
        preserved=original.preserved,
        transformed=original.transformed,
        lost=original.lost,
    )
    worlds_before = _snapshot(kernel)
    identity_before = _identity_snapshot(kernel)
    budget_before = kernel._budget_snapshot()
    tick_before = kernel.tick
    ledger_before = tuple(kernel.tendril_ledger)
    error = ""
    try:
        kernel.transact_tendril(
            TENDRIL_ID,
            coupling=COUPLING,
            authorized_sources=_authorization(kernel),
        )
    except CarrierMismatch as exc:
        error = str(exc)
    return {
        "error": error,
        "phase_rejected": "complex-valued" in error,
        "worldlets_exact": _same_snapshot(worlds_before, kernel),
        "identity_exact": _same_identity(identity_before, kernel),
        "budget_exact": kernel._budget_snapshot() == budget_before,
        "tick_exact": kernel.tick == tick_before,
        "ledger_exact": tuple(kernel.tendril_ledger) == ledger_before,
    }


def _run_seed(seed: int) -> dict:
    active = build_hb0(seed=seed)
    initial = _snapshot(active)
    identity_initial = _identity_snapshot(active)
    active_report = active.transact_tendril(
        TENDRIL_ID,
        coupling=COUPLING,
        authorized_sources=_authorization(active),
    )

    disabled = build_hb0(seed=seed)
    disabled_before = _snapshot(disabled)
    disabled_report = disabled.transact_tendril(
        TENDRIL_ID,
        coupling=COUPLING,
        authorized_sources=_authorization(disabled),
        mode="disabled_control",
    )

    shuffled = build_hb0(seed=seed)
    shuffled_before = _snapshot(shuffled)
    shuffled_report = shuffled.transact_tendril(
        TENDRIL_ID,
        coupling=COUPLING,
        authorized_sources=_authorization(shuffled),
        mode="shuffled_target_control",
        control_target=SHUFFLED_TARGET,
    )

    rejected = build_hb0(seed=seed)
    rejected_before = _snapshot(rejected)
    rejected_identity = _identity_snapshot(rejected)
    rejected_report = rejected.transact_tendril(
        TENDRIL_ID,
        coupling=COUPLING,
        authorized_sources={},
    )

    duplicate = build_hb0(seed=seed)
    duplicate_report = duplicate.transact_tendril(
        TENDRIL_ID,
        coupling=COUPLING,
        authorized_sources=_authorization(duplicate),
    )

    return {
        "seed": seed,
        "input_digest": _state_digest(initial),
        "active": _serialise_report(active_report),
        "active_changed_worldlets": _changed_worldlets(initial, active),
        "active_identity_exact": _same_identity(identity_initial, active),
        "disabled": _serialise_report(disabled_report),
        "disabled_changed_worldlets": _changed_worldlets(
            disabled_before, disabled
        ),
        "shuffled": _serialise_report(shuffled_report),
        "shuffled_changed_worldlets": _changed_worldlets(
            shuffled_before, shuffled
        ),
        "shuffled_declared_target_exact": np.array_equal(
            shuffled_before[DECLARED_TARGET],
            shuffled.worldlets[DECLARED_TARGET].coordinates,
        ),
        "rejected": _serialise_report(rejected_report),
        "rejected_worldlets_exact": _same_snapshot(
            rejected_before, rejected
        ),
        "rejected_identity_exact": _same_identity(
            rejected_identity, rejected
        ),
        "complex_exception": _complex_exception_control(seed),
        "deterministic_report": active_report == duplicate_report,
        "deterministic_worldlets": all(
            np.array_equal(
                active.worldlets[worldlet_id].coordinates,
                duplicate.worldlets[worldlet_id].coordinates,
            )
            for worldlet_id in active.worldlets
        ),
    }


def run() -> dict:
    rows = [_run_seed(seed) for seed in SEEDS]
    controls = {
        "active_accepted": all(row["active"]["accepted"] for row in rows),
        "active_only_declared_target": all(
            row["active_changed_worldlets"] == [DECLARED_TARGET]
            for row in rows
        ),
        "active_nonzero_vector_delta": all(
            row["active"]["committed_delta_norm"] > 0.0
            and any(value != 0.0 for value in row["active"]["committed_delta"])
            for row in rows
        ),
        "active_alignment_decreases": all(
            row["active"]["alignment_after"]
            < row["active"]["alignment_before"]
            for row in rows
        ),
        "round_trip_guard_holds": all(
            row["active"]["transport_remainder"]["magnitude"] <= 1e-12
            and row["active"]["return_fidelity"] >= 1.0 - 1e-12
            and row["disabled"]["round_trip"]
            == row["active"]["round_trip"]
            and row["shuffled"]["round_trip"]
            == row["active"]["round_trip"]
            for row in rows
        ),
        "identity_not_consolidated_in_this_slice": all(
            row["active_identity_exact"] for row in rows
        ),
        "disabled_matched_observation_and_cost": all(
            row["disabled"]["transported_output"]
            == row["active"]["transported_output"]
            and row["disabled"]["cost"] == row["active"]["cost"]
            for row in rows
        ),
        "disabled_zero_committed_delta": all(
            row["disabled_changed_worldlets"] == []
            and row["disabled"]["committed_delta_norm"] == 0.0
            and not row["disabled"]["committed"]
            for row in rows
        ),
        "shuffled_only_control_target": all(
            row["shuffled_changed_worldlets"] == [SHUFFLED_TARGET]
            and row["shuffled_declared_target_exact"]
            and row["shuffled"]["selected_target"] == SHUFFLED_TARGET
            for row in rows
        ),
        "shuffled_matched_observation_and_cost": all(
            row["shuffled"]["transported_output"]
            == row["active"]["transported_output"]
            and row["shuffled"]["cost"] == row["active"]["cost"]
            and row["shuffled"]["permeability"]
            == row["active"]["permeability"]
            for row in rows
        ),
        "missing_authorization_rejects_exactly": all(
            not row["rejected"]["accepted"]
            and row["rejected"]["governance_reasons"] == ("compute",)
            and row["rejected_worldlets_exact"]
            and row["rejected_identity_exact"]
            for row in rows
        ),
        "complex_phase_rejected_without_state_change": all(
            control["phase_rejected"]
            and control["worldlets_exact"]
            and control["identity_exact"]
            and control["budget_exact"]
            and control["tick_exact"]
            and control["ledger_exact"]
            for control in (row["complex_exception"] for row in rows)
        ),
        "seed_deterministic": all(
            row["deterministic_report"] and row["deterministic_worldlets"]
            for row in rows
        ),
    }
    return {
        "schema": "hypercomplexbrain.hb0.active_tendril.v1",
        "evidence_status": "bounded_simulator_measurement",
        "probe": {
            "seeds": list(SEEDS),
            "tendril_id": TENDRIL_ID,
            "declared_target": DECLARED_TARGET,
            "shuffled_target": SHUFFLED_TARGET,
            "coupling": COUPLING,
            "authorization": {"compute": 0.1},
        },
        "transaction_law": (
            "u=F_t(x); y*=Retract_Y(y + alpha*permeability_Y*(u-y))"
        ),
        "controls": controls,
        "rows": rows,
        "summary": {
            "sample_size": len(rows),
            "minimum_committed_delta_norm": min(
                row["active"]["committed_delta_norm"] for row in rows
            ),
            "maximum_committed_delta_norm": max(
                row["active"]["committed_delta_norm"] for row in rows
            ),
            "minimum_alignment_reduction": min(
                row["active"]["alignment_before"]
                - row["active"]["alignment_after"]
                for row in rows
            ),
            "all_controls_hold": all(controls.values()),
        },
        "scope": {
            "real_carrier_only": True,
            "single_tendril_only": True,
            "identity_consolidation_tested": False,
            "task_competence_claim": False,
            "cognitive_advantage_claim": False,
            "quantum_advantage_claim": False,
            "consciousness_or_agi_claim": False,
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    envelope_only = "--envelope-only" in sys.argv[1:]
    if envelope_only:
        report = json.loads(RESULT.read_text(encoding="utf-8"))
    else:
        report = run()
        _canonical_json(RESULT, report)

    envelope = EvidenceEnvelope(
        claim_id="EXP-HB0-ACTIVE-TENDRIL",
        evidence_tag="M",
        command="python experiments/run_hb0_tendril_transaction.py",
        observed_result={
            "sample_size": report["summary"]["sample_size"],
            "all_controls_hold": report["summary"]["all_controls_hold"],
            "minimum_committed_delta_norm": report["summary"][
                "minimum_committed_delta_norm"
            ],
            "minimum_alignment_reduction": report["summary"][
                "minimum_alignment_reduction"
            ],
            "single_tendril_only": True,
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=list(SEEDS),
        input_hashes=sorted(
            {row["input_digest"] for row in report["rows"]}
        ),
        raw_artifacts={
            "artifacts/hb0_active_tendril/active_tendril.json": file_digest(
                RESULT
            ),
            "experiments/run_hb0_tendril_transaction.py": file_digest(
                ROOT / "experiments" / "run_hb0_tendril_transaction.py"
            ),
            "manifests/hb0_active_tendril_preregistration.json": file_digest(
                PREREG
            ),
            "src/aionq/hb0/kernel.py": file_digest(
                ROOT / "src" / "aionq" / "hb0" / "kernel.py"
            ),
            "tests/test_hb0_tendril_transaction.py": file_digest(
                ROOT / "tests" / "test_hb0_tendril_transaction.py"
            ),
        },
        environment_dependent=["NumPy QR in the seeded HB-0 factory"],
        producer="experiments/run_hb0_tendril_transaction.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {
                "kind": "identity_remainder",
                "carrier": "slow-clock identity sections",
                "comparison": (
                    "the transaction moves one worldlet but deliberately does "
                    "not consolidate identity sections; that is the next "
                    "independent slice"
                ),
            },
            {
                "kind": "carrier_remainder",
                "carrier": "complex and hypercomplex coordinates",
                "comparison": (
                    "HB0-T1 rejects non-real outputs instead of discarding phase; "
                    "phase-preserving transport remains unimplemented"
                ),
            },
            {
                "kind": "scope_remainder",
                "carrier": "one deterministic simulator transaction",
                "comparison": (
                    "target landing is not evidence of held-out competence, "
                    "cognitive advantage, quantum advantage, consciousness, or AGI"
                ),
            },
            {
                "kind": "evidence_remainder",
                "carrier": "local producer run",
                "comparison": (
                    "the envelope binds code, controls, inputs, and output but "
                    "has not been independently recomputed"
                ),
            },
        ],
    )
    save_envelope(envelope, ENVELOPE)
    ENVELOPE.write_bytes(
        ENVELOPE.read_text(encoding="utf-8")
        .replace("\r\n", "\n")
        .encode("utf-8")
    )
    print(
        json.dumps(
            {
                "all_controls_hold": report["summary"][
                    "all_controls_hold"
                ],
                "minimum_committed_delta_norm": report["summary"][
                    "minimum_committed_delta_norm"
                ],
                "minimum_alignment_reduction": report["summary"][
                    "minimum_alignment_reduction"
                ],
                "rows": len(report["rows"]),
                "mode": (
                    "envelope_only"
                    if envelope_only
                    else "primary_execution"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["summary"]["all_controls_hold"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
