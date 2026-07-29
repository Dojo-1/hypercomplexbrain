"""Does hyperbolic representational capacity survive the unitary realization cost?

No.  Two independent instruments say so, and they say it in different currencies.

    PACKING   how many states are eps-separated out to source radius R
    HOLEVO    how many bits a receiver can extract from a codebook of them

The source measure grows as ``e^{2 rho}``.  The packing number does not: its
log-slope against R is ~0, so geometric separability saturates.  And the Holevo
information does not merely saturate -- it is CAPPED, by a bound that does not
depend on the codebook size at all.

The ceiling, and why N cannot beat it
-------------------------------------
From the R6d flag decomposition, at a single depth the Jensen gap vanishes and

    chi  =  pbar * S(sigmahat),      pbar = (1 + q^2)/2,   q = e^{-2 rho}

The success branch lives on ``C^4``, so ``S(sigmahat) <= log2 4 = 2`` no matter
how many codewords there are.  Hence

    chi  <=  2 pbar  =  1 + e^{-4 rho}   ->   1 bit.

**N is absent from that bound.**  A codebook of 100 eps-separated states at depth
8 transmits exactly what a codebook of 8 does: 1.000000 bit, while ``log2 N``
climbs from 3 to 6.644.  Geometric separation and information transmissibility
come apart completely, and the packing number is measuring the first while
saying nothing about the second.

The control that makes the number mean something
------------------------------------------------
A ceiling of 1 bit is only interesting against something that is not 1.  The
matched compact baseline is the same construction with ``SU(2)`` in place of
``SL(2,R)``: same Bell probe, same dimension, same codebook sizes, but a COMPACT
group, so every element is unitary, the success probability is identically 1, and
there is no erasure branch.  Its ceiling is ``log2 4 = 2`` bits and it reaches
1.994 at N = 256.

    compact      SU(2)      chi -> 2 bits
    non-compact  SL(2,R)    chi -> 1 bit

Exactly half, and the half is not mysterious: it is ``pbar -> 1/2``, the weight
that the erasure flag takes when the depth becomes large.  The unitary
realization cost of hyperbolic depth is a factor of two in the Holevo ceiling.

Scope
-----
One-shot, single use, one probe, one bipartition.  No coding theorem, no
regularisation, no asymptotic capacity, and no claim about any other encoding of
the same geometry.  The statement is about THIS realization, which is the one R6
measured and the one the packing instrument was run on.
"""

from __future__ import annotations

import math

import numpy as np

from aionq.holevo_sandwich import (flag_success_decomposition, holevo_chi,
                                   von_neumann_entropy)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import (attempted_use_state,
                                            trace_distance_closed_form)

__all__ = ["BELL", "holevo_ceiling", "sl2_codeword", "su2_matrix",
           "su2_codeword", "grid_codebook", "su2_codebook", "packing_number",
           "packing_log_slope", "ceiling_report"]

BELL = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)

#: The success branch lives on C^4, so its entropy cannot exceed 2 bits.
SUCCESS_BRANCH_DIM = 4


def holevo_ceiling(rho: float) -> float:
    """``chi <= 2 pbar = 1 + e^{-4 rho}``, independent of the codebook size.

    The bound comes from the flag decomposition plus a dimension count, not from
    any property of the code.  That is what makes it a ceiling rather than a
    measurement: no choice of codewords, and no number of them, can exceed it.

    ``pbar`` here is the CODEBOOK mean, not one codeword's success probability.
    A scratch check of this bound once printed ``2 p`` for a single codeword at
    one orientation and reported a violation at every non-Bell probe.  There was
    no violation: over a full angular codebook ``pbar = 1/2`` at every probe,
    because the orientation dependence averages out.  The confusion is easy to
    make and worth naming, since ``p`` and ``pbar`` differ by up to 0.4 here.
    """
    return 1.0 + math.exp(-4.0 * rho)


