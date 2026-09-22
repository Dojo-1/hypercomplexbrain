"""R1Y gates, and the finding that its central prediction was untestable.

Frozen in `manifests/qsigma_r1y_hyperellipsoid_tessellation_preregistration.json`
at b91bd3b, before this file or `src/aionq/hyperellipsoid.py` existed.
"""

import numpy as np
import pytest

from aionq.hyperellipsoid import (orientation_defect, principal_angles,
                                  regular_tessellations_available,
                                  survival_time, williamson_frame)
from aionq.lebesgue import spectral_measure
from aionq.supercable import (_orthogonal_from_generator, vacuum_covariance)


def random_gaussian(qubits, seed):
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(2 * qubits, 2 * qubits))
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    return rotation @ vacuum_covariance(qubits) @ rotation.T


# -- G1 ---------------------------------------------------------------------

@pytest.mark.parametrize("qubits", [4, 6, 8])
def test_g1_the_recovered_frame_reconstructs_the_block(qubits):
    """If the frame is wrong every orientation number in the round is noise.

    The orthogonal real-Schur form is the skew-normal form of the antisymmetric
    covariance, so `frame @ canonical @ frame.T` returns the block exactly.
    """
    gamma = random_gaussian(qubits, seed=qubits)
    for split in range(1, qubits):
        modes = list(range(2 * split))
        _, _, canonical, block = williamson_frame(gamma, modes)
        from scipy.linalg import schur
        rebuilt_canonical, rebuilt_frame = schur(block, output="real")
        assert rebuilt_frame @ rebuilt_canonical @ rebuilt_frame.T == pytest.approx(
            block, abs=1e-10)


# -- G2 ---------------------------------------------------------------------

@pytest.mark.parametrize("qubits", [4, 6, 8])
def test_g2_the_semi_axes_agree_with_the_R1X_spectrum(qubits):
    """A third code path for a quantity two already compute.

    `covariance_entropy` reads the eigenvalues, `spectral_measure` sorts them
    into one-per-pair, and this reads them off the Schur blocks. A new
    instrument reproduces the old ones before any new number is recorded.
    """
    gamma = random_gaussian(qubits, seed=10 + qubits)
    for split in range(1, qubits):
        modes = list(range(2 * split))
        nus, _, _, _ = williamson_frame(gamma, modes)
        assert nus == pytest.approx(spectral_measure(gamma, modes), abs=1e-12)


# -- G3: invariant inside a tile, NOT across --------------------------------

def test_g3_orientation_is_invariant_inside_a_tile_and_moves_across_one():
    """Both halves asserted, on a block whose spectrum is actually separated.

    R1X's frame-invariance control was invariant under everything by
    construction and could not discriminate. An orientation statistic must be
    blind to how modes are written down INSIDE a tile and sensitive to which
    tile they are in, because moving a mode between tiles changes the geometry
    rather than the description of it.
    """
    # At most HALF the register, or rank forces the surplus axes to exactly 1:
    # a pure global state restricted to |A| modes can entangle at most
    # |complement|/2 pairs across the cut, and the rest of A is pure. A tied
    # spectrum makes the observable ill-posed, which the next test is about.
    gamma = random_gaussian(8, seed=0)
    modes = list(range(8))
    tiles = [(0, 1, 2, 3), (4, 5, 6, 7)]
    nus, _, _, _ = williamson_frame(gamma, modes)
    assert len(set(np.round(nus, 9))) == len(nus), "the gate needs separated axes"

    reference = orientation_defect(gamma, modes, tiles)["defect"]

    rng = np.random.default_rng(17)
    for _ in range(6):                   # permute WITHIN tiles only
        order = np.arange(8)
        for tile in tiles:
            block = np.array(tile)
            order[block] = rng.permutation(block)
        permuted = gamma[np.ix_(order, order)]
        assert orientation_defect(permuted, modes, tiles)["defect"] == pytest.approx(
            reference, abs=1e-12)

    crossed = []
    for _ in range(6):                   # swap modes BETWEEN tiles
        order = np.arange(8)
        a, b = int(rng.integers(0, 4)), int(rng.integers(4, 8))
        order[a], order[b] = order[b], order[a]
        permuted = gamma[np.ix_(order, order)]
        crossed.append(abs(orientation_defect(permuted, modes, tiles)["defect"]
                           - reference))
    assert max(crossed) > 1e-9, (
        "an orientation statistic blind to tile membership measures nothing")


