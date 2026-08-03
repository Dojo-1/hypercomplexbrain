"""QSigma-R4: the preregistered attacks on the witness membrane.

Each test below is one row of ``manifests/qsigma_r4_preregistration.json``. They
are written to FAIL if the membrane is ceremonial -- a layer that only restates
what the registry already said would pass none of them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Instruction

sys.path.insert(0, "src")

from aionq.evidence import (SCHEMA_VERSION, EvidenceEnvelope, ProofEnvelope,
                            effective_sample_size, file_digest, save_envelope,
                            verify)
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
        schema_version=SCHEMA_VERSION,
        seeds=[1, 2, 3], input_hashes=["a", "b", "c"],
        raw_artifacts={str(artifact): file_digest(artifact)},
        computed_artifacts=[str(artifact)],
        producer="runner", verifier="reviewer")
    base.update(kw)
    return EvidenceEnvelope(**base)


def _git(root, *args) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _init_git(root) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "evidence-v2@example.invalid")
    _git(root, "config", "user.name", "Evidence V2 Test")


def _commit_all(root, message: str) -> str:
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _strict_envelope(relative: str, artifact, commit: str, **kw):
    base = dict(
        claim_id="TEST-EVIDENCE-V2-COMMIT",
        evidence_tag="M",
        command="python deterministic.py",
        observed_result={"sample_size": 1},
        schema_version=SCHEMA_VERSION,
        artifact_commit_sha=commit,
        commit_sha=commit,
        raw_artifacts={relative: file_digest(artifact)},
        input_hashes=["input:one"],
        producer="producer-a",
        verifier="",
    )
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


def test_commit_bound_history_survives_a_later_worktree_edit(
    artifact,
    monkeypatch,
):
    import aionq.evidence as evidence_module

    env = _envelope(artifact, commit_sha="abcdef1")
    committed_digest = next(iter(env.raw_artifacts.values()))
    artifact.write_text(json.dumps({"auroc": 0.99}))
    monkeypatch.setattr(
        evidence_module,
        "_committed_file_digest",
        lambda _path, _commit, _root: committed_digest,
    )
    result = verify(env, check_commit=False)
    assert result.ok
    assert any("recorded commit" in warning for warning in result.warnings)


def test_v2_exact_commit_binding_survives_a_later_head(tmp_path):
    _init_git(tmp_path)
    artifact = tmp_path / "raw.json"
    artifact.write_text('{"value":1}\n', encoding="utf-8")
    artifact_commit = _commit_all(tmp_path, "raw artifact")
    (tmp_path / "later.txt").write_text("later\n", encoding="utf-8")
    _commit_all(tmp_path, "later head")

    result = verify(
        _strict_envelope("raw.json", artifact, artifact_commit),
        repo_root=tmp_path,
        check_commit=True,
    )
    assert result.ok
    assert any("immutable artifact binding" in warning for warning in result.warnings)


def test_v2_live_match_cannot_mask_artifact_absent_at_commit(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "before.txt").write_text("before\n", encoding="utf-8")
    before_artifact = _commit_all(tmp_path, "before artifact")
    artifact = tmp_path / "raw.json"
    artifact.write_text('{"value":1}\n', encoding="utf-8")

    result = verify(
        _strict_envelope("raw.json", artifact, before_artifact),
        repo_root=tmp_path,
        check_commit=True,
    )
    assert not result.ok
    assert any("absent at recorded commit" in failure for failure in result.failures)


def test_v2_live_forgery_cannot_mask_a_different_committed_blob(tmp_path):
    _init_git(tmp_path)
    artifact = tmp_path / "raw.json"
    artifact.write_text('{"value":1}\n', encoding="utf-8")
    artifact_commit = _commit_all(tmp_path, "original artifact")
    artifact.write_text('{"value":999}\n', encoding="utf-8")

    result = verify(
        _strict_envelope("raw.json", artifact, artifact_commit),
        repo_root=tmp_path,
        check_commit=True,
    )
    assert not result.ok
    assert any("committed artifact digest mismatch" in failure
               for failure in result.failures)


def test_v2_check_commit_requires_a_full_resolvable_sha(tmp_path):
    artifact = tmp_path / "raw.json"
    artifact.write_text('{"value":1}\n', encoding="utf-8")
    result = verify(
        _strict_envelope("raw.json", artifact, ""),
        repo_root=tmp_path,
        check_commit=True,
    )
    assert not result.ok
    assert any("exactly 40 lowercase" in failure for failure in result.failures)


def test_v2_commit_bound_paths_cannot_escape_the_repository(tmp_path):
    _init_git(tmp_path)
    inside = tmp_path / "inside.json"
    inside.write_text('{"value":1}\n', encoding="utf-8")
    commit = _commit_all(tmp_path, "inside")
    env = _strict_envelope("../inside.json", inside, commit)
    result = verify(env, repo_root=tmp_path, check_commit=True)
    assert not result.ok
    assert any("escapes repository" in failure for failure in result.failures)


def test_zero_envelope_corpus_is_a_failure(tmp_path, capsys):
    from aionq.verify_envelopes import main

    empty = tmp_path / "artifacts"
    empty.mkdir()
    assert main([str(empty)]) == 1
    assert "denominator is zero" in capsys.readouterr().out


def test_evidence_catalog_detects_missing_and_extra_paths(tmp_path):
    from aionq.verify_envelopes import _catalog_failures

    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "schema": "hypercomplexbrain.evidence_catalog.v1",
        "root": "artifacts",
        "envelopes": [
            {"path": "artifacts/expected.envelope.json", "claim_id": "EXPECTED"}
        ],
    }), encoding="utf-8")
    failures = _catalog_failures(
        [Path("artifacts/unexpected.envelope.json")], catalog
    )
    assert any("missing" in failure for failure in failures)
    assert any("uncatalogued" in failure for failure in failures)


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


def test_v2_positive_sample_size_requires_recorded_inputs(artifact):
    env = _envelope(
        artifact,
        seeds=[1, 2, 3],
        input_hashes=[],
        observed_result={"sample_size": 3},
    )
    result = verify(env, check_commit=False)
    assert not result.ok
    assert any("records no distinct input hashes" in failure
               for failure in result.failures)


def test_v2_malformed_sample_size_fails_without_raising(artifact):
    env = _envelope(
        artifact,
        seeds=[1],
        input_hashes=["sha256:" + "1" * 64],
        observed_result={"sample_size": "1"},
    )
    result = verify(env, check_commit=False)
    assert not result.ok
    assert any("sample_size must be a nonnegative integer" in failure
               for failure in result.failures)


def test_v2_malformed_artifact_collections_fail_closed(artifact):
    env = _envelope(
        artifact,
        producer="producer-a",
        verifier="verifier-b",
        verification_mode="recomputed",
    )
    env.raw_artifacts = []
    env.computed_artifacts = {str(artifact): file_digest(artifact)}
    result = verify(env, check_commit=False)
    assert not result.ok
    assert not env.independent
    assert any("raw_artifacts must be a JSON object" in failure
               for failure in result.failures)
    assert any("computed_artifacts must be a list" in failure
               for failure in result.failures)


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
    _init_git(artifact.parent)
    artifact_commit = _commit_all(artifact.parent, "measured artifact")
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS, "x",
                          kill_condition="k", sample_size=3,
                          interval=(0.8, 1.0), null="chance")])
    reg.promote("TEST-R4-CANDIDATE", EvidenceTag.MEASURED,
                envelope=_strict_envelope(
                    "raw.json", artifact, artifact_commit,
                    claim_id="TEST-R4-CANDIDATE",
                    observed_result={"sample_size": 3, "auroc": 0.91},
                    input_hashes=["a", "b", "c"],
                ),
                repo_root=artifact.parent)
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.MEASURED
    assert reg.envelopes("TEST-R4-CANDIDATE")


def test_verified_envelope_cannot_bypass_destination_tag_invariants(artifact):
    _init_git(artifact.parent)
    artifact_commit = _commit_all(artifact.parent, "measured artifact")
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS, "x",
                          kill_condition="k")])
    envelope = _strict_envelope(
        "raw.json", artifact, artifact_commit,
        claim_id="TEST-R4-CANDIDATE",
        observed_result={"sample_size": 1},
    )
    with pytest.raises(GovernanceError, match="destination tag M"):
        reg.promote(
            "TEST-R4-CANDIDATE",
            EvidenceTag.MEASURED,
            envelope=envelope,
            repo_root=artifact.parent,
        )
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.HYPOTHESIS


@pytest.mark.parametrize(
    "binding",
    [
        {"claim_id": "TEST-R4-OTHER"},
        {"evidence_tag": EvidenceTag.AXIOMATIZED},
    ],
)
def test_envelope_binding_must_match_promoted_claim_and_tag(artifact, binding):
    reg = Registry([Claim("TEST-R4-CANDIDATE", EvidenceTag.HYPOTHESIS, "x",
                          kill_condition="k", sample_size=3,
                          interval=(0.8, 1.0), null="chance")])
    envelope_fields = {"claim_id": "TEST-R4-CANDIDATE"}
    envelope_fields.update(binding)
    envelope = _envelope(artifact, **envelope_fields)
    with pytest.raises(GovernanceError, match="envelope binding"):
        reg.promote(
            "TEST-R4-CANDIDATE",
            EvidenceTag.MEASURED,
            envelope=envelope,
        )
    assert reg["TEST-R4-CANDIDATE"].tag == EvidenceTag.HYPOTHESIS
    assert not reg.envelopes("TEST-R4-CANDIDATE")


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


def test_a_proof_resting_on_an_axiom_is_flagged_even_when_it_builds(tmp_path):
    """The Wall-Sheaf failure mode, as a check rather than as a memory.

    `theorem P_neq_NP := ambrose_singer_bridge ...` with the bridge declared as
    an axiom compiles cleanly and proves nothing about its conclusion.
    """
    # Every binding field is well formed on purpose. The point of the test is
    # that an envelope with NOTHING else wrong with it -- real path, canonical
    # digest, real commit, clean build -- is still not a proof of its own
    # conclusion when the conclusion is assumed. If the fixture were malformed
    # the axiom warning could hide behind an unrelated failure, and the test
    # would pass for the wrong reason.
    olean = tmp_path / "formal" / "PvsNP.olean"
    olean.parent.mkdir(parents=True)
    olean.write_bytes(b"compiled cleanly, assumes its conclusion")
    env = ProofEnvelope(
        claim_id="TEST-R4-AXIOM_PROOF", theorem_name="P_neq_NP",
        prover="lean4", prover_version="4.11.0", build_command="lake build",
        artifact_path="formal/PvsNP.olean",
        artifact_digest=file_digest(olean),
        artifact_commit_sha="0" * 40,
        build_status="built",
        axiom_inventory=["ambrose_singer_bridge"],
        producer="a", verifier="b")
    result = verify(env, repo_root=tmp_path, check_commit=False)
    assert result.ok, result.failures                    # it does build
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
        {"mode": "attested", "verifier": "godelian-1",
         "notes": "looks right"})))
    assert env.verifier == "godelian-1"          # a genuinely different party
    assert env.verification_mode == VerificationMode.ATTESTED
    assert not result.independent                # and still not independent


def test_recomputation_with_matching_digests_is_independent(artifact):
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    reply = {"mode": "recomputed",
             "verifier": "godelian-1",
             "artifacts": {str(artifact): file_digest(artifact)},
             "environment": "godelian-1 sandbox"}
    env, result = apply_witness(env, parse_response(json.dumps(reply)))
    assert env.verification_mode == VerificationMode.RECOMPUTED
    assert result.ok and result.independent


def test_a_script_path_is_not_an_independent_party_identity(artifact):
    from aionq.witness import VerificationMode

    env = _envelope(
        artifact,
        producer="experiments/run_equal_resource_reservoir.py",
        verifier="claude-code-linux",
        verification_mode=VerificationMode.RECOMPUTED,
    )
    result = verify(env, check_commit=False)
    assert not env.independent
    assert not result.independent


def test_proof_independence_also_requires_identified_parties():
    script_producer = ProofEnvelope(
        claim_id="P-V2-X",
        theorem_name="x",
        prover="Lean",
        prover_version="4",
        build_command="lake build",
        artifact_digest="sha256:" + "0" * 64,
        producer="proofs/build.py",
        verifier="external-party",
        build_status="built",
    )
    assert not script_producer.independent


def test_recomputation_without_a_declared_computed_output_is_review_only(artifact):
    from aionq.witness import VerificationMode, apply_witness, parse_response

    env = _envelope(
        artifact,
        producer="producer-a",
        verifier="",
        computed_artifacts=[],
    )
    response = parse_response(json.dumps({
        "mode": "recomputed",
        "verifier": "verifier-b",
        "artifacts": {str(artifact): file_digest(artifact)},
    }))
    env, result = apply_witness(env, response)
    assert env.verification_mode == VerificationMode.REVIEWED
    assert not result.independent
    assert "no declared computed output" in env.witness_notes


def test_a_response_without_a_party_identity_cannot_be_independent(artifact):
    from aionq.witness import apply_witness, parse_response

    env = _envelope(artifact, producer="producer-a", verifier="")
    response = parse_response(json.dumps({
        "mode": "recomputed",
        "artifacts": {str(artifact): file_digest(artifact)},
    }))
    env, result = apply_witness(env, response)
    assert env.verifier == ""
    assert not result.independent


def test_a_contradicted_recomputation_fails_the_envelope(artifact):
    """The outcome worth having a membrane for.

    The two results are not averaged and the newer one does not win.
    """
    from aionq.witness import VerificationMode, apply_witness, parse_response
    env = _envelope(artifact, producer="me", verifier="")
    reply = {"mode": "recomputed",
             "verifier": "godelian-1",
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
        json.dumps({"mode": "recomputed", "verifier": "godelian-1",
                    "artifacts": {}})))
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
    assert "artifact_paths" in prompt
    assert file_digest(artifact) not in prompt
    assert "auroc" not in prompt                  # producer's answer is withheld
    assert "withheld until after your response" in prompt


def test_the_token_is_never_placed_in_an_envelope(artifact, monkeypatch):
    from aionq.witness import apply_witness, build_request, parse_response
    monkeypatch.setenv("GODELIAN_AGENT_TOKEN", "sk-secret-value")
    env = _envelope(artifact, producer="me", verifier="")
    env, _ = apply_witness(env, parse_response(json.dumps(
        {"mode": "attested", "verifier": "godelian-1"})))
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
            "verifier": "godelian-1",
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


# --------------------------------------------------------------------------
# The witness relation as a nerve: evidence is a graph property
# --------------------------------------------------------------------------

def _wg(*acts):
    from aionq.witness_nerve import WitnessAct, WitnessGraph
    return WitnessGraph([WitnessAct(*a) for a in acts])


def test_an_attestation_cycle_cannot_manufacture_independence():
    """The theorem, in the form that survived its own test.

    A attests to B, B to C, C to A. Every `producer != verifier` check passes,
    every party is verified by someone else, and nobody computed anything. The
    rank is capped at ATTESTED however large the ring gets.

    The first version of this test asserted the STRONGER claim that removing the
    cycle leaves the rank unchanged -- that attestation cycles are inert. It
    failed immediately (`assert 0 == 1`): when the ring is the only support,
    removing it drops ATTESTED to NONE. An attestation is not nothing; it is
    bounded. The theorem was corrected, not the test.
    """
    from aionq.witness_nerve import EvidenceRank, attestation_cycles, evidence_rank
    ring = _wg(("K-R4-X", "A", "B", "attested"),
               ("K-R4-X", "B", "C", "attested"),
               ("K-R4-X", "C", "A", "attested"))
    assert len(attestation_cycles(ring)) >= 1
    assert evidence_rank(ring, "K-R4-X") == EvidenceRank.ATTESTED
    assert evidence_rank(ring, "K-R4-X") < EvidenceRank.INDEPENDENT

    # max(existing, ATTESTED): a ring cannot lift a reviewed claim either.
    reviewed = _wg(("K-R4-Y", "A", "R", "reviewed"))
    assert evidence_rank(reviewed, "K-R4-Y") == EvidenceRank.REVIEWED
    for act in ring.acts:
        from aionq.witness_nerve import WitnessAct
        reviewed.add(WitnessAct("K-R4-Y", act.producer, act.verifier, act.mode))
    assert evidence_rank(reviewed, "K-R4-Y") == EvidenceRank.REVIEWED


def test_adding_parties_to_a_ring_never_raises_the_rank():
    """Evidence must be orbit-collapsed under inserting attestation cycles."""
    from aionq.witness_nerve import WitnessAct, evidence_rank
    ring = _wg(("K-R4-X", "A", "B", "attested"), ("K-R4-X", "B", "A", "attested"))
    before = evidence_rank(ring, "K-R4-X")
    for extra in "CDEFGH":
        ring.add(WitnessAct("K-R4-X", extra, "A", "attested"))
        ring.add(WitnessAct("K-R4-X", "A", extra, "attested"))
        assert evidence_rank(ring, "K-R4-X") == before


def test_one_recomputation_outranks_any_number_of_attestations():
    from aionq.witness_nerve import WitnessAct, EvidenceRank, evidence_rank, is_independent
    g = _wg(*[("K-R4-X", "A", f"P{i}", "attested") for i in range(20)])
    assert not is_independent(g, "K-R4-X")
    g.add(WitnessAct("K-R4-X", "A", "Z", "recomputed"))
    assert evidence_rank(g, "K-R4-X") == EvidenceRank.INDEPENDENT
    assert is_independent(g, "K-R4-X")


def test_a_self_loop_transmits_nothing_however_it_was_done():
    """R4's producer == verifier rule, restated so that it composes."""
    from aionq.witness_nerve import EvidenceRank, evidence_rank
    g = _wg(("K-R4-X", "A", "A", "recomputed"))
    assert evidence_rank(g, "K-R4-X") == EvidenceRank.NONE


def test_a_contradiction_transmits_no_support_though_it_is_informative():
    from aionq.witness_nerve import EvidenceRank, evidence_rank
    g = _wg(("K-R4-X", "A", "B", "contradicted"))
    assert evidence_rank(g, "K-R4-X") == EvidenceRank.NONE


def test_review_sits_strictly_between_attestation_and_recomputation():
    from aionq.witness_nerve import MODE_RANK
    assert MODE_RANK["attested"] < MODE_RANK["reviewed"] < MODE_RANK["recomputed"]


def test_the_live_witness_graph_is_honest_about_itself():
    """This repository's actual state, computed rather than asserted."""
    from aionq.witness_nerve import EvidenceRank, evidence_rank
    live = _wg(("METRIC-R4-INSTRUMENT_COST",
                "experiments/run_instrument_benchmark.py",
                "godelian-1", "declined"))
    assert evidence_rank(live, "METRIC-R4-INSTRUMENT_COST") == EvidenceRank.NONE