def entangled_probe(lam: float) -> np.ndarray:
    """``sqrt(lam)|00> + sqrt(1-lam)|11>``.  lam = 1/2 is Bell, lam -> 0 or 1 product."""
    return np.array([math.sqrt(lam), 0.0, 0.0, math.sqrt(1.0 - lam)], dtype=complex)


def probe_codeword(rho: float, phi: float, psi: float, lam: float = 0.5,
                   norm: str = "spectral") -> tuple:
    """The R6 encoding with the probe's entanglement and the normalisation free.

    Both are the obvious places a ceiling could be an artifact rather than a
    fact, so both are made variable and swept.
    """
    M = to_sl2(swirl_point(rho, phi, psi))
    scale = (float(np.linalg.norm(M, 2)) if norm == "spectral"
             else float(np.linalg.norm(M, "fro")))
    A = M / scale
    v = np.kron(np.eye(2), A) @ entangled_probe(lam)
    p = float(np.real(v.conj() @ v))
    W = np.zeros((5, 5), dtype=complex)
    W[:4, :4] = np.outer(v, v.conj())
    W[4, 4] = 1.0 - p
    return W, p


def probe_codebook(rho: float, n: int, lam: float = 0.5,
                   norm: str = "spectral") -> list:
    return [probe_codeword(rho, 2 * math.pi * k / n, 2 * math.pi * (k * 3 % n) / n,
                           lam, norm)[0] for k in range(n)]


def probe_sweep(rho: float = 8.0, n: int = 64,
                lams=(0.5, 0.4, 0.3, 0.2, 0.1, 0.02)) -> dict:
    """Is the 1-bit ceiling a property of the Bell probe, or the best it can do?

    The best it can do.  chi is MAXIMISED at lam = 1/2 and falls monotonically as
    the probe is de-entangled, so 1 bit is the optimum over this family rather
    than an artifact of choosing a convenient probe.

    The sweep also narrows a statement from R6d.  That round found that a
    fixed-depth codebook has an uninformative erasure flag, and attributed it to
    the shared depth.  The actual condition is equal ``p_i``, and equal depth
    implies that ONLY for the maximally entangled probe, where
    ``p = tr(A^T A)/2`` does not depend on orientation.  At lam = 0.3 the
    per-codeword spread is 0.4 and the flag carries 0.059 bits -- reporting the
    codeword's ORIENTATION, not its depth.
    """
    rows = []
    for lam in lams:
        book = probe_codebook(rho, n, lam)
        ps = [probe_codeword(rho, 2 * math.pi * k / n, 0.0, lam)[1]
              for k in range(n)]
        d = flag_success_decomposition(book)
        rows.append({"lam": lam, "chi": holevo_chi(book), "p_bar": d["p_bar"],
                     "success_branch_bits": d["success_branch_bits"],
                     "flag_bits": d["flag_bits"],
                     "per_codeword_p_spread": max(ps) - min(ps)})
    best = max(rows, key=lambda r: r["chi"])
    return {"rho": rho, "n": n, "rows": rows, "best_lam": best["lam"],
            "best_chi": best["chi"],
            "chi_is_monotone_in_entanglement": all(
                rows[i]["chi"] >= rows[i + 1]["chi"] - 1e-12
                for i in range(len(rows) - 1))}


def normalisation_control(rho: float = 8.0, n: int = 64) -> dict:
    """Spectral against Frobenius: does the ceiling depend on how we normalise?"""
    out = {}
    for norm in ("spectral", "frobenius"):
        book = probe_codebook(rho, n, 0.5, norm)
        d = flag_success_decomposition(book)
        out[norm] = {"chi": holevo_chi(book), "p_bar": d["p_bar"]}
    out["identical"] = abs(out["spectral"]["chi"] - out["frobenius"]["chi"]) < 1e-9
    return out


def sl2_codeword(rho: float, phi: float, psi: float) -> np.ndarray:
    return attempted_use_state(to_sl2(swirl_point(rho, phi, psi)))[0].astype(complex)


