"""The geometry the repository was already using, named.

Two structures here were built without their geometry stated, and stating it
changes what can be computed about them.

I. THE WITNESS NERVE IS A NERVE.

`witness_nerve.py` is named for the nerve of a cover and behaves like one.
Parties are the patches.  An act between two parties is a 1-simplex, an
agreement among three is a 2-simplex, and *evidence is a connection*: each act
transports a claim's rank from producer to verifier.

Read that way, the Gödelian gap stops being a limitation and becomes a
dimension count.  The self-audit says every predicate this repository can
express about its own artifacts is decidable *here* -- that is: every section is
locally defined.  What is missing is a gluing condition, and a gluing condition
lives on overlaps.  With one party the cover has one patch, the nerve is a
POINT, and there are no 1-simplices with distinct endpoints at all.

    The obstruction to closing the self is not that H^1 is non-zero.
    It is that the complex has no degree-1 part in which an obstruction
    could live.

That is why no internal act of any quality lifts the rank: quality is a property
of the fibre, and the problem is the base.  The portfolio result follows
immediately -- four simulation strategies are four methods of one party, so the
nerve of the portfolio is a point, and `evidence_rank` is NONE however many
strategies agree.

The attestation-cycle theorem is a FLATNESS statement in this reading.  A cycle
of attestations is a loop in the nerve, and the theorem says its holonomy adds
nothing beyond the first edge: transport around the loop returns ATTESTED, never
accumulating.  Only `recomputed` edges carry non-trivial transport.  The
repository proved flatness of the evidence connection on attestation loops and
recorded it as an inequality.

II. `HOLD` IS A STRATUM, NOT A REFUSAL.

The advantage cone K is a region in the 8-dimensional outcome space: a product
of per-coordinate half-spaces, `improve` dimensions requiring more than their
margin and `no_worse` dimensions requiring more than minus the tolerance.

The R3B-0 effect vector has four finite coordinates and four NaN.  It therefore
does not lie inside K, and it does not lie outside K.  It lies on a stratum
where K's defining inequalities are not evaluable, and `AdvantageCone.contains`
returns False there -- correctly, since a point that cannot be shown inside must
not be treated as inside.  But False and OUTSIDE are different geometric
statements, and the registered outcome is HOLD precisely because the question is
not posed rather than answered no.

Because the constraints are per-coordinate and uncoupled, K is a product, and
the projection onto the measured coordinates is EXACT rather than an
approximation: pi(K) is just the product of the measured coordinates' own
constraints.  So the conditional question is well posed and answerable --

    does the measured sub-vector lie in pi(K)?

and answering it separates a scientific failure from a missing audit.  Measured:
it does, on every axis, by a factor of about 2.5.  The organ's measured
cognitive effect is interior to the admissible region with margin, and it is
still not promotable, because `audit_strength` is 0.0 against a threshold of
1.0.  Remainder 3 is what holds remainder 2 shut, with numbers.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from .witness_nerve import EvidenceRank, WitnessAct, WitnessGraph, evidence_rank

__all__ = [
    "NerveShape",
    "party_nerve",
    "attestation_holonomy",
    "ConeStratum",
    "cone_stratum",
    "R3B_ARTIFACT",
    "R3B_MANIFEST",
]

R3B_MANIFEST = "manifests/qsigma_r3b_four_cell_calibration_preregistration.json"
R3B_ARTIFACT = "artifacts/r3b_four_cell/four_cell_calibration.json"


@dataclass
class NerveShape:
    """The simplicial shape of a witness graph's party nerve."""

    parties: int
    edges: int              # 1-simplices: pairs of DISTINCT parties joined
    triangles: int          # 2-simplices: mutually joined triples
    self_loops: int         # acts whose verifier is their producer

    @property
    def dimension(self) -> int:
        if self.triangles:
            return 2
        if self.edges:
            return 1
        return 0

    @property
    def has_room_for_independence(self) -> bool:
        """Whether a 1-simplex with distinct endpoints exists at all.

        Independence is a property of an overlap.  With no overlap it is not
        false; there is nowhere for it to be stated.
        """
        return self.edges > 0

    @property
    def euler_characteristic(self) -> int:
        return self.parties - self.edges + self.triangles


def party_nerve(graph: WitnessGraph) -> NerveShape:
    """The nerve of the cover whose patches are parties.

    A self-loop -- an act whose verifier is its producer -- contributes a
    0-simplex and nothing else.  That is the geometric content of
    ``WitnessAct.rank`` returning 0 for such an act: it is not a low-quality
    edge, it is not an edge.
    """
    parties = sorted(graph.parties)
    index = {party: position for position, party in enumerate(parties)}
    adjacency = {position: set() for position in index.values()}
    self_loops = 0

    for act in graph.acts:
        if act.producer == act.verifier:
            self_loops += 1
            continue
        left, right = index[act.producer], index[act.verifier]
        adjacency[left].add(right)
        adjacency[right].add(left)

    edges = {frozenset((position, other))
             for position, others in adjacency.items() for other in others}
    triangles = sum(
        1 for triple in combinations(sorted(index.values()), 3)
        if all(frozenset(pair) in edges for pair in combinations(triple, 2)))

    return NerveShape(parties=len(parties), edges=len(edges),
                      triangles=triangles, self_loops=self_loops)


