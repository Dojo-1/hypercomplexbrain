"""Range partitions, where R1Q-R1T all used domain partitions.

Riemann chops the base and evaluates the function on each piece.  Lebesgue chops
the RANGE and asks how much base sits at each height.  Everything this
repository partitioned from R1Q to R1T is a base: mode indices at a cut (R1Q),
the cut swept (R1R), the herald alphabet cut into GF(16) orbit caps (R1S),
sixteen GF(16) labels cut into four cells (R1T).  Three consecutive rounds in
which a base statistic either did not survive a change of coordinates -- R1Q's
rule was a labelling artifact -- or did not reconstruct from its pieces: R1S's
additivity gate FAILED, and the sign reversed at M3, so not even a directional
inequality survives.

The range object was already here and already integrated.  For a Gaussian state
the block ``Gamma_A`` has spectrum ``+-i nu_k`` with ``nu_k`` in ``[0, 1]``, and

    S(A) = sum_k H2((1 + nu_k) / 2)

is an integral of a fixed function against the empirical measure of those
values.  `supercable.covariance_entropy` has been computing that integral since
R1J.  This module names the measure it integrates:

    mu_A = (1/m) sum_k delta_{nu_k}        a probability measure on [0, 1]

WHAT THAT BUYS, AND WHAT IT DOES NOT.  It does not repair additivity; R1S killed
that and `reconstruction_defect` MEASURES the failure rather than mending it.
It does not make anything physical.  Frame invariance -- ``mu_A`` is unchanged
by any relabelling inside ``A``, because a similarity does not move a spectrum
-- is a triviality of linear algebra and is preregistered as a CONTROL, not as a
finding.  The triviality is exactly the point: it is the property R1Q's rule
lacked, and it is free here rather than earned.

What is not free is whether the measure separates states the scalar merges.  One
mode at ``nu = 0.5`` beside a pure mode carries the same bits as two modes near
``nu = 0.72``, and those are not the same state.  Whether that difference is
REALISED on this repository's testbed is R1X's one falsifiable question, frozen
in ``manifests/qsigma_r1x_spectral_measure_preregistration.json`` with the
thresholds that decide it, and a negative answer is that round's result.
"""

from __future__ import annotations

import numpy as np

from .supercable import covariance_entropy, covariance_storm, vacuum_covariance

__all__ = [
    "spectral_measure",
    "lebesgue_weight",
    "measure_entropy",
    "wasserstein1",
    "reconstruction_defect",
    "ladder_spectral_sweep",
    "merged_by_entropy_separated_by_defect",
]

PURITY_EPS = 1e-9


def spectral_measure(gamma, modes) -> np.ndarray:
    """The symplectic values of ``Gamma`` restricted to ``modes``, sorted.

    One representative per conjugate pair.  ``+i nu_k`` and ``-i nu_k`` both
    appear in ``|Im spectrum|``, so every second entry of the sorted list is
    wanted and NOT its larger half -- the R1S correction, which turned
    ``[1, 1, 0.325, 0.325]`` into ``[1, 1]`` and reported 0.000 bits against an
    exact 0.922, and which passes at a single pair where the two rules coincide.
    The same rule is used here, from the same place, so that the two cannot
    drift apart.

    Returned as the atom list rather than as a measure object: at finite ``m``
    the measure IS the multiset of atoms, and every consumer here wants them
    sorted.
    """
    gamma = np.asarray(gamma, dtype=float)
    index = np.asarray(sorted(modes), dtype=int)
    if index.size % 2:
        raise ValueError("a mode subset carries whole conjugate pairs; got an odd count")
    block = gamma[np.ix_(index, index)]
    values = np.sort(np.abs(np.linalg.eigvals(block).imag))[::-1][::2]
    return np.sort(np.clip(values, 0.0, 1.0))


