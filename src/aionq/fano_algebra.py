"""The S8 crosstalk decomposition, as code rather than as a comment.

Why this module exists
----------------------
Round S8 ended with three addenda appended to ``experiments/run_fano_multiplex.py``
recording a diamond-holonomy check, an alternating-drive readout, and an
algebra-valued crosstalk decomposition -- the last reporting an exact orthogonal
splitting ``dim so(8) = 28 = 7 + 21`` and a rank gap between the Fano design and
random triple systems.

An external audit checked those three commits and found that **all three added
zero executable lines**.  They are comment blocks.  The measurements behind them
were run in throwaway shell heredocs; the conclusions were committed and the
computations were not.

That is the failure this repository was built to prevent, arriving in a form its
own machinery could not see: an ``EvidenceEnvelope`` binds a claim to a command
and a digest, and ``verify_envelopes`` checks the ones that exist -- but a claim
written as a source comment never enters the membrane at all.  Prose in a ``#``
block has the authority of code and none of the accountability.  The audit is
credited: the finding is not mine.

So the numbers are recomputed here, in importable functions, under a recorded
seed, with an artifact and an envelope.

On 497 versus 489
-----------------
The S8 comment reported that 497 of 1000 random triple systems reach full
crosstalk rank.  The audit reran it and got 489.  Neither is wrong.  At p ~ 0.49
the binomial standard error on 1000 draws is about 16, so 497 and 489 are the
same measurement quoted twice, and the disagreement is entirely an artifact of
reporting a Monte Carlo proportion as a bare integer with no interval and no
seed.  :func:`random_rank_census` returns the interval, so the next comparison
can be conclusive instead of decorative.

What is measured
----------------
The commutator ``[G_A, G_B]`` is an element of ``so(8)``, not a number.  Taking
its Frobenius norm -- which every earlier S8 instrument did -- keeps the magnitude
and discards the direction, and direction is what a decoder needs.  Kept
algebra-valued there are two separate questions:

    ORTHOGONALITY -- does the crosstalk land outside the signal space?
    RANK          -- how many independent directions does it land in?

The first turns out to be generic and the second does not.  A norm can see
neither.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from aionq.cayley_dickson import fast_associator, fast_multiply

__all__ = ["EYE", "fano_lines", "left_mult", "channel_generator",
           "commutator", "frobenius_inner", "signal_crosstalk_projection",
           "rank_decomposition", "random_rank_census", "diamond_holonomy",
           "alternating_drive", "wilson_interval"]

EYE = np.eye(8)
SO8_DIM = 28


def fano_lines() -> list:
    """The 7 associative triples of Im(O), computed from the algebra."""
    return [t for t in itertools.combinations(range(1, 8), 3)
            if np.linalg.norm(fast_associator(EYE[t[0]], EYE[t[1]], EYE[t[2]])) < 1e-9]


def left_mult(a: np.ndarray) -> np.ndarray:
    """The 8x8 matrix of ``x -> a x``.  Antisymmetric for imaginary unit `a`."""
    return np.stack([fast_multiply(a, EYE[k]) for k in range(8)], axis=1)


def channel_generator(triple) -> np.ndarray:
    """Generator for the WHOLE line, not one of its units.

    Using ``triple[0]`` alone was the S8 bug: two lines sharing a first element
    produced identical generators, so their commutator vanished and the design
    scored perfect separation by channel COLLAPSE.  Kept here as the corrected
    form so the module cannot silently regress to it.
    """
    return sum(left_mult(EYE[u]) for u in triple) / len(triple)


def commutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    return A @ B - B @ A


def frobenius_inner(A: np.ndarray, B: np.ndarray) -> float:
    """``<A, B> = tr(A^T B)``, the invariant inner product on so(8)."""
    return float(np.tensordot(A, B, axes=([0, 1], [0, 1])))


def signal_crosstalk_projection(triples) -> dict:
    """How far the crosstalk leans on the signal space.

    Returns the worst absolute inner product between any channel generator and
    any pairwise commutator, over 7 channels x 21 pairs = 147 products, plus the
    same normalised by the operand norms so the number means something
    scale-free.  A raw inner product near zero can be an artifact of small
    operands; the normalised one cannot.
    """
    G = [channel_generator(t) for t in triples]
    n = len(G)
    worst_raw, worst_norm, count = 0.0, 0.0, 0
    for i, j in itertools.combinations(range(n), 2):
        C = commutator(G[i], G[j])
        c_norm = float(np.linalg.norm(C))
        for k in range(n):
            raw = abs(frobenius_inner(G[k], C))
            g_norm = float(np.linalg.norm(G[k]))
            worst_raw = max(worst_raw, raw)
            if c_norm > 1e-12 and g_norm > 1e-12:
                worst_norm = max(worst_norm, raw / (c_norm * g_norm))
            count += 1
    return {"n_products": count,
            "worst_abs_inner": worst_raw,
            "worst_normalised_inner": worst_norm}


def _span_rank(mats, tol: float = 1e-9) -> int:
    if not mats:
        return 0
    flat = np.stack([np.asarray(M, dtype=float).ravel() for M in mats])
    s = np.linalg.svd(flat, compute_uv=False)
    return int((s > tol * max(1.0, s[0])).sum())


def rank_decomposition(triples) -> dict:
    """Ranks of the signal span, the crosstalk span, and their union.

    The S8 comment claimed ``28 = 7 + 21`` exactly.  Reported here with the union
    rank alongside the two parts, because ``7 + 21 = 28`` is arithmetic and
    ``rank(union) = 28`` is the claim -- they coincide only if the two spans meet
    trivially, which is the thing being asserted.
    """
    G = [channel_generator(t) for t in triples]
    pairs = list(itertools.combinations(range(len(G)), 2))
    C = [commutator(G[i], G[j]) for i, j in pairs]
    signal, cross, union = _span_rank(G), _span_rank(C), _span_rank(G + C)
    return {"n_channels": len(G), "n_pairs": len(pairs),
            "signal_rank": signal, "crosstalk_rank": cross,
            "union_rank": union, "so8_dim": SO8_DIM,
            "splits_the_algebra": signal + cross == union == SO8_DIM}


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple:
    """Wilson score interval -- the reason 497 and 489 are the same number."""
    if trials == 0:
        return (0.0, 1.0)
    p = successes / trials
    d = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / d
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def random_rank_census(trials: int = 1000, seed: int = 20260728) -> dict:
    """Matched control: how often do random triple systems reach full rank?

    Random 7-subsets of the 35 possible triples on 7 points -- same point set,
    same channel count, same generator construction.  Only the design differs.
    """
    rng = np.random.default_rng(seed)
    all_triples = list(itertools.combinations(range(1, 8), 3))
    ranks = []
    for _ in range(trials):
        idx = rng.choice(len(all_triples), size=7, replace=False)
        cand = [all_triples[i] for i in idx]
        ranks.append(rank_decomposition(cand)["crosstalk_rank"])
    ranks = np.array(ranks)
    full = int((ranks == 21).sum())
    lo, hi = wilson_interval(full, trials)
    return {"trials": trials, "seed": seed,
            "full_rank_count": full,
            "full_rank_fraction": full / trials,
            "wilson_95": [lo, hi],
            "median_rank": float(np.median(ranks)),
            "min_rank": int(ranks.min()), "max_rank": int(ranks.max())}


def _expm_antisym(A: np.ndarray) -> np.ndarray:
    from scipy.linalg import expm
    return expm(A)


def diamond_holonomy(GA: np.ndarray, GB: np.ndarray, theta: float) -> float:
    """Group commutator ``e^{tA} e^{tB} e^{-tA} e^{-tB}``, read at second order.

    BCH gives ``= I + theta^2 [A,B] + O(theta^3)``, so dividing the deviation by
    ``theta^2`` recovers ``||[A,B]||``.  This is a second route to the same
    invariant, which is why S8 trusted it -- and why the rank finding mattered:
    three routes agreeing to six figures were all reading one scalar shadow.
    """
    U = (_expm_antisym(theta * GA) @ _expm_antisym(theta * GB)
         @ _expm_antisym(-theta * GA) @ _expm_antisym(-theta * GB))
    return float(np.linalg.norm(U - np.eye(U.shape[0])) / (theta * theta))


def alternating_drive(GA: np.ndarray, GB: np.ndarray, theta: float,
                      cycles: int) -> dict:
    """Accumulated deviation under an alternating A/B drive.

    Linear accumulation in `cycles` means the signal is COHERENT rather than a
    random walk, which is the property that makes non-commutation usable as a
    carrier at all.  A commuting pair must emit nothing at every cycle count.
    """
    step = (_expm_antisym(theta * GA) @ _expm_antisym(theta * GB)
            @ _expm_antisym(-theta * GA) @ _expm_antisym(-theta * GB))
    U = np.eye(GA.shape[0])
    for _ in range(cycles):
        U = step @ U
    total = float(np.linalg.norm(U - np.eye(U.shape[0])))
    return {"cycles": cycles, "total": total, "per_cycle": total / max(1, cycles)}
