"""The first graded member of the strategy portfolio, and what it is not.

`matchgate_plan` answers a question with a bit.  `matchgate_defect` answers the
same question with four residuals.  The bit carries a soundness theorem and
feeds `q_sim_upper`; the residuals carry neither and feed nothing, and these
tests assert that separation as hard as they assert the arithmetic -- because a
distance with no cost theorem behind it entering an upper bound would stop the
bound from being one.

What the residuals buy is measured here rather than asserted in prose:

* the refusal cliff is a function.  `RZZ(t)` is certified on exactly two points
  of its whole family and the determinant residual is `2|sin t|`, exactly.
* over all 240 affine frames of AGL(1,16), the bit takes 2 values and the
  residual takes 36, at the same stabiliser -- and every bit of that movement
  sits in ONE residual, because relabelling qubits changes which wires a gate
  sits on and never changes the gate.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import (CXGate, HGate, RXXGate, RZZGate, SwapGate,
                                    TGate, iSwapGate)

from aionq.frame_orbit import relabel
from aionq.gf_frames import agl42_generators, subgroup
from aionq.matchgate import matchgate_plan
from aionq.matchgate_defect import (matchgate_defect, matrix_determinant_defect,
                                    matrix_diagonal_defect, matrix_parity_defect)


def _free_fermion(n: int, layers: int, seed: int = 0) -> QuantumCircuit:
    """A nearest-neighbour matchgate core saturated with T gates.

    T saturation is deliberate: it is what makes `stabilizer_rank` price this
    family arbitrarily badly, and it costs the free-fermion simulator nothing.
    """
    rng = np.random.default_rng(seed)
    circuit = QuantumCircuit(n)
    for _ in range(layers):
        for qubit in range(n - 1):
            circuit.append(RXXGate(float(rng.uniform(0, np.pi))), [qubit, qubit + 1])
        for qubit in range(n):
            circuit.append(TGate(), [qubit])
    return circuit


# --------------------------------------------------------------------------
# The residuals agree with the bit, and only where the bit is metric
# --------------------------------------------------------------------------

def test_the_certified_class_is_exactly_the_zero_set():
    """Zero defect and a valid plan must be the same condition, both ways.

    One direction is the soundness that matters: if any residual is nonzero the
    plan must refuse, or the graded quantity would be calling something free
    that the certified path does not.  The other keeps the residuals honest --
    a defect that fired on a genuinely free circuit would make the landscape
    below an artefact of the instrument.
    """
    certified = [_free_fermion(6, 3, seed) for seed in range(4)]
    for circuit in certified:
        assert matchgate_plan(circuit).valid
        assert matchgate_defect(circuit).worst == pytest.approx(0.0, abs=1e-12)

    broken = []
    swapped = _free_fermion(6, 2)
    swapped.append(SwapGate(), [2, 3])
    broken.append(swapped)
    hadamard = _free_fermion(6, 2)
    hadamard.append(HGate(), [1])
    broken.append(hadamard)
    distant = QuantumCircuit(6)
    distant.append(iSwapGate(), [0, 4])
    broken.append(distant)
    entangling = QuantumCircuit(4)
    entangling.append(CXGate(), [0, 1])
    broken.append(entangling)

    for circuit in broken:
        assert not matchgate_plan(circuit).valid
        assert matchgate_defect(circuit).worst > 1e-6


def test_a_categorical_refusal_gets_no_number():
    """Distance from a domain one is not in is not a distance.

    A measurement is not "far from free fermions"; it is outside the class of
    objects the question is about.  Inventing a residual for it would be the
    module's own warning committed at the top level, so the result is marked
    inapplicable and the aggregates are infinite rather than large.
    """
    measured = _free_fermion(4, 1)
    measured.measure_all()
    defect = matchgate_defect(measured)

    assert not defect.applicable
    assert defect.worst == math.inf
    assert defect.by_residual == {}
    assert not matchgate_plan(measured).valid


# --------------------------------------------------------------------------
# The cliff has a shape
# --------------------------------------------------------------------------

@pytest.mark.parametrize("k", range(17))
def test_the_rzz_family_is_certified_at_two_points_and_graded_everywhere(k):
    """`det A = exp(-it)`, `det B = exp(+it)`, so the residual is `2|sin t|`.

    Exact, not fitted.  The certified set is the two-point set `t in {0, pi}`
    out of a continuum; the residual is a smooth function on the same family,
    maximal at `t = pi/2` where the two determinants are antipodal.  This is the
    whole claim of the module in one gate: the boolean was never describing a
    wall, it was thresholding a function that already existed.
    """
    angle = k * math.pi / 16
    matrix = np.array(RZZGate(angle).to_matrix())

    assert matrix_determinant_defect(matrix) == pytest.approx(2 * abs(math.sin(angle)),
                                                              abs=1e-12)
    assert matrix_parity_defect(matrix) == pytest.approx(0.0, abs=1e-12)

    circuit = QuantumCircuit(2)
    circuit.append(RZZGate(angle), [0, 1])
    certified = matchgate_plan(circuit).valid
    assert certified == (k in (0, 16))
    assert certified == (matchgate_defect(circuit).worst < 1e-9)


def test_swap_and_cz_sit_at_the_far_end_of_the_same_residual():
    """The gate that lifts matchgates to universality is not merely refused.

    SWAP has `det A = +1, det B = -1`, so its determinant residual is 2 -- the
    maximum the residual attains, the same value as `RZZ(pi/2)`. The residual
    does not just separate SWAP from the class; it places it as far from the
    class as this constraint can put anything.
    """
    from qiskit.circuit.library import CZGate

    for gate in (SwapGate(), CZGate()):
        matrix = np.array(gate.to_matrix())
        assert matrix_parity_defect(matrix) == pytest.approx(0.0, abs=1e-12)
        assert matrix_determinant_defect(matrix) == pytest.approx(2.0, abs=1e-12)

    assert matrix_parity_defect(np.array(CXGate().to_matrix())) > 1.0


def test_the_parity_residual_is_an_exact_distance_and_the_others_are_not_claimed_to_be():
    """Only one of the four is a distance, and the module says which.

    The parity-preserving matrices are a linear subspace, so zeroing the eight
    off-block entries IS the orthogonal projection and the residual IS the
    Frobenius distance to it.  Verified against an explicit projection rather
    than against the formula that computes it.
    """
    rng = np.random.default_rng(11)
    for _ in range(50):
        matrix = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
        projected = matrix.copy()
        for row, column in ((0, 1), (0, 2), (3, 1), (3, 2),
                            (1, 0), (2, 0), (1, 3), (2, 3)):
            projected[row, column] = 0.0

        assert matrix_parity_defect(matrix) == pytest.approx(
            float(np.linalg.norm(matrix - projected, "fro")), rel=1e-12)
        assert matrix_parity_defect(projected) == pytest.approx(0.0, abs=1e-12)

    # H = (1/sqrt2)[[1,1],[1,-1]]: both off-diagonal entries are 1/sqrt2, so the
    # distance to the diagonal matrices is sqrt(1/2 + 1/2) = 1 exactly.
    diagonal = np.diag([1.0 + 0j, np.exp(1j * 0.3)])
    assert matrix_diagonal_defect(diagonal) == pytest.approx(0.0, abs=1e-12)
    assert matrix_diagonal_defect(np.array(HGate().to_matrix())) == pytest.approx(
        1.0, abs=1e-12)


# --------------------------------------------------------------------------
# The frame orbit: where a step becomes a landscape, and why
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def agl_orbit():
    """Both instruments on all 240 affine frames of AGL(1,16). Exhaustive."""
    circuit = _free_fermion(16, 2)
    rows = []
    for frame in subgroup("AGL"):
        moved = relabel(circuit, frame)
        defect = matchgate_defect(moved)
        rows.append((matchgate_plan(moved).valid, defect.total, defect.by_residual))
    return rows


def test_the_bit_takes_two_values_over_the_orbit_and_the_residual_takes_thirty_six(agl_orbit):
    """The measured difference between a step and something with a gradient.

    240 frames walked in full, not sampled.  The certificate is true on exactly
    2 of them -- the identity and the reversal, `Aut` of the path graph the gates
    were laid on, index 120.  The residual has the SAME stabiliser and 36 level
    sets, so it agrees with the bit about which frames are certifiable and
    additionally ranks the 238 that are not.
    """
    certified = [row[0] for row in agl_orbit]
    totals = [row[1] for row in agl_orbit]

    assert len(agl_orbit) == 240
    assert sum(certified) == 2
    assert len({round(value, 9) for value in totals}) == 36
    assert min(totals) == pytest.approx(0.0, abs=1e-12)
    assert max(totals) == pytest.approx(212.0, abs=1e-9)

    stabiliser = sum(1 for value in totals if abs(value - totals[0]) <= 1e-12)
    assert stabiliser == 2
    assert stabiliser == sum(1 for value in certified if value == certified[0])


def test_the_zero_set_of_the_residual_is_the_certified_set_on_the_whole_orbit(agl_orbit):
    """Agreement checked on all 240 frames, not on a favourable one."""
    for certified, total, _ in agl_orbit:
        assert certified == (total <= 1e-12)


def test_every_frame_dependent_bit_of_the_certificate_lives_in_one_residual(agl_orbit):
    """Relabelling changes which wires a gate sits on; it never changes a gate.

    So parity, determinant and diagonal are constant on the entire orbit and
    `locality` carries all 36 levels by itself.  The free-fermion certificate's
    notorious frame sensitivity is, exactly and only, a routing quantity -- which
    is a statement about the certificate, obtained without touching the bound it
    feeds.
    """
    levels = {name: {round(row[2][name], 9) for row in agl_orbit}
              for name in ("parity", "determinant", "diagonal", "locality")}

    assert levels["parity"] == {0.0}
    assert levels["determinant"] == {0.0}
    assert levels["diagonal"] == {0.0}
    assert len(levels["locality"]) == 36


def test_the_matrix_residuals_are_invariant_under_the_full_affine_group():
    """The invariance is structural, so it is checked on generators, not samples.

    `relabel` reuses each `instruction.operation` unchanged, so no relabelling
    of any kind can move a residual computed from a gate matrix.  Sixteen
    generators decide all 322 560 frames of AGL(4,2), a group 1344 times larger
    than the one walked above -- the one place a group-sized claim is available
    without a group-sized computation.
    """
    circuit = _free_fermion(16, 2)
    base = matchgate_defect(circuit).by_residual

    for name, frame in agl42_generators().items():
        moved = matchgate_defect(relabel(circuit, frame)).by_residual
        for residual in ("parity", "determinant", "diagonal"):
            assert moved[residual] == pytest.approx(base[residual], abs=1e-12), (
                f"generator {name} moved {residual}, which no relabelling can do")


# --------------------------------------------------------------------------
# The separation from the published bound
# --------------------------------------------------------------------------

def test_the_bound_does_not_consult_this_module():
    """No cost theorem, so no entry into `q_sim_upper`. Asserted, not intended.

    `matchgate_plan` is sound because a theorem says the exactly-free-fermion
    case is poly-time simulable. Nothing here bounds simulation cost by a small
    nonzero defect, and a bound that consulted a quantity with no theorem behind
    it would stop being a bound. The separation is the module's whole safety
    argument, so it is checked mechanically rather than left to discipline.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src" / "aionq"
    importers = sorted(
        path.name for path in root.rglob("*.py")
        if re.search(r"^\s*(from|import)\s+\S*\bmatchgate_defect\b",
                     path.read_text(encoding="utf-8"), flags=re.MULTILINE))

    assert importers == [], (
        f"the ungrounded distance has acquired consumers in the library: "
        f"{importers}")

    residency = (root / "residency.py").read_text(encoding="utf-8")
    assert "matchgate_defect" not in residency
    assert "matchgate_plan" in residency
