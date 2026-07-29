"""Information-theoretic gates for the compactified channel (QSigma-R6d)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.holevo_sandwich import (apply_channel, binary_entropy,
                                   flag_success_decomposition, holevo_chi,
                                   information_sandwich, pgm_analysis,
                                   pgm_mutual_information, pgm_povm,
                                   random_cptp, von_neumann_entropy)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state


def _omega(rho, phi, psi):
    return attempted_use_state(to_sl2(swirl_point(rho, phi, psi)))[0].astype(complex)


def _book(rho, n=6, seed=7):
    rng = np.random.default_rng(seed)
    return [_omega(rho, rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi))
            for _ in range(n)]


def _grid_book(rho, n=8):
    return [_omega(rho, 2 * math.pi * k / n, 2 * math.pi * (k * 3 % n) / n)
            for k in range(n)]


# ---------------------------------------------------------------- entropy basics

def test_pure_state_has_zero_entropy():
    """The reason zero eigenvalues are dropped rather than clipped."""
    psi = np.zeros((5, 5), dtype=complex)
    psi[0, 0] = 1.0
    assert von_neumann_entropy(psi) == pytest.approx(0.0, abs=1e-14)


def test_maximally_mixed_entropy_is_log2_dim():
    for d in (2, 4, 5):
        assert von_neumann_entropy(np.eye(d) / d) == pytest.approx(math.log2(d), abs=1e-12)


def test_binary_entropy_endpoints_and_peak():
    assert binary_entropy(0.0) == 0.0
    assert binary_entropy(1.0) == 0.0
    assert binary_entropy(0.5) == pytest.approx(1.0)


# ------------------------------------------------------------------ the sandwich

@pytest.mark.parametrize("rho", [0.1, 0.5, 1.0, 2.0, 5.0])
def test_sandwich_ordering(rho):
    s = information_sandwich(_book(rho))
    assert s["I_PGM"] <= s["chi"] + 1e-9
    assert s["chi"] <= s["log2_N"] + 1e-9
    assert s["ordering_holds"]


def test_pgm_povm_is_complete():
    book = _book(0.7)
    total = sum(pgm_povm(book))
    mean = sum(book) / len(book)
    support = np.linalg.matrix_rank(mean, tol=1e-10)
    # PGM resolves the identity only on the support of rhobar.
    w = np.linalg.eigvalsh(total)
    assert int(np.sum(w > 0.5)) == support


def test_identical_codewords_carry_no_information():
    """chi = 0 when there is nothing to distinguish -- the degenerate control."""
    s = _omega(0.9, 0.3, 1.2)
    assert holevo_chi([s, s, s]) == pytest.approx(0.0, abs=1e-12)
    assert pgm_mutual_information([s, s, s]) == pytest.approx(0.0, abs=1e-9)


def test_pgm_analysis_keeps_raw_guards_before_row_repair():
    states = [
        np.diag([1.0, 0.0, 0.0, 0.0]).astype(complex),
        np.diag([0.0, 1.0, 0.0, 0.0]).astype(complex),
        np.diag([0.0, 0.0, 1.0, 0.0]).astype(complex),
    ]
    priors = np.array([0.5, 0.3, 0.2])
    analysis = pgm_analysis(states, priors)
    entropy = -float(np.sum(priors * np.log2(priors)))
    assert analysis["I_PGM"] == pytest.approx(entropy, abs=1e-12)
    assert analysis["mean_state_rank"] == 3
    assert analysis["support_projector_defect"] <= 1e-12
    assert analysis["minimum_raw_probability"] >= -1e-12
    assert analysis["maximum_row_sum_defect"] <= 1e-12
    assert analysis["maximum_imaginary_probability"] <= 1e-12
    assert analysis["numerical_guards_hold"]


# ----------------------------------------------------- the flag decomposition

@pytest.mark.parametrize("rho", [0.1, 0.5, 1.0, 3.0])
def test_flag_decomposition_is_exact(rho):
    d = flag_success_decomposition(_book(rho))
    assert d["residual"] < 1e-12
    assert d["reconstructed_chi"] == pytest.approx(d["direct_chi"], abs=1e-12)


@pytest.mark.parametrize("rho", [0.1, 0.5, 1.0, 3.0])
def test_fixed_depth_flag_carries_nothing(rho):
    """The Jensen gap vanishes when every codeword sits at one depth."""
    d = flag_success_decomposition(_book(rho))
    assert abs(d["flag_bits"]) < 1e-12
    assert not d["flag_is_informative"]
    assert d["success_branch_bits"] == pytest.approx(d["direct_chi"], abs=1e-12)


def test_mixed_depth_flag_does_carry_something():
    """The other direction, or the previous test is vacuous."""
    rng = np.random.default_rng(3)
    mixed = [_omega(r, rng.uniform(-3, 3), rng.uniform(-3, 3))
             for r in (0.05, 0.4, 1.0, 2.5)]
    d = flag_success_decomposition(mixed)
    assert d["flag_bits"] > 1e-3
    assert d["flag_is_informative"]
    assert d["residual"] < 1e-12


def test_flag_bits_are_a_nonnegative_jensen_gap():
    """h2 is concave, so h2(pbar) >= <h2(p_i)> always."""
    rng = np.random.default_rng(21)
    for _ in range(20):
        depths = rng.uniform(0.05, 3.0, size=4)
        book = [_omega(r, rng.uniform(-3, 3), rng.uniform(-3, 3)) for r in depths]
        assert flag_success_decomposition(book)["flag_bits"] >= -1e-12


# ------------------------------------------------------------- data processing

def test_random_cptp_is_trace_preserving_and_complete():
    rng = np.random.default_rng(4)
    for _ in range(10):
        K = random_cptp(5, 3, rng)
        assert np.max(np.abs(sum(k.conj().T @ k for k in K) - np.eye(5))) < 1e-12
        rho = _omega(0.6, 0.2, 0.4)
        assert np.trace(apply_channel(rho, K)).real == pytest.approx(1.0, abs=1e-12)


def test_channel_cannot_increase_holevo_information():
    rng = np.random.default_rng(11)
    book = _book(0.8)
    chi0 = holevo_chi(book)
    for _ in range(10):
        K = random_cptp(5, 3, rng)
        assert holevo_chi([apply_channel(s, K) for s in book]) <= chi0 + 1e-9


def test_no_measurement_after_the_channel_beats_chi_before_it():
    """The correct data-processing statement for the PGM.

    ``I_PGM(Phi(ensemble)) <= I_PGM(ensemble)`` is NOT implied and is not tested:
    the PGM is chosen for whichever ensemble it is handed, so a better measurement
    on a worse ensemble can beat a worse measurement on a better one. What is
    implied is that nothing after the channel exceeds chi before it.
    """
    rng = np.random.default_rng(12)
    book = _book(0.8)
    chi0 = holevo_chi(book)
    for _ in range(10):
        K = random_cptp(5, 3, rng)
        assert pgm_mutual_information([apply_channel(s, K) for s in book]) <= chi0 + 1e-9


# ------------------------------------------------------------ the q -> 0 boundary

def test_boundary_survival_probability_is_one_half():
    assert flag_success_decomposition(_grid_book(16.0))["p_bar"] == pytest.approx(
        0.5, abs=1e-9)


def test_boundary_chi_is_at_most_one_bit():
    """chi -> (1/2) S(sigmahat) <= (1/2)(2) = 1 bit.

    At infinite depth ``A`` is rank one, so ``|v>`` is a PRODUCT state of norm^2
    1/2. Half the weight goes to the erasure flag, and the success branch lives on
    C^4, so its entropy is at most 2 bits.
    """
    for n in (4, 8, 16):
        assert holevo_chi(_grid_book(16.0, n)) <= 1.0 + 1e-9


def test_grid_codebook_saturates_the_one_bit_bound():
    """Evenly spaced product states average to the maximally mixed state."""
    assert holevo_chi(_grid_book(16.0, 8)) == pytest.approx(1.0, abs=1e-9)


def test_boundary_limit_converges():
    vals = [holevo_chi(_grid_book(r, 8)) for r in (8.0, 12.0, 16.0, 20.0)]
    assert max(vals) - min(vals) < 1e-9


def test_chi_is_not_monotone_in_depth():
    """A falsified claim, asserted as falsified.

    The first random codebook showed chi rising with depth and it looked like a
    finding. The deterministic grid codebook dips from 0.9017 at rho=0.1 to 0.8985
    at rho=0.25 before rising. The claim is withdrawn, and this test pins the
    counterexample so a future change cannot quietly restore it.
    """
    lo = holevo_chi(_grid_book(0.1, 8))
    hi = holevo_chi(_grid_book(0.25, 8))
    assert hi < lo, "the counterexample to depth-monotonicity has disappeared"


def test_what_survives_is_convergence_not_monotonicity():
    vals = [holevo_chi(_grid_book(r, 8)) for r in (0.1, 0.25, 0.5, 1.0, 2.0, 8.0)]
    assert vals != sorted(vals)                     # not monotone
    assert vals[-1] == pytest.approx(1.0, abs=1e-9)  # but convergent
