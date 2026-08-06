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
    "outcome_probability",
    "entanglement_entropy",
    "storm",
    "rung_pairs",
    "two_flats",
    "ladder_storm",
    "ladder_saturates",
    "collapse_trajectory",
    "weak_herald",
    "breathing_trajectory",
    "complement_pairs",
    "same_qubit_pairs",
    "cut_crossing_pairs",
    "pauli_centre_rank",
    "relabelling_report",
]


def covariance(state, operators) -> np.ndarray:
    """``Gamma_jk = (i/2) <[c_j, c_k]>``: the field description, ``2n x 2n``.

    Real and antisymmetric for any state.  It *determines* the state only when
    the state is Gaussian, which is exactly what `wick_defect` tests and what
    this function cannot.
    """
    state = np.asarray(state).ravel()
    modes = len(operators)
    # Each c_j is Hermitian, so <c_j c_k> = (c_j psi)^dag (c_k psi).  Precomputing
    # the 2n vectors c_j psi turns 2n(2n-1) matrix products into 2n matrix-vector
    # products plus inner products -- the difference between reaching n = 5 and
    # reaching n = 8, which is where 2n = 16 = |GF(16)| and the field structure
    # of `gf_frames` becomes available as a testbed.
    applied = np.array([operator @ state for operator in operators])
    grams = applied.conj() @ applied.T
    return np.real(0.5j * (grams - grams.T))


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
    # <c_a c_b c_c c_d> = (c_b c_a psi)^dag (c_c c_d psi), again because the
    # Majoranas are Hermitian.  Precomputing the ordered pair-vectors makes each
    # of the C(2n,4) quadruples one inner product instead of four matrix
    # products; measured identical to the direct form to 0.0 at n = 4 and n = 5,
    # on Gaussian and non-Gaussian states alike, and it brings n = 8 from
    # intractable to 0.52 seconds.
    pair = {}
    for right in range(modes):
        applied = operators[right] @ state
        for left in range(modes):
            if left != right:
                pair[(left, right)] = operators[left] @ applied
    worst = 0.0
    for a, b, c, d in combinations(range(modes), 4):
        exact = complex(np.vdot(pair[(b, a)], pair[(c, d)]))
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


def herald_parity(state, operators, indices, outcome: int = 1,
                  measure_defect: bool = True) -> dict:
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
        "wick_defect": (wick_defect(projected, operators) if measure_defect
                        else float("nan")),
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


def outcome_probability(gamma, first: int, second: int, outcome: int = 1) -> float:
    """``p(s) = (1 + s * Gamma_ab) / 2``, read straight off the field.

    The duality closing.  Every herald outcome's probability is one entry of the
    covariance matrix -- no ``2^n`` object is touched.  Measured against the exact
    amplitude calculation over all 28 mode pairs at ``n = 4``: worst disagreement
    2.2e-16.  So the whole storm, outcomes and all, is samplable from ``O(n^2)``
    numbers, and the record it produces carries no more than they do.
    """
    return float((1.0 + outcome * np.asarray(gamma)[first, second]) / 2.0)


def entanglement_entropy(state, qubits: int, split: int | None = None) -> float:
    """Von Neumann entropy across a contiguous cut, in bits.

    Included because it is what reveals where the storm actually goes.  The
    Gaussianity of the state never moves; its entropy does.

    ``split`` is the number of qubits on the left and defaults to the MIDDLE
    cut, ``qubits // 2``.  That default was the only cut R1M through R1Q used,
    and by R1R it is not an innocent one: every collapse result in those rounds
    is relative to it, because :func:`cut_crossing_pairs` is defined against the
    same boundary.  Qubit 0 is the most significant index of the state vector,
    so a left block of ``split`` qubits is modes ``0 .. 2*split - 1``.
    """
    state = np.asarray(state).ravel()
    split = qubits // 2 if split is None else split
    values = np.linalg.svd(state.reshape(2 ** split, -1), compute_uv=False)
    weights = values ** 2
    weights = weights[weights > 1e-30]
    return float(-np.sum(weights * np.log2(weights)))


