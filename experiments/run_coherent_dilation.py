#!/usr/bin/env python3
"""Frozen QSigma-R6i coherent-dilation execution.

Preregistered in ``manifests/qsigma_r6i_coherent_dilation_preregistration.json``.
The grid, metrics, margin, decision rule, controls, and scope remainders are
loaded exactly as committed; this runner contains no outcome-dependent tuning.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.capacity_ceiling import holevo_ceiling
from aionq.coherent_dilation import (
    RESCUE_MARGIN_BITS,
    classify_rescue,
    composition_defect,
    density_state_diagnostics,
    ensemble_information,
    halmos_dilation,
    matched_codebooks,
    normalised_contraction,
)
from aionq.evidence import (
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
)
from aionq.hyperbolic_qubit import swirl_point, to_sl2


PREREG = ROOT / "manifests" / "qsigma_r6i_coherent_dilation_preregistration.json"
OUT = ROOT / "artifacts" / "r6i_coherent_dilation"
RESULT = OUT / "coherent_dilation.json"
ENVELOPE = OUT / "coherent_dilation.envelope.json"


def _canonical_json(path: Path, payload: dict) -> None:
    path.write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True, default=float) + "\n").encode("utf-8")
    )


def _coordinate_digest(coordinates) -> str:
    payload = json.dumps(coordinates, separators=(",", ":"), sort_keys=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dft(dimension: int) -> np.ndarray:
    indices = np.arange(dimension)
    return np.exp(2j * math.pi * np.outer(indices, indices) / dimension) / math.sqrt(
        dimension
    )


def _padding(states, extra: int = 3):
    dimension = states[0].shape[0]
    padded = []
    for state in states:
        expanded = np.zeros((dimension + extra, dimension + extra), dtype=complex)
        expanded[:dimension, :dimension] = state
        padded.append(expanded)
    return padded


def _invariance_controls() -> dict:
    r6, coherent, coordinates = matched_codebooks(2.0, 32)
    baseline = ensemble_information(coherent)
    permuted = ensemble_information(list(reversed(coherent)))
    unitary = _dft(coherent[0].shape[0])
    conjugated = ensemble_information(
        [unitary @ state @ unitary.conj().T for state in coherent]
    )
    padded = ensemble_information(_padding(coherent))
    return {
        "frozen_source_digest": _coordinate_digest(coordinates),
        "r6_count": len(r6),
        "coherent_count": len(coherent),
        "permutation_chi_residual": abs(permuted["chi"] - baseline["chi"]),
        "permutation_pgm_residual": abs(permuted["I_PGM"] - baseline["I_PGM"]),
        "gauge_chi_residual": abs(conjugated["chi"] - baseline["chi"]),
        "gauge_pgm_residual": abs(conjugated["I_PGM"] - baseline["I_PGM"]),
        "padding_chi_residual": abs(padded["chi"] - baseline["chi"]),
        "padding_pgm_residual": abs(padded["I_PGM"] - baseline["I_PGM"]),
    }


def run() -> dict:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    depths = tuple(float(value) for value in prereg["frozen_grid"]["depths"])
    sizes = tuple(int(value) for value in prereg["frozen_grid"]["codebook_sizes"])
    tolerance = float(prereg["frozen_grid"]["numerical_tolerance"])
    margin = float(prereg["frozen_grid"]["decision_margin_bits"])
    if margin != RESCUE_MARGIN_BITS:
        raise RuntimeError("implementation margin does not match preregistration")

    rows = []
    input_hashes = []
    maximum_unitarity_residual = 0.0
    maximum_density_residual = 0.0
    minimum_density_eigenvalue = math.inf
    all_density_states_valid = True
    r6_ceiling_holds = True

    for rho in depths:
        for n in sizes:
            r6, coherent, coordinates = matched_codebooks(rho, n)
            input_hashes.append(_coordinate_digest(coordinates))
            r6_information = ensemble_information(r6)
            coherent_information = ensemble_information(coherent)
            ceiling = holevo_ceiling(rho)
            r6_ceiling_holds &= r6_information["chi"] <= ceiling + tolerance

            for point, state in zip(coordinates, coherent):
                matrix = to_sl2(swirl_point(*point))
                unitary = halmos_dilation(normalised_contraction(matrix))
                residual = float(
                    np.linalg.norm(
                        unitary.conj().T @ unitary - np.eye(unitary.shape[0]), "fro"
                    )
                )
                maximum_unitarity_residual = max(maximum_unitarity_residual, residual)
                diagnostics = density_state_diagnostics(state, tolerance)
                maximum_density_residual = max(
                    maximum_density_residual,
                    diagnostics["hermiticity_residual"],
                    abs(diagnostics["trace_real"] - 1.0),
                    abs(diagnostics["trace_imag"]),
                    abs(diagnostics["purity"] - 1.0),
                )
                minimum_density_eigenvalue = min(
                    minimum_density_eigenvalue, diagnostics["minimum_eigenvalue"]
                )
                all_density_states_valid &= bool(diagnostics["valid"])

            rows.append(
                {
                    "rho": rho,
                    "n": n,
                    "source_digest": input_hashes[-1],
                    "r6": r6_information,
                    "coherent_dilation": coherent_information,
                    "r6_analytic_ceiling": ceiling,
                    "chi_improvement": coherent_information["chi"]
                    - r6_information["chi"],
                    "pgm_improvement": coherent_information["I_PGM"]
                    - r6_information["I_PGM"],
                }
            )

    invariance = _invariance_controls()
    composition_defects = [
        composition_defect((0.3, 0.2, -0.1), (0.5, -0.4, 0.7)),
        composition_defect((1.0, -0.3, 0.9), (0.7, 0.6, -0.2)),
        composition_defect((2.0, 0.1, 0.4), (0.2, -0.7, 1.1)),
    ]
    controls = {
        "same_source_count": all(
            row["r6"]["n_codewords"] == row["coherent_dilation"]["n_codewords"]
            for row in rows
        ),
        "unitarity": maximum_unitarity_residual <= tolerance,
        "density_states": all_density_states_valid,
        "permutation_invariance": max(
            invariance["permutation_chi_residual"],
            invariance["permutation_pgm_residual"],
        )
        <= tolerance,
        "common_unitary_gauge_invariance": max(
            invariance["gauge_chi_residual"], invariance["gauge_pgm_residual"]
        )
        <= tolerance,
        "passive_padding_invariance": max(
            invariance["padding_chi_residual"], invariance["padding_pgm_residual"]
        )
        <= tolerance,
        "r6_analytic_ceiling": bool(r6_ceiling_holds),
        "composition_defect_measured": all(
            math.isfinite(value) and value >= 0.0 for value in composition_defects
        ),
    }
    controls = {name: bool(value) for name, value in controls.items()}
    decision = classify_rescue(rows, margin=margin)
    if not all(controls.values()):
        decision = {**decision, "verdict": "HOLD", "control_override": True}

    return {
        "schema": "hypercomplexbrain.r6i.coherent-dilation.v1",
        "round": "QSigma-R6i",
        "preregistration": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "preregistration_sha256": file_digest(PREREG),
        "rows": rows,
        "decision": decision,
        "controls": controls,
        "control_diagnostics": {
            **invariance,
            "maximum_unitarity_residual": maximum_unitarity_residual,
            "maximum_density_residual": maximum_density_residual,
            "minimum_density_eigenvalue": minimum_density_eigenvalue,
            "composition_defects": composition_defects,
        },
        "scope": {
            "map_specific": True,
            "point_encoding_not_representation": bool(
                max(composition_defects, default=0.0) > tolerance
            ),
            "quantum_advantage_claim": False,
            "asymptotic_capacity_claim": False,
            "hardware_claim": False,
            "cognition_claim": False,
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = run()
    _canonical_json(RESULT, report)
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6I-COHERENT-DILATION",
        evidence_tag="M",
        command="python experiments/run_coherent_dilation.py",
        observed_result={
            "sample_size": len(report["rows"]),
            "verdict": report["decision"]["verdict"],
            "controls": report["controls"],
            "rescue_depths": report["decision"].get("rescue_depths", []),
            "map_specific": True,
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[],
        input_hashes=sorted(set(row["source_digest"] for row in report["rows"])),
        raw_artifacts={
            "artifacts/r6i_coherent_dilation/coherent_dilation.json": file_digest(RESULT),
            "experiments/run_coherent_dilation.py": file_digest(
                ROOT / "experiments" / "run_coherent_dilation.py"
            ),
            "manifests/qsigma_r6i_coherent_dilation_preregistration.json": file_digest(
                PREREG
            ),
            "src/aionq/coherent_dilation.py": file_digest(
                ROOT / "src" / "aionq" / "coherent_dilation.py"
            ),
            "tests/test_coherent_dilation.py": file_digest(
                ROOT / "tests" / "test_coherent_dilation.py"
            ),
        },
        environment_dependent=["eigendecomposition", "matrix square root", "PGM"],
        producer="experiments/run_coherent_dilation.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {
                "kind": "representation_remainder",
                "carrier": "composition law",
                "comparison": (
                    "the Halmos block is a pointwise unitary dilation. A nonzero "
                    "composition defect forbids treating it as a finite-dimensional "
                    "unitary representation of SL(2,R)"
                ),
            },
            {
                "kind": "capacity_remainder",
                "carrier": "finite frozen ensembles",
                "comparison": (
                    "Holevo chi upper-bounds accessible information and PGM is one "
                    "achievable lower bound; this is not a regularized capacity result"
                ),
            },
            {
                "kind": "scope_remainder",
                "carrier": "one coherent-dilation map",
                "comparison": (
                    "either verdict applies to this map and frozen grid only; it "
                    "does not prove a general fixed-width rescue or impossibility"
                ),
            },
        ],
    )
    save_envelope(envelope, ENVELOPE)
    # ``save_envelope`` is semantically UTF-8 but currently opens text with the
    # platform newline default. Commit canonical LF bytes for digest stability.
    ENVELOPE.write_bytes(
        ENVELOPE.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    )
    print(
        json.dumps(
            {
                "verdict": report["decision"]["verdict"],
                "controls": report["controls"],
                "rescue_depths": report["decision"].get("rescue_depths", []),
                "rows": len(report["rows"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if all(report["controls"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
