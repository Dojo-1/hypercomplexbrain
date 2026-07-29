"""The capacity ceiling (QSigma-R6f), and the control that gives it meaning."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.capacity_ceiling import (grid_codebook, holevo_ceiling,
                                    packing_log_slope, packing_number,
                                    su2_codebook, su2_codeword, su2_matrix)
from aionq.holevo_sandwich import flag_success_decomposition, holevo_chi


# ------------------------------------------------------ the ceiling has no N

@pytest.mark.parametrize("n", [8, 16, 32, 64, 100])
def test_chi_does_not_grow_with_codebook_size(n):
    """log2 N climbs from 3 to 6.644; chi does not move at all."""
    assert holevo_chi(grid_codebook(8.0, n)) == pytest.approx(1.0, abs=1e-9)


def test_geometric_separation_and_transmissibility_come_apart():
    """The headline, as one assertion.

    A hundred eps-separated codewords transmit exactly what eight do. The packing
    number measures separability; it says nothing about how many bits get through.
    """
    small, large = holevo_chi(grid_codebook(8.0, 8)), holevo_chi(grid_codebook(8.0, 100))
    assert large == pytest.approx(small, abs=1e-9)
    assert math.log2(100) - math.log2(8) > 3.6


@pytest.mark.parametrize("rho", [0.1, 0.5, 1.0, 2.0, 4.0, 8.0])
def test_ceiling_equals_twice_the_survival_probability(rho):
    """chi <= 2 pbar = 1 + e^{-4 rho}, from the flag decomposition plus dim C^4."""
    book = grid_codebook(rho, 64)
    d = flag_success_decomposition(book)
    assert holevo_ceiling(rho) == pytest.approx(2 * d["p_bar"], abs=1e-12)
    assert holevo_chi(book) <= holevo_ceiling(rho) + 1e-9


def test_ceiling_tends_to_one_bit():
    assert holevo_ceiling(0.0) == pytest.approx(2.0)
    assert holevo_ceiling(8.0) == pytest.approx(1.0, abs=1e-12)


# --------------------------------------------------- the matched compact control

def test_su2_matrix_is_actually_unitary_and_three_parameter():
    """The control was mis-specified once, with real rotations.

    A real 2x2 rotation is a ONE-parameter family, reaching only a circle inside
    the maximally entangled states. It gave a spurious ceiling of 1 bit that
    accidentally matched the non-compact side and erased the contrast the control
    exists to provide. Three Euler angles, and genuinely complex.
    """
    rng = np.random.default_rng(3)
    seen_imag = False
    for _ in range(20):
        U = su2_matrix(*rng.uniform(0, 2 * math.pi, 3))
        assert np.max(np.abs(U @ U.conj().T - np.eye(2))) < 1e-12
        assert abs(abs(np.linalg.det(U)) - 1.0) < 1e-12
        seen_imag |= np.max(np.abs(U.imag)) > 1e-6
    assert seen_imag, "a real-only family is not SU(2)"


def test_compact_codewords_are_pure_with_no_erasure_branch():
    U = su2_matrix(0.4, 1.1, 2.3)
    W = su2_codeword(U)
    assert W[4, 4] == pytest.approx(0.0, abs=1e-12)      # no erasure weight
    assert np.trace(W).real == pytest.approx(1.0, abs=1e-12)
    w = np.linalg.eigvalsh(W)
    assert np.sum(w > 1e-9) == 1                          # pure


def test_compact_baseline_beats_the_non_compact_ceiling():
    """1 bit is only interesting against something that is not 1 bit."""
    compact = holevo_chi(su2_codebook(256))
    non_compact = holevo_chi(grid_codebook(8.0, 256))
    assert compact > 1.9
    assert compact <= 2.0 + 1e-9
    assert non_compact == pytest.approx(1.0, abs=1e-9)
    assert compact / non_compact > 1.9


# ----------------------------------------------------------------- packing

def test_packing_is_greedy_and_therefore_a_lower_bound():
    """Monotone in samples: more draws can only find more separated points."""
    a = packing_number(4.0, 0.2, samples=200, seed=1)
    b = packing_number(4.0, 0.2, samples=800, seed=1)
    assert b >= a


def test_packing_shrinks_with_epsilon():
    assert (packing_number(4.0, 0.05, samples=400)
            >= packing_number(4.0, 0.20, samples=400))


@pytest.mark.parametrize("eps", [0.05, 0.10, 0.20])
def test_packing_slope_is_not_the_source_exponent(eps):
    """The source measure grows as e^{2 rho}; the packing count does not.

    The claim is that the log-slope is nowhere near 2, not that it is exactly 0 --
    an independent external run reported 0 at these epsilons and this reproduces
    the slope, with different counts because the sampling differs.
    """
    r = packing_log_slope(eps, samples=600, seed=7)
    assert r["source_exponent"] == 2.0
    assert abs(r["log2_slope"]) < 0.5
    assert r["log2_slope"] < 1.0


# --------------------------------------------- is the ceiling probe-dependent?

def test_bell_probe_is_the_optimum_not_a_convenience():
    """1 bit is the best this probe family achieves, not an artifact.

    chi is maximised at lam = 1/2 and falls monotonically as the probe is
    de-entangled. If a less entangled probe had beaten it, the R6f conclusion
    would have been an artifact of a convenient choice; it is not.
    """
    from aionq.capacity_ceiling import probe_sweep
    s = probe_sweep()
    assert s["best_lam"] == pytest.approx(0.5)
    assert s["best_chi"] == pytest.approx(1.0, abs=1e-9)
    assert s["chi_is_monotone_in_entanglement"]


def test_ceiling_holds_at_every_probe():
    from aionq.capacity_ceiling import probe_sweep
    for r in probe_sweep()["rows"]:
        assert r["chi"] <= holevo_ceiling(8.0) + 1e-9
        assert r["p_bar"] == pytest.approx(0.5, abs=1e-9)


def test_flag_informativeness_needs_equal_p_not_equal_depth():
    """Narrows an R6d statement that was true only for the Bell probe.

    R6d found a fixed-depth codebook has an uninformative flag and attributed it
    to the shared depth. The real condition is equal p_i. Equal depth gives that
    ONLY when the probe is maximally entangled, because p = tr(A^T A)/2 is then
    orientation-independent. Off Bell, same depth, the flag reports ORIENTATION.
    """
    from aionq.capacity_ceiling import probe_sweep
    rows = {r["lam"]: r for r in probe_sweep()["rows"]}
    assert abs(rows[0.5]["flag_bits"]) < 1e-9
    assert rows[0.5]["per_codeword_p_spread"] < 1e-12
    assert rows[0.1]["flag_bits"] > 1e-3
    assert rows[0.1]["per_codeword_p_spread"] > 0.5


def test_normalisation_choice_does_not_move_the_ceiling():
    """Spectral against Frobenius: another place the result could have been an
    artifact, and is not."""
    from aionq.capacity_ceiling import normalisation_control
    n = normalisation_control()
    assert n["identical"]
    assert n["spectral"]["chi"] == pytest.approx(1.0, abs=1e-9)
    assert n["frobenius"]["chi"] == pytest.approx(1.0, abs=1e-9)


# ------------------------------------ can width or parallelism beat the ceiling?

def test_more_ancilla_buys_nothing_because_rank_A_is_two():
    """Width does not move the ceiling, and the reason is falsifiable.

    A is 2x2 of rank 2, so it cannot act on more than two Schmidt coefficients
    however large the ancilla. If chi rose with d, the rank argument would be
    wrong -- so this is a test of the argument, not a restatement of it.
    """
    from aionq.capacity_ceiling import width_sweep
    w = width_sweep()
    assert w["width_is_useless"]
    assert w["spread"] < 1e-9
    assert w["rows"][-1]["state_dim"] > 3 * w["rows"][0]["state_dim"]
    for r in w["rows"]:
        assert r["chi"] == pytest.approx(1.0, abs=1e-9)


def test_parallel_use_is_exactly_additive():
    """Holevo information is NOT additive in general, so this had to be measured.

    chi/k is constant to machine precision at k = 1, 2, 3: parallel use buys
    exactly k times one use and not a bit more. No super-additivity, no rescue.
    """
    from aionq.capacity_ceiling import parallel_sweep
    p = parallel_sweep()
    assert p["exactly_additive"]
    assert p["per_use_spread"] < 1e-9
    per = [r["chi_per_use"] for r in p["rows"]]
    assert per[0] == pytest.approx(per[-1], abs=1e-9)
    assert p["rows"][-1]["k"] == 3
