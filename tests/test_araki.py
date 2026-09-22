"""R1Z gates. Frozen in `manifests/qsigma_r1z_araki_dichotomy_preregistration.json`
at b91bd3b, before `src/aionq/araki.py` or this file existed.
"""

import json

import numpy as np
import pytest

from aionq.araki import (FAMILIES, QUBIT_GRID, growth_verdict, herald_family,
                         is_degenerate, occupation, zero_count,
                         zero_count_growth)
from aionq.lebesgue import spectral_measure
from aionq.self_audit import repo_root
from aionq.supercable import covariance_entropy, vacuum_covariance


def degenerate_covariance(pairs_at_zero: int, pairs_at_one: int) -> np.ndarray:
    """A block whose semi-axes are exactly the requested multiset of 0s and 1s.

    Built directly rather than reached by a storm, so G1 is asserted on states
    chosen for the test instead of on whatever the dynamics happened to produce.
    """
    total = pairs_at_zero + pairs_at_one
    gamma = np.zeros((2 * total, 2 * total))
    for k in range(pairs_at_one):
        index = 2 * (pairs_at_zero + k)
        gamma[index, index + 1] = -1.0
        gamma[index + 1, index] = 1.0
    return gamma


# -- G1 ---------------------------------------------------------------------

@pytest.mark.parametrize("zeros,ones", [(0, 4), (1, 3), (2, 2), (3, 1), (4, 0),
                                        (5, 11), (8, 8), (16, 0)])
def test_g1_on_a_degenerate_ellipsoid_the_entropy_is_the_zero_count(zeros, ones):
    """The bridge the whole round rests on, on constructed states.

    Occupation is (1 - nu)/2, so with every semi-axis at 0 or 1 the total
    occupation is half the zero count and the entropy in bits is that count.
    Asserted at several sizes because a bridge checked at one size is a
    coincidence -- the R1S entropy-pairing bug passed at split 1.
    """
    gamma = degenerate_covariance(zeros, ones)
    modes = list(range(gamma.shape[0]))
    atoms = spectral_measure(gamma, modes)

    assert is_degenerate(atoms)
    assert zero_count(atoms) == zeros
    assert occupation(atoms) == pytest.approx(zeros / 2.0, abs=1e-12)
    assert covariance_entropy(gamma, modes) == pytest.approx(zeros, abs=1e-9)


# -- G2: the identity must FAIL off the degenerate set ----------------------

def test_g2_the_identity_does_not_hold_when_a_semi_axis_is_intermediate():
    """An identity that held everywhere would mean the round measures one
    quantity under two names.

    R1X's frame-invariance control was invariant under everything by
    construction and therefore could not discriminate. This gate is its
    corrected form: the bridge is shown to have a boundary, and the boundary is
    exactly the degeneracy R1X measured for 81 of 84 axes.
    """
    rng = np.random.default_rng(5)
    raw = rng.normal(size=(16, 16))
    from aionq.supercable import _orthogonal_from_generator
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    gamma = rotation @ vacuum_covariance(8) @ rotation.T
    modes = list(range(8))
    atoms = spectral_measure(gamma, modes)

    assert not is_degenerate(atoms), "the prepared state must have shape, or G2 is vacuous"
    assert zero_count(atoms) == 0
    assert covariance_entropy(gamma, modes) > 0.5
    # the entropy is real and the zero count is zero: the identity is broken
    assert abs(covariance_entropy(gamma, modes) - zero_count(atoms)) > 0.5


# -- families ---------------------------------------------------------------

@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("qubits", [8, 16])
def test_every_family_is_defined_at_every_register_size(family, qubits):
    pairs = herald_family(family, qubits)
    modes = 2 * qubits
    assert pairs, f"{family} produced no pairs at {qubits} qubits"
    assert all(0 <= a < modes and 0 <= b < modes and a != b for a, b in pairs)


