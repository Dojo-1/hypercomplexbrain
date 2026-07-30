from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

from aionq.governance import EvidenceTag, GovernanceError, registry
from aionq.hb0 import (
    QUALITY_ORDER,
    AdiabaticController,
    AdiabaticState,
    CarrierMismatch,
    ChartFunctor,
    ClockSpec,
    ContactHamiltonianGovernor,
    CosmosCage,
    FlatCollapseError,
    GerbeCell,
    HamiltonianEnvelope,
    HoloportiveReconstructor,
    IdentityEcology,
    IdentityRegime,
    LorentzIsometry,
    MindOperatorBank,
    MindQualityField,
    MorphogenesisGate,
    MutualRecognitionCoupler,
    OperatorContext,
    ProfunctorTendril,
    PoincareBallBase,
    RecognitionInput,
    RemainderEnvelope,
    ViabilityBounds,
    WorldletState,
    build_hb0,
    teleport_qubit,
    tunnel_two_level,
)


def rec_input(**updates):
    values = dict(
        gluing=0.7,
        useful_update=0.6,
        preserved_difference=0.5,
        absorption_pressure=0.1,
        projection_violence=0.1,
        phase_delta=0.0,
        geometric_distance=0.1,
        gluing_defect=0.1,
        return_fidelity=0.9,
        telos_alignment=0.8,
    )
    values.update(updates)
    return RecognitionInput(**values)


def test_quality_field_has_sixteen_typed_coordinates():
    field = MindQualityField.zero()
    assert len(QUALITY_ORDER) == 16
    assert field.as_array().shape == (16,)
    assert set(field.values) == set(QUALITY_ORDER)


def test_quality_field_refuses_weighted_scalar_collapse():
    with pytest.raises(FlatCollapseError):
        MindQualityField.full().weighted_sum(np.ones(16))


def test_quality_field_uses_partial_order():
    low = MindQualityField.full(0.2)
    high = MindQualityField.full(0.8)
    mixed = high.with_updates({"grounding": 0.1})
    assert high.pareto_relation(low) == "dominates"
    assert mixed.pareto_relation(low) == "incomparable"


def test_quality_field_is_deeply_immutable():
    field = MindQualityField(
        {name: 0.5 for name in QUALITY_ORDER},
        obligations={"grounding": ("retain provenance",)},
        kill_conditions={"grounding": ("kill on missing source",)},
    )
    with pytest.raises(TypeError):
        field.values["grounding"] = float("nan")
    with pytest.raises(TypeError):
        field.obligations["grounding"] = ("changed",)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"period": True, "rate": 1.0},
        {"period": 1, "rate": float("nan")},
        {"period": 1, "rate": float("inf")},
    ],
)
def test_clock_spec_fails_closed_on_nonfinite_or_boolean_parameters(kwargs):
    with pytest.raises(GovernanceError):
        ClockSpec("clock", role="test", **kwargs)


def test_remainders_are_typed_and_measured_ones_need_instruments():
    with pytest.raises(GovernanceError):
        RemainderEnvelope("R", "identity", "x", "M", "bad", magnitude=1.0)
    with pytest.raises(GovernanceError):
        RemainderEnvelope("[R]_id", "identity", "x", "M", "bad", magnitude=1.0)
    rem = RemainderEnvelope(
        "[R]_id", "identity", "x", "M", "gap", instrument="l2", magnitude=1.0
    )
    assert rem.magnitude == 1.0


def test_different_remainder_carriers_cannot_be_subtracted():
    a = RemainderEnvelope(
        "[R]_id", "identity", "x", "M", "gap", instrument="l2", magnitude=1.0
    )
    b = RemainderEnvelope(
        "[R]_transport", "transport", "x", "M", "gap", instrument="l2", magnitude=0.5
    )
    with pytest.raises(CarrierMismatch):
        a.difference(b)


def test_worldlet_poincare_chart_stays_inside_ball():
    world = WorldletState(
        "w", "R2", "poincare_ball", "real", np.array([0.5, 0.0]), ("fast",)
    )
    world.apply_delta(np.array([10.0, 0.0]))
    assert np.linalg.norm(world.coordinates) < 1.0


