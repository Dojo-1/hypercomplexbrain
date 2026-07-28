"""Verification of the external quantum-channel derivation (QSigma-R6b).

The closed forms under test were derived elsewhere and published before this file
existed. Every check here recomputes them by a route that never sees them --
finite differences for the Fisher information, dense linear algebra for the
distances -- so agreement is evidence rather than restatement.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import (analytic_qfi, attempted_use_state,
                                            conditional_concurrence,
                                            induced_metric_signature, kappa,
                                            normalised_A, numeric_qfi,
                                            operational_qfi_volume, p_bell,
                                            q_of_rho, rho_of_q,
                                            root_fidelity_closed_form,
                                            trace_distance_closed_form,
                                            volume_form_distortion)

RHOS = [0.3, 0.6, 1.0, 1.5, 2.0, 3.0]


def _state(rho, phi, psi):
    return attempted_use_state(to_sl2(swirl_point(rho, phi, psi)))[0]


# ------------------------------------------------ the compactification itself

@pytest.mark.parametrize("rho", RHOS)
def test_normalisation_sends_singular_values_to_one_and_q(rho):
    A = normalised_A(to_sl2(swirl_point(rho, 0.4, 0.9)))
    s = np.linalg.svd(A, compute_uv=False)
    assert s[0] == pytest.approx(1.0, abs=1e-12)
    assert s[1] == pytest.approx(q_of_rho(rho), abs=1e-12)


@pytest.mark.parametrize("rho", RHOS)
def test_depth_is_compactified_not_deleted(rho):
    """det A = q still names the depth: the coordinate survives, ill-conditioned."""
    A = normalised_A(to_sl2(swirl_point(rho, 1.1, -0.3)))
    assert abs(float(np.linalg.det(A))) == pytest.approx(q_of_rho(rho), abs=1e-12)
    assert rho_of_q(q_of_rho(rho)) == pytest.approx(rho, abs=1e-12)
    assert 0.0 < q_of_rho(rho) <= 1.0


# ------------------------------------------------------------------------ QFI

@pytest.mark.parametrize("rho", RHOS)
def test_numeric_qfi_matches_the_closed_form(rho):
    J = numeric_qfi((rho, 0.4, 0.9), _state)
    A = analytic_qfi(rho)
    assert np.allclose(np.diag(J), np.diag(A), rtol=1e-6)


@pytest.mark.parametrize("rho", RHOS)
def test_qfi_is_diagonal(rho):
    J = numeric_qfi((rho, 0.4, 0.9), _state)
    assert np.max(np.abs(J - np.diag(np.diag(J)))) < 1e-8


def test_radial_information_decays_at_the_r6_cost_exponent():
    """J_rr ~ 8 e^{-4 rho}: the same exponent R6 measured as post-selection cost.

    Two independent routes -- one a block-encoding survival probability, the other
    a Fisher information -- landing on the same exponent is the substance of the
    claim that operational information does not inherit source growth.
    """
    for rho in (2.0, 2.5, 3.0):
        assert analytic_qfi(rho)[0, 0] == pytest.approx(8.0 * math.exp(-4.0 * rho),
                                                        rel=1e-3)


def test_angular_information_saturates_while_radial_vanishes():
    deep = analytic_qfi(6.0)
    assert deep[1, 1] == pytest.approx(1.0, abs=1e-4)
    assert deep[2, 2] == pytest.approx(1.0, abs=1e-4)
    assert deep[0, 0] < 1e-9


def test_operational_volume_is_finite_and_the_constant_is_corrected():
    """sqrt(2) pi^3, not 2 pi^3 -- one constant, off by exactly sqrt(2).

    det J = 8 q^2 (1 - q^2), so sqrt(det J) = 2 sqrt2 q sqrt(1-q^2); writing sqrt8
    as 4 gives the reported value. Finiteness, which is the actual claim, is
    unaffected.
    """
    from scipy.integrate import quad
    v = operational_qfi_volume()

    def integrand(rho):
        q = q_of_rho(rho)
        return math.sqrt((8.0 / (math.exp(4.0 * rho) - 1.0))
                         * (1.0 + q) ** 2 * (1.0 - q) ** 2)

    numeric = quad(integrand, 1e-9, 60.0)[0] * (2.0 * math.pi) ** 2
    assert numeric == pytest.approx(v["value"], rel=1e-8)
    assert v["value"] == pytest.approx(math.sqrt(2.0) * math.pi ** 3, rel=1e-12)
    assert v["ratio_to_reported"] == pytest.approx(1.0 / math.sqrt(2.0), rel=1e-12)
    assert math.isfinite(v["value"])


@pytest.mark.parametrize("rho", RHOS)
def test_volume_form_distortion_decays_like_e_minus_four_rho(rho):
    ratio = volume_form_distortion(rho)
    assert 0.0 < ratio
    if rho >= 2.0:
        assert ratio == pytest.approx(8.0 * math.sqrt(2.0) * math.exp(-4.0 * rho),
                                      rel=1e-2)


# --------------------------------------------------------------- probe values

@pytest.mark.parametrize("rho", [0.0] + RHOS)
def test_p_bell_closed_form(rho):
    _, p = attempted_use_state(to_sl2(swirl_point(rho, 0.3, 0.8)))
    assert p == pytest.approx(p_bell(rho), abs=1e-12)


def test_success_probability_saturates_at_one_half():
    assert p_bell(0.0) == pytest.approx(1.0)
    assert p_bell(6.0) == pytest.approx(0.5, abs=1e-5)


@pytest.mark.parametrize("rho", [0.0] + RHOS)
def test_conditional_concurrence_is_sech_two_rho(rho):
    W, p = attempted_use_state(to_sl2(swirl_point(rho, 0.3, 0.8)))
    lam, V = np.linalg.eigh(W[:4, :4])
    v = V[:, int(np.argmax(lam))]
    s = np.linalg.svd(v.reshape(2, 2), compute_uv=False)
    assert 2.0 * s[0] * s[1] == pytest.approx(conditional_concurrence(rho), abs=1e-9)


# ------------------------------------------------------- distinguishability

def _psd_sqrt(X):
    w, V = np.linalg.eigh((X + X.T) / 2.0)
    w = np.where(w < 16.0 * float(np.finfo(float).eps), 0.0, w)
    return V @ np.diag(np.sqrt(w)) @ V.T


def test_trace_distance_and_fidelity_match_dense_linear_algebra():
    rng = np.random.default_rng(5)
    for _ in range(40):
        MA = to_sl2(swirl_point(rng.uniform(0.05, 2.5), rng.uniform(-3, 3),
                                rng.uniform(-3, 3)))
        MB = to_sl2(swirl_point(rng.uniform(0.05, 2.5), rng.uniform(-3, 3),
                                rng.uniform(-3, 3)))
        WA, WB = attempted_use_state(MA)[0], attempted_use_state(MB)[0]
        dense_d = 0.5 * float(np.sum(np.abs(np.linalg.eigvalsh(WA - WB))))
        dense_f = float(np.sum(np.linalg.svd(_psd_sqrt(WA) @ _psd_sqrt(WB),
                                             compute_uv=False)))
        assert dense_d == pytest.approx(trace_distance_closed_form(MA, MB), abs=1e-10)
        assert dense_f == pytest.approx(root_fidelity_closed_form(MA, MB), abs=1e-10)
        # Fuchs-van de Graaf: 1 - F <= D <= sqrt(1 - F^2)
        assert 1.0 - dense_f <= dense_d + 1e-9
        assert dense_d <= math.sqrt(max(0.0, 1.0 - dense_f ** 2)) + 1e-9


# ------------------------------------------------------------- weave cocycle

def _rand_sl2(rng):
    M = rng.normal(size=(2, 2))
    return M / math.sqrt(abs(float(np.linalg.det(M))))


def test_kappa_is_nonnegative_and_composition_holds():
    rng = np.random.default_rng(9)
    for _ in range(60):
        X, Y = _rand_sl2(rng), _rand_sl2(rng)
        k = kappa(X, Y)
        assert k >= -1e-12                      # submultiplicativity
        AX = X / np.linalg.norm(X, 2)
        AY = Y / np.linalg.norm(Y, 2)
        AXY = (X @ Y) / np.linalg.norm(X @ Y, 2)
        assert np.max(np.abs(AX @ AY - math.exp(-k) * AXY)) < 1e-12


def test_kappa_satisfies_the_exact_cocycle_law():
    rng = np.random.default_rng(13)
    for _ in range(60):
        X, Y, Z = _rand_sl2(rng), _rand_sl2(rng), _rand_sl2(rng)
        assert (kappa(X, Y) + kappa(X @ Y, Z)
                == pytest.approx(kappa(Y, Z) + kappa(X, Y @ Z), abs=1e-12))


@pytest.mark.parametrize("rho", RHOS)
def test_source_reversibility_is_not_operational_reversibility(rho):
    """M^-1 M = I exactly, and streaming it still costs e^{-4 rho}.

    R6's P4 said echoing is free only if the net element may be compiled directly.
    Here that is an identity rather than a measurement: kappa(M^-1, M) = 2 rho.
    """
    M = to_sl2(swirl_point(rho, 0.0, 0.0))
    k = kappa(np.linalg.inv(M), M)
    assert k == pytest.approx(2.0 * rho, abs=1e-10)
    assert math.exp(-2.0 * k) == pytest.approx(math.exp(-4.0 * rho), abs=1e-12)
    assert np.max(np.abs(np.linalg.inv(M) @ M - np.eye(2))) < 1e-12


# ------------------------------------------------------- the terminology guard

@pytest.mark.parametrize("rho", RHOS)
def test_the_source_is_lorentzian_not_hyperbolic_three_space(rho):
    """The correction that renames what this programme has been measuring.

    g = diag(-1, cosh^2 rho, -sinh^2 rho): signature (1,2). Hyperbolic 3-space
    would be (3,0). The measure was right and the word was not.
    """
    sig = induced_metric_signature(rho)
    assert (sig["n_positive"], sig["n_negative"], sig["n_zero"]) == (1, 2, 0)
    assert not sig["is_riemannian"]
    assert sig["sqrt_abs_det"] == pytest.approx(math.cosh(rho) * math.sinh(rho))


def test_source_measure_grows_while_operational_volume_does_not():
    """The whole round, as one assertion."""
    src = [induced_metric_signature(r)["sqrt_abs_det"] for r in (1.0, 2.0, 3.0, 4.0)]
    assert src == sorted(src) and src[-1] / src[0] > 100.0
    assert math.isfinite(operational_qfi_volume()["value"])
