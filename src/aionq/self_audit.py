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
import re
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
    "corrections_are_bound", "manifest_pointers_resolve",
    "corrections_name_rounds_that_ran",
    "preregistration_ordering", "godelian_gap",
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
        "q_sim_upper was reported as a property of a core and is ORBIT-RESOLVING: "
        "0.0000 in the identity frame and 0.9000 after swapping the names of two "
        "wires, an orbit spread of 0.9 on a scale of [0,1] from relabelling. The "
        "free-fermion path reads the qubit labelling through its adjacency test, "
        "and a minimum over strategies inherits the worst typing of its members. "
        "This is the S4-G100 error -- a headline retired as basis-dependent -- "
        "reappearing inside the metric built to replace the one S4 killed",
        "tests/test_frame_orbit.py::test_q_sim_upper_inherits_it_and_is_orbit_resolving",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "test_a_clean_tracked_target_is_accepted named src/aionq/residency.py "
        "outright, so it asserted a property of the WORKING TREE rather than of "
        "assert_clean: it failed in any session with uncommitted changes to that "
        "file, which is most sessions in which anyone is editing it. The subject "
        "is the function, so the file must be chosen by asking git which tracked "
        "file is currently clean",
        "tests/test_mutation_probe.py::test_a_clean_tracked_target_is_accepted",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "a cycle-structure reading separates translations from transvections on "
        "the GENERATORS -- 2^8 against 2^4 1^8 -- and that looked like a second "
        "separator. Across the whole of AGL(1,16) three of the five cycle types "
        "contain both line-preserving and line-breaking frames, so cycle type "
        "cannot decide which half of the frame group an element lies in. 3-XOR "
        "orthogonality decides it exactly, so it is the only separator",
        "tests/test_gf_frames.py::test_cycle_type_separates_the_generators_but_not_the_group",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "there is no hardness saddle in frame space and the reason is structural, "
        "not empirical: q_sim_upper is a minimum over four strategies, three are "
        "orbit-collapsed on all 322560 frames and the only resolving member is "
        "BINARY, so the minimum takes at most two values. Measured, exactly two "
        "are realised -- 0.00 on the stabiliser and 0.25 on the other 238 -- so "
        "the landscape is flat at two levels with a cliff between them and "
        "nothing is close to the transition",
        "tests/test_gf_frames.py::test_the_hardness_landscape_is_a_step_and_not_a_saddle",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "AGL(1,16) of order 240 is only the SEMILINEAR frame group. The full "
        "GF(2)-linear one is AGL(4,2) of order 322560, a factor of 1344 larger, "
        "and invariance on it is decidable exactly from sixteen generators "
        "rather than by walking it: contraction width is broken by 0 of 16 and "
        "so is invariant on all 322560 frames, while the free-fermion "
        "certificate is broken by 16 of 16 -- maximal fragility, sharper than "
        "the index-120 statement",
        "tests/test_gf_frames.py::test_the_lift_to_agl42_is_decided_exactly_by_sixteen_generators",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the first 3-XOR run reported that not every generator preserves the 35 "
        "lines of PG(3,2) and that read as a finding. It was a mis-grouping: "
        "linear maps must preserve a^b^c=0 since M(a^b^c)=Ma^Mb^Mc, and it is "
        "the translations alone that break it, because (a^t)^(b^t)^(c^t)=t. "
        "3-XOR orthogonality is a GL(4,2) invariant and NOT an AGL(4,2) one -- "
        "the relation is anchored at the origin and translations move it",
        "tests/test_gf_frames.py::test_three_xor_orthogonality_separates_the_linear_part_from_the_affine",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the moving-frame review sampled four to six points of S_16, a group of "
        "order 2.1e13, and reported orbit-collapse from it. Zero spread over six "
        "random frames is consistent with luck. Labelling the qubits by GF(16) "
        "built as GF(4)[y]/(y^2+y+w) gives AGL(1,16) of order 240, which is "
        "walked in full: contraction width is collapsed on every one of the 240 "
        "frames, upgrading the sampled suspicion to a fact about the group",
        "tests/test_gf_frames.py::test_contraction_width_is_collapsed_on_the_whole_affine_group",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the free-fermion certificate's frame dependence was reported as a "
        "spread. Enumerated over the whole affine group it is a stabiliser: "
        "exactly two of 240 frames preserve it, the identity and XOR with "
        "all-ones, which is x -> 15-x. Its stabiliser is Aut(P_16), the "
        "automorphism group of the path graph the gates were laid on, of index "
        "120 -- and it already fails on a two-element subgroup",
        "tests/test_gf_frames.py::test_the_free_fermion_certificate_survives_exactly_two_of_240_frames",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the first moving-frame measurement sampled 24 uniformly random "
        "permutations of ten qubits and reported orbit spread ZERO for a family "
        "whose true spread is 0.9, because none of the 24 was the identity and "
        "the identity is the frame in which the free-fermion path applies. An "
        "orbit sample that cannot reach the frame where the quantity differs "
        "measures nothing",
        "tests/test_frame_orbit.py::test_the_orbit_sample_always_reaches_the_identity",
        True,
    ),
    Correction(
        "REGISTRY",
        "every instrument in this repository measures a deficiency and none "
        "reports the positive quantity, so what the programme KNOWS had never "
        "been computed. It is: 93 claims, 26 retired -- retirement is the "
        "largest single category, above 25 proved and 25 measured -- and of 57 "
        "live evidence-requiring claims exactly ONE carries a verified "
        "envelope, the AXIOM, whose envelope the architecture already records "
        "as unsigned and self-recomputed. Zero proved and zero measured claims "
        "carry one",
        "tests/test_knowledge_ledger.py::test_exactly_one_evidence_requiring_claim_is_witnessed_and_it_is_the_axiom",
        True,
    ),
    Correction(
        "REGISTRY",
        "registry.unwitnessed() returns claims at an EVIDENCE-REQUIRING tag with "
        "no envelope, so HYPOTHESIS and SEMANTIC claims never appear in it. "
        "Reading their absence as 'witnessed' inverts the ledger and turns "
        "1-of-57 coverage into an apparent 11-of-67 -- a sixfold overstatement "
        "in the one direction that flatters the programme",
        "tests/test_knowledge_ledger.py::test_hypotheses_and_metaphors_are_not_counted_as_witnessed",
        True,
    ),
    Correction(
        "REGISTRY",
        "the evidence deficit was reported as a level and never as a "
        "derivative. Against the R4 baseline recorded in ARCHITECTURE section 7 "
        "-- 48 of 81 claims carrying no envelope -- it is now 56 of 93: twelve "
        "claims added and eight arrived bare, so coverage moved the wrong way "
        "while the corpus grew. A large deficit that is closing is a programme "
        "in progress; a smaller deficit that is widening is not",
        "tests/test_knowledge_ledger.py::test_the_gap_is_widening_not_closing",
        True,
    ),
    Correction(
        "CORPUS",
        "the dependency instrument published three wrong figures before it was "
        "reviewed: it scanned only the top level of the package and missed 24 "
        "modules under hb0/ and recognition/, it dropped 'from . import (...)' "
        "entirely, and it matched bare round names so that '3-manifold' counted "
        "as a reference to the manifold round and 'r40_complete' as one to r4. "
        "It also skipped envelopes, which is where this repository records "
        "provenance binding -- looking for composition everywhere except the "
        "file whose job is to record it. Corrected: 114 code edges not 60, and "
        "2 evidence edges not 4",
        "tests/test_dependency_closure.py::test_the_code_graph_is_an_order_of_magnitude_denser_than_the_evidence_graph",
        True,
    ),
    Correction(
        "CORPUS",
        "the leverage ranking was published with the claim that every module at "
        "its top has depends_on = 0 and is therefore a foundation that can only "
        "originate a defect. On the corrected graph governance moves from sixth "
        "to SECOND at radius 21 with depends_on = 1, so the ranking was wrong in "
        "its order and the foundations reading was wrong outright: the top "
        "splits into sources, which can only originate, and transmitters, which "
        "can inherit a defect and then fan it out",
        "tests/test_dependency_closure.py::test_the_highest_leverage_modules_split_into_sources_and_transmitters",
        True,
    ),
    Correction(
        "CORPUS",
        "the round names promise a descent -- unitary price through common "
        "receiver to quantum movement -- and the artifacts do not compose in "
        "that shape. 60 local import edges against 4 genuine scientific "
        "cross-round references, 21 of 26 rounds referencing nothing, and 0 "
        "artifacts declaring an upstream key, so the graph a defect actually "
        "travels along is recorded almost nowhere in the evidence",
        "tests/test_dependency_closure.py::test_the_code_graph_is_an_order_of_magnitude_denser_than_the_evidence_graph",
        True,
    ),
    Correction(
        "CORPUS",
        "audit attention was spent on the module with blast radius ZERO while "
        "the modules with blast radius seven and ten went unexamined. "
        "_principal_psd_sqrt cost a full round and nothing imports its module, "
        "so its containment was assumed by never being asked about; "
        "hyperbolic_qubit reaches ten modules across R6e to R8 and part B, "
        "carries the HB0 axiom whose witnessing the architecture already "
        "records as absent, and depends on nothing itself",
        "tests/test_dependency_closure.py::test_the_load_bearing_modules_are_the_ones_nobody_audited",
        True,
    ),
    Correction(
        "QSigma-R3B-0",
        "neg_energy and neg_latency were recorded as unmeasurable because "
        "operation counts are not energy and depth is not latency -- correct "
        "about the QUANTITY, but the cone asks for a DIFFERENCE. With the arms "
        "at verified resource parity the difference vanishes exactly for every "
        "cost model that is a function of the resource profile, so two "
        "coordinates were derivable without naming the quantity at all",
        "tests/test_parity_derived.py::test_the_derivation_lowers_the_codimension_from_four_to_two",
        True,
    ),
    Correction(
        "QSigma-R3B-0",
        "the HOLD was read as though the organ had failed to show an effect. It "
        "had not: the cone's constraints are per-coordinate and uncoupled, so the "
        "projection onto the four measured axes is exact, and the measured effect "
        "is interior to it on every axis by a factor near 2.5. All four "
        "unmeasured axes are no_worse and demand no improvement. HOLD is a "
        "stratum of codimension 4 where membership is not posed, not a refusal",
        "tests/test_witness_geometry.py::test_the_measured_sub_vector_is_interior_to_the_projected_cone",
        True,
    ),
    Correction(
        "WITNESS-NERVE",
        "the evidence rank of a one-party graph was read as an obstruction that "
        "happens to vanish. The nerve of a one-party cover is a POINT -- 12 "
        "self-loops, 0 edges, dimension 0 -- so there is no degree-1 part in "
        "which an obstruction could live. Quality lives in the fibre and the "
        "problem is the base, which is why no internal act of any mode lifts it",
        "tests/test_witness_geometry.py::test_a_one_party_nerve_is_a_point",
        True,
    ),
    Correction(
        "ARCHITECTURE",
        "section 8 presented three load-bearing remainders as three separate "
        "debts, with the Godelian one as the philosophical outlier. Computed "
        "against the live repository they share a single blocker -- an act by a "
        "party that is not this one -- and the promotion gate makes it explicit: "
        "audit is not tradeable against effect size, so measuring the four "
        "missing cone coordinates would leave the gate shut",
        "tests/test_closure.py::test_all_three_remainders_share_one_blocker",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the corroboration round measured where two simulation strategies agree "
        "without first asking whether agreement would count. It would not: four "
        "strategies are four methods of one party, so producer equals verifier "
        "and evidence_rank is NONE even granting every ordered pair a full "
        "recomputed act. The agreeing region that round went looking for was "
        "worth nothing before it was measured",
        "tests/test_closure.py::test_the_portfolio_agreement_carries_no_evidence",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the mutation probe edits the source under test in place and restored it "
        "in a finally, which does not survive SIGKILL. An interrupted run left "
        "residency.py carrying a live mutation -- informative returning "
        "bounding_strategy == 'dense', the exact inversion of its contract -- "
        "which no test could kill and which sat in the working tree, one "
        "'git commit -a' from being published, and would have been adopted as "
        "the baseline by the next run",
        "tests/test_mutation_probe.py::test_a_dirty_target_is_refused_before_any_mutation",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the two new strategy modules had a mutation kill rate of 52.2%: 11 of "
        "23 single-line breakages went unnoticed by the modules' own tests, "
        "including the cost convention's width + 1, both wrongly-shaped-matrix "
        "guards, and the 'and' in is_diagonal_matrix. A suite reports whether "
        "its witnesses fail and never whether they reach",
        "tests/test_contraction.py::test_the_cost_convention_charges_width_plus_one_exactly",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "the saturation flag reported the zero-qubit circuit as saturated, "
        "claiming absence of information about the one circuit whose cost is "
        "exactly known, and contradicting its own definition since q_sim_upper "
        "is 0.0 there. The test asserting the equivalence never included a "
        "witness with n = 0",
        "tests/test_saturation.py::test_the_degenerate_zero_qubit_circuit_is_not_reported_as_saturated",
        True,
    ),
    Correction(
        "QSigma-R1a",
        "matchgate_plan conjugated the gate matrix by the operand swap for "
        "descending operands, under a comment claiming the parity blocks were "
        "not swap-symmetric. They are: the required-zero set is closed under the "
        "exchange, A is read from indices the exchange fixes, and B is conjugated "
        "so its determinant is preserved. The conjugation was a no-op on every "
        "input and the test guarding it used two swap-symmetric gates, so it "
        "could not fail",
        "tests/test_matchgate.py::test_the_classification_is_invariant_under_the_operand_swap",
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
    Correction(
        "LeanMath-import",
        "the first survey of the imported archive reported that HardnessHolonomy "
        "imports eight LambdaSatSolver.VDIS modules 'none of which are in the "
        "zip'. Measured against the files: one resolves, two are present at "
        "another path, five are absent. The overstatement was in the direction "
        "of the conclusion already drawn, which is the direction that needs a "
        "measurement rather than a reading",
        "tests/test_leanmath_vendor.py::test_the_five_carrier_file_is_the_least_satisfiable_of_all",
        True,
    ),
    Correction(
        "LeanMath-import",
        "the archive's placeholders were first counted with grep, which returned "
        "16 and put two of them at TuringHalting_Master.lean:376,407. A "
        "comment-aware census returns 1: thirteen of the sixteen are prose about "
        "placeholders, including the sentence claiming there are none, and the "
        "two at 376 and 407 are inside a block comment that never closes",
        "tests/test_leanmath_vendor.py::test_grep_would_report_sixteen_times_as_many_placeholders_as_exist",
        True,
    ),
    Correction(
        "LeanMath-import",
        "'no lean/lake toolchain in this environment' was recorded as the reason "
        "nothing in the archive could be checked. elan was in fact installed with "
        "an empty toolchains directory, and the archive's own pinned "
        "leanprover/lean4:v4.32.0-rc1 installed in minutes. Accepting the "
        "unverifiability cost two toolchain-confirmed lex failures covering 39% "
        "of the archive's bytes, including both of its README's Key Theorems",
        "tests/test_leanmath_vendor.py::test_the_python_counter_still_agrees_with_the_pinned_lexer",
        True,
    ),
    Correction(
        "LeanMath-import",
        "formal/README.md asserted 'lean, lake and elan are present on PATH' and "
        "the claim was carried forward across sessions unchecked; in this "
        "container only elan was present and no lean binary existed on PATH at "
        "all. An environment claim written on one machine does not travel",
        "tests/test_leanmath_vendor.py::test_the_formal_readme_no_longer_claims_a_toolchain_on_path",
        True,
    ),
    Correction(
        "QSigma-R1d",
        "the first coordinate-free free-fermion defect was still coordinate "
        "dependent, and not in its formula but in its AGGREGATOR: it took max "
        "over the individual Majorana residuals, and a maximum over a basis does "
        "not survive rotating the basis. Measured deviation 1.2e-1 under random "
        "O(4) frames on a quantity presented as invariant; summing squares "
        "instead measures 1.3e-15. Writing a formula without indices does not "
        "make it invariant if the reduction that turns it into a number reads them",
        "tests/test_majorana.py::test_a_max_over_the_basis_is_not_invariant_and_a_sum_of_squares_is",
        True,
    ),
    Correction(
        "QSigma-R1f",
        "three rounds reported quantities as ORBIT-COLLAPSED and treated collapse "
        "as the good case without ever running the control that distinguishes an "
        "invariant from a blind quantity. A measurement constant on the frame "
        "orbit AND constant under a non-frame perturbation is not seeing the "
        "object, it has no content. Found by testing a proposed gauge-covariance "
        "device whose frame bounds are (1,1) under a gauge change AND under a "
        "shuffled connection, while spectrum, holonomy and localisation move by "
        "3.6e-1, 1.60 and 5.8e-2. Applied retroactively: R1C's three collapsed "
        "strategies do move under a change of circuit, so they are not blind and "
        "the findings stand -- but that was asserted for three rounds, not measured",
        "tests/test_connection_frame.py::test_the_repositorys_own_collapsed_quantities_are_not_blind",
        True,
    ),
    Correction(
        "QSigma-R1g",
        "the first QFFO-excitation measurement built its generator as "
        "sum A_jk c_j c_k and Hermitised. For j != k the Majorana product is "
        "ANTI-Hermitian, so symmetrising annihilated it exactly: every "
        "Hamiltonian was zero, every unitary was the identity, and both "
        "excitation branches reported free-fermion defect 0.000e+00. A clean "
        "dichotomy was one step from being recorded from a measurement of the "
        "identity operator. The missing factor of i is the entire difference, "
        "and the exact zero -- not 1e-16 -- was the only thing that looked wrong",
        "tests/test_fishnet.py::test_the_generator_is_not_identically_zero",
        True,
    ),
    Correction(
        "QSigma-R1h",
        "R1G recorded a planarity remainder claiming matchgate_plan's "
        "nearest-neighbour condition is a 1D restriction where free-fermion "
        "tractability needs only planarity, so the certified path plausibly "
        "refuses free-fermion circuits on planar non-linear layouts. Measured: a "
        "matchgate matrix on non-adjacent qubits is not a free-fermion operation "
        "at all -- iSWAP on (0,2) has gaussian_defect 6.93 against 0.0 on (0,1) "
        "-- because Jordan-Wigner gives it the Z string of the qubit it jumps. "
        "The refusal is semantically correct. The remainder reasoned about the "
        "gate layout while the constraint lives in the encoding",
        "tests/test_mode_locality.py::test_a_matchgate_on_non_adjacent_qubits_is_not_a_free_fermion_operation",
        True,
    ),
    Correction(
        "QSigma-R1h",
        "the retroactive not-blind control named three of the four strategies it "
        "was written to cover, omitting basis_permutation -- the one whose base "
        "value is infinite and which the chosen variants therefore looked least "
        "likely to move. It does move, so nothing was hidden, but a control that "
        "quietly drops the case least likely to pass is the defect the test "
        "itself exists to detect",
        "tests/test_connection_frame.py::test_the_repositorys_own_collapsed_quantities_are_not_blind",
        True,
    ),
    Correction(
        "QSigma-R1i",
        "R1G recorded the QFFO many-body excitation as supplying 'the "
        "parameterised transverse departure the portfolio lacks'. It supplies an "
        "ALGEBRAIC departure and no DYNAMICAL one: f(H) shares the eigenbasis of "
        "H, hence its conserved quantities, so the level-spacing ratio moves by "
        "4e-4 while a quartic term moves it 0.29 on the same spectrum, from 0.309 "
        "to 0.596. One axis was measured and the conclusion was drawn about the "
        "other. The mechanism is that the QFFO weights saturate -- identical to "
        "eight decimals at n=100 and n=2048 -- so on a 512-level spectrum the "
        "multiplier is a constant, and the statistic is scale-invariant",
        "tests/test_spectral_slice.py::test_the_qffo_excitation_does_not_move_the_dynamical_axis",
        True,
    ),
    Correction(
        "QSigma-R1i",
        "qffo.q_gamma overflowed for arguments above about 1500: Gamma_q carries "
        "a factor (1-q)^(1-x), which at q=0.5 and x=2000 is 2^1999. Every use in "
        "the module is a RATIO in which that factor cancels exactly, so the "
        "quantity was always well conditioned and only the intermediate was not. "
        "Unnoticed for a round because nothing had asked the multiplier for a "
        "coefficient index above about twenty",
        "tests/test_spectral_slice.py::test_the_multiplier_saturates_which_is_the_mechanism",
        True,
    ),
    Correction(
        "QSigma-R1j",
        "a driven free-fermion fishnet was measured at quasi-energy <r> = 0.43, "
        "between Poisson 0.386 and GUE 0.600, and was one step from being "
        "recorded as partial chaos. It is a folding artefact: quasi-energies are "
        "angles, and at 5.8 wraps the statistic does not merely degrade but "
        "INVERTS -- the integrable system reads more chaotic than the chaotic "
        "one, separation -0.05 against +0.24 below one wrap",
        "tests/test_braid.py::test_past_the_threshold_the_statistic_inverts_its_sign",
        True,
    ),
    Correction(
        "QSigma-R1j",
        "the control that caught the folding artefact was itself overclaimed: "
        "from two data points it concluded that folding pushes the statistic "
        "toward Poisson. Across eight seeds and three periods the shift has mean "
        "-0.016, std 0.082, sixteen down and eight up. Folding is a SCRAMBLE, not "
        "a bias, worst magnitude 0.161 against a signal of 0.212 -- which is "
        "worse than a bias, because a bias could be subtracted",
        "tests/test_braid.py::test_folding_alone_scrambles_the_statistic_by_as_much_as_the_signal",
        True,
    ),
    Correction(
        "QSigma-R1k",
        "herald_parity built its observable by symmetrising a Majorana product "
        "instead of phasing it by i^(k(k-1)/2). For k=2 the product is "
        "ANTI-Hermitian, so symmetrising annihilated it: every projector became "
        "I/2, all six quadratic heralds fired at probability exactly 0.25, and "
        "the 'post-selected' state was the input. The headline -- quadratic "
        "parity heralding preserves Gaussianity -- was for one round supported by "
        "a measurement of the identity. It survives the fix, at probabilities "
        "0.135 to 0.865 and defect 4.4e-16. Second missing factor of i this "
        "session, and the Hermiticity assertion meant to catch it PASSED, because "
        "the zero matrix is Hermitian; the guard is now on the spectrum",
        "tests/test_pond.py::test_the_herald_observable_is_a_genuine_two_outcome_measurement",
        True,
    ),
    Correction(
        "QSigma-R1l",
        "the positive control for the storm experiment was VACUOUS: a quartic "
        "herald applied to a post-storm state fired at probability 1.000, so the "
        "state was already an eigenvector and the projection did nothing. Its "
        "wick_defect of 1.1e-16 would have been reported as 'even a quartic "
        "herald cannot disturb a post-storm state', which is false. The tell is "
        "the probability, not the defect, and a control that cannot fire is not "
        "a control",
        "tests/test_pond.py::test_a_vacuous_herald_is_detected_rather_than_reported_as_a_null",
        True,
    ),
    Correction(
        "QSigma-R1l",
        "having caught the vacuous control, the replacement reading -- that the "
        "storm destroys a state's capacity to receive magic -- was itself wrong, "
        "and wrong twice: it was one seed and it was n = 4. Across twelve seeds "
        "at n = 4 only 1 of 36 quartic heralds is vacuous, and across six seeds "
        "at n = 6 every single post-storm state is taken to wick_defect 1.0 by "
        "some quartic herald. Two successive readings of the same experiment "
        "were both artifacts of a single small case",
        "tests/test_pond.py::test_a_post_storm_state_can_still_receive_magic",
        True,
    ),
    Correction(
        "QSigma-R1n",
        "R1M published a seven-row table of final entropies and supports per "
        "ladder rung as though each were a property of the rung. They are one "
        "draw: over five seeds T16 gives 3.0, 1.0, 1.0, 2.0, 1.0 and M15 gives "
        "2.0, 2.0, 0.0, 2.0, 2.0 -- M15 reaching the collapsed value once. Only "
        "the collapse/no-collapse dichotomy is seed-robust, and within it only "
        "T2, T4 and FROBENIUS collapse on all five seeds. The non-monotonicity "
        "claim survives (FROBENIUS robustly 0, M3 robustly not) but the specific "
        "values do not",
        "tests/test_pond.py::test_translation_by_a_proper_subfield_collapses_at_this_labelling",
        True,
    ),
    Correction(
        "QSigma-R1o",
        "the weak-herald sweep at alpha/(pi/4)=0.8 was read as reaching 0.0000 at "
        "600 steps and recorded as 'weak measurement slows the collapse but does "
        "not prevent it'. The printed 0.0000 was 2.18e-06 shown at four decimals. "
        "Measured properly: 8.4e-1 at 150 steps, 6.8e-3 at 300, 2.2e-6 at 600, "
        "1.5e-8 at 1000 -- an asymptotic decay that never arrives, where the "
        "projective case reaches exactly 0 in seven steps and freezes. Weak and "
        "projective differ in KIND, not in rate, and the display precision hid it",
        "tests/test_pond.py::test_weak_measurement_gives_an_asymptotic_approach_not_a_slower_arrival",
        True,
    ),
    Correction(
        "QSigma-R1p",
        "a 'spectral analysis of the rungs' was built on an ANTISYMMETRIC pair "
        "matrix, whose signs require choosing an orientation per edge that is no "
        "part of the pair set. T4 gives four distinct spectra over twelve random "
        "orientations. The first pass looked only at T2 and M3, which happen to "
        "give one each, and only at the top four magnitudes, which are "
        "degenerate -- so it read an arbitrary choice as an invariant. The "
        "orientation-free object is the symmetric adjacency matrix",
        "tests/test_pond.py::test_the_antisymmetric_pair_spectrum_depends_on_an_arbitrary_orientation",
        True,
    ),
    Correction(
        "QSigma-R1p",
        "the orientation check itself printed 'the antisymmetric spectrum is NOT "
        "a property of the pair set' from output showing four IDENTICAL spectra. "
        "The conclusion was right and the evidence displayed did not support it; "
        "it took a second run at full spectrum and twelve orientations to find "
        "the T4 counterexample that does. Stating a conclusion the visible data "
        "contradicts is the same defect as stating one the data does not reach",
        "tests/test_pond.py::test_the_antisymmetric_pair_spectrum_depends_on_an_arbitrary_orientation",
        True,
    ),
    Correction(
        "QSigma-R1q",
        "R1M's headline -- 'the break in the field tower is between GF(4) and "
        "GF(16)', with T2, T4 and FROBENIUS collapsing and M3, M15, T16 and AGL "
        "not -- is WITHDRAWN. It is an artifact of the mode-to-qubit labelling. "
        "A relabelling permutes the modes and changes no intrinsic invariant of "
        "the pair set, yet over three collapsing rungs, eight relabellings each "
        "and three storm seeds each the result is 9 of 9 collapses as given and "
        "0 of 72 relabelled. R1M's own typed remainder named this exact test and "
        "it went unrun for three rounds while R1N, R1O and R1P were built on top "
        "of it. The control that it is not a step budget was also run: relabelled "
        "families at 900 steps freeze at 1.0 to 3.0 rather than drifting to zero",
        "tests/test_pond.py::test_the_collapse_does_not_survive_a_relabelling_of_the_modes",
        True,
    ),
    Correction(
        "QSigma-R1q",
        "the Pauli centre -- the radical of the symplectic form on the F2 edge "
        "span, which is the centre of the stabiliser group each pair family "
        "generates -- separated all ten families PERFECTLY: radical 4 or 8 for "
        "every collapsing family, 0 or 1 for every other. It then failed on the "
        "first family it was not fitted to. A random perfect matching has radical "
        "8, identical to T2, and gives final entropy 2.0 at three seeds. Ten "
        "points of agreement bought nothing, because the rule named no mechanism",
        "tests/test_pond.py::test_the_pauli_centre_separates_every_family_it_was_fitted_to_and_then_fails",
        True,
    ),
    Correction(
        "QSigma-R1q",
        "the replacement rule was ALSO wrong on first reading. Having found that "
        "T2's eight pairs are exactly the eight single-qubit Z measurements, this "
        "round recorded 'the same-qubit count is what tracks the outcome' -- and "
        "the same run's own output already contradicted it: FROBENIUS collapses "
        "with 3 same-qubit pairs while relabellings with 3 and with 4 do not. A "
        "family built as all eight Z's plus eight cut-crossing pairs has the "
        "maximum count of 8 and does not collapse at any seed. The mechanism is "
        "cut_crossing_pairs: entanglement_entropy reads the middle cut, and a "
        "herald on a pair that does not straddle it is local to one side",
        "tests/test_pond.py::test_the_same_qubit_count_is_not_the_mechanism",
        True,
    ),
    Correction(
        "QSigma-R1q",
        "the anticommutation criterion behind pauli_centre_rank was written in "
        "three places as '|S symmetric-difference T| odd'. For two 2-element sets "
        "that quantity is ALWAYS EVEN, so as stated it says no two edges ever "
        "anticommute -- the opposite of what the function relies on. The correct "
        "condition is |S intersect T| odd, from c_S c_T = (-1)^(|S||T| - |S cap "
        "T|) c_T c_S with both weights even. The code was right throughout: it "
        "computes bin(u & v).count('1') & 1, the intersection parity. Caught on "
        "re-reading before commit. A wrong statement of a rule sitting beside a "
        "correct implementation of it is worse than either alone",
        "tests/test_pond.py::test_the_pauli_centre_separates_every_family_it_was_fitted_to_and_then_fails",
        True,
    ),
    Correction(
        "QSigma-R1r",
        "rule C's weak direction -- 'zero pairs across the cut implies collapse' "
        "-- was recorded in R1Q as CONFIRMED, 9 of 9, one commit before it was "
        "refuted. The supporting families were all constructed at the same single "
        "cut the rule was defined against, so they were not out of sample in the "
        "respect that mattered: entanglement_entropy cut at qubits//2 and "
        "cut_crossing_pairs was defined against the same boundary, so the two "
        "agreed by construction. Sweeping the cut gave 27 of 28 cells in "
        "agreement and one refutation, and the refutation was the only cell the "
        "rule had never seen -- M3 at split 2 has zero crossings and does not "
        "collapse, 0.984, 0.978, 0.741, identical at 400 and 900 steps. The "
        "strong direction survives; the biconditional does not",
        "tests/test_pond.py::test_zero_crossings_is_necessary_and_not_sufficient",
        True,
    ),
    Correction(
        "QSigma-R1r",
        "no check had ever verified that a manifest's executable_form points at a "
        "test that exists. Seventy pointers across fifteen manifests, unvalidated "
        "for sixteen rounds, and a manifest is never executed so a pointer into "
        "nothing fails silently and forever. The gap surfaced because this round "
        "renamed a test whose old name asserted a claim R1Q had withdrawn, and "
        "the citing manifest went stale in the same commit. Same shape as every "
        "other defect in this ledger -- a guard whose witness cannot reach the "
        "case it asserts -- except that here there was no guard at all",
        "tests/test_self_audit.py::test_every_manifest_pointer_resolves_to_a_test_that_exists",
        True,
    ),
    Correction(
        "QSigma-R1r",
        "supersession was recorded in one direction only. A new manifest declared "
        "what it superseded; the superseded file said nothing, so R1M could be "
        "read on its own as a live finding while stating a claim R1Q had "
        "retracted. R1Q itself repeated the omission. Making the link "
        "bidirectional and enforcing it by test immediately turned up three more "
        "one-directional links in the R6k Part B chain, unrelated to this round",
        "tests/test_self_audit.py::test_supersession_is_recorded_in_both_directions",
        True,
    ),
    Correction(
        "QSigma-R1s",
        "the covariance formalism's vacuum was written with i c_2k c_2k+1 = +1 "
        "on |0>. In this repository's Jordan-Wigner convention it is -1. The "
        "preregistered gate reported a defect of exactly 2.0 -- a clean sign "
        "flip -- on its first run. Nothing downstream would have reported it: "
        "every later quantity in the formalism is built from the vacuum "
        "covariance, so a wrong convention there is consistent with itself all "
        "the way up. It was caught only because the gate compares against the "
        "old formalism rather than against the new one's own expectations",
        "tests/test_supercable.py::test_the_vacuum_sign_convention_is_read_off_and_not_assumed",
        True,
    ),
    Correction(
        "QSigma-R1s",
        "the covariance entropy took the larger HALF of |Im spectrum| as the "
        "symplectic values. Each nu_k appears twice, once per conjugate partner, "
        "so one representative per pair is wanted -- every second entry. The "
        "wrong rule turned [1, 1, 0.325, 0.325] into [1, 1] and returned entropy "
        "0.000 against an exact 0.922. Critically it PASSES at split 1, where "
        "one pair makes the larger half and one representative the same element: "
        "a check at the smallest case would have gone green and shipped it. The "
        "gate sweeps every split, which is the only reason it was seen",
        "tests/test_supercable.py::test_the_entropy_pairing_bug_is_invisible_at_the_smallest_split",
        True,
    ),
    Correction(
        "QSigma-R1s",
        "the vacuum_covariance docstring was left arguing that i c_2k c_2k+1 is "
        "+1 on |0>, and displaying the opposite block, for a whole commit AFTER "
        "the gate had caught the code and the code had been fixed. Fixing a value "
        "while leaving the reasoning that generated it is worse than the original "
        "bug: the bug was inert, the reasoning is contagious, and a maintainer "
        "following the derivation would have restored the defect and then found "
        "the regression test apparently at fault. No check in this repository "
        "compares a docstring against the code beside it, so a full green suite "
        "saw nothing",
        "tests/test_supercable.py::test_the_vacuum_sign_convention_is_read_off_and_not_assumed",
        False,
    ),
    Correction(
        "QSigma-R1s",
        "the R1S preregistration called C ~ sqrt(N) 'the trivial Cauchy-Schwarz "
        "bound'. Cauchy-Schwarz needs a sum and a norm and the protocol "
        "constructed neither: each storm is a separate stochastic trajectory, "
        "entropy is nonlinear in Gamma, and sequential heralds do not commute. "
        "Worse, and found while verifying that objection, the definition compared "
        "runs 'at the same step budget', so a cap received steps*|F_theta|/|F| "
        "heralds inside the union run against steps alone -- a dose mismatch up "
        "to fifteenfold, which would have made the ratio meaningless on its own. "
        "The protocol also declared two different controls to be run first. All "
        "three survived being written, committed and described in a handoff",
        "tests/test_supercable.py::test_the_cap_decomposition_is_a_partition_at_matched_dose",
        False,
    ),
    Correction(
        "QSigma-R1s",
        "the additivity-gate finding stated that the M3 sign reversal means 'no "
        "inequality controlling the whole by an aggregate of the parts can hold, "
        "in l2 or in any other norm'. FALSE, and refuted by the table printed "
        "three lines above it: norms discard sign, and any finite set of cells "
        "admits some K -- the largest ratio measured is 2.957, so K = 3 satisfies "
        "the l2 inequality on all fifteen. What the sign reversal kills is "
        "ADDITIVE RECONSTRUCTION. R1P recorded that stating a conclusion the "
        "visible data contradicts is worse than stating one the data does not "
        "reach, because it looks verified; this is the same defect four commits "
        "later in the same session. Retired (R)",
        "tests/test_supercable.py::test_the_additivity_gate_failed_and_the_name_was_dropped",
        False,
    ),
    Correction(
        "QSigma-R1s",
        "the frozen verdict function was not disjoint. C < 2 for LOW and "
        "C > 0.7*sqrt(N) for HIGH are ordered the wrong way whenever "
        "0.7*sqrt(N) < 2, that is for N < 8.163, so the region described as "
        "'indeterminate' is an OVERLAP in which a cell satisfies BOTH verdicts. "
        "Eight of the fifteen cells already measured land in it, including "
        "FROBENIUS at all three seeds -- more than half the data was "
        "unclassifiable by the rule meant to classify it, and a control cell "
        "would have been reported as whichever verdict was read first. The "
        "categorical rule is abandoned rather than patched, in favour of a paired "
        "directional comparison with two exhaustive mutually exclusive outcomes",
        "tests/test_supercable.py::test_the_frozen_verdict_thresholds_were_not_disjoint",
        False,
    ),
    Correction(
        "QSigma-R1s",
        "while auditing an external Lean review, this session claimed that "
        "lean_census.strip_noncode UNDER-counts placeholders and is 'broken in "
        "the flattering direction', citing TuringHalting_Master.lean:376,407 as "
        "real sorrys reported as zero. FALSE, and refuted by this repository's "
        "own recorded measurement: those lines sit inside an unterminated "
        "comment whose opener is line 69, and the archive's own pinned toolchain "
        "-- Lean 4.32.0-rc1, installed here -- reports 'unterminated comment at "
        "1363:0 (end of file)' for exactly that file. There are no proofs after "
        "line 69, so there are no placeholders in proofs there. The counter "
        "agrees with the real lexer on 11 of 11 files and the agreement is "
        "already asserted by a test. The evidence gathered was CORRECT -- 87 "
        "openers against 85 closers, depth never returning to zero -- and its "
        "meaning was inverted: an unterminated comment makes those lines prose, "
        "not code. Caught only by opening the module before editing it; one more "
        "step would have 'fixed' correct code into a defect on the strength of "
        "the error, which is exactly the hazard recorded against the "
        "vacuum_covariance docstring two commits earlier. Filed at first under "
        "the label QSigma-R1t, which is a DIFFERENT round -- R1T is a frozen, "
        "never-executed preregistration on another development line -- so the "
        "ledger briefly attributed an error to a round that has run nothing and "
        "cannot have made one",
        "tests/test_leanmath_vendor.py::test_the_python_counter_still_agrees_with_the_pinned_lexer",
        True,
    ),
    Correction(
        "QSigma-R1x",
        "the R1X preregistration froze the two thresholds that decide its one "
        "falsifiable prediction -- 0.05 bits and 0.10 in W1 -- and then wrote "
        "'fixed step budget' without fixing it. A free parameter inside a frozen "
        "protocol is a threshold in disguise. P3 HOLDS at 300 steps, with two "
        "hits out of sixty-three matched-seed pairs, and FAILS at 900 with "
        "zero; either budget could have been reported alone as the round's "
        "answer, in opposite directions, without breaking a single frozen "
        "clause. Caught only because R1O had already recorded a budget artifact "
        "in this line, so both budgets were run. Every other frozen quantity in "
        "the manifest was checked for a free parameter after this one surfaced; "
        "the split, the qubit count, the ladder and the seeds are all named "
        "explicitly, and the budget was the only gap",
        "tests/test_lebesgue.py::test_p3_does_not_survive_a_change_of_step_budget",
        True,
    ),
    Correction(
        "QSigma-R1x",
        "gf_frames.exponent_orbits carried a docstring asserting that zero is a "
        "fixed point of every rung in the ladder. It is not. The multiplicative "
        "rungs fix it; the translations x -> x + t move it, so T2, T4, T16 and "
        "AGL carry 0 inside an orbit and the function looked it up in a table "
        "with no entry for log 0, raising KeyError. FOUR of the seven ladder "
        "cells, crashing, for a whole round. Invisible because the only two "
        "callers in this repository pass FROBENIUS and M3 -- exactly the rungs "
        "the false premise holds for -- and the one test reaches them through "
        "orbit_geometry_report, which hardcodes the same two. Not repaired by "
        "inventing a value for log 0: the discrete logarithm is a CHART on "
        "GF(16)*, fifteen points, and a translation orbit leaves it, so the "
        "function now refuses and names the coordinate that would work",
        "tests/test_pond.py::test_the_exponent_chart_refuses_the_rungs_it_does_not_cover",
        False,
    ),
    Correction(
        "QSigma-R1x",
        "R1X reported that its one falsifiable prediction failed because the "
        "protocol left the step budget free. The budget defect is real and the "
        "flip between 300 and 900 is a fact, but the CAUSE was wrong and the "
        "true one is worse. A Gaussian covariance restricted to a mode subset "
        "IS an ellipsoid and the symplectic values ARE its semi-axes; the "
        "prepared state's are (0.044, 0.513, 0.701, 0.983), a genuine "
        "non-degenerate body. The projective herald storm destroys it -- "
        "intermediate-axis count falls 4, 3, 2, 1, 0 and by step 100 only M3 "
        "retains one -- and across R1X's whole sweep 81 of 84 semi-axes sit "
        "exactly at 0 or 1. A measure on {0,1} has ONE degree of freedom, so "
        "the measure could not out-inform the scalar for six of seven cells at "
        "ANY budget. R1X sampled at 300 and 900, long after the object it was "
        "measuring had been flattened, and never checked that the body it named "
        "still had a shape. Found only when an outside reading asked why "
        "ellipsoids had not been considered at all",
        "tests/test_lebesgue.py::test_the_storm_flattens_the_ellipsoid_before_R1X_ever_looked",
        False,
    ),
    Correction(
        "QSigma-R1z",
        "R1Z froze a BOUNDED verdict that no bounded family could reach. The "
        "rule was 'slope < 0.05 AND largest <= 2 * max(smallest, 1e-12)', and "
        "that second clause is a RATIO test on counts: a genuinely bounded "
        "family sits at ZERO for small registers, so smallest is 0, the clause "
        "becomes 'largest <= 2e-12', and it is False for any family with one "
        "nonzero count. Three of five families hit it, TWO OF THEM WITH "
        "NEGATIVE FITTED SLOPES, and were refused. The slope bound is broken "
        "too: one unit of change in an integer count across the frozen grid is "
        "worth about 0.05, so 0.05 IS the resolution of the data and the rule "
        "certifies only an exactly constant sequence. And the observable itself "
        "was the wrong one -- Araki's criterion is about expected particle "
        "number, which needs no precondition, while the frozen zero count needs "
        "full degeneracy that 32 of 105 rows do not have. Fourth consecutive "
        "round decided by its own frozen decision procedure rather than by the "
        "physics: R1S's regions overlapped, R1X left a parameter free, R1Y "
        "amended R1X, and this one made a verdict unreachable. Nothing requires "
        "a frozen criterion to be exercised against a synthetic instance of "
        "each of its verdicts before the round runs. The failed predictions "
        "stand as failed and the criterion is not patched",
        "tests/test_araki.py::test_the_frozen_BOUNDED_verdict_was_unreachable_by_any_bounded_family",
        True,
    ),
    Correction(
        "QSigma-R2a",
        "the recommendation that opened R2A said a criterion check is 'three "
        "lines of test' and 'would have caught R1S, R1X, R1Y and R1Z'. FALSE, "
        "and refuted by the ledger it was summarising. Those are THREE defect "
        "classes: R1S froze verdict regions that OVERLAP, R1Z froze a verdict "
        "that is UNREACHABLE, and R1X left a PARAMETER FREE -- which is not a "
        "property of a verdict function at all, so no amount of exercising one "
        "would surface it. R1Y is not in the class: it amended R1X's causal "
        "diagnosis and froze nothing that failed. Three independent checks for "
        "three independent failure modes, and R1Z demonstrates they are "
        "independent by PASSING the parameter check while being decided by an "
        "unreachable verdict. Bundling distinct defects under one remedy and "
        "costing it at three lines is the aggregation-layer overclaim this "
        "line had audited in an external repository ONE TURN EARLIER -- "
        "attributing to a mechanism numbers it does not produce -- made in a "
        "recommendation about rigour, which is where it is least likely to be "
        "checked",
        "tests/test_criterion.py::test_R1Z_froze_its_knobs_even_though_its_verdict_was_broken",
        True,
    ),
    Correction(
        "QSigma-R2a",
        "criterion.exercise was fail-open: an empty invocation and omitted checks defaulted to clean, uncovered regions were ignored by the composite verdict, predicate exceptions were swallowed, and callers could omit a verdict from the witness map. It now requires an exact required-check declaration, an exact declared-verdict universe, exhaustive samples, and zero predicate errors",
        "tests/test_criterion.py::test_exercise_fails_closed_when_no_checks_are_declared_or_run",
        False,
    ),
    Correction(
        "QSigma-R1y",
        "the finding promoted G3 to PASS only after restricting its domain to blocks no larger than half the register, a constraint absent from the frozen preregistration. The original frozen gate is now preserved as ILL-POSED and the restricted calculation is only a post-freeze semantic control",
        "tests/test_hyperellipsoid.py::test_r1y_finding_preserves_the_failed_frozen_gate_and_correct_theorem",
        False,
    ),
    Correction(
        "QSigma-R1y",
        "the real-Schur skew-normal form of an antisymmetric fermionic covariance was called Williamson's canonical form. Williamson's theorem is a symplectic-congruence theorem for positive-definite symmetric matrices. The computation remains an orthogonal Schur reconstruction; the theorem attribution and geometric promotion were removed",
        "tests/test_hyperellipsoid.py::test_r1y_finding_preserves_the_failed_frozen_gate_and_correct_theorem",
        False,
    ),
    Correction(
        "QSigma-R1z",
        "the frozen preregistration equated bounded-versus-divergent entropy with an area-law-versus-volume-law dichotomy. Divergence may be logarithmic or otherwise sublinear. The historical bytes remain frozen and the finding now records the narrower bounded-versus-divergent statement",
        "tests/test_araki.py::test_r1z_corrects_area_volume_language_without_rewriting_preregistration",
        False,
    ),
    Correction(
        "CI",
        "the main CI workflow used a depth-one checkout even though package import verifies evidence against historical commits. All six jobs failed before tests because the bound commit could not resolve. CI now fetches full history and a regression test binds that requirement",
        "tests/test_criterion.py::test_ci_fetches_the_history_required_by_evidence_bindings",
        False,
    ),
    Correction(
        "CI",
        "the Lean archive census used str(Path) for manifest keys, so Windows emitted backslashes while the committed manifest used canonical forward slashes. Five evidence tests failed although the measured files were identical. Every persisted relative path now uses Path.as_posix and a regression test forbids host-native separators",
        "tests/test_leanmath_vendor.py::test_census_paths_are_canonical_posix_keys",
        False,
    ),
    Correction(
        "CI",
        "the byte-pinned vendored Lean archive inherited text normalization for its extensionless lean-toolchain file. A Windows checkout therefore contained one extra byte and no longer matched the provenance manifest. The entire external archive is now checkout-opaque and a test binds that attribute",
        "tests/test_leanmath_vendor.py::test_vendored_archive_is_checkout_opaque",
        False,
    ),
    Correction(
        "CI",
        "a commit-binding test wrote text through platform newline translation, hashed the working-tree CRLF bytes on Windows, then compared them with Git's normalized LF object. The fixture now writes the exact byte stream whose immutable binding it claims to test",
        "tests/test_evidence.py::test_v2_exact_commit_binding_survives_a_later_head",
        False,
    ),
    Correction(
        "QSigma-R1y",
        "the degenerate-frame witness encoded non-uniqueness as an arbitrary principal-angle threshold above one radian. LAPACK basis choice inside the repeated eigenspace is platform-dependent and macOS produced the same nonzero separation at 0.967 and 0.993 radians. The gate now tests a conservative substantial separation while the refusal on degeneracy remains the semantic invariant",
        "tests/test_hyperellipsoid.py::test_p3_is_ill_posed_because_degeneracy_destroys_the_frame",
        False,
    ),    Correction(
        "R6k-W1-B",
        "the Part B execution blocker named DEPTH_COORDS in common_receiver_"
        "reservoir as THE obstacle to evaluating R6l at held-out depths, and "
        "R6M's fork was framed as 'the identical recipe with a depth grid as "
        "an argument' on that basis. It is one of three. The numerics iterate "
        "DEPTHS in equal_resource_reservoir, a DIFFERENT module the blocker "
        "never mentions, and execute_protocol checks a literal store count of "
        "320 that assumes five depths. At R6l's own grid all three coincide "
        "with their sealed values, so a fork built to the blocker's "
        "description would have PASSED R6M's preregistered equivalence test "
        "and then crashed at the first held-out depth. The preregistered test "
        "is structurally blind to it; a separate wiring control, injecting the "
        "sealed depths in a permuted order, is the only thing that sees it. "
        "Written by this development line on 2026-08-03 and caught by it on "
        "2026-09-25, by tracing where depth reaches the numerics instead of "
        "where it is named",
        "tests/test_common_receiver_parametric.py::test_the_wiring_test_can_fail_on_a_labels_only_fork",
        True,
    ),
    Correction(
        "QSigma-R6m",
        "R6M's pre-run implementation note promised that the fork would "
        "never modify sys.modules. False on the first load: Python 3.11's "
        "dataclass resolves string annotations through "
        "sys.modules[cls.__module__] and raises in an unregistered namespace. "
        "Forks are now registered under private unique names; what survives, "
        "and what mattered, is that no EXISTING entry is replaced and the "
        "sealed modules are untouched by value, identity and registration. "
        "Two more claims in the same round were wrong and never reached a "
        "commit: the note's first draft said no depth constant was read at "
        "import time (an AST check found a default argument that is), and "
        "the kill-condition guard matched the decimal SPELLING, so '0.2' "
        "passed where '0.20' was refused -- with a test comment asserting the "
        "respelling was 'refused for a different reason below'. It was not "
        "refused at all",
        "tests/test_common_receiver_parametric.py::test_building_a_fork_never_touches_the_sealed_modules",
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
# Manifest pointers, which nothing checked until a rename broke one
# --------------------------------------------------------------------------

#: ``executable_form`` values mix pointers with prose, so pointers are extracted
#: rather than parsed: a qualified ``path::name``, or a bare ``::name`` that
#: inherits the last path seen.
_POINTER = re.compile(r"(?:([\w./-]+\.py))?::(test_\w+)")


def _iter_pointers(node, manifest: str):
    """Every ``executable_form`` pointer anywhere in a manifest, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "executable_form":
                for text in ([value] if isinstance(value, str) else
                             value if isinstance(value, list) else []):
                    last = None
                    for path, name in _POINTER.findall(text):
                        last = path or last
                        if last:
                            yield manifest, last, name
            else:
                yield from _iter_pointers(value, manifest)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_pointers(item, manifest)


def manifest_pointers_resolve(root=None) -> dict:
    """Every ``executable_form`` in every manifest must name a test that exists.

    The manifests are where this repository states what it has measured, and
    ``executable_form`` is the field that turns each statement into something a
    reader can run.  **Nothing checked those pointers for sixteen rounds.**  The
    gap surfaced in R1R for the dullest possible reason: a test was renamed
    because its old name asserted a claim R1Q had withdrawn, and the manifest
    that cited it went stale in the same commit.

    That is the same defect this repository keeps finding in its own physics --
    a guard whose witness cannot reach the case it asserts -- except here there
    was no guard at all.  A pointer into nothing fails silently and forever,
    because a manifest is not executed.

    Source-level, like :func:`corrections_are_bound`, and for the same reason: it
    is called from a test, and a test that runs the suite it belongs to either
    recurses or measures nothing.
    """
    root = Path(root) if root is not None else repo_root()
    defined: dict[str, set] = {}
    for path in sorted((root / "tests").rglob("*.py")):
        defined[path.relative_to(root).as_posix()] = set(
            re.findall(r"^def (test_\w+)", path.read_text(encoding="utf-8"), re.M))

    rows = []
    for path in sorted((root / "manifests").glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rows.append({"manifest": path.name, "target": None, "resolves": False,
                         "reason": "unreadable"})
            continue
        for manifest, test_path, test_name in _iter_pointers(document, path.name):
            rows.append({
                "manifest": manifest,
                "target": f"{test_path}::{test_name}",
                "resolves": test_name in defined.get(test_path, ()),
                "reason": ("" if test_path in defined else "no such test file"),
            })

    unresolved = [row for row in rows if not row["resolves"]]
    return {
        "pointers": len(rows),
        "manifests_with_pointers": len({r["manifest"] for r in rows}),
        "resolved": len(rows) - len(unresolved),
        "all_resolve": not unresolved,
        "unresolved": unresolved,
        "rows": rows,
    }


def corrections_name_rounds_that_ran(root=None) -> dict:
    """No correction may be attributed to a round whose manifest says "not run".

    The ledger labels each error with the round that made it, and nothing checked
    that the label named a round of this development line.  R1S's `lean_census`
    retraction was filed under ``QSigma-R1t`` -- colliding with R1T, a frozen
    preregistration on a *different* line whose ``result.observed`` is still "not
    run".  A round that has executed nothing has produced no artifact, so it has
    produced no defect, and attributing one to it puts a false entry in the only
    ledger this repository uses to describe its own reliability.

    Narrow on purpose.  Most labels have no manifest at all, because the older
    rounds predate the manifest convention, so ABSENCE proves nothing and is not
    reported.  The single contradiction available to a mechanical check is a
    manifest that exists and states it has not run.
    """
    root = Path(root) if root is not None else repo_root()
    unrun = {}
    for path in sorted((root / "manifests").glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = document.get("round")
        if isinstance(name, str) and (document.get("result") or {}).get(
                "observed") == "not run":
            unrun[name.upper()] = f"manifests/{path.name}"

    offenders = [{"round": correction.round_id,
                  "manifest": unrun[correction.round_id.upper()]}
                 for correction in CORRECTIONS
                 if correction.round_id.upper() in unrun]
    return {
        "unrun_rounds": unrun,
        "offenders": offenders,
        "clean": not offenders,
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
