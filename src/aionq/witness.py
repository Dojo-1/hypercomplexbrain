"""External witnessing: the half of R4-D this repository could not supply itself.

Round QSigma-R4 built an evidence membrane and then reported, on every single
envelope it wrote, that ``producer == verifier``.  That was the honest state and
also the round's own unclosed gap: hashing your own artifact binds a result to a
command, which is real, but it is not an external witness.

A second party -- here a Godelian-1 workspace agent reachable over HTTP -- can
close it.  What it must not do is close it cosmetically.

The distinction this module exists to enforce
---------------------------------------------
There are two very different things an external agent can do with an envelope,
and collapsing them would rebuild the same failure at higher cost:

``attested``
    The agent read the envelope and agreed with it.  A second signature on the
    producer's own arithmetic.  It adds a party; it adds no computation.  If the
    producer's number is wrong, the attestation is wrong in the same way.
    **This does not make an envelope independent.**

``recomputed``
    The agent ran the recorded command in its own environment and produced its
    own artifact digest.  Now there are two computations, and they can disagree.
    Independent *iff* the digests match -- and far more interesting if they do
    not, which is why ``contradicted`` is a first-class outcome rather than an
    error to be retried away.

``reviewed``
    The agent examined the ARGUMENT rather than re-running the command, and
    returned findings about it.  This is a third axis, added after the first live
    handshake and not present in the original design.  A critic can establish
    that a claim is suggestive but unproven, or evocative but underspecified,
    which no amount of digest-matching detects -- and it can do so without ever
    reproducing a number.  It is genuinely more than ``attested``, because it can
    DISAGREE while the arithmetic is right.  It is not ``recomputed``, because it
    produces no second computation.  It does not set ``independent``.

``contradicted``
    The agent recomputed and got something else.  This is the outcome worth
    having a membrane for.  It does not fail silently and it does not average
    with the producer's result; it fails the envelope and names both digests.

Only ``recomputed`` with a matching digest sets ``independent``.  An agent that
merely says yes is recorded as having said yes.

Credentials
-----------
The token is read from the environment and never written to disk, never placed
in an envelope, and never echoed in an error message.  An envelope is a
committed artifact; a bearer token in one would be a credential leak dressed as
provenance.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .evidence import (EvidenceEnvelope, VerificationResult, file_digest,
                       load_envelope, save_envelope, verify)

__all__ = ["WitnessRequest", "WitnessResponse", "WitnessError", "VerificationMode",
           "GODELIAN_1_ENDPOINT", "build_request", "request_witness",
           "apply_witness", "witness_envelope"]

GODELIAN_1_ENDPOINT = (
    "https://api.chatgpt.com/v1/workspace_agents/"
    "agtch_6a66ff08ace481918db751444d4f7078/trigger"
)

TOKEN_ENV_VARS = ("GODELIAN_AGENT_TOKEN", "AGENT_ACCESS_TOKEN")


class VerificationMode:
    """What the external party actually did.  Not what it claimed to conclude."""

    ATTESTED = "attested"           # agreed with the producer's own numbers
    REVIEWED = "reviewed"           # examined the argument, returned findings
    RECOMPUTED = "recomputed"       # ran the command and produced its own digest
    CONTRADICTED = "contradicted"   # ran it and got something else
    DECLINED = "declined"           # could not or would not
    PENDING = "pending"             # run accepted, verdict not yet available
    NOT_REQUESTED = "not_requested"

    #: The only mode that can make an envelope independent.
    #:
    #: ``REVIEWED`` is deliberately absent.  Argument-independence and
    #: arithmetic-independence are different axes and collapsing them would let a
    #: well-argued wrong number climb the evidence lattice.
    INDEPENDENT_MODES = frozenset({RECOMPUTED})


class WitnessError(RuntimeError):
    """Raised for transport and protocol failures.  Never carries the token."""


@dataclass
class WitnessRequest:
    """The challenge sent to the external verifier.

    Deliberately carries the *command* and the artifact *digests*, and not the
    artifact contents.  A verifier handed the answer cannot recompute it; it can
    only agree.  Sending the question and withholding the answer is the whole
    protocol.
    """

    claim_id: str
    command: str
    commit_sha: str
    expected_artifacts: dict           # path -> digest the producer observed
    observed_result: dict
    repository: str = "jesusvilela/hypercomplexbrain"
    #: How the verifier is expected to OBTAIN the code.  The first live challenge
    #: omitted this and instructed a verifier to "run the command in a clean
    #: checkout" while supplying no clone URL and assuming outbound network.
    #: Godelian-1 spent 2m55s discovering that its container blocks GitHub with
    #: CONNECT 403.  A challenge that cannot be executed is not a challenge, and
    #: the wasted attempt was the protocol's fault, not the verifier's.
    source: dict = field(default_factory=dict)
    protocol_version: str = "hypercomplexbrain.witness.v2"

    def to_prompt(self) -> str:
        return json.dumps({
            "protocol": self.protocol_version,
            "role": "independent verifier",
            "repository": self.repository,
            "commit_sha": self.commit_sha,
            "claim_id": self.claim_id,
            "instruction": (
                "Run the command below in a clean checkout of the stated commit. "
                "Report the SHA-256 of each artifact you produce. Do NOT copy the "
                "digests given under expected_artifacts -- they are supplied so "
                "you can report agreement or disagreement, not so you can echo "
                "them. If you cannot run the command, answer with mode "
                "'declined' and say why. Answering 'attested' means you read the "
                "numbers and agree without having run anything; that is an "
                "acceptable answer and it will be recorded as non-independent."),
            "command": self.command,
            "source": self.source or {
                "note": "NO SOURCE SUPPLIED. If you cannot obtain the code, "
                        "answer 'declined' immediately rather than searching -- "
                        "that is a defect in this challenge, not in you."},
            "requires": ["outbound network to the source", "python3", "numpy"],
            "expected_artifacts": self.expected_artifacts,
            "producer_observed_result": self.observed_result,
            "reply_schema": {
                "mode": "recomputed | reviewed | attested | declined",
                "artifacts": {"<path>": "sha256:<hex>"},
                "observed_result": "<object, if recomputed>",
                "environment": "<free-form description of where it ran>",
                "notes": "<string>",
            },
        }, indent=2, sort_keys=True)


@dataclass
class WitnessResponse:
    """What came back, parsed but not yet believed."""

    mode: str
    conversation_url: str = ""
    artifacts: dict = field(default_factory=dict)
    observed_result: dict = field(default_factory=dict)
    environment: str = ""
    notes: str = ""
    verifier_identity: str = "godelian-1"
    raw: dict = field(default_factory=dict)


# --------------------------------------------------------------------------

def build_request(envelope: EvidenceEnvelope, repository: str | None = None,
                  source: dict | None = None) -> WitnessRequest:
    kwargs = {}
    if repository:
        kwargs["repository"] = repository
    if source:
        kwargs["source"] = source
    return WitnessRequest(
        claim_id=envelope.claim_id,
        command=envelope.command,
        commit_sha=envelope.commit_sha,
        expected_artifacts=dict(envelope.raw_artifacts),
        observed_result=dict(envelope.observed_result),
        **kwargs)


def _token() -> str:
    for name in TOKEN_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise WitnessError(
        "no agent token in the environment. Set one of "
        f"{', '.join(TOKEN_ENV_VARS)} for this shell only -- do NOT add it to a "
        "file in the repository, and do not pass it on a command line that a "
        "shell history will keep.")


def request_witness(request: WitnessRequest, endpoint: str = GODELIAN_1_ENDPOINT,
                    timeout: float = 300.0, transport=None) -> WitnessResponse:
    """POST the challenge and parse the reply.

    ``transport`` exists so the protocol can be tested without a live agent and
    without a credential; it takes ``(endpoint, payload_bytes, headers)`` and
    returns the decoded response body.
    """
    payload = json.dumps({"input": request.to_prompt()}).encode()

    if transport is not None:
        body = transport(endpoint, payload, {"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(
            endpoint, data=payload, method="POST",
            headers={"Authorization": f"Bearer {_token()}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode()
        except urllib.error.HTTPError as exc:
            # The token is in the request headers; the message must not repeat it.
            raise WitnessError(
                f"witness endpoint returned HTTP {exc.code}. "
                "401 means the token is missing, expired or lacks workspace "
                "admin scope.") from None
        except urllib.error.URLError as exc:
            raise WitnessError(f"witness endpoint unreachable: {exc.reason}") from None

    return parse_response(body)


def parse_response(body) -> WitnessResponse:
    """Parse a reply, treating anything unrecognised as ``declined``.

    A verifier whose answer cannot be read has not verified anything.  Guessing
    at its intent would put the producer back in charge of the verdict, which is
    the arrangement this module exists to break.
    """
    data = body if isinstance(body, dict) else json.loads(body)

    # The live endpoint is ASYNCHRONOUS.  Measured against Godelian-1: the
    # trigger returns HTTP 202 with a body of exactly
    #
    #     {"conversation_url": "https://chatgpt.com/c/<id>"}
    #
    # and no verdict.  The first version of this parser saw no "mode" key and
    # returned DECLINED, which is the safe reading -- an unreadable answer is not
    # a verification -- but it is the WRONG one: the run was accepted and is
    # still going.  Recording it as declined would blame the verifier for the
    # protocol's own latency.  PENDING says what actually happened, carries the
    # handle needed to collect the verdict, and is not independent.
    if "conversation_url" in data and "mode" not in data:
        return WitnessResponse(mode=VerificationMode.PENDING,
                               conversation_url=str(data["conversation_url"]),
                               notes="trigger accepted; verdict not yet returned",
                               raw=data)

    inner = data
    for key in ("output", "result", "response", "content"):
        if isinstance(inner.get(key), (dict, str)):
            candidate = inner[key]
            if isinstance(candidate, str):
                try:
                    candidate = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
            inner = candidate
            break

    mode = str(inner.get("mode", VerificationMode.DECLINED)).lower()
    if mode not in {VerificationMode.RECOMPUTED, VerificationMode.ATTESTED,
                    VerificationMode.REVIEWED, VerificationMode.DECLINED}:
        mode = VerificationMode.DECLINED
    return WitnessResponse(
        mode=mode,
        conversation_url=str(data.get("conversation_url", "")),
        artifacts=dict(inner.get("artifacts") or {}),
        observed_result=dict(inner.get("observed_result") or {}),
        environment=str(inner.get("environment", "")),
        notes=str(inner.get("notes", "")),
        verifier_identity=str(inner.get("verifier", "godelian-1")),
        raw=data if isinstance(data, dict) else {})


def apply_witness(envelope: EvidenceEnvelope, response: WitnessResponse
                  ) -> tuple[EvidenceEnvelope, VerificationResult]:
    """Record what the witness did, then re-verify.

    Digest comparison happens HERE, on the producer's side, against the digests
    the producer already recorded.  The verifier does not get to declare its own
    result matching; it reports digests and this function compares them.
    """
    mode = response.mode

    if mode == VerificationMode.RECOMPUTED:
        mismatches = []
        for path, declared in envelope.raw_artifacts.items():
            theirs = response.artifacts.get(path)
            if theirs is None:
                mismatches.append(f"{path}: verifier reported no digest")
            elif theirs != declared:
                mismatches.append(
                    f"{path}: producer {declared[:19]}... vs verifier "
                    f"{theirs[:19]}...")
        if mismatches:
            mode = VerificationMode.CONTRADICTED
            envelope.typed_remainders.append({
                "kind": "empirical_residual",
                "carrier": f"{envelope.claim_id} artifact digests",
                "comparison": "independent recomputation disagreed: "
                              + "; ".join(mismatches)})

    envelope.verification_mode = mode
    envelope.verifier = (response.verifier_identity
                         if mode in (VerificationMode.RECOMPUTED,
                                     VerificationMode.ATTESTED,
                                     VerificationMode.REVIEWED,
                                     VerificationMode.CONTRADICTED) else "")
    if response.conversation_url:
        envelope.witness_conversation_url = response.conversation_url
    envelope.witness_environment = response.environment
    envelope.witness_notes = response.notes
    return envelope, verify(envelope)


def witness_envelope(path, endpoint: str = GODELIAN_1_ENDPOINT, transport=None):
    """Load an envelope, get it witnessed, write it back, return the verdict."""
    path = Path(path)
    envelope = load_envelope(path)
    if not isinstance(envelope, EvidenceEnvelope):
        raise WitnessError(f"{path} is not an EvidenceEnvelope")
    response = request_witness(build_request(envelope), endpoint=endpoint,
                               transport=transport)
    envelope, result = apply_witness(envelope, response)
    save_envelope(envelope, path)
    return envelope, result


def main(argv=None) -> int:  # pragma: no cover - CLI
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        print(f"usage: python -m aionq.witness <envelope.json> [...]\n"
              f"token from: {' or '.join(TOKEN_ENV_VARS)}")
        return 2
    failed = 0
    for target in args:
        try:
            envelope, result = witness_envelope(target)
        except WitnessError as exc:
            print(f"FAIL {target}: {exc}")
            failed += 1
            continue
        print(f"{'ok  ' if result.ok else 'FAIL'} {target}  "
              f"mode={envelope.verification_mode}  "
              f"independent={result.independent}")
        for f in result.failures:
            print(f"       FAIL  {f}")
        for w in result.warnings:
            print(f"       warn  {w}")
        failed += not result.ok
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