def storm(qubits: int = 6, steps: int = 200, adaptive: bool = False,
          seed: int = 0) -> dict:
    """A long stream of quadratic parity heralds, optionally adaptive.

    ``adaptive`` chooses the next mode pair from the record of outcomes so far,
    which is the one route by which a disturbance could compound rather than
    reset.  Measured, it does not: the Wick defect stays at machine zero for 200
    heralds either way.

    WHERE THE STORM ACTUALLY GOES.  Under Jordan-Wigner ``i c_a c_b`` is a Pauli
    string, so a storm of quadratic parity heralds is repeated Pauli measurement
    -- which drives any state into the stabilizer set.  The signature is
    unmistakable in the trajectory: the entanglement entropy converges to
    **integers** (1.0000, 2.0000 exactly) and the support to powers of two.  The
    storm is a sink, and what it sinks to is a stabilizer state.

    Sampling here is honest rather than post-selected: the outcome is drawn with
    the probability the field predicts, so the trajectory is one the experiment
    would actually produce.
    """
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

    from scipy.linalg import expm
    state = expm(1j * hamiltonian) @ vacuum(qubits)
    pairs = [(a, b) for a in range(modes) for b in range(a + 1, modes)]

    record, trajectory, worst = [], [], 0.0
    for step in range(steps):
        if adaptive and record:
            index = (sum(1 for x in record if x > 0) * 7 + len(record) * 13) % len(pairs)
            first, second = pairs[index]
        else:
            first, second = pairs[int(rng.integers(0, len(pairs)))]
        gamma = covariance(state, operators)
        probability = outcome_probability(gamma, first, second, +1)
        outcome = 1 if rng.random() < probability else -1
        checkpoint = (step + 1) in (5, 20, 50, 100, steps)
        herald = herald_parity(state, operators, (first, second), outcome,
                               measure_defect=checkpoint)
        if herald["probability"] < 1e-12:
            continue
        state = herald["state"]
        record.append(outcome)
        if checkpoint:
            worst = max(worst, herald["wick_defect"])
        if checkpoint:
            trajectory.append({
                "heralds": step + 1,
                "entropy": entanglement_entropy(state, qubits),
                "support": int((np.abs(state) > 1e-9).sum()),
                "wick_defect": herald["wick_defect"],
            })

    return {
        "qubits": qubits,
        "adaptive": adaptive,
        "heralds": len(record),
        "worst_wick_defect": worst,
        "trajectory": trajectory,
        "final_state": state,
        "operators": operators,
    }


# --------------------------------------------------------------------------
# The testbed as a field rather than as a size
# --------------------------------------------------------------------------
#
# At n = 8 there are 16 Majorana modes, and 16 = |GF(16)| = |GF(GF(2,2), GF(2,2))|.
# So the mode set is not an arbitrary index range: it carries the field structure
# `gf_frames` already built, and the herald families can be indexed by the rungs
# of the AGL(1,16) subgroup ladder instead of drawn uniformly.
#
# That turns "which pairs do we measure" from a nuisance parameter into a
# coordinate on a known group, and the answer changes with it.


def rung_pairs(name: str) -> tuple:
    """Mode pairs ``{x, g(x)}`` for ``g`` in one rung of the AGL(1,16) ladder.

    The identity contributes nothing, so a rung of order ``m`` gives at most
    ``m - 1`` orbits' worth of pairs.  Measured sizes: T2 gives 8 -- a perfect
    matching, since ``x -> x + 1`` is a fixed-point-free involution -- T4 gives
    24, M3 15, FROBENIUS 19, M15 105, and T16 and AGL both give all 120.
    """
    from .gf_frames import subgroup

    out = set()
    for permutation in subgroup(name):
        for element in range(16):
            image = permutation[element]
            if element != image:
                out.add(tuple(sorted((element, image))))
    return tuple(sorted(out))


def two_flats() -> tuple:
    """The 140 four-element sets whose GF(16) labels XOR to zero.

    These are the 2-flats of ``AG(4,2)`` -- affine planes ``{x, x+u, x+v, x+u+v}``
    -- and they are the quartic index sets the field structure singles out.  The
    condition is the same characteristic-2 orthogonality `gf_frames.pg32_lines`
    uses one dimension lower.  The remaining 1680 quadruples are generic.
    """
    return tuple(quad for quad in combinations(range(16), 4)
                 if quad[0] ^ quad[1] ^ quad[2] ^ quad[3] == 0)


