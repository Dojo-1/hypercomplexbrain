"""The nerve is a nerve, evidence is a connection, HOLD is a stratum.

These are not new claims dressed in geometry. They are the geometry of claims
the repository already proved, and stating it makes three things computable
that were not:

* why no internal act lifts the evidence rank -- the nerve of a one-party cover
  is a POINT, so there is no degree-1 part for an obstruction to live in;
* why attestation cycles are bounded -- the evidence connection is FLAT on
  them, holonomy zero after the first edge;
* why `HOLD` is not a refusal -- the effect vector sits on a stratum where the
  cone's inequalities are not evaluable, and the projection onto the measured
  coordinates is exact because the cone is a product.
"""

from __future__ import annotations

import pytest

from aionq.self_audit import repo_root
from aionq.witness_geometry import (attestation_holonomy, cone_stratum,
                                    party_nerve)
from aionq.witness_nerve import EvidenceRank, WitnessAct, WitnessGraph


def _portfolio_graph(party: str = "self") -> WitnessGraph:
    """The four simulation strategies, every ordered pair, one party."""
    graph = WitnessGraph()
    strategies = ("stabilizer_rank", "basis_permutation", "contraction",
                  "free_fermion")
    for producer in strategies:
        for verifier in strategies:
            if producer != verifier:
                graph.add(WitnessAct("q_sim_upper", party, party, "recomputed"))
    return graph


# ------------------------------------------------------------------ the nerve

def test_a_one_party_nerve_is_a_point():
    """The dimension count that replaces the philosophical statement.

    Twelve acts, all self-loops, no 1-simplex with distinct endpoints. The
    obstruction to independence is not non-zero here; there is nowhere to write
    it down.
    """
    shape = party_nerve(_portfolio_graph())
    assert shape.parties == 1
    assert shape.self_loops == 12
    assert shape.edges == 0
    assert shape.triangles == 0
    assert shape.dimension == 0
    assert not shape.has_room_for_independence
    assert shape.euler_characteristic == 1


def test_a_self_loop_is_not_a_low_quality_edge_it_is_not_an_edge():
    """`WitnessAct.rank` returning 0 is this fact about the base, not the fibre.

    Quality lives in the fibre -- the mode, the care taken, the number of
    strategies. None of it can help, because the problem is that the base has
    no 1-cells.
    """
    graph = WitnessGraph()
    for mode in ("attested", "reviewed", "recomputed"):
        graph.add(WitnessAct("c", "self", "self", mode))
    shape = party_nerve(graph)
    assert shape.self_loops == 3
    assert shape.edges == 0
    assert shape.dimension == 0


def test_two_parties_create_the_1_simplex_that_independence_needs():
    """The falsifier: it is the shared party that flattens the nerve.

    Relabelling the same acts to distinct parties produces an edge immediately,
    so nothing about the modelling forces dimension 0.
    """
    graph = WitnessGraph()
    graph.add(WitnessAct("c", "A", "B", "recomputed"))
    shape = party_nerve(graph)
    assert shape.parties == 2
    assert shape.edges == 1
    assert shape.dimension == 1
    assert shape.has_room_for_independence


def test_three_mutually_witnessing_parties_close_a_triangle():
    graph = WitnessGraph()
    for producer, verifier in (("A", "B"), ("B", "C"), ("A", "C")):
        graph.add(WitnessAct("c", producer, verifier, "reviewed"))
    shape = party_nerve(graph)
    assert (shape.parties, shape.edges, shape.triangles) == (3, 3, 1)
    assert shape.dimension == 2
    assert shape.euler_characteristic == 1     # a filled triangle


# ------------------------------------------------------------------- flatness

def test_the_evidence_connection_is_flat_on_attestation_loops():
    """The attestation-cycle theorem, restated as holonomy.

    Once the graph carries an attestation, going around a loop of them
    transports the rank back to where it started. That is what "cannot
    manufacture independence" means geometrically.
    """
    base = WitnessGraph().add(WitnessAct("c", "A", "B", "attested"))
    cycle = WitnessGraph()
    for producer, verifier in (("A", "B"), ("B", "C"), ("C", "A")):
        cycle.add(WitnessAct("c", producer, verifier, "attested"))

    transport = attestation_holonomy(base, "c", cycle)
    assert transport["holonomy"] == 0
    assert transport["flat"]
    assert transport["bounded_by_attested"]


