"""The causal advantage cone: promotion is not a scalar either.

The Atlas escaped one scalar and left a second one sovereign over it:

    promote  iff  q_causal > 0

That reinstalls a monarch. Cognitive benefit is not one axis. A quantum organ
may improve compositional generalisation, delayed-memory recovery, robustness
and sample efficiency while worsening latency, energy, calibration and recovery
after failure. Collapsing that to one number chooses a weighting in secret.

The replacement: promotion is a statement about a *region*.

    Promote_tau(O)  iff  Pr( DeltaY_tau in K_tau ) >= 1 - alpha
                    and  audit >= eta
                    and  compute parity holds
                    and  no safety or resource constraint is violated

where DeltaY is the multi-dimensional intervention effect against a *matched
free-theory control*, and K is a pre-registered admissible improvement cone.

The cone must be declared before the experiment. Choosing it afterwards is how a
weighting gets picked to fit the result, which is the same failure as choosing
the scalar afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Sequence

import numpy as np

__all__ = [
    "OUTCOME_DIMENSIONS",
    "Direction",
    "OutcomeVector",
    "AdvantageCone",
    "EffectPosterior",
    "EmpiricalEffectPosterior",
    "PromotionDecision",
    "promote",
]


# Sign convention: every dimension is stated so that HIGHER IS BETTER.
# Cost-like quantities are therefore negated at measurement time.
OUTCOME_DIMENSIONS = (
    "accuracy",
    "generalization",
    "robustness",
    "sample_efficiency",
    "calibration",
    "neg_energy",       # negated cost
    "neg_latency",      # negated cost
    "recovery",
)


class Direction:
    """What the pre-registered cone demands of one outcome dimension."""

    IMPROVE = "improve"        # must strictly increase
    NO_WORSE = "no_worse"      # must not decrease
    FREE = "free"              # not constrained


@dataclass(frozen=True)
class OutcomeVector:
    """One typed, non-scalar outcome on the registered eight-coordinate atlas.

    Missing measurements are represented twice on purpose: by ``NaN`` in
    ``values`` *and* by ``False`` in ``observed``.  The redundancy prevents a
    downstream consumer from silently treating a missing cost or recovery axis
    as a measured zero.
    """

    values: np.ndarray
    observed: np.ndarray

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        observed = np.asarray(self.observed, dtype=bool)
        shape = (len(OUTCOME_DIMENSIONS),)
        if values.shape != shape:
            raise ValueError(
                f"outcome values must follow {OUTCOME_DIMENSIONS!r} "
                f"with shape {shape}, got {values.shape}"
            )
        if observed.shape != shape:
            raise ValueError(
                f"outcome observed mask must have shape {shape}, "
                f"got {observed.shape}"
            )
        if not np.all(np.isfinite(values[observed])):
            raise ValueError("every observed outcome coordinate must be finite")
        if not np.all(np.isnan(values[~observed])):
            raise ValueError(
                "every unobserved outcome coordinate must be NaN as well as masked"
            )
        values = values.copy()
        observed = observed.copy()
        values.setflags(write=False)
        observed.setflags(write=False)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "observed", observed)

    @classmethod
    def from_mapping(
        cls,
        values: dict[str, float],
        *,
        observed: Sequence[str] | None = None,
    ) -> "OutcomeVector":
        """Build without allowing coordinate-order drift or unknown names."""
        unknown = set(values) - set(OUTCOME_DIMENSIONS)
        if unknown:
            raise ValueError(f"unknown outcome dimension(s): {sorted(unknown)}")
        observed_names = set(values if observed is None else observed)
        unknown_observed = observed_names - set(OUTCOME_DIMENSIONS)
        if unknown_observed:
            raise ValueError(
                f"unknown observed outcome dimension(s): {sorted(unknown_observed)}"
            )
        missing_values = observed_names - set(values)
        if missing_values:
            raise ValueError(
                f"observed dimensions lack values: {sorted(missing_values)}"
            )
        vector = np.full(len(OUTCOME_DIMENSIONS), np.nan, dtype=float)
        mask = np.zeros(len(OUTCOME_DIMENSIONS), dtype=bool)
        for index, dimension in enumerate(OUTCOME_DIMENSIONS):
            if dimension in observed_names:
                vector[index] = float(values[dimension])
                mask[index] = True
        return cls(vector, mask)

    @property
    def missing_dimensions(self) -> tuple[str, ...]:
        return tuple(
            dimension
            for dimension, is_observed in zip(OUTCOME_DIMENSIONS, self.observed)
            if not is_observed
        )

    def to_dict(self) -> dict:
        return {
            "coordinate_order": list(OUTCOME_DIMENSIONS),
            "values": {
                dimension: (float(value) if is_observed else None)
                for dimension, value, is_observed in zip(
                    OUTCOME_DIMENSIONS, self.values, self.observed
                )
            },
            "observed": {
                dimension: bool(is_observed)
                for dimension, is_observed in zip(
                    OUTCOME_DIMENSIONS, self.observed
                )
            },
            "missing_dimensions": list(self.missing_dimensions),
        }

    def as_dict(self) -> dict[str, float | None]:
        """Compact coordinate mapping used by result artifacts."""
        return {
            dimension: (float(value) if is_observed else None)
            for dimension, value, is_observed in zip(
                OUTCOME_DIMENSIONS, self.values, self.observed
            )
        }

    def __float__(self) -> float:
        raise TypeError(
            "OutcomeVector has no scalar conversion; evaluate a pre-registered cone"
        )


@dataclass
class AdvantageCone:
    """A pre-registered region of admissible improvement.

    ``constraints`` maps outcome dimension -> Direction.  ``margins`` optionally
    requires a minimum effect size on IMPROVE dimensions, so that a
    statistically detectable but practically irrelevant gain does not promote.
    """

    name: str
    constraints: dict = field(default_factory=dict)
    margins: dict = field(default_factory=dict)
    tolerance: float = 0.0     # allowed slack on NO_WORSE dimensions

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("advantage cone name must be a non-empty string")
        known = set(OUTCOME_DIMENSIONS)
        unknown_constraints = set(self.constraints) - known
        if unknown_constraints:
            raise ValueError(
                f"unknown constrained dimension(s): {sorted(unknown_constraints)}"
            )
        unknown_margins = set(self.margins) - known
        if unknown_margins:
            raise ValueError(
                f"unknown margin dimension(s): {sorted(unknown_margins)}"
            )
        directions = {Direction.IMPROVE, Direction.NO_WORSE, Direction.FREE}
        invalid = {
            dimension: direction
            for dimension, direction in self.constraints.items()
            if direction not in directions
        }
        if invalid:
            raise ValueError(f"invalid cone direction(s): {invalid}")
        if not np.isfinite(self.tolerance) or self.tolerance < 0:
            raise ValueError("cone tolerance must be finite and non-negative")
        for dimension, margin in self.margins.items():
            if not np.isfinite(float(margin)):
                raise ValueError(f"margin for {dimension} must be finite")

    @property
    def required_dimensions(self) -> tuple[str, ...]:
        return tuple(
            dimension
            for dimension in OUTCOME_DIMENSIONS
            if self.constraints.get(dimension, Direction.FREE) != Direction.FREE
        )

    def contains(self, delta: np.ndarray) -> bool:
        """Is a single effect vector inside the cone?"""
        delta = np.asarray(delta, dtype=float)
        if delta.shape != (len(OUTCOME_DIMENSIONS),):
            raise ValueError(
                f"effect vector must have shape {(len(OUTCOME_DIMENSIONS),)}, "
                f"got {delta.shape}"
            )
        for i, dim in enumerate(OUTCOME_DIMENSIONS):
            rule = self.constraints.get(dim, Direction.FREE)
            if rule != Direction.FREE and not np.isfinite(delta[i]):
                return False
            if rule == Direction.IMPROVE:
                if delta[i] <= self.margins.get(dim, 0.0):
                    return False
            elif rule == Direction.NO_WORSE:
                if delta[i] < -self.tolerance:
                    return False
        return True

    def __str__(self) -> str:  # pragma: no cover - display only
        parts = []
        for dim in OUTCOME_DIMENSIONS:
            rule = self.constraints.get(dim, Direction.FREE)
            if rule == Direction.IMPROVE:
                parts.append(f"{dim} > {self.margins.get(dim, 0.0):g}")
            elif rule == Direction.NO_WORSE:
                parts.append(f"{dim} >= -{self.tolerance:g}")
        return f"{self.name}: " + ", ".join(parts) if parts else f"{self.name}: (unconstrained)"


@dataclass
class EffectPosterior:
    """Uncertainty about the intervention effect, not a point estimate.

    ``mean`` and ``cov`` describe DeltaY = Y_quantum - Y_matched_free_control.
    """

    mean: np.ndarray
    cov: np.ndarray

    def __post_init__(self) -> None:
        self.mean = np.asarray(self.mean, dtype=float)
        self.cov = np.asarray(self.cov, dtype=float)
        expected = len(OUTCOME_DIMENSIONS)
        if self.mean.shape != (expected,):
            raise ValueError(
                f"posterior mean must have shape {(expected,)}, "
                f"got {self.mean.shape}"
            )
        if self.cov.shape != (expected, expected):
            raise ValueError(
                f"posterior covariance must have shape {(expected, expected)}, "
                f"got {self.cov.shape}"
            )
        if not np.all(np.isfinite(self.mean)) or not np.all(np.isfinite(self.cov)):
            raise ValueError("legacy Gaussian posterior must be fully finite")
        if not np.allclose(self.cov, self.cov.T, atol=1e-12, rtol=0.0):
            raise ValueError("posterior covariance must be symmetric")
        if np.min(np.linalg.eigvalsh(self.cov)) < -1e-12:
            raise ValueError("posterior covariance must be positive semidefinite")

    @property
    def missing_dimensions(self) -> tuple[str, ...]:
        return ()

    def sample(self, n: int, seed: int = 0) -> np.ndarray:
        if not isinstance(n, (int, np.integer)) or n <= 0:
            raise ValueError("posterior sample count must be a positive integer")
        rng = np.random.default_rng(seed)
        return rng.multivariate_normal(self.mean, self.cov, size=n)


@dataclass
class EmpiricalEffectPosterior:
    """Paired seed-cluster uncertainty with its joint dependence intact.

    ``bootstrap_draws`` contains *whole eight-coordinate mean vectors*.  Sampling
    chooses rows, never coordinates, so correlations induced by a shared seed
    schedule survive the posterior interface.
    """

    cluster_effects: np.ndarray
    bootstrap_draws: np.ndarray
    observed: np.ndarray
    bootstrap_seed: int

    def __post_init__(self) -> None:
        expected = len(OUTCOME_DIMENSIONS)
        self.cluster_effects = np.asarray(self.cluster_effects, dtype=float)
        self.bootstrap_draws = np.asarray(self.bootstrap_draws, dtype=float)
        self.observed = np.asarray(self.observed, dtype=bool)
        if self.cluster_effects.ndim != 2 or self.cluster_effects.shape[1] != expected:
            raise ValueError(
                f"cluster effects must have shape (n, {expected})"
            )
        if self.cluster_effects.shape[0] < 2:
            raise ValueError("paired empirical posterior requires at least two clusters")
        if (
            self.bootstrap_draws.ndim != 2
            or self.bootstrap_draws.shape[1] != expected
            or self.bootstrap_draws.shape[0] == 0
        ):
            raise ValueError(
                f"bootstrap draws must have non-empty shape (draws, {expected})"
            )
        if self.observed.shape != (expected,):
            raise ValueError(f"observed mask must have shape {(expected,)}")
        for array_name, array in (
            ("cluster effects", self.cluster_effects),
            ("bootstrap draws", self.bootstrap_draws),
        ):
            if not np.all(np.isfinite(array[:, self.observed])):
                raise ValueError(f"observed {array_name} must be finite")
            if not np.all(np.isnan(array[:, ~self.observed])):
                raise ValueError(
                    f"missing {array_name} must remain NaN and explicitly masked"
                )

    @classmethod
    def from_paired(
        cls,
        target: Sequence[OutcomeVector],
        control: Sequence[OutcomeVector],
        *,
        draws: int = 20_000,
        seed: int = 0,
    ) -> "EmpiricalEffectPosterior":
        if len(target) != len(control):
            raise ValueError("target and control must contain the same seed clusters")
        if len(target) < 2:
            raise ValueError("paired empirical posterior requires at least two clusters")
        if not isinstance(draws, (int, np.integer)) or draws <= 0:
            raise ValueError("bootstrap draw count must be a positive integer")
        if not all(isinstance(vector, OutcomeVector) for vector in (*target, *control)):
            raise TypeError("paired effects require OutcomeVector instances")

        observed = target[0].observed
        for vector in (*target, *control):
            if not np.array_equal(vector.observed, observed):
                raise ValueError(
                    "all paired outcome vectors must have the same observed mask"
                )

        target_values = np.stack([vector.values for vector in target])
        control_values = np.stack([vector.values for vector in control])
        effects = target_values - control_values
        rng = np.random.default_rng(seed)
        indices = rng.integers(
            0, len(target), size=(int(draws), len(target)), endpoint=False
        )
        boot = np.full((int(draws), len(OUTCOME_DIMENSIONS)), np.nan, dtype=float)
        boot[:, observed] = effects[indices][:, :, observed].mean(axis=1)
        return cls(
            cluster_effects=effects,
            bootstrap_draws=boot,
            observed=observed.copy(),
            bootstrap_seed=int(seed),
        )

    @property
    def missing_dimensions(self) -> tuple[str, ...]:
        return tuple(
            dimension
            for dimension, is_observed in zip(OUTCOME_DIMENSIONS, self.observed)
            if not is_observed
        )

    @property
    def mean(self) -> np.ndarray:
        mean = np.full(len(OUTCOME_DIMENSIONS), np.nan, dtype=float)
        mean[self.observed] = self.cluster_effects[:, self.observed].mean(axis=0)
        return mean

    @property
    def draw_digest(self) -> str:
        payload = {
            "bootstrap_seed": self.bootstrap_seed,
            "observed": self.observed.astype(int).tolist(),
            "draws": [
                [
                    float(value) if is_observed else None
                    for value, is_observed in zip(row, self.observed)
                ]
                for row in self.bootstrap_draws
            ],
        }
        encoded = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def interval(self, level: float = 0.99) -> dict[str, tuple[float, float] | None]:
        if not 0.0 < level < 1.0:
            raise ValueError("interval level must lie strictly between zero and one")
        tail = (1.0 - level) / 2.0
        result: dict[str, tuple[float, float] | None] = {}
        for index, dimension in enumerate(OUTCOME_DIMENSIONS):
            if not self.observed[index]:
                result[dimension] = None
                continue
            low, high = np.quantile(
                self.bootstrap_draws[:, index], [tail, 1.0 - tail]
            )
            result[dimension] = (float(low), float(high))
        return result

    def sample(self, n: int, seed: int = 0) -> np.ndarray:
        if not isinstance(n, (int, np.integer)) or n <= 0:
            raise ValueError("posterior sample count must be a positive integer")
        rng = np.random.default_rng(seed)
        indices = rng.integers(
            0, self.bootstrap_draws.shape[0], size=int(n), endpoint=False
        )
        return self.bootstrap_draws[indices].copy()


@dataclass
class PromotionDecision:
    """The outcome of a pre-registered promotion test."""

    promoted: bool
    probability: float | None
    alpha: float
    cone: str
    blockers: tuple = ()

    def __str__(self) -> str:  # pragma: no cover - display only
        head = "PROMOTE" if self.promoted else "HOLD"
        probability = (
            "undefined"
            if self.probability is None
            else f"{self.probability:.3f}"
        )
        line = (
            f"{head}: Pr(DeltaY in {self.cone}) = {probability} "
            f"(need >= {1 - self.alpha:.3f})"
        )
        if self.blockers:
            line += "\n  blocked by: " + "; ".join(self.blockers)
        return line


def promote(posterior: EffectPosterior | EmpiricalEffectPosterior,
            cone: AdvantageCone,
            alpha: float = 0.05,
            audit: float = 1.0,
            audit_threshold: float = 0.5,
            compute_parity: bool = True,
            constraints_ok: bool = True,
            samples: int = 20000,
            seed: int = 0) -> PromotionDecision:
    """Decide promotion against a pre-registered cone.

    Every gate is separate and every failure is named.  A high probability of
    landing in the cone does not promote an organ that failed compute parity or
    lacks external audit: those are not tradeable against effect size.
    """
    if not isinstance(posterior, (EffectPosterior, EmpiricalEffectPosterior)):
        raise TypeError(
            "posterior must be EffectPosterior or EmpiricalEffectPosterior"
        )
    if not isinstance(cone, AdvantageCone):
        raise TypeError("cone must be an AdvantageCone")
    if not np.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between zero and one")
    if not isinstance(samples, (int, np.integer)) or samples <= 0:
        raise ValueError("samples must be a positive integer")

    missing = tuple(
        dimension
        for dimension in cone.required_dimensions
        if dimension in posterior.missing_dimensions
    )
    blockers = []
    if missing:
        blockers.append(
            "cone-constrained outcome(s) unmeasured: " + ", ".join(missing)
        )
        if audit < audit_threshold:
            blockers.append(
                f"audit strength {audit:.2f} below {audit_threshold:.2f}"
            )
        if not compute_parity:
            blockers.append("compute/parameter/sampling parity not established")
        if not constraints_ok:
            blockers.append("a safety or resource constraint is violated")
        return PromotionDecision(
            promoted=False,
            probability=None,
            alpha=alpha,
            cone=cone.name,
            blockers=tuple(blockers),
        )

    draws = posterior.sample(samples, seed=seed)
    inside = np.mean([cone.contains(d) for d in draws])

    if inside < 1 - alpha:
        blockers.append(f"effect probability {inside:.3f} below {1 - alpha:.3f}")
    if audit < audit_threshold:
        blockers.append(f"audit strength {audit:.2f} below {audit_threshold:.2f}")
    if not compute_parity:
        blockers.append("compute/parameter/sampling parity not established")
    if not constraints_ok:
        blockers.append("a safety or resource constraint is violated")

    return PromotionDecision(
        promoted=not blockers,
        probability=float(inside),
        alpha=alpha,
        cone=cone.name,
        blockers=tuple(blockers),
    )
