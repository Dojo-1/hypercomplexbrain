"""Rank and metric positivity tests for typed heterogeneous Worldlets.

Finite NumPy checks are independent matrix controls, not a Lean proof
witness and not a physical quantum/cognition experiment.
"""
import numpy as np
import pytest


def target_spd(rng, n):
    a = rng.normal(size=(n, n))
    return a.T @ a + 0.5 * np.eye(n)


@pytest.mark.parametrize("dims", [(1, 2), (2, 3), (3, 2), (3, 3), (4, 6), (6, 4)])
@pytest.mark.parametrize("seed", [9, 31, 107])
def test_positive_pullback_iff_full_column_rank(dims, seed):
    n, m = dims
    rng = np.random.default_rng(seed + 31 * n + m)
    for _ in range(35):
        t = rng.normal(size=(m, n))
        g = target_spd(rng, m)
        pullback = t.T @ g @ t
        eigs = np.linalg.eigvalsh(pullback)
        full_col_rank = np.linalg.matrix_rank(t, tol=1e-9) == n
        assert (float(eigs.min()) > 1e-8) == full_col_rank


@pytest.mark.parametrize("dims", [(2, 3), (3, 4), (4, 4)])
def test_manufactured_nontrivial_kernel_destroyed_strict_positivity(dims):
    n, m = dims
    rng = np.random.default_rng(255)
    t = rng.normal(size=(m, n))
    t[:, -1] = t[:, 0]
    g = target_spd(rng, m)
    null = np.zeros(n)
    null[0], null[-1] = 1.0, -1.0
    assert np.linalg.norm(null) > 0
    assert np.linalg.norm(t @ null) < 1e-12
    assert abs(float(null @ (t.T @ g @ t) @ null)) < 1e-10
    assert np.linalg.matrix_rank(t) < n


def test_injectivity_alone_does_not_make_indefinite_metric_positive():
    t = np.eye(2)
    assert np.linalg.matrix_rank(t) == 2
    for target in [np.zeros((2, 2)), np.diag([1.0, -1.0])]:
        pulled = t.T @ target @ t
        assert np.linalg.eigvalsh(pulled).min() <= 0


def test_zero_defect_and_positive_source_does_not_imply_surjectivity():
    t = np.array([[1., 0.], [0., 1.], [0., 0.]])
    target = np.diag([2., 3., 9.])
    source = t.T @ target @ t
    np.testing.assert_allclose(t.T @ target @ t - source, 0, atol=0, rtol=0)
    assert np.linalg.matrix_rank(t) == 2 < 3
    assert np.linalg.eigvalsh(source).min() > 0


def test_zero_transport_preserves_nonnegativity_but_not_positivity():
    t = np.zeros((3, 2))
    g = np.eye(3)
    pulled = t.T @ g @ t
    assert np.linalg.matrix_rank(t) == 0
    np.testing.assert_allclose(pulled, 0, atol=0, rtol=0)
    assert np.linalg.eigvalsh(pulled).min() >= 0


@pytest.mark.parametrize("n,m,k", [(2, 3, 4), (1, 2, 3), (3, 4, 6)])
def test_composed_injective_tendrils_preserve_positive_pullback(n, m, k):
    t = np.zeros((m, n))
    s = np.zeros((k, m))
    t[:n, :] = np.eye(n)
    s[:m, :] = np.eye(m)
    g = np.diag(np.arange(1, k+1, dtype=float))
    pulled = (s @ t).T @ g @ (s @ t)
    assert np.linalg.eigvalsh(pulled).min() > 0