def attestation_holonomy(graph: WitnessGraph, claim_id: str,
                         cycle: WitnessGraph) -> dict:
    """Transport of evidence around an attestation loop.

    The attestation-cycle theorem says ``evidence_rank(G + C) =
    max(evidence_rank(G), ATTESTED)``.  Expressed as transport: the holonomy of
    the evidence connection around an attestation loop is the identity once the
    graph already carries an attestation, so the loop is FLAT and going around
    it again buys nothing.

    Returned ``holonomy`` is the rank gained by traversing the loop.  It is
    non-zero only in the one case the theorem's first, wrong version missed:
    when the cycle is the sole support, the first traversal lifts NONE to
    ATTESTED.  An attestation is not nothing; it is bounded.
    """
    before = evidence_rank(graph, claim_id)
    combined = WitnessGraph(list(graph.acts) + list(cycle.acts))
    after = evidence_rank(combined, claim_id)
    return {
        "rank_before": before,
        "rank_after": after,
        "holonomy": after - before,
        "flat": after == before,
        "bounded_by_attested": after <= max(before, EvidenceRank.ATTESTED),
    }


@dataclass
class ConeStratum:
    """Where an effect vector sits relative to a pre-registered cone."""

    coordinates: int
    measured: tuple = ()
    unmeasured: tuple = ()
    #: Constrained coordinates that are NaN.  The membership question is not
    #: posed on this stratum; it is not answered no.
    codimension: int = 0
    posed: bool = False
    #: Does the measured sub-vector lie in the projection of the cone?  Exact,
    #: because the cone is a product of per-coordinate constraints.
    projected_inside: bool = False
    slack: dict = field(default_factory=dict)
    detail: dict = field(default_factory=dict)

    @property
    def blocked_by_science(self) -> bool:
        """True when the measured axes themselves fail the cone."""
        return self.posed is False and not self.projected_inside


def cone_stratum(root, include_derived: bool = False) -> ConeStratum:
    """Locate the R3B-0 effect vector relative to its registered cone.

    ``include_derived`` admits the QSigma-R3B-1 parity derivation, which closes
    ``neg_energy`` and ``neg_latency`` at an exact zero for every cost model
    that is a function of the resource profile.  It is off by default: a derived
    coordinate and a measured one are different objects, and the caller should
    have to ask for them to be mixed.
    """
    root = Path(root)
    manifest = json.loads((root / R3B_MANIFEST).read_text(encoding="utf-8"))
    artifact = json.loads((root / R3B_ARTIFACT).read_text(encoding="utf-8"))

    cone = manifest["advantage_cone"]
    order = tuple(manifest["outcome_contract"]["coordinate_order"])
    effect = artifact["paired_seed_cluster_posterior"]["mean_effect"]
    constraints = cone["constraints"]
    margins = cone.get("margins", {})
    tolerance = float(cone["no_worse_tolerance"])

    derived_axes: dict = {}
    if include_derived:
        from .parity_derived import derive_parity_axes

        derivation = derive_parity_axes(root)
        if derivation.premise_holds:
            derived_axes = {name: entry["delta"]
                            for name, entry in derivation.derived.items()}

    measured, unmeasured = [], []
    for name in order:
        value = derived_axes.get(name, effect.get(name))
        if value is None or not math.isfinite(float(value)):
            unmeasured.append(name)
        else:
            measured.append(name)
            effect[name] = float(value)

    constrained_unmeasured = [name for name in unmeasured
                              if constraints.get(name, "free") != "free"]

    slack, inside = {}, True
    for name in measured:
        value = float(effect[name])
        rule = constraints.get(name, "free")
        if rule == "improve":
            floor = float(margins.get(name, 0.0))
            slack[name] = value - floor
            if value <= floor:
                inside = False
        elif rule == "no_worse":
            slack[name] = value + tolerance
            if value < -tolerance:
                inside = False

    return ConeStratum(
        coordinates=len(order),
        measured=tuple(measured),
        unmeasured=tuple(unmeasured),
        codimension=len(constrained_unmeasured),
        posed=not constrained_unmeasured,
        projected_inside=inside,
        slack=slack,
        detail={
            "cone": cone["name"],
            "registered_outcome": cone["registered_outcome"],
            "audit_strength": float(cone["audit_strength"]),
            "audit_threshold": float(cone["audit_threshold"]),
            "unmeasured_are_all_no_worse": all(
                constraints.get(name) == "no_worse"
                for name in constrained_unmeasured),
            "derived_axes": tuple(sorted(derived_axes)),
            "reading": (
                "the effect vector lies on a stratum of codimension "
                f"{len(constrained_unmeasured)} where the cone's inequalities "
                "are not evaluable, so membership is NOT POSED rather than "
                "answered no. Projected onto the measured coordinates the cone "
                "is exact, because its constraints are per-coordinate and "
                f"uncoupled, and the measured sub-vector is "
                f"{'INSIDE' if inside else 'OUTSIDE'} that projection."),
        },
    )
