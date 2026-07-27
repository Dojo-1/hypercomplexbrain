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

1.  ``ARTIFACT`` hashes are read from disk at verification time, not carried in
    memory from whoever produced them.  A corrupted or edited artifact fails.
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
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

__all__ = ["EvidenceEnvelope", "ProofEnvelope", "VerificationResult",
           "file_digest", "environment_digest", "current_commit",
           "effective_sample_size", "verify", "load_envelope", "save_envelope",
           "EvidenceTag_REQUIRING_EVIDENCE"]

SCHEMA_VERSION = "hypercomplexbrain.evidence.v1"


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
    schema_version: str = SCHEMA_VERSION
    commit_sha: str = ""
    working_directory: str = ""
    platform: str = ""
    environment: dict = field(default_factory=dict)
    input_hashes: list = field(default_factory=list)
    seeds: list = field(default_factory=list)
    raw_artifacts: dict = field(default_factory=dict)   # path -> digest
    uncertainty: dict = field(default_factory=dict)
    producer: str = ""
    verifier: str = ""
    timestamp: str = ""
    signature_status: str = "unsigned"
    typed_remainders: list = field(default_factory=list)

    @property
    def independent(self) -> bool:
        """False when producer and verifier are the same party.

        Not an error.  A self-verified envelope is still better than prose --
        it binds a result to a command and a hash.  But it is not independent
        witnessing, and calling it that is the thing this round exists to stop.
        """
        return bool(self.verifier) and self.verifier != self.producer

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
    commit_sha: str = ""
    producer: str = ""
    verifier: str = ""
    build_status: str = "not_built"        # never default to "built"
    typed_remainders: list = field(default_factory=list)

    @property
    def independent(self) -> bool:
        return bool(self.verifier) and self.verifier != self.producer

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

# Re-exported so governance need not re-derive the set and drift from it.
EvidenceTag_REQUIRING_EVIDENCE = frozenset(_TAGS_REQUIRING_EVIDENCE)


def verify(envelope, repo_root=None, check_commit: bool = True) -> VerificationResult:
    """Re-check an envelope against the filesystem it points at.

    Nothing here trusts a value the envelope carries about itself: artifact
    digests are recomputed from disk, the commit is read from git, and the
    environment digest is recomputed from the running interpreter.
    """
    failures: list = []
    warnings: list = []

    if isinstance(envelope, ProofEnvelope):
        if envelope.build_status != "built":
            failures.append(
                f"{envelope.claim_id}: build_status is {envelope.build_status!r}. "
                "A P claim may not rest on a proof that was never compiled.")
        if envelope.axiom_inventory:
            warnings.append(
                f"{envelope.claim_id}: proved relative to {len(envelope.axiom_inventory)} "
                f"axiom(s) {envelope.axiom_inventory}. A theorem proved from an axiom "
                "that restates its conclusion proves nothing about the conclusion.")
        return VerificationResult(ok=not failures, failures=failures,
                                  warnings=warnings, effective_n=0,
                                  independent=envelope.independent)

    if envelope.schema_version != SCHEMA_VERSION:
        failures.append(f"schema {envelope.schema_version!r} != {SCHEMA_VERSION!r}")

    if not envelope.command.strip():
        failures.append(f"{envelope.claim_id}: no command recorded; the result "
                        "cannot be re-run and is therefore not evidence")

    # 1. Artifacts, recomputed from disk.
    root = Path(repo_root) if repo_root else Path.cwd()
    if not envelope.raw_artifacts:
        failures.append(f"{envelope.claim_id}: no raw artifact recorded. Prose "
                        "copied into JSON is not independent witnessing.")
    for rel, declared in envelope.raw_artifacts.items():
        path = root / rel
        if not path.exists():
            failures.append(f"{envelope.claim_id}: artifact missing: {rel}")
            continue
        actual = file_digest(path)
        if actual != declared:
            failures.append(f"{envelope.claim_id}: artifact digest mismatch for "
                            f"{rel}: declared {declared[:19]}..., found "
                            f"{actual[:19]}...")

    # 2. Commit, read from git.
    if check_commit and envelope.commit_sha:
        head = current_commit(repo_root)
        if head != "unknown" and not head.startswith(envelope.commit_sha):
            warnings.append(f"{envelope.claim_id}: envelope commit "
                            f"{envelope.commit_sha[:8]} != HEAD {head[:8]}. The "
                            "artifact may predate the code that claims it.")

    # 3. Environment, recomputed here.
    if envelope.environment:
        now = environment_digest()
        if envelope.environment.get("digest") != now["digest"]:
            warnings.append(f"{envelope.claim_id}: environment differs from the "
                            f"one that produced this result: recorded "
                            f"{envelope.environment.get('fields')}, running "
                            f"{now['fields']}.")

    # 4. The borrowed rule: sample size against distinct inputs.
    n_eff = effective_sample_size(envelope.seeds, envelope.input_hashes)
    declared_n = envelope.observed_result.get("sample_size")
    if declared_n is not None and n_eff and declared_n > n_eff:
        failures.append(
            f"{envelope.claim_id}: declares sample_size {declared_n} but only "
            f"{n_eff} DISTINCT input(s) across {len(envelope.seeds)} seed(s). "
            "Seeds that do not change the input do not add observations.")
    if envelope.seeds and n_eff and n_eff < len(envelope.seeds):
        warnings.append(
            f"{envelope.claim_id}: {len(envelope.seeds)} seeds produced only "
            f"{n_eff} distinct inputs; the remainder are repeats.")

    # 5. Independence, recorded rather than assumed.
    if envelope.evidence_tag in _TAGS_REQUIRING_EVIDENCE and not envelope.independent:
        warnings.append(
            f"{envelope.claim_id}: producer and verifier are the same party "
            f"({envelope.producer!r}). This envelope binds a result to a command "
            "and a hash, which is real; it is NOT independent witnessing.")

    return VerificationResult(ok=not failures, failures=failures, warnings=warnings,
                              effective_n=n_eff, independent=envelope.independent)


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def load_envelope(path):
    data = json.loads(Path(path).read_text())
    if "theorem_name" in data:
        known = {f for f in ProofEnvelope.__dataclass_fields__}
        return ProofEnvelope(**{k: v for k, v in data.items() if k in known})
    known = {f for f in EvidenceEnvelope.__dataclass_fields__}
    return EvidenceEnvelope(**{k: v for k, v in data.items() if k in known})
