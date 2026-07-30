from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.governance import GovernanceError
from aionq.atlas import poincare_distance
from aionq.hb0 import (
    CarrierMismatch,
    EuclideanBaseControl,
    LorentzIsometry,
    PoincareBallBase,
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
)


def test_universal_base_spec_separates_tangent_and_ambient_signatures():
    base = PoincareBallBase("decision-H3", 3, sectional_curvature=-2.0)
    spec = base.to_spec()
    assert spec["scope"] == "universal_atlas"
    assert spec["universal"] is True
    assert spec["tangent_signature"] == [3, 0]
    assert spec["ambient_signature"] == [3, 1]
    assert PoincareBallBase.from_spec(spec) == base


def test_base_refuses_nonnegative_curvature_local_scope_and_missing_control():
    with pytest.raises(GovernanceError):
        PoincareBallBase("flat", 2, sectional_curvature=0.0)
    with pytest.raises(GovernanceError):
        PoincareBallBase("local-only", 2, scope="decision_context_only")
    with pytest.raises(GovernanceError):
        PoincareBallBase("uncontrolled", 2, euclidean_control_declared=False)


def test_stable_distance_resolves_sub_machine_sqrt_separation():
    base = PoincareBallBase("H2", 2)
    separation = 1e-12
    distance = base.distance(np.zeros(2), np.array([separation, 0.0]))
    assert distance == pytest.approx(2.0 * separation, rel=1e-12)
    assert distance > 0.0
    assert poincare_distance(
        np.zeros(2),
        np.array([separation, 0.0]),
    ) == pytest.approx(distance)
    with pytest.raises(ValueError):
        poincare_distance(np.zeros(2), np.array([math.nan, 0.0]))


def test_ball_hyperboloid_roundtrip_metric_and_distance_agree():
    base = PoincareBallBase("H2", 2)
    left = np.array([0.2, -0.1])
    right = np.array([-0.3, 0.25])
    left_lift = base.to_hyperboloid(left)
    right_lift = base.to_hyperboloid(right)
    assert base.from_hyperboloid(left_lift) == pytest.approx(left)
    assert base.lorentz_inner(left_lift, left_lift) == pytest.approx(-1.0)
    assert base.metric_tensor(np.zeros(2)) == pytest.approx(4.0 * np.eye(2))
    assert base.distance(left, right) == pytest.approx(
        base.hyperboloid_distance(left_lift, right_lift),
        rel=1e-12,
    )


def test_exp_log_and_parallel_transport_preserve_declared_geometry():
    base = PoincareBallBase("H2", 2)
    left = base.to_hyperboloid(np.array([0.2, 0.1]))
    right = base.to_hyperboloid(np.array([-0.25, 0.2]))
    tangent = base.log(left, right)
    distance = base.hyperboloid_distance(left, right)
    assert base.tangent_norm(left, tangent) == pytest.approx(distance)
    assert base.exp(left, tangent) == pytest.approx(right, abs=1e-12)
    transported = base.parallel_transport(left, right, tangent)
    assert base.tangent_norm(right, transported) == pytest.approx(distance)
    returned = base.parallel_transport(right, left, transported)
    assert returned == pytest.approx(tangent, abs=1e-12)


