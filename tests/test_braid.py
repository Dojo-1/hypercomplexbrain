"""Topology that is entirely real and entirely invisible to hardness.

Exchanging two Majorana modes is `exp(theta c_k c_{k+1})` -- quadratic, hence
free-fermion. So the braid group representation these generate satisfies its
relations exactly, is genuinely nonabelian, and does nothing whatever on the
axis this repository measures hardness on.

The same holds for driving: a Floquet operator built from quadratic Hamiltonians
is a product of Gaussian unitaries, hence Gaussian, at any period and for any
number of periods. Braiding, deforming and moving all stay inside; only an
interaction leaves.

The last group of tests is about the instrument rather than the physics: the
obvious way to ask whether a driven system is chaotic reads quasi-energies,
quasi-energies are angles, and angles wrap.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.braid import (braid_generator, braid_relation_defect, braid_report,
                         braid_word, far_commutator_defect, floquet_operator)
from aionq.majorana import gaussian_defect, majorana_operators
from aionq.spectral_slice import (free_fermion_spectrum, quartic_perturbation,
                                  quasi_energy_statistic, ratio_statistic,
                                  parity_sector, wrap_count)

QUBITS = 4


@pytest.fixture(scope="module")
def report():
    return braid_report(QUBITS)


# --------------------------------------------------------------------------
# The topology is real
# --------------------------------------------------------------------------

@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5])
def test_the_braid_relation_holds_on_the_nose_not_projectively(index):
    """`s_k s_{k+1} s_k = s_{k+1} s_k s_{k+1}` to 6.3e-16, phase +1.000000.

    Both the exact and the up-to-phase difference are checked, because a
    representation satisfying its relations only up to a phase is *projective*
    and the phase is a 2-cocycle rather than a rounding error. There is no
    cocycle here: the representation is genuine.
    """
    operators = majorana_operators(QUBITS)
    defect = braid_relation_defect(index, operators)

    assert defect["exact"] < 1e-13
    assert defect["phase"] == pytest.approx(1.0 + 0j, abs=1e-12)
    assert defect["up_to_phase"] < 1e-13


@pytest.mark.parametrize("pair", [(0, 2), (0, 3), (1, 4), (2, 5)])
def test_far_generators_commute_exactly(pair):
    """The braid group's other relation, for `|j - k| >= 2`."""
    operators = majorana_operators(QUBITS)
    assert far_commutator_defect(pair[0], pair[1], operators) < 1e-13


def test_the_representation_is_genuinely_nonabelian():
    """Otherwise "the braid relations hold" would be a statement about scalars.

    Adjacent generators must NOT commute, or the whole structure is abelian and
    satisfying the braid relation is vacuous.
    """
    operators = majorana_operators(QUBITS)
    first, second = (braid_generator(0, operators), braid_generator(1, operators))
    assert np.linalg.norm(first @ second - second @ first) > 0.5


# --------------------------------------------------------------------------
# ...and entirely invisible to hardness
# --------------------------------------------------------------------------

def test_every_braid_generator_is_a_free_fermion_operation(report):
    """`exp(theta c_j c_k)` is quadratic in the Majoranas, so it cannot leave."""
    assert all(value < 1e-12 for value in report["generators"].values())


def test_a_long_random_braid_word_is_still_free(report):
    """60 letters, generators and inverses mixed. Defect 5.8e-15.

    Composition cannot escape a group, and this is the measured form of the
    statement that Majorana braiding alone is not universal for quantum
    computation.
    """
    assert report["word"] < 1e-12


def test_the_whole_theta_family_is_free(report):
    """Not just the braid point: partial exchanges are equally free.

    If only `theta = pi/4` were free, the freedom would be an accident of that
    angle. It is a property of the generator being quadratic, which every
    `theta` shares.
    """
    assert set(report["theta_family"]) >= {0.1, math.pi / 4, 2.5}
    assert all(value < 1e-12 for value in report["theta_family"].values())


def test_a_moving_fishnet_cannot_leave_the_class_either(report):
    """A Floquet operator of quadratic Hamiltonians is a product of Gaussians.

    Checked after one period and after seven, because "stays free for a while"
    and "stays free" are different claims and only the second is true here.
    """
    assert report["floquet"] < 1e-10
    assert report["floquet_seven_periods"] < 1e-10


def test_only_the_interaction_leaves():
    """The contrast that makes the null results above informative.

    Braid, theta-deform and drive all sit at machine zero. A quartic term sits
    at 64. Without this the tests above would be consistent with an instrument
    that cannot detect anything.
    """
    operators = majorana_operators(8)
    hamiltonian, _ = free_fermion_spectrum(8)
    from scipy.linalg import expm

    chaotic = hamiltonian + 1.0 * quartic_perturbation(8, seed=1)
    assert gaussian_defect(expm(1j * chaotic * 0.7), operators) > 1.0


# --------------------------------------------------------------------------
# The instrument: quasi-energies are angles, and angles wrap
# --------------------------------------------------------------------------