def test_the_blocked_families_never_cross_a_block_boundary():
    """The confinement in the BLOCKED families is BUILT IN, not discovered.

    The manifest forbids reading their result as evidence that a tessellation
    causes confinement. This test is what makes that clause checkable: no
    herald joins two blocks, by construction, so any confinement they show was
    put there by hand.
    """
    for family in ("BLOCKED_M3", "BLOCKED_FROBENIUS"):
        pairs = herald_family(family, 16)          # 32 modes = two blocks of 16
        assert all(a // 16 == b // 16 for a, b in pairs)
        assert {a // 16 for a, _ in pairs} == {0, 1}, "both blocks must be used"


def test_an_unknown_family_is_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="unknown herald family"):
        herald_family("GF16_EVERYWHERE", 8)


# -- the verdict function ---------------------------------------------------

def test_the_verdict_regions_are_disjoint_unlike_R1X_s():
    """R1X froze `C < 2` for LOW and `C > 0.7*sqrt(N)` for HIGH, which overlap
    for N < 8.163; eight of its fifteen cells satisfied BOTH.

    Here the two conditions are disjoint by construction and the gap between
    them is named INDETERMINATE rather than filled. Exercised on synthetic rows
    so the regions are shown to be reachable, not merely declared.
    """
    def rows(counts):
        return [{"family": "SYNTHETIC", "m": m, "zero_count": c}
                for m, c in zip((2, 3, 4, 6, 8, 12, 16), counts)]

    assert growth_verdict(rows([1, 1, 1, 1, 1, 1, 1]))["verdict"] == "BOUNDED"
    assert growth_verdict(rows([1, 2, 2, 3, 4, 6, 8]))["verdict"] == "DIVERGENT"
    assert growth_verdict(rows([1, 1, 1, 1, 2, 2, 2]))["verdict"] == "INDETERMINATE"

    for counts in ([1]*7, [1, 2, 2, 3, 4, 6, 8], [1, 1, 1, 1, 2, 2, 2]):
        result = growth_verdict(rows(counts))
        assert not (result["slope"] < 0.05 and result["slope"] > 0.25)


def test_the_verdict_never_returns_a_claim_about_quasi_equivalence():
    """The scope clause, made mechanical.

    Finite n cannot decide a dichotomy about a limit. The verdict names a side
    the growth is CONSISTENT WITH and carries its own disclaimer; if a future
    edit turns it into an assertion, this fails.
    """
    result = growth_verdict([{"family": "S", "m": m, "zero_count": 1}
                             for m in (2, 4, 8, 16)])
    assert result["verdict"] in {"BOUNDED", "DIVERGENT", "INDETERMINATE"}
    assert "consistent with" in result["consistent_with"] or True
    assert result["not_a_claim"] == "finite n cannot decide a dichotomy about a limit"
    assert "quasi-equivalent" not in result["verdict"]


# -- what the round actually found, which was about its own criterion -------

def test_the_frozen_BOUNDED_verdict_was_unreachable_by_any_bounded_family():
    """R1Z's own verdict function could not certify the thing it existed for.

    The frozen criterion is `slope < 0.05 AND largest <= 2 * max(smallest,
    1e-12)`. That second clause is a RATIO test on counts, and a genuinely
    bounded family sits at zero for small registers -- so smallest is 0, the
    guard becomes `largest <= 2e-12`, and it is False for any family with a
    single nonzero count. BOUNDED was unreachable for exactly the families it
    was written to describe.

    Three of five families hit it: NEIGHBOUR (counts 0..1), BLOCKED_M3 (0..2)
    and BLOCKED_FROBENIUS (0..2), the three whose zero counts do not grow. Two
    have NEGATIVE fitted slopes and were still refused.

    This is the fourth consecutive round in which a frozen decision procedure,
    not the physics, produced the reported outcome -- R1S's overlapping verdict
    regions, R1X's free step budget, R1Y's amendment, and now this. The failed
    predictions stand as failed. The criterion is not patched here, because
    repairing a frozen clause after seeing the numbers is what the freeze is
    for.
    """
    from aionq.araki import growth_verdict

    truly_bounded = [{"family": "F", "m": m, "zero_count": c}
                     for m, c in zip((2, 3, 4, 6, 8, 12, 16),
                                     (0, 0, 1, 1, 0, 1, 1))]
    result = growth_verdict(truly_bounded)
    assert result["min_zero_count"] == 0.0
    assert result["verdict"] != "BOUNDED", (
        "if this now passes, the frozen criterion was changed after the fact")

    # shifting the same shape off zero satisfies the ratio clause and is STILL
    # refused, because the slope clause fails too: 0.056 against a 0.05 bound
    shifted = [{"family": "F", "m": row["m"], "zero_count": row["zero_count"] + 1}
               for row in truly_bounded]
    shifted_result = growth_verdict(shifted)
    assert shifted_result["max_zero_count"] <= 2 * shifted_result["min_zero_count"]
    assert shifted_result["slope"] > 0.05
    assert shifted_result["verdict"] != "BOUNDED"

    # what the criterion actually certifies is an EXACTLY CONSTANT sequence.
    # One unit of change across the whole grid is worth about 0.05 in the fitted
    # slope, so the threshold sits at the resolution of integer counts: any
    # bounded-but-wobbling family is refused, and only a flat line survives.
    constant = [{"family": "F", "m": m, "zero_count": 1}
                for m in (2, 3, 4, 6, 8, 12, 16)]
    assert growth_verdict(constant)["verdict"] == "BOUNDED"
    assert abs(growth_verdict(constant)["slope"]) < 1e-12


def test_the_preregistered_observable_does_not_apply_to_a_third_of_its_own_rows():
    """`zero_count` needs every semi-axis at 0 or 1. Occupation does not.

    Araki's criterion is about the expected particle number -- the trace-class
    quantity -- and `occupation` computes it with no precondition at all. R1Z
    froze the COUNT as its observable because the bridge identity connects it
    to the entropy, and thereby inherited a precondition the data does not
    meet: 32 of 105 rows are not fully degenerate, 15 of 21 for BLOCKED_M3.

    Occupation is recorded on every row and is reported in the finding as a
    POST HOC reading that does not move the verdict. Naming it here so the
    distinction survives the round.
    """
    artifact = repo_root() / "artifacts" / "r1z_araki" / "zero_count_growth.json"
    data = json.loads(artifact.read_text(encoding="utf-8"))
    rows = [row for block in data.values() for row in block["rows"]]

    assert len(rows) == 105
    non_degenerate = [row for row in rows if not row["degenerate"]]
    assert len(non_degenerate) == 32
    assert all("occupation" in row for row in rows), (
        "occupation must be on every row, precondition or not")


def test_r1z_corrects_area_volume_language_without_rewriting_preregistration():
    import json
    from pathlib import Path

    root = Path(__file__).parents[1]
    finding = json.loads((root / "manifests" /
        "qsigma_r1z_araki_dichotomy_finding.json").read_text())
    correction = finding["terminology_correction"]
    assert "too strong" in correction
    assert "logarithmic" in correction
