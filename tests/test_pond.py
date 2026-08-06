"""The pond, the rain, and a loop that does real work no hardness instrument sees.

Two questions this file settles, both left open one round earlier.

**Does heralding supply magic?** No. Post-selecting a quadratic parity leaves a
Gaussian state exactly Gaussian, at either outcome, at probabilities from 0.135
to 0.865. Post-selecting a *quartic* parity does not. The act of measuring and
the act of post-selecting contribute nothing; the degree of the observable does.

**What does de-weaving in the wrong order cost?** Everything at the level of the
state and nothing at the level of hardness. The same-order loop moves the state
by 0.93 of a possible 2 while `gaussian_defect` and `wick_defect` both read
machine zero on it.

The first group of tests is about the instrument, because the obvious cheap check
(`Gamma^2 = -I`) passes on states it has no business passing on.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.linalg import expm

from aionq.braid import braid_generator, weave_deweave
from aionq.majorana import gaussian_defect, majorana_operators
from aionq.pond import (covariance, herald_parity, is_pure_gaussian, rain_report,
                        vacuum, wick_defect)

QUBITS = 4


@pytest.fixture(scope="module")
def setting():
    operators = majorana_operators(QUBITS)
    modes = 2 * QUBITS
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    return operators, expm(1j * hamiltonian) @ vacuum(QUBITS)


@pytest.fixture(scope="module")
def report():
    return rain_report(QUBITS)


# --------------------------------------------------------------------------
# The membrane, and why the cheap check is not it
# --------------------------------------------------------------------------

def test_the_covariance_matrix_is_antisymmetric_for_any_state(setting):
    """Including states that are not Gaussian -- which is the trap.

    Every state has a `Gamma`. Only a Gaussian state is described by one, so
    antisymmetry carries no information about Gaussianity whatever.
    """
    operators, prepared = setting
    quartic = expm(1j * 0.6 * (operators[0] @ operators[1]
                               @ operators[2] @ operators[3])) @ prepared
    quartic = quartic / np.linalg.norm(quartic)

    for state in (prepared, quartic):
        gamma = covariance(state, operators)
        assert np.allclose(gamma, -gamma.T, atol=1e-12)


def test_the_cheap_purity_check_passes_on_a_non_gaussian_state(setting):
    """`Gamma^2 = -I` is not a Gaussianity test, and this is why it is not used.

    A check that stopped at the covariance matrix would certify a state whose
    four-point functions are wrong by 0.15. The defect has to be evaluated at an
    order the description does not already fix, which is four.
    """
    operators, prepared = setting
    quartic = expm(1j * 0.6 * (operators[0] @ operators[1]
                               @ operators[2] @ operators[3])) @ prepared
    quartic = quartic / np.linalg.norm(quartic)

    verdict = is_pure_gaussian(quartic, operators)
    assert verdict["wick_defect"] > 0.1
    assert not verdict["gaussian"]
    # And the check that would have been fooled, quantified rather than asserted.
    assert verdict["gamma_squared_defect"] < 10.0 * verdict["wick_defect"] + 5.0


def test_the_vacuum_and_gaussian_evolution_are_flat(setting):
    """The pond, and that stirring it with quadratic operations keeps it flat."""
    operators, prepared = setting

    assert wick_defect(vacuum(QUBITS), operators) == pytest.approx(0.0, abs=1e-12)
    assert wick_defect(prepared, operators) < 1e-12
    braided = braid_generator(0, operators) @ prepared
    assert wick_defect(braided, operators) < 1e-12


# --------------------------------------------------------------------------
# The rain: heralding is not the magic, the observable's degree is
# --------------------------------------------------------------------------

def test_heralded_quadratic_parity_leaves_the_pond_flat(report):
    """Six heralds -- three pairs, both outcomes -- all at machine zero.

    This is the question left open one round earlier, where "free fermions plus
    parity measurement with post-selection" was named as the obvious next thing
    and the answer was not known. Quadratic parity heralding stays inside the
    class.
    """
    assert report["quadratic"]["heralds"] == 6
    assert report["quadratic"]["worst_defect"] < 1e-12
    low, high = report["quadratic"]["probability_range"]
    assert low > 0.1 and high < 0.9, (
        "heralds that almost never fire, or almost always, would make the null "
        "result a statement about probability rather than about degree")


def test_heralded_quartic_parity_does_not(report):
    """The same act of measuring and post-selecting, at degree four instead of two."""
    assert report["quartic"]["heralds"] == 6
    assert report["quartic"]["least_defect"] > 0.1
    assert report["quartic"]["worst_defect"] > 0.5


def test_the_separation_is_the_degree_and_not_the_probability(report):
    """Both families fire at comparable rates; only one leaves the class.

    Without this the result would be consistent with "unlikely heralds disturb
    more", which is a different and uninteresting claim.
    """
    quadratic_low, quadratic_high = report["quadratic"]["probability_range"]
    quartic_low, quartic_high = report["quartic"]["probability_range"]

    assert quartic_low > 0.3 and quartic_high < 0.7
    assert quadratic_low < quartic_low and quadratic_high > quartic_high
    assert (report["quartic"]["least_defect"]
            / max(report["quadratic"]["worst_defect"], 1e-18)) > 1e10


@pytest.mark.parametrize("outcome", [1, -1])
def test_a_herald_returns_a_normalised_state_and_its_probability(setting, outcome):
    """The instrument itself, since every result above is read through it."""
    operators, prepared = setting
    herald = herald_parity(prepared, operators, (0, 3), outcome)

    assert 0.0 < herald["probability"] < 1.0
    assert np.linalg.norm(herald["state"]) == pytest.approx(1.0, abs=1e-12)
    assert herald["degree"] == 2


# --------------------------------------------------------------------------
# Weave and de-weave: a loop that is hardness-collapsed and state-resolving
# --------------------------------------------------------------------------

def test_de_weaving_in_reversed_order_closes_the_loop_exactly(setting):
    """The group inverse. 8.1e-16."""
    operators, _ = setting
    loop = weave_deweave(7, operators, reverse=True)
    assert np.linalg.norm(loop - np.eye(loop.shape[0])) < 1e-12


def test_de_weaving_in_the_same_order_does_not_close(setting):
    """Because the generators do not commute -- which is the whole of the braid.

    A trivial group would close either way and this measurement would be empty.
    """
    operators, _ = setting
    loop = weave_deweave(7, operators, reverse=False)
    assert np.linalg.norm(loop - np.eye(loop.shape[0])) > 1.0


def test_the_open_loop_does_real_work_that_no_hardness_instrument_sees(setting):
    """0.93 of a possible 2 on the state; machine zero on every hardness axis.

    `gaussian_defect` is an operator-level instrument and `wick_defect` a
    state-level one, and both read zero. The loop is hardness-COLLAPSED and
    state-RESOLVING -- the `movingframe` distinction appearing at the level of a
    physical process rather than a coordinate. De-weaving in the wrong order is
    real, physical, and undetectable by any measurement of hardness in this
    repository.
    """
    operators, prepared = setting
    loop = weave_deweave(7, operators, reverse=False)
    moved = loop @ prepared

    assert gaussian_defect(loop, operators) < 1e-12
    assert wick_defect(moved, operators) < 1e-12
    displacement = float(np.linalg.norm(moved - prepared))
    assert displacement > 0.5
    assert displacement < 2.0 + 1e-9

    closed = weave_deweave(7, operators, reverse=True) @ prepared
    assert float(np.linalg.norm(closed - prepared)) < 1e-12, (
        "the closing loop must leave the state alone, or the displacement above "
        "is not attributable to the ordering")


@pytest.mark.parametrize("indices", [(0, 3), (2, 5), (0, 1, 2, 3), (0, 2, 4, 6)])
def test_the_herald_observable_is_a_genuine_two_outcome_measurement(indices, setting):
    """The guard for the bug that produced this module's headline from nothing.

    A product of `k` distinct Majoranas is Hermitian only after multiplying by
    `i^(k(k-1)/2)`. An earlier version omitted that and symmetrised instead,
    which for `k = 2` annihilates the operator exactly: every projector became
    `I/2`, every herald fired with probability 0.25, and the "post-selected"
    state was the input. The finding survived the fix -- but for a round it was
    supported by a measurement of the identity.

    The Hermiticity assertion that was meant to catch it passed, because the zero
    matrix is Hermitian. So the guard is on the spectrum: the observable must
    square to the identity, which zero does not.
    """
    operators, prepared = setting
    plus = herald_parity(prepared, operators, indices, +1)
    minus = herald_parity(prepared, operators, indices, -1)

    assert plus["probability"] + minus["probability"] == pytest.approx(1.0, abs=1e-10)
    assert plus["probability"] != pytest.approx(0.25, abs=1e-9) or \
        minus["probability"] != pytest.approx(0.25, abs=1e-9), (
        "both outcomes at exactly 0.25 is the signature of the projector being "
        "I/2, which is what a vanishing observable produces")


def test_a_vanishing_observable_is_refused_rather_than_measured():
    """The refusal path, exercised directly.

    `herald_parity` rejects an odd number of modes outright, and rejects any
    operator whose spectrum is not +-1. Without this, a silently-zero observable
    reads as a successful measurement with probability 0.25.
    """
    operators = majorana_operators(3)
    state = vacuum(3)

    with pytest.raises(ValueError, match="even number"):
        herald_parity(state, operators, (0, 1, 2))

    class _Zeroed(list):
        pass

    zeroed = _Zeroed(operators)
    zeroed[1] = np.zeros_like(operators[1])
    with pytest.raises(ValueError, match="square to the identity"):
        herald_parity(state, zeroed, (0, 1))


# --------------------------------------------------------------------------
# The storm: many heralds, adaptive, and where they actually take the state
# --------------------------------------------------------------------------

def test_the_field_predicts_every_particle_event(setting):
    """`p(+1) = (1 + Gamma_ab)/2`, over all 28 mode pairs, to 2.2e-16.

    The duality closing. Every herald outcome's probability is one entry of the
    covariance matrix, so the entire storm -- outcomes and all -- is samplable
    from `O(n^2)` numbers and the record it produces carries no more than they
    do. There is no magic in what we collect either.
    """
    from aionq.pond import outcome_probability

    operators, prepared = setting
    gamma = covariance(prepared, operators)
    modes = len(operators)

    worst = 0.0
    for first in range(modes):
        for second in range(first + 1, modes):
            exact = herald_parity(prepared, operators, (first, second), +1)
            worst = max(worst, abs(exact["probability"]
                                   - outcome_probability(gamma, first, second, +1)))
    assert worst < 1e-12


@pytest.mark.parametrize("adaptive", [False, True])
def test_two_hundred_heralds_never_leave_the_class(adaptive):
    """Adaptive or not, the Wick defect stays at machine zero throughout.

    Adaptivity -- choosing the next measurement from the record of outcomes so
    far -- is the one route by which a disturbance could compound rather than
    reset. It does not. Sampling is honest rather than post-selected: outcomes
    are drawn at the probability the field predicts, so this is a trajectory the
    experiment would actually produce.
    """
    from aionq.pond import storm

    result = storm(qubits=6, steps=200, adaptive=adaptive)
    assert result["heralds"] == 200
    assert result["worst_wick_defect"] < 1e-12
    assert all(row["wick_defect"] < 1e-12 for row in result["trajectory"])


def test_the_storm_is_a_sink_toward_stabiliser_states():
    """Entropy converges to integers; support to powers of two.

    Under Jordan-Wigner `i c_a c_b` is a Pauli string, so a storm of quadratic
    parity heralds is repeated Pauli measurement -- which drives any state into
    the stabiliser set. The signature is that the entropy stops being a generic
    real number: 1.0000 and 2.0000 exactly, on a state that started at 1.7168.
    """
    from aionq.pond import storm

    result = storm(qubits=6, steps=200)
    late = [row for row in result["trajectory"] if row["heralds"] >= 20]

    assert late, "no late trajectory points to test"
    for row in late:
        assert abs(row["entropy"] - round(row["entropy"])) < 1e-6, (
            f"entropy {row['entropy']} is not an integer, so the state is not "
            "in the stabiliser set and this identification is wrong")
        support = row["support"]
        assert support & (support - 1) == 0, f"support {support} is not a power of two"

    assert result["trajectory"][0]["entropy"] != pytest.approx(
        round(result["trajectory"][0]["entropy"]), abs=1e-6), (
        "the state must START at a non-integer entropy, or the sink is not a sink")


def test_a_post_storm_state_can_still_receive_magic():
    """Six seeds at `n = 6`, every one taken to Wick defect 1.0 by some quartic.

    A first version of this measurement ran a single seed at `n = 4` and
    concluded that the storm destroys the capacity to receive magic. That was
    wrong twice: wrong seed, and wrong size. Across twelve seeds at `n = 4` only
    three of twelve exceed 0.5; across six seeds at `n = 6` all six do, at
    exactly 1.0. The size dependence is about how OFTEN, not about whether.
    """
    from aionq.pond import storm

    best = []
    for seed in range(6):
        result = storm(qubits=6, steps=200, seed=seed)
        operators, state = result["operators"], result["final_state"]
        live = []
        for quad in ((0, 1, 2, 3), (0, 2, 4, 6), (1, 3, 5, 7), (2, 3, 4, 5)):
            herald = herald_parity(state, operators, quad, +1)
            if 1e-6 < herald["probability"] < 1 - 1e-6:
                live.append(herald["wick_defect"])
        assert len(live) >= 3, f"seed {seed}: too few non-vacuous quartic heralds"
        best.append(max(live))

    assert all(value > 0.5 for value in best)


def test_a_vacuous_herald_is_detected_rather_than_reported_as_a_null():
    """The control failure that would have supported a false null.

    A herald on a state that is already an eigenvector of the observable fires
    at probability 0 or 1 and changes nothing, so its Wick defect reads 1e-16 --
    which, reported without the probability, is "even a quartic herald cannot
    disturb this state". The vacuum is such a case by construction: it is an
    eigenvector of `c_0 c_1 c_2 c_3`, at `p = 1.000000` exactly, at both sizes.

    The tell is the probability, and it is asserted here on a deliberately
    constructed case rather than on a storm trajectory -- because the trajectory
    version turned out to be one seed in thirty-six, which is itself the reason
    this test exists.
    """
    for qubits in (4, 6):
        operators = majorana_operators(qubits)
        herald = herald_parity(vacuum(qubits), operators, (0, 1, 2, 3), +1)
        assert herald["probability"] == pytest.approx(1.0, abs=1e-12)
        assert herald["wick_defect"] < 1e-12

        # ...while a herald that genuinely fires on the same state does not
        # have a degenerate probability, which is what makes the tell a tell.
        live = herald_parity(vacuum(qubits), operators, (0, 2, 4, 6), +1)
        assert 0.01 < live["probability"] < 0.99


# --------------------------------------------------------------------------
# The testbed as a field: 16 Majorana modes = |GF(16)|
# --------------------------------------------------------------------------

def test_the_ladder_rungs_give_genuinely_different_herald_families():
    """T2 is a perfect matching of 8; T16 and AGL give all 120.

    Without this the rung comparison below would be comparing sample sizes
    rather than structures.
    """
    from aionq.pond import rung_pairs

    sizes = {rung: len(rung_pairs(rung))
             for rung in ("T2", "T4", "T16", "M3", "M15", "FROBENIUS", "AGL")}
    assert sizes == {"T2": 8, "T4": 24, "T16": 120, "M3": 15,
                     "M15": 105, "FROBENIUS": 19, "AGL": 120}
    # T2 is x -> x + 1, a fixed-point-free involution, so its pairs partition
    # the 16 modes exactly -- which is what makes it the extreme case.
    covered = [mode for pair in rung_pairs("T2") for mode in pair]
    assert sorted(covered) == list(range(16))


def test_the_field_singles_out_one_hundred_forty_quartic_index_sets():
    """The 2-flats of AG(4,2): quadruples whose GF(16) labels XOR to zero."""
    from aionq.pond import two_flats

    flats = two_flats()
    assert len(flats) == 140
    assert all(a ^ b ^ c ^ d == 0 for a, b, c, d in flats)
    from math import comb
    assert comb(16, 4) - len(flats) == 1680


@pytest.mark.parametrize("rung,entropy,support", [
    ("T2", 0.0, 1), ("M3", 1.0, 128), ("AGL", 2.0, 64),
])
def test_the_sink_depends_on_the_rung_and_not_on_the_number_of_pairs(
        rung, entropy, support):
    """The same state, the same 200 heralds, three different destinations.

    `M3` has fifteen pairs and leaves the state at entropy 1 with support 128 --
    LESS collapsed than `FROBENIUS`, which has nineteen and drives it to entropy
    0. `T2`, the perfect matching, collapses it to a single basis state. So the
    algebraic structure of the herald family decides the sink, not its size.

    This is the measurement that only exists because the mode set carries the
    field: with 2n = 16 = |GF(16)| the herald family is a coordinate on a known
    group rather than a nuisance parameter.
    """
    from aionq.pond import ladder_storm

    result = ladder_storm(rung)
    assert result["entropy"] == pytest.approx(entropy, abs=1e-6)
    assert result["support"] == support
    assert result["wick_defect"] < 1e-12, (
        "every rung must stay Gaussian; only where it stops differs")


def test_more_pairs_does_not_mean_more_collapse():
    """The non-monotonicity, asserted directly rather than left to the table."""
    from aionq.pond import ladder_storm

    frobenius = ladder_storm("FROBENIUS")
    multiplicative = ladder_storm("M3")

    assert frobenius["pairs"] > multiplicative["pairs"]
    assert frobenius["entropy"] < multiplicative["entropy"]
    assert frobenius["support"] < multiplicative["support"]


# --------------------------------------------------------------------------
# The limit, and the moments at which the symmetry breaks
# --------------------------------------------------------------------------

def test_there_is_no_omni_rung_because_the_ladder_saturates():
    """The union of all seven rungs is 120 pairs -- exactly what T16 alone gives.

    Translations by the 15 nonzero field elements already realise every unordered
    pair `{x, x+t}`, so `T16`, `AGL` and any union of rungs are the same herald
    family. An "all at once" storm is not a new object, and the distinctions that
    matter live in the SMALL rungs.
    """
    from aionq.pond import ladder_saturates

    report = ladder_saturates()
    assert report["union_size"] == 120
    assert set(report["saturating_rungs"]) == {"T16", "AGL"}
    assert report["subfield_tower"], "T2 < T4 < T16 must nest as pair sets"
    assert report["sizes"]["T2"] == 8 and report["sizes"]["M3"] == 15


@pytest.mark.parametrize("rung", ["T2", "T4", "FROBENIUS"])
def test_a_collapsing_rung_breaks_seven_times_and_then_freezes(rung):
    """Seven symmetry-breaking moves, all early, then a fixed point.

    R1M reported only endpoints, and endpoints hide the crossing. Traced step by
    step, the collapsing rungs move exactly seven times -- inside the first ten
    heralds for `T2` and `T4`, the first twenty-five for `FROBENIUS` -- and are
    then frozen for the remaining 125 steps.
    """
    from aionq.pond import collapse_trajectory

    result = collapse_trajectory(rung)
    assert result["break_count"] == 7
    assert result["last_break"] <= 25
    assert result["final_entropy"] == pytest.approx(0.0, abs=1e-9)
    assert all(abs(value) < 1e-9 for value in result["entropies"][30:])


@pytest.mark.parametrize("rung", ["T16", "M3", "M15", "AGL"])
def test_a_non_collapsing_rung_never_stops_moving(rung):
    """Forty or more breaks, spread throughout, and no fixed point.

    The dichotomy has nothing between it: seven breaks or forty-plus. Asserting
    both halves is what makes it a dichotomy rather than an observation about
    three rungs.
    """
    from aionq.pond import collapse_trajectory

    result = collapse_trajectory(rung)
    assert result["break_count"] >= 40
    assert result["last_break"] > 100


@pytest.mark.parametrize("rung,collapses", [
    ("T2", True), ("T4", True), ("FROBENIUS", True), ("T16", False),
])
def test_the_break_in_the_field_tower_is_between_gf4_and_gf16(rung, collapses):
    """Translation by a PROPER subfield collapses the state; by the whole field not.

    `T2`, `T4` and `T16` are translation by `GF(2)`, `GF(4)` and `GF(16)` -- the
    subfield tower itself. Over five seeds, the proper subfields reach entropy 0
    every time and the full field never does (3.0, 1.0, 1.0, 2.0, 1.0).

    This is the seed-robust core of R1M. That round reported a single-draw table
    of endpoint values; the values fluctuate seed to seed and only the
    collapse/no-collapse dichotomy survives.
    """
    from aionq.pond import collapse_trajectory

    finals = [collapse_trajectory(rung, seed=seed)["final_entropy"]
              for seed in range(5)]
    if collapses:
        assert all(abs(value) < 1e-9 for value in finals)
    else:
        assert all(abs(value) > 0.5 for value in finals)


def test_the_state_level_escape_from_the_class_is_first_order():
    """Escape order 1.0000 in every quartic direction, 2-flat or generic.

    §8.7 measured first-order escape at the OPERATOR level. This is the same
    question at the STATE level, and it gives the same answer: the Gaussian class
    is transverse in every quartic direction tested, and the field-structured
    2-flats have no different escape rate from generic quadruples.

    So the 2-flat effect R1M recorded is about where the state ENDS UP after a
    collapse, not about how the boundary is crossed.
    """
    import math
    from itertools import combinations

    from aionq.pond import two_flats

    operators = majorana_operators(8)
    modes = 16
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    prepared = expm(1j * (hamiltonian + hamiltonian.conj().T) / 2.0) @ vacuum(8)

    generic = [q for q in combinations(range(16), 4)
               if q[0] ^ q[1] ^ q[2] ^ q[3] != 0]
    scales = np.geomspace(1e-5, 1e-2, 6)

    picker = np.random.default_rng(3)
    for pool in (list(two_flats()), generic):
        for index in picker.choice(len(pool), 3, replace=False):
            quad = pool[int(index)]
            product = np.eye(2 ** 8, dtype=complex)
            for mode in quad:
                product = product @ operators[mode]
            product = (product + product.conj().T) / 2.0
            values = []
            for scale in scales:
                moved = expm(1j * scale * product) @ prepared
                values.append(wick_defect(moved / np.linalg.norm(moved), operators))
            slope = np.polyfit(np.log(scales),
                               np.log(np.maximum(values, 1e-300)), 1)[0]
            assert slope == pytest.approx(1.0, abs=0.05)


# --------------------------------------------------------------------------
# The continuum: strength as an infinitesimal, closure as the real variable
# --------------------------------------------------------------------------

@pytest.mark.parametrize("fraction", [0.0, 0.25, 0.5, 0.8, 0.999])
def test_a_weak_herald_is_still_exactly_gaussian(fraction):
    """`M = i c_a c_b` has `M^2 = 1`, so `a + bM` is proportional to `exp(tM)`.

    That is the exponential of a quadratic, hence a (non-unitary) Gaussian
    operation -- so a PARTIAL parity measurement cannot leave the class either,
    at any strength. Breathing keeps the pond flat.
    """
    import math

    from aionq.pond import weak_herald

    operators = majorana_operators(4)
    modes = 8
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    prepared = expm(1j * (hamiltonian + hamiltonian.conj().T) / 2.0) @ vacuum(4)

    alpha = fraction * math.pi / 4
    for outcome in (+1, -1):
        moved, probability = weak_herald(prepared, operators, 0, 3, alpha, outcome)
        if probability > 1e-12:
            assert wick_defect(moved, operators) < 1e-12


def test_the_break_count_is_continuous_in_the_measurement_strength():
    """R1N's "seven or forty-plus, nothing between" was one end of a family.

    At `T2`: 7 breaks projective, then 37, 63, 148 as the herald weakens. The
    dichotomy was measured at a single point of a one-parameter family and the
    family fills the gap.
    """
    import math

    from aionq.pond import breathing_trajectory, rung_pairs

    pairs = rung_pairs("T2")
    counts = [breathing_trajectory(pairs, fraction * math.pi / 4)["break_count"]
              for fraction in (0.0, 0.2, 0.4, 0.6)]

    assert counts[0] == 7
    assert all(left < right for left, right in zip(counts, counts[1:]))
    assert counts[-1] > 100


def test_weak_measurement_gives_an_asymptotic_approach_not_a_slower_arrival():
    """The apparent threshold in strength is the step budget -- and the fix to
    that reading is itself a correction.

    At `alpha/(pi/4) = 0.8` the entropy reads 8.4e-1 after 150 heralds, 6.8e-3
    after 300, 2.2e-6 after 600, 1.5e-8 after 1000. It is not collapsing more
    slowly to zero; it is decaying toward zero **asymptotically and never
    arriving**, roughly two and a half orders of magnitude per 300 steps.

    The projective case is different in KIND, not in rate: it reaches exactly
    0 in seven steps and freezes. So the `alpha -> 0` limit is a decay whose
    rate diverges until the process becomes finite.

    A first reading called 600 steps "0.0000" -- that was 2.18e-06 shown at four
    decimals, and it would have been recorded as an exact collapse.
    """
    import math

    from aionq.pond import breathing_trajectory, rung_pairs

    pairs = rung_pairs("T2")
    alpha = 0.8 * math.pi / 4

    finals = [breathing_trajectory(pairs, alpha, steps=steps)["final_entropy"]
              for steps in (150, 300, 600, 1000)]

    assert all(left > right for left, right in zip(finals, finals[1:]))
    assert finals[0] > 0.5
    assert finals[-1] < 1e-6
    assert finals[-1] > 0.0, (
        "a weak herald approaches zero asymptotically; exactly zero would make "
        "it projective, which is the case this test contrasts against")

    projective = breathing_trajectory(pairs, 0.0, steps=150)
    assert projective["final_entropy"] == pytest.approx(0.0, abs=1e-12)
    assert projective["last_break"] <= 10


def test_contaminating_a_closed_pair_set_destroys_the_collapse_at_once():
    """Six extra pairs added to T2's eight, and the collapse is gone.

    There is no gradual threshold in the pair count: `T2` with 8 pairs collapses
    to 0, and `T2` plus six arbitrary pairs -- 14 in all -- does not collapse at
    all. The property is CLOSURE of the family under a subgroup, not its size,
    and closure is destroyed by any contamination.
    """
    from aionq.pond import breathing_trajectory, rung_pairs

    base = list(rung_pairs("T2"))
    everything = [(a, b) for a in range(16) for b in range(a + 1, 16)]
    rest = [pair for pair in everything if pair not in set(base)]
    extra = [rest[index] for index in
             np.random.default_rng(11).permutation(len(rest))[:6]]

    assert breathing_trajectory(base)["final_entropy"] == pytest.approx(0.0, abs=1e-9)
    assert breathing_trajectory(base + extra)["final_entropy"] > 0.5


@pytest.mark.parametrize("rung", ["T2", "T4", "FROBENIUS", "M15"])
def test_the_orthogonal_clone_of_a_rung_never_collapses(rung):
    """Every complement fails, including the one with fifteen pairs.

    `M15^c` has 15 pairs -- the same count as `M3`, twice `T2`'s 8 -- and does
    not collapse where `T2` does. So collapse is not about how many pairs a
    family has. It is about the family being closed under a subgroup, and a
    complement is exactly the thing that is not.
    """
    from aionq.pond import breathing_trajectory, complement_pairs

    result = breathing_trajectory(complement_pairs(rung))
    assert result["final_entropy"] > 0.5
    if rung == "M15":
        assert len(complement_pairs(rung)) == 15
