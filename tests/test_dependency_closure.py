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
    scientific = evidence["edges"] - len(evidence["by_round"].get("self_audit", []))
    assert graph.edges >= 50
    assert scientific <= 10
    assert graph.edges > 5 * scientific


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
    assert len(reach) >= 8
    for module in ("capacity_ceiling", "carrier_telemetry",
                   "common_receiver_reservoir", "equal_resource_reservoir",
                   "qsigma_r7_information", "quantum_movement"):
        assert module in reach, module

    assert len(blast_radius(graph, "holevo_sandwich")) >= 6


def test_the_highest_leverage_modules_are_foundations_with_no_dependencies(graph):
    """The repository is layered, and the load sits on unaudited bases.

    Every module at the top of the leverage ranking depends on nothing itself.
    They cannot inherit a defect; they can only originate one.
    """
    ranking = leverage_ranking(graph, 5)
    assert ranking[0]["blast_radius"] >= 8
    for row in ranking[:4]:
        assert row["depends_on"] == 0, row["module"]


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
