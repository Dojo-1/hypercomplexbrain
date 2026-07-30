"""QB2 tests for the positive-chiral H4 spin connection."""

from __future__ import annotations

import builtins
from dataclasses import fields, replace
import math

import numpy as np
import pytest

from aionq.governance import EvidenceTag, GovernanceError
from aionq.hb0.chiral_spin import (
    ChiralSpinConnection,
    ChiralSpinLink,
    QiskitProjectionUnavailable,
    SectionalAcceleratorBoundary,
    probe_central_lift_qiskit,
    project_spin_path_to_qiskit,
    spinor_preparation_unitary,
)
from aionq.hb0.core import CarrierMismatch
from aionq.hb0.quantum_base import (
    HyperbolicQuantumBase,
    quantum_root_fidelity,
    quantum_trace_distance,
)
from aionq.hyperbolic import PoincareBallBase


CONNECTION = ChiralSpinConnection()
SECTIONAL = SectionalAcceleratorBoundary()
IDENTITY2 = np.eye(2, dtype=complex)
IDENTITY_PATH = CONNECTION.path((np.zeros(4), np.zeros(4)))


class ForgedLink(ChiralSpinLink):
    """Adversarial subtype that deliberately suppresses parent validation."""

    def __post_init__(self) -> None:
        pass


@pytest.mark.parametrize(
    "source,target",
    [
        (
            np.array([0.10, 0.05, 0.00, 0.00]),
            np.array([0.00, 0.12, 0.03, 0.00]),
        ),
        (
            np.array([-0.21, 0.07, 0.05, 0.10]),
            np.array([0.13, -0.09, 0.11, 0.04]),
        ),
        (
            np.array([0.50, 0.10, -0.05, 0.02]),
            np.array([-0.20, 0.35, 0.04, -0.08]),
        ),
    ],
)
def test_closed_form_link_matches_independent_levi_civita_frame(source, target):
    link = CONNECTION.link(source, target)
    assert link.passed
    assert link.tangent_rotation.T @ link.tangent_rotation == pytest.approx(
        np.eye(4),
        abs=1e-12,
    )
    assert np.linalg.det(link.tangent_rotation) == pytest.approx(1.0, abs=1e-12)
    assert link.unitary.conj().T @ link.unitary == pytest.approx(
        IDENTITY2,
        abs=1e-12,
    )
    assert np.linalg.det(link.unitary) == pytest.approx(1.0, abs=1e-12)
    assert link.spin_intertwining_defect < 1e-12
    assert link.scalar_part > 0.0


def test_same_point_and_radial_geodesics_have_identity_spin_link():
    point = np.array([0.20, -0.10, 0.05, 0.02])
    assert CONNECTION.link(point, point).unitary == pytest.approx(IDENTITY2)
    radial = np.array([0.35, 0.0, 0.0, 0.0])
    assert CONNECTION.link(np.zeros(4), radial).unitary == pytest.approx(IDENTITY2)
    assert CONNECTION.link(0.2 * radial, radial).unitary == pytest.approx(
        IDENTITY2
    )


def test_reverse_edge_is_the_continuously_signed_adjoint():
    source = np.array([0.17, -0.04, 0.08, 0.03])
    target = np.array([-0.06, 0.19, 0.02, -0.07])
    forward = CONNECTION.link(source, target).unitary
    reverse = CONNECTION.link(target, source).unitary
    assert reverse == pytest.approx(forward.conj().T, abs=1e-12)
    assert reverse @ forward == pytest.approx(IDENTITY2, abs=1e-12)


def test_link_arrays_are_immutable():
    link = CONNECTION.link(
        np.array([0.1, 0.0, 0.0, 0.0]),
        np.array([0.0, 0.1, 0.0, 0.0]),
    )
    with pytest.raises(ValueError):
        link.unitary[0, 0] = 0.0
    with pytest.raises(ValueError):
        link.tangent_rotation[0, 0] = 0.0


