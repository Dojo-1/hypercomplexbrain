"""EvidenceEnvelope: binding a claim to an artifact it did not write itself.

Round QSigma-R4.  The governance registry in :mod:`aionq.governance` is the
strongest single piece of this repository -- it separates P/A/M/H/S/R, refuses an
M claim without a sample size, an interval and a null, refuses an H claim without
a kill condition, and supersedes rather than overwrites.  Its weakness is
structural and was named by an external audit:

    the registry is the sole source of its own evidence status.

Its tests establish that the hand-authored ledger agrees with itself.  They do
not establish that the cited command ran, that the stored interval came from the
cited artifact, or that the artifact belongs to the cited commit.  An envelope
carries exactly those bindings.

The failure mode this module must avoid
---------------------------------------
An envelope that hashes a file the same process just wrote from the same prose is
self-witnessing with extra steps.  That is the preregistered kill condition for
this round, and it is the one most likely to fire.  Three defences:

1.  ``ARTIFACT`` hashes are recomputed at verification time, not carried in
    memory from whoever produced them.  In v2 the immutable Git blobs are
    checked unconditionally; the working tree is only a secondary copy.
2.  ``producer`` and ``verifier`` are separate fields and
    :meth:`EvidenceEnvelope.independent` is False when they coincide.  An
    envelope that verifies itself is *recorded as such* rather than counted.
3.  Sample size is checked against the DISTINCT input hashes, not against the
    length of the seed list -- see :func:`effective_sample_size` below.

The third rule is borrowed
--------------------------
It comes from a sibling codebase (m1-bordon v0.8.0), where a six-seed audit
ensemble reported ``transferDelta = -0.00219727`` identically at all six seeds.
The generator for that phase was ``e = ((t / block) * 7 + k * 31) % N`` -- purely
deterministic in the loop indices, never consulting the RNG.  Measured there: one
distinct trace across six seeds, while the JSON presented six rows as six
observations.  The ensemble existed precisely because "a single lucky seed could
be mistaken for a stable engineering result", and for that one phase the fix
reported n = 1 six times.

That is an evidence defect, not a C defect, so the correction belongs here: an
envelope declaring six seeds whose inputs hash identically has an effective
sample size of one, and this module says so.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath

__all__ = ["EvidenceEnvelope", "ProofEnvelope", "VerificationResult",
           "file_digest", "environment_digest", "current_commit",
           "effective_sample_size", "party_identity_established",
           "evidence_independence_established", "verify", "load_envelope",
           "save_envelope", "EvidenceTag_REQUIRING_EVIDENCE"]

LEGACY_SCHEMA_VERSION = "hypercomplexbrain.evidence.v1"
SCHEMA_VERSION = "hypercomplexbrain.evidence.v2"
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SCHEMA_VERSION, SCHEMA_VERSION})

#: Duplicated from :class:`aionq.witness.VerificationMode` to keep this module
#: importable without the network layer.  A test asserts the two agree.
_INDEPENDENT_MODES = frozenset({"recomputed"})
_VERIFICATION_MODES = frozenset({
    "not_requested", "pending", "declined", "attested", "reviewed",
    "recomputed", "contradicted",
})


# --------------------------------------------------------------------------
# Digests.  Everything hashed here is read from disk at the moment of use.
# --------------------------------------------------------------------------

def file_digest(path) -> str:
    """SHA-256 of a file's bytes, prefixed with the algorithm."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def environment_digest() -> dict:
    """What would have to be equal for a rerun to be a rerun.

    Deliberately coarse: exact library patch versions change more often than
    results do, and an envelope that never verifies is as useless as one that
    always does.  The digest is reported alongside the raw fields so a mismatch
    can be inspected rather than merely detected.
    """
    try:
        import numpy
        numpy_version = numpy.__version__
    except ImportError:                     # pragma: no cover - numpy is required
        numpy_version = "absent"
    fields = {
        "python": ".".join(str(v) for v in sys.version_info[:3]),
        "platform": platform.system().lower(),
        "machine": platform.machine(),
        "numpy": numpy_version,
    }
    payload = json.dumps(fields, sort_keys=True).encode()
    return {"fields": fields, "digest": _digest_bytes(payload)}


