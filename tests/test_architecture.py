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
from aionq.atlas import (CLASSICAL, SEPARABLE, STABILIZER, Interval,
                         QuantumNecessityAtlas, embed_hierarchy,
                         hierarchy_distortion, poincare_distance, resource_over)
from aionq.residency import (simulation_residency, max_bipartite_entanglement,
                             stabilizer_renyi_entropy)
from aionq.selfknowledge import (copies_for_self_tomography, self_knowledge_tradeoff,
                                syndrome_extraction_disturbance)


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
    r = simulation_residency(qc)
    assert r.q_naive == pytest.approx(1.0)
    assert r.q_sim_upper == pytest.approx(0.0)


def test_clifford_core_scores_zero_at_any_depth():
    """Gottesman-Knill: depth does not buy quantum residency."""
    for seed in (1, 7, 42):
        qc = random_clifford(8, seed=seed).to_circuit()
        assert simulation_residency(qc).q_sim_upper == pytest.approx(0.0)


def test_entanglement_is_not_quantum_residency():
    """GHZ maximises entanglement and has exactly zero magic and zero Q_cert."""
    qc = QuantumCircuit(8)
    qc.h(0)
    for i in range(7):
        qc.cx(i, i + 1)
    sv = Statevector(qc)
    assert max_bipartite_entanglement(sv) == pytest.approx(1.0)
    assert stabilizer_renyi_entropy(sv) == pytest.approx(0.0, abs=1e-9)
    assert simulation_residency(qc).q_sim_upper == pytest.approx(0.0)


def test_t_state_magic_is_exact():
    """Single T-state magic must equal log2(4/3)."""
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.t(0)
    assert stabilizer_renyi_entropy(Statevector(qc)) == pytest.approx(math.log2(4 / 3))


def test_residency_scales_with_t_count():
    """q_sim_upper = alpha * t / n until it saturates.

    T gates are separated by Hadamards.  Without that separation two T gates on
    the same qubit merge into S, which is Clifford and free -- the compiler
    portfolio spots this and the score correctly *drops*.  That behaviour is the
    metric working, so the test must not accidentally rely on it.
    """
    n = 8
    prev = -1.0
    for layers in (0, 1, 3, 7):
        qc = QuantumCircuit(n)
        qc.h(range(n))
        for _ in range(layers):
            qc.t(range(n))
            qc.h(range(n))
        cur = simulation_residency(qc).q_sim_upper
        assert cur >= prev
        prev = cur
    assert prev == pytest.approx(1.0, abs=0.01)


def test_merged_t_gates_are_correctly_recognised_as_clifford():
    """T followed by T on the same qubit is S: Clifford, hence free."""
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.t(0)
    qc.t(0)
    assert simulation_residency(qc).q_sim_upper == pytest.approx(0.0, abs=1e-9)


def test_residency_is_bounded():
    qc = QuantumCircuit(4)
    qc.h(range(4))
    for k in range(500):
        qc.t(k % 4)
    r = simulation_residency(qc)
    assert 0.0 <= r.q_sim_upper <= 1.0


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


def test_duplicated_holonomies_add_no_span_dimension():
    rho, holos, _ = _random_setup()
    base = analyse_identity(rho, holos).holonomy_span_dimension
    padded = analyse_identity(rho, holos + [h.copy() for h in holos])
    assert padded.holonomy_span_dimension == base


def test_effective_rank_is_continuous_and_bounded_by_rank():
    rho, holos, _ = _random_setup()
    rep = analyse_identity(rho, holos)
    assert 0.0 < rep.effective_rank <= rep.rank + 1e-9
    assert rep.condition_number >= 1.0


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


# --------------------------------------------------------------------------
# Claim 1b: the metric must resist equivalence attacks
# --------------------------------------------------------------------------

def test_identity_circuit_scores_zero():
    """H T Tdg H is exactly the identity and must not score as quantum."""
    from qiskit.quantum_info import Operator
    qc = QuantumCircuit(1)
    qc.h(0); qc.t(0); qc.tdg(0); qc.h(0)
    assert np.allclose(Operator(qc).data, np.eye(2), atol=1e-9)
    assert simulation_residency(qc).q_sim_upper == pytest.approx(0.0, abs=1e-9)


