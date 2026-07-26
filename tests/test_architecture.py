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
    """q_sim_upper = 0 does not mean "zero quantum": q_phys and q_logical are 1."""
    memory = QuantumNecessityAtlas(
        organ="Clifford FT memory", base=STABILIZER, q_phys=1.0, q_logical=1.0,
        q_sim=Interval(0.0, 0.0), q_causal=0.4)
    assert memory.q_sim.upper == 0.0
    assert float(memory.q_phys) == 1.0 and float(memory.q_logical) == 1.0


def test_asserted_q_causal_no_longer_promotes():
    """The scalar gate is retired: a stored float is an assertion, not a measurement."""
    memory = QuantumNecessityAtlas(
        organ="Clifford FT memory", base=STABILIZER, q_phys=1.0, q_logical=1.0,
        q_sim=Interval(0.0, 0.0), q_causal=0.4)
    verdict = memory.promote()
    assert not verdict.promoted
    assert "cone" in verdict.reason


def test_promotion_delegates_to_the_cone_when_supplied():
    from aionq.advantage import AdvantageCone, Direction, EffectPosterior, OUTCOME_DIMENSIONS
    cone = AdvantageCone(name="K", constraints={"generalization": Direction.IMPROVE},
                         margins={"generalization": 0.02})
    dims = {d: i for i, d in enumerate(OUTCOME_DIMENSIONS)}
    v = [0.0] * len(OUTCOME_DIMENSIONS)
    v[dims["generalization"]] = 0.09
    post = EffectPosterior(np.array(v), np.eye(len(OUTCOME_DIMENSIONS)) * 4e-4)
    organ = QuantumNecessityAtlas("organ", STABILIZER, q_audit=1.0)
    assert organ.promote(posterior=post, cone=cone).promoted


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
    assert math.isnan(float(moved.section.q_resource))
    assert moved.remainder and moved.evidence


def test_identity_transport_preserves_everything():
    magic = QuantumNecessityAtlas("magic", STABILIZER, q_resource=1.2)
    moved = magic.transport_to(STABILIZER)
    assert moved.lost == ()
    assert float(moved.section.q_resource) == pytest.approx(1.2)


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


# --------------------------------------------------------------------------
# Claim 16: epistemic governance is executable, not aspirational
# --------------------------------------------------------------------------

def test_every_claim_is_tagged_and_wellformed():
    """Construction enforces the lattice; a malformed claim cannot exist."""
    from aionq.governance import registry, EvidenceTag
    assert len(registry) > 20
    for tag, n in registry.audit()["counts"].items():
        assert tag in EvidenceTag.ALL
        assert n >= 0


def test_axiomatized_claims_must_state_their_surrogate():
    from aionq.governance import Claim, EvidenceTag, GovernanceError
    with pytest.raises(GovernanceError):
        Claim("METRIC-R9-BAD", EvidenceTag.AXIOMATIZED, "passes a check")


def test_hypotheses_must_carry_a_kill_condition():
    from aionq.governance import Claim, EvidenceTag, GovernanceError
    with pytest.raises(GovernanceError):
        Claim("BRIDGE-R9-BAD", EvidenceTag.HYPOTHESIS, "something improves")


def test_retired_claims_cannot_be_cited_in_results():
    from aionq.governance import registry, GovernanceError
    with pytest.raises(GovernanceError):
        registry.cite("RET-R3-HYPERBOLIC_BASE", section="results")
    assert registry.cite("RET-R3-HYPERBOLIC_BASE", section="correction_history")


def test_semantic_claims_cannot_be_cited_in_results():
    from aionq.governance import registry, GovernanceError
    with pytest.raises(GovernanceError):
        registry.cite("SEM-R0-BREATHING", section="results")
    assert registry.cite("SEM-R0-BREATHING", section="motivation")


def test_correction_supersedes_rather_than_deletes():
    from aionq.governance import Claim, EvidenceTag, Registry
    stats = dict(sample_size=10, interval=(0.1, 0.3), null="zero effect")
    r = Registry([Claim("MATH-R1-OLD", EvidenceTag.MEASURED, "old reading", **stats)])
    r.supersede("MATH-R1-OLD",
                Claim("MATH-R2-NEW", EvidenceTag.MEASURED, "new reading", **stats))
    assert r["MATH-R1-OLD"].superseded_by == "MATH-R2-NEW"
    assert r["MATH-R2-NEW"].supersedes == "MATH-R1-OLD"
    assert len(r) == 2                      # history preserved, not overwritten


def test_remainders_are_typed_and_do_not_transport():
    from aionq.governance import Remainder, RemainderKind, UntypedTransportError, GovernanceError
    r = Remainder(RemainderKind.EMPIRICAL, "unexplained residual", 0.03)
    assert r.transport_to(RemainderKind.EMPIRICAL) is r
    with pytest.raises(UntypedTransportError):
        r.transport_to(RemainderKind.COHOMOLOGY)
    with pytest.raises(GovernanceError):
        Remainder("vibes", "untyped leftover")


