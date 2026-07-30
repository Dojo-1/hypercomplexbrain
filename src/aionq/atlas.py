"""The Quantum Necessity Atlas over a universal Poincare base.

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
    So the resource coordinate belongs to a named free-theory fiber/index, and
    "how much resource does this state have" is not a well-posed question until
    that full specification is named.  :func:`resource_over` makes this
    numerical: the same state returns 1.0 in one fiber and 0.0 in another.

3.  Its architectural base is the universal Poincare atlas ``H^n``.
    This is an A-tagged coordinate contract, not an empirical conclusion from
    the five-node free-theory graph.  The earlier K13 measurement remains valid:
    that graph has delta/diameter = 0.5 and does not *earn* curvature from
    tree-likeness.  ``FreeTheory`` therefore remains a categorical fiber/index;
    it is placed in ``H^n`` by a declared chart, not identified with the
    hyperbolic metric.  A dimension-matched Euclidean chart remains the ablation.

Promotion requires a pre-registered advantage cone over the outcome vector --
see :mod:`aionq.advantage`.  The scalar gate ``q_causal > 0`` is retired:
hardness never promotes, and neither does a single asserted number.
"""

from __future__ import annotations

import math
import hashlib
import json
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from .hyperbolic import (
    PoincareBallBase,
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
)
from .quantities import (Bits, Effect, Fraction, IncommensurableError, Monotone,
                         Quantity, Strength, coerce)
from .residency import max_bipartite_entanglement, stabilizer_renyi_entropy

