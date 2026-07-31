from __future__ import annotations

import json
import math

import numpy as np
import pytest

from aionq.coherent_dilation import density_state_diagnostics
from aionq.equal_resource_reservoir import (
    AMBIENT_DIM,
    CODEWORDS_PER_DEPTH,
    DEPTHS,
    NOISE_STRENGTHS,
    FourShardAssociativeReservoir,
    TaskEnsemble,
    build_map_tasks,
    build_pgm_receiver,
    classify_protocol,
    compiler_cost_proxy,
    depolarize,
    encode_r6,
    encode_r6i,
    evaluate_receiver,
    flagged_truncation_trace_distance,
    required_cutoff,
    source_grid,
    trace_distance,
    truncated_two_mode_state,
    truncation_cost_report,
    validate_protocol_grid,
)
from aionq.holevo_sandwich import holevo_chi
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state


def _matrix(point):
    return to_sl2(swirl_point(*point))


def test_source_grid_has_exact_central_sign_pairs():
    points = source_grid(1.0)
    matrices = [_matrix(point) for point in points]
    assert len(points) == CODEWORDS_PER_DEPTH == 32
    for k in range(16):
        assert matrices[k + 16] == pytest.approx(-matrices[k], abs=2e-15)


def test_r6_embedding_is_passive_and_places_erasure_at_zero():
    matrix = _matrix((1.0, 0.4, 0.7))
    native, _ = attempted_use_state(matrix)
    embedded = encode_r6(matrix)
    assert embedded.shape == (AMBIENT_DIM, AMBIENT_DIM)
    assert embedded[0, 0] == pytest.approx(native[4, 4], abs=1e-15)
    assert embedded[12:16, 12:16] == pytest.approx(native[:4, :4], abs=1e-15)
    native_spectrum = np.sort(np.pad(np.linalg.eigvalsh(native), (0, 11)))
    assert np.linalg.eigvalsh(embedded) == pytest.approx(native_spectrum, abs=1e-12)


def test_r6_padding_preserves_holevo_information():
    matrices = [_matrix(point) for point in source_grid(2.0)]
    native = [attempted_use_state(matrix)[0] for matrix in matrices]
    embedded = [encode_r6(matrix) for matrix in matrices]
    assert holevo_chi(embedded) == pytest.approx(holevo_chi(native), abs=1e-12)


def test_true_projective_twirl_is_not_a_half_grid_section():
    r6_tasks, _ = build_map_tasks("R6")
    r6i_tasks, _ = build_map_tasks("R6i")
    signed_r6 = next(
        task for task in r6_tasks
        if task.name == "signed_fixed_depth" and task.depth == 2.0
    )
    quotient_r6 = next(
        task for task in r6_tasks
        if task.name == "projective_fixed_depth" and task.depth == 2.0
    )
    signed_r6i = next(
        task for task in r6i_tasks
        if task.name == "signed_fixed_depth" and task.depth == 2.0
    )
    quotient_r6i = next(
        task for task in r6i_tasks
        if task.name == "projective_fixed_depth" and task.depth == 2.0
    )
    assert signed_r6.templates[0] == pytest.approx(
        signed_r6.templates[16], abs=1e-14
    )
    assert quotient_r6.templates[0] == pytest.approx(
        signed_r6.templates[0], abs=1e-14
    )
    expected = (signed_r6i.templates[0] + signed_r6i.templates[16]) / 2.0
    assert quotient_r6i.templates[0] == pytest.approx(expected, abs=1e-14)
    assert density_state_diagnostics(quotient_r6i.templates[0])["rank"] == 2
    assert np.linalg.norm(
        quotient_r6i.templates[0] - signed_r6i.templates[0], "fro"
    ) > 0.1


def test_task_geometry_includes_radial_and_joint_endpoints():
    tasks, diagnostics = build_map_tasks("R6i")
    assert len(tasks) == 12
    assert sum(task.name == "signed_fixed_depth" for task in tasks) == 5
    assert sum(task.name == "projective_fixed_depth" for task in tasks) == 5
    radial = next(task for task in tasks if task.name == "radial")
    joint = next(task for task in tasks if task.name == "joint_depth_projective")
    assert radial.classes == len(DEPTHS) == 5
    assert joint.classes == 5 * 16 == 80
    assert diagnostics["maximum_central_pair_residual"] <= 1e-12


def test_signed_query_order_keeps_paired_jitter_labels_aligned():
    rho = 1.0
    tasks, _ = build_map_tasks("R6i")
    signed = next(
        task for task in tasks
        if task.name == "signed_fixed_depth" and task.depth == rho
    )
    _, phi, psi = source_grid(rho)[0]
    perturbations = (
        (0.01, math.pi / 64.0, -math.pi / 80.0),
        (-0.01, -math.pi / 64.0, math.pi / 80.0),
    )
    positive = [
        encode_r6i(_matrix((rho + dr, phi + dp, psi + ds)))
        for dr, dp, ds in perturbations
    ]
    negative = [
        encode_r6i(_matrix((rho + dr, phi + dp + math.pi,
                            psi + ds + math.pi)))
        for dr, dp, ds in perturbations
    ]
    assert signed.queries[0] == pytest.approx(sum(positive) / 2.0, abs=1e-12)
    assert signed.queries[16] == pytest.approx(sum(negative) / 2.0, abs=1e-12)
    assert np.linalg.norm(signed.queries[0] - signed.queries[16], "fro") > 0.1