def test_worldlet_distance_refuses_undeclared_cross_geometry_comparison():
    a = WorldletState("a", "R2", "poincare_ball", "real", np.zeros(2), ("fast",))
    b = WorldletState("b", "R2", "euclidean_control", "real", np.zeros(2), ("fast",))
    with pytest.raises(CarrierMismatch):
        a.distance_to(b)


def test_worldlet_metric_is_finite_immutable_and_comparison_is_symmetric():
    source_metric = np.eye(2)
    left = WorldletState(
        "left", "R2", "riemannian_chart", "real", np.zeros(2), ("fast",),
        metric_tensor=source_metric,
    )
    right = WorldletState(
        "right", "R2", "riemannian_chart", "real", np.ones(2), ("fast",),
        metric_tensor=np.eye(2),
    )
    source_metric[0, 0] = 99.0
    assert left.metric_tensor[0, 0] == 1.0
    with pytest.raises(ValueError):
        left.metric_tensor.setflags(write=True)
    assert left.distance_to(right) == pytest.approx(right.distance_to(left))

    mismatch = WorldletState(
        "mismatch", "R2", "riemannian_chart", "real", np.ones(2), ("fast",),
        metric_tensor=4.0 * np.eye(2),
    )
    with pytest.raises(CarrierMismatch, match="different local metrics"):
        left.distance_to(mismatch)
    with pytest.raises(CarrierMismatch, match="different local metrics"):
        mismatch.distance_to(left)


@pytest.mark.parametrize(
    "metric",
    [
        np.array([[float("nan"), 0.0], [0.0, 1.0]]),
        np.array([[float("inf"), 0.0], [0.0, 1.0]]),
    ],
)
def test_worldlet_metric_rejects_nonfinite_entries(metric):
    with pytest.raises(GovernanceError, match="finite"):
        WorldletState(
            "bad", "R2", "riemannian_chart", "real", np.zeros(2), ("fast",),
            metric_tensor=metric,
        )


def test_worldlet_geometry_variants_do_not_share_one_silent_metric_rule():
    with pytest.raises(GovernanceError, match="induced metric"):
        WorldletState(
            "p", "R2", "poincare_ball", "real", np.zeros(2), ("fast",),
            metric_tensor=np.eye(2),
        )
    with pytest.raises(GovernanceError, match="requires an explicit metric"):
        WorldletState(
            "f", "R2", "fisher_metric", "real", np.zeros(2), ("fast",)
        )
    discrete_a = WorldletState(
        "da", "bits2", "discrete", "symbolic", np.array([0.0, 1.0]), ("fast",)
    )
    discrete_b = WorldletState(
        "db", "bits2", "discrete", "symbolic", np.array([1.0, 1.0]), ("fast",)
    )
    assert discrete_a.distance_to(discrete_a) == 0.0
    assert discrete_a.distance_to(discrete_b) == 1.0
    with pytest.raises(GovernanceError, match="transition relation"):
        discrete_a.apply_delta(np.array([1.0, 0.0]))


def test_worldlet_poincare_distance_is_stable_near_boundary():
    left = WorldletState(
        "left", "R1", "poincare_ball", "real",
        np.array([1.0 - 1e-12]), ("fast",),
    )
    right = WorldletState(
        "right", "R1", "poincare_ball", "real",
        np.array([1.0 - 2e-12]), ("fast",),
    )
    typed_base = PoincareBallBase("local-H1-check", 1)
    assert left.distance_to(right) == pytest.approx(
        typed_base.distance(left.coordinates, right.coordinates),
        rel=1e-12,
    )


def test_worldlet_poincare_delta_uses_exponential_and_fails_atomically():
    world = WorldletState(
        "world", "R2", "poincare_ball", "real", np.array([0.8, 0.0]), ("fast",)
    )
    before = world.coordinates.copy()
    with pytest.raises(GovernanceError):
        world.apply_delta(np.ones(2), rate=float("nan"))
    assert np.array_equal(world.coordinates, before)
    world.apply_delta(np.array([0.01, 0.02]), rate=0.5)
    assert np.linalg.norm(world.coordinates) < 1.0
    assert not np.array_equal(world.coordinates, before + 0.5 * np.array([0.01, 0.02]))