__all__ = [
    "FreeTheory",
    "FREE_THEORIES",
    "ALL_FREE",
    "MINIMAL_FREE",
    "IncomparableFibersError",
    "Transport",
    "free_theory_graph_metric",
    "gromov_delta",
    "compare_embeddings_on_real_hierarchy",
    "poincare_distance",
    "embed_hierarchy",
    "place_free_theories_on_universal_base",
    "resource_over",
    "Interval",
    "QuantumNecessityAtlas",
    "PromotionVerdict",
    "IntervalOrder",
    "UNIVERSAL_POINCARE_BASE",
    "UNIVERSAL_EUCLIDEAN_CONTROL",
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
    """A categorical fiber/index: what is free and which frames preserve it.

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

# Formerly named UNIVERSAL with free_states="none" and free_operations="none",
# which was semantically inverted: if nothing is free then almost everything is a
# resource, yet resource_over returned 0.  The containment order also requires
# this node to be the *largest* free set, since free sets grow upward
# (stabilizer states are a subset of all states).  Corrected to ALL_FREE.
ALL_FREE = FreeTheory(
    name="all-free",
    free_states="all states",
    free_operations="all unitaries and measurements",
    admissible_group="full unitary group",
    monotone="(none: every monotone vanishes when everything is free)",
    contains=("stabilizer", "matchgate / free-fermion", "separable"),
)

# The opposite orientation, kept explicit so the inversion cannot recur.
MINIMAL_FREE = FreeTheory(
    name="minimal-free",
    free_states="a single fiducial state",
    free_operations="identity only",
    admissible_group="trivial group",
    monotone="(almost every state carries resource)",
)

UNIVERSAL = ALL_FREE   # backwards-compatible alias

FREE_THEORIES = (CLASSICAL, STABILIZER, MATCHGATE, SEPARABLE, ALL_FREE)


# --------------------------------------------------------------------------
# Universal Poincare base and its matched Euclidean chart
# --------------------------------------------------------------------------

def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Geodesic distance in the Poincare ball.

    The stable form

        d(u,v) = 2 asinh(|u-v| / sqrt((1-|u|^2)(1-|v|^2)))

    resolves very small separations that cancel in ``arcosh(1 + epsilon)``.
    This is the curvature ``-1`` specialization used by legacy callers.
    Typed atlas sections use :data:`UNIVERSAL_POINCARE_BASE` directly.
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    if u.ndim != 1 or v.ndim != 1 or u.shape != v.shape:
        raise ValueError("Poincare points must be equal-size one-dimensional arrays")
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(v)):
        raise ValueError("Poincare points must be finite")
    nu, nv = float(u @ u), float(v @ v)
    if nu >= 1.0 or nv >= 1.0:
        raise ValueError("points must lie strictly inside the unit ball")
    ratio = float(np.linalg.norm(u - v)) / math.sqrt((1.0 - nu) * (1.0 - nv))
    return float(2.0 * np.arcsinh(ratio))


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


def place_free_theories_on_universal_base(
    theories=FREE_THEORIES,
    spread: float = 0.72,
    geometric_base: PoincareBallBase = UNIVERSAL_POINCARE_BASE,
) -> dict:
    """Place the free-theory index category in the universal Poincare chart.

    Depth controls radius, but the directions span ``H^n`` rather than a disk.
    This declared placement does not assert that graph distance equals
    hyperbolic distance; K13 remains the counterexample to that inference.
    """
    if not isinstance(geometric_base, PoincareBallBase):
        raise TypeError(
            "universal placement needs a typed PoincareBallBase"
        )
    theories = tuple(theories)
    if not theories:
        raise ValueError("free-theory index must not be empty")
    if any(not isinstance(theory, FreeTheory) for theory in theories):
        raise TypeError("every free-theory index entry must be a FreeTheory")
    if (
        isinstance(spread, (bool, np.bool_))
        or not np.isfinite(spread)
        or not 0.0 < float(spread) < 1.0
    ):
        raise ValueError(
            "spread must be finite and satisfy 0 < spread < 1 in the unit-ball chart"
        )
    by_name = {t.name: t for t in theories}
    if len(by_name) != len(theories):
        raise ValueError("free-theory index names must be unique")
    dangling = sorted({
        child
        for theory in theories
        for child in theory.contains
        if child not in by_name
    })
    if dangling:
        raise ValueError(
            f"free-theory index has unresolved containment names: {dangling}"
        )

    memo: dict[str, int] = {}
    visiting: set[str] = set()
    def depth(t: FreeTheory) -> int:
        if t.name in memo:
            return memo[t.name]
        if t.name in visiting:
            raise ValueError(
                f"free-theory containment must be acyclic; cycle at {t.name!r}"
            )
        visiting.add(t.name)
        value = (
            0
            if not t.contains
            else 1 + max(depth(by_name[child]) for child in t.contains)
        )
        visiting.remove(t.name)
        memo[t.name] = value
        return value

    order = sorted(theories, key=lambda t: (-depth(t), t.name))

    coords: dict[str, np.ndarray] = {}
    for t in order:
        identity_payload = json.dumps(
            {
                "name": t.name,
                "free_states": t.free_states,
                "free_operations": t.free_operations,
                "admissible_group": t.admissible_group,
                "monotone": t.monotone,
                "contains": list(t.contains),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        seed = int.from_bytes(
            hashlib.sha256(identity_payload).digest()[:8],
            byteorder="big",
            signed=False,
        )
        direction_rng = np.random.default_rng(seed)
        direction = direction_rng.normal(size=geometric_base.dimension)
        direction_norm = float(np.linalg.norm(direction))
        if not math.isfinite(direction_norm) or direction_norm <= 0.0:
            raise ValueError(f"failed to derive a direction for {t.name!r}")
        direction = direction / direction_norm
        # Radius depends only on this object's containment depth.  Adding an
        # unrelated object cannot adiabatically move an existing atlas point.
        radius = spread / (1.0 + depth(t))
        coords[t.name] = geometric_base.point(
            radius * direction,
            f"free_theory:{t.name}",
        )
    collisions = [
        (left.name, right.name)
        for left, right in combinations(order, 2)
        if geometric_base.distance(coords[left.name], coords[right.name])
        <= geometric_base.tolerance
    ]
    if collisions:
        raise ValueError(
            "free-theory placement is not injective in this base dimension: "
            f"{collisions}"
        )
    return coords


def embed_hierarchy(theories=FREE_THEORIES, spread: float = 0.72) -> dict:
    """Legacy two-dimensional placement used to reproduce the K13 audit.

    This function is intentionally frozen: changing it would rewrite the
    historical 5.29/6.64 distortion result.  Live atlas sections use
    :func:`place_free_theories_on_universal_base`.
    """

    by_name = {theory.name: theory for theory in theories}

    def depth(theory: FreeTheory) -> int:
        if not theory.contains:
            return 0
        return 1 + max(
            depth(by_name[child])
            for child in theory.contains
            if child in by_name
        )

    maximum_depth = max(depth(theory) for theory in theories)
    order = sorted(theories, key=lambda theory: (-depth(theory), theory.name))
    level_counts: dict[int, int] = {}
    for theory in order:
        level = maximum_depth - depth(theory)
        level_counts[level] = level_counts.get(level, 0) + 1

    seen: dict[int, int] = {}
    coordinates = {}
    for theory in order:
        level = maximum_depth - depth(theory)
        seen[level] = seen.get(level, 0) + 1
        index, total = seen[level] - 1, level_counts[level]
        angle = 2.0 * math.pi * index / max(1, total)
        radius = spread * (1.0 - math.exp(-1.2 * level))
        coordinates[theory.name] = np.array(
            [radius * math.cos(angle), radius * math.sin(angle)]
        )
    return coordinates


# --------------------------------------------------------------------------
# The fiber: a resource monotone is defined by a full FreeTheory specification
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
    The same state returns different numbers in different fibers, which is why
    "how quantum is it" has no answer until a complete free theory is named.
    """
    if not isinstance(theory, FreeTheory):
        raise TypeError("resource theory must be a FreeTheory")
    registered = FREE_THEORIES + (MINIMAL_FREE,)
    if theory not in registered:
        raise ValueError(
            "unregistered FreeTheory specification; a canonical name alone "
            "does not select a resource monotone"
        )
    vec = np.asarray(state, dtype=complex).ravel()
    if vec.size == 0 or not (
        np.all(np.isfinite(vec.real)) and np.all(np.isfinite(vec.imag))
    ):
        raise ValueError("state vector must be non-empty and finite")
    norm = float(np.linalg.norm(vec))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("state vector must have finite non-zero norm")
    vec = vec / norm

    if theory == CLASSICAL:
        return _relative_entropy_of_coherence(vec)
    if theory == STABILIZER:
        return stabilizer_renyi_entropy(vec)
    if theory == SEPARABLE:
        n = int(math.log2(len(vec)))
        return max_bipartite_entanglement(vec) if n >= 2 else 0.0
    if theory == MATCHGATE:
        # Placeholder: a real non-Gaussianity monotone is not implemented.
        return float("nan")
    if theory == ALL_FREE:
        return 0.0      # everything is free, so nothing is a resource
    if theory == MINIMAL_FREE:
        # Almost nothing is free, so almost every state carries resource.  Use
        # distance from the fiducial |0...0>.
        return float(1.0 - abs(vec[0]) ** 2)
    raise AssertionError("registered FreeTheory dispatch is incomplete")


# --------------------------------------------------------------------------
# The atlas
# --------------------------------------------------------------------------

class IntervalOrder:
    """How to order two simulation-cost intervals.

    ``_vector`` previously fed only ``q_sim.lower`` into the coordinatewise
    comparison.  Since the lower bound is 0 absent a hardness argument, that
    made the simulation coordinate inert: organs with intervals [0, 0.05] and
    [0, 1.00] compared equal.  An interval order has to be chosen explicitly.
    """

    GUARANTEED = "guaranteed"      # self.lower >= other.upper: true under any refinement
    OPTIMISTIC = "optimistic"      # compare upper bounds: best-known hardness
    INFORMATION = "information"    # no weaker bound, and strictly narrower

    ALL = (GUARANTEED, OPTIMISTIC, INFORMATION)

    @staticmethod
    def compare(a: "Interval", b: "Interval", policy: str) -> bool:
        """Is `a` at least as good as `b` under `policy`?"""
        if policy == IntervalOrder.GUARANTEED:
            return a.lower >= b.upper - 1e-12
        if policy == IntervalOrder.OPTIMISTIC:
            return a.upper >= b.upper - 1e-12
        if policy == IntervalOrder.INFORMATION:
            return (a.lower >= b.lower - 1e-12 and a.upper <= b.upper + 1e-12)
        raise ValueError(f"unknown interval order policy {policy!r}")


class IncomparableFibersError(TypeError):
    """Raised when two sections over different free theories are compared."""


@dataclass
class Transport:
    """A section moved between charts, with a typed account of the move."""

    section: "QuantumNecessityAtlas"
    preserved: tuple
    transformed: tuple
    lost: tuple
    remainder: str
    evidence: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"transported to : {self.section.base.name}",
            f"  preserved    : {', '.join(self.preserved) or '-'}",
            f"  transformed  : {', '.join(self.transformed) or '-'}",
            f"  lost         : {', '.join(self.lost) or '-'}",
            f"  remainder    : {self.remainder}",
            f"  evidence     : {self.evidence}",
        ])


