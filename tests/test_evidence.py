"""QSigma-R4: the preregistered attacks on the witness membrane.

Each test below is one row of ``manifests/qsigma_r4_preregistration.json``. They
are written to FAIL if the membrane is ceremonial -- a layer that only restates
what the registry already said would pass none of them.
"""

from __future__ import annotations

import json
import sys

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Instruction

sys.path.insert(0, "src")

from aionq.evidence import (EvidenceEnvelope, ProofEnvelope, effective_sample_size,
                            file_digest, save_envelope, verify)
from aionq.governance import EvidenceTag, GovernanceError, Registry, Claim
from aionq.residency import (PathStatus, TransitionClass, classify_instruction,
                             simulation_residency)


# --------------------------------------------------------------------------
# R4-A: an invalid path may never lower the bound
# --------------------------------------------------------------------------

def _base_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(4)
    qc.h(0); qc.t(1); qc.ccx(0, 1, 2); qc.t(3); qc.cx(2, 3)
    return qc


def test_an_opaque_instruction_cannot_lower_the_simulation_bound():
    """The R4-A kill condition, stated as its negation."""
    base = simulation_residency(_base_circuit())
    attacked = _base_circuit()
    attacked.append(Instruction("blackbox", 2, 0, []), [0, 1])
    after = simulation_residency(attacked)
    assert after.q_sim_upper >= base.q_sim_upper
    assert TransitionClass.OPAQUE in after.class_counts


def test_a_path_that_cannot_price_an_instruction_is_excluded_by_name():
    attacked = _base_circuit()
    attacked.append(Instruction("blackbox", 2, 0, []), [0, 1])
    report = simulation_residency(attacked)
    assert report.portfolio_status                       # every level accounted for
    assert all(v != PathStatus.VALID for v in report.portfolio_status.values())
    assert not report.portfolio, "an excluded path must not carry a T-count"


def test_an_instruction_with_no_declared_width_is_unpriceable_not_cheap():
    """The old code charged an unknown-width operation as ONE qubit.

    That is an under-charge, and an under-charge in this metric is an
    understated simulation cost, i.e. an overstated quantum advantage.
    """
    class Widthless:
        name = "widthless"

    cls, cost = classify_instruction(Widthless())
    assert cls == TransitionClass.UNPRICEABLE
    assert cost == float("inf")


def test_no_valid_path_falls_back_to_the_direct_walk_and_says_so():
    attacked = _base_circuit()
    attacked.append(Instruction("blackbox", 2, 0, []), [0, 1])
    report = simulation_residency(attacked)
    assert any("no valid compiler path survived" in n for n in report.notes)
    assert report.q_sim_upper_known, "the direct walk still prices every instruction"


# --------------------------------------------------------------------------
# R4-B: cache correctness is a counting question, not a timing one
# --------------------------------------------------------------------------

def test_the_quaternion_basis_is_built_once_and_then_reused():
    from aionq import sheaf as S
    saved = S._QUATERNION_BASIS
    try:
        S.reset_quaternion_basis()
        first = S._quaternion_basis()
        assert S.quaternion_basis_builds() == 1
        for _ in range(5):
            again = S._quaternion_basis()
            assert again is first                        # the same object, not a copy
        assert S.quaternion_basis_builds() == 1
    finally:
        S._QUATERNION_BASIS = saved                      # global state restored


# --------------------------------------------------------------------------
# R4-D: the membrane
# --------------------------------------------------------------------------

@pytest.fixture()
def artifact(tmp_path):
    p = tmp_path / "raw.json"
    p.write_text(json.dumps({"auroc": 0.91}))
    return p


def _envelope(artifact, **kw) -> EvidenceEnvelope:
    base = dict(
        claim_id="TEST-R4-EXAMPLE", evidence_tag="M",
        command="python3 experiments/run_example.py",
        observed_result={"sample_size": 3, "auroc": 0.91},
        seeds=[1, 2, 3], input_hashes=["a", "b", "c"],
        raw_artifacts={str(artifact): file_digest(artifact)},
        producer="runner", verifier="reviewer")
    base.update(kw)
    return EvidenceEnvelope(**base)


def test_a_well_formed_envelope_verifies(artifact):
    assert verify(_envelope(artifact), check_commit=False).ok


