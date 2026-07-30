from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.governance import GovernanceError
from aionq.hb0 import (
    CONTINUE,
    HOLD,
    STOP,
    CarrierMismatch,
    FiniteAdiabaticCriterion,
    OrthogonalWallChart,
    WallObservation,
    WallPathSample,
    glue_wall_sections,
    trace_wall_breath,
)


def observation(
    delta,
    metric=None,
    *,
    carrier="decision:R2",
    section_id="u",
    tolerance=1e-10,
    order_coframe=None,
):
    delta = np.asarray(delta, dtype=float)
    return WallObservation(
        section_id=section_id,
        carrier=carrier,
        continue_coordinates=delta,
        stop_coordinates=np.zeros_like(delta),
        metric=np.eye(delta.size) if metric is None else np.asarray(metric, dtype=float),
        evidence_refs=("bounded-test",),
        tolerance=tolerance,
        order_coframe=order_coframe,
    )


def criterion(*, min_gap_ratio=0.5, max_load=1.5):
    return FiniteAdiabaticCriterion(
        parameter_name="registered_tick",
        parameter_unit="tick",
        section_scale=1.0,
        metric_scale=1.0,
        min_gap_ratio=min_gap_ratio,
        max_adiabatic_load=max_load,
    )


def sampled(observations, parameters):
    return tuple(
        WallPathSample(parameter, item)
        for parameter, item in zip(parameters, observations)
    )


def test_nonzero_kernel_difference_is_the_degenerate_wall():
    report = observation([0.0, 1.0], np.diag([1.0, 0.0])).analyse()
    assert report.decision == HOLD
    assert report.degenerate_wall
    assert not report.ordinary_tie
    assert report.intrinsic_gap == pytest.approx(1.0)
    assert report.observable_gap == pytest.approx(0.0)
    assert report.kernel_amplitude == pytest.approx(1.0)
    assert report.positive_component_gap == pytest.approx(0.0)
    assert report.remainder is not None
    assert report.remainder.name == "[R]_wall"


def test_small_positive_eigenvalue_does_not_hide_a_non_kernel_component():
    report = observation(
        [0.01, 1.0],
        np.diag([1e-9, 0.0]),
        tolerance=1e-10,
    ).analyse()
    assert report.rank == 1
    assert report.nullity == 1
    assert report.positive_component_gap == pytest.approx(0.01)
    assert not report.degenerate_wall
    assert report.decision == CONTINUE
    assert report.remainder is None


def test_zero_difference_is_tie_not_metric_degeneration():
    report = observation([0.0, 0.0], np.diag([1.0, 0.0])).analyse()
    assert report.decision == HOLD
    assert report.ordinary_tie
    assert not report.degenerate_wall
    assert report.remainder is not None


@pytest.mark.parametrize(
    ("delta", "expected"),
    [([1.0, 0.0], CONTINUE), ([-1.0, 0.0], STOP)],
)
def test_resolved_directions_have_no_unresolved_remainder(delta, expected):
    report = observation(delta).analyse()
    assert report.decision == expected
    assert report.remainder is None


def test_pareto_incomparability_holds_without_scalar_collapse():
    report = observation([1.0, -1.0]).analyse()
    assert report.decision == HOLD
    assert report.pareto_incomparable
    assert not report.degenerate_wall
    assert report.remainder is not None


def test_metric_must_be_symmetric_positive_semidefinite_under_one_cutoff():
    with pytest.raises(GovernanceError):
        observation([1.0, 0.0], [[1.0, 2.0], [0.0, 1.0]])
    with pytest.raises(GovernanceError):
        observation([1.0, 0.0], np.diag([1.0, -1.0]))
    with pytest.raises(GovernanceError):
        observation(
            [1.0, 0.0],
            np.diag([1.0, -5e-11]),
            tolerance=1e-12,
        )


@pytest.mark.parametrize(
    "coframe",
    (
        np.ones((2, 3)),
        np.array([[1.0, 0.0], [0.0, math.nan]]),
        np.array([[1.0, 1.0], [0.0, 1.0]]),
    ),
)
def test_order_coframe_must_be_finite_square_and_orthogonal(coframe):
    with pytest.raises(GovernanceError):
        observation([1.0, 0.0], order_coframe=coframe)


def test_carriers_cannot_be_implicitly_identified():
    section = observation([1.0, 0.0], carrier="local")
    chart = OrthogonalWallChart("other", "atlas", np.eye(2))
    with pytest.raises(CarrierMismatch):
        chart.transport(section)


def test_large_tolerance_cannot_turn_a_destructive_matrix_into_a_chart():
    with pytest.raises(GovernanceError):
        OrthogonalWallChart("local", "atlas", np.zeros((2, 2)), tolerance=2.0)
    with pytest.raises(GovernanceError):
        observation([1.0, 0.0], tolerance=2.0)


