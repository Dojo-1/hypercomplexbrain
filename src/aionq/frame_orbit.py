"""Moving-frame audit for circuit measurements: object, or frame?

`aionq.movingframe` asks this of sheaf measurements and states the distinction
better than it can be restated:

    ORBIT-COLLAPSED   the measurement is constant on the frame orbit.  It sees
                      the orbit quotient -- the object -- and nothing else.
    ORBIT-RESOLVING   the measurement varies across the orbit.  It is reporting
                      frame coordinates.

    "A measurement that is orbit-resolving is not therefore wrong.  It is
    MISTYPED: it has been reported as a property of the sheaf when it is a
    property of the pair (sheaf, frame)."

That module's frame bundle is over sheaves.  This one is over CIRCUITS, where
the frame is the qubit labelling and the group is S_n acting by relabelling.
Nothing physical changes under it: the same gates act on the same wires, and
only the names of the wires move.

WHY THIS EXISTS.  Everything QSigma-R1a added to `q_sim_upper` was reported as
a property of a core.  Measured here, it is not:

    identity frame        q_sim_upper = 0.0000   bounding = free_fermion
    swap labels 0 and 1   q_sim_upper = 0.9000   bounding = contraction
    reversal              q_sim_upper = 0.0000   bounding = free_fermion

An orbit spread of 0.9 on a scale of [0, 1], from renaming two wires.  This is
the S4-G100 finding again -- the round that retired a headline claim as
basis-dependent -- reproduced in the metric built to replace the one S4 killed.

The reversal row is the structure rather than an accident.  `q_sim_upper` is not
randomly frame-dependent: it is CONSTANT on the subgroup preserving the
interaction graph's adjacency, and jumps outside it.  So the honest type is not
"a number about a circuit" but "a number about a circuit together with a
labelling", and the quantity is orbit-collapsed on the stabiliser of the
adjacency structure.

A NOTE ON SAMPLING, because the first attempt at this measurement failed.
Twenty-four uniformly random permutations of ten qubits reported orbit spread
ZERO for exactly the family that has spread 0.9 -- because none of the 24 was
the identity, and the identity is the frame in which the free-fermion path
applies.  An orbit sample that cannot reach the frame where the quantity
differs measures nothing, which is the same defect this repository has now
recorded in a residency witness, a K3 attack, a projection freeze, a saturation
equivalence and two of its own guards.  `orbit_frames` therefore always
includes the identity, and always includes a single adjacent transposition,
because those are the two frames most likely to disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "COLLAPSED",
    "RESOLVING",
    "identity_frame",
    "orbit_frames",
    "relabel",
    "compose",
    "invert",
    "OrbitReport",
    "orbit_report",
    "loop_closure",
    "equivariance_defect",
]

COLLAPSED = "orbit-collapsed"
RESOLVING = "orbit-resolving"


def identity_frame(n: int) -> tuple:
    return tuple(range(n))


def compose(second: tuple, first: tuple) -> tuple:
    """Apply ``first`` then ``second``."""
    return tuple(second[index] for index in first)


def invert(frame: tuple) -> tuple:
    out = [0] * len(frame)
    for position, target in enumerate(frame):
        out[target] = position
    return tuple(out)


def relabel(circuit, frame: tuple):
    """Act on a circuit by a qubit relabelling.

    Physically trivial: the same operations on the same wires under different
    names.  Any measurement that moves under this is reporting the names.
    """
    from qiskit import QuantumCircuit

    out = QuantumCircuit(circuit.num_qubits)
    for instruction in circuit.data:
        indices = [frame[circuit.find_bit(qubit).index]
                   for qubit in instruction.qubits]
        out.append(instruction.operation, indices)
    return out


def orbit_frames(n: int, samples: int = 6, seed: int = 0) -> tuple:
    """A path through the frame bundle that always reaches the telling points.

    The identity and one adjacent transposition are included unconditionally.
    A uniform sample over S_n almost never contains either, and the first
    version of this measurement reported spread 0 on a family with spread 0.9
    for exactly that reason.
    """
    frames = [identity_frame(n)]
    if n >= 2:
        swapped = list(range(n))
        swapped[0], swapped[1] = swapped[1], swapped[0]
        frames.append(tuple(swapped))
        frames.append(tuple(range(n - 1, -1, -1)))     # reversal
    rng = np.random.default_rng(seed)
    while len(frames) < samples:
        candidate = tuple(int(x) for x in rng.permutation(n))
        if candidate not in frames:
            frames.append(candidate)
    return tuple(frames)


@dataclass
class OrbitReport:
    """Whether a circuit measurement sees the circuit or its labelling."""

    name: str
    values: tuple = ()
    frames: tuple = ()
    spread: float = 0.0
    verdict: str = COLLAPSED
    closure_defect: float = 0.0
    equivariance_defect: float = 0.0

    @property
    def mistyped(self) -> bool:
        """Reported as a property of the object while varying on the orbit."""
        return self.verdict == RESOLVING

    @property
    def hidden_state(self) -> bool:
        """A non-zero closure defect is a bug, not a finding.

        Composing frames whose product is the identity must return the
        measurement to its starting value exactly, because the composite acts
        trivially.  If it does not, something is being remembered between
        calls.
        """
        return self.closure_defect > 0.0


def loop_closure(measure, circuit, frames) -> float:
    """Act by a frame and then by its inverse; the value must return exactly."""
    base = float(measure(circuit))
    worst = 0.0
    for frame in frames:
        there = relabel(circuit, frame)
        back = relabel(there, invert(frame))
        worst = max(worst, abs(float(measure(back)) - base))
    return worst


def equivariance_defect(measure, circuit, first: tuple, second: tuple) -> float:
    """Acting by ``second`` after ``first`` must equal acting by the composite.

    Checked before any orbit statistic is believed: if the group action is
    implemented wrongly, every number above it is meaningless.
    """
    stepwise = relabel(relabel(circuit, first), second)
    composed = relabel(circuit, compose(second, first))
    return abs(float(measure(stepwise)) - float(measure(composed)))


def orbit_report(name: str, measure, circuit, frames=None,
                 tolerance: float = 1e-12) -> OrbitReport:
    """Classify one measurement as orbit-collapsed or orbit-resolving."""
    frames = frames or orbit_frames(circuit.num_qubits)
    values = tuple(float(measure(relabel(circuit, frame))) for frame in frames)
    spread = max(values) - min(values)

    first, second = frames[0], frames[min(1, len(frames) - 1)]
    return OrbitReport(
        name=name,
        values=values,
        frames=frames,
        spread=spread,
        verdict=RESOLVING if spread > tolerance else COLLAPSED,
        closure_defect=loop_closure(measure, circuit, frames[:3]),
        equivariance_defect=equivariance_defect(measure, circuit, first, second),
    )
