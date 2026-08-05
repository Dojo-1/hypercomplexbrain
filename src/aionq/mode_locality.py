"""Adjacency is not a syntactic convenience: it is the encoding, measured.

R1G closed with a remainder claiming that `matchgate_plan`'s nearest-neighbour
condition is a ONE-DIMENSIONAL restriction where the classical tractability of
free-fermion counting -- Kasteleyn orientations, the FKT algorithm -- only needs
PLANARITY, which Euler's formula supplies and which is strictly weaker.  The
remainder concluded that there are plausibly free-fermion circuits on planar but
non-linear layouts that the certified path refuses, and called that an
unmeasured false negative.

**That remainder is wrong, and this module is the measurement that refutes it.**

    iSWAP on qubits (0,1)   matchgate_plan valid    gaussian_defect 0.0000
    iSWAP on qubits (1,2)   matchgate_plan valid    gaussian_defect 0.0000
    iSWAP on qubits (0,2)   matchgate_plan REFUSES  gaussian_defect 6.9282
    RXX   on qubits (0,2)   matchgate_plan REFUSES  gaussian_defect 3.6442

A matchgate matrix placed on non-adjacent qubits is **not a free-fermion
operation at all**.  Under Jordan-Wigner the modes of qubit ``k`` carry a string
of ``Z``s from every qubit below it, so a two-qubit gate spanning a gap picks up
the string of the qubits it jumps, and the resulting operator is not quadratic in
Majoranas.  The refusal is semantically correct.  `matchgate_plan` is not
imposing a layout convention it could relax; it is enforcing the encoding.

WHERE THE REAL GAP IS: ARITY, NOT LOCALITY.  A genuinely Gaussian three-qubit
unitary -- built from a quadratic Majorana generator, ``gaussian_defect``
2.8e-15 -- is refused by `matchgate_plan` with "acts on 3 qubits".  So the
certificate is *semantic* in its locality condition and *syntactic* in its arity
condition: it recognises presentations, not operations.  The refusal raises the
reported bound, which is the safe direction, and it means a poly-time-simulable
circuit can be priced as hard purely for how it was written down.

WHAT THE ADJACENCY CONDITION COSTS, IN CLOSED FORM.  A quadratic generator
``c_j c_k`` is directly expressible as a same-or-adjacent-qubit gate exactly when
``|j//2 - k//2| <= 1``.  Counting those:

    reachable(n) = 5n - 4          verified exactly for n = 2 .. 19
    dim so(2n)   = n(2n - 1)
    fraction     = (5n - 4) / (n(2n - 1))  ~  5 / (2n)

    n = 2:  6/6   = 100%
    n = 4:  16/28 = 57.1%
    n = 8:  36/120 = 30.0%
    n = 16: 76/496 = 15.3%

So the directly expressible slice of the free-fermion Lie algebra shrinks to a
vanishing fraction as ``n`` grows.  It remains **generating**: the 11 reachable
generators at ``n = 3`` Lie-generate all 15 dimensions of ``so(6)``, and 16
generate all 28 of ``so(8)``, both verified by explicit closure.  Adjacency costs
depth, not expressiveness.

AND THAT IS THE LOCALITY RESIDUAL, ALGEBRAICALLY.  R1B measured that of the four
residuals in the free-fermion certificate exactly one moves under the frame
group, and it is ``locality``.  R1C measured that of the four strategies in the
portfolio exactly one is frame-resolving, and it is the one imposing adjacency.
This is why: adjacency selects a ``5/(2n)`` slice of ``so(2n)``, and *which*
slice depends on the qubit labelling.  The residual that is written in indices is
frame-dependent because the structure it refers to genuinely is.

WHERE EULER STILL BELONGS.  Not at the gate layout -- at the **encoding**.
Jordan-Wigner is a one-dimensional encoding, and its strings are what make
non-adjacent gates non-Gaussian.  Encodings whose locality structure is
two-dimensional exist, and under one of those the reachable slice would be
determined by a planar mode graph rather than by a line.  No such encoding is
implemented here and none of the above is evidence about one.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "reachable_generators",
    "reachable_fraction",
    "adjacency_report",
    "lie_closure_dimension",
    "so_basis",
]


def so_basis(qubits: int) -> tuple:
    """Every quadratic generator ``c_j c_k``, as an antisymmetric ``2n x 2n``.

    Returned with its mode pair, because which pair a generator belongs to is
    exactly what the adjacency test reads.
    """
    modes = 2 * qubits
    out = []
    for left in range(modes):
        for right in range(left + 1, modes):
            matrix = np.zeros((modes, modes))
            matrix[left, right], matrix[right, left] = 1.0, -1.0
            out.append(((left, right), matrix))
    return tuple(out)


def reachable_generators(qubits: int) -> tuple:
    """Generators expressible as a same-or-adjacent-qubit gate: ``|j//2 - k//2| <= 1``.

    Mode ``j`` lives on qubit ``j // 2``, so this is the condition that the two
    modes a generator couples sit on one qubit or on two neighbouring ones --
    exactly the gates `matchgate_plan` accepts.
    """
    return tuple((pair, matrix) for pair, matrix in so_basis(qubits)
                 if abs(pair[0] // 2 - pair[1] // 2) <= 1)


def reachable_fraction(qubits: int) -> dict:
    """``(5n - 4) / (n(2n - 1))``, with both the count and the closed form.

    The closed form is not fitted: ``n`` same-qubit pairs plus ``4(n-1)``
    adjacent-qubit pairs is ``5n - 4``.  It is asserted against the explicit
    count in `tests/test_mode_locality.py` for ``n = 2 .. 19`` rather than
    trusted.
    """
    reachable = len(reachable_generators(qubits))
    total = qubits * (2 * qubits - 1)
    return {
        "qubits": qubits,
        "reachable": reachable,
        "closed_form": 5 * qubits - 4,
        "total": total,
        "fraction": reachable / total,
        "asymptotic": 5.0 / (2.0 * qubits),
    }


def lie_closure_dimension(generators, tolerance: float = 1e-9,
                          rounds: int = 12) -> int:
    """Dimension of the Lie algebra generated by ``generators`` under bracketing.

    Repeated commutators, with each new element kept only if it has a component
    orthogonal to everything already found.  Used to establish that adjacency
    costs depth and not expressiveness -- a claim that would be worthless
    asserted and is cheap to measure.
    """
    matrices = [np.asarray(matrix, dtype=float) for matrix in generators]
    if not matrices:
        return 0
    span = np.linalg.qr(np.array([m.ravel() for m in matrices]).T,
                        mode="reduced")[0]
    current = list(matrices)
    for _ in range(rounds):
        found = []
        for left in current:
            for right in current:
                bracket = left @ right - right @ left
                vector = bracket.ravel()
                residual = vector - span @ (span.conj().T @ vector)
                if np.linalg.norm(residual) > tolerance:
                    span = np.hstack([span,
                                      (residual / np.linalg.norm(residual))[:, None]])
                    found.append(bracket)
        if not found:
            break
        current = current + found
    return int(span.shape[1])


def adjacency_report(qubits: int = 3) -> dict:
    """Reach, closure, and the semantic check, in one place.

    The semantic check is the load-bearing part and is why this module exists:
    it is what refutes the planarity remainder of R1G. A matchgate matrix on
    non-adjacent qubits is measured, not argued, to be non-Gaussian.
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import iSwapGate
    from qiskit.quantum_info import Operator

    from .majorana import gaussian_defect, majorana_operators
    from .matchgate import matchgate_plan

    operators = majorana_operators(qubits)
    placements = {}
    for left in range(qubits):
        for right in range(left + 1, qubits):
            circuit = QuantumCircuit(qubits)
            circuit.append(iSwapGate(), [left, right])
            unitary = np.array(Operator(circuit).data)
            placements[(left, right)] = {
                "adjacent": right - left == 1,
                "certified": matchgate_plan(circuit).valid,
                "defect": gaussian_defect(unitary, operators),
            }

    reach = reachable_fraction(qubits)
    reach["closure"] = lie_closure_dimension(
        [matrix for _, matrix in reachable_generators(qubits)])
    reach["so_dimension"] = qubits * (2 * qubits - 1)
    reach["generating"] = reach["closure"] == reach["so_dimension"]
    reach["placements"] = placements
    return reach
