"""What a defect would reach, and what the evidence says it would reach.

Every round in this repository is audited from inside itself.  That is the
right scale for finding a wrong tolerance or an unreached guard, and it is the
wrong scale for one question: *if this is wrong, what else is wrong?*

Two graphs answer it differently.

    THE CODE GRAPH.  Which module imports which.  60 local edges across 58
    modules; 18 among the round modules alone.  This is the graph a defect
    actually travels along, because a result computed by a module that imports
    another module inherits that module's correctness.

    THE EVIDENCE GRAPH.  Which artifact references which other round.  FOUR
    edges across 26 rounds, and not one artifact declares an upstream key at
    all.  Nine rounds reference nothing.

The round names promise a descent -- unitary price, operational information,
Hopf layer, Holevo sandwich, carrier telemetry, capacity ceiling, translation
epsilon, equal resource, common receiver, source information, quantum movement
-- and the artifacts do not compose in anything like that shape.  ``r6l``
references ``r6k``, which proves the mechanism exists and works.  Its absence
elsewhere is therefore informative rather than accidental.

The consequence is not abstract.  Measured here:

    _principal_psd_sqrt, the non-portable matrix square root that cost a full
    round of investigation, is inherited by ZERO modules.  It is a leaf.  The
    defect was contained, and nothing in the round that found it established
    that -- the containment was assumed by not being asked about.

    hyperbolic_qubit is inherited by TEN modules, spanning R6e, R6f, R6h, R6k,
    R6l, R7, R8, ohnium and part B.  holevo_sandwich by SEVEN.  Neither
    relationship is recorded in any artifact, so a defect in either would
    propagate across most of the R6-to-R8 arc without any evidence surface
    showing it had.

That asymmetry is the finding.  Attention had been going to the module with
blast radius zero while the modules with blast radius seven and ten went
unexamined, and no instrument in the repository was positioned to say so.

This module computes both graphs and their difference.  It does not repair the
evidence graph: writing upstream keys into sealed artifacts would be editing
results after the fact, which is the one thing the provenance discipline
forbids.  What it can do is make the omission visible and rank the surface by
leverage.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ModuleGraph",
    "build_module_graph",
    "blast_radius",
    "dependency_closure",
    "evidence_edges",
    "leverage_ranking",
]


@dataclass
class ModuleGraph:
    """Local import structure of the ``aionq`` package."""

    imports: dict = field(default_factory=dict)      # module -> modules it uses
    importers: dict = field(default_factory=dict)    # module -> modules using it

    @property
    def modules(self) -> set:
        return set(self.imports)

    @property
    def edges(self) -> int:
        return sum(len(targets & self.modules)
                   for targets in self.imports.values())


def build_module_graph(root) -> ModuleGraph:
    """Parse local ``aionq`` imports without importing anything.

    Static, so a module that fails to import still contributes its edges, and
    so no side effect of an import can influence the graph being measured.
    """
    package = Path(root) / "src" / "aionq"
    imports: dict = {}
    for path in sorted(package.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level or "aionq" in node.module:
                    tail = node.module.split(".")[-1]
                    if tail:
                        used.add(tail)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("aionq."):
                        used.add(alias.name.split(".")[-1])
        imports[path.stem] = used - {path.stem}

    known = set(imports)
    importers = {name: set() for name in known}
    for name, targets in imports.items():
        for target in targets & known:
            importers[target].add(name)
    return ModuleGraph(imports=imports, importers=importers)


def _closure(start: str, graph: dict, universe: set) -> set:
    seen, stack = set(), [start]
    while stack:
        current = stack.pop()
        for neighbour in graph.get(current, ()):
            if neighbour in universe and neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return seen


def dependency_closure(graph: ModuleGraph, module: str) -> set:
    """Everything ``module`` transitively relies on."""
    return _closure(module, graph.imports, graph.modules)


def blast_radius(graph: ModuleGraph, module: str) -> set:
    """Everything that would inherit a defect in ``module``.

    The set a round's own audit cannot see, because it is the set of rounds
    that are not the one being audited.
    """
    return _closure(module, graph.importers, graph.modules)


def evidence_edges(root) -> dict:
    """Cross-round references actually present in the artifacts.

    A reference is counted when one round's result mentions another round's
    artifact directory by name.  Generous on purpose: the point is that even a
    permissive count finds almost nothing.
    """
    artifacts = Path(root) / "artifacts"
    rounds = sorted(entry.name for entry in artifacts.iterdir() if entry.is_dir())
    found: dict = {}
    declares_upstream = 0
    for name in rounds:
        referenced = set()
        for path in sorted((artifacts / name).rglob("*.json")):
            if path.name.endswith(".envelope.json"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):  # pragma: no cover
                continue
            if '"upstream"' in text:
                declares_upstream += 1
            referenced |= {other for other in rounds
                           if other != name and other in text}
        found[name] = sorted(referenced)
    return {
        "rounds": len(rounds),
        "edges": sum(len(targets) for targets in found.values()),
        "rounds_referencing_nothing": sum(
            1 for targets in found.values() if not targets),
        "artifacts_declaring_upstream": declares_upstream,
        "by_round": found,
    }


def leverage_ranking(graph: ModuleGraph, limit: int = 10) -> list:
    """Modules ordered by how much would inherit a defect in them.

    This is the ranking an audit should follow and did not.  A module with
    blast radius zero can be wrong without endangering another round; a module
    with blast radius ten is a single point of failure for most of the arc.
    """
    scored = [
        {
            "module": name,
            "blast_radius": len(blast_radius(graph, name)),
            "depends_on": len(dependency_closure(graph, name)),
            "inherited_by": sorted(blast_radius(graph, name)),
        }
        for name in sorted(graph.modules)
    ]
    scored.sort(key=lambda row: (-row["blast_radius"], row["module"]))
    return scored[:limit]