@dataclass
class PromotionVerdict:
    promoted: bool
    reason: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{'PROMOTE' if self.promoted else 'HOLD'}: {self.reason}"


@dataclass
class QuantumNecessityAtlas:
    """Eight coordinates in a fiber over a named point of universal ``H^n``.

    No coordinate dominates another and there is no total order.  Comparing two
    organs means comparing sections within one free-theory fiber: a partial
    order on typed coordinates plus an explicit :class:`IntervalOrder` policy.
    The legacy field name ``base`` denotes that free-theory index; the geometric
    base is explicitly ``geometric_base``.
    """

    organ: str
    base: FreeTheory
    geometric_base: PoincareBallBase = field(
        default_factory=lambda: UNIVERSAL_POINCARE_BASE,
        kw_only=True,
    )
    base_point: np.ndarray | None = field(default=None, kw_only=True)

    q_phys: Fraction | float = 0.0      # state/transitions in protected quantum dof
    q_coh: Fraction | float = 0.0       # coherence actually *used* by interference
    q_resource: Monotone | float = 0.0  # monotone over `base` (fiber-dependent)
    q_process: Bits | float = 0.0       # non-Markovian temporal memory, bits
    q_logical: Fraction | float = 0.0   # code distance / recoverability
    q_sim: Interval = field(default_factory=lambda: Interval(0.0, 0.0))
    q_causal: Effect | float = 0.0      # task gain over matched free-theory control
    q_audit: Strength | float = 0.0     # external certification strength

    def __post_init__(self) -> None:
        if not isinstance(self.base, FreeTheory):
            raise TypeError("atlas base index must be a FreeTheory")
        if not isinstance(self.geometric_base, PoincareBallBase):
            raise TypeError("atlas geometric_base must be a PoincareBallBase")
        if self.geometric_base.scope != "universal_atlas":
            raise ValueError("atlas geometric base must have universal_atlas scope")
        if self.base_point is None:
            if self.base not in FREE_THEORIES:
                raise ValueError(
                    "an unregistered FreeTheory needs an explicit universal-base "
                    "point; a canonical name alone does not identify a fiber"
                )
            placement = place_free_theories_on_universal_base(
                geometric_base=self.geometric_base,
            )
            if self.base.name not in placement:
                raise ValueError(
                    f"free theory {self.base.name!r} has no universal-base placement"
                )
            self.base_point = placement[self.base.name]
        else:
            self.base_point = self.geometric_base.point(
                self.base_point,
                f"atlas:{self.organ}.base_point",
            )
        # Coordinates are stored typed, not as bare floats.  This is what makes
        # the comparison rules enforceable rather than advisory: `q_process` in
        # bits can no longer be ranked against `q_audit` in audit-strength, and
        # `q_resource` carries the free theory it was computed over.
        self.q_phys = coerce(self.q_phys, Fraction)
        self.q_coh = coerce(self.q_coh, Fraction)
        self.q_resource = coerce(self.q_resource, Monotone, base=self.base.name)
        self.q_process = coerce(self.q_process, Bits)
        self.q_logical = coerce(self.q_logical, Fraction)
        self.q_causal = coerce(self.q_causal, Effect)
        self.q_audit = coerce(self.q_audit, Strength)

    @property
    def free_theory(self) -> FreeTheory:
        """Unambiguous name for the legacy ``base`` field."""

        return self.base

    def promote(self, posterior=None, cone=None, **kwargs) -> PromotionVerdict:
        """Promotion requires a pre-registered advantage cone.

        The scalar gate ``q_causal > 0`` is retired.  It was the last monarch
        over the atlas: it silently chose a weighting across generalisation,
        robustness, latency, energy and calibration, and it promoted an organ
        whose gain was bought entirely by spending latency.

        Calling this without a cone does **not** fall back to the scalar.  It
        returns HOLD, because a stored ``q_causal`` float is an assertion, not a
        measurement against a matched free-theory control.  Supply an
        :class:`aionq.advantage.EffectPosterior` and
        :class:`aionq.advantage.AdvantageCone` to obtain a real decision.
        """
        if posterior is None or cone is None:
            return PromotionVerdict(
                False,
                "no pre-registered advantage cone supplied. The scalar "
                "q_causal gate is retired; see aionq.advantage.promote(). "
                f"(stored q_causal = {self.q_causal} is an assertion, not a "
                "measured effect against a matched control)")

        from .advantage import promote as _cone_promote
        decision = _cone_promote(posterior, cone, audit=float(self.q_audit), **kwargs)
        return PromotionVerdict(decision.promoted, str(decision))

    def dominates(self, other: "QuantumNecessityAtlas",
                  interval_policy: str = IntervalOrder.GUARANTEED) -> bool:
        """Partial order, valid only within one fiber.

        Raises if the two sections lie over different free theories.  Comparing
        1.2 bits of magic against 0.9 bits of entanglement because both are
        Python floats is exactly the flattening this object exists to prevent:
        the monotones measure different things and are not commensurable.
        Transport one section into the other's chart first -- see
        :meth:`transport_to` -- and read the declared remainder before comparing.
        """
        if interval_policy not in IntervalOrder.ALL:
            raise ValueError(f"unknown interval order policy {interval_policy!r}")
        if self.base != other.base:
            raise IncomparableFibersError(
                f"cannot compare a section over '{self.base.name}' "
                f"(monotone: {self.base.monotone}) with one over "
                f"'{other.base.name}' (monotone: {other.base.monotone}). "
                "FreeTheory specifications, not names alone, identify fibers. "
                "Transport to a common chart first; see transport_to()."
            )
        if self.geometric_base.to_spec() != other.geometric_base.to_spec():
            raise IncomparableFibersError(
                "cannot compare sections carried by different geometric bases"
            )
        if self.geometric_base.distance(self.base_point, other.base_point) > 1e-10:
            raise IncomparableFibersError(
                "same free-theory label is attached to different base points"
            )
        mine = self._vector()
        theirs = other._vector()
        scalars_ok = all(a >= b - 1e-12 for a, b in zip(mine, theirs))
        interval_ok = IntervalOrder.compare(self.q_sim, other.q_sim, interval_policy)
        strict = mine != theirs or (self.q_sim.lower, self.q_sim.upper) != (
            other.q_sim.lower, other.q_sim.upper)
        return scalars_ok and interval_ok and strict

    def transport_to(self, target: FreeTheory) -> "Transport":
        """Move this section into another chart, declaring what is lost.

        Base-relative coordinates do not survive a change of free theory.  This
        returns the transported section together with a typed account of what
        was preserved, transformed, lost, and what remainder the transport
        leaves -- never a silently rebased number.
        """
        if not isinstance(target, FreeTheory):
            raise TypeError("transport target must be a FreeTheory")
        if target == self.base:
            return Transport(self, preserved=("all",), transformed=(), lost=(),
                             remainder="none: identity transport",
                             evidence="same base point")
        if target not in FREE_THEORIES:
            raise ValueError(
                "transport target has no registered universal-base point; "
                "matching a canonical name is insufficient"
            )

        moved = QuantumNecessityAtlas(
            organ=self.organ, base=target,
            geometric_base=self.geometric_base,
            q_phys=self.q_phys, q_coh=self.q_coh,
            q_resource=float("nan"),          # not transportable without recompute
            q_process=self.q_process, q_logical=self.q_logical,
            q_sim=self.q_sim, q_causal=float("nan"), q_audit=self.q_audit)

        return Transport(
            moved,
            preserved=("q_phys", "q_process", "q_logical", "q_sim", "q_audit"),
            transformed=("free_theory_fiber", "geometric_base_point"),
            lost=("q_resource", "q_causal"),
            remainder=(f"q_resource must be recomputed as {target.monotone}; "
                       f"q_causal is task- and control-relative and does not "
                       f"transport with the base"),
            evidence="no free conversion between these theories is implemented",
        )

    def _vector(self) -> tuple:
        """Scalar coordinates only.  q_sim is an interval and is ordered separately
        by an explicit :class:`IntervalOrder` policy, never collapsed to one end."""
        return tuple(float(v) for v in (self.q_phys, self.q_coh, self.q_resource,
                                        self.q_process, self.q_logical,
                                        self.q_causal, self.q_audit))

    def base_distance(self, other: "QuantumNecessityAtlas") -> float:
        """Live distance in the shared universal Poincare atlas."""

        if self.geometric_base.to_spec() != other.geometric_base.to_spec():
            raise IncomparableFibersError(
                "base distance needs one shared universal Poincare specification"
            )
        return self.geometric_base.distance(self.base_point, other.base_point)

    def experimental_poincare_instrument(
        self,
        other: "QuantumNecessityAtlas",
        coords=None,
    ) -> float:
        """Deprecated compatibility alias for the now-live base distance."""

        import warnings
        warnings.warn(
            "experimental_poincare_instrument is deprecated; use base_distance. "
            "K13 remains historical evidence against graph-inferred curvature.",
            DeprecationWarning,
            stacklevel=2,
        )
        if coords is None:
            return self.base_distance(other)
        return poincare_distance(
            coords[self.base.name],
            coords[other.base.name],
        )

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"organ        : {self.organ}",
            f"free theory  : {self.base.name}  (monotone: {self.base.monotone})",
            f"geometry     : {self.geometric_base.id} @ "
            f"{np.asarray(self.base_point).round(4).tolist()}",
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