def test_exact_profunctor_round_trip_has_zero_remainder():
    q = np.array([[0.0, -1.0], [1.0, 0.0]])
    chart = ChartFunctor(
        "f", "R2", "R2", lambda x: q @ x, lambda y: q.T @ y,
        ("norm",), ("coordinates",), ()
    )
    obs = ProfunctorTendril("t", "a", "b", chart).transport(np.array([0.2, -0.4]))
    assert obs.remainder.magnitude == pytest.approx(0.0)
    assert obs.fidelity == pytest.approx(1.0)


def test_lossy_profunctor_exposes_round_trip_defect():
    chart = ChartFunctor(
        "f", "R2", "R1", lambda x: x[:1], lambda y: np.array([y[0], 0.0]),
        ("first coordinate",), (), ("second coordinate",)
    )
    obs = ProfunctorTendril("t", "a", "b", chart).transport(np.array([0.2, -0.4]))
    assert obs.remainder.magnitude == pytest.approx(0.4)
    assert obs.fidelity < 1.0


def test_one_way_functor_requires_a_reason():
    with pytest.raises(GovernanceError):
        ChartFunctor("f", "a", "b", lambda x: x, None, (), (), ())


def test_gerbe_identity_witness_has_zero_coherence_defect():
    eye = np.eye(3)
    cell = GerbeCell("g", ("a", "b", "c"), eye, eye, eye, eye)
    assert cell.coherence_defect() == pytest.approx(0.0)
    assert cell.remainder().channel == "coherence"


def test_gerbe_perturbation_is_detected():
    eye = np.eye(2)
    changed = eye.copy()
    changed[0, 0] = 2.0
    cell = GerbeCell("g", ("a", "b", "c"), changed, eye, eye, eye)
    assert cell.coherence_defect() > 0.0


def test_russian_doll_cage_has_paths_and_refuses_cycles():
    root = CosmosCage("root", "cover")
    child = CosmosCage("child", "chart", ("w",))
    root.add_child(child)
    assert root.depth == 2
    assert root.locate("w") == ("root", "child")
    with pytest.raises(GovernanceError):
        child.add_child(root)


def identity_ecology():
    eye = np.eye(2)
    regimes = {
        "self": IdentityRegime("self", np.array([1.0, 0.0]), (eye,), ("w1",)),
        "other": IdentityRegime("other", np.array([0.0, 1.0]), (eye,), ("w2",)),
    }
    exact = ChartFunctor(
        "j", "R2", "R2", lambda x: x.copy(), lambda y: y.copy(),
        ("all",), (), ()
    )
    return IdentityEcology(regimes, {("self", "other"): exact, ("other", "self"): exact})


def test_polyholonomic_identity_fidelity_and_plurality():
    ecology = identity_ecology()
    assert ecology.identity_fidelity() == pytest.approx(1.0)
    assert ecology.plurality() == pytest.approx(1.0)
    assert ecology.fragmentation_risk() == pytest.approx(0.0)


def test_godelian_identity_remainder_is_bounded_instrument_not_closure_claim():
    rem = identity_ecology().godelian_remainder(np.array([1.0, 2.0]), np.array([1.0, 1.0]))
    assert rem.name == "[R]_id"
    assert rem.magnitude == pytest.approx(1.0)
    assert "instrument" in rem.statement


def test_mutual_recognition_rewards_alterity_and_penalises_absorption():
    coupler = MutualRecognitionCoupler()
    healthy = coupler.evaluate(rec_input(), rec_input())
    absorbed = coupler.evaluate(
        rec_input(absorption_pressure=0.95, preserved_difference=0.01),
        rec_input(absorption_pressure=0.95, preserved_difference=0.01),
    )
    assert healthy.mutual_recognition > absorbed.mutual_recognition
    assert healthy.resonance > absorbed.resonance
    assert healthy.preserved_alterity > absorbed.preserved_alterity


def test_mutual_recognition_is_deck_symmetric():
    coupler = MutualRecognitionCoupler()
    ab = rec_input(useful_update=0.8)
    ba = rec_input(useful_update=0.4)
    first = coupler.evaluate(ab, ba)
    second = coupler.evaluate(ba, ab)
    assert first.mutual_recognition == pytest.approx(second.mutual_recognition)
    assert first.resonance == pytest.approx(second.resonance)