def ladder_storm(rung: str, steps: int = 200, seed: int = 7,
                 prepared_seed: int = 0) -> dict:
    """A storm whose herald pairs come from one rung of the GF(16) ladder.

    THE RESULT.  The same prepared state (entropy 2.2792) under the same number
    of heralds lands in completely different places depending on the rung, and
    **not monotonically in the number of pairs**:

        rung        pairs   final entropy   support
        T2              8         0.0000           1
        T4             24         0.0000           8
        FROBENIUS      19         0.0000          16
        M3             15         1.0000         128
        T16           120         2.0000          64
        M15           105         2.0000          64
        AGL           120         2.0000          64

    ``M3`` has fifteen pairs and leaves the state at entropy 1 with support 128 --
    less collapsed than ``FROBENIUS``, which has nineteen and drives it to entropy
    0.  ``T2``, the perfect matching, collapses it to a single basis state.  So it
    is the algebraic structure of the herald family that decides the sink, not
    how many pairs it contains.

    Every rung leaves the Wick defect at machine zero.  The storm stays Gaussian
    on all of them; where it stops does not.
    """
    from scipy.linalg import expm

    from .majorana import majorana_operators

    qubits = 8
    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(prepared_seed)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * hamiltonian) @ vacuum(qubits)

    pairs = rung_pairs(rung)
    walker = np.random.default_rng(seed)
    for _ in range(steps):
        first, second = pairs[int(walker.integers(0, len(pairs)))]
        gamma = covariance(state, operators)
        outcome = 1 if walker.random() < outcome_probability(gamma, first, second) else -1
        herald = herald_parity(state, operators, (first, second), outcome,
                               measure_defect=False)
        if herald["probability"] < 1e-12:
            continue
        state = herald["state"]

    return {
        "rung": rung,
        "pairs": len(pairs),
        "entropy": entanglement_entropy(state, qubits),
        "support": int((np.abs(state) > 1e-9).sum()),
        "wick_defect": wick_defect(state, operators),
        "final_state": state,
        "operators": operators,
    }


def ladder_saturates() -> dict:
    """Is there an OMNI rung beyond the top of the ladder?  There is not.

    The union of all seven rungs' pair sets is 120 pairs -- which is exactly what
    ``T16`` alone gives, because translations by the 15 nonzero field elements
    already realise every unordered pair ``{x, x+t}``.  So ``T16``, ``AGL`` and
    any union of rungs are the same herald family, and an "all at once" storm is
    not a new object.  The distinctions that matter live in the SMALL rungs:
    T2 (8 pairs), M3 (15), FROBENIUS (19), T4 (24), M15 (105).
    """
    from .gf_frames import SUBGROUP_LADDER

    sets = {rung: frozenset(rung_pairs(rung)) for rung in SUBGROUP_LADDER}
    union = frozenset().union(*sets.values())
    return {
        "union_size": len(union),
        "sizes": {rung: len(pairs) for rung, pairs in sets.items()},
        "saturating_rungs": tuple(sorted(r for r, p in sets.items() if p == union)),
        "subfield_tower": (sets["T2"] <= sets["T4"] <= sets["T16"]),
    }


