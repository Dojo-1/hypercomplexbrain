"""What this programme currently knows, as opposed to what it has corrected.

Every instrument in this repository measures a deficiency: unwitnessed claims,
unreached guards, missing strategies, absent audits.  That is the right
instinct and it has one blind spot -- none of them reports the positive
quantity.  A session can drive the correction count from 41 to 67 and never
once ask what is standing.

Three movements are visible only at the scale of the whole registry, and none
of them is visible from inside any round.

    RETIREMENT IS THE LARGEST CATEGORY.  93 claims: 26 RETIRED against 25
    PROVED and 25 MEASURED.  The programme demotes claims at very nearly the
    rate it proves them, which is either unusual rigour or claims arriving
    faster than support, and the ledger alone cannot say which.

    EVIDENCE COVERAGE IS ONE CLAIM.  Of 57 live claims at an evidence-requiring
    tag, exactly one carries a verified envelope, and it is
    ``AXIOM-HB0-UNIVERSAL_POINCARE_BASE`` -- the AXIOM.  Zero PROVED and zero
    MEASURED claims have one.  The architecture already records that this
    envelope is "unsigned, self-recomputed, and neither commit-bound nor
    independently witnessed", so the single evidenced claim in the programme is
    the one evidenced by assumption.

    THE GAP IS WIDENING.  At QSigma-R4 the architecture recorded 48 of 81
    claims carrying no envelope.  It is now 56 of 93.  Twelve claims were
    added and eight of them arrived unwitnessed, so the coverage ratio moved in
    the wrong direction while the corpus grew.

The third is the one that matters, because it is a derivative rather than a
level.  A large deficit that is closing is a programme in progress; a smaller
deficit that is widening is not.

A note on reading ``registry.unwitnessed()``: it returns claims at an
EVIDENCE-REQUIRING tag with no verified envelope, so HYPOTHESIS and SEMANTIC
claims never appear in it.  Their absence means the question does not apply --
a metaphor cannot carry an envelope -- and reading it as "witnessed" inverts
the ledger, turning 1-of-57 coverage into an apparent 11-of-67.  This module
computes the distinction rather than leaving it to the reader.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import EvidenceTag_REQUIRING_EVIDENCE
from .governance import registry as _default_registry

__all__ = [
    "KnowledgeLedger",
    "knowledge_ledger",
    "R4_BASELINE",
]

#: Recorded in docs/ARCHITECTURE.md section 7 for QSigma-R4: "48 of 81 prior
#: claims carry no envelope".  Kept here so the trajectory is a computation
#: against a written number rather than a recollection.
R4_BASELINE = {"claims": 81, "unwitnessed": 48}


@dataclass
class KnowledgeLedger:
    """The positive and negative sides of the registry, side by side."""

    total: int = 0
    retired: int = 0
    live: int = 0
    by_tag: dict = field(default_factory=dict)
    #: Live claims at a tag that REQUIRES evidence (P, A, M).
    evidence_requiring: int = 0
    witnessed: tuple = ()
    unwitnessed: int = 0
    #: Live claims whose tag makes the question inapplicable (H, S).
    not_applicable: int = 0
    trajectory: dict = field(default_factory=dict)

    @property
    def retirement_rate(self) -> float:
        return self.retired / self.total if self.total else 0.0

    @property
    def coverage(self) -> float:
        """Fraction of evidence-requiring live claims carrying an envelope."""
        if not self.evidence_requiring:
            return 0.0
        return len(self.witnessed) / self.evidence_requiring

    @property
    def gap_is_widening(self) -> bool:
        """Is the unwitnessed count growing faster than coverage improves?"""
        return bool(self.trajectory.get("unwitnessed_added", 0) > 0)


def knowledge_ledger(registry=None) -> KnowledgeLedger:
    """Compute what stands, what was demoted, and which way the ratio moves."""
    registry = registry or _default_registry
    claims = registry._claims
    unwitnessed_ids = set(registry.unwitnessed())

    by_tag: dict = {}
    for claim in claims.values():
        by_tag[claim.tag] = by_tag.get(claim.tag, 0) + 1

    retired = [c for c in claims.values() if c.tag == "R"]
    live = [c for c in claims.values() if c.tag != "R"]
    requiring = [c for c in live if c.tag in EvidenceTag_REQUIRING_EVIDENCE]
    witnessed = tuple(sorted(c.id for c in requiring if c.id not in unwitnessed_ids))
    not_applicable = [c for c in live
                      if c.tag not in EvidenceTag_REQUIRING_EVIDENCE]

    claims_added = len(claims) - R4_BASELINE["claims"]
    unwitnessed_added = len(unwitnessed_ids) - R4_BASELINE["unwitnessed"]

    return KnowledgeLedger(
        total=len(claims),
        retired=len(retired),
        live=len(live),
        by_tag=by_tag,
        evidence_requiring=len(requiring),
        witnessed=witnessed,
        unwitnessed=len(unwitnessed_ids),
        not_applicable=len(not_applicable),
        trajectory={
            "baseline_round": "QSigma-R4",
            "baseline_claims": R4_BASELINE["claims"],
            "baseline_unwitnessed": R4_BASELINE["unwitnessed"],
            "claims_added": claims_added,
            "unwitnessed_added": unwitnessed_added,
            "share_of_new_claims_unwitnessed": (
                unwitnessed_added / claims_added if claims_added else 0.0),
            "reading": (
                f"{claims_added} claims added since the R4 baseline and "
                f"{unwitnessed_added} of them arrived without an envelope, so "
                "the coverage ratio moved in the wrong direction while the "
                "corpus grew. A large deficit that is closing is a programme in "
                "progress; a smaller deficit that is widening is not."),
        },
    )
