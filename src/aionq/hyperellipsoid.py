"""The body, its frame, and the orientation R1X threw away.

R1X built the empirical measure of a restricted covariance's singular values.
The orthogonal skew-normal form packages those values into canonical pairs, so
``mu_A`` is the pushforward of that body under the map that keeps axis LENGTHS
and forgets ORIENTATION -- and orientation is what survives when the lengths
degenerate, which on this dynamics they do: R1X measured 81 of 84 axes at
exactly 0 or 1.

This module keeps both halves. ``williamson_frame`` (a retained compatibility
name) returns the paired singular values AND an orthonormal Schur frame. This
is the orthogonal skew-normal form of a real antisymmetric covariance, not
Williamson's symplectic-congruence theorem. ``orientation_defect`` then asks how
the body sits relative to a TESSELLATION of the mode set, rather than relative
to the arbitrary left-half bipartition R1X inherited from R1Q and four rounds
carried without re-examining.

WHAT THIS MODULE CANNOT DO, ESTABLISHED BEFORE IT WAS WRITTEN.  R1Y's P2 asked
whether tessellation regularity predicts survival, to be tested on at least six
regular and six irregular subgroups enumerated independently of the hypothesis.
``GammaL(1,16)`` has forty subgroups and exactly FOUR give a regular
non-transitive tessellation -- three excluding the trivial one -- in three
distinct tile shapes.  The gate is unsatisfiable and was unsatisfiable when it
was frozen, so P2 is NOT TESTED by R1Y's own kill condition.  That was found by
enumerating the family before building anything, which is the R2A discipline
applied to a round rather than to a verdict function, and it is the first time
in this line that such a defect was caught BEFORE the round ran.
"""

from __future__ import annotations

import numpy as np

from .lebesgue import spectral_measure

__all__ = [
    "williamson_frame",
    "principal_angles",
    "orientation_defect",
    "survival_time",
    "regular_tessellations_available",
]


