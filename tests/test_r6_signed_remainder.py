"""Adversarial numerical checks of signed R6 squared-norm remainders.

Not physical-energy measurement, quantum advantage, or independent Lean proof.
"""
import math

import numpy as np
import pytest


def delta(A, v):
    out = A @ v
    return float(out @ out - v @ v)


def positive_negative(d):
    return max(d, 0.0), max(-d, 0.0)


def rotation(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=float)


@pytest.mark.parametrize("rho", [0.15, 0.8, 1.6])
def test_expanding_and_contracting_axes_are_opposite(rho):
    B = np.diag([math.exp(rho), math.exp(-rho)])
    d1 = delta(B, np.array([1.0, 0.0]))
    d2 = delta(B, np.array([0.0, 1.0]))
    assert d1 == pytest.approx(math.exp(2 * rho) - 1, abs=1e-12)
    assert d2 == pytest.approx(math.exp(-2 * rho) - 1, abs=1e-12)
    assert d1 > 0 > d2


def test_nonnegative_signed_parts_balance_and_exclusion():
    for d in [-7.0, -0.001, 0.0, 0.002, 4.5]:
        plus, minus = positive_negative(d)
        assert plus >= 0 and minus >= 0
        assert plus == 0 or minus == 0
        assert plus - minus == pytest.approx(d)


def test_composition_uses_intermediate_state_not_original_state():
    rng = np.random.default_rng(4456)
    for _ in range(200):
        A, B = rng.normal(size=(2, 2)), rng.normal(size=(2, 2))
        v = rng.normal(size=2)
        assert delta(B @ A, v) == pytest.approx(
            delta(A, v) + delta(B, A @ v), rel=1e-12, abs=2e-12)
    A, B, v = np.diag([2.0, 0.5]), np.diag([0.5, 2.0]), np.array([1.0, 0.0])
    assert delta(B @ A, v) == pytest.approx(0)
    assert delta(A, v) + delta(B, v) != pytest.approx(0)


@pytest.mark.parametrize("rho", [0.1, 0.7, 1.4])
def test_closed_loop_has_nonzero_local_remainders(rho):
    B = np.diag([math.exp(rho), math.exp(-rho)])
    I = np.diag([math.exp(-rho), math.exp(rho)])
    v = np.array([1.0, 0.0])
    assert delta(I @ B, v) == pytest.approx(0, abs=1e-12)
    assert delta(B, v) > 0
    assert delta(I, B @ v) < 0


@pytest.mark.parametrize("seed", [2, 17, 92])
def test_both_signs_covary_under_orthogonal_reframing(seed):
    rng = np.random.default_rng(seed)
    F, G = rotation(0.8), rotation(-1.11)
    for _ in range(100):
        T = rng.normal(size=(2, 2))
        v = rng.normal(size=2)
        transported = G @ T @ F.T
        observed = delta(transported, F @ v)
        reference = delta(T, v)
        assert observed == pytest.approx(reference, rel=1e-12, abs=2e-12)
        np.testing.assert_allclose(positive_negative(observed),
                                   positive_negative(reference),
                                   rtol=1e-12, atol=2e-12)


def test_nonorthogonal_transport_is_not_a_free_reframe():
    v = np.array([1.0, 0.0])
    assert delta(np.diag([2.0, 0.5]), v) == pytest.approx(3.0)
    assert delta(np.eye(2), v) == pytest.approx(0.0)


@pytest.mark.parametrize("rho", [0.0, 0.2, 0.9, 1.7])
def test_normalized_filter_does_not_expand(rho):
    rng = np.random.default_rng(1)
    K = np.diag([1.0, math.exp(-2 * rho)])
    for _ in range(100):
        v = rng.normal(size=2)
        d = delta(K, v)
        assert d <= 2e-12
        assert positive_negative(d)[0] <= 2e-12
