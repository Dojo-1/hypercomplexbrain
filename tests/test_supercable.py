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
    """Every step of every trajectory, not just where they end up.

    The frozen gate asks for final entropy, and the first version of this test
    compared only that -- while its own docstring said "whole trajectories".
    Two different entropy paths can land on the same endpoint and pass. GPT
    caught the overstatement on review; the assertion is now over all 151 points
    of each trajectory, which strengthens the check without touching the
    preregistered acceptance criterion (final entropy under 1e-9 is asserted
    separately below and is unchanged).

    Four rungs at two splits, 150 heralds each. It reproduces R1R's refuting cell
    exactly -- `M3` at split 2 gives 0.983691 in both formalisms -- which is the
    strongest single check available, because that number is the one that killed
    a rule and nothing about it is round or expected.
    """
    qubits, _, _, gamma = prepared

    worst_final, worst_path = 0.0, 0.0
    for rung in ("T2", "T4", "FROBENIUS", "M3"):
        pairs = rung_pairs(rung)
        for split in (2, 4):
            exact = breathing_trajectory(pairs, steps=150, seed=7, split=split)
            fast = covariance_storm(pairs, qubits, steps=150, seed=7, split=split,
                                    prepared=gamma)
            worst_final = max(worst_final,
                              abs(exact["final_entropy"] - fast["final_entropy"]))

            left, right = np.asarray(exact["entropies"]), np.asarray(fast["entropies"])
            assert left.shape == right.shape == (151,)
            worst_path = max(worst_path, float(np.abs(left - right).max()))

    assert worst_final < 1e-9, "the preregistered criterion, unchanged"
    assert worst_path < 1e-9, "and every intermediate point as well"

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


# --------------------------------------------------------------------------
# The reconstructed cap decomposition, after GPT's review
# --------------------------------------------------------------------------

def test_the_cap_decomposition_is_a_partition_at_matched_dose(prepared):
    """One draw, partitioned -- not several runs compared.

    The frozen protocol compared a storm on `F` against storms on each `F_theta`
    "at the same step budget and seed". The walker draws uniformly from whatever
    family it is handed, so a cap received about `steps * |F_theta| / |F|`
    heralds inside the union run and `steps` when run alone. For a 120-pair rung
    against an 8-pair cap that is a fifteenfold dose mismatch, and it would have
    made the ratio meaningless independently of the Cauchy-Schwarz question.

    Materialising the sequence once and partitioning it fixes both: the cap
    sub-sequences are disjoint, their sizes sum to the whole, and their union IS
    the whole sequence. That is what makes a cap-level reconstruction even
    askable.
    """
    from aionq.supercable import additivity_defect, herald_sequence

    qubits, _, _, gamma = prepared
    pairs = rung_pairs("T4")
    caps = _orbit_caps("T4")

    sequence = herald_sequence(pairs, steps=150, seed=7)
    assert len(sequence) == 150
    assert set(map(tuple, map(sorted, sequence))) <= set(pairs)

    report = additivity_defect(pairs, caps, qubits, gamma, steps=150, seed=7, split=4)

    assert report["dose_is_matched"], "cap sub-sequences must partition the whole"
    assert sum(report["heralds_kept_per_cap"]) == report["heralds_kept_whole"] == 150
    assert report["caps"] == len(caps)


def test_the_additivity_gate_decides_what_the_ratio_may_be_called(prepared):
    """Declared before measuring: additive licenses "decoupling", otherwise not.

    The rule is fixed in `manifests/qsigma_r1s_protocol_amendment_v1.json` --
    relative additivity defect below 0.1 earns the l2 baseline and the name
    "decoupling constant"; at or above it, the quantity is permanently an
    INTERACTION RATIO whose thresholds are operational conventions with no bound
    behind them.

    This test does not assert which way it goes. It asserts that the gate is
    computable, is reported with the numbers a reader needs to check it, and is
    not silently skipped -- the outcome is recorded in the round's finding
    manifest, not decided here.
    """
    from aionq.supercable import additivity_defect

    qubits, _, _, gamma = prepared
    report = additivity_defect(rung_pairs("T4"), _orbit_caps("T4"), qubits, gamma,
                               steps=150, seed=7, split=4)

    for key in ("delta_whole", "delta_per_cap", "additivity_defect",
                "additivity_defect_relative", "root_sum_square", "ratio"):
        assert key in report
    assert np.isfinite(report["additivity_defect"])
    assert report["additivity_defect"] >= 0.0


def test_the_additivity_gate_failed_and_the_name_was_dropped(prepared):
    """The declared rule fired against the framing. Recorded as a test, not prose.

    Protocol amendment 1 fixed the rule before the number existed: relative
    additivity defect under 0.1 earns the l2 baseline and the name "decoupling
    constant"; at or above it, the quantity is permanently an INTERACTION RATIO.

    Measured over 5 rungs and 3 seeds: median relative defect 0.109, maximum
    1.730. The gate failed.

    The load-bearing cell is `M3`, and it is not a matter of degree. On the same
    partitioned sequence at matched dose the whole family moves the entropy
    **up** by 0.507 while its caps together move it **down** by 0.370. A large
    defect could be a correction term; a sign reversal cannot be absorbed into an
    ADDITIVE reconstruction.

    The first version of this docstring went further and said "no inequality
    controlling the whole by an aggregate of its parts survives that, in l2 or
    any other norm". That is false, and the round's own table refutes it: norms
    discard sign, and any finite set of cells admits some `K`. The largest ratio
    measured is 2.957, so `K = 3` satisfies the l2 inequality on all fifteen
    cells. Caught by GPT on second review; retracted in amendment 2.
    """
    from aionq.supercable import additivity_defect

    qubits, _, _, gamma = prepared

    whole_up = additivity_defect(rung_pairs("M3"), _orbit_caps("M3"), qubits, gamma,
                                 steps=150, seed=7, split=4)
    assert whole_up["delta_whole"] > 0.0
    assert sum(whole_up["delta_per_cap"]) < 0.0, "the sign reversal that settles it"
    assert whole_up["additivity_defect_relative"] > 0.1

    worst = max(
        additivity_defect(rung_pairs(rung), _orbit_caps(rung), qubits, gamma,
                          steps=150, seed=seed, split=4)["additivity_defect_relative"]
        for rung in ("T2", "T4", "FROBENIUS", "M3") for seed in (7, 11))
    assert worst > 0.1, "the declared threshold, and it is exceeded"


