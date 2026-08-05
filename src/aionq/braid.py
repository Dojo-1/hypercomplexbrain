"""What a braid does to hardness, which is nothing, measured.

Exchanging two Majorana modes is the operation

    sigma_k(theta) = exp(theta * c_k c_{k+1}),      braid at theta = pi/4

and it is **quadratic in the Majoranas**.  So it is a free-fermion operation, and
so is every word in the sigma_k, and so is the whole one-parameter family.  The
braid group representation these generate lands entirely inside the Gaussian
group, and this module measures that rather than citing it.

MEASURED, ``n = 4`` qubits, 8 modes:

    sigma_k(pi/4), k = 0,1,2               gaussian_defect  0.000e+00
    a 60-letter random braid word          gaussian_defect  5.8e-15
    theta in {0.1, pi/8, pi/4, 1.0, 2.5}   gaussian_defect  0.000e+00

    braid relation s_k s_{k+1} s_k = s_{k+1} s_k s_{k+1}
        exact difference 6.3e-16, phase +1.000000 -- so the relation holds ON
        THE NOSE, not projectively, on all five adjacent triples tested
    far commutation [s_j, s_k] for |j-k| >= 2   exactly 0.0

So the representation is a genuine one, the braid relations are satisfied
exactly, the topology is entirely real -- and on the hardness axis the whole
structure is invisible.  ``gaussian_defect`` does not move, and by R1I neither
does the level statistic, because a Gaussian unitary conjugates a quadratic
Hamiltonian to a quadratic Hamiltonian.  **This is the measured content of the
statement that Majorana braiding alone is not universal for quantum
computation.**

THE MOVING FISHNET IS ALSO FREE.  A time-periodic quadratic Hamiltonian has a
Floquet operator that is a product of Gaussian unitaries, hence Gaussian.
Measured on a two-step drive at ``n = 8``: ``gaussian_defect(F) = 1.7e-13``, and
``gaussian_defect(F^7) = 4.6e-13`` after seven periods.  Driving cannot leave the
class, at any period, for any number of periods.

    braid            stays          exact braid relations, defect 0
    theta-deform     stays          whole family, defect 0
    Floquet drive    stays          defect 1.7e-13, 4.6e-13 after 7 periods
    quartic term     LEAVES         defect 6.4e+01

Everything that looks like it should matter -- topology, motion, deformation --
leaves the class exactly where it was.  The one thing that leaves it is an
interaction.

A THIRD BLIND INSTRUMENT, CAUGHT BY A CONTROL.  The obvious way to ask whether a
driven system is chaotic is to take the ratio statistic of its quasi-energies.
That statistic is computed on angles, and angles wrap.  Measured, at ``n = 8``,
against a spectrum of half-width 26:

    period T   wraps (||H||T/pi)   integrable   chaotic   separation
      <= 0.1        <= 0.83          0.3348      0.5742     0.2394
       0.30           2.50           0.3448      0.4158     0.0710
       0.70           5.83           0.4349      0.3842    -0.0507

Below one wrap the statistic has its full discriminating power.  By 2.5 wraps it
has lost two thirds of it.  By 5.8 wraps the **sign has inverted**: the
integrable system reads more chaotic than the chaotic one.  A first attempt at
this measurement reported 0.43 for a driven free-fermion fishnet and was one step
from recording it as partial chaos.

The control that caught it needed correcting in turn.  Folding a static
integrable spectrum by hand, at one seed, moved it from 0.335 to 0.4385, and the
first reading of that was that folding pushes the statistic toward Poisson.
Across eight seeds and three periods it does nothing so orderly: mean shift
-0.016, standard deviation 0.082, sixteen down and eight up, worst magnitude
0.161 against an integrable-to-chaotic signal of 0.212.  Folding is a
**scramble, not a bias**, and the artefact is 76% of the signal it would be
confused with -- which is worse than a bias, because a bias could be subtracted.

`spectral_slice.quasi_energy_statistic` therefore refuses above one wrap rather
than returning a number.  This is the third instrument this session whose reach
turned out to be shorter than its claim, and the second to be caught only because
a control was run on a case where the answer was already known.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "braid_generator",
    "braid_word",
    "braid_relation_defect",
    "far_commutator_defect",
    "floquet_operator",
    "braid_report",
]


def braid_generator(index: int, operators, theta: float = math.pi / 4) -> np.ndarray:
    """``exp(theta * c_k c_{k+1})``: the exchange of two adjacent Majorana modes.

    Quadratic in the Majoranas by inspection, which is the whole point and the
    whole limitation.  ``theta = pi/4`` is the braid; every other ``theta`` is a
    partial exchange and is equally free.
    """
    from scipy.linalg import expm

    return expm(theta * (operators[index] @ operators[index + 1]))


def braid_word(letters, operators, theta: float = math.pi / 4) -> np.ndarray:
    """A product of generators and their inverses.

    ``letters`` is a sequence of ``(index, inverted)`` pairs rather than signed
    integers, because a signed encoding cannot express the inverse of generator
    zero: negative zero is not distinguishable from zero.
    """
    dimension = operators[0].shape[0]
    out = np.eye(dimension, dtype=complex)
    for index, inverted in letters:
        gate = braid_generator(index, operators, theta)
        out = out @ (gate.conj().T if inverted else gate)
    return out


def braid_relation_defect(index: int, operators,
                          theta: float = math.pi / 4) -> dict:
    """``s_k s_{k+1} s_k`` against ``s_{k+1} s_k s_{k+1}``, exactly and up to phase.

    Both are reported because a representation of the braid group that satisfies
    its relations only up to a phase is a *projective* representation, and the
    phase is a 2-cocycle rather than a rounding error.  Measured here the phase
    is ``+1.000000`` and the exact difference is 6.3e-16, so the representation
    is genuine and there is no cocycle to record.
    """
    left = (braid_generator(index, operators, theta)
            @ braid_generator(index + 1, operators, theta)
            @ braid_generator(index, operators, theta))
    right = (braid_generator(index + 1, operators, theta)
             @ braid_generator(index, operators, theta)
             @ braid_generator(index + 1, operators, theta))
    phase = complex(np.trace(right.conj().T @ left)
                    / (np.linalg.norm(left) ** 2))
    return {
        "exact": float(np.linalg.norm(left - right)),
        "phase": phase,
        "up_to_phase": float(np.linalg.norm(left - phase * right)),
    }


def far_commutator_defect(left: int, right: int, operators,
                          theta: float = math.pi / 4) -> float:
    """``[s_j, s_k]`` for ``|j - k| >= 2``: the other braid relation."""
    first = braid_generator(left, operators, theta)
    second = braid_generator(right, operators, theta)
    return float(np.linalg.norm(first @ second - second @ first))


def floquet_operator(hamiltonians, periods) -> np.ndarray:
    """A multi-step drive: the ordered product of ``exp(i H_j t_j)``.

    A product of Gaussian unitaries is Gaussian, so a periodically driven
    quadratic Hamiltonian cannot leave the free-fermion class -- at any period,
    for any number of periods.  Stated as a fact about the product and measured
    in `braid_report`.
    """
    from scipy.linalg import expm

    dimension = np.asarray(hamiltonians[0]).shape[0]
    out = np.eye(dimension, dtype=complex)
    for hamiltonian, period in zip(hamiltonians, periods):
        out = expm(1j * np.asarray(hamiltonian) * period) @ out
    return out


def braid_report(qubits: int = 4, theta: float = math.pi / 4,
                 word_length: int = 60, seed: int = 0) -> dict:
    """Braids, a random word, the theta family, and a driven fishnet."""
    from .majorana import gaussian_defect, majorana_operators

    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(seed)

    letters = [(int(rng.integers(0, modes - 1)), bool(rng.random() < 0.5))
               for _ in range(word_length)]

    def quadratic(generator):
        total = sum(1j * generator[left, right] * (operators[left] @ operators[right])
                    for left in range(modes) for right in range(modes) if left < right)
        return (total + total.conj().T) / 2.0

    first = rng.normal(size=(modes, modes))
    first = (first - first.T) / 2.0
    second = rng.normal(size=(modes, modes))
    second = (second - second.T) / 2.0
    floquet = floquet_operator([quadratic(first), quadratic(second)], [1.3, 0.7])

    return {
        "generators": {index: gaussian_defect(
            braid_generator(index, operators, theta), operators)
            for index in range(min(3, modes - 1))},
        "word": gaussian_defect(braid_word(letters, operators, theta), operators),
        "theta_family": {value: gaussian_defect(
            braid_generator(0, operators, value), operators)
            for value in (0.1, math.pi / 8, math.pi / 4, 1.0, 2.5)},
        "relations": {index: braid_relation_defect(index, operators, theta)
                      for index in range(modes - 2)},
        "far_commutators": {(0, 2): far_commutator_defect(0, 2, operators, theta),
                            (0, 3): far_commutator_defect(0, 3, operators, theta)},
        "floquet": gaussian_defect(floquet, operators),
        "floquet_seven_periods": gaussian_defect(
            np.linalg.matrix_power(floquet, 7), operators),
    }
