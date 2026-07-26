"""The resource reservoir, as a view over the existing Bordon model.

:mod:`aionq.bordon` already implements the reservoir with its one sharp
consequence -- ``drone_ceiling == refill_rate``, because a finite reservoir
cannot fund an uninterrupted channel forever.  This module does not reimplement
that; it wraps it in the vocabulary S4-G100 needs and adds the throttling policy.

The split that matters:

    invariant channel     provenance, identity continuity, correction history,
                          audit logging, raw evidence retention.  Continuous.
                          Never a source of savings.
    speculative channel   candidate generation, alternate frames, perturbation
                          sweeps, higher-order search.  Interruptible.

The invariant channel maps onto the bordón (drone) and the speculative channel
onto the puntero (melody).  That is not decoration: the drone ceiling theorem is
exactly the statement that ``invariant_draw <= refill_rate`` is *necessary* for
indefinite survival, which is theorem target P4.

Throttling order is fixed and is not a policy knob:

    1. narrow speculative branching
    2. shorten unresolved lifetimes
    3. preserve evidence and provenance
    4. record the intervention

Step 3 is unconditional.  There is no code path in this module that reduces the
invariant draw, which is the structural version of "never sacrificed".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..bordon import BordonBreath, Fol, Pipe, PipeKind

__all__ = ["BordonBudget", "ThrottleEvent", "CollapseState"]


class CollapseState:
    HEALTHY = "healthy"
    THROTTLED = "throttled"
    INVARIANT_AT_RISK = "invariant_at_risk"
    COLLAPSED = "collapsed"


@dataclass(frozen=True)
class ThrottleEvent:
    """A recorded intervention.  Step 4 of the policy, made non-optional."""

    step: int
    action: str
    before: float
    after: float
    level: float
    reason: str


@dataclass
class BordonBudget:
    """Reservoir with an invariant and a speculative channel."""

    capacity: float
    refill_rate: float
    invariant_draw: float
    speculative_draw: float = 0.0
    level: float = None            # type: ignore[assignment]
    interventions: list = field(default_factory=list)
    state: str = CollapseState.HEALTHY

    def __post_init__(self) -> None:
        if self.level is None:
            self.level = self.capacity
        for name in ("capacity", "refill_rate", "invariant_draw", "speculative_draw"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")

    # -- the theorem, exposed --------------------------------------------------

    @property
    def drone_ceiling(self) -> float:
        """The largest indefinitely fundable continuous draw: the refill rate.

        Delegated to :class:`aionq.bordon.BordonBreath` so there is exactly one
        implementation of this claim in the repository.
        """
        return self._breath().drone_ceiling

    @property
    def invariant_survives(self) -> bool:
        """``invariant_draw <= refill_rate``: necessary for indefinite survival."""
        return self.invariant_draw <= self.drone_ceiling + 1e-12

    def depletion_time(self) -> float:
        """Ticks until the reservoir empties at the current constant draw.

        Infinite when total draw is within refill.  Finite whenever the draw
        exceeds it, *for any finite capacity* -- which is P4.
        """
        deficit = self.invariant_draw + self.speculative_draw - self.refill_rate
        if deficit <= 1e-12:
            return math.inf
        return self.level / deficit

    def _breath(self) -> BordonBreath:
        return BordonBreath(
            fol=Fol(capacity=self.capacity, refill_rate=self.refill_rate,
                    level=self.level),
            pipes=(Pipe("invariant", PipeKind.BORDON, self.invariant_draw),
                   Pipe("speculative", PipeKind.PUNTERO, self.speculative_draw)))

    # -- dynamics --------------------------------------------------------------

    @property
    def pressure(self) -> float:
        """How close to empty, in [0, 1].  The signal the aperture responds to."""
        if self.capacity <= 0:
            return 1.0
        headroom = self.level / self.capacity
        return float(min(1.0, max(0.0, 1.0 - headroom)))

    def charge(self, speculative_draw: float) -> None:
        self.speculative_draw = float(max(0.0, speculative_draw))

    def tick(self, step: int, aperture=None) -> str:
        """Advance one tick and throttle if needed.  Never touches the invariant."""
        draw = self.invariant_draw + self.speculative_draw
        self.level = min(self.capacity, self.level + self.refill_rate - draw)

        if self.level > 0.0:
            self.state = (CollapseState.HEALTHY if not self.interventions
                          or self.interventions[-1].step != step
                          else CollapseState.THROTTLED)
            if not self.invariant_survives:
                self.state = CollapseState.INVARIANT_AT_RISK
            return self.state

        # Out of pressure. Policy order is fixed.
        self.level = 0.0
        if aperture is not None and aperture.branch_width > aperture.bounds.kappa_min:
            before = aperture.branch_width
            aperture.set("branch_width", max(aperture.bounds.kappa_min,
                                             int(before // 2)),
                         step, "bordon: reservoir empty, narrow speculation",
                         self.pressure)
            self.interventions.append(ThrottleEvent(
                step, "narrow_branch_width", float(before),
                float(aperture.branch_width), self.level,
                "step 1: speculative branching is the first thing cut"))
            self.state = CollapseState.THROTTLED
            return self.state

        if aperture is not None and \
                aperture.unresolved_lifetime > aperture.bounds.tau_min:
            before = aperture.unresolved_lifetime
            aperture.set("unresolved_lifetime",
                         max(aperture.bounds.tau_min, before / 2.0),
                         step, "bordon: reservoir empty, shorten lifetimes",
                         self.pressure)
            self.interventions.append(ThrottleEvent(
                step, "shorten_unresolved_lifetime", float(before),
                float(aperture.unresolved_lifetime), self.level,
                "step 2: unresolved lifetimes are cut only after branch width"))
            self.state = CollapseState.THROTTLED
            return self.state

        # Speculation is already minimal. The invariant channel is NOT cut.
        self.interventions.append(ThrottleEvent(
            step, "hold_invariant", self.invariant_draw, self.invariant_draw,
            self.level,
            "step 3: speculation is exhausted; the invariant channel is preserved "
            "and the deficit is reported instead of being absorbed by cutting it"))
        self.state = (CollapseState.COLLAPSED if not self.invariant_survives
                      else CollapseState.THROTTLED)
        return self.state

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"level {self.level:.2f}/{self.capacity:.2f} refill "
                f"{self.refill_rate:.2f} invariant {self.invariant_draw:.2f} "
                f"speculative {self.speculative_draw:.2f} [{self.state}]")