def test_public_link_cannot_hide_an_anti_chiral_frame_rotation():
    link = CONNECTION.link(np.zeros(4), np.zeros(4))
    with pytest.raises(GovernanceError):
        replace(
            link,
            tangent_rotation=-np.eye(4),
            tangent_orthogonality_defect=0.0,
            tangent_determinant_defect=0.0,
            spin_intertwining_defect=0.0,
        )


def test_public_link_cannot_rename_or_rescale_the_universal_h4_base():
    link = CONNECTION.link(np.zeros(4), np.zeros(4))
    with pytest.raises(CarrierMismatch):
        replace(link, base_id="renamed-H4")
    with pytest.raises(CarrierMismatch):
        replace(link, curvature_radius=2.0)


def test_unvalidated_link_subclass_is_not_a_typed_carrier():
    valid = CONNECTION.link(np.zeros(4), np.zeros(4))
    payload = {
        field.name: getattr(valid, field.name)
        for field in fields(ChiralSpinLink)
    }
    payload["unitary"] = -IDENTITY2
    forged = ForgedLink(**payload)
    assert isinstance(forged, ChiralSpinLink)
    assert type(forged) is not ChiralSpinLink

    with pytest.raises(CarrierMismatch):
        replace(IDENTITY_PATH, links=(forged,))
    with pytest.raises(CarrierMismatch):
        project_spin_path_to_qiskit(forged)
    with pytest.raises(CarrierMismatch):
        project_spin_path_to_qiskit((forged,))

    receipt = project_spin_path_to_qiskit(IDENTITY_PATH)
    with pytest.raises(CarrierMismatch):
        replace(receipt, links=(forged,))


@pytest.mark.parametrize(
    "base",
    [
        PoincareBallBase(id="wrong-H3", dimension=3),
        PoincareBallBase(
            id="other-H4",
            dimension=4,
            sectional_curvature=-0.25,
        ),
        PoincareBallBase(
            id="renamed-H4",
            dimension=4,
            sectional_curvature=-1.0,
        ),
    ],
)
def test_chiral_objects_require_the_exact_universal_h4_base(base):
    with pytest.raises(CarrierMismatch):
        ChiralSpinConnection(base=base)
    with pytest.raises(CarrierMismatch):
        SectionalAcceleratorBoundary(base=base)


def test_open_ball_boundary_is_rejected_not_clipped():
    with pytest.raises(GovernanceError):
        CONNECTION.link(np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(4))


def test_path_product_order_is_last_link_on_the_left():
    points = (
        np.array([0.11, 0.02, 0.00, 0.00]),
        np.array([0.00, 0.13, 0.03, 0.00]),
        np.array([0.02, 0.00, 0.16, 0.04]),
    )
    report = CONNECTION.path(points)
    expected = report.links[1].unitary @ report.links[0].unitary
    reversed_order = report.links[0].unitary @ report.links[1].unitary
    assert report.unitary == pytest.approx(expected, abs=1e-12)
    assert np.linalg.norm(expected - reversed_order, ord="fro") > 1e-5
    assert not report.is_loop


def test_public_path_report_recomputes_links_unitary_and_diagnostics():
    path = CONNECTION.path(
        (
            np.zeros(4),
            np.array([0.1, 0.0, 0.0, 0.0]),
            np.array([0.0, 0.1, 0.0, 0.0]),
        )
    )
    with pytest.raises(GovernanceError):
        replace(path, unitary=np.full((2, 2), np.nan))
    with pytest.raises(GovernanceError):
        replace(path, signed_half_trace=path.signed_half_trace + 0.1)
    with pytest.raises(CarrierMismatch):
        replace(path, links=(path.links[1], path.links[0]))


