"""R1X gates: the range-partition carrier, checked where the answer is known.

Frozen in `manifests/qsigma_r1x_spectral_measure_preregistration.json` at
1b55ce0, before this file or `src/aionq/lebesgue.py` existed.
"""

import numpy as np
import pytest

from aionq.gf_frames import SUBGROUP_LADDER
from aionq.lebesgue import (ladder_spectral_sweep, lebesgue_weight,
                            measure_entropy,
                            merged_by_entropy_separated_by_defect,
                            reconstruction_defect, spectral_measure,
                            wasserstein1)
from aionq.supercable import (covariance_entropy, covariance_storm,
                              vacuum_covariance, _orthogonal_from_generator)


def random_gaussian(qubits, seed):
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(2 * qubits, 2 * qubits))
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    return rotation @ vacuum_covariance(qubits) @ rotation.T


# -- G1 ---------------------------------------------------------------------

@pytest.mark.parametrize("qubits", [4, 6, 8])
def test_g1_the_entropy_is_the_integral_against_this_measure(qubits):
    """The old instrument and the new one, on the old one's whole domain.

    R1X's first gate. If these disagree, `mu_A` is not the measure
    `covariance_entropy` integrates and nothing else in the round is read. Two
    code paths for one quantity is deliberate: a single path cannot be checked
    against itself.
    """
    gamma = random_gaussian(qubits, seed=qubits)
    for split in range(1, qubits):
        left = list(range(2 * split))
        assert measure_entropy(spectral_measure(gamma, left)) == pytest.approx(
            covariance_entropy(gamma, left), abs=1e-12)


# -- G2 ---------------------------------------------------------------------

def test_g2_the_vacuum_is_a_point_mass_at_purity_on_whole_pairs():
    gamma = vacuum_covariance(4)
    for split in range(1, 4):
        atoms = spectral_measure(gamma, list(range(2 * split)))
        assert atoms == pytest.approx(np.ones(split), abs=1e-12)
        assert lebesgue_weight(atoms) == 1.0
        assert measure_entropy(atoms) == pytest.approx(0.0, abs=1e-12)


def test_g2_two_modes_from_different_pairs_are_a_point_mass_at_zero():
    """The case a careless reading of "the vacuum is pure" gets backwards.

    Modes 0 and 2 belong to different Majorana pairs. The vacuum covariance has
    nothing linking them, so the restricted block is ZERO and `mu_A = delta_0`
    -- one full bit, maximally mixed, in a state that is globally pure. A
    subset of a pure state is not a pure subset unless the subset closes on its
    own pairs, and that is the whole reason `split` is counted in pairs
    throughout this line.
    """
    atoms = spectral_measure(vacuum_covariance(4), [0, 2])
    assert atoms == pytest.approx(np.zeros(1), abs=1e-12)
    assert lebesgue_weight(atoms) == 0.0
    assert measure_entropy(atoms) == pytest.approx(1.0, abs=1e-12)


# -- G3 ---------------------------------------------------------------------

def test_g3_the_measure_does_not_move_under_relabelling_inside_the_block():
    """The attack that killed R1Q's rule, run against the new carrier.

    Known in advance to pass: a permutation is orthogonal and a similarity does
    not move a spectrum. It is a CONTROL and the manifest forbids reporting it
    as a finding. Exhibited rather than asserted because R1Q's statistic was
    stated in mode indices and nobody had run this against it.
    """
    gamma = random_gaussian(6, seed=3)
    left = list(range(6))
    reference = spectral_measure(gamma, left)

    rng = np.random.default_rng(19)
    for _ in range(8):
        order = rng.permutation(12)
        permuted = gamma[np.ix_(order, order)]
        relabelled = [int(np.where(order == mode)[0][0]) for mode in left]
        assert spectral_measure(permuted, relabelled) == pytest.approx(
            reference, abs=1e-12)


def test_g3_orthogonal_mixing_inside_the_block_moves_nothing_either():
    gamma = random_gaussian(6, seed=5)
    left = list(range(6))
    reference = spectral_measure(gamma, left)

    rng = np.random.default_rng(23)
    raw = rng.normal(size=(6, 6))
    inner = _orthogonal_from_generator((raw - raw.T) / 2.0)
    mixed = np.array(gamma)
    rotation = np.eye(12)
    rotation[np.ix_(left, left)] = inner
    mixed = rotation @ mixed @ rotation.T

    assert spectral_measure(mixed, left) == pytest.approx(reference, abs=1e-12)


# -- the defect functional --------------------------------------------------

