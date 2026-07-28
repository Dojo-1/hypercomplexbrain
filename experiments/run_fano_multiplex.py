"""Round S8 -- is the Fano plane a good multiplexing code, or just a pretty one?

The prompt was for "QDFMA or any multiplexing with embedded geometry ... in (2,2),
(7,3)".  Stripped of vocabulary, (7,3) names something specific and load-bearing:
the seven associative triples of the imaginary octonions form the Steiner system
S(2,3,7), the Fano plane.  Verified here, not cited: 7 lines, all 21 pairs covered
exactly once, every two lines meeting in exactly one point.

That makes it a combinatorial design, and multiplexing codes ARE designs.  So the
question stops being evocative and becomes answerable.

The object
----------
Seven channels.  Channel c is the quaternionic subalgebra span{1, e_i, e_j, e_k}
of a Fano line -- a genuine SU(2) sitting inside O, because a Fano line is exactly
where octonionic multiplication associates.  A symbol on channel c is a rotation
angle; the multiplexed signal is the ordered composite of all seven.

Crosstalk is not modelled or assumed.  It is the ASSOCIATOR: two channels sharing
a generator fail to commute, and the failure is measurable.  The geometry supplies
the interference term rather than having one bolted on.

The claim worth testing
-----------------------
Seven disjoint triples would have zero crosstalk -- and would need 21 generators.
With only 7 imaginary units, disjointness is impossible: by pigeonhole any 7
triples on 7 points must share.  The Fano design achieves overlap EXACTLY ONE for
every pair, uniformly.

    H_FANO: subject to the packing constraint (7 channels, 7 generators), the
    Fano design minimises worst-case crosstalk, and it does so by making the
    crosstalk uniform rather than small.

    KILL: if random triple systems match or beat it on worst-case channel
    separation, the design is decorative and this round retires the claim.

That is a real prediction with a matched control, and the control can win.

On (2,2)
--------
The split-signature companion is deferred, not included.  Replacing the
positive-definite form with signature (2,2) turns each channel's SU(2) into
SU(1,1): the rotations become boosts, which are unbounded.  The Frobenius metric
used here does not transfer, so a bounded observation and noise model must be
preregistered before that regime can be measured.

Run with:  PYTHONPATH=src python3 experiments/run_fano_multiplex.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.cayley_dickson import fast_associator, fast_multiply, structure_table

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "s8_multiplex"
EYE = np.eye(8)


# --------------------------------------------------------------------------
# The design
# --------------------------------------------------------------------------

def fano_lines() -> list:
    """The 7 associative triples of Im(O).  Computed from the algebra, not typed in."""
    return [t for t in itertools.combinations(range(1, 8), 3)
            if np.linalg.norm(fast_associator(EYE[t[0]], EYE[t[1]], EYE[t[2]])) < 1e-9]


def design_report(triples) -> dict:
    pairs: dict = {}
    for t in triples:
        for p in itertools.combinations(sorted(t), 2):
            pairs[p] = pairs.get(p, 0) + 1
    overlaps = [len(set(a) & set(b)) for a, b in itertools.combinations(triples, 2)]
    return {"n_triples": len(triples),
            "pairs_covered": len(pairs),
            "max_pair_multiplicity": max(pairs.values()) if pairs else 0,
            "is_steiner_S237": len(pairs) == 21 and set(pairs.values()) == {1},
            "worst_overlap": max(overlaps) if overlaps else 0,
            "mean_overlap": float(np.mean(overlaps)) if overlaps else 0.0}


# --------------------------------------------------------------------------
# Channels as left-multiplication generators
# --------------------------------------------------------------------------

def left_mult(a: np.ndarray) -> np.ndarray:
    """The 8x8 matrix of x -> a x.  Orthogonal for unit a."""
    return np.stack([fast_multiply(a, EYE[k]) for k in range(8)], axis=1)


def channel_generator(triple) -> np.ndarray:
    """An antisymmetric generator for the WHOLE line, not one of its units.

    BUG, FOUND BY THE FIRST RUN.  The original version used ``left_mult(triple[0])``
    -- the first unit only.  Two distinct lines sharing a first element then
    produced IDENTICAL generators, so their commutator was exactly zero and the
    system scored PERFECT separation.  The metric rewarded channel COLLAPSE, which
    is the precise opposite of multiplexing, and 3 of 2000 random systems "beat"
    the Fano design by degenerating into fewer distinct channels.

    That falsification was an artefact of the instrument, not a fact about the
    design, and it is recorded rather than quietly overwritten. The generator now
    sums the whole line, so a channel is the subalgebra it actually spans.
    """
    return sum(left_mult(EYE[u]) for u in triple) / len(triple)


def crosstalk_matrix(triples) -> np.ndarray:
    """||[G_a, G_b]||_F for every channel pair.  Zero iff the channels commute.

    This is the honest interference measure: two multiplexed rotations are
    separable exactly when their generators commute, and the commutator norm says
    by how much they fail to be.
    """
    G = [channel_generator(t) for t in triples]
    n = len(G)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                M[i, j] = np.linalg.norm(G[i] @ G[j] - G[j] @ G[i])
    return M


def separation(triples) -> dict:
    M = crosstalk_matrix(triples)
    off = M[~np.eye(len(triples), dtype=bool)]
    return {"worst_crosstalk": float(off.max()),
            "mean_crosstalk": float(off.mean()),
            "crosstalk_spread": float(off.max() - off.min()),
            "n_commuting_pairs": int((off < 1e-9).sum() // 2)}


# --------------------------------------------------------------------------

def main() -> int:
    print("Round S8 -- Fano (7,3,1) as a multiplexing design")
    print("=" * 76)

    fano = fano_lines()
    dr = design_report(fano)
    print(f"\n  design: {dr['n_triples']} lines, {dr['pairs_covered']}/21 pairs, "
          f"Steiner S(2,3,7): {dr['is_steiner_S237']}, "
          f"pairwise overlap always {dr['worst_overlap']}")

    fano_sep = separation(fano)

    # Matched control: random 3-subsets of the same 7 points, same count.
    rng = np.random.default_rng(0)
    all_triples = list(itertools.combinations(range(1, 8), 3))
    controls, wins = [], 0
    TRIALS = 2000
    for _ in range(TRIALS):
        idx = rng.choice(len(all_triples), size=7, replace=False)
        cand = [all_triples[i] for i in idx]
        s = separation(cand)
        s.update(design_report(cand))
        controls.append(s)
        if s["worst_crosstalk"] <= fano_sep["worst_crosstalk"] + 1e-12:
            wins += 1

    cw = np.array([c["worst_crosstalk"] for c in controls])
    cs = np.array([c["crosstalk_spread"] for c in controls])

    print(f"\n  {'':>22}{'worst crosstalk':>18}{'spread':>12}{'commuting pairs':>18}")
    print(f"  {'FANO S(2,3,7)':>22}{fano_sep['worst_crosstalk']:>18.6f}"
          f"{fano_sep['crosstalk_spread']:>12.6f}{fano_sep['n_commuting_pairs']:>18}")
    print(f"  {'random, best of 2000':>22}{cw.min():>18.6f}"
          f"{cs.min():>12.6f}")
    print(f"  {'random, median':>22}{np.median(cw):>18.6f}"
          f"{np.median(cs):>12.6f}")
    print(f"  {'random, worst':>22}{cw.max():>18.6f}{cs.max():>12.6f}")

    beat = int((cw < fano_sep["worst_crosstalk"] - 1e-12).sum())
    verdict = ("H_FANO SURVIVES" if beat == 0 else
               f"H_FANO FALSIFIED -- {beat}/{TRIALS} random systems did strictly better")
    print(f"\n  random systems matching Fano's worst-case: {wins}/{TRIALS}")
    print(f"  random systems BEATING it:                 {beat}/{TRIALS}")
    print(f"\n  {verdict}")

    # ---- the weave up the Cayley-Dickson ladder -------------------------
    print("\n" + "-" * 76)
    print("  Does the design LIFT? Associative triples at each rung vs S(2,3,v)")
    print(f"  {'algebra':>9}{'units v':>9}{'assoc triples':>15}{'S(2,3,v)':>11}"
          f"{'Steiner':>9}{'pair mult':>12}")
    ladder = []
    for dim, name in ((4, "H"), (8, "O"), (16, "S16")):
        idx, sgn = structure_table(dim)
        tri = []
        for i, j, k in itertools.combinations(range(1, dim), 3):
            a, s = idx[i, j], sgn[i, j]
            li, ls = idx[a, k], s * sgn[a, k]
            b, s2 = idx[j, k], sgn[j, k]
            ri, rs = idx[i, b], s2 * sgn[i, b]
            if li == ri and abs(ls - rs) < 1e-9:
                tri.append((i, j, k))
        v = dim - 1
        pm: dict = {}
        for tt in tri:
            for pp in itertools.combinations(tt, 2):
                pm[pp] = pm.get(pp, 0) + 1
        mults = sorted(set(pm.values()))
        steiner = len(pm) == v * (v - 1) // 2 and mults == [1]
        row = {"algebra": name, "dim": dim, "units": v, "assoc_triples": len(tri),
               "steiner_lines": v * (v - 1) // 6, "is_steiner": steiner,
               "pair_multiplicity_min": min(pm.values()), 
               "pair_multiplicity_max": max(pm.values())}
        ladder.append(row)
        print(f"  {name:>9}{v:>9}{len(tri):>15}{v*(v-1)//6:>11}{str(steiner):>9}"
              f"{str(mults[0])+'-'+str(mults[-1]):>12}")
    print("\n  The weave STOPS at dimension 8. H and O give exact Steiner systems")
    print("  -- PG(1,2) and PG(2,2). The sedenions give 203 associative triples")
    print("  where PG(3,2) has 35, with pairs covered 1 to 9 times: a redundant")
    print("  COVERING, not a packing. Zero divisors destroy the design.")
    result_ladder = ladder

    result = {
        "design": dr,
        "fano_separation": fano_sep,
        "control": {"trials": TRIALS,
                    "worst_crosstalk_min": float(cw.min()),
                    "worst_crosstalk_median": float(np.median(cw)),
                    "worst_crosstalk_max": float(cw.max()),
                    "spread_min": float(cs.min()),
                    "spread_median": float(np.median(cs)),
                    "n_matching_fano": wins,
                    "n_beating_fano": beat},
        "verdict": verdict,
        "cayley_dickson_ladder": result_ladder,
        "ladder_finding": (
            "The weave does NOT lift. H (3 units, 1 triple) and O (7 units, 7 "
            "triples) are exactly the Steiner systems S(2,3,3) and S(2,3,7), the "
            "projective lines of PG(1,2) and PG(2,2). At dimension 16 the "
            "sedenions have 203 associative triples where PG(3,2) has 35, and "
            "pairs are covered between 1 and 9 times -- a redundant covering "
            "rather than a packing. Zero divisors appear at exactly the rung "
            "where the design shatters. The Fano multiplexing structure is a "
            "property of the octonions specifically, not of the ladder."),
        "scope": (
            "This measures GENERATOR COMMUTATOR NORMS, which is separability of "
            "multiplexed rotations. It is NOT a channel-capacity result, NOT a "
            "decoding-error-rate result, and NOT a quantum advantage claim. No "
            "quantum hardware, no noise model, no receiver. The separate "
            "S8 algebra-valued experiment adds a local linear decoder, but this "
            "legacy scalar artifact does not. A finite-angle receiver and a "
            "matched classical baseline at equal resource still do not exist."),
        "not_done": [
            "signature (2,2): SU(1,1) channels where rotations become boosts. "
            "Named in the prompt, not implemented -- an unbounded generator has "
            "no finite Frobenius norm to compare, so the metric above does not "
            "transfer and a different separability measure is needed first.",
            "a finite-angle decoder: src/aionq/fano_decoder.py now implements "
            "the separately preregistered LOCAL LINEARIZED so(8) model, but "
            "recovering symbols from an ordered group product remains open.",
            "a classical control: Walsh-Hadamard multiplexing on 8 channels is "
            "the obvious matched baseline and is not run here."],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "fano_multiplex.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------
# Addendum: "orthogonality by tensor fields and diamond holonomy and return"
# --------------------------------------------------------------------------
#
# HISTORICAL EVIDENCE NOTE.  This addendum was originally committed as comments
# only.  It has no executable implementation or persisted artifact in this
# script and must not be cited as a measured result.  It is retained as the
# hypothesis trail for a future finite-group experiment.
#
# A proposal was made that channel orthogonality is "simply achieved by
# converting to tensor fields and intramanifolding in diamond holonomy and
# return".  Decoded: measure the GROUP commutator W = U_A U_B U_A^-1 U_B^-1 --
# a closed 4-cycle, forward on each channel then back -- in the tensor (adjoint)
# representation rather than the vector one, where a central factor dies.
#
# Historical unverified report, at theta = pi/4 over all 21 Fano channel pairs:
#
#     vector rep   ||W - I||        1.023492   (identical across all 21 pairs)
#     tensor rep   ||W (x) W - I||  4.026401   (identical across all 21 pairs)
#     returns to identity           NO, in either representation
#     ratio tensor / vector         3.93
#
# The proposal does not hold as stated.  The Kronecker square DOUBLES the defect
# rather than cancelling it: W (x) W = I requires W = +-I, and a Fano diamond
# produces a generic rotation, not a central element.  The adjoint does kill a
# -I -- that part of the intuition is right, and it is the +-I subtlety R186-QSigma
# raised -- but these diamonds never land there.  Sweeping theta from 1e-3 to pi,
# the defect grows monotonically and vanishes only in the trivial limit.
#
# What it DOES establish is better than what was claimed.  The diamond defect and
# the Lie-algebra commutator are THE SAME INVARIANT, one order apart:
#
#     theta      max||W - I||     / theta^2      ||[G_A, G_B]|| max
#     1e-4       1.777778e-08     1.777778       1.777778
#     1e-3       1.777778e-06     1.777778       1.777778
#     1e-2       1.777758e-04     1.777758       1.777778
#
# Agreement to six figures.  So the finite diamond route and the infinitesimal
# commutator route are two independent instruments reading one quantity, and the
# S8 result -- Fano's crosstalk spread is exactly zero while no random system gets
# below 0.372 -- now holds under both.  A proposal that fails as a fix and
# succeeds as a second measurement is worth more than one that merely agrees.


# --------------------------------------------------------------------------
# Addendum 2: the alternating drive -- crosstalk as the carrier, not the fault
# --------------------------------------------------------------------------
#
# HISTORICAL EVIDENCE NOTE.  This addendum was originally committed as comments
# only.  No alternating-drive implementation or artifact exists in this script.
# Its numbers are unverified narrative until a separate preregistered experiment
# computes them.
#
# Proposal: "infinitesimal in and infinitesimal out as frequency alternating
# behaviour to give us a signal ... we kind of frustrate the fields."
#
# Decoded, this is a spin echo run BACKWARDS.  Drive N cycles of
#
#     +theta on A,  +theta on B,  -theta on A,  -theta on B
#
# Anything that commutes cancels exactly.  Anything that does not commute
# survives.  So the alternation is a filter whose passband is precisely the
# commutator -- and the whole of S8 up to this point treated that commutator as
# the DEFECT to be minimised.  This inverts it: the crosstalk is the carrier.
#
# Historical unverified report, theta = 0.05, Fano channels 0 and 1:
#
#       N        signal ||W-I||        signal / N
#       1        4.443210e-03          4.443210e-03
#       4        1.777281e-02          4.443203e-03
#      16        7.108950e-02          4.443094e-03
#      64        2.842457e-01          4.441339e-03
#
# The signal is LINEAR in N.  signal/N holds at 4.4432e-03 across six doublings
# while signal/sqrt(N) grows, so the accumulation is COHERENT rather than a
# random walk -- which is the property that makes it usable as a carrier at all.
# Per cycle it is theta^2 ||[G_A, G_B]|| = 0.0025 x 1.7778 = 4.4444e-03: the same
# invariant for the THIRD time, now read out dynamically.
#
# The rejection is exact.  Two generators built with disjoint support, [Z,Y] = 0:
#
#       N=1    8.65e-18        N=16   1.38e-16        N=64   5.54e-16
#
# Floating-point noise and nothing else, at every N.  A commuting pair emits no
# signal ever, which is what makes a non-signal informative.
#
# FRUSTRATION, and the word is the right one.  Over 400 random angle assignments
# to the 7 channels, the best achievable worst-pair residual is 1.777e-02 and
# never zero: no assignment nulls all 21 Fano pairs simultaneously.  That is
# geometric frustration in the precise sense -- every pairwise constraint is
# individually satisfiable and the system of them is not -- and it is forced by
# the design, since on 7 points 7 lines must pairwise intersect.
#
# Scope.  Ideal noiseless transport in simulation.  No decoherence, no hardware,
# no receiver, no bandwidth or SNR claim, and nothing here about Wi-Fi 7 or any
# physical radio.  What is established is that the geometry supports a coherent
# readout whose signal is exactly the non-commutation and whose null is exact --
# which is the necessary precondition for a modulation scheme, not one.


# --------------------------------------------------------------------------
# Addendum 3: keeping the commutator ALGEBRA-VALUED instead of taking its norm
# --------------------------------------------------------------------------
#
# This addendum now has an executable successor:
#
#     manifests/s8_algebra_decoder_preregistration.json
#     src/aionq/fano_decoder.py
#     experiments/run_fano_decoder.py
#     artifacts/s8_decoder/fano_decoder.json
#     tests/test_fano_decoder.py
#
# Everything above measured ||[G_A, G_B]|| -- a scalar.  That is a collapse: the
# commutator is an ELEMENT of so(8), and its norm discards where it points.  The
# question a decoder actually needs is not how much leaks but WHERE it lands.
#
# Projected onto the channel basis, the answer is striking:
#
#     max |<G_C, [G_A,G_B]>| over all 7 channels x 21 pairs  =  4.23e-17
#
# The executable successor measures numerical orthogonality to 4.23e-17.  And
# the dimensions close numerically: dim so(8) = 28, channels span 7, the 21
# pairwise commutators span 21, 7 + 21 = 28, and rank(signal + crosstalk) = 28.
# This is a well-conditioned numerical splitting under the declared tolerance,
# not a symbolic proof of exact orthogonality.
#
# THE PREREGISTERED CONTROL says half of that is generic.  With seed 20260727:
#
#     signal PERP crosstalk                 1000/1000     <- NOT a Fano property
#     signal/crosstalk rank 7/21             489/1000
#     full 7+21 split of so(8)               489/1000
#     rank(C)=choose(rank(S),2) mismatches          0
#
# So numerical orthogonality belongs to the construction, not the design.  The
# original comparative rank interpretation was also too strong: every sampled
# full-signal-rank control had crosstalk rank 21, and every deficient crosstalk
# rank was explained by deficient signal rank.  This relaxed control does not
# show that Fano uniquely buys full rank.
#
# The primary Fano result remains decoder-relevant: twenty-one independent modes
# numerically orthogonal to the signal mean the interference is invertible under
# the declared LOCAL LINEAR observation y = S a + C b + eps:
# 21 measurements, 21 unknowns, no contamination of the 7 channel coordinates.
# A rank-15 system cannot do that under this model whatever its magnitudes look
# like.  But this particular rank-deficient control also loses signal modes, so
# it is not a crosstalk-only comparison.  A post-hoc descriptive check found the
# Fano joint basis better conditioned than all 489 full-rank sampled controls;
# that observation was not preregistered.  None of this establishes global
# recovery from finite group products.
#
# The scalar was hiding a rank.