def su2_matrix(alpha: float, beta: float, gamma: float) -> np.ndarray:
    """A genuine SU(2) element from three Euler angles.

    Three real parameters, and it matters.  The first version of the baseline
    used real 2x2 rotations -- a ONE-parameter family -- which reaches only a
    circle inside the maximally entangled states and gave a spurious ceiling of
    1 bit, accidentally matching the non-compact side and erasing the very
    contrast the control exists to provide.
    """
    return np.array([
        [math.cos(beta / 2) * np.exp(1j * (alpha + gamma) / 2),
         math.sin(beta / 2) * np.exp(1j * (alpha - gamma) / 2)],
        [-math.sin(beta / 2) * np.exp(-1j * (alpha - gamma) / 2),
         math.cos(beta / 2) * np.exp(-1j * (alpha + gamma) / 2)]])


def su2_codeword(U) -> np.ndarray:
    """The same Bell probe with a COMPACT group: pure, p = 1, no erasure branch."""
    v = np.kron(np.eye(2), np.asarray(U)) @ BELL
    W = np.zeros((5, 5), dtype=complex)
    W[:4, :4] = np.outer(v, v.conj())
    return W


def grid_codebook(rho: float, n: int) -> list:
    """Deterministic evenly-spaced angular codebook at one depth."""
    return [sl2_codeword(rho, 2 * math.pi * k / n, 2 * math.pi * (k * 3 % n) / n)
            for k in range(n)]


def su2_codebook(n: int, seed: int = 5) -> list:
    """Matched compact baseline: same probe, same dimension, same sizes."""
    rng = np.random.default_rng(seed)
    return [su2_codeword(su2_matrix(*rng.uniform(0, 2 * math.pi, 3)))
            for _ in range(n)]


def packing_number(radius: float, eps: float, samples: int = 1200,
                   seed: int = 7) -> int:
    """Greedy count of eps-separated states drawn out to source radius `radius`.

    Greedy packing under-counts the true packing number, so this is a LOWER
    bound.  That is the safe direction: the claim is that the count fails to
    grow, and an under-count cannot manufacture a failure to grow.
    """
    rng = np.random.default_rng(seed)
    kept: list = []
    for _ in range(samples):
        p = (rng.uniform(0.05, radius), rng.uniform(-math.pi, math.pi),
             rng.uniform(-math.pi, math.pi))
        M = to_sl2(swirl_point(*p))
        if all(trace_distance_closed_form(M, to_sl2(swirl_point(*q))) > eps
               for q in kept):
            kept.append(p)
    return len(kept)


def packing_log_slope(eps: float, radii=(4.0, 5.0, 6.0), samples: int = 1200,
                      seed: int = 7) -> dict:
    """``d log2(packing) / d R``.  The source exponent is 2; this should be ~0."""
    counts = [packing_number(R, eps, samples, seed) for R in radii]
    slope = ((math.log2(counts[-1]) - math.log2(counts[0]))
             / (radii[-1] - radii[0]))
    return {"eps": eps, "radii": list(radii), "counts": counts,
            "log2_slope": slope, "source_exponent": 2.0}


def ceiling_report(rho: float, sizes=(8, 16, 32, 64, 100)) -> dict:
    """chi against log2 N at fixed depth, with the compact baseline alongside."""
    rows = []
    for n in sizes:
        chi_nc = holevo_chi(grid_codebook(rho, n))
        chi_c = holevo_chi(su2_codebook(n))
        rows.append({"n": n, "log2_n": math.log2(n),
                     "chi_non_compact": chi_nc, "chi_compact": chi_c,
                     "ceiling": holevo_ceiling(rho),
                     "ratio": chi_c / chi_nc if chi_nc > 0 else None})
    return {"rho": rho, "rows": rows,
            "chi_spread_over_sizes": max(r["chi_non_compact"] for r in rows)
                                     - min(r["chi_non_compact"] for r in rows),
            "log2_n_spread": max(r["log2_n"] for r in rows)
                             - min(r["log2_n"] for r in rows)}
