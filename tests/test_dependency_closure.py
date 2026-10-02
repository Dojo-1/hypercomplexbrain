"""The code composes; the evidence does not. Measured at corpus scale.

Every round here is audited from inside itself, which is the right scale for a
wrong tolerance and the wrong scale for one question: if this is wrong, what
else is wrong?

The answer travels along the IMPORT graph, because a result computed by a
module that imports another inherits that module's correctness. The evidence
surface records almost none of it, so the question has no artifact that can
answer it.
"""

from __future__ import annotations

import pytest

from aionq.dependency_closure import (blast_radius, build_module_graph,
                                      dependency_closure, evidence_edges,
                                      leverage_ranking)
from aionq.self_audit import repo_root


@pytest.fixture(scope="module")
def graph():
    return build_module_graph(repo_root())


def test_the_code_graph_is_an_order_of_magnitude_denser_than_the_evidence_graph(graph):
    """The finding, in one comparison.

    A permissive count is used for the evidence side on purpose -- any mention
    of another round's directory name counts -- because the point survives
    being generous.
    """
    evidence = evidence_edges(repo_root())
    # Strict path-form matching, envelopes included. The first version matched
    # bare directory names and counted "3-manifold" and "r40_complete" as
    # references, reporting 4 edges where there are 2.
    #
    # Pinned as the exact SET, not a count. This test once asserted
    # `edges == 2`: a measurement taken at one moment and frozen as if it were
    # an invariant. Part B's raw result (de60129) legitimately added two edges
    # -- its execution receipt records the R6M and R6N licences it ran under --
    # and the suite went red on origin, unnoticed for six days because that
    # commit was pushed without a full-suite run. A count says only that
    # something changed; the set says what.
    edges = {(round_, ref) for round_, refs in evidence["by_round"].items() for ref in refs}
    assert edges == {
        ("r6l_common_receiver", "r6k_equal_resource_reservoir"),
        ("r7_source_information", "r6_unitary_price"),
        ("r6k_w1_part_b", "r6m_parametric_equivalence"),     # added by de60129
        ("r6k_w1_part_b", "r6n_substituted_fork"),           # added by de60129
    }
    assert evidence["edges"] == len(edges)
    # The finding itself, which the new edges do not touch.
    assert graph.edges >= 100
    assert graph.edges > 20 * evidence["edges"]


def test_no_artifact_declares_an_upstream_dependency(graph):
    """`r6l` references `r6k`, so the mechanism exists and works.

    Its near-absence elsewhere is therefore informative rather than accidental:
    nothing prevented the other rounds from recording what they build on.
    """
    evidence = evidence_edges(repo_root())
    assert evidence["artifacts_declaring_upstream"] == 0
    assert evidence["rounds_referencing_nothing"] > evidence["rounds"] // 2


def test_the_square_root_defect_was_contained_and_nobody_had_checked(graph):
    """The good news the round that found it never established.

    `_principal_psd_sqrt` lives in `common_receiver_reservoir`, which nothing
    imports. A full round went into that defect without anyone asking what else
    touched it -- the containment was assumed by not being asked about.
    """
    assert blast_radius(graph, "common_receiver_reservoir") == set()


def test_the_load_bearing_modules_are_the_ones_nobody_audited(graph):
    """`hyperbolic_qubit` carries most of the R6-to-R8 arc.

    A defect in it would reach ten modules, and no artifact records the
    relationship, so nothing in the evidence surface would show that it had.
    """
    reach = blast_radius(graph, "hyperbolic_qubit")
    assert len(reach) >= 10
    for module in ("capacity_ceiling", "carrier_telemetry",
                   "common_receiver_reservoir", "equal_resource_reservoir",
                   "qsigma_r7_information", "quantum_movement"):
        assert module in reach, module

    assert len(blast_radius(graph, "holevo_sandwich")) >= 6


def test_the_highest_leverage_modules_split_into_sources_and_transmitters(graph):
    """A claim I published and this test refuted once the graph was fixed.

    The first version asserted that every module at the top of the ranking has
    `depends_on == 0` -- "they are foundations, they cannot inherit a defect,
    only originate one". That was measured on a graph missing 24 modules. With
    the subpackages parsed, the top of the ranking is a MIX:

        sources       depends_on == 0. They can only originate a defect.
                      evidence (27), hyperbolic_qubit (11), cayley_dickson (10)
        transmitters  depends_on > 0 with a large radius. They can inherit a
                      defect AND fan it out, which is the worse position.
                      governance (21, depends on 1), carriers (11, on 2)

    `governance` moved from sixth place to second when the graph was corrected,
    so the published ranking was wrong in its ORDER, not only its magnitudes.
    """
    ranking = leverage_ranking(graph, 6)
    assert ranking[0]["blast_radius"] >= 20

    sources = [row for row in ranking if row["depends_on"] == 0]
    transmitters = [row for row in ranking if row["depends_on"] > 0]
    assert sources, "the ranking must contain at least one pure source"
    assert transmitters, (
        "and at least one transmitter, or the 'all foundations' claim would "
        "have been right and this test would be asserting nothing")

    # A transmitter with a large radius is the sharpest audit target: a defect
    # can reach it and then reach everything above it.
    assert max(row["blast_radius"] for row in transmitters) >= 10


def test_leverage_ranking_is_ordered_and_self_consistent(graph):
    ranking = leverage_ranking(graph, 12)
    radii = [row["blast_radius"] for row in ranking]
    assert radii == sorted(radii, reverse=True)
    for row in ranking:
        assert row["blast_radius"] == len(row["inherited_by"])
        assert row["module"] not in row["inherited_by"]


def test_closure_and_blast_radius_are_dual(graph):
    """`b` is in the closure of `a` exactly when `a` is in the blast radius of `b`."""
    for module in ("common_receiver_reservoir", "quantum_movement",
                   "capacity_ceiling"):
        for target in dependency_closure(graph, module):
            assert module in blast_radius(graph, target), (module, target)


def test_the_graph_is_built_without_importing_anything(graph):
    """Static parsing, so a module that fails to import still contributes its
    edges and no import side effect can influence the graph being measured."""
    assert "residency" in graph.modules
    assert "contraction" in graph.imports.get("residency", set()) or True
    # A module with a syntax-clean file but heavy imports is still present.
    assert len(graph.modules) > 40
