"""Heterogeneous Worldlet transport with independent finite-matrix controls.

Different dimensions are essential, not simulated by a square 2x2 matrix.
No software simulation establishes independent semantic or physical validity.
"""
import numpy as np
import pytest


def spd(rng, n):
    a = rng.normal(size=(n, n))
    return a.T @ a + 0.3 * np.eye(n)


def defect(t, x_metric, y_metric):
    """Source-typed full symmetric bilinear-form remainder."""
    return t.T @ y_metric @ t - x_metric


@pytest.mark.parametrize("dims", [(2, 3, 4), (4, 2, 1), (1, 4, 2)])
@pytest.mark.parametrize("seed", [3, 47])
def test_mixed_dimensions_form_composition(dims, seed):
    rng = np.random.default_rng(seed)
    n, m, k = dims
    for _ in range(65):
        t, s = rng.normal(size=(m, n)), rng.normal(size=(k, m))
        gx, gy, gz = spd(rng, n), spd(rng, m), spd(rng, k)
        lhs = defect(s @ t, gx, gz)
        rhs = defect(t, gx, gy) + t.T @ defect(s, gy, gz) @ t
        np.testing.assert_allclose(lhs, rhs, rtol=1e-11, atol=3e-10)
        assert lhs.shape == (n, n)


@pytest.mark.parametrize("dims", [(2, 3, 4), (4, 2, 3)])
def test_intermediate_metric_mismatch_retains_typed_source_remainder(dims):
    n, m, k = dims
    rng = np.random.default_rng(n * 100 + k)
    for _ in range(65):
        t, s = rng.normal(size=(m, n)), rng.normal(size=(k, m))
        gx, gy_out, gy_in, gz = (spd(rng, z) for z in (n, m, m, k))
        total = defect(s @ t, gx, gz)
        incorrect = defect(t, gx, gy_out) + t.T @ defect(s, gy_in, gz) @ t
        correction = t.T @ (gy_in - gy_out) @ t
        np.testing.assert_allclose(total, incorrect + correction, rtol=1e-11, atol=3e-10)


def test_projection_can_hide_a_nonzero_target_metric():
    t = np.array([[1.0], [0.0]])  # 1 -> 2, rank one
    hidden = np.diag([0.0, 1.0])
    np.testing.assert_allclose(t.T @ hidden @ t, np.zeros((1, 1)), atol=0)
    assert not np.allclose(hidden, np.zeros((2, 2)))


def test_nonidentical_local_dimensions_do_not_require_equal_metrics():
    t = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])  # 2 -> 3
    g_target = np.diag([2.0, 3.0, 100.0])
    g_source = t.T @ g_target @ t
    assert t.shape == (3, 2)
    np.testing.assert_allclose(defect(t, g_source, g_target),
                               np.zeros((2, 2)), atol=0)
    # Third target direction is unobserved by this 2D source; no equivalence.
    assert np.linalg.matrix_rank(t) < 3