def test_w1_refuses_unequal_atom_counts_rather_than_guessing():
    with pytest.raises(ValueError, match="equal-atom-count"):
        wasserstein1([0.1, 0.2], [0.1, 0.2, 0.3])


def test_the_parts_must_actually_partition_the_block():
    gamma = random_gaussian(4, seed=1)
    with pytest.raises(ValueError, match="partition"):
        reconstruction_defect(gamma, [0, 1, 2, 3], [[0, 1], [2, 3], [4, 5]])


def test_the_defect_is_zero_when_the_parts_carry_no_entanglement():
    """Reconstruction holds exactly where the block factorises, and only there.

    The vacuum's pairs are independent, so the whole spectrum IS the union of
    the parts' spectra and `D` is 0. Rotate the state and it stops being 0.
    That second half matters: a defect that is zero everywhere measures
    nothing, and R1S's ratio was tested only where it was interesting.
    """
    parts = [[0, 1], [2, 3]]
    clean = reconstruction_defect(vacuum_covariance(2), [0, 1, 2, 3], parts)
    assert clean["defect"] == pytest.approx(0.0, abs=1e-12)
    assert clean["entropy_gap"] == pytest.approx(0.0, abs=1e-12)
    assert clean["agrees_with_supercable"]

    entangled = reconstruction_defect(random_gaussian(2, seed=7), [0, 1, 2, 3], parts)
    assert entangled["defect"] > 1e-6


def test_the_defect_is_bounded_and_never_reverses_sign():
    """The two properties R1S's interaction ratio did not have.

    That ratio was unbounded once its Cauchy-Schwarz baseline turned out to be
    unearned, and it reversed sign at M3, which is what killed the directional
    reading as well as the additive one. `D` is a distance: in [0, 1] by
    construction, with no sign to reverse.
    """
    for seed in range(12):
        gamma = random_gaussian(4, seed=100 + seed)
        result = reconstruction_defect(gamma, list(range(8)),
                                       [[0, 1, 2, 3], [4, 5, 6, 7]])
        assert 0.0 <= result["defect"] <= 1.0
        assert result["agrees_with_supercable"]


def test_the_defect_does_not_move_under_relabelling_but_the_cut_count_does():
    """P2. The carrier is immune to the artifact class that killed R1Q's rule.

    Same permutation, two statistics: the spectral defect is unchanged to 1e-12
    and the domain-side crossing count is not. The point is not that a spectrum
    is permutation-invariant -- it is that the quantity R1Q stated its rule in
    was not, and this one is, at no cost.
    """
    from aionq.pond import cut_crossing_pairs, rung_pairs

    gamma = random_gaussian(4, seed=11)
    modes = list(range(8))
    parts = [[0, 1, 2, 3], [4, 5, 6, 7]]
    reference = reconstruction_defect(gamma, modes, parts)

    rng = np.random.default_rng(31)
    moved_defect = []
    for _ in range(6):
        order = rng.permutation(8)
        permuted = gamma[np.ix_(order, order)]
        relabelled = [[int(np.where(order == mode)[0][0]) for mode in part]
                      for part in parts]
        pooled = sorted(m for part in relabelled for m in part)
        result = reconstruction_defect(permuted, pooled, relabelled)
        moved_defect.append(abs(result["defect"] - reference["defect"]))
    assert max(moved_defect) < 1e-12

    # The domain-side statistic, under the same kind of relabelling. R1Q stated
    # its rule in this quantity; relabelling the modes moves it, and that is the
    # whole content of the labelling-artifact finding.
    moved_counts = set()
    for rung in SUBGROUP_LADDER:
        pairs = rung_pairs(rung)
        before = len(cut_crossing_pairs(pairs, qubits=8, split=2))
        for _ in range(8):
            order = rng.permutation(16)
            shuffled = tuple((int(order[a]), int(order[b])) for a, b in pairs)
            after = len(cut_crossing_pairs(shuffled, qubits=8, split=2))
            moved_counts.add(after - before)
    assert moved_counts != {0}, (
        "the domain statistic must actually move, or there is nothing to contrast")


# -- P3, and the budget parameter the protocol left free ---------------------

