"""A proposed theorem, its control, and the type that control creates.

The device: on a finite mesh with a discretised connection Laplacian, the
eigensections form a Parseval frame, and a gauge transformation conjugates the
frame operator, so the frame bounds are gauge-invariant. True, and proved
without ever touching the connection.

These tests run it with the control it lacked -- a shuffled connection, which is
not gauge-equivalent to the original -- and the frame bounds do not move under
that either. Three other observables do. So the classification `movingframe`
uses, ORBIT-COLLAPSED versus ORBIT-RESOLVING, needs a third case, and the last
test in this file applies it back to this repository's own earlier results
rather than only to someone else's proposal.
"""

from __future__ import annotations

import numpy as np
import pytest

from aionq.connection_frame import (connection_laplacian, discrimination_report,
                                    frame_bounds, gauge_transform,
                                    holonomy_traces, localisation,
                                    random_connection, ring_with_chords,
                                    shuffle_connection)

FIBER = 2


@pytest.fixture(scope="module")
def report():
    return discrimination_report()


@pytest.fixture(scope="module")
def setting():
    mesh = ring_with_chords()
    base = random_connection(mesh, FIBER, seed=11)
    gauged, frames = gauge_transform(mesh, base, FIBER)
    shuffled = shuffle_connection(mesh, base)
    return mesh, base, gauged, frames, shuffled


def test_the_device_is_true(setting):
    """The Parseval and gauge-covariance claims hold exactly, as stated."""
    mesh, base, gauged, _, _ = setting
    assert frame_bounds(connection_laplacian(mesh, base, FIBER)) == pytest.approx(
        (1.0, 1.0), abs=1e-12)
    assert frame_bounds(connection_laplacian(mesh, gauged, FIBER)) == pytest.approx(
        (1.0, 1.0), abs=1e-12)


def test_the_device_is_also_empty(setting, report):
    """It holds identically for a connection that is NOT gauge-equivalent.

    The shuffle permutes which edge carries which transport. It changes the
    holonomies, so it is a different connection, not a different frame. The
    frame bounds do not notice. Neither would they notice the zero connection or
    a random Hermitian matrix, because the proof uses only the spectral theorem.
    """
    mesh, base, _, _, shuffled = setting
    assert frame_bounds(connection_laplacian(mesh, shuffled, FIBER)) == pytest.approx(
        (1.0, 1.0), abs=1e-12)
    assert report["frame_bounds"]["gauge"] < 1e-12
    assert report["frame_bounds"]["shuffle"] < 1e-12
    assert report["frame_bounds"]["type"] == "BLIND"


def test_the_shuffle_really_is_a_different_connection(setting):
    """Otherwise the control proves nothing and this file is circular.

    A gauge change conjugates every cycle product at its base point, so cycle
    traces are class functions and cannot move. If the shuffle moved them no
    more than the gauge did, it would be indistinguishable from a frame change
    and could not serve as a control.
    """
    mesh, base, gauged, _, shuffled = setting
    before = holonomy_traces(mesh, base, FIBER)

    assert np.abs(before - holonomy_traces(mesh, gauged, FIBER)).max() < 1e-12
    assert np.abs(before - holonomy_traces(mesh, shuffled, FIBER)).max() > 1e-2


@pytest.mark.parametrize("observable", ["spectrum", "holonomy", "localisation"])
def test_three_observables_are_invariant_and_discriminating(observable, report):
    """Gauge-invariant to machine precision, and they move under the shuffle.

    These are what the device's conclusion becomes when it is made about
    connections: the same gauge-covariance statement, on a quantity that can
    fail. The holonomies are the sharpest -- they are the complete
    gauge-invariant content of a connection on a graph, and the frame bounds see
    none of it.
    """
    row = report[observable]
    assert row["gauge"] < 1e-12
    assert row["shuffle"] > 1e-3
    assert row["type"] == "INVARIANT_AND_DISCRIMINATING"


def test_localisation_is_gauge_invariant_for_a_structural_reason(setting):
    """A gauge acts as `G_i` on the fiber over vertex `i`, preserving `||f_i||`.

    Worth its own test because it is the one discriminating observable whose
    invariance is not a class-function argument, and because it is the closest
    thing here to the localisation a packet calculus would need. Checked against
    the eigenvector weights directly rather than through the report.
    """
    mesh, base, gauged, _, _ = setting
    spectrum = np.linalg.eigvalsh(connection_laplacian(mesh, base, FIBER))
    assert np.min(np.diff(spectrum)) > 1e-6, (
        "a degenerate spectrum makes an eigenvector-dependent quantity "
        "ill-defined, and this test would be measuring the eigensolver")

    before = localisation(connection_laplacian(mesh, base, FIBER), mesh.vertices, FIBER)
    after = localisation(connection_laplacian(mesh, gauged, FIBER), mesh.vertices, FIBER)
    assert np.abs(before - after).max() < 1e-12
    assert before.min() > 1.0 / mesh.vertices - 1e-9


# --------------------------------------------------------------------------
# Turning the control back on this repository's own results
# --------------------------------------------------------------------------

def test_the_repositorys_own_collapsed_quantities_are_not_blind():
    """R1C reported three of four strategies constant over 240 frames as a result.

    Constant over the frame orbit is only informative if something else moves
    them. That control was never run: R1B, R1C and R1D all reported collapse and
    treated it as the good case. It is applied here, retroactively, to the three
    quantities that were called orbit-collapsed.

    All three move under a change of circuit, so none of them is blind and the
    earlier findings stand. That is the outcome, not the point -- the point is
    that it was asserted for three rounds without being measured.
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import CXGate, RXXGate, TGate

    from aionq.residency import simulation_residency

    def ladder(n, layers, entangler, seed=0):
        rng = np.random.default_rng(seed)
        circuit = QuantumCircuit(n)
        for _ in range(layers):
            for qubit in range(n - 1):
                if entangler == "rxx":
                    circuit.append(RXXGate(float(rng.uniform(0, np.pi))),
                                   [qubit, qubit + 1])
                else:
                    circuit.append(CXGate(), [qubit, qubit + 1])
            for qubit in range(n):
                circuit.append(TGate(), [qubit])
        return circuit

    def costs(circuit):
        report = simulation_residency(circuit, portfolio=False)
        record = report if isinstance(report, dict) else report.__dict__
        return record["strategy_costs"]

    reference = costs(ladder(8, 2, "rxx"))
    variants = [costs(ladder(8, 4, "rxx")), costs(ladder(8, 2, "cx")),
                costs(ladder(12, 2, "rxx"))]

    for name in ("stabilizer_rank", "basis_permutation", "contraction",
                 "free_fermion"):
        moved = any(variant[name] != reference[name] for variant in variants)
        assert moved, (
            f"{name} was reported orbit-collapsed and does not move under a "
            f"change of circuit either -- it would be BLIND, and the R1C "
            f"finding would not mean what it was recorded to mean")

    # `basis_permutation` is infinite on everything above, and a control that can
    # only observe one value is the defect this whole file is about.  The CX
    # ladder does move it to 0.0 -- so the loop passes -- but that is luck rather
    # than design, and a circuit built to be basis-confined makes it deliberate.
    permutation_only = QuantumCircuit(8)
    for qubit in range(7):
        permutation_only.append(CXGate(), [qubit, qubit + 1])
    assert costs(permutation_only)["basis_permutation"] == 0.0
    assert reference["basis_permutation"] == float("inf")
