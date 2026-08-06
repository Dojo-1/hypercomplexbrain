"""The covariance formalism, because 64 modes is 2^32 amplitudes.

Every state in the R1J-R1R line is exactly Gaussian.  That was measured, not
assumed: braids, theta-deformations, Floquet drives and quadratic heralds all sit
at machine zero on `wick_defect`, and only a quartic term leaves.  A Gaussian
state is fully described by

    Gamma_jk = (i/2) <[c_j, c_k]>          real, antisymmetric, 2n x 2n

so the whole storm can run on a matrix that grows quadratically where the state
vector grows exponentially.  At 16 modes that is 16 x 16 against 256 amplitudes;
at 64 modes it is 64 x 64 against 4.3e9, which is the difference between the
round happening and not.

THE HERALD IN THIS FORMALISM, derived rather than looked up.  For ``M = i c_a
c_b`` the projector is ``Pi_s = (1 + sM)/2``.  Two facts do the work: ``c_j``
commutes with ``M`` for ``j`` outside ``{a,b}``, and the four-point function is
fixed by Wick's theorem in exactly the form `pond.wick_defect` already uses,
``<c_a c_b c_c c_d> = -(G_ab G_cd - G_ac G_bd + G_ad G_bc)``.  Then

    p(s)       = (1 + s Gamma_ab) / 2
    Gamma'_jk  = Gamma_jk - s (Gamma_ja Gamma_kb - Gamma_jb Gamma_ka)
                            / (1 + s Gamma_ab)
    Gamma'_ab  = s,   Gamma'_ja = Gamma'_jb = 0  for j outside {a,b}

The measured pair is projected out and the rest of the matrix takes a rank-two
correction -- which is the covariance-level statement of what R1R found at the
level of entropy: a herald acts locally, and what it can reach is decided by
which modes it touches.

ENTANGLEMENT ENTROPY.  Restrict ``Gamma`` to the modes on one side of the cut and
diagonalise; the eigenvalues come in pairs ``+-i nu_k`` and

    S = sum_k H2((1 + nu_k) / 2),    H2 the binary entropy in bits

WHY THIS MODULE IS GATED.  It is new code that will run where the old code
cannot, which is the entire reason for writing it -- and that is also the reason
not to trust it.  `agrees_with_state_vector` is the preregistered gate: the
formalism must reproduce the R1K-R1R state-vector results at 16 modes before any
64-mode number is recorded.  A new instrument that disagrees with the old one on
the old one's domain is a bug until proven otherwise, and this repository has
twice mistaken an instrument artifact for a finding.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "vacuum_covariance",
    "gaussian_purity_defect",
    "herald_probability",
    "herald_covariance",
    "covariance_entropy",
    "covariance_storm",
    "agrees_with_state_vector",
]


def vacuum_covariance(qubits: int) -> np.ndarray:
    """``Gamma`` of ``|0...0>`` under the Jordan-Wigner convention used here.

    Read off the convention rather than assumed: mode ``2k`` and ``2k+1`` live on
    qubit ``k``, and ``i c_2k c_2k+1`` is the single-qubit ``Z``, which is ``+1``
    on ``|0>``.  So the vacuum block-diagonalises into ``[[0, 1], [-1, 0]]``.

    `agrees_with_state_vector` checks this against `pond.covariance` rather than
    taking it on trust, because a sign convention that is wrong here would be
    wrong everywhere downstream and invisible.
    """
    modes = 2 * qubits
    gamma = np.zeros((modes, modes))
    for k in range(qubits):
        gamma[2 * k, 2 * k + 1] = -1.0
        gamma[2 * k + 1, 2 * k] = 1.0
    return gamma


def gaussian_purity_defect(gamma) -> float:
    """``|Gamma^2 + I|``, and it is deliberately the WEAK check.

    By `pond`'s own module docstring this passes on states that are not Gaussian
    at all, so it is a necessary condition and never a certificate.  In the
    covariance formalism it cannot be anything else: the formalism has no way to
    represent a non-Gaussian state, so it cannot detect one.  That is a real loss
    of instrument relative to `wick_defect`, and it is stated here rather than
    discovered later.
    """
    gamma = np.asarray(gamma, dtype=float)
    return float(np.linalg.norm(gamma @ gamma + np.eye(gamma.shape[0])))


def herald_probability(gamma, first: int, second: int, outcome: int = 1) -> float:
    """``p(s) = (1 + s Gamma_ab)/2``, since ``<i c_a c_b> = Gamma_ab``."""
    return float((1.0 + outcome * np.asarray(gamma)[first, second]) / 2.0)


def herald_covariance(gamma, first: int, second: int, outcome: int = 1):
    """Project onto ``i c_a c_b = outcome`` and return ``(Gamma', probability)``.

    A zero-probability outcome returns ``(None, 0.0)`` rather than raising, for
    the same reason `pond.herald_parity` does: "this herald never fires" is an
    answer, and turning it into an exception loses it.
    """
    gamma = np.array(gamma, dtype=float)
    probability = herald_probability(gamma, first, second, outcome)
    if probability < 1e-14:
        return None, probability

    denominator = 1.0 + outcome * gamma[first, second]
    column_a, column_b = gamma[:, first].copy(), gamma[:, second].copy()
    correction = np.outer(column_a, column_b) - np.outer(column_b, column_a)
    moved = gamma - outcome * correction / denominator

    for index in (first, second):
        moved[index, :] = 0.0
        moved[:, index] = 0.0
    moved[first, second], moved[second, first] = outcome, -outcome
    return moved, probability


def covariance_entropy(gamma, modes_on_the_left) -> float:
    """Von Neumann entropy of the reduced state, in bits, from the block alone.

    ``Gamma`` restricted to a mode subset has spectrum ``+-i nu_k`` with
    ``nu_k`` in ``[0, 1]``; ``nu = 1`` is a pure mode contributing nothing and
    ``nu = 0`` is maximally mixed contributing one bit.

    THE PAIRING MATTERS AND THE FIRST VERSION GOT IT WRONG.  Each ``nu_k``
    appears TWICE in ``|Im spectrum|``, once for ``+i nu_k`` and once for
    ``-i nu_k``, so one representative per conjugate pair is wanted -- every
    second entry of the sorted list, not its larger half.  Taking the larger half
    gave ``[1, 1]`` from ``[1, 1, 0.325, 0.325]`` and returned entropy 0.000
    against an exact 0.922.

    It passed at ``split = 1``.  With one pair the larger half and one
    representative are the same element, so the smallest case cannot see the
    bug -- which is why the gate sweeps every split rather than checking one.
    """
    gamma = np.asarray(gamma, dtype=float)
    index = np.asarray(sorted(modes_on_the_left), dtype=int)
    block = gamma[np.ix_(index, index)]

    values = np.linalg.eigvals(block)
    nus = np.sort(np.abs(values.imag))[::-1][::2]

    total = 0.0
    for nu in np.clip(nus, 0.0, 1.0):
        for weight in ((1.0 + nu) / 2.0, (1.0 - nu) / 2.0):
            if weight > 1e-15:
                total -= weight * np.log2(weight)
    return float(total)


def covariance_storm(pairs, qubits: int, steps: int = 150, seed: int = 7,
                     prepared_seed: int = 0, split: int | None = None,
                     prepared: np.ndarray | None = None) -> dict:
    """The R1R storm, run on ``Gamma`` instead of on the state vector.

    Deliberately the same control flow as `pond.breathing_trajectory` at
    ``alpha = 0`` -- same walker, same outcome draw, same order -- so that a
    disagreement between the two is attributable to the formalism rather than to
    the loop.  One code path per condition is the round discipline; here it is
    two code paths for one condition, which is why they must be pinned together.
    """
    modes = 2 * qubits
    split = qubits // 2 if split is None else split
    left = list(range(2 * split))

    if prepared is None:
        rng = np.random.default_rng(prepared_seed)
        raw = rng.normal(size=(modes, modes))
        generator = (raw - raw.T) / 2.0
        rotation = _orthogonal_from_generator(generator)
        gamma = rotation @ vacuum_covariance(qubits) @ rotation.T
    else:
        gamma = np.array(prepared, dtype=float)

    pairs = tuple(pairs)
    walker = np.random.default_rng(seed)
    entropies = [covariance_entropy(gamma, left)]
    for _ in range(steps):
        first, second = pairs[int(walker.integers(0, len(pairs)))]
        probability = herald_probability(gamma, first, second, +1)
        outcome = 1 if walker.random() < probability else -1
        moved, _ = herald_covariance(gamma, first, second, outcome)
        if moved is not None:
            gamma = moved
        entropies.append(covariance_entropy(gamma, left))

    entropies = np.array(entropies)
    breaks = [index for index in range(1, len(entropies))
              if abs(entropies[index] - entropies[index - 1]) > 1e-9]
    return {
        "modes": modes,
        "split": split,
        "entropies": entropies,
        "break_count": len(breaks),
        "final_entropy": float(entropies[-1]),
        "purity_defect": gaussian_purity_defect(gamma),
        "covariance": gamma,
    }


def _orthogonal_from_generator(generator) -> np.ndarray:
    """``exp(A)`` for antisymmetric ``A``, via the real Schur route."""
    from scipy.linalg import expm

    return np.real(expm(np.asarray(generator, dtype=float)))


def agrees_with_state_vector(qubits: int = 4, tolerance: float = 1e-9) -> dict:
    """THE GATE.  Reproduce the exact formalism where the exact formalism runs.

    Four independent bindings, because agreeing on one number is not agreement:

    1. the vacuum covariance matches `pond.covariance` on the literal vacuum
       state -- this pins the Jordan-Wigner sign convention;
    2. herald probabilities match `pond.herald_parity` pair by pair and outcome
       by outcome;
    3. the post-herald covariance matches, so the update formula is right and not
       merely right on its diagonal;
    4. the entropy from the covariance block matches
       `pond.entanglement_entropy` on the same state, at every split.

    Anything short of all four leaves the 64-mode regime resting on a formalism
    that was checked on a projection of itself.
    """
    from scipy.linalg import expm

    from .majorana import majorana_operators
    from .pond import covariance, entanglement_entropy, herald_parity, vacuum

    operators = majorana_operators(qubits)
    modes = 2 * qubits

    worst = {"vacuum": 0.0, "probability": 0.0, "post_herald": 0.0, "entropy": 0.0}

    worst["vacuum"] = float(np.abs(
        covariance(vacuum(qubits), operators) - vacuum_covariance(qubits)).max())

    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * hamiltonian) @ vacuum(qubits)
    gamma = covariance(state, operators)

    for first in range(modes):
        for second in range(first + 1, modes):
            for outcome in (+1, -1):
                exact = herald_parity(state, operators, (first, second), outcome,
                                      measure_defect=False)
                worst["probability"] = max(worst["probability"], abs(
                    exact["probability"] - herald_probability(
                        gamma, first, second, outcome)))
                moved, _ = herald_covariance(gamma, first, second, outcome)
                if moved is None or exact["probability"] < 1e-9:
                    continue
                worst["post_herald"] = max(worst["post_herald"], float(np.abs(
                    covariance(exact["state"], operators) - moved).max()))

    for split in range(1, qubits):
        worst["entropy"] = max(worst["entropy"], abs(
            entanglement_entropy(state, qubits, split)
            - covariance_entropy(gamma, range(2 * split))))

    return {
        "qubits": qubits,
        "worst": worst,
        "tolerance": tolerance,
        "passes": all(value < tolerance for value in worst.values()),
    }
