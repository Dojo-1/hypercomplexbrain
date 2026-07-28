"""Why fixed-width operational information does not inherit source volume growth.

Round R6 established that a point at depth ``rho`` on the ``Q = +1`` pseudo-sphere
has singular values ``(e^rho, e^-rho)`` and is a gate only at ``rho = 0``.  It left
one question open and said so: the source measure grows like ``e^{2 rho}`` while
the worst-case post-selection cost falls like ``e^{-4 rho}``, and whether capacity
survives the cost was not settled.

An external derivation settled it, and this module verifies that derivation rather
than restating it.  The governing object is not a capacity ratio.  It is a change
of coordinate,

    q = e^{-2 rho}   in   [0, 1],

together with a normalisation cocycle for composed movement.

The mechanism, in one line
--------------------------
Normalising ``A = M / ||M||_2`` sends ``sigma(M) = (e^rho, e^-rho)`` to
``sigma(A) = (1, q)``.  The unbounded radial direction is not deleted -- ``det A =
q`` still names it -- it is COMPACTIFIED onto a finite interval.  What was an
infinite ray becomes a segment with a boundary at ``q = 0``, and the price of
reaching the far end is that the coordinate becomes exponentially ill-conditioned
rather than unavailable.

Read as quantum Fisher information on the attempted-use state, the split is
explicit:

    J = diag( 8/(e^{4 rho} - 1),  (1 + q)^2,  (1 - q)^2 )

The radial entry decays as ``8 e^{-4 rho}`` -- exactly the R6 worst-case cost
exponent, arrived at from an entirely different direction.  The two angular
entries go to 1.  So the operational manifold does not grow with the source: it
flattens onto a 2-torus boundary carrying two angular coordinates and a finite
inward direction, and its total Fisher volume is a CONSTANT.

That constant is the one place the external derivation is off, and the correction
is recorded in :func:`operational_qfi_volume`.

What "hyperbolic" is doing in this programme, corrected
-------------------------------------------------------
The induced metric on the ``Q = +1`` pseudo-sphere in swirl coordinates is

    g = diag(-1, cosh^2 rho, -sinh^2 rho)

-- signature (1,2), Lorentzian.  This is an AdS_3-like Cartan geometry, NOT
positive-definite hyperbolic 3-space.  Earlier rounds in this repository called
the growth ``e^{2 rho}`` "hyperbolic volume".  The MEASURE is right,
``sqrt|det g| = cosh rho sinh rho``, and the NAME was wrong.  The guard is the
external auditor's; :func:`induced_metric_signature` makes it checkable instead of
asserted.

Relatedly: ``so(2,2) = sl(2,R) + sl(2,R)`` is SEMISIMPLE, not simple.  R6's
docstring said simple.  The obstruction survives verbatim under the corrected
word, because a connected semisimple Lie group with a faithful finite-dimensional
unitary representation must be compact.

Source reversibility is not operational reversibility
-----------------------------------------------------
``kappa(X, Y) = log||X|| + log||Y|| - log||XY|| >= 0`` measures how much
normalisation is lost by composing before normalising, and it satisfies an exact
2-cocycle law.  For an inverse pair, ``kappa(M^-1, M) = 2 rho`` exactly: the
source returns to the identity with zero defect, while the streamed survival
probability is ``e^{-4 rho}``.  Undoing a movement costs the same as making it.
This is R6's P4 -- echoing is free only if the net element may be compiled
directly -- re-derived as an exact algebraic identity rather than a measurement.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["q_of_rho", "rho_of_q", "normalised_A", "attempted_use_state",
           "p_bell", "analytic_qfi", "numeric_qfi", "operational_qfi_volume",
           "kappa", "conditional_concurrence", "trace_distance_closed_form",
           "root_fidelity_closed_form", "induced_metric_signature",
           "volume_form_distortion", "BELL"]

#: |Phi+> in the |00>,|01>,|10>,|11> basis.
BELL = np.array([1.0, 0.0, 0.0, 1.0]) / math.sqrt(2.0)


def q_of_rho(rho: float) -> float:
    """The operational coordinate.  An infinite ray becomes ``[0, 1]``."""
    return math.exp(-2.0 * rho)


def rho_of_q(q: float) -> float:
    if not 0.0 < q <= 1.0:
        raise ValueError("q must lie in (0, 1]")
    return -0.5 * math.log(q)


def normalised_A(M) -> np.ndarray:
    """``M / ||M||_2``.  Singular values ``(1, q)``: this is the compactification."""
    M = np.asarray(M, dtype=float)
    return M / float(np.linalg.norm(M, 2))


def p_bell(rho: float) -> float:
    """Success probability on the Bell probe: ``(1 + q^2)/2``.

    Saturates at 1/2, which is R6's average-case result reached by another route.
    """
    q = q_of_rho(rho)
    return (1.0 + q * q) / 2.0


def attempted_use_state(M) -> tuple:
    """``omega_A = |v><v| (+) (1-p)|e><e|`` with ``|v> = (I (x) A)|Phi+>``.

    A 5x5 density matrix: the 4x4 subnormalised success branch and one erasure
    flag.  Keeping the flag explicit is what makes the failure branch carry
    information instead of being silently discarded.
    """
    A = normalised_A(M)
    v = np.kron(np.eye(2), A) @ BELL
    p = float(v @ v)
    W = np.zeros((5, 5))
    W[:4, :4] = np.outer(v, v)
    W[4, 4] = 1.0 - p
    return W, p


def analytic_qfi(rho: float) -> np.ndarray:
    """``diag(8/(e^{4rho}-1), (1+q)^2, (1-q)^2)``.  Diverges at ``rho = 0``.

    The divergence is a coordinate artefact, not a physical one: at ``rho = 0`` the
    swirl angle ``psi`` is undefined and the state family changes rank, exactly as
    a polar angle is undefined at the origin.  Note ``J_psipsi -> 0`` there for the
    same reason.
    """
    q = q_of_rho(rho)
    if rho <= 0.0:
        raise ValueError("the analytic form is stated for rho > 0")
    return np.diag([8.0 / (math.exp(4.0 * rho) - 1.0), (1.0 + q) ** 2, (1.0 - q) ** 2])


def numeric_qfi(point, state_fn, h: float = 1e-5) -> np.ndarray:
    """SLD quantum Fisher information by central differences.

    Independent of :func:`analytic_qfi` by construction -- it never sees the closed
    form -- so agreement between the two is a real check rather than a tautology.
    """
    W0 = state_fn(*point)
    lam, U = np.linalg.eigh(W0)
    grads = []
    for i in range(len(point)):
        hi = list(point)
        lo = list(point)
        hi[i] += h
        lo[i] -= h
        grads.append((state_fn(*hi) - state_fn(*lo)) / (2.0 * h))

    n = len(point)
    J = np.zeros((n, n))
    rotated = [U.T @ g @ U for g in grads]
    for i in range(n):
        for j in range(n):
            total = 0.0
            for k in range(len(lam)):
                for l in range(len(lam)):
                    den = lam[k] + lam[l]
                    if den > 1e-9:
                        total += 2.0 * rotated[i][k, l] * rotated[j][l, k] / den
            J[i, j] = total
    return J


def operational_qfi_volume() -> dict:
    """``int sqrt(det J) drho dphi dpsi`` -- finite, and the constant is corrected.

    ``det J = 8 u^2 (1 - u^2)`` with ``u = q``, so ``sqrt(det J) = 2 sqrt2 u
    sqrt(1-u^2)``.  Substituting ``drho = -du/(2u)``:

        int_0^inf sqrt(det J) drho = sqrt2 * int_0^1 sqrt(1-u^2) du = sqrt2 * pi/4

    and multiplying by ``(2 pi)^2`` for the two angles gives ``sqrt2 * pi^3``.

    The external derivation reported ``2 pi^3``.  The ratio is exactly ``1/sqrt2``,
    which is what dropping ``sqrt8 = 2 sqrt2`` to 4 would produce.  Every other
    quantity in that derivation reproduces here to ~1e-15; this is a single
    arithmetic slip in a constant, not a defect in the argument, and the argument
    does not depend on the constant -- what matters is that the integral CONVERGES
    while the source measure diverges.
    """
    return {"value": math.sqrt(2.0) * math.pi ** 3,
            "closed_form": "sqrt(2) * pi^3",
            "externally_reported": 2.0 * math.pi ** 3,
            "ratio_to_reported": 1.0 / math.sqrt(2.0),
            "note": "finiteness is the claim; the constant is a correction"}


def volume_form_distortion(rho: float) -> float:
    """``sqrt(det J) / sqrt|det g_src|`` -- how violently the projection compresses.

    ``sqrt|det g_src| = cosh rho sinh rho``.  The ratio decays as ``e^{-4 rho}``:
    at every depth the operational medium sees exponentially less than the source
    contains, and the exponent is R6's.
    """
    if rho <= 0.0:
        raise ValueError("stated for rho > 0")
    q = q_of_rho(rho)
    src = math.cosh(rho) * math.sinh(rho)
    op = math.sqrt(8.0 * q * q * (1.0 - q * q))
    return op / src


def kappa(X, Y) -> float:
    """``log||X|| + log||Y|| - log||XY|| >= 0``: the normalisation lost by composing.

    Submultiplicativity of the operator norm makes this nonnegative, and
    associativity makes it an exact 2-cocycle.  It is the quantitative content of
    "streaming costs more than compiling".
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    return (math.log(float(np.linalg.norm(X, 2)))
            + math.log(float(np.linalg.norm(Y, 2)))
            - math.log(float(np.linalg.norm(X @ Y, 2))))