# --------------------------------------------------------------------------
# The geometry of the ACTUAL base, not a synthetic tree
# --------------------------------------------------------------------------

def free_theory_graph_metric(theories=FREE_THEORIES) -> tuple:
    """Shortest-path metric on the real containment structure.

    :func:`hierarchy_distortion` measures a *synthetic complete binary tree*.
    The live free-theory structure is not that tree: classical-reversible sits
    below three separate parents, so the Hasse diagram contains a diamond and is
    a DAG rather than a tree.  Any geometric claim about "the hierarchy" must be
    tested against this graph, not against the synthetic one.

    Returns ``(names, distance_matrix)``.
    """
    names = [t.name for t in theories]
    index = {n: i for i, n in enumerate(names)}
    n = len(names)

    inf = float("inf")
    dist = np.full((n, n), inf)
    np.fill_diagonal(dist, 0.0)
    for t in theories:
        for child in t.contains:
            if child in index:
                i, j = index[t.name], index[child]
                dist[i, j] = dist[j, i] = 1.0

    for k in range(n):                      # Floyd-Warshall
        dist = np.minimum(dist, dist[:, k][:, None] + dist[None, k, :])
    return names, dist


def gromov_delta(dist: np.ndarray) -> float:
    """Gromov four-point hyperbolicity constant of a finite metric.

    For every quadruple, form the three pairings S1, S2, S3 and sort them; the
    local defect is (S_max - S_mid)/2.  delta = 0 exactly for tree metrics, and
    grows as the space becomes less tree-like.  A hyperbolic embedding is only
    indicated when delta is small relative to the diameter.
    """
    n = dist.shape[0]
    worst = 0.0
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    sums = sorted([
                        dist[a, b] + dist[c, d],
                        dist[a, c] + dist[b, d],
                        dist[a, d] + dist[b, c],
                    ])
                    worst = max(worst, (sums[2] - sums[1]) / 2.0)
    return float(worst)