def test_p3_does_not_survive_a_change_of_step_budget():
    """R1X's one falsifiable prediction, and it is not established.

    P3 asked for a pair of ladder cells, at matched seed, that the entropy
    scalar calls the same and the measure calls different: |Delta S| < 0.05 bits
    and |Delta D| > 0.10, both frozen in the manifest before any of this code
    existed. At 300 steps there are two such pairs, both at seed 7 and both
    involving M15, so a single state produces the whole effect. At 900 steps
    there are none: every matched-seed pair that shares an entropy shares a
    defect too.

    THE PROTOCOL DEFECT THAT MADE THIS POSSIBLE. The preregistration froze the
    two thresholds and then wrote "fixed step budget" without fixing it. A free
    parameter inside a frozen protocol is a threshold in disguise -- 300 and 900
    answer the same preregistered question in opposite directions, and either
    could have been reported alone. R1O already recorded a budget artifact in
    this line, which is the only reason both budgets were run.

    This test pins the negative. If a later change makes P3 hold at both
    budgets, that is a real result and this test should fail loudly rather than
    let the round quietly turn positive.
    """
    short = merged_by_entropy_separated_by_defect(ladder_spectral_sweep(steps=300))
    long = merged_by_entropy_separated_by_defect(ladder_spectral_sweep(steps=900))

    assert short["entropy_window"] == 0.05 and short["defect_floor"] == 0.10, \
        "the thresholds are frozen by the manifest; a change here voids the round"
    assert short["pairs_examined"] == 63 and long["pairs_examined"] == 63

    assert short["p3_holds"], "the 300-step reading is part of the record"
    assert len(short["hits"]) == 2
    assert {hit["seed"] for hit in short["hits"]} == {7}
    assert all("M15" in hit["rungs"] for hit in short["hits"])

    assert not long["p3_holds"], (
        "P3 was recorded as budget-dependent and NOT established; if it now "
        "holds at 900 steps the finding manifest is stale, not this test")


def test_every_swept_row_still_agrees_with_the_old_instrument():
    """G1 again, on the rows actually reported rather than on random states.

    The gate is cheap and the failure it guards is expensive: a new instrument
    that disagrees with the old one on the old one's domain is a bug, and this
    repository has twice mistaken an instrument artifact for a finding.
    """
    rows = ladder_spectral_sweep(steps=300)
    assert len(rows) == 21
    assert all(row["agrees_with_supercable"] for row in rows)
    assert all(0.0 <= row["defect"] <= 1.0 for row in rows)
    assert all(0.0 <= row["weight"] <= 1.0 for row in rows)


def test_T16_and_AGL_are_the_same_cell_and_the_sweep_shows_it():
    """A consistency check, not a discovery: R1N already recorded this.

    Translations by the fifteen nonzero field elements already realise every
    unordered pair {x, x+t}, so T16 and AGL are the same herald family and every
    comparison between them across this line has been a cell against itself. If
    the sweep ever separated them, the sweep would be wrong.
    """
    rows = {(row["rung"], row["seed"]): row for row in ladder_spectral_sweep(steps=300)}
    for seed in (7, 13, 29):
        left, right = rows[("T16", seed)], rows[("AGL", seed)]
        assert left["entropy"] == pytest.approx(right["entropy"], abs=1e-12)
        assert left["defect"] == pytest.approx(right["defect"], abs=1e-12)
        assert left["weight"] == right["weight"]


def test_the_storm_flattens_the_ellipsoid_before_R1X_ever_looked():
    """R1X measured a body the dynamics had already crushed flat.

    A Gaussian covariance restricted to a mode subset IS an ellipsoid and the
    symplectic values ARE its semi-axes. The prepared state's are
    (0.044, 0.513, 0.701, 0.983) -- a genuine non-degenerate four-dimensional
    hyperellipsoid. The projective herald storm destroys it: by step 100 only
    M3 retains a single intermediate axis and every other cell is at 0 or 1
    throughout.

    R1X sampled at 300 and 900 steps. A measure supported on {0,1} has ONE
    degree of freedom, so it could not out-inform the scalar it was built to
    beat -- for six of seven cells, at any budget. Its P3 was structurally
    unable to succeed and the round never checked that the body still had a
    shape.
    """
    from aionq.gf_frames import SUBGROUP_LADDER
    from aionq.pond import rung_pairs
    from aionq.supercable import covariance_storm

    gamma = random_gaussian(8, seed=0)
    left = list(range(8))

    prepared_axes = spectral_measure(gamma, left)
    intermediate = lambda axes: int(((axes > 1e-9) & (axes < 1 - 1e-9)).sum())
    assert intermediate(prepared_axes) == 4, "the prepared body must have shape"

    survivors = set()
    for rung in SUBGROUP_LADDER:
        storm = covariance_storm(rung_pairs(rung), 8, steps=100, seed=7,
                                 split=4, prepared=gamma)
        if intermediate(spectral_measure(storm["covariance"], left)):
            survivors.add(rung)
    assert survivors == {"M3"}, (
        f"by step 100 only M3 should retain an intermediate axis; got {survivors}")
