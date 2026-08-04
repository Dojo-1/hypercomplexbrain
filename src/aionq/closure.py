"""What would close the architecture, computed rather than concluded.

`docs/ARCHITECTURE.md` §8 names three load-bearing parts of the remainder:

1. the classical frontier is not closed -- `q_sim_upper` is an upper bound from
   the strategies implemented here, and a better classical algorithm lowers it;
2. measured-high does not mean thinks-better -- nothing connects the metric to
   cognitive performance, so the architecture is auditable and not justified;
3. the self cannot close -- the identity signature is estimable only from
   outside, so the architecture is complete only as a two-party object.

They read as three separate debts, and the third as the philosophical one.  This
module computes all three against the live repository, and they are one debt.

    R1 is blocked because a bound produced by one algorithm has nothing
       checking it, and every algorithm in the portfolio is this party's.
    R2 is blocked because `promote()` requires `audit >= audit_threshold`, and
       the R3B-0 cone sets that threshold to 1.0 against an audit strength of
       0.0.  The code's own words: an organ that "lacks external audit" is not
       promoted, and audit is "not tradeable against effect size".
    R3 is blocked because `evidence_rank` caps at ATTESTED for any act whose
       verifier is its producer, and `closable_from_inside` is False.

The common factor is not a metaphor.  It is the same predicate in all three:
an act by a party that is not this one.  §8 called point 3 "the same remainder
the draft named Gödelian"; what is computable here is that points 1 and 2 are
that remainder too, wearing the clothes of a metric and of a promotion gate.

The strongest form is the portfolio result below.  Two simulation strategies
agreeing on a core feels like corroboration, and QSigma-R1a spent a round
looking for where that happens.  Modelled honestly as witness acts, it is not
corroboration at all: the strategies are methods, not parties, so producer
equals verifier, so `WitnessAct.rank` is 0 and `evidence_rank` is NONE.  The
agreement that round went looking for would not have counted even if it had
been found -- which is worth knowing before spending another round looking.

Nothing here claims independent witnessing.  It computes its absence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .witness_nerve import EvidenceRank, WitnessAct, WitnessGraph, evidence_rank

__all__ = [
    "ClosureItem",
    "portfolio_witness_rank",
    "promotion_gate_state",
    "godelian_closure",
    "architecture_closure",
    "PORTFOLIO_STRATEGIES",
    "R3B_MANIFEST",
]

#: The four simulation strategies `simulation_residency` minimises over.  They
#: are METHODS of one party, not parties: one author, one repository, one
#: process, one circuit model.  Naming them here is what makes that explicit
#: enough to compute with.
PORTFOLIO_STRATEGIES = (
    "stabilizer_rank",
    "basis_permutation",
    "contraction",
    "free_fermion",
)

R3B_MANIFEST = "manifests/qsigma_r3b_four_cell_calibration_preregistration.json"


@dataclass
class ClosureItem:
    """One remainder, its blocker, and what would close it."""

    remainder: str
    blocked: bool
    measured: dict = field(default_factory=dict)
    blocker: str = ""
    closes_it: str = ""
    #: True when no act performed by this party can lift the blocker, whatever
    #: its quality or quantity.  This is the field the three items share.
    requires_another_party: bool = False


def portfolio_witness_rank(strategies=PORTFOLIO_STRATEGIES,
                           party: str = "hypercomplexbrain") -> dict:
    """Evidence rank of the simulation portfolio, read as a witness graph.

    Each strategy is modelled as recomputing the claim that another strategy
    produced -- the most generous possible reading, since ``recomputed`` is the
    highest mode `MODE_RANK` offers.  Every act is still performed by one party,
    so ``WitnessAct.rank`` returns 0 and the graph's evidence rank is NONE.

    This is the attestation-cycle theorem applied to methods rather than to
    people: a party checking its own arithmetic transmits nothing, and running
    four different algorithms is still one party checking its own arithmetic.
    """
    graph = WitnessGraph()
    for producer in strategies:
        for verifier in strategies:
            if producer == verifier:
                continue
            graph.add(WitnessAct(
                claim_id="q_sim_upper",
                producer=party,      # the METHOD differs; the party does not
                verifier=party,
                mode="recomputed",   # the most generous mode available
            ))
    rank = evidence_rank(graph, "q_sim_upper")
    return {
        "strategies": len(strategies),
        "acts": len(graph.acts),
        "distinct_parties": len(graph.parties),
        "evidence_rank": rank,
        "evidence_rank_name": {
            EvidenceRank.NONE: "NONE",
            EvidenceRank.ATTESTED: "ATTESTED",
            EvidenceRank.REVIEWED: "REVIEWED",
            EvidenceRank.INDEPENDENT: "INDEPENDENT",
        }[rank],
        "reaches_independent": rank >= EvidenceRank.INDEPENDENT,
    }


def promotion_gate_state(root) -> dict:
    """The R3B-0 promotion gate: what it demands and what it has."""
    manifest = json.loads((Path(root) / R3B_MANIFEST).read_text(encoding="utf-8"))
    cone = manifest["advantage_cone"]
    contract = manifest["outcome_contract"]
    return {
        "cone": cone["name"],
        "registered_outcome": cone["registered_outcome"],
        "hold_reasons": list(cone["hold_reasons"]),
        "audit_strength": float(cone["audit_strength"]),
        "audit_threshold": float(cone["audit_threshold"]),
        "audit_deficit": float(cone["audit_threshold"]) - float(cone["audit_strength"]),
        "coordinates": len(contract["coordinate_order"]),
        "observed": sorted(contract["observed"]),
        "missing": sorted(contract["missing"]),
    }


def godelian_closure(root) -> dict:
    """The self-audit's own verdict on whether it can close itself."""
    from .self_audit import self_audit

    audit = self_audit(root)
    return dict(audit["godelian_gap"])


