"""Two places to apply a spectral multiplier to a fermionic network, and they differ.

`qffo` showed a QFFO is a spectral band weight. `majorana` showed the
free-fermion class is a subgroup of dimension `C(2n,2)+1`. Applying the first to
the second has two readings that sound alike and are opposite: weight the
single-particle spectrum and you move along the class exactly, weight the
many-body spectrum and you leave it by a measured amount.

The first test in this file is not about either. It is about the factor of `i`
that the first version of this measurement omitted, which made every Hamiltonian
zero and every unitary the identity, and which would have produced the same
headline dichotomy from a measurement of nothing at all.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.linalg import expm

from aionq.fishnet import (excitation_report, excite_many_body,
                           excite_single_particle, gaussian_unitary,
                           quadratic_hamiltonian, random_generator)
from aionq.majorana import gaussian_defect, gaussian_dimension, majorana_operators


def test_the_generator_is_not_identically_zero():
    """The bug that nearly produced a dichotomy from the identity operator.

    For `j != k` the Majorana product `c_j c_k` is ANTI-Hermitian, so building
    `sum A_jk c_j c_k` and symmetrising annihilates it exactly. The first version
    of this measurement did that, got `H = 0`, `exp(iH) = I`, and reported
    free-fermion defect `0.000e+00` for both branches -- a perfect dichotomy
    between two things that were both the identity.

    Asserted on the norm, because that is the quantity that was zero.
    """
    operators = majorana_operators(3)
    generator = random_generator(6, seed=4)
    hamiltonian = quadratic_hamiltonian(generator, operators)

    assert np.linalg.norm(hamiltonian, "fro") > 1.0
    assert np.allclose(hamiltonian, hamiltonian.conj().T, atol=1e-12)

    naive = sum(generator[j, k] * (operators[j] @ operators[k])
                for j in range(6) for k in range(6) if j < k)
    assert np.linalg.norm(naive + naive.conj().T) < 1e-12, (
        "without the factor of i, symmetrising gives exactly zero -- which is "
        "the failure this test exists to prevent recurring")


@pytest.mark.parametrize("qubits", [2, 3])
def test_a_quadratic_generator_produces_a_free_fermion_unitary(qubits):
    """The baseline. Without it the two branches below compare against nothing."""
    operators = majorana_operators(qubits)
    unitary = gaussian_unitary(random_generator(2 * qubits, seed=4), operators)
    assert gaussian_defect(unitary, operators) == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------
# The dichotomy
# --------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["caputo", "integral"])
@pytest.mark.parametrize("q", [0.5, 0.9])
def test_the_single_particle_branch_moves_far_and_stays_on_the_class(kind, q):
    """Transport along the fiber, and not by standing still.

    Displacement of up to 0.40 in the generator with the defect never leaving
    4e-15. Containment is structural: reweighting the spectrum of the Hermitian
    `iA` and mapping back returns a real antisymmetric matrix, so the result is
    Gaussian for ANY weights whatever.
    """
    report = excitation_report(qubits=3, kind=kind, q=q)
    branch = report["single_particle"]

    assert branch["displacement"] > 0.1, "a branch that stays by not moving proves nothing"
    assert branch["defect"] < 1e-9


@pytest.mark.parametrize("kind", ["caputo", "integral"])
@pytest.mark.parametrize("q", [0.5, 0.9])
def test_the_many_body_branch_leaves_the_class(kind, q):
    """Weighting the many-body spectrum breaks quadraticity, measurably."""
    report = excitation_report(qubits=3, kind=kind, q=q)
    branch = report["many_body"]

    assert branch["displacement"] > 0.1
    assert branch["defect"] > 0.5


@pytest.mark.parametrize("kind", ["caputo", "integral"])
def test_the_two_branches_separate_at_matched_displacement(kind):
    """The comparison that carries the content.

    Nearly the same distance travelled -- 0.18 against 0.20 at `q = 0.5` -- and
    fifteen orders of magnitude apart in whether the certificate survives. So the
    difference is the DIRECTION of the excitation and not its size, which is what
    makes this a fiber/transverse split rather than a statement about magnitude.
    """
    report = excitation_report(qubits=3, kind=kind, q=0.5)
    single, many = report["single_particle"], report["many_body"]

    assert abs(single["displacement"] - many["displacement"]) < 0.05
    assert many["defect"] / max(single["defect"], 1e-18) > 1e10


def test_q_is_a_knob_on_how_far_off_the_class_the_excitation_lands():
    """The transverse departure the strategy portfolio has no other source for.

    `matchgate_plan` certifies or refuses; the only thing the frame group moves
    is routing. Here the departure is parameterised, generated by an operator
    with a fractal order rather than by a random kick, and measured by an
    invariant. Monotone in `q` over the values tested.
    """
    defects = [excitation_report(qubits=3, kind="caputo", q=q)["many_body"]["defect"]
               for q in (0.5, 0.7, 0.9)]

    assert all(left < right for left, right in zip(defects, defects[1:]))
    assert defects[0] > 0.5


def test_the_single_particle_branch_cannot_leave_by_construction():
    """Checked with adversarial weights, not only with the ones a QFFO supplies.

    The containment claim is structural, so it must survive weights chosen to
    break it: negative, zero, enormous, and random. If it did not, the claim
    would be about the QFFO's particular weights and not about the branch.
    """
    operators = majorana_operators(3)
    generator = random_generator(6, seed=4)
    rng = np.random.default_rng(0)

    for weights in (np.full(6, -3.0), np.zeros(6), np.full(6, 1e3),
                    rng.normal(size=6), rng.normal(size=6) * 50):
        moved = excite_single_particle(generator, weights)
        assert np.allclose(moved, -moved.T, atol=1e-10), "left so(2n)"
        assert gaussian_defect(gaussian_unitary(moved, operators),
                               operators) == pytest.approx(0.0, abs=1e-8)


def test_the_departure_is_transverse_to_the_dimension_majorana_derived():
    """`so(2n)` has dimension `C(2n,2)`, and that is where the safe branch lives.

    The single-particle branch moves inside a space of dimension 15 at `n = 3`;
    the many-body branch moves in the full `4^n = 64`. The ratio is the
    codimension the excitation can reach, and it is why one branch cannot leave
    and the other cannot help but.
    """
    geometry = gaussian_dimension(3)
    assert geometry["dimension"] == 16
    assert geometry["ambient"] == 64
    assert geometry["codimension"] == 48

    generator = random_generator(6, seed=4)
    assert generator.shape == (6, 6)
    independent = 6 * 5 // 2
    assert independent == geometry["quadratic"] == 15
