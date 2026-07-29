"""QΣ-R3B-0: frozen four-cell calibration and missingness governance."""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import run_four_cell_calibration as runner

from aionq.advantage import (
    OUTCOME_DIMENSIONS,
    AdvantageCone,
    Direction,
    EffectPosterior,
    EmpiricalEffectPosterior,
    OutcomeVector,
    promote,
)
from aionq.four_cell import (
    Arm,
    CALIBRATION_PHASES,
    COMMON_FRAMES,
    HELDOUT_PHASES,
    REPETITIONS_PER_FACTOR_CELL,
    TRIALS_PER_ARM_PER_SEED,
    Cell,
    Relation,
    TrialSpec,
    analytic_click_probability,
    basis_attack_observable,
    complete_dephase,
    execute_four_cell,
    phase_density,
    protocol_schedule,
    role_ablation_observables,
    run_protocol_arm,
    run_seed_calibration,
    run_trial,
)


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = (
    ROOT / "manifests" / "qsigma_r3b_four_cell_calibration_preregistration.json"
)
OBSERVED = ("accuracy", "generalization", "robustness", "calibration")
MISSING = ("sample_efficiency", "neg_energy", "neg_latency", "recovery")


def _registered_vector(
    accuracy: float,
    generalization: float,
    robustness: float,
    calibration: float,
) -> OutcomeVector:
    return OutcomeVector.from_mapping(
        {
            "accuracy": accuracy,
            "generalization": generalization,
            "robustness": robustness,
            "calibration": calibration,
        }
    )


def _registered_cone() -> AdvantageCone:
    return AdvantageCone(
        name="K_R3B0_CALIBRATION",
        constraints={
            "accuracy": Direction.IMPROVE,
            "generalization": Direction.IMPROVE,
            "robustness": Direction.IMPROVE,
            "sample_efficiency": Direction.NO_WORSE,
            "calibration": Direction.IMPROVE,
            "neg_energy": Direction.NO_WORSE,
            "neg_latency": Direction.NO_WORSE,
            "recovery": Direction.NO_WORSE,
        },
        margins={
            "accuracy": 0.2,
            "generalization": 0.2,
            "robustness": 0.2,
            "calibration": 0.1,
        },
        tolerance=0.02,
    )


def test_manifest_is_the_frozen_protocol_surface():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "FROZEN_BEFORE_EXECUTION_AND_RESULTS"
    assert tuple(manifest["protocol"]["calibration_phases"]) == pytest.approx(
        CALIBRATION_PHASES
    )
    assert tuple(manifest["protocol"]["heldout_phases"]) == pytest.approx(
        HELDOUT_PHASES
    )
    assert tuple(manifest["protocol"]["common_frames"]) == COMMON_FRAMES
    assert manifest["protocol"]["repetitions_per_factor_cell"] == (
        REPETITIONS_PER_FACTOR_CELL
    )
    assert manifest["protocol"]["trials_per_arm_per_seed"] == (
        TRIALS_PER_ARM_PER_SEED
    )
    assert tuple(manifest["outcome_contract"]["coordinate_order"]) == (
        OUTCOME_DIMENSIONS
    )
    assert manifest["advantage_cone"]["no_worse_tolerance"] == 0.02
    assert manifest["advantage_cone"]["registered_outcome"] == "HOLD"


def test_phase_density_and_dephasing_are_physical():
    for phase in CALIBRATION_PHASES + HELDOUT_PHASES:
        density = phase_density(phase)
        dephased = complete_dephase(density)
        for state in (density, dephased):
            assert state.shape == (2, 2)
            assert np.allclose(state, state.conj().T, atol=1e-12)
            assert np.trace(state).real == pytest.approx(1.0, abs=1e-12)
            assert np.min(np.linalg.eigvalsh(state)) >= -1e-12
        assert np.allclose(dephased, np.eye(2) / 2.0, atol=1e-12)


@pytest.mark.parametrize(
    ("arm", "relation", "expected"),
    [
        (Arm.COHERENT, Relation.SAME, 1.0),
        (Arm.COHERENT, Relation.ORTHOGONAL, 0.0),
        (Arm.DEPHASED, Relation.SAME, 0.5),
        (Arm.DEPHASED, Relation.ORTHOGONAL, 0.5),
    ],
)
def test_analytic_oracle_survives_every_registered_frame(arm, relation, expected):
    for phase in CALIBRATION_PHASES + HELDOUT_PHASES:
        assert analytic_click_probability(phase, relation, arm) == expected
        for frame in COMMON_FRAMES:
            result = run_trial(
                TrialSpec(phase, relation, arm, 73001, frame, repetition=0)
            )
            assert result.click_probability == pytest.approx(expected, abs=1e-12)
            assert len(result.cells) == 4
            assert {cell.role for cell in result.cells} == set(Cell)
            assert result.povm.completeness_defect <= 1e-12