def test_cancelling_pairs_do_not_inflate_score():
    plain = QuantumCircuit(3)
    plain.h(range(3)); plain.ccx(0, 1, 2)
    padded = QuantumCircuit(3)
    padded.h(range(3)); padded.ccx(0, 1, 2)
    for _ in range(8):
        padded.t(0); padded.tdg(0)
    assert (simulation_residency(padded).q_sim_upper
            <= simulation_residency(plain).q_sim_upper + 1e-9)


def test_rccx_is_not_magic_free():
    """RCCX contains four T/Tdg operations; scoring it 0 was a bug."""
    from aionq.residency import _KNOWN_T_COUNT
    assert _KNOWN_T_COUNT["rccx"] == 4


def test_report_is_an_interval_with_honest_lower_bound():
    qc = QuantumCircuit(4)
    qc.h(range(4))
    for k in range(10):
        qc.t(k % 4)
    r = simulation_residency(qc)
    lo, hi = r.interval
    assert lo == 0.0                      # no lower-bound technology applied
    assert hi >= lo
    assert "none" in r.lower_justification


# --------------------------------------------------------------------------
# Claim 7b: structured self-measurement is non-disturbing
# --------------------------------------------------------------------------

def test_syndrome_extraction_disturbs_nothing():
    for err in (None, 0, 1, 2):
        rep = syndrome_extraction_disturbance(error_qubit=err)
        assert rep.logical_fidelity == pytest.approx(1.0, abs=1e-9)


def test_syndrome_carries_information():
    assert syndrome_extraction_disturbance(error_qubit=1).information_bits > 0
    seen = {syndrome_extraction_disturbance(error_qubit=e).syndrome
            for e in (None, 0, 1, 2)}
    assert len(seen) == 4        # syndromes distinguish all four cases


# --------------------------------------------------------------------------
# Claim 9/10: the atlas is not a scalar and its base is not Euclidean
# --------------------------------------------------------------------------

def test_resource_depends_on_the_free_theory():
    """|+> is a resource over classical-reversible and free over stabilizer."""
    plus = np.array([1, 1], dtype=complex) / math.sqrt(2)
    assert resource_over(plus, CLASSICAL) == pytest.approx(1.0)
    assert resource_over(plus, STABILIZER) == pytest.approx(0.0, abs=1e-9)


def test_ghz_is_free_over_stabilizer_but_not_over_separable():
    ghz = np.zeros(8, dtype=complex)
    ghz[0] = ghz[7] = 1 / math.sqrt(2)
    assert resource_over(ghz, STABILIZER) == pytest.approx(0.0, abs=1e-9)
    assert resource_over(ghz, SEPARABLE) == pytest.approx(1.0)


def test_hardness_alone_does_not_promote():
    padded = QuantumNecessityAtlas(
        organ="magic identity", base=STABILIZER, q_resource=1.2,
        q_sim=Interval(0.0, 0.68), q_causal=0.0)
    assert not padded.promote().promoted


def test_clifford_memory_is_not_zero_quantum():
    memory = QuantumNecessityAtlas(
        organ="Clifford FT memory", base=STABILIZER, q_phys=1.0, q_logical=1.0,
        q_sim=Interval(0.0, 0.0), q_causal=0.4)
    assert memory.q_sim.upper == 0.0
    assert memory.promote().promoted


def test_atlas_is_a_partial_order_not_a_ranking():
    memory = QuantumNecessityAtlas("m", STABILIZER, q_phys=1.0, q_logical=1.0,
                                   q_sim=Interval(0.0, 0.0), q_causal=0.4)
    padded = QuantumNecessityAtlas("p", STABILIZER, q_resource=1.2,
                                   q_sim=Interval(0.0, 0.68), q_causal=0.0)
    assert not memory.dominates(padded)
    assert not padded.dominates(memory)


def test_interval_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        Interval(0.9, 0.1)