def test_frozen_wall_objects_do_not_retain_mutable_array_aliases():
    metric = np.eye(2)
    coframe = np.eye(2)
    matrix = np.eye(2)
    section = observation([1.0, 0.0], metric, order_coframe=coframe)
    chart = OrthogonalWallChart("decision:R2", "atlas", matrix)
    metric[0, 0] = -1.0
    coframe[0, 0] = 0.0
    matrix[0, 0] = 0.0
    assert section.metric == pytest.approx(np.eye(2))
    assert section.order_coframe == pytest.approx(np.eye(2))
    assert chart.matrix == pytest.approx(np.eye(2))
    with pytest.raises(ValueError):
        section.metric[0, 0] = 2.0


@pytest.mark.parametrize("delta", ([1.0, 0.0], [-1.0, 0.0]))
def test_q_minus_identity_transports_the_order_and_preserves_decision(delta):
    local = observation(delta, carrier="local")
    transported = OrthogonalWallChart("local", "atlas", -np.eye(2)).transport(local)
    assert transported.analyse().decision == local.analyse().decision
    assert transported.order_coordinates == pytest.approx(local.order_coordinates)


def test_rotation_preserves_pareto_incomparability_when_coframe_moves():
    angle = math.pi / 4.0
    q = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    local = observation([1.0, -0.5], carrier="local")
    transported = OrthogonalWallChart("local", "atlas", q).transport(local)
    assert local.analyse().pareto_incomparable
    assert transported.analyse().pareto_incomparable
    assert transported.order_coordinates == pytest.approx(local.order_coordinates)


def test_wall_property_is_invariant_under_orthogonal_chart_transport():
    q = np.array([[0.0, -1.0], [1.0, 0.0]])
    local = observation([0.0, 1.0], np.diag([1.0, 0.0]), carrier="local")
    transported = OrthogonalWallChart("local", "atlas", q).transport(local)
    report = transported.analyse()
    assert report.degenerate_wall
    assert report.intrinsic_gap == pytest.approx(1.0)
    assert report.observable_gap == pytest.approx(0.0)


def test_sheaf_gluing_compares_complete_fields_after_declared_transport():
    q = np.array([[0.0, -1.0], [1.0, 0.0]])
    atlas = observation(
        [0.0, 1.0],
        np.diag([1.0, 0.0]),
        carrier="atlas",
        section_id="a",
    )
    local = observation(
        [1.0, 0.0],
        np.diag([0.0, 1.0]),
        carrier="local",
        section_id="b",
        order_coframe=q,
    )
    report = glue_wall_sections(
        {"a": atlas, "b": local},
        {
            "a": OrthogonalWallChart("atlas", "atlas", np.eye(2)),
            "b": OrthogonalWallChart("local", "atlas", q),
        },
    )
    assert report.glued
    assert report.decision_coherent
    assert report.atlas_decision == HOLD
    assert report.remainder is None
    assert all(local_report.degenerate_wall for local_report in report.local_reports.values())


def test_equal_vectors_and_metrics_with_opposite_orders_do_not_glue():
    report = glue_wall_sections(
        {
            "a": observation([1.0, 0.0], section_id="a"),
            "b": observation(
                [1.0, 0.0],
                section_id="b",
                order_coframe=-np.eye(2),
            ),
        },
        {
            "a": OrthogonalWallChart("decision:R2", "atlas", np.eye(2)),
            "b": OrthogonalWallChart("decision:R2", "atlas", np.eye(2)),
        },
    )
    assert not report.glued
    assert not report.decision_coherent
    assert report.atlas_decision == HOLD
    assert report.remainder is not None


def test_gluing_uses_pairwise_diameter_not_a_reference_star():
    epsilon = 1e-7
    report = glue_wall_sections(
        {
            "a": observation([1.0, 0.0], section_id="a"),
            "b": observation([1.0 + 0.75 * epsilon, 0.0], section_id="b"),
            "c": observation([1.0 - 0.75 * epsilon, 0.0], section_id="c"),
        },
        {
            name: OrthogonalWallChart("decision:R2", "atlas", np.eye(2))
            for name in ("a", "b", "c")
        },
        tolerance=epsilon,
    )
    assert report.gluing_defect == pytest.approx(1.5 * epsilon)
    assert not report.glued
    assert report.atlas_decision == HOLD


