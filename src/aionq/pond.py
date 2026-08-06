"""The quiet pond, the rain, and the membrane that reads one without disturbing it.

Everything measured in this repository up to here has been about OPERATORS: is a
unitary quadratic in the Majoranas, does a spectrum repel.  A state has a
description too, and for a fermionic Gaussian state it is small:

    Gamma_jk = (i/2) <[c_j, c_k]>          a real antisymmetric 2n x 2n matrix

That is the **field** side of the duality.  ``2n(2n-1)/2`` numbers stand in for
``2^n`` amplitudes, and every correlator of every order is determined by them
through Wick's theorem:

    <c_a c_b c_c c_d> = -( Gamma_ab Gamma_cd - Gamma_ac Gamma_bd + Gamma_ad Gamma_bc )

So the **membrane** -- the instrument that says whether a state is still Gaussian
-- is the failure of that identity, maximised over all four-index sets:

    wick_defect(psi) = max over {a<b<c<d} | <c_a c_b c_c c_d> + Pf-expansion |

It is a state-level analogue of `majorana.gaussian_defect`, which is an
operator-level quantity, and the two answer different questions about different
objects.

MEASURED, ``n = 4`` qubits, 8 modes:

    vacuum                                       wick_defect  0.000e+00
    after a random Gaussian unitary              wick_defect  3.2e-16
    after a braid                                wick_defect  3.3e-16
    heralded QUADRATIC parity i c_a c_b, both
      outcomes, three different pairs            wick_defect  1.1e-16 .. 4.4e-16
    heralded QUARTIC parity c_a c_b c_c c_d      wick_defect  1.8e-01 .. 6.5e-01
    a quartic unitary kick                       wick_defect  1.5e-01

THE RESULT.  **Heralding is not the magic; the degree of the measured observable
is.**  Post-selecting on a quadratic parity -- the standard fermionic parity
measurement, at either outcome, at probabilities from 0.135 to 0.865 -- leaves
the pond exactly flat.  Post-selecting on a quartic parity disturbs it by up to
0.65.  The act of measuring and the act of post-selecting contribute nothing; the
observable does.

This settles a question left open one round earlier, where "free fermions plus
parity measurement with post-selection" was named as the obvious next thing and
the answer was not known.  The answer is that quadratic parity heralding stays
inside the class.  Magic has to be brought in, and it is brought in by measuring
something of degree four -- or equivalently by injecting a state that is not
Gaussian.  It does not condense out of the measurement process.

WHY THE MEMBRANE IS THE RIGHT INSTRUMENT AND ``Gamma`` ALONE IS NOT.  Every state
has a ``Gamma``; only a Gaussian state is *described* by it.  Reading ``Gamma``
off a non-Gaussian state gives a perfectly well-formed antisymmetric matrix that
predicts the two-point functions correctly and the four-point functions wrongly.
A check that only looked at ``Gamma`` -- its antisymmetry, or ``Gamma^2 = -I``
for purity -- would pass on states it has no business passing on.  The defect has
to be evaluated at an order the description does not already fix, which is four.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

__all__ = [
    "covariance",
    "wick_defect",
    "is_pure_gaussian",
    "vacuum",
    "herald_parity",
    "rain_report",
]


def covariance(state, operators) -> np.ndarray:
    """``Gamma_jk = (i/2) <[c_j, c_k]>``: the field description, ``2n x 2n``.

    Real and antisymmetric for any state.  It *determines* the state only when
    the state is Gaussian, which is exactly what `wick_defect` tests and what
    this function cannot.
    """
    state = np.asarray(state).ravel()
    modes = len(operators)
    out = np.zeros((modes, modes))
    for left in range(modes):
        for right in range(modes):
            if left == right:
                continue
            bracket = (operators[left] @ operators[right]
                       - operators[right] @ operators[left])
            out[left, right] = (0.5j * np.vdot(state, bracket @ state)).real
    return out


def wick_defect(state, operators, gamma=None) -> float:
    """Worst violation of Wick's theorem at order four. The membrane.

    Order four and not order two: the two-point functions are what ``Gamma``
    *is*, so testing them tests nothing.  Four is the lowest order at which the
    Gaussian description makes a prediction that can fail.
    """
    state = np.asarray(state).ravel()
    modes = len(operators)
    if gamma is None:
        gamma = covariance(state, operators)
    worst = 0.0
    for a, b, c, d in combinations(range(modes), 4):
        product = operators[a] @ operators[b] @ operators[c] @ operators[d]
        exact = complex(np.vdot(state, product @ state))
        pfaffian = (gamma[a, b] * gamma[c, d] - gamma[a, c] * gamma[b, d]
                    + gamma[a, d] * gamma[b, c])
        worst = max(worst, abs(exact + pfaffian))
    return float(worst)


def is_pure_gaussian(state, operators, tolerance: float = 1e-9) -> dict:
    """Both conditions, reported separately because only one of them has content.

    ``Gamma^2 = -I`` is purity of the *Gaussian* description and is satisfied by
    states that are not Gaussian at all; the Wick defect is the discriminating
    one.  Returning both makes the distinction visible instead of letting the
    cheap check stand in for the real one.
    """
    gamma = covariance(state, operators)
    modes = len(operators)
    return {
        "gamma_squared_defect": float(np.linalg.norm(
            gamma @ gamma + np.eye(modes))),
        "wick_defect": wick_defect(state, operators, gamma),
        "gaussian": wick_defect(state, operators, gamma) <= tolerance,
    }


def vacuum(qubits: int) -> np.ndarray:
    """``|0...0>``: the quiet pond."""
    state = np.zeros(2 ** qubits, dtype=complex)
    state[0] = 1.0
    return state


def herald_parity(state, operators, indices, outcome: int = 1) -> dict:
    """Measure a Majorana parity and post-select on ``outcome``. The rain.

    The observable is ``i^(k(k-1)/2) c_{a1}...c_{ak}`` for an even number ``k`` of
    distinct modes, which is Hermitian and squares to the identity, so it is a
    genuine two-outcome measurement.  The degree ``k`` is the variable this
    module is about: two leaves the pond flat, four does not.

    Returns the post-selected state, its probability, and the membrane reading.
    A zero-probability outcome is reported rather than raising, because "this
    herald never fires" is an answer.
    """
    state = np.asarray(state).ravel()
    dimension = state.shape[0]
    degree = len(indices)
    if degree % 2:
        raise ValueError("a parity observable needs an even number of modes")
    product = np.eye(dimension, dtype=complex)
    for index in indices:
        product = product @ operators[index]
    # The phase is load-bearing.  A product of k distinct Majoranas obeys
    # (c_1...c_k)* = (-1)^(k(k-1)/2) c_1...c_k, so it is Hermitian only after
    # multiplying by i^(k(k-1)/2): i for k = 2, -1 for k = 4.  An earlier version
    # omitted it and symmetrised instead, which for k = 2 annihilates the
    # operator exactly -- every projector became I/2, every herald fired with
    # probability 0.25, and the "post-selected" state was the input.  The
    # Hermiticity assertion that was supposed to catch this passed, because the
    # zero matrix is Hermitian.  The guard below is on the spectrum instead.
    observable = (1j ** (degree * (degree - 1) // 2)) * product
    if not np.allclose(observable, observable.conj().T, atol=1e-12):
        raise ValueError("the phased Majorana product is not Hermitian")
    spectrum = np.linalg.eigvalsh(observable)
    if not np.allclose(np.abs(spectrum), 1.0, atol=1e-9):
        raise ValueError(
            "a parity observable must square to the identity; its spectrum is "
            f"in [{spectrum.min():.3g}, {spectrum.max():.3g}], so the operator "
            "is not a projective measurement of anything")

    projected = ((np.eye(dimension) + outcome * observable) / 2.0) @ state
    probability = float(np.linalg.norm(projected) ** 2)
    if probability < 1e-12:
        return {"probability": 0.0, "state": None, "wick_defect": float("nan"),
                "degree": len(indices)}
    projected = projected / np.linalg.norm(projected)
    return {
        "probability": probability,
        "state": projected,
        "wick_defect": wick_defect(projected, operators),
        "degree": len(indices),
    }


def rain_report(qubits: int = 4, seed: int = 0) -> dict:
    """Quadratic heralds against quartic ones, on the same Gaussian state.

    The contrast is the finding.  Both are measurements, both are post-selected,
    both fire with substantial probability; only one of them leaves the class.
    """
    from scipy.linalg import expm

    from .majorana import majorana_operators

    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    prepared = expm(1j * hamiltonian) @ vacuum(qubits)

    quadratic, quartic = [], []
    for pair in ((0, 3), (2, 5), (1, 6)):
        for outcome in (1, -1):
            quadratic.append(herald_parity(prepared, operators, pair, outcome))
    for quad in ((0, 1, 2, 3), (0, 2, 4, 6), (1, 3, 5, 7)):
        for outcome in (1, -1):
            quartic.append(herald_parity(prepared, operators, quad, outcome))

    live = lambda rows: [row for row in rows if row["probability"] > 1e-9]
    return {
        "prepared_defect": wick_defect(prepared, operators),
        "quadratic": {
            "heralds": len(live(quadratic)),
            "worst_defect": max(row["wick_defect"] for row in live(quadratic)),
            "probability_range": (min(row["probability"] for row in live(quadratic)),
                                  max(row["probability"] for row in live(quadratic))),
        },
        "quartic": {
            "heralds": len(live(quartic)),
            "worst_defect": max(row["wick_defect"] for row in live(quartic)),
            "least_defect": min(row["wick_defect"] for row in live(quartic)),
            "probability_range": (min(row["probability"] for row in live(quartic)),
                                  max(row["probability"] for row in live(quartic))),
        },
    }