def test_mind_operator_bank_emits_all_sixteen_coordinates():
    recognition = MutualRecognitionCoupler().evaluate(rec_input(), rec_input())
    remainder = identity_ecology().godelian_remainder(np.array([1.0]), np.array([0.5]))
    report = MindOperatorBank().evaluate(
        OperatorContext(
            evidence_tag=EvidenceTag.HYPOTHESIS,
            evidence_refs=("manifest",),
            operation=np.array([1.0]),
            self_model=np.array([0.5]),
            identity_remainder=remainder,
            recognition=recognition,
            fast_delta_norm=1.0,
            slow_delta_norm=0.01,
            coverage_gain=1.0,
            information_gain=1.0,
            diversity_gain=1.0,
            compute_cost=1.0,
            integration_completed=4,
            integration_required=4,
            distinct_clocks=3,
            reconstruction_fidelity=0.9,
            typed_remainders=3,
            total_remainders=3,
        )
    )
    assert set(report.field.values) == set(QUALITY_ORDER)
    assert report.field.values["godelian_identity"] == 1.0
    assert report.field.values["adiabatic_patience"] > 0.9


@pytest.mark.parametrize(
    "updates",
    [
        {"coherence_loss": float("nan")},
        {"gluing_defect": float("inf")},
        {"fast_delta_norm": float("nan")},
    ],
)
def test_mind_operator_context_rejects_nonfinite_values_instead_of_rewarding_them(
    updates,
):
    with pytest.raises(GovernanceError):
        OperatorContext(**updates)


@pytest.mark.parametrize(
    "values",
    [
        (float("nan"), 0.0, 0.0, 0.0),
        (0.0, float("inf"), 0.0, 0.0),
        (-1.0, 0.0, 0.0, 0.0),
    ],
)
def test_hamiltonian_envelope_rejects_unknown_or_negative_components(values):
    with pytest.raises(GovernanceError):
        HamiltonianEnvelope(*values)


def test_governor_rejects_nonfinite_sources_and_observations():
    governor = ContactHamiltonianGovernor(ViabilityBounds())
    before = HamiltonianEnvelope(0.0, 0.0, 0.0, 0.0)
    after = HamiltonianEnvelope(1.0, 0.0, 0.0, 0.0)
    observed = {
        "gluing_defect": 0.0,
        "identity_defect": 0.0,
        "absorption": 0.0,
        "compute": 1.0,
        "plurality": 1.0,
        "lob_trap": 0.0,
        "fragmentation": 0.0,
    }
    with pytest.raises(GovernanceError):
        governor.decide(before, after, {"compute": float("nan")}, observed)
    with pytest.raises(GovernanceError):
        governor.decide(
            before,
            after,
            {"compute": 1.0},
            {**observed, "gluing_defect": float("nan")},
        )


def test_adiabatic_controller_separates_three_timescales():
    controller = AdiabaticController()
    state = AdiabaticState(np.zeros(2), np.zeros(2), np.zeros(2))
    out = controller.step(state, np.ones(2), tick=16)
    assert np.linalg.norm(out.fast) > np.linalg.norm(out.meso) > np.linalg.norm(out.slow)


def test_governor_uses_componentwise_budgets_and_viability_region():
    governor = ContactHamiltonianGovernor(ViabilityBounds())
    observed = dict(
        gluing_defect=0.1,
        identity_defect=0.1,
        absorption=0.1,
        compute=2.0,
        plurality=0.8,
        lob_trap=0.0,
        fragmentation=0.1,
    )
    ok = governor.decide(
        HamiltonianEnvelope(1, 0.1, 0.1, 0.1),
        HamiltonianEnvelope(2, 0.1, 0.1, 0.1),
        {"compute": 1.0},
        observed,
    )
    assert ok.accepted
    bad = governor.decide(
        HamiltonianEnvelope(1, 0.1, 0.1, 0.1),
        HamiltonianEnvelope(2, 0.1, 0.1, 0.9),
        {"compute": 1.0, "absorption": 0.8},
        {**observed, "absorption": 0.9},
    )
    assert not bad.accepted
    assert "non_absorption" in bad.reasons


