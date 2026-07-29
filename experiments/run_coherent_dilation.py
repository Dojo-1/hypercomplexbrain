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
    composition_defect_matrices,
    density_state_diagnostics,
    dilation_diagnostics,
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
PREREG = ROOT / "manifests" / "qsigma_r6i_coherent_dilation_preregistration.json"
CORRECTION = (
    ROOT / "manifests" / "qsigma_r6i_coherent_dilation_correction.json"
)
OUT = ROOT / "artifacts" / "r6i_coherent_dilation"
RESULT = OUT / "coherent_dilation.json"
ENVELOPE = OUT / "coherent_dilation.envelope.json"
ATTEMPT1 = OUT / "coherent_dilation.attempt1_eigh.json"


def _canonical_json(path: Path, payload: dict) -> None:
    path.write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True, default=float) + "\n").encode("utf-8")
    )


def _coordinate_digest(coordinates) -> str:
    payload = json.dumps(coordinates, separators=(",", ":"), sort_keys=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _matrix_digest(matrices) -> str:
    digest = hashlib.sha256()
    for matrix in matrices:
        array = np.asarray(matrix, dtype="<c16", order="C")
        digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
        digest.update(array.tobytes(order="C"))
    return "sha256:" + digest.hexdigest()


def _dft(dimension: int) -> np.ndarray:
    indices = np.arange(dimension)
    return np.exp(2j * math.pi * np.outer(indices, indices) / dimension) / math.sqrt(
        dimension
    )


def _padding(states, extra: int = 3, *, target_dimension: int | None = None):
    dimension = states[0].shape[0]
    output_dimension = (
        dimension + extra if target_dimension is None else target_dimension
    )
    if output_dimension < dimension:
        raise ValueError("padding target cannot be smaller than the source")
    padded = []
    for state in states:
        expanded = np.zeros((output_dimension, output_dimension), dtype=complex)
        expanded[:dimension, :dimension] = state
        padded.append(expanded)
    return padded


def _information_residuals(prefix: str, baseline: dict, candidate: dict) -> dict:
    return {
        f"{prefix}_chi_residual": abs(candidate["chi"] - baseline["chi"]),
        f"{prefix}_pgm_residual": abs(
            candidate["I_PGM"] - baseline["I_PGM"]
        ),
        f"{prefix}_mean_rank_residual": abs(
            candidate["mean_state_rank"] - baseline["mean_state_rank"]
        ),
    }


def _invariance_controls(r6, coherent, tolerance: float) -> dict:
    output: dict[str, float | bool] = {}
    for name, states, padded in (
        ("r6", r6, _padding(r6, target_dimension=16)),
        ("coherent", coherent, _padding(coherent)),
    ):
        baseline = ensemble_information(states, tol=tolerance)
        permuted = ensemble_information(list(reversed(states)), tol=tolerance)
        unitary = _dft(states[0].shape[0])
        conjugated = ensemble_information(
            [unitary @ state @ unitary.conj().T for state in states],
            tol=tolerance,
        )
        padded_metrics = ensemble_information(padded, tol=tolerance)
        output.update(
            _information_residuals(
                f"{name}_permutation", baseline, permuted
            )
        )
        output.update(
            _information_residuals(f"{name}_common_unitary", baseline, conjugated)
        )
        output.update(
            _information_residuals(f"{name}_passive_padding", baseline, padded_metrics)
        )
        output[f"{name}_invariance_numerically_valid"] = bool(
            baseline["numerically_valid"]
            and permuted["numerically_valid"]
            and conjugated["numerically_valid"]
            and padded_metrics["numerically_valid"]
        )
    return output


def _attempt_comparison(rows: list[dict]) -> dict:
    attempt1 = json.loads(ATTEMPT1.read_text(encoding="utf-8"))
    earlier = {
        (float(row["rho"]), int(row["n"])): row
        for row in attempt1["rows"]
    }
    current = {(float(row["rho"]), int(row["n"])): row for row in rows}
    if set(earlier) != set(current):
        return {
            "comparable": False,
            "reason": "attempt grids differ",
        }
    fields = {
        "r6_chi": lambda row: row["r6"]["chi"],
        "r6_pgm": lambda row: row["r6"]["I_PGM"],
        "coherent_chi": lambda row: row["coherent_dilation"]["chi"],
        "coherent_pgm": lambda row: row["coherent_dilation"]["I_PGM"],
    }
    return {
        "comparable": True,
        "maximum_absolute_metric_delta": {
            name: max(
                abs(float(selector(current[key])) - float(selector(earlier[key])))
                for key in current
            )
            for name, selector in fields.items()
        },
        "attempt1_verdict": attempt1["decision"]["verdict"],
    }


def run() -> dict:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    correction = json.loads(CORRECTION.read_text(encoding="utf-8"))
    depths = tuple(float(value) for value in prereg["frozen_grid"]["depths"])
    sizes = tuple(int(value) for value in prereg["frozen_grid"]["codebook_sizes"])
    tolerance = float(prereg["frozen_grid"]["numerical_tolerance"])
    margin = float(prereg["frozen_grid"]["decision_margin_bits"])
    if margin != RESCUE_MARGIN_BITS:
        raise RuntimeError("implementation margin does not match preregistration")

    expected_attempt1_digest = correction["first_attempt"]["sha256"]
    observed_attempt1_digest = file_digest(ATTEMPT1)

    entries = []
    maximum_left_unitarity_residual = 0.0
    maximum_right_unitarity_residual = 0.0
    maximum_intertwining_residual = 0.0
    maximum_coherent_density_residual = 0.0
    maximum_r6_density_residual = 0.0
    minimum_density_eigenvalue = math.inf
    all_coherent_density_states_valid = True
    all_r6_density_states_valid = True
    all_source_counts_match = True
    maximum_matrix_sign_residual = 0.0
    maximum_r6_sign_alias_residual = 0.0
    maximum_sign_overlap_residual = 0.0
    maximum_sign_fidelity_residual = 0.0

    # Structural preflight. No Holevo or PGM metric is evaluated in this loop.
    for rho in depths:
        for n in sizes:
            r6, coherent, coordinates, matrices = matched_codebooks(rho, n)
            coordinate_hash = _coordinate_digest(coordinates)
            matrix_hash = _matrix_digest(matrices)
            all_source_counts_match &= (
                len(r6)
                == len(coherent)
                == len(coordinates)
                == len(matrices)
                == n
            )

            unitaries = []
            for matrix, r6_state, coherent_state in zip(matrices, r6, coherent):
                contraction = normalised_contraction(matrix)
                unitary = halmos_dilation(contraction)
                unitaries.append(unitary)
                dilation = dilation_diagnostics(
                    contraction, unitary, tol=tolerance
                )
                maximum_left_unitarity_residual = max(
                    maximum_left_unitarity_residual,
                    dilation["left_unitarity_residual"],
                )
                maximum_right_unitarity_residual = max(
                    maximum_right_unitarity_residual,
                    dilation["right_unitarity_residual"],
                )
                maximum_intertwining_residual = max(
                    maximum_intertwining_residual,
                    dilation["intertwining_residual"],
                )

                diagnostics = density_state_diagnostics(
                    coherent_state, tolerance, require_pure=True
                )
                maximum_coherent_density_residual = max(
                    maximum_coherent_density_residual,
                    diagnostics["hermiticity_residual"],
                    abs(diagnostics["trace_real"] - 1.0),
                    abs(diagnostics["trace_imag"]),
                    abs(diagnostics["purity"] - 1.0),
                )
                minimum_density_eigenvalue = min(
                    minimum_density_eigenvalue, diagnostics["minimum_eigenvalue"]
                )
                all_coherent_density_states_valid &= bool(diagnostics["valid"])

                r6_diagnostics = density_state_diagnostics(
                    r6_state, tolerance, require_pure=False
                )
                maximum_r6_density_residual = max(
                    maximum_r6_density_residual,
                    r6_diagnostics["hermiticity_residual"],
                    abs(r6_diagnostics["trace_real"] - 1.0),
                    abs(r6_diagnostics["trace_imag"]),
                )
                minimum_density_eigenvalue = min(
                    minimum_density_eigenvalue,
                    r6_diagnostics["minimum_eigenvalue"],
                )
                all_r6_density_states_valid &= bool(r6_diagnostics["valid"])

            pair_diagnostics = []
            expected_overlap = -math.exp(-4.0 * rho)
            expected_fidelity = math.exp(-8.0 * rho)
            for index in range(n // 2):
                other = index + n // 2
                matrix_residual = float(
                    np.linalg.norm(matrices[other] + matrices[index], "fro")
                )
                r6_residual = float(
                    np.linalg.norm(r6[other] - r6[index], "fro")
                )
                overlap = complex(
                    np.trace(unitaries[index].conj().T @ unitaries[other])
                    / unitaries[index].shape[0]
                )
                fidelity = float(
                    np.real(np.trace(coherent[index] @ coherent[other]))
                )
                maximum_matrix_sign_residual = max(
                    maximum_matrix_sign_residual, matrix_residual
                )
                maximum_r6_sign_alias_residual = max(
                    maximum_r6_sign_alias_residual, r6_residual
                )
                maximum_sign_overlap_residual = max(
                    maximum_sign_overlap_residual,
                    abs(overlap - expected_overlap),
                )
                maximum_sign_fidelity_residual = max(
                    maximum_sign_fidelity_residual,
                    abs(fidelity - expected_fidelity),
                )
                pair_diagnostics.append(
                    {
                        "pair": [index, other],
                        "matrix_sign_residual": matrix_residual,
                        "r6_alias_residual": r6_residual,
                        "coherent_overlap_real": float(np.real(overlap)),
                        "coherent_overlap_imag": float(np.imag(overlap)),
                        "expected_overlap": expected_overlap,
                        "coherent_density_fidelity": fidelity,
                        "expected_density_fidelity": expected_fidelity,
                    }
                )

            entries.append(
                {
                    "rho": rho,
                    "n": n,
                    "coordinates": coordinates,
                    "coordinate_digest": coordinate_hash,
                    "matrix_digest": matrix_hash,
                    "r6": r6,
                    "coherent": coherent,
                    "sign_pairs": pair_diagnostics,
                }
            )

    preflight_controls = {
        "attempt1_trace_bound": observed_attempt1_digest
        == expected_attempt1_digest,
        "same_exact_source_matrices": bool(all_source_counts_match),
        "two_sided_unitarity": max(
            maximum_left_unitarity_residual,
            maximum_right_unitarity_residual,
        )
        <= tolerance,
        "defect_intertwining": maximum_intertwining_residual <= tolerance,
        "coherent_density_states": all_coherent_density_states_valid,
        "r6_density_states": all_r6_density_states_valid,
        "central_sign_matrix_identity": maximum_matrix_sign_residual <= tolerance,
        "r6_central_sign_alias": maximum_r6_sign_alias_residual <= tolerance,
        "coherent_sign_overlap_identity": max(
            maximum_sign_overlap_residual,
            maximum_sign_fidelity_residual,
        )
        <= tolerance,
    }
    preflight_controls = {
        name: bool(value) for name, value in preflight_controls.items()
    }
    if not all(preflight_controls.values()):
        return {
            "schema": "hypercomplexbrain.r6i.coherent-dilation.v2",
            "round": "QSigma-R6i",
            "preregistration": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
            "correction_ledger": str(CORRECTION.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "rows": [],
            "decision": {
                "verdict": "HOLD",
                "grid_valid": False,
                "rescue_depths": [],
                "hold_reasons": ["structural preflight failed"],
            },
            "controls": preflight_controls,
            "primary_metrics_status": "void_preflight_failed",
            "control_diagnostics": {
                "maximum_left_unitarity_residual": (
                    maximum_left_unitarity_residual
                ),
                "maximum_right_unitarity_residual": (
                    maximum_right_unitarity_residual
                ),
                "maximum_intertwining_residual": (
                    maximum_intertwining_residual
                ),
            },
            "execution_history": [
                {
                    "attempt": 1,
                    "artifact": str(ATTEMPT1.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": observed_attempt1_digest,
                    "status": "invalidated_numerical_implementation",
                }
            ],
            "scope": {"map_specific": True},
        }

    # Primary metrics are revealed only after every structural preflight passes.
    rows = []
    r6_ceiling_holds = True
    all_information_numerics_valid = True
    for entry in entries:
        rho = entry["rho"]
        n = entry["n"]
        r6_information = ensemble_information(entry["r6"], tol=tolerance)
        coherent_information = ensemble_information(
            entry["coherent"], tol=tolerance
        )
        all_information_numerics_valid &= bool(
            r6_information["numerically_valid"]
            and coherent_information["numerically_valid"]
        )
        ceiling = holevo_ceiling(rho)
        r6_ceiling_holds &= r6_information["chi"] <= ceiling + tolerance

        half = n // 2
        sign_quotiented_r6 = ensemble_information(
            entry["r6"][:half], tol=tolerance
        )
        sign_quotiented_coherent = ensemble_information(
            entry["coherent"][:half], tol=tolerance
        )
        rows.append(
            {
                "rho": rho,
                "n": n,
                "source_coordinate_digest": entry["coordinate_digest"],
                "source_matrix_digest": entry["matrix_digest"],
                "r6": r6_information,
                "coherent_dilation": coherent_information,
                "r6_analytic_ceiling": ceiling,
                "chi_improvement": coherent_information["chi"]
                - r6_information["chi"],
                "pgm_improvement": coherent_information["I_PGM"]
                - r6_information["I_PGM"],
                "central_sign_pairs": entry["sign_pairs"],
                "posthoc_sign_quotiented_half_grid": {
                    "decision_impact": False,
                    "r6": sign_quotiented_r6,
                    "coherent_dilation": sign_quotiented_coherent,
                    "chi_improvement": sign_quotiented_coherent["chi"]
                    - sign_quotiented_r6["chi"],
                    "pgm_improvement": sign_quotiented_coherent["I_PGM"]
                    - sign_quotiented_r6["I_PGM"],
                },
            }
        )

    frozen_control = next(
        entry
        for entry in entries
        if entry["rho"] == 2.0 and entry["n"] == 32
    )
    invariance = _invariance_controls(
        frozen_control["r6"],
        frozen_control["coherent"],
        tolerance,
    )
    composition_defects = [
        composition_defect((0.3, 0.2, -0.1), (0.5, -0.4, 0.7)),
        composition_defect((1.0, -0.3, 0.9), (0.7, 0.6, -0.2)),
        composition_defect((2.0, 0.1, 0.4), (0.2, -0.7, 1.1)),
    ]
    identity_composition_defect = composition_defect_matrices(
        np.eye(2), np.eye(2)
    )
    invariance_residuals = [
        float(value)
        for name, value in invariance.items()
        if name.endswith("_residual")
    ]
    controls = {
        **preflight_controls,
        "pgm_and_information_numerics": all_information_numerics_valid,
        "permutation_invariance": max(
            (
                value
                for name, value in invariance.items()
                if "permutation" in name and name.endswith("_residual")
            ),
            default=math.inf,
        )
        <= tolerance,
        "common_unitary_gauge_invariance": max(
            (
                value
                for name, value in invariance.items()
                if "common_unitary" in name and name.endswith("_residual")
            ),
            default=math.inf,
        )
        <= tolerance,
        "passive_padding_invariance": max(
            (
                value
                for name, value in invariance.items()
                if "passive_padding" in name and name.endswith("_residual")
            ),
            default=math.inf,
        )
        <= tolerance,
        "invariance_pgm_guards": all(
            bool(value)
            for name, value in invariance.items()
            if name.endswith("_numerically_valid")
        ),
        "r6_analytic_ceiling": bool(r6_ceiling_holds),
        "composition_defect_measured": bool(
            all(
                math.isfinite(value) and value > tolerance
                for value in composition_defects
            )
        ),
        "identity_composition_known_answer": abs(
            identity_composition_defect - 2.0 * math.sqrt(2.0)
        )
        <= tolerance,
    }
    controls = {name: bool(value) for name, value in controls.items()}
    if all_information_numerics_valid:
        decision = classify_rescue(
            rows,
            margin=margin,
            expected_depths=depths,
            expected_sizes=sizes,
        )
    else:
        decision = {
            "verdict": "HOLD",
            "margin_bits": margin,
            "large_sizes": [64, 100, 256],
            "rescue_depths": [],
            "grid_valid": False,
            "hold_reasons": ["PGM or information-ordering numerical guard failed"],
        }
    if not all(controls.values()):
        decision = {
            **decision,
            "verdict": "HOLD",
            "control_override": True,
            "failed_controls": [
                name for name, value in controls.items() if not value
            ],
        }

    return {
        "schema": "hypercomplexbrain.r6i.coherent-dilation.v2",
        "round": "QSigma-R6i",
        "preregistration": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "preregistration_sha256": file_digest(PREREG),
        "correction_ledger": str(CORRECTION.relative_to(ROOT)).replace("\\", "/"),
        "correction_ledger_sha256": file_digest(CORRECTION),
        "primary_metrics_status": (
            "eligible_for_frozen_classifier"
            if all_information_numerics_valid
            else "void_numerical_guard_failure"
        ),
        "rows": rows,
        "decision": decision,
        "controls": controls,
        "control_diagnostics": {
            **invariance,
            "maximum_invariance_residual": max(
                invariance_residuals, default=0.0
            ),
            "maximum_left_unitarity_residual": (
                maximum_left_unitarity_residual
            ),
            "maximum_right_unitarity_residual": (
                maximum_right_unitarity_residual
            ),
            "maximum_intertwining_residual": maximum_intertwining_residual,
            "maximum_coherent_density_residual": (
                maximum_coherent_density_residual
            ),
            "maximum_r6_density_residual": maximum_r6_density_residual,
            "minimum_density_eigenvalue": minimum_density_eigenvalue,
            "maximum_matrix_sign_residual": maximum_matrix_sign_residual,
            "maximum_r6_sign_alias_residual": (
                maximum_r6_sign_alias_residual
            ),
            "maximum_sign_overlap_residual": maximum_sign_overlap_residual,
            "maximum_sign_fidelity_residual": maximum_sign_fidelity_residual,
            "composition_defects": composition_defects,
            "identity_composition_defect": identity_composition_defect,
            "active_carrier_dimensions": {"r6": 5, "coherent_dilation": 16},
        },
        "execution_history": [
            {
                "attempt": 1,
                "artifact": str(ATTEMPT1.relative_to(ROOT)).replace("\\", "/"),
                "sha256": observed_attempt1_digest,
                "status": "invalidated_numerical_implementation",
                "reason": correction["first_attempt"]["reason"],
            },
            {
                "attempt": 2,
                "status": "corrected_shared_svd_execution",
                "comparison_to_attempt1": _attempt_comparison(rows),
            },
        ],
        "scope": {
            "map_specific": True,
            "point_encoding_not_representation": bool(
                max(composition_defects, default=0.0) > tolerance
            ),
            "quantum_advantage_claim": False,
            "asymptotic_capacity_claim": False,
            "hardware_claim": False,
            "cognition_claim": False,
            "central_sign_interpretation": (
                "the candidate lifts the M versus -M projective alias of R6; "
                "this is not a generic fixed-width capacity claim"
            ),
            "completion_gauge_nonunique": True,
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    envelope_only = "--envelope-only" in sys.argv[1:]
    if envelope_only:
        report = json.loads(RESULT.read_text(encoding="utf-8"))
    else:
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
        # One digest per frozen ensemble: the concrete matrices are the actual
        # encoder inputs and already subsume the separately reported coordinates.
        # Counting both hashes would falsely double n_eff from 36 to 72.
        input_hashes=sorted(
            {row["source_matrix_digest"] for row in report["rows"]}
        ),
        raw_artifacts={
            "artifacts/r6i_coherent_dilation/coherent_dilation.json": file_digest(RESULT),
            "artifacts/r6i_coherent_dilation/coherent_dilation.attempt1_eigh.json": (
                file_digest(ATTEMPT1)
            ),
            "experiments/run_coherent_dilation.py": file_digest(
                ROOT / "experiments" / "run_coherent_dilation.py"
            ),
            "manifests/qsigma_r6i_coherent_dilation_correction.json": file_digest(
                CORRECTION
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
        environment_dependent=["SVD", "eigendecomposition", "PGM"],
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
            {
                "kind": "central_sign_remainder",
                "carrier": "M versus -M source pairs",
                "comparison": (
                    "R6 aliases every frozen central-sign pair while the canonical "
                    "positive-root dilation separates it with fidelity exp(-8 rho). "
                    "A gain therefore partly restores a projective sign bit."
                ),
            },
            {
                "kind": "completion_gauge_remainder",
                "carrier": "Halmos completion",
                "comparison": (
                    "the positive-root completion is canonical, but completion "
                    "gauges are nonunique. Only a codeword-independent common gauge "
                    "is automatically information preserving."
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
                "mode": "envelope_only" if envelope_only else "primary_execution",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if all(report["controls"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