def test_the_single_cap_row_is_a_tautology_and_is_labelled_one():
    """`M15` reads perfectly for a reason that is not evidence.

    Its orbits are `{0}` and the other fifteen elements, and the singleton
    carries no pairs, so all 105 land in ONE cap. Whole equals cap by
    construction: defect exactly 0.0, ratio exactly 1.0. Reported in the finding
    rather than dropped, because removing it would leave a cleaner table than the
    experiment supports.
    """
    assert len(_orbit_caps("M15")) == 1
    assert len(_orbit_caps("M15")[0]) == 105


def _orbit_caps(rung: str) -> tuple:
    """Caps = the orbits of the rung, as the round specifies.

    The orbits partition the sixteen modes, so assigning each pair to the orbit
    containing its SMALLER endpoint makes the caps disjoint and exhaustive over
    the family. Any pair-to-cap rule must be a partition or the reconstruction is
    not one, which is what
    `test_the_cap_decomposition_is_a_partition_at_matched_dose` checks.
    """
    from aionq.gf_frames import subgroup

    permutations = subgroup(rung)
    owner, seen = {}, set()
    for element in range(16):
        if element in seen:
            continue
        orbit = frozenset(permutation[element] for permutation in permutations)
        seen |= orbit
        for mode in orbit:
            owner[mode] = orbit

    caps = {}
    for pair in rung_pairs(rung):
        caps.setdefault(owner[min(pair)], []).append(pair)
    return tuple(tuple(group) for group in caps.values())


# --------------------------------------------------------------------------
# The verdict function, after the frozen one turned out not to be disjoint
# --------------------------------------------------------------------------

def test_the_frozen_verdict_thresholds_were_not_disjoint():
    """The blocking defect, kept as the arithmetic that shows it.

    R1S froze `C < 2` for LOW and `C > 0.7*sqrt(N)` for HIGH, calling the region
    between them indeterminate. The thresholds are ordered the wrong way whenever
    `0.7*sqrt(N) < 2`, i.e. `N < 8.163`, so there is no band -- there is an
    overlap, and a cell inside it satisfies **both** verdicts.

        N = 4  ->  HIGH above 1.400, LOW below 2.000  ->  overlap [1.400, 2.000]
        N = 5  ->  HIGH above 1.565                   ->  overlap [1.565, 2.000]
        N = 8  ->  HIGH above 1.980                   ->  overlap [1.980, 2.000]

    Eight of the fifteen cells the round had already produced land in it --
    `FROBENIUS` at all three seeds among them. More than half the data was
    unclassifiable by the rule that was supposed to classify it. Caught by GPT on
    second review.
    """
    import math

    for caps, low_edge in ((1, 0.700), (4, 1.400), (5, 1.565), (8, 1.980)):
        assert 0.7 * math.sqrt(caps) == pytest.approx(low_edge, abs=1e-3)
        assert 0.7 * math.sqrt(caps) < 2.0, "HIGH edge below the LOW edge = overlap"

    # a measured cell that satisfies both, with its real numbers
    ratio, caps = 1.648, 4                       # FROBENIUS, seed 7
    assert ratio > 0.7 * math.sqrt(caps) and ratio < 2.0


def test_the_replacement_verdict_is_exhaustive_and_mutually_exclusive():
    """Two outcomes, by construction, which is the whole point of replacing it.

    Paired by seed, `D_s = C_FLAT(s) - C_CURVED(s)`. SEPARATED requires every
    difference to share one sign **and** the median magnitude to reach the floor.
    NOT SEPARATED is everything else. There is no third verdict and no region
    where both apply.
    """
    from aionq.supercable import paired_separation

    clean = paired_separation([2.0, 2.1, 2.2], [1.0, 1.1, 1.2])
    assert clean["separated"] and clean["sign_consistent"]
    assert clean["direction"] == "flat_above_curved"

    mixed = paired_separation([2.0, 0.9, 2.2], [1.0, 1.1, 1.2])
    assert not mixed["separated"], "one sign flip is enough to refuse"
    assert mixed["direction"] == "mixed"

    small = paired_separation([1.2, 1.3, 1.4], [1.0, 1.1, 1.2])
    assert small["sign_consistent"] and not small["separated"], (
        "consistent direction below the floor is still not a separation")

    # exhaustive and exclusive: every input lands in exactly one verdict
    rng = np.random.default_rng(0)
    for _ in range(200):
        flat, curved = rng.normal(size=8), rng.normal(size=8)
        verdict = paired_separation(flat, curved)
        assert verdict["separated"] == (
            verdict["sign_consistent"]
            and verdict["median_absolute_difference"] >= verdict["floor"])


def test_the_verdict_function_refuses_unpaired_input():
    """FLAT and CURVED are matched by protocol; unpaired samples are a bug."""
    from aionq.supercable import paired_separation

    with pytest.raises(ValueError, match="paired"):
        paired_separation([1.0, 2.0, 3.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="paired"):
        paired_separation([], [])
