"""Binary edge-degeneration loci for the HB-0 governance kernel.

This module is a 1-face instrument, not the global decision object.  The global
object lives in :mod:`aionq.hb0.decision_field` and has at least three
alternatives.  Here, two vector-valued sections and a positive-semidefinite
comparison metric define a *wall point* when their non-zero difference lies in
the metric kernel.  The alternatives remain distinct, but the declared
instrument cannot distinguish that edge.

An unresolved edge returns ``HOLD`` with a typed remainder.  A resolved edge
has no unresolved remainder, and its label is never promoted to the full n-ary
cell.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Mapping

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from .core import CarrierMismatch, RemainderEnvelope, _as_vector, _finite


CONTINUE = "CONTINUE"
STOP = "STOP"
HOLD = "HOLD"
DECISIONS = (CONTINUE, STOP, HOLD)
_MAX_NUMERICAL_TOLERANCE = 1e-6


def _readonly(array: np.ndarray) -> np.ndarray:
    contiguous = np.ascontiguousarray(array, dtype=float)
    return np.frombuffer(contiguous.tobytes(), dtype=float).reshape(contiguous.shape)


def _metric_decomposition(
    metric: np.ndarray,
    tolerance: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None]:
    """Return spectrum, kernel mask/projector, and the positive-band gap."""

    eigenvalues, eigenvectors = np.linalg.eigh(metric)
    scale = max(1.0, float(np.max(np.abs(eigenvalues))))
    cutoff = tolerance * scale
    kernel_mask = np.abs(eigenvalues) <= cutoff
    kernel_vectors = eigenvectors[:, kernel_mask]
    kernel_projector = (
        np.zeros_like(metric)
        if kernel_vectors.shape[1] == 0
        else kernel_vectors @ kernel_vectors.T
    )
    positive = eigenvalues[eigenvalues > cutoff]
    positive_gap = None if positive.size == 0 else float(np.min(positive))
    return eigenvalues, kernel_mask, kernel_projector, positive_gap


@dataclass(frozen=True)
class WallObservation:
    """A local section of the continue/stop comparison field."""

    section_id: str
    carrier: str
    continue_coordinates: np.ndarray
    stop_coordinates: np.ndarray
    metric: np.ndarray
    evidence_refs: tuple[str, ...] = ()
    tolerance: float = 1e-10
    order_coframe: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not self.section_id or not self.carrier:
            raise GovernanceError("wall section id and carrier are required")
        tolerance = _finite(self.tolerance, "tolerance")
        if tolerance <= 0.0 or tolerance > _MAX_NUMERICAL_TOLERANCE:
            raise GovernanceError(
                f"wall tolerance must lie in (0, {_MAX_NUMERICAL_TOLERANCE}]"
            )
        cont = _as_vector(self.continue_coordinates, "continue_coordinates")
        stop = _as_vector(self.stop_coordinates, "stop_coordinates")
        if cont.shape != stop.shape:
            raise CarrierMismatch("continue and stop sections need one shared carrier")
        metric = np.array(self.metric, dtype=float, copy=True)
        if metric.shape != (cont.size, cont.size):
            raise GovernanceError("wall metric shape must match its decision carrier")
        if not np.all(np.isfinite(metric)):
            raise GovernanceError("wall metric contains a non-finite coordinate")
        if np.linalg.norm(metric - metric.T, ord="fro") > 1e-10 * max(
            1.0,
            float(np.linalg.norm(metric, ord="fro")),
        ):
            raise GovernanceError("wall metric must be symmetric")
        eigenvalues = np.linalg.eigvalsh(metric)
        eigenvalue_scale = max(1.0, float(np.max(np.abs(eigenvalues))))
        if float(np.min(eigenvalues)) < -tolerance * eigenvalue_scale:
            raise GovernanceError("wall metric must be positive semidefinite")
        coframe = (
            np.eye(cont.size)
            if self.order_coframe is None
            else np.array(self.order_coframe, dtype=float, copy=True)
        )
        if coframe.shape != (cont.size, cont.size):
            raise GovernanceError("wall order coframe shape must match its decision carrier")
        if not np.all(np.isfinite(coframe)):
            raise GovernanceError("wall order coframe contains a non-finite coordinate")
        if np.linalg.norm(coframe @ coframe.T - np.eye(cont.size), ord="fro") > 1e-10:
            raise GovernanceError("wall order coframe must be orthogonal")
        object.__setattr__(self, "continue_coordinates", _readonly(cont))
        object.__setattr__(self, "stop_coordinates", _readonly(stop))
        object.__setattr__(self, "metric", _readonly(metric))
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "order_coframe", _readonly(coframe))

    @property
    def difference(self) -> np.ndarray:
        return self.continue_coordinates - self.stop_coordinates

    @property
    def order_coordinates(self) -> np.ndarray:
        """Difference evaluated by the declared decision covectors."""

        return self.order_coframe @ self.difference  # type: ignore[operator]

    def analyse(self) -> "WallReport":
        eigenvalues, kernel_mask, kernel_projector, _ = _metric_decomposition(
            self.metric,
            self.tolerance,
        )
        delta = self.difference
        observable = self.metric @ delta
        observable_gap = float(np.linalg.norm(observable))
        intrinsic_gap = float(np.linalg.norm(delta))
        kernel_component = kernel_projector @ delta
        kernel_amplitude = float(np.linalg.norm(kernel_component))
        positive_component_gap = float(np.linalg.norm(delta - kernel_component))

        ordinary_tie = intrinsic_gap <= self.tolerance
        degenerate_wall = (
            not ordinary_tie
            and bool(np.any(kernel_mask))
            and positive_component_gap
            <= self.tolerance * max(1.0, intrinsic_gap)
        )
        order_coordinates = self.order_coordinates
        has_positive = bool(np.any(order_coordinates > self.tolerance))
        has_negative = bool(np.any(order_coordinates < -self.tolerance))
        pareto_incomparable = has_positive and has_negative

        if ordinary_tie or degenerate_wall or pareto_incomparable:
            decision = HOLD
        elif has_positive:
            decision = CONTINUE
        elif has_negative:
            decision = STOP
        else:
            decision = HOLD

        if degenerate_wall:
            statement = (
                "non-zero continue/stop difference lies in the declared metric "
                "kernel; the alternatives remain distinct but unresolvable"
            )
        elif ordinary_tie:
            statement = "continue and stop sections coincide on the declared carrier"
        elif pareto_incomparable:
            statement = "continue and stop are incomparable in the componentwise order"
        elif decision == HOLD:
            statement = (
                "the declared order coframe cannot resolve the difference outside "
                "its componentwise tolerance"
            )
        else:
            statement = ""

        remainder = None
        if decision == HOLD:
            if degenerate_wall:
                magnitude = kernel_amplitude
            elif ordinary_tie:
                magnitude = intrinsic_gap
            else:
                magnitude = float(np.max(np.abs(order_coordinates)))
            remainder = RemainderEnvelope(
                name="[R]_wall",
                channel="formal",
                carrier=self.carrier,
                evidence_tag=EvidenceTag.MEASURED,
                statement=statement,
                instrument="semidefinite-kernel-and-declared-order-coframe",
                magnitude=magnitude,
                assumptions=(
                    "finite-dimensional real carrier",
                    "positive-semidefinite metric",
                    "declared orthonormal decision coframe",
                ),
                provenance="aionq.hb0.wall.WallObservation.analyse",
            )
        return WallReport(
            section_id=self.section_id,
            carrier=self.carrier,
            decision=decision,
            rank=int(np.count_nonzero(~kernel_mask)),
            nullity=int(np.count_nonzero(kernel_mask)),
            eigenvalues=eigenvalues,
            intrinsic_gap=intrinsic_gap,
            observable_gap=observable_gap,
            kernel_amplitude=kernel_amplitude,
            positive_component_gap=positive_component_gap,
            ordinary_tie=ordinary_tie,
            degenerate_wall=degenerate_wall,
            pareto_incomparable=pareto_incomparable,
            order_coordinates=order_coordinates,
            remainder=remainder,
            evidence_refs=self.evidence_refs,
        )


@dataclass(frozen=True)
class WallReport:
    section_id: str
    carrier: str
    decision: str
    rank: int
    nullity: int
    eigenvalues: np.ndarray
    intrinsic_gap: float
    observable_gap: float
    kernel_amplitude: float
    positive_component_gap: float
    ordinary_tie: bool
    degenerate_wall: bool
    pareto_incomparable: bool
    order_coordinates: np.ndarray
    remainder: RemainderEnvelope | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class OrthogonalWallChart:
    """Lossless local-to-atlas chart used to glue wall observations."""

    source_carrier: str
    atlas_carrier: str
    matrix: np.ndarray
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        if not self.source_carrier or not self.atlas_carrier:
            raise GovernanceError("a wall chart must name source and atlas carriers")
        tolerance = _finite(self.tolerance, "chart.tolerance")
        if tolerance <= 0.0:
            raise GovernanceError("wall chart tolerance must be positive")
        if tolerance > _MAX_NUMERICAL_TOLERANCE:
            raise GovernanceError(
                f"wall chart tolerance must not exceed {_MAX_NUMERICAL_TOLERANCE}"
            )
        matrix = np.array(self.matrix, dtype=float, copy=True)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise GovernanceError("a wall chart must be a square matrix")
        if not np.all(np.isfinite(matrix)):
            raise GovernanceError("a wall chart contains a non-finite coordinate")
        eye = np.eye(matrix.shape[0])
        if np.linalg.norm(matrix.T @ matrix - eye, ord="fro") > tolerance:
            raise GovernanceError("wall charts must be orthogonal lossless transports")
        object.__setattr__(self, "matrix", _readonly(matrix))
        object.__setattr__(self, "tolerance", tolerance)

    def transport(self, section: WallObservation) -> WallObservation:
        if section.carrier != self.source_carrier:
            raise CarrierMismatch("wall chart source does not match section carrier")
        q = self.matrix
        return WallObservation(
            section_id=section.section_id,
            carrier=self.atlas_carrier,
            continue_coordinates=q @ section.continue_coordinates,
            stop_coordinates=q @ section.stop_coordinates,
            metric=q @ section.metric @ q.T,
            evidence_refs=section.evidence_refs,
            tolerance=max(section.tolerance, self.tolerance),
            order_coframe=section.order_coframe @ q.T,  # type: ignore[operator]
        )


@dataclass(frozen=True)
class WallAtlasReport:
    local_reports: Mapping[str, WallReport]
    gluing_defect: float
    decision_coherent: bool
    glued: bool
    atlas_decision: str
    remainder: RemainderEnvelope | None
    global_decision_permitted: bool = False


def glue_wall_sections(
    sections: Mapping[str, WallObservation],
    charts: Mapping[str, OrthogonalWallChart],
    tolerance: float = 1e-9,
) -> WallAtlasReport:
    """Glue local wall sections after explicit transport to one atlas carrier."""

    tolerance = _finite(tolerance, "gluing.tolerance")
    if tolerance <= 0.0 or tolerance > _MAX_NUMERICAL_TOLERANCE:
        raise GovernanceError(
            f"wall gluing tolerance must lie in (0, {_MAX_NUMERICAL_TOLERANCE}]"
        )
    if len(sections) < 2:
        raise GovernanceError("a wall atlas needs at least two overlapping sections")
    if set(sections) != set(charts):
        raise GovernanceError("every wall section needs exactly one atlas chart")
    transported = {name: charts[name].transport(section) for name, section in sections.items()}
    carriers = {section.carrier for section in transported.values()}
    dimensions = {section.difference.size for section in transported.values()}
    if len(carriers) != 1 or len(dimensions) != 1:
        raise CarrierMismatch("transported wall sections do not share an atlas carrier")

    transported_sections = tuple(transported.values())
    defects = []
    for left, right in combinations(transported_sections, 2):
        defects.append(float(np.linalg.norm(left.difference - right.difference)))
        defects.append(float(np.linalg.norm(left.metric - right.metric, ord="fro")))
        defects.append(
            float(np.linalg.norm(left.order_coframe - right.order_coframe, ord="fro"))
        )
    gluing_defect = max(defects, default=0.0)
    local_reports = {name: section.analyse() for name, section in transported.items()}
    decisions = {report.decision for report in local_reports.values()}
    decision_coherent = len(decisions) == 1
    glued = gluing_defect <= tolerance and decision_coherent
    atlas_decision = next(iter(decisions)) if glued else HOLD
    remainder = None
    if not glued:
        remainder = RemainderEnvelope(
            name="[R]_wall_gluing",
            channel="coherence",
            carrier=next(iter(carriers)),
            evidence_tag=EvidenceTag.MEASURED,
            statement=(
                "local decisions disagree after declared transport"
                if not decision_coherent
                else "local degeneration sections disagree after declared transport"
            ),
            instrument="max-pairwise-field-defect-and-decision-coherence",
            magnitude=max(gluing_defect, 0.0 if decision_coherent else 1.0),
            assumptions=(
                "difference, metric, decision coframe, and decision must glue pairwise",
            ),
            provenance="aionq.hb0.wall.glue_wall_sections",
        )
    return WallAtlasReport(
        local_reports=local_reports,
        gluing_defect=gluing_defect,
        decision_coherent=decision_coherent,
        glued=glued,
        atlas_decision=atlas_decision,
        remainder=remainder,
    )


@dataclass(frozen=True)
class WallPathSample:
    """One observation at a declared finite-path parameter."""

    parameter: float
    observation: WallObservation

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameter", _finite(self.parameter, "path.parameter"))
        if not isinstance(self.observation, WallObservation):
            raise GovernanceError("a wall path sample needs a WallObservation")


@dataclass(frozen=True)
class FiniteAdiabaticCriterion:
    """Policy for a finite rate/gap certificate; not a physical adiabatic theorem."""

    parameter_name: str
    parameter_unit: str
    section_scale: float
    metric_scale: float
    min_gap_ratio: float
    max_adiabatic_load: float

    def __post_init__(self) -> None:
        if not self.parameter_name or not self.parameter_unit:
            raise GovernanceError("an adiabatic criterion must name its path parameter and unit")
        for name in (
            "section_scale",
            "metric_scale",
            "min_gap_ratio",
            "max_adiabatic_load",
        ):
            value = _finite(getattr(self, name), f"criterion.{name}")
            if value <= 0.0:
                raise GovernanceError(f"criterion {name} must be positive")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class WallBreath:
    """Measured finite path through the wall under one declared policy."""

    criterion: FiniteAdiabaticCriterion
    parameters: tuple[float, ...]
    decisions: tuple[str, ...]
    has_intermediate_hold: bool
    degenerate_wall_indices: tuple[int, ...]
    ordinary_tie_indices: tuple[int, ...]
    pareto_hold_indices: tuple[int, ...]
    direct_continue_stop_jumps: tuple[int, ...]
    reversal_spans: tuple[tuple[int, int], ...]
    unwitnessed_reversal_spans: tuple[tuple[int, int], ...]
    kernel_nullities: tuple[int, ...]
    minimum_gap_ratio: float | None
    maximum_path_rate: float
    maximum_adiabatic_load: float | None
    adiabatic_certified_under_policy: bool
    violations: tuple[str, ...]


def trace_wall_breath(
    samples: tuple[WallPathSample, ...],
    criterion: FiniteAdiabaticCriterion,
) -> WallBreath:
    """Measure a path without turning an intermediate ``HOLD`` into a certificate.

    The finite instrument uses divided differences for the decision section,
    PSD metric, kernel projector, and order coframe.  Their maximum normalized
    rate is divided by the square of the positive spectral-gap ratio.  Every
    resolved ``CONTINUE``/``STOP`` reversal must also contain an actual
    non-zero metric-kernel wall sample.
    """

    if len(samples) < 2:
        raise GovernanceError("a wall path needs at least two parameterized samples")
    if not isinstance(criterion, FiniteAdiabaticCriterion):
        raise GovernanceError("a wall path needs a FiniteAdiabaticCriterion")

    parameters = tuple(sample.parameter for sample in samples)
    if any(right <= left for left, right in zip(parameters, parameters[1:])):
        raise GovernanceError("wall path parameters must be strictly increasing")
    observations = tuple(sample.observation for sample in samples)
    carriers = {observation.carrier for observation in observations}
    dimensions = {observation.difference.size for observation in observations}
    if len(carriers) != 1 or len(dimensions) != 1:
        raise CarrierMismatch(
            "wall path samples must already share one declared atlas carrier"
        )

    reports = tuple(observation.analyse() for observation in observations)
    decisions = tuple(report.decision for report in reports)
    degenerate_wall_indices = tuple(
        index for index, report in enumerate(reports) if report.degenerate_wall
    )
    ordinary_tie_indices = tuple(
        index for index, report in enumerate(reports) if report.ordinary_tie
    )
    pareto_hold_indices = tuple(
        index for index, report in enumerate(reports) if report.pareto_incomparable
    )
    direct_jumps = tuple(
        index
        for index, (left, right) in enumerate(zip(decisions, decisions[1:]))
        if {left, right} == {CONTINUE, STOP}
    )

    resolved = tuple(
        (index, decision)
        for index, decision in enumerate(decisions)
        if decision in (CONTINUE, STOP)
    )
    reversal_spans = tuple(
        (left_index, right_index)
        for (left_index, left), (right_index, right) in zip(resolved, resolved[1:])
        if left != right
    )
    has_intermediate_hold = bool(reversal_spans) and all(
        any(decisions[index] == HOLD for index in range(left + 1, right))
        for left, right in reversal_spans
    )
    unwitnessed_reversal_spans = tuple(
        (left, right)
        for left, right in reversal_spans
        if not any(
            reports[index].degenerate_wall for index in range(left + 1, right)
        )
    )

    decompositions = tuple(
        _metric_decomposition(observation.metric, observation.tolerance)
        for observation in observations
    )
    projectors = tuple(item[2] for item in decompositions)
    positive_gaps = tuple(item[3] for item in decompositions)
    kernel_nullities = tuple(
        int(np.count_nonzero(item[1])) for item in decompositions
    )

    path_rates = []
    for index, (left, right) in enumerate(zip(observations, observations[1:])):
        delta_parameter = parameters[index + 1] - parameters[index]
        section_rate = (
            float(np.linalg.norm(right.difference - left.difference))
            / criterion.section_scale
            / delta_parameter
        )
        metric_rate = (
            float(np.linalg.norm(right.metric - left.metric, ord=2))
            / criterion.metric_scale
            / delta_parameter
        )
        projector_rate = (
            float(np.linalg.norm(projectors[index + 1] - projectors[index], ord=2))
            / delta_parameter
        )
        order_rate = (
            float(
                np.linalg.norm(
                    right.order_coframe - left.order_coframe,
                    ord=2,
                )
            )
            / delta_parameter
        )
        path_rate = max(section_rate, metric_rate, projector_rate, order_rate)
        path_rates.append(_finite(path_rate, f"path.rate[{index}]"))
    maximum_path_rate = max(path_rates)

    all_gaps_present = all(gap is not None for gap in positive_gaps)
    if all_gaps_present:
        gap_ratios = tuple(
            float(gap) / criterion.metric_scale for gap in positive_gaps
        )
        minimum_gap_ratio = min(gap_ratios)
        loads = tuple(
            rate / min(gap_ratios[index], gap_ratios[index + 1]) ** 2
            for index, rate in enumerate(path_rates)
        )
        maximum_adiabatic_load = max(loads)
    else:
        minimum_gap_ratio = None
        maximum_adiabatic_load = None

    violations = []
    if not reversal_spans:
        violations.append("no_resolved_reversal")
    if unwitnessed_reversal_spans:
        violations.append("reversal_without_metric_wall")
    if any(nullity == 0 for nullity in kernel_nullities):
        violations.append("positive_kernel_band_absent")
    if len(set(kernel_nullities)) != 1:
        violations.append("kernel_nullity_changed")
    if not all_gaps_present:
        violations.append("positive_spectral_band_missing")
    elif minimum_gap_ratio < criterion.min_gap_ratio:
        violations.append("spectral_gap_below_floor")
    if (
        maximum_adiabatic_load is not None
        and maximum_adiabatic_load > criterion.max_adiabatic_load
    ):
        violations.append("adiabatic_load_exceeds_bound")

    return WallBreath(
        criterion=criterion,
        parameters=parameters,
        decisions=decisions,
        has_intermediate_hold=has_intermediate_hold,
        degenerate_wall_indices=degenerate_wall_indices,
        ordinary_tie_indices=ordinary_tie_indices,
        pareto_hold_indices=pareto_hold_indices,
        direct_continue_stop_jumps=direct_jumps,
        reversal_spans=reversal_spans,
        unwitnessed_reversal_spans=unwitnessed_reversal_spans,
        kernel_nullities=kernel_nullities,
        minimum_gap_ratio=minimum_gap_ratio,
        maximum_path_rate=maximum_path_rate,
        maximum_adiabatic_load=maximum_adiabatic_load,
        adiabatic_certified_under_policy=not violations,
        violations=tuple(violations),
    )
