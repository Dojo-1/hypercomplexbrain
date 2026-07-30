from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

from aionq.cayley_dickson import cd_conjugate, cd_multiply
from aionq.governance import EvidenceTag, GovernanceError
from aionq.hb0 import (
    AlternativeSection,
    CarrierMismatch,
    DecisionGluingTolerance,
    EvidenceBinding,
    FlatCollapseError,
    HamiltonianEnvelope,
    HypercomplexAdiabaticCriterion,
    HypercomplexDecisionField,
    HypercomplexFieldPathSample,
    LorentzIsometry,
    MindQualityField,
    ObservationChannel,
    PoincareBallBase,
    QuaternionFieldChart,
    WallObservation,
    glue_decision_fields,
    trace_hypercomplex_field_path,
)


def base():
    return PoincareBallBase("decision-H2", 2)


def hamiltonian(cost=1.0, credit=1.0):
    return HamiltonianEnvelope(
        compute=cost,
        coherence=cost,
        identity=cost,
        absorption=cost,
        exploration_credit=credit,
        integration_credit=credit,
    )


def section(
    name,
    point,
    quaternion,
    *,
    quality=0.5,
    cost=1.0,
    credit=1.0,
    quality_updates=None,
    evidence=True,
):
    qualities = MindQualityField.full(quality)
    if quality_updates:
        qualities = qualities.with_updates(quality_updates)
    return AlternativeSection(
        id=name,
        base_point=np.asarray(point, dtype=float),
        quaternion=np.asarray(quaternion, dtype=float),
        qualities=qualities,
        hamiltonian=hamiltonian(cost, credit),
        evidence_refs=(
            (
                EvidenceBinding(
                    claim_id="MATH-R1-GRAM_PSD",
                    evidence_tag=EvidenceTag.PROVED,
                    artifact_digest="sha256:" + "0" * 64,
                    verification_mode="kernel_checked",
                ),
            )
            if evidence
            else ()
        ),
    )


def hidden_ternary_field(*, carrier="quaternion:local", order=("a", "b", "c")):
    alternatives = {
        "a": section("a", [0.0, 0.0], [0.0, 0.0, 0.0, 0.0]),
        "b": section("b", [0.2, 0.0], [1.0, 0.0, 0.0, 0.0]),
        "c": section("c", [0.0, 0.2], [2.0, 0.0, 1.0, 0.0]),
    }
    return HypercomplexDecisionField(
        id="ternary",
        carrier=carrier,
        base=base(),
        alternatives=tuple(alternatives[name] for name in order),
        channels=(
            ObservationChannel("real_only", np.diag([1.0, 0.0, 0.0, 0.0])),
        ),
    )


def adiabatic_criterion(**updates):
    values = {
        "parameter_name": "annealing_time",
        "parameter_unit": "s",
        "min_singular_gap": 0.1,
        "max_base_speed": 0.1,
        "max_omega_rate": 0.1,
        "max_quality_speed": 0.1,
        "max_hamiltonian_speed": 0.1,
        "max_fiber_load": 0.1,
        "max_operator_load": 0.1,
        "max_projector_load": 0.1,
    }
    values.update(updates)
    return HypercomplexAdiabaticCriterion(**values)


def test_irreducible_ternary_degeneracy_exists_without_degenerate_edges():
    field = hidden_ternary_field()
    report = field.analyse()
    for first, second in (("a", "b"), ("a", "c"), ("b", "c")):
        edge = field.restrict_binary_face(first, second, "real_only")
        assert not edge.report.degenerate_wall
        assert not edge.global_decision_permitted
    full_cell = report.cells[("a", "b", "c")]
    assert full_cell.intrinsic_rank == 2
    assert full_cell.observed_ranks["real_only"] == 1
    assert full_cell.rank_losses["real_only"] == 1
    assert report.irreducible_degeneracy_cells == (("a", "b", "c"),)
    assert report.binary_faces_insufficient
    witness = full_cell.contrast_witnesses["real_only"][0]
    assert float(np.sum(witness)) == pytest.approx(0.0, abs=1e-12)
    values = np.stack(
        [alternative.quaternion for alternative in field.alternatives]
    )
    hidden_value = values.T @ witness
    assert np.linalg.norm(hidden_value) > 1e-8
    assert np.diag([1.0, 0.0, 0.0, 0.0]) @ hidden_value == pytest.approx(
        np.zeros(4),
        abs=1e-10,
    )


