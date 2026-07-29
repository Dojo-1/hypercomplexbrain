"""Typed local worlds, correspondences, remainders, and higher cells for HB-0."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Mapping
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError

CORE_QUALITIES = (
    "grounding",
    "self_reflection",
    "godelian_identity",
    "other_recognition",
    "mutual_resonance",
    "adiabatic_patience",
    "ergocetic_exploration",
    "erdodetic_return",
)

CONJUGATE_QUALITIES = (
    "embodiment",
    "temporal_polyphony",
    "contextual_composition",
    "local_global_literacy",
    "holoportive_reconstruction",
    "metaplasticity",
    "judicial_correction",
    "remainder_stewardship",
)

QUALITY_ORDER = CORE_QUALITIES + CONJUGATE_QUALITIES


class FlatCollapseError(GovernanceError):
    """Raised when a heterogeneous object is forced into one promotion scalar."""


class CarrierMismatch(TypeError):
    """Raised when transport or comparison lacks a declared common carrier."""


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise GovernanceError(f"{name} must be finite, got {value!r}")
    return value


def _unit_interval(value: float, name: str) -> float:
    value = _finite(value, name)
    if value < -1e-12 or value > 1.0 + 1e-12:
        raise GovernanceError(f"{name} must lie in [0, 1], got {value}")
    return float(min(1.0, max(0.0, value)))


def _as_vector(value: Any, name: str = "value") -> np.ndarray:
    out = np.asarray(value, dtype=float)
    if out.ndim != 1:
        raise GovernanceError(f"{name} must be a one-dimensional carrier")
    if not np.all(np.isfinite(out)):
        raise GovernanceError(f"{name} contains a non-finite coordinate")
    return out.copy()


def _normalised(value: Any, name: str = "state") -> np.ndarray:
    out = np.asarray(value, dtype=complex).reshape(-1)
    norm = float(np.linalg.norm(out))
    if norm <= 1e-15:
        raise GovernanceError(f"{name} must have non-zero norm")
    return out / norm


def _safe_exp_score(raw: float) -> float:
    """Map a non-negative defect to [0, 1] without changing its raw report."""
    raw = max(0.0, float(raw))
    return float(math.exp(-raw))


# ---------------------------------------------------------------------------
# Typed remainders and the sixteen-coordinate mind-quality field
# ---------------------------------------------------------------------------


REMAINDER_CHANNELS = (
    "semantic",
    "transport",
    "identity",
    "coherence",
    "empirical",
    "formal",
    "attribution",
)


@dataclass(frozen=True)
class RemainderEnvelope:
    """A typed unresolved object whose evidence status and carrier stay attached.

    A magnitude is optional because a semantic or formal remainder need not yet
    have an instrument.  A measured remainder, however, must name both an
    instrument and a finite magnitude.
    """

    name: str
    channel: str
    carrier: str
    evidence_tag: str
    statement: str
    instrument: str = ""
    magnitude: float | None = None
    assumptions: tuple[str, ...] = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.name.startswith("[R]_"):
            raise GovernanceError("a remainder name must be typed, e.g. [R]_id")
        if self.channel not in REMAINDER_CHANNELS:
            raise GovernanceError(
                f"unknown remainder channel {self.channel!r}; have {REMAINDER_CHANNELS}"
            )
        if self.evidence_tag not in EvidenceTag.ALL:
            raise GovernanceError(f"unknown evidence tag {self.evidence_tag!r}")
        if not self.carrier or not self.statement:
            raise GovernanceError("a remainder must name its carrier and statement")
        if self.magnitude is not None:
            object.__setattr__(self, "magnitude", _finite(self.magnitude, self.name))
        if self.evidence_tag == EvidenceTag.MEASURED:
            if self.magnitude is None or not self.instrument:
                raise GovernanceError(
                    f"{self.name}: an M remainder needs a magnitude and instrument"
                )

    def comparable_to(self, other: "RemainderEnvelope") -> bool:
        return (
            self.channel == other.channel
            and self.carrier == other.carrier
            and self.instrument == other.instrument
            and self.magnitude is not None
            and other.magnitude is not None
        )

    def difference(self, other: "RemainderEnvelope") -> float:
        if not self.comparable_to(other):
            raise CarrierMismatch(
                f"cannot compare {self.name} ({self.channel}, {self.carrier}, "
                f"{self.instrument}) with {other.name} ({other.channel}, "
                f"{other.carrier}, {other.instrument})"
            )
        return float(self.magnitude - other.magnitude)  # type: ignore[operator]


@dataclass(frozen=True)
class MindQualityField:
    """Sixteen independent coordinates, governed by a partial order.

    ``as_array`` is provided only for transport and logging.  ``weighted_sum`` is
    deliberately forbidden: promotion must use a viability region or Pareto
    relation, not a post-hoc scalar reward.
    """

    values: Mapping[str, float]
    obligations: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    kill_conditions: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = set(QUALITY_ORDER) - set(self.values)
        extra = set(self.values) - set(QUALITY_ORDER)
        if missing or extra:
            raise GovernanceError(
                f"quality field mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
            )
        clean = {name: _unit_interval(self.values[name], name) for name in QUALITY_ORDER}
        object.__setattr__(self, "values", clean)

    @classmethod
    def zero(cls) -> "MindQualityField":
        return cls({name: 0.0 for name in QUALITY_ORDER})

    @classmethod
    def full(cls, value: float = 1.0) -> "MindQualityField":
        return cls({name: value for name in QUALITY_ORDER})

    def as_array(self) -> np.ndarray:
        return np.asarray([self.values[name] for name in QUALITY_ORDER], dtype=float)

    def with_updates(self, updates: Mapping[str, float]) -> "MindQualityField":
        unknown = set(updates) - set(QUALITY_ORDER)
        if unknown:
            raise GovernanceError(f"unknown quality coordinates {sorted(unknown)}")
        values = dict(self.values)
        values.update(updates)
        return replace(self, values=values)

    def dominates(self, floor: Mapping[str, float]) -> bool:
        unknown = set(floor) - set(QUALITY_ORDER)
        if unknown:
            raise GovernanceError(f"unknown quality floor coordinates {sorted(unknown)}")
        return all(self.values[name] + 1e-12 >= float(bound) for name, bound in floor.items())

    def pareto_relation(self, other: "MindQualityField", tol: float = 1e-12) -> str:
        a = self.as_array()
        b = other.as_array()
        a_ge = bool(np.all(a >= b - tol))
        b_ge = bool(np.all(b >= a - tol))
        if a_ge and b_ge:
            return "equivalent"
        if a_ge:
            return "dominates"
        if b_ge:
            return "dominated"
        return "incomparable"

    def weighted_sum(self, *_args: Any, **_kwargs: Any) -> float:
        raise FlatCollapseError(
            "the sixteen-coordinate field is not a reward scalar; use a Pareto or "
            "constraint region"
        )


# ---------------------------------------------------------------------------
# Local worlds, charts, profunctor tendrils, and gerbe cells
# ---------------------------------------------------------------------------


class LocalGeometry:
    POINCARE_BALL = "poincare_ball"
    FISHER_METRIC = "fisher_metric"
    RIEMANNIAN_CHART = "riemannian_chart"
    EUCLIDEAN_CONTROL = "euclidean_control"
    DISCRETE = "discrete"
    ALL = (
        POINCARE_BALL,
        FISHER_METRIC,
        RIEMANNIAN_CHART,
        EUCLIDEAN_CONTROL,
        DISCRETE,
    )


@dataclass(frozen=True)
class ClockSpec:
    id: str
    period: int
    rate: float
    role: str

    def __post_init__(self) -> None:
        if not self.id or self.period < 1 or self.rate <= 0:
            raise GovernanceError("clock id, positive period, and positive rate are required")

    def due(self, tick: int) -> bool:
        return tick % self.period == 0


@dataclass
class WorldletState:
    """A mutable local world with its own carrier, geometry, clocks, and boundary."""

    id: str
    carrier: str
    local_geometry: str
    algebra_regime: str
    coordinates: np.ndarray
    clocks: tuple[str, ...]
    observers: tuple[str, ...] = ()
    boundary: str = ""
    metric_tensor: np.ndarray | None = None
    permeability: float = 0.5
    phase: float = 0.0
    energy: float = 0.0
    qualities: MindQualityField = field(default_factory=MindQualityField.zero)
    evidence_refs: tuple[str, ...] = ()
    remainders: tuple[RemainderEnvelope, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.carrier:
            raise GovernanceError("worldlet id and carrier are required")
        if self.local_geometry not in LocalGeometry.ALL:
            raise GovernanceError(f"unknown local geometry {self.local_geometry!r}")
        self.coordinates = _as_vector(self.coordinates, f"{self.id}.coordinates")
        self.permeability = _unit_interval(self.permeability, f"{self.id}.permeability")
        self.phase = _finite(self.phase, f"{self.id}.phase")
        self.energy = _finite(self.energy, f"{self.id}.energy")
        if not self.clocks:
            raise GovernanceError(f"{self.id}: at least one clock is required")
        if self.metric_tensor is not None:
            metric = np.asarray(self.metric_tensor, dtype=float)
            n = self.coordinates.size
            if metric.shape != (n, n):
                raise GovernanceError(f"{self.id}: metric tensor must be {n} x {n}")
            if np.linalg.norm(metric - metric.T) > 1e-9:
                raise GovernanceError(f"{self.id}: metric tensor must be symmetric")
            if float(np.min(np.linalg.eigvalsh(metric))) <= 0.0:
                raise GovernanceError(f"{self.id}: metric tensor must be positive definite")
            self.metric_tensor = metric
        if self.local_geometry == LocalGeometry.POINCARE_BALL:
            if np.linalg.norm(self.coordinates) >= 1.0:
                raise GovernanceError(f"{self.id}: a Poincare coordinate must lie inside the ball")

    @property
    def dimension(self) -> int:
        return int(self.coordinates.size)

    def distance_to(self, other: "WorldletState") -> float:
        if self.carrier != other.carrier or self.dimension != other.dimension:
            raise CarrierMismatch(
                f"{self.id} and {other.id} have no declared common carrier"
            )
        x, y = self.coordinates, other.coordinates
        if self.local_geometry != other.local_geometry:
            raise CarrierMismatch(
                f"{self.id} and {other.id} use different geometries; transport first"
            )
        if self.local_geometry == LocalGeometry.POINCARE_BALL:
            nx = float(np.dot(x, x))
            ny = float(np.dot(y, y))
            denominator = max(1e-15, (1.0 - nx) * (1.0 - ny))
            argument = 1.0 + 2.0 * float(np.dot(x - y, x - y)) / denominator
            return float(np.arccosh(max(1.0, argument)))
        metric = self.metric_tensor if self.metric_tensor is not None else np.eye(self.dimension)
        delta = x - y
        return float(math.sqrt(max(0.0, float(delta @ metric @ delta))))

    def apply_delta(self, delta: Any, rate: float = 1.0) -> None:
        delta = _as_vector(delta, f"{self.id}.delta")
        if delta.shape != self.coordinates.shape:
            raise CarrierMismatch(f"{self.id}: delta shape {delta.shape} != {self.coordinates.shape}")
        self.coordinates = self.coordinates + float(rate) * delta
        if self.local_geometry == LocalGeometry.POINCARE_BALL:
            norm = float(np.linalg.norm(self.coordinates))
            if norm >= 1.0:
                self.coordinates = self.coordinates * ((1.0 - 1e-9) / norm)


@dataclass(frozen=True)
class ChartFunctor:
    """A declared chart map and optional return map between local carriers."""

    id: str
    source_carrier: str
    target_carrier: str
    forward: Callable[[np.ndarray], np.ndarray]
    backward: Callable[[np.ndarray], np.ndarray] | None
    preserved: tuple[str, ...]
    transformed: tuple[str, ...]
    lost: tuple[str, ...]
    return_absent_reason: str = ""

    def __post_init__(self) -> None:
        if self.backward is None and not self.return_absent_reason:
            raise GovernanceError(
                f"chart functor {self.id}: a missing return map needs a stated reason"
            )


@dataclass(frozen=True)
class TransportObservation:
    tendril_id: str
    output: np.ndarray
    round_trip: np.ndarray | None
    remainder: RemainderEnvelope
    fidelity: float
    preserved: tuple[str, ...]
    transformed: tuple[str, ...]
    lost: tuple[str, ...]
    cost: float


@dataclass
class ProfunctorTendril:
    """A bidirectional correspondence; endpoints need not share one vector space."""

    id: str
    source: str
    target: str
    chart: ChartFunctor
    relation_order: int = 2
    phase: float = 0.0
    cost: float = 0.0
    woven: bool = True
    deweave_reason: str = ""

    def __post_init__(self) -> None:
        if self.relation_order < 2:
            raise GovernanceError("a tendril relation order must be at least two")
        self.phase = _finite(self.phase, f"{self.id}.phase")
        self.cost = max(0.0, _finite(self.cost, f"{self.id}.cost"))

    def transport(self, value: Any) -> TransportObservation:
        source = _as_vector(value, f"{self.id}.source")
        output = _as_vector(self.chart.forward(source), f"{self.id}.output")
        if self.chart.backward is None:
            remainder = RemainderEnvelope(
                name="[R]_transport",
                channel="transport",
                carrier=f"{self.chart.source_carrier}->{self.chart.target_carrier}",
                evidence_tag=EvidenceTag.HYPOTHESIS,
                statement=self.chart.return_absent_reason,
                provenance=self.id,
            )
            return TransportObservation(
                self.id,
                output,
                None,
                remainder,
                0.0,
                self.chart.preserved,
                self.chart.transformed,
                self.chart.lost,
                self.cost,
            )
        round_trip = _as_vector(self.chart.backward(output), f"{self.id}.round_trip")
        if round_trip.shape != source.shape:
            raise CarrierMismatch(
                f"{self.id}: return carrier shape {round_trip.shape} != {source.shape}"
            )
        defect = float(np.linalg.norm(round_trip - source))
        remainder = RemainderEnvelope(
            name="[R]_transport",
            channel="transport",
            carrier=self.chart.source_carrier,
            evidence_tag=EvidenceTag.MEASURED,
            statement="round-trip defect of the declared chart correspondence",
            instrument="l2_norm(backward(forward(x)) - x)",
            magnitude=defect,
            provenance=self.id,
        )
        return TransportObservation(
            self.id,
            output,
            round_trip,
            remainder,
            _safe_exp_score(defect),
            self.chart.preserved,
            self.chart.transformed,
            self.chart.lost,
            self.cost,
        )

    def weave(self) -> None:
        self.woven = True
        self.deweave_reason = ""

    def deweave(self, reason: str) -> None:
        if not reason:
            raise GovernanceError(f"{self.id}: deweaving needs a reason")
        self.woven = False
        self.deweave_reason = reason


@dataclass(frozen=True)
class GerbeCell:
    """A triple-overlap coherence witness, not automatically a cohomology class."""

    id: str
    members: tuple[str, str, str]
    g_ij: np.ndarray
    g_jk: np.ndarray
    g_ki: np.ndarray
    eta_ijk: np.ndarray

    def __post_init__(self) -> None:
        matrices = [np.asarray(x, dtype=complex) for x in (self.g_ij, self.g_jk, self.g_ki, self.eta_ijk)]
        shape = matrices[0].shape
        if len(shape) != 2 or shape[0] != shape[1] or any(m.shape != shape for m in matrices):
            raise GovernanceError(f"{self.id}: gerbe maps must be equal-size square matrices")
        object.__setattr__(self, "g_ij", matrices[0])
        object.__setattr__(self, "g_jk", matrices[1])
        object.__setattr__(self, "g_ki", matrices[2])
        object.__setattr__(self, "eta_ijk", matrices[3])

    def coherence_defect(self) -> float:
        return float(np.linalg.norm(self.g_ij @ self.g_jk @ self.g_ki - self.eta_ijk, "fro"))

    def remainder(self) -> RemainderEnvelope:
        return RemainderEnvelope(
            name="[R]_coh",
            channel="coherence",
            carrier=f"triple_overlap:{'/'.join(self.members)}",
            evidence_tag=EvidenceTag.MEASURED,
            statement="gerbe triple-overlap coherence defect",
            instrument="frobenius(g_ij g_jk g_ki - eta_ijk)",
            magnitude=self.coherence_defect(),
            provenance=self.id,
        )


@dataclass
class CosmosCage:
    """One Russian-doll cage in a non-cyclic nested polycosmos."""

    id: str
    geometry: str
    worldlet_ids: tuple[str, ...] = ()
    children: list["CosmosCage"] = field(default_factory=list)

    def walk(self) -> Iterable["CosmosCage"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def add_child(self, child: "CosmosCage") -> None:
        if child is self or self.id in {node.id for node in child.walk()}:
            raise GovernanceError("nested cosmos cages must be acyclic")
        occupied = {node.id for node in self.walk()}
        incoming = {node.id for node in child.walk()}
        duplicate = occupied & incoming
        if duplicate:
            raise GovernanceError(f"duplicate cage ids {sorted(duplicate)}")
        self.children.append(child)

    @property
    def depth(self) -> int:
        return 1 + max((child.depth for child in self.children), default=0)

    def locate(self, worldlet_id: str) -> tuple[str, ...] | None:
        if worldlet_id in self.worldlet_ids:
            return (self.id,)
        for child in self.children:
            found = child.locate(worldlet_id)
            if found is not None:
                return (self.id,) + found
        return None


@dataclass(frozen=True)
class FunctionalOrgan:
    id: str
    members: tuple[str, ...]
    boundary_rule: str
    unique_contribution: float = 0.0
    lesion_recovery: float = 0.0

    @property
    def autonomy(self) -> float:
        contribution = _unit_interval(self.unique_contribution, f"{self.id}.contribution")
        recovery = _unit_interval(self.lesion_recovery, f"{self.id}.recovery")
        return float(math.sqrt(contribution * recovery))