def test_loop_requires_three_edges_and_closed_endpoints():
    with pytest.raises(GovernanceError):
        CONNECTION.loop((np.zeros(4), np.array([0.1, 0.0, 0.0, 0.0])))
    with pytest.raises(GovernanceError):
        CONNECTION.loop(
            (
                np.zeros(4),
                np.array([0.1, 0.0, 0.0, 0.0]),
                np.array([0.0, 0.1, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.1, 0.0]),
            )
        )


def test_public_holonomy_curvature_and_triangle_reports_recompute():
    holonomy = CONNECTION.loop(
        (
            np.zeros(4),
            np.array([0.1, 0.0, 0.0, 0.0]),
            np.array([0.0, 0.1, 0.0, 0.0]),
            np.zeros(4),
        )
    )
    with pytest.raises(GovernanceError):
        replace(holonomy, flat_control_unitary=-IDENTITY2)
    span = CONNECTION.curvature_span()
    with pytest.raises(GovernanceError):
        replace(span, rank=2)
    triangle = CONNECTION.triangle_curvature(0.2)
    with pytest.raises(GovernanceError):
        replace(triangle, hyperbolic_area=-1.0)
    with pytest.raises(GovernanceError):
        replace(triangle, expected_unitary=-triangle.expected_unitary)


def test_spinor_and_density_transport_preserve_fiber_invariants():
    source = np.array([0.12, -0.03, 0.04, 0.00])
    target = np.array([-0.05, 0.18, 0.00, 0.06])
    spinor = np.array([math.sqrt(0.3), 1.0j * math.sqrt(0.7)])
    density = np.outer(spinor, spinor.conj())
    moved_spinor = CONNECTION.transport_spinor(source, target, spinor)
    moved_density = CONNECTION.transport_density(source, target, density)
    assert np.linalg.norm(moved_spinor) == pytest.approx(1.0)
    assert moved_density == pytest.approx(
        np.outer(moved_spinor, moved_spinor.conj()),
        abs=1e-12,
    )
    assert np.linalg.eigvalsh(moved_density) == pytest.approx(
        np.linalg.eigvalsh(density),
        abs=1e-12,
    )
    assert np.trace(moved_density) == pytest.approx(1.0)


def test_spin_transport_rejects_wrong_density_carrier():
    with pytest.raises(CarrierMismatch):
        CONNECTION.transport_density(np.zeros(4), np.zeros(4), np.eye(3) / 3.0)
    with pytest.raises(CarrierMismatch):
        CONNECTION.transport_qutrit_density(
            np.zeros(4),
            np.zeros(4),
            np.eye(2) / 2.0,
        )


def test_spin_transport_does_not_silently_symmetrise_accepted_input():
    density = np.array(
        [
            [0.5, 0.1 + 1e-12j],
            [0.1, 0.5],
        ],
        dtype=complex,
    )
    moved = CONNECTION.transport_density(np.zeros(4), np.zeros(4), density)
    assert np.array_equal(moved, density)


def test_qb1_qutrit_lift_preserves_radial_flag_and_spectrum():
    quantum_base = HyperbolicQuantumBase()
    source = np.array([0.16, -0.07, 0.03, 0.02])
    target = np.array([-0.04, 0.19, 0.06, 0.01])
    density = quantum_base.encode(source).density
    moved = CONNECTION.transport_qutrit_density(source, target, density)
    assert moved[0, 0] == pytest.approx(density[0, 0], abs=1e-12)
    assert np.trace(moved[1:, 1:]) == pytest.approx(
        np.trace(density[1:, 1:]),
        abs=1e-12,
    )
    assert np.linalg.eigvalsh(moved) == pytest.approx(
        np.linalg.eigvalsh(density),
        abs=1e-12,
    )
    # A transported fiber state is not silently identified with QB1's separate
    # canonical endpoint encoding.
    assert np.linalg.norm(
        moved - quantum_base.encode(target).density,
        ord="fro",
    ) > 1e-3


