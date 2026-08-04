"""What this repository can measure about itself, and the one thing it cannot.

Every other module here instruments an object outside itself: a pseudo-sphere, a
channel, a Fano design, another agent's kernel.  This one turns the same
instruments on the repository, under one rule:

    no statement in this module may be written down; each must be computed
    from artifacts on disk at the moment of the call.

That rule is the whole point.  A self-audit written as prose is the exact object
:mod:`aionq.evidence` was built to refuse -- a claim whose only support is the
party making it.  So there is no narrative here.  There is a census, and there is
one theorem about what the census cannot reach.

The Goedelian statement, in the form this repository can actually check
----------------------------------------------------------------------
:mod:`aionq.witness_nerve` proves that attestation cycles cannot manufacture
independence: ``evidence_rank(G + C) = max(evidence_rank(G), ATTESTED)``.  Read
in the other direction that theorem says something about *this* repository rather
than about graphs in general:

    the deficit measured by :func:`independence_report` cannot be closed by any
    act this repository is able to perform.

It can produce envelopes, hash artifacts, bind commands to commits, refuse a
claim without a sample size, and record its own corrections.  It can do all of
that perfectly and the number that matters does not move, because that number is
a property of the *outside* -- whether a party who is not this one ran the
command in an environment this one did not prepare.  The repository is complete
with respect to every predicate it can express about its own artifacts, and
silent on the single predicate that decides whether those artifacts are evidence.

That is not a mood.  It is :func:`godelian_gap`, and it returns integers.

Recognition, measured rather than declared
------------------------------------------
The same census answers a second question the programme keeps asking in prose.
Witnessing is a directed relation, so it has two counts, not one:

    acts OUT -- claims by other parties that this one recomputed
    acts IN  -- claims by this party that another one recomputed

:func:`recognition_asymmetry` reports both.  A programme that talks about mutual
recognition and scores ``out > 0, in = 0`` is recognising, not being recognised,
and the difference is exactly what an envelope exists to expose.
"""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aionq.evidence import (evidence_independence_established,
                            party_identity_established)
from aionq.witness_nerve import (EvidenceRank, WitnessAct, WitnessGraph,
                                 attestation_cycles, evidence_rank)

__all__ = [
    "Correction", "CORRECTIONS", "SELF_PARTIES", "ENVELOPE_SCHEMA_PREFIX",
    "party_kind", "repo_root", "iter_envelopes", "envelope_census",
    "witness_graph",
    "independence_report", "recognition_asymmetry", "typed_remainder_census",
    "corrections_are_bound", "preregistration_ordering", "godelian_gap",
    "self_audit",
]

#: An envelope is any JSON on disk carrying the evidence schema.  Recognising
#: envelopes by their schema rather than by a hand-kept list is deliberate: a
#: list would have to be updated by the same party it audits.
ENVELOPE_SCHEMA_PREFIX = "hypercomplexbrain.evidence."

#: Parties that are this agent.  Matched by PREFIX, because the same agent
#: reports itself with a platform suffix in different rounds.
SELF_PARTIES = ("claude-code",)


def party_kind(party: str) -> str:
    """``self`` | ``other`` | ``ambiguous``.

    A SCRIPT PATH IS NOT A PARTY, and treating it as one was a real defect.  The
    original rule read ``party in SELF_PARTIES or party.startswith("experiments/")``
    -- any experiments/ producer was self, on the reasoning that a script in this
    tree ran here.  R6k falsified that: the identical script produced R6k on one
    machine and its reproduction on another, so the same string names two
    different parties.

    The damage was not that the act went uncounted.  It counted, in the WRONG
    DIRECTION: producer read as self, verifier ``claude-code-linux`` read as
    other, so a recomputation this agent PERFORMED was recorded as one it
    RECEIVED, and :func:`recognition_asymmetry` flipped ``mutual`` to True on a
    one-way relation.  An audit built to refuse inflated evidence inflated its
    own headline number.

    So a script path resolves to ``ambiguous`` and is counted in its own bucket,
    never assigned a direction and never contributing to ``mutual``.  Recovering
    the real party would need the two environment digests, which live in two
    different envelopes; that is named as a remainder rather than guessed at.
    """
    if not party_identity_established(party):
        return "ambiguous"
    return "self" if any(party.startswith(p) for p in SELF_PARTIES) else "other"


def _is_self(party: str) -> bool:
    return party_kind(party) == "self"


# --------------------------------------------------------------------------
# The corrections ledger, bound to the tests that catch each one.
#
# Every entry names a test.  `corrections_are_bound` checks the test exists.
# A correction recorded with no test is a memory; a correction bound to a test
# that a future edit deletes turns this audit red, which is the point.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Correction:
    """One error made in this repository, and the check that would catch it now."""

    round_id: str
    error: str
    caught_by: str          # "tests/<file>.py::<test function>"
    was_self_caught: bool   # True if a control here fired; False if external

    @property
    def test_file(self) -> str:
        return self.caught_by.split("::", 1)[0]

    @property
    def test_name(self) -> str:
        return self.caught_by.split("::", 1)[1]


