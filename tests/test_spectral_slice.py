"""Two axes, and the one R1G generalised to without measuring.

R1G recorded the QFFO many-body excitation as supplying "the parameterised
transverse departure the portfolio lacks". It supplies an ALGEBRAIC departure --
the operator stops being quadratic in the Majoranas, `gaussian_defect` 3e-15 to
1.02 -- and no DYNAMICAL one: the level-spacing ratio moves by 4e-4, because
`f(H)` shares the eigenbasis of `H` and therefore its conserved quantities.

A quartic term moves the same statistic from 0.309 to 0.596, landing where the
Riemann zeta zeros are measured to be. These tests pin both axes and keep them
apart.
"""

from __future__ import annotations

import numpy as np
import pytest

from aionq.majorana import gaussian_defect, majorana_operators, parity_operator
from aionq.qffo import MultiplierReading
from aionq.spectral_slice import (GUE, POISSON, free_fermion_spectrum,
                                  parity_sector, quartic_perturbation,
                                  ratio_statistic, spectral_axis_report,
                                  zeta_zeros)

QUBITS = 10


@pytest.fixture(scope="module")
def report():
    return spectral_axis_report(QUBITS)


# --------------------------------------------------------------------------
# The instrument, and the references that make its output mean something
# --------------------------------------------------------------------------

def test_the_statistic_reproduces_its_analytic_references():
    """Poisson 0.386 and GUE 0.600, from uncorrelated levels and a random matrix.

    Without both ends calibrated, a measured 0.31 or 0.60 is a number rather than
    a placement on an axis.
    """
    rng = np.random.default_rng(0)
    assert ratio_statistic(rng.uniform(size=4000)) == pytest.approx(POISSON, abs=0.02)

    matrix = (rng.normal(size=(800, 800)) + 1j * rng.normal(size=(800, 800)))
    matrix = (matrix + matrix.conj().T) / 2
    assert ratio_statistic(np.linalg.eigvalsh(matrix)) == pytest.approx(GUE, abs=0.02)


def test_the_statistic_is_invariant_under_affine_rescaling():
    """Which is what lets a many-body spectrum and 400 zeta ordinates be compared.

    It is also exactly why the statistic is blind to the QFFO, whose action on a
    long spectrum is asymptotically a constant. The property that makes the
    comparison possible is the property that makes the null result inevitable,
    and both are worth stating.

    Exact in exact arithmetic; only conditionally exact in floating point, and
    the condition is stated here rather than tuned away. Gaps are obtained by
    differencing, so a spectrum sitting at height `T` with gaps of size `d`
    loses about `eps * T / d` of relative precision. The last case below is
    deliberately the bad one -- gaps of 1e-4 at height 900, ratio 1e7 -- and it
    agrees to 1e-7 rather than to 1e-9. That matters for the intended use: zeta
    ordinates near height 1e6 have gaps of order 1, so the same loss is about
    1e-10 there and harmless, but it would not stay harmless much higher.
    """
    rng = np.random.default_rng(1)
    levels = np.sort(rng.normal(size=600))
    base = ratio_statistic(levels)

    for scale, shift in ((3.7, 0.0), (1.0, -12.5)):
        assert ratio_statistic(scale * levels + shift) == pytest.approx(base, rel=1e-12)

    ill_conditioned = ratio_statistic(1e-4 * levels + 900.0)
    assert ill_conditioned == pytest.approx(base, rel=1e-6)
    assert ill_conditioned != base, (
        "the ill-conditioned case was expected to differ in the last digits; "
        "if it is now exact the differencing has changed and the caveat above "
        "needs re-deriving")


def test_the_cached_zeta_zeros_are_the_real_ones():
    """The artifact is pinned against a live recomputation, not trusted.

    500 zeros take 87 seconds via `mpmath.zetazero`, which does not belong in a
    suite; six do not. If mpmath is absent the cache still loads and the rest of
    this file still runs, so the dependency is a check and not a requirement.
    """
    cached = zeta_zeros(6)
    assert cached[0] == pytest.approx(14.134725141734693, abs=1e-9)

    mpmath = pytest.importorskip("mpmath")
    for index in range(1, 7):
        assert cached[index - 1] == pytest.approx(
            float(mpmath.zetazero(index).imag), abs=1e-9)