def williamson_frame(gamma, modes):
    """Semi-axes and the orthonormal frame carrying them, for a restricted block.

    A real antisymmetric matrix has an orthogonal real Schur form that is block diagonal
    with ``2 x 2`` blocks ``[[0, nu], [-nu, 0]]``.  That IS the canonical form,
    so the Schur vectors give a canonical-pair frame away from degeneracies
    is needed.  Returned together because R1X's whole defect was keeping one and
    discarding the other.
    """
    from scipy.linalg import schur

    gamma = np.asarray(gamma, dtype=float)
    index = np.asarray(sorted(modes), dtype=int)
    block = gamma[np.ix_(index, index)]

    canonical, frame = schur(block, output="real")
    nus = np.array([abs(canonical[2 * k, 2 * k + 1])
                    for k in range(block.shape[0] // 2)])
    order = np.argsort(nus)
    pairs = np.concatenate([[2 * k, 2 * k + 1] for k in order])
    return np.clip(nus[order], 0.0, 1.0), frame[:, pairs], canonical, block


def principal_angles(left_basis, right_basis) -> np.ndarray:
    """Principal angles between two subspaces, in radians, ascending."""
    from scipy.linalg import subspace_angles

    return np.sort(subspace_angles(np.asarray(left_basis, dtype=float),
                                   np.asarray(right_basis, dtype=float)))


def orientation_defect(gamma, modes, tiles, axes: int = 2) -> dict:
    """How the body sits relative to a tessellation, not how long its axes are.

    The span of the ``axes`` largest principal axes against each tile's own
    coordinate subspace.  This is the quantity ``mu_A`` discards, and it stays
    informative exactly where ``mu_A`` stops being: on a degenerated ellipsoid
    every semi-axis is 0 or 1, the measure has one degree of freedom, and the
    FRAME still has as many as the Grassmannian does.

    Frame-invariant under relabelling INSIDE a tile and not across one, which is
    the correct sensitivity: moving a mode between tiles changes the geometry
    rather than the description of it.  R1X's control was invariant under
    everything and therefore could not discriminate.
    """
    modes = sorted(modes)
    position = {mode: slot for slot, mode in enumerate(modes)}
    nus, frame, _, _ = williamson_frame(gamma, modes)

    # THE CUT MAY NOT FALL INSIDE A TIE, and this is why R1Y's P3 is ill-posed.
    # A repeated semi-axis means a higher-dimensional eigenspace, and every
    # orthonormal basis of it is equally canonical -- so "the top k axes" names
    # no particular subspace.  Two states with IDENTICAL spectra were measured
    # here to give top-2 subspaces differing by up to 1.24 radians.  R1X found
    # 81 of 84 axes sitting at exactly 0 or 1, a two-value spectrum, which is
    # precisely the regime P3 targets: "after all semi-axes have degenerated".
    # R1Y's premise -- lengths degenerate, orientation survives -- is backwards.
    # Degeneracy of the spectrum is what destroys the frame.
    #
    # Refused rather than returned, on the exponent_orbits precedent: a number
    # that is not a function of the state is worse than no number, because it
    # looks like a measurement.
    if axes and 0 < 2 * axes < len(nus) * 2:
        boundary = len(nus) - axes
        if abs(nus[boundary] - nus[boundary - 1]) < 1e-9:
            raise ValueError(
                f"the top-{axes} principal subspace is not a function of the "
                f"state here: semi-axes {nus[boundary - 1]:.6f} and "
                f"{nus[boundary]:.6f} are tied across the cut, so every basis "
                f"of the shared eigenspace is equally canonical. Use the whole "
                f"eigenspace instead of a top-k slice.")

    top = frame[:, -2 * axes:] if axes else frame[:, :0]
    rows = []
    for tile in tiles:
        columns = np.zeros((len(modes), len(tile)))
        for slot, mode in enumerate(sorted(tile)):
            columns[position[mode], slot] = 1.0
        angles = principal_angles(top, columns)
        rows.append({"tile": tuple(sorted(tile)),
                     "angles": angles,
                     "min_angle": float(angles.min()),
                     "mean_cosine": float(np.mean(np.cos(angles)))})

    cosines = np.array([row["mean_cosine"] for row in rows])
    return {
        "semi_axes": nus,
        "tiles": len(rows),
        "rows": rows,
        "defect": float(cosines.max() - cosines.min()),
        "spread": float(np.std(cosines)),
    }


def survival_time(pairs, qubits: int, prepared, step_grid, seed: int = 7,
                  split: int | None = None, tolerance: float = 1e-9) -> dict:
    """Largest step on the grid at which the body still has an intermediate axis.

    The observable R1X should have had.  Read off the grid and never
    interpolated, per the frozen parameters: an interpolated survival time
    would be a fifth number nobody froze.
    """
    from .supercable import covariance_storm

    split = qubits // 2 if split is None else split
    left = list(range(2 * split))
    alive, counts = -1, []
    for steps in step_grid:
        storm = covariance_storm(pairs, qubits, steps=steps, seed=seed,
                                 split=split, prepared=prepared)
        axes = spectral_measure(storm["covariance"], left)
        count = int(((axes > tolerance) & (axes < 1.0 - tolerance)).sum())
        counts.append(count)
        if count:
            alive = steps
    return {"step_grid": tuple(step_grid), "intermediate_counts": tuple(counts),
            "survival_time": alive}


def regular_tessellations_available() -> dict:
    """How many regular tessellations GammaL(1,16) actually offers. FOUR.

    R1Y's P2 required at least six regular and six irregular subgroups from an
    independently enumerated family.  The group has forty subgroups; four give a
    regular non-transitive orbit partition, three if the trivial subgroup is
    excluded, in three distinct tile shapes -- 15x1, 5x3 and 3x5.  The gate
    could not be met when it was frozen.

    Computed rather than quoted, because a count asserted in prose is exactly
    what `exponent_orbits` got wrong about zero being fixed.
    """
    import itertools

    from .gf_frames import gf16_mul

    def frobenius(value, power):
        for _ in range(power % 4):
            value = gf16_mul(value, value)
        return value

    elements = sorted({tuple(gf16_mul(a, frobenius(x, k)) for x in range(16))
                       for a in range(1, 16) for k in range(4)})
    identity = tuple(range(16))

    def generated(generators):
        seen, frontier = {identity}, [identity]
        while frontier:
            current = frontier.pop()
            for element in generators:
                nxt = tuple(current[element[x]] for x in range(16))
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        return frozenset(seen)

    subgroups = {generated(gens) for size in (1, 2)
                 for gens in itertools.combinations(elements, size)}

    def shape(group):
        seen, out = set(), []
        for x in range(1, 16):
            if x in seen:
                continue
            orbit = frozenset(h[x] for h in group)
            seen |= orbit
            out.append(len(orbit))
        return tuple(sorted(out))

    regular, irregular = [], []
    for group in subgroups:
        tiles = shape(group)
        if len(tiles) == 1:
            continue                                  # transitive: tiles nothing
        (regular if len(set(tiles)) == 1 else irregular).append((len(group), tiles))

    return {
        "order": len(elements),
        "subgroups": len(subgroups),
        "regular": len(regular),
        "regular_nontrivial": len([row for row in regular if row[0] > 1]),
        "irregular": len(irregular),
        "regular_shapes": sorted({row[1] for row in regular}),
        "r1y_gate": 6,
        "gate_is_satisfiable": len(regular) >= 6 and len(irregular) >= 6,
    }