@pytest.mark.parametrize("epsilon", [0.05, 0.2, 0.55])
def test_exact_h4_triangle_curvature_and_flat_control(epsilon):
    report = CONNECTION.triangle_curvature(epsilon)
    angle = math.atan(epsilon * epsilon)
    assert report.unitary_defect < 1e-12
    assert report.hyperbolic_area == pytest.approx(
        2.0 * CONNECTION.base.radius_squared * angle
    )
    assert report.spin_rotation_angle == pytest.approx(-2.0 * angle)
    assert report.area_rotation_defect == pytest.approx(0.0, abs=1e-15)
    assert report.holonomy.flat_control_unitary == pytest.approx(IDENTITY2)
    assert report.holonomy.flat_control_identity_distance == 0.0
    assert report.holonomy.path.identity_distance > 0.0


@pytest.mark.parametrize("epsilon", [0.04, 0.25, 0.7])
def test_triangle_density_probe_formula_and_blind_axis(epsilon):
    report = CONNECTION.triangle_curvature(epsilon)
    assert report.plus_x_trace_distance == pytest.approx(
        epsilon * epsilon / math.sqrt(1.0 + epsilon**4),
        abs=1e-12,
    )
    assert report.plus_x_root_fidelity == pytest.approx(
        1.0 / math.sqrt(1.0 + epsilon**4),
        abs=1e-12,
    )
    assert report.sigma3_blind_trace_distance == pytest.approx(0.0, abs=1e-12)


def test_density_conjugation_cannot_see_the_central_spin_sign():
    density = 0.5 * np.array([[1.0, 1.0], [1.0, 1.0]], dtype=complex)
    plus = IDENTITY2 @ density @ IDENTITY2
    minus = (-IDENTITY2) @ density @ (-IDENTITY2).conj().T
    assert quantum_trace_distance(plus, minus) == pytest.approx(0.0)
    assert quantum_root_fidelity(plus, minus) == pytest.approx(1.0)


def test_omitted_negative_chirality_remains_explicit():
    loop = CONNECTION.loop(
        (
            np.zeros(4),
            np.array([0.1, 0.0, 0.0, 0.0]),
            np.array([0.0, 0.1, 0.0, 0.0]),
            np.zeros(4),
        )
    )
    remainder = loop.omitted_chirality
    assert remainder.name == "[R]_negative_chirality"
    assert remainder.evidence_tag == EvidenceTag.SEMANTIC
    assert "SU(2)-" in remainder.carrier


def test_positive_chiral_curvature_span_has_rank_three():
    report = CONNECTION.curvature_span()
    assert report.rank == 3
    assert len(report.planes) == 6
    assert report.curvature_components.shape == (3, 6)
    assert report.singular_values == pytest.approx(
        np.full(3, math.sqrt(2.0) / CONNECTION.base.radius_squared),
        abs=1e-12,
    )


def test_generation_100_geodesic_refinement_preserves_signed_link():
    source = np.array([0.14, -0.06, 0.02, 0.03])
    target = np.array([-0.08, 0.17, 0.07, -0.04])
    report = SECTIONAL.refine(CONNECTION, source, target, sections=100)
    assert report.sections == 100
    assert report.passed
    assert report.composition_defect < 1e-12
    assert report.maximum_segment_distance < CONNECTION.base.distance(source, target)


def test_public_refinement_report_cannot_forge_a_zero_defect():
    report = SECTIONAL.refine(
        CONNECTION,
        np.array([0.08, 0.01, 0.0, 0.0]),
        np.array([0.0, 0.09, 0.02, 0.0]),
        sections=8,
    )
    with pytest.raises(GovernanceError):
        replace(
            report,
            refined_unitary=-report.direct_unitary,
            composition_defect=0.0,
        )