def test_lorentz_boost_preserves_distance_and_review_passes():
    base = PoincareBallBase("H2", 2)
    rapidity = 0.4
    boost = LorentzIsometry(
        np.array(
            [
                [math.cosh(rapidity), math.sinh(rapidity), 0.0],
                [math.sinh(rapidity), math.cosh(rapidity), 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
    )
    review = base.review(
        (np.zeros(2), np.array([0.2, 0.1]), np.array([-0.3, 0.2])),
        (boost,),
    )
    assert review.passed, review.violations
    assert review.isometries_reviewed == 1
    assert review.maximum_isometry_distance_defect < 1e-12


def test_split_or_euclidean_matrix_is_not_a_lorentz_isometry():
    with pytest.raises(GovernanceError):
        LorentzIsometry(
            np.array(
                [
                    [0.0, 1.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0],
                ]
            )
        )


def test_split_signature_transport_and_psd_kernel_are_not_hyperbolic_geometry():
    angle = 0.3
    split_isometry = np.eye(4)
    split_isometry[:2, :2] = np.array(
        [
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ]
    )
    split_form = np.diag([1.0, 1.0, -1.0, -1.0])
    assert split_isometry.T @ split_form @ split_isometry == pytest.approx(
        split_form
    )
    with pytest.raises(GovernanceError):
        LorentzIsometry(split_isometry)

    split_null = np.array([1.0, 0.0, 1.0, 0.0])
    assert split_null @ split_form @ split_null == pytest.approx(0.0)
    psd_metric = np.diag([1.0, 0.0, 0.0, 0.0])
    assert np.linalg.norm(psd_metric @ split_null) > 0.0
    psd_kernel_vector = np.array([0.0, 0.0, 1.0, 0.0])
    assert psd_metric @ psd_kernel_vector == pytest.approx(np.zeros(4))
    assert psd_kernel_vector @ split_form @ psd_kernel_vector == pytest.approx(
        -1.0
    )
    with pytest.raises(GovernanceError):
        LorentzIsometry(
            np.array(
                [
                    [0.0, 1.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
        )


def test_open_boundary_and_wrong_sheet_fail_closed_without_clipping():
    base = PoincareBallBase("H2", 2)
    for point in (
        np.array([1.0, 0.0]),
        np.array([math.nan, 0.0]),
        np.array([math.inf, 0.0]),
    ):
        with pytest.raises(GovernanceError):
            base.distance(np.zeros(2), point)
    future = base.to_hyperboloid(np.array([0.2, 0.0]))
    past = -future
    with pytest.raises(GovernanceError):
        base.from_hyperboloid(past)
    with pytest.raises(CarrierMismatch):
        base.distance(np.zeros(2), np.zeros(3))


def test_radial_coordinate_has_exact_distance_and_diverges_at_boundary():
    base = PoincareBallBase("H2", 2)
    direction = np.array([3.0, 4.0])
    for distance in (0.1, 1.0, 5.0):
        point = base.radial_point(distance, direction)
        assert base.distance(np.zeros(2), point) == pytest.approx(distance)
    radii = (0.9, 0.99, 0.999)
    distances = tuple(
        base.distance(np.zeros(2), np.array([radius, 0.0])) for radius in radii
    )
    assert distances[0] < distances[1] < distances[2]


def test_hyperboloid_and_lorentz_validators_fail_closed_under_large_scale():
    base = PoincareBallBase("H1", 1)
    with pytest.raises(GovernanceError):
        base.from_hyperboloid(np.array([1e8, 1e8]))
    for matrix in (
        np.full((2, 2), 1e8),
        np.full((2, 2), 1e308),
    ):
        with pytest.raises(GovernanceError):
            LorentzIsometry(matrix)


def test_curvature_and_rapidity_stay_inside_declared_float64_domain():
    with pytest.raises(GovernanceError):
        PoincareBallBase("tiny-radius", 1, sectional_curvature=-1e308)
    with pytest.raises(GovernanceError):
        PoincareBallBase("huge-radius", 1, sectional_curvature=-1e-320)
    base = PoincareBallBase("H2", 2)
    origin = base.to_hyperboloid(np.zeros(2))
    with pytest.raises(GovernanceError):
        base.exp(origin, np.array([0.0, 10.0, 0.0]))
    with pytest.raises(GovernanceError):
        base.radial_point(40.0, np.array([1.0, 0.0]))


def test_lorentz_matrix_is_bytes_backed_and_cannot_be_mutated_after_validation():
    isometry = LorentzIsometry(np.eye(3))
    with pytest.raises(ValueError):
        isometry.matrix.setflags(write=True)


def test_spec_roundtrip_preserves_numerical_contract_and_rejects_signature_drift():
    base = PoincareBallBase("H2", 2, tolerance=1e-8)
    spec = base.to_spec()
    assert PoincareBallBase.from_spec(spec) == base
    for key, value in (
        ("tangent_signature", [2, 2]),
        ("ambient_signature", [2, 2]),
        ("canonical_model", "split_signature"),
        ("chart", "closed_ball"),
        ("dimension", 2.7),
        ("euclidean_control_declared", "true"),
    ):
        changed = dict(spec)
        changed[key] = value
        with pytest.raises(GovernanceError):
            PoincareBallBase.from_spec(changed)
    legacy = dict(spec)
    legacy["schema"] = "aionq.hb0.poincare-base.v1"
    with pytest.raises(GovernanceError):
        PoincareBallBase.from_spec(legacy)


def test_repository_default_and_euclidean_control_share_origin_tangent_metric():
    base = UNIVERSAL_POINCARE_BASE
    control = UNIVERSAL_EUCLIDEAN_CONTROL
    assert base.dimension == control.dimension == 4
    assert control.metric_tensor == pytest.approx(
        base.metric_tensor(np.zeros(base.dimension))
    )
    assert EuclideanBaseControl.from_spec(control.to_spec()) == control


def test_review_requires_real_overlaps_and_validates_isometry_dimensions_upfront():
    base = PoincareBallBase("H2", 2)
    with pytest.raises(GovernanceError):
        base.review((np.zeros(2),))
    with pytest.raises(CarrierMismatch):
        base.review(
            (np.zeros(2), np.array([0.1, 0.0])),
            (LorentzIsometry(np.eye(4)),),
        )


def test_exp_log_and_parallel_transport_are_lorentz_equivariant():
    base = PoincareBallBase("H2", 2)
    rapidity = 0.25
    isometry = LorentzIsometry(
        np.array(
            [
                [math.cosh(rapidity), math.sinh(rapidity), 0.0],
                [math.sinh(rapidity), math.cosh(rapidity), 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
    )
    left = base.to_hyperboloid(np.array([0.1, -0.15]))
    right = base.to_hyperboloid(np.array([-0.2, 0.1]))
    ambient = np.array([0.0, 0.2, -0.1])
    tangent = ambient + (
        base.lorentz_inner(left, ambient) / base.radius_squared
    ) * left
    moved_left = base.apply_isometry(isometry, left)
    moved_right = base.apply_isometry(isometry, right)
    moved_tangent = isometry.matrix @ tangent
    assert base.apply_isometry(isometry, base.exp(left, tangent)) == pytest.approx(
        base.exp(moved_left, moved_tangent),
        abs=1e-11,
    )
    assert isometry.matrix @ base.log(left, right) == pytest.approx(
        base.log(moved_left, moved_right),
        abs=1e-11,
    )
    assert isometry.matrix @ base.parallel_transport(left, right, tangent) == pytest.approx(
        base.parallel_transport(moved_left, moved_right, moved_tangent),
        abs=1e-11,
    )
