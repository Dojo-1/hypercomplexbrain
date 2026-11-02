"""Independent matrix controls for the scoped R6 metric-pullback defect.

All matrices here are real 2x2. This is not a physical quantum or
cognition benchmark, nor an independent human mathematical review.
"""
import numpy as np
import pytest


def random_spd(rng):
    a = rng.normal(size=(2, 2))
    return a.T @ a + np.eye(2) * 0.25


def defect(M, gx, gy):
    return M.T @ gy @ M - gx


@pytest.mark.parametrize("seed", [7, 19, 73])
def test_pullback_observation_matches_before_after_quadratic_forms(seed):
    rng = np.random.default_rng(seed)
    for _ in range(80):
        m, gx, gy, v = rng.normal(size=(2, 2)), random_spd(rng), random_spd(rng), rng.normal(size=2)
        observed = float(v @ defect(m, gx, gy) @ v)
        direct = float((m @ v) @ gy @ (m @ v) - v @ gx @ v)
        assert observed == pytest.approx(direct, abs=1e-11, rel=1e-11)


@pytest.mark.parametrize("seed", [11, 27, 51])
def test_full_tensor_composition_and_matched_intermediate_form(seed):
    rng = np.random.default_rng(seed)
    for _ in range(80):
        t, s = rng.normal(size=(2, 2)), rng.normal(size=(2, 2))
        gx, gy, gz = random_spd(rng), random_spd(rng), random_spd(rng)
        lhs = defect(s @ t, gx, gz)
        rhs = defect(t, gx, gy) + t.T @ defect(s, gy, gz) @ t
        np.testing.assert_allclose(lhs, rhs, atol=1e-10, rtol=1e-12)


def test_intermediate_metric_mismatch_requires_correction_term():
    t = np.diag([2.0, 0.5])
    s = np.array([[1.0, 0.5], [-0.25, 1.0]])
    gx, gz = np.eye(2), 2.0 * np.eye(2)
    gy_out = np.diag([2.0, 3.0])
    gy_in = np.diag([1.0, 4.0])
    lhs = defect(s @ t, gx, gz)
    incorrect = defect(t, gx, gy_out) + t.T @ defect(s, gy_in, gz) @ t
    correction = t.T @ (gy_in - gy_out) @ t
    assert not np.allclose(lhs, incorrect)
    np.testing.assert_allclose(lhs, incorrect + correction, atol=1e-12)


def test_one_zero_scalar_does_not_annul_anisotropic_form():
    m = np.diag([2.0, 0.5])
    g = np.eye(2)
    d = defect(m, g, g)
    np.testing.assert_allclose(d, np.diag([3.0, -0.75]), atol=0)
    v = np.array([1.0, 2.0])
    assert float(v @ d @ v) == pytest.approx(0, abs=1e-15)
    assert np.linalg.norm(d, ord="fro") > 0
    assert float(d[0, 0]) > 0 > float(d[1, 1])


def test_identity_zero_defect_for_arbitrary_symmetric_form():
    for g in [np.array([[1, 0.7], [0.7, 2.0]]),
              np.diag([1.0, -1.0]),
              np.zeros((2, 2))]:
        np.testing.assert_allclose(defect(np.eye(2), g, g),
                                   np.zeros((2, 2)), atol=0)


def test_scalar_bridge_agrees_with_existing_euclidean_norm_instrument():
    rng = np.random.default_rng(29)
    for _ in range(80):
        m = rng.normal(size=(2, 2))
        v = rng.normal(size=2)
        old_scalar = float(np.linalg.norm(m @ v) ** 2 - np.linalg.norm(v) ** 2)
        new_scalar = float(v @ defect(m, np.eye(2), np.eye(2)) @ v)
        assert new_scalar == pytest.approx(old_scalar, abs=1e-11, rel=1e-11)
