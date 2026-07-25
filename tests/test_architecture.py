"""Tests for the falsifiable claims of AION-Omega^Q.

Each test corresponds to a claim in docs/ARCHITECTURE.md.  A failure here is a
falsification of the architecture, not merely a broken build.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, random_clifford

sys.path.insert(0, "src")

from aionq.budget import CoherenceBudget, bennett_time_cost
from aionq.coherentize import coherentization_audit, stinespring_dilation
from aionq.fusion import associator_defect, hexagon_defect, pentagon_defect, verify_coherence
from aionq.identity import analyse_identity, holonomy_gram
from aionq.process import non_markovianity
from aionq.qrf import compare_frames
from aionq.residency import (certified_residency, max_bipartite_entanglement,
                             stabilizer_renyi_entropy)
from aionq.selfknowledge import copies_for_self_tomography, self_knowledge_tradeoff


# --------------------------------------------------------------------------
# Claim 1: quantum residency is global, not additive over edges
# --------------------------------------------------------------------------

def test_classical_reversible_core_scores_zero():
    """A permutation core is 100% 'unitary' and 0% quantum."""
    qc = QuantumCircuit(8)
    for i in range(7):
        qc.cx(i, i + 1)
    qc.ccx(0, 1, 2)
    qc.x(range(8))
    r = certified_residency(qc)
    assert r.q_naive == pytest.approx(1.0)
    assert r.q_cert == pytest.approx(0.0)


def test_clifford_core_scores_zero_at_any_depth():
    """Gottesman-Knill: depth does not buy quantum residency."""
    for seed in (1, 7, 42):
        qc = random_clifford(8, seed=seed).to_circuit()
        assert certified_residency(qc).q_cert == pytest.approx(0.0)


def test_entanglement_is_not_quantum_residency():
    """GHZ maximises entanglement and has exactly zero magic and zero Q_cert."""
    qc = QuantumCircuit(8)
    qc.h(0)
    for i in range(7):
        qc.cx(i, i + 1)
    sv = Statevector(qc)
    assert max_bipartite_entanglement(sv) == pytest.approx(1.0)
    assert stabilizer_renyi_entropy(sv) == pytest.approx(0.0, abs=1e-9)
    assert certified_residency(qc).q_cert == pytest.approx(0.0)


def test_t_state_magic_is_exact():
    """Single T-state magic must equal log2(4/3)."""
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.t(0)
    assert stabilizer_renyi_entropy(Statevector(qc)) == pytest.approx(math.log2(4 / 3))


def test_residency_scales_with_t_count():
    """Q_cert = alpha * t / n until it saturates."""
    n = 8
    prev = -1.0
    for t in (0, 5, 15, 35):
        qc = QuantumCircuit(n)
        qc.h(range(n))
        for k in range(t):
            qc.t(k % n)
        cur = certified_residency(qc).q_cert
        assert cur >= prev
        prev = cur
    assert prev == pytest.approx(1.0, abs=0.01)


def test_residency_is_bounded():
    qc = QuantumCircuit(4)
    qc.h(range(4))
    for k in range(500):
        qc.t(k % 4)
    r = certified_residency(qc)
    assert 0.0 <= r.q_cert <= 1.0


# --------------------------------------------------------------------------
# Claim 2: coherentization relocates classicality
# --------------------------------------------------------------------------

def _dynamic_core() -> QuantumCircuit:
    q = QuantumRegister(4, "q")
    c = ClassicalRegister(2, "c")
    qc = QuantumCircuit(q, c)
    qc.h(0)
    qc.t(1)
    qc.cx(0, 1)
    qc.t(2)
    qc.measure(0, c[0])
    with qc.if_test((c[0], 1)):
        qc.x(2)
        qc.t(3)
    qc.measure(1, c[1])
    with qc.if_test((c[1], 1)):
        qc.z(3)
    return qc


def test_coherentization_gain_is_far_below_advertised():
    audit = coherentization_audit(_dynamic_core())
    assert audit.naive_delta > 0.3          # draft metric claims a large gain
    assert audit.cert_delta < 0.05          # the real gain is small
    assert audit.cert_delta < 0.2 * audit.naive_delta


def test_coherentization_costs_ancillas_and_magic():
    audit = coherentization_audit(_dynamic_core())
    assert audit.ancillas_added > 0
    assert audit.after.t_count > audit.before.t_count


def test_stinespring_dilation_is_an_isometry():
    """Every CPTP cognitive operation admits a coherent realisation."""
    p = 0.3
    kraus = [np.sqrt(1 - p) * np.eye(2),
             np.sqrt(p) * np.array([[0, 1], [1, 0]], dtype=complex)]
    v = np.asarray(stinespring_dilation(kraus).data)
    assert v.shape == (4, 2)                      # system (x) environment
    assert np.allclose(v.conj().T @ v, np.eye(2), atol=1e-9)


# --------------------------------------------------------------------------
# Claim 3: exhalation is forced
# --------------------------------------------------------------------------

def test_irreversibility_shortens_the_breath():
    reversible = CoherenceBudget(200, 120, 3, 0.0).schedule()
    lossy = CoherenceBudget(200, 120, 3, 0.5).schedule()
    assert math.isinf(reversible.exhale_period)
    assert lossy.exhale_period < math.inf
    assert lossy.exhale_period >= 1


def test_horizon_shrinks_as_data_grows():
    wide = CoherenceBudget(100, 10).schedule()
    narrow = CoherenceBudget(100, 90).schedule()
    assert wide.horizon > narrow.horizon


def test_bennett_cost_superlinear_when_pebbles_scarce():
    cheap = bennett_time_cost(64, pebbles=64)
    dear = bennett_time_cost(64, pebbles=3)
    assert dear > cheap


# --------------------------------------------------------------------------
# Claim 4: process memory is measurable
# --------------------------------------------------------------------------

def test_decoupled_process_is_exactly_markovian():
    assert non_markovianity(0.0).markovian


def test_memory_increases_with_coupling():
    vals = [non_markovianity(c).non_markovianity for c in (0.0, 0.2, 0.5, 1.0)]
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))
    assert vals[-1] > 0.5


# --------------------------------------------------------------------------
# Claim 5: fusion coherence
# --------------------------------------------------------------------------

def test_pentagon_and_hexagon_hold():
    assert pentagon_defect() < 1e-10
    assert hexagon_defect() < 1e-10


def test_grammar_is_coherent_but_not_associative():
    rep = verify_coherence()
    assert rep.coherent
    assert rep.nontrivial
    assert associator_defect() > 1e-6


# --------------------------------------------------------------------------
# Claim 6: identity Gram
# --------------------------------------------------------------------------

def _random_setup(d=4, k=3, seed=3):
    rng = np.random.default_rng(seed)

    def rand_u():
        m = rng.normal(size=(d, d)) + 1j * rng.normal(size=(d, d))
        q, _ = np.linalg.qr(m)
        return q

    basis = rand_u()
    probs = rng.random(d)
    probs /= probs.sum()
    rho = basis @ np.diag(probs) @ basis.conj().T
    return rho, [rand_u() for _ in range(k)], rand_u()


def test_gram_is_hermitian_psd():
    rho, holos, _ = _random_setup()
    rep = analyse_identity(rho, holos)
    assert rep.hermitian_defect < 1e-9
    assert rep.psd


def test_gram_is_frame_invariant():
    rho, holos, frame = _random_setup()
    rep = analyse_identity(rho, holos, frame=frame)
    assert rep.frame_defect < 1e-9


def test_duplicated_holonomies_add_no_identity_capacity():
    rho, holos, _ = _random_setup()
    base = analyse_identity(rho, holos).identity_capacity
    padded = analyse_identity(rho, holos + [h.copy() for h in holos])
    assert padded.identity_capacity == base


# --------------------------------------------------------------------------
# Claim 7: self-knowledge is bounded by no-cloning
# --------------------------------------------------------------------------

def test_self_knowledge_costs_identity_fidelity():
    points = self_knowledge_tradeoff()
    assert points[0].info_gain_bits == pytest.approx(0.0, abs=1e-12)
    assert points[0].fidelity_retained == pytest.approx(1.0, abs=1e-9)
    # information strictly increases, fidelity strictly decreases
    for a, b in zip(points, points[1:]):
        assert b.info_gain_bits >= a.info_gain_bits - 1e-12
        assert b.fidelity_retained <= a.fidelity_retained + 1e-12
    assert points[-1].fidelity_retained < 1.0


def test_self_tomography_burden_is_superlinear():
    assert copies_for_self_tomography(64, 0.01) > copies_for_self_tomography(64, 0.1)
    assert copies_for_self_tomography(128, 0.01) > copies_for_self_tomography(64, 0.01)


# --------------------------------------------------------------------------
# Claim 8: entanglement is frame-relative
# --------------------------------------------------------------------------

def test_entanglement_is_frame_dependent():
    cmp_ = compare_frames()
    assert cmp_.entropy_in_a == pytest.approx(0.0, abs=1e-9)
    assert cmp_.entropy_in_b == pytest.approx(1.0, abs=1e-9)
    assert cmp_.frame_dependent