def test_hyperbolic_beats_euclidean_only_as_depth_grows():
    shallow = hierarchy_distortion(1)
    deep = hierarchy_distortion(6)
    assert shallow["euclidean_distortion"] / shallow["hyperbolic_distortion"] < 1.1
    assert deep["euclidean_distortion"] / deep["hyperbolic_distortion"] > 2.0


def test_poincare_distance_rejects_points_outside_the_ball():
    with pytest.raises(ValueError):
        poincare_distance(np.array([1.5, 0.0]), np.array([0.0, 0.0]))


# --------------------------------------------------------------------------
# Claim 11: fibers are not comparable without transport
# --------------------------------------------------------------------------

def test_cross_fiber_comparison_is_refused():
    """1.2 bits of magic is not 0.9 bits of entanglement."""
    from aionq.atlas import IncomparableFibersError
    magic = QuantumNecessityAtlas("magic", STABILIZER, q_resource=1.2)
    ent = QuantumNecessityAtlas("entangled", SEPARABLE, q_resource=0.9)
    with pytest.raises(IncomparableFibersError):
        magic.dominates(ent)


def test_transport_declares_what_it_loses():
    magic = QuantumNecessityAtlas("magic", STABILIZER, q_resource=1.2, q_causal=0.5)
    moved = magic.transport_to(SEPARABLE)
    assert "q_resource" in moved.lost
    assert "q_causal" in moved.lost
    assert math.isnan(moved.section.q_resource)
    assert moved.remainder and moved.evidence


def test_identity_transport_preserves_everything():
    magic = QuantumNecessityAtlas("magic", STABILIZER, q_resource=1.2)
    moved = magic.transport_to(STABILIZER)
    assert moved.lost == ()
    assert moved.section.q_resource == pytest.approx(1.2)


def test_free_theory_orientation_is_consistent():
    """all-free -> nothing is a resource; minimal-free -> almost everything is."""
    from aionq.atlas import ALL_FREE, MINIMAL_FREE
    ghz = np.zeros(8, dtype=complex)
    ghz[0] = ghz[7] = 1 / math.sqrt(2)
    assert resource_over(ghz, ALL_FREE) == pytest.approx(0.0)
    assert resource_over(ghz, MINIMAL_FREE) > 0.0
    assert "all states" in ALL_FREE.free_states


# --------------------------------------------------------------------------
# Claim 12: the real hierarchy is not tree-like
# --------------------------------------------------------------------------

def test_real_free_theory_structure_is_not_tree_like():
    """Measured on the live DAG, not a synthetic binary tree."""
    from aionq.atlas import compare_embeddings_on_real_hierarchy
    r = compare_embeddings_on_real_hierarchy()
    assert not r["tree_like"]
    assert r["gromov_delta"] > 0.0
    # delta/diameter = 0.5 is the maximum possible for any metric space
    assert r["delta_over_diameter"] == pytest.approx(0.5, abs=1e-9)


def test_gromov_delta_is_zero_on_a_tree():
    from aionq.atlas import gromov_delta
    # path graph 0-1-2-3 is a tree
    d = np.array([[0., 1, 2, 3], [1, 0, 1, 2], [2, 1, 0, 1], [3, 2, 1, 0]])
    assert gromov_delta(d) == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------
# Claim 13: promotion is a cone, not a scalar
# --------------------------------------------------------------------------

def _cone():
    from aionq.advantage import AdvantageCone, Direction
    return AdvantageCone(
        name="K", constraints={"generalization": Direction.IMPROVE,
                               "robustness": Direction.IMPROVE,
                               "neg_latency": Direction.NO_WORSE},
        margins={"generalization": 0.02, "robustness": 0.02}, tolerance=0.05)


def _effect(**kw):
    from aionq.advantage import OUTCOME_DIMENSIONS, EffectPosterior
    dims = {d: i for i, d in enumerate(OUTCOME_DIMENSIONS)}
    v = [0.0] * len(OUTCOME_DIMENSIONS)
    for k, x in kw.items():
        v[dims[k]] = x
    return EffectPosterior(np.array(v), np.eye(len(OUTCOME_DIMENSIONS)) * 4e-4)