def test_the_zeta_zeros_sit_at_the_wigner_dyson_end(report):
    """Montgomery-Odlyzko, measured here rather than cited.

    The pair correlation of the zeta zeros matching random-matrix statistics is a
    known correspondence. It is measured because this repository's discipline is
    that a number used in a comparison is computed, and because it anchors the
    far end of the axis everything else is placed on.
    """
    assert report["zeta_zeros"] == pytest.approx(0.6166, abs=0.02)
    assert report["zeta_zeros"] > GUE - 0.02
    assert report["zeta_zeros"] - report["free_fermion"] > 0.25


# --------------------------------------------------------------------------
# The correction: one axis moved, the other did not
# --------------------------------------------------------------------------

def test_the_free_fermion_spectrum_is_at_the_integrable_end(report):
    assert report["free_fermion"] < POISSON
    assert report["free_fermion"] == pytest.approx(0.309, abs=0.03)


def test_the_qffo_excitation_moves_the_algebraic_axis(report):
    """R1G's measurement, reproduced. It is correct as far as it goes."""
    operators = majorana_operators(3)
    from aionq.fishnet import excitation_report

    fishnet = excitation_report(qubits=3, kind="caputo", q=0.5)
    assert fishnet["many_body"]["defect"] > 0.5
    assert fishnet["single_particle"]["defect"] < 1e-9


def test_the_qffo_excitation_does_not_move_the_dynamical_axis(report):
    """The correction. `f(H)` shares the eigenbasis of `H`, so it cannot.

    Measured shift 4e-4 against the quartic term's 0.29 on the same spectrum.
    R1G reported the algebraic departure and generalised it to a departure from
    tractability; those are different axes and only one of them moved.
    """
    assert report["_qffo_shift"] < 0.01
    assert report["_quartic_shift"] > 0.2
    assert report["_quartic_shift"] / max(report["_qffo_shift"], 1e-12) > 20


def test_the_multiplier_saturates_which_is_the_mechanism():
    """Identical to eight decimals at n = 100 and n = 2048.

    So on a 512-level spectrum the QFFO is a constant times a transient in the
    first twenty levels, and a constant cannot move a scale-invariant statistic.
    This is why the null result above is structural rather than a matter of the
    parameters chosen.
    """
    reading = MultiplierReading("caputo", 0.4, 0.3, 0.5)
    assert reading.weight(100) == pytest.approx(reading.weight(2048), abs=1e-8)
    assert abs(reading.weight(2) - reading.weight(2048)) > 0.05, (
        "the transient at small n is real; only the tail is flat")


@pytest.mark.parametrize("coupling", [0.05, 0.2, 1.0])
def test_a_quartic_term_carries_the_spectrum_to_wigner_dyson(coupling, report):
    """Quartic, not quadratic, is the distinction that matters dynamically.

    Quadratic terms generate the free-fermion group. Quartic ones do not, and
    they take the statistic from 0.309 to 0.596 -- to the GUE end, where the
    zeta zeros are.
    """
    value = report[f"quartic_g{coupling}"]
    # The weakest coupling, g = 0.05, reaches 0.49 rather than 0.60: the
    # transition is gradual and the smallest kick does not complete it. Asserting
    # 0.15 there and the full GUE value at g = 1.0 records that, rather than
    # choosing one threshold that hides which couplings actually arrive.
    assert value > report["free_fermion"] + (0.15 if coupling == 0.05 else 0.25)
    if coupling == 1.0:
        assert value == pytest.approx(GUE, abs=0.03)
    assert value > report["qffo_excited"] + 0.15


# --------------------------------------------------------------------------
# The step that makes the whole measurement valid
# --------------------------------------------------------------------------

def test_ignoring_the_parity_sector_manufactures_integrability():
    """Statistics across an unresolved symmetry look Poissonian for any dynamics.

    The two parity sectors of a Majorana Hamiltonian are independent sequences,
    and independent sequences interleave without repelling. Measured here: a
    strongly chaotic Hamiltonian reads near-GUE inside one sector and collapses
    toward Poisson across both. This is the standard way to measure integrability
    that is not there, and it is why `parity_sector` is not optional.
    """
    hamiltonian, _ = free_fermion_spectrum(QUBITS)
    chaotic = hamiltonian + 1.0 * quartic_perturbation(QUBITS)

    inside = ratio_statistic(np.linalg.eigvalsh(parity_sector(chaotic, QUBITS)))
    across = ratio_statistic(np.linalg.eigvalsh(chaotic))

    assert inside > GUE - 0.03
    assert across < inside - 0.05

    parity = parity_operator(QUBITS)
    assert np.allclose(parity @ chaotic @ parity, chaotic, atol=1e-9), (
        "the perturbation must preserve parity, or the sector split is not a "
        "symmetry of it and this test is measuring something else")
