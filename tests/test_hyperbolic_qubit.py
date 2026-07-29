"""Tests for the unitary price of hyperbolic depth (QSigma-R6).

The predictions are closed form, so these are equality tests to machine
precision rather than threshold tests.  Where a tolerance appears it is because
a Monte Carlo or an eigendecomposition is involved, and it is stated with its
reason.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.hyperbolic_qubit import (block_encode, block_encoding_circuit,
                                    composed_success_probability,
                                    conjugacy_class, elliptic_fraction_analytic,
                                    from_sl2, generator_norm_diagnostic,
                                    is_orthogonal, q22, singular_values,
                                    so22_generators, success_probability,
                                    swirl_point, swirl_state, to_sl2)

GRID = [(r, p, s)
        for r in (0.0, 0.15, 0.5, 1.0, 2.0, 3.0)
        for p in (0.0, 0.7, 1.5708, 2.9, -1.2)
        for s in (0.0, 1.1, -2.4)]


# --------------------------------------------------------------- the identity

@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_det_is_the_quadratic_form(rho, phi, psi):
    """det(to_sl2(x)) == q22(x).  Not approximately: this is the same polynomial."""
    x = swirl_point(rho, phi, psi)
    assert np.linalg.det(to_sl2(x)) == pytest.approx(q22(x), abs=1e-13)
    assert q22(x) == pytest.approx(1.0, abs=1e-13)


@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_sl2_roundtrip(rho, phi, psi):
    x = swirl_point(rho, phi, psi)
    assert from_sl2(to_sl2(x)) == pytest.approx(x, abs=1e-13)


@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_swirl_state_roundtrip(rho, phi, psi):
    st = swirl_state(swirl_point(rho, phi, psi))
    assert st.rho == pytest.approx(rho, abs=1e-13)
    assert math.cos(st.phi) == pytest.approx(math.cos(phi), abs=1e-13)
    if rho > 1e-9:
        assert math.cos(st.psi) == pytest.approx(math.cos(psi), abs=1e-13)


# ------------------------------------------------------------------------ P1

@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_singular_values_are_exp_plus_minus_rho(rho, phi, psi):
    s = singular_values(to_sl2(swirl_point(rho, phi, psi)))
    assert s[0] == pytest.approx(math.exp(rho), abs=1e-12)
    assert s[1] == pytest.approx(math.exp(-rho), abs=1e-12)


@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_frobenius_norm_and_condition_number(rho, phi, psi):
    M = to_sl2(swirl_point(rho, phi, psi))
    assert float(np.sum(M * M)) == pytest.approx(2.0 * math.cosh(2.0 * rho), abs=1e-11)
    s = singular_values(M)
    assert s[0] / s[1] == pytest.approx(math.exp(2.0 * rho), rel=1e-11)


@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_unitary_if_and_only_if_zero_depth(rho, phi, psi):
    """The whole finding, as one assertion."""
    M = to_sl2(swirl_point(rho, phi, psi))
    assert is_orthogonal(M) == (rho == 0.0)


# ------------------------------------------------------------------------ P2

@pytest.mark.parametrize("rho", [0.0, 0.25, 0.5, 1.0, 2.0, 3.0])
def test_trace_formula(rho):
    for phi in (0.0, 0.6, 1.9, -2.5):
        M = to_sl2(swirl_point(rho, phi, 0.83))
        assert np.trace(M) == pytest.approx(2.0 * math.cosh(rho) * math.cos(phi), abs=1e-12)


@pytest.mark.parametrize("rho", [0.1, 0.5, 1.0, 2.0, 3.0])
def test_elliptic_fraction_matches_direct_quadrature(rho):
    """Check the closed form against brute-force integration, not against itself."""
    phis = np.linspace(-math.pi, math.pi, 2_000_001)
    direct = float(np.mean(np.abs(2.0 * math.cosh(rho) * np.cos(phis)) < 2.0))
    assert direct == pytest.approx(elliptic_fraction_analytic(rho), abs=1e-5)


def test_elliptic_fraction_decays_like_four_over_pi_exp_minus_rho():
    for rho in (4.0, 5.0, 6.0):
        assert elliptic_fraction_analytic(rho) == pytest.approx(
            4.0 / math.pi * math.exp(-rho), rel=1e-3)


def test_elliptic_is_not_the_same_as_unitary():
    """Conjugate to a rotation is not the same as being one.

    This is the trap the trace classification would set if read carelessly: the
    conjugating element is itself hyperbolic, so it is not a change of basis a
    quantum computer can perform for free.
    """
    M = to_sl2(swirl_point(1.5, math.pi / 2.0, 0.4))
    assert conjugacy_class(M) == "elliptic"
    assert not is_orthogonal(M)
    assert singular_values(M)[0] / singular_values(M)[1] == pytest.approx(
        math.exp(3.0), rel=1e-11)


# ------------------------------------------------------------------------ P3

@pytest.mark.parametrize("rho", [0.0, 0.1, 0.5, 1.0, 2.0, 3.0])
def test_average_success_probability_closed_form(rho):
    M = to_sl2(swirl_point(rho, 0.0, 0.0))
    assert success_probability(M) == pytest.approx((1.0 + math.exp(-4.0 * rho)) / 2.0,
                                                   abs=1e-12)


@pytest.mark.parametrize("rho", [0.2, 0.4, 0.8])
@pytest.mark.parametrize("L", [1, 2, 3, 4])
def test_worst_case_chain_is_exponential(rho, L):
    M = to_sl2(swirl_point(rho, 0.0, 0.0))
    p = composed_success_probability([M] * L, [0.0, 1.0])
    assert p == pytest.approx(math.exp(-4.0 * L * rho), abs=1e-12)


def test_average_case_saturates_and_worst_case_does_not():
    """Quoting either number alone misleads, so assert that they diverge."""
    deep = to_sl2(swirl_point(3.0, 0.0, 0.0))
    assert success_probability(deep) == pytest.approx(0.5, abs=1e-4)
    assert composed_success_probability([deep], [0.0, 1.0]) < 1e-5


# ------------------------------------------------------------------------ P4

def test_zero_depth_loop_is_exactly_free():
    from scipy.linalg import expm
    gens = so22_generators()
    word = [("K02", 0.9), ("K13", -0.4), ("K03", 1.1)]
    acc = np.eye(4)
    for name, amount in word + [(n, -a) for n, a in reversed(word)]:
        acc = expm(amount * gens[name]) @ acc
    x = acc @ swirl_point(0.0, 0.0, 0.0)
    assert swirl_state(x).rho == pytest.approx(0.0, abs=1e-12)
    assert is_orthogonal(to_sl2(x), tol=1e-10)
    assert success_probability(to_sl2(x)) == pytest.approx(1.0, abs=1e-10)


def test_stepwise_materialisation_still_pays():
    """The echo is free only if the net element may be compiled directly."""
    steps = [to_sl2(swirl_point(0.6, 0.0, 0.0)),
             to_sl2(swirl_point(0.6, math.pi, 0.0))]
    p = composed_success_probability(steps, [0.0, 1.0])
    assert p < 0.5


# -------------------------------------------------------------- the encoding

@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_block_encoding_is_orthogonal_and_carries_the_matrix(rho, phi, psi):
    M = to_sl2(swirl_point(rho, phi, psi))
    U, s = block_encode(M)
    assert np.max(np.abs(U @ U.T - np.eye(4))) < 1e-13
    assert np.max(np.abs(U[:2, :2] - M / s)) < 1e-13
    assert s == pytest.approx(math.exp(rho), abs=1e-12)


@pytest.mark.parametrize("rho,phi,psi", GRID)
def test_compiled_circuit_equals_the_encoding(rho, phi, psi):
    from qiskit.quantum_info import Operator
    M = to_sl2(swirl_point(rho, phi, psi))
    U, s = block_encode(M)
    qc, _ = block_encoding_circuit(M)
    compiled = np.asarray(Operator(qc).data)
    assert np.max(np.abs(compiled - U)) < 1e-13
    assert np.max(np.abs(compiled @ compiled.conj().T - np.eye(4))) < 1e-13


@pytest.mark.parametrize("phi", [0.0, 0.4, 0.9, 2.2, -1.7])
def test_zero_depth_encoding_has_no_leakage(phi):
    """Regression: sqrt of rounding noise is not small.

    The first run of QSigma-R6 produced 4e-9 of spurious ancilla leakage at
    rho = 0, because ``I - A A^T`` is exactly zero there, ``eigh`` returns
    +-1e-16 for it, and sqrt(1e-16) is 1e-8.  The error was eight orders of
    magnitude larger than the noise that caused it, and it sat exactly in the
    regime the round claims is free.

    The C1 amplitude-level control caught it at 1e-12; the C2 probability-level
    control did not, because leakage enters a probability squared.  This test
    pins the amplitude, which is the level at which the defect is visible.
    """
    M = to_sl2(swirl_point(0.0, phi, 0.0))
    U, s = block_encode(M)
    assert s == pytest.approx(1.0, abs=1e-13)
    assert np.max(np.abs(U[:2, 2:])) < 1e-14, "off-diagonal block must be zero"
    assert np.max(np.abs(U[2:, :2])) < 1e-14
    assert np.max(np.abs(U @ U.T - np.eye(4))) < 1e-14


# ------------------------------------------------------- the wrong instrument

def test_generator_norms_cannot_distinguish_compact_from_non_compact():
    """S8 said the generators are unbounded. They are not, and they are equal.

    All six so(2,2) generators have Frobenius norm sqrt(2). A norm that assigns
    the same number to a rotation generator and a boost generator cannot be the
    instrument that separates them.
    """
    norms = {k: float(np.linalg.norm(v, "fro")) for k, v in so22_generators().items()}
    assert set(round(v, 12) for v in norms.values()) == {round(math.sqrt(2.0), 12)}


def test_group_norm_diverges_for_boosts_and_is_constant_for_rotations():
    rows = [generator_norm_diagnostic(r) for r in (0.0, 1.0, 2.0, 3.0)]
    rotations = [r["group_frobenius_rotation_J01"] for r in rows]
    boosts = [r["group_frobenius_boost_K02"] for r in rows]
    assert max(rotations) - min(rotations) < 1e-12
    assert boosts == sorted(boosts) and boosts[-1] > 10 * boosts[0]


# ---------------------------------- the word that stood wrong for three commits

def _linear_map(action) -> np.ndarray:
    """The 4x4 matrix of a linear map on R^{2,2}, read off the standard basis."""
    cols = []
    for i in range(4):
        e = np.zeros(4)
        e[i] = 1.0
        cols.append(from_sl2(action(to_sl2(e))))
    return np.column_stack(cols)


def test_so22_is_semisimple_and_not_simple():
    """The correction, made executable through this repository's own map.

    Three commits of R6 called SO_0(2,2) 'simple'. It is SEMISIMPLE: the algebra
    splits, ``so(2,2) = sl(2,R) + sl(2,R)``, so it has two proper nonzero ideals
    and the word was wrong. An external reader caught it; nothing here would have.

    The split is not quoted, it is built -- and out of ``to_sl2``, the map the
    whole R6 arc runs on. Because ``det(AM) = det(MA) = det M`` for ``A`` of unit
    determinant, LEFT and RIGHT multiplication by ``sl(2,R)`` each act on
    ``R^{2,2}`` preserving ``q22``, and they commute because matrix
    multiplication is associative. Two commuting 3-dimensional ideals spanning
    all six directions is exactly the statement.

    Semisimplicity gets Cartan's criterion: the Killing form is nondegenerate.
    Both halves are asserted, because 'not simple' alone is also true of an
    abelian algebra and would say nothing.
    """
    eta = np.diag([1.0, 1.0, -1.0, -1.0])
    sl2 = [np.array([[1.0, 0.0], [0.0, -1.0]]),
           np.array([[0.0, 1.0], [0.0, 0.0]]),
           np.array([[0.0, 0.0], [1.0, 0.0]])]

    left = [_linear_map(lambda M, A=A: A @ M) for A in sl2]
    right = [_linear_map(lambda M, A=A: M @ A) for A in sl2]

    # Both families really are so(2,2): X^T eta + eta X = 0.
    for X in left + right:
        assert np.max(np.abs(X.T @ eta + eta @ X)) < 1e-12

    # ... and they span the same six directions as the module's own generators.
    G = np.column_stack([v.reshape(-1) for v in so22_generators().values()])
    S = np.column_stack([X.reshape(-1) for X in left + right])
    assert np.linalg.matrix_rank(S, tol=1e-10) == 6
    assert np.linalg.matrix_rank(np.column_stack([G, S]), tol=1e-10) == 6

    # NOT SIMPLE: the two halves commute, so each is a proper nonzero ideal.
    for L in left:
        for R in right:
            assert np.max(np.abs(L @ R - R @ L)) < 1e-12
    assert np.linalg.matrix_rank(
        np.column_stack([X.reshape(-1) for X in left]), tol=1e-10) == 3

    # SEMISIMPLE: Killing form nondegenerate on the six-dimensional algebra.
    basis = left + right
    coords = np.column_stack([X.reshape(-1) for X in basis])
    inv = np.linalg.pinv(coords)

    def ad(X):
        return np.column_stack([inv @ (X @ Y - Y @ X).reshape(-1) for Y in basis])

    ads = [ad(X) for X in basis]
    killing = np.array([[float(np.trace(a @ b)) for b in ads] for a in ads])
    assert abs(np.linalg.det(killing)) > 1e-6
    # An abelian algebra would also fail to be simple; its Killing form is zero.
    assert np.min(np.abs(np.linalg.eigvalsh(killing))) > 1e-6