def collapse_trajectory(rung: str, steps: int = 150, seed: int = 7,
                        prepared_seed: int = 0) -> dict:
    """The dense entropy trace, and the steps at which it actually moves.

    R1M reported only endpoints, and endpoints hide the crossing.  Traced step by
    step the rungs fall into two classes with nothing between them:

        rung        break steps                          final entropy
        T2          1, 2, 3, 4, 6, 8, 10  (7 moves)      0.0
        T4          1, 2, 4, 5, 6, 8, 10  (7 moves)      0.0
        FROBENIUS   1, 4, 6, 8, 15, 16, 25 (7 moves)     0.0
        T16         48 moves, spread throughout          1.0 - 3.0
        M3          56 moves                             1.0 - 2.7
        M15         48 moves                             0.0 - 2.0
        AGL         48 moves                             1.0 - 3.0

    The collapsing rungs make **seven** symmetry-breaking moves, all inside the
    first ten to twenty-five heralds, and are then frozen.  The others never stop
    moving.  That is the liminal structure: a short finite sequence of breaks and
    then a fixed point, versus an orbit that keeps wandering.

    WHAT THE FIELD TOWER SAYS.  ``T2``, ``T4`` and ``T16`` are translation by
    ``GF(2)``, ``GF(4)`` and ``GF(16)`` -- the subfield tower itself, and nested
    as sets.  Over five seeds, translation by a PROPER subfield reaches entropy 0
    every time (T2: 5/5, T4: 5/5) and translation by the WHOLE field never does
    (T16: 3.0, 1.0, 1.0, 2.0, 1.0).  The break in the tower is exactly between
    ``GF(4)`` and ``GF(16)``.
    """
    from scipy.linalg import expm

    from .majorana import majorana_operators

    qubits = 8
    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(prepared_seed)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * hamiltonian) @ vacuum(qubits)

    pairs = rung_pairs(rung)
    walker = np.random.default_rng(seed)
    entropies = [entanglement_entropy(state, qubits)]
    for _ in range(steps):
        first, second = pairs[int(walker.integers(0, len(pairs)))]
        gamma = covariance(state, operators)
        outcome = 1 if walker.random() < outcome_probability(gamma, first, second) else -1
        herald = herald_parity(state, operators, (first, second), outcome,
                               measure_defect=False)
        if herald["probability"] >= 1e-12:
            state = herald["state"]
        entropies.append(entanglement_entropy(state, qubits))

    entropies = np.array(entropies)
    breaks = [index for index in range(1, len(entropies))
              if abs(entropies[index] - entropies[index - 1]) > 1e-9]
    return {
        "rung": rung,
        "pairs": len(pairs),
        "entropies": entropies,
        "breaks": tuple(breaks),
        "break_count": len(breaks),
        "last_break": breaks[-1] if breaks else 0,
        "final_entropy": float(entropies[-1]),
        "final_state": state,
        "operators": operators,
    }


# --------------------------------------------------------------------------
# The continuum: measurement strength as an infinitesimal, and the pair set
# as something that must be CLOSED rather than merely small
# --------------------------------------------------------------------------

def weak_herald(state, operators, first: int, second: int, alpha: float,
                outcome: int = 1):
    """A partial parity measurement: ``alpha = 0`` projective, ``alpha = pi/4`` none.

    ``K_+ = cos(alpha) Pi_+ + sin(alpha) Pi_-`` and ``K_-`` the swap, so
    ``K_+* K_+ + K_-* K_- = I`` exactly.  This is the infinitesimal form of the
    herald and it fills in the whole circle between measuring and not.

    IT IS STILL GAUSSIAN, at every strength.  ``M = i c_a c_b`` satisfies
    ``M^2 = 1``, so ``a + bM`` is proportional to ``exp(t M)`` with
    ``tanh t = b/a`` -- the exponential of a quadratic, hence a (non-unitary)
    Gaussian operation.  Measured: worst Wick defect 4.3e-16 to 5.3e-16 across
    ``alpha/(pi/4) = 0, 0.25, 0.5, 0.8, 0.999``.  Breathing keeps the pond flat.
    """
    dimension = np.asarray(state).ravel().shape[0]
    parity = 1j * operators[first] @ operators[second]
    parity = (parity + parity.conj().T) / 2.0
    plus = (np.eye(dimension) + parity) / 2.0
    minus = (np.eye(dimension) - parity) / 2.0
    kraus = (np.cos(alpha) * plus + np.sin(alpha) * minus if outcome > 0
             else np.sin(alpha) * plus + np.cos(alpha) * minus)
    moved = kraus @ np.asarray(state).ravel()
    probability = float(np.linalg.norm(moved) ** 2)
    if probability < 1e-14:
        return None, probability
    return moved / np.linalg.norm(moved), probability