def compare_embeddings_on_real_hierarchy() -> dict:
    """Reproduce the frozen K13 free-theory-graph diagnostic.

    Reports the Gromov delta of the live free-theory graph, its diameter, and
    the normalised ratio delta/diameter.  A tree gives 0.  Values near 0.5 mean
    the structure is not tree-like, so that graph does not *induce* or
    empirically earn a hyperbolic metric.  This narrow result is preserved
    independently of the A-tagged universal Poincare atlas: graph distance is
    not declared to be the atlas metric.
    """
    names, dist = free_theory_graph_metric()
    finite = dist[np.isfinite(dist)]
    diameter = float(finite.max())
    delta = gromov_delta(dist)

    coords = embed_hierarchy()
    hyp, euc, tru = [], [], []
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j <= i or not np.isfinite(dist[i, j]):
                continue
            tru.append(dist[i, j])
            hyp.append(poincare_distance(coords[a], coords[b]))
            euc.append(float(np.linalg.norm(coords[a] - coords[b])))

    def distortion(emb) -> float:
        ratios = [e / t for e, t in zip(emb, tru) if t > 0 and e > 0]
        return max(ratios) / min(ratios) if ratios else float("inf")

    return {
        "nodes": len(names),
        "diameter": diameter,
        "gromov_delta": delta,
        "delta_over_diameter": delta / diameter if diameter else float("nan"),
        "tree_like": delta < 1e-9,
        "hyperbolic_distortion": distortion(hyp),
        "euclidean_distortion": distortion(euc),
    }