def test_a_corrupted_artifact_fails_verification(artifact):
    env = _envelope(artifact)
    artifact.write_text(json.dumps({"auroc": 0.99}))     # the result, improved
    result = verify(env, check_commit=False)
    assert not result.ok
    assert any("digest mismatch" in f for f in result.failures)


def test_a_missing_artifact_fails_verification(artifact):
    env = _envelope(artifact)
    artifact.unlink()
    assert not verify(env, check_commit=False).ok


def test_an_envelope_with_no_artifact_at_all_is_refused():
    env = EvidenceEnvelope(claim_id="X-R4-Y", evidence_tag="M",
                           command="run", observed_result={})
    result = verify(env, check_commit=False)
    assert not result.ok
    assert any("Prose copied into JSON" in f for f in result.failures)


def test_seeds_that_do_not_change_the_input_do_not_add_observations(artifact):
    """The borrowed m1-bordon rule.

    Six seeds, one distinct input -- exactly the shape of that repository's
    TRANSFER gate, where a deterministic generator ignored the RNG and six
    identical rows were reported as six observations.
    """
    env = _envelope(artifact, seeds=[1, 7, 42, 99, 313, 1024],
                    input_hashes=["same"] * 6,
                    observed_result={"sample_size": 6, "delta": -0.00219727})
    result = verify(env, check_commit=False)
    assert not result.ok
    assert result.effective_n == 1
    assert any("do not add observations" in f for f in result.failures)


def test_effective_sample_size_refuses_to_guess_when_inputs_are_unrecorded():
    assert effective_sample_size([1, 2, 3], []) == 0


def test_self_verification_is_recorded_as_such(artifact):
    env = _envelope(artifact, producer="me", verifier="me")
    result = verify(env, check_commit=False)
    assert result.ok                                     # still binds a hash
    assert not result.independent
    assert any("not independently witnessed" in w for w in result.warnings)


def test_a_registry_edit_alone_cannot_promote_a_claim():
    """The central R4-D property."""
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS,
                          "a hypothesis awaiting evidence",
                          kill_condition="the effect does not replicate")])
    with pytest.raises(GovernanceError, match="requires an EvidenceEnvelope"):
        reg.promote("TEST-R4-CANDIDATE", EvidenceTag.MEASURED)
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.HYPOTHESIS


def test_promotion_with_a_broken_envelope_is_refused(artifact):
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS, "x",
                          kill_condition="k")])
    env = _envelope(artifact, claim_id="TEST-R4-CANDIDATE")
    artifact.unlink()
    with pytest.raises(GovernanceError, match="promotion refused"):
        reg.promote("TEST-R4-CANDIDATE", EvidenceTag.MEASURED, envelope=env)
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.HYPOTHESIS


def test_promotion_with_a_verified_envelope_succeeds(artifact):
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS, "x",
                          kill_condition="k")])
    reg.promote("TEST-R4-CANDIDATE", EvidenceTag.MEASURED,
                envelope=_envelope(artifact, claim_id="TEST-R4-CANDIDATE"))
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.MEASURED
    assert reg.envelopes("TEST-R4-CANDIDATE")


def test_demotion_never_requires_evidence():
    """Admitting an error must not be gated on producing an artifact."""
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.MEASURED, "x",
                          sample_size=10, interval=(0.1, 0.2), null="chance")])
    reg.promote("TEST-R4-CANDIDATE", EvidenceTag.RETIRED)
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.RETIRED


# --------------------------------------------------------------------------
# R4-F: the historical regression the membrane must reject
# --------------------------------------------------------------------------

def test_the_uncompiled_lean_surface_is_rejected_as_a_proof():
    """`formal/RecognitionChamber.lean` states P1-P5 and has never been compiled.

    No Lean toolchain exists in this environment, which the repository has always
    said. What it did NOT have was a mechanism that refuses to count the file as
    a proof. This is that mechanism, and this is the historical case it rejects.
    """
    env = ProofEnvelope(
        claim_id="FORMAL-S4-RECOGNITION_CHAMBER",
        theorem_name="P1..P5", prover="lean4", prover_version="unknown",
        build_command="lake build", artifact_digest="",
        build_status="not_built", producer="repo", verifier="repo")
    result = verify(env)
    assert not result.ok
    assert any("never compiled" in f for f in result.failures)


