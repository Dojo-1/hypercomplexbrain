"""Typed carriers for S4-G100.

Everything here is a *type*, not a claim.  The names Emperor, Empress, Nest,
Worldlet and Tendril are semantic handles registered at S tier in
:mod:`aionq.governance`; what this module supplies is the explicit operator each
handle stands for, so that no evaluation ever has to guess what a field means.

Two repository rules are enforced structurally rather than by convention.

**Every remainder is typed.**  :class:`TypedRemainder` refuses to exist without a
kind drawn from :class:`aionq.governance.RemainderKind`, and it carries its own
carrier, comparison and provenance.  A transport defect measured in Frobenius
norm on O(4) is not a cohomology class and not a semantic leftover; the type
system says so before any arithmetic can conflate them.

**Nothing is compared across incompatible frames.**  :class:`TransportReport`
records preserved / transformed / lost fields at every edge, so a quantity that
crossed a frame boundary carries the record of what it cost.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..governance import EvidenceTag, GovernanceError, RemainderKind

__all__ = [
    "TypedRemainder", "TransportReport", "CandidateSection", "NestDeposit",
    "DepositType", "CarrierMismatch", "EvidenceTag", "RemainderKind",
]


class CarrierMismatch(TypeError):
    """Raised when two quantities from incompatible carriers are compared."""


# --------------------------------------------------------------------------
# Typed remainders
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TypedRemainder:
    """A remainder that knows its own kind, carrier and comparison.

    The Atlas rule this repository already enforces for :class:`Remainder` is
    tightened here: a remainder must also name the *carrier* it lives on and the
    *metric or comparison* that produced its value.  Without those two fields a
    number like 0.0034 is not interpretable, and the round-trip defect of
    S4-G100 is exactly such a number.
    """

    remainder_type: str
    carrier: str
    metric_or_comparison: str
    raw_value: float
    assumptions: tuple = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.remainder_type not in RemainderKind.ALL:
            raise GovernanceError(
                f"untyped remainder {self.remainder_type!r}; must be one of "
                f"{RemainderKind.ALL}")
        if not self.carrier or not self.metric_or_comparison:
            raise GovernanceError(
                "a remainder must name its carrier and its comparison: a bare "
                "number is not interpretable and cannot be transported")
        if self.raw_value is None or (isinstance(self.raw_value, float)
                                      and math.isnan(self.raw_value)):
            raise GovernanceError("remainder raw_value must be a real number")

    def comparable_to(self, other: "TypedRemainder") -> bool:
        return (self.remainder_type == other.remainder_type
                and self.carrier == other.carrier
                and self.metric_or_comparison == other.metric_or_comparison)

    def difference(self, other: "TypedRemainder") -> float:
        """Refuse to subtract remainders that do not live in the same place."""
        if not self.comparable_to(other):
            raise CarrierMismatch(
                f"cannot subtract a {self.remainder_type} on {self.carrier} "
                f"({self.metric_or_comparison}) from a {other.remainder_type} on "
                f"{other.carrier} ({other.metric_or_comparison})")
        return float(self.raw_value - other.raw_value)

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"[{self.remainder_type}] {self.raw_value:.6g} on {self.carrier} "
                f"via {self.metric_or_comparison}")


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TransportReport:
    """What crossing one edge preserved, changed, lost, and left over.

    ``lost`` is not a complaint.  It is the field list an auditor needs in order
    to know which downstream comparisons are illegitimate.  A tendril whose
    ``lost`` list is empty and whose remainder is zero is the only kind of edge
    across which a raw quantity may be compared without further argument.
    """

    edge: str
    preserved: tuple
    transformed: tuple
    lost: tuple
    remainder: TypedRemainder
    evidence: str = ""
    cost: float = 0.0

    @property
    def is_lossless(self) -> bool:
        return not self.lost and abs(self.remainder.raw_value) <= 1e-12

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"{self.edge}: preserved {list(self.preserved)}, transformed "
                f"{list(self.transformed)}, lost {list(self.lost)}, "
                f"{self.remainder}")


# --------------------------------------------------------------------------
# Candidates and deposits
# --------------------------------------------------------------------------

@dataclass
class CandidateSection:
    """One proposed local section: a hypothesis about where the defect is.

    ``generated_by`` and the deposit's ``authorized_by`` are the two halves of
    the no-self-promotion rule (P5).  A candidate records the dependency closure
    that produced it so that a witness inside that closure can be recognised as
    not a witness.
    """

    candidate_id: str
    state: object
    source_worldlets: tuple
    transformations: tuple = ()
    evidence_envelope: dict = field(default_factory=dict)
    resource_cost: float = 0.0
    active_remainders: tuple = ()
    generated_by: frozenset = frozenset()

    def __post_init__(self) -> None:
        for r in self.active_remainders:
            if not isinstance(r, TypedRemainder):
                raise GovernanceError(
                    f"candidate {self.candidate_id} carries an untyped remainder")


class DepositType:
    PROOF = "Proof"
    CONDITIONAL_PROOF = "ConditionalProof"
    MEASURED_PATTERN = "MeasuredPattern"
    CONJECTURE = "Conjecture"
    DESIGN_OBJECT = "DesignObject"
    RETIRED_CLAIM = "RetiredClaim"
    UNRESOLVED = "RemainUnresolved"

    ALL = (PROOF, CONDITIONAL_PROOF, MEASURED_PATTERN, CONJECTURE,
           DESIGN_OBJECT, RETIRED_CLAIM, UNRESOLVED)

    #: The evidence tag each deposit type is allowed to carry.  A deposit may
    #: never carry a tag stronger than its type: this is the table that stops a
    #: Conjecture from being filed as a measurement.
    ALLOWED_TAGS = {
        PROOF: (EvidenceTag.PROVED,),
        CONDITIONAL_PROOF: (EvidenceTag.AXIOMATIZED,),
        MEASURED_PATTERN: (EvidenceTag.MEASURED,),
        CONJECTURE: (EvidenceTag.HYPOTHESIS,),
        DESIGN_OBJECT: (EvidenceTag.SEMANTIC,),
        RETIRED_CLAIM: (EvidenceTag.RETIRED,),
        UNRESOLVED: (EvidenceTag.HYPOTHESIS, EvidenceTag.SEMANTIC),
    }


@dataclass
class NestDeposit:
    """A candidate that has passed the evidence gate, with its limits attached."""

    candidate_id: str
    deposit_type: str
    evidence_tag: str
    supporting_artifacts: tuple = ()
    assumptions: tuple = ()
    controls: tuple = ()
    limitations: tuple = ()
    authorized_by: frozenset = frozenset()
    supersedes: str | None = None
    superseded_by: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.deposit_type not in DepositType.ALL:
            raise GovernanceError(f"unknown deposit type {self.deposit_type!r}")
        if self.evidence_tag not in EvidenceTag.ALL:
            raise GovernanceError(f"unknown evidence tag {self.evidence_tag!r}")
        allowed = DepositType.ALLOWED_TAGS[self.deposit_type]
        if self.evidence_tag not in allowed:
            raise GovernanceError(
                f"{self.candidate_id}: a {self.deposit_type} may not carry tag "
                f"{self.evidence_tag}; allowed {allowed}")
        if self.deposit_type == DepositType.MEASURED_PATTERN and not self.controls:
            raise GovernanceError(
                f"{self.candidate_id}: a MeasuredPattern must name its controls")

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"[{self.evidence_tag}] {self.deposit_type} {self.candidate_id}"