def test_contact_flow_is_not_shape_agnostic():
    governor = ContactHamiltonianGovernor(ViabilityBounds())
    out = governor.contact_flow(np.array([1.0, 0.0]), np.array([0.0, 1.0]), 0.1, 0.0)
    assert out.shape == (2,)
    with pytest.raises(GovernanceError):
        governor.contact_flow(np.ones(3), np.ones(3), 0.1, 0.0)


def test_holoportive_reconstruction_exposes_null_space_remainder():
    boundary_map = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    report = HoloportiveReconstructor.reconstruct(
        boundary_map, np.array([2.0, 3.0]), reference=np.array([2.0, 3.0, 4.0])
    )
    assert report.nullity == 1
    assert report.remainder.magnitude == pytest.approx(4.0)
    assert report.fidelity < 1.0


@pytest.mark.parametrize(
    "state",
    [
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
        np.array([1.0, 1.0]) / math.sqrt(2),
        np.array([1.0, 1.0j]) / math.sqrt(2),
    ],
)
def test_quantum_holoportation_is_exact_but_makes_no_advantage_claim(state):
    report = teleport_qubit(state)
    assert report.average_fidelity == pytest.approx(1.0, abs=1e-12)
    assert sum(branch.probability for branch in report.branches) == pytest.approx(1.0)
    assert report.bell_entropy_bits == pytest.approx(1.0)
    assert report.simulator_only
    assert not report.advantage_claim


def test_tunnelling_toy_model_is_unitary_and_bounded():
    report = tunnel_two_level(np.array([1.0, 0.0]), coupling=1.0, barrier=2.0, duration=0.5)
    assert 0.0 <= report.transfer_probability <= 1.0
    assert report.norm_defect < 1e-12
    assert report.simulator_only and not report.advantage_claim


def test_morphogenesis_requires_persistence_gain_and_low_fragmentation():
    gate = MorphogenesisGate()
    good = gate.decide(0.9, 0.05, 1.0, 0.1)
    assert good.spawn
    bad = gate.decide(0.9, 0.0, 1.0, 0.1)
    assert not bad.spawn
    assert "no_gain_over_width_control" in bad.reasons


def test_hb0_factory_builds_32_worldlets_four_organs_three_clocks_and_nested_cover():
    kernel = build_hb0(seed=5)
    assert len(kernel.worldlets) == 32
    assert len(kernel.organs) == 4
    assert len(kernel.clocks) == 3
    assert kernel.cages.depth == 2
    assert len({w.local_geometry for w in kernel.worldlets.values()}) == 4
    assert len(kernel.identity.regimes) == 4


def test_hb0_step_is_deterministic_and_records_typed_remainders():
    a = build_hb0(seed=7)
    b = build_hb0(seed=7)
    deltas = {wid: np.full(world.dimension, 0.001) for wid, world in a.worldlets.items()}
    ra = a.step(deltas)
    rb = b.step(deltas)
    assert ra.accepted == rb.accepted
    assert [r.magnitude for r in ra.transport_remainders] == pytest.approx(
        [r.magnitude for r in rb.transport_remainders]
    )
    assert all(r.name == "[R]_transport" for r in ra.transport_remainders)
    assert all(r.name == "[R]_coh" for r in ra.coherence_remainders)
    assert len(a.evidence_ledger) == 1


def test_hb0_rolls_back_an_absorptive_move():
    kernel = build_hb0(seed=9)
    before = {wid: w.coordinates.copy() for wid, w in kernel.worldlets.items()}
    target = next(iter(kernel.worldlets))
    report = kernel.step({target: np.ones(kernel.worldlets[target].dimension)}, absorption=0.95)
    assert not report.accepted
    assert "non_absorption" in report.governance_reasons
    for wid, coordinates in before.items():
        assert np.array_equal(kernel.worldlets[wid].coordinates, coordinates)