def architecture_closure(root) -> dict:
    """The three remainders, and the predicate they share.

    Returns the items plus a joint statement.  The joint statement is only
    interesting because it is FALSIFIABLE: if a second party recomputes a result
    here, or audits the four-cell organ, the corresponding item stops being
    blocked and the join weakens.  Nothing in this repository can make that
    happen, which is the point.
    """
    root = Path(root)
    portfolio = portfolio_witness_rank()
    promotion = promotion_gate_state(root)
    godelian = godelian_closure(root)

    items = [
        ClosureItem(
            remainder="R1: the classical frontier is not closed",
            blocked=not portfolio["reaches_independent"],
            measured=portfolio,
            blocker=("every bound comes from a strategy this party wrote, so "
                     "agreement between strategies is one party checking its "
                     "own arithmetic and carries evidence rank "
                     f"{portfolio['evidence_rank_name']}"),
            closes_it="a bound computed by a party that is not this one",
            requires_another_party=True,
        ),
        ClosureItem(
            remainder="R2: measured-high does not mean thinks-better",
            blocked=promotion["registered_outcome"] != "PROMOTE",
            measured=promotion,
            blocker=(f"promote() requires audit >= {promotion['audit_threshold']} "
                     f"and audit strength is {promotion['audit_strength']}; "
                     f"{len(promotion['missing'])} of {promotion['coordinates']} "
                     "cone coordinates are also unmeasured"),
            closes_it=("an external audit of the organ, plus the four missing "
                       "coordinates; the audit is not tradeable against effect "
                       "size, so measuring the coordinates alone does not "
                       "promote"),
            requires_another_party=True,
        ),
        ClosureItem(
            remainder="R3: the self cannot close",
            blocked=not godelian["closable_from_inside"],
            measured=godelian,
            blocker=godelian["statement"],
            closes_it="a recomputation received from another party",
            requires_another_party=True,
        ),
    ]

    blocked = [item for item in items if item.blocked]
    return {
        "items": items,
        "blocked": len(blocked),
        "all_require_another_party": all(
            item.requires_another_party for item in blocked),
        "statement": (
            "The three remainders in ARCHITECTURE.md section 8 are one "
            "remainder. Each is blocked by the absence of an act performed by a "
            "party that is not this repository, and no internal act of any "
            "quality or quantity lifts any of them: the portfolio's agreement "
            "carries evidence rank "
            f"{portfolio['evidence_rank_name']}, the promotion gate holds an "
            f"audit deficit of {promotion['audit_deficit']:.1f}, and the "
            "self-audit reports closable_from_inside = "
            f"{godelian['closable_from_inside']}. The architecture is not "
            "incomplete in three ways; it is incomplete in one way, three "
            "times."),
    }
