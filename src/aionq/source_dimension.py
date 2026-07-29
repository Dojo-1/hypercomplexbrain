"""Which "dimension" does the ceiling actually count?

Three senses of the word get used interchangeably around this programme, and the
R6 arc turns on keeping them apart:

    HILBERT       degrees of freedom in the carrier state.  Abstract.  The R6
                  encoding uses n^2 + 1 = 5 at n = 2.  This is what
                  ``holevo_ceiling_general(D, p_bar) = p_bar log2 D`` counts.
    SOURCE        real dimension of the geometric manifold being encoded.
                  SL(2,R) is 3-dimensional; SL(2,C) is 6.  This is where the
                  exponential measure growth e^{2 rho} lives.
    ENGINEERED    physically restrained systems -- 2D sheets, 1D wires.  Not
                  touched here; named so the taxonomy is complete.

The R6 result reads, in those terms: **the exponential growth is a SOURCE fact
and the ceiling is a HILBERT fact, and the first does not transfer to the
second.**  This module measures the non-transfer instead of asserting it.

The experiment
--------------
Hold the carrier fixed at n = 2 (five dimensions) and DOUBLE the source: encode
SL(2,C), a 6-real-dimensional non-compact group, through the identical recipe
that encodes 3-dimensional SL(2,R).  Same matrix size, same probe, same
normalisation, same codebook structure.  Only the source manifold grows.

What was found, including the part I first got wrong
----------------------------------------------------
My first summary line said the extra dimensions buy "zero".  That contradicted
my own table on the line above it: at rho = 0.5 the richer source scores 1.042
against 0.949, a gap of 9.3e-02.  Extra source dimensions DO buy something.

What they buy is transient, and the rate is the finding:

    rho     gap          d(ln gap)/d(rho)
    1.0     1.313e-02        3.9222
    1.5     1.787e-03        3.9894
    2.0     2.420e-04        3.9986
    3.0     4.432e-06        3.9999
    4.0     8.118e-08        4.0000

The advantage decays as ``e^{-4 rho}`` -- the SAME exponent as the radial quantum
Fisher information ``8 e^{-4 rho}`` from R6b and the same as the worst-case
post-selection cost from R6.  At the boundary both sources give exactly
1.000000000, agreeing to 9.6e-15 despite one having twice the dimension.

So the ceiling does not merely BOUND the extra source dimensions.  It CONSUMES
them, at the characteristic rate of the compactification.  Adding dimensions to
the source buys a head start that the geometry then eats at e^{-4 rho}; only
adding dimensions to the CARRIER changes the asymptote.

Scope
-----
One encoding recipe, one probe, one codebook family.  No claim that this holds
for every map from every non-compact group.  ``n = 3`` is deliberately not used
for the headline: an SL(3,R) run gives chi = 2/3, but its codebook explores only
a two-angle subgroup of a larger space, so that number is codebook-limited
rather than ceiling-limited and would be misread as a dimension effect.
"""

from __future__ import annotations

import math

import numpy as np

from aionq.holevo_sandwich import flag_success_decomposition, holevo_chi

__all__ = ["encode_at_size", "sl2r_element", "sl2c_element", "source_gap_sweep",
           "decay_exponent"]


def encode_at_size(M, n: int):
    """The R6 recipe at any matrix size: normalise, act on half of |Phi_n>."""
    A = np.asarray(M, dtype=complex) / float(np.linalg.norm(M, 2))
    phi = np.eye(n).reshape(-1) / math.sqrt(n)
    v = np.kron(np.eye(n), A) @ phi
    p = float(np.real(v.conj() @ v))
    D = n * n
    W = np.zeros((D + 1, D + 1), dtype=complex)
    W[:D, :D] = np.outer(v, v.conj())
    W[D, D] = 1.0 - p
    return W, p


def sl2r_element(rho: float, a: float, b: float) -> np.ndarray:
    """SL(2,R) in KAK form.  Real dimension 3."""
    def R(t):
        return np.array([[math.cos(t), -math.sin(t)],
                         [math.sin(t), math.cos(t)]], dtype=complex)
    return R(a) @ np.diag([math.exp(rho), math.exp(-rho)]).astype(complex) @ R(b)


def sl2c_element(rho: float, a: float, b: float, phase: float) -> np.ndarray:
    """SL(2,C).  Real dimension 6 -- twice SL(2,R), same 2x2 matrix size."""
    def U(t, p_):
        return np.array([[math.cos(t) * np.exp(1j * p_), -math.sin(t)],
                         [math.sin(t), math.cos(t) * np.exp(-1j * p_)]],
                        dtype=complex)
    return (U(a, phase)
            @ np.diag([math.exp(rho), math.exp(-rho)]).astype(complex)
            @ U(b, -phase))


def source_gap_sweep(depths=(0.5, 1.0, 1.5, 2.0, 3.0, 4.0), n_code: int = 64) -> dict:
    """chi for a 3-dimensional and a 6-dimensional source at matched carrier."""
    rows = []
    for rho in depths:
        two_pi = 2.0 * math.pi
        bR = [encode_at_size(sl2r_element(rho, two_pi * k / n_code,
                                          two_pi * (3 * k % n_code) / n_code), 2)[0]
              for k in range(n_code)]
        bC = [encode_at_size(sl2c_element(rho, two_pi * k / n_code,
                                          two_pi * (3 * k % n_code) / n_code,
                                          two_pi * (5 * k % n_code) / n_code), 2)[0]
              for k in range(n_code)]
        cR, cC = holevo_chi(bR), holevo_chi(bC)
        rows.append({"rho": rho, "chi_source_dim_3": cR, "chi_source_dim_6": cC,
                     "gap": abs(cC - cR),
                     "p_bar": flag_success_decomposition(bR, flag_index=4)["p_bar"]})
    return {"rows": rows, "carrier_dim": 5,
            "boundary_gap": rows[-1]["gap"],
            "richer_source_helps_at_finite_depth": rows[0]["gap"] > 1e-3}


def decay_exponent(sweep: dict) -> dict:
    """``-d(ln gap)/d(rho)``.  Converges to 4, the compactification exponent."""
    rows = sweep["rows"]
    exps = []
    for i in range(1, len(rows)):
        g0, g1 = rows[i - 1]["gap"], rows[i]["gap"]
        dr = rows[i]["rho"] - rows[i - 1]["rho"]
        if g0 > 0 and g1 > 0:
            exps.append(-(math.log(g1) - math.log(g0)) / dr)
    return {"exponents": exps, "final": exps[-1] if exps else None,
            "matches_four": bool(exps and abs(exps[-1] - 4.0) < 1e-3)}