def test_a_proof_resting_on_an_axiom_is_flagged_even_when_it_builds():
    """The Wall-Sheaf failure mode, as a check rather than as a memory.

    `theorem P_neq_NP := ambrose_singer_bridge ...` with the bridge declared as
    an axiom compiles cleanly and proves nothing about its conclusion.
    """
    env = ProofEnvelope(
        claim_id="TEST-R4-AXIOM_PROOF", theorem_name="P_neq_NP",
        prover="lean4", prover_version="4.11.0", build_command="lake build",
        artifact_digest="sha256:deadbeef", build_status="built",
        axiom_inventory=["ambrose_singer_bridge"],
        producer="a", verifier="b")
    result = verify(env)
    assert result.ok                                     # it does build
    assert any("proves nothing about the conclusion" in w for w in result.warnings)


def test_the_registry_reports_how_much_of_itself_is_unwitnessed():
    """Not a pass/fail. The number is the honest state of the ledger."""
    from aionq.governance import registry
    gap = registry.unwitnessed()
    assert isinstance(gap, list)
    assert len(gap) > 0, ("if every claim were already witnessed the membrane "
                          "would be measuring nothing")


def test_saved_envelopes_round_trip(tmp_path, artifact):
    from aionq.evidence import load_envelope
    path = save_envelope(_envelope(artifact), tmp_path / "e.json")
    assert verify(load_envelope(path), check_commit=False).ok


# --------------------------------------------------------------------------
# External witnessing (Godelian-1): a second party is necessary, not sufficient
# --------------------------------------------------------------------------

def _reply(payload):
    """A fake transport standing in for the live agent."""
    return lambda endpoint, body, headers: json.dumps(payload)


def test_a_distinct_party_that_only_agrees_is_not_independent(artifact):
    """Attestation adds a signature, not a computation.

    If the producer's number is wrong, an attestation is wrong the same way.
    This is the failure this whole module exists to refuse.
    """
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    env, result = apply_witness(env, parse_response(json.dumps(
        {"mode": "attested", "notes": "looks right"})))
    assert env.verifier == "godelian-1"          # a genuinely different party
    assert env.verification_mode == VerificationMode.ATTESTED
    assert not result.independent                # and still not independent


def test_recomputation_with_matching_digests_is_independent(artifact):
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    reply = {"mode": "recomputed",
             "artifacts": {str(artifact): file_digest(artifact)},
             "environment": "godelian-1 sandbox"}
    env, result = apply_witness(env, parse_response(json.dumps(reply)))
    assert env.verification_mode == VerificationMode.RECOMPUTED
    assert result.ok and result.independent


def test_a_contradicted_recomputation_fails_the_envelope(artifact):
    """The outcome worth having a membrane for.

    The two results are not averaged and the newer one does not win.
    """
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    reply = {"mode": "recomputed",
             "artifacts": {str(artifact): "sha256:" + "0" * 64}}
    env, result = apply_witness(env, parse_response(json.dumps(reply)))
    assert env.verification_mode == VerificationMode.CONTRADICTED
    assert not result.ok
    assert not result.independent
    assert any("not averaged" in f for f in result.failures)
    assert any(r["kind"] == "empirical_residual" for r in env.typed_remainders)


def test_a_verifier_that_reports_no_digest_is_a_contradiction_not_a_pass(artifact):
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    env, result = apply_witness(env, parse_response(
        json.dumps({"mode": "recomputed", "artifacts": {}})))
    assert env.verification_mode == VerificationMode.CONTRADICTED
    assert not result.ok


def test_an_unreadable_reply_is_declined_not_guessed():
    from aionq.witness import VerificationMode, parse_response
    assert parse_response(json.dumps({"blah": 1})).mode == VerificationMode.DECLINED
    assert parse_response(json.dumps({"mode": "verified!"})).mode == \
        VerificationMode.DECLINED


