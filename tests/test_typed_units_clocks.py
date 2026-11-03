"""Adversarial finite controls for physical dimensions, readouts and plural clocks.

These test exact matrix/arithmetic contracts. They do not independently
establish real-clock synchronization, SI calibration, or shared semantics.
"""
import numpy as np
import pytest


def basis(i):
    return tuple(int(j == i) for j in range(7))


def dimension_product(a, b):
    return tuple(x + y for x, y in zip(a, b))


def dimension_quotient(a, b):
    return tuple(x - y for x, y in zip(a, b))


def clock_residual(src, dst, tick, rate, offset, n):
    return rate * src(n) + offset - dst(tick(n))


def metric_defect(t, source_metric, target_metric):
    return t.T @ target_metric @ t - source_metric


def observed_defect(t, source_obs, target_obs, factor):
    return factor * source_obs - target_obs @ t


def test_dimension_indices_and_product_are_not_a_common_scalar():
    length, mass, time = basis(0), basis(1), basis(2)
    assert length != time
    assert mass != time
    velocity = dimension_quotient(length, time)
    assert velocity == (1, 0, -1, 0, 0, 0, 0)
    assert dimension_product(velocity, time) == length


@pytest.mark.parametrize("first,second", [(100., 0.01), (3., 5.), (0.2, 0.7)])
def test_positive_same_dimension_unit_factors_compose(first, second):
    assert first > 0 and second > 0
    for value in (0.1, 1., 53.7):
        assert second * (first * value) == pytest.approx(
            (second * first) * value)
        assert first * value > 0 and second * first * value > 0
    assert 100. * 1. == 100.


@pytest.mark.parametrize("a,b,c,d", [
    (2., 0., 3., 0.),
    (1.25, 0.5, 1.5, -2.),
    (0.75, -3., 4., 1.),
])
def test_clock_composition_keeps_both_local_residuals(a, b, c, d):
    src = lambda n: float(n) + 0.1
    mid = lambda n: float(n) * 1.7 + 3.
    dst = lambda n: float(n) * 2.1 - 0.7
    e_tick, f_tick = lambda n: 2*n, lambda n: 3*n
    assert a > 0 and c > 0
    for n in range(75):
        re = clock_residual(src, mid, e_tick, a, b, n)
        rf = clock_residual(mid, dst, f_tick, c, d, e_tick(n))
        total = clock_residual(
            src, dst, lambda i: f_tick(e_tick(i)),
            c*a, c*b + d, n)
        assert total == pytest.approx(c*re + rf, abs=2e-12)


def test_strictly_increasing_clocks_can_disagree_about_epoch():
    src = lambda n: float(n)
    dst = lambda n: float(n)
    assert all(src(n) < src(n+1) and dst(n) < dst(n+1)
               for n in range(60))
    assert clock_residual(src, dst, lambda n: n, 1., 1., 0) == 1.
    assert all(clock_residual(src, dst, lambda n: n, 1., 1., n) == 1.
               for n in range(60))


def test_two_exact_clock_bridges_compose_with_different_tick_indices():
    src, mid, dst = (lambda n: float(n) for _ in range(3))
    e_tick, f_tick = lambda n: 2*n, lambda n: 3*n
    for n in range(75):
        assert clock_residual(src, mid, e_tick, 2., 0., n) == 0.
        assert clock_residual(mid, dst, f_tick, 3., 0., e_tick(n)) == 0.
        assert clock_residual(
            src, dst, lambda i: f_tick(e_tick(i)), 6., 0., n) == 0.


@pytest.mark.parametrize("dims", [(2, 3, 4), (1, 2, 3)])
def test_full_geometric_and_observable_composition(dims):
    n, m, k = dims
    rng = np.random.default_rng(n + 311)
    t, s = rng.normal(size=(m, n)), rng.normal(size=(k, m))
    ax, ay, az = (rng.normal(size=(j, j)) for j in (n, m, k))
    gx, gy, gz = (x.T @ x + np.eye(j) for x, j in (
        (ax, n), (ay, m), (az, k)))
    ox, oy, oz = (rng.normal(size=(1, j)) for j in (n, m, k))

    lhs = metric_defect(s @ t, gx, gz)
    rhs = metric_defect(t, gx, gy) + (
        t.T @ metric_defect(s, gy, gz) @ t)
    np.testing.assert_allclose(lhs, rhs, atol=1e-11, rtol=1e-11)

    for u, v in [(100., 2.), (0.5, 3.)]:
        ro_e = observed_defect(t, ox, oy, u)
        ro_f = observed_defect(s, oy, oz, v)
        np.testing.assert_allclose(
            observed_defect(s @ t, ox, oz, v*u),
            v*ro_e + ro_f @ t, atol=1e-11, rtol=1e-11)


def test_perfect_geometry_does_not_entail_observer_or_clock_agreement():
    t = np.eye(2)
    metric = np.eye(2)
    source_obs = np.array([[1., 0.]])
    target_obs = np.zeros((1, 2))
    np.testing.assert_allclose(
        metric_defect(t, metric, metric), 0, atol=0)
    assert np.linalg.norm(
        observed_defect(t, source_obs, target_obs, 1.)) > 0
    assert clock_residual(
        lambda n: float(n), lambda n: float(n),
        lambda n: n, 1., 1., 3) == 1.


def test_jointly_compatible_positive_embedding_need_not_be_surjective():
    t = np.array([[1., 0.], [0., 1.], [0., 0.]])
    source_metric, target_metric = np.eye(2), np.eye(3)
    source_obs = np.array([[1., 0.]])
    target_obs = np.array([[100., 0., 0.]])
    np.testing.assert_allclose(
        metric_defect(t, source_metric, target_metric), 0, atol=0)
    np.testing.assert_allclose(
        observed_defect(t, source_obs, target_obs, 100.), 0, atol=0)
    for n in range(60):
        assert clock_residual(
            lambda i: float(i), lambda i: float(i),
            lambda i: 2*i, 2., 0., n) == 0.
    assert np.linalg.matrix_rank(t) == 2 < 3
