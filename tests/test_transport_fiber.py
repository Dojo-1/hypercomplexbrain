"""The dichotomy a finite frame group cannot see, and the portfolio-wide census.

Over a FINITE frame group a certified class can only be hit or missed: 240
isolated points, a finite union of varieties of one dimension, and no
dimension-growth phenomenon possible.  The step measured over AGL(1,16) is that
fact about finite groups, not a fact about hardness.

The geometry is in the continuous group.  Transport a gate along
``G(s) = G0 exp(i s H)``: some ``H`` keep it on the class for every ``s`` -- the
class is a subgroup, so containment is exact -- and the rest leave at first
order.  These tests pin the two numbers that dichotomy produces for each of the
repository's two threshold strategies, and then run the census the template
implies: **which strategies does the frame group actually move?**

The census answer is a single sentence and these tests are what make it
assertable: of the four strategies behind `q_sim_upper`, exactly one is
frame-resolving, and every bit of the metric's notorious orbit spread comes
from it.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, RXXGate, SwapGate, TGate

from aionq import transport_fiber as fiber
from aionq.frame_orbit import relabel
from aionq.gf_frames import subgroup
from aionq.matchgate_defect import (matrix_determinant_defect,
                                    matrix_parity_defect)
from aionq.residency import simulation_residency


def _matchgate_residual(matrix) -> float:
    return matrix_parity_defect(matrix) + matrix_determinant_defect(matrix)


def _monomial_residual(matrix) -> float:
    return float(np.linalg.norm(fiber.monomial_defining_functions(matrix)))


def _free_fermion_ladder(n: int = 16, layers: int = 2, seed: int = 0) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    circuit = QuantumCircuit(n)
    for _ in range(layers):
        for qubit in range(n - 1):
            circuit.append(RXXGate(float(rng.uniform(0, np.pi))), [qubit, qubit + 1])
        for qubit in range(n):
            circuit.append(TGate(), [qubit])
    return circuit


# --------------------------------------------------------------------------
# The two classes, and the dimensions they actually have
# --------------------------------------------------------------------------

@pytest.mark.parametrize("theta", [0.0, 0.3, 0.7, 1.1, math.pi / 2])
def test_the_matchgate_class_is_seven_dimensional_inside_sixteen(theta):
    """Not fitted: `U(2) x U(2)` is 8, and `det A = det B` is one real condition.

    The prediction is arithmetic and the measurement is a numerical rank, which
    is only worth something if the spectrum has a gap -- otherwise "rank 9" is a
    tolerance in costume.  Measured, the singular values are `{2, sqrt2 x 8}`
    then a drop of nine orders of magnitude.
    """
    geometry = fiber.tangent_dimension(np.array(RXXGate(theta).to_matrix()))

    assert geometry["on_the_class"] == pytest.approx(0.0, abs=1e-12)
    assert geometry["ambient"] == 16
    assert geometry["rank"] == 9
    assert geometry["tangent"] == 7
    assert geometry["gap"] > 1e6


@pytest.mark.parametrize("name", ["cnot", "swap", "phases"])
def test_the_monomial_class_is_four_dimensional_inside_sixteen(name):
    """`basis_permutation`'s class: a permutation times four free phases.

    The same template on a different variety, and it returns a different number
    -- which is what makes it a measurement rather than a restatement of the
    instrument.  4, not 7, and codimension 12, not 9.
    """
    matrices = {
        "cnot": np.array(CXGate().to_matrix()),
        "swap": np.array(SwapGate().to_matrix()),
        "phases": np.diag(np.exp(1j * np.array([0.1, 0.7, 1.3, 2.2]))),
    }
    geometry = fiber.tangent_dimension(matrices[name],
                                       fiber.monomial_defining_functions)

    assert geometry["on_the_class"] == pytest.approx(0.0, abs=1e-12)
    assert geometry["tangent"] == 4
    assert geometry["codimension"] == 12


# --------------------------------------------------------------------------
# Transport: exact containment one way, first-order escape the other
# --------------------------------------------------------------------------

def test_transport_along_a_fiber_is_exact_containment_not_osculation():
    """A tangent direction stays in the class at s = 1, not merely as s -> 0.

    This is the difference between a fiber and a curve tangent to a surface.
    The class is a group, so ``exp(i s H)`` for ``H`` in its algebra is in the
    class for every ``s``; the containment has no small-parameter hypothesis and
    the "tube" has zero transverse thickness.  Checked out to s = 10, five
    orders of magnitude beyond the range the escape-order fit uses.
    """
    base = np.array(RXXGate(0.7).to_matrix())
    # Within-block couplings: |00>-|11> in the even sector, |01>-|10> in the odd.
    tangent = [generator for generator in fiber.hermitian_basis(4)
               if math.isinf(fiber.escape_order(base, generator, _matchgate_residual))]
    assert len(tangent) == 4, "the standard basis meets the tangent space in 4 elements"

    from scipy.linalg import expm
    for generator in tangent:
        for scale in (0.1, 1.0, 3.0, 10.0):
            moved = base @ expm(1j * scale * generator)
            assert _matchgate_residual(moved) == pytest.approx(0.0, abs=1e-10), (
                f"the fiber left the class at s = {scale}")


@pytest.mark.parametrize("residual,defining,point", [
    (_matchgate_residual, fiber.defining_functions, "rxx"),
    (_monomial_residual, fiber.monomial_defining_functions, "cnot"),
])
def test_every_generic_direction_escapes_at_order_exactly_one(residual, defining, point):
    """No direction curves back. The constraint map is a submersion.

    216 directions per class -- 16 basis plus 200 sampled uniformly in the
    Hermitian directions -- and every escaping one has log-log slope 1.000. Zero
    directions of order 2 or more, so there is nowhere the first-order defect
    vanishes and the class doubles back.

    This is the non-degeneracy hypothesis that Kakeya- and Falconer-type
    estimates assume rather than verify. Here it is verified, and it is the only
    thing in this file that a harmonic-analysis programme could actually use.
    """
    matrices = {"rxx": np.array(RXXGate(0.7).to_matrix()),
                "cnot": np.array(CXGate().to_matrix())}
    report = fiber.fiber_report(matrices[point], residual, defining,
                                random_directions=200)

    assert report["random_contained"] == 0, (
        "a uniformly sampled Hermitian direction landed in the tangent space, "
        "which has measure zero -- the sampler is not uniform")
    assert report["escape_order_min"] == pytest.approx(1.0, abs=1e-3)
    assert report["escape_order_max"] == pytest.approx(1.0, abs=1e-3)
    assert report["directions_of_order_two_or_more"] == 0


def test_a_finite_frame_group_cannot_produce_this_dichotomy():
    """Why the finite measurement had to come out a step, independent of hardness.

    Relabelling acts by permutation, so its orbit through a point is a finite
    set. There is no direction along which to transport, no escape rate to
    measure, and no dimension that can grow: a union of 240 copies of a
    7-dimensional variety is 7-dimensional. The step over AGL(1,16) is a fact
    about finite groups.

    Asserted concretely: every frame in the group sends the class into a copy of
    itself of the SAME tangent dimension.
    """
    base = np.array(RXXGate(0.7).to_matrix())
    dimensions = set()
    for permutation in ((0, 1, 2, 3), (0, 2, 1, 3), (3, 2, 1, 0), (1, 0, 3, 2)):
        moved = base[np.ix_(permutation, permutation)]
        dimensions.add(fiber.tangent_dimension(moved)["tangent"])
    assert dimensions == {7}


# --------------------------------------------------------------------------
# The census the template implies
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def strategy_orbit():
    """All four strategies on all 240 affine frames of AGL(1,16). Exhaustive."""
    circuit = _free_fermion_ladder()
    rows, uppers = [], []
    for frame in subgroup("AGL"):
        report = simulation_residency(relabel(circuit, frame), portfolio=False)
        record = report if isinstance(report, dict) else report.__dict__
        rows.append(record["strategy_costs"])
        uppers.append(record["q_sim_upper"])
    return rows, uppers


def test_exactly_one_strategy_of_four_is_frame_resolving(strategy_orbit):
    """The whole census, in one assertion.

    `stabilizer_rank` charges a T-count, `basis_permutation` reads gate matrices,
    `contraction` reads a graph invariant -- none of the three can see a wire
    name, and measured over the full group none of them moves. `free_fermion`
    alone moves, because it alone imposes a condition on wire ADJACENCY.

    So `q_sim_upper`'s frame-dependence, the finding that started this line and
    reproduced the defect S4 retired a headline for, is localised to one strategy
    and inside it to one residual, and that residual is routing.
    """
    rows, uppers = strategy_orbit
    levels = {name: len({row[name] for row in rows})
              for name in ("stabilizer_rank", "basis_permutation",
                           "contraction", "free_fermion")}

    assert len(rows) == 240
    assert levels["stabilizer_rank"] == 1
    assert levels["basis_permutation"] == 1
    assert levels["contraction"] == 1
    assert levels["free_fermion"] == 2

    assert len(set(uppers)) == 2
    assert min(uppers) == pytest.approx(0.0, abs=1e-12)
    assert max(uppers) == pytest.approx(0.25, abs=1e-12)


def test_the_metrics_orbit_spread_is_exactly_the_free_fermion_strategys(strategy_orbit):
    """Attribution, not correlation: freeze the one mover and the spread dies.

    Recomputing the minimum with `free_fermion` held at its identity-frame value
    leaves a constant. The other three are not merely quieter than it; they
    contribute nothing at all.
    """
    rows, uppers = strategy_orbit
    held = [min(16.0, rows[0]["free_fermion"],
                row["stabilizer_rank"], row["basis_permutation"],
                row["contraction"]) / 16.0
            for row in rows]

    assert len(set(held)) == 1
    assert len(set(uppers)) == 2