def current_commit(repo_root=None) -> str:
    """HEAD of the working repository, or ``unknown`` outside one."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=15,
                             cwd=str(repo_root) if repo_root else None)
    except (OSError, subprocess.SubprocessError):   # pragma: no cover
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def _is_full_commit_sha(value: str) -> bool:
    """Whether ``value`` is the canonical SHA-1 spelling used by this repo."""

    return isinstance(value, str) and bool(
        re.fullmatch(r"[0-9a-f]{40}", value)
    )


def _commit_exists(commit_sha: str, repo_root) -> bool:
    """True only when ``commit_sha`` resolves to a Git commit object."""

    if not _is_full_commit_sha(commit_sha):
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
            capture_output=True,
            timeout=30,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


@lru_cache(maxsize=256)
def _committed_file_digest(relative_path, commit_sha: str, repo_root) -> str | None:
    """Digest a repository blob without trusting the mutable working tree."""

    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit_sha or ""):
        return None
    portable = PurePosixPath(str(relative_path).replace("\\", "/"))
    if portable.is_absolute() or ".." in portable.parts or not portable.parts:
        return None
    try:
        result = subprocess.run(
            ["git", "cat-file", "blob", f"{commit_sha}:{portable.as_posix()}"],
            capture_output=True,
            timeout=30,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _digest_bytes(result.stdout)


def party_identity_established(party: str) -> bool:
    """Whether a label identifies a party rather than an executable artifact.

    This is deliberately a narrow syntactic floor, not authentication.  It
    closes the concrete ambiguity found in R6k-W1: the same ``experiments/``
    script ran on two machines, so its path cannot identify either party.
    Cryptographic identity remains a typed remainder of the v2 protocol.
    """

    if not isinstance(party, str) or not party.strip():
        return False
    normalized = party.strip().replace("\\", "/")
    return not (normalized.startswith("experiments/") or normalized.endswith(".py"))


def evidence_independence_established(
    *, schema_version: object, producer: object, verifier: object,
    verification_mode: object, computed_artifacts: object,
    environment_dependent: object, raw_artifacts: object,
) -> bool:
    """One fail-closed independence predicate shared by every audit surface."""

    if schema_version != SCHEMA_VERSION:
        return False
    if not (party_identity_established(producer)
            and party_identity_established(verifier)):
        return False
    if verifier == producer or verification_mode not in _INDEPENDENT_MODES:
        return False
    if not (
        isinstance(computed_artifacts, list)
        and all(isinstance(path, str) and path for path in computed_artifacts)
        and isinstance(environment_dependent, list)
        and all(isinstance(path, str) and path for path in environment_dependent)
        and isinstance(raw_artifacts, dict)
    ):
        return False
    comparable = set(computed_artifacts) - set(environment_dependent)
    return bool(comparable) and comparable.issubset(set(raw_artifacts))


# --------------------------------------------------------------------------
# The borrowed rule
# --------------------------------------------------------------------------

def effective_sample_size(seeds, input_hashes) -> int:
    """How many DISTINCT experiments a seed list actually ran.

    ``len(seeds)`` is a claim about intent.  ``len(set(input_hashes))`` is a
    claim about inputs.  When a generator ignores its seed the two diverge, and
    the first is the one that ends up in a paper.

    An empty ``input_hashes`` means the producer declined to record its inputs,
    and no sample size can be certified from it -- so this returns 0 rather than
    falling back to ``len(seeds)``, which would restore exactly the assumption
    the function exists to check.
    """
    if not input_hashes:
        return 0
    return len(set(input_hashes))


# --------------------------------------------------------------------------
# Envelopes
# --------------------------------------------------------------------------

@dataclass
class EvidenceEnvelope:
    """One machine-checkable binding of a claim to how it was produced."""

    claim_id: str
    evidence_tag: str                       # P / A / M / H / S / R
    command: str
    observed_result: dict
    # One-phase historical producers must opt in to v2 only after they implement
    # source -> raw -> envelope chronology.  This default prevents a rerun from
    # silently writing a v2-shaped envelope with no artifact commit.
    schema_version: str = LEGACY_SCHEMA_VERSION
    #: Exact immutable commit containing every byte in ``raw_artifacts``.
    #: Required, full length, and checked unconditionally by evidence.v2.
    artifact_commit_sha: str = ""
    #: Retained for compatibility with the v1 field and witness request format.
    #: In v2 it must equal ``artifact_commit_sha``.
    commit_sha: str = ""
    #: Optional exact code snapshot.  It is provenance, not artifact binding.
    source_commit_sha: str = ""
    preregistration_commit_sha: str = ""
    working_directory: str = ""
    platform: str = ""
    environment: dict = field(default_factory=dict)
    input_hashes: list = field(default_factory=list)
    seeds: list = field(default_factory=list)
    raw_artifacts: dict = field(default_factory=dict)   # path -> digest
    #: The subset that a recomputing witness must actually PRODUCE.  Source,
    #: manifests, and other cloned inputs may be bound in ``raw_artifacts`` but
    #: cannot establish a second computation merely by hashing the checkout.
    computed_artifacts: list = field(default_factory=list)
    #: Artifacts whose CONTENT is a function of the environment -- timings, CPU
    #: model, library versions.  An honest recomputation of one of these on any
    #: other machine produces a different digest, so digest equality is the wrong
    #: check and would report `contradicted` for a verifier that did everything
    #: right.  Listed here, they are checked for existence and integrity against
    #: the producer's own copy, and excluded from cross-party digest comparison.
    environment_dependent: list = field(default_factory=list)
    uncertainty: dict = field(default_factory=dict)
    producer: str = ""
    verifier: str = ""
    timestamp: str = ""
    signature_status: str = "unsigned"
    typed_remainders: list = field(default_factory=list)
    verification_mode: str = "not_requested"
    witness_environment: str = ""
    witness_notes: str = ""
    witness_conversation_url: str = ""

    @property
    def independent(self) -> bool:
        """A different party is necessary and not sufficient.

        Two conditions, and the second was added when an external verifier
        became reachable.  A distinct party who merely *agrees* with the
        producer's arithmetic has added a signature, not a computation; if the
        producer's number is wrong the attestation is wrong the same way.  Only
        a party that RECOMPUTED -- ran the command in its own environment and
        produced its own artifact digests, compared here rather than there --
        makes an envelope independently witnessed.

        See :mod:`aionq.witness`.  Keeping this property permissive would have
        rebuilt self-witnessing at higher cost and with a second logo on it.
        """
        return evidence_independence_established(
            schema_version=self.schema_version,
            producer=self.producer,
            verifier=self.verifier,
            verification_mode=self.verification_mode,
            computed_artifacts=self.computed_artifacts,
            environment_dependent=self.environment_dependent,
            raw_artifacts=self.raw_artifacts,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProofEnvelope:
    """The P-tag variant.  A proof's evidence is a build, not a measurement."""

    claim_id: str
    theorem_name: str
    prover: str
    prover_version: str
    build_command: str
    artifact_digest: str
    axiom_inventory: list = field(default_factory=list)
    dependency_digests: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    artifact_path: str = ""
    artifact_commit_sha: str = ""
    commit_sha: str = ""
    producer: str = ""
    verifier: str = ""
    build_status: str = "not_built"        # never default to "built"
    verification_mode: str = "not_requested"
    typed_remainders: list = field(default_factory=list)

    @property
    def independent(self) -> bool:
        return (
            self.schema_version == SCHEMA_VERSION
            and self.build_status == "built"
            and self.verification_mode == "recomputed"
            and party_identity_established(self.producer)
            and party_identity_established(self.verifier)
            and self.verifier != self.producer
            and isinstance(self.artifact_path, str)
            and bool(self.artifact_path)
            and isinstance(self.artifact_digest, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", self.artifact_digest) is not None
            and _is_full_commit_sha(self.artifact_commit_sha)
            and self.commit_sha == self.artifact_commit_sha
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationResult:
    ok: bool
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    effective_n: int = 0
    independent: bool = False

    def __str__(self) -> str:  # pragma: no cover - display only
        head = "VERIFIED" if self.ok else "FAILED"
        parts = [f"{head}  n_eff={self.effective_n}  independent={self.independent}"]
        parts += [f"  FAIL  {f}" for f in self.failures]
        parts += [f"  warn  {w}" for w in self.warnings]
        return "\n".join(parts)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------

_TAGS_REQUIRING_EVIDENCE = {"P", "A", "M"}
_EVIDENCE_TAGS = frozenset({"P", "A", "M", "H", "S", "R"})

# Re-exported so governance need not re-derive the set and drift from it.
EvidenceTag_REQUIRING_EVIDENCE = frozenset(_TAGS_REQUIRING_EVIDENCE)


def verify(envelope, repo_root=None, check_commit: bool = True) -> VerificationResult:
    """Re-check an envelope against its live files or recorded Git commit.

    Nothing here trusts a value the envelope carries about itself: artifact
    digests are recomputed from disk or immutable Git blobs, the current commit
    is read from Git, and the environment digest is recomputed from the running
    interpreter.
    """
    failures: list = []
    warnings: list = []

    if isinstance(envelope, ProofEnvelope):
        root = Path(repo_root) if repo_root else Path.cwd()
        claim = envelope.claim_id if isinstance(envelope.claim_id, str) else "<invalid-proof>"
        if envelope.schema_version != SCHEMA_VERSION:
            failures.append(
                f"{claim}: proof schema must be exactly {SCHEMA_VERSION!r}")
        for label, value in (
            ("claim_id", envelope.claim_id),
            ("theorem_name", envelope.theorem_name),
            ("prover", envelope.prover),
            ("prover_version", envelope.prover_version),
            ("build_command", envelope.build_command),
        ):
            if not isinstance(value, str) or not value.strip():
                failures.append(f"{claim}: {label} must be a nonempty string")
        if envelope.build_status != "built":
            failures.append(
                f"{claim}: build_status is {envelope.build_status!r}. "
                "A P claim may not rest on a proof that was never compiled.")
        if envelope.verification_mode not in _VERIFICATION_MODES:
            failures.append(
                f"{claim}: unknown proof verification_mode "
                f"{envelope.verification_mode!r}")
        if not isinstance(envelope.axiom_inventory, list):
            failures.append(f"{claim}: axiom_inventory must be a JSON list")
        elif envelope.axiom_inventory:
            warnings.append(
                f"{claim}: proved relative to {len(envelope.axiom_inventory)} "
                f"axiom(s) {envelope.axiom_inventory}. A theorem proved from an axiom "
                "that restates its conclusion proves nothing about the conclusion.")

        artifact_path_ok = isinstance(envelope.artifact_path, str) and bool(
            envelope.artifact_path)
        if not artifact_path_ok:
            failures.append(f"{claim}: artifact_path must be a nonempty string")
        if not isinstance(envelope.artifact_digest, str) or re.fullmatch(
                r"sha256:[0-9a-f]{64}", envelope.artifact_digest) is None:
            failures.append(f"{claim}: artifact_digest must be canonical SHA-256")

        if not isinstance(envelope.dependency_digests, dict):
            failures.append(f"{claim}: dependency_digests must be a JSON object")
            dependency_digests = {}
        else:
            dependency_digests = envelope.dependency_digests
        bindings = {}
        if artifact_path_ok:
            bindings[envelope.artifact_path] = envelope.artifact_digest
        for path, digest in dependency_digests.items():
            if path in bindings and bindings[path] != digest:
                failures.append(f"{claim}: conflicting digest declarations for {path!r}")
            bindings[path] = digest

        commit_is_valid = False
        if check_commit:
            if not _is_full_commit_sha(envelope.artifact_commit_sha):
                failures.append(
                    f"{claim}: artifact_commit_sha must be exactly 40 lowercase "
                    "hexadecimal characters")
            elif envelope.commit_sha != envelope.artifact_commit_sha:
                failures.append(
                    f"{claim}: proof commit_sha must equal artifact_commit_sha")
            elif not _commit_exists(envelope.artifact_commit_sha, root):
                failures.append(
                    f"{claim}: artifact_commit_sha does not resolve to a commit")
            else:
                commit_is_valid = True

        for rel, declared in bindings.items():
            if not isinstance(rel, str) or not rel:
                failures.append(f"{claim}: proof artifact path must be nonempty")
                continue
            if not isinstance(declared, str) or re.fullmatch(
                    r"sha256:[0-9a-f]{64}", declared) is None:
                failures.append(
                    f"{claim}: malformed SHA-256 declaration for {rel!r}")
                continue
            portable = PurePosixPath(rel.replace("\\", "/"))
            if check_commit and (
                    portable.is_absolute() or ".." in portable.parts
                    or not portable.parts):
                failures.append(
                    f"{claim}: proof artifact path escapes repository: {rel!r}")
                continue
            committed = None
            if check_commit and commit_is_valid:
                committed = _committed_file_digest(
                    rel, envelope.artifact_commit_sha, root)
                if committed is None:
                    failures.append(
                        f"{claim}: proof artifact is absent at recorded commit: {rel}")
                elif committed != declared:
                    failures.append(
                        f"{claim}: committed proof artifact digest mismatch for {rel}")
            path = root / rel
            if not path.exists():
                if committed == declared:
                    warnings.append(
                        f"{claim}: live proof artifact is absent for {rel}; immutable "
                        "commit binding remains valid")
                else:
                    failures.append(f"{claim}: proof artifact missing: {rel}")
            elif file_digest(path) != declared:
                if committed == declared:
                    warnings.append(
                        f"{claim}: live proof artifact differs for {rel}; immutable "
                        "commit binding remains valid")
                else:
                    failures.append(f"{claim}: proof artifact digest mismatch: {rel}")
        return VerificationResult(ok=not failures, failures=failures,
                                  warnings=warnings, effective_n=0,
                                  independent=envelope.independent and not failures)

    claim = envelope.claim_id if isinstance(envelope.claim_id, str) else "<invalid-evidence>"
    if not isinstance(envelope.claim_id, str) or not envelope.claim_id.strip():
        failures.append("claim_id must be a nonempty string")
    if not isinstance(envelope.evidence_tag, str) \
            or envelope.evidence_tag not in _EVIDENCE_TAGS:
        failures.append(
            f"{claim}: evidence_tag must be one of {sorted(_EVIDENCE_TAGS)!r}")
    if not isinstance(envelope.verification_mode, str) \
            or envelope.verification_mode not in _VERIFICATION_MODES:
        failures.append(
            f"{claim}: unknown verification_mode {envelope.verification_mode!r}")
    if not isinstance(envelope.environment_dependent, list) or any(
            not isinstance(path, str) or not path
            for path in envelope.environment_dependent):
        failures.append(
            f"{claim}: environment_dependent must be a list of nonempty paths")
        environment_dependent = []
    else:
        environment_dependent = envelope.environment_dependent

    if (not isinstance(envelope.schema_version, str)
            or envelope.schema_version not in SUPPORTED_SCHEMA_VERSIONS):
        failures.append(
            f"unsupported schema {envelope.schema_version!r}; expected one of "
            f"{sorted(SUPPORTED_SCHEMA_VERSIONS)!r}")
    is_v2 = envelope.schema_version == SCHEMA_VERSION
    if not is_v2:
        warnings.append(
            f"{envelope.claim_id}: legacy evidence.v1 envelope; its commit field "
            "is not a fail-closed artifact binding and it cannot be ranked "
            "INDEPENDENT. Migrate it to evidence.v2.")

    if not isinstance(envelope.command, str) or not envelope.command.strip():
        failures.append(f"{envelope.claim_id}: no command recorded; the result "
                        "cannot be re-run and is therefore not evidence")

    # 1. Immutable artifact binding, then the mutable working-tree copy.
    root = Path(repo_root) if repo_root else Path.cwd()
    artifact_commit = (envelope.artifact_commit_sha if is_v2
                       else envelope.commit_sha)
    commit_is_valid = False
    if check_commit and is_v2:
        if not _is_full_commit_sha(envelope.artifact_commit_sha):
            failures.append(
                f"{envelope.claim_id}: artifact_commit_sha must be exactly 40 "
                "lowercase hexadecimal characters")
        elif envelope.commit_sha != envelope.artifact_commit_sha:
            failures.append(
                f"{envelope.claim_id}: v2 commit_sha must equal "
                "artifact_commit_sha; source provenance belongs in "
                "source_commit_sha")
        elif not _commit_exists(envelope.artifact_commit_sha, root):
            failures.append(
                f"{envelope.claim_id}: artifact_commit_sha does not resolve to "
                f"a commit: {envelope.artifact_commit_sha}")
        else:
            commit_is_valid = True
        for label, value in (("source_commit_sha", envelope.source_commit_sha),
                             ("preregistration_commit_sha",
                              envelope.preregistration_commit_sha)):
            if value and (not _is_full_commit_sha(value)
                          or not _commit_exists(value, root)):
                failures.append(
                    f"{envelope.claim_id}: {label} is not a resolvable canonical "
                    f"commit SHA: {value!r}")
    if not isinstance(envelope.raw_artifacts, dict):
        failures.append(
            f"{envelope.claim_id}: raw_artifacts must be a JSON object")
        raw_artifacts = {}
    else:
        raw_artifacts = envelope.raw_artifacts
    if not raw_artifacts:
        failures.append(f"{envelope.claim_id}: no raw artifact recorded. Prose "
                        "copied into JSON is not independent witnessing.")
    for rel, declared in raw_artifacts.items():
        if not isinstance(rel, str) or not rel:
            failures.append(f"{envelope.claim_id}: artifact path must be a nonempty string")
            continue
        if not isinstance(declared, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", declared):
            failures.append(
                f"{envelope.claim_id}: malformed SHA-256 declaration for {rel!r}")
            continue
        portable = PurePosixPath(rel.replace("\\", "/"))
        if is_v2 and check_commit and (
                portable.is_absolute() or ".." in portable.parts
                or not portable.parts):
            failures.append(
                f"{envelope.claim_id}: v2 artifact path escapes repository: {rel!r}")
            continue

        committed = None
        if check_commit and is_v2 and commit_is_valid:
            committed = _committed_file_digest(rel, artifact_commit, root)
            if committed is None:
                failures.append(
                    f"{envelope.claim_id}: artifact is absent at recorded commit "
                    f"{artifact_commit[:8]}: {rel}")
            elif committed != declared:
                failures.append(
                    f"{envelope.claim_id}: committed artifact digest mismatch for "
                    f"{rel} at {artifact_commit[:8]}: declared {declared[:19]}..., "
                    f"found {committed[:19]}...")

        path = root / rel
        if not path.exists():
            if committed is None and not (check_commit and is_v2):
                committed = _committed_file_digest(rel, artifact_commit, root)
            if committed == declared:
                warnings.append(
                    f"{envelope.claim_id}: working-tree artifact is absent for "
                    f"{rel}, but the declared digest matches recorded commit "
                    f"{artifact_commit[:8]}. Historical evidence remains "
                    "bound to that commit."
                )
            else:
                failures.append(f"{envelope.claim_id}: artifact missing: {rel}")
            continue
        actual = file_digest(path)
        if actual != declared:
            if committed is None and not (check_commit and is_v2):
                committed = _committed_file_digest(rel, artifact_commit, root)
            if committed == declared:
                warnings.append(
                    f"{envelope.claim_id}: working-tree artifact differs for "
                    f"{rel}, but the declared digest matches recorded commit "
                    f"{artifact_commit[:8]}. Historical evidence remains "
                    "bound to that commit, not to the current file."
                )
            else:
                failures.append(f"{envelope.claim_id}: artifact digest mismatch for "
                                f"{rel}: declared {declared[:19]}..., found "
                                f"{actual[:19]}...")

    # 2. Current checkout, read from git.  A later HEAD is normal; the immutable
    # artifact comparison above is the binding and this is only provenance.
    if check_commit and artifact_commit:
        head = current_commit(repo_root)
        if head != "unknown" and head != artifact_commit:
            warnings.append(f"{envelope.claim_id}: envelope commit "
                            f"{artifact_commit[:8]} != HEAD {head[:8]}. The "
                            "immutable artifact binding was checked at the "
                            "recorded commit.")

    # 2b. A recomputation must name outputs it computed, not merely source files
    # it received by cloning the producer's repository.
    if is_v2:
        computed = envelope.computed_artifacts
        computed_is_valid = isinstance(computed, list) and not any(
            not isinstance(path, str) or not path for path in computed
        )
        if not computed_is_valid:
            failures.append(
                f"{envelope.claim_id}: computed_artifacts must be a list of paths")
        elif len(computed) != len(set(computed)):
            failures.append(
                f"{envelope.claim_id}: computed_artifacts contains duplicates")
        elif any(path not in raw_artifacts for path in computed):
            failures.append(
                f"{envelope.claim_id}: every computed artifact must also be raw-bound")
        if envelope.verification_mode == "recomputed" and computed_is_valid:
            comparable = set(computed) - set(environment_dependent)
            if not comparable:
                warnings.append(
                    f"{envelope.claim_id}: recomputed mode has no comparable "
                    "computed output and is capped below INDEPENDENT")

    # 3. Environment, recomputed here.
    if not isinstance(envelope.environment, dict):
        failures.append(
            f"{envelope.claim_id}: environment must be a JSON object")
    elif envelope.environment:
        now = environment_digest()
        if envelope.environment.get("digest") != now["digest"]:
            warnings.append(f"{envelope.claim_id}: environment differs from the "
                            f"one that produced this result: recorded "
                            f"{envelope.environment.get('fields')}, running "
                            f"{now['fields']}.")

    # 4. The borrowed rule: sample size against distinct inputs.
    seeds_are_valid = isinstance(envelope.seeds, list)
    hashes_are_valid = (
        isinstance(envelope.input_hashes, list)
        and all(isinstance(value, str) and value.strip()
                for value in envelope.input_hashes)
    )
    if not seeds_are_valid:
        failures.append(f"{envelope.claim_id}: seeds must be a JSON list")
    if not hashes_are_valid:
        failures.append(
            f"{envelope.claim_id}: input_hashes must be a JSON list of nonempty strings")
    n_eff = effective_sample_size(
        envelope.seeds if seeds_are_valid else [],
        envelope.input_hashes if hashes_are_valid else [],
    )
    if not isinstance(envelope.observed_result, dict):
        failures.append(
            f"{envelope.claim_id}: observed_result must be a JSON object")
        observed_result = {}
    else:
        observed_result = envelope.observed_result
    declared_n = observed_result.get("sample_size")
    if is_v2 and declared_n is not None:
        if isinstance(declared_n, bool) or not isinstance(declared_n, int) \
                or declared_n < 0:
            failures.append(
                f"{envelope.claim_id}: sample_size must be a nonnegative integer")
        elif declared_n > 0 and n_eff == 0:
            failures.append(
                f"{envelope.claim_id}: declares sample_size {declared_n} but "
                "records no distinct input hashes")
    declared_n_is_integer = (
        isinstance(declared_n, int) and not isinstance(declared_n, bool)
    )
    if declared_n_is_integer and n_eff and declared_n > n_eff:
        failures.append(
            f"{envelope.claim_id}: declares sample_size {declared_n} but only "
            f"{n_eff} DISTINCT input(s) across "
            f"{len(envelope.seeds) if seeds_are_valid else 0} seed(s). "
            "Seeds that do not change the input do not add observations.")
    if seeds_are_valid and envelope.seeds and n_eff and n_eff < len(envelope.seeds):
        warnings.append(
            f"{envelope.claim_id}: {len(envelope.seeds)} seeds produced only "
            f"{n_eff} distinct inputs; the remainder are repeats.")

    # 5. A contradicted recomputation is a failure, not a warning.
    if envelope.verification_mode == "contradicted":
        failures.append(
            f"{envelope.claim_id}: an independent recomputation produced "
            "different artifacts. The producer's result and the verifier's "
            "result are not averaged and the newer one does not win; the "
            "envelope fails until the disagreement is explained.")

    # 6. Independence, recorded rather than assumed.
    if (isinstance(envelope.evidence_tag, str)
            and envelope.evidence_tag in _TAGS_REQUIRING_EVIDENCE
            and not envelope.independent):
        warnings.append(
            f"{envelope.claim_id}: not independently witnessed "
            f"(producer={envelope.producer!r}, verifier={envelope.verifier!r}, "
            f"mode={envelope.verification_mode!r}). Binding a result to a command "
            "and a hash is real; a second party agreeing without recomputing is "
            "a signature, not a computation.")

    return VerificationResult(
        ok=not failures,
        failures=failures,
        warnings=warnings,
        effective_n=n_eff,
        independent=envelope.independent and not failures,
    )


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def save_envelope(envelope, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = envelope.to_dict()
    payload.setdefault("timestamp", "")
    if not payload.get("timestamp"):
        payload["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_envelope(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evidence envelope must be a top-level JSON object")
    if "theorem_name" in data:
        known = {f for f in ProofEnvelope.__dataclass_fields__}
        return ProofEnvelope(**{k: v for k, v in data.items() if k in known})
    known = {f for f in EvidenceEnvelope.__dataclass_fields__}
    return EvidenceEnvelope(**{k: v for k, v in data.items() if k in known})