def test_the_first_attestation_is_not_free():
    """The correction the original theorem missed, kept as a live check.

    The first version claimed attestation cycles are inert. They are not: when
    the cycle is the only support, the first traversal lifts NONE to ATTESTED.
    An attestation is not nothing; it is bounded.
    """
    cycle = WitnessGraph()
    for producer, verifier in (("A", "B"), ("B", "C"), ("C", "A")):
        cycle.add(WitnessAct("c", producer, verifier, "attested"))

    transport = attestation_holonomy(WitnessGraph(), "c", cycle)
    assert transport["rank_before"] == EvidenceRank.NONE
    assert transport["rank_after"] == EvidenceRank.ATTESTED
    assert transport["holonomy"] == 1
    assert transport["bounded_by_attested"]


def test_no_number_of_attestation_loops_reaches_independent():
    graph = WitnessGraph()
    for round_number in range(20):
        for producer, verifier in (("A", "B"), ("B", "C"), ("C", "A")):
            graph.add(WitnessAct("c", producer, verifier, "attested"))
    from aionq.witness_nerve import evidence_rank
    assert evidence_rank(graph, "c") == EvidenceRank.ATTESTED


# -------------------------------------------------------------- the stratum

def test_hold_is_a_stratum_where_membership_is_not_posed():
    """Four NaN coordinates put the effect vector where K is not evaluable.

    `AdvantageCone.contains` returns False there, correctly -- a point that
    cannot be shown inside must not be treated as inside. But False and OUTSIDE
    are different statements, and only one of them is a scientific result.
    """
    stratum = cone_stratum(repo_root())
    assert stratum.coordinates == 8
    assert len(stratum.measured) == 4
    assert len(stratum.unmeasured) == 4
    assert stratum.codimension == 4
    assert not stratum.posed


def test_the_measured_sub_vector_is_interior_to_the_projected_cone():
    """The substantive result, and it is not a null one.

    The cone's constraints are per-coordinate and uncoupled, so the projection
    onto the measured coordinates is EXACT rather than an approximation. On
    that projection the organ's effect clears every margin, by roughly a factor
    of 2.5 on each. The science is not what is blocking promotion.
    """
    stratum = cone_stratum(repo_root())
    assert stratum.projected_inside
    assert set(stratum.slack) == set(stratum.measured)
    for dimension, slack in stratum.slack.items():
        assert slack > 0.0, dimension
    # Comfortably interior, not marginal.
    assert min(stratum.slack.values()) > 0.1


def test_every_unmeasured_axis_is_only_no_worse():
    """So the four missing coordinates are the weaker of the two blockers.

    They demand no improvement at all -- only that nothing degrades past the
    tolerance. The audit deficit is the load-bearing one.
    """
    stratum = cone_stratum(repo_root())
    assert stratum.detail["unmeasured_are_all_no_worse"]


def test_the_audit_deficit_stands_regardless_of_the_geometry():
    """Closing the stratum would not promote the organ.

    `promote()` treats audit as not tradeable against effect size, so a fully
    measured, comfortably interior effect vector still yields HOLD while
    audit_strength is 0.0. This is remainder 3 holding remainder 2 shut.
    """
    stratum = cone_stratum(repo_root())
    assert stratum.detail["registered_outcome"] == "HOLD"
    assert stratum.detail["audit_strength"] == 0.0
    assert stratum.detail["audit_threshold"] == 1.0
    assert stratum.projected_inside      # and yet


def test_blocked_by_science_distinguishes_the_two_failures():
    """A cone failure and a missing coordinate must not read the same."""
    stratum = cone_stratum(repo_root())
    assert not stratum.blocked_by_science
    assert stratum.projected_inside and not stratum.posed
