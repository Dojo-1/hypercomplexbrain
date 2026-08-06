"""The covariance formalism, and the gate that had to pass before it was believed.

R1S preregistered this instrument with a kill condition: it must reproduce the
16-mode state-vector results or the round stops and reports the discrepancy. The
gate fired on the first run and caught two real bugs. Both are recorded here as
tests rather than quietly fixed, because the gate catching them is the only
reason the 64-mode regime is reachable at all.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.linalg import expm

from aionq.majorana import majorana_operators
from aionq.pond import (breathing_trajectory, covariance, entanglement_entropy,
                        rung_pairs, vacuum)
from aionq.supercable import (agrees_with_state_vector, covariance_entropy,
                              covariance_storm, gaussian_purity_defect,
                              herald_covariance, herald_probability,
                              vacuum_covariance)


@pytest.fixture(scope="module")
def prepared():
    """The state `breathing_trajectory` prepares, reproduced exactly.

    Same generator, same seed, same Hermitisation -- so that a disagreement
    between the two formalisms is attributable to the formalism and not to the
    state they were handed.
    """
    qubits = 8
    modes = 2 * qubits
    operators = majorana_operators(qubits)
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * (hamiltonian + hamiltonian.conj().T) / 2.0) @ vacuum(qubits)
    return qubits, operators, state, covariance(state, operators)


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

@pytest.mark.parametrize("qubits", [2, 3, 4, 5])
def test_the_covariance_formalism_reproduces_the_exact_one(qubits):
    """Four bindings, all at machine zero, at four register sizes.

    Agreeing on one number is not agreement, so the gate pins the sign
    convention, every herald probability, every post-herald covariance and the
    entropy at every split -- `2 * 2n * (2n - 1)` comparisons at each size.
    """
    result = agrees_with_state_vector(qubits)

    assert result["passes"], result["worst"]
    assert result["worst"]["vacuum"] == 0.0
    for key in ("probability", "post_herald", "entropy"):
        assert result["worst"][key] < 1e-9


def test_the_storm_agrees_at_sixteen_modes_including_the_r1r_refutation(prepared):
    """The half of the gate that matters: whole trajectories, not single steps.

    Four rungs at two splits, 150 heralds each, worst disagreement 9.5e-14
    against a preregistered tolerance of 1e-9. It reproduces R1R's refuting cell
    exactly -- `M3` at split 2 gives 0.983691 in both formalisms -- which is the
    strongest single check available, because that number is the one that killed
    a rule and nothing about it is round or expected.
    """
    qubits, _, _, gamma = prepared

    worst = 0.0
    for rung in ("T2", "T4", "FROBENIUS", "M3"):
        pairs = rung_pairs(rung)
        for split in (2, 4):
            exact = breathing_trajectory(pairs, steps=150, seed=7, split=split)
            fast = covariance_storm(pairs, qubits, steps=150, seed=7, split=split,
                                    prepared=gamma)
            worst = max(worst, abs(exact["final_entropy"] - fast["final_entropy"]))

    assert worst < 1e-9

    refutation = covariance_storm(rung_pairs("M3"), qubits, steps=150, seed=7,
                                  split=2, prepared=gamma)
    assert refutation["final_entropy"] == pytest.approx(0.983691, abs=1e-5)


# --------------------------------------------------------------------------
# The two bugs the gate caught, kept as tests
# --------------------------------------------------------------------------

def test_the_vacuum_sign_convention_is_read_off_and_not_assumed():
    """The first version had it backwards, and nothing downstream would have said so.

    `i c_2k c_2k+1` is the single-qubit `Z`, and the first draft assumed that is
    `+1` on `|0>`. In this repository's Jordan-Wigner convention it is `-1`. The
    gate reported a defect of exactly 2.0 -- a clean sign flip -- and a
    convention error here would have been invisible everywhere downstream, since
    every later quantity is built from it.
    """
    for qubits in (2, 3, 4):
        operators = majorana_operators(qubits)
        assert np.array_equal(covariance(vacuum(qubits), operators),
                              vacuum_covariance(qubits))
        assert vacuum_covariance(qubits)[0, 1] == -1.0


def test_the_entropy_pairing_bug_is_invisible_at_the_smallest_split():
    """Which is why the gate sweeps every split instead of checking one.

    Each `nu_k` appears twice in `|Im spectrum|`, once per conjugate partner, so
    the entropy wants one representative per pair -- every second entry of the
    sorted list. The first version took the larger *half*, which turned
    `[1, 1, 0.325, 0.325]` into `[1, 1]` and reported entropy 0.000 against an
    exact 0.922.

    At `split = 1` there is one pair, so the larger half and one representative
    are the same element and the wrong code gives the right answer. A check at
    the smallest case would have passed and shipped the bug.
    """
    qubits = 3
    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[a, b] * (operators[a] @ operators[b])
        for a in range(modes) for b in range(modes) if a < b)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * hamiltonian) @ vacuum(qubits)
    gamma = covariance(state, operators)

    # the split that hides it, and the split that exposes it
    assert covariance_entropy(gamma, range(2)) == pytest.approx(
        entanglement_entropy(state, qubits, 1), abs=1e-12)
    assert covariance_entropy(gamma, range(4)) == pytest.approx(
        entanglement_entropy(state, qubits, 2), abs=1e-12)
    assert entanglement_entropy(state, qubits, 2) > 0.9, (
        "the exposing split must carry real entropy or it exposes nothing")

    # and the wrong rule, stated explicitly so the difference is visible
    values = np.sort(np.abs(np.linalg.eigvals(gamma[np.ix_(range(4), range(4))]).imag))[::-1]
    assert len(set(np.round(values, 9))) == 2, "each nu appears twice"
    assert not np.allclose(values[:2], values[::2]), (
        "larger-half and one-per-pair must actually differ here")


# --------------------------------------------------------------------------
# What the formalism cannot do, stated rather than discovered later
# --------------------------------------------------------------------------

def test_the_purity_defect_is_a_necessary_condition_and_not_a_certificate(prepared):
    """`Gamma^2 = -I` is the cheap check `pond` already warns about.

    The covariance formalism has no representation for a non-Gaussian state, so
    it cannot detect one -- this is a real loss of instrument against
    `wick_defect`, not a property of the states. Recorded so that a future round
    does not read a small purity defect as Gaussianity certified.
    """
    _, _, _, gamma = prepared

    assert gaussian_purity_defect(gamma) < 1e-9

    # A matrix that is antisymmetric and squares to -I, hence indistinguishable
    # here, carries no evidence about Wick's theorem at order four.
    fake = np.zeros((8, 8))
    for k in range(4):
        fake[2 * k, 2 * k + 1], fake[2 * k + 1, 2 * k] = -1.0, 1.0
    assert gaussian_purity_defect(fake) < 1e-12


def test_a_herald_that_never_fires_is_reported_rather_than_raised(prepared):
    """Same contract as `pond.herald_parity`: a null outcome is an answer."""
    qubits, _, _, gamma = prepared

    moved, probability = herald_covariance(vacuum_covariance(qubits), 0, 1, +1)
    assert probability == pytest.approx(0.0, abs=1e-12)
    assert moved is None

    moved, probability = herald_covariance(vacuum_covariance(qubits), 0, 1, -1)
    assert probability == pytest.approx(1.0, abs=1e-12)
    assert moved is not None


def test_the_formalism_reaches_where_the_state_vector_cannot():
    """Sixty-four modes: 64 x 64 against 4.3e9 amplitudes. The whole point.

    Kept small in step count because this test exists to show the regime is
    reachable at all, not to measure anything in it. No result is claimed here.
    """
    qubits = 32
    pairs = tuple((2 * k, 2 * k + 1) for k in range(qubits))

    result = covariance_storm(pairs, qubits, steps=40, seed=7, split=16)

    assert result["modes"] == 64
    assert result["covariance"].shape == (64, 64)
    assert result["purity_defect"] < 1e-8
    assert np.isfinite(result["final_entropy"])
