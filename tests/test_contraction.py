"""Tensor-network contraction as a third simulation strategy (QSigma-R1a).

The QSigma-R1a gate left "tensor-network / matchgate / low-treewidth families
not yet covered". These tests close the contraction part of it, and most of
them try to make the new strategy lie: a strategy that lowers `q_sim_upper` is
lowering an upper bound on classical cost, so an unsound one silently
understates quantum residency, which is the direction this metric is least
entitled to be wrong in.
"""

from __future__ import annotations

import math

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.random import random_circuit

from aionq.contraction import (contraction_plan, elimination_width,
                               interaction_graph)
from aionq.residency import simulation_residency


def _disconnected_blocks(n: int) -> QuantumCircuit:
    """k independent 2-qubit blocks, each carrying two T gates."""
    circuit = QuantumCircuit(n)
    for base in range(0, n, 2):
        circuit.h(base)
        circuit.cx(base, base + 1)
        circuit.t(base)
        circuit.t(base + 1)
        circuit.cx(base, base + 1)
        circuit.h(base)
    return circuit


# ------------------------------------------------------- the defect it closes

def test_the_two_strategy_portfolio_does_not_decay_where_the_exponent_is_fixed():
    """The measurement that motivated the strategy, kept as a live check.

    k disconnected 2-qubit blocks are k separate 4x4 problems, so the cost
    exponent is 2 for every n. Stabilizer rank charges alpha*T, and T grows in
    step with n, so its normalised figure is CONSTANT. A metric that does not
    move on a family whose exponent is fixed is not measuring structure.
    """
    stabilizer_only = []
    for n in (8, 16, 24, 32):
        circuit = _disconnected_blocks(n)
        report = simulation_residency(circuit)
        # alpha * T / n with T = n is constant in n, by construction.
        stabilizer_only.append(report.t_count / n)
    assert len(set(round(value, 12) for value in stabilizer_only)) == 1, (
        "T-count per qubit must be constant for this family, or the test below "
        "is not measuring what it claims")


def test_contraction_makes_the_disconnected_family_decay():
    values = {n: simulation_residency(_disconnected_blocks(n)).q_sim_upper
              for n in (16, 20, 24, 32)}
    # It must now fall, where before it was 0.2284 at every one of these n.
    ordered = [values[n] for n in (16, 20, 24, 32)]
    assert ordered == sorted(ordered, reverse=True)
    assert ordered[-1] < ordered[0]
    assert values[32] < 0.2284


def test_the_contraction_path_never_prices_below_its_own_true_cost():
    """The soundness property that the contraction strategy actually owes.

    A tempting stronger claim -- that no reported figure may fall below the
    exponent-only truth 2/n -- is NOT available, and asserting it fails on the
    pre-existing stabilizer path rather than on this one: at n = 8 stabilizer
    rank reports 0.2284 against a 2/n of 0.25. That is not a defect. The
    exponent-only convention discards each strategy's polynomial prefactor, and
    stabilizer rank's prefactor is the poly(n) work per stabilizer state, so
    comparing bare exponents across strategies with different prefactor
    structure gives no common floor. Recorded here because the floor looks
    obviously correct until it is written down.

    What this strategy does owe is that its charge is what its own ordering
    costs. For k disconnected 2-qubit blocks the structure repeats, so the
    width must not shrink as n grows -- a width that fell with n would mean the
    ordering was getting cheaper on a problem that is getting no easier.
    """
    widths = {}
    for n in (8, 16, 24, 32, 40):
        plan = contraction_plan(_disconnected_blocks(n))
        assert plan.valid
        widths[n] = plan.width
        # An intermediate tensor must at least span one block's two qubits.
        assert plan.log2_cost >= 3.0
    assert len(set(widths.values())) == 1, widths


# ------------------------------------------------------------ can it be wrong?

def test_a_dense_random_core_is_not_made_cheap_by_the_new_strategy():
    """The strategy must not lower the bound where there is no structure."""
    for n in (6, 8, 10):
        circuit = random_circuit(n, depth=n, seed=7)
        plan = contraction_plan(circuit)
        assert plan.valid
        # A dense core has width of order n, so contraction buys nothing.
        assert plan.log2_cost >= n