def complement_pairs(rung: str) -> tuple:
    """The 120 pairs minus one rung's: the primed, orthogonal clone of it.

    Measured, no complement collapses -- including ``M15^c``, which has 15 pairs,
    the same count as ``M3``, and which fails where ``T2``'s 8 succeed.  So
    collapse is not about how many pairs a family has.

    SUPERSEDED READING (R1Q).  This docstring used to continue "it is about the
    family being closed under a subgroup, and a complement is exactly the thing
    that is not".  That is withdrawn.  Closure under a subgroup is neither
    necessary nor sufficient: a relabelling of the modes preserves closure and
    destroys the collapse, 0 out of 72.  What a complement actually is, is a
    family that straddles the cut -- ``T2^c`` has 64 crossing pairs against
    ``T2``'s 0 -- and by :func:`cut_crossing_pairs` that is what decides it.  The
    measurement above is unaffected; only the reason given for it was wrong.
    """
    everything = {(a, b) for a in range(16) for b in range(a + 1, 16)}
    return tuple(sorted(everything - set(rung_pairs(rung))))


def breathing_trajectory(pairs, alpha: float = 0.0, steps: int = 150,
                         seed: int = 7, prepared_seed: int = 0,
                         split: int | None = None) -> dict:
    """A storm of partial heralds at strength ``alpha``.

    THE CONTINUUM, and it dissolves R1N's dichotomy.  At ``T2`` with 150 steps:

        alpha/(pi/4)   final entropy   breaks   last break
             0.00          0.0000          7        10
             0.20          0.0000         37        44
             0.40          0.0000         63        71
             0.60          0.0000        148       150
             0.80          0.8386        150       150
             0.90          1.7231        150       150
             0.98          2.2576        150       150

    "Seven breaks or forty-plus, nothing between" was the PROJECTIVE END of a
    one-parameter family.  The break count is continuous in the strength.

    AND THE APPARENT THRESHOLD IS THE STEP BUDGET, NOT THE PHYSICS -- but the
    correction to that reading needed correcting too.  At ``alpha/(pi/4) = 0.8``
    the entropy reads 8.4e-1 at 150 steps, 6.8e-3 at 300, 2.2e-6 at 600, 1.5e-8
    at 1000.  It is not collapsing more slowly to zero; it is decaying toward
    zero **asymptotically and never arriving**, about two and a half orders of
    magnitude per 300 heralds.

    So weak and projective differ in KIND, not in rate.  Projective reaches
    exactly 0 in seven steps and freezes; weak approaches 0 forever.  The
    ``alpha -> 0`` limit is a decay whose rate diverges until the process
    becomes finite.  A first reading of the 600-step number as "0.0000" was
    2.18e-06 printed at four decimals.
    """
    from scipy.linalg import expm

    from .majorana import majorana_operators

    qubits = 8
    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(prepared_seed)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    state = expm(1j * (hamiltonian + hamiltonian.conj().T) / 2.0) @ vacuum(qubits)

    pairs = tuple(pairs)
    walker = np.random.default_rng(seed)
    entropies = [entanglement_entropy(state, qubits, split)]
    for _ in range(steps):
        first, second = pairs[int(walker.integers(0, len(pairs)))]
        _, probability = weak_herald(state, operators, first, second, alpha, +1)
        outcome = 1 if walker.random() < probability else -1
        moved, _ = weak_herald(state, operators, first, second, alpha, outcome)
        if moved is not None:
            state = moved
        entropies.append(entanglement_entropy(state, qubits, split))

    entropies = np.array(entropies)
    breaks = [index for index in range(1, len(entropies))
              if abs(entropies[index] - entropies[index - 1]) > 1e-9]
    return {
        "alpha": alpha,
        "pairs": len(pairs),
        "entropies": entropies,
        "break_count": len(breaks),
        "last_break": breaks[-1] if breaks else 0,
        "final_entropy": float(entropies[-1]),
        "final_state": state,
        "operators": operators,
    }


# --------------------------------------------------------------------------
# What was actually driving the collapse, and it is not the field
# --------------------------------------------------------------------------

