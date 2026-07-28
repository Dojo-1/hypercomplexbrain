"""What hyperbolic depth costs on a unitary substrate.

The programme's cognitive substrate is the Q = +1 pseudo-sphere in R^{2,2},

    Q(x) = x0^2 + x1^2 - x2^2 - x3^2,

with SO(2,2) moving points around on it.  Quantum computation is unitary.  Those
two facts are in tension, and the tension is not a matter of engineering effort:

    A connected non-compact SEMISIMPLE Lie group has no faithful
    finite-dimensional unitary representation.

CORRECTED at R6b, on an external auditor's guard.  This originally read "simple".
``so(2,2) = sl(2,R) + sl(2,R)`` has two ideals, so SO_0(2,2) is semisimple and NOT
simple.  The obstruction survives verbatim under the corrected word -- a connected
semisimple Lie group with a faithful finite-dimensional unitary representation
must be compact -- but the word was wrong and a wrong word in a theorem statement
is not a small thing.

A second guard from the same audit, recorded here because this module's title
says "hyperbolic".  The induced metric on the Q = +1 pseudo-sphere is
``g = diag(-1, cosh^2 rho, -sinh^2 rho)``, signature (1,2): an AdS_3-like
LORENTZIAN geometry, not positive-definite hyperbolic 3-space.  The depth
coordinate behaves hyperbolically and the measure ``cosh rho sinh rho`` is right,
but "hyperbolic" in the Riemannian sense is the wrong name for the space.  See
:func:`aionq.quantum_channel_geometry.induced_metric_signature`, which checks it.

SO(2,2) is non-compact.  So the hyperbolic directions of this substrate cannot
be gates, in any width, ever.  This module does not argue about that; it prices
it, exactly, and then hands the price to Qiskit to confirm.

The identification that makes it concrete
-----------------------------------------
Map a point of R^{2,2} to a real 2x2 matrix by

    x  ->  M = [[x0 + x2, x1 + x3],
                [-x1 + x3, x0 - x2]]

Then ``det M = Q(x)`` identically, so the Q = +1 hyperboloid *is* SL(2,R) as a
set, and SO(2,2)_0 acts by ``M -> A M B^-1``.  This is not an analogy imported
from elsewhere: it is the same object, written twice.

In the swirl coordinates the TELOS archive already uses,

    x = (cosh(r) cos(f), cosh(r) sin(f), sinh(r) cos(p), sinh(r) sin(p)),

everything becomes closed form.  ``tr M = 2 cosh(r) cos(f)``, the singular values
are ``e^r`` and ``e^-r``, and:

    THE POINT IS A UNITARY IF AND ONLY IF r = 0.

That single line is the whole finding.  The compact coordinates f (spin) and p
(swirl) are free -- they are phases, they are gates, they cost nothing.  The one
coordinate that makes the geometry hyperbolic rather than Euclidean, r, is
exactly and only the coordinate that is not implementable.  Depth is the bill.

What S8 got wrong, recorded here because this module is where it was caught
--------------------------------------------------------------------------
Round S8 left the (2,2) signature unimplemented and typed the remainder as "the
SU(1,1) generators are unbounded, so the Frobenius norm and the rank argument
need re-deriving".  The first clause is false.  The generators are fixed 4x4
matrices with entries in {0, +-1}; their norms are constants.  What is unbounded
is not the algebra but the GROUP: ``||exp(r K)||_F`` diverges while
``||exp(t J)||_F`` does not.

That distinction matters because it says where the instrument failed.  S8 carried
a norm that is fine on a compact group into a non-compact one, at the group level,
and got a quantity that measures rapidity and nothing else.  The invariant that
survives the move is the conjugacy class -- ``|tr M|`` against 2 -- which is bounded,
basis-independent, and actually classifies.  :func:`generator_norm_diagnostic`
reproduces the failure rather than quietly stepping around it.

What this module does NOT claim
-------------------------------
No advantage.  Nothing here suggests the (2,2) substrate is good for quantum
computation; the round's own preregistration lists "any claim of quantum
advantage" as a kill condition.  There is no device, no noise model, and no
truncation study -- the infinite-dimensional-representation branch is left open
and typed, not silently omitted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = [
    "q22",
    "swirl_point",
    "to_sl2",
    "from_sl2",
    "swirl_state",
    "singular_values",
    "conjugacy_class",
    "is_orthogonal",
    "elliptic_fraction_analytic",
    "block_encode",
    "block_encoding_circuit",
    "success_probability",
    "composed_success_probability",
    "so22_generators",
    "generator_norm_diagnostic",
    "SwirlState",
]

_ETA = np.diag([1.0, 1.0, -1.0, -1.0])


def q22(x) -> float:
    """The split quadratic form ``x0^2 + x1^2 - x2^2 - x3^2``."""
    x = np.asarray(x, dtype=float)
    return float(x @ _ETA @ x)


def swirl_point(rho: float, phi: float, psi: float) -> np.ndarray:
    """The Q = +1 point at hyperbolic depth `rho`, spin `phi`, swirl `psi`.

    Coordinates are taken verbatim from the TELOS ``SectionalComputer`` so that
    any conclusion here transfers back to that codebase without re-derivation.
    """
    return np.array(
        [
            math.cosh(rho) * math.cos(phi),
            math.cosh(rho) * math.sin(phi),
            math.sinh(rho) * math.cos(psi),
            math.sinh(rho) * math.sin(psi),
        ],
        dtype=float,
    )


def to_sl2(x) -> np.ndarray:
    """The 2x2 matrix whose determinant IS the quadratic form.

    ``det(to_sl2(x)) == q22(x)`` exactly, so Q = +1 becomes det = 1.
    """
    x = np.asarray(x, dtype=float)
    x0, x1, x2, x3 = x
    return np.array([[x0 + x2, x1 + x3], [-x1 + x3, x0 - x2]], dtype=float)


def from_sl2(M) -> np.ndarray:
    """Inverse of :func:`to_sl2`."""
    M = np.asarray(M, dtype=float)
    (a, b), (c, d) = M
    return np.array([(a + d) / 2.0, (b - c) / 2.0, (a - d) / 2.0, (b + c) / 2.0])


@dataclass(frozen=True)
class SwirlState:
    """Depth, spin, swirl -- the three coordinates, with depth singled out."""

    rho: float
    phi: float
    psi: float

    @property
    def is_compact(self) -> bool:
        """True when the point is a rotation, i.e. when it is free to run."""
        return abs(self.rho) < 1e-12


def swirl_state(x) -> SwirlState:
    """Recover ``(rho, phi, psi)`` from a Q = +1 point."""
    x = np.asarray(x, dtype=float)
    cosh_r = math.hypot(x[0], x[1])
    sinh_r = math.hypot(x[2], x[3])
    rho = math.asinh(sinh_r)
    phi = math.atan2(x[1], x[0]) if cosh_r > 0 else 0.0
    psi = math.atan2(x[3], x[2]) if sinh_r > 1e-15 else 0.0
    return SwirlState(rho=rho, phi=phi, psi=psi)


def singular_values(M) -> tuple:
    """Singular values, largest first.  For a Q = +1 point these are e^r, e^-r."""
    s = np.linalg.svd(np.asarray(M, dtype=float), compute_uv=False)
    return (float(s[0]), float(s[1]))


def conjugacy_class(M, tol: float = 1e-9) -> str:
    """SL(2,R) conjugacy class from the trace: elliptic / parabolic / hyperbolic.

    This is the invariant that survives the move to a non-compact group.  Unlike
    a Frobenius norm it is bounded on the compact part, basis-independent, and it
    classifies rather than merely ranking.
    """
    t = abs(float(np.trace(np.asarray(M, dtype=float))))
    if t < 2.0 - tol:
        return "elliptic"
    if t <= 2.0 + tol:
        return "parabolic"
    return "hyperbolic"


def is_orthogonal(M, tol: float = 1e-12) -> bool:
    """Whether the matrix is a rotation, hence directly implementable as a gate."""
    M = np.asarray(M, dtype=float)
    return bool(np.max(np.abs(M.T @ M - np.eye(M.shape[0]))) <= tol)


def elliptic_fraction_analytic(rho: float) -> float:
    """Fraction of spins `phi` giving an elliptic element, at depth `rho`.

    ``tr M = 2 cosh(rho) cos(phi)``, so elliptic means ``|cos phi| < sech(rho)``
    and the measure of that set on the circle is ``4 arcsin(sech rho)``.  Hence

        fraction = (2 / pi) * arcsin(sech(rho))  ~  (4 / pi) e^-rho.

    The unitarily-conjugable part of the substrate thins out exponentially with
    depth, at a rate that is predicted rather than fitted.
    """
    return float(2.0 / math.pi * math.asin(1.0 / math.cosh(rho)))


def block_encode(M) -> tuple:
    """Return ``(U, subnormalisation)`` with ``U[:2, :2] == M / ||M||_2``.

    The standard unitary dilation

        U = [[A,                 sqrt(I - A A^T)],
             [sqrt(I - A^T A),   -A^T           ]],     A = M / ||M||_2

    is orthogonal because ``A f(A^T A) = f(A A^T) A`` for analytic f.  Applying M
    then means: run U, measure the ancilla, keep the ``|0>`` branch.  The kept
    branch carries ``A`` and not ``M``, which is where the subnormalisation --
    the actual bill -- appears.
    """
    M = np.asarray(M, dtype=float)
    s = float(np.linalg.norm(M, 2))
    if s == 0.0:
        raise ValueError("cannot block-encode the zero matrix")
    A = M / s
    n = M.shape[0]
    eye = np.eye(n)
    left = _psd_sqrt(eye - A @ A.T)
    right = _psd_sqrt(eye - A.T @ A)
    U = np.block([[A, left], [right, -A.T]])
    return U, s


#: Eigenvalues of ``I - A A^T`` below this are zero, not small.  See below.
_SQRT_FLOOR = 16.0 * float(np.finfo(float).eps)


def _psd_sqrt(X) -> np.ndarray:
    """Symmetric square root, with a floor -- and the floor is load-bearing.

    Clipping at zero is not enough, and the reason is worth keeping.  ``A`` here
    always has spectral norm exactly 1, so ``X = I - A A^T`` has entries of order
    one and ``eigh`` resolves its eigenvalues to about machine epsilon.  When a
    true eigenvalue is exactly 0 -- which happens at EVERY depth, since ``A`` has
    singular values 1 and e^{-2 rho}, and at rho = 0 happens for both -- the
    computed value is noise of order 1e-16.

    Square root is not Lipschitz at the origin.  sqrt(1e-16) is 1e-8.  So taking
    the root of clipped noise does not produce a small error, it produces an
    error eight orders of magnitude larger than the noise, and it produces it in
    the off-diagonal blocks, which is precisely where spurious ancilla leakage
    lives.  The first run of this round measured 4e-9 of it at rho = 0 -- in the
    regime the round claims costs nothing.

    The C1 fidelity control caught it at 1e-12 and voided the round, as
    preregistered.  The looser probability control C2 did not, because leakage
    enters a probability squared and 1e-8 squared sits under its 1e-10 threshold.
    That is the argument for keeping the strict amplitude-level control.
    """
    w, V = np.linalg.eigh((X + X.T) / 2.0)
    w = np.where(w < _SQRT_FLOOR, 0.0, w)
    return V @ np.diag(np.sqrt(w)) @ V.T


def block_encoding_circuit(M):
    """A 2-qubit Qiskit circuit: qubit 0 carries the state, qubit 1 the ancilla.

    Kept separate from :func:`block_encode` so that the algebra can be tested
    without Qiskit and the circuit can be checked against the algebra.
    """
    from qiskit import QuantumCircuit

    U, s = block_encode(M)
    qc = QuantumCircuit(2, name="blockenc")
    qc.unitary(U, [0, 1])
    return qc, s


def success_probability(M, state=None) -> float:
    """Post-selection probability of the ancilla-|0> branch, via Qiskit.

    With `state` omitted the Haar average over single-qubit inputs is returned
    instead of a single draw; that average is ``tr(A^T A) / 2``, which for a
    depth-`rho` point is exactly ``(1 + e^{-4 rho}) / 2``.
    """
    from qiskit.quantum_info import Statevector

    U, _ = block_encode(M)
    A = U[:2, :2]
    if state is None:
        return float(np.trace(A.T @ A) / 2.0)

    qc, _ = block_encoding_circuit(M)
    amp = np.zeros(4, dtype=complex)
    amp[:2] = np.asarray(state, dtype=complex)  # ancilla (qubit 1) in |0>
    amp /= np.linalg.norm(amp)
    out = Statevector(amp).evolve(qc)
    data = np.asarray(out.data)
    return float(np.sum(np.abs(data[:2]) ** 2))


def composed_success_probability(matrices, state) -> float:
    """All-ancillas-|0> probability for a chain of block-encoded steps.

    One fresh ancilla per step, so the circuit is ``len(matrices) + 1`` qubits.
    The kept branch carries the product of the *subnormalised* factors, which is
    why the cost compounds: L steps at depth rho contract the worst-case
    direction by ``e^{-4 L rho}``.
    """
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    matrices = list(matrices)
    n_anc = len(matrices)
    qc = QuantumCircuit(n_anc + 1)
    for i, M in enumerate(matrices):
        U, _ = block_encode(M)
        qc.unitary(U, [0, i + 1])

    amp = np.zeros(2 ** (n_anc + 1), dtype=complex)
    amp[:2] = np.asarray(state, dtype=complex)
    amp /= np.linalg.norm(amp)
    out = np.asarray(Statevector(amp).evolve(qc).data)
    return float(np.sum(np.abs(out[:2]) ** 2))


def so22_generators() -> dict:
    """The six generators of so(2,2): two compact, four non-compact.

    Compact J01, J23 rotate within the positive and negative planes.  The four
    K's mix a positive with a negative direction and are the boosts.  Every one
    of them is a bounded matrix -- the divergence lives in the group, not here.
    """
    def E(i, j):
        m = np.zeros((4, 4))
        m[i, j] = 1.0
        return m

    return {
        "J01": E(0, 1) - E(1, 0),
        "J23": E(2, 3) - E(3, 2),
        "K02": E(0, 2) + E(2, 0),
        "K03": E(0, 3) + E(3, 0),
        "K12": E(1, 2) + E(2, 1),
        "K13": E(1, 3) + E(3, 1),
    }


def generator_norm_diagnostic(rho: float) -> dict:
    """The wrong instrument, run on purpose, so the failure is on the record.

    Round S8 measured channel separation with a Frobenius norm and left (2,2)
    unimplemented on the stated grounds that "the generators are unbounded".
    They are not.  This returns, side by side:

    * the generator norms, which are constants and identical for compact and
      non-compact alike -- so at the algebra level the norm cannot even tell the
      two kinds apart;
    * the group-element norms, where ``||exp(rho K)||_F`` diverges while
      ``||exp(rho J)||_F`` stays put -- so at the group level the norm reports
      rapidity and nothing else;
    * ``|tr|`` of the corresponding SL(2,R) elements, which stays bounded on the
      compact side and classifies on the other.
    """
    from scipy.linalg import expm

    g = so22_generators()
    boost = expm(rho * g["K02"])
    rot = expm(rho * g["J01"])
    return {
        "rho": float(rho),
        "generator_frobenius": {k: float(np.linalg.norm(v, "fro")) for k, v in g.items()},
        "group_frobenius_boost_K02": float(np.linalg.norm(boost, "fro")),
        "group_frobenius_rotation_J01": float(np.linalg.norm(rot, "fro")),
        "abs_trace_sl2_boost": float(abs(np.trace(to_sl2(boost @ swirl_point(0.0, 0.0, 0.0))))),
        "abs_trace_sl2_rotation": float(abs(np.trace(to_sl2(rot @ swirl_point(0.0, 0.0, 0.0))))),
    }
