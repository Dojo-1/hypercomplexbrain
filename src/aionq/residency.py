"""Certified quantum residency.

The governing correction to QSigma-infinity.

The draft architecture defined quantum causal residency as a weighted count of
internal transitions that are "realized as a quantum channel, supermap, logical
operation or coherent control":

    Q_causal = sum_e w_e * 1[e is quantum] / sum_e w_e

That definition is additive over edges and is therefore gameable in two
independent ways:

1.  Permutation embedding.  Any classical reversible computation embeds as a
    permutation unitary.  Every edge then satisfies the indicator, so the naive
    score is exactly 1.00, while the whole core is simulable in linear time.

2.  Gottesman-Knill.  A circuit of arbitrary depth built only from Clifford
    gates generates maximal entanglement across every cut and is still simulable
    in polynomial time.  Entanglement is *not* quantum residency.

Both failures share one cause: quantumness is not an additive property of edges.
It is a global property of the causal core.  A sum of locally quantum-looking
transitions can be globally classical.

The replacement is a *simulation-cost* definition.  Let C_sim be the best known
classical cost of simulating the causal core to constant total-variation error,
and let n be the number of logical qubits the core spans, so that dense
simulation costs 2^n.  Define

    Q_cert = log2(C_sim) / n,   clipped to [0, 1]

Q_cert is the fraction of the Hilbert-space exponent that a classical simulator
is actually forced to pay.  It reads:

    permutation core            -> Q_cert ~ 0
    Clifford core (any depth)   -> Q_cert ~ 0
    Clifford + t T gates        -> Q_cert = alpha * t / n
    generic core                -> Q_cert = 1

with alpha the Bravyi-Gosset stabilizer-rank exponent per T gate.  Saturation at
Q_cert = 1 needs t ~ n / alpha ~ 4.4 n non-Clifford gates: an almost-all-quantum
brain must spend on the order of four non-Clifford operations per logical qubit,
per coherent episode.  That is a hardware budget, not a slogan.

Scope and honesty
-----------------
Q_cert is an *upper bound on classical hardness* built from the best simulation
strategies this module implements (basis-permutation, stabilizer, stabilizer
rank).  A better classical algorithm lowers C_sim and therefore lowers Q_cert.
That direction is the correct one: the metric can only ever be revised
downward by classical progress, never inflated by notation.  It is a
falsifiable claim about a circuit, not a property the architecture may assert
about itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Barrier, ControlFlowOp, Delay, Measure, Reset
from qiskit.quantum_info import Clifford, Operator, Statevector

__all__ = [
    "ALPHA_BG",
    "TransitionClass",
    "ResidencyReport",
    "classify_instruction",
    "certified_residency",
    "naive_residency",
    "stabilizer_renyi_entropy",
    "max_bipartite_entanglement",
]

# Bravyi et al., "Simulation of quantum circuits by low-rank stabilizer
# decompositions" (2019): asymptotic stabilizer rank per T gate ~ 2^(0.2284 t).
ALPHA_BG = 0.2284

# Ross-Selinger optimal ancilla-free single-qubit synthesis: T-count ~ 3 log2(1/eps).
RS_SLOPE = 3.0

# Default synthesis precision when a continuous rotation must be discretised.
DEFAULT_EPS = 1e-3

# Exact T-counts for the standard non-Clifford library.
_KNOWN_T_COUNT = {
    "t": 1,
    "tdg": 1,
    "cs": 3,
    "csdg": 3,
    "ccx": 7,
    "ccz": 7,
    "rccx": 0,      # relative-phase Toffoli is Clifford+T-free up to phase
    "cswap": 7,
}

_FREE_OPS = {"barrier", "delay", "id", "measure", "reset", "store", "snapshot"}

# Gates that permute computational basis states.  Under the basis-permutation
# simulation strategy these are free; under stabilizer-rank they may not be.
_PERMUTATION_NAMES = {"x", "cx", "ccx", "cswap", "swap", "mcx", "rccx", "id"}

# Gates that leave the computational basis (up to phase) and therefore
# invalidate the basis-permutation strategy for the whole core.
_BASIS_LEAVING = {"h", "ry", "rx", "sx", "sxdg", "u", "u2", "u3", "r", "initialize"}


class TransitionClass:
    """Simulation class of a single transition."""

    FREE = "free"                  # no simulation cost (barriers, measurement bookkeeping)
    PERMUTATION = "permutation"    # basis permutation: classical reversible
    CLIFFORD = "clifford"          # stabilizer-simulable
    NONCLIFFORD = "nonclifford"    # pays stabilizer-rank cost
    OPAQUE = "opaque"              # unclassifiable: charged at full support width


@dataclass
class ResidencyReport:
    """Result of a residency audit."""

    n_qubits: int
    t_count: float
    opaque_exponent: float
    q_cert: float
    q_naive: float
    log2_sim_cost: float
    class_counts: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def gap(self) -> float:
        """How much the naive metric overstates quantum residency."""
        return self.q_naive - self.q_cert

    def __str__(self) -> str:  # pragma: no cover - display only
        lines = [
            f"qubits             : {self.n_qubits}",
            f"T-count            : {self.t_count:.1f}",
            f"log2 C_sim         : {self.log2_sim_cost:.2f}",
            f"Q_cert  (certified): {self.q_cert:.4f}",
            f"Q_naive (draft def): {self.q_naive:.4f}",
            f"overstatement gap  : {self.gap:+.4f}",
            f"classes            : {self.class_counts}",
        ]
        lines.extend(f"note: {n}" for n in self.notes)
        return "\n".join(lines)


def _is_permutation(matrix: np.ndarray, atol: float = 1e-9) -> bool:
    """True if `matrix` maps computational basis states to basis states."""
    mag = np.abs(matrix)
    # exactly one entry of modulus 1 per row and per column
    if not np.allclose(np.sum(mag > atol, axis=0), 1, atol=atol):
        return False
    if not np.allclose(np.sum(mag > atol, axis=1), 1, atol=atol):
        return False
    return bool(np.allclose(mag[mag > atol], 1.0, atol=1e-7))


def _is_strict_permutation(matrix: np.ndarray, atol: float = 1e-9) -> bool:
    """True if `matrix` is a permutation that is not merely diagonal.

    A diagonal unitary trivially satisfies "one unit-modulus entry per row and
    column", so :func:`_is_permutation` alone would misclassify every phase gate
    as classical reversible logic.  Diagonal gates are handled separately: they
    preserve the computational basis but still cost rotation synthesis.
    """
    if not _is_permutation(matrix, atol=atol):
        return False
    off = matrix - np.diag(np.diag(matrix))
    return bool(np.any(np.abs(off) > atol))


def _diagonal_synthesis_cost(matrix: np.ndarray, eps: float) -> float:
    """T-cost of a diagonal non-Clifford gate from its phase angles.

    Phases that are integer multiples of pi/4 lie in the Clifford+T lattice and
    cost one T each; anything else needs Ross-Selinger synthesis.
    """
    phases = np.angle(np.diag(matrix))
    phases = phases - phases[0]  # global phase is free
    cost = 0.0
    for phi in phases[1:]:
        k = phi / (math.pi / 4.0)
        if abs(k - round(k)) < 1e-8:
            cost += 1.0 if abs(round(k)) % 2 == 1 else 0.0
        else:
            cost += RS_SLOPE * math.log2(1.0 / eps)
    return cost


def _is_diagonal(operation, atol: float = 1e-9) -> bool:
    """True if `operation` is diagonal in the computational basis.

    Diagonal gates apply unobservable phases to basis states, so they preserve
    the validity of the basis-permutation simulation strategy.
    """
    if operation.name.lower() in {"z", "s", "sdg", "t", "tdg", "cz", "ccz", "rz",
                                  "p", "cp", "crz", "rzz", "cs", "csdg"}:
        return True
    try:
        mat = Operator(operation).data
    except Exception:
        return False
    return bool(np.allclose(mat - np.diag(np.diag(mat)), 0, atol=atol))


def _is_clifford(operation) -> bool:
    try:
        Clifford(operation)
        return True
    except Exception:
        return False


def classify_instruction(operation, eps: float = DEFAULT_EPS) -> tuple[str, float]:
    """Classify one instruction and return ``(TransitionClass, t_cost)``.

    ``t_cost`` is the number of T gates a fault-tolerant compilation must spend.
    Free, permutation and Clifford transitions all cost zero: none of them moves
    the core off the classically-simulable manifold.
    """
    name = operation.name.lower()

    if isinstance(operation, (Barrier, Delay, Measure, Reset)) or name in _FREE_OPS:
        return TransitionClass.FREE, 0.0

    if isinstance(operation, ControlFlowOp):
        # Classical feedforward is itself free; the bodies are audited separately
        # by the caller walking into them.
        return TransitionClass.FREE, 0.0

    if name in _KNOWN_T_COUNT:
        cost = float(_KNOWN_T_COUNT[name])
        # Toffoli-family gates are basis permutations *and* cost 7 T under
        # stabilizer-rank simulation.  Report both facts; the global auditor
        # takes the cheaper strategy.
        cls = TransitionClass.PERMUTATION if name in _PERMUTATION_NAMES else (
            TransitionClass.CLIFFORD if cost == 0 else TransitionClass.NONCLIFFORD
        )
        return cls, cost

    try:
        matrix = Operator(operation).data
    except Exception:
        matrix = None

    if _is_clifford(operation):
        is_perm = matrix is not None and _is_strict_permutation(matrix)
        return (TransitionClass.PERMUTATION if is_perm else TransitionClass.CLIFFORD), 0.0

    if matrix is None:
        width = getattr(operation, "num_qubits", 1)
        return TransitionClass.OPAQUE, float(width) / ALPHA_BG

    # Controlled versions of a non-Clifford base gate.  A controlled rotation is
    # built by the standard phase gadget (two half-angle rotations conjugated by
    # CNOTs), so it costs about twice the base gate plus Clifford overhead.
    base = getattr(operation, "base_gate", None)
    if base is not None and getattr(operation, "num_ctrl_qubits", 0) > 0:
        _, base_cost = classify_instruction(base, eps=eps)
        if base_cost > 0:
            ctrl = operation.num_ctrl_qubits
            cost = (2 ** ctrl) * base_cost + (2 ** ctrl - 1)
            cls = (TransitionClass.NONCLIFFORD if not _is_diagonal(operation)
                   else TransitionClass.NONCLIFFORD)
            return cls, float(cost)

    if _is_diagonal(operation, atol=1e-9):
        # Diagonal but non-Clifford: applies unobservable phases to basis states,
        # so it never leaves the computational basis, but it still costs
        # rotation synthesis if the surrounding core does.
        return TransitionClass.NONCLIFFORD, _diagonal_synthesis_cost(matrix, eps)

    if _is_strict_permutation(matrix):
        # Classical reversible logic wearing unitary notation: free under the
        # basis-permutation strategy, priced by stabilizer rank otherwise.
        return TransitionClass.PERMUTATION, float(_KNOWN_T_COUNT.get(name, 7))

    width = operation.num_qubits
    if width == 1:
        # Continuous rotation: Ross-Selinger synthesis cost.
        return TransitionClass.NONCLIFFORD, RS_SLOPE * math.log2(1.0 / eps)

    # Multi-qubit non-Clifford of unknown structure: charge a conservative
    # synthesis estimate proportional to the number of rotations in a generic
    # two-qubit-basis decomposition.
    rotations = 3 * (4 ** width - 1) / 3
    return TransitionClass.NONCLIFFORD, RS_SLOPE * math.log2(1.0 / eps) * rotations / 4


def _walk(circuit: QuantumCircuit):
    """Yield every leaf instruction, descending into control-flow bodies."""
    for inst in circuit.data:
        op = inst.operation
        if isinstance(op, ControlFlowOp):
            yield op
            for block in op.blocks:
                yield from _walk(block)
        else:
            yield op


def certified_residency(
    circuit: QuantumCircuit,
    eps: float = DEFAULT_EPS,
    alpha: float = ALPHA_BG,
) -> ResidencyReport:
    """Audit a circuit and return certified vs. naive quantum residency."""
    n = circuit.num_qubits
    t_total = 0.0
    opaque_exponent = 0.0
    counts: dict[str, int] = {}
    quantum_edges = 0
    total_edges = 0
    basis_confined = True  # does the core ever leave the computational basis?

    for op in _walk(circuit):
        cls, cost = classify_instruction(op, eps=eps)
        counts[cls] = counts.get(cls, 0) + 1

        if cls not in (TransitionClass.FREE, TransitionClass.PERMUTATION):
            if not _is_diagonal(op):
                basis_confined = False

        if cls == TransitionClass.OPAQUE:
            opaque_exponent += cost * alpha
        else:
            t_total += cost

        # The draft definition: every transition realised as a unitary, channel
        # or coherent control counts as fully quantum; only classical
        # feedforward and measurement-mediated control do not.
        if cls != TransitionClass.FREE:
            quantum_edges += 1
            total_edges += 1
        elif isinstance(op, (Measure, Reset)) or isinstance(op, ControlFlowOp):
            total_edges += 1

    # Strategy A: stabilizer-rank decomposition, cost 2^(alpha * T).
    log2_stabrank = alpha * t_total + opaque_exponent
    # Strategy B: basis permutation.  Valid only if the core never leaves the
    # computational basis, in which case a basis input stays a phased basis
    # state and computational-basis readout is a point mass.
    log2_basis = 0.0 if basis_confined else math.inf
    # A classical simulator picks whichever strategy is cheaper.
    log2_cost = min(float(n), log2_stabrank, log2_basis)

    q_cert = 0.0 if n == 0 else max(0.0, min(1.0, log2_cost / n))
    q_naive = 0.0 if total_edges == 0 else quantum_edges / total_edges

    notes = []
    if basis_confined and total_edges > 0:
        notes.append(
            "core never leaves the computational basis: classical reversible logic "
            f"wearing unitary notation (stabilizer-rank strategy would have charged "
            f"{log2_stabrank:.2f} bits, basis-permutation strategy charges 0)."
        )
    elif counts.get(TransitionClass.PERMUTATION):
        notes.append(
            f"{counts[TransitionClass.PERMUTATION]} permutation transitions present; "
            "they are free in isolation but priced by stabilizer rank here because "
            "the surrounding core leaves the computational basis."
        )
    if t_total == 0 and opaque_exponent == 0 and total_edges > 0:
        notes.append(
            "core is entirely stabilizer/permutation simulable (Gottesman-Knill): "
            "Q_cert = 0 regardless of depth, width or entanglement."
        )
    if q_cert >= 1.0:
        notes.append("core saturates the Hilbert-space exponent; classically intractable.")

    return ResidencyReport(
        n_qubits=n,
        t_count=t_total,
        opaque_exponent=opaque_exponent,
        q_cert=q_cert,
        q_naive=q_naive,
        log2_sim_cost=log2_cost,
        class_counts=counts,
        notes=notes,
    )


def naive_residency(circuit: QuantumCircuit) -> float:
    """The draft QSigma-infinity metric, kept for comparison."""
    return certified_residency(circuit).q_naive


# --------------------------------------------------------------------------
# State-level diagnostics (small n only; exact, no sampling)
# --------------------------------------------------------------------------

def stabilizer_renyi_entropy(state: Statevector | np.ndarray) -> float:
    """Second stabilizer Renyi entropy M2 (Leone-Oliviero-Hamma magic monotone).

    M2 = -log2( sum_P <psi|P|psi>^4 / 2^n ).  Zero on every stabilizer state;
    log2(4/3) ~ 0.415 on a single T-state.  Exact for n <= ~8.
    """
    sv = state if isinstance(state, Statevector) else Statevector(state)
    n = sv.num_qubits
    vec = np.asarray(sv.data, dtype=complex)
    rho = np.outer(vec, vec.conj())

    # Per-qubit Pauli transform.  Fold each qubit's (row, col) index pair into a
    # single axis of length 4 and contract it against W[p, (i, j)] = P_p[j, i],
    # so that the full contraction yields Tr(rho P) for every Pauli string in
    # O(n 4^n) rather than O(4^n) explicit Kronecker products.
    paulis = np.array([
        [[1, 0], [0, 1]],
        [[0, 1], [1, 0]],
        [[0, -1j], [1j, 0]],
        [[1, 0], [0, -1]],
    ], dtype=complex)
    w = paulis.transpose(0, 2, 1).reshape(4, 4)  # W[p, i*2 + j] = P_p[j, i]

    # rho indices (i1 j1 i2 j2 ... in jn) -> group into n axes of length 4
    tensor = rho.reshape([2] * (2 * n))
    order = []
    for q in range(n):
        order.extend([q, n + q])
    tensor = tensor.transpose(order).reshape([4] * n)

    for axis in range(n):
        tensor = np.moveaxis(tensor, axis, -1)
        tensor = tensor @ w.T
        tensor = np.moveaxis(tensor, -1, axis)

    exps = np.real(tensor).ravel()
    total = float(np.sum(exps ** 4))
    return float(-math.log2(total / (2 ** n)))


def max_bipartite_entanglement(state: Statevector | np.ndarray) -> float:
    """Maximum von Neumann entanglement entropy over contiguous bipartitions.

    Included specifically to be *excluded* from Q_cert: a GHZ state maximises
    this quantity and is exactly stabilizer-simulable.
    """
    sv = state if isinstance(state, Statevector) else Statevector(state)
    n = sv.num_qubits
    vec = np.asarray(sv.data, dtype=complex).reshape([2] * n)

    best = 0.0
    for cut in range(1, n):
        mat = vec.reshape(2 ** cut, 2 ** (n - cut))
        svals = np.linalg.svd(mat, compute_uv=False)
        probs = np.clip(svals ** 2, 1e-18, None)
        probs = probs / probs.sum()
        best = max(best, float(-np.sum(probs * np.log2(probs))))
    return best