def test_genuine_gain_promotes():
    from aionq.advantage import promote
    assert promote(_effect(generalization=.09, robustness=.07), _cone()).promoted


def test_gain_bought_with_latency_does_not_promote():
    from aionq.advantage import promote
    d = promote(_effect(generalization=.09, robustness=.07, neg_latency=-.15), _cone())
    assert not d.promoted


def test_gain_below_margin_does_not_promote():
    from aionq.advantage import promote
    assert not promote(_effect(generalization=.012, robustness=.011), _cone()).promoted


def test_parity_and_audit_are_not_tradeable_against_effect_size():
    from aionq.advantage import promote
    strong = _effect(generalization=.09, robustness=.07)
    no_parity = promote(strong, _cone(), compute_parity=False)
    no_audit = promote(strong, _cone(), audit=0.2)
    assert not no_parity.promoted and not no_audit.promoted
    # the effect itself was fine in both cases; the blocker is separate
    assert no_parity.probability > 0.95
    assert any("parity" in b for b in no_parity.blockers)
    assert any("audit" in b for b in no_audit.blockers)


# --------------------------------------------------------------------------
# Claim 14: coordinates are typed; incommensurable comparisons are illegal
# --------------------------------------------------------------------------

def test_different_kinds_do_not_compare():
    from aionq.stack import Bits, IncommensurableError, Strength
    with pytest.raises(IncommensurableError):
        Bits(0.9) >= Strength(0.9)


def test_monotones_over_different_bases_do_not_compare():
    from aionq.stack import IncommensurableError, Monotone
    with pytest.raises(IncommensurableError):
        Monotone(1.2, base="stabilizer") >= Monotone(0.9, base="separable")


def test_monotones_over_the_same_base_do_compare():
    from aionq.stack import Monotone
    assert Monotone(1.2, base="stabilizer") >= Monotone(0.9, base="stabilizer")


def test_a_monotone_must_declare_its_free_theory():
    from aionq.stack import Monotone
    with pytest.raises(ValueError):
        Monotone(0.5)


def test_fraction_is_range_checked():
    from aionq.stack import Fraction
    with pytest.raises(ValueError):
        Fraction(1.7)


# --------------------------------------------------------------------------
# Claim 15: transport holonomy around a loop of free theories
# --------------------------------------------------------------------------

def _t_state():
    return np.array([1, complex(math.cos(math.pi / 4), math.sin(math.pi / 4))],
                    dtype=complex) / math.sqrt(2)


def test_section_only_loop_is_lossy():
    """Keep the summary, lose the ability to recompute it."""
    from aionq.stack import transport_loop
    sec = QuantumNecessityAtlas("T-organ", STABILIZER, q_resource=0.415)
    rep = transport_loop(sec)
    assert not rep.trivial
    assert "q_resource" in rep.lost_coordinates


def test_state_anchored_loop_closes_exactly():
    """Keep the state, and every base change is recoverable."""
    from aionq.stack import state_anchored_loop
    rep = state_anchored_loop(_t_state())
    assert rep.trivial
    assert rep.defect == pytest.approx(0.0, abs=1e-12)
    assert rep.start_value == pytest.approx(rep.end_value)


def test_holonomy_gap_is_the_price_of_forgetting_the_state():
    from aionq.stack import holonomy_defect
    sec = QuantumNecessityAtlas("T-organ", STABILIZER, q_resource=0.415)
    d = holonomy_defect(_t_state(), sec)
    assert d["state_anchored_trivial"]
    assert not d["section_only_trivial"]
    assert d["state_anchored_defect"] < d["section_only_defect"]


def test_loop_profile_is_genuinely_base_dependent():
    """The monotone really does move around the loop; it is not constant."""
    from aionq.atlas import ALL_FREE, CLASSICAL
    t = _t_state()
    assert resource_over(t, STABILIZER) == pytest.approx(math.log2(4 / 3), abs=1e-4)
    assert resource_over(t, ALL_FREE) == pytest.approx(0.0)
    assert resource_over(t, CLASSICAL) == pytest.approx(1.0)
