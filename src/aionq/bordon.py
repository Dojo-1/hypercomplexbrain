"""Bordón respiration: breathing with a reservoir, not a scheduled interruption.

The breath model in :mod:`aionq.budget` is periodic and global: accumulate
branch records until the horizon is exhausted, then exhale.  Cognition stops
while the system breathes.  That model is A-tier anyway (its pebbling
interpolation is a project heuristic, not Bennett's theorem), but its real defect
is structural rather than numerical.

The Galician gaita is a better model, and it is a *literal* breathing
instrument.  Its geometry, from the source corpus:

    puntero  (chanter)   visible melody          -- the readable projection
    bordón   (drone)     continuous harmonic     -- resonates, never plays melody
    fol      (bag)       pressure reservoir      -- the remainder [R]
    pallón   (reed)      threshold / wall        -- where pressure becomes sound

Three things follow that the periodic model cannot express.

**1. The fol decouples intake from expenditure.**  A piper inhales *while the
melody continues*, because the bag buffers pressure.  Respiration and
computation are not phase-locked.  The periodic model forces a global stop; the
reservoir model only fails when the bag actually runs dry.

**2. The bordón is never interrupted.**  The drone is a constant-draw channel
that carries no melody and is never silenced.  Architecturally this is the
identity/invariant carrier: a channel that must be exempt from the breath cycle.
The periodic model has no such exemption, so it would happily exhale the very
structure whose continuity defines the organ.

**3. Channels breathe at different rates.**  puntero is fast and interruptible,
bordón is slow and continuous.  Respiration is polyrhythmic per channel, not one
global period.

The model yields two quantities the periodic one could not:

    sustain time     how long the melody survives a deficit, = fol / (draw - refill)
    drone ceiling    the largest continuous draw that survives indefinitely,
                     which is bounded by the refill rate ALONE, because the
                     reservoir cannot cover an uninterrupted channel forever

The second is the useful one.  It says an architecture may spend its buffer on
melody but must fund its invariant carrier out of steady income.

Status: this is a *model*, tagged S/H in :mod:`aionq.governance`.  The
quantities below are exact consequences of the model, not measurements of any
physical brain.  Credit: Bordón / Bordón Siphony architecture, from the source
corpus; see docs/SOURCES_DIGEST.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = ["Pipe", "Fol", "BordonBreath", "RespirationReport", "PipeKind"]


class PipeKind:
    PUNTERO = "puntero"    # melody: interruptible, may be silenced to save pressure
    BORDON = "bordon"      # drone: continuous, never interrupted


@dataclass(frozen=True)
class Pipe:
    """One channel drawing on the reservoir."""

    name: str
    kind: str
    draw: float                 # pressure units consumed per tick

    def __post_init__(self) -> None:
        if self.kind not in (PipeKind.PUNTERO, PipeKind.BORDON):
            raise ValueError(f"unknown pipe kind {self.kind!r}")
        if self.draw < 0:
            raise ValueError("draw must be non-negative")

    @property
    def interruptible(self) -> bool:
        return self.kind == PipeKind.PUNTERO


@dataclass
class Fol:
    """The bag: a pressure reservoir that decouples intake from expenditure."""

    capacity: float
    refill_rate: float          # steady intake per tick (the piper's actual breath)
    level: float = None         # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.level is None:
            self.level = self.capacity


@dataclass
class RespirationReport:
    """What the reservoir model says about an organ's respiration."""

    drone_draw: float
    melody_draw: float
    refill_rate: float
    capacity: float
    drone_ceiling: float
    sustain_ticks: float
    drone_survives: bool
    melody_survives: bool
    collapse_tick: float | None = None
    notes: list = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - display only
        sustain = ("indefinite" if math.isinf(self.sustain_ticks)
                   else f"{self.sustain_ticks:.1f} ticks")
        lines = [
            f"drone draw     : {self.drone_draw:.3f}   (continuous, never interrupted)",
            f"melody draw    : {self.melody_draw:.3f}   (interruptible)",
            f"refill rate    : {self.refill_rate:.3f}",
            f"fol capacity   : {self.capacity:.3f}",
            f"drone ceiling  : {self.drone_ceiling:.3f}   (funded by refill alone)",
            f"melody sustain : {sustain}",
            f"drone survives : {self.drone_survives}",
            f"melody survives: {self.melody_survives}",
        ]
        if self.collapse_tick is not None:
            lines.append(f"collapse at    : tick {self.collapse_tick:.1f}")
        lines.extend(f"note: {n}" for n in self.notes)
        return "\n".join(lines)


@dataclass
class BordonBreath:
    """Respiration as reservoir dynamics across pipes of different kinds."""

    fol: Fol
    pipes: tuple

    @property
    def drone_draw(self) -> float:
        return sum(p.draw for p in self.pipes if not p.interruptible)

    @property
    def melody_draw(self) -> float:
        return sum(p.draw for p in self.pipes if p.interruptible)

    @property
    def drone_ceiling(self) -> float:
        """Largest continuous draw fundable indefinitely.

        A reservoir of any finite size cannot fund an uninterrupted channel
        forever, so the ceiling is the refill rate alone.  This is the model's
        one sharp architectural consequence: an invariant carrier must be paid
        for out of steady income, never out of buffer.
        """
        return self.fol.refill_rate

    def analyse(self, horizon: int = 1000) -> RespirationReport:
        """Simulate and report. Melody is silenced first when pressure runs low."""
        notes: list[str] = []
        drone, melody = self.drone_draw, self.melody_draw
        drone_survives = drone <= self.drone_ceiling + 1e-12

        deficit = drone + melody - self.fol.refill_rate
        if deficit <= 1e-12:
            sustain = math.inf
        else:
            sustain = self.fol.capacity / deficit

        level = self.fol.level
        collapse = None
        melody_on = True
        for tick in range(horizon):
            draw = drone + (melody if melody_on else 0.0)
            level = min(self.fol.capacity, level + self.fol.refill_rate - draw)
            if level <= 0:
                if melody_on and drone <= self.fol.refill_rate + 1e-12:
                    # Silence the melody and keep the drone: this is what a piper
                    # does, and what an architecture should do with its invariant.
                    melody_on = False
                    level = 0.0
                    notes.append(f"melody silenced at tick {tick} to protect the drone")
                    continue
                collapse = float(tick)
                break

        if not drone_survives:
            notes.append(
                f"drone draw {drone:.3f} exceeds the ceiling {self.drone_ceiling:.3f}: "
                "an uninterrupted channel cannot be funded from the reservoir, so "
                "collapse is only a matter of time regardless of capacity")

        if math.isinf(sustain) and melody_on:
            notes.append("total draw is within refill: no breath interruption is "
                         "required at all, which the periodic model cannot express")

        return RespirationReport(
            drone_draw=drone,
            melody_draw=melody,
            refill_rate=self.fol.refill_rate,
            capacity=self.fol.capacity,
            drone_ceiling=self.drone_ceiling,
            sustain_ticks=sustain,
            drone_survives=drone_survives,
            melody_survives=melody_on and collapse is None,
            collapse_tick=collapse,
            notes=notes,
        )
