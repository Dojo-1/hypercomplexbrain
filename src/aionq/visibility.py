"""The visibility probe and coupling field, in quantum form.

The Manifold Research Atlas records this as the programme's *surviving late
positive*:

    Visibility probe -- depth-r local instrument over a certified backbone;
                        defines r*(n) and survival layers.
    Coupling field   -- g_r(alpha): the invisible fraction of the certified
                        backbone.  Intensive medium response.

and states the one-sentence thesis it supports:

    Certified global structure can be extensively present while remaining
    weakly coupled to bounded local inference.

That is a SAT statement, and no bridge to complexity is claimed by it or here.
But the *instrument* transfers exactly, and this repository had nothing like it:
no way to ask how much of an organ's structure is invisible to bounded local
probes.

A wrong first attempt, and why
------------------------------
The obvious construction is to bin the Pauli weight: call a Pauli of weight k
visible at depth r when k <= r, and set g_r to the fraction of weight above r.
That is wrong, and measurement caught it immediately: the product state
|+>^6 scored g_1 = 0.891 when it should score 0.

The reason is that Pauli *weight* is not Pauli *visibility*.  For a product
state <X_1 X_2> = <X_1><X_2>: a weight-2 expectation completely determined by
1-local data.  Binning by weight counts it as invisible anyway.  The weight
spectrum measures where a state keeps its Pauli mass, which is a different and
much less interesting quantity.  It is retained below as
:func:`pauli_weight_spectrum`, correctly labelled.

Quantum form that works
-----------------------
Visibility is about *determination*, not weight: which structure is fixed by the
r-local marginals.  For stabilizer states this has an exact, cheap answer.

A stabilizer state on n qubits is fixed by its stabilizer group S, of rank n.
An r-local probe can access exactly the elements of S of weight <= r.  So let
S_r = <{s in S : |s| <= r}> be the subgroup they generate, and define

    g_r = (n - rank(S_r)) / n

the fraction of the stabilizer structure that no r-local measurement can reach.
This reads correctly:

    product state   g_1 = 0     every generator has weight 1
    GHZ_n           g_r = 1/n for r < n, and 0 at r = n:
                    the Z_i Z_j subgroup has rank n-1 and is 2-local, while the
                    single generator X^{(x)n} has weight n. GHZ hides exactly one
                    bit from every local probe -- no more and no less.
    [[n,k,d]] code  structure remains hidden below r = d

Scope: exact for stabilizer states.  Non-stabilizer states need the maximum-
entropy state consistent with the r-marginals, which is not implemented here.

The last line is the useful one, and it is a *prediction this module can be
wrong about*: for a stabilizer code of distance d, the logical information is
carried by operators of weight at least d, so the visibility profile should show
its structure at r = d and not before.  :func:`code_visibility_signature` tests
it against codes of known distance.

Architectural reading
---------------------
This finally makes measurable a tension flagged in the first round of this
architecture and never implemented: **an organ whose identity is invisible to
local probes is protected from local noise but cannot be locally read or acted
upon.** High ``g_r`` is exactly protection, and exactly inertness.  A design must
choose where on that curve each organ sits; it cannot have both ends.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from qiskit.quantum_info import Statevector

__all__ = ["pauli_weight_spectrum", "visibility_profile", "VisibilityReport",
           "r_star", "code_visibility_signature", "stabilizer_group",
           "generators_from_labels", "NotAStabilizerState"]


class NotAStabilizerState(TypeError):
    """Raised when the exact visibility instrument is applied out of scope."""

_PAULIS = np.array([
    [[1, 0], [0, 1]],
    [[0, 1], [1, 0]],
    [[0, -1j], [1j, 0]],
    [[1, 0], [0, -1]],
], dtype=complex)


def _all_pauli_expectations(state) -> np.ndarray:
    """<P> for every Pauli string, as an n-dimensional array indexed by (p1..pn).

    Uses the same per-qubit transform as :func:`aionq.residency.stabilizer_renyi_entropy`:
    fold each qubit's (row, col) index pair into one axis of length 4 and contract
    against W[p, (i,j)] = P_p[j, i].  O(n 4^n) rather than 4^n Kronecker products.
    """
    sv = state if isinstance(state, Statevector) else Statevector(state)
    n = sv.num_qubits
    vec = np.asarray(sv.data, dtype=complex)
    rho = np.outer(vec, vec.conj())

    w = _PAULIS.transpose(0, 2, 1).reshape(4, 4)
    tensor = rho.reshape([2] * (2 * n))
    order = []
    for q in range(n):
        order.extend([q, n + q])
    tensor = tensor.transpose(order).reshape([4] * n)
    for axis in range(n):
        tensor = np.moveaxis(tensor, axis, -1)
        tensor = tensor @ w.T
        tensor = np.moveaxis(tensor, -1, axis)
    return np.real(tensor)


def _weight_index(n: int) -> np.ndarray:
    """Weight (number of non-identity factors) of every Pauli string index."""
    idx = np.zeros([4] * n, dtype=int)
    for q in range(n):
        shape = [1] * n
        shape[q] = 4
        contrib = np.array([0, 1, 1, 1]).reshape(shape)
        idx = idx + contrib
    return idx


def pauli_weight_spectrum(state) -> np.ndarray:
    """Total Pauli weight sum_{|P|=k} <P>^2 at each weight k, normalised to sum 1.

    For a pure state the unnormalised total is 2^n (Parseval), so the returned
    array is a probability distribution over weights: where the state keeps its
    structure.
    """
    sv = state if isinstance(state, Statevector) else Statevector(state)
    n = sv.num_qubits
    exps = _all_pauli_expectations(sv)
    weights = _weight_index(n)
    spectrum = np.zeros(n + 1)
    sq = exps ** 2
    for k in range(n + 1):
        spectrum[k] = sq[weights == k].sum()
    return spectrum / spectrum.sum()


def generators_from_labels(labels) -> tuple:
    """Symplectic (x|z) generator rows from Pauli label strings.

    Supplying generators directly avoids trusting a hand-written encoder.  That
    matters: the first version of this experiment used a hand-built Steane
    circuit which turned out to stabilize none of the Steane generators, and the
    apparent falsification it produced was an artifact of the bug.
    """
    n = len(labels[0])
    rows = np.zeros((len(labels), 2 * n), dtype=np.uint8)
    for i, lab in enumerate(labels):
        if len(lab) != n:
            raise ValueError("all stabilizer labels must have equal length")
        for q, ch in enumerate(reversed(lab)):     # qiskit little-endian
            if ch in ("X", "Y"):
                rows[i, q] = 1
            if ch in ("Z", "Y"):
                rows[i, n + q] = 1
    return n, rows


def stabilizer_group(circuit_or_labels) -> tuple:
    """Symplectic (x|z) rows for all 2^n elements of the stabilizer group.

    Accepts a Clifford circuit or an explicit list of Pauli generator labels.
    Returns ``(n, rows, weights)`` where rows is a GF(2) array of shape
    (2^n, 2n) and weights[i] is the Pauli weight of row i.
    """
    if isinstance(circuit_or_labels, (list, tuple)) and circuit_or_labels \
            and isinstance(circuit_or_labels[0], str):
        n, gens = generators_from_labels(list(circuit_or_labels))
        if np.linalg.matrix_rank(gens.astype(float)) and _gf2_rank(gens) != n:
            raise NotAStabilizerState(
                f"supplied {len(gens)} generators of GF(2) rank {_gf2_rank(gens)}, "
                f"but a stabilizer state on {n} qubits needs rank {n}")
    else:
        from qiskit.quantum_info import Clifford
        try:
            cliff = Clifford(circuit_or_labels)
        except Exception as exc:                   # pragma: no cover - guard
            raise NotAStabilizerState(
                "exact visibility is defined here only for stabilizer states; "
                f"this circuit is not Clifford ({exc})") from exc
        n = cliff.num_qubits
        gens = np.concatenate([cliff.stab_x.astype(np.uint8),
                               cliff.stab_z.astype(np.uint8)], axis=1)

    rows = np.zeros((1 << n, 2 * n), dtype=np.uint8)
    for mask in range(1 << n):
        acc = np.zeros(2 * n, dtype=np.uint8)
        m = mask
        g = 0
        while m:
            if m & 1:
                acc ^= gens[g]
            m >>= 1
            g += 1
        rows[mask] = acc
    weights = np.count_nonzero(rows[:, :n] | rows[:, n:], axis=1)
    return n, rows, weights


def _gf2_rank(rows: np.ndarray) -> int:
    """Rank over GF(2)."""
    m = rows.copy().astype(np.uint8)
    if m.size == 0:
        return 0
    rank, r = 0, 0
    for c in range(m.shape[1]):
        piv = None
        for i in range(r, m.shape[0]):
            if m[i, c]:
                piv = i
                break
        if piv is None:
            continue
        m[[r, piv]] = m[[piv, r]]
        for i in range(m.shape[0]):
            if i != r and m[i, c]:
                m[i] ^= m[r]
        r += 1
        rank += 1
        if r == m.shape[0]:
            break
    return rank


@dataclass
class VisibilityReport:
    """The coupling field of one state."""

    n_qubits: int
    rank_at: np.ndarray           # rank(S_r) for r = 0..n
    coupling: np.ndarray          # g_r = (n - rank(S_r)) / n
    r_star: int                   # smallest r with g_r <= threshold
    threshold: float
    spectrum: np.ndarray = field(default_factory=lambda: np.zeros(0))

    @property
    def g1(self) -> float:
        """Fraction of the stabilizer structure invisible to single-qubit probes."""
        return float(self.coupling[1])

    @property
    def hidden_bits(self) -> float:
        """Number of stabilizer generators no local probe of depth r* - 1 reaches."""
        return float(self.coupling[max(0, self.r_star - 1)] * self.n_qubits)

    def __str__(self) -> str:  # pragma: no cover - display only
        prof = "  ".join(f"g{r}={self.coupling[r]:.3f}"
                         for r in range(1, min(self.n_qubits, 7) + 1))
        return (f"n={self.n_qubits}  r*={self.r_star} (g<={self.threshold})  {prof}")


def visibility_profile(circuit_or_labels, threshold: float = 1e-9) -> VisibilityReport:
    """Exact coupling field g_r of a stabilizer state.

    g_r = (n - rank(S_r)) / n, where S_r is generated by the stabilizer elements
    of weight at most r.
    """
    n, rows, weights = stabilizer_group(circuit_or_labels)
    ranks = np.zeros(n + 1, dtype=int)
    for r in range(n + 1):
        sel = rows[weights <= r]
        sel = sel[np.any(sel, axis=1)] if sel.size else sel
        ranks[r] = _gf2_rank(sel) if sel.size else 0
    coupling = (n - ranks) / n
    rs = int(np.argmax(coupling <= threshold))
    return VisibilityReport(n_qubits=n, rank_at=ranks, coupling=coupling,
                            r_star=rs, threshold=threshold)


def r_star(state, threshold: float = 0.05) -> int:
    """Visibility depth: the smallest probe depth that sees all but `threshold`."""
    return visibility_profile(state, threshold).r_star


def code_visibility_signature(circuit_or_state, distance: int,
                              threshold: float = 1e-9) -> dict:
    """Test the prediction that a distance-d code hides structure below depth d.

    Returns the profile together with a verdict.  The prediction is that a
    codeword of distance ``d`` still has invisible weight at probe depth
    ``d - 1``: no measurement on fewer than d qubits reaches the logical
    operators.  A codeword that is fully visible below its own distance would
    falsify the reading.
    """
    rep = visibility_profile(circuit_or_state, threshold)
    below = float(rep.coupling[max(0, distance - 1)])
    return {
        "distance": distance,
        "r_star": rep.r_star,
        "g_at_d_minus_1": below,
        "hides_below_distance": below > threshold,
        "profile": rep,
    }