def test_headline_metric_is_axiomatized_not_measured():
    """q_sim_upper is verified by a surrogate weaker than the claim it supports."""
    from aionq.governance import registry, EvidenceTag
    c = registry["METRIC-R3-QSIM_UPPER"]
    assert c.tag == EvidenceTag.AXIOMATIZED
    assert "weaker than circuit equivalence" in c.surrogate


# --------------------------------------------------------------------------
# D15 / interval order / retired instrument
# --------------------------------------------------------------------------

def test_atlas_coordinates_are_typed_not_floats():
    from aionq.quantities import Bits, Fraction, Monotone, Strength
    a = QuantumNecessityAtlas("x", STABILIZER, q_phys=1.0, q_process=0.9,
                              q_resource=1.2, q_audit=0.8)
    assert isinstance(a.q_phys, Fraction)
    assert isinstance(a.q_process, Bits)
    assert isinstance(a.q_resource, Monotone)
    assert isinstance(a.q_audit, Strength)
    assert a.q_resource.base == STABILIZER.name


def test_atlas_coordinates_refuse_cross_unit_comparison():
    from aionq.quantities import IncommensurableError
    a = QuantumNecessityAtlas("x", STABILIZER, q_process=0.9, q_audit=0.9)
    with pytest.raises(IncommensurableError):
        a.q_process >= a.q_audit


def test_interval_order_is_explicit_and_not_collapsed_to_lower():
    """Two organs differing only in q_sim.upper must not compare equal."""
    from aionq.atlas import IntervalOrder
    narrow = QuantumNecessityAtlas("a", STABILIZER, q_sim=Interval(0.0, 0.05))
    wide = QuantumNecessityAtlas("b", STABILIZER, q_sim=Interval(0.0, 1.00))
    # optimistic: wide has the better known upper bound
    assert wide.dominates(narrow, interval_policy=IntervalOrder.OPTIMISTIC)
    # guaranteed: neither, since both lower bounds are 0
    assert not wide.dominates(narrow, interval_policy=IntervalOrder.GUARANTEED)
    assert not narrow.dominates(wide, interval_policy=IntervalOrder.GUARANTEED)


def test_unknown_interval_policy_raises():
    a = QuantumNecessityAtlas("a", STABILIZER)
    b = QuantumNecessityAtlas("b", STABILIZER)
    with pytest.raises(ValueError):
        a.dominates(b, interval_policy="wishful")


def test_retired_poincare_instrument_warns():
    a = QuantumNecessityAtlas("a", STABILIZER)
    b = QuantumNecessityAtlas("b", SEPARABLE)
    assert not hasattr(a, "base_distance")       # the live default is gone
    with pytest.warns(UserWarning, match="RETIRED"):
        a.experimental_poincare_instrument(b)


def test_syndrome_information_is_computed_not_hardcoded():
    """All four outcomes are distinguishable, so each carries the full 2 bits."""
    for err in (None, 0, 1, 2):
        assert syndrome_extraction_disturbance(error_qubit=err).information_bits \
            == pytest.approx(2.0)


# --------------------------------------------------------------------------
# Bordon respiration
# --------------------------------------------------------------------------

def test_drone_ceiling_is_the_refill_rate_not_the_capacity():
    """A reservoir of any size cannot fund an uninterrupted channel."""
    from aionq.bordon import BordonBreath, Fol, Pipe, PipeKind
    huge = BordonBreath(Fol(capacity=1e6, refill_rate=0.2),
                        (Pipe("identity", PipeKind.BORDON, 0.5),))
    rep = huge.analyse()
    assert rep.drone_ceiling == pytest.approx(0.2)
    assert not rep.drone_survives          # capacity 1e6 does not save it


def test_melody_is_silenced_to_protect_the_drone():
    from aionq.bordon import BordonBreath, Fol, Pipe, PipeKind
    rep = BordonBreath(Fol(10, 0.5),
                       (Pipe("identity", PipeKind.BORDON, 0.3),
                        Pipe("task", PipeKind.PUNTERO, 0.9))).analyse()
    assert rep.drone_survives and not rep.melody_survives
    assert any("silenced" in n for n in rep.notes)


def test_no_interruption_needed_when_refill_covers_draw():
    """The periodic model cannot express this case at all."""
    from aionq.bordon import BordonBreath, Fol, Pipe, PipeKind
    rep = BordonBreath(Fol(10, 1.0),
                       (Pipe("identity", PipeKind.BORDON, 0.3),
                        Pipe("task", PipeKind.PUNTERO, 0.5))).analyse()
    assert math.isinf(rep.sustain_ticks)
    assert rep.drone_survives and rep.melody_survives


# --------------------------------------------------------------------------
# Round V1: visibility / coupling field
# --------------------------------------------------------------------------

def _ghz(n):
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1, n):
        qc.cx(0, i)
    return qc


def test_product_state_is_fully_visible():
    """The defect that killed the first instrument: this must be exactly 0."""
    from aionq.visibility import visibility_profile
    qc = QuantumCircuit(6)
    qc.h(range(6))
    assert visibility_profile(qc).g1 == pytest.approx(0.0)


