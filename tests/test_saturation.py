"""`q_sim_upper = 1.00` is a shrug wearing the units of a measurement.

QSigma-R1a ended with a diagnosis and no instrument: a portfolio missing a
strategy is not uniformly optimistic, it is arbitrarily wrong on whatever that
strategy was for, and gives no signal about where. This is the signal, and it
was there the whole time.

`q_sim_upper == 1.0` holds exactly when `log2_sim_cost >= n`, which holds
exactly when nothing in the portfolio simulated the core below brute force.
These are UPPER bounds, so a bound at the ceiling is the absence of a bound.
1.00 therefore never means "measured maximally quantum". It always means "no
applicable strategy" -- and it was being averaged in with real measurements.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from aionq.residency import simulation_residency


def _single_qubit_chains(n: int) -> QuantumCircuit:
    """QSigma-R1a defect 1: a product state the metric called maximally quantum."""
    circuit = QuantumCircuit(n)
    circuit.h(range(n))
    for _ in range(7):
        circuit.t(range(n))
        circuit.h(range(n))
    return circuit


def _free_fermion(n: int) -> QuantumCircuit:
    """QSigma-R1a defect 2: poly-time, T-saturated, scored 1.00."""
    circuit = QuantumCircuit(n)
    for layer in range(10):
        for qubit in range(n):
            circuit.t(qubit)
        for qubit in range(layer % 2, n - 1, 2):
            circuit.append(XXPlusYYGate(0.3 + 0.1 * qubit), [qubit, qubit + 1])
    return circuit


def _all_to_all_magic(n: int) -> QuantumCircuit:
    circuit = QuantumCircuit(n)
    for _ in range(3):
        circuit.h(range(n))
        circuit.t(range(n))
        for first in range(n):
            for second in range(first + 1, n):
                circuit.cx(first, second)
    return circuit


def test_saturation_is_exactly_the_condition_q_sim_upper_equals_one():
    """The flag is not a heuristic; it is a restatement of the clip.

    If these ever came apart, one of them would be lying about the other.
    """
    circuits = [
        _single_qubit_chains(8), _free_fermion(8), _all_to_all_magic(6),
        QuantumCircuit(4),
        # The zero-qubit circuit, which this test asserted over and never
        # reached. It used to report bounding_strategy "dense" and therefore
        # informative False, while q_sim_upper was 0.0 -- breaking the very
        # equivalence asserted below. A witness list that cannot reach the
        # degenerate case is the defect this whole file is about.
        QuantumCircuit(0),
        QuantumCircuit(1),
    ]
    swapped = _free_fermion(8)
    swapped.swap(0, 1)
    circuits.append(swapped)

    for circuit in circuits:
        report = simulation_residency(circuit)
        if not report.q_sim_upper_known:
            continue
        assert (report.q_sim_upper >= 1.0 - 1e-12) == (not report.informative), (
            circuit.num_qubits, report.q_sim_upper, report.bounding_strategy)


def test_a_universal_circuit_saturates_and_that_is_correct():
    """Saturation marks absence of information, NOT presence of easiness.

    Matchgates plus SWAP is universal, so the portfolio genuinely has nothing to
    say about this core. It reports 1.00 -- the same 1.00 it reported for the
    poly-time version before the free-fermion strategy existed. The number
    cannot distinguish them. That is the finding.
    """
    circuit = _free_fermion(12)
    circuit.swap(0, 1)
    report = simulation_residency(circuit)
    assert report.q_sim_upper == pytest.approx(1.0)
    assert not report.informative
    assert report.bounding_strategy == "dense"
    assert any("SATURATED" in note for note in report.notes)


def test_the_two_known_defects_are_no_longer_saturated():
    """Both sat at 1.00 before their strategy existed. Neither does now."""
    for build in (_single_qubit_chains, _free_fermion):
        report = simulation_residency(build(12))
        assert report.informative
        assert report.q_sim_upper < 0.9
        assert report.bounding_strategy in {"contraction", "free_fermion"}


def test_the_flag_would_have_fired_on_both_defects_before_discovery():
    """Retrodiction, run rather than asserted.

    With the two structural strategies disabled -- the state of the portfolio
    when both defects were live -- each defective family saturates, and the
    genuinely hard control does not. A flag that fired on everything would be
    useless; this one separates them.
    """
    from aionq import contraction, matchgate

    real_contraction = contraction.contraction_plan
    real_matchgate = matchgate.matchgate_plan
    contraction.contraction_plan = lambda c: contraction.ContractionPlan(
        valid=False, reason="disabled: portfolio state before QSigma-R1a")
    matchgate.matchgate_plan = lambda c: matchgate.MatchgatePlan(
        valid=False, reason="disabled: portfolio state before QSigma-R1a")
    try:
        assert not simulation_residency(_single_qubit_chains(12)).informative
        assert not simulation_residency(_free_fermion(12)).informative
        # The genuinely hard control was never saturated, so the flag is not
        # simply firing on everything expensive.
        assert simulation_residency(_all_to_all_magic(12)).informative
    finally:
        contraction.contraction_plan = real_contraction
        matchgate.matchgate_plan = real_matchgate


def test_no_random_acaf_core_is_saturated():
    """0 of 150, measured. The flag has no false positives on that corpus.

    This is what makes it usable: it is not a warning attached to every
    expensive core, it is a warning attached to the cores where the portfolio
    has nothing to say -- and on the random fuzz there are none.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))
    from acaf_sweep import Ambigator

    amb = Ambigator(n_values=[4, 6, 8], t_densities=[0.0, 0.05, 0.25],
                    depths=[2, 4], seed=17)
    saturated = total = 0
    for _, _, _, circuit in amb.sweep(samples_per_config=1):
        total += 1
        if not simulation_residency(circuit).informative:
            saturated += 1
    assert total > 0
    assert saturated == 0, f"{saturated}/{total} random cores saturated"