def measure_entropy(atoms) -> float:
    """``sum_k H2((1 + nu_k) / 2)``, the integral this repository already takes.

    Kept separate from `supercable.covariance_entropy` on purpose.  The gate
    R1X preregisters is that the two agree to 1e-12 on every split of a random
    Gaussian state, which is only a check if there are two code paths to
    compare.  A new instrument reproduces the old one on the old one's domain
    before any new number is recorded; this repository has twice mistaken an
    instrument artifact for a finding.
    """
    total = 0.0
    for nu in np.clip(np.asarray(atoms, dtype=float), 0.0, 1.0):
        for weight in ((1.0 + nu) / 2.0, (1.0 - nu) / 2.0):
            if weight > 1e-15:
                total -= weight * np.log2(weight)
    return float(total)


def lebesgue_weight(atoms, eps: float = PURITY_EPS) -> float:
    """Mass of ``mu_A`` sitting on the atom at purity: the fraction already pure.

    ``mu_A = w * delta_1 + (1 - w) * mu_tilde`` splits the measure at ``nu = 1``.
    Collapse of a region is ``w -> 1``, which is graded where ``final_entropy``
    is one number: a state can lose a bit by two modes drifting together or by
    one mode going pure, and ``w`` tells those apart while ``S`` does not.

    [R]_finite is declared in the manifest and repeated here because the name
    invites the wrong reading: at finite ``m`` every measure is atomic, so this
    is the split at a distinguished point, NOT the absolutely-continuous versus
    singular decomposition of Lebesgue's theorem.  That decomposition is
    unavailable here and is not claimed.
    """
    atoms = np.asarray(atoms, dtype=float)
    if atoms.size == 0:
        return 0.0
    return float(np.count_nonzero(atoms >= 1.0 - eps) / atoms.size)


def wasserstein1(left_atoms, right_atoms) -> float:
    """``W1`` between two empirical measures with the same number of atoms.

    For equal atom counts this is the mean absolute difference of the sorted
    lists, which is the L1 distance between the two cumulative distribution
    functions.

    WHY NOT TOTAL VARIATION, decided before measuring.  Both measures are purely
    atomic and generically share no atom at all, so total variation is
    identically 1 and reports nothing.  W1 respects the metric of ``[0, 1]``.
    Choosing the metric after seeing the numbers is how a defect functional gets
    tuned into significance, so the choice is frozen in the manifest.
    """
    left = np.sort(np.asarray(left_atoms, dtype=float))
    right = np.sort(np.asarray(right_atoms, dtype=float))
    if left.shape != right.shape:
        raise ValueError(
            f"W1 here is the equal-atom-count formula; got {left.size} and {right.size}")
    return float(np.mean(np.abs(left - right)))


def reconstruction_defect(gamma, modes, parts) -> dict:
    """How far the whole block's spectrum is from the union of its parts'.

    ``D = W1(mu_A, sum_i (m_i / m) mu_{A_i})``.  The parts partition ``A``, so
    the atom counts match by construction and the mixture is just the pooled
    atom list.  ``D = 0`` exactly when the two spectra agree as multisets, which
    happens when the parts carry no entanglement between them.

    This is the R1S quantity done in a way that does not break.  That ratio was
    unbounded, had no baseline once the additivity gate failed, and REVERSED
    SIGN at M3, which killed the directional reading too.  ``D`` is bounded in
    ``[0, 1]``, has no sign to reverse, is zero exactly at reconstruction, and
    does not move under relabelling.  It measures the failure R1S found.  It
    does not repair it, and the manifest forbids saying that it does.
    """
    modes = sorted(modes)
    parts = [sorted(part) for part in parts]

    pooled = sorted(mode for part in parts for mode in part)
    if pooled != modes:
        raise ValueError("parts must be a partition of modes, exactly")

    whole = spectral_measure(gamma, modes)
    part_atoms = [spectral_measure(gamma, part) for part in parts]
    mixture = np.sort(np.concatenate(part_atoms)) if part_atoms else np.array([])

    entropy_whole = measure_entropy(whole)
    entropy_parts = float(sum(measure_entropy(atoms) for atoms in part_atoms))
    return {
        "atoms_whole": whole,
        "atoms_mixture": mixture,
        "defect": wasserstein1(whole, mixture),
        "weight_whole": lebesgue_weight(whole),
        "weight_parts": [lebesgue_weight(atoms) for atoms in part_atoms],
        "entropy_whole": entropy_whole,
        "entropy_parts": entropy_parts,
        "entropy_gap": float(entropy_parts - entropy_whole),
        "agrees_with_supercable": abs(
            entropy_whole - covariance_entropy(gamma, modes)) < 1e-12,
    }