def test_ghz_hides_exactly_one_generator():
    from aionq.visibility import visibility_profile
    for n in range(3, 8):
        rep = visibility_profile(_ghz(n))
        for r in range(2, n):
            assert rep.coupling[r] == pytest.approx(1.0 / n)
        assert rep.r_star == n
        assert rep.coupling[n] == pytest.approx(0.0)


def test_visibility_depth_is_not_the_code_distance():
    """Steane [[7,1,3]] has r* = 4: r* is generating weight, not distance."""
    from aionq.visibility import visibility_profile
    steane = ["IIIXXXX", "IXXIIXX", "XIXIXIX",
              "IIIZZZZ", "IZZIIZZ", "ZIZIZIZ", "ZZZZZZZ"]
    assert visibility_profile(steane).r_star == 4


def test_visibility_rejects_non_stabilizer_input():
    from aionq.visibility import NotAStabilizerState, visibility_profile
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.t(0)
    with pytest.raises(NotAStabilizerState):
        visibility_profile(qc)


# --------------------------------------------------------------------------
# Cayley-Dickson ladder replication
# --------------------------------------------------------------------------

def test_associativity_holds_exactly_through_quaternions():
    from aionq.cayley_dickson import associator
    rng = np.random.default_rng(0)
    for dim in (1, 2, 4):
        for _ in range(20):
            x, y, z = (rng.normal(size=dim) for _ in range(3))
            assert np.linalg.norm(associator(x, y, z)) == pytest.approx(0.0, abs=1e-12)


def test_octonions_are_non_associative():
    from aionq.cayley_dickson import associator
    rng = np.random.default_rng(0)
    worst = max(np.linalg.norm(associator(*(rng.normal(size=8) for _ in range(3))))
                for _ in range(50))
    assert worst > 1e-6


def test_zero_divisors_appear_exactly_at_sedenions():
    from aionq.cayley_dickson import cd_multiply, find_zero_divisor
    assert find_zero_divisor(8) is None
    zd = find_zero_divisor(16)
    assert zd is not None
    a, b = zd
    assert np.linalg.norm(a) > 0 and np.linalg.norm(b) > 0
    assert np.linalg.norm(cd_multiply(a, b)) == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------
# Statistical discipline
# --------------------------------------------------------------------------

def test_measured_claims_must_report_sample_size_and_interval():
    """The Atlas M rule, now enforced rather than merely stated."""
    from aionq.governance import Claim, EvidenceTag, GovernanceError
    with pytest.raises(GovernanceError, match="sample_size"):
        Claim("EXP-R9-BARE", EvidenceTag.MEASURED, "a number with no uncertainty")


def test_every_registered_measured_claim_carries_statistics():
    from aionq.governance import registry, EvidenceTag
    for c in registry.by_tag(EvidenceTag.MEASURED):
        assert c.sample_size and c.sample_size > 0, c.id
        assert c.interval and len(c.interval) == 2, c.id
        assert c.null, c.id


def test_bootstrap_ci_brackets_a_known_mean():
    from aionq.statistics import bootstrap_ci
    rng = np.random.default_rng(0)
    data = rng.normal(5.0, 1.0, 500)
    lo, hi = bootstrap_ci(data, seed=1)
    assert lo < 5.0 < hi
    assert hi - lo < 0.5


def test_measurement_significance_is_interval_based():
    from aionq.statistics import summarize
    rng = np.random.default_rng(2)
    shifted = summarize("shifted", rng.normal(1.0, 0.1, 400))
    centred = summarize("centred", rng.normal(0.0, 1.0, 400))
    assert shifted.excludes(0.0)
    assert not centred.excludes(0.0)


def test_effect_size_detects_and_rejects():
    from aionq.statistics import compare_groups
    rng = np.random.default_rng(3)
    real = compare_groups("real", rng.normal(1, 1, 300), rng.normal(0, 1, 300), resamples=2000)
    null = compare_groups("null", rng.normal(0, 1, 300), rng.normal(0, 1, 300), resamples=2000)
    assert real.significant and abs(real.cohens_d) > 0.5
    assert not null.significant


# --------------------------------------------------------------------------
# Round V3: split forms over R and F_2, and computed code distance
# --------------------------------------------------------------------------

def test_real_22_signature_is_two_hyperbolic_planes():
    """SO(2,2) is the split orthogonal group: Q = uv + st exactly."""
    from aionq.splitform import real_split_planes
    r = real_split_planes()
    assert r["signature"] == (2, 2)
    assert r["is_two_hyperbolic_planes"]
    gram = r["gram_in_split_basis"]
    assert np.allclose(np.diag(gram), 0.0)        # both planes isotropic
    assert np.allclose(gram[:2, 2:], 0.0)         # and mutually orthogonal


def test_f2_phase_space_is_n_hyperbolic_planes():
    """One hyperbolic plane per qubit, spanned by X_i and Z_i."""
    from aionq.splitform import symplectic_basis
    for n in (2, 3, 4):
        vecs = []
        for i in range(n):
            x = np.zeros(2 * n, dtype=np.uint8); x[i] = 1; vecs.append(x)
            z = np.zeros(2 * n, dtype=np.uint8); z[n + i] = 1; vecs.append(z)
        planes, radical = symplectic_basis(vecs)
        assert len(planes) == n
        assert len(radical) == 0


