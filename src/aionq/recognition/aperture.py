"""The aperture: three separately reported dials, never one "openness" scalar.

This repository has retired a weighted scalar twice already -- `Q_causal` as an
additive edge sum, and the scalar promotion gate -- and both times the defect was
the same: a single number hid which of several conditions had fired.  The
aperture is therefore a triple, and it stays a triple all the way to the report.

    tau    unresolved_lifetime      how long an alternative stays alive
    kappa  branch_width             how many stay alive at once
    beta   crystallisation_barrier  how hard it is to commit to one

Each has declared bounds and every update records its own provenance, so an
ablation can ask which dial did the work.  :func:`AdaptiveAperture.update` is
deliberately the simplest transparent rule that satisfies the four requirements
in the round's specification; a more sophisticated controller would confound the
question this round is asking, which is whether adaptivity helps *at all*.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["ApertureState", "ApertureBounds", "ApertureUpdate", "AdaptiveAperture",
           "FixedAperture", "RandomAperture"]


@dataclass(frozen=True)
class ApertureBounds:
    """Declared domains.  An aperture outside these is a bug, not a policy."""

    tau_min: float = 1.0
    tau_max: float = 16.0
    kappa_min: int = 1
    kappa_max: int = 32
    beta_min: float = 0.0
    beta_max: float = 1.0


@dataclass(frozen=True)
class ApertureUpdate:
    """Provenance for one aperture change: what moved, why, and on what signal."""

    step: int
    field_name: str
    old: float
    new: float
    reason: str
    signal: float


@dataclass
class ApertureState:
    """Three dials with bounds and a change log."""

    unresolved_lifetime: float = 4.0
    branch_width: int = 8
    crystallisation_barrier: float = 0.5
    bounds: ApertureBounds = field(default_factory=ApertureBounds)
    history: list = field(default_factory=list)

    def __post_init__(self) -> None:
        self._clamp_all()

    def _clamp_all(self) -> None:
        b = self.bounds
        self.unresolved_lifetime = min(max(self.unresolved_lifetime, b.tau_min),
                                       b.tau_max)
        self.branch_width = int(min(max(self.branch_width, b.kappa_min), b.kappa_max))
        self.crystallisation_barrier = min(
            max(self.crystallisation_barrier, b.beta_min), b.beta_max)

    def set(self, name: str, value: float, step: int, reason: str,
            signal: float = 0.0) -> None:
        old = getattr(self, name)
        setattr(self, name, value)
        self._clamp_all()
        new = getattr(self, name)
        if new != old:
            self.history.append(ApertureUpdate(step, name, float(old), float(new),
                                               reason, float(signal)))

    def as_tuple(self) -> tuple:
        return (self.unresolved_lifetime, self.branch_width,
                self.crystallisation_barrier)

    def copy(self) -> "ApertureState":
        return ApertureState(self.unresolved_lifetime, self.branch_width,
                             self.crystallisation_barrier, self.bounds, [])

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"tau={self.unresolved_lifetime:.2f} kappa={self.branch_width} "
                f"beta={self.crystallisation_barrier:.2f}")


# --------------------------------------------------------------------------
# Controllers.  Each is an ablation of the next.
# --------------------------------------------------------------------------

class FixedAperture:
    """No adaptation at all.  The control for every adaptivity claim."""

    name = "fixed"

    def __init__(self, state: ApertureState) -> None:
        self.state = state

    def update(self, step, susceptibility, instability, resource_pressure):
        return self.state


class RandomAperture:
    """Matched random walk over the same box, ignoring every signal.

    The point of this control is that an adaptive controller which merely *moves*
    will beat a frozen one on some instances by luck.  To claim adaptation one
    must beat a controller that moves the same amount for no reason.
    """

    name = "random"

    def __init__(self, state: ApertureState, rng, scale: float = 0.25) -> None:
        self.state = state
        self.rng = rng
        self.scale = scale

    def update(self, step, susceptibility, instability, resource_pressure):
        b = self.state.bounds
        self.state.set("unresolved_lifetime",
                       self.state.unresolved_lifetime
                       + self.rng.normal() * self.scale * (b.tau_max - b.tau_min) / 8,
                       step, "random walk", 0.0)
        self.state.set("branch_width",
                       self.state.branch_width + int(self.rng.integers(-2, 3)),
                       step, "random walk", 0.0)
        self.state.set("crystallisation_barrier",
                       self.state.crystallisation_barrier + self.rng.normal() * 0.05,
                       step, "random walk", 0.0)
        return self.state


class AdaptiveAperture:
    """The simplest rule that meets all four stated requirements.

    1. structured susceptibility raises or preserves the aperture;
    2. instability lowers it;
    3. resource pressure lowers kappa and tau first;
    4. the invariant evidence channel is never a source of savings -- this
       controller cannot touch it, by construction, because it has no handle on
       it at all.

    Susceptibility here means *structured* disagreement among candidates: high
    dispersion of candidate scores while the residual gluing defect is still
    falling.  Dispersion alone is not susceptibility -- that is noise -- and the
    ablation against :class:`RandomAperture` is what tests the difference.
    """

    name = "adaptive"

    def __init__(self, state: ApertureState, gain: float = 0.5) -> None:
        self.state = state
        self.gain = gain

    def update(self, step, susceptibility, instability, resource_pressure):
        s = self.state
        if resource_pressure > 0.0:
            s.set("branch_width",
                  int(round(s.branch_width * (1.0 - min(1.0, resource_pressure)))),
                  step, "resource pressure: throttle speculative branching",
                  resource_pressure)
            s.set("unresolved_lifetime",
                  s.unresolved_lifetime * (1.0 - 0.5 * min(1.0, resource_pressure)),
                  step, "resource pressure: shorten unresolved lifetime",
                  resource_pressure)
            return s

        if instability > 0.5:
            s.set("branch_width", int(round(s.branch_width * (1.0 - self.gain
                                                              * (instability - 0.5)))),
                  step, "instability: narrow the branch", instability)
            s.set("crystallisation_barrier",
                  s.crystallisation_barrier - self.gain * 0.2 * (instability - 0.5),
                  step, "instability: crystallise sooner", instability)
            return s

        if susceptibility > 0.5:
            s.set("branch_width",
                  int(round(s.branch_width * (1.0 + self.gain * (susceptibility - 0.5)))),
                  step, "structured susceptibility: widen the branch", susceptibility)
            s.set("unresolved_lifetime",
                  s.unresolved_lifetime * (1.0 + 0.5 * self.gain
                                           * (susceptibility - 0.5)),
                  step, "structured susceptibility: hold alternatives longer",
                  susceptibility)
        return s
