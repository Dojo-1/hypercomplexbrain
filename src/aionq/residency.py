"""Simulation-cost residency: an upper bound, never a certificate.

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

    q_sim_upper = log2(C_sim) / n,   clipped to [0, 1]

q_sim_upper is the fraction of the Hilbert-space exponent that the best
simulation strategy implemented here is *known* to pay.  It is an upper bound on
classical hardness and never a certificate of it: exhibiting a good algorithm
bounds cost from above, while proving no better one exists is a different and
much harder problem.  The honest object is the interval
[q_sim_lower, q_sim_upper], with q_sim_lower = 0 absent a real lower-bound
argument.  It reads:

    permutation core            -> q_sim_upper ~ 0
    Clifford core (any depth)   -> q_sim_upper ~ 0
    Clifford + t T gates        -> q_sim_upper = alpha * t / n
    generic core                -> q_sim_upper = 1

with alpha the Bravyi-Gosset stabilizer-rank exponent per T gate.  Saturation
needs t ~ n / alpha ~ 4.4 n non-Clifford gates: an almost-all-quantum
brain must spend on the order of four non-Clifford operations per logical qubit,
per coherent episode.  That is a hardware budget, not a slogan.

Scope and honesty
-----------------
q_sim_upper is built from the simulation strategies this module implements
(basis-permutation, stabilizer, stabilizer rank), and is compiler-dependent by
construction: a compiler portfolio defeats the cancellation attacks in the
sweep, but circuit equivalence is intractable in general, so residual gaming
vectors exist.  A better classical algorithm lowers C_sim and therefore lowers
q_sim_upper.  That direction is the correct one: the metric can only ever be revised
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
from qiskit.exceptions import QiskitError
from qiskit.quantum_info import Clifford, Operator, Statevector

__all__ = [
    "ALPHA_BG",
    "TransitionClass",
    "ResidencyReport",
    "classify_instruction",
    "simulation_residency",
    "certified_residency",
    "PathStatus",
    "naive_residency",
    "stabilizer_renyi_entropy",
    "max_bipartite_entanglement",
    "SWALLOWED",
    "swallowed_report",
    "clear_swallowed",
]

# --------------------------------------------------------------------------
# The swallow ledger
# --------------------------------------------------------------------------
#
# Three sites here must tolerate an operation that has no unitary, is not
# Clifford, or cannot be transpiled -- those are ordinary answers, not faults.
# They were written as bare ``except Exception: return False``, which an external
# reviewer flagged.  The objection is exact: with a blanket catch, a real defect
# -- a broken import, a numpy failure, a shape bug -- is indistinguishable from
# "this gate simply has no matrix", and the classification degrades silently to
# OPAQUE.  OPAQUE inflates the reported residency, so the failure mode is a
# *quiet overstatement of quantum advantage*, which is the exact direction this
# repository is least entitled to be wrong in.
#
# Two changes.  The catch is narrowed to what Qiskit actually raises for an
# unrepresentable operation, so anything else propagates.  And the ones that are
# still caught are RECORDED rather than dropped, so "nothing was swallowed" is a
# checkable statement instead of an assumption.

_EXPECTED = (QiskitError, TypeError, ValueError)

SWALLOWED: list = []


def _swallow(site: str, operation, exc: Exception) -> None:
    SWALLOWED.append({"site": site,
                      "op": getattr(operation, "name", repr(operation)),
                      "error": f"{type(exc).__name__}: {exc}"})


def swallowed_report() -> list:
    """Every expected-but-caught exception since the last :func:`clear_swallowed`.

    Empty is the normal state.  A non-empty report is not necessarily a bug --
    a measurement genuinely has no unitary -- but it is the only place the
    distinction can be made, so it is reported rather than inferred.
    """
    return list(SWALLOWED)


def clear_swallowed() -> None:
    SWALLOWED.clear()

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
    # Relative-phase Toffoli.  Qiskit's RCCXGate definition is
    # H T CX Tdg CX T CX Tdg H: four T/Tdg operations.  Relative phase reduces
    # T-cost inside a larger construction; it does not make the isolated gate
    # Clifford or magic-free.
    "rccx": 4,
    "cswap": 7,
}

_FREE_OPS = {"barrier", "delay", "id", "measure", "reset", "store", "snapshot"}

# Gates that permute computational basis states.  Under the basis-permutation
# simulation strategy these are free; under stabilizer-rank they may not be.
_PERMUTATION_NAMES = {"x", "cx", "ccx", "cswap", "swap", "mcx", "rccx", "id"}


class TransitionClass:
    """Simulation class of a single transition."""

    FREE = "free"                  # no simulation cost (barriers, measurement bookkeeping)
    PERMUTATION = "permutation"    # basis permutation: classical reversible
    CLIFFORD = "clifford"          # stabilizer-simulable
    NONCLIFFORD = "nonclifford"    # pays stabilizer-rank cost
    OPAQUE = "opaque"              # unclassifiable: charged at full support width
    UNPRICEABLE = "unpriceable"    # not even a support width is available


class PathStatus:
    """Outcome of one compiler-portfolio candidate.  Only VALID may be minimised.

    The distinction exists because the previous code had exactly one outcome --
    "a number" -- and so a path that failed to price an instruction was
    indistinguishable from one that priced every instruction at zero.
    """

    VALID = "valid"
    OPAQUE_INSTRUCTION = "opaque_instruction"
    TRANSPILE_FAILED = "transpile_failed"
    UNSUPPORTED_REPRESENTATION = "unsupported_representation"


@dataclass
class ResidencyReport:
    """Result of a residency audit.

    ``q_sim_upper`` is an upper bound on classical simulation cost, normalised by
    the Hilbert-space exponent.  ``q_sim_lower`` is a *certified* lower bound and
    is 0.0 unless a genuine lower-bound argument is supplied: proving that no
    classical algorithm can do better is a different and much harder problem than
    exhibiting one that does this well.  The honest object is the interval.
    """

    n_qubits: int
    t_count: float
    opaque_exponent: float
    q_sim_upper: float
    q_naive: float
    log2_sim_cost: float
    raw_exponent: float = 0.0        # pre-clipping, so soundness is testable
    q_sim_lower: float = 0.0
    lower_justification: str = "none: no lower-bound technology applied"
    portfolio: dict = field(default_factory=dict)
    portfolio_status: dict = field(default_factory=dict)
    class_counts: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    q_sim_upper_known: bool = True
    typed_remainders: list = field(default_factory=list)

    @property
    def interval(self) -> tuple[float, float]:
        return (self.q_sim_lower, self.q_sim_upper)

    @property
    def gap(self) -> float:
        """How much the draft metric overstates relative to the upper bound."""
        return self.q_naive - self.q_sim_upper

    def __str__(self) -> str:  # pragma: no cover - display only
        lines = [
            f"qubits             : {self.n_qubits}",
            f"T-count (best)     : {self.t_count:.1f}",
            f"log2 C_sim (upper) : {self.log2_sim_cost:.2f}",
            f"q_sim interval     : [{self.q_sim_lower:.4f}, "
            + ("UNKNOWN]" if not self.q_sim_upper_known else f"{self.q_sim_upper:.4f}]"),
            f"Q_naive (draft def): {self.q_naive:.4f}",
            f"overstatement gap  : {self.gap:+.4f}",
            f"lower bound        : {self.lower_justification}",
        ]
        if self.portfolio:
            lines.append(f"compiler portfolio : {self.portfolio}")
        if self.portfolio_status:
            lines.append(f"path status        : {self.portfolio_status}")
        lines.append(f"classes            : {self.class_counts}")
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
    except _EXPECTED as exc:
        _swallow("_is_diagonal/Operator", operation, exc)
        return False
    return bool(np.allclose(mat - np.diag(np.diag(mat)), 0, atol=atol))


def _is_clifford(operation) -> bool:
    try:
        Clifford(operation)
        return True
    except _EXPECTED as exc:
        # The overwhelmingly common case, and a correct answer: T is not Clifford.
        _swallow("_is_clifford/Clifford", operation, exc)
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
    except _EXPECTED as exc:
        _swallow("classify_instruction/Operator", operation, exc)
        matrix = None

    if _is_clifford(operation):
        is_perm = matrix is not None and _is_strict_permutation(matrix)
        return (TransitionClass.PERMUTATION if is_perm else TransitionClass.CLIFFORD), 0.0

    if matrix is None:
        width = getattr(operation, "num_qubits", None)
        if width is None:
            # R4-A.  This used to default to 1, which prices an unknown-width
            # operation as a single qubit -- an UNDER-charge, and therefore an
            # understated simulation cost.  An operation whose support is unknown
            # is not opaque-but-priced; it is unpriceable, and the bound built
            # from it is not a bound.
            return TransitionClass.UNPRICEABLE, float("inf")
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
            return TransitionClass.NONCLIFFORD, float(cost)

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


CLIFFORD_T_BASIS = ["h", "s", "sdg", "x", "y", "z", "cx", "cz", "swap", "t", "tdg"]


def _portfolio_t_count(circuit: QuantumCircuit, eps: float,
                       levels=(0, 1, 2, 3)) -> tuple[float, dict]:
    """Minimum T-count over a portfolio of compilations.

    A syntactic audit of leaf instructions is gameable: ``H T Tdg H`` is exactly
    the identity yet contains two T gates.  Running the circuit through a
    compiler portfolio and taking the minimum defends against cancellation
    attacks that any optimiser in the portfolio can see.

    It is *not* a solution to circuit equivalence, which is not tractable in
    general.  The returned figure is therefore compiler-dependent, and the
    per-level breakdown is reported so that dependence is visible rather than
    hidden inside a single number.

    R4-A.  This function used to skip opaque instructions when summing:

        for op in _walk(compiled):
            cls, cost = classify_instruction(op, eps=eps)
            if cls != TransitionClass.OPAQUE:   # <- the defect
                total += cost

    An unpriced instruction was therefore *omitted* rather than invalidating the
    path, and the resulting partial total went straight into ``min``.  Injecting
    an opaque gate could make a circuit look CHEAPER to simulate -- a quiet
    OVERSTATEMENT of quantum advantage, the one direction this metric is least
    entitled to be wrong in.  Now a path carrying an unpriced instruction is
    marked ``opaque_instruction`` and is not a candidate at all.
    """
    from qiskit import transpile

    results: dict[str, float] = {}
    status: dict[str, str] = {}
    best = math.inf
    for level in levels:
        key = f"opt{level}"
        try:
            compiled = transpile(circuit, basis_gates=CLIFFORD_T_BASIS,
                                 optimization_level=level, seed_transpiler=11)
        except _EXPECTED as exc:
            # One optimisation level failing is survivable; ALL of them failing
            # leaves no candidate, which is why `best` is not defaulted to 0.
            _swallow(f"clifford_t_cost/transpile(opt{level})", circuit, exc)
            status[key] = PathStatus.TRANSPILE_FAILED
            continue
        total, opaque_seen = 0.0, False
        for op in _walk(compiled):
            cls, cost = classify_instruction(op, eps=eps)
            if cls == TransitionClass.OPAQUE:
                opaque_seen = True
                break                       # the path is already invalid
            total += cost
        if opaque_seen:
            status[key] = PathStatus.OPAQUE_INSTRUCTION
            continue
        status[key] = PathStatus.VALID
        results[key] = total
        best = min(best, total)

    return (best if best < math.inf else float("nan")), results, status


def simulation_residency(
    circuit: QuantumCircuit,
    eps: float = DEFAULT_EPS,
    alpha: float = ALPHA_BG,
    portfolio: bool = True,
) -> ResidencyReport:
    """Audit a circuit and return the q_sim interval vs. the draft metric.

    Renamed from ``certified_residency``: nothing here is certified.  The upper
    end of the interval is the best bound the implemented simulation strategies
    can produce; the lower end is 0 absent a real lower-bound argument.
    """
    n = circuit.num_qubits
    t_total = 0.0
    opaque_exponent = 0.0
    counts: dict[str, int] = {}
    quantum_edges = 0
    total_edges = 0
    basis_confined = True  # does the core ever leave the computational basis?
    remainders: list = []
    unpriceable = 0

    for op in _walk(circuit):
        cls, cost = classify_instruction(op, eps=eps)
        counts[cls] = counts.get(cls, 0) + 1

        if cls not in (TransitionClass.FREE, TransitionClass.PERMUTATION):
            if not _is_diagonal(op):
                basis_confined = False

        if cls == TransitionClass.UNPRICEABLE:
            unpriceable += 1
            remainders.append({
                "kind": "empirical_residual",
                "carrier": f"instruction {getattr(op, 'name', '?')!r}",
                "comparison": "no unitary representation AND no declared support "
                              "width, so no implemented strategy prices it"})
        elif cls == TransitionClass.OPAQUE:
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

    # Strategy A: stabilizer-rank decomposition, cost 2^(alpha * T).  Take the
    # cheapest compilation available, so that syntactic padding and cancelling
    # non-Clifford blocks do not inflate the score.
    portfolio_counts: dict = {}
    portfolio_status: dict = {}
    if portfolio:
        best_t, portfolio_counts, portfolio_status = _portfolio_t_count(circuit, eps)
        # Only a VALID path may lower the bound.  `results` now contains valid
        # paths only, so `best_t` is NaN precisely when none survived.
        if best_t == best_t:  # not NaN
            t_total = min(t_total, best_t)
    log2_stabrank = alpha * t_total + opaque_exponent
    # Strategy B: basis permutation.  Valid only if the core never leaves the
    # computational basis, in which case a basis input stays a phased basis
    # state and computational-basis readout is a point mass.
    log2_basis = 0.0 if basis_confined else math.inf
    # Strategy C: tensor-network contraction in a constructed elimination
    # ordering, cost 2^(induced width + 1).  A and B are both blind to
    # STRUCTURE: stabilizer rank charges for magic wherever it sits, so k
    # disconnected 2-qubit blocks each carrying a T gate are charged alpha*T,
    # which does not move when T grows in step with n, while the true cost
    # exponent of k independent 4x4 problems is fixed at 2.  Measured before
    # this strategy existed, that family sat at q_sim_upper = 0.2284 for every n
    # from 4 to 32 -- a metric that does not decay where the exponent is
    # constant is not measuring structure.  With this strategy it decays as 4/n,
    # staying above the exponent-only truth 2/n as an upper bound must.
    from .contraction import contraction_plan
    plan = contraction_plan(circuit)
    log2_tensor = plan.log2_cost if plan.valid else math.inf
    # Strategy D: free-fermion (matchgate) evolution, poly-time and therefore
    # exponent 0.  This is the one case none of A, B or C can see.  T is a
    # Z-rotation, hence a perfectly good free-fermion operation, so a
    # nearest-neighbour matchgate core can be SATURATED with T gates and remain
    # poly-time: measured, a 12-qubit 10-layer such core carries T-count 6286,
    # contraction width 14, and scored q_sim_upper = 1.0000 under A+B+C -- "no
    # implemented strategy simulates this below dense cost" -- while being
    # exactly solvable.  Stabilizer rank can be driven arbitrarily wrong here by
    # adding magic that costs the real simulator nothing.
    from .matchgate import matchgate_plan
    fermion = matchgate_plan(circuit)
    log2_fermion = fermion.log2_cost if fermion.valid else math.inf
    # A classical simulator picks whichever strategy is cheaper.
    log2_cost = min(float(n), log2_stabrank, log2_basis, log2_tensor, log2_fermion)

    raw = 0.0 if n == 0 else min(
        log2_stabrank, log2_basis, log2_tensor, log2_fermion) / n
    q_upper = 0.0 if n == 0 else max(0.0, min(1.0, log2_cost / n))
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
            "q_sim_upper = 0 regardless of depth, width or entanglement."
        )
    if q_upper >= 1.0:
        notes.append("no implemented strategy simulates this core below dense cost; "
                     "this is an upper bound, not a hardness certificate.")
    if plan.valid and log2_tensor < min(log2_stabrank, log2_basis, float(n)):
        notes.append(
            f"tensor-network contraction is the cheapest strategy here: induced "
            f"width {plan.width} over {plan.vertices} bonds charges "
            f"{log2_tensor:.2f} bits where stabilizer rank charges "
            f"{log2_stabrank:.2f} and dense charges {n}. The core is structurally "
            "local; its non-Clifford content is not connected enough to be "
            "expensive.")
    elif not plan.valid:
        notes.append(f"tensor-network path excluded from the minimum: "
                     f"{plan.reason}. An excluded path cannot lower the bound.")
    if fermion.valid:
        notes.append(
            f"core is a nearest-neighbour free-fermion (matchgate) evolution: "
            f"{fermion.two_qubit_gates} matchgate(s) and "
            f"{fermion.diagonal_gates} diagonal gate(s), simulable in polynomial "
            f"time regardless of T-count. Stabilizer rank would have charged "
            f"{log2_stabrank:.2f} bits on a T-count of {t_total:.0f}, and "
            f"contraction {log2_tensor:.2f}; T is a Z-rotation and therefore free "
            "to a free-fermion simulator.")
    if portfolio_counts and len(set(portfolio_counts.values())) > 1:
        notes.append(f"T-count is compiler-dependent across the portfolio: "
                     f"{portfolio_counts}. The reported figure is the minimum.")
    invalid = {k: v for k, v in portfolio_status.items() if v != PathStatus.VALID}
    if invalid:
        notes.append(f"portfolio paths excluded from the minimum: {invalid}. An "
                     "excluded path cannot lower the reported bound.")
    if portfolio and not portfolio_counts and portfolio_status:
        notes.append("no valid compiler path survived; the bound falls back to the "
                     "direct instruction walk, which prices every instruction and "
                     "is therefore still sound.")

    known = unpriceable == 0
    if not known:
        notes.append(f"{unpriceable} unpriceable instruction(s): q_sim_upper is "
                     "UNKNOWN, not low. No implemented strategy bounds this core, "
                     "and reporting a number here would be an understatement "
                     "dressed as a measurement.")

    return ResidencyReport(
        n_qubits=n,
        t_count=t_total,
        opaque_exponent=opaque_exponent,
        q_sim_upper=q_upper if known else float("nan"),
        q_naive=q_naive,
        log2_sim_cost=log2_cost if known else float("inf"),
        raw_exponent=raw,
        q_sim_lower=0.0,
        lower_justification="none: no lower-bound technology applied",
        portfolio=portfolio_counts,
        portfolio_status=portfolio_status,
        class_counts=counts,
        notes=notes,
        q_sim_upper_known=known,
        typed_remainders=remainders,
    )


def naive_residency(circuit: QuantumCircuit) -> float:
    """The draft QSigma-infinity metric, kept for comparison."""
    return simulation_residency(circuit, portfolio=False).q_naive


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

    Included specifically to be *excluded* from q_sim_upper: a GHZ state maximises
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


def certified_residency(*args, **kwargs) -> ResidencyReport:
    """Deprecated alias for :func:`simulation_residency`.

    The original name overclaimed: an upper bound on the cost of the simulation
    strategies implemented here is not a certificate that no cheaper classical
    algorithm exists.  Kept so existing call sites keep working.
    """
    import warnings
    warnings.warn("certified_residency is a misnomer; use simulation_residency. "
                  "The quantity is an upper bound, not a certificate.",
                  DeprecationWarning, stacklevel=2)
    return simulation_residency(*args, **kwargs)
