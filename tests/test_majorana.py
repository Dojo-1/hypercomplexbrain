"""The certificate stated without coordinates, and what that changes.

Three things these tests pin, in increasing order of how much they matter:

1. the coordinate-free forms AGREE with the index forms exactly, so nothing was
   quietly redefined while being renamed;
2. the covariant defect is invariant under the full continuous frame group
   ``O(2n)`` -- and the first version was not, because its aggregator read the
   basis even though its formula did not;
3. the tangent dimension `transport_fiber` measured as a numerical rank is
   ``C(2n,2) + 1``, so it was never a measurement.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from qiskit.circuit.library import (CXGate, CZGate, RXXGate, RZZGate, SwapGate,
                                    iSwapGate)
from scipy.linalg import expm

from aionq import transport_fiber as fiber
from aionq.majorana import (gaussian_defect, gaussian_dimension, graded_parts,
                            is_gaussian, majorana_operators, parity_defect,
                            parity_operator)
from aionq.matchgate import is_matchgate_matrix
from aionq.matchgate_defect import matrix_parity_defect

_ZOO = {
    "rxx": RXXGate(0.7), "rzz": RZZGate(0.4), "iswap": iSwapGate(),
    "swap": SwapGate(), "cz": CZGate(), "cnot": CXGate(),
}


def _random_gaussian(n: int, seed: int, scale: float = 1.0) -> np.ndarray:
    """``exp(i H)`` for ``H`` quadratic in Majoranas: on the class by construction."""
    modes = majorana_operators(n)
    rng = np.random.default_rng(seed)
    hamiltonian = sum(
        float(rng.normal()) * 1j * (modes[left] @ modes[right])
        for left in range(2 * n) for right in range(left + 1, 2 * n))
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    return expm(1j * scale * hamiltonian)


# --------------------------------------------------------------------------
# 1. The index forms were shadows, not different quantities
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_ZOO))
def test_the_parity_blocks_are_a_z2_grading_and_the_two_forms_agree_exactly(name):
    """``||U-||_F`` where ``U- = (U - PUP)/2``, versus a list of eight positions.

    Exactly equal, not approximately: the eight forbidden entries ARE the
    coordinates of the parity-odd part, so the index version was computing the
    grading all along without saying so.
    """
    matrix = np.array(_ZOO[name].to_matrix())
    even, odd = graded_parts(matrix)

    assert parity_defect(matrix) == matrix_parity_defect(matrix)
    assert np.allclose(even + odd, matrix, atol=1e-15)
    parity = parity_operator(2)
    assert np.allclose(parity @ even @ parity, even, atol=1e-14)
    assert np.allclose(parity @ odd @ parity, -odd, atol=1e-14)


@pytest.mark.parametrize("name", sorted(_ZOO))
def test_majorana_covariance_decides_what_the_index_test_needed_two_tests_for(name):
    """One invariant condition subsumes the parity block test AND the determinant.

    `CZ` is the case that makes the point: it preserves the grading, so its
    parity defect is 0 and the index version must run a second, separate
    determinant test to reject it. The covariant version rejects it in the one
    number, because preserving the grading is not the same as preserving the
    Majorana span.
    """
    matrix = np.array(_ZOO[name].to_matrix())

    assert is_gaussian(matrix) == is_matchgate_matrix(matrix)

    if name == "cz":
        assert parity_defect(matrix) == pytest.approx(0.0, abs=1e-14)
        assert gaussian_defect(matrix) > 1.0
        assert not is_matchgate_matrix(matrix)


def test_the_algebra_it_was_derived_from_generates_the_class():
    """Anything ``exp(i * quadratic)`` is on the class, at any strength.

    Not a small-parameter statement: checked at scale 3.0 as well as 0.1, which
    is the group property `transport_fiber` observed as exact containment along
    a fiber. Here it is the definition rather than an observation.
    """
    for seed in range(6):
        for scale in (0.1, 1.0, 3.0):
            assert gaussian_defect(_random_gaussian(2, seed, scale)) == pytest.approx(
                0.0, abs=1e-9)


# --------------------------------------------------------------------------
# 2. Invariance, and the aggregator that broke it
# --------------------------------------------------------------------------

def test_the_defect_is_invariant_under_the_full_continuous_frame_group():
    """``O(2n)`` rotations of the Majorana frame, and Gaussian conjugation.

    The span of the modes is what the condition refers to, and a rotation
    preserves a span, so invariance is structural. It is checked anyway, because
    the first version of this module was structurally invariant and numerically
    not -- see the next test.
    """
    modes = majorana_operators(2)
    matrix = np.array(CXGate().to_matrix())
    base = gaussian_defect(matrix, modes)
    rng = np.random.default_rng(5)

    for _ in range(40):
        rotation, _ = np.linalg.qr(rng.normal(size=(4, 4)))
        rotated = tuple(sum(rotation[j, k] * modes[j] for j in range(4))
                        for k in range(4))
        assert gaussian_defect(matrix, rotated) == pytest.approx(base, abs=1e-12)

        gaussian = _random_gaussian(2, int(rng.integers(0, 10 ** 6)))
        moved = gaussian @ matrix @ gaussian.conj().T
        assert gaussian_defect(moved, modes) == pytest.approx(base, abs=1e-12)


def test_a_max_over_the_basis_is_not_invariant_and_a_sum_of_squares_is():
    """The defect this module shipped first, and why it was wrong.

    Writing a formula without indices does not make it invariant if the
    reduction that turns it into a number still reads them. ``max`` over the
    individual mode residuals is a maximum over a BASIS; rotating the basis mixes
    the residuals and the maximum moves. Measured here: the max form deviates by
    more than 1e-2 under random ``O(4)`` frames, the shipped sum-of-squares form
    by less than 1e-12.

    This is the eighth time this repository has found a quantity whose invariance
    claim outran its instrument, and the first time in a module written
    specifically to be invariant.
    """
    modes = majorana_operators(2)
    matrix = np.array(CXGate().to_matrix())

    def max_form(mtx, mds):
        scale = float(mtx.shape[0])
        worst = 0.0
        for mode in mds:
            moved = mtx @ mode @ mtx.conj().T
            projected = sum((np.trace(other.conj().T @ moved) / scale) * other
                            for other in mds)
            worst = max(worst, float(np.linalg.norm(moved - projected, "fro")))
        return worst

    rng = np.random.default_rng(5)
    max_base, sum_base = max_form(matrix, modes), gaussian_defect(matrix, modes)
    max_worst = sum_worst = 0.0
    for _ in range(40):
        rotation, _ = np.linalg.qr(rng.normal(size=(4, 4)))
        rotated = tuple(sum(rotation[j, k] * modes[j] for j in range(4))
                        for k in range(4))
        max_worst = max(max_worst, abs(max_form(matrix, rotated) - max_base))
        sum_worst = max(sum_worst, abs(gaussian_defect(matrix, rotated) - sum_base))

    assert max_worst > 1e-2, "the basis-dependent aggregator failed to misbehave"
    assert sum_worst < 1e-12


# --------------------------------------------------------------------------
# 3. The number that was never a measurement
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n,expected", [(1, 2), (2, 7), (3, 16), (4, 29)])
def test_the_class_dimension_is_derived_not_fitted(n, expected):
    """``C(2n,2) + 1``: ``so(2n)`` from the quadratic monomials, plus the phase."""
    geometry = gaussian_dimension(n)

    assert geometry["dimension"] == expected
    assert geometry["dimension"] == math.comb(2 * n, 2) + 1
    assert geometry["ambient"] == 4 ** n
    assert geometry["frame_group"] == f"O({2 * n})"


@pytest.mark.parametrize("n", [2, 3])
def test_the_derivation_matches_the_jacobian_rank_it_replaces(n):
    """The measured tangent dimension and the algebraic one are the same number.

    `transport_fiber` obtained 7 at ``n = 2`` from a numerical rank with a
    nine-order singular-value gap. Here it is ``C(4,2)+1`` with nothing measured.
    The agreement is the point: an instrument that returns the answer the algebra
    already knows is an instrument that can be trusted where the algebra is
    silent.
    """
    modes = majorana_operators(n)
    dimension = 2 ** n
    base = _random_gaussian(n, seed=1, scale=0.3)
    assert gaussian_defect(base, modes) == pytest.approx(0.0, abs=1e-9)

    def defining(matrix):
        scale = float(dimension)
        parts = []
        for mode in modes:
            moved = matrix @ mode @ matrix.conj().T
            projected = sum((np.trace(other.conj().T @ moved) / scale) * other
                            for other in modes)
            residual = moved - projected
            parts.extend((residual.real.ravel(), residual.imag.ravel()))
        return np.concatenate(parts)

    geometry = fiber.tangent_dimension(base, defining)
    assert geometry["tangent"] == gaussian_dimension(n)["dimension"]
    assert geometry["gap"] > 1e6


def test_qubit_relabelling_is_a_discrete_subgroup_of_the_real_frame_group():
    """Why the finite walk could only ever produce a step.

    Relabelling permutes Majorana PAIRS, so ``S_n`` sits inside ``O(2n)`` as a
    finite subgroup. At ``n = 16`` the frame group is 496-dimensional and ``S_16``
    is 2.1e13 isolated points in it. The R1B/R1C step is what a discrete subgroup
    of a Lie group can see, and the continuous directions were never sampled.
    """
    geometry = gaussian_dimension(16)
    assert geometry["frame_group_dimension"] == 496
    assert math.factorial(16) == 20922789888000

    modes = majorana_operators(2)
    matrix = np.array(CXGate().to_matrix())
    base = gaussian_defect(matrix, modes)
    swap = np.array(SwapGate().to_matrix())          # relabelling on 2 qubits
    assert gaussian_defect(swap @ matrix @ swap.conj().T, modes) == pytest.approx(
        base, abs=1e-12)
