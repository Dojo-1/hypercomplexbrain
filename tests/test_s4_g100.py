"""S4-G100 test families.

Eight families, per the round specification: analytic known-answer, black-box,
structural, property-based, metamorphic, fuzz, historical regression, and
security/robustness.

A standing caveat, stated here because it belongs in the artifact rather than in
a document nobody reads: **these tests were authored from the same implementation
narrative as the code they exercise.** They are correlated evidence. They
establish that the implementation does what its author believed it does; they do
not establish that the belief was right. The only checks below that escape this
are the analytic known-answer cases, where the expected value is fixed by
mathematics rather than by the implementation, and the historical regressions,
which encode findings from an earlier round.
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, "src")

from aionq.governance import EvidenceTag, GovernanceError, RemainderKind, registry
from aionq.recognition import (AdaptiveAperture, ApertureBounds, ApertureState,
                               BordonBudget, CandidateSection, ComponentGate,
                               DepositType, EffectRegion, Explorer, FixedAperture,
                               Geometry, ManifestError, MODES, NestDeposit,
                               Polycosmos, RandomAperture, RecognitionChamber,
                               Tendril, TransportPair, TypedRemainder, Verifier,
                               Worldlet, auroc, brier_score, candidate_diversity,
                               gauge_conjugate, independent_witness_status,
                               load_manifest, loop_defect, make_fields,
                               nest_decision, validate_manifest)
from aionq.recognition.perturbations import (FIELD_SEEDS, matched_surrogate,
                                             seed_int, structured_field)
from aionq.recognition.types import CarrierMismatch
from aionq.sheaf import make_obstructed_sheaf, ring_of_worldlets

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "s4_g100_architecture.json"
PREREG = ROOT / "manifests" / "s4_g100_preregistration.json"


def _instance(seed=11, n=9, k=3):
    nerve = ring_of_worldlets(n, chords=((0, 4), (1, 6), (2, 7), (3, 8)))
    rng = np.random.default_rng(seed)
    defects = rng.choice(nerve.n_edges, size=k, replace=False)
    sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
    labels = np.zeros(nerve.n_edges, dtype=bool)
    labels[defects] = True
    return nerve, sheaf, defects, labels


def _chamber(nerve, sheaf, mode, seed=7, **kw):
    return RecognitionChamber(nerve, sheaf, mode, np.random.default_rng(seed),
                              ApertureState(), BordonBudget(50.0, 0.6, 0.4),
                              evaluation_budget=kw.pop("evaluation_budget", 64), **kw)


# ==========================================================================
# 1. ANALYTIC KNOWN-ANSWER TESTS
#    Expected values fixed by mathematics, not by the implementation.
# ==========================================================================

def test_identity_transport_has_exactly_zero_loop_defect():
    pair = TransportPair("identity", lambda x: x, lambda x: x,
                         carrier="real_vector", metric_name="euclidean")
    for x in (np.zeros(4), np.arange(5.0), np.random.default_rng(0).normal(size=7)):
        assert loop_defect(x, pair).raw_value == 0.0


def test_exact_permutation_inverse_has_zero_loop_defect():
    """P2 numerically: an exact left inverse gives zero, not merely small."""
    rng = np.random.default_rng(1)
    perm = rng.permutation(9)
    inv = np.argsort(perm)
    pair = TransportPair("permutation", lambda x: np.asarray(x)[perm],
                         lambda y: np.asarray(y)[inv], carrier="real_vector",
                         metric_name="euclidean")
    assert loop_defect(rng.normal(size=9), pair).raw_value == 0.0


def test_isometric_coordinate_change_preserves_the_loop_defect():
    """P3 numerically: conjugation by an isometry leaves the defect unchanged."""
    rng = np.random.default_rng(2)
    q, r = np.linalg.qr(rng.normal(size=(4, 4)))
    q = q * np.sign(np.diag(r))
    base = TransportPair("lossy", lambda m: np.triu(m), lambda m: m,
                         carrier="real_matrix", metric_name="frobenius")
    x = rng.normal(size=(4, 4))
    d0 = loop_defect(x, base).raw_value
    dg = loop_defect(q @ x @ q.T,
                     gauge_conjugate(base, lambda m: q @ m @ q.T,
                                     lambda m: q.T @ m @ q)).raw_value
    assert d0 > 0.0, "the probe must be lossy or the test is vacuous"
    assert abs(d0 - dg) < 1e-12


def test_zero_branch_width_is_refused_by_the_bounds():
    ap = ApertureState(branch_width=0)
    assert ap.branch_width == ap.bounds.kappa_min >= 1


def test_zero_reservoir_collapses_without_cutting_the_invariant():
    b = BordonBudget(capacity=0.0, refill_rate=0.0, invariant_draw=0.1)
    before = b.invariant_draw
    b.tick(1, ApertureState(branch_width=1, unresolved_lifetime=1.0))
    assert b.invariant_draw == before, "no code path may reduce the invariant draw"
    assert b.state in ("collapsed", "throttled")


def test_invariant_draw_exactly_equal_to_refill_survives():
    """The boundary case of P4: d == rho is survivable, d > rho is not."""
    b = BordonBudget(capacity=10.0, refill_rate=0.5, invariant_draw=0.5)
    assert b.invariant_survives
    assert math.isinf(b.depletion_time())


def test_invariant_draw_above_refill_depletes_in_finite_time():
    b = BordonBudget(capacity=1e9, refill_rate=0.5, invariant_draw=0.5000001)
    assert not b.invariant_survives
    assert math.isfinite(b.depletion_time())


def test_drone_ceiling_is_the_refill_rate_and_delegates_to_bordon():
    b = BordonBudget(capacity=1234.0, refill_rate=0.37, invariant_draw=0.1)
    assert b.drone_ceiling == pytest.approx(0.37)


# ==========================================================================
# 2. BLACK-BOX TESTS
# ==========================================================================

def test_chamber_input_produces_a_typed_deposit_output():
    region = EffectRegion("t", (ComponentGate("delta_auroc_vs_c0", 0.03),))
    d = nest_decision({"delta_auroc_vs_c0": 0.5}, region,
                      generated_by=frozenset({"A"}), authorized_by=frozenset({"B"}),
                      dependency_edges={"A": set()}, witness_status="correlated")
    assert d.deposit_type == DepositType.MEASURED_PATTERN
    assert d.evidence_tag == EvidenceTag.MEASURED


def test_evidence_tags_never_silently_upgrade():
    with pytest.raises(GovernanceError):
        NestDeposit("x", DepositType.CONJECTURE, EvidenceTag.MEASURED)
    with pytest.raises(GovernanceError):
        NestDeposit("x", DepositType.MEASURED_PATTERN, EvidenceTag.PROVED)
    with pytest.raises(GovernanceError):
        NestDeposit("x", DepositType.DESIGN_OBJECT, EvidenceTag.PROVED)


def test_measured_deposit_must_name_its_controls():
    with pytest.raises(GovernanceError):
        NestDeposit("x", DepositType.MEASURED_PATTERN, EvidenceTag.MEASURED)
    NestDeposit("x", DepositType.MEASURED_PATTERN, EvidenceTag.MEASURED,
                controls=("C0", "C2"))


def test_deterministic_replay_from_seeds():
    nerve, sheaf, _d, _l = _instance()
    for mode in MODES:
        a = _chamber(nerve, sheaf, mode).run()
        b = _chamber(nerve, sheaf, mode).run()
        assert np.array_equal(a.belief, b.belief), f"{mode} is not replayable"


# ==========================================================================
# 3. STRUCTURAL TESTS
# ==========================================================================

def test_manifest_passes_strict_validation():
    report = validate_manifest(load_manifest(MANIFEST), strict=True)
    assert report.ok, str(report)
    assert report.checks_run > 100
    assert len(report.summary["geometries"]) >= 2


@pytest.mark.parametrize("mutation,label", [
    (lambda b: b["worldlets"].pop(), "too few worldlets"),
    (lambda b: b["clocks"].pop(), "too few clocks"),
    (lambda b: b["tendrils"][0].pop("return_transport"), "no return, no reason"),
    (lambda b: b["tendrils"][0]["typed_remainder"].update(remainder_type="vibes"),
     "untyped remainder"),
    (lambda b: b["tendrils"][0].pop("lost_fields"), "lost_fields undeclared"),
    (lambda b: b["tendrils"][4].update(lost_fields=["x"]), "exact inverse with a loss"),
    (lambda b: b["dynamics"].update(hyperedges=[]), "no hyperedge"),
    (lambda b: b["dynamics"]["breathing"].update(invariant_draw=0.9),
     "invariant draw above refill"),
    (lambda b: b["dynamics"].pop("deweaving"), "no deweaving"),
    (lambda b: b["worldlets"][0].update(algebra_regime="octonion"),
     "octonionic flat-sheaf role"),
    (lambda b: b["evidence"][5].update(kill_condition=""), "H with no kill condition"),
    (lambda b: b.update(evidence_floor="M"), "evidence floor above H"),
    (lambda b: b.update(falsifiers=b["falsifiers"][:2]), "too few falsifiers"),
    (lambda b: b.pop("observables"), "missing top-level field"),
])
def test_validator_catches_each_violation(mutation, label):
    """A validator that only ever passes is a rubber stamp."""
    blob = copy.deepcopy(load_manifest(MANIFEST))
    mutation(blob)
    assert not validate_manifest(blob, strict=True).ok, f"missed: {label}"


def test_every_tendril_has_a_return_map_or_a_stated_reason():
    for t in load_manifest(MANIFEST)["tendrils"]:
        assert t.get("return_transport") or t.get("return_absent_reason"), t["id"]


def test_every_remainder_in_the_manifest_is_typed():
    for t in load_manifest(MANIFEST)["tendrils"]:
        assert t["typed_remainder"]["remainder_type"] in RemainderKind.ALL


def test_untyped_remainder_is_refused_in_code():
    with pytest.raises(GovernanceError):
        TypedRemainder("obstruction", "x", "y", 1.0)
    with pytest.raises(GovernanceError):
        TypedRemainder(RemainderKind.EMPIRICAL, "", "y", 1.0)


def test_remainders_of_different_kinds_cannot_be_subtracted():
    a = TypedRemainder(RemainderKind.EMPIRICAL, "real_matrix", "frobenius", 1.0)
    b = TypedRemainder(RemainderKind.COHOMOLOGY, "real_matrix", "frobenius", 0.5)
    with pytest.raises(CarrierMismatch):
        a.difference(b)


def test_a_one_way_tendril_must_say_why():
    with pytest.raises(GovernanceError):
        Tendril("t", "a", "b", forward_transport=lambda x: x)
    Tendril("t", "a", "b", forward_transport=lambda x: x,
            return_absent_reason="projection is genuinely lossy")


def test_every_h_claim_in_the_manifest_has_a_kill_condition():
    for e in load_manifest(MANIFEST)["evidence"]:
        if e["tag"] == EvidenceTag.HYPOTHESIS:
            assert e.get("kill_condition"), e["id"]


def test_retired_claims_cannot_appear_as_active_results():
    for cid in ("RET-S4-OPTIMAL_COGNITION", "RET-S3-OCTONIONIC_SHEAF"):
        with pytest.raises(GovernanceError):
            registry.cite(cid, section="results")


# ==========================================================================
# 4. PROPERTY-BASED TESTS
#    Hand-rolled: `hypothesis` is absent in this environment, so these are
#    seeded randomised checks and are NOT a shrinking fuzzer.
# ==========================================================================

def test_property_loop_defect_is_nonnegative():
    rng = np.random.default_rng(3)
    for _ in range(200):
        n = int(rng.integers(1, 8))
        a = rng.normal(size=(n, n))
        pair = TransportPair("rand", lambda x, a=a: a @ np.asarray(x),
                             lambda y, a=a: np.linalg.pinv(a) @ np.asarray(y),
                             carrier="real_vector", metric_name="euclidean")
        assert loop_defect(rng.normal(size=n), pair).raw_value >= 0.0


def test_property_candidate_count_obeys_the_aperture():
    rng = np.random.default_rng(4)
    for _ in range(60):
        n = int(rng.integers(3, 20))
        k = int(rng.integers(1, 24))
        ap = ApertureState(branch_width=k)
        ex = Explorer(n, rng, max_support=3)
        got = ex.generate(np.full(n, 1.0 / n), ap)
        assert len(got) == ap.branch_width


def test_property_aperture_stays_inside_declared_bounds():
    rng = np.random.default_rng(5)
    b = ApertureBounds()
    ap = ApertureState(bounds=b)
    ctrl = AdaptiveAperture(ap)
    for step in range(400):
        ctrl.update(step, float(rng.random()), float(rng.random()),
                    float(rng.random()))
        assert b.tau_min <= ap.unresolved_lifetime <= b.tau_max
        assert b.kappa_min <= ap.branch_width <= b.kappa_max
        assert b.beta_min <= ap.crystallisation_barrier <= b.beta_max


def test_property_reservoir_level_stays_bounded():
    rng = np.random.default_rng(6)
    b = BordonBudget(20.0, 0.5, 0.3)
    ap = ApertureState()
    for step in range(500):
        b.charge(float(rng.random()))
        b.tick(step, ap)
        assert -1e-9 <= b.level <= b.capacity + 1e-9


def test_property_role_weights_stay_in_their_domain():
    nerve, sheaf, _d, _l = _instance()
    ch = _chamber(nerve, sheaf, "explore_verify")
    ch.run()
    for v in ch.state.role_potentials.values():
        assert 0.0 <= v <= 1.0 + 1e-12


def test_property_evaluations_never_exceed_the_declared_budget():
    nerve, sheaf, _d, _l = _instance()
    for mode in ("static", "adaptive_unordered", "explore_verify", "verify_explore"):
        for budget in (16, 64, 200):
            ch = _chamber(nerve, sheaf, mode, evaluation_budget=budget)
            assert ch.run().evaluations <= budget, f"{mode} overspent at {budget}"


# ==========================================================================
# 5. METAMORPHIC TESTS
# ==========================================================================

def test_orthogonal_gauge_leaves_the_chamber_output_exactly_unchanged():
    """The one invariance that actually holds, and it holds exactly."""
    from aionq.sheaf import CellularSheaf
    nerve, sheaf, _d, _l = _instance()
    rng = np.random.default_rng(8)
    q, r = np.linalg.qr(rng.normal(size=(4, 4)))
    q = q * np.sign(np.diag(r))
    gauged = CellularSheaf(nerve, [q @ g @ q.T for g in sheaf.transitions], 4)
    for mode in ("static", "explore_verify"):
        a = _chamber(nerve, sheaf, mode).run().belief
        b = _chamber(nerve, gauged, mode).run().belief
        assert np.allclose(a, b, atol=1e-9), f"{mode} is not gauge invariant"


def test_equivalent_candidate_encodings_agree_exactly():
    n = 12
    v = np.array([0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0], dtype=np.uint8)
    pair = TransportPair("encoding", lambda x: np.flatnonzero(x),
                         lambda s: np.isin(np.arange(n), s).astype(np.uint8),
                         carrier="f2_cochain", metric_name="hamming")
    assert loop_defect(v, pair).raw_value == 0.0


def test_shuffled_role_labels_do_not_change_any_number():
    """Renaming the roles is not an intervention. If it were, the labels would
    be doing work the operators are supposed to do."""
    nerve, sheaf, _d, _l = _instance()
    ch = _chamber(nerve, sheaf, "explore_verify")
    before = ch.run().belief
    ch2 = _chamber(nerve, sheaf, "explore_verify")
    ch2.explorer.name, ch2.verifier.name = "empress", "emperor"
    assert np.array_equal(before, ch2.run().belief)


def test_vertex_relabeling_is_recorded_as_NOT_invariant():
    """A metamorphic test that asserts a FAILURE, because that is the finding.

    The chamber's output is not invariant under worldlet relabelling: the
    fundamental cycle basis comes from a spanning tree, and relabelling grows a
    different one. This test locks the defect in place so that a later change
    which accidentally fixes it cannot pass silently as if nothing happened.
    """
    from aionq.sheaf import CellularSheaf, Nerve
    nerve, sheaf, _d, _l = _instance()
    rng = np.random.default_rng(9)
    perm = rng.permutation(nerve.n_worldlets)
    pairs = sorted((tuple(sorted((int(perm[i]), int(perm[j])))), k)
                   for k, (i, j) in enumerate(nerve.edges))
    n2 = Nerve(nerve.n_worldlets, tuple(p[0] for p in pairs))
    s2 = CellularSheaf(n2, [sheaf.transitions[p[1]] for p in pairs], 4)
    a = _chamber(nerve, sheaf, "explore_verify").run().belief
    b = _chamber(n2, s2, "explore_verify").run().belief
    order = [p[1] for p in pairs]
    inv = np.argsort(order)
    assert not np.allclose(a, b[inv], atol=1e-6), (
        "the chamber is now relabel-invariant; RET-S4-* and the superseded "
        "EXP-S3-SHEAF_LOCALISATION_V2 must be revisited rather than left standing")


def test_matched_surrogate_preserves_the_power_spectrum_exactly():
    nerve, _s, _d, _l = _instance()
    base = structured_field(nerve, "thinking")
    sur = matched_surrogate(nerve, base, np.random.default_rng(10))
    assert np.allclose(np.sort(base.spectrum), np.sort(sur.spectrum), atol=1e-9)
    assert not np.allclose(base.values, sur.values)


# ==========================================================================
# 6. FUZZING
# ==========================================================================

def test_fuzz_malformed_transports_and_metrics():
    bad = TransportPair("nan", lambda x: np.full_like(np.asarray(x, float), np.nan),
                        lambda y: y, carrier="real_vector", metric_name="euclidean")
    with pytest.raises(ValueError):
        loop_defect(np.zeros(3), bad)
    negative = TransportPair("neg", lambda x: x, lambda y: y,
                             carrier="real_vector", metric_name="euclidean")
    object.__setattr__(negative, "metric_name", "euclidean")
    with pytest.raises(KeyError):
        TransportPair("x", lambda a: a, lambda a: a, carrier="c",
                      metric_name="not_a_metric").metric


def test_fuzz_incompatible_carriers_are_refused():
    a = TypedRemainder(RemainderKind.EMPIRICAL, "real_matrix", "frobenius", 1.0)
    b = TypedRemainder(RemainderKind.EMPIRICAL, "f2_cochain", "hamming", 1.0)
    with pytest.raises(CarrierMismatch):
        a.difference(b)


def test_fuzz_extreme_apertures_are_clamped():
    for tau, kappa, beta in ((-1e9, -5, -3.0), (1e9, 10 ** 6, 42.0),
                             (float("inf"), 2, 0.5)):
        ap = ApertureState(tau, kappa, beta)
        assert ap.bounds.tau_min <= ap.unresolved_lifetime <= ap.bounds.tau_max
        assert ap.bounds.kappa_min <= ap.branch_width <= ap.bounds.kappa_max
        assert ap.bounds.beta_min <= ap.crystallisation_barrier <= ap.bounds.beta_max


def test_fuzz_invalid_evidence_transitions_are_refused():
    with pytest.raises(GovernanceError):
        NestDeposit("x", "NotAType", EvidenceTag.HYPOTHESIS)
    with pytest.raises(GovernanceError):
        NestDeposit("x", DepositType.CONJECTURE, "Z")


def test_fuzz_resource_exhaustion_is_survivable():
    b = BordonBudget(1.0, 0.0, 0.0)
    ap = ApertureState(branch_width=32, unresolved_lifetime=16.0)
    for step in range(200):
        b.charge(5.0)
        b.tick(step, ap)
    assert b.level >= 0.0
    assert b.interventions, "exhaustion must be recorded, not absorbed silently"
    assert any(e.action == "narrow_branch_width" for e in b.interventions)


def test_fuzz_negative_budget_parameters_are_refused():
    for kw in ({"capacity": -1.0}, {"refill_rate": -1.0}, {"invariant_draw": -1.0}):
        base = {"capacity": 1.0, "refill_rate": 1.0, "invariant_draw": 0.5}
        base.update(kw)
        with pytest.raises(ValueError):
            BordonBudget(**base)


# ==========================================================================
# 7. SECURITY / ROBUSTNESS
# ==========================================================================

def test_manifest_loading_refuses_paths_outside_the_repository():
    with pytest.raises(ManifestError):
        load_manifest("/etc/passwd")


def test_manifest_loading_refuses_non_json():
    with pytest.raises(ManifestError):
        load_manifest(ROOT / "README.md")


def test_manifest_loading_refuses_a_missing_file():
    with pytest.raises(ManifestError):
        load_manifest(ROOT / "manifests" / "does_not_exist.json")


def test_generated_candidate_counts_are_bounded():
    ap = ApertureState(branch_width=10 ** 9)
    assert ap.branch_width <= ap.bounds.kappa_max


# ==========================================================================
# 8. HISTORICAL REGRESSIONS
#    These encode findings from earlier rounds and must not be relaxed.
# ==========================================================================

def test_s3_negative_findings_are_preserved():
    assert registry["RET-S3-HYPERCOMPLEX_DIAGNOSIS"].tag == EvidenceTag.RETIRED
    assert registry["RET-S3-OCTONIONIC_SHEAF"].tag == EvidenceTag.RETIRED
    assert registry["MATH-S3-NO_FLAT_ABOVE_H"].tag == EvidenceTag.PROVED


def test_no_octonionic_flat_sheaf_can_be_declared():
    blob = copy.deepcopy(load_manifest(MANIFEST))
    for regime in ("octonion", "sedenion"):
        blob["worldlets"][0]["algebra_regime"] = regime
        blob["worldlets"][0]["flat_sheaf_role"] = True
        rep = validate_manifest(blob, strict=True)
        assert not rep.ok
        assert any("RET-S3-OCTONIONIC_SHEAF" in e for e in rep.errors)


def test_the_primary_representation_is_real_not_hypercomplex():
    ev = next(w for w in load_manifest(MANIFEST)["worldlets"]
              if w["role"] == "local_evidence_carrier")
    assert ev["algebra_regime"] == "real_matrix"


def test_promotion_is_a_region_and_never_a_weighted_score():
    """RET-R3-SCALAR_PROMOTION, enforced: no trade-off between axes is possible."""
    region = EffectRegion("t", (ComponentGate("a", 0.1), ComponentGate("b", 0.1)))
    assert not region.dominated({"a": 100.0, "b": 0.0})
    assert region.dominated({"a": 0.1, "b": 0.1})


def test_a_claim_cannot_promote_itself():
    """P5, as a test: authorisation from inside the generating closure is not
    authorisation."""
    region = EffectRegion("t", (ComponentGate("a", 0.0),))
    edges = {"gen": {"helper"}, "helper": {"auditor_inside"}}
    inside = nest_decision({"a": 1.0}, region, generated_by=frozenset({"gen"}),
                           authorized_by=frozenset({"auditor_inside"}),
                           dependency_edges=edges)
    assert inside.self_promotion_blocked
    assert inside.deposit_type == DepositType.UNRESOLVED
    outside = nest_decision({"a": 1.0}, region, generated_by=frozenset({"gen"}),
                            authorized_by=frozenset({"external"}),
                            dependency_edges=edges)
    assert not outside.self_promotion_blocked


def test_the_s4_witnesses_are_declared_correlated_not_independent():
    same = {"code": "aionq.recognition", "assumptions": "S4", "data": "sheaf",
            "author": "same"}
    st = independent_witness_status({"explorer": same, "verifier": same,
                                     "auditor": same})
    assert st["status"] == "correlated"
    assert set(st["shared_axes"]) == {"code", "assumptions", "data", "author"}


# ==========================================================================
# 9. PREREGISTRATION INTEGRITY
# ==========================================================================

def test_preregistration_gates_match_the_registered_claims():
    region = EffectRegion.from_preregistration(load_manifest(PREREG))
    names = {g.name for g in region.gates}
    assert {"delta_auroc_vs_c0", "instability", "ordered_flow_margin"} <= names
    assert len(region.gates) == 10


def test_preregistration_records_no_post_hoc_amendment():
    assert load_manifest(PREREG)["amendment_policy"]["amendments_made"] == []


def test_perturbation_seeds_are_frozen():
    assert FIELD_SEEDS == {"thinking": "7a8c4a8d", "proving": "8cad443b",
                           "formalising": "450deccc"}
    assert seed_int("thinking") == int("7a8c4a8d", 16)


def test_s4_claims_are_registered_at_the_right_tiers():
    assert registry["MATH-S4-LOOP_ZERO"].tag == EvidenceTag.PROVED
    assert registry["MODEL-S4-BORDON_CEILING"].tag == EvidenceTag.PROVED
    assert registry["RET-S4-FERTILE_APERTURE"].tag == EvidenceTag.RETIRED
    assert registry["RET-S4-ORDERED_FLOW"].tag == EvidenceTag.RETIRED
    assert registry["RET-S4-OPTIMAL_COGNITION"].tag == EvidenceTag.RETIRED
    assert registry["SEM-S4-EMPEROR"].tag == EvidenceTag.SEMANTIC
    assert registry["EXP-S3-SHEAF_LOCALISATION"].superseded_by == \
        "EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT"


# ==========================================================================
# 10. THE CONJUGATE ANTI-PAIR: true identity, unsupported interpretation
# ==========================================================================

def test_conjugate_associator_antipair_holds_exactly():
    """A(conj a, b, c) = -A(a, b, c). True, and two lines to prove."""
    from aionq.cayley_dickson import cd_conjugate, fast_associator, _random_unit
    rng = np.random.default_rng(0)
    for dim in (2, 4, 8, 16):
        for _ in range(200):
            a, b, c = (_random_unit(dim, rng) for _ in range(3))
            std = fast_associator(a, b, c)
            assert np.allclose(fast_associator(cd_conjugate(a), b, c), -std,
                               atol=1e-12)


def test_plain_negation_produces_the_same_antipair():
    """The claim that conjugation makes this an 'algebraically exact anti-pair,
    not an aesthetic duality' does not survive: negation does it too, exactly.

    conj(a) and -a differ by 2 Re(a) . 1, and A(1, b, c) = 0, so the two act
    identically on the associator.  A diagnostic that cannot separate
    Cayley-Dickson conjugation from multiplication by -1 is not evidence that
    conjugation is the right relation between a provability tower and a doxastic
    one.  Locks RET-S4-CONJUGATION_IS_LOAD_BEARING.
    """
    from aionq.cayley_dickson import fast_associator, _random_unit
    rng = np.random.default_rng(1)
    for dim in (8, 16):
        for _ in range(200):
            a, b, c = (_random_unit(dim, rng) for _ in range(3))
            # negation flips the associator EXACTLY, not just to tolerance
            assert np.array_equal(fast_associator(-a, b, c),
                                  -fast_associator(a, b, c))


def test_the_antipair_is_vacuous_below_octonions():
    """Identically zero at dim 2 and 4: no content for complex or quaternionic
    towers, so the construction cannot distinguish them at all."""
    from aionq.cayley_dickson import fast_associator, _random_unit
    rng = np.random.default_rng(2)
    for dim in (1, 2, 4):
        for _ in range(200):
            a, b, c = (_random_unit(dim, rng) for _ in range(3))
            assert np.allclose(fast_associator(a, b, c), 0.0, atol=1e-12)


def test_associator_vanishes_on_the_identity():
    """A(1, b, c) = 0 exactly: the reason the whole thing is trilinear-trivial."""
    from aionq.cayley_dickson import fast_associator, _random_unit
    rng = np.random.default_rng(3)
    for dim in (2, 4, 8, 16):
        one = np.zeros(dim)
        one[0] = 1.0
        for _ in range(100):
            b, c = _random_unit(dim, rng), _random_unit(dim, rng)
            assert np.allclose(fast_associator(one, b, c), 0.0, atol=1e-14)


# ==========================================================================
# 11. MODULE-INDEPENDENT REMAINDER SAFETY
#     Transplanted from an external audit of a sibling codebase, which found a
#     module whose remainder stayed bounded only because another module ran.
# ==========================================================================

def test_aperture_is_bounded_without_any_controller():
    """No controller, no budget tick: bounds must come from the type itself."""
    ap = ApertureState()
    for step in range(500):
        ap.set("branch_width", ap.branch_width * 2, step, "unbounded widening")
        ap.set("unresolved_lifetime", ap.unresolved_lifetime * 2, step, "unbounded")
    assert ap.branch_width == ap.bounds.kappa_max
    assert ap.unresolved_lifetime == ap.bounds.tau_max


def test_reservoir_is_bounded_with_no_aperture_to_throttle():
    """tick(aperture=None) removes the throttle's handle; level must still hold."""
    b = BordonBudget(capacity=10.0, refill_rate=0.1, invariant_draw=0.05)
    worst = 0.0
    for step in range(1000):
        b.charge(9.0)
        b.tick(step, None)
        worst = min(worst, b.level)
    assert worst >= -1e-9


