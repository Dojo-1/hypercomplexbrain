"""Frozen gates for the Ohnium V2 observable-ascent slice."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from aionq.governance import GovernanceError, RemainderKind
from aionq.hopf_layer import hopf_ladder, hopf_map
from aionq.ohnium_observability import (
    AUMPhase,
    CARRIER_ORDER,
    DEFAULT_ENDPOINTS,
    EndpointConfig,
    FRAMES,
    MAX_STABLE_RHO,
    TOLERANCE,
    atlas_payload,
    build_ohnium_atlas,
    phase_operator,
    poincare_disk_point,
    run_endpoint,
)
from aionq.quantities import Quantity
from aionq.recognition.worldlet import AlgebraRegime, Geometry
from experiments.run_ohnium_observatory import _html


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (ROOT / "manifests" / "ohnium_v2_observability_preregistration.json")
    .read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def atlas():
    return build_ohnium_atlas()


def test_name_boundary_is_explicit_and_not_a_quantum_claim():
    assert MANIFEST["name_contract"]["OHM"] == "Ohnium architecture"
    assert MANIFEST["phase_order"] == ["A", "U", "M"]
    boundary = MANIFEST["name_contract"]["boundary"].lower()
    assert "no chant" in boundary
    assert "physical quantum effect" in boundary


@pytest.mark.parametrize("phase", tuple(AUMPhase))
@pytest.mark.parametrize("tau", [0.0, 0.1, 1.7, 2.0 * math.pi])
def test_aum_phase_operators_are_su2(phase, tau):
    operator = phase_operator(phase, tau)
    assert operator.shape == (2, 2)
    assert operator.conj().T @ operator == pytest.approx(
        np.eye(2), abs=1e-12
    )
    assert np.linalg.det(operator) == pytest.approx(1.0 + 0.0j, abs=1e-12)


@pytest.mark.parametrize("phase", tuple(AUMPhase))
def test_aum_phase_operators_have_explicit_inverse_and_group_law(phase):
    first = 0.37
    second = -0.19
    identity = np.eye(2, dtype=complex)
    assert phase_operator(phase, first) @ phase_operator(
        phase, -first
    ) == pytest.approx(identity, abs=1e-12)
    assert phase_operator(phase, first) @ phase_operator(
        phase, second
    ) == pytest.approx(
        phase_operator(phase, first + second),
        abs=1e-12,
    )


def test_hopf_map_keeps_the_full_fibre_invariant():
    rng = np.random.default_rng(MANIFEST["seed"])
    for _ in range(50):
        spinor = rng.normal(size=2) + 1j * rng.normal(size=2)
        spinor /= np.linalg.norm(spinor)
        phase = rng.uniform(-math.pi, math.pi)
        assert hopf_map(np.exp(1j * phase) * spinor) == pytest.approx(
            hopf_map(spinor), abs=1e-12
        )
        assert np.linalg.norm(hopf_map(spinor)) == pytest.approx(
            1.0, abs=1e-12
        )


def test_r40_is_append_only_and_carries_the_registered_sequence(atlas):
    assert atlas.frames == FRAMES == 40
    assert atlas.carrier_order == CARRIER_ORDER
    for endpoint in atlas.endpoints:
        assert tuple(frame.index for frame in endpoint.frames) == tuple(range(40))
        for frame in endpoint.frames:
            assert tuple(item.carrier for item in frame.carrier_trace) == (
                "R",
                "H",
                "O",
                "CD32",
                "A_n",
            )
            assert tuple((item.dimension for item in frame.carrier_trace)) == (
                4,
                3,
                8,
                32,
                endpoint.active_dimension,
            )
            assert frame.phase in {"A", "U", "M"}
            assert frame.weave_action in {"weave", "deweave"}
            assert frame.weave_reason


def test_aum_phase_offsets_cover_the_frozen_r40_cadence(atlas):
    counts = {
        endpoint.id: {
            phase: sum(frame.phase == phase for frame in endpoint.frames)
            for phase in ("A", "U", "M")
        }
        for endpoint in atlas.endpoints
    }
    assert counts == {
        "cosmos.north": {"A": 14, "U": 13, "M": 13},
        "cosmos.equator": {"A": 13, "U": 14, "M": 13},
        "cosmos.deep": {"A": 13, "U": 13, "M": 14},
    }


def test_dominance_trace_is_the_requested_observable_ascent(atlas):
    expected = (
        ("R",) * 8
        + ("H",) * 8
        + ("O",) * 8
        + ("CD32",) * 8
        + ("A_n",) * 8
    )
    for endpoint in atlas.endpoints:
        assert endpoint.dominance_trace == expected


def test_every_bridge_has_typed_energy_and_full_landing_vector(atlas):
    for endpoint in atlas.endpoints:
        for frame in endpoint.frames:
            assert len(frame.bridges) == 4
            for bridge in frame.bridges:
                assert math.isfinite(bridge.source_energy)
                assert math.isfinite(bridge.target_energy)
                assert bridge.transferred_energy == pytest.approx(
                    bridge.target_energy - bridge.source_energy, abs=1e-12
                )
                assert bridge.energy_balance_defect <= TOLERANCE
                assert bridge.remainder_record_defect <= TOLERANCE
                assert bridge.return_path.closes_with_sidecar
            final = frame.bridges[-1]
            assert len(final.violence.discarded_vector) == 32
            assert final.violence.rank_loss == 32 - endpoint.active_dimension
            assert final.violence.landing_carrier == (
                "CD32 orthogonal complement"
            )
            assert final.violence.discarded_energy == pytest.approx(
                final.violence.energy_loss, abs=1e-12
            )
            assert isinstance(
                final.violence.volume_form_distortion, Quantity
            )
            assert (
                final.violence.volume_form_distortion
                == frame.source_operational_volume_distortion
            )
            assert (
                final.violence.volume_form_distortion.unit
                == "pullback-volume-form-ratio"
            )
            assert (
                final.violence.volume_form_distortion.base
                == "SL2-to-Bell-erasure"
            )


def test_baseline_motion_passes_all_four_proof_pressure_surfaces(atlas):
    for endpoint in atlas.endpoints:
        for frame in endpoint.frames:
            pressure = frame.proof_pressure
            assert pressure.coherent
            assert pressure.failures == ()
            assert pressure.fano_signal_rank == 7
            assert pressure.fano_crosstalk_rank == 21
            assert pressure.fano_joint_rank == 28
            assert pressure.fano_cross_gram <= 1e-12
            assert pressure.fano_surface == "baseline"
            assert "deterministic 21-coordinate diagnostic probe" in (
                pressure.fano_probe_definition
            )
            assert "not measured active-operator commutator telemetry" in (
                pressure.fano_probe_definition
            )
            assert len(pressure.fano_probe_coefficients) == 21
            assert len(pressure.fano_probe_landing) == 28
            assert len(pressure.fano_probe_signal_projection) == 7
            assert np.linalg.norm(
                pressure.fano_probe_coefficients
            ) == pytest.approx(1.0, abs=1e-12)
            assert np.linalg.norm(pressure.fano_probe_landing) > 0.0
            assert np.all(np.isfinite(pressure.fano_probe_landing))
            assert np.max(
                np.abs(pressure.fano_probe_signal_projection)
            ) <= 1e-12
            assert pressure.fano_braid_defect <= TOLERANCE
            assert pressure.light_cone_defect <= TOLERANCE
            assert pressure.swirl_defect <= TOLERANCE
            assert pressure.carrier_ring_defect <= TOLERANCE
            assert math.hypot(*pressure.disk_point) < 1.0


def test_registered_faults_are_typed_and_detected(atlas):
    assert tuple(probe.fault for probe in atlas.fault_probes) == (
        "false_ascent",
        "energy_leakage",
        "bridge_absorption",
    )
    assert all(probe.caught for probe in atlas.fault_probes)
    for probe in atlas.fault_probes:
        assert probe.observed_failures == (probe.fault,)
        assert probe.telemetry.index == probe.frame
    false_ascent = atlas.fault_probes[0]
    assert (
        false_ascent.telemetry.proof_pressure.fano_surface
        == "duplicated_channel_control"
    )
    assert false_ascent.telemetry.proof_pressure.fano_joint_rank < 28


def test_cosmos_level_multiplicity_is_a_real_polycosmos(atlas):
    assert len(atlas.endpoints) == 3
    assert set(atlas.polycosmos.worldlets) == {
        "cosmos.north",
        "cosmos.equator",
        "cosmos.deep",
    }
    assert len(atlas.polycosmos.tendrils) == 3
    assert atlas.polycosmos.hyperedges == (
        ("cosmos.north", "cosmos.equator", "cosmos.deep"),
    )
    for worldlet in atlas.polycosmos.worldlets.values():
        assert worldlet.local_geometry == Geometry.CAYLEY_DICKSON_L2
        assert worldlet.algebra_regime == AlgebraRegime.CD32
        assert worldlet.typed_remainders
        assert worldlet.typed_remainders[0].remainder_type == (
            RemainderKind.EMPIRICAL
        )
        assert worldlet.typed_remainders[0].provenance.endswith(
            "ohnium_v2_observability_preregistration.json"
        )


def test_each_endpoint_keeps_remainder_and_return_path(atlas):
    for endpoint in atlas.endpoints:
        assert endpoint.active_remainder.raw_value > 0.0
        assert len(endpoint.active_discarded_vector) == 32
        assert np.linalg.norm(endpoint.active_discarded_vector) > 0.0
        assert endpoint.return_path.closes_with_sidecar
        assert endpoint.return_path.reconstruction_defect <= 1e-12


def test_hamiltonian_eight_quality_vector_is_not_a_promotion_score(atlas):
    audit = atlas.governance
    assert len(audit.qualities) == 8
    assert all(value == 1.0 for _, value in audit.qualities)
    assert all(value == 0.0 for _, value in audit.energy_components)
    assert audit.total_energy == 0.0
    assert audit.promotion_forbidden


def test_governance_marks_out_of_preregistration_endpoint_scope():
    custom = (
        DEFAULT_ENDPOINTS[0],
        EndpointConfig(
            id="cosmos.custom",
            rho=1.5,
            phi=0.1,
            psi=-0.2,
            active_dimension=10,
            phase_offset=1,
        ),
    )
    qualities = dict(build_ohnium_atlas(custom).governance.qualities)
    assert qualities["preregistered_scope"] == 0.0


def test_payload_keeps_vectors_and_attribution(atlas):
    payload = atlas_payload(atlas)
    assert payload["schema"] == "ohnium.observable-ascent.v2"
    assert payload["name"] == "OHM / Ohnium"
    assert len(payload["endpoints"]) == 3
    assert len(payload["endpoints"][0]["frames"]) == 40
    first_bridge = payload["endpoints"][0]["frames"][0]["bridges"][-1]
    assert len(
        first_bridge["projection_violence"]["discarded_vector"]
    ) == 32
    final_bridge = payload["endpoints"][0]["frames"][-1]["bridges"][-1]
    assert (
        payload["endpoints"][0]["active_remainder"]["discarded_vector"]
        == final_bridge["projection_violence"]["discarded_vector"]
    )
    pressure = payload["endpoints"][0]["frames"][0]["proof_pressure"]
    assert "not measured active-operator commutator telemetry" in (
        pressure["fano_probe_definition"]
    )
    assert len(pressure["fano_probe_coefficients"]) == 21
    assert len(pressure["fano_probe_landing"]) == 28
    assert len(pressure["fano_probe_signal_projection"]) == 7
    assert pressure["fano_surface"] == "baseline"
    distortion = final_bridge["projection_violence"][
        "volume_form_distortion"
    ]
    assert distortion["unit"] == "pullback-volume-form-ratio"
    assert distortion["base"] == "SL2-to-Bell-erasure"
    assert json.loads(json.dumps(payload)) == payload
    assert payload["attribution"] == (
        "(c) Jesús Vilela Jato, all rights reserved. 21/05/2026"
    )


def test_live_atlas_embeds_the_evidence_surface_without_global_event(atlas):
    payload = atlas_payload(atlas)
    html = _html(payload)
    assert "OHM · OHNIUM R40" in html
    assert "R → H → O → CD32 → A<sub>n</sub>" in html
    assert 'id="atlas-data"' in html
    assert 'onclick=(ev)=>' in html
    assert "event.target" not in html
    assert '"discarded_vector"' in html


def test_poincare_projection_never_leaves_the_disk():
    for rho in [1e-9, 0.5, 2.0, 20.0]:
        point = poincare_disk_point(rho, 1.23)
        assert math.hypot(*point) < 1.0


def test_invalid_fault_and_flat_single_cosmos_are_rejected():
    with pytest.raises(ValueError, match="unknown"):
        run_endpoint(DEFAULT_ENDPOINTS[0], {0: "ornamental_metaphor"})
    with pytest.raises(GovernanceError, match="multiplicity"):
        build_ohnium_atlas((DEFAULT_ENDPOINTS[0],))
    with pytest.raises(ValueError, match="active_dimension"):
        EndpointConfig("bad", 1.0, 0.0, 0.0, 32)
    with pytest.raises(ValueError, match="finite"):
        EndpointConfig("bad", float("nan"), 0.0, 0.0, 8)
    with pytest.raises(ValueError, match="active_dimension"):
        EndpointConfig("bad", 1.0, 0.0, 0.0, True)
    with pytest.raises(ValueError, match="phase_offset"):
        EndpointConfig("bad", 1.0, 0.0, 0.0, 8, True)
    with pytest.raises(ValueError, match=r"SL\(2,R\) determinant seam"):
        EndpointConfig("bad", MAX_STABLE_RHO, 0.0, 0.0, 8)
    boundary = EndpointConfig(
        "boundary",
        MAX_STABLE_RHO - 0.08,
        0.0,
        0.0,
        8,
    )
    assert len(run_endpoint(boundary).frames) == FRAMES


def test_cd32_is_registered_as_non_flat():
    assert AlgebraRegime.CD32 in AlgebraRegime.NON_FLAT
    assert Geometry.CAYLEY_DICKSON_L2 in Geometry.ALL


def test_cd32_is_not_promoted_to_a_hopf_rung():
    ladder = hopf_ladder()
    assert [rung["dim"] for rung in ladder if rung["fibration"]] == [1, 2, 4, 8]
    assert all(rung["dim"] != 32 for rung in ladder)