def test_stabilizer_checks_are_totally_isotropic():
    """Commuting checks pair to zero: they are the radical, carrying no plane."""
    from aionq.splitform import symplectic_basis
    from aionq.visibility import generators_from_labels
    _, checks = generators_from_labels(["IIIXXXX", "IXXIIXX", "XIXIXIX",
                                        "IIIZZZZ", "IZZIIZZ", "ZIZIZIZ"])
    planes, radical = symplectic_basis(list(checks))
    assert len(planes) == 0
    assert len(radical) == 6


def test_computed_distance_matches_known_codes():
    from aionq.splitform import code_distance
    assert code_distance(["IIIXXXX", "IXXIIXX", "XIXIXIX",
                          "IIIZZZZ", "IZZIIZZ", "ZIZIZIZ"]) == 3   # Steane
    assert code_distance(["XZZXI", "IXZZX", "XIXZZ", "ZXIXZ"]) == 3  # [[5,1,3]]
    assert code_distance(["XXXX", "ZZZZ"]) == 2                      # [[4,2,2]]


def test_repetition_code_stabilizer_distance_is_one():
    """The V1 correction: [[n,1,n]] is the X-distance convention, not d."""
    from aionq.splitform import code_distance
    for n in (3, 5, 7):
        checks = ["".join("Z" if k in (i, i + 1) else "I" for k in range(n))
                  for i in range(n - 1)]
        assert code_distance(checks) == 1


def test_rstar_is_not_the_distance_on_any_family():
    """P2 falsified against computed d, including where V1 said it survived."""
    from aionq.splitform import code_distance
    from aionq.visibility import visibility_profile
    qc = QuantumCircuit(5)
    qc.h(0)
    for i in range(1, 5):
        qc.cx(0, i)
    checks = ["".join("Z" if k in (i, i + 1) else "I" for k in range(5))
              for i in range(4)]
    assert visibility_profile(qc).r_star == 5
    assert code_distance(checks) == 1             # not 5


# --------------------------------------------------------------------------
# Round S1: the Sigma-infinity Transcendence Sentinel, and its retirement
# --------------------------------------------------------------------------

def _recurrent(n=400):
    u = np.zeros(n)
    u[0], u[1] = 1.0, 0.5
    for i in range(2, n):
        u[i] = 0.6 * u[i - 1] + 0.3 * u[i - 2]
    return u


def test_exact_recurrence_leaves_nothing_to_protect():
    from aionq.sentinel import sentinel_score
    s = sentinel_score(_recurrent())
    assert s.score == pytest.approx(0.0, abs=1e-9)


def test_dense_noise_is_not_flagged_as_sparse_novelty():
    from aionq.sentinel import sentinel_score
    rng = np.random.default_rng(0)
    s = sentinel_score(rng.normal(size=400))
    assert s.sparsity < 0.2
    assert s.score == pytest.approx(0.0, abs=1e-9)


def _fixed_and_expanding(seed):
    from aionq.sentinel import sentinel_score
    rng = np.random.default_rng(seed)
    fixed = _recurrent()
    for m in range(17, fixed.size, 17):
        fixed[m] += rng.normal() * 3.0
    expanding = _recurrent()
    m, k, gap = 12, 1, 6
    while m < expanding.size:
        expanding[m] += rng.normal() * 3.0 * (k ** 0.5)
        gap = int(gap * 1.35) + 1
        m += gap
        k += 1
    return sentinel_score(fixed), sentinel_score(expanding)


def test_composite_score_weakly_separates_expanding_from_fixed_rate():
    """The sentinel's only real signal, and it is weak: AUROC ~0.6 in Round S1."""
    wins = sum(1 for seed in range(20)
               if _fixed_and_expanding(seed)[1].score > _fixed_and_expanding(seed)[0].score)
    assert wins > 10          # better than chance, nowhere near reliable


def test_gap_expansion_alone_does_not_order_the_classes():
    """The component imported from Hecke-Mahler is NOT the one doing the work.

    On individual streams the fixed-rate class often shows a higher gap slope
    than the expanding-gap class, because the recurrence filter smears each
    isolated anomaly across several residual positions. What weakly separates
    them is magnitude variation, not gap expansion -- the opposite of what the
    source condition emphasises. Recorded rather than hidden.
    """
    disagreements = sum(1 for seed in range(20)
                        if _fixed_and_expanding(seed)[1].gap_expansion
                        <= _fixed_and_expanding(seed)[0].gap_expansion)
    assert disagreements > 5


def test_sentinel_components_are_reported_separately():
    """A single number would hide which condition fired."""
    from aionq.sentinel import sentinel_score
    s = sentinel_score(_recurrent())
    for field in ("sparsity", "gap_expansion", "variation", "support_size"):
        assert hasattr(s, field)