def test_hb0_step_validation_and_exceptions_are_transactional():
    kernel = build_hb0(seed=91)
    ids = list(kernel.worldlets)
    before = {wid: world.coordinates.copy() for wid, world in kernel.worldlets.items()}
    budget_before = (
        kernel.budget.level,
        kernel.budget.speculative_draw,
        kernel.budget.state,
        tuple(kernel.budget.interventions),
    )
    with pytest.raises(CarrierMismatch):
        kernel.step(
            {
                ids[0]: np.zeros(kernel.worldlets[ids[0]].dimension),
                ids[1]: np.zeros(kernel.worldlets[ids[1]].dimension + 1),
            }
        )
    assert kernel.tick == 0
    assert not kernel.evidence_ledger
    assert all(
        np.array_equal(kernel.worldlets[wid].coordinates, coordinates)
        for wid, coordinates in before.items()
    )
    assert (
        kernel.budget.level,
        kernel.budget.speculative_draw,
        kernel.budget.state,
        tuple(kernel.budget.interventions),
    ) == budget_before

    with pytest.raises(GovernanceError):
        kernel.step({ids[0]: np.zeros(kernel.worldlets[ids[0]].dimension)},
                    absorption=float("nan"))
    assert kernel.tick == 0

    tendril = next(iter(kernel.tendrils.values()))
    original_chart = tendril.chart
    calls = {"count": 0}

    def fail_after_preflight(value):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("synthetic post-mutation transport failure")
        return original_chart.forward(value)

    tendril.chart = replace(original_chart, forward=fail_after_preflight)
    with pytest.raises(RuntimeError, match="post-mutation"):
        kernel.step({ids[0]: np.full(kernel.worldlets[ids[0]].dimension, 0.001)})
    assert kernel.tick == 0
    assert not kernel.evidence_ledger
    assert all(
        np.array_equal(kernel.worldlets[wid].coordinates, coordinates)
        for wid, coordinates in before.items()
    )
    assert (
        kernel.budget.level,
        kernel.budget.speculative_draw,
        kernel.budget.state,
        tuple(kernel.budget.interventions),
    ) == budget_before


def test_hb0_universal_contract_is_immutable_after_construction():
    from aionq.hb0 import EuclideanBaseControl

    kernel = build_hb0(seed=92)
    with pytest.raises(AttributeError, match="immutable universal-base contract"):
        kernel.euclidean_base_control = EuclideanBaseControl(
            "wrong-scale",
            kernel.base.dimension,
            metric_scale=999.0,
        )
    assert kernel.review_universal_base().passed


def test_hb0_constructor_checks_mapping_ids_and_clock_references():
    kernel = build_hb0(seed=93)
    clocks = dict(kernel.clocks)
    clocks["renamed"] = clocks.pop("fast")
    with pytest.raises(GovernanceError, match="mapping keys"):
        replace(kernel, clocks=clocks)

    worldlets = dict(kernel.worldlets)
    worldlet_id = next(iter(worldlets))
    worldlets[worldlet_id] = replace(
        worldlets[worldlet_id],
        clocks=("missing-clock",),
    )
    with pytest.raises(GovernanceError, match="undeclared clocks"):
        replace(kernel, worldlets=worldlets)


def test_hb0_uses_one_universal_hyperbolic_base_without_flattening_local_fibers():
    kernel = build_hb0(seed=11)
    geometries = {w.local_geometry for w in kernel.worldlets.values()}
    assert kernel.base.scope == "universal_atlas"
    assert kernel.base.dimension == 4
    assert kernel.cages.geometry == "dynamic_cover"
    assert all(cage.base_id == kernel.base.id for cage in kernel.cages.walk())
    assert "poincare_ball" in geometries
    assert "euclidean_control" in geometries
    assert len(geometries) > 1
    review = kernel.review_universal_base()
    assert review.passed, review.violations
    assert review.affine_rank == kernel.base.dimension
    assert review.hyperboloid_rank == kernel.base.dimension + 1
    assert kernel.base_distance("W_somatic_00", "W_episodic_00") > 0.0
    with pytest.raises(TypeError):
        kernel.base_points["W_somatic_00"] = np.zeros(kernel.base.dimension)
    with pytest.raises(ValueError):
        kernel.base_points["W_somatic_00"].setflags(write=True)


def test_universal_base_is_n_dimensional_and_not_a_hidden_disk():
    kernel = build_hb0(seed=12, base_dim=6)
    review = kernel.review_universal_base()
    assert review.passed, review.violations
    assert kernel.base.dimension == 6
    assert review.tangent_rank == 6
    assert review.hyperboloid_rank == 7