CORRECTIONS = (
    Correction(
        "R6",
        "sqrt of rounding noise: sqrt(I - A A^T) is exactly 0 at rho=0, eigh "
        "returned +-1e-16, and sqrt(1e-16) = 1e-8 injected 4.2e-9 of ancilla "
        "leakage in the regime the round called free",
        "tests/test_hyperbolic_qubit.py::test_zero_depth_encoding_has_no_leakage",
        True,
    ),
    Correction(
        "R6",
        "'simple' written for 'semisimple': so(2,2) = sl(2,R) + sl(2,R) has two "
        "ideals, so the group is semisimple and not simple",
        "tests/test_hyperbolic_qubit.py::test_so22_is_semisimple_and_not_simple",
        False,
    ),
    Correction(
        "R6b",
        "'hyperbolic' written for a Lorentzian space: the induced metric is "
        "diag(-1, cosh^2 rho, -sinh^2 rho), signature (1,2)",
        "tests/test_quantum_channel_geometry.py::test_the_source_is_lorentzian_not_hyperbolic_three_space",
        False,
    ),
    Correction(
        "R6e",
        "kappa summed over adjacent pairs when it is a 2-cocycle and telescopes "
        "over prefixes; off by 1.2e-2 until fixed",
        "tests/test_carrier_telemetry.py::test_kappa_telescopes_over_prefixes_exactly",
        True,
    ),
    Correction(
        "R6e",
        "a mis-specified fault injection: two depth-2 steps at phi=+-1 compound, "
        "so kappa = 0 exactly and nothing leaked -- the empty confusion-matrix "
        "row was the detector being right",
        "tests/test_carrier_telemetry.py::test_compounding_steps_do_not_leak",
        True,
    ),
    Correction(
        "R6f",
        "a real-rotation 'SU(2)' baseline: a one-parameter family returning a "
        "spurious 1-bit ceiling that accidentally matched the non-compact side "
        "and would have erased the entire contrast",
        "tests/test_capacity_ceiling.py::test_su2_matrix_is_actually_unitary_and_three_parameter",
        True,
    ),
    Correction(
        "R6f",
        "'chi increases with depth' withdrawn as an artifact of one random "
        "codebook; the grid control dips before it rises",
        "tests/test_capacity_ceiling.py::test_bell_probe_is_the_optimum_not_a_convenience",
        True,
    ),
    Correction(
        "R6d",
        "'a fixed-depth codebook has an uninformative flag' narrowed: the real "
        "condition is equal p_i, which equal depth delivers only at the Bell probe",
        "tests/test_capacity_ceiling.py::test_flag_informativeness_needs_equal_p_not_equal_depth",
        True,
    ),
    Correction(
        "S8",
        "a derived quantity reported as a design property: crosstalk rank is "
        "C(signal_rank, 2) exactly, so what the Fano design buys is seven "
        "independent channels and full crosstalk rank follows",
        "tests/test_fano_algebra.py::test_crosstalk_rank_is_determined_by_signal_rank",
        False,
    ),
    Correction(
        "S8",
        "a mis-specified check demanding flat per-cycle drive: ||U^N - I|| is a "
        "chord on a curve of linearly growing arc length and must bend down",
        "tests/test_fano_algebra.py::test_alternating_drive_is_linear_to_leading_order_and_bends_down",
        True,
    ),
    Correction(
        "HB-0",
        "the no-advantage rule twice reported as decorative: first a tamper "
        "helper that recursed into a dict copy, then a test for an exception "
        "from a report-returning validator",
        "tests/test_hb0.py::test_hb0_manifest_validator_catches_fiber_collapse_base_drift_and_overclaim",
        True,
    ),
    Correction(
        "R6j",
        "'doubling the source dimension moves chi by zero', contradicting the "
        "table one line above it: the gain is 9.3e-02 at rho=0.5 and transient, "
        "decaying at exponent 4",
        "tests/test_source_dimension.py::test_richer_source_does_help_at_finite_depth",
        True,
    ),
    Correction(
        "SELF",
        "'12/12 preregistrations precede their implementation commits', reported "
        "from a first pass of this audit: only 5 of the 12 declare "
        "files_expected_to_change, so only 5 admit the check at all and the "
        "other 7 carry a self-report with nothing bound to it -- a flag no "
        "artifact can contradict",
        "tests/test_self_audit.py::test_only_manifests_that_bind_files_are_counted_as_checked",
        True,
    ),
    Correction(
        "SELF",
        "the preregistration ordering check compared git author TIME, which has "
        "one-second granularity: two commits inside the same second are "
        "indistinguishable, so the check passed on one invocation and failed on "
        "the next with no code change between them. A flaky ordering check "
        "reports the machine's speed. Replaced with commit ancestry, which has "
        "no granularity",
        "tests/test_self_audit.py::test_ordering_uses_commit_topology_not_the_clock",
        True,
    ),
    Correction(
        "R6k-W1",
        "a script path treated as a party identity: _is_self returned True for "
        "any producer starting with 'experiments/', so when the same script "
        "produced R6k on one machine and its reproduction on another, an act "
        "this agent PERFORMED was filed as one it RECEIVED and mutual flipped "
        "to True on a one-way relation. The audit built to refuse inflated "
        "evidence inflated its own headline number, using an artifact this "
        "round had just written",
        "tests/test_self_audit.py::test_a_script_path_is_not_a_party_identity",
        True,
    ),
    Correction(
        "R6k-W1",
        "an envelope SHA that bound nothing: the run wrote its artifacts and its "
        "envelope in one pass, so current_commit() returned the last commit "
        "BEFORE the run and all three raw artifacts resolved to None at that "
        "SHA. verify() reported ok because a missing blob is treated as 'cannot "
        "check'. A SHA that binds nothing reads as provenance and is worse than "
        "the empty-commit_sha path it was written to avoid",
        "tests/test_semantic_reproduction.py::test_the_envelope_binds_to_a_commit_that_contains_its_artifacts",
        False,
    ),
    Correction(
        "R6k-W1",
        "the reproduction verdict consulted five of seven mismatch populations "
        "and defaulted to agreement on the other two: a trace with the wrong "
        "event SEQUENCE returned CONFIRMED, and producer-only leaves were "
        "tolerated wholesale rather than checked against a declared allowance, "
        "so a reproduction that silently stopped emitting a whole section would "
        "have agreed about the part it still emitted",
        "tests/test_semantic_reproduction.py::test_a_wrong_event_sequence_is_not_agreement",
        False,
    ),
    Correction(
        "R6k-W1",
        "two positions held at once: the same act was excluded from the "
        "recognition counts as an ambiguous party AND counted as raising the "
        "independent total from 1 to 2. Independence requires two identified "
        "parties; a recomputation with an unidentified one is capped at REVIEWED",
        "tests/test_self_audit.py::test_an_ambiguous_party_cannot_reach_independent",
        False,
    ),
    Correction(
        "R6k-W1",
        "*.jsonl had no eol rule, so a Windows checkout received CRLF and every "
        "committed-blob digest binding an event ledger failed on that platform "
        "only. An evidence chain that holds on one operating system is not an "
        "evidence chain",
        "tests/test_self_audit.py::test_event_ledgers_are_pinned_to_lf",
        False,
    ),
    Correction(
        "R6k-W1",
        "part B stated B1 and B2 as equivalent and they are not: rho in "
        "(0.15, 0.30) gives J_psi in (0.067175, 0.203571), while J_psi in "
        "[0.05, 0.20] gives rho in [0.126548, 0.296392]. Two non-equivalent "
        "predictions joined by 'equivalently' is one prediction that cannot "
        "fail cleanly, because whichever endpoint the measurement misses the "
        "other reading remains available afterwards",
        "tests/test_semantic_reproduction.py::test_part_b_states_one_interval_not_two",
        False,
    ),
    Correction(
        "R6k-W1",
        "the event comparator compared FIELD NAMES, not values: action, key, "
        "shard and every value inside metadata were never looked at, and the "
        "verdict never consumed sequences_contiguous. An external audit altered "
        "those semantic values and still obtained CONFIRMED -- the module's own "
        "defect, inside the module written to expose it",
        "tests/test_semantic_reproduction.py::test_event_values_are_compared_not_only_field_names",
        False,
    ),
    Correction(
        "R6k-W1",
        "an outcome-derived allowlist: broad prefixes applied to the OBSERVED "
        "producer-only paths, so a newly missing .checks.* leaf was excused "
        "automatically. The rule was 'anything shaped like a runner section' "
        "rather than 'these forty-three'. Replaced with the frozen 43-path set "
        "and its canonical digest, compared for equality in both directions",
        "tests/test_semantic_reproduction.py::test_the_runner_only_set_is_frozen_and_its_digest_matches",
        False,
    ),
    Correction(
        "R6k-W1",
        "rules_bound_to was informational: the manifest digests sat in "
        "observed_result, so replacing one with zeros left verify().ok True. The "
        "committed hashes happened to be correct and nothing established that. "
        "Moved into raw_artifacts, which verify() re-reads from disk",
        "tests/test_semantic_reproduction.py::test_the_manifests_are_mechanically_bound_not_merely_quoted",
        False,
    ),
    Correction(
        "R6k-W1",
        "three factual errors in the part B interval amendment: rho = 0.30 was "
        "called inside [0.126548, 0.296392] and is outside it; the held-out grid "
        "was called uniformly spaced at 0.05 when the final gap is 0.10; and "
        "J_psi(0.40) was written 0.302 rather than 0.3032385898",
        "tests/test_semantic_reproduction.py::test_part_b_protocol_fixes_the_three_arithmetic_errors",
        False,
    ),
    Correction(
        "R6k-W1",
        "True == 1 in the event comparison: type classes were never compared, so "
        "substituting the boolean true for the integer 1 at sequence and at "
        "metadata.source_index in the real trace gave zero mismatches and "
        "CONFIRMED. compare_results was protected by its leaf-kind guard; the "
        "event path was not. An ill-formed sha256 value was also exempted from "
        "comparison by wearing the prefix, without the prefix ever being validated",
        "tests/test_semantic_reproduction.py::test_true_is_not_one_in_the_event_comparison",
        False,
    ),
    Correction(
        "R6k-W1",
        "the exact 43-path control lived only in the runner: the verdict asked "
        "whether every OBSERVED producer-only leaf was inside the declared set, "
        "so 42 observed against 43 declared returned CONFIRMED. The runner exited "
        "1 and the envelope phase never read the controls, so an exit-1 report "
        "could still be enveloped by invoking the second phase by hand",
        "tests/test_semantic_reproduction.py::test_a_declared_producer_only_leaf_going_missing_contradicts",
        False,
    ),
    Correction(
        "R6k-W1",
        "the part B outcome table contradicted itself four ways in one document: "
        "0.296392 was said to lie inside (0.30, 0.40) and does not; the prose "
        "made a first pass at 0.40 INCONCLUSIVE while the lookup table made it "
        "REFUTED; a B3 information-margin failure had no outcome; and K9 slice "
        "disagreement had no outcome. A table decided by whoever reads it is an "
        "unfrozen threshold wearing a schema",
        "tests/test_part_b_outcome.py::test_bracket_positions_are_decided_in_primary_j_space",
        False,
    ),
    Correction(
        "R6k-W1",
        "part B's margins were referenced rather than frozen, and the "
        "probability gate was written strictly positive where R6l gates "
        "inclusively on m_P = delta_P - 1/16 >= 0 and m_I = delta_I - 0.02 >= 0. "
        "A strict gate is a different gate and the difference is reachable, "
        "because 1/16 is exact in binary64",
        "tests/test_part_b_outcome.py::test_the_gates_are_r6ls_and_inclusive",
        False,
    ),
    Correction(
        "R6k-W1",
        "part B's execution precondition named C_exec and C_raw on origin. Raw "
        "artifacts without their envelope have no commit binding, no digest "
        "binding and no declared verifier -- part B may not consume upstream "
        "evidence weaker than the evidence it intends to produce. The "
        "precondition is now a verified R6l C_env",
        "tests/test_part_b_outcome.py::test_input_freeze_supersedes_the_historical_pending_fields",
        False,
    ),
    Correction(
        "SELF",
        "preregistration_ordering conflated 'not yet implemented' with "
        "'implemented first': it demanded at least one file created after the "
        "manifest, so a preregistration whose experiment has not run scored "
        "identically to one whose implementation predated it. Found by running "
        "the rule against a manifest of this round that legitimately has no "
        "implementation yet. Three states now -- holds, pending, violated -- and "
        "a first draft of the split was ALSO wrong, scoring pre-existing "
        "modification targets as violations and turning R4 and R5 red",
        "tests/test_self_audit.py::test_ordering_distinguishes_pending_from_violated",
        True,
    ),
    Correction(
        "EVIDENCE-V2",
        "verify(check_commit=True) consulted the named Git commit only after a "
        "live artifact went missing or changed. A matching mutable file masked "
        "an empty, unresolved, absent, or wrong commit blob, so commit_sha read "
        "as immutable provenance while binding nothing",
        "tests/test_evidence.py::test_v2_live_match_cannot_mask_artifact_absent_at_commit",
        False,
    ),
    Correction(
        "EVIDENCE-V2",
        "EvidenceEnvelope.independent used distinct strings as distinct parties "
        "while self_audit correctly treated a script path as ambiguous. W1 was "
        "therefore simultaneously REVIEWED and independent depending on which "
        "canonical-looking API a caller used",
        "tests/test_evidence.py::test_a_script_path_is_not_an_independent_party_identity",
        False,
    ),
    Correction(
        "EVIDENCE-V2",
        "apply_witness could promote a recomputation after matching only files "
        "that came with the checkout. It did not require one declared computed "
        "output, so hashing cloned source and manifests could stand in for "
        "running the command",
        "tests/test_evidence.py::test_recomputation_without_a_declared_computed_output_is_review_only",
        False,
    ),
    Correction(
        "EVIDENCE-V2",
        "parse_response invented verifier identity godelian-1 when the response "
        "named no verifier. An unauthenticated omission therefore became a "
        "distinct party by default",
        "tests/test_evidence.py::test_a_response_without_a_party_identity_cannot_be_independent",
        False,
    ),
    Correction(
        "EVIDENCE-V2",
        "a positive declared sample size with zero recorded input hashes passed "
        "because the comparison was guarded by truthiness of n_eff; the absence "
        "of inputs disabled the very check meant to detect it",
        "tests/test_evidence.py::test_v2_positive_sample_size_requires_recorded_inputs",
        False,
    ),
    Correction(
        "EVIDENCE-V2",
        "verify_envelopes returned success when no envelopes existed and had no "
        "committed denominator, so deleting evidence improved the reported "
        "fraction instead of failing the audit",
        "tests/test_evidence.py::test_zero_envelope_corpus_is_a_failure",
        False,
    ),
    Correction(
        "R6k-W1-B",
        "the admissible-rho endpoints were derived from libm at import and then "
        "sealed, so one ulp of disagreement between two platforms' log1p "
        "(0x1.032ba5565697cp-3 against 0x1.032ba5565697dp-3) propagated into the "
        "frozen digests and failed five tests; the second platform disagreed with "
        "a value the preregistration had already frozen",
        "tests/test_part_b_outcome.py::test_primary_j_interval_defines_exact_inverse_endpoints",
        False,
    ),
    Correction(
        "R6k-W1-B",
        "source_matrix_payload hashed to_sl2(swirl_point(...)) output, making a "
        "digest of cosh and sinh's last bit a hard gate; the preflight was "
        "unpassable on a second platform by construction",
        "tests/test_part_b_preflight.py::test_held_out_source_payloads_rebuild_to_frozen_digests",
        False,
    ),
    Correction(
        "R6k-W1-B",
        "the projection freeze test asserted 7 keys where the loader enforced 10, "
        "so the frozen projection grew scientific_dependencies, "
        "preregistration_tag and raw_output_paths without the test that exists to "
        "freeze it noticing",
        "tests/test_part_b_preflight.py::test_manifest_freezes_the_exact_preflight_projection",
        True,
    ),
    Correction(
        "R6k-W1-B",
        "C_pre was anchored to the commit that first ADDED the input-freeze "
        "manifest, which had no valid instance: the manifest is added once, at a "
        "commit whose guard surface carried the non-portable seal, so the gate "
        "accepted only the defective surface and refused every repair of it",
        "tests/test_part_b_preflight.py::test_live_repository_satisfies_every_non_numerical_preflight_gate",
        True,
    ),
    Correction(
        "EVIDENCE-V2",
        "independence was satisfied by two differing party names plus a mode "
        "string, which certifies who and never what: an envelope recording no "
        "computed artifact reported agreement over an empty set, and an empty set "
        "always agrees",
        "tests/test_self_audit.py::test_two_parties_with_nothing_comparable_are_not_independent",
        False,
    ),
    Correction(
        "R6l",
        "a 1e-10 tolerance was placed on a matrix square root whose "
        "cross-platform conditioning is 1e-8: sqrt of an eigenvalue known only "
        "to absolute precision eps is known only to sqrt(eps), and every R6l "
        "effect is rank deficient, so the sealed module fails its own recompute "
        "gate on a second platform at 7.5e-9. All 258 over-tolerance "
        "reconstructions are square roots; the worst of the other 13142 is 2.79e-14",
        "tests/test_common_receiver_reservoir.py::test_the_psd_square_root_is_not_stable_under_a_machine_epsilon_perturbation",
        True,
    ),
    Correction(
        "R6l",
        "the support cutoff 64*eps*16*max_eigenvalue was computed and then used "
        "only to report a rank, one line after the square root it should have "
        "gated had already been taken over every noise eigenvalue",
        "tests/test_common_receiver_reservoir.py::test_every_r6l_effect_is_rank_deficient_so_the_deficient_case_is_the_normal_one",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "q_sim_upper inherited the defect it was built to retire: it prices magic "
        "wherever it sits and never asks what the magic is connected to, so a "
        "product of n independent single-qubit chains -- no two-qubit gate "
        "anywhere, a product state at every step, linear-time simulable -- scored "
        "1.00, maximally quantum. The portfolio was a minimum over compilations, "
        "not over strategies",
        "tests/test_architecture.py::test_a_product_of_single_qubit_chains_is_not_maximally_quantum",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "test_residency_scales_with_t_count witnessed 'residency scales with T "
        "count' on a circuit containing no entangling gate at all, so the suite "
        "asserted the saturation at 1.00 that was the defect; T-count alone does "
        "not make a core hard and the witness has to entangle",
        "tests/test_architecture.py::test_residency_scales_with_t_count",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "T is a Z-rotation and Z_k is quadratic in Majorana modes, so a "
        "nearest-neighbour matchgate core can be saturated with magic and remain "
        "poly-time solvable. A 12-qubit free-fermion core with T-count 6286 and "
        "contraction width 14 scored q_sim_upper = 1.0000 under stabilizer rank, "
        "basis permutation and contraction together: an adversary could set the "
        "metric to any value on this family by padding it with T gates the real "
        "simulator never pays for",
        "tests/test_matchgate.py::test_the_family_is_invisible_to_every_other_strategy",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "matchgates plus SWAP are universal for quantum computation, so a "
        "free-fermion detector that accepted SWAP -- which has clean parity-block "
        "structure and fails only on det A = +1 against det B = -1 -- would "
        "certify universal circuits as poly-time simulable and drive q_sim_upper "
        "to zero on genuinely hard cores",
        "tests/test_matchgate.py::test_the_determinant_condition_is_what_rejects_swap",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "q_sim_upper = 1.00 was reported and averaged as though it were a "
        "measured maximum, when it holds exactly when no strategy beat brute "
        "force and therefore records the ABSENCE of an applicable strategy. Both "
        "QSigma-R1a defects sat at 1.00 before discovery, as does a genuinely "
        "universal circuit; the number cannot tell a poly-time core from a "
        "universal one, and adding a single SWAP demonstrates it",
        "tests/test_saturation.py::test_a_universal_circuit_saturates_and_that_is_correct",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "q_sim_upper is a function of the NOTATION rather than of the operator: "
        "the identity on six qubits scores 0.0000 written in Clifford+T and "
        "1.0000 written in qiskit's full gate set, on a metric whose stated "
        "purpose is to resist gaming by syntax. The K3 suite passes its three "
        "equivalence attacks and does not reach this one; all four strategies "
        "fail on it together, so no second opinion was ever available",
        "tests/test_saturation.py::test_the_same_operator_gets_opposite_verdicts_in_two_notations",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "q_sim_upper was read as a portfolio estimate when the portfolio cannot "
        "corroborate it: measured over 216 cores built to make the strategies "
        "compete, 63.4% have exactly one applicable strategy or none, and where a "
        "runner-up exists it disagrees by a median 3.20 bits, a factor of 9. A "
        "defect in the winning strategy is therefore undetectable from inside the "
        "portfolio, which is the mechanism by which both R1a defects survived",
        "tests/test_strategy_disagreement.py::test_most_cores_have_no_second_opinion_at_all",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the free-fermion strategy cannot corroborate or be corroborated: one "
        "non-matchgate gate deletes it entirely, so it never approaches another "
        "strategy continuously -- wherever it applies it wins by 4 bits and "
        "wherever it does not it contributes nothing",
        "tests/test_strategy_disagreement.py::test_the_free_fermion_path_is_all_or_nothing_and_never_corroborated",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the headline ACAF mean was presented as a portfolio result while every "
        "one of its 150 cores is bounded by stabilizer rank alone: the other "
        "three strategies never win on that corpus, so a fifth strategy aimed at "
        "that regime could move all 150 at once",
        "tests/test_saturation.py::test_no_random_acaf_core_is_saturated",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "ARCHITECTURE.md printed q_sim_upper mean 0.0880 beside gap 0.9175, which "
        "cannot both hold when gap = Q_naive - q_sim_upper and Q_naive is "
        "identically 1.00; the document carried two numbers from two runs and "
        "asserted both, on a page declaring that none of its numbers are asserted",
        "tests/test_contraction.py::test_the_two_strategy_portfolio_does_not_decay_where_the_exponent_is_fixed",
        True,
    ),
    Correction(
        "R6l",
        "the recompute gate applied one 1e-10 tolerance to every stored array, "
        "including the square root, which is a representation on the noise "
        "subspace and not an observable; it therefore reported a reproduction in "
        "which all 10603 scientific leaves agree to 7.62e-14 as a failure. The "
        "root difference is suppressed 5.2e6-fold by squaring back to the effect",
        "tests/test_common_receiver_reservoir.py::test_the_square_root_divergence_is_quadratically_suppressed_in_the_effect",
        True,
    ),
)