def test_refinement_validates_count_and_carrier():
    with pytest.raises(GovernanceError):
        SECTIONAL.refine(CONNECTION, np.zeros(4), np.zeros(4), sections=True)
    with pytest.raises(GovernanceError):
        SECTIONAL.refine(CONNECTION, np.zeros(4), np.zeros(4), sections=0)
    with pytest.raises(CarrierMismatch):
        ChiralSpinConnection(
            base=PoincareBallBase(
                id="other-H4",
                dimension=4,
                sectional_curvature=-0.25,
            )
        )
    with pytest.raises(CarrierMismatch):
        SectionalAcceleratorBoundary(
            base=PoincareBallBase(
                id="other-H4",
                dimension=4,
                sectional_curvature=-0.25,
            )
        )


def test_near_boundary_refinement_fails_closed_before_false_certificate():
    source = np.array(
        [
            -0.4286143430440551,
            0.6651503982223048,
            0.2656578445392388,
            -0.537902967380166,
        ]
    )
    target = np.array(
        [
            0.3612884352822544,
            0.42508478986742537,
            -0.2640892586582573,
            0.777868530933087,
        ]
    )
    with pytest.raises(GovernanceError, match="conditioned float64"):
        SECTIONAL.refine(CONNECTION, source, target, sections=100)


def test_strict_mobius_translation_preserves_pair_distance():
    translation = np.array([0.07, -0.02, 0.01, 0.00])
    left = np.array([0.10, 0.03, -0.02, 0.01])
    right = np.array([-0.04, 0.13, 0.05, -0.02])
    moved_left = SECTIONAL.mobius_add(translation, left)
    moved_right = SECTIONAL.mobius_add(translation, right)
    assert CONNECTION.base.distance(moved_left, moved_right) == pytest.approx(
        CONNECTION.base.distance(left, right),
        abs=1e-12,
    )


def test_mobius_near_inverse_cancellation_is_rejected():
    translation = np.array([1.0 - 1e-8, 0.0, 0.0, 0.0])
    point = np.array([-(1.0 - 1.4e-8), -1e-9, 0.0, 0.0])
    with pytest.raises(GovernanceError, match="conditioned float64"):
        SECTIONAL.mobius_add(translation, point)


def test_mobius_distance_sensitive_boundary_output_is_rejected():
    left = np.array(
        [
            0.20440138642186528,
            0.8520958221763578,
            -0.4453995018864628,
            -0.17825001199917698,
        ]
    )
    translation = np.array(
        [
            -0.034412575368504464,
            -0.4279189623491974,
            -0.33513556095020663,
            -0.8374880847540958,
        ]
    )
    with pytest.raises(GovernanceError):
        SECTIONAL.mobius_add(translation, left)


def test_mobius_geodesic_sections_have_exact_endpoints():
    source = np.array([0.09, -0.04, 0.01, 0.02])
    target = np.array([-0.05, 0.16, 0.03, -0.01])
    assert SECTIONAL.geodesic_section(source, target, 0.0) == pytest.approx(
        source,
        abs=1e-12,
    )
    assert SECTIONAL.geodesic_section(source, target, 1.0) == pytest.approx(
        target,
        abs=1e-12,
    )
    with pytest.raises(GovernanceError):
        SECTIONAL.geodesic_section(source, target, 1.1)


def test_sectional_hadamard_is_typed_as_amplitude_control():
    hadamard4 = SECTIONAL.hadamard4()
    spin_gate = SECTIONAL.hadamard_spin_gate()
    assert hadamard4.T @ hadamard4 == pytest.approx(np.eye(4))
    assert spin_gate.conj().T @ spin_gate == pytest.approx(IDENTITY2)
    assert np.linalg.det(spin_gate) == pytest.approx(1.0)
    ordinary_h = spin_gate / 1.0j
    assert np.linalg.det(ordinary_h) == pytest.approx(-1.0)