def test_p3_is_ill_posed_because_degeneracy_destroys_the_frame():
    """R1Y's premise is backwards, and it is a theorem rather than a result.

    P3 asked whether orientation separates states AFTER all semi-axes have
    degenerated to {0,1} -- the idea being that lengths die and orientation
    survives. It is the other way round. A repeated semi-axis means a
    higher-dimensional eigenspace in which every orthonormal basis is equally
    canonical, so "the top k axes" names no particular subspace at all.

    Demonstrated on two states with IDENTICAL spectra: their top-2 subspaces
    differ by angles up to 1.2 radians. R1X measured 81 of 84 axes sitting at
    exactly 0 or 1, which is a two-value spectrum, so P3's entire target regime
    is the regime where its observable stops being a function of the state.

    The function refuses rather than returning a number, on the
    `exponent_orbits` precedent: a number that is not a function of the state
    is worse than none, because it looks like a measurement.
    """
    tied = np.zeros((8, 8))
    for k in range(4):                   # all four semi-axes equal to 1
        tied[2 * k, 2 * k + 1] = -1.0
        tied[2 * k + 1, 2 * k] = 1.0

    nus, frame_a, _, _ = williamson_frame(tied, list(range(8)))
    assert nus == pytest.approx(np.ones(4), abs=1e-12)

    rng = np.random.default_rng(1)
    raw = rng.normal(size=(8, 8))
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    copy = rotation @ tied @ rotation.T
    nus_copy, frame_b, _, _ = williamson_frame(copy, list(range(8)))

    assert nus_copy == pytest.approx(nus, abs=1e-12), "same spectrum"
    assert max(principal_angles(frame_a[:, -4:], frame_b[:, -4:])) > 1.0, (
        "same spectrum, different top-2 subspace: the frame is not determined")

    tiles = [(0, 1, 2, 3), (4, 5, 6, 7)]
    with pytest.raises(ValueError, match="not a function of the state"):
        orientation_defect(tied, list(range(8)), tiles, axes=2)


# -- the survival observable ------------------------------------------------

def test_survival_time_is_read_off_the_grid_and_m3_is_the_outlier():
    """The observable R1X should have had, on the frozen step grid.

    Every ladder cell starts with four intermediate semi-axes and loses them.
    M3 alone still has one at step 900; that is the coincidence which generated
    R1Y's P2, and it is a sample of one cell among three chartable ones.
    """
    from aionq.gf_frames import SUBGROUP_LADDER
    from aionq.pond import rung_pairs

    grid = (0, 1, 2, 3, 5, 10, 25, 50, 100, 300, 900)
    prepared = random_gaussian(8, seed=0)
    survivors = {}
    for rung in SUBGROUP_LADDER:
        result = survival_time(rung_pairs(rung), 8, prepared, grid, seed=7)
        assert result["intermediate_counts"][0] == 4, "the body must start with shape"
        survivors[rung] = result["survival_time"]

    assert survivors["M3"] == 900
    assert [r for r, s in survivors.items() if s == 900] == ["M3"]


# -- P2 was not testable ----------------------------------------------------

def test_p2_was_unsatisfiable_when_it_was_frozen():
    """R1Y required six regular tessellations from a group that contains four.

    P2 asked whether tessellation regularity predicts ellipsoid survival, on at
    least six regular and six irregular subgroups enumerated independently of
    the hypothesis. GammaL(1,16) has forty subgroups; FOUR give a regular
    non-transitive orbit partition -- three excluding the trivial one -- in
    three distinct tile shapes: 15x1, 5x3, 3x5.

    So P2 is NOT TESTED, by R1Y's own kill condition, and it was unsatisfiable
    from the moment the manifest was written. Same defect class as R1Z's
    unreachable BOUNDED -- a frozen condition no instance can meet -- and the
    FIRST one in this line caught before the round ran rather than after.
    """
    available = regular_tessellations_available()

    assert available["order"] == 60
    assert available["subgroups"] == 40
    assert available["regular"] == 4
    assert available["regular_nontrivial"] == 3
    assert available["irregular"] == 33
    assert available["regular"] < available["r1y_gate"]
    assert not available["gate_is_satisfiable"]
    assert available["regular_shapes"] == [
        (1,) * 15, (3, 3, 3, 3, 3), (5, 5, 5)]


def test_r1y_finding_preserves_the_failed_frozen_gate_and_correct_theorem():
    import json
    from pathlib import Path

    root = Path(__file__).parents[1]
    finding = json.loads((root / "manifests" /
        "qsigma_r1y_hyperellipsoid_tessellation_finding.json").read_text())
    assert "ILL-POSED, not PASS" in finding["gates"]["G3_invariance"]
    assert "not Williamson" in finding["gates"]["G1_skew_normal"]
    assert "G1_williamson" not in finding["gates"]
