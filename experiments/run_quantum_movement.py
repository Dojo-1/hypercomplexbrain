#!/usr/bin/env python3
"""Append-once execution of the frozen QSigma-R8 quantum-movement round.

The runner keeps the two declared carriers separate.  Source pseudo-volume is
reported as a typed source quantity; operational information is reported in
bits on the five-dimensional Bell-erasure density family.  No arithmetic in
this file adds, averages, or ranks those carriers against one another.

This file deliberately contains no tuning surface.  The path, thresholds,
finite-difference step, postprocessing channel, tolerances, controls, and H1
verdict rule are loaded from the preregistration whose exact digest is bound
below.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.evidence import (  # noqa: E402
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    verify,
)
from aionq.governance import GovernanceError  # noqa: E402
from aionq.hyperbolic_qubit import q22, swirl_point  # noqa: E402
from aionq.qsigma_r7_information import (  # noqa: E402
    InvalidOperationalMetric,
    bell_codeword,
    compact_su2,
    information_metrics,
    reject_split_form_distance,
    trace_distance,
)
from aionq.quantities import Bits, IncommensurableError  # noqa: E402
from aionq.quantum_movement import (  # noqa: E402
    QuantumMovement,
    QuantumMovementOmniTool,
    RankChangeBoundary,
    SourceMovement,
    analytic_qfi_q,
    analytic_qfi_rho,
    build_quantum_polycosmos,
    bures_qfi_finite_difference,
    cocycle_identity_defect,
    compact_frame,
    compose_word,
    density_root_fidelity,
    depolarize_density,
    echo_transport,
    normalization_cocycle,
    pairwise_quantum_geometry,
    qfi_volume_exact,
    qfi_volume_numeric,
)
from aionq.recognition.worldlet import Geometry  # noqa: E402

PREREG = ROOT / "manifests" / "qsigma_r8_quantum_movement_preregistration.json"
PREREG_SHA256 = (
    "409344240b5042c72f7ca3b4102a50c991595784a88ca7c018cf7fac46490d62"
)
SOURCE = ROOT / "src" / "aionq" / "quantum_movement.py"
WORLDLET_SOURCE = ROOT / "src" / "aionq" / "recognition" / "worldlet.py"
R7_SOURCE = ROOT / "src" / "aionq" / "qsigma_r7_information.py"
R6_SOURCE = ROOT / "src" / "aionq" / "hyperbolic_qubit.py"
QUANTITY_SOURCE = ROOT / "src" / "aionq" / "quantities.py"
TEST = ROOT / "tests" / "test_quantum_movement.py"
RUNNER = Path(__file__).resolve()
OUT_DIR = ROOT / "artifacts" / "r8_quantum_movement"
OUT = OUT_DIR / "quantum_movement.json"
ENVELOPE = OUT_DIR / "quantum_movement.envelope.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _density_digest(density: np.ndarray) -> str:
    value = np.asarray(density, dtype="<c16")
    return "sha256:" + hashlib.sha256(value.tobytes(order="C")).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    """Write stable JSON and refuse NaN/Infinity rather than laundering them."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _frozen_manifest() -> dict:
    observed = _sha256(PREREG)
    if observed != PREREG_SHA256:
        raise RuntimeError(
            "frozen QSigma-R8 preregistration changed: "
            f"{observed} != {PREREG_SHA256}"
        )
    return json.loads(PREREG.read_text(encoding="utf-8"))


def _finite(value: float) -> bool:
    return math.isfinite(float(value))


def _control(
    identifier: str,
    name: str,
    passed: bool,
    metrics: dict,
    gate: str,
) -> dict:
    return {
        "id": identifier,
        "name": name,
        "passed": bool(passed),
        "gate": gate,
        "metrics": metrics,
    }


def _quantity_payload(quantity) -> dict:
    return {
        "kind": type(quantity).__name__,
        "value": float(quantity.value),
        "unit": quantity.unit,
        "base": quantity.base,
        "uncertainty": float(quantity.uncertainty),
    }


def _typed_remainder_payload(remainder) -> dict:
    return {
        "kind": remainder.remainder_type,
        "carrier": remainder.carrier,
        "comparison": remainder.metric_or_comparison,
        "raw_value": float(remainder.raw_value),
        "assumptions": list(remainder.assumptions),
        "provenance": remainder.provenance,
    }


def _metrics_payload(metrics) -> dict:
    return {
        "pgm_mutual_information_bits": float(metrics.pgm_mutual_information),
        "holevo_information_bits": float(metrics.holevo_information),
        "oracle_erasure_information_bits": float(
            metrics.oracle_erasure_information
        ),
        "log2_codewords_bits": float(metrics.log2_codewords),
        "catalogue_proxy_not_bits": float(metrics.catalogue_proxy),
        "minimum_success_probability": float(
            metrics.minimum_success_probability
        ),
        "pgm_maximum_row_defect": float(metrics.pgm_maximum_row_defect),
        "pgm_minimum_raw_probability": float(
            metrics.pgm_minimum_raw_probability
        ),
        "pgm_support_projector_defect": float(
            metrics.pgm_support_projector_defect
        ),
        "confusion_digest": metrics.confusion_digest,
    }


def _pair_payload(pair) -> dict:
    return {
        "trace_distance": float(pair.trace_distance),
        "dense_trace_distance": float(pair.dense_trace_distance),
        "root_fidelity": float(pair.root_fidelity),
        "dense_root_fidelity": float(pair.dense_root_fidelity),
        "bures_squared": float(pair.bures_squared),
        "helstrom_equal_prior_error": float(
            pair.helstrom_equal_prior_error
        ),
        "fuchs_lower": float(pair.fuchs_lower),
        "fuchs_upper": float(pair.fuchs_upper),
    }