def test_invariant_draw_never_falls_under_any_pressure():
    """The one thing no code path may do."""
    b = BordonBudget(capacity=1.0, refill_rate=0.0, invariant_draw=0.9)
    ap = ApertureState()
    for step in range(1000):
        b.charge(50.0)
        b.tick(step, ap)
    assert b.invariant_draw == 0.9


def test_provenance_log_growth_is_registered_as_a_known_drift():
    """The audit's one real finding: the log grows while invariant_draw is fixed.

    MODEL-S4-BORDON_CEILING stays true inside its constant-rate model; what is
    retired is the implicit claim that the model's constant draw matches the
    implementation's actual consumption.
    """
    from aionq.governance import registry
    b = BordonBudget(capacity=1.0, refill_rate=0.0, invariant_draw=0.5)
    ap = ApertureState()
    for step in range(300):
        b.charge(10.0)
        b.tick(step, ap)
    assert len(b.interventions) > 100, "the log does grow without bound"
    assert registry["RET-S4-CONSTANT_INVARIANT_COST"].tag == EvidenceTag.RETIRED


# ==========================================================================
# 12. MOVING FRAME: orbit-collapse vs orbit-resolution
# ==========================================================================

def _mf_instance(seed=5):
    from aionq.sheaf import Nerve
    rng = np.random.default_rng(seed)
    nerve = Nerve(8, tuple(sorted({(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                                   (6, 7), (7, 0), (0, 4), (1, 5), (2, 6)})))
    defects = rng.choice(nerve.n_edges, size=2, replace=False)
    sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
    labels = np.zeros(nerve.n_edges, dtype=bool)
    labels[defects] = True
    return nerve, sheaf, labels, rng


def test_frame_action_is_a_genuine_group_action():
    """Gates everything else: acting by f2 after f1 must equal the composite.

    The first implementation re-sorted edges on every action.  Sorting is a
    canonicalisation, not a group operation, so this returned infinity and
    correctly invalidated every orbit statistic built on it.
    """
    from aionq.movingframe import equivariance_defect, random_frame
    nerve, sheaf, _l, rng = _mf_instance()
    for _ in range(50):
        f1 = random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
        f2 = random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
        assert equivariance_defect(nerve, sheaf, f1, f2) < 1e-9


def test_frame_composed_with_its_inverse_is_the_identity():
    from aionq.movingframe import compose, identity_frame, invert, random_frame
    nerve, sheaf, _l, rng = _mf_instance()
    ident = identity_frame(nerve.n_worldlets, 4, nerve.n_edges)
    for _ in range(50):
        f = random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
        c = compose(invert(f), f)
        assert c.vertex_perm == ident.vertex_perm
        assert c.edge_order == ident.edge_order
        assert np.allclose(c.gauge, ident.gauge, atol=1e-9)


def test_loop_closure_is_exact_for_every_instrument():
    """Nonzero closure would be hidden state carried between runs, not frame
    dependence.  It is a bug class no single-frame-pair attack can detect."""
    from aionq.movingframe import loop_closure, random_frame
    from aionq.sheaf import localise
    nerve, sheaf, labels, rng = _mf_instance()
    frames = [random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
              for _ in range(6)]
    for name in ("laplacian", "sheaf", "graph", "character"):
        m = (lambda n2, s2, l2, nm=name:
             auroc(localise(s2, nm, np.random.default_rng(7)), l2))
        assert loop_closure(m, nerve, sheaf, labels, frames) == 0.0


def test_laplacian_instrument_is_orbit_collapsed():
    """The basis-free instrument is EXACTLY frame-invariant, like betti_1.

    It never references a fundamental cycle basis, so there is no spanning tree
    for a relabelling to change.  Locks MATH-S5-LAPLACIAN_INVARIANT.
    """
    from aionq.movingframe import orbit_report, random_frame
    from aionq.sheaf import localise
    nerve, sheaf, labels, rng = _mf_instance()
    frames = [random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
              for _ in range(30)]
    m = lambda n2, s2, l2: auroc(localise(s2, "laplacian",
                                          np.random.default_rng(7)), l2)
    r = orbit_report("laplacian", m, nerve, sheaf, labels, frames)
    assert r.max_deviation == 0.0
    assert r.is_invariant


def test_cycle_basis_instruments_are_orbit_resolving():
    """A metamorphic test that asserts a FAILURE, because that is the finding.

    Every instrument that spreads blame over a fundamental cycle basis reports
    frame coordinates, not object structure.  Locked so a later change that
    accidentally fixes one cannot pass silently.
    """
    from aionq.movingframe import orbit_report, random_frame
    from aionq.sheaf import localise
    nerve, sheaf, labels, rng = _mf_instance()
    frames = [random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
              for _ in range(30)]
    for name in ("sheaf", "graph", "scalar"):
        m = (lambda n2, s2, l2, nm=name:
             auroc(localise(s2, nm, np.random.default_rng(7)), l2))
        r = orbit_report(name, m, nerve, sheaf, labels, frames)
        assert not r.is_invariant, f"{name} is now invariant; revisit the ledger"


def test_topological_control_is_exactly_invariant():
    from aionq.movingframe import orbit_report, random_frame
    nerve, sheaf, labels, rng = _mf_instance()
    frames = [random_frame(nerve.n_worldlets, 4, rng, nerve.n_edges)
              for _ in range(20)]
    r = orbit_report("betti_1", lambda n2, s2, l2: n2.betti_1,
                     nerve, sheaf, labels, frames)
    assert r.max_deviation == 0.0


def test_moving_frame_claims_are_registered():
    from aionq.governance import registry
    assert registry["MATH-S5-LAPLACIAN_INVARIANT"].tag == EvidenceTag.PROVED
    assert registry["EXP-S5-INVARIANT_LOCALISATION"].tag == EvidenceTag.MEASURED
    assert registry["RET-S5-CYCLE_BASIS_INSTRUMENTS"].tag == EvidenceTag.RETIRED
    assert registry["EXP-S4-SHEAF_LOCALISATION_BASIS_DEPENDENT"].superseded_by == \
        "EXP-S5-INVARIANT_LOCALISATION"


# ==========================================================================
# 13. ACAF: the degenerate-spectrum boundary that falsified a P-tagged claim
# ==========================================================================

def test_degeneracy_safe_cut_never_splits_an_eigenspace():
    from aionq.sheaf import _degeneracy_safe_cut
    # a spectrum with a 4-fold degenerate block straddling k=2
    vals = np.array([0.0, 1.0, 1.0, 1.0, 1.0, 5.0])
    assert _degeneracy_safe_cut(vals, 2) == 5, "cut must clear the whole block"
    assert _degeneracy_safe_cut(vals, 5) == 5, "already in a gap: unchanged"
    assert _degeneracy_safe_cut(np.array([0.0, 1.0, 2.0]), 2) == 2


def test_laplacian_is_invariant_on_a_single_cycle_where_the_old_cut_failed():
    """Cycle rank 1 is where every ACAF invariance failure lived.

    The fixed-k instrument broke here with deviations up to 0.80; this locks the
    regime so the fix cannot silently regress.
    """
    from aionq.movingframe import orbit_report, random_frame
    from aionq.sheaf import Nerve, localise
    rng = np.random.default_rng(17)
    for v in (6, 9, 14):
        nerve = Nerve(v, tuple((i, (i + 1) % v) for i in range(v)))
        assert nerve.betti_1 == 1
        for dim in (3, 4, 8):
            defects = rng.choice(nerve.n_edges, size=1, replace=False)
            sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic",
                                          dim=dim)
            labels = np.zeros(nerve.n_edges, dtype=bool)
            labels[defects] = True
            frames = [random_frame(v, dim, rng, nerve.n_edges) for _ in range(10)]
            m = lambda n2, s2, l2: auroc(
                localise(s2, "laplacian", np.random.default_rng(7)), l2)
            r = orbit_report("laplacian", m, nerve, sheaf, labels, frames)
            assert r.max_deviation == 0.0, f"broke at V={v} dim={dim}"


def test_the_falsified_p_claim_is_retired_and_superseded():
    from aionq.governance import registry
    assert registry["RET-S5-FIXED_CUT_INVARIANT"].tag == EvidenceTag.RETIRED
    assert registry["MATH-S6-LAPLACIAN_INVARIANT_SAFE"].tag == EvidenceTag.PROVED
    assert registry["MATH-S5-LAPLACIAN_INVARIANT"].superseded_by == \
        "MATH-S6-LAPLACIAN_INVARIANT_SAFE"
    assert registry["EXP-S5-INVARIANT_LOCALISATION"].superseded_by == \
        "EXP-S6-ACAF_REPLICATION"