# --------------------------------------------------------------------------
# R1X's one falsifiable question
# --------------------------------------------------------------------------

ENTROPY_WINDOW = 0.05      # bits; frozen by the manifest, not by this file
DEFECT_FLOOR = 0.10        # W1; same


def ladder_spectral_sweep(qubits: int = 8, steps: int = 300,
                          seeds=(7, 13, 29), prepared_seed: int = 0) -> list:
    """Run the storm on every ladder cell and read the measure, not just its integral.

    One prepared state, shared by every cell, so a difference between cells is
    attributable to the cell.  Same walker, same budget, same split as
    `supercable.covariance_storm` -- this adds a reading, it does not add a
    condition.
    """
    from .pond import rung_pairs
    from .gf_frames import SUBGROUP_LADDER

    rng = np.random.default_rng(prepared_seed)
    raw = rng.normal(size=(2 * qubits, 2 * qubits))
    from .supercable import _orthogonal_from_generator
    rotation = _orthogonal_from_generator((raw - raw.T) / 2.0)
    prepared = rotation @ vacuum_covariance(qubits) @ rotation.T

    split = qubits // 2
    left = list(range(2 * split))
    halves = [left[: split], left[split:]]

    rows = []
    for rung in SUBGROUP_LADDER:
        pairs = rung_pairs(rung)
        for seed in seeds:
            storm = covariance_storm(pairs, qubits, steps=steps, seed=seed,
                                     split=split, prepared=prepared)
            result = reconstruction_defect(storm["covariance"], left, halves)
            rows.append({
                "rung": rung,
                "seed": seed,
                "steps": steps,
                "entropy": float(result["entropy_whole"]),
                "defect": float(result["defect"]),
                "weight": float(result["weight_whole"]),
                "atoms": [float(value) for value in result["atoms_whole"]],
                "agrees_with_supercable": bool(result["agrees_with_supercable"]),
            })
    return rows


def merged_by_entropy_separated_by_defect(rows, entropy_window: float = ENTROPY_WINDOW,
                                          defect_floor: float = DEFECT_FLOOR) -> dict:
    """P3, and it is allowed to come back empty.

    A pair of cells at the SAME seed that the entropy scalar calls the same and
    the measure calls different.  If no such pair exists then on this testbed
    the measure carries nothing the scalar does not, and that is R1X's result --
    not a reason to widen the window or narrow the floor.  Both numbers are
    frozen in the manifest so that the temptation is a matter of record.
    """
    hits = []
    for left in rows:
        for right in rows:
            if left["seed"] != right["seed"] or left["rung"] >= right["rung"]:
                continue
            gap = abs(left["entropy"] - right["entropy"])
            spread = abs(left["defect"] - right["defect"])
            if gap < entropy_window and spread > defect_floor:
                hits.append({"seed": left["seed"], "rungs": [left["rung"], right["rung"]],
                             "entropy_gap": gap, "defect_gap": spread})
    return {
        "entropy_window": entropy_window,
        "defect_floor": defect_floor,
        "pairs_examined": sum(1 for a in rows for b in rows
                              if a["seed"] == b["seed"] and a["rung"] < b["rung"]),
        "hits": hits,
        "p3_holds": bool(hits),
    }
