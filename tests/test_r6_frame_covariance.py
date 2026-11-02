"""Independent small-matrix controls for the scoped R6 frame theorem.

The existing production block encoder is exercised against an explicit
analytic frame conjugation. These tests are *not* Lean proof certificates or
physical quantum measurements. They guard semantic correspondence between
the formal statement and the live numeric operation.
"""

import math

import numpy as np
import pytest

from aionq.hyperbolic_qubit import block_encode


def rotation(theta: float) -> np.ndarray:
    """Real proper orthogonal change of two-dimensional frame."""
    return np.array([[math.cos(theta), -math.sin(theta)],
                     [math.sin(theta), math.cos(theta)]], dtype=float)


def cartan(depth: float) -> np.ndarray:
    return np.diag([math.exp(depth), math.exp(-depth)])


@pytest.mark.parametrize("rho", [0.0, 0.1, 0.7, 1.4, 2.0])
def test_live_block_matches_orthogonal_frame_transport(rho):
    """The live top-left block agrees with a separately constructed expression."""
    in_frame, out_frame = rotation(0.71), rotation(-1.13)
    M = out_frame @ cartan(rho) @ in_frame.T
    U, scale = block_encode(M)
    predicted = out_frame @ np.diag([1.0, math.exp(-2 * rho)]) @ in_frame.T

    assert scale == pytest.approx(math.exp(rho), rel=1e-12, abs=1e-12)
    np.testing.assert_allclose(U[:2, :2], predicted, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(U.T @ U, np.eye(4), rtol=0, atol=2e-12)


@pytest.mark.parametrize("rho", [0.0, 0.3, 1.0, 2.0])
def test_acceptance_bounds_and_frame_transported_extremizers(rho):
    rng = np.random.default_rng(6202026)
    F, G = rotation(0.61), rotation(-0.83)
    A = G @ np.diag([1.0, math.exp(-2 * rho)]) @ F.T
    lower = math.exp(-4 * rho)
    for _ in range(200):
        v = rng.normal(size=2)
        v /= np.linalg.norm(v)
        p = float(np.dot(A @ v, A @ v))
        assert lower - 2e-12 <= p <= 1 + 2e-12
    assert float(np.linalg.norm(A @ F[:, 1]) ** 2) == pytest.approx(lower, abs=1e-12)
    assert float(np.linalg.norm(A @ F[:, 0]) ** 2) == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize("rho", [0.0, 0.2, 0.8, 1.8])
def test_joint_frame_and_state_rotation_is_covariant(rho):
    rng = np.random.default_rng(1313)
    F, G, H = rotation(0.39), rotation(-1.11), rotation(0.77)
    K = np.diag([1.0, math.exp(-2 * rho)])
    A = G @ K @ F.T
    changed = (H @ G) @ K @ (H @ F).T
    for _ in range(100):
        v = rng.normal(size=2)
        v /= np.linalg.norm(v)
        np.testing.assert_allclose(changed @ (H @ v), H @ (A @ v),
                                   atol=2e-12, rtol=0)
        assert np.linalg.norm(changed @ (H @ v)) ** 2 == pytest.approx(
            np.linalg.norm(A @ v) ** 2, abs=2e-12)


def test_rotating_only_the_input_frame_can_change_physical_weight():
    """Negative control: frame covariance cannot imply state-fixed invariance."""
    rho = 1.0
    input_state = np.array([1.0, 0.0])
    fixed = np.diag([1.0, math.exp(-2 * rho)])
    rotated = fixed @ rotation(math.pi / 2).T
    p_fixed = float(np.linalg.norm(fixed @ input_state) ** 2)
    p_rotated = float(np.linalg.norm(rotated @ input_state) ** 2)
    assert p_fixed == pytest.approx(1.0, abs=1e-12)
    assert p_rotated == pytest.approx(math.exp(-4 * rho), abs=1e-12)
    assert p_rotated < p_fixed