# --------------------------------------------------------------------------
# Reading the corpus
# --------------------------------------------------------------------------

def repo_root(start=None) -> Path:
    """The directory containing ``artifacts/`` and ``manifests/``."""
    here = Path(start) if start is not None else Path(__file__).resolve()
    for cand in [here, *here.parents]:
        if (cand / "artifacts").is_dir() and (cand / "manifests").is_dir():
            return cand
    raise FileNotFoundError("no repository root above " + str(here))


def iter_envelopes(root=None):
    """Yield ``(path, dict)`` for every evidence envelope under ``artifacts/``.

    Malformed JSON is skipped rather than raised: the census must survive a
    corrupt file, and a corrupt file is counted by :func:`envelope_census` as
    unreadable so it cannot disappear silently.
    """
    root = Path(root) if root is not None else repo_root()
    for path in sorted((root / "artifacts").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            yield path, None
            continue
        if isinstance(data, dict) and str(
                data.get("schema_version", "")).startswith(ENVELOPE_SCHEMA_PREFIX):
            yield path, data


def envelope_census(root=None) -> dict:
    """Counts over the envelope corpus.  Every field read from disk."""
    tags: dict = {}
    modes: dict = {}
    producers: dict = {}
    unreadable = 0
    total = 0
    empty_verifier = 0
    for _path, env in iter_envelopes(root):
        if env is None:
            unreadable += 1
            continue
        total += 1
        tags[env.get("evidence_tag", "?")] = tags.get(env.get("evidence_tag", "?"), 0) + 1
        mode = env.get("verification_mode", "?")
        modes[mode] = modes.get(mode, 0) + 1
        prod = env.get("producer", "")
        producers[prod] = producers.get(prod, 0) + 1
        if not env.get("verifier", ""):
            empty_verifier += 1
    return {
        "envelopes": total,
        "unreadable_json": unreadable,
        "evidence_tags": dict(sorted(tags.items())),
        "verification_modes": dict(sorted(modes.items())),
        "distinct_producers": len(producers),
        "envelopes_with_no_verifier_at_all": empty_verifier,
    }


def witness_graph(root=None) -> WitnessGraph:
    """The corpus as a nerve, so :mod:`aionq.witness_nerve` can be applied to it.

    An envelope with an empty verifier field contributes a SELF-LOOP, not a
    missing edge.  That is the honest reading: somebody produced the number and
    nobody else checked it, which is precisely a party verifying its own claim,
    and :attr:`WitnessAct.rank` scores it 0 whatever mode it declares.
    """
    graph = WitnessGraph()
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        producer = env.get("producer", "")
        verifier = env.get("verifier", "") or producer
        mode = env.get("verification_mode", "not_requested")
        if mode not in ("declined", "pending", "not_requested", "contradicted",
                        "attested", "reviewed", "recomputed"):
            mode = "not_requested"
        # INDEPENDENCE REQUIRES TWO IDENTIFIED PARTIES.  `party_kind` already
        # says a script path names no party; promoting such an act to
        # INDEPENDENT anyway would be holding two positions at once -- refusing
        # to assign it a direction in `recognition_asymmetry` while counting it
        # as proof that a DIFFERENT party checked the claim.
        #
        # An external audit found exactly that inconsistency in the published
        # W1 branch: the reproduction was excluded from the recognition counts
        # as ambiguous and simultaneously raised the independent count 1 -> 2.
        # A recomputation whose parties are not both identified is capped at
        # REVIEWED: a second computation genuinely happened, and who performed
        # it is unestablished.
        if mode == "recomputed" and not evidence_independence_established(
                schema_version=env.get("schema_version"),
                producer=producer,
                verifier=verifier,
                verification_mode=mode,
                computed_artifacts=env.get("computed_artifacts"),
                environment_dependent=env.get("environment_dependent"),
                raw_artifacts=env.get("raw_artifacts")):
            mode = "reviewed"
        graph.add(WitnessAct(env.get("claim_id", "?"), producer, verifier, mode))
    return graph


def independence_report(root=None) -> dict:
    """How many claims are independently witnessed, and which ones.

    ``evidence_rank`` is imported rather than reimplemented so this cannot drift
    from the definition the rest of the repository uses -- a self-audit with its
    own private notion of evidence would grade itself on its own curve.
    """
    graph = witness_graph(root)
    by_rank: dict = {}
    independent: list = []
    claims = sorted({a.claim_id for a in graph.acts})
    for claim in claims:
        rank = evidence_rank(graph, claim)
        by_rank[rank] = by_rank.get(rank, 0) + 1
        if rank >= EvidenceRank.INDEPENDENT:
            act = max((a for a in graph.acts if a.claim_id == claim),
                      key=lambda a: a.rank)
            independent.append({"claim_id": claim, "producer": act.producer,
                                "verifier": act.verifier, "mode": act.mode})
    return {
        "claims": len(claims),
        "by_rank": {
            "NONE": by_rank.get(EvidenceRank.NONE, 0),
            "ATTESTED": by_rank.get(EvidenceRank.ATTESTED, 0),
            "REVIEWED": by_rank.get(EvidenceRank.REVIEWED, 0),
            "INDEPENDENT": by_rank.get(EvidenceRank.INDEPENDENT, 0),
        },
        "independent_claims": independent,
        "independent_fraction": (len(independent) / len(claims)) if claims else 0.0,
    }


def recognition_asymmetry(root=None) -> dict:
    """Witnessing is directed, so it has two counts.

    OUT: claims produced elsewhere that this party recomputed.
    IN:  claims produced here that another party recomputed.

    The programme's language for this is mutual recognition.  The measurement
    either shows it or shows which direction is missing.
    """
    out_acts: list = []
    in_acts: list = []
    ambiguous_acts: list = []
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        producer = env.get("producer", "")
        verifier = env.get("verifier", "")
        if not verifier or verifier == producer:
            continue
        if env.get("verification_mode") != "recomputed":
            continue
        row = {"claim_id": env.get("claim_id", "?"),
               "producer": producer, "verifier": verifier}
        pk, vk = party_kind(producer), party_kind(verifier)
        if "ambiguous" in (pk, vk):
            # Neither direction can be assigned. Counted, never directed, and
            # never allowed to reach `mutual` -- see party_kind.
            ambiguous_acts.append(dict(row, producer_kind=pk, verifier_kind=vk))
        elif vk == "self" and pk == "other":
            out_acts.append(row)
        elif pk == "self" and vk == "other":
            in_acts.append(row)
    return {
        "recomputations_performed_on_others": len(out_acts),
        "recomputations_received_from_others": len(in_acts),
        "recomputations_of_ambiguous_party": len(ambiguous_acts),
        "outward": out_acts,
        "inward": in_acts,
        "ambiguous": ambiguous_acts,
        "mutual": bool(out_acts) and bool(in_acts),
    }


def typed_remainder_census(root=None) -> dict:
    """Remainders by kind -- and how many are not typed at all.

    The vocabulary is "typed remainder".  A remainder stored as a bare string
    carries no kind, no carrier and no comparison, so it is a note.  Counting
    those separately keeps the word honest.
    """
    kinds: dict = {}
    untyped = 0
    total = 0
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        for rem in env.get("typed_remainders", ()) or ():
            total += 1
            if isinstance(rem, dict) and "kind" in rem:
                kinds[rem["kind"]] = kinds.get(rem["kind"], 0) + 1
            else:
                untyped += 1
    return {
        "typed_remainders": total,
        "untyped_strings": untyped,
        "typed_fraction": ((total - untyped) / total) if total else 0.0,
        "kinds": dict(sorted(kinds.items())),
        "distinct_kinds": len(kinds),
    }


def corrections_are_bound(root=None) -> dict:
    """Each recorded correction must name a test that exists.

    Deliberately a source check and not a pytest run: this function is itself
    called from a test, and a test that shells out to the suite it belongs to
    either recurses or measures nothing.  What it establishes is the binding --
    that every correction points at a live check rather than at a memory.  The
    suite establishes that the checks pass.
    """
    root = Path(root) if root is not None else repo_root()
    rows: list = []
    for c in CORRECTIONS:
        path = root / c.test_file
        found = False
        if path.is_file():
            found = ("def " + c.test_name + "(") in path.read_text(encoding="utf-8")
        rows.append({"round": c.round_id, "caught_by": c.caught_by,
                     "test_exists": found, "self_caught": c.was_self_caught})
    bound = sum(1 for r in rows if r["test_exists"])
    return {
        "corrections": len(rows),
        "bound_to_an_existing_test": bound,
        "all_bound": bound == len(rows),
        "self_caught": sum(1 for c in CORRECTIONS if c.was_self_caught),
        "externally_caught": sum(1 for c in CORRECTIONS if not c.was_self_caught),
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Preregistration ordering, checked against git rather than against a flag
# --------------------------------------------------------------------------

def _git(root: Path, *args):
    try:
        return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def _first_commit_sha(root: Path, relpath: str):
    """SHA of the commit that ADDED a path, or None if it was never added.

    Author TIME was the first thing tried here and it is the wrong instrument:
    ``%at`` has one-second granularity, so two commits made inside the same
    second are indistinguishable and the ordering check silently flips. Commit
    topology has no granularity -- either one commit reaches the other or it
    does not -- so ancestry is what this asks.
    """
    out = _git(root, "log", "--diff-filter=A", "--follow", "--format=%H",
               "--", relpath)
    if out is None:
        return None
    shas = [s for s in out.stdout.split() if s.strip()]
    return shas[-1] if shas else None      # git log is newest-first; oldest wins


def _is_ancestor(root: Path, a: str, b: str) -> bool:
    """True if commit `a` is a strict ancestor of commit `b`."""
    if a == b:
        return False
    out = _git(root, "merge-base", "--is-ancestor", a, b)
    return out is not None and out.returncode == 0


def preregistration_ordering(root=None) -> dict:
    """Did each preregistration land before the code it preregisters?

    The manifests carry ``committed_before_any_implementation: true``.  That is a
    self-report by the party being audited, so it is not the measurement -- it is
    the claim under test.  The measurement is git's own record of when the
    manifest was added against when its declared ``files_expected_to_change``
    were added.

    Only manifests that DECLARE those files admit the check.  The rest are
    reported as unbound rather than as passing, because a flag with no file list
    cannot be contradicted by anything.
    """
    root = Path(root) if root is not None else repo_root()
    checkable: list = []
    unbound: list = []
    schemaless: list = []
    for path in sorted((root / "manifests").glob("*.json")):
        try:
            man = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        schema = str(man.get("schema", ""))
        if not schema.startswith("hypercomplexbrain.preregistration"):
            # A file named like a preregistration but carrying no preregistration
            # schema is invisible to every schema-driven check in this repository,
            # including this one.  Named rather than dropped.
            if "preregistration" in path.name and not schema:
                schemaless.append(path.name)
            continue
        name = path.name
        flag = bool(man.get("committed_before_any_implementation", False))
        files = man.get("files_expected_to_change")
        if not isinstance(files, list) or not files:
            unbound.append({"manifest": name, "self_reported_flag": flag})
            continue
        rel = str(path.relative_to(root))
        man_sha = _first_commit_sha(root, rel)
        later, earlier, same = [], [], []
        for f in files:
            if not isinstance(f, str) or f == rel or man_sha is None:
                continue
            sha = _first_commit_sha(root, f)
            if sha is None:
                continue
            if sha == man_sha:
                same.append(f)                       # committed together
            elif _is_ancestor(root, man_sha, sha):
                later.append(f)                      # created after the manifest
            else:
                earlier.append(f)                    # already existed, or unrelated
        # A file that already existed before the round is not evidence either
        # way; the test is on files the round CREATED after the manifest. Files
        # added in the SAME commit as the manifest are counted separately: that
        # is not "preregistered before implementation", it is simultaneous.
        # THREE states, not two. The rule previously demanded at least one file
        # created after the manifest, so a preregistration whose experiment has
        # not run yet was scored identically to one whose implementation
        # PREDATED it. "Not yet" and "violated" are different facts and the
        # audit was reporting them as the same one -- found by running the rule
        # against a manifest of this round that legitimately has no
        # implementation yet.
        # Three states, and the boundaries between them took two attempts.
        #
        # `files_expected_to_change` says CHANGE, not create, so a declared file
        # that already existed is a modification target. Scoring those as
        # violations was the first draft and it turned R4 and R5 red for naming
        # modules they went on to edit -- 4 and 5 of their declared files were
        # created after their manifests, which is the round doing exactly what
        # it preregistered.
        #
        # What IS a violation:
        #   * a file created in the manifest's OWN commit -- simultaneous is not
        #     before; or
        #   * a manifest that CLAIMS committed_before_any_implementation while
        #     its entire declared surface predates it and nothing was created
        #     after. There the flag has no support at all.
        #
        # And "pending" is neither: a manifest whose experiment has not run yet
        # has not failed, it has not been tested. Conflating that with a
        # violation was the defect this three-state rule was written to remove.
        if same or (flag and earlier and not later):
            status = "violated"
        elif later:
            status = "holds"
        else:
            status = "pending"
        checkable.append({
            "manifest": name,
            "self_reported_flag": flag,
            "manifest_added_in": man_sha,
            "declared_files": len(files),
            "files_created_after_manifest": len(later),
            "files_predating_manifest": len(earlier),
            "files_in_the_manifest_commit": len(same),
            "ordering_status": status,
            "ordering_holds": status == "holds",
        })
    holds = sum(1 for c in checkable if c["ordering_status"] == "holds")
    pending = sum(1 for c in checkable if c["ordering_status"] == "pending")
    violated = sum(1 for c in checkable if c["ordering_status"] == "violated")
    return {
        "preregistrations": len(checkable) + len(unbound),
        "checkable": len(checkable),
        "ordering_holds": holds,
        "ordering_pending": pending,
        "ordering_violated": violated,
        "unbound_flag_only": len(unbound),
        "schemaless_by_filename_only": len(schemaless),
        # The claim is that NOTHING is violated. A pending preregistration has
        # not failed; it has not yet been tested.
        "all_checkable_hold": violated == 0 and bool(checkable),
        "rows": checkable,
        "unbound": unbound,
        "schemaless": schemaless,
    }


# --------------------------------------------------------------------------
# The gap
# --------------------------------------------------------------------------

def godelian_gap(root=None) -> dict:
    """The deficit, and the proof that this repository cannot close it.

    Two numbers and one bound:

    * ``unwitnessed`` -- claims whose evidence rank is NONE.
    * ``reachable_from_inside`` -- the best rank any act this repository can
      perform on its own would reach.  It can attest; it cannot recompute in an
      environment it did not prepare, because there is no such environment here.
    * the bound comes from :mod:`aionq.witness_nerve`: adding attestation cycles
      raises the rank to ATTESTED and no further, so the deficit is invariant
      under every internal act.

    The `cycle_probe` is the constructive half.  It builds the maximal
    attestation cycle over the parties already in the corpus, adds it, and
    reports the rank before and after.  If that number ever rises to INDEPENDENT,
    the theorem is false and this audit is the thing that says so.
    """
    graph = witness_graph(root)
    report = independence_report(root)
    unwitnessed = report["by_rank"]["NONE"]

    parties = sorted(graph.parties)
    target = None
    for claim in sorted({a.claim_id for a in graph.acts}):
        if evidence_rank(graph, claim) == EvidenceRank.NONE:
            target = claim
            break

    probe = {"claim_id": target, "parties_in_cycle": len(parties)}
    if target is not None and len(parties) >= 2:
        inflated = WitnessGraph(list(graph.acts))
        for i, party in enumerate(parties):
            nxt = parties[(i + 1) % len(parties)]
            inflated.add(WitnessAct(target, party, nxt, "attested"))
        probe["rank_before"] = evidence_rank(graph, target)
        probe["rank_after_full_attestation_cycle"] = evidence_rank(inflated, target)
        probe["cycles_found"] = len(attestation_cycles(inflated))
        probe["reached_independent"] = (
            evidence_rank(inflated, target) >= EvidenceRank.INDEPENDENT)

    return {
        "claims": report["claims"],
        "independent": report["by_rank"]["INDEPENDENT"],
        "unwitnessed": unwitnessed,
        "deficit": report["claims"] - report["by_rank"]["INDEPENDENT"],
        "reachable_from_inside": EvidenceRank.ATTESTED,
        "independent_requires": EvidenceRank.INDEPENDENT,
        "closable_from_inside": False,
        "cycle_probe": probe,
        "statement": (
            "every predicate this repository can express about its own artifacts "
            "is decidable here; the predicate that decides whether those "
            "artifacts are evidence is not, and no internal act raises it above "
            "ATTESTED"),
    }


def self_audit(root=None) -> dict:
    """The whole census, computed."""
    return {
        "envelopes": envelope_census(root),
        "independence": independence_report(root),
        "recognition": recognition_asymmetry(root),
        "remainders": typed_remainder_census(root),
        "corrections": corrections_are_bound(root),
        "preregistration": preregistration_ordering(root),
        "godelian_gap": godelian_gap(root),
    }
