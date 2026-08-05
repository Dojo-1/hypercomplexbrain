"""Refuting a remainder this repository recorded one round earlier.

R1G's planarity remainder said `matchgate_plan`'s nearest-neighbour condition is
a one-dimensional restriction where free-fermion tractability only needs
planarity, and that there are plausibly free-fermion circuits on planar but
non-linear layouts that the certified path wrongly refuses.

It is measured here and it is wrong. A matchgate matrix on non-adjacent qubits
is not a free-fermion operation: under Jordan-Wigner it picks up the `Z` string
of the qubits it jumps, and the covariant defect reads 6.93 rather than 0. The
refusal is semantically correct.

What IS a false negative is arity, not locality, and the second group of tests
pins that instead. The third group measures what the adjacency condition costs.
"""

from __future__ import annotations

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import RXXGate, UnitaryGate, iSwapGate
from qiskit.quantum_info import Operator

from aionq.fishnet import gaussian_unitary, random_generator
from aionq.majorana import gaussian_defect, majorana_operators
from aionq.matchgate import matchgate_plan
from aionq.mode_locality import (adjacency_report, lie_closure_dimension,
                                 reachable_fraction, reachable_generators,
                                 so_basis)


def _unitary(circuit) -> np.ndarray:
    return np.array(Operator(circuit).data)


# --------------------------------------------------------------------------
# 1. The refutation: adjacency is semantic, not a layout convention
# --------------------------------------------------------------------------

@pytest.mark.parametrize("gate,name", [(iSwapGate(), "iswap"), (RXXGate(0.7), "rxx")])
def test_a_matchgate_on_non_adjacent_qubits_is_not_a_free_fermion_operation(gate, name):
    """The measurement that refutes R1G's planarity remainder.

    The SAME matrix is free-fermion on adjacent qubits and not free-fermion one
    qubit further apart. Nothing about the gate changed; the Jordan-Wigner string
    of the qubit it jumped did. So `matchgate_plan` is not imposing a relaxable
    layout convention, it is enforcing the encoding.
    """
    operators = majorana_operators(3)

    adjacent = QuantumCircuit(3)
    adjacent.append(gate, [0, 1])
    assert matchgate_plan(adjacent).valid
    assert gaussian_defect(_unitary(adjacent), operators) == pytest.approx(0.0, abs=1e-9)

    spanning = QuantumCircuit(3)
    spanning.append(gate, [0, 2])
    assert not matchgate_plan(spanning).valid
    assert gaussian_defect(_unitary(spanning), operators) > 1.0


def test_the_report_agrees_on_every_placement_in_a_three_qubit_register():
    """Certified and Gaussian coincide on all three pairs, not just the chosen one."""
    report = adjacency_report(3)
    for pair, row in report["placements"].items():
        assert row["certified"] == row["adjacent"], pair
        assert (row["defect"] < 1e-9) == row["adjacent"], pair


# --------------------------------------------------------------------------
# 2. Where the false negative actually is: arity
# --------------------------------------------------------------------------

def test_a_genuinely_gaussian_multi_qubit_unitary_is_refused_for_its_arity():
    """Semantic in locality, syntactic in arity: it recognises presentations.

    A three-qubit unitary built from a quadratic Majorana generator is
    free-fermion to 2.8e-15 and is refused with "acts on 3 qubits". The refusal
    raises the reported bound, which is the safe direction for a bound and the
    wrong direction for a measurement: a poly-time-simulable operation is priced
    as hard for how it was written down.
    """
    operators = majorana_operators(3)
    unitary = gaussian_unitary(random_generator(6, seed=4), operators)
    assert gaussian_defect(unitary, operators) == pytest.approx(0.0, abs=1e-9)

    circuit = QuantumCircuit(3)
    circuit.append(UnitaryGate(unitary, label="gaussian"), [0, 1, 2])
    plan = matchgate_plan(circuit)

    assert not plan.valid
    assert "3 qubits" in plan.reason


# --------------------------------------------------------------------------
# 3. What adjacency costs: a vanishing slice, but a generating one
# --------------------------------------------------------------------------

@pytest.mark.parametrize("qubits", list(range(2, 20)))
def test_the_reachable_count_is_five_n_minus_four_exactly(qubits):
    """`n` same-qubit pairs plus `4(n-1)` adjacent pairs. Counted, not fitted."""
    report = reachable_fraction(qubits)
    assert report["reachable"] == report["closed_form"] == 5 * qubits - 4
    assert report["total"] == qubits * (2 * qubits - 1)
    assert len(so_basis(qubits)) == report["total"]


@pytest.mark.parametrize("qubits,expected", [(2, 1.0), (4, 16 / 28), (8, 36 / 120),
                                             (16, 76 / 496)])
def test_the_reachable_fraction_vanishes_like_five_over_two_n(qubits, expected):
    """100% at n=2, 57% at n=4, 30% at n=8, 15.3% at n=16.

    The directly expressible slice of the free-fermion Lie algebra shrinks to a
    vanishing fraction. This is the locality residual of R1B stated
    algebraically: adjacency selects a `5/(2n)` slice of `so(2n)`, and WHICH
    slice depends on the qubit labelling -- which is why that residual, alone
    among the four, moves under the frame group.
    """
    report = reachable_fraction(qubits)
    assert report["fraction"] == pytest.approx(expected, rel=1e-12)
    assert report["fraction"] == pytest.approx(report["asymptotic"], rel=0.25)


@pytest.mark.parametrize("qubits", [3, 4])
def test_the_vanishing_slice_is_nonetheless_generating(qubits):
    """Adjacency costs depth, not expressiveness -- measured by explicit closure.

    11 reachable generators Lie-generate all 15 dimensions of `so(6)`; 16
    generate all 28 of `so(8)`. Without this the fraction above would read as a
    loss of reachable operations, which it is not.
    """
    report = adjacency_report(qubits) if qubits == 3 else None
    dimension = lie_closure_dimension(
        [matrix for _, matrix in reachable_generators(qubits)])

    assert dimension == qubits * (2 * qubits - 1)
    if report is not None:
        assert report["generating"]
        assert report["closure"] == report["so_dimension"] == 15
        assert report["reachable"] == 11


def test_a_strict_subset_of_generators_does_not_generate():
    """The closure instrument must be able to report failure, or it proves nothing.

    Same-qubit generators only -- no coupling between qubits at all -- span `n`
    dimensions and close on themselves. If the closure routine returned the full
    dimension here too, its answer above would be meaningless.
    """
    qubits = 3
    same_qubit = [matrix for pair, matrix in so_basis(qubits)
                  if pair[0] // 2 == pair[1] // 2]
    assert len(same_qubit) == qubits
    assert lie_closure_dimension(same_qubit) < qubits * (2 * qubits - 1)