def test_sentinel_is_registered_as_retired():
    """It lost against the thesis's own kill condition and must stay retired."""
    from aionq.governance import registry, EvidenceTag
    c = registry["RET-S1-TRANSCENDENCE_SENTINEL"]
    assert c.tag == EvidenceTag.RETIRED
    assert any("kill condition" in x for x in c.corrections)


# --------------------------------------------------------------------------
# Round S2: Stokes-Thimble routing
# --------------------------------------------------------------------------

def test_stokes_matrix_is_unipotent_upper():
    from aionq.stokes import is_unipotent_upper, stokes_matrix
    rng = np.random.default_rng(0)
    s = stokes_matrix(4, rng=rng)
    assert is_unipotent_upper(s)
    assert np.linalg.det(s) == pytest.approx(1.0)     # a basis change, not a rescaling


def test_router_refuses_a_non_stokes_crossing():
    from aionq.stokes import StokesRouter
    r = StokesRouter(basis=np.eye(3))
    with pytest.raises(ValueError):
        r.mutate(np.diag([2.0, 1.0, 1.0]))            # not unipotent


def test_mutation_is_recorded_with_provenance():
    """The point of the router: the basis change is auditable, not hidden."""
    from aionq.stokes import StokesRouter, stokes_matrix
    r = StokesRouter(basis=np.eye(3))
    r.mutate(stokes_matrix(3, entries={(0, 1): 0.7}), at_step=42, reason="crossing")
    assert len(r.history) == 1
    assert r.history[0].at_step == 42 and r.sector == 1
    assert "crossing" in str(r.history[0])


def test_braid_action_preserves_unipotent_upper_form():
    from aionq.stokes import braid_action, is_unipotent_upper, stokes_matrix
    rng = np.random.default_rng(3)
    s = stokes_matrix(4, rng=rng)
    for i in range(3):
        assert is_unipotent_upper(braid_action(s, i))


def test_stokes_router_is_registered_as_retired_on_accuracy():
    from aionq.governance import registry, EvidenceTag
    assert registry["RET-S2-STOKES_ROUTER_ACCURACY"].tag == EvidenceTag.RETIRED
    assert registry["EXP-S2-STOKES_CONDITIONAL"].tag == EvidenceTag.MEASURED


# --------------------------------------------------------------------------
# Round S3: sheaf obstruction localisation (Sigma-infinity section 16, exp. 1)
# --------------------------------------------------------------------------

def test_cycle_rank_matches_euler_formula():
    from aionq.sheaf import Nerve, ring_of_worldlets
    n = ring_of_worldlets(6, chords=((0, 3), (1, 4)))
    assert n.betti_1 == n.n_edges - n.n_worldlets + n.n_components == 3
    assert len(n.cycle_basis()) == n.betti_1
    disconnected = Nerve(4, ((0, 1), (2, 3)))
    assert disconnected.n_components == 2 and disconnected.betti_1 == 0


def test_clean_sheaf_has_exactly_trivial_holonomy():
    """No defect must mean no obstruction, or nothing below is a measurement."""
    from aionq.sheaf import make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(11)
    nerve = ring_of_worldlets(6, chords=((0, 3), (1, 4)))
    for kind in ("generic", "commutator"):
        s = make_obstructed_sheaf(nerve, [], rng, kind=kind, dim=4)
        for c in nerve.cycle_basis():
            assert np.allclose(s.holonomy(c), np.eye(4), atol=1e-9)


def test_no_overlap_is_locally_anomalous():
    """The defect must be invisible edge by edge, or the task is an outlier scan.

    Every transition, defective or not, is an orthogonal matrix drawn from the
    same set; in the commutator regime every one of them is L_q for some q in Q_8.
    A per-edge test therefore has nothing to separate.
    """
    from aionq.sheaf import (left_multiplication_matrix, make_obstructed_sheaf,
                             quaternion_group, ring_of_worldlets)
    rng = np.random.default_rng(12)
    nerve = ring_of_worldlets(6, chords=((0, 3),))
    s = make_obstructed_sheaf(nerve, [2, 5], rng, kind="commutator", dim=4)
    group = [left_multiplication_matrix(q) for q in quaternion_group()]
    for g in s.transitions:
        assert any(np.allclose(g, h, atol=1e-9) for h in group)


def test_no_scalar_character_separates_the_commutator_regime():
    """Proved, not measured: det is a homomorphism into an abelian group.

    Every L_q for a unit quaternion lies in SO(4), so det = 1 on every overlap
    and every cycle holonomy, defective or clean.  No sample size, tuning or
    noise model can rescue a homomorphic scalar coordinate here.
    """
    from aionq.sheaf import auroc, localise, make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(13)
    nerve = ring_of_worldlets(7, chords=((0, 3), (1, 5)))
    for _ in range(20):
        defects = rng.choice(nerve.n_edges, size=2, replace=False)
        s = make_obstructed_sheaf(nerve, defects, rng, kind="commutator", dim=4)
        assert np.allclose([np.linalg.det(g) for g in s.transitions], 1.0, atol=1e-9)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        assert auroc(localise(s, "character", rng), labels) == 0.5


