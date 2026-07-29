"""Frozen controls for QSigma-R8 dual-carrier quantum movement."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from aionq.governance import GovernanceError
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.qsigma_r7_information import (
    InvalidOperationalMetric,
    bell_codeword,
    compact_su2,
    information_metrics,
    reject_split_form_distance,
    trace_distance,
)
from aionq.quantities import Bits, IncommensurableError
from aionq.quantum_movement import (
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
    qfi_volume_density,
    qfi_volume_exact,
    qfi_volume_numeric,
    source_to_qfi_volume_distortion,
)
from aionq.recognition.worldlet import AlgebraRegime, Geometry


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (ROOT / "manifests" / "qsigma_r8_quantum_movement_preregistration.json")
    .read_text(encoding="utf-8")
)
GRID = MANIFEST["frozen_grid"]
ALGEBRA_TOLERANCE = GRID["algebra_tolerance"]
DENSITY_TOLERANCE = GRID["density_tolerance"]
QFI_RELATIVE_TOLERANCE = GRID["qfi_relative_tolerance"]


def _matrix(coordinates) -> np.ndarray:
    return to_sl2(swirl_point(*coordinates))


def _assert_density(density: np.ndarray) -> None:
    assert density.shape == (5, 5)
    assert np.max(np.abs(density - density.conj().T)) <= DENSITY_TOLERANCE
    assert np.min(np.linalg.eigvalsh(density)) >= -DENSITY_TOLERANCE
    assert np.trace(density).real == pytest.approx(
        1.0, abs=DENSITY_TOLERANCE
    )


def _framed_bures_qfi(
    coordinates: np.ndarray,
    left_frame: np.ndarray,
    right_frame: np.ndarray,
    step: float,
) -> np.ndarray:
    """Independent finite-distance reconstruction after a common SO(2) frame."""

    def density(point: np.ndarray) -> np.ndarray:
        matrix = left_frame @ _matrix(point.tolist()) @ right_frame
        return bell_codeword(matrix).density

    def directional(direction: np.ndarray) -> float:
        lower = density(coordinates - step * direction)
        upper = density(coordinates + step * direction)
        root_fidelity = density_root_fidelity(lower, upper)
        return max(0.0, 2.0 * (1.0 - root_fidelity) / step**2)

    basis = np.eye(3)
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


@pytest.mark.parametrize("rho", [0.0, *GRID["interior_rho"]])
def test_source_and_operational_carriers_obey_exact_r6_bridge(rho):
    source = SourceMovement.from_coordinates(
        rho, GRID["base_phi"], GRID["base_psi"]
    )
    movement = QuantumMovement.from_source(source)
    q = math.exp(-2.0 * rho)

    assert np.linalg.det(source.matrix) == pytest.approx(
        1.0, abs=ALGEBRA_TOLERANCE
    )
    assert source.singular_values == pytest.approx(
        (math.exp(rho), math.exp(-rho)), abs=ALGEBRA_TOLERANCE
    )
    assert source.volume_density.value == pytest.approx(
        math.cosh(rho) * math.sinh(rho), rel=1e-12, abs=1e-12
    )
    assert source.slab_volume.value == pytest.approx(
        2.0 * math.pi**2 * math.sinh(rho) ** 2, rel=1e-12, abs=1e-12
    )
    assert movement.q == pytest.approx(q, abs=ALGEBRA_TOLERANCE)
    assert movement.bell_success_probability == pytest.approx(
        (1.0 + q * q) / 2.0, abs=ALGEBRA_TOLERANCE
    )
    assert movement.worst_success_probability == pytest.approx(
        q * q, abs=ALGEBRA_TOLERANCE
    )
    _assert_density(movement.codeword.density)

    alias = bell_codeword(-source.matrix)
    assert trace_distance(
        movement.codeword.density, alias.density
    ) <= ALGEBRA_TOLERANCE


def test_split_source_form_and_operational_bits_refuse_scalar_collapse():
    source = SourceMovement.from_coordinates(
        1.0, GRID["base_phi"], GRID["base_psi"]
    )
    movement = QuantumMovement.from_source(source)
    with pytest.raises(InvalidOperationalMetric, match="indefinite"):
        reject_split_form_distance(
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
        )
    with pytest.raises(IncommensurableError):
        _ = source.volume_density > movement.conditional_entanglement
    with pytest.raises(IncommensurableError):
        _ = source.slab_volume >= Bits(
            1.0, base="r8-frozen-uniform-path-ensemble"
        )


def test_density_validation_and_rank_change_boundary_are_explicit():
    source = SourceMovement.from_coordinates(
        0.0, GRID["base_phi"], GRID["base_psi"]
    )
    movement = QuantumMovement.from_source(source)
    _assert_density(movement.codeword.density)
    assert movement.rank_change_boundary
    assert movement.qfi_rho is None
    assert movement.qfi_q is None
    assert movement.volume_form_distortion is None

    with pytest.raises(RankChangeBoundary, match="rank"):
        analytic_qfi_rho(0.0)
    with pytest.raises(RankChangeBoundary, match="rank"):
        analytic_qfi_q(1.0)
    with pytest.raises(RankChangeBoundary, match="interior"):
        source_to_qfi_volume_distortion(0.0)
    with pytest.raises(ValueError, match="exceed"):
        bures_qfi_finite_difference(
            GRID["finite_difference_step"],
            GRID["base_phi"],
            GRID["base_psi"],
            step=GRID["finite_difference_step"],
        )

    nearby = QuantumMovement.from_source(
        SourceMovement.from_coordinates(
            2.0 * GRID["finite_difference_step"],
            GRID["base_phi"],
            GRID["base_psi"],
        )
    )
    finite_boundary_probe = pairwise_quantum_geometry(
        movement.codeword, nearby.codeword
    )
    assert math.isfinite(finite_boundary_probe.trace_distance)
    assert math.isfinite(finite_boundary_probe.root_fidelity)

    with pytest.raises(ValueError, match="unit trace"):
        density_root_fidelity(np.eye(5), movement.codeword.density)
    non_positive = np.diag([1.1, -0.1, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="positive semidefinite"):
        density_root_fidelity(non_positive, movement.codeword.density)


@pytest.mark.parametrize(
    "left_coordinates,right_coordinates",
    [
        (GRID["path"][0], GRID["path"][1]),
        (GRID["path"][2], GRID["path"][3]),
        (GRID["path"][6], GRID["path"][7]),
        (GRID["path"][7], GRID["path"][8]),
    ],
)
def test_dense_and_closed_pair_geometry_fuchs_and_helstrom(
    left_coordinates, right_coordinates
):
    left = bell_codeword(_matrix(left_coordinates))
    right = bell_codeword(_matrix(right_coordinates))
    geometry = pairwise_quantum_geometry(left, right)

    assert geometry.trace_distance == pytest.approx(
        geometry.dense_trace_distance, abs=ALGEBRA_TOLERANCE
    )
    assert geometry.root_fidelity == pytest.approx(
        geometry.dense_root_fidelity, abs=ALGEBRA_TOLERANCE
    )
    assert geometry.fuchs_lower <= (
        geometry.trace_distance + ALGEBRA_TOLERANCE
    )
    assert geometry.trace_distance <= (
        geometry.fuchs_upper + ALGEBRA_TOLERANCE
    )
    assert geometry.helstrom_equal_prior_error == pytest.approx(
        (1.0 - geometry.dense_trace_distance) / 2.0,
        abs=ALGEBRA_TOLERANCE,
    )
    assert geometry.bures_squared == pytest.approx(
        2.0 * (1.0 - geometry.dense_root_fidelity),
        abs=ALGEBRA_TOLERANCE,
    )


@pytest.mark.parametrize("rho", GRID["qfi_finite_difference_rho"])
def test_bures_finite_difference_reconstructs_frozen_analytic_qfi(rho):
    analytic = analytic_qfi_rho(rho)
    reconstructed = bures_qfi_finite_difference(
        rho,
        GRID["base_phi"],
        GRID["base_psi"],
        step=GRID["finite_difference_step"],
    )
    analytic_diagonal = np.diag(analytic)
    reconstructed_diagonal = np.diag(reconstructed)

    assert np.all(
        np.abs(reconstructed_diagonal - analytic_diagonal)
        <= QFI_RELATIVE_TOLERANCE * analytic_diagonal
    )
    off_diagonal = reconstructed - np.diag(reconstructed_diagonal)
    assert np.max(np.abs(off_diagonal)) <= (
        QFI_RELATIVE_TOLERANCE * np.max(analytic_diagonal)
    )


def test_q_coordinate_compactification_and_finite_qfi_volume():
    rhos = np.asarray(GRID["interior_rho"], dtype=float)
    qs = np.exp(-2.0 * rhos)
    assert np.all(np.diff(qs) < 0.0)
    assert qs[-1] > 0.0

    rho_left, rho_right = 4.0, 6.0
    j_left = analytic_qfi_rho(rho_left)[0, 0]
    j_right = analytic_qfi_rho(rho_right)[0, 0]
    high_depth_log_slope = (
        math.log(j_right) - math.log(j_left)
    ) / (rho_right - rho_left)
    assert high_depth_log_slope == pytest.approx(-4.0, abs=0.02)
    assert analytic_qfi_q(0.0) == pytest.approx(
        np.diag([2.0, 1.0, 1.0]), abs=ALGEBRA_TOLERANCE
    )

    assert qfi_volume_density(0.0) == pytest.approx(
        0.0, abs=ALGEBRA_TOLERANCE
    )
    assert qfi_volume_numeric() == pytest.approx(
        qfi_volume_exact(),
        abs=GRID["volume_integral_absolute_tolerance"],
    )
    assert qfi_volume_exact() == pytest.approx(
        math.sqrt(2.0) * math.pi**3, abs=ALGEBRA_TOLERANCE
    )
    for rho in GRID["interior_rho"]:
        expected = (
            8.0
            * math.sqrt(2.0)
            * math.exp(-4.0 * rho)
            / math.sqrt(1.0 - math.exp(-4.0 * rho))
        )
        assert source_to_qfi_volume_distortion(rho) == pytest.approx(
            expected, rel=1e-12
        )


def test_normalization_cocycle_and_word_materialization_identities():
    matrices = [_matrix(item) for item in GRID["composition_coordinates"]]
    left, middle, right = matrices
    assert normalization_cocycle(left, middle) >= 0.0
    assert cocycle_identity_defect(
        left, middle, right
    ) <= ALGEBRA_TOLERANCE

    word = compose_word(matrices)
    assert word.kappa >= 0.0
    assert word.transmissivity == pytest.approx(
        math.exp(-2.0 * word.kappa), abs=ALGEBRA_TOLERANCE
    )
    assert word.streamed_success_probability == pytest.approx(
        word.transmissivity * word.direct_success_probability,
        abs=ALGEBRA_TOLERANCE,
    )
    assert word.normalized_product == pytest.approx(
        math.exp(-word.kappa) * word.direct_normalized_product,
        abs=ALGEBRA_TOLERANCE,
    )
    assert word.normalized_product_defect <= ALGEBRA_TOLERANCE
    _assert_density(word.streamed_density)


@pytest.mark.parametrize("rho", GRID["echo_rho"])
def test_source_echo_returns_but_materialized_attempt_survival_is_costed(rho):
    echo = echo_transport(
        _matrix([rho, GRID["base_phi"], GRID["base_psi"]])
    )
    assert echo.rho == pytest.approx(rho, abs=ALGEBRA_TOLERANCE)
    assert echo.source_return_defect <= ALGEBRA_TOLERANCE
    assert echo.conditional_return_fidelity == pytest.approx(
        1.0, abs=ALGEBRA_TOLERANCE
    )
    assert echo.direct_success_probability == pytest.approx(
        1.0, abs=ALGEBRA_TOLERANCE
    )
    assert echo.streamed_success_probability == pytest.approx(
        math.exp(-4.0 * rho), abs=ALGEBRA_TOLERANCE
    )
    assert echo.expected_streamed_success_probability == pytest.approx(
        math.exp(-4.0 * rho), abs=ALGEBRA_TOLERANCE
    )


def test_echo_cost_is_cocycle_derived_for_a_generic_invertible_matrix():
    echo = echo_transport(np.diag([2.0, 1.0]))
    assert echo.source_return_defect <= ALGEBRA_TOLERANCE
    assert echo.expected_streamed_success_probability == pytest.approx(
        math.exp(-2.0 * echo.kappa) * echo.direct_success_probability,
        abs=ALGEBRA_TOLERANCE,
    )
    assert echo.streamed_success_probability == pytest.approx(
        echo.expected_streamed_success_probability,
        abs=ALGEBRA_TOLERANCE,
    )


def test_frozen_depolarizing_channel_obeys_data_processing():
    left = bell_codeword(_matrix(GRID["path"][2]))
    right = bell_codeword(_matrix(GRID["path"][7]))
    strength = GRID["depolarizing_strength"]
    left_post = depolarize_density(left.density, strength)
    right_post = depolarize_density(right.density, strength)

    distance_before = trace_distance(left.density, right.density)
    distance_after = trace_distance(left_post, right_post)
    fidelity_before = density_root_fidelity(left.density, right.density)
    fidelity_after = density_root_fidelity(left_post, right_post)
    assert distance_after <= distance_before + ALGEBRA_TOLERANCE
    assert fidelity_after + ALGEBRA_TOLERANCE >= fidelity_before

    channel = lambda density: depolarize_density(density, strength)
    for rho in GRID["qfi_finite_difference_rho"]:
        input_qfi = analytic_qfi_rho(rho)
        output_qfi = bures_qfi_finite_difference(
            rho,
            GRID["base_phi"],
            GRID["base_psi"],
            step=GRID["finite_difference_step"],
            channel=channel,
        )
        tolerance = QFI_RELATIVE_TOLERANCE * np.max(np.linalg.eigvalsh(input_qfi))
        assert np.min(np.linalg.eigvalsh(input_qfi - output_qfi)) >= -tolerance


def test_common_compact_frames_preserve_probe_geometry_qfi_and_holevo():
    left_frame = compact_frame(0.41)
    right_frame = compact_frame(-0.73)
    assert left_frame.T @ left_frame == pytest.approx(
        np.eye(2), abs=ALGEBRA_TOLERANCE
    )
    assert right_frame.T @ right_frame == pytest.approx(
        np.eye(2), abs=ALGEBRA_TOLERANCE
    )

    coordinates = GRID["composition_coordinates"]
    original_matrices = [_matrix(item) for item in coordinates]
    framed_matrices = [
        left_frame @ matrix @ right_frame for matrix in original_matrices
    ]
    original_words = [bell_codeword(matrix) for matrix in original_matrices]
    framed_words = [bell_codeword(matrix) for matrix in framed_matrices]
    for original, framed, matrix, framed_matrix in zip(
        original_words, framed_words, original_matrices, framed_matrices
    ):
        assert np.linalg.norm(framed_matrix, 2) == pytest.approx(
            np.linalg.norm(matrix, 2), abs=ALGEBRA_TOLERANCE
        )
        assert framed.success_probability == pytest.approx(
            original.success_probability, abs=ALGEBRA_TOLERANCE
        )

    original_pair = pairwise_quantum_geometry(
        original_words[0], original_words[1]
    )
    framed_pair = pairwise_quantum_geometry(framed_words[0], framed_words[1])
    assert framed_pair.trace_distance == pytest.approx(
        original_pair.trace_distance, abs=ALGEBRA_TOLERANCE
    )
    assert framed_pair.root_fidelity == pytest.approx(
        original_pair.root_fidelity, abs=ALGEBRA_TOLERANCE
    )
    assert information_metrics(
        framed_words
    ).holevo_information == pytest.approx(
        information_metrics(original_words).holevo_information,
        abs=ALGEBRA_TOLERANCE,
    )

    point = np.asarray(GRID["path"][2], dtype=float)
    framed_qfi = _framed_bures_qfi(
        point,
        left_frame,
        right_frame,
        GRID["finite_difference_step"],
    )
    unframed_qfi = bures_qfi_finite_difference(
        *point.tolist(), step=GRID["finite_difference_step"]
    )
    spectral_scale = max(1.0, float(np.max(np.linalg.eigvalsh(unframed_qfi))))
    assert np.max(
        np.abs(
            np.linalg.eigvalsh(framed_qfi)
            - np.linalg.eigvalsh(unframed_qfi)
        )
    ) <= QFI_RELATIVE_TOLERANCE * spectral_scale

    compact_word = bell_codeword(
        compact_su2(2.0 * math.atan(1.0), GRID["base_phi"], GRID["base_psi"])
    )
    assert compact_word.density.shape == original_words[0].density.shape
    assert compact_word.success_probability == pytest.approx(
        1.0, abs=ALGEBRA_TOLERANCE
    )


def test_aion_worldlet_tendril_seam_keeps_heterogeneous_types_and_cost():
    source = SourceMovement.from_coordinates(
        1.0, GRID["base_phi"], GRID["base_psi"]
    )
    movement = QuantumMovement.from_source(source)
    polycosmos = build_quantum_polycosmos(source, movement)

    assert len(polycosmos.worldlets) == 2
    assert polycosmos.geometries == {
        Geometry.SL2_ABSOLUTE_PSEUDO_VOLUME,
        Geometry.DENSITY_OPERATOR_BURES,
    }
    regimes = {
        worldlet.algebra_regime for worldlet in polycosmos.worldlets.values()
    }
    assert regimes == {AlgebraRegime.REAL_MATRIX, AlgebraRegime.COMPLEX}
    source_worldlet = next(
        worldlet
        for worldlet in polycosmos.worldlets.values()
        if worldlet.local_geometry == Geometry.SL2_ABSOLUTE_PSEUDO_VOLUME
    )
    operational_worldlet = next(
        worldlet
        for worldlet in polycosmos.worldlets.values()
        if worldlet.local_geometry == Geometry.DENSITY_OPERATOR_BURES
    )
    assert source_worldlet.local_state is source
    assert operational_worldlet.local_state is movement
    assert operational_worldlet.typed_remainders

    tendril = next(iter(polycosmos.tendrils.values()))
    assert tendril.preserved_fields
    assert tendril.transformed_fields
    assert tendril.lost_fields == ("global sign",)
    assert tendril.transport_cost == pytest.approx(
        1.0 - movement.bell_success_probability, abs=ALGEBRA_TOLERANCE
    )
    assert tendril.typed_remainder is not None
    assert tendril.return_transport is None
    assert tendril.return_absent_reason
    assert not tendril.is_reversible
    assert not tendril.claims_lossless

    with pytest.raises(IncommensurableError):
        _ = source.volume_density > movement.conditional_entanglement


def test_aion_seam_rejects_mismatched_local_sections():
    source = SourceMovement.from_coordinates(
        1.0, GRID["base_phi"], GRID["base_psi"]
    )
    unrelated = QuantumMovement.from_source(
        SourceMovement.from_coordinates(
            2.0, GRID["base_phi"], GRID["base_psi"]
        )
    )
    with pytest.raises(GovernanceError, match="gluing law"):
        build_quantum_polycosmos(source, unrelated)


def test_interior_formulas_are_stable_and_source_range_is_explicit():
    far_qfi = analytic_qfi_rho(178.0)
    assert np.all(np.isfinite(far_qfi))
    assert far_qfi[0, 0] >= 0.0
    near_boundary = 1e-18
    assert math.isfinite(qfi_volume_density(near_boundary))
    assert math.isfinite(source_to_qfi_volume_distortion(near_boundary))
    for invalid in (math.nan, math.inf, -math.inf, 351.0):
        with pytest.raises(ValueError):
            SourceMovement.from_coordinates(
                invalid, GRID["base_phi"], GRID["base_psi"]
            )


def test_omnitool_weave_history_is_append_only_and_not_physical_inverse():
    tool = QuantumMovementOmniTool(GRID["weave_trace_threshold"])
    with pytest.raises(ValueError, match="compose_word telemetry"):
        tool.observe(*GRID["path"][0], materialization_mode="materialized_prefix")
    tool.observe(*GRID["path"][0])
    initial = tool.events
    assert isinstance(initial, tuple)
    assert [event.index for event in initial] == [0]

    with pytest.raises(GovernanceError, match="reason"):
        tool.deweave("")
    tool.deweave("manual audit retirement")
    assert initial == tool.events[:1]
    assert tool.events[-1].action == "deweave"
    assert tool.events[-1].reason == "manual audit retirement"
    assert not tool.events[-1].physical_inverse
    assert not next(iter(tool.polycosmos.tendrils.values())).woven

    tool.weave("manual audit re-entry")
    assert [event.index for event in tool.events] == [0, 1, 2]
    assert all(event.reason for event in tool.events)
    assert all(not event.physical_inverse for event in tool.events)
    assert next(iter(tool.polycosmos.tendrils.values())).woven

    frozen_tool = QuantumMovementOmniTool(GRID["weave_trace_threshold"])
    frozen_tool.observe_path(GRID["path"])
    with pytest.raises(GovernanceError, match="append-once"):
        frozen_tool.observe_path(GRID["path"])
    with pytest.raises(GovernanceError, match="reason"):
        next(iter(frozen_tool.polycosmos.tendrils.values())).deweave("")


def test_h1_frozen_path_contains_radial_deweave_and_boundary_angular_weave():
    trace = QuantumMovementOmniTool(
        GRID["weave_trace_threshold"]
    ).observe_path(GRID["path"])
    assert len(trace.observations) == len(GRID["path"])
    assert len(trace.events) == len(GRID["path"])
    assert [event.index for event in trace.events] == list(
        range(len(GRID["path"]))
    )
    assert all(event.reason for event in trace.events)
    assert all(not event.physical_inverse for event in trace.events)

    radial_deweaves = []
    boundary_angular_weaves = []
    for index in range(1, len(trace.observations)):
        previous = trace.observations[index - 1]
        current = trace.observations[index]
        event = trace.events[index]
        fixed_angles = (
            previous.source.phi == current.source.phi
            and previous.source.psi == current.source.psi
        )
        if (
            event.action == "deweave"
            and fixed_angles
            and current.source.rho >= 3.0
        ):
            radial_deweaves.append(event)
        if (
            event.action == "weave"
            and previous.source.rho == 6.0
            and current.source.rho == 6.0
            and not fixed_angles
        ):
            boundary_angular_weaves.append(event)

    assert radial_deweaves
    assert boundary_angular_weaves
    assert all(
        event.trace_distance < GRID["weave_trace_threshold"]
        for event in radial_deweaves
    )
    assert all(
        event.trace_distance >= GRID["weave_trace_threshold"]
        for event in boundary_angular_weaves
    )

    information = trace.information
    assert information.pgm.value <= (
        information.holevo.value + ALGEBRA_TOLERANCE
    )
    assert information.holevo.value <= (
        information.oracle_erasure.value + ALGEBRA_TOLERANCE
    )
    assert information.oracle_erasure.value <= (
        information.log2_codewords.value + ALGEBRA_TOLERANCE
    )
    assert trace.source_extent is trace.ambient_source_slab_extent
    with pytest.raises(IncommensurableError):
        _ = trace.ambient_source_slab_extent > information.holevo
