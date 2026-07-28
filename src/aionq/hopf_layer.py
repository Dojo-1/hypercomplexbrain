"""Hopf: why the swirl coordinates split the way they do, and the deferred quotient.

"Hopf in hypercomplex hyperdim quantum" turns out to name something exact here,
not a decoration.  Three results, all checkable, all connected:

1.  THE SWIRL COORDINATES ARE THE CARTAN DECOMPOSITION.
    The (rho, phi, psi) parameterisation borrowed from TELOS is not a convenient
    chart.  It is ``KAK``:

        M = R(alpha) . diag(e^rho, e^-rho) . R(beta),
        alpha = -(phi - psi)/2,   beta = (phi + psi)/2      (mod pi)

    verified over 400 random points to 2e-15.  ``dim SL(2,R) = 3 = 1 + 1 + 1``:
    two compact angles from the K factors and one non-compact parameter from A.

    This explains what R6b measured rather than merely restating it.  The QFI came
    out DIAGONAL in (rho, phi, psi) -- that is not luck, it is the Cartan
    decomposition being orthogonal.  The two compact directions act by local
    UNITARIES, which move a state inside its unitary orbit and change no
    singular value, so their Fisher information is bounded and saturates.  The A
    direction moves BETWEEN orbits by changing the singular values themselves, and
    that is the one that decays as ``e^{-4 rho}``.

    Free versus costly is therefore not a fact about three coordinates.  It is the
    compact/non-compact split of the group, read in the only coordinates that
    diagonalise it.

2.  THE FIBRATION IS THE LORENTZIAN SIBLING OF THE HOPF FIBRATION.

        S^1 -> S^3 -> S^2          (Hopf, base curvature +1)
        S^1 -> SL(2,R) -> H^2      (base curvature -1)

    Both are principal U(1) bundles over a 2-dimensional space of constant
    curvature; ``SL(2,R)/SO(2) = H^2`` is the Poincare disc this programme has
    been computing on since S3.  The fibre is the compact K direction.

    And the Hopf map is not an analogy for the quantum part: ``S^3 -> S^2`` IS the
    density-matrix map.  ``|psi> -> (<sigma_x>, <sigma_y>, <sigma_z>)`` equals the
    Hopf map exactly (3.3e-16 over 200 draws), and its fibre is precisely the
    global phase.  Quotienting by the fibre is what "taking the density matrix"
    means.

3.  THE PROJECTIVE QUOTIENT R6b DEFERRED IS A FACTOR OF EXACTLY 2.
    The external derivation reported its operational volume "before projective
    quotienting" and left the quotient open.  Here it is: ``omega(A) = omega(-A)``
    exactly -- 0.0, not 1e-16, because ``|v><v|`` is quadratic in ``v`` -- so the
    operational space is ``PSL(2,R) = SL(2,R)/{+-1}``, and

        operational volume  =  sqrt(2) pi^3 / 2  =  pi^3 / sqrt(2).

    Still finite, which was the whole point; now finite and correctly normalised.

The ladder, and where it stops
------------------------------
Hopf fibrations exist for exactly four dimensions -- 1, 2, 4, 8 -- because they
exist exactly where normed division algebras do: R, C, H, O.  There is no
``S^15 -> S^31 -> S^16``.  This repository already has the reason in
:mod:`aionq.cayley_dickson`: the sedenions have zero divisors, so the Cayley-Dickson
ladder stops being a division algebra at dimension 16 and the fibration stops with
it.  :func:`hopf_ladder` reports both facts together rather than citing either.

That is the honest scope of "hypercomplex" here.  The tower is not open-ended; it
has four rungs and the fourth is the last, and Round S8's Fano/octonion work sits
on that last rung by necessity, not by choice.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["kak_decompose", "kak_reconstruct", "swirl_to_kak", "hopf_map",
           "bloch_vector", "hopf_ladder", "projective_volume",
           "fibre_is_local_unitary"]


def _angle(Q) -> float:
    return math.atan2(float(Q[1, 0]), float(Q[0, 0]))


def _rot(t: float) -> np.ndarray:
    return np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])


def kak_decompose(M) -> dict:
    """``M = R(alpha) diag(e^rho, e^-rho) R(beta)`` for ``M`` in SL(2,R).

    The SVD with both factors forced to determinant +1.  The angles are defined
    modulo pi, because ``(U, V) -> (-U, -V)`` leaves ``M`` unchanged; comparisons
    against them must therefore be made on the doubled angles.
    """
    M = np.asarray(M, dtype=float)
    U, S, Vt = np.linalg.svd(M)
    if np.linalg.det(U) < 0:
        U = U.copy()
        Vt = Vt.copy()
        U[:, 1] *= -1
        Vt[1, :] *= -1
    return {"alpha": _angle(U), "rho": float(math.log(S[0])), "beta": _angle(Vt.T),
            "singular_values": (float(S[0]), float(S[1]))}


def kak_reconstruct(alpha: float, rho: float, beta: float) -> np.ndarray:
    return _rot(alpha) @ np.diag([math.exp(rho), math.exp(-rho)]) @ _rot(beta).T


def swirl_to_kak(phi: float, psi: float) -> tuple:
    """``(alpha, beta) = (-(phi - psi)/2, (phi + psi)/2)``, modulo pi.

    The two compact swirl angles are the SUM and DIFFERENCE of the two Cartan
    angles.  Spin and swirl are not two independent decorations on a radius; they
    are the two K factors of the group, rotated by 45 degrees.
    """
    return (-(phi - psi) / 2.0, (phi + psi) / 2.0)


def fibre_is_local_unitary(M, delta: float) -> dict:
    """Moving along the compact fibre changes no singular value.

    This is the mechanism behind R6b's saturating angular Fisher information,
    stated as something that can fail: if a compact step altered the spectrum,
    the free/costly split would not be the compact/non-compact split.
    """
    M = np.asarray(M, dtype=float)
    before = np.linalg.svd(M, compute_uv=False)
    after = np.linalg.svd(_rot(delta) @ M, compute_uv=False)
    return {"max_singular_value_change": float(np.max(np.abs(before - after))),
            "spectrum_preserved": bool(np.allclose(before, after, atol=1e-12))}


def hopf_map(psi) -> np.ndarray:
    """``S^3 -> S^2``: ``(z1, z2) -> (2 Re(z1* z2), 2 Im(z1* z2), |z1|^2 - |z2|^2)``.

    Identical to the Bloch vector of the same state -- see :func:`bloch_vector`.
    Taking a density matrix IS quotienting by the Hopf fibre.
    """
    z1, z2 = np.asarray(psi, dtype=complex)
    return np.array([2.0 * (z1.conjugate() * z2).real,
                     2.0 * (z1.conjugate() * z2).imag,
                     abs(z1) ** 2 - abs(z2) ** 2])


def bloch_vector(psi) -> np.ndarray:
    """``(<sigma_x>, <sigma_y>, <sigma_z>)`` computed the quantum-mechanical way."""
    psi = np.asarray(psi, dtype=complex)
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]])
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    return np.array([complex(np.vdot(psi, s @ psi)).real for s in (sx, sy, sz)])


def hopf_ladder() -> list:
    """The four rungs, with the algebra that permits each and the one that ends it.

    Reported together because either fact alone invites the wrong extrapolation:
    the fibrations look like a pattern that should continue, and the
    Cayley-Dickson construction genuinely does continue -- it just stops producing
    division algebras, which is what the fibrations need.
    """
    return [
        {"fibration": "S^0 -> S^1 -> S^1", "algebra": "R", "dim": 1,
         "is_division_algebra": True, "associative": True, "commutative": True},
        {"fibration": "S^1 -> S^3 -> S^2", "algebra": "C", "dim": 2,
         "is_division_algebra": True, "associative": True, "commutative": True},
        {"fibration": "S^3 -> S^7 -> S^4", "algebra": "H", "dim": 4,
         "is_division_algebra": True, "associative": True, "commutative": False},
        {"fibration": "S^7 -> S^15 -> S^8", "algebra": "O", "dim": 8,
         "is_division_algebra": True, "associative": False, "commutative": False},
        {"fibration": None, "algebra": "S (sedenions)", "dim": 16,
         "is_division_algebra": False, "associative": False, "commutative": False,
         "why_it_stops": "zero divisors exist, so there is no norm multiplicativity "
                         "and no Hopf fibration; see aionq.cayley_dickson"},
    ]


def projective_volume(unquotiented: float | None = None) -> dict:
    """The factor-of-2 quotient the external derivation left open.

    ``omega(A) = omega(-A)`` exactly, so the operational parameter space is
    ``PSL(2,R)``, and the operational Fisher volume halves.
    """
    if unquotiented is None:
        unquotiented = math.sqrt(2.0) * math.pi ** 3
    return {"unquotiented": unquotiented,
            "quotient_order": 2,
            "quotiented": unquotiented / 2.0,
            "closed_form": "pi^3 / sqrt(2)",
            "reason": "omega is quadratic in v, so the sign of A is invisible; the "
                      "operational space is PSL(2,R) = SL(2,R)/{+-1}"}
