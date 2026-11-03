"""Numerical controls for typed geometry, observation and clock remainders.

Clock channels here are linear state readouts, NOT synchronized physical time.
This test suite provides finite matrix controls, not semantic equivalence.
"""
import numpy as np
import pytest


def spd(rng, n):
    a = rng.normal(size=(n, n))
    return a.T @ a + 0.5 * np.eye(n)


def metric_defect(t, source_metric, target_metric):
    return t.T @ target_metric @ t - source_metric


def readout_defect(t, obs_source, obs_target, converter):
    return converter @ obs_source - obs_target @ t


@pytest.mark.parametrize("dims", [(2, 3, 4), (3, 2, 5)])
@pytest.mark.parametrize("seed", [7, 23, 91])
def test_mixed_dimensions_three_distinct_remainder_compositions(dims, seed):
    n, m, k = dims
    rng = np.random.default_rng(seed)
    for _ in range(65):
        t, s = rng.normal(size=(m, n)), rng.normal(size=(k, m))
        gx, gy, gz = spd(rng, n), spd(rng, m), spd(rng, k)
        oo, op, oq = 2, 3, 2
        to, tp, tq = 1, 2, 3
        ox, oy, oz = (rng.normal(size=d) for d in ((oo, n), (op, m), (oq, k)))
        cx, cy, cz = (rng.normal(size=d) for d in ((to, n), (tp, m), (tq, k)))
        u, v = rng.normal(size=(op, oo)), rng.normal(size=(oq, op))
        a, b = rng.normal(size=(tp, to)), rng.normal(size=(tq, tp))

        dg_e = metric_defect(t, gx, gy)
        dg_f = metric_defect(s, gy, gz)
        np.testing.assert_allclose(
            metric_defect(s @ t, gx, gz), dg_e + t.T @ dg_f @ t,
            atol=1e-9, rtol=1e-10)

        ro_e = readout_defect(t, ox, oy, u)
        ro_f = readout_defect(s, oy, oz, v)
        np.testing.assert_allclose(
            readout_defect(s @ t, ox, oz, v @ u),
            v @ ro_e + ro_f @ t, atol=1e-9, rtol=1e-10)

        rc_e = readout_defect(t, cx, cy, a)
        rc_f = readout_defect(s, cy, cz, b)
        np.testing.assert_allclose(
            readout_defect(s @ t, cx, cz, b @ a),
            b @ rc_e + rc_f @ t, atol=1e-9, rtol=1e-10)


def test_perfect_metric_bridge_need_not_preserve_any_observer():
    metric = np.eye(2)
    t = np.eye(2)
    src_observer = np.eye(2)
    tgt_observer = np.zeros((2, 2))
    src_clock, tgt_clock = np.eye(2), 2.0 * np.eye(2)
    unit_converter = np.eye(2)
    clock_converter = np.eye(2)
    np.testing.assert_allclose(metric_defect(t, metric, metric), 0, atol=0)
    assert np.linalg.norm(readout_defect(
        t, src_observer, tgt_observer, unit_converter)) > 0
    assert np.linalg.norm(readout_defect(
        t, src_clock, tgt_clock, clock_converter)) > 0


def test_exact_joint_compatibility_survives_composed_embeddings():
    t = np.array([[1., 0.], [0., 1.], [0., 0.]])  # 2 -> 3
    s = np.array([[1., 0., 0.], [0., 1., 0.],
                  [0., 0., 1.], [0., 0., 0.]])  # 3 -> 4
    gx, gy, gz = np.eye(2), np.eye(3), np.eye(4)
    ox, oy, oz = np.eye(2), np.array([[1., 0., 0.], [0., 1., 0.]]), (
        np.array([[1., 0., 0., 0.], [0., 1., 0., 0.]])
    )
    cx, cy, cz = np.array([[1., 0.]]), np.array([[1., 0., 0.]]), (
        np.array([[1., 0., 0., 0.]])
    )
    u, v = np.eye(2), np.eye(2)
    a, b = np.eye(1), np.eye(1)
    np.testing.assert_allclose(metric_defect(t, gx, gy), 0, atol=0)
    np.testing.assert_allclose(metric_defect(s, gy, gz), 0, atol=0)
    for r in (readout_defect(t, ox, oy, u), readout_defect(s, oy, oz, v),
              readout_defect(t, cx, cy, a), readout_defect(s, cy, cz, b),
              readout_defect(s @ t, ox, oz, v @ u),
              readout_defect(s @ t, cx, cz, b @ a)):
        np.testing.assert_allclose(r, 0, atol=0)


def test_changed_clock_conversion_is_not_inferred_from_metric():
    t = np.eye(2)
    g = np.eye(2)
    o = np.eye(2)
    c = np.array([[1., 0.]])
    np.testing.assert_allclose(metric_defect(t, g, g), 0, atol=0)
    np.testing.assert_allclose(readout_defect(t, o, o, np.eye(2)), 0, atol=0)
    assert np.linalg.norm(readout_defect(
        t, c, c, np.array([[2.]]))) > 0