def test_sheaf_instrument_beats_the_matched_controls():
    from aionq.sheaf import auroc, localise, make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(14)
    nerve = ring_of_worldlets(8, chords=((0, 4), (1, 5), (2, 6)))
    got = {k: [] for k in ("sheaf", "shuffled", "graph")}
    for _ in range(40):
        defects = rng.choice(nerve.n_edges, size=2, replace=False)
        s = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        for k in got:
            got[k].append(auroc(localise(s, k, rng), labels))
    assert np.mean(got["sheaf"]) > np.mean(got["shuffled"]) + 0.1
    assert np.mean(got["sheaf"]) > np.mean(got["graph"]) + 0.1


def test_quaternionic_coordinates_tie_on_their_home_ground_and_lose_off_it():
    """The thesis's conditional, as a test: 'may improve ... only when ...'.

    The shape reproduces -- exact tie in the quaternionic regime, clear loss on
    generic O(4) -- but a tie is not an improvement, which is why
    RET-S3-HYPERCOMPLEX_DIAGNOSIS is retired rather than promoted.
    """
    from aionq.sheaf import auroc, localise, make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(15)
    nerve = ring_of_worldlets(8, chords=((0, 4), (1, 5)))
    home, away = [], []
    for _ in range(40):
        defects = rng.choice(nerve.n_edges, size=2, replace=False)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        q = make_obstructed_sheaf(nerve, defects, rng, kind="commutator", dim=4)
        home.append(auroc(localise(q, "quaternion", rng), labels)
                    - auroc(localise(q, "sheaf", rng), labels))
        g = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
        away.append(auroc(localise(g, "quaternion", rng), labels)
                    - auroc(localise(g, "sheaf", rng), labels))
    assert abs(np.mean(home)) < 1e-9        # exact tie, not a small win
    assert np.mean(away) < -0.05            # strictly worse off its home ground


def test_a_vertex_gauge_is_flat_exactly_through_the_quaternions():
    """The octonionic clause is ill-posed, and this is why.

    A gauge a_ij = g_j g_i^-1 gives zero holonomy iff L_a L_b = L_{ab}.  That
    holds through dimension 4 and fails from 8, so above the quaternions the
    CLEAN sheaf already carries an obstruction and there is no zero to measure
    a defect against.
    """
    from aionq.sheaf import flatness_ladder, ring_of_worldlets
    nerve = ring_of_worldlets(5, chords=((0, 2),))
    ladder = flatness_ladder(nerve, dims=(1, 2, 4, 8, 16), samples=25,
                             rng=np.random.default_rng(16))
    for d in (1, 2, 4):
        assert ladder[d][1] < 1e-9, f"dimension {d} should be flat"
    for d in (8, 16):
        assert ladder[d][0] > 1.0, f"dimension {d} should not be flat"


def test_left_multiplication_stops_being_a_homomorphism_at_dimension_eight():
    from aionq.sheaf import left_action_is_associative_on, random_unit_hypercomplex
    rng = np.random.default_rng(17)
    for d in (1, 2, 4):
        a, b = random_unit_hypercomplex(d, rng), random_unit_hypercomplex(d, rng)
        assert left_action_is_associative_on(a, b)
    a, b = random_unit_hypercomplex(8, rng), random_unit_hypercomplex(8, rng)
    assert not left_action_is_associative_on(a, b)


def test_associator_channel_vanishes_in_associative_algebras():
    from aionq.sheaf import localise, make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(18)
    nerve = ring_of_worldlets(6, chords=((0, 3),))
    s = make_obstructed_sheaf(nerve, [1, 4], rng, kind="commutator", dim=4)
    assert np.allclose(localise(s, "associator", rng), 0.0, atol=1e-9)


def test_gluing_defect_is_nonnegative_and_vanishes_on_a_global_section():
    """The thesis's formalisation programme asks for exactly this."""
    from aionq.sheaf import gluing_defect, make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(19)
    nerve = ring_of_worldlets(5)
    s = make_obstructed_sheaf(nerve, [], rng, kind="generic", dim=4)
    x0 = rng.normal(size=4)
    sections = [x0]
    for k in range(1, 5):
        sections.append(s.transitions[k - 1] @ sections[k - 1])
    assert gluing_defect(s, sections) >= 0.0
    assert gluing_defect(s, sections) < 1e-18
    assert gluing_defect(s, [rng.normal(size=4) for _ in range(5)]) > 0.0


def test_sheaf_laplacian_is_psd():
    from aionq.sheaf import make_obstructed_sheaf, ring_of_worldlets
    rng = np.random.default_rng(20)
    s = make_obstructed_sheaf(ring_of_worldlets(5, chords=((0, 2),)), [1], rng,
                              kind="generic", dim=3)
    ev = np.linalg.eigvalsh(s.sheaf_laplacian())
    assert ev.min() > -1e-9


def test_auroc_averages_ties_to_chance():
    """A constant-score instrument must read 0.5, not a spurious 0 or 1."""
    from aionq.sheaf import auroc
    assert auroc(np.zeros(8), np.array([1, 1, 0, 0, 0, 0, 0, 0], dtype=bool)) == 0.5


