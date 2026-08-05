"""How far a circuit is from free fermions, as a number rather than a bit.

Every member of the simulation-strategy portfolio behind ``q_sim_upper`` is
all-or-nothing.  ``matchgate_plan`` charges 0 on the free-fermion class and
switches off entirely one gate outside it; ``basis_permutation`` and
``stabilizer_rank`` are the same shape.  Measured consequence, from
``gf_frames``: over the 240 affine frames of AGL(1,16) the minimum takes at most
two values, so the hardness landscape over the frame group is a **step, not a
saddle**.  A step has no gradient to read and no direction to follow.

This module replaces the free-fermion bit with four residuals, one per reason
``matchgate_plan`` refuses, each of which is zero exactly when that reason is
satisfied and grows continuously as it fails:

    parity      ||off-block part of U||_F        U mixes fermionic parity
    determinant |det A - det B|                  the blocks have unequal dets
    locality    max(0, |i - j| - 1)              the gate is not nearest-neighbour
    diagonal    ||off-diagonal part of u||_F     a one-qubit gate is not a Z-rotation

WHAT THIS IS NOT.  It is **not** a graded certificate, and nothing here may be
read as one.  ``matchgate_plan`` is sound because a theorem (Valiant;
Terhal-DiVincenzo; Jozsa-Miyake) says the exactly-free-fermion case is poly-time
simulable.  There is no theorem here bounding simulation cost by a small nonzero
defect, and this module does not supply one.  A circuit at defect 1e-3 is not
"almost poly-time simulable"; it is a circuit whose certificate does not apply,
at a measured distance from one whose does.  Consequently ``q_sim_upper`` does
not import this module and must not: an upper bound that consulted a quantity
with no cost theorem behind it would stop being an upper bound.

WHAT IT IS FOR.  Two things the bit cannot do.

*It gives the cliff a shape.*  ``RZZ(t)`` has ``det A = exp(-it)`` and
``det B = exp(+it)``, so the boolean certificate holds on exactly the two points
``t in {0, pi}`` of the whole family, while the determinant residual is
``2|sin t|`` -- smooth, maximal at ``t = pi/2``, and exact rather than
approximated.  The refusal is not a wall; it is a function, and it was always a
function.

*It says where the frame-dependence lives.*  Relabelling qubits does not change
a single gate matrix, only which wires the gates sit on.  So parity, determinant
and diagonal are invariant on the whole frame orbit and **locality is the only
residual that moves** -- measured over all 240 frames of AGL(1,16), not sampled.
The free-fermion certificate's notorious frame-sensitivity is therefore entirely
a routing quantity, and where the bit reports two values over the orbit the
residual reports a ranked landscape.  That is the difference between a step and
something with a gradient, and it is obtained without touching the bound.

A NOTE ON WHICH RESIDUALS ARE DISTANCES.  Only ``parity`` is one.  The
parity-preserving matrices form a linear subspace, so the nearest point in
Frobenius norm is obtained by zeroing the off-block entries and the residual is
exactly the distance to it.  ``determinant`` is a proxy: it is a defect in a
scalar constraint, not a distance to the variety that constraint cuts out, and
when ``parity`` is large the blocks it reads are a projection rather than the
gate's actual blocks.  Reading the four as commensurable would be the error this
module exists to avoid, so they are reported separately and the aggregates are
labelled as aggregates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "GateDefect",
    "CircuitDefect",
    "matrix_parity_defect",
    "matrix_determinant_defect",
    "matrix_diagonal_defect",
    "gate_defect",
    "matchgate_defect",
]

#: Entries of a 4x4 unitary that couple the even-parity subspace span{|00>,|11>}
#: to the odd-parity subspace span{|01>,|10>}.  A matchgate has all eight zero.
_OFF_BLOCK = ((0, 1), (0, 2), (3, 1), (3, 2), (1, 0), (2, 0), (1, 3), (2, 3))

_SKIPPABLE = frozenset({"barrier", "delay", "id", "snapshot"})
_REFUSED = frozenset({
    "measure", "reset", "if_else", "while_loop", "for_loop", "switch_case",
    "break_loop", "continue_loop", "store",
})


def matrix_parity_defect(matrix) -> float:
    """Frobenius norm of the part of ``U`` that mixes fermionic parity.

    This is an exact distance.  The parity-preserving 4x4 matrices are a linear
    subspace -- the eight coordinates in ``_OFF_BLOCK`` set to zero -- so the
    nearest parity-preserving matrix is the orthogonal projection, and the norm
    of what is discarded is the Frobenius distance to the subspace.
    """
    matrix = np.asarray(matrix)
    if matrix.shape != (4, 4):
        return math.inf
    return float(np.sqrt(sum(abs(matrix[row, column]) ** 2
                             for row, column in _OFF_BLOCK)))


def matrix_determinant_defect(matrix) -> float:
    """``|det A - det B|`` on the even- and odd-parity blocks.

    A defect in a constraint, not a distance to the set the constraint cuts out,
    and the blocks are read by projection, so this is only interpretable as a
    near-distance once `matrix_parity_defect` is small.  It is nonetheless the
    residual that carries the family's whole content: it is the condition that
    separates matchgates from the parity-preserving gates that are not
    free-fermion evolutions, and hence the only thing standing between the
    strategy and certifying SWAP -- which lifts matchgates to universality.
    """
    matrix = np.asarray(matrix)
    if matrix.shape != (4, 4):
        return math.inf
    even = np.array([[matrix[0, 0], matrix[0, 3]],
                     [matrix[3, 0], matrix[3, 3]]])
    odd = np.array([[matrix[1, 1], matrix[1, 2]],
                    [matrix[2, 1], matrix[2, 2]]])
    return float(abs(np.linalg.det(even) - np.linalg.det(odd)))


def matrix_diagonal_defect(matrix) -> float:
    """Frobenius norm of the off-diagonal part of a one-qubit gate.

    Zero exactly for a Z-rotation, whose Jordan-Wigner image ``-i c_{2k-1} c_2k``
    is quadratic in Majoranas.  Also an exact distance, for the same reason as
    `matrix_parity_defect`: the diagonal matrices are a linear subspace.
    """
    matrix = np.asarray(matrix)
    if matrix.shape != (2, 2):
        return math.inf
    return float(np.sqrt(abs(matrix[0, 1]) ** 2 + abs(matrix[1, 0]) ** 2))


@dataclass(frozen=True)
class GateDefect:
    """One instruction's distance from the free-fermion conditions."""

    name: str
    qubits: tuple
    parity: float = 0.0
    determinant: float = 0.0
    locality: float = 0.0
    diagonal: float = 0.0

    @property
    def total(self) -> float:
        return self.parity + self.determinant + self.locality + self.diagonal

    @property
    def worst(self) -> float:
        return max(self.parity, self.determinant, self.locality, self.diagonal)