def test_common_lorentz_transport_preserves_universal_base_review_and_distances():
    kernel = build_hb0(seed=13)
    rapidity = 0.2
    matrix = np.eye(kernel.base.dimension + 1)
    matrix[:2, :2] = np.array(
        [
            [math.cosh(rapidity), math.sinh(rapidity)],
            [math.sinh(rapidity), math.cosh(rapidity)],
        ]
    )
    isometry = LorentzIsometry(matrix)
    moved_points = {
        worldlet_id: kernel.base.from_hyperboloid(
            kernel.base.apply_isometry(
                isometry,
                kernel.base.to_hyperboloid(point),
            )
        )
        for worldlet_id, point in kernel.base_points.items()
    }
    moved = replace(kernel, base_points=moved_points)
    before_review = kernel.review_universal_base()
    after_review = moved.review_universal_base()
    assert after_review.passed, after_review.violations
    assert after_review.tangent_rank == before_review.tangent_rank
    assert after_review.hyperboloid_rank == before_review.hyperboloid_rank
    ids = tuple(kernel.worldlets)
    for left, right in zip(ids[:5], ids[5:10]):
        assert moved.base_distance(left, right) == pytest.approx(
            kernel.base_distance(left, right),
            rel=1e-10,
        )


def test_fiber_motion_does_not_move_base_and_euclidean_control_matches_origin():
    kernel = build_hb0(seed=14)
    left, right = "W_social_00", "W_prospective_00"
    before = kernel.base_distance(left, right)
    kernel.worldlets[left].apply_delta(
        np.full(kernel.worldlets[left].dimension, 0.01),
        rate=1.0,
    )
    assert kernel.base_distance(left, right) == pytest.approx(before)
    assert kernel.euclidean_base_control.metric_tensor == pytest.approx(
        kernel.base.metric_tensor(np.zeros(kernel.base.dimension))
    )
    assert kernel.euclidean_base_distance(left, right) > 0.0


def test_hb0_manifest_passes_strict_validation():
    import json
    from pathlib import Path
    from aionq.hb0 import validate_hb0_manifest

    path = Path(__file__).resolve().parent.parent / "manifests" / "hb0_polycosmic_architecture.json"
    report = validate_hb0_manifest(json.loads(path.read_text()))
    assert report.ok, report.errors
    assert report.checks_run > 100
    assert report.summary["declared_worldlets"] == 32


def test_universal_poincare_axiom_supersedes_without_erasing_k13_retirement():
    from pathlib import Path

    from aionq.evidence import verify

    retired = registry["RET-R3-HYPERBOLIC_BASE"]
    active = registry["AXIOM-HB0-UNIVERSAL_POINCARE_BASE"]
    assert retired.tag == EvidenceTag.RETIRED
    assert active.tag == EvidenceTag.AXIOMATIZED
    assert retired.superseded_by == active.id
    assert active.supersedes == retired.id
    assert "declared, not inferred" in active.surrogate
    envelopes = registry.envelopes(active.id)
    assert len(envelopes) == 1
    root = Path(__file__).resolve().parent.parent
    verification = verify(envelopes[0], repo_root=root)
    assert verification.ok
    assert not verification.independent
    assert active.id not in registry.unwitnessed(
        tags=(EvidenceTag.AXIOMATIZED,)
    )


def test_hb0_manifest_validator_catches_fiber_collapse_base_drift_and_overclaim():
    import json
    from pathlib import Path
    from aionq.hb0 import validate_hb0_manifest

    path = Path(__file__).resolve().parent.parent / "manifests" / "hb0_polycosmic_architecture.json"
    blob = json.loads(path.read_text())
    for worldlet in blob["worldlets"]:
        worldlet["local_geometry"] = "poincare_ball"
    blob["base_geometry"] = "poincare_ball"
    blob["universal_base"]["scope"] = "local_chart"
    blob["quantum_transport"]["advantage_claim"] = True
    report = validate_hb0_manifest(blob)
    assert not report.ok
    assert any("Euclidean" in error for error in report.errors)
    assert any("universal_atlas" in error for error in report.errors)
    assert any("quantum advantage" in error for error in report.errors)
