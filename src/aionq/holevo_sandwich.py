"""How much of the source a fixed-width channel can actually hand over.

R6b showed the radial coordinate compactifies: the Fisher information along
depth decays as ``8 e^{-4 rho}`` while the two angular directions saturate.  That
is a statement about *distinguishing nearby points*.  This module asks the other
question -- how many bits a receiver can actually read out of a finite codebook --
and bounds it from both sides:

    I_PGM  <=  I_acc  <=  chi  <=  log2 N

Only the outer three are computable.  ``I_acc`` is a maximisation over all POVMs
and is left as a bracket rather than estimated, because an estimate of it would
be the one number here that could be quietly tuned.

The flag decomposition, exactly
-------------------------------
Every codeword state is block diagonal in the same success/erasure split,

    omega_i = |v_i><v_i|  (+)  (1 - p_i) |e><e|,

so the flag is a classical register that every state shares.  Writing
``sigma = (1/N) sum_i p_i |vhat_i><vhat_i|`` with trace ``pbar``:

    chi  =  pbar * S(sigmahat)  +  [ h2(pbar) - <h2(p_i)> ]
            \_______________/     \____________________/
             success branch          the flag itself

The second bracket is a Jensen gap and is nonnegative because ``h2`` is concave.
It is exactly zero when every codeword sits at the same depth, which is the usual
case -- so in a fixed-depth codebook the erasure flag carries NO information, and
all of ``chi`` lives in the success branch weighted by survival.  That is worth
stating because "the flag tells you something" is a plausible-sounding way to
recover bits that are not there.

Data processing, and the direction that matters
-----------------------------------------------
A parameter-independent CPTP map applied after encoding cannot increase ``chi``,
cannot increase trace distance, and cannot decrease fidelity.  The tempting wrong
test is ``I_PGM(Phi(ensemble)) <= I_PGM(ensemble)``, which is NOT implied: the PGM
is a specific measurement chosen for whichever ensemble it is given, and choosing
a better measurement for a worse ensemble can beat a worse measurement for a
better one.  The correct statement is ``I_PGM(Phi(ensemble)) <= chi(ensemble)``,
and that is what is checked.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["von_neumann_entropy", "binary_entropy", "holevo_chi",
           "flag_success_decomposition", "pgm_povm", "pgm_analysis",
           "pgm_diagnostics", "pgm_mutual_information", "random_cptp",
           "apply_channel", "information_sandwich"]

_TOL = 1e-12


def _spectrum(rho) -> np.ndarray:
    w = np.linalg.eigvalsh((np.asarray(rho) + np.asarray(rho).conj().T) / 2.0)
    return np.real(w)


def von_neumann_entropy(rho) -> float:
    """``-tr(rho log2 rho)``, with zero eigenvalues contributing zero.

    Eigenvalues below tolerance are dropped rather than clipped: ``0 log 0 = 0``
    is the correct limit, and clipping to a small positive number would inject a
    spurious positive entropy exactly where the state is pure.
    """
    w = _spectrum(rho)
    w = w[w > _TOL]
    return float(-np.sum(w * np.log2(w)))


def binary_entropy(p: float) -> float:
    if p <= _TOL or p >= 1.0 - _TOL:
        return 0.0
    return float(-p * math.log2(p) - (1 - p) * math.log2(1 - p))


def holevo_chi(states, priors=None) -> float:
    """``S(sum_i q_i rho_i) - sum_i q_i S(rho_i)``."""
    states = [np.asarray(s) for s in states]
    n = len(states)
    q = np.full(n, 1.0 / n) if priors is None else np.asarray(priors, dtype=float)
    mean = sum(qi * s for qi, s in zip(q, states))
    return von_neumann_entropy(mean) - float(sum(qi * von_neumann_entropy(s)
                                                 for qi, s in zip(q, states)))


def flag_success_decomposition(states, flag_index: int = 4) -> dict:
    """Split ``chi`` into the success branch and the flag, exactly.

    ``states`` are the block-diagonal ``omega_i``; ``flag_index`` is the erasure
    basis element.  Returns both terms and the reconstruction residual, so the
    identity is asserted rather than assumed.
    """
    states = [np.asarray(s) for s in states]
    n = len(states)
    keep = [i for i in range(states[0].shape[0]) if i != flag_index]
    ps = np.array([float(np.real(np.trace(s[np.ix_(keep, keep)]))) for s in states])
    pbar = float(np.mean(ps))

    sigma = sum(s[np.ix_(keep, keep)] for s in states) / n
    s_sigma_hat = von_neumann_entropy(sigma / pbar) if pbar > _TOL else 0.0
    jensen_gap = binary_entropy(pbar) - float(np.mean([binary_entropy(p) for p in ps]))
    reconstructed = pbar * s_sigma_hat + jensen_gap
    return {"p_bar": pbar,
            "success_branch_bits": pbar * s_sigma_hat,
            "flag_bits": jensen_gap,
            "reconstructed_chi": reconstructed,
            "direct_chi": holevo_chi(states),
            "residual": abs(reconstructed - holevo_chi(states)),
            "flag_is_informative": jensen_gap > 1e-9}


def _validated_pgm_inputs(states, priors=None) -> tuple[list[np.ndarray], np.ndarray]:
    states = [np.asarray(state, dtype=complex) for state in states]
    if not states:
        raise ValueError("at least one state is required")
    shape = states[0].shape
    if len(shape) != 2 or shape[0] != shape[1]:
        raise ValueError("states must be square matrices")
    for state in states:
        if state.shape != shape or not np.all(np.isfinite(state)):
            raise ValueError("states must be finite and have one common shape")
        hermitian = (state + state.conj().T) / 2.0
        if np.linalg.norm(state - state.conj().T, "fro") > 1e-10:
            raise ValueError("states must be Hermitian")
        if float(np.min(np.linalg.eigvalsh(hermitian))) < -1e-10:
            raise ValueError("states must be positive semidefinite")
        if abs(complex(np.trace(state)) - 1.0) > 1e-10:
            raise ValueError("states must have unit trace")

    count = len(states)
    q = (
        np.full(count, 1.0 / count)
        if priors is None
        else np.asarray(priors, dtype=float)
    )
    if (
        q.shape != (count,)
        or not np.all(np.isfinite(q))
        or np.any(q <= 0.0)
    ):
        raise ValueError("priors must be finite strictly positive weights")
    if abs(float(np.sum(q)) - 1.0) > _TOL:
        raise ValueError("priors must sum to one")
    return states, q


def _pgm_components(states, priors=None):
    states, q = _validated_pgm_inputs(states, priors)
    mean = sum(qi * state for qi, state in zip(q, states))
    hermitian_mean = (mean + mean.conj().T) / 2.0
    values, vectors = np.linalg.eigh(hermitian_mean)
    maximum = max(0.0, float(np.max(np.real(values))))
    cutoff = (
        64.0
        * np.finfo(float).eps
        * mean.shape[0]
        * maximum
    )
    mask = np.real(values) > cutoff
    support = vectors[:, mask]
    projector = support @ support.conj().T
    inverse_sqrt = (
        support
        @ np.diag(1.0 / np.sqrt(np.real(values[mask])))
        @ support.conj().T
    )
    effects = [
        inverse_sqrt @ (qi * state) @ inverse_sqrt
        for qi, state in zip(q, states)
    ]
    return states, q, effects, projector, cutoff


def pgm_povm(states, priors=None) -> list:
    """Pretty-good measurement: ``E_i = rhobar^{-1/2} q_i rho_i rhobar^{-1/2}``."""
    return _pgm_components(states, priors)[2]


def pgm_analysis(states, priors=None, *, guard_tolerance: float = 1e-10) -> dict:
    """PGM information plus the numerical guards applied before repair.

    The PGM effects sum to the projector onto the support of the mean state,
    rather than necessarily to the ambient identity.  Every ensemble state is
    supported there, so the raw conditional-probability rows must still sum to
    one.  Tiny negative values are clipped and rows are normalized only after
    these raw quantities have been recorded.
    """
    states, q, effects, projector, cutoff = _pgm_components(states, priors)
    completeness = sum(effects, np.zeros_like(states[0]))
    support_defect = float(np.linalg.norm(completeness - projector, 2))
    complex_raw = np.array(
        [
            [np.trace(effect @ state) for effect in effects]
            for state in states
        ],
        dtype=complex,
    )
    raw = np.real(complex_raw)
    minimum_raw = float(np.min(raw))
    maximum_row_defect = float(
        np.max(np.abs(np.sum(raw, axis=1) - 1.0))
    )
    maximum_imaginary = float(np.max(np.abs(np.imag(complex_raw))))
    guards_hold = bool(
        minimum_raw >= -guard_tolerance
        and maximum_row_defect <= guard_tolerance
        and support_defect <= guard_tolerance
        and maximum_imaginary <= guard_tolerance
    )

    conditional = np.clip(raw, 0.0, None)
    row_sums = np.sum(conditional, axis=1, keepdims=True)
    if np.any(row_sums <= _TOL):
        mutual_information = 0.0
        guards_hold = False
    else:
        conditional = conditional / row_sums
        joint = q[:, None] * conditional
        px = np.sum(joint, axis=1)
        py = np.sum(joint, axis=0)
        mutual_information = 0.0
        for i in range(len(states)):
            for j in range(len(effects)):
                if joint[i, j] > _TOL and px[i] > _TOL and py[j] > _TOL:
                    mutual_information += joint[i, j] * math.log2(
                        joint[i, j] / (px[i] * py[j])
                    )
    return {
        "I_PGM": float(mutual_information),
        "support_projector_defect": support_defect,
        "support_cutoff": float(cutoff),
        "minimum_raw_probability": minimum_raw,
        "maximum_row_sum_defect": maximum_row_defect,
        "maximum_imaginary_probability": maximum_imaginary,
        "mean_state_rank": int(round(float(np.real(np.trace(projector))))),
        "numerical_guards_hold": guards_hold,
    }


def pgm_diagnostics(states, priors=None) -> dict:
    """Compatibility projection of :func:`pgm_analysis` diagnostics."""
    return pgm_analysis(states, priors)


def pgm_mutual_information(states, priors=None) -> float:
    """``I(X;Y)`` for the PGM -- a LOWER bound on accessible information.

    A concrete measurement really performed, so this is achievable, unlike
    ``I_acc`` which is a supremum nobody in this round computes.
    """
    return float(pgm_analysis(states, priors)["I_PGM"])


def random_cptp(dim: int, n_kraus: int, rng) -> list:
    """A random CPTP map by Stinespring: isometry then partial trace.

    Built to satisfy ``sum K^dag K = I`` by construction rather than by
    normalisation afterwards, so the completeness relation is exact.
    """
    G = rng.normal(size=(dim * n_kraus, dim)) + 1j * rng.normal(size=(dim * n_kraus, dim))
    Q, _ = np.linalg.qr(G)                     # isometry: Q^dag Q = I
    return [Q[k * dim:(k + 1) * dim, :] for k in range(n_kraus)]


def apply_channel(rho, kraus) -> np.ndarray:
    return sum(K @ np.asarray(rho) @ K.conj().T for K in kraus)


def information_sandwich(states, priors=None) -> dict:
    """``I_PGM <= I_acc <= chi <= log2 N``, with the middle left as a bracket."""
    n = len(states)
    chi = holevo_chi(states, priors)
    ipgm = pgm_mutual_information(states, priors)
    oracle = math.log2(n) if n > 1 else 0.0
    return {"n_codewords": n, "I_PGM": ipgm, "chi": chi, "log2_N": oracle,
            "I_acc_bracket": [ipgm, chi],
            "ordering_holds": bool(
                ipgm <= chi + 1e-9 and chi <= oracle + 1e-9
            ),
            "note": "I_acc is a supremum over all POVMs and is deliberately not "
                    "estimated; it is reported as the bracket [I_PGM, chi]"}