def test_binary_restriction_matches_legacy_wall_but_cannot_govern_cell():
    field = hidden_ternary_field()
    projection = field.restrict_binary_face("a", "b", "real_only")
    manual = WallObservation(
        section_id="manual",
        carrier="edge",
        continue_coordinates=np.zeros(4),
        stop_coordinates=np.array([1.0, 0.0, 0.0, 0.0]),
        metric=np.diag([1.0, 0.0, 0.0, 0.0]),
    ).analyse()
    assert projection.report.degenerate_wall == manual.degenerate_wall
    assert projection.report.intrinsic_gap == pytest.approx(manual.intrinsic_gap)
    assert not projection.global_decision_permitted


def test_binary_hold_cannot_promote_third_when_full_cell_remains_obstructed():
    low = dict(quality=0.2, cost=2.0, credit=0.2)
    field = HypercomplexDecisionField(
        id="third-alternative",
        carrier="quaternion:local",
        base=base(),
        alternatives=(
            section("a", [0.0, 0.0], [0.0, 1.0, 0.0, 0.0], **low),
            section("b", [0.1, 0.0], [0.0, -1.0, 0.0, 0.0], **low),
            section(
                "c",
                [0.0, 0.1],
                [1.0, 0.0, 0.0, 0.0],
                quality=0.9,
                cost=0.5,
                credit=1.0,
            ),
        ),
        channels=(
            ObservationChannel("real_only", np.diag([1.0, 0.0, 0.0, 0.0])),
        ),
    )
    edge = field.restrict_binary_face("a", "b", "real_only")
    report = field.analyse()
    assert edge.report.degenerate_wall
    assert report.status == "PARETO_SINGLETON_CANDIDATE"
    assert report.frontier == ("c",)
    assert report.pareto_projection == ("c",)
    assert "higher_cell_observation_loss" in report.promotion_blockers
    assert "nary_decision_policy_absent" in report.promotion_blockers
    assert not report.global_decision_permitted