# --------------------------------------------------------------------------
# Round S3: quantum interference on the same obstruction (the QSigma claim)
# --------------------------------------------------------------------------

def test_bernstein_vazirani_reads_the_class_in_one_noiseless_query():
    from aionq.interference import bv_recover
    rng = np.random.default_rng(21)
    for b in (1, 2, 3, 5, 7):
        for _ in range(20):
            hidden = rng.integers(0, 2, size=b).astype(np.uint8)
            assert np.array_equal(bv_recover(hidden, 0.0, rng), hidden)


def test_the_obstruction_class_is_blind_to_coboundaries():
    """Two defects differing by a cut are indistinguishable to ANY query count.

    This is what makes b, not E, the learner's target -- and it bounds the
    quantum advantage as tightly as it bounds the classical cost.
    """
    from aionq.interference import cycle_incidence, obstruction_class
    from aionq.sheaf import ring_of_worldlets
    nerve = ring_of_worldlets(5, chords=((0, 2),))
    c = cycle_incidence(nerve)
    # a coboundary: the set of edges incident to one worldlet
    cut = [k for k, (i, j) in enumerate(nerve.edges) if 0 in (i, j)]
    assert np.array_equal((c @ np.eye(nerve.n_edges, dtype=np.uint8)[cut].sum(0)) % 2,
                          np.zeros(nerve.betti_1, dtype=np.uint8))
    base = obstruction_class(nerve, [1])
    moved = obstruction_class(nerve, [1] + cut)
    assert np.array_equal(base, moved)


def test_classical_cost_is_the_cycle_rank_and_quantum_cost_is_one():
    from aionq.interference import query_report
    from aionq.sheaf import ring_of_worldlets
    r = query_report(ring_of_worldlets(4, chords=((0, 2),)))
    assert (r.betti_1, r.classical_queries, r.quantum_queries) == (2, 2, 1)
    assert r.query_ratio == 2.0


def test_building_the_oracle_costs_more_than_the_queries_it_saves():
    """The caveat, as a test: outside the oracle model the advantage is negative."""
    from aionq.interference import query_report
    from aionq.sheaf import ring_of_worldlets
    for n, chords in ((4, ((0, 2),)), (6, ((0, 3), (1, 4))),
                      (12, tuple((i, i + 6) for i in range(6)))):
        r = query_report(ring_of_worldlets(n, chords=chords))
        assert r.oracle_build_cost > r.classical_queries
        assert r.honest_ratio < 1.0


def test_minimum_weight_representative_reproduces_the_class():
    from aionq.interference import minimum_weight_representative, obstruction_class
    from aionq.sheaf import ring_of_worldlets
    nerve = ring_of_worldlets(5, chords=((0, 2),))
    cls = obstruction_class(nerve, [3])
    rep = minimum_weight_representative(nerve, cls)
    assert np.array_equal(obstruction_class(nerve, np.flatnonzero(rep)), cls)
    assert rep.sum() <= 1


def test_noise_erodes_the_single_query_advantage():
    from aionq.interference import bv_success_rate
    rng = np.random.default_rng(22)
    clean = bv_success_rate(6, 0.0, 60, rng)
    noisy = bv_success_rate(6, 0.15, 200, rng)
    assert clean == 1.0
    assert noisy < 0.5


def test_round_s3_claims_are_registered_with_their_corrections():
    from aionq.governance import registry, EvidenceTag
    assert registry["EXP-S3-SHEAF_LOCALISATION"].tag == EvidenceTag.MEASURED
    assert registry["MATH-S3-NO_FLAT_ABOVE_H"].tag == EvidenceTag.PROVED
    assert registry["MATH-S3-BV_QUERY_SEPARATION"].tag == EvidenceTag.PROVED
    assert registry["RET-S3-HYPERCOMPLEX_DIAGNOSIS"].tag == EvidenceTag.RETIRED
    assert registry["RET-S3-OCTONIONIC_SHEAF"].tag == EvidenceTag.RETIRED
    assert registry["BRIDGE-S3-COHERENT_ORACLE"].kill_condition
    with pytest.raises(Exception):
        registry.cite("RET-S3-OCTONIONIC_SHEAF", section="results")


# --------------------------------------------------------------------------
# Round S7: adjudicating an external corrections audit
#
# Each test below re-derives one verdict.  They are cheap on purpose -- the
# point is that an audit's checkable content stays checked on every run, not
# only on the day it arrived.
# --------------------------------------------------------------------------

def test_berry_phase_is_half_the_enclosed_solid_angle():
    """The audit's step [1]: CORRECT, and it replicates to 1e-8."""
    from run_audit_adjudication import berry_phase_of_cone, _wrapped
    theta0 = math.acos(0.5)                      # solid angle exactly pi
    omega = 2.0 * math.pi * (1.0 - math.cos(theta0))
    assert _wrapped(berry_phase_of_cone(theta0, steps=4000) + omega / 2.0) < 1e-6
    assert abs(omega - math.pi) < 1e-12