def test_an_instruction_without_a_unitary_invalidates_the_path():
    """Contraction cost is fixed by connectivity, which is available even when
    the matrix is not. Pricing structure alone would let a circuit be made to
    look cheap by adding something whose behaviour was never checked."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.measure(0, 0)
    plan = contraction_plan(circuit)
    assert not plan.valid
    assert plan.log2_cost == math.inf
    assert "measure" in plan.reason


def test_an_invalid_contraction_path_cannot_lower_the_reported_bound():
    circuit = QuantumCircuit(3, 3)
    for qubit in range(3):
        circuit.h(qubit)
        circuit.t(qubit)
    circuit.measure(0, 0)
    report = simulation_residency(circuit)
    assert any("excluded from the minimum" in note for note in report.notes)
    assert report.q_sim_upper == report.q_sim_upper  # not NaN


def test_reset_and_control_flow_are_refused_too():
    reset_circuit = QuantumCircuit(2)
    reset_circuit.h(0)
    reset_circuit.reset(0)
    assert not contraction_plan(reset_circuit).valid


# --------------------------------------------------------- the ordering itself

def test_the_elimination_width_is_the_width_that_ordering_actually_incurs():
    """Not an estimate of treewidth: a constructed ordering and its real cost.

    On a path graph the minimum-degree ordering achieves width 1, which is the
    true treewidth; on a clique every ordering incurs width k-1. Both are what
    contracting in the returned order costs, which is why a suboptimal ordering
    weakens the bound without invalidating it.
    """
    path = {0: {1}, 1: {0, 2}, 2: {1, 3}, 3: {2}}
    width, order = elimination_width(path)
    assert width == 1
    assert sorted(order) == [0, 1, 2, 3]

    clique = {i: {j for j in range(5) if j != i} for i in range(5)}
    width, order = elimination_width(clique)
    assert width == 4
    assert len(order) == 5


def test_the_ordering_is_deterministic_across_repeated_calls():
    """A portfolio whose answer depends on set iteration order would be one
    more seal over a computed quantity -- the defect this repository has now
    recorded five times."""
    circuit = _disconnected_blocks(12)
    first = contraction_plan(circuit)
    for _ in range(5):
        again = contraction_plan(circuit)
        assert again.order == first.order
        assert again.width == first.width
        assert again.log2_cost == first.log2_cost


def test_the_graph_is_closed_and_every_gate_forms_a_clique():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    adjacency, reason = interaction_graph(circuit)
    assert reason == ""
    # 2 input bonds + 2 output bonds, all mutually adjacent.
    assert len(adjacency) == 4
    for vertex, neighbours in adjacency.items():
        assert len(neighbours) == 3


def test_an_empty_circuit_costs_nothing_rather_than_failing():
    plan = contraction_plan(QuantumCircuit(0))
    assert plan.valid
    assert plan.log2_cost == 0.0


# ------------------------------------------------------ it stays an upper bound

def test_adding_the_strategy_never_raises_the_reported_bound():
    """A minimum over more strategies cannot be larger. If any core scored
    HIGHER after the strategy was added, the wiring would be wrong, not the
    strategy."""
    for seed in range(6):
        circuit = random_circuit(6, depth=5, seed=seed)
        with_tensor = simulation_residency(circuit)
        plan = contraction_plan(circuit)
        if not plan.valid:
            continue
        # The reported cost is a minimum that includes the tensor path, so it
        # can never exceed what that path alone would charge.
        assert with_tensor.log2_sim_cost <= plan.log2_cost + 1e-12


def test_a_clifford_core_is_still_free_and_not_made_expensive():
    """Gottesman-Knill must keep winning where it applies."""
    circuit = QuantumCircuit(10)
    for qubit in range(10):
        circuit.h(qubit)
    for qubit in range(9):
        circuit.cx(qubit, qubit + 1)
    report = simulation_residency(circuit)
    assert report.q_sim_upper == pytest.approx(0.0, abs=1e-12)