def test_the_quasi_energy_statistic_refuses_past_one_wrap():
    """The guard, and the reason it exists.

    A first attempt at this measurement reported 0.43 for a driven free-fermion
    fishnet and was one step from recording it as partial chaos. Folding the
    *static integrable* spectrum by hand gives 0.4385 on its own, so the whole
    effect was the folding.
    """
    hamiltonian, _ = free_fermion_spectrum(8)

    assert wrap_count(hamiltonian, 0.1) < 1.0
    assert quasi_energy_statistic(hamiltonian, 0.1, 8) < 0.45

    assert wrap_count(hamiltonian, 0.7) > 1.0
    with pytest.raises(ValueError, match="folds the spectrum"):
        quasi_energy_statistic(hamiltonian, 0.7, 8)


def test_folding_alone_scrambles_the_statistic_by_as_much_as_the_signal():
    """The control that caught it -- and then corrected the first version of it.

    No dynamics are involved here at all: the same static integrable spectrum is
    folded mod 2pi at several periods. The first reading of this control used two
    data points and concluded that folding pushes the statistic toward Poisson.
    Across eight seeds and three periods it does no such thing: mean shift
    -0.016, std 0.082, sixteen down and eight up, worst magnitude 0.161 against
    an integrable-to-chaotic signal of 0.212.

    So folding is a SCRAMBLE, not a bias, and the artefact is 76% of the signal
    it would be confused with. That is a worse defect than a bias would be,
    because a bias could be subtracted.
    """
    shifts = []
    for seed in range(8):
        _, spectrum = free_fermion_spectrum(8, seed=seed)
        unfolded = ratio_statistic(spectrum)
        shifts += [ratio_statistic(np.angle(np.exp(1j * period * spectrum))) - unfolded
                   for period in (1.0, 3.0, 10.0)]
    shifts = np.array(shifts)

    assert (shifts > 0).any() and (shifts < 0).any(), (
        "a one-signed shift would be a bias, which could be corrected for")
    assert shifts.std() > 0.05

    hamiltonian, spectrum = free_fermion_spectrum(8, seed=0)
    chaotic = hamiltonian + 1.0 * quartic_perturbation(8, seed=0)
    signal = (ratio_statistic(np.linalg.eigvalsh(parity_sector(chaotic, 8)))
              - ratio_statistic(spectrum))
    assert np.abs(shifts).max() > 0.5 * abs(signal)


def test_past_the_threshold_the_statistic_inverts_its_sign():
    """Not merely degraded -- backwards.

    At 5.8 wraps the integrable system reads MORE chaotic than the chaotic one,
    measured separation -0.05 against +0.24 below one wrap. An instrument that
    inverts is worse than one that saturates, because its output still looks
    like a reading.
    """
    from scipy.linalg import expm

    integrable, _ = free_fermion_spectrum(8)
    chaotic = integrable + 1.0 * quartic_perturbation(8, seed=1)

    def statistic(hamiltonian, period):
        sector = parity_sector(hamiltonian, 8)
        return ratio_statistic(np.angle(np.linalg.eigvals(expm(1j * sector * period))))

    below = statistic(chaotic, 0.05) - statistic(integrable, 0.05)
    above = statistic(chaotic, 0.7) - statistic(integrable, 0.7)

    assert below > 0.2
    assert above < 0.0
    assert wrap_count(chaotic, 0.7) > 4.0


# --------------------------------------------------------------------------
# One family, two axes: the braid is the imaginary direction of the herald
# --------------------------------------------------------------------------

def test_the_herald_is_the_exponential_of_the_parity():
    """`K(alpha) = cos a Pi_+ + sin a Pi_-` equals `exp(t M)` up to scale.

    `Pi_+- = (1 +- M)/2`, so `K` is proportional to `1 + lambda M` with
    `lambda = tan(pi/4 - alpha)`; and `M^2 = 1` makes that `exp(t M)` with
    `t = artanh lambda`. The projective limit is `t -> infinity`, which is why
    weak measurement never arrives: the arrival is at infinite parameter.
    """
    from aionq.braid import complex_axis_report

    assert complex_axis_report()["herald_is_exponential"] < 1e-12


def test_the_braid_is_the_imaginary_axis_of_the_herald():
    """`exp(i s M) = exp(-s c_a c_b)` -- the braid generator, exactly.

    Agreement 0.00e+00 at three values of `s`. So the herald family and the
    braid family are not analogous, not related: they are the same
    one-parameter object `exp(t M)` continued in two directions.

        real t        measurement, non-unitary, drives entropy down
        imaginary t   braid, unitary, and by R1J invisible to hardness

    Everything measured about braids in R1J and about heralds in R1K-R1O is
    that single object read along two perpendicular lines.
    """
    from aionq.braid import complex_axis_report

    assert complex_axis_report()["braid_is_the_imaginary_axis"] < 1e-14


def test_the_whole_complex_plane_stays_gaussian():
    """25 points of the complex `t`-plane, worst Wick defect 3.3e-16.

    Neither axis can leave the class, and neither can any combination of them.
    """
    from aionq.braid import complex_axis_report

    assert complex_axis_report()["complex_plane_stays_gaussian"] < 1e-12


def test_a_half_turn_in_the_imaginary_direction_is_negation():
    """`exp((t + i pi) M) = -exp(t M)`: the family is pi-periodic, projectively.

    So the 180-degree intersection is exact and the two half-turns are the same
    channel. There is no additional structure hiding at the antipode.
    """
    from aionq.braid import complex_axis_report

    assert complex_axis_report()["half_turn_is_negation"] < 1e-12