def _density_family_qfi(
    point: Sequence[float],
    density_factory: Callable[[np.ndarray], np.ndarray],
    step: float,
) -> np.ndarray:
    """Independent Bures finite-difference reconstruction for frame controls."""
    point = np.asarray(point, dtype=float)
    basis = np.eye(3)

    def directional(direction: np.ndarray) -> float:
        lower = density_factory(point - step * direction)
        upper = density_factory(point + step * direction)
        fidelity = density_root_fidelity(lower, upper)
        return max(0.0, 2.0 * (1.0 - fidelity) / (step * step))

    output = np.zeros((3, 3), dtype=float)
    for axis in range(3):
        output[axis, axis] = directional(basis[axis])
    for left in range(3):
        for right in range(left):
            pair = directional(basis[left] + basis[right])
            value = (
                pair - output[left, left] - output[right, right]
            ) / 2.0
            output[left, right] = output[right, left] = value
    return output


def _run_controls(manifest: dict, tool: QuantumMovementOmniTool, trace) -> dict:
    grid = manifest["frozen_grid"]
    algebra_tolerance = float(grid["algebra_tolerance"])
    density_tolerance = float(grid["density_tolerance"])
    qfi_tolerance = float(grid["qfi_relative_tolerance"])
    step = float(grid["finite_difference_step"])
    path = [tuple(map(float, item)) for item in grid["path"]]
    controls: dict[str, dict] = {}

    # C1: bind the new seam back to the exact R6/R7 source and density laws.
    binding_rows = []
    sign_alias_errors = []
    for rho, phi, psi in path:
        source = SourceMovement.from_coordinates(rho, phi, psi)
        quantum = QuantumMovement.from_source(source)
        point = swirl_point(rho, phi, psi)
        expected_singular = np.array([math.exp(rho), math.exp(-rho)])
        observed_singular = np.array(source.singular_values)
        density = quantum.codeword.density
        signed = bell_codeword(-source.matrix)
        sign_alias_errors.append(
            float(np.max(np.abs(density - signed.density)))
        )
        binding_rows.append(
            {
                "rho": rho,
                "q22_error": abs(q22(point) - 1.0),
                "determinant_error": abs(
                    float(np.linalg.det(source.matrix)) - 1.0
                ),
                "singular_value_max_error": float(
                    np.max(np.abs(observed_singular - expected_singular))
                ),
                "volume_density_error": abs(
                    source.volume_density.value
                    - math.cosh(rho) * math.sinh(rho)
                ),
                "slab_volume_error": abs(
                    source.slab_volume.value
                    - 2.0 * math.pi**2 * math.sinh(rho) ** 2
                ),
                "bell_success_error": abs(
                    quantum.bell_success_probability
                    - (1.0 + math.exp(-4.0 * rho)) / 2.0
                ),
                "worst_success_error": abs(
                    quantum.worst_success_probability
                    - math.exp(-4.0 * rho)
                ),
                "density_trace_error": abs(
                    float(np.trace(density).real) - 1.0
                ),
                "density_min_eigenvalue": float(
                    np.min(np.linalg.eigvalsh(density))
                ),
            }
        )
    split_form_rejected = False
    try:
        reject_split_form_distance(np.zeros(4), np.ones(4))
    except InvalidOperationalMetric:
        split_form_rejected = True
    info = trace.information.metrics
    information_order = (
        info.pgm_mutual_information
        <= info.holevo_information + algebra_tolerance
        <= info.oracle_erasure_information + 2.0 * algebra_tolerance
        <= info.log2_codewords + 3.0 * algebra_tolerance
    )
    c1_error = max(
        max(
            row[key]
            for key in (
                "q22_error",
                "determinant_error",
                "singular_value_max_error",
                "volume_density_error",
                "slab_volume_error",
                "bell_success_error",
                "worst_success_error",
                "density_trace_error",
            )
        )
        for row in binding_rows
    )
    c1_min_eigenvalue = min(
        row["density_min_eigenvalue"] for row in binding_rows
    )
    controls["C1"] = _control(
        "C1",
        "R7 and R6 binding",
        (
            c1_error <= algebra_tolerance
            and c1_min_eigenvalue >= -density_tolerance
            and max(sign_alias_errors) <= density_tolerance
            and split_form_rejected
            and information_order
        ),
        {
            "rows": binding_rows,
            "max_exact_error": c1_error,
            "minimum_density_eigenvalue": c1_min_eigenvalue,
            "projective_sign_alias_max_error": max(sign_alias_errors),
            "split_form_rejected_as_distance": split_form_rejected,
            "information_sandwich": information_order,
        },
        manifest["controls"][0]["gate"],
    )

    # C2: algebra-valued density geometry is checked against dense spectra.
    pair_rows = []
    for previous, current in zip(
        trace.observations[:-1], trace.observations[1:]
    ):
        pair = pairwise_quantum_geometry(
            previous.quantum.codeword, current.quantum.codeword
        )
        pair_rows.append(
            {
                "from_index": previous.index,
                "to_index": current.index,
                **_pair_payload(pair),
                "trace_closed_dense_error": abs(
                    pair.trace_distance - pair.dense_trace_distance
                ),
                "fidelity_closed_dense_error": abs(
                    pair.root_fidelity - pair.dense_root_fidelity
                ),
                "fuchs_pass": (
                    pair.trace_distance + algebra_tolerance >= pair.fuchs_lower
                    and pair.trace_distance <= pair.fuchs_upper + algebra_tolerance
                ),
                "helstrom_pass": (
                    abs(
                        pair.helstrom_equal_prior_error
                        - (1.0 - pair.trace_distance) / 2.0
                    )
                    <= algebra_tolerance
                ),
            }
        )
    controls["C2"] = _control(
        "C2",
        "dense versus closed pair geometry",
        (
            max(row["trace_closed_dense_error"] for row in pair_rows)
            <= algebra_tolerance
            and max(row["fidelity_closed_dense_error"] for row in pair_rows)
            <= algebra_tolerance
            and all(row["fuchs_pass"] for row in pair_rows)
            and all(row["helstrom_pass"] for row in pair_rows)
        ),
        {"pairs": pair_rows},
        manifest["controls"][1]["gate"],
    )

    # C3: reconstruct the full symmetric QFI rather than one scalar shadow.
    qfi_rows = []
    for rho in map(float, grid["qfi_finite_difference_rho"]):
        analytic = analytic_qfi_rho(rho)
        numerical = bures_qfi_finite_difference(
            rho,
            float(grid["base_phi"]),
            float(grid["base_psi"]),
            step=step,
        )
        relative_error = float(
            np.linalg.norm(numerical - analytic, ord="fro")
            / max(np.linalg.norm(analytic, ord="fro"), 1e-15)
        )
        qfi_rows.append(
            {
                "rho": rho,
                "analytic": analytic.tolist(),
                "numerical": numerical.tolist(),
                "relative_frobenius_error": relative_error,
                "analytic_eigenvalues": np.linalg.eigvalsh(analytic).tolist(),
                "numerical_eigenvalues": np.linalg.eigvalsh(numerical).tolist(),
            }
        )
    controls["C3"] = _control(
        "C3",
        "QFI reconstruction",
        max(row["relative_frobenius_error"] for row in qfi_rows)
        <= qfi_tolerance,
        {
            "finite_difference_step": step,
            "relative_tolerance": qfi_tolerance,
            "rows": qfi_rows,
        },
        manifest["controls"][2]["gate"],
    )

    # C4: rho=0 is a rank-changing boundary, not an interior SLD point.
    boundary_rejected = False
    try:
        analytic_qfi_rho(0.0)
    except RankChangeBoundary:
        boundary_rejected = True
    boundary_source = SourceMovement.from_coordinates(
        0.0, float(grid["base_phi"]), float(grid["base_psi"])
    )
    boundary_quantum = QuantumMovement.from_source(boundary_source)
    boundary_neighbour = QuantumMovement.from_source(
        SourceMovement.from_coordinates(
            10.0 * step,
            float(grid["base_phi"]),
            float(grid["base_psi"]),
        )
    )
    boundary_pair = pairwise_quantum_geometry(
        boundary_quantum.codeword, boundary_neighbour.codeword
    )
    boundary_finite = all(
        _finite(value)
        for value in (
            boundary_pair.trace_distance,
            boundary_pair.root_fidelity,
            boundary_pair.bures_squared,
        )
    )
    controls["C4"] = _control(
        "C4",
        "rank-changing boundary",
        (
            boundary_rejected
            and boundary_quantum.rank_change_boundary
            and boundary_quantum.qfi_rho is None
            and boundary_quantum.qfi_q is None
            and boundary_finite
        ),
        {
            "interior_qfi_rejected_at_rho_zero": boundary_rejected,
            "rank_change_boundary": boundary_quantum.rank_change_boundary,
            "finite_boundary_pair": _pair_payload(boundary_pair),
        },
        manifest["controls"][3]["gate"],
    )

    # C5: compactify rho to q without confusing coordinate sensitivity with loss.
    interior = [float(value) for value in grid["interior_rho"]]
    q_values = [math.exp(-2.0 * rho) for rho in interior]
    high_left, high_right = 4.0, 6.0
    radial_log_slope = (
        math.log(float(analytic_qfi_rho(high_right)[0, 0]))
        - math.log(float(analytic_qfi_rho(high_left)[0, 0]))
    ) / (high_right - high_left)
    q_near_zero = math.exp(-2.0 * max(interior))
    q_metric_near_zero = analytic_qfi_q(q_near_zero)
    numeric_volume = qfi_volume_numeric()
    exact_volume = qfi_volume_exact()
    volume_error = abs(numeric_volume - exact_volume)
    volume_tolerance = float(grid["volume_integral_absolute_tolerance"])
    controls["C5"] = _control(
        "C5",
        "coordinate compactification",
        (
            all(left > right for left, right in zip(q_values[:-1], q_values[1:]))
            and abs(radial_log_slope + 4.0) <= 0.02
            and np.all(np.isfinite(q_metric_near_zero))
            and abs(float(q_metric_near_zero[0, 0]) - 2.0) <= 1e-8
            and volume_error <= volume_tolerance
        ),
        {
            "rho": interior,
            "q": q_values,
            "J_rhorho_high_depth_log_slope": radial_log_slope,
            "expected_slope": -4.0,
            "q_near_zero": q_near_zero,
            "J_q_near_zero": q_metric_near_zero.tolist(),
            "qfi_volume_numeric": numeric_volume,
            "qfi_volume_exact": exact_volume,
            "qfi_volume_absolute_error": volume_error,
            "source_slab_growth_exponent": 2.0,
        },
        manifest["controls"][4]["gate"],
    )

    # C6: the norm removed at each prefix is an explicit two-cocycle cost.
    composition_sources = [
        SourceMovement.from_coordinates(*map(float, coordinates))
        for coordinates in grid["composition_coordinates"]
    ]
    matrices = [item.matrix for item in composition_sources]
    kappas = [
        normalization_cocycle(matrices[index], matrices[index + 1])
        for index in range(len(matrices) - 1)
    ]
    word = compose_word(matrices)
    cocycle_defect = cocycle_identity_defect(*matrices)
    stream_identity_error = abs(
        word.streamed_success_probability
        - word.transmissivity * word.direct_success_probability
    )
    transmissivity_error = abs(
        word.transmissivity - math.exp(-2.0 * word.kappa)
    )
    controls["C6"] = _control(
        "C6",
        "normalization cocycle",
        (
            min(kappas + [word.kappa]) >= -algebra_tolerance
            and cocycle_defect <= algebra_tolerance
            and word.normalized_product_defect <= algebra_tolerance
            and stream_identity_error <= algebra_tolerance
            and transmissivity_error <= algebra_tolerance
        ),
        {
            "pair_kappa": kappas,
            "word_kappa": word.kappa,
            "eta": word.transmissivity,
            "cocycle_identity_defect": cocycle_defect,
            "normalized_product_defect": word.normalized_product_defect,
            "direct_success": word.direct_success_probability,
            "streamed_success": word.streamed_success_probability,
            "stream_identity_error": stream_identity_error,
            "transmissivity_error": transmissivity_error,
        },
        manifest["controls"][5]["gate"],
    )

    # C7: a source inverse word returns exactly but pays attempted-use survival.
    echo_rows = []
    for rho in map(float, grid["echo_rho"]):
        source = SourceMovement.from_coordinates(
            rho, float(grid["base_phi"]), float(grid["base_psi"])
        )
        echo = echo_transport(source.matrix)
        echo_rows.append(
            {
                "rho": rho,
                "source_return_defect": echo.source_return_defect,
                "conditional_return_fidelity": echo.conditional_return_fidelity,
                "direct_success_probability": echo.direct_success_probability,
                "streamed_success_probability": echo.streamed_success_probability,
                "expected_streamed_success_probability": (
                    echo.expected_streamed_success_probability
                ),
                "streamed_success_error": abs(
                    echo.streamed_success_probability
                    - echo.expected_streamed_success_probability
                ),
                "kappa": echo.kappa,
            }
        )
    generic_echo = echo_transport(np.diag([2.0, 1.0]))
    generic_echo_identity_error = abs(
        generic_echo.expected_streamed_success_probability
        - math.exp(-2.0 * generic_echo.kappa)
        * generic_echo.direct_success_probability
    )
    controls["C7"] = _control(
        "C7",
        "source echo versus attempted survival",
        (
            max(row["source_return_defect"] for row in echo_rows)
            <= algebra_tolerance
            and max(
                abs(row["conditional_return_fidelity"] - 1.0)
                for row in echo_rows
            )
            <= algebra_tolerance
            and max(
                abs(row["direct_success_probability"] - 1.0)
                for row in echo_rows
            )
            <= algebra_tolerance
            and max(row["streamed_success_error"] for row in echo_rows)
            <= algebra_tolerance
            and generic_echo.source_return_defect <= algebra_tolerance
            and abs(
                generic_echo.streamed_success_probability
                - generic_echo.expected_streamed_success_probability
            )
            <= algebra_tolerance
            and generic_echo_identity_error <= algebra_tolerance
        ),
        {
            "echoes": echo_rows,
            "generic_invertible_control": {
                "matrix": [[2.0, 0.0], [0.0, 1.0]],
                "expected_law": "exp(-2*kappa)*p_direct",
                "echo": {
                    "rho": generic_echo.rho,
                    "kappa": generic_echo.kappa,
                    "source_return_defect": (
                        generic_echo.source_return_defect
                    ),
                    "direct_success_probability": (
                        generic_echo.direct_success_probability
                    ),
                    "streamed_success_probability": (
                        generic_echo.streamed_success_probability
                    ),
                    "expected_streamed_success_probability": (
                        generic_echo.expected_streamed_success_probability
                    ),
                    "identity_error": generic_echo_identity_error,
                },
            },
            "deweave_used_as_inverse": False,
        },
        manifest["controls"][6]["gate"],
    )

    # C8: a declared CPTP post-channel may contract, never manufacture signal.
    depolarizing_strength = float(grid["depolarizing_strength"])
    post_rows = []
    for previous, current in zip(
        trace.observations[:-1], trace.observations[1:]
    ):
        before_distance = trace_distance(
            previous.quantum.codeword.density, current.quantum.codeword.density
        )
        before_fidelity = density_root_fidelity(
            previous.quantum.codeword.density, current.quantum.codeword.density
        )
        previous_post = depolarize_density(
            previous.quantum.codeword.density, depolarizing_strength
        )
        current_post = depolarize_density(
            current.quantum.codeword.density, depolarizing_strength
        )
        after_distance = trace_distance(previous_post, current_post)
        after_fidelity = density_root_fidelity(previous_post, current_post)
        post_rows.append(
            {
                "from_index": previous.index,
                "to_index": current.index,
                "trace_before": before_distance,
                "trace_after": after_distance,
                "trace_contraction": before_distance - after_distance,
                "fidelity_before": before_fidelity,
                "fidelity_after": after_fidelity,
                "fidelity_increase": after_fidelity - before_fidelity,
            }
        )
    qfi_post_rows = []
    for rho in map(float, grid["qfi_finite_difference_rho"]):
        input_qfi = bures_qfi_finite_difference(
            rho,
            float(grid["base_phi"]),
            float(grid["base_psi"]),
            step=step,
        )
        output_qfi = bures_qfi_finite_difference(
            rho,
            float(grid["base_phi"]),
            float(grid["base_psi"]),
            step=step,
            channel=lambda density: depolarize_density(
                density, depolarizing_strength
            ),
        )
        difference = (output_qfi - input_qfi)
        difference = (difference + difference.T) / 2.0
        maximum_violation = float(np.max(np.linalg.eigvalsh(difference)))
        allowed = qfi_tolerance * max(
            1.0, float(np.linalg.norm(input_qfi, ord=2))
        )
        qfi_post_rows.append(
            {
                "rho": rho,
                "input_qfi": input_qfi.tolist(),
                "output_qfi": output_qfi.tolist(),
                "maximum_loewner_violation": maximum_violation,
                "numerical_allowance": allowed,
            }
        )
    controls["C8"] = _control(
        "C8",
        "CPTP data processing",
        (
            min(row["trace_contraction"] for row in post_rows)
            >= -algebra_tolerance
            and min(row["fidelity_increase"] for row in post_rows)
            >= -algebra_tolerance
            and all(
                row["maximum_loewner_violation"]
                <= row["numerical_allowance"]
                for row in qfi_post_rows
            )
        ),
        {
            "depolarizing_strength": depolarizing_strength,
            "pairs": post_rows,
            "qfi": qfi_post_rows,
        },
        manifest["controls"][7]["gate"],
    )

    # C9: common compact frames are covariance, not a free radial register.
    left_frame_angle = float(grid["base_phi"])
    right_frame_angle = -float(grid["base_psi"])
    left_frame = compact_frame(left_frame_angle)
    right_frame = compact_frame(right_frame_angle)
    original_words = [
        observation.quantum.codeword for observation in trace.observations
    ]
    framed_words = [
        bell_codeword(left_frame @ observation.source.matrix @ right_frame)
        for observation in trace.observations
    ]
    frame_success_error = max(
        abs(left.success_probability - right.success_probability)
        for left, right in zip(original_words, framed_words)
    )
    frame_pair_errors = []
    for left_index in range(len(original_words) - 1):
        original_pair = pairwise_quantum_geometry(
            original_words[left_index], original_words[left_index + 1]
        )
        framed_pair = pairwise_quantum_geometry(
            framed_words[left_index], framed_words[left_index + 1]
        )
        frame_pair_errors.append(
            {
                "from_index": left_index,
                "to_index": left_index + 1,
                "trace_error": abs(
                    original_pair.trace_distance - framed_pair.trace_distance
                ),
                "fidelity_error": abs(
                    original_pair.root_fidelity - framed_pair.root_fidelity
                ),
            }
        )
    original_info = information_metrics(original_words)
    framed_info = information_metrics(framed_words)
    frame_holevo_error = abs(
        original_info.holevo_information - framed_info.holevo_information
    )
    qfi_point = np.array(
        [1.0, float(grid["base_phi"]), float(grid["base_psi"])],
        dtype=float,
    )
    original_frame_qfi = _density_family_qfi(
        qfi_point,
        lambda coordinates: bell_codeword(
            SourceMovement.from_coordinates(*coordinates.tolist()).matrix
        ).density,
        step,
    )
    attacked_frame_qfi = _density_family_qfi(
        qfi_point,
        lambda coordinates: bell_codeword(
            left_frame
            @ SourceMovement.from_coordinates(*coordinates.tolist()).matrix
            @ right_frame
        ).density,
        step,
    )
    qfi_spectrum_error = float(
        np.max(
            np.abs(
                np.linalg.eigvalsh(original_frame_qfi)
                - np.linalg.eigvalsh(attacked_frame_qfi)
            )
        )
    )
    qfi_spectrum_allowance = qfi_tolerance * max(
        1.0, float(np.max(np.linalg.eigvalsh(original_frame_qfi)))
    )
    compact_rows = []
    for rho in map(float, grid["interior_rho"]):
        compact_word = bell_codeword(
            compact_su2(
                2.0 * math.atan(rho),
                float(grid["base_phi"]),
                float(grid["base_psi"]),
            )
        )
        compact_rows.append(
            {
                "rho_parameter": rho,
                "density_shape": list(compact_word.density.shape),
                "success_probability": compact_word.success_probability,
                "unitarity_error": float(
                    np.linalg.norm(
                        compact_word.encoded_matrix.conj().T
                        @ compact_word.encoded_matrix
                        - np.eye(2),
                        ord="fro",
                    )
                ),
            }
        )
    controls["C9"] = _control(
        "C9",
        "compact frame and matched compact family",
        (
            frame_success_error <= algebra_tolerance
            and max(
                max(row["trace_error"], row["fidelity_error"])
                for row in frame_pair_errors
            )
            <= algebra_tolerance
            and frame_holevo_error <= algebra_tolerance
            and qfi_spectrum_error <= qfi_spectrum_allowance
            and all(row["density_shape"] == [5, 5] for row in compact_rows)
            and max(
                abs(row["success_probability"] - 1.0)
                for row in compact_rows
            )
            <= algebra_tolerance
            and max(row["unitarity_error"] for row in compact_rows)
            <= algebra_tolerance
        ),
        {
            "left_SO2_angle": left_frame_angle,
            "right_SO2_angle": right_frame_angle,
            "success_max_error": frame_success_error,
            "pair_errors": frame_pair_errors,
            "holevo_error_bits": frame_holevo_error,
            "qfi_spectrum_max_error": qfi_spectrum_error,
            "qfi_spectrum_numerical_allowance": qfi_spectrum_allowance,
            "matched_compact_SU2": compact_rows,
        },
        manifest["controls"][8]["gate"],
    )

    # C10: the AION seam remains heterogeneous and its loss is typed.
    if tool.polycosmos is None:
        raise RuntimeError("OmniTool path did not construct a Polycosmos")
    polycosmos = tool.polycosmos
    bridge = next(iter(polycosmos.tendrils.values()))
    quantity_bits_refused = False
    try:
        _ = trace.observations[-1].source.volume_density >= trace.information.holevo
    except IncommensurableError:
        quantity_bits_refused = True
    expected_geometries = {
        Geometry.SL2_ABSOLUTE_PSEUDO_VOLUME,
        Geometry.DENSITY_OPERATOR_BURES,
    }
    mismatched_sections_refused = False
    try:
        build_quantum_polycosmos(
            SourceMovement.from_coordinates(*path[0]),
            QuantumMovement.from_source(
                SourceMovement.from_coordinates(*path[1])
            ),
        )
    except GovernanceError:
        mismatched_sections_refused = True
    controls["C10"] = _control(
        "C10",
        "typed AION seam",
        (
            polycosmos.geometries == expected_geometries
            and bool(bridge.preserved_fields)
            and bool(bridge.transformed_fields)
            and bool(bridge.lost_fields)
            and bridge.transport_cost >= 0.0
            and bridge.typed_remainder is not None
            and bridge.return_transport is None
            and bool(bridge.return_absent_reason)
            and quantity_bits_refused
            and mismatched_sections_refused
        ),
        {
            "worldlets": {
                identifier: {
                    "carrier": worldlet.carrier,
                    "geometry": worldlet.local_geometry,
                    "algebra_regime": worldlet.algebra_regime,
                    "clocks": list(worldlet.clocks),
                }
                for identifier, worldlet in polycosmos.worldlets.items()
            },
            "tendril": {
                "id": bridge.id,
                "source": bridge.source,
                "target": bridge.target,
                "preserved": list(bridge.preserved_fields),
                "transformed": list(bridge.transformed_fields),
                "lost": list(bridge.lost_fields),
                "cost": float(bridge.transport_cost),
                "typed_remainder": _typed_remainder_payload(
                    bridge.typed_remainder
                ),
                "return_transport": None,
                "return_absent_reason": bridge.return_absent_reason,
            },
            "source_quantity_vs_operational_bits_refused": quantity_bits_refused,
            "mismatched_local_sections_refused": mismatched_sections_refused,
        },
        manifest["controls"][9]["gate"],
    )

    # C11: routing is append-only governance; it is never the echo inverse.
    empty_reason_refused = False
    fresh = QuantumMovementOmniTool(
        weave_trace_threshold=float(grid["weave_trace_threshold"])
    )
    fresh.observe(*path[0])
    try:
        fresh.deweave("")
    except GovernanceError:
        empty_reason_refused = True
    second_trace_refused = False
    try:
        tool.observe_path(path)
    except GovernanceError:
        second_trace_refused = True
    materialized_prefix_refused = False
    prefix_probe = QuantumMovementOmniTool(
        weave_trace_threshold=float(grid["weave_trace_threshold"])
    )
    try:
        prefix_probe.observe(
            *path[0], materialization_mode="materialized_prefix"
        )
    except ValueError:
        materialized_prefix_refused = True
    controls["C11"] = _control(
        "C11",
        "weave/deweave history",
        (
            empty_reason_refused
            and second_trace_refused
            and materialized_prefix_refused
            and len(trace.events) == len(trace.observations) == len(path)
            and all(event.reason for event in trace.events)
            and all(not event.physical_inverse for event in trace.events)
        ),
        {
            "empty_deweave_reason_refused": empty_reason_refused,
            "second_append_refused": second_trace_refused,
            "materialized_prefix_refused_until_compose_word_telemetry": (
                materialized_prefix_refused
            ),
            "observations": len(trace.observations),
            "events": len(trace.events),
            "physical_inverse_event_count": sum(
                event.physical_inverse for event in trace.events
            ),
            "echo_transport_implemented_through_deweave": False,
        },
        manifest["controls"][10]["gate"],
    )

    # C12: bind all implementation surfaces and keep information ordered.
    required_sources = (
        PREREG,
        SOURCE,
        WORLDLET_SOURCE,
        R7_SOURCE,
        R6_SOURCE,
        QUANTITY_SOURCE,
        TEST,
        RUNNER,
    )
    sources_present = all(path.exists() for path in required_sources)
    source_digests = (
        {_relative(path): file_digest(path) for path in required_sources}
        if sources_present
        else {
            _relative(path): (
                file_digest(path) if path.exists() else "MISSING"
            )
            for path in required_sources
        }
    )
    c12_information_order = (
        trace.information.pgm.value
        <= trace.information.holevo.value + algebra_tolerance
        <= trace.information.oracle_erasure.value + 2.0 * algebra_tolerance
        <= trace.information.log2_codewords.value + 3.0 * algebra_tolerance
    )
    controls["C12"] = _control(
        "C12",
        "information and evidence",
        (
            sources_present
            and _sha256(PREREG) == PREREG_SHA256
            and c12_information_order
        ),
        {
            "information": {
                "pgm": _quantity_payload(trace.information.pgm),
                "holevo": _quantity_payload(trace.information.holevo),
                "oracle_erasure": _quantity_payload(
                    trace.information.oracle_erasure
                ),
                "log2_codewords": _quantity_payload(
                    trace.information.log2_codewords
                ),
                "ordered": c12_information_order,
            },
            "source_digests": source_digests,
            "preregistration_sha256": f"sha256:{PREREG_SHA256}",
            "result_path": _relative(OUT),
            "envelope_path": _relative(ENVELOPE),
            "local_envelope_verification": (
                "required after immutable result emission; failure raises"
            ),
            "independent_witness": False,
        },
        manifest["controls"][11]["gate"],
    )
    return controls