def test_three_incomparable_alternatives_remain_an_open_multisection():
    field = HypercomplexDecisionField(
        id="open",
        carrier="quaternion:local",
        base=base(),
        alternatives=(
            section(
                "a",
                [0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                quality_updates={"grounding": 0.9, "self_reflection": 0.1},
            ),
            section(
                "b",
                [0.1, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                quality_updates={"grounding": 0.1, "self_reflection": 0.9},
            ),
            section(
                "c",
                [0.0, 0.1],
                [0.0, 0.0, 1.0, 0.0],
                quality_updates={"mutual_resonance": 0.9, "grounding": 0.2},
            ),
        ),
        channels=(ObservationChannel("full", np.eye(4)),),
    )
    report = field.analyse()
    assert report.status == "OPEN_MULTISECTION"
    assert set(report.frontier) == {"a", "b", "c"}
    assert any(item.name == "[R]_decision_frontier" for item in report.remainders)
    with pytest.raises(FlatCollapseError):
        report.weighted_sum()
    with pytest.raises(FlatCollapseError):
        field.weighted_sum()


def test_quaternion_relations_are_noncommutative_and_ternary_channel_is_real():
    one = np.array([1.0, 0.0, 0.0, 0.0])
    i = np.array([0.0, 1.0, 0.0, 0.0])
    j = np.array([0.0, 0.0, 1.0, 0.0])
    assert cd_multiply(i, j) == pytest.approx(-cd_multiply(j, i))
    field = HypercomplexDecisionField(
        id="quaternion-relations",
        carrier="quaternion:local",
        base=base(),
        alternatives=(
            section("one", [0.0, 0.0], one),
            section("i", [0.1, 0.0], i),
            section("j", [0.0, 0.1], j),
        ),
        channels=(ObservationChannel("full", np.eye(4)),),
    )
    report = field.analyse()
    assert report.quaternion_relations[("i", "j")] == pytest.approx(
        -report.quaternion_relations[("j", "i")]
    )
    omega = report.ternary_omega[("one", "i", "j")]
    assert np.linalg.norm(omega[1:]) > 0.0


def test_degeneracy_is_permutation_invariant_without_erasing_orientation():
    first = hidden_ternary_field(order=("a", "b", "c")).analyse()
    permuted_field = hidden_ternary_field(order=("c", "a", "b"))
    second = permuted_field.analyse()
    first_full = first.cells[("a", "b", "c")]
    second_full = second.cells[("c", "a", "b")]
    assert first_full.rank_losses == second_full.rank_losses
    assert set(first.frontier) == set(second.frontier)


def test_mirror_hyperbolic_triangles_have_same_edges_and_opposite_2_cell():
    shared_quaternions = (
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    )

    def triangle(sign):
        return HypercomplexDecisionField(
            id=f"triangle:{sign}",
            carrier="quaternion:local",
            base=base(),
            alternatives=tuple(
                section(name, point, quaternion)
                for name, point, quaternion in zip(
                    ("a", "b", "c"),
                    ([0.0, 0.0], [0.2, 0.0], [0.0, sign * 0.2]),
                    shared_quaternions,
                )
            ),
            channels=(ObservationChannel("full", np.eye(4)),),
        ).analyse()

    upper = triangle(1.0)
    lower = triangle(-1.0)
    assert sorted(upper.pairwise_base_distances.values()) == pytest.approx(
        sorted(lower.pairwise_base_distances.values())
    )
    upper_orientation = upper.oriented_base_cells[("a", "b", "c")]
    lower_orientation = lower.oriented_base_cells[("a", "b", "c")]
    assert upper_orientation == pytest.approx(-lower_orientation)
    assert upper_orientation != 0.0


def test_h4_base_and_five_alternatives_form_a_nonflat_four_cell():
    h4 = PoincareBallBase("universal-H4-test", 4)
    points = [np.zeros(4)]
    points.extend(0.1 * np.eye(4))
    quaternions = [np.zeros(4)]
    quaternions.extend(np.eye(4))
    field = HypercomplexDecisionField(
        id="five-cell",
        carrier="quaternion:universal-H4",
        base=h4,
        alternatives=tuple(
            section(name, point, quaternion)
            for name, point, quaternion in zip(
                ("a", "b", "c", "d", "e"),
                points,
                quaternions,
            )
        ),
        channels=(ObservationChannel("full", np.eye(4)),),
    )
    report = field.analyse()
    cell = report.cells[("a", "b", "c", "d", "e")]
    assert cell.intrinsic_rank == 4
    assert cell.observed_ranks["full"] == 4
    assert report.oriented_base_cells[("a", "b", "c", "d", "e")] != 0.0


def test_quaternion_and_base_transport_preserve_full_cell_invariants():
    field = hidden_ternary_field()
    angle = 0.3
    unit = np.array([math.cos(angle), math.sin(angle), 0.0, 0.0])
    rapidity = 0.2
    boost = LorentzIsometry(
        np.array(
            [
                [math.cosh(rapidity), math.sinh(rapidity), 0.0],
                [math.sinh(rapidity), math.cosh(rapidity), 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
    )
    chart = QuaternionFieldChart(
        "quaternion:local",
        "quaternion:atlas",
        unit,
        base_isometry=boost,
    )
    transported = chart.transport(field)
    local_report = field.analyse()
    atlas_report = transported.analyse()
    assert local_report.cells[("a", "b", "c")].rank_losses == (
        atlas_report.cells[("a", "b", "c")].rank_losses
    )
    assert local_report.pairwise_base_distances == pytest.approx(
        atlas_report.pairwise_base_distances
    )
    for pair, relation in local_report.quaternion_relations.items():
        expected = cd_multiply(
            cd_multiply(unit, relation),
            cd_conjugate(unit),
        )
        assert atlas_report.quaternion_relations[pair] == pytest.approx(expected)


def test_complete_field_gluing_uses_all_channels_and_exposes_failed_fiber():
    atlas = hidden_ternary_field(carrier="quaternion:atlas")
    angle = 0.4
    unit = np.array([math.cos(angle), math.sin(angle), 0.0, 0.0])
    inverse = np.array([unit[0], -unit[1], -unit[2], -unit[3]])
    local = QuaternionFieldChart(
        "quaternion:atlas",
        "quaternion:local",
        inverse,
    ).transport(atlas)
    report = glue_decision_fields(
        {"atlas": atlas, "local": local},
        {
            "atlas": QuaternionFieldChart(
                "quaternion:atlas",
                "quaternion:atlas",
                np.array([1.0, 0.0, 0.0, 0.0]),
            ),
            "local": QuaternionFieldChart(
                "quaternion:local",
                "quaternion:atlas",
                unit,
            ),
        },
    )
    assert report.glued
    assert all(report.channel_gates.values())
    assert not report.remainders

    changed_alternatives = list(local.alternatives)
    changed = changed_alternatives[0]
    changed_alternatives[0] = AlternativeSection(
        id=changed.id,
        base_point=changed.base_point,
        quaternion=changed.quaternion + np.array([0.0, 0.1, 0.0, 0.0]),
        qualities=changed.qualities,
        hamiltonian=changed.hamiltonian,
        evidence_refs=changed.evidence_refs,
    )
    perturbed = HypercomplexDecisionField(
        id=local.id,
        carrier=local.carrier,
        base=local.base,
        alternatives=tuple(changed_alternatives),
        channels=local.channels,
    )
    failed = glue_decision_fields(
        {"atlas": atlas, "local": perturbed},
        {
            "atlas": QuaternionFieldChart(
                "quaternion:atlas",
                "quaternion:atlas",
                np.array([1.0, 0.0, 0.0, 0.0]),
            ),
            "local": QuaternionFieldChart(
                "quaternion:local",
                "quaternion:atlas",
                unit,
            ),
        },
    )
    assert not failed.glued
    assert not failed.channel_gates["fiber"]
    assert any(
        remainder.carrier.endswith(":fiber") for remainder in failed.remainders
    )


def test_fail_closed_guards_reject_binary_field_octonion_chart_and_missing_evidence():
    alternatives = (
        section("a", [0.0, 0.0], [1.0, 0.0, 0.0, 0.0], evidence=False),
        section("b", [0.1, 0.0], [0.0, 1.0, 0.0, 0.0], evidence=False),
        section("c", [0.0, 0.1], [0.0, 0.0, 1.0, 0.0], evidence=False),
    )
    field = HypercomplexDecisionField(
        "no-evidence",
        "quaternion:local",
        base(),
        alternatives,
        (ObservationChannel("full", np.eye(4)),),
    )
    report = field.analyse()
    assert report.status == "OPEN_MULTISECTION"
    assert set(report.frontier) == {"a", "b", "c"}
    assert set(report.ineligible_ids) == {"a", "b", "c"}
    assert "unbound_evidence" in report.promotion_blockers
    assert not report.global_decision_permitted
    with pytest.raises(GovernanceError):
        HypercomplexDecisionField(
            "binary",
            "quaternion:local",
            base(),
            alternatives[:2],
            (ObservationChannel("full", np.eye(4)),),
        )
    with pytest.raises(CarrierMismatch):
        QuaternionFieldChart(
            "quaternion:local",
            "quaternion:atlas",
            np.ones(8) / math.sqrt(8.0),
        )


def test_blind_higher_cell_blocks_a_unique_pairwise_pareto_projection():
    field = HypercomplexDecisionField(
        "blind-promotion",
        "quaternion:local",
        base(),
        (
            section(
                "a",
                [0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
                quality=0.9,
                cost=0.2,
                credit=1.0,
            ),
            section(
                "b",
                [0.1, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                quality=0.2,
                cost=2.0,
                credit=0.1,
            ),
            section(
                "c",
                [0.0, 0.1],
                [0.0, 1.0, 0.0, 0.0],
                quality=0.1,
                cost=3.0,
                credit=0.0,
            ),
        ),
        (ObservationChannel("blind", np.zeros((1, 4))),),
    )
    report = field.analyse()
    assert report.pareto_projection == ("a",)
    assert report.status == "PARETO_SINGLETON_CANDIDATE"
    assert "higher_cell_observation_loss" in report.promotion_blockers
    assert not report.global_decision_permitted


def test_all_fin_n_sectors_are_preserved_with_reconstruction_and_parseval_checks():
    report = hidden_ternary_field().analyse()
    assert report.sector_order == ("a", "b", "c")
    assert set(report.sector_coefficients) == {0, 1, 2}
    assert set(report.observed_sector_coefficients["real_only"]) == {0, 1, 2}
    assert report.sector_reconstruction_defect < 1e-12
    assert report.sector_parseval_defect < 1e-12


def test_h4_ternary_base_cell_keeps_exterior_data_not_only_edges():
    h4 = PoincareBallBase("ternary-H4", 4)
    quaternions = (
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    )

    def field(sign):
        return HypercomplexDecisionField(
            f"h4-triangle:{sign}",
            "quaternion:H4",
            h4,
            tuple(
                section(name, point, quaternion)
                for name, point, quaternion in zip(
                    ("a", "b", "c"),
                    (
                        [0.0, 0.0, 0.0, 0.0],
                        [0.2, 0.0, 0.0, 0.0],
                        [0.0, sign * 0.2, 0.0, 0.0],
                    ),
                    quaternions,
                )
            ),
            (ObservationChannel("full", np.eye(4)),),
        )

    positive = field(1.0).analyse()
    negative = field(-1.0).analyse()
    assert positive.oriented_base_cells == {}
    assert ("a", "b", "c") in positive.base_exterior_cells
    assert positive.pairwise_base_distances == pytest.approx(
        negative.pairwise_base_distances
    )
    assert not np.allclose(
        positive.base_exterior_cells[("a", "b", "c")],
        negative.base_exterior_cells[("a", "b", "c")],
    )


def test_hypercomplex_change_cannot_silently_become_the_same_global_promotion():
    low = dict(quality=0.2, cost=2.0, credit=0.1)

    def field(scale, mirror):
        return HypercomplexDecisionField(
            f"metamorphic:{scale}:{mirror}",
            "quaternion:local",
            base(),
            (
                section(
                    "a", [0.0, 0.0], [1.0, scale, 0.0, 0.0],
                    quality=0.9, cost=0.2, credit=1.0,
                ),
                section("b", [0.2, 0.0], [0.0, 1.0, scale, 0.0], **low),
                section("c", [0.0, mirror * 0.2], [0.0, 0.0, 1.0, scale], **low),
            ),
            (ObservationChannel("full", np.eye(4)),),
        )

    first = field(1.0, 1.0).analyse()
    second = field(100.0, -1.0).analyse()
    assert first.pareto_projection == second.pareto_projection == ("a",)
    assert first.status == second.status == "PARETO_SINGLETON_CANDIDATE"
    assert not first.global_decision_permitted
    assert not second.global_decision_permitted
    assert not np.allclose(
        first.ternary_omega[("a", "b", "c")],
        second.ternary_omega[("a", "b", "c")],
    )
    assert "nary_decision_policy_absent" in first.promotion_blockers


def test_six_alternatives_expose_intrinsic_r4_collapse():
    h4 = PoincareBallBase("six-alternative-H4", 4)
    points = (
        [0.0, 0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0, 0.0],
        [0.0, 0.1, 0.0, 0.0],
        [0.0, 0.0, 0.1, 0.0],
        [0.0, 0.0, 0.0, 0.1],
        [0.05, 0.05, 0.05, 0.05],
    )
    alternatives = tuple(
        section(
            str(index),
            point,
            np.eye(4)[index % 4],
            quality=(0.9 if index == 0 else 0.2),
            cost=(0.2 if index == 0 else 2.0),
            credit=(1.0 if index == 0 else 0.1),
        )
        for index, point in enumerate(points)
    )
    report = HypercomplexDecisionField(
        "six",
        "quaternion:H4",
        h4,
        alternatives,
        (ObservationChannel("full", np.eye(4)),),
    ).analyse()
    full_cell = tuple(str(index) for index in range(6))
    assert report.cells[full_cell].intrinsic_nullity >= 1
    assert full_cell in report.intrinsic_collapses
    assert "intrinsic_quaternion_carrier_collapse" in report.promotion_blockers
    assert any(
        remainder.name == "[R]_intrinsic_cell_collapse"
        for remainder in report.remainders
    )
    assert not report.global_decision_permitted


def test_irreducible_degeneracy_is_indexed_by_cell_and_channel():
    field = HypercomplexDecisionField(
        "multi-channel",
        "quaternion:local",
        base(),
        hidden_ternary_field().alternatives,
        (
            ObservationChannel(
                "real_only",
                np.diag([1.0, 0.0, 0.0, 0.0]),
            ),
            ObservationChannel("blind", np.zeros((1, 4))),
        ),
    )
    report = field.analyse()
    assert (("a", "b", "c"), "real_only") in report.irreducible_degeneracies
    assert (("a", "b", "c"), "blind") not in report.irreducible_degeneracies
    assert report.binary_faces_insufficient


def test_action_wall_is_a_true_projector_and_amplifying_channels_are_rejected():
    with pytest.raises(GovernanceError):
        ObservationChannel(
            "amplifying",
            np.diag([1.0, 1e12, 0.0, 0.0]),
        )
    report = hidden_ternary_field().analyse()
    for cell in report.cells.values():
        for channel, projector in cell.action_wall_projectors.items():
            assert projector == pytest.approx(projector.T)
            assert projector @ projector == pytest.approx(projector, abs=1e-10)
            assert float(np.min(np.linalg.eigvalsh(projector))) >= -1e-10
            assert len(cell.contrast_witnesses[channel]) == cell.rank_losses[channel]


def test_typed_evidence_rejects_arbitrary_strings():
    with pytest.raises(GovernanceError):
        AlternativeSection(
            id="untyped-evidence",
            base_point=np.zeros(2),
            quaternion=np.zeros(4),
            qualities=MindQualityField.full(0.5),
            hamiltonian=hamiltonian(),
            evidence_refs=("not-a-verified-envelope",),
        )


def test_gluing_is_permutation_equivariant_bounded_and_checks_quality_policy():
    atlas = hidden_ternary_field(
        carrier="quaternion:atlas",
        order=("a", "b", "c"),
    )
    permuted = HypercomplexDecisionField(
        atlas.id,
        "quaternion:local",
        atlas.base,
        tuple(atlas._alternative_map()[name] for name in ("c", "a", "b")),
        atlas.channels,
    )
    identity_atlas = QuaternionFieldChart(
        "quaternion:atlas",
        "quaternion:atlas",
        np.array([1.0, 0.0, 0.0, 0.0]),
    )
    identity_local = QuaternionFieldChart(
        "quaternion:local",
        "quaternion:atlas",
        np.array([1.0, 0.0, 0.0, 0.0]),
    )
    glued = glue_decision_fields(
        {"atlas": atlas, "permuted": permuted},
        {"atlas": identity_atlas, "permuted": identity_local},
    )
    assert glued.glued

    changed = list(permuted.alternatives)
    changed[0] = replace(
        changed[0],
        qualities=replace(
            changed[0].qualities,
            obligations={"grounding": ("preserve-policy",)},
        ),
    )
    policy_drift = replace(permuted, alternatives=tuple(changed))
    failed = glue_decision_fields(
        {"atlas": atlas, "permuted": policy_drift},
        {"atlas": identity_atlas, "permuted": identity_local},
    )
    assert not failed.glued
    assert not failed.channel_gates["quality_policy"]
    with pytest.raises(GovernanceError):
        bad_tolerances = DecisionGluingTolerance(base_distance=-1.0)
        glue_decision_fields(
            {"atlas": atlas, "permuted": permuted},
            {"atlas": identity_atlas, "permuted": identity_local},
            tolerances=bad_tolerances,
        )
    with pytest.raises(GovernanceError):
        glue_decision_fields({"atlas": atlas}, {"atlas": identity_atlas})


def test_gluing_tolerances_are_channel_typed_and_triple_cocycle_is_checked():
    atlas = hidden_ternary_field(carrier="quaternion:atlas")
    fields = {
        "a": atlas,
        "b": replace(atlas, carrier="quaternion:b"),
        "c": replace(atlas, carrier="quaternion:c"),
    }
    charts = {
        "a": QuaternionFieldChart(
            "quaternion:atlas", "quaternion:atlas", np.array([1.0, 0.0, 0.0, 0.0])
        ),
        "b": QuaternionFieldChart(
            "quaternion:b", "quaternion:atlas", np.array([1.0, 0.0, 0.0, 0.0])
        ),
        "c": QuaternionFieldChart(
            "quaternion:c", "quaternion:atlas", np.array([1.0, 0.0, 0.0, 0.0])
        ),
    }
    report = glue_decision_fields(fields, charts)
    assert report.glued
    assert report.triple_cocycle_defects[("a", "b", "c")] < 1e-12

    changed = list(fields["b"].alternatives)
    changed[0] = replace(
        changed[0],
        qualities=changed[0].qualities.with_updates({"grounding": 0.5001}),
    )
    fields["b"] = replace(fields["b"], alternatives=tuple(changed))
    strict_quality = glue_decision_fields(
        fields,
        charts,
        tolerances=DecisionGluingTolerance(fiber_norm=1.0),
    )
    assert not strict_quality.channel_gates["qualities"]
    assert strict_quality.channel_gates["fiber"]


def test_binary_edge_label_is_covariant_but_never_globally_promotable():
    field = hidden_ternary_field()
    local = field.restrict_binary_face("a", "b", "real_only")
    chart = QuaternionFieldChart(
        "quaternion:local",
        "quaternion:atlas",
        np.array([-1.0, 0.0, 0.0, 0.0]),
    )
    transported = chart.transport(field).restrict_binary_face(
        "a",
        "b",
        "real_only",
    )
    assert local.report.decision == transported.report.decision
    assert not local.global_decision_permitted
    assert not transported.global_decision_permitted


def test_nary_adiabatic_path_uses_rates_gaps_and_no_binary_label():
    initial = HypercomplexDecisionField(
        "adiabatic",
        "quaternion:local",
        base(),
        (
            section("a", [0.0, 0.0], [0.0, 0.0, 0.0, 0.0]),
            section("b", [0.1, 0.0], [1.0, 0.0, 0.0, 0.0]),
            section("c", [0.0, 0.1], [0.0, 1.0, 0.0, 0.0]),
        ),
        (ObservationChannel("full", np.eye(4)),),
    )
    changed = list(initial.alternatives)
    changed[2] = replace(
        changed[2],
        quaternion=np.array([0.0, 1.01, 0.0, 0.0]),
    )
    final = replace(initial, alternatives=tuple(changed))
    slow = trace_hypercomplex_field_path(
        (
            HypercomplexFieldPathSample(0.0, initial),
            HypercomplexFieldPathSample(100.0, final),
        ),
        adiabatic_criterion(),
    )
    assert slow.adiabatic_certified_under_policy
    assert not hasattr(slow, "decision")
    fast = trace_hypercomplex_field_path(
        (
            HypercomplexFieldPathSample(0.0, initial),
            HypercomplexFieldPathSample(0.001, final),
        ),
        adiabatic_criterion(),
    )
    assert not fast.adiabatic_certified_under_policy
    assert any("fiber_load" in violation for violation in fast.violations)


def test_adiabatic_path_rejects_rank_and_frontier_topology_changes():
    initial = HypercomplexDecisionField(
        "topology",
        "quaternion:local",
        base(),
        (
            section("a", [0.0, 0.0], [0.0, 0.0, 0.0, 0.0]),
            section("b", [0.1, 0.0], [1.0, 0.0, 0.0, 0.0]),
            section("c", [0.0, 0.1], [0.0, 1.0, 0.0, 0.0]),
        ),
        (ObservationChannel("full", np.eye(4)),),
    )
    rank_changed = list(initial.alternatives)
    rank_changed[2] = replace(
        rank_changed[2],
        quaternion=np.array([2.0, 0.0, 0.0, 0.0]),
    )
    rank_report = trace_hypercomplex_field_path(
        (
            HypercomplexFieldPathSample(0.0, initial),
            HypercomplexFieldPathSample(
                100.0,
                replace(initial, alternatives=tuple(rank_changed)),
            ),
        ),
        adiabatic_criterion(max_fiber_load=10.0, max_omega_rate=10.0),
    )
    assert not rank_report.adiabatic_certified_under_policy
    assert rank_report.intrinsic_ranks == (2, 1)
    assert "intrinsic_rank_constant_exceeds_bound" in rank_report.violations

    first = replace(
        initial,
        alternatives=(
            section(
                "a",
                [0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
                quality=0.9,
                cost=0.2,
                credit=1.0,
            ),
            section(
                "b",
                [0.1, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                quality=0.1,
                cost=2.0,
                credit=0.1,
            ),
            section(
                "c",
                [0.0, 0.1],
                [0.0, 1.0, 0.0, 0.0],
                quality=0.1,
                cost=2.0,
                credit=0.1,
            ),
        ),
    )
    second = replace(
        first,
        alternatives=(
            section(
                "a",
                [0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
                quality=0.1,
                cost=2.0,
                credit=0.1,
            ),
            section(
                "b",
                [0.1, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                quality=0.9,
                cost=0.2,
                credit=1.0,
            ),
            section(
                "c",
                [0.0, 0.1],
                [0.0, 1.0, 0.0, 0.0],
                quality=0.1,
                cost=2.0,
                credit=0.1,
            ),
        ),
    )
    frontier_report = trace_hypercomplex_field_path(
        (
            HypercomplexFieldPathSample(0.0, first),
            HypercomplexFieldPathSample(100.0, second),
        ),
        adiabatic_criterion(),
    )
    assert not frontier_report.adiabatic_certified_under_policy
    assert frontier_report.frontiers == (("a",), ("b",))
    assert not frontier_report.frontier_stable