def test_exactly_seven_octonion_triples_associate():
    """The Fano lines, counted rather than cited: 7 of 35."""
    from aionq.cayley_dickson import fast_associator
    eye = np.eye(8)
    associative = [(i, j, k)
                   for i in range(1, 8) for j in range(i + 1, 8)
                   for k in range(j + 1, 8)
                   if np.linalg.norm(fast_associator(eye[i], eye[j], eye[k])) < 1e-9]
    assert len(associative) == 7


def test_cm_curve_is_supersingular_exactly_at_the_inert_primes():
    from run_audit_adjudication import ap_of_congruent_number_curve
    for p in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31):
        assert (ap_of_congruent_number_curve(p) == 0) == (p % 4 == 3)


def test_a_nerve_carries_flat_connections_with_nontrivial_holonomy():
    """A graph has no 2-cells, so curvature is identically zero.

    Holonomy is not.  This is the counterexample to "non-trivial holonomy <=>
    non-trivial curvature" -- and it says this repository works entirely inside
    the flat-monodromy regime, not the Berry/Chern one the archive invokes.
    """
    from run_audit_adjudication import random_sheaf
    from aionq.sheaf import ring_of_worldlets
    rng = np.random.default_rng(3)
    nerve = ring_of_worldlets(7)
    sheaf = random_sheaf(nerve, 4, rng)
    hol = sheaf.holonomy([(k, +1) for k in range(nerve.n_edges)])
    assert np.linalg.norm(hol - np.eye(4)) > 0.5


def test_h1_of_a_graph_sheaf_grows_with_the_section_space():
    """dim H^1 = dim H^0 + (b1 - 1) d, so ||H^1|| is not an obstruction measure.

    Checked in its sharpest form: on one fixed nerve the UNOBSTRUCTED sheaf has
    strictly the larger H^1.
    """
    from run_audit_adjudication import cohomology_dims, random_sheaf
    from aionq.sheaf import CellularSheaf, ring_of_worldlets
    nerve = ring_of_worldlets(8, chords=((0, 4), (2, 6)))
    d, b1 = 4, nerve.n_edges - nerve.n_worldlets + 1
    flat = CellularSheaf(nerve=nerve, fiber_dim=d,
                         transitions=[np.eye(d)] * nerve.n_edges)
    generic = random_sheaf(nerve, d, np.random.default_rng(5))

    f0, f1 = cohomology_dims(flat)
    g0, g1 = cohomology_dims(generic)
    assert f1 == f0 + (b1 - 1) * d
    assert g1 == g0 + (b1 - 1) * d
    assert (f0, g0) == (d, 0)            # flat: full sections; generic: none
    assert f1 > g1                       # and yet H^1 is LARGER where nothing is wrong


def test_a_tree_nerve_has_no_first_cohomology_whatever_the_transitions():
    from run_audit_adjudication import cohomology_dims, random_sheaf
    from aionq.sheaf import Nerve
    rng = np.random.default_rng(9)
    for n in (5, 8):
        for d in (2, 4):
            nerve = Nerve(n_worldlets=n, edges=tuple((0, i) for i in range(1, n)))
            h0, h1 = cohomology_dims(random_sheaf(nerve, d, rng))
            assert (h0, h1) == (d, 0)


def test_round_s7_claims_are_registered():
    from aionq.governance import registry, EvidenceTag
    assert registry["EXP-S7-AUDIT_REPLICATION"].tag == EvidenceTag.MEASURED
    assert registry["MATH-S7-EULER_H1_IDENTITY"].tag == EvidenceTag.PROVED
    assert registry["MATH-S7-FLAT_HOLONOMY_ON_A_NERVE"].tag == EvidenceTag.PROVED
    assert registry["RET-S7-H1_AS_REMAINDER"].tag == EvidenceTag.RETIRED
    assert registry["RET-S7-AMBROSE_SINGER_BRIDGE"].tag == EvidenceTag.RETIRED
    with pytest.raises(Exception):
        registry.cite("RET-S7-H1_AS_REMAINDER", section="results")


# --------------------------------------------------------------------------
# The swallow ledger (external peer review: bare `except Exception`)
# --------------------------------------------------------------------------

def test_expected_qiskit_failures_are_recorded_not_dropped():
    from qiskit.circuit import Measure
    from qiskit.circuit.library import TGate
    from aionq.residency import (_is_clifford, _is_diagonal, clear_swallowed,
                                 swallowed_report)
    clear_swallowed()
    assert _is_clifford(TGate()) is False
    assert _is_diagonal(Measure()) is False
    sites = {r["site"] for r in swallowed_report()}
    assert sites == {"_is_clifford/Clifford", "_is_diagonal/Operator"}
    clear_swallowed()
    assert swallowed_report() == []


def test_an_unexpected_error_is_not_swallowed():
    """Narrowing the catch is the point: a real defect must still propagate."""
    from aionq.residency import _is_clifford

    class Exploding:
        name = "boom"

        def __repr__(self):
            raise KeyboardInterrupt("this must escape")

    with pytest.raises(KeyboardInterrupt):
        _is_clifford(Exploding())