def test_the_challenge_withholds_nothing_but_answers_nothing(artifact):
    """The verifier gets the command and the digests, never the artifact body.

    A verifier handed the answer can only agree.
    """
    from aionq.witness import build_request
    prompt = build_request(_envelope(artifact)).to_prompt()
    assert "python3 experiments/run_example.py" in prompt
    assert "expected_artifacts" in prompt
    assert "auroc" in prompt                     # the producer's claim, for comparison
    assert "Do NOT copy the digests" in prompt


def test_the_token_is_never_placed_in_an_envelope(artifact, monkeypatch):
    from aionq.witness import apply_witness, build_request, parse_response
    monkeypatch.setenv("GODELIAN_AGENT_TOKEN", "sk-secret-value")
    env = _envelope(artifact, producer="me", verifier="")
    env, _ = apply_witness(env, parse_response(json.dumps({"mode": "attested"})))
    assert "sk-secret-value" not in json.dumps(env.to_dict())
    assert "sk-secret-value" not in build_request(env).to_prompt()


def test_a_missing_token_names_the_variable_and_not_a_value(monkeypatch):
    from aionq.witness import WitnessError, build_request, request_witness
    for name in ("GODELIAN_AGENT_TOKEN", "AGENT_ACCESS_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    env = EvidenceEnvelope(claim_id="X-R4-Y", evidence_tag="M", command="run",
                           observed_result={})
    with pytest.raises(WitnessError, match="GODELIAN_AGENT_TOKEN"):
        request_witness(build_request(env))


def test_the_two_definitions_of_independence_agree():
    """`evidence` duplicates the mode set to stay importable without the network."""
    from aionq.evidence import _INDEPENDENT_MODES
    from aionq.witness import VerificationMode
    assert _INDEPENDENT_MODES == VerificationMode.INDEPENDENT_MODES


def test_an_accepted_but_unfinished_run_is_pending_not_declined(artifact):
    """The live endpoint returns 202 with only a conversation_url.

    Reading that as `declined` is safe and wrong: the run was accepted and is
    still going. Blaming the verifier for the protocol's latency would make
    every real handshake look like a refusal.
    """
    from aionq.witness import VerificationMode, apply_witness, parse_response
    reply = parse_response(json.dumps(
        {"conversation_url": "https://chatgpt.com/c/6a670bfc"}))
    assert reply.mode == VerificationMode.PENDING
    env, result = apply_witness(_envelope(artifact, producer="me", verifier=""),
                                reply)
    assert env.verification_mode == VerificationMode.PENDING
    assert env.witness_conversation_url.endswith("6a670bfc")
    assert env.verifier == ""            # nothing has verified anything yet
    assert not result.independent


def test_a_reviewer_is_a_real_verifier_and_still_not_independent(artifact):
    """The third axis, added after the first live handshake.

    Godelian-1 is a critic, not an execution environment. It can establish that
    a claim is suggestive but unproven -- which no digest comparison detects --
    and it can disagree while the arithmetic is right. That is more than
    attestation and it is not recomputation, so it names a verifier and leaves
    `independent` False. Collapsing the two axes would let a well-argued wrong
    number climb the lattice.
    """
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env, result = apply_witness(
        _envelope(artifact, producer="me", verifier=""),
        parse_response(json.dumps({
            "mode": "reviewed",
            "notes": "sample_size 1 is correct but the interval conflates two "
                     "conditions rather than bounding one"})))
    assert env.verification_mode == VerificationMode.REVIEWED
    assert env.verifier == "godelian-1"
    assert not result.independent
    assert VerificationMode.REVIEWED not in VerificationMode.INDEPENDENT_MODES


def test_a_challenge_without_a_source_says_so_instead_of_implying_one(artifact):
    """The defect the first live handshake exposed, as a check.

    The v1 challenge told a verifier to run a command "in a clean checkout" and
    supplied no clone URL. Godelian-1 spent 2m55s discovering its container
    blocks GitHub. That was the protocol's fault.
    """
    from aionq.witness import build_request
    prompt = build_request(_envelope(artifact)).to_prompt()
    assert "NO SOURCE SUPPLIED" in prompt
    assert "answer 'declined' immediately" in prompt
    assert "requires" in prompt

    supplied = build_request(_envelope(artifact),
                             source={"clone": "https://example.invalid/r.git"})
    assert "NO SOURCE SUPPLIED" not in supplied.to_prompt()