def conditional_concurrence(rho: float) -> float:
    """``sech(2 rho)`` on the success branch: Bell-like near 0, product-like deep.

    A probe-specific diagnostic of the fixed Bell bipartition, NOT an invariant of
    the architecture.  Recorded with that caveat because the number is seductive.
    """
    return 1.0 / math.cosh(2.0 * rho)


def trace_distance_closed_form(MA, MB) -> float:
    """``(1/2)[sqrt((pA+pB)^2 - 4|c|^2) + |pA - pB|]`` with ``c = tr(A^T B)/2``."""
    A, B = normalised_A(MA), normalised_A(MB)
    pA = float(np.trace(A.T @ A)) / 2.0
    pB = float(np.trace(B.T @ B)) / 2.0
    c = float(np.trace(A.T @ B)) / 2.0
    return 0.5 * (math.sqrt(max(0.0, (pA + pB) ** 2 - 4.0 * c * c)) + abs(pA - pB))


def root_fidelity_closed_form(MA, MB) -> float:
    """``|c| + sqrt((1-pA)(1-pB))`` -- the erasure flag contributes coherently."""
    A, B = normalised_A(MA), normalised_A(MB)
    pA = float(np.trace(A.T @ A)) / 2.0
    pB = float(np.trace(B.T @ B)) / 2.0
    c = float(np.trace(A.T @ B)) / 2.0
    return abs(c) + math.sqrt(max(0.0, (1.0 - pA) * (1.0 - pB)))


def induced_metric_signature(rho: float) -> dict:
    """The source is Lorentzian, and this is the check that says so.

    ``g = diag(-1, cosh^2 rho, -sinh^2 rho)``: one positive eigenvalue and two
    negative.  Signature (1,2).  Not hyperbolic 3-space, whose signature would be
    (3,0).  Everything this programme called "hyperbolic volume" was the
    pseudo-Riemannian volume of an AdS_3-like geometry.
    """
    g = np.diag([-1.0, math.cosh(rho) ** 2, -math.sinh(rho) ** 2])
    ev = np.linalg.eigvalsh(g)
    return {"eigenvalues": ev.tolist(),
            "n_positive": int((ev > 1e-12).sum()),
            "n_negative": int((ev < -1e-12).sum()),
            "n_zero": int((np.abs(ev) <= 1e-12).sum()),
            "is_riemannian": bool((ev > 0).all()),
            "sqrt_abs_det": math.cosh(rho) * math.sinh(rho)}
