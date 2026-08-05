"""Does `q_sim_upper` see the core, or the wire names?

`aionq.movingframe` poses this for sheaf measurements. The frame bundle here is
over circuits: the frame is the qubit labelling, the group is S_n acting by
relabelling, and nothing physical moves under it -- the same gates act on the
same wires, only the names change.

The answer, measured: `q_sim_upper` is ORBIT-RESOLVING. It is a property of the
pair (circuit, labelling) and has been reported as a property of the circuit,
which is the S4-G100 error -- the one that retired a headline claim as
basis-dependent -- reappearing inside the metric built to replace the one S4
killed.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from aionq.contraction import contraction_plan
from aionq.frame_orbit import (COLLAPSED, RESOLVING, compose, identity_frame,
                               invert, orbit_frames, orbit_report, relabel)
from aionq.matchgate import matchgate_plan
from aionq.residency import simulation_residency


def _free_fermion(n: int, layers: int = 3) -> QuantumCircuit:
    circuit = QuantumCircuit(n)
    for layer in range(layers):
        for qubit in range(n):
            circuit.t(qubit)
        for qubit in range(layer % 2, n - 1, 2):
            circuit.append(XXPlusYYGate(0.3 + 0.05 * qubit), [qubit, qubit + 1])
    return circuit


# ------------------------------------------------------------- the group action

def test_the_group_action_is_a_group_action(graph=None):
    """Checked before any orbit statistic is believed.

    If composition or inversion were wrong, every number computed above them
    would be meaningless, and the orbit report would be measuring its own bug.
    """
    n = 5
    first = (1, 0, 3, 4, 2)
    second = (4, 3, 2, 1, 0)
    assert compose(first, identity_frame(n)) == first
    assert compose(identity_frame(n), first) == first
    assert compose(first, invert(first)) == identity_frame(n)
    assert compose(invert(first), first) == identity_frame(n)
    assert invert(invert(second)) == second


def test_relabelling_is_physically_trivial():
    """Same gates, same wires, different names -- and it round-trips exactly."""
    circuit = _free_fermion(6)
    frame = (2, 0, 1, 5, 3, 4)
    there = relabel(circuit, frame)
    back = relabel(there, invert(frame))
    assert len(there.data) == len(circuit.data)
    assert [i.operation.name for i in back.data] == \
           [i.operation.name for i in circuit.data]
    for original, restored in zip(circuit.data, back.data):
        assert [circuit.find_bit(q).index for q in original.qubits] == \
               [back.find_bit(q).index for q in restored.qubits]


# --------------------------------------------------------------- the sampling

def test_the_orbit_sample_always_reaches_the_identity():
    """The defect that made the first version of this measurement useless.

    Twenty-four uniformly random permutations of ten qubits reported orbit
    spread ZERO for a family whose true spread is 0.9, because none of the 24
    was the identity -- and the identity is the frame in which the free-fermion
    path applies. An orbit sample that cannot reach the frame where the
    quantity differs measures nothing.
    """
    frames = orbit_frames(8, samples=6, seed=1)
    assert frames[0] == identity_frame(8)
    # And an adjacent transposition, the cheapest way to break 1D adjacency.
    assert (1, 0, 2, 3, 4, 5, 6, 7) in frames
    assert len(set(frames)) == len(frames)


# ------------------------------------------------------------ the verdicts

@pytest.fixture(scope="module")
def reports():
    circuit = _free_fermion(6, layers=2)
    frames = orbit_frames(6, samples=4, seed=3)
    return {
        name: orbit_report(name, measure, circuit, frames)
        for name, measure in (
            ("q_sim_upper", lambda c: simulation_residency(c).q_sim_upper),
            ("contraction_width", lambda c: contraction_plan(c).width),
            ("matchgate_valid", lambda c: float(matchgate_plan(c).valid)),
        )
    }


def test_no_measurement_carries_hidden_state(reports):
    """A non-zero closure defect is a bug, not a finding.

    Acting by a frame and then by its inverse must return the value exactly,
    because the composite acts trivially on the circuit. Anything else means
    something is being remembered between calls.
    """
    for report in reports.values():
        assert report.closure_defect == 0.0, report.name
        assert not report.hidden_state
        assert report.equivariance_defect == 0.0, report.name


def test_the_matchgate_path_is_orbit_resolving_with_maximal_spread(reports):
    """Adjacency is a property of the labelling, so this is expected.

    It is not a defect in the strategy: matchgates on non-adjacent qubits are
    universal, so the detector is right to refuse them. The defect is the TYPE
    under which its output was reported.
    """
    report = reports["matchgate_valid"]
    assert report.verdict == RESOLVING
    assert report.spread == 1.0        # a boolean flipping across the orbit
    assert report.mistyped


def test_q_sim_upper_inherits_it_and_is_orbit_resolving(reports):
    """The finding. A minimum over strategies inherits the worst typing.

    Measured on a 10-qubit free-fermion core: 0.0000 in the identity frame,
    0.9000 after swapping the names of two wires. Renaming wires is not an
    operation on the core.
    """
    report = reports["q_sim_upper"]
    assert report.verdict == RESOLVING
    assert report.spread > 0.1
    assert report.mistyped


def test_the_other_two_strategies_are_orbit_collapsed(reports):
    """So the resolving verdict is not an artefact of the instrument.

    Contraction width and stabilizer T-count are constant on the orbit. If
    everything came out resolving, the measurement would be suspect rather
    than the metric.
    """
    assert reports["contraction_width"].verdict == COLLAPSED
    assert reports["contraction_width"].spread == 0.0

    circuit = _free_fermion(6, layers=2)
    frames = orbit_frames(6, samples=4, seed=3)
    t_count = orbit_report("t_count",
                           lambda c: simulation_residency(c).t_count,
                           circuit, frames)
    assert t_count.verdict == COLLAPSED


def test_the_quantity_is_collapsed_on_the_adjacency_preserving_subgroup():
    """The structure, not an accident.

    Reversal preserves the path graph's adjacency, so the free-fermion path
    survives it and the value does not move. `q_sim_upper` is constant on the
    stabiliser of the interaction structure and jumps outside it -- which is
    why the honest type is (circuit, labelling) rather than "frame-dependent
    noise".
    """
    circuit = _free_fermion(8, layers=2)
    identity = simulation_residency(circuit).q_sim_upper
    reversal = tuple(range(7, -1, -1))
    assert simulation_residency(relabel(circuit, reversal)).q_sim_upper == \
        pytest.approx(identity)

    swapped = (1, 0, 2, 3, 4, 5, 6, 7)
    assert simulation_residency(relabel(circuit, swapped)).q_sim_upper != \
        pytest.approx(identity)


def test_any_single_frame_is_still_a_sound_upper_bound():
    """What survives, and why this is a typing error rather than unsoundness.

    A classical simulator is free to relabel before simulating, so the value in
    ANY frame is a cost some simulator really can pay: every frame gives a valid
    upper bound. What is not valid is calling one of them a property of the
    circuit, or comparing two circuits whose numbers were taken in arbitrary and
    different frames.
    """
    circuit = _free_fermion(6, layers=2)
    for frame in orbit_frames(6, samples=4, seed=5):
        value = simulation_residency(relabel(circuit, frame)).q_sim_upper
        assert 0.0 <= value <= 1.0
