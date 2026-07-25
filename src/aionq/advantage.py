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

import numpy as np

__all__ = ["OUTCOME_DIMENSIONS", "Direction", "AdvantageCone", "EffectPosterior",
           "PromotionDecision", "promote"]


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

    def contains(self, delta: np.ndarray) -> bool:
        """Is a single effect vector inside the cone?"""
        delta = np.asarray(delta, dtype=float)
        for i, dim in enumerate(OUTCOME_DIMENSIONS):
            rule = self.constraints.get(dim, Direction.FREE)
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

    def sample(self, n: int, seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.multivariate_normal(np.asarray(self.mean, dtype=float),
                                       np.asarray(self.cov, dtype=float), size=n)


@dataclass
class PromotionDecision:
    """The outcome of a pre-registered promotion test."""

    promoted: bool
    probability: float
    alpha: float
    cone: str
    blockers: tuple = ()

    def __str__(self) -> str:  # pragma: no cover - display only
        head = "PROMOTE" if self.promoted else "HOLD"
        line = (f"{head}: Pr(DeltaY in {self.cone}) = {self.probability:.3f} "
                f"(need >= {1 - self.alpha:.3f})")
        if self.blockers:
            line += "\n  blocked by: " + "; ".join(self.blockers)
        return line


def promote(posterior: EffectPosterior,
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
    draws = posterior.sample(samples, seed=seed)
    inside = np.mean([cone.contains(d) for d in draws])

    blockers = []
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