def test_the_bounding_strategy_names_a_real_strategy_that_achieved_the_minimum():
    for build in (_single_qubit_chains, _free_fermion, _all_to_all_magic):
        report = simulation_residency(build(8))
        # "dense" and "trivial" are not strategies -- they are the fallback and
        # the degenerate case -- so neither appears in strategy_costs. Skipping
        # only on `not informative` would have missed "trivial", which is
        # informative and still not a strategy name.
        if report.bounding_strategy in {"dense", "trivial"}:
            continue
        winner = report.bounding_strategy
        assert winner in report.strategy_costs
        assert report.strategy_costs[winner] == pytest.approx(
            report.log2_sim_cost, abs=1e-9)


# ------------------------------------------- the flag catches a live gaming vector

def test_the_same_operator_gets_opposite_verdicts_in_two_notations():
    """A representation attack the K3 suite's three attacks do not reach.

    Both circuits below implement EXACTLY the same operator -- the identity on
    six qubits. Written in Clifford+T it scores 0.0000, because the compiler
    portfolio cancels it. Written in qiskit's full gate set it scores 1.0000,
    because no optimisation level in the portfolio sees the cancellation and no
    structural strategy penetrates the gate set either.

    So `q_sim_upper` is not a function of the operator. It is a function of the
    notation, and the metric's stated purpose is to resist exactly that.
    """
    import numpy as np
    from qiskit import transpile
    from qiskit.circuit.random import random_circuit
    from qiskit.quantum_info import Operator

    dense = random_circuit(6, depth=6, seed=5)
    rich = QuantumCircuit(6)
    rich.compose(dense, inplace=True)
    rich.compose(dense.inverse(), inplace=True)

    clifford_t_source = transpile(
        random_circuit(6, depth=6, seed=5),
        basis_gates=["h", "t", "tdg", "s", "sdg", "cx", "x", "z", "rz"],
        optimization_level=0, seed_transpiler=3)
    clifford_t = QuantumCircuit(6)
    clifford_t.compose(clifford_t_source, inplace=True)
    clifford_t.compose(clifford_t_source.inverse(), inplace=True)

    identity = np.eye(64)
    assert np.allclose(Operator(rich).data, identity, atol=1e-9)
    assert np.allclose(Operator(clifford_t).data, identity, atol=1e-9)

    rich_report = simulation_residency(rich)
    clifford_report = simulation_residency(clifford_t)

    assert clifford_report.q_sim_upper == pytest.approx(0.0, abs=1e-12)
    assert rich_report.q_sim_upper == pytest.approx(1.0)


def test_the_saturation_flag_catches_that_gaming_vector():
    """The instrument was built as a diagnostic and it fires on a live attack.

    This is the one piece of predictive value the saturation flag has shown:
    it was derived from two defects already known, and it independently marks a
    third case -- an identity circuit scored 1.00 -- that the K3 equivalence
    attacks pass over. A wrong answer the metric flags is not the same failure
    as a wrong answer it states confidently.
    """
    from qiskit.circuit.random import random_circuit

    dense = random_circuit(6, depth=6, seed=5)
    circuit = QuantumCircuit(6)
    circuit.compose(dense, inplace=True)
    circuit.compose(dense.inverse(), inplace=True)

    report = simulation_residency(circuit)
    assert report.q_sim_upper == pytest.approx(1.0)
    assert not report.informative
    assert report.bounding_strategy == "dense"


def test_all_four_strategies_fail_on_it_together():
    """No corroboration was available, which is 0.5's point made concrete.

    Every strategy either refuses the core or fails to beat brute force on it,
    so there was never a second opinion that could have caught the first.
    """
    from qiskit.circuit.random import random_circuit

    dense = random_circuit(6, depth=6, seed=5)
    circuit = QuantumCircuit(6)
    circuit.compose(dense, inplace=True)
    circuit.compose(dense.inverse(), inplace=True)

    report = simulation_residency(circuit)
    for name, cost in report.strategy_costs.items():
        assert cost >= float(circuit.num_qubits), (name, cost)




def test_the_degenerate_zero_qubit_circuit_is_not_reported_as_saturated():
    """It has no dense ceiling to fail to beat, and its cost is exactly known.

    Reporting it as saturated claimed absence of information about the one
    circuit whose cost is certain, and contradicted the definition of the flag,
    since `q_sim_upper` is 0.0 there.
    """
    report = simulation_residency(QuantumCircuit(0))
    assert report.q_sim_upper == pytest.approx(0.0)
    assert report.bounding_strategy == "trivial"
    assert report.informative


def test_the_reported_winner_is_one_of_the_recorded_achievers():
    """A winner label is chosen from ties by declaration order.

    That makes a histogram of winners potentially misleading in a corpus where
    ties are common, so the full achiever set is recorded alongside it. Measured
    on ACAF: 0 ties in 150 cores, so the "stabilizer rank 150" result is 150
    strict wins rather than an artefact of the tie rule.
    """
    for build in (_single_qubit_chains, _free_fermion, _all_to_all_magic):
        report = simulation_residency(build(8))
        if report.bounding_strategy in {"dense", "trivial"}:
            assert report.bounding_achievers == ()
        else:
            assert report.bounding_strategy in report.bounding_achievers
            for name in report.bounding_achievers:
                assert report.strategy_costs[name] == pytest.approx(
                    report.log2_sim_cost, abs=1e-9)