def test_four_shard_store_is_deterministic_and_append_only(tmp_path):
    path = tmp_path / "events.jsonl"
    state = np.diag([1.0, *([0.0] * 15)]).astype(complex)
    first = FourShardAssociativeReservoir(path)
    record = first.store("R6:test:0", state, {"source": 0})
    assert record.shard == ("positive-0", "positive-1", "tension-0", "tension-1")[
        FourShardAssociativeReservoir.shard_index("R6:test:0")
    ]
    assert first.get("R6:test:0").state == pytest.approx(state)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["sequence"] == 0
    with pytest.raises(FileExistsError):
        FourShardAssociativeReservoir(path)


def test_complete_pgm_counts_support_complement_as_abstention():
    templates = (
        np.diag([1.0, 0.0, 0.0, 0.0]).astype(complex),
        np.diag([0.0, 1.0, 0.0, 0.0]).astype(complex),
    )
    receiver = build_pgm_receiver(templates)
    clean = evaluate_receiver(
        receiver, templates, templates, noise_strength=0.0
    )
    noisy = evaluate_receiver(
        receiver, templates, templates, noise_strength=0.2
    )
    assert receiver.diagnostics["clean_mean_support_rank"] == 2
    assert receiver.diagnostics["completeness_residual"] <= 1e-12
    assert clean["correct_probability"] == pytest.approx(1.0, abs=1e-12)
    assert clean["abstention_probability"] == pytest.approx(0.0, abs=1e-12)
    # Depolarization puts eta*(D-rank)/D into the explicit complement.
    assert noisy["abstention_probability"] == pytest.approx(0.1, abs=1e-12)
    assert noisy["maximum_raw_row_sum_defect"] <= 1e-12


def test_hilbert_schmidt_oracle_uses_distance_not_overlap():
    pure = np.diag([1.0, 0.0]).astype(complex)
    mixed = np.eye(2, dtype=complex) / 2.0
    templates = (pure, mixed)
    metrics = evaluate_receiver(
        build_pgm_receiver(templates),
        templates,
        templates,
        noise_strength=0.0,
    )
    assert metrics["hilbert_schmidt_tomography_oracle_accuracy"] == pytest.approx(
        1.0, abs=1e-12
    )


@pytest.mark.parametrize("strength", [0.0, 0.01, 0.1, 1.0])
def test_global_depolarization_remains_a_density(strength):
    state = encode_r6i(_matrix((0.7, 0.2, -0.3)))
    output = depolarize(state, strength)
    assert density_state_diagnostics(output)["valid"]
    assert np.trace(output) == pytest.approx(1.0, abs=1e-12)


def test_radial_trace_distance_is_well_defined_on_density_states():
    states = [encode_r6(_matrix(point)) for point in source_grid(0.5)[:2]]
    assert trace_distance(states[0], states[0]) == pytest.approx(0.0, abs=1e-12)
    assert 0.0 <= trace_distance(states[0], states[1]) <= 1.0 + 1e-12


@pytest.mark.parametrize("rho", DEPTHS)
def test_exact_truncation_state_charges_the_tail(rho):
    state = truncated_two_mode_state(rho, 0.37)
    tail = math.tanh(rho) ** 8
    assert state.shape == (16, 16)
    assert state[1, 1] == pytest.approx(tail, abs=1e-12)
    assert np.trace(state) == pytest.approx(1.0, abs=1e-12)
    assert density_state_diagnostics(state)["valid"]


def test_required_cutoff_exposes_the_deep_truncation_wall():
    assert required_cutoff(0.5, 1e-3) == 5
    assert required_cutoff(1.0, 1e-3) == 13
    assert required_cutoff(2.0, 1e-3) == 95
    report = truncation_cost_report()
    rows = {row["rho"]: row for row in report["rows"]}
    tau = math.tanh(0.5) ** 8
    expected_flagged = 0.5 * (tau + math.sqrt(4 * tau - 3 * tau * tau))
    assert flagged_truncation_trace_distance(tau) == pytest.approx(
        expected_flagged, abs=1e-15
    )
    assert rows[0.5]["flagged_state_trace_distance"] > math.sqrt(tau)
    assert rows[0.5]["worst_perturbed_query_flagged_trace_distance"] < 0.05
    assert rows[0.1]["inside_primary_trace_error_budget_0.05"]
    assert rows[0.5]["inside_primary_trace_error_budget_0.05"]
    assert not rows[1.0]["inside_primary_trace_error_budget_0.05"]
    assert rows[4.0]["mean_total_photons_in_infinite_orbit"] > 1000.0


