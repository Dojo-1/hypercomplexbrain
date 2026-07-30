from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from aionq.governance import GovernanceError
from aionq.hb0 import (
    CarrierMismatch,
    EuclideanBaseControl,
    HopfUnitaryChart,
    HyperbolicQuantumBase,
    HyperbolicQuantumPoint,
    PoincareBallBase,
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
    quantum_root_fidelity,
    quantum_trace_distance,
)


def test_preregistration_is_frozen_and_forbids_metric_collapse():
    manifest = json.loads(
        Path("manifests/hb0_hyperbolic_quantum_base_preregistration.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["status"] == "FROZEN_BEFORE_IMPLEMENTATION_AND_EXECUTION"
    assert any(
        "scalar combines base distance" in condition
        for condition in manifest["kill_conditions"]
    )


@pytest.mark.parametrize(
    "point",
    (
        np.zeros(4),
        np.array([0.2, -0.1, 0.3, 0.05]),
        np.array([-0.6, 0.1, 0.2, -0.15]),
    ),
)
def test_encoding_is_a_physical_immutable_qutrit_state(point):
    encoded = HyperbolicQuantumBase().encode(point)
    assert encoded.density.shape == (3, 3)
    assert encoded.density == pytest.approx(encoded.density.conj().T)
    assert float(np.trace(encoded.density).real) == pytest.approx(1.0)
    assert np.min(np.linalg.eigvalsh(encoded.density)) >= -1e-12
    with pytest.raises(ValueError):
        encoded.density.setflags(write=True)


@pytest.mark.parametrize("radius", (0.0, 0.1, 0.4, 0.8, 0.99))
def test_radius_and_hyperbolic_depth_are_exactly_recoverable(radius):
    quantum_base = HyperbolicQuantumBase()
    point = np.array([radius, 0.0, 0.0, 0.0])
    encoded = quantum_base.encode(point)
    assert quantum_base.recover_ball_radius(encoded) == pytest.approx(radius)
    assert quantum_base.recover_ball_radius(encoded.density) == pytest.approx(radius)
    assert quantum_base.recover_hyperbolic_radius(encoded) == pytest.approx(
        quantum_base.base.distance(np.zeros(4), point)
    )
    assert quantum_base.recover_hyperbolic_radius(encoded.density) == pytest.approx(
        quantum_base.base.distance(np.zeros(4), point)
    )


@pytest.mark.parametrize("radius", (0.0, 0.2, 0.7, 0.99))
def test_quantum_distance_from_origin_compactifies_infinite_depth(radius):
    quantum_base = HyperbolicQuantumBase()
    origin = quantum_base.encode(np.zeros(4)).density
    point = quantum_base.encode(np.array([radius, 0.0, 0.0, 0.0])).density
    assert quantum_trace_distance(origin, point) == pytest.approx(radius)
    if radius > 0.0:
        assert quantum_base.base.distance(
            np.zeros(4), np.array([radius, 0.0, 0.0, 0.0])
        ) > radius


def test_root_fidelity_retains_small_positive_boundary_overlap():
    quantum_base = HyperbolicQuantumBase()
    radius = 0.999
    overlap = 5e-5
    left = radius * np.array([1.0, 0.0, 0.0, 0.0])
    right = radius * np.array(
        [overlap, 0.0, math.sqrt(1.0 - overlap * overlap), 0.0]
    )
    fidelity = quantum_root_fidelity(
        quantum_base.encode(left).density,
        quantum_base.encode(right).density,
    )
    assert fidelity == pytest.approx(
        (1.0 - radius) + radius * overlap,
        abs=1e-12,
    )


def test_origin_is_direction_independent_and_open_boundary_fails_closed():
    quantum_base = HyperbolicQuantumBase()
    assert quantum_base.phase_rotate(np.zeros(4), 1.7) == pytest.approx(np.zeros(4))
    with pytest.raises(GovernanceError):
        quantum_base.encode(np.array([1.0, 0.0, 0.0, 0.0]))


def test_small_nonzero_directions_are_not_thickened_into_the_origin():
    quantum_base = HyperbolicQuantumBase()
    radius = 0.5 * quantum_base.tolerance
    left = np.array([radius, 0.0, 0.0, 0.0])
    right = np.array([0.0, 0.0, radius, 0.0])
    assert quantum_base.base.distance(left, right) > 0.0
    assert quantum_trace_distance(
        quantum_base.encode(left).density,
        quantum_base.encode(right).density,
    ) == pytest.approx(radius)


def test_hopf_phase_is_a_nonzero_source_orbit_and_exact_quantum_kernel():
    quantum_base = HyperbolicQuantumBase()
    point = np.array([0.3, -0.2, 0.1, 0.25])
    report = quantum_base.hopf_kernel(point, phase=0.73)
    assert report.source_hyperbolic_distance > 0.0
    assert report.source_euclidean_distance > 0.0
    assert report.quantum_trace_distance < 1e-12
    assert report.quantum_root_fidelity == pytest.approx(1.0)
    assert report.remainder.name == "[R]_hopf_phase"
    assert report.remainder.magnitude == pytest.approx(
        report.source_hyperbolic_distance
    )
    with pytest.raises(GovernanceError):
        quantum_base.hopf_kernel(point, phase=0.0)
    with pytest.raises(GovernanceError):
        quantum_base.hopf_kernel(np.zeros(4), phase=0.7)


def test_generic_differential_has_one_phase_kernel():
    report = HyperbolicQuantumBase().differential(
        np.array([0.27, -0.18, 0.14, 0.22])
    )
    assert report.rank == 3
    assert report.singular_values[2] > 1e-3
    assert report.singular_values[3] < report.rank_cutoff
    assert report.phase_directional_defect < 1e-8
    assert report.finite_difference_step == pytest.approx(1e-6)
    assert report.finite_difference_defect < 1e-8


def _unitary(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    matrix = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
    q, r = np.linalg.qr(matrix)
    phases = np.diag(r)
    phases = np.where(np.abs(phases) > 0.0, phases / np.abs(phases), 1.0)
    return q @ np.diag(phases.conj())


@pytest.mark.parametrize("seed", range(8))
def test_u2_transport_intertwines_base_and_quantum_geometry(seed):
    quantum_base = HyperbolicQuantumBase()
    chart = HopfUnitaryChart(_unitary(seed))
    report = quantum_base.covariance(
        np.array([0.2, -0.1, 0.25, 0.05]),
        np.array([-0.35, 0.2, 0.1, -0.15]),
        chart,
    )
    assert report.passed


def test_nonunitary_chart_is_rejected_before_transport():
    with pytest.raises(GovernanceError):
        HopfUnitaryChart(np.array([[1.0, 1.0], [0.0, 1.0]]))
    with pytest.raises(GovernanceError):
        HopfUnitaryChart(np.eye(2), tolerance=math.nan)
    with pytest.raises(GovernanceError):
        HopfUnitaryChart(
            np.diag([1.0 + 2e-7, 1.0]),
            tolerance=1e-6,
        )


def test_pair_report_keeps_all_metric_carriers_separate():
    report = HyperbolicQuantumBase().compare(
        np.array([0.1, 0.2, 0.0, -0.1]),
        np.array([-0.2, 0.1, 0.15, 0.05]),
    )
    assert report.hyperbolic_distance > 0.0
    assert report.euclidean_control_distance > 0.0
    assert 0.0 <= report.trace_distance <= 1.0
    assert 0.0 <= report.root_fidelity <= 1.0
    assert report.bures_distance == pytest.approx(
        math.sqrt(2.0 * (1.0 - report.root_fidelity))
    )
    assert not hasattr(report, "score")


def test_dephasing_obeys_data_processing_directions():
    report = HyperbolicQuantumBase().data_processing(
        np.array([0.25, 0.15, -0.1, 0.2]),
        np.array([-0.2, 0.1, 0.3, -0.05]),
    )
    assert report.contractive
    assert report.output_trace_distance <= report.input_trace_distance + 1e-12
    assert report.output_root_fidelity >= report.input_root_fidelity - 1e-12


def test_quantum_metrics_refuse_non_density_and_dimension_mismatch():
    with pytest.raises(GovernanceError):
        quantum_trace_distance(np.eye(2), np.eye(2) / 2.0)
    with pytest.raises(GovernanceError):
        quantum_root_fidelity(np.diag([1.0, -0.1, 0.1]), np.diag([1.0, 0.0, 0.0]))
    with pytest.raises(CarrierMismatch):
        quantum_trace_distance(np.eye(2) / 2.0, np.eye(3) / 3.0)


def test_hopf_quantum_base_requires_h4_and_origin_matched_control():
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumBase(
            base=PoincareBallBase("H3", 3),
            euclidean_control=EuclideanBaseControl("R3", 3, metric_scale=2.0),
        )
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumBase(
            euclidean_control=EuclideanBaseControl("bad-R4", 4, metric_scale=1.0)
        )


def test_hopf_quantum_base_rejects_parallel_h4_specs_but_accepts_roundtrip_specs():
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumBase(
            base=PoincareBallBase("H4-alias", 4),
            euclidean_control=UNIVERSAL_EUCLIDEAN_CONTROL,
        )
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumBase(
            base=UNIVERSAL_POINCARE_BASE,
            euclidean_control=EuclideanBaseControl(
                "R4-control-alias",
                4,
                metric_scale=UNIVERSAL_EUCLIDEAN_CONTROL.metric_scale,
            ),
        )

    parallel = PoincareBallBase(
        UNIVERSAL_POINCARE_BASE.id,
        4,
        sectional_curvature=-0.25,
    )
    parallel_control = EuclideanBaseControl(
        "parallel-control-R4",
        4,
        metric_scale=2.0 * parallel.radius,
    )
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumBase(
            base=parallel,
            euclidean_control=parallel_control,
        )

    reconstructed = HyperbolicQuantumBase(
        base=PoincareBallBase.from_spec(UNIVERSAL_POINCARE_BASE.to_spec()),
        euclidean_control=EuclideanBaseControl.from_spec(
            UNIVERSAL_EUCLIDEAN_CONTROL.to_spec()
        ),
    )
    assert reconstructed.base.to_spec() == UNIVERSAL_POINCARE_BASE.to_spec()
    assert (
        reconstructed.euclidean_control.to_spec()
        == UNIVERSAL_EUCLIDEAN_CONTROL.to_spec()
    )


def test_inverse_recovery_rejects_qutrits_outside_the_open_hopf_cone():
    quantum_base = HyperbolicQuantumBase()
    valid = quantum_base.encode(np.array([0.2, -0.1, 0.3, 0.05]))
    assert quantum_base.recover_ball_radius(valid.density) == pytest.approx(
        valid.ball_radius
    )

    with pytest.raises(CarrierMismatch):
        quantum_base.recover_ball_radius(np.eye(3) / 3.0)
    with pytest.raises(CarrierMismatch):
        quantum_base.recover_hyperbolic_radius(np.diag([0.0, 1.0, 0.0]))

    coherent = np.outer(
        np.array([math.sqrt(0.5), math.sqrt(0.5), 0.0]),
        np.array([math.sqrt(0.5), math.sqrt(0.5), 0.0]),
    )
    with pytest.raises(CarrierMismatch):
        quantum_base.recover_ball_radius(coherent)
    with pytest.raises(CarrierMismatch):
        quantum_base.recover_ball_radius(np.diag([0.5, 0.25, 0.25]))


def test_public_quantum_point_cannot_be_forged_with_inconsistent_radius():
    with pytest.raises(GovernanceError):
        HyperbolicQuantumPoint(
            base_id=UNIVERSAL_POINCARE_BASE.id,
            base_point=np.array([0.2, 0.0, 0.0, 0.0]),
            density=np.diag([0.8, 0.2, 0.0]),
            ball_radius=0.3,
            hyperbolic_radius=0.4,
            curvature_radius=1.0,
        )
    with pytest.raises(GovernanceError):
        HyperbolicQuantumPoint(
            base_id=UNIVERSAL_POINCARE_BASE.id,
            base_point=np.array([0.2, 0.0, 0.0, 0.0]),
            density=np.eye(3) / 3.0,
            ball_radius=0.2,
            hyperbolic_radius=2.0 * math.atanh(0.2),
            curvature_radius=1.0,
        )
    with pytest.raises(GovernanceError):
        HyperbolicQuantumPoint(
            base_id=UNIVERSAL_POINCARE_BASE.id,
            base_point=np.array([0.2, 0.0, 0.0, 0.0]),
            density=np.diag([0.8, 0.2, 0.0]),
            ball_radius=0.2,
            hyperbolic_radius=999.0,
            curvature_radius=1.0,
        )


def test_public_quantum_point_rejects_forged_base_identity_and_curvature():
    fields = {
        "base_point": np.array([0.2, 0.0, 0.0, 0.0]),
        "density": np.diag([0.8, 0.2, 0.0]),
        "ball_radius": 0.2,
        "hyperbolic_radius": 2.0 * math.atanh(0.2),
        "curvature_radius": UNIVERSAL_POINCARE_BASE.radius,
    }
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumPoint(base_id="parallel-H4", **fields)
    with pytest.raises(CarrierMismatch):
        HyperbolicQuantumPoint(
            base_id=UNIVERSAL_POINCARE_BASE.id,
            **{**fields, "curvature_radius": 2.0},
        )