def test_gluing_pairwise_diameter_includes_metric_disagreement():
    epsilon = 1e-7
    report = glue_wall_sections(
        {
            "a": observation([1.0, 0.0], np.eye(2), section_id="a"),
            "b": observation(
                [1.0, 0.0],
                np.diag([1.0 + 0.75 * epsilon, 1.0]),
                section_id="b",
            ),
            "c": observation(
                [1.0, 0.0],
                np.diag([1.0 - 0.75 * epsilon, 1.0]),
                section_id="c",
            ),
        },
        {
            name: OrthogonalWallChart("decision:R2", "atlas", np.eye(2))
            for name in ("a", "b", "c")
        },
        tolerance=epsilon,
    )
    assert report.gluing_defect == pytest.approx(1.5 * epsilon)
    assert not report.glued


def test_failed_gluing_forces_hold_and_exposes_coherence_remainder():
    report = glue_wall_sections(
        {
            "a": observation([1.0, 0.0], section_id="a"),
            "b": observation([-1.0, 0.0], section_id="b"),
        },
        {
            "a": OrthogonalWallChart("decision:R2", "atlas", np.eye(2)),
            "b": OrthogonalWallChart("decision:R2", "atlas", np.eye(2)),
        },
    )
    assert not report.glued
    assert report.atlas_decision == HOLD
    assert report.remainder is not None
    assert report.remainder.channel == "coherence"
    assert report.remainder.magnitude > 0.0


def test_slow_metric_wall_passage_is_certified_but_fast_copy_is_not():
    metric = np.diag([1.0, 0.0])
    observations = (
        observation([1.0, 0.0], metric),
        observation([0.0, 1.0], metric),
        observation([-1.0, 0.0], metric),
    )
    slow = trace_wall_breath(sampled(observations, (0.0, 1.0, 2.0)), criterion())
    fast = trace_wall_breath(
        sampled(observations, (0.0, 0.01, 0.02)),
        criterion(),
    )
    assert slow.decisions == (CONTINUE, HOLD, STOP)
    assert slow.degenerate_wall_indices == (1,)
    assert slow.has_intermediate_hold
    assert slow.maximum_adiabatic_load == pytest.approx(math.sqrt(2.0))
    assert slow.adiabatic_certified_under_policy
    assert not fast.adiabatic_certified_under_policy
    assert "adiabatic_load_exceeds_bound" in fast.violations


def test_pareto_hold_does_not_witness_a_metric_wall():
    observations = (
        observation([1.0, 0.0]),
        observation([1.0, -1.0]),
        observation([-1.0, 0.0]),
    )
    breath = trace_wall_breath(
        sampled(observations, (0.0, 2.0, 4.0)),
        criterion(max_load=10.0),
    )
    assert breath.decisions == (CONTINUE, HOLD, STOP)
    assert breath.has_intermediate_hold
    assert breath.pareto_hold_indices == (1,)
    assert breath.degenerate_wall_indices == ()
    assert breath.unwitnessed_reversal_spans == ((0, 2),)
    assert not breath.adiabatic_certified_under_policy
    assert "reversal_without_metric_wall" in breath.violations


def test_gap_floor_and_kernel_rank_are_part_of_the_certificate():
    small_gap_metric = np.diag([1.0, 1e-6, 0.0])
    small_gap = trace_wall_breath(
        sampled(
            (
                observation([1.0, 0.0, 0.0], small_gap_metric),
                observation([0.0, 0.0, 1.0], small_gap_metric),
                observation([-1.0, 0.0, 0.0], small_gap_metric),
            ),
            (0.0, 2.0, 4.0),
        ),
        criterion(min_gap_ratio=1e-3, max_load=1e9),
    )
    assert not small_gap.adiabatic_certified_under_policy
    assert "spectral_gap_below_floor" in small_gap.violations

    rank_change = trace_wall_breath(
        sampled(
            (
                observation([1.0, 0.0], np.diag([1.0, 0.0])),
                observation([0.0, 1.0], np.zeros((2, 2))),
                observation([-1.0, 0.0], np.diag([1.0, 0.0])),
            ),
            (0.0, 2.0, 4.0),
        ),
        criterion(max_load=1e9),
    )
    assert not rank_change.adiabatic_certified_under_policy
    assert "kernel_nullity_changed" in rank_change.violations
    assert "positive_spectral_band_missing" in rank_change.violations


def test_path_parameter_and_carrier_guards_fail_closed():
    obs = observation([1.0, 0.0])
    with pytest.raises(GovernanceError):
        trace_wall_breath(sampled((obs, obs), (0.0, 0.0)), criterion())
    with pytest.raises(GovernanceError):
        trace_wall_breath((WallPathSample(0.0, obs),), criterion())
    with pytest.raises(CarrierMismatch):
        trace_wall_breath(
            (
                WallPathSample(0.0, obs),
                WallPathSample(1.0, observation([1.0, 0.0], carrier="other")),
            ),
            criterion(),
        )