def _observation_payload(observation) -> dict:
    quantum = observation.quantum
    source = observation.source
    transport = observation.transport
    return {
        "index": observation.index,
        "coordinates": {
            "rho": source.rho,
            "phi": source.phi,
            "psi": source.psi,
            "q": quantum.q,
        },
        "source_carrier": {
            "matrix": source.matrix.tolist(),
            "singular_values": list(source.singular_values),
            "absolute_pseudo_volume_density": _quantity_payload(
                source.volume_density
            ),
            "absolute_pseudo_slab_volume": _quantity_payload(
                source.slab_volume
            ),
            "used_as_operational_distance": False,
            "used_as_bits": False,
        },
        "operational_carrier": {
            "density_digest": _density_digest(quantum.codeword.density),
            "density_eigenvalues": np.linalg.eigvalsh(
                quantum.codeword.density
            ).tolist(),
            "density_dimension": int(quantum.codeword.density.shape[0]),
            "bell_success_probability": quantum.bell_success_probability,
            "erasure_probability": 1.0 - quantum.bell_success_probability,
            "worst_success_probability": quantum.worst_success_probability,
            "qfi_rho": (
                None if quantum.qfi_rho is None else quantum.qfi_rho.tolist()
            ),
            "qfi_q": None if quantum.qfi_q is None else quantum.qfi_q.tolist(),
            "qfi_volume_density": _quantity_payload(quantum.qfi_volume),
            "source_to_qfi_volume_form_distortion": (
                None
                if quantum.volume_form_distortion is None
                else _quantity_payload(quantum.volume_form_distortion)
            ),
            "fixed_bell_bipartition": {
                "conditional_concurrence": quantum.conditional_concurrence,
                "conditional_entanglement": _quantity_payload(
                    quantum.conditional_entanglement
                ),
                "identity_invariant": False,
            },
            "rank_change_boundary": quantum.rank_change_boundary,
        },
        "transport": {
            "edge": transport.edge,
            "preserved": list(transport.preserved),
            "transformed": list(transport.transformed),
            "lost": list(transport.lost),
            "cost": float(transport.cost),
            "typed_remainder": _typed_remainder_payload(transport.remainder),
            "evidence": transport.evidence,
        },
        "transition": (
            None
            if observation.transition is None
            else _pair_payload(observation.transition)
        ),
        "routing": {
            "action": observation.event.action,
            "reason": observation.event.reason,
            "trace_distance": observation.event.trace_distance,
            "evidence_tag": observation.event.evidence_tag,
            "physical_inverse": observation.event.physical_inverse,
        },
        "materialization_mode": observation.materialization_mode,
        "frame_id": observation.frame_id,
    }


