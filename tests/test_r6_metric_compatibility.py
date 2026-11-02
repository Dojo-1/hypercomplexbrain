"""Numerical adversarial controls for form-valued coordinate covariance.

These verify exact finite-dimensional algebra within tolerances; they do not
independently peer-review the Lean proof or establish physical quantum costs.
"""
import numpy as np
import pytest


def random_spd(rng):
    a = rng.normal(size=(2, 2))
    return a.T @ a + np.eye(2) * 0.25


def random_chart(rng):
    for _ in range(200):
        f = rng.normal(size=(2, 2))
        if abs(float(np.linalg.det(f))) > 0.4:
            return f
    raise AssertionError("no nondegenerate chart generated")


def defect(t, gx, gy):
    return t.T @ gy @ t - gx


@pytest.mark.parametrize("seed", [3, 17, 83])
def test_commuting_square_covariance_of_full_symmetric_form(seed):
    rng = np.random.default_rng(seed)
    for _ in range(90):
        f, g = random_chart(rng), random_chart(rng)
        t = rng.normal(size=(2, 2))
        gx, gy = random_spd(rng), random_spd(rng)
        tnew = np.linalg.solve(g, t @ f)
        dnew = defect(tnew, f.T @ gx @ f, g.T @ gy @ g)
        np.testing.assert_allclose(dnew, f.T @ defect(t, gx, gy) @ f,
                                   rtol=1e-10, atol=2e-9)


@pytest.mark.parametrize("seed", [11, 59])
def test_state_level_covariance_requires_state_transport(seed):
    rng = np.random.default_rng(seed)
    for _ in range(70):
        f, g = random_chart(rng), random_chart(rng)
        t = rng.normal(size=(2, 2))
        gx, gy = random_spd(rng), random_spd(rng)
        v = rng.normal(size=2)
        tnew = np.linalg.solve(g, t @ f)
        new = defect(tnew, f.T @ gx @ f, g.T @ gy @ g)
        old = defect(t, gx, gy)
        assert float(v @ new @ v) == pytest.approx(
            float((f @ v) @ old @ (f @ v)), abs=2e-9, rel=1e-10)


def test_anisotropic_chart_requires_transporting_the_metric():
    f = np.diag([2.0, 0.5])
    inv = np.diag([0.5, 2.0])
    np.testing.assert_allclose(f @ inv, np.eye(2), rtol=0, atol=0)
    np.testing.assert_allclose(inv @ f, np.eye(2), rtol=0, atol=0)
    d_matched = defect(f, f.T @ f, np.eye(2))
    d_unmatched = defect(f, np.eye(2), np.eye(2))
    np.testing.assert_allclose(d_matched, np.zeros((2, 2)), rtol=0, atol=0)
    np.testing.assert_allclose(d_unmatched, np.diag([3.0, -0.75]),
                               rtol=0, atol=0)


def test_singular_projection_hides_a_nonzero_form():
    projection = np.diag([1.0, 0.0])
    hidden = np.diag([0.0, 1.0])
    np.testing.assert_allclose(projection.T @ hidden @ projection,
                               np.zeros((2, 2)), rtol=0, atol=0)
    assert np.linalg.matrix_rank(projection) == 1
    assert np.linalg.norm(hidden) > 0


def test_compatible_metric_reflects_zero_under_invertible_chart():
    rng = np.random.default_rng(742)
    for _ in range(75):
        f, t = random_chart(rng), random_chart(rng)
        gy = random_spd(rng)
        gx = t.T @ gy @ t
        observed = defect(t @ f, f.T @ gx @ f, gy)
        np.testing.assert_allclose(observed, np.zeros((2, 2)),
                                   atol=2e-9, rtol=1e-10)
        recovered = np.linalg.solve(f.T, observed) @ np.linalg.inv(f)
        np.testing.assert_allclose(recovered, defect(t, gx, gy),
                                   atol=2e-9, rtol=1e-10)