@dataclass
class CircuitDefect:
    """A circuit's residuals, per gate and aggregated.

    ``applicable`` is False for anything `matchgate_plan` refuses categorically
    rather than metrically -- a measurement, a reset, control flow, a gate with
    no unitary matrix, a gate on three or more qubits.  Those are not far from
    free fermions; they are outside the domain where "far" means anything, and
    inventing a number for them would be the whole error this module warns about
    committed at the top level.
    """

    applicable: bool = True
    reason: str = ""
    gates: tuple = field(default_factory=tuple)

    @property
    def total(self) -> float:
        """Sum over gates: extensive, so it grows with circuit size."""
        return sum(gate.total for gate in self.gates) if self.applicable else math.inf

    @property
    def worst(self) -> float:
        """Max over gates: intensive, and the one the boolean thresholds."""
        if not self.applicable:
            return math.inf
        return max((gate.worst for gate in self.gates), default=0.0)

    @property
    def by_residual(self) -> dict:
        """Where the defect actually sits, which is the diagnostic content."""
        if not self.applicable:
            return {}
        return {name: sum(getattr(gate, name) for gate in self.gates)
                for name in ("parity", "determinant", "locality", "diagonal")}

    def summary(self) -> str:
        if not self.applicable:
            return f"defect undefined: {self.reason}"
        parts = ", ".join(f"{name}={value:.4g}"
                          for name, value in self.by_residual.items())
        return f"worst={self.worst:.4g} total={self.total:.4g} [{parts}]"


def gate_defect(name: str, matrix, indices) -> GateDefect:
    """Residuals for a single instruction, given its matrix and wire indices."""
    if len(indices) == 1:
        return GateDefect(name, tuple(indices),
                          diagonal=matrix_diagonal_defect(matrix))
    first, second = indices
    return GateDefect(
        name, tuple(indices),
        parity=matrix_parity_defect(matrix),
        determinant=matrix_determinant_defect(matrix),
        locality=float(max(0, abs(first - second) - 1)),
    )


def matchgate_defect(circuit) -> CircuitDefect:
    """Measure ``circuit``'s distance from the nearest-neighbour matchgate class.

    Agrees with `matchgate.matchgate_plan` on the boolean question wherever that
    function is metric: on an all-unitary circuit, the plan is valid exactly when
    every residual vanishes.  The two are kept in separate modules on purpose --
    `matchgate_plan` carries a soundness theorem and feeds a published bound,
    this carries neither and feeds nothing.
    """
    gates = []
    for instruction in circuit.data:
        operation = instruction.operation
        name = getattr(operation, "name", "")
        if name in _SKIPPABLE:
            continue
        if name in _REFUSED or getattr(operation, "condition", None) is not None:
            return CircuitDefect(False, f"instruction {name!r} is not a unitary gate")
        if getattr(operation, "num_clbits", 0):
            return CircuitDefect(False, f"instruction {name!r} touches classical bits")

        try:
            matrix = operation.to_matrix()
        except Exception:
            matrix = None
        if matrix is None:
            return CircuitDefect(False, f"instruction {name!r} exposes no unitary matrix")

        indices = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        if len(indices) not in (1, 2):
            return CircuitDefect(
                False, f"gate {name!r} acts on {len(indices)} qubits; free-fermion "
                       "evolution is generated by quadratic terms only, and a "
                       "distance from a domain one is not in is not a distance")
        gates.append(gate_defect(name, matrix, indices))

    return CircuitDefect(True, gates=tuple(gates))