def test_schedule_has_the_registered_64_64_384_partition():
    schedule = protocol_schedule(73001, Arm.COHERENT)
    assert len(schedule) == 512
    calibration = [
        spec
        for spec in schedule
        if spec.frame == "I" and spec.reference_phase in CALIBRATION_PHASES
    ]
    heldout = [
        spec
        for spec in schedule
        if spec.frame == "I" and spec.reference_phase in HELDOUT_PHASES
    ]
    robust = [spec for spec in schedule if spec.frame != "I"]
    assert (len(calibration), len(heldout), len(robust)) == (64, 64, 384)
    assert len({spec.pair_key for spec in schedule}) == 512


def test_paired_arms_share_schedule_and_uniforms_but_not_memory_channel():
    target = run_protocol_arm(73001, Arm.COHERENT)
    control = run_protocol_arm(73001, Arm.DEPHASED)
    assert [trial.spec.pair_key for trial in target.trials] == [
        trial.spec.pair_key for trial in control.trials
    ]
    assert np.array_equal(
        [trial.uniform_draw for trial in target.trials],
        [trial.uniform_draw for trial in control.trials],
    )
    assert target.outcome.as_dict()["accuracy"] == 1.0
    assert target.outcome.as_dict()["calibration"] == 1.0
    assert control.outcome.as_dict()["calibration"] == 0.75


def test_seed_replay_is_exact_and_different_seed_changes_stream():
    first = run_protocol_arm(73005, Arm.DEPHASED)
    replay = run_protocol_arm(73005, Arm.DEPHASED)
    other = run_protocol_arm(73006, Arm.DEPHASED)
    first_uniforms = [trial.uniform_draw for trial in first.trials]
    assert first_uniforms == [trial.uniform_draw for trial in replay.trials]
    assert first.outcome.as_dict() == replay.outcome.as_dict()
    assert first_uniforms != [trial.uniform_draw for trial in other.trials]


def test_covariant_frame_control_and_basis_attack_are_distinct():
    observable = basis_attack_observable()
    assert observable.covariant_max_defect <= 1e-12
    assert observable.untransported_povm_max_shift >= 0.99
    assert observable.covariant
    assert observable.attack_detected


def test_every_cell_ablation_is_a_typed_hold():
    spec = TrialSpec(
        CALIBRATION_PHASES[0],
        Relation.SAME,
        Arm.COHERENT,
        seed=73001,
    )
    observables = role_ablation_observables(spec)
    assert {item.role for item in observables} == set(Cell)
    for item in observables:
        assert item.decision == "HOLD"
        assert item.typed_refusal
        assert set(item.attempted_roles) == set(Cell) - {item.role}
        direct = execute_four_cell(spec, item.attempted_roles)
        assert direct == item
    complete = execute_four_cell(spec, tuple(Cell))
    assert complete.correct


def test_seed_calibration_is_positive_control_but_registered_hold():
    result = run_seed_calibration(73001)
    assert result.controls_hold
    assert result.parity.holds
    assert result.auditor.holds
    assert result.registered_decision == "HOLD"
    assert result.paired_outcome.delta.missing_dimensions == MISSING
    assert result.paired_outcome.delta.as_dict()["accuracy"] > 0.2
    assert result.paired_outcome.delta.as_dict()["generalization"] > 0.2
    assert result.paired_outcome.delta.as_dict()["robustness"] > 0.2
    assert result.paired_outcome.delta.as_dict()["calibration"] == 0.25


def test_outcome_vector_requires_nan_plus_mask_and_refuses_scalarization():
    vector = _registered_vector(1.0, 1.0, 1.0, 1.0)
    assert vector.missing_dimensions == MISSING
    assert tuple(
        dim
        for dim, present in zip(OUTCOME_DIMENSIONS, vector.observed)
        if present
    ) == OBSERVED
    with pytest.raises(TypeError, match="no scalar conversion"):
        float(vector)
    values = vector.values.copy()
    values[3] = 0.0
    with pytest.raises(ValueError, match="unobserved"):
        OutcomeVector(values, vector.observed)
    values = vector.values.copy()
    values[0] = np.nan
    with pytest.raises(ValueError, match="observed"):
        OutcomeVector(values, vector.observed)


