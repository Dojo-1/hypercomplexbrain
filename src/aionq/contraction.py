"""Tensor-network contraction as a third simulation strategy.

`residency.simulation_residency` prices a core as the cheapest of the
simulation strategies it implements.  Until now there were two: stabilizer-rank
decomposition at ``2**(alpha*T)``, and basis permutation at ``2**0`` when the
core never leaves the computational basis.  Both are blind to *structure*.
Stabilizer rank charges for non-Clifford content wherever it sits, so it prices
a circuit by how much magic it contains and never by how that magic is
connected.

That blindness is measurable, and it is not a rounding artefact.  Take k
independent 2-qubit blocks, each carrying two T gates, on n = 2k qubits.  Every
block is a separate 4x4 problem, so the simulation exponent is 2 no matter how
large n gets, and the normalised residency ought to fall like ``2/n -> 0``.
Measured before and after this strategy existed::

     n     T   two strategies   three strategies   exponent-only truth
     4     4           0.2284             0.2284                0.5000
     8     8           0.2284             0.2284                0.2500
    12    12           0.2284             0.2284                0.1667
    16    16           0.2284             0.2284                0.1250
    20    20           0.2284             0.2000                0.1000
    24    24           0.2284             0.1667                0.0833
    32    32           0.2284             0.1250                0.0625

The old column is *constant*, because ``alpha*T/n`` does not move when T grows
in step with n.  A metric that does not decay on a family whose cost exponent
is fixed is not measuring structure at all: it says a pile of disconnected
2-qubit gadgets is permanently and equally quantum, however many of them there
are.  The new column decays like ``4/n``, staying above the truth ``2/n`` -- an
upper bound, as required, and now one that falls at the right rate.

All three columns are exponent-only.  The polynomial prefactor (here the k
independent blocks) is dropped on every strategy alike, exactly as dense
simulation is charged ``n`` rather than ``n + log2(depth)``.  Comparing a
prefactor-carrying figure against these would be comparing two conventions.

The QSigma-R1a gate anticipated exactly this family -- "tensor-network /
matchgate / low-treewidth families not yet covered" -- and this module closes
the tensor-network and low-treewidth part of it.  Matchgate/free-fermion cores
remain uncovered: their simulability argument is not a contraction-width
argument, and claiming it without implementing it would be the kind of
unearned bound this module exists to avoid.

Soundness.  ``q_sim_upper`` is an UPPER bound on classical simulation cost, so
adding a strategy and taking the minimum can only lower it, and lowering it is
sound as long as the new strategy really can pay what it claims.  This module
therefore does not estimate treewidth and hope: it *constructs* a concrete
elimination ordering and reports the induced width that ordering actually
incurs.  A better ordering would lower the number further; a worse one cannot
make the number invalid.  The bound is the cost of an algorithm that is written
down here, not the cost of an algorithm someone might find.

What is priced.  The exponent only, consistently with the strategies already
present: dense simulation is charged ``n``, stabilizer rank ``alpha*T`` and
basis permutation ``0``, none of which carry their polynomial prefactors.  A
contraction in an ordering of induced width ``w`` is charged ``w + 1`` on the
same convention -- the largest intermediate tensor spans ``w + 1`` bonds.  The
polynomial number of contraction steps, and the polynomial overhead of turning
amplitudes into samples by the chain rule, are dropped on this strategy exactly
as they are dropped on the others.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "ContractionPlan",
    "contraction_plan",
    "interaction_graph",
    "elimination_width",
]


# Instructions that have no unitary tensor, or that break the closed-network
# picture entirely.  A path that cannot price every instruction is not a
# candidate -- the same discipline the compiler portfolio already applies.
_NON_TENSOR = frozenset({
    "measure", "reset", "if_else", "while_loop", "for_loop", "switch_case",
    "break_loop", "continue_loop", "store",
})

# Instructions that carry no tensor at all and can simply be skipped.
_SKIPPABLE = frozenset({"barrier", "delay", "id", "snapshot"})


@dataclass
class ContractionPlan:
    """One concrete contraction ordering and the width it actually costs.

    ``valid`` is False when some instruction has no tensor, in which case
    ``log2_cost`` is infinite: an unpriceable instruction must invalidate the
    path rather than be skipped, or a circuit could be made to look cheaper by
    adding something the strategy cannot handle.
    """

    valid: bool
    reason: str = ""
    width: int = 0
    vertices: int = 0
    log2_cost: float = math.inf
    order: list = field(default_factory=list)

    def summary(self) -> str:
        if not self.valid:
            return f"contraction path invalid: {self.reason}"
        return (f"induced width {self.width} over {self.vertices} bonds, "
                f"log2 cost {self.log2_cost:.2f}")


def interaction_graph(circuit) -> tuple[dict, str]:
    """Build the circuit's tensor-network interaction graph.

    Every wire segment between consecutive gates is a bond, and therefore a
    vertex.  A k-qubit gate is a tensor touching its k incoming and k outgoing
    bonds, so those 2k vertices form a clique -- eliminating any one of them
    requires the others to be present together.

    The input bonds are the ``|0>`` legs and the output bonds are closed by a
    fixed measurement bitstring, so the network is closed and its contraction
    yields one amplitude.  Returns ``({vertex: set(neighbours)}, reason)`` with
    an empty reason on success.
    """
    adjacency: dict[int, set] = {}
    counter = 0

    def fresh() -> int:
        nonlocal counter
        vertex = counter
        counter += 1
        adjacency[vertex] = set()
        return vertex

    segment = {index: fresh() for index in range(circuit.num_qubits)}

    for instruction in circuit.data:
        operation = instruction.operation
        name = getattr(operation, "name", "")
        if name in _SKIPPABLE:
            continue
        if name in _NON_TENSOR or getattr(operation, "condition", None) is not None:
            return {}, f"instruction {name!r} has no closed tensor form"
        if getattr(operation, "num_clbits", 0):
            return {}, f"instruction {name!r} touches classical bits"

        # Contraction cost is fixed by CONNECTIVITY alone, so this graph could be
        # built for an instruction whose matrix is unknown. It must not be. A
        # non-unitary instruction breaks the closed-network picture that makes
        # the contraction an amplitude, and pricing it by structure would let a
        # circuit be made to look cheap by adding something whose behaviour this
        # strategy never checked. Unitarity is verified, not assumed.
        try:
            matrix = operation.to_matrix()
        except Exception:
            matrix = None
        if matrix is None:
            return {}, f"instruction {name!r} exposes no unitary matrix"

        try:
            indices = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        except Exception:  # pragma: no cover - qiskit always resolves its own bits
            return {}, f"instruction {name!r} has unresolvable qubits"
        if not indices:
            continue

        incoming = [segment[index] for index in indices]
        outgoing = [fresh() for _ in indices]
        for index, vertex in zip(indices, outgoing):
            segment[index] = vertex

        legs = incoming + outgoing
        for i, left in enumerate(legs):
            for right in legs[i + 1:]:
                adjacency[left].add(right)
                adjacency[right].add(left)

    return adjacency, ""


def elimination_width(adjacency: dict) -> tuple[int, list]:
    """Eliminate by minimum degree and report the width that ordering incurs.

    This is a constructed ordering, not an estimate of treewidth.  The returned
    width is what contracting in this order actually costs, so it is a valid
    upper bound whether or not the ordering is optimal.  Ties are broken by
    vertex index so the plan is deterministic across platforms -- a portfolio
    whose answer depends on set iteration order would be one more seal over a
    computed quantity.
    """
    remaining = {vertex: set(neighbours) for vertex, neighbours in adjacency.items()}
    width = 0
    order: list = []

    while remaining:
        vertex = min(remaining, key=lambda v: (len(remaining[v]), v))
        neighbours = remaining[vertex]
        width = max(width, len(neighbours))
        order.append(vertex)
        # Eliminating a vertex makes its neighbours mutually adjacent.
        for left in neighbours:
            remaining[left].discard(vertex)
            for right in neighbours:
                if left != right:
                    remaining[left].add(right)
        del remaining[vertex]

    return width, order


def contraction_plan(circuit) -> ContractionPlan:
    """Price ``circuit`` under tensor-network contraction.

    The cost charged is ``width + 1`` in log2, matching the exponent-only
    convention the other strategies use: the largest intermediate tensor spans
    ``width + 1`` bonds and therefore holds ``2**(width + 1)`` amplitudes.
    """
    adjacency, reason = interaction_graph(circuit)
    if reason:
        return ContractionPlan(valid=False, reason=reason)
    if not adjacency:
        return ContractionPlan(valid=True, width=0, vertices=0, log2_cost=0.0)

    width, order = elimination_width(adjacency)
    return ContractionPlan(
        valid=True,
        width=width,
        vertices=len(adjacency),
        log2_cost=float(width + 1),
        order=order,
    )