def test_split_boost_preserves_q22_but_is_not_hilbert_unitary():
    report = SECTIONAL.audit(
        CONNECTION,
        np.array([0.1, 0.0, 0.0, 0.0]),
        np.array([0.0, 0.1, 0.0, 0.0]),
        np.array([0.02, 0.0, 0.0, 0.0]),
        rapidity=0.4,
    )
    assert report.split_signature_defect < 1e-12
    assert report.split_hilbert_unitarity_defect > 0.1
    assert not report.split_qiskit_eligible
    assert report.split_remainder.name == "[R]_split_signature_substrate"
    with pytest.raises(CarrierMismatch):
        project_spin_path_to_qiskit((report.split_boost,))
    with pytest.raises(GovernanceError, match="conditioned float64"):
        SECTIONAL.split_boost(1000.0)


def test_evolved_sectional_metadata_is_bounded_and_honest():
    report = SECTIONAL.audit(
        CONNECTION,
        np.array([0.08, 0.01, 0.0, 0.0]),
        np.array([0.0, 0.09, 0.01, 0.0]),
        np.array([0.01, 0.0, 0.0, 0.0]),
        rapidity=0.2,
    )
    assert report.generation == 100
    assert report.fixed_phase == pytest.approx(1.2368)
    assert report.jitter == pytest.approx(0.19685006)
    assert report.perlin_seed == 0x0B62C6DD
    assert not report.jitter_operational
    assert not report.perlin_seed_operational
    assert report.fixed_phase_gate.conj().T @ report.fixed_phase_gate == pytest.approx(
        IDENTITY2
    )
    with pytest.raises(GovernanceError):
        replace(
            report,
            split_signature_defect=0.0,
            split_boost=np.eye(4),
        )
    with pytest.raises(GovernanceError):
        replace(report, split_qiskit_eligible=True)


def test_spinor_preparation_is_su2_and_prepares_first_column():
    spinor = np.array([math.sqrt(0.35), np.exp(0.7j) * math.sqrt(0.65)])
    preparation = spinor_preparation_unitary(spinor)
    assert preparation[:, 0] == pytest.approx(spinor)
    assert preparation.conj().T @ preparation == pytest.approx(IDENTITY2)
    assert np.linalg.det(preparation) == pytest.approx(1.0)
    with pytest.raises(GovernanceError):
        spinor_preparation_unitary(np.array([1.0, 1.0]))


def test_qiskit_projection_matches_operator_statevector_and_density():
    points = (
        np.array([0.12, 0.01, 0.00, 0.00]),
        np.array([0.00, 0.14, 0.03, 0.00]),
        np.array([0.02, 0.00, 0.15, 0.05]),
    )
    path = CONNECTION.path(points)
    spinor = np.array([math.sqrt(0.4), 1.0j * math.sqrt(0.6)])
    report = project_spin_path_to_qiskit(
        path,
        initial_spinor=spinor,
    )
    assert report.passed
    assert report.qiskit_version
    assert report.link_count == 2
    assert report.path_unitary == pytest.approx(path.unitary, abs=1e-12)
    assert report.circuit_operator == pytest.approx(
        report.expected_circuit_operator,
        abs=1e-12,
    )
    assert report.output_statevector == pytest.approx(
        report.expected_statevector,
        abs=1e-12,
    )
    assert report.output_density == pytest.approx(
        report.expected_density,
        abs=1e-12,
    )
    assert report.circuit.num_qubits == 1
    assert report.circuit.num_clbits == 0
    assert report.simulator_only
    assert not report.backend_executed
    assert not report.advantage_claim


def test_qiskit_projection_preserves_noncommuting_order():
    first = CONNECTION.link(
        np.array([0.1, 0.0, 0.0, 0.0]),
        np.array([0.0, 0.1, 0.02, 0.0]),
    )
    second = CONNECTION.link(
        np.array([0.0, 0.1, 0.02, 0.0]),
        np.array([0.0, 0.0, 0.12, 0.03]),
    )
    report = project_spin_path_to_qiskit((first, second))
    assert report.path_unitary == pytest.approx(
        second.unitary @ first.unitary,
        abs=1e-12,
    )
    assert (
        np.linalg.norm(
            second.unitary @ first.unitary - first.unitary @ second.unitary,
            ord="fro",
        )
        > 1e-6
    )