def test_empirical_bootstrap_preserves_paired_cluster_dependence():
    controls = [
        _registered_vector(0.4, 0.3, 0.2, 0.75),
        _registered_vector(0.5, 0.4, 0.3, 0.75),
        _registered_vector(0.6, 0.5, 0.4, 0.75),
    ]
    targets = [
        _registered_vector(0.5, 0.5, 0.5, 1.0),
        _registered_vector(0.7, 0.8, 0.9, 1.0),
        _registered_vector(0.9, 1.1, 1.3, 1.0),
    ]
    posterior = EmpiricalEffectPosterior.from_paired(
        targets, controls, draws=2000, seed=314159
    )
    # Per-cluster generalization effects are exactly 2x accuracy effects.
    assert np.allclose(
        posterior.cluster_effects[:, 1],
        2.0 * posterior.cluster_effects[:, 0],
    )
    assert np.allclose(
        posterior.bootstrap_draws[:, 1],
        2.0 * posterior.bootstrap_draws[:, 0],
    )
    assert posterior.missing_dimensions == MISSING
    assert posterior.sample(10, seed=4).shape == (10, 8)
    assert posterior.draw_digest == posterior.draw_digest
    assert posterior.interval(0.99)["sample_efficiency"] is None


def test_missing_constrained_axes_block_before_sampling(monkeypatch):
    targets = [_registered_vector(1.0, 1.0, 1.0, 1.0)] * 3
    controls = [_registered_vector(0.5, 0.5, 0.5, 0.75)] * 3
    posterior = EmpiricalEffectPosterior.from_paired(
        targets, controls, draws=100, seed=314159
    )

    def forbidden_sample(*args, **kwargs):
        raise AssertionError("promotion sampled despite constrained missing axes")

    monkeypatch.setattr(posterior, "sample", forbidden_sample)
    decision = promote(
        posterior,
        _registered_cone(),
        alpha=0.01,
        audit=0.0,
        audit_threshold=1.0,
        samples=20_000,
        seed=271828,
    )
    assert not decision.promoted
    assert decision.probability is None
    assert any("unmeasured" in blocker for blocker in decision.blockers)
    assert any("audit" in blocker for blocker in decision.blockers)


def test_cone_rejects_nonfinite_constrained_coordinate():
    vector = np.zeros(len(OUTCOME_DIMENSIONS))
    vector[0] = np.nan
    assert not _registered_cone().contains(vector)


def test_legacy_gaussian_posterior_still_validates_and_samples():
    mean = np.zeros(len(OUTCOME_DIMENSIONS))
    covariance = np.eye(len(OUTCOME_DIMENSIONS)) * 1e-4
    posterior = EffectPosterior(mean, covariance)
    assert posterior.sample(3, seed=1).shape == (3, 8)
    with pytest.raises(ValueError, match="shape"):
        EffectPosterior(np.zeros(7), covariance)
    with pytest.raises(ValueError, match="positive semidefinite"):
        EffectPosterior(mean, -np.eye(8))


def test_kernel_contains_no_assignment_to_retired_q_causal():
    tree = ast.parse((ROOT / "src" / "aionq" / "four_cell.py").read_text())
    assigned_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    assigned_attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
    }
    assert "q_causal" not in assigned_names | assigned_attributes


def test_phase_sets_are_disjoint_modulo_two_pi():
    calibration = {round(value % (2 * math.pi), 12) for value in CALIBRATION_PHASES}
    heldout = {round(value % (2 * math.pi), 12) for value in HELDOUT_PHASES}
    assert calibration.isdisjoint(heldout)


def test_result_producer_is_append_once(tmp_path, monkeypatch):
    existing = tmp_path / "four_cell_calibration.json"
    existing.write_text("already bound", encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT", existing)
    monkeypatch.setattr(
        runner, "ENVELOPE", tmp_path / "four_cell_calibration.envelope.json"
    )
    with pytest.raises(FileExistsError, match="append-once"):
        runner.main()
    assert existing.read_text(encoding="utf-8") == "already bound"


def test_result_producer_refuses_dirty_head_provenance(monkeypatch):
    monkeypatch.setattr(runner, "current_commit", lambda root: "a" * 40)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=" M src/aionq/four_cell.py\n",
            stderr="",
        ),
    )
    with pytest.raises(RuntimeError, match="clean worktree"):
        runner._assert_clean_producer_state()


def test_strict_result_json_accepts_numpy_derived_control_flags():
    controls = {
        "joint_bootstrap": np.all(np.array([True, True])),
        "frame_covariance": np.allclose([0.0], [0.0]),
    }
    normalized = runner._native_bools(controls)
    encoded = json.dumps(normalized, allow_nan=False, sort_keys=True)
    assert encoded == '{"frame_covariance": true, "joint_bootstrap": true}'