def _synthetic_rows(*, radial_gain: bool) -> list[dict]:
    rows = []

    def complete(row):
        return {
            **row,
            "abstention_probability": 0.0,
            "holevo_chi_bits": 0.2,
            "minimum_raw_probability": 0.0,
            "maximum_raw_probability": 1.0,
            "maximum_raw_row_sum_defect": 0.0,
            "maximum_raw_imaginary_probability": 0.0,
            "template_digest": "sha256:" + "1" * 64,
            "query_digest": "sha256:" + "2" * 64,
            "confusion_digest": "sha256:" + "3" * 64,
        }

    for map_name, direction in (("R6", 0.0), ("R6i", 1.0)):
        for noise in NOISE_STRENGTHS:
            for task, classes, margin in (
                ("signed_fixed_depth", 32, 1.0 / 32.0),
                ("projective_fixed_depth", 16, 1.0 / 16.0),
            ):
                for rho in DEPTHS:
                    rows.append(complete({
                        "map": map_name, "task": task, "rho": rho,
                        "noise_strength": noise,
                        "correct_probability": 0.1 + direction * (margin + 0.01),
                        "mutual_information_bits": 0.1 + direction * 0.03,
                        "hilbert_schmidt_tomography_oracle_accuracy": 0.1,
                        "classes": classes,
                    }))
            rows.append(complete({
                "map": map_name, "task": "radial", "rho": None,
                "noise_strength": noise,
                "correct_probability": 0.2 + direction * (0.21 if radial_gain else 0.0),
                "mutual_information_bits": 0.1 + direction * (0.03 if radial_gain else 0.0),
                "hilbert_schmidt_tomography_oracle_accuracy": 0.2,
                "classes": 5,
            }))
            rows.append(complete({
                "map": map_name, "task": "joint_depth_projective", "rho": None,
                "noise_strength": noise,
                "correct_probability": 0.02 + direction * 0.02,
                "mutual_information_bits": 0.1 + direction * 0.03,
                "hilbert_schmidt_tomography_oracle_accuracy": 0.02,
                "classes": 80,
            }))
    return rows


def test_frozen_decision_rule_can_report_anisotropy():
    decision = classify_protocol(
        _synthetic_rows(radial_gain=False),
        {"all": True},
        {"passed": True},
    )
    assert decision["projective_angular_survival"]
    assert not decision["radial_survival"]
    assert decision["joint_depth_projective_survival"]
    assert decision["verdict"] == "ANISOTROPIC_ANGULAR_GAIN_NO_RADIAL_GAIN"
    assert decision["decision_semantics"]["comparison"] == (
        "R6i minus R6 differential gain"
    )
    assert not decision["decision_semantics"][
        "absolute_information_inference_permitted"
    ]


def test_frozen_decision_rule_holds_on_a_failed_control():
    decision = classify_protocol(
        _synthetic_rows(radial_gain=True),
        {"density": False},
        {"passed": True},
    )
    assert decision["verdict"] == "HOLD"


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "extra", "nan", "wrong_classes"],
)
def test_frozen_grid_validator_rejects_malformed_cells(mutation):
    rows = _synthetic_rows(radial_gain=False)
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(dict(rows[-1]))
    elif mutation == "extra":
        extra = dict(rows[-1])
        extra["task"] = "invented"
        rows.append(extra)
    elif mutation == "nan":
        rows[-1]["mutual_information_bits"] = math.nan
    else:
        rows[-1]["classes"] = 79
    validation = validate_protocol_grid(rows)
    assert not validation["valid"]
    assert validation["reasons"]
    decision = classify_protocol(rows, {"all": True}, {"passed": True})
    assert decision["verdict"] == "HOLD"


def test_qiskit_compiler_proxy_reconstructs_the_shared_core():
    proxy = compiler_cost_proxy()
    assert proxy["settings"]["basis_gates"] == ["u", "cx"]
    assert proxy["settings"]["optimization_level"] == 3
    assert proxy["settings"]["seed_transpiler"] == 11
    assert proxy["shared_core_global_phase_residual"] <= 1e-10
    assert proxy["R6i_full_state_fidelity"] == pytest.approx(1.0, abs=1e-12)
    assert proxy["R6i_full_density_residual"] <= 1e-10
    assert proxy["R6_coarse_grained_density_residual"] <= 1e-10
    assert not proxy["R6_common_erasure_coarse_graining_charged"]
    assert proxy["rows"]["R6i"]["cx"] - proxy["rows"]["R6"]["cx"] <= 1
    assert set(proxy["rows"]["shared_halmos_core"]["all_counts"]) <= {"u", "cx"}
    assert set(proxy["rows"]["R6"]["all_counts"]) <= {"u", "cx", "measure"}
    assert set(proxy["rows"]["R6i"]["all_counts"]) <= {"u", "cx"}
