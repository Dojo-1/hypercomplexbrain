"""Moving-frame audit: does a measurement see the object, or the frame?

The setting is taken from the source archive, which states it directly:

    X = (M, g_{2,2}, A, nabla, Omega, H, F, S, Pi, R)

with M the base, g_{2,2} the split metric, A the hypercomplex carrier, nabla the
connection / moving-frame transport, F the fiber bundle of local states, S the
sheaf of compatible local truths, and R the active remainder.  This repository
already instantiates most of it -- :mod:`aionq.sheaf` is S, :mod:`aionq.splitform`
is g_{2,2}, :mod:`aionq.cayley_dickson` is A, :mod:`aionq.governance` types R.

What is missing is **nabla as a moving frame**.  Every measurement in this
repository so far was taken in one fixed frame: one vertex labelling, one edge
ordering, one spanning tree, one gauge.  Round S4 found the consequence -- the S3
headline retains only a fifth of its effect after an admissible relabelling -- but
it found it with a single attack, which is a *pair* of frames rather than a path
through the frame bundle.

The diagnostic language comes from the same archive:

    "inertness is orbit-collapse; splitting is orbit-resolution"

That is exactly the right distinction, and it is sharper than "invariant or not":

    ORBIT-COLLAPSED   the measurement is constant on the frame orbit.  It sees
                      the orbit quotient -- the object -- and nothing else.
    ORBIT-RESOLVING   the measurement varies across the orbit.  It is reporting
                      frame coordinates.  Its variation may still be informative,
                      but it is information about the description, not the thing.

A measurement that is orbit-resolving is not therefore wrong.  It is *mistyped*:
it has been reported as a property of the sheaf when it is a property of the pair
(sheaf, frame).  The repository's rule for this case already exists -- demote to a
representation-sensitive diagnostic -- and this module supplies the instrument
that decides which quantities must be demoted.

Three observables
-----------------
**Orbit spread.**  The dispersion of a measurement over a sampled orbit.  Zero
means orbit-collapsed.

**Loop closure.**  Compose frames whose product is the identity.  The measurement
*must* return to its starting value exactly, because the composite acts trivially
on the object.  A nonzero closure defect is not frame-dependence -- it is hidden
state, and it is a bug rather than a finding.  This check has no analogue in a
single-attack design and it is the reason to build the path rather than the pair.

**Equivariance.**  Acting by f2 after f1 must equal acting by their composite.  If
it does not, the group action is implemented wrongly and every orbit statistic
above it is meaningless.  Checked before anything else is believed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .sheaf import CellularSheaf, Nerve

__all__ = ["Frame", "identity_frame", "random_frame", "compose", "invert",
           "act", "orbit", "OrbitReport", "orbit_report", "loop_closure",
           "equivariance_defect", "COLLAPSED", "RESOLVING"]

COLLAPSED = "orbit-collapsed"
RESOLVING = "orbit-resolving"


@dataclass(frozen=True)
class Frame:
    """One point in the fiber of the frame bundle over an instance.

    Three admissible reparametrisations, none of which changes the sheaf:

        vertex_perm   relabel the worldlets
        edge_order    present the overlaps in a different order, which grows a
                      different spanning tree and hence a different fundamental
                      cycle basis
        gauge         conjugate every transition by one orthogonal matrix

    ``edge_order[m]`` is the index of the old edge presented at new position m.

    An earlier version stored the edge part as a *shift and a reversal* and
    re-sorted the edge list on every action.  Sorting is a canonicalisation, not
    a group operation, so shifts did not compose and ``equivariance_defect``
    returned infinity -- correctly refusing every orbit statistic built on it.
    The edge part is an explicit permutation now, and no sorting happens at all,
    which also keeps canonicalisation available as a separate attack rather than
    baking it into the action.
    """

    vertex_perm: tuple
    edge_order: tuple
    gauge: np.ndarray

    @property
    def n_worldlets(self) -> int:
        return len(self.vertex_perm)

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"Frame(sigma={self.vertex_perm}, pi={self.edge_order}, |Q-I|="
                f"{np.linalg.norm(self.gauge - np.eye(self.gauge.shape[0])):.2f})")


def identity_frame(n_worldlets: int, dim: int, n_edges: int = 0) -> Frame:
    return Frame(tuple(range(n_worldlets)), tuple(range(n_edges)), np.eye(dim))


def random_frame(n_worldlets: int, dim: int, rng, n_edges: int = 0) -> Frame:
    q, r = np.linalg.qr(rng.normal(size=(dim, dim)))
    q = q * np.sign(np.diag(r))
    return Frame(tuple(int(x) for x in rng.permutation(n_worldlets)),
                 tuple(int(x) for x in rng.permutation(n_edges)), q)


def compose(f2: Frame, f1: Frame) -> Frame:
    """f2 after f1.  Both permutations compose; gauges multiply.

    For the edge part: f1 places old edge ``order1[m]`` at position m, then f2
    reads that list, so the composite places old edge ``order1[order2[m]]`` at m.
    """
    sigma = tuple(f2.vertex_perm[f1.vertex_perm[i]]
                  for i in range(len(f1.vertex_perm)))
    order = tuple(f1.edge_order[m] for m in f2.edge_order)
    return Frame(sigma, order, f2.gauge @ f1.gauge)


def invert(f: Frame) -> Frame:
    inv = [0] * len(f.vertex_perm)
    for i, p in enumerate(f.vertex_perm):
        inv[p] = i
    einv = [0] * len(f.edge_order)
    for m, k in enumerate(f.edge_order):
        einv[k] = m
    return Frame(tuple(inv), tuple(einv), f.gauge.T)


def act(nerve: Nerve, sheaf: CellularSheaf, frame: Frame) -> tuple:
    """Transport an instance into a new frame.

    Returns ``(nerve', sheaf', edge_map)`` where ``edge_map[k]`` is the new index
    of old edge ``k``.  The sheaf is unchanged as a mathematical object; only its
    presentation moves.
    """
    sigma = frame.vertex_perm
    order = list(frame.edge_order) or list(range(nerve.n_edges))
    edges = tuple((sigma[nerve.edges[k][0]], sigma[nerve.edges[k][1]])
                  for k in order)
    new_nerve = Nerve(nerve.n_worldlets, edges)
    q = frame.gauge
    new_sheaf = CellularSheaf(new_nerve,
                              [q @ sheaf.transitions[k] @ q.T for k in order],
                              sheaf.fiber_dim,
                              labels=None)
    edge_map = np.empty(len(order), dtype=int)
    for new_idx, old_idx in enumerate(order):
        edge_map[old_idx] = new_idx
    return new_nerve, new_sheaf, edge_map


# --------------------------------------------------------------------------
# Orbit statistics
# --------------------------------------------------------------------------

@dataclass
class OrbitReport:
    """What a measurement does across the frame orbit."""

    name: str
    values: list
    identity_value: float
    loop_closure_defect: float = 0.0
    tolerance: float = 1e-9
    notes: list = field(default_factory=list)

    @property
    def spread(self) -> float:
        return float(np.std(self.values)) if len(self.values) > 1 else 0.0

    @property
    def range(self) -> float:
        return float(np.max(self.values) - np.min(self.values)) if self.values else 0.0

    @property
    def max_deviation(self) -> float:
        """Worst departure from the identity-frame value.  Worst case, not mean.

        An invariant that holds on average and fails on one admissible frame is
        not an invariant.
        """
        return max((abs(v - self.identity_value) for v in self.values), default=0.0)

    @property
    def classification(self) -> str:
        return COLLAPSED if self.max_deviation <= self.tolerance else RESOLVING

    @property
    def is_invariant(self) -> bool:
        return self.classification == COLLAPSED

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"{self.name:<26}{self.identity_value:>9.4f}"
                f"{self.max_deviation:>12.4f}{self.spread:>10.4f}"
                f"  {self.classification}")


def orbit(measure, nerve, sheaf, labels, frames) -> tuple:
    """Evaluate ``measure(nerve, sheaf, labels)`` at every frame in ``frames``.

    ``measure`` receives the transported instance with labels already permuted,
    so an instrument never has to know it is being audited.
    """
    values = []
    for f in frames:
        n2, s2, emap = act(nerve, sheaf, f)
        lab2 = np.zeros(n2.n_edges, dtype=bool)
        lab2[emap[np.flatnonzero(labels)]] = True
        values.append(float(measure(n2, s2, lab2)))
    return values


def orbit_report(name, measure, nerve, sheaf, labels, frames,
                 tolerance: float = 1e-9) -> OrbitReport:
    ident = identity_frame(nerve.n_worldlets, sheaf.fiber_dim, nerve.n_edges)
    base = orbit(measure, nerve, sheaf, labels, [ident])[0]
    values = orbit(measure, nerve, sheaf, labels, frames)
    closure = loop_closure(measure, nerve, sheaf, labels, frames)
    return OrbitReport(name=name, values=values, identity_value=base,
                       loop_closure_defect=closure, tolerance=tolerance)


def loop_closure(measure, nerve, sheaf, labels, frames) -> float:
    """Compose a frame with its own inverse; the measurement must return exactly.

    This is not a frame-dependence test.  The composite acts trivially on the
    object, so any nonzero result is hidden state carried between runs -- a bug,
    not a finding.  It is the check a single-frame-pair attack cannot perform.
    """
    ident = identity_frame(nerve.n_worldlets, sheaf.fiber_dim, nerve.n_edges)
    base = orbit(measure, nerve, sheaf, labels, [ident])[0]
    worst = 0.0
    for f in frames[:8]:
        closed = compose(invert(f), f)
        got = orbit(measure, nerve, sheaf, labels, [closed])[0]
        worst = max(worst, abs(got - base))
    return float(worst)


def equivariance_defect(nerve, sheaf, f1: Frame, f2: Frame) -> float:
    """Acting by f2 after f1 must equal acting by ``compose(f2, f1)``.

    Checked before any orbit statistic is believed: if the group action is wrong,
    every number built on it is meaningless.
    """
    n1, s1, _ = act(nerve, sheaf, f1)
    n12, s12, _ = act(n1, s1, f2)
    nc, sc, _ = act(nerve, sheaf, compose(f2, f1))
    if n12.edges != nc.edges:
        return float("inf")
    return max(float(np.linalg.norm(a - b))
               for a, b in zip(s12.transitions, sc.transitions))
