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
        if not report.informative:
            continue
        winner = report.bounding_strategy
        assert winner in report.strategy_costs
        assert report.strategy_costs[winner] == pytest.approx(
            report.log2_sim_cost, abs=1e-9)
