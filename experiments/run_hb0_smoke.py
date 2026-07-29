"""Deterministic HB-0 architecture smoke run; calibration, not promotion."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.hb0 import (
    HoloportiveReconstructor,
    MutualRecognitionCoupler,
    RecognitionInput,
    build_hb0,
    teleport_qubit,
    tunnel_two_level,
    validate_hb0_manifest,
)


def recognition_input() -> RecognitionInput:
    return RecognitionInput(
        gluing=0.72,
        useful_update=0.61,
        preserved_difference=0.54,
        absorption_pressure=0.08,
        projection_violence=0.07,
        phase_delta=0.03,
        geometric_distance=0.12,
        gluing_defect=0.06,
        return_fidelity=0.93,
        telos_alignment=0.82,
    )


def run(seed: int = 11) -> dict:
    manifest_path = ROOT / "manifests" / "hb0_polycosmic_architecture.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = validate_hb0_manifest(manifest)
    if not validation.ok:
        raise RuntimeError(validation.errors)

    kernel = build_hb0(seed=seed)
    selected = sorted(kernel.worldlets)[:8]
    deltas = {
        wid: np.full(kernel.worldlets[wid].dimension, 0.001 * (i + 1))
        for i, wid in enumerate(selected)
    }
    accepted = kernel.step(deltas, absorption=0.05)

    snapshot = {wid: w.coordinates.copy() for wid, w in kernel.worldlets.items()}
    target = selected[0]
    rejected = kernel.step(
        {target: np.ones(kernel.worldlets[target].dimension)}, absorption=0.95
    )
    rollback_exact = all(
        np.array_equal(snapshot[wid], kernel.worldlets[wid].coordinates)
        for wid in kernel.worldlets
    )

    recognition = MutualRecognitionCoupler().evaluate(
        recognition_input(), recognition_input()
    )
    reconstruction = HoloportiveReconstructor.reconstruct(
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        np.array([2.0, 3.0]),
        reference=np.array([2.0, 3.0, 4.0]),
    )
    teleportation = teleport_qubit(np.array([1.0, 1.0j]) / np.sqrt(2.0))
    tunnelling = tunnel_two_level(
        np.array([1.0, 0.0]), coupling=1.0, barrier=2.0, duration=0.5
    )

    return {
        "schema": "hypercomplexbrain.hb0.smoke.v1",
        "evidence_status": "calibration_only",
        "seed": seed,
        "manifest_checks": validation.checks_run,
        "worldlets": len(kernel.worldlets),
        "tendrils": len(kernel.tendrils),
        "gerbe_cells": len(kernel.gerbe_cells),
        "clocks": len(kernel.clocks),
        "identity_regimes": len(kernel.identity.regimes),
        "identity_plurality": kernel.identity.plurality(),
        "accepted_step": accepted.accepted,
        "accepted_observed": dict(accepted.viability.observed),
        "rejected_step": rejected.accepted,
        "rejected_reasons": list(rejected.governance_reasons),
        "rollback_exact": rollback_exact,
        "mutual_recognition": recognition.mutual_recognition,
        "mutual_resonance": recognition.resonance,
        "reconstruction_fidelity": reconstruction.fidelity,
        "reconstruction_nullity": reconstruction.nullity,
        "teleportation_fidelity": teleportation.average_fidelity,
        "teleportation_advantage_claim": teleportation.advantage_claim,
        "tunnelling_transfer_probability": tunnelling.transfer_probability,
        "tunnelling_norm_defect": tunnelling.norm_defect,
        "tunnelling_advantage_claim": tunnelling.advantage_claim,
    }


def main() -> int:
    print(json.dumps(run(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
