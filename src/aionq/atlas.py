"""The Quantum Necessity Atlas: quantumness is not a scalar and not Euclidean.

QSigma-R made a real correction and then repeated the original mistake one level
up.  It killed an additive scalar (Q_naive) and installed a different scalar
(Q_cert) in the same slot.  A single ordered axis cannot carry the question,
because at least four inequivalent things were being conflated:

    classical simulation upper bound
        != certified quantum necessity
        != physical quantum residency
        != cognitive advantage

A Clifford fault-tolerant memory has q_sim_upper ~ 0 and is *not* "zero quantum":
it is genuinely quantum tissue whose current dynamics happen to admit an
efficient classical description.  A syntactically magic-heavy identity circuit
has q_sim_upper > 0 and does no work at all.  Any scalar that orders these two
wrongly is the wrong instrument.

The replacement has three structural features, each forced by a specific defect
rather than chosen for ornament.

1.  It is interval-valued, not point-valued.
    Exhibiting a good classical algorithm bounds cost from above.  Proving no
    better one exists is a different and much harder problem.  So the honest
    object is [q_sim_lower, q_sim_upper], with q_sim_lower = 0 until a real
    lower-bound argument or a named complexity assumption is supplied.

2.  It is a section of a bundle, not a vector.
    Resource monotones are defined only relative to a free theory.  Magic is
    magic *with respect to* stabilizer states and Clifford operations; under a
    non-Clifford change of frame a stabilizer state can become a magic state.
    So the resource coordinate is a fiber over a base of free theories, and
    "how much resource does this state have" is not a well-posed question until
    a base point is named.  :func:`resource_over` makes this numerical: the same
    state returns 1.0 over one base point and 0.0 over another.

3.  Its base is hyperbolic, not Euclidean.
    Free theories are ordered by containment -- classical reversible inside
    stabilizer inside Clifford+T inside universal -- and that containment order
    branches.  Tree-like hierarchies embed with bounded distortion in hyperbolic
    space and with unbounded distortion in Euclidean space of any fixed
    dimension, because the number of nodes at depth d grows exponentially while
    Euclidean volume grows polynomially.  Flattening the base to a Euclidean
    scalar axis is precisely the error of ranking resource theories along a
    line.  The base is therefore the Poincare ball and comparisons use
    :func:`poincare_distance`.

Promotion to "this organ is quantum in a way that matters" requires
``q_causal > 0`` against a matched free-theory control.  Hardness alone never
promotes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .residency import max_bipartite_entanglement, stabilizer_renyi_entropy

__all__ = [
    "FreeTheory",
    "FREE_THEORIES",
    "poincare_distance",
    "embed_hierarchy",
    "resource_over",
    "Interval",
    "QuantumNecessityAtlas",
    "PromotionVerdict",
]


# --------------------------------------------------------------------------
# Interval arithmetic: the honest shape of a bound
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Interval:
    """A bound that knows what it does not know."""

    lower: float
    upper: float
    justification: str = "upper bound only"

    def __post_init__(self) -> None:
        if self.lower > self.upper + 1e-12:
            raise ValueError(f"invalid interval [{self.lower}, {self.upper}]")

    @property
    def width(self) -> float:
        """Epistemic width: how much is not known."""
        return self.upper - self.lower

    @property
    def certain(self) -> bool:
        return self.width < 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"[{self.lower:.3f}, {self.upper:.3f}]"


# --------------------------------------------------------------------------
# The base space: free theories ordered by containment
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class FreeTheory:
    """A base point: what counts as free, and which frames preserve that.

    A resource monotone is meaningless without this.  ``admissible_group`` is the
    set of frame transformations under which the monotone is invariant; outside
    it, resource claims do not transport.
    """

    name: str
    free_states: str
    free_operations: str
    admissible_group: str
    monotone: str
    contains: tuple = ()   # free theories strictly contained in this one

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.name} (monotone: {self.monotone}, frames: {self.admissible_group})"


CLASSICAL = FreeTheory(
    name="classical-reversible",
    free_states="computational basis states",
    free_operations="permutations of the basis",
    admissible_group="basis permutations",
    monotone="coherence (relative entropy of coherence)",
)

STABILIZER = FreeTheory(
    name="stabilizer",
    free_states="stabilizer states",
    free_operations="Clifford + Pauli measurement",
    admissible_group="Clifford group",
    monotone="stabilizer Renyi entropy (magic)",
    contains=("classical-reversible",),
)

MATCHGATE = FreeTheory(
    name="matchgate / free-fermion",
    free_states="fermionic Gaussian states",
    free_operations="matchgate circuits",
    admissible_group="Gaussian (Bogoliubov) transformations",
    monotone="non-Gaussianity",
    contains=("classical-reversible",),
)

SEPARABLE = FreeTheory(
    name="separable",
    free_states="product states",
    free_operations="LOCC",
    admissible_group="local unitaries",
    monotone="entanglement entropy",
    contains=("classical-reversible",),
)

UNIVERSAL = FreeTheory(
    name="universal",
    free_states="none",
    free_operations="none",
    admissible_group="full unitary group",
    monotone="(no nontrivial monotone)",
    contains=("stabilizer", "matchgate / free-fermion", "separable"),
)

FREE_THEORIES = (CLASSICAL, STABILIZER, MATCHGATE, SEPARABLE, UNIVERSAL)


# --------------------------------------------------------------------------
# Hyperbolic base geometry
# --------------------------------------------------------------------------

def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Geodesic distance in the Poincare ball.

    d(u,v) = arcosh(1 + 2|u-v|^2 / ((1-|u|^2)(1-|v|^2)))

    Used instead of Euclidean distance because the base is a branching
    containment hierarchy: sibling free theories must be farther from each other
    than from their common parent, and that separation grows without bound as
    the hierarchy deepens.  Euclidean space of fixed dimension cannot supply it.
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    nu, nv = float(u @ u), float(v @ v)
    if nu >= 1.0 or nv >= 1.0:
        raise ValueError("points must lie strictly inside the unit ball")
    num = 2.0 * float((u - v) @ (u - v))
    return float(np.arccosh(1.0 + num / ((1.0 - nu) * (1.0 - nv))))


def hierarchy_distortion(depth: int, spread: float = 0.95) -> dict:
    """Measure, do not assert, the cost of flattening a hierarchy.

    Builds a complete binary containment tree of the given depth, embeds it in
    the Poincare disk and in the Euclidean plane by the same radial rule, and
    reports the worst-case multiplicative distortion of each embedding against
    the true tree metric.

    The hyperbolic advantage is asymptotic in depth.  At two levels it is small;
    the point of this function is to show where it becomes decisive rather than
    to claim it everywhere.
    """
    nodes: list[tuple[int, int]] = []
    for d in range(depth + 1):
        for k in range(2 ** d):
            nodes.append((d, k))

    def tree_distance(a, b) -> int:
        (da, ka), (db, kb) = a, b
        steps = 0
        while da > db:
            ka //= 2; da -= 1; steps += 1
        while db > da:
            kb //= 2; db -= 1; steps += 1
        while ka != kb:
            ka //= 2; kb //= 2; steps += 2
        return steps

    def place(node, hyperbolic: bool):
        d, k = node
        angle = 2.0 * math.pi * (k + 0.5) / max(1, 2 ** d)
        radius = spread * (1.0 - 2.0 ** (-d)) if hyperbolic else spread * d / max(1, depth)
        return np.array([radius * math.cos(angle), radius * math.sin(angle)])

    def distortion(hyperbolic: bool) -> float:
        ratios = []
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                td = tree_distance(a, b)
                if td == 0:
                    continue
                pa, pb = place(a, hyperbolic), place(b, hyperbolic)
                ed = (poincare_distance(pa, pb) if hyperbolic
                      else float(np.linalg.norm(pa - pb)))
                if ed <= 1e-12:
                    return math.inf
                ratios.append(ed / td)
        return max(ratios) / min(ratios)

    return {
        "depth": depth,
        "nodes": len(nodes),
        "hyperbolic_distortion": distortion(True),
        "euclidean_distortion": distortion(False),
    }


def embed_hierarchy(theories=FREE_THEORIES, spread: float = 0.72) -> dict:
    """Embed the containment hierarchy of free theories in the Poincare disk.

    Depth in the containment order maps to hyperbolic radius; siblings are
    spread by angle.  The root (universal, the least free theory) sits near the
    origin and the most restrictive theories sit near the boundary, which is
    where hyperbolic volume is.
    """
    by_name = {t.name: t for t in theories}

    def depth(t: FreeTheory) -> int:
        if not t.contains:
            return 0
        return 1 + max(depth(by_name[c]) for c in t.contains if c in by_name)

    max_depth = max(depth(t) for t in theories)
    order = sorted(theories, key=lambda t: (-depth(t), t.name))

    coords: dict[str, np.ndarray] = {}
    level_counts: dict[int, int] = {}
    for t in order:
        d = max_depth - depth(t)
        level_counts[d] = level_counts.get(d, 0) + 1

    seen: dict[int, int] = {}
    for t in order:
        d = max_depth - depth(t)
        seen[d] = seen.get(d, 0) + 1
        k, total = seen[d] - 1, level_counts[d]
        angle = 2.0 * math.pi * k / max(1, total)
        radius = spread * (1.0 - math.exp(-1.2 * d))
        coords[t.name] = np.array([radius * math.cos(angle), radius * math.sin(angle)])
    return coords


# --------------------------------------------------------------------------
# The fiber: a resource monotone is only defined over a base point
# --------------------------------------------------------------------------

def _relative_entropy_of_coherence(state: np.ndarray) -> float:
    """Coherence in the computational basis: S(diag(rho)) - S(rho)."""
    vec = np.asarray(state, dtype=complex).ravel()
    vec = vec / np.linalg.norm(vec)
    probs = np.clip(np.abs(vec) ** 2, 1e-18, None)
    probs = probs / probs.sum()
    return float(-np.sum(probs * np.log2(probs)))  # pure state: S(rho) = 0


def resource_over(state: np.ndarray, theory: FreeTheory) -> float:
    """Resource content of `state` measured over the free theory `theory`.

    The point of this function is that it is not a property of the state alone.
    The same state returns different numbers over different base points, which
    is why "how quantum is it" has no answer until a free theory is named.
    """
    if theory.name == CLASSICAL.name:
        return _relative_entropy_of_coherence(state)
    if theory.name == STABILIZER.name:
        return stabilizer_renyi_entropy(state)
    if theory.name == SEPARABLE.name:
        n = int(math.log2(len(np.asarray(state).ravel())))
        return max_bipartite_entanglement(state) if n >= 2 else 0.0
    if theory.name == MATCHGATE.name:
        # Placeholder: a real non-Gaussianity monotone is not implemented.
        return float("nan")
    return 0.0  # universal: nothing is free, so nothing is a resource


# --------------------------------------------------------------------------
# The atlas
# --------------------------------------------------------------------------

@dataclass
class PromotionVerdict:
    promoted: bool
    reason: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{'PROMOTE' if self.promoted else 'HOLD'}: {self.reason}"


@dataclass
class QuantumNecessityAtlas:
    """Eight coordinates, several interval-valued, over a named free theory.

    No coordinate dominates another and there is no total order.  Comparing two
    organs means comparing sections, which is a partial order plus a hyperbolic
    distance on the base -- not a subtraction of scalars.
    """

    organ: str
    base: FreeTheory

    q_phys: float = 0.0          # state/transitions in protected quantum dof
    q_coh: float = 0.0           # coherence actually *used* by interference
    q_resource: float = 0.0      # monotone over `base` (fiber-dependent)
    q_process: float = 0.0       # non-Markovian temporal memory, bits
    q_logical: float = 0.0       # code distance / recoverability
    q_sim: Interval = field(default_factory=lambda: Interval(0.0, 0.0))
    q_causal: float = 0.0        # task gain over matched free-theory control
    q_audit: float = 0.0         # external certification strength

    def promote(self, threshold: float = 0.0) -> PromotionVerdict:
        """Cognitive gain is the decisive gate. Hardness alone never promotes."""
        if self.q_causal > threshold:
            return PromotionVerdict(True, f"q_causal = {self.q_causal:.3f} > {threshold} "
                                          "against a matched free-theory control")
        if self.q_sim.upper > 0.5:
            return PromotionVerdict(False, f"hard to simulate (q_sim {self.q_sim}) but "
                                           f"q_causal = {self.q_causal:.3f}: hardness "
                                           "without cognitive gain does not promote")
        return PromotionVerdict(False, f"q_causal = {self.q_causal:.3f}: no measured "
                                       "advantage over the matched control")

    def dominates(self, other: "QuantumNecessityAtlas") -> bool:
        """Partial order: better in every coordinate, worse in none."""
        mine = self._vector()
        theirs = other._vector()
        return all(a >= b - 1e-12 for a, b in zip(mine, theirs)) and mine != theirs

    def _vector(self) -> tuple:
        return (self.q_phys, self.q_coh, self.q_resource, self.q_process,
                self.q_logical, self.q_sim.lower, self.q_causal, self.q_audit)

    def base_distance(self, other: "QuantumNecessityAtlas", coords=None) -> float:
        """Hyperbolic distance between the two organs' free theories."""
        coords = coords or embed_hierarchy()
        return poincare_distance(coords[self.base.name], coords[other.base.name])

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"organ        : {self.organ}",
            f"base theory  : {self.base.name}  (monotone: {self.base.monotone})",
            f"  q_phys     : {self.q_phys:.3f}      physical/logical residency",
            f"  q_coh      : {self.q_coh:.3f}      coherence actually used",
            f"  q_resource : {self.q_resource:.3f}      over this base only",
            f"  q_process  : {self.q_process:.3f}      non-Markovian memory (bits)",
            f"  q_logical  : {self.q_logical:.3f}      protected recoverability",
            f"  q_sim      : {self.q_sim}   simulation-cost interval",
            f"  q_causal   : {self.q_causal:.3f}      task gain vs matched control",
            f"  q_audit    : {self.q_audit:.3f}      external certification",
            f"verdict      : {self.promote()}",
        ])
