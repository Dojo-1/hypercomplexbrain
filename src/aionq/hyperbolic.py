"""The shared Riemannian hyperbolic base for AION/HB-0 contexts.

The canonical representation is the future sheet of a Lorentz hyperboloid.
The Poincare ball is an isometric chart of that same object.  The base is a
declared universal atlas; heterogeneous Fisher, Euclidean, Riemannian, and
hypercomplex structures remain local fiber data.  Universal base therefore
does not mean universal local metric.

The earlier empirical claim that the live free-theory diamond *earned* negative
curvature remains falsified.  The present contract is explicitly axiomatic and
keeps a matched Euclidean ablation rather than rewriting that measurement.

Ambient Lorentz signature, the positive-definite tangent metric, the split
``(2, 2)`` substrate, and semidefinite decision instruments are distinct types.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from .carriers import CarrierMismatch, _as_vector, _finite
from .governance import GovernanceError

__all__ = [
    "EuclideanBaseControl",
    "HyperbolicBaseReview",
    "LorentzIsometry",
    "PoincareBallBase",
    "UNIVERSAL_EUCLIDEAN_CONTROL",
    "UNIVERSAL_POINCARE_BASE",
]


_MAX_GEOMETRY_TOLERANCE = 1e-6
_MIN_GEOMETRY_TOLERANCE = 128.0 * np.finfo(float).eps
_MIN_NUMERICAL_RADIUS = 8.0 * math.sqrt(np.finfo(float).tiny)
_MAX_NUMERICAL_RADIUS = math.sqrt(np.finfo(float).max) / 8.0
_MAX_BALL_DISTANCE_IN_RADII = 32.0
_SCHEMA = "aionq.poincare-universal-base.v2"
_EUCLIDEAN_CONTROL_SCHEMA = "aionq.euclidean-base-control.v1"


def _readonly(value) -> np.ndarray:
    """Return a bytes-backed array whose write flag cannot be re-enabled."""

    contiguous = np.ascontiguousarray(value, dtype=float)
    return np.frombuffer(contiguous.tobytes(), dtype=float).reshape(contiguous.shape)


def _positive(value: float, name: str) -> float:
    value = _finite(value, name)
    if value <= 0.0:
        raise GovernanceError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class EuclideanBaseControl:
    """Origin-tangent-matched ``R^n`` ablation for universal ``H^n``."""

    id: str
    dimension: int
    metric_scale: float = 1.0

    def __post_init__(self) -> None:
        if not self.id:
            raise GovernanceError("a Euclidean base control needs an id")
        if isinstance(self.dimension, bool) or not isinstance(
            self.dimension, (int, np.integer)
        ):
            raise GovernanceError("Euclidean base-control dimension must be an integer")
        if self.dimension < 1:
            raise GovernanceError("Euclidean base-control dimension must be positive")
        object.__setattr__(
            self,
            "metric_scale",
            _positive(self.metric_scale, "euclidean_base_control.metric_scale"),
        )

    def point(self, value, name: str = "euclidean_base_point") -> np.ndarray:
        point = _as_vector(value, name)
        if point.size != self.dimension:
            raise CarrierMismatch(
                f"{name} has dimension {point.size}; expected {self.dimension}"
            )
        return _readonly(point)

    def distance(self, left, right) -> float:
        left = self.point(left, "euclidean_distance.left")
        right = self.point(right, "euclidean_distance.right")
        return _finite(
            self.metric_scale * float(np.linalg.norm(left - right)),
            "Euclidean base-control distance",
        )

    @property
    def metric_tensor(self) -> np.ndarray:
        return _readonly(
            (self.metric_scale * self.metric_scale) * np.eye(self.dimension)
        )

    def to_spec(self) -> dict:
        return {
            "schema": _EUCLIDEAN_CONTROL_SCHEMA,
            "id": self.id,
            "dimension": self.dimension,
            "metric_scale": self.metric_scale,
            "matching": "same tangent metric at the Poincare origin",
        }

    @classmethod
    def from_spec(cls, spec: dict) -> "EuclideanBaseControl":
        if not isinstance(spec, dict) or spec.get("schema") != _EUCLIDEAN_CONTROL_SCHEMA:
            raise GovernanceError("unknown Euclidean base-control schema")
        if spec.get("matching") != "same tangent metric at the Poincare origin":
            raise GovernanceError("Euclidean base control has an unknown matching rule")
        dimension = spec.get("dimension")
        if isinstance(dimension, bool) or not isinstance(
            dimension, (int, np.integer)
        ):
            raise GovernanceError("Euclidean base-control dimension must be an integer")
        return cls(
            id=spec.get("id", ""),
            dimension=dimension,
            metric_scale=spec.get("metric_scale", 0.0),
        )


@dataclass(frozen=True)
class LorentzIsometry:
    """A future-sheet-preserving linear isometry of ``R^(1,n)``."""

    matrix: np.ndarray
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        tolerance = _positive(self.tolerance, "lorentz_isometry.tolerance")
        if not _MIN_GEOMETRY_TOLERANCE <= tolerance <= _MAX_GEOMETRY_TOLERANCE:
            raise GovernanceError(
                "Lorentz-isometry tolerance lies outside the conditioned float64 "
                f"domain [{_MIN_GEOMETRY_TOLERANCE}, {_MAX_GEOMETRY_TOLERANCE}]"
            )
        matrix = np.array(self.matrix, dtype=float, copy=True)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise GovernanceError("a Lorentz isometry must be a square matrix")
        if matrix.shape[0] < 2 or not np.all(np.isfinite(matrix)):
            raise GovernanceError("a Lorentz isometry must be finite and at least 2 x 2")
        eta = np.diag([-1.0] + [1.0] * (matrix.shape[0] - 1))
        with np.errstate(over="ignore", invalid="ignore"):
            matrix_norm = float(np.linalg.norm(matrix, ord="fro"))
            conditioning_error = (
                np.finfo(float).eps * matrix_norm * matrix_norm
            )
            residual = matrix.T @ eta @ matrix - eta
            defect = float(np.linalg.norm(residual, ord="fro"))
            condition_number = float(np.linalg.cond(matrix))
            sign, log_abs_determinant = np.linalg.slogdet(matrix)
        if not all(
            math.isfinite(value)
            for value in (
                matrix_norm,
                conditioning_error,
                defect,
                condition_number,
                log_abs_determinant,
            )
        ):
            raise GovernanceError("Lorentz isometry diagnostics must be finite")
        if conditioning_error > tolerance / 8.0:
            raise GovernanceError(
                "Lorentz isometry is outside the conditioned float64 domain"
            )
        if defect > tolerance * float(np.linalg.norm(eta, ord="fro")):
            raise GovernanceError("matrix does not preserve the declared Lorentz form")
        if sign == 0.0 or abs(log_abs_determinant) > tolerance * matrix.shape[0]:
            raise GovernanceError("Lorentz isometry must be invertible with |det| = 1")
        if condition_number * np.finfo(float).eps > tolerance:
            raise GovernanceError("Lorentz isometry is too ill-conditioned to certify")
        if matrix[0, 0] <= 0.0:
            raise GovernanceError("Lorentz isometry must preserve the future sheet")
        object.__setattr__(self, "matrix", _readonly(matrix))
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def dimension(self) -> int:
        return int(self.matrix.shape[0] - 1)


@dataclass(frozen=True)
class HyperbolicBaseReview:
    base_id: str
    dimension: int
    points_reviewed: int
    pairs_reviewed: int
    isometries_reviewed: int
    minimum_boundary_margin: float
    minimum_metric_eigenvalue: float
    maximum_chart_roundtrip_defect: float
    maximum_hyperboloid_constraint_defect: float
    maximum_distance_chart_defect: float
    maximum_isometry_distance_defect: float
    passed: bool
    violations: tuple[str, ...]


@dataclass(frozen=True)
class PoincareBallBase:
    """A declared universal ``H^n`` atlas with curvature ``K < 0``."""

    id: str
    dimension: int
    sectional_curvature: float = -1.0
    scope: str = "universal_atlas"
    euclidean_control_declared: bool = True
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        if not self.id:
            raise GovernanceError("a hyperbolic base needs an id")
        if isinstance(self.dimension, bool) or not isinstance(
            self.dimension, (int, np.integer)
        ):
            raise GovernanceError("hyperbolic-base dimension must be an integer")
        if self.dimension < 1:
            raise GovernanceError("a hyperbolic base needs positive dimension")
        curvature = _finite(self.sectional_curvature, "sectional_curvature")
        if curvature >= 0.0:
            raise GovernanceError("hyperbolic sectional curvature must be negative")
        if self.scope != "universal_atlas":
            raise GovernanceError(
                "the active Poincare contract requires scope='universal_atlas'"
            )
        if not self.euclidean_control_declared:
            raise GovernanceError(
                "the universal hyperbolic base needs a matched Euclidean ablation"
            )
        tolerance = _positive(self.tolerance, "hyperbolic_base.tolerance")
        if not _MIN_GEOMETRY_TOLERANCE <= tolerance <= _MAX_GEOMETRY_TOLERANCE:
            raise GovernanceError(
                "hyperbolic-base tolerance lies outside the conditioned float64 "
                f"domain [{_MIN_GEOMETRY_TOLERANCE}, {_MAX_GEOMETRY_TOLERANCE}]"
            )
        radius = 1.0 / math.sqrt(-curvature)
        if (
            not math.isfinite(radius)
            or not _MIN_NUMERICAL_RADIUS <= radius <= _MAX_NUMERICAL_RADIUS
        ):
            raise GovernanceError(
                "hyperbolic radius lies outside the representable float64 domain"
            )
        radius_squared = radius * radius
        if not math.isfinite(radius_squared) or radius_squared <= 0.0:
            raise GovernanceError("hyperbolic radius squared must be finite and positive")
        object.__setattr__(self, "sectional_curvature", curvature)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "_radius", radius)
        object.__setattr__(self, "_radius_squared", radius_squared)

    @property
    def kappa(self) -> float:
        return -self.sectional_curvature

    @property
    def radius(self) -> float:
        return self._radius

    @property
    def radius_squared(self) -> float:
        return self._radius_squared

    @property
    def lorentz_metric(self) -> np.ndarray:
        return _readonly(np.diag([-1.0] + [1.0] * self.dimension))

    @property
    def tangent_signature(self) -> tuple[int, int]:
        return (self.dimension, 0)

    @property
    def ambient_signature(self) -> tuple[int, int]:
        return (self.dimension, 1)

    def to_spec(self) -> dict:
        return {
            "schema": _SCHEMA,
            "id": self.id,
            "dimension": self.dimension,
            "sectional_curvature": self.sectional_curvature,
            "scope": self.scope,
            "universal": True,
            "euclidean_control_declared": self.euclidean_control_declared,
            "canonical_model": "future_hyperboloid",
            "chart": "open_poincare_ball",
            "tangent_signature": list(self.tangent_signature),
            "ambient_signature": list(self.ambient_signature),
            "tolerance": self.tolerance,
            "numerical_domain": "conditioned-float64",
        }

    @classmethod
    def from_spec(cls, spec: dict) -> "PoincareBallBase":
        if not isinstance(spec, dict):
            raise GovernanceError("a hyperbolic-base specification must be a mapping")
        if spec.get("schema") != _SCHEMA:
            raise GovernanceError("unknown hyperbolic-base schema")
        if spec.get("universal") is not True:
            raise GovernanceError("a serialized Poincare base must be universal")
        dimension = spec.get("dimension")
        if isinstance(dimension, bool) or not isinstance(
            dimension, (int, np.integer)
        ):
            raise GovernanceError("serialized hyperbolic dimension must be an integer")
        if spec.get("canonical_model") != "future_hyperboloid":
            raise GovernanceError("serialized canonical model must be future_hyperboloid")
        if spec.get("chart") != "open_poincare_ball":
            raise GovernanceError("serialized chart must be open_poincare_ball")
        if spec.get("tangent_signature") != [int(dimension), 0]:
            raise GovernanceError("serialized tangent signature is inconsistent")
        if spec.get("ambient_signature") != [int(dimension), 1]:
            raise GovernanceError("serialized ambient signature is inconsistent")
        if spec.get("euclidean_control_declared") is not True:
            raise GovernanceError("serialized Euclidean control must be explicitly true")
        if spec.get("numerical_domain") != "conditioned-float64":
            raise GovernanceError("serialized numerical domain is not supported")
        return cls(
            id=spec.get("id", ""),
            dimension=dimension,
            sectional_curvature=spec.get("sectional_curvature", 0.0),
            scope=spec.get("scope", ""),
            euclidean_control_declared=True,
            tolerance=spec.get("tolerance", 0.0),
        )

    def _ball_point(self, value, name: str = "poincare_point") -> np.ndarray:
        point = _as_vector(value, name)
        if point.size != self.dimension:
            raise CarrierMismatch(
                f"{name} has dimension {point.size}; base {self.id} has {self.dimension}"
            )
        with np.errstate(over="ignore", invalid="ignore"):
            squared_norm = float(point @ point)
        if not math.isfinite(squared_norm):
            raise GovernanceError(f"{name} has a non-finite squared norm")
        if squared_norm >= 1.0:
            raise GovernanceError(f"{name} must lie strictly inside the open unit ball")
        return point

    def point(self, value, name: str = "poincare_point") -> np.ndarray:
        """Validate and freeze one point of the universal Poincare atlas."""

        return _readonly(self._ball_point(value, name))

    def _hyperboloid_point(self, value, name: str = "hyperboloid_point") -> np.ndarray:
        point = _as_vector(value, name)
        if point.size != self.dimension + 1:
            raise CarrierMismatch(
                f"{name} has dimension {point.size}; expected {self.dimension + 1}"
            )
        with np.errstate(over="ignore", invalid="ignore"):
            euclidean_squared = float(point @ point)
            lorentz_squared = self.lorentz_inner(point, point)
            constraint = lorentz_squared + self.radius_squared
            conditioning_error = (
                np.finfo(float).eps
                * euclidean_squared
                / self.radius_squared
            )
            relative_constraint = abs(constraint) / self.radius_squared
        if not all(
            math.isfinite(value)
            for value in (
                euclidean_squared,
                lorentz_squared,
                constraint,
                conditioning_error,
                relative_constraint,
            )
        ):
            raise GovernanceError(f"{name} has non-finite Lorentz diagnostics")
        if conditioning_error > self.tolerance / 8.0:
            raise GovernanceError(
                f"{name} is outside the conditioned float64 hyperboloid domain"
            )
        if relative_constraint > self.tolerance:
            raise GovernanceError(f"{name} does not lie on the declared hyperboloid")
        if point[0] <= 0.0:
            raise GovernanceError(f"{name} lies on the past sheet")
        return point

    def lorentz_inner(self, left, right) -> float:
        left = _as_vector(left, "lorentz.left")
        right = _as_vector(right, "lorentz.right")
        if left.shape != right.shape or left.size != self.dimension + 1:
            raise CarrierMismatch("Lorentz operands must share the base ambient carrier")
        with np.errstate(over="ignore", invalid="ignore"):
            value = float(left @ self.lorentz_metric @ right)
        return _finite(value, "Lorentz inner product")

    def metric_tensor(self, point) -> np.ndarray:
        point = self._ball_point(point)
        factor = 2.0 * self.radius / (1.0 - float(point @ point))
        with np.errstate(over="ignore", invalid="ignore"):
            metric = (factor * factor) * np.eye(self.dimension)
        if not np.all(np.isfinite(metric)):
            raise GovernanceError("Poincare metric is not representable in float64")
        return _readonly(metric)

    def distance(self, left, right) -> float:
        """Stable Poincare distance, including separations below sqrt(eps)."""

        left = self._ball_point(left, "distance.left")
        right = self._ball_point(right, "distance.right")
        left_margin = 1.0 - float(left @ left)
        right_margin = 1.0 - float(right @ right)
        ratio = float(np.linalg.norm(left - right)) / math.sqrt(
            left_margin * right_margin
        )
        distance = float(2.0 * self.radius * np.arcsinh(ratio))
        return _finite(distance, "Poincare distance")

    def to_hyperboloid(self, point) -> np.ndarray:
        point = self._ball_point(point)
        denominator = 1.0 - float(point @ point)
        lifted = np.concatenate(
            (
                [self.radius * (1.0 + float(point @ point)) / denominator],
                2.0 * self.radius * point / denominator,
            )
        )
        if not np.all(np.isfinite(lifted)):
            raise GovernanceError("hyperboloid lift is not representable in float64")
        return _readonly(self._hyperboloid_point(lifted, "hyperboloid_lift"))

    def from_hyperboloid(self, point) -> np.ndarray:
        point = self._hyperboloid_point(point)
        denominator = point[0] + self.radius
        if not math.isfinite(denominator) or denominator <= 0.0:
            raise GovernanceError("hyperboloid chart denominator is not positive")
        chart_point = point[1:] / denominator
        return _readonly(self._ball_point(chart_point, "hyperboloid_chart"))

    def hyperboloid_distance(self, left, right) -> float:
        left = self._hyperboloid_point(left, "hyperboloid_distance.left")
        right = self._hyperboloid_point(right, "hyperboloid_distance.right")
        difference = right - left
        squared_chord = self.lorentz_inner(difference, difference)
        if squared_chord < -self.tolerance * self.radius_squared:
            raise GovernanceError("hyperboloid chord has an invalid timelike separation")
        half_chord = 0.5 * math.sqrt(max(0.0, squared_chord)) / self.radius
        distance = float(2.0 * self.radius * np.arcsinh(half_chord))
        return _finite(distance, "hyperboloid distance")

    def tangent_norm(self, point, tangent) -> float:
        point = self._hyperboloid_point(point, "tangent.base")
        tangent = _as_vector(tangent, "tangent.vector")
        if tangent.size != self.dimension + 1:
            raise CarrierMismatch("tangent vector has the wrong ambient dimension")
        orthogonality = self.lorentz_inner(point, tangent)
        point_norm = float(np.linalg.norm(point))
        tangent_norm = float(np.linalg.norm(tangent))
        reference = self.radius * max(self.radius, tangent_norm)
        conditioning_error = (
            np.finfo(float).eps * point_norm * tangent_norm / reference
        )
        relative_orthogonality = abs(orthogonality) / reference
        if not all(
            math.isfinite(value)
            for value in (
                point_norm,
                tangent_norm,
                reference,
                conditioning_error,
                relative_orthogonality,
            )
        ):
            raise GovernanceError("tangent diagnostics must be finite")
        if conditioning_error > self.tolerance / 8.0:
            raise GovernanceError(
                "tangent is outside the conditioned float64 hyperboloid domain"
            )
        if relative_orthogonality > self.tolerance:
            raise GovernanceError("vector is not tangent to the hyperboloid")
        squared_norm = self.lorentz_inner(tangent, tangent)
        if squared_norm < 0.0:
            raise GovernanceError("hyperbolic tangent metric must be positive definite")
        return math.sqrt(max(0.0, squared_norm))

    def exp(self, point, tangent) -> np.ndarray:
        point = self._hyperboloid_point(point, "exp.base")
        tangent = _as_vector(tangent, "exp.tangent")
        norm = self.tangent_norm(point, tangent)
        z = norm / self.radius
        maximum_conditioned_rapidity = 0.5 * math.log(
            self.tolerance / (8.0 * np.finfo(float).eps)
        )
        if z > maximum_conditioned_rapidity:
            raise GovernanceError(
                "exponential step exceeds the conditioned hyperboloid domain"
            )
        sinhc = 1.0 + z * z / 6.0 if abs(z) < 1e-8 else math.sinh(z) / z
        result = math.cosh(z) * point + sinhc * tangent
        if not np.all(np.isfinite(result)):
            raise GovernanceError("exponential result is not representable in float64")
        return _readonly(self._hyperboloid_point(result, "exp.result"))

    def log(self, left, right) -> np.ndarray:
        left = self._hyperboloid_point(left, "log.left")
        right = self._hyperboloid_point(right, "log.right")
        distance = self.hyperboloid_distance(left, right)
        z = distance / self.radius
        factor = 1.0 - z * z / 6.0 if abs(z) < 1e-8 else z / math.sinh(z)
        tangent = factor * (right - math.cosh(z) * left)
        self.tangent_norm(left, tangent)
        return _readonly(tangent)

    def parallel_transport(self, left, right, tangent) -> np.ndarray:
        left = self._hyperboloid_point(left, "transport.left")
        right = self._hyperboloid_point(right, "transport.right")
        tangent = _as_vector(tangent, "transport.tangent")
        source_norm = self.tangent_norm(left, tangent)
        denominator = self.radius**2 - self.lorentz_inner(left, right)
        if denominator <= 0.0:
            raise GovernanceError("parallel-transport denominator is not positive")
        transported = tangent + (
            self.lorentz_inner(right, tangent) / denominator
        ) * (left + right)
        target_norm = self.tangent_norm(right, transported)
        if abs(source_norm - target_norm) > self.tolerance * max(
            self.radius, source_norm
        ):
            raise GovernanceError("parallel transport failed its tangent-norm invariant")
        return _readonly(transported)

    def apply_isometry(self, isometry: LorentzIsometry, point) -> np.ndarray:
        if isometry.dimension != self.dimension:
            raise CarrierMismatch("Lorentz isometry dimension does not match the base")
        point = self._hyperboloid_point(point, "isometry.point")
        return _readonly(
            self._hyperboloid_point(isometry.matrix @ point, "isometry.result")
        )

    def radial_point(self, distance: float, direction) -> np.ndarray:
        distance = _finite(distance, "radial.distance")
        if distance < 0.0:
            raise GovernanceError("radial distance must be non-negative")
        direction = _as_vector(direction, "radial.direction")
        if direction.size != self.dimension:
            raise CarrierMismatch("radial direction has the wrong dimension")
        norm = float(np.linalg.norm(direction))
        if norm <= self.tolerance:
            raise GovernanceError("radial direction must be non-zero")
        if distance / self.radius > _MAX_BALL_DISTANCE_IN_RADII:
            raise GovernanceError(
                "radial distance exceeds the representable open-ball domain"
            )
        radius = math.tanh(distance / (2.0 * self.radius))
        point = radius * direction / norm
        if not np.all(np.isfinite(point)) or float(point @ point) >= 1.0:
            raise GovernanceError("radial point is not representable inside the open ball")
        return _readonly(point)

    def review(
        self,
        points: Iterable[np.ndarray],
        isometries: Iterable[LorentzIsometry] = (),
    ) -> HyperbolicBaseReview:
        """Audit dimensionless internal invariants, not empirical suitability."""

        points = tuple(self._ball_point(point, "review.point") for point in points)
        if len(points) < 2:
            raise GovernanceError(
                "a hyperbolic-base review needs at least two points"
            )
        isometries = tuple(isometries)
        for isometry in isometries:
            if not isinstance(isometry, LorentzIsometry):
                raise GovernanceError("review isometries must be typed LorentzIsometry")
            if isometry.dimension != self.dimension:
                raise CarrierMismatch(
                    "review isometry dimension does not match the hyperbolic base"
                )
        lifts = tuple(self.to_hyperboloid(point) for point in points)
        margins = tuple(1.0 - float(point @ point) for point in points)
        metric_minima = tuple(
            float(np.min(np.linalg.eigvalsh(self.metric_tensor(point))))
            for point in points
        )
        roundtrips = tuple(
            float(np.linalg.norm(self.from_hyperboloid(lift) - point))
            for point, lift in zip(points, lifts)
        )
        constraints = tuple(
            abs(self.lorentz_inner(lift, lift) + self.radius_squared)
            / self.radius_squared
            for lift in lifts
        )

        distance_defects = []
        isometry_defects = []
        pair_count = 0
        for left_index in range(len(points)):
            for right_index in range(left_index + 1, len(points)):
                pair_count += 1
                ball_distance = self.distance(points[left_index], points[right_index])
                hyperboloid_distance = self.hyperboloid_distance(
                    lifts[left_index],
                    lifts[right_index],
                )
                distance_defects.append(
                    abs(ball_distance - hyperboloid_distance)
                    / max(self.radius, ball_distance, hyperboloid_distance)
                )
                for isometry in isometries:
                    moved_left = self.apply_isometry(isometry, lifts[left_index])
                    moved_right = self.apply_isometry(isometry, lifts[right_index])
                    isometry_defects.append(
                        abs(
                            hyperboloid_distance
                            - self.hyperboloid_distance(moved_left, moved_right)
                        )
                        / max(self.radius, hyperboloid_distance)
                    )

        maximum_roundtrip = max(roundtrips, default=0.0)
        maximum_constraint = max(constraints, default=0.0)
        maximum_distance = max(distance_defects, default=0.0)
        maximum_isometry = max(isometry_defects, default=0.0)
        diagnostics = (
            margins
            + metric_minima
            + roundtrips
            + constraints
            + tuple(distance_defects)
            + tuple(isometry_defects)
        )
        review_tolerance = max(100.0 * self.tolerance, 1024.0 * np.finfo(float).eps)
        violations = []
        if not all(math.isfinite(value) for value in diagnostics):
            violations.append("nonfinite_review_diagnostic")
        if min(margins) <= 0.0:
            violations.append("nonpositive_boundary_margin")
        if min(metric_minima) <= 0.0:
            violations.append("nonpositive_tangent_metric")
        if maximum_roundtrip > review_tolerance:
            violations.append("chart_roundtrip_defect")
        if maximum_constraint > review_tolerance:
            violations.append("hyperboloid_constraint_defect")
        if maximum_distance > review_tolerance:
            violations.append("distance_chart_disagreement")
        if maximum_isometry > review_tolerance:
            violations.append("isometry_distance_defect")

        return HyperbolicBaseReview(
            base_id=self.id,
            dimension=self.dimension,
            points_reviewed=len(points),
            pairs_reviewed=pair_count,
            isometries_reviewed=len(isometries),
            minimum_boundary_margin=min(margins),
            minimum_metric_eigenvalue=min(metric_minima),
            maximum_chart_roundtrip_defect=maximum_roundtrip,
            maximum_hyperboloid_constraint_defect=maximum_constraint,
            maximum_distance_chart_defect=maximum_distance,
            maximum_isometry_distance_defect=maximum_isometry,
            passed=not violations,
            violations=tuple(violations),
        )


UNIVERSAL_POINCARE_BASE = PoincareBallBase(
    "AION-universal-H4",
    4,
    sectional_curvature=-1.0,
    scope="universal_atlas",
    euclidean_control_declared=True,
)

UNIVERSAL_EUCLIDEAN_CONTROL = EuclideanBaseControl(
    "AION-universal-euclidean-control-R4",
    4,
    metric_scale=2.0 * UNIVERSAL_POINCARE_BASE.radius,
)