def test_fixed_phase_gauge_control_is_not_smuggled_in_as_a_geometric_link():
    phase = SECTIONAL.fixed_phase_gate()
    link = CONNECTION.link(
        np.array([0.1, 0.02, 0.0, 0.0]),
        np.array([0.0, 0.11, 0.03, 0.0]),
    )
    with pytest.raises(CarrierMismatch):
        project_spin_path_to_qiskit((phase.conj().T, link, phase))


def test_qiskit_projection_rejects_all_detached_matrix_carriers():
    nonunitary = np.diag([1.1, 1.0 / 1.1])
    u2_not_su2 = np.exp(0.2j) * IDENTITY2
    valid_but_detached_su2 = SECTIONAL.fixed_phase_gate()
    for detached in (nonunitary, u2_not_su2, valid_but_detached_su2):
        with pytest.raises(CarrierMismatch):
            project_spin_path_to_qiskit((detached,))
    with pytest.raises(GovernanceError):
        project_spin_path_to_qiskit(
            IDENTITY_PATH,
            initial_spinor=(1.0, 1.0),
        )
    with pytest.raises(GovernanceError):
        project_spin_path_to_qiskit(())


def test_qiskit_receipt_binds_expectations_and_live_circuit_shape():
    report = project_spin_path_to_qiskit(IDENTITY_PATH)
    with pytest.raises(GovernanceError):
        replace(
            report,
            expected_circuit_operator=np.array(
                [[0.0, 1.0], [1.0, 0.0]],
                dtype=complex,
            ),
            circuit_operator=np.array(
                [[0.0, 1.0], [1.0, 0.0]],
                dtype=complex,
            ),
            output_statevector=np.array([0.0, 1.0], dtype=complex),
            expected_statevector=np.array([0.0, 1.0], dtype=complex),
            output_density=np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex),
            expected_density=np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex),
            circuit_operator_defect=0.0,
            statevector_defect=0.0,
            density_intertwining_defect=0.0,
        )
    with pytest.raises(CarrierMismatch):
        replace(report, base_id="other-H4")
    with pytest.raises(GovernanceError):
        replace(report, links=())
    with pytest.raises(GovernanceError):
        replace(report, qiskit_version="forged-version")
    report.circuit.x(0)
    report.circuit.x(0)
    assert not report.passed
    with pytest.raises(GovernanceError):
        replace(report)


def test_defensive_qiskit_absence_boundary(monkeypatch):
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "qiskit" or name.startswith("qiskit."):
            raise ModuleNotFoundError("blocked in QB2 absence control")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    with pytest.raises(QiskitProjectionUnavailable):
        project_spin_path_to_qiskit(IDENTITY_PATH)


def test_qiskit_central_minus_identity_is_operator_visible():
    report = probe_central_lift_qiskit(-IDENTITY2)
    assert report.passed
    assert report.positive_identity_distance == pytest.approx(2.0 * math.sqrt(2.0))
    assert report.negative_identity_distance == pytest.approx(0.0)
    assert report.density_change == pytest.approx(0.0)
    assert report.control_one_probability == pytest.approx(1.0, abs=1e-12)
    assert report.circuit.num_qubits == 2
    assert report.simulator_only
    assert not report.backend_executed
    with pytest.raises(GovernanceError):
        replace(report, control_one_probability=0.0)
    report.circuit.x(0)
    assert not report.passed


def test_qiskit_central_plus_identity_control_is_dark():
    report = probe_central_lift_qiskit(IDENTITY2)
    assert report.passed
    assert report.positive_identity_distance == pytest.approx(0.0)
    assert report.control_one_probability == pytest.approx(0.0, abs=1e-12)
