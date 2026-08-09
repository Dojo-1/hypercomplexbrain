import numpy as np

from run_hb0_r1w_competence import (
    correctness,
    coordination,
    delayed_correction,
    runtime_contract,
    tracking_instance,
)


def test_hb0_runtime_contract_is_live():
    report = runtime_contract()
    assert report["passed"]
    assert report["worldlets"] == 32
    assert set(report["clocks"]) >= {"fast", "meso", "slow"}
    assert set(report["identity_regimes"]) == {"somatic", "episodic", "social", "prospective"}


def test_tracking_correctness_invariants():
    report = correctness()
    assert report["passed"]
    assert report["max_orthogonality_defect"] <= 1e-10
    assert report["max_roundtrip_defect"] <= 1e-10


def test_task_generator_is_reproducible_and_method_independent():
    left = tracking_instance(16, 3)
    right = tracking_instance(16, 3)
    for a, b in zip(left[:3], right[:3]):
        if isinstance(a, dict):
            for key in a:
                assert np.array_equal(a[key], b[key])
        else:
            assert np.array_equal(a, b)


def test_mutual_recognition_mask_preserves_private_coordinate():
    report = coordination(2, "HB0_TYPED")
    assert report["private_leakage"] == 0.0
    assert report["viewpoint_asymmetry"] <= 0.05


def test_multiclock_policy_does_not_commit_provisional_false_state():
    report = delayed_correction(1, "HB0_TYPED")
    assert report["premature_slow_overwrite"] == 0.0