def same_qubit_pairs(pairs) -> tuple:
    """The pairs whose two modes sit on the same qubit -- i.e. the Pauli Z's.

    Under Jordan-Wigner mode ``j`` lives on qubit ``j // 2``, so ``i c_2k c_2k+1``
    is DIAGONAL: it is the single-qubit ``Z`` on qubit ``k``.  A herald on such a
    pair is a computational-basis measurement of one qubit, and eight of them are
    a measurement of the whole register.

    ``T2`` is translation by 1, which pairs ``x`` with ``x ^ 1`` -- and ``x`` and
    ``x ^ 1`` differ only in the lowest bit, so they are ``2k`` and ``2k+1``.
    **T2's eight pairs are exactly the eight single-qubit Z measurements.**

    THIS COUNT IS NOT THE MECHANISM, and the first version of this docstring said
    it was.  Two measurements kill that reading:

        FROBENIUS at the identity labelling collapses with 3 same-qubit pairs,
        while relabellings of FROBENIUS with 3 and with 4 do not collapse
        (final entropies 3.0, 3.0, 2.0 and 2.0, 1.0, 1.0);

        a family built as the eight single-qubit Z's PLUS eight cut-crossing
        pairs has the maximum count of 8 and does not collapse at any seed
        (3.0, 1.0, 1.0).

    What does track it is :func:`cut_crossing_pairs`.  Kept because the count is
    the right diagnostic for what ``T2`` is, and because a rule that separated
    every family it was fitted to and then failed out of sample is worth the
    line.
    """
    return tuple(pair for pair in pairs if pair[0] // 2 == pair[1] // 2)


def cut_crossing_pairs(pairs, qubits: int = 8, split: int | None = None) -> tuple:
    """The pairs straddling the bipartition that :func:`entanglement_entropy` reads.

    That function cuts the register in the middle, so on ``qubits = 8`` the cut
    falls between mode 7 and mode 8.  A herald on a pair that does not cross it is
    an operation local to one side, and local operations cannot build entanglement
    across it.

    MEASURED over the seven rungs and three complements:

        T2   T4   FROBENIUS      0 crossing pairs      collapse
        M3   M15^c              8                      no collapse
        M15  M3^c              56                      no collapse
        T16  AGL  T2^c         64                      no collapse

    Perfect separation, and unlike the F2 rank, the component count and the Pauli
    centre it is a *mechanism* rather than a coincidence of ten points.  It also
    explains the control that destroyed the centre rule: a random perfect matching
    has four crossing pairs.

    The two directions do not hold equally, and by R1R only one of them holds:

        crossing pairs  ->  no ROBUST collapse.  Stands.  Confirmed out of
        sample on a family carrying all eight Z's and eight crossings, and
        across all seven cuts of :func:`entanglement_entropy`, 28 cells.
        Individual seeds can still reach zero at a low crossing count -- ``T4``
        at split 5 gives ``0, 0, 1`` -- so what crossings destroy is
        reproducibility across seeds, not the possibility.

        no crossing pairs  ->  collapse.  **REFUTED**, one commit after it was
        recorded.  Sweeping the cut instead of holding it at the middle put the
        rule's own prediction in front of it: at ``split = 2`` the family ``M3``
        has ZERO crossing pairs and must collapse.  It does not -- 0.984, 0.978,
        0.741 at three seeds, identical at 400 and at 900 steps, so not a budget
        artifact either.  27 of 28 cells agreed and the one that did not was the
        single out-of-sample prediction.

    WHAT THE MISS BOUGHT.  Zero crossings is necessary and not sufficient: the
    family must also *reach* every mode inside each block.  ``M3`` is
    multiplication, ``0`` is its fixed point, so mode 0 receives no herald ever
    and the left block cannot be purified.  Adding ONE pair to cover it --
    ``M3 + (0,1)``, same zero crossings -- takes all three seeds to exactly 0.0
    at both budgets.  One pair, chosen for coverage, flips it.

    So the condition is: zero pairs across the cut AND every mode covered.  That
    is a mechanism and it is testable; it is also, still, entirely a fact about
    the labelling.

    The step budget cuts only one way, and that was checked rather than assumed:
    relabelled families run to 900 steps do NOT drift to zero, they freeze at 1.0
    to 3.0.  So the 0-out-of-72 of :func:`relabelling_report` is not a budget
    artifact -- the trap R1O had to correct.

    And it is a fact about the LABELLING, not about GF(16): which pairs cross
    depends entirely on where the modes sit relative to the cut, which is why the
    dichotomy does not survive :func:`relabelling_report`.
    """
    # ``split`` counts QUBITS on the left, matching entanglement_entropy's
    # reshape(2 ** (qubits // 2)).  The first version of this function took the
    # boundary to be ``qubits`` directly, which agrees for even ``qubits`` and is
    # wrong for odd -- at 7 qubits the entropy cuts at mode 6 and the crossing
    # count would have been taken at mode 7.  Latent: no odd case was ever run.
    split = qubits // 2 if split is None else split
    boundary = 2 * split         # modes 0..boundary-1 left, boundary.. right
    return tuple(pair for pair in pairs
                 if (pair[0] < boundary) != (pair[1] < boundary))


def pauli_centre_rank(pairs) -> dict:
    """Rank, and the radical of the symplectic form -- the centre of the group.

    For even-weight Majorana monomials ``c_S`` and ``c_T`` anticommute exactly
    when ``|S & T|`` is odd -- ``c_S c_T = (-1)^(|S||T| - |S & T|) c_T c_S`` and
    both weights are even -- so two edge generators anticommute exactly when the
    edges share a vertex.  The radical of the induced form on the F2 span is the
    centre of the Pauli group the family generates.

    **This was measured and it does NOT govern the collapse.**  On the seven
    rungs and three controls it separated them perfectly -- radical 4 or 8 for
    every collapsing family, 0 to 2 for every other -- and then failed on the
    first family it had not been fitted to: a random perfect matching has radical
    8, identical to ``T2``, and does not collapse.  Recorded because the near-miss
    is the point.
    """
    pivots = []
    for left, right in pairs:
        vector = (1 << left) ^ (1 << right)
        for pivot in pivots:
            vector = min(vector, vector ^ pivot)
        if vector:
            pivots.append(vector)
            pivots.sort(reverse=True)
    dimension = len(pivots)
    rows = [[bin(u & v).count("1") & 1 for v in pivots] for u in pivots]
    used, rank = [False] * dimension, 0
    for column in range(dimension):
        pivot_row = next((index for index in range(dimension)
                          if not used[index] and rows[index][column]), None)
        if pivot_row is None:
            continue
        used[pivot_row], rank = True, rank + 1
        for index in range(dimension):
            if index != pivot_row and rows[index][column]:
                rows[index] = [a ^ b for a, b in zip(rows[index], rows[pivot_row])]
    return {"rank": dimension, "radical": dimension - rank,
            "max_abelian": (dimension - rank) + rank // 2}


def relabelling_report(rung: str = "T2", trials: int = 5, seed: int = 0) -> dict:
    """Does the collapse survive a relabelling of the modes?  It does not.

    The pair set, the group it generates, its rank, radical and every graph
    invariant are unchanged by relabelling -- a relabelling only renames the
    modes.  If the field structure were doing the work, the collapse would
    survive.

    Measured over all three collapsing rungs, eight relabellings each and three
    storm seeds each:

        T2          identity 3/3 collapse      relabelled 0/24
        T4          identity 3/3               relabelled 0/24
        FROBENIUS   identity 3/3               relabelled 0/24

    **Nine out of nine as given, zero out of seventy-two relabelled.**

    So the collapse dichotomy of R1M through R1O is an artifact of the
    mode-to-qubit labelling, not a fact about GF(16).  R1M's own remainder named
    this risk exactly -- "identifying mode j with field element j is a choice the
    Jordan-Wigner ordering fixes; the rungs act on those labels, so a relabelling
    conjugates them" -- and it went untested for three rounds.

    The mechanism is :func:`cut_crossing_pairs`, not :func:`same_qubit_pairs`; a
    first reading of this experiment blamed the same-qubit count and is corrected
    in that function's docstring.
    """
    base = rung_pairs(rung)
    rng = np.random.default_rng(seed)
    rows = [{"labelling": "identity", "same_qubit": len(same_qubit_pairs(base)),
             "final_entropy": breathing_trajectory(base, steps=150)["final_entropy"]}]
    for trial in range(trials):
        permutation = rng.permutation(16)
        moved = [tuple(sorted((int(permutation[a]), int(permutation[b]))))
                 for a, b in base]
        rows.append({
            "labelling": f"random {trial}",
            "same_qubit": len(same_qubit_pairs(moved)),
            "final_entropy": breathing_trajectory(moved, steps=150)["final_entropy"],
        })
    return {"rung": rung, "rows": rows,
            "collapses_as_given": abs(rows[0]["final_entropy"]) < 1e-9,
            "collapses_after_relabelling": any(abs(r["final_entropy"]) < 1e-9
                                               for r in rows[1:])}