def _h1_verdict(trace) -> dict:
    radial_deweaves = []
    boundary_angular_weaves = []
    for previous, current in zip(
        trace.observations[:-1], trace.observations[1:]
    ):
        same_angles = (
            previous.source.phi == current.source.phi
            and previous.source.psi == current.source.psi
        )
        if (
            same_angles
            and current.source.rho >= 6.0
            and current.event.action == "deweave"
        ):
            radial_deweaves.append(current.index)
        angular = (
            previous.source.rho == current.source.rho == 6.0
            and (
                previous.source.phi != current.source.phi
                or previous.source.psi != current.source.psi
            )
        )
        if angular and current.event.action == "weave":
            boundary_angular_weaves.append(current.index)
    survives = bool(radial_deweaves and boundary_angular_weaves)
    return {
        "id": "H1",
        "verdict": "SURVIVES" if survives else "FALSIFIED",
        "high_depth_fixed_angle_radial_deweave_indices": radial_deweaves,
        "rho6_boundary_angular_weave_indices": boundary_angular_weaves,
        "rule": (
            "SURVIVES iff both a high-depth fixed-angle radial deweave and "
            "a rho=6 boundary angular weave occur on the frozen path"
        ),
        "scope": "frozen routing-policy behavior only",
    }


def main() -> int:
    if OUT.exists() or ENVELOPE.exists():
        raise FileExistsError(
            "QSigma-R8 outputs already exist; the frozen run is append-once"
        )
    manifest = _frozen_manifest()
    grid = manifest["frozen_grid"]
    tool = QuantumMovementOmniTool(
        weave_trace_threshold=float(grid["weave_trace_threshold"])
    )
    trace = tool.observe_path(grid["path"])
    controls = _run_controls(manifest, tool, trace)
    control_failures = [
        identifier
        for identifier, result in controls.items()
        if not result["passed"]
    ]
    h1 = _h1_verdict(trace)
    status = (
        "COMPLETED"
        if not control_failures
        else "VOID_EXACT_OR_TYPED_CONTROL"
    )

    observations = [
        _observation_payload(observation)
        for observation in trace.observations
    ]
    density_hashes = [
        item["operational_carrier"]["density_digest"]
        for item in observations
    ]
    source_digests = controls["C12"]["metrics"]["source_digests"]
    transport_remainders = [
        item["transport"]["typed_remainder"] for item in observations
    ]
    payload = {
        "schema": "hypercomplexbrain.qsigma_r8.quantum_movement.v1",
        "round": "QSigma-R8",
        "status": status,
        "preregistration": {
            "path": _relative(PREREG),
            "sha256": f"sha256:{PREREG_SHA256}",
            "status": manifest["status"],
        },
        "architecture_binding": manifest["architecture_binding"],
        "source_digests": source_digests,
        "formulas": {
            "source_absolute_pseudo_volume_density": "cosh(rho)*sinh(rho)",
            "source_slab_volume": "2*pi^2*sinh(R)^2",
            "operational_coordinate": "q=exp(-2*rho)",
            "bell_success": "p=(1+q^2)/2",
            "worst_success": "p_worst=q^2",
            "qfi_rho": (
                "diag(8/(exp(4rho)-1),(1+exp(-2rho))^2,"
                "(1-exp(-2rho))^2)"
            ),
            "qfi_q": "diag(2/(1-q^2),(1+q)^2,(1-q)^2)",
            "qfi_total_volume": "sqrt(2)*pi^3",
            "volume_form_distortion": (
                "8*sqrt(2)*exp(-4rho)/sqrt(1-exp(-4rho))"
            ),
            "normalization_cocycle": (
                "kappa(X,Y)=log||X||2+log||Y||2-log||XY||2"
            ),
            "streamed_success": (
                "p_stream=exp(-2*kappa_word)*p_direct"
            ),
            "pair_trace_distance": (
                "0.5*(sqrt((pA+pB)^2-4*abs(c)^2)+abs(pA-pB))"
            ),
            "pair_root_fidelity": (
                "abs(c)+sqrt((1-pA)*(1-pB))"
            ),
        },
        "carrier_contract": {
            "source": manifest["carrier_contract"]["source"],
            "operational": manifest["carrier_contract"]["operational"],
            "bridge": manifest["carrier_contract"]["bridge"],
            "common_scalar_score": None,
        },
        "movement": {
            "path": grid["path"],
            "observations": observations,
            "events": [
                {
                    "index": event.index,
                    "action": event.action,
                    "reason": event.reason,
                    "trace_distance": event.trace_distance,
                    "evidence_tag": event.evidence_tag,
                    "physical_inverse": event.physical_inverse,
                }
                for event in trace.events
            ],
            "ambient_source_slab_extent": _quantity_payload(
                trace.ambient_source_slab_extent
            ),
            "operational_information": {
                "codewords": trace.information.codewords,
                "pgm": _quantity_payload(trace.information.pgm),
                "holevo": _quantity_payload(trace.information.holevo),
                "oracle_erasure": _quantity_payload(
                    trace.information.oracle_erasure
                ),
                "log2_codewords": _quantity_payload(
                    trace.information.log2_codewords
                ),
                "raw_metrics": _metrics_payload(trace.information.metrics),
            },
        },
        "controls": controls,
        "control_failures": control_failures,
        "hypotheses": {"H1": h1},
        "verdicts": {
            **{
                prediction["id"]: (
                    "SURVIVES" if not control_failures else "VOID"
                )
                for prediction in manifest["exact_predictions"]
            },
            "H1": h1["verdict"],
            "overall": status,
        },
        "typed_remainders": {
            "transport": transport_remainders,
            "projective_loss": {
                "kind": "scalar_constant",
                "carrier": "SL2-to-density projective fibre",
                "comparison": "projective alias multiplicity minus one",
                "raw_value": 1.0,
                "statement": "M and -M share one density",
            },
            "attenuation_not_loss": {
                "carrier": "operational radial coordinate",
                "statement": (
                    "At every finite rho, exact tomography recovers "
                    "q=exp(-2rho); fixed additive delta-rho sensitivity decays."
                ),
            },
            "nontransported_aggregate": {
                "carrier": "SL(2,R) source measure",
                "statement": (
                    "Cartan source-volume multiplicity is not a density-state "
                    "field, codeword count, information quantity, or capacity."
                ),
            },
            "routing": {
                "evidence_tag": "S",
                "statement": (
                    "weave/deweave is append-only governance state and never a "
                    "physical inverse or recovery channel"
                ),
            },
            "independence": {
                "statement": "No independent witness.",
                "independent": False,
            },
        },
        "interpretation": {
            "bounded_result": (
                "One exact Bell-erasure attempted-use instrument on one frozen "
                "finite path, with a typed AION weave/deweave telemetry trace."
            ),
            "source_growth": (
                "The source slab has exponent two; it remains source measure."
            ),
            "operational_movement": (
                "The five-dimensional density family is read through trace, "
                "fidelity, Bures, QFI, and finite-ensemble information."
            ),
            "coordinate_caveat": (
                "Fixed delta-rho sensitivity decays at high depth while q is a "
                "regular compactified coordinate; this is not literal deletion "
                "of every finite-rho distinction."
            ),
            "evidence_ceiling": manifest["evidence_ceiling"],
        },
        "excluded_claims": manifest["kill_conditions"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT, payload)
    envelope = EvidenceEnvelope(
        claim_id="QSIGMA-R8-QUANTUM-MOVEMENT",
        evidence_tag="M",
        command="python experiments/run_quantum_movement.py",
        observed_result={
            "status": status,
            "sample_size": len(set(density_hashes)),
            "path_observations": len(observations),
            "controls_passed": len(controls) - len(control_failures),
            "controls_total": len(controls),
            "H1": h1["verdict"],
            "independent": False,
            "interval": "deterministic frozen path; no sampling interval",
        },
        commit_sha=current_commit(ROOT),
        working_directory=".",
        platform=platform.system().lower(),
        environment=environment_digest(),
        input_hashes=sorted(set(density_hashes)),
        seeds=[],
        raw_artifacts={_relative(OUT): file_digest(OUT)},
        uncertainty={
            "scope": "one fixed Bell-erasure attempted-use instrument",
            "routing": "S-tier frozen threshold policy",
            "qfi": "interior finite-difference reconstruction; rho=0 excluded",
            "capacity": "not optimized or claimed",
            "infinite_dimension": "not implemented",
            "independence": False,
        },
        producer="codex-gpt5.6",
        verifier="",
        timestamp="",
        signature_status="unsigned",
        typed_remainders=[
            {
                "kind": "projective_loss",
                "carrier": "SL2-to-density fibre",
                "statement": "M and -M share one density",
            },
            {
                "kind": "conditioning",
                "carrier": "q=exp(-2rho)",
                "statement": (
                    "finite-rho recoverability does not imply fixed-shot "
                    "additive-rho resolution"
                ),
            },
            {
                "kind": "scope",
                "carrier": "evidence boundary",
                "statement": (
                    "no channel-capacity, hardware, advantage, memory, "
                    "cognition, consciousness, or AGI claim"
                ),
            },
        ],
        verification_mode="not_requested",
    )
    _write_json(ENVELOPE, envelope.to_dict())
    check = verify(envelope, repo_root=ROOT)
    if not check.ok:
        raise RuntimeError(
            "local EvidenceEnvelope verification failed: "
            + "; ".join(check.failures)
        )

    print(status)
    print(
        f"controls={len(controls) - len(control_failures)}/{len(controls)} "
        f"H1={h1['verdict']} independent={check.independent}"
    )
    print(
        "source_volume_and_operational_bits_common_scalar=False "
        f"envelope_verified={check.ok}"
    )
    print(OUT)
    return 0 if status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
