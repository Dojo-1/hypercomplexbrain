"""QSigma-R3: typed quantities and transport holonomy.

Two defects survived the R3 round.

**Untyped coordinates.** The atlas stored fractions, bits, resource monotones,
simulation intervals and audit strengths as bare floats and compared them
coordinatewise.  The units differ, the uncertainties differ, and some are
base-relative.  Comparing 0.9 bits of process memory against a 0.9 audit
strength is meaningless, and nothing in the code prevented it.  :class:`Quantity`
and its subclasses make the comparison illegal rather than merely unwise.

**Transport holonomy was never measured.** R3 added ``transport_to`` but never
asked the obvious question: if a section is carried around a *loop* of free
theories and back to its starting chart, does it return?

It does not, and the reason is sharp:

    Section-only transport around a loop is lossy.  State-anchored transport
    around the same loop is exact.

A resource monotone is not data the section carries; it is data the section
*computes from the underlying state*.  Discard the state and keep only the
number, and the number cannot survive a change of base -- there is nothing left
to recompute it from.  Retain the state and every base change is recoverable.

This is the architecture's own self-reflection result, and it is measurable.  An
organ whose self-assessment is path-independent must retain the state its
assessments were computed from.  An organ that keeps only its own summary
statistics has a path-dependent self-image: what it believes about itself
depends on the route it took through its own assumptions.  That is a Goedelian
flavour with a number attached, not a metaphor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .atlas import (ALL_FREE, CLASSICAL, SEPARABLE, STABILIZER, FreeTheory,
                    resource_over)

__all__ = [
    "Quantity", "Fraction", "Bits", "Monotone", "Strength", "IncommensurableError",
    "LoopReport", "transport_loop", "state_anchored_loop",
    "holonomy_defect",
]


class IncommensurableError(TypeError):
    """Raised when two quantities of different kind or unit are compared."""


@dataclass(frozen=True)
class Quantity:
    """A number that knows its unit, its uncertainty and its base-relativity."""

    value: float
    unit: str = "dimensionless"
    uncertainty: float = 0.0
    base: str | None = None          # set iff the quantity is base-relative

    @property
    def base_relative(self) -> bool:
        return self.base is not None

    def _check(self, other: "Quantity") -> None:
        if type(self) is not type(other):
            raise IncommensurableError(
                f"cannot compare {type(self).__name__} with {type(other).__name__}")
        if self.unit != other.unit:
            raise IncommensurableError(
                f"cannot compare {self.unit} with {other.unit}")
        if self.base != other.base:
            raise IncommensurableError(
                f"cannot compare a quantity over '{self.base}' with one over "
                f"'{other.base}': base-relative quantities need transport first")

    def __ge__(self, other: "Quantity") -> bool:
        self._check(other)
        return self.value >= other.value - 1e-12

    def __gt__(self, other: "Quantity") -> bool:
        self._check(other)
        return self.value > other.value + 1e-12

    def __str__(self) -> str:  # pragma: no cover - display only
        s = f"{self.value:.4f} {self.unit}"
        if self.uncertainty:
            s += f" +/- {self.uncertainty:.4f}"
        if self.base:
            s += f" [over {self.base}]"
        return s


@dataclass(frozen=True)
class Fraction(Quantity):
    """A dimensionless fraction in [0, 1]."""

    unit: str = "fraction"

    def __post_init__(self) -> None:
        if not (-1e-9 <= self.value <= 1 + 1e-9):
            raise ValueError(f"fraction out of range: {self.value}")


@dataclass(frozen=True)
class Bits(Quantity):
    """An information quantity in bits."""

    unit: str = "bits"


@dataclass(frozen=True)
class Monotone(Quantity):
    """A resource monotone.  Meaningless without a base point."""

    unit: str = "monotone"

    def __post_init__(self) -> None:
        if self.base is None:
            raise ValueError("a resource monotone must declare its free theory")


@dataclass(frozen=True)
class Strength(Quantity):
    """External certification strength: not an information measure."""

    unit: str = "audit-strength"


# --------------------------------------------------------------------------
# Transport holonomy around a loop of free theories
# --------------------------------------------------------------------------

DEFAULT_LOOP = (STABILIZER, ALL_FREE, SEPARABLE, CLASSICAL, STABILIZER)


@dataclass
class LoopReport:
    """What survived a round trip through a loop of free theories."""

    path: tuple
    anchored: bool
    start_value: float
    end_value: float
    defect: float
    surviving_coordinates: tuple = ()
    lost_coordinates: tuple = ()
    notes: list = field(default_factory=list)

    @property
    def trivial(self) -> bool:
        """Did the section return to where it started?"""
        return math.isfinite(self.defect) and abs(self.defect) < 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        route = " -> ".join(self.path)
        lines = [
            f"loop        : {route}",
            f"mode        : {'state-anchored' if self.anchored else 'section-only'}",
            f"start value : {self.start_value:.6f}",
            f"end value   : {self.end_value if math.isfinite(self.end_value) else float('nan'):.6f}",
            f"defect      : {self.defect if math.isfinite(self.defect) else float('inf')}",
            f"holonomy    : {'trivial (returns)' if self.trivial else 'NON-TRIVIAL (lossy)'}",
        ]
        if self.surviving_coordinates:
            lines.append(f"survived    : {', '.join(self.surviving_coordinates)}")
        if self.lost_coordinates:
            lines.append(f"lost        : {', '.join(self.lost_coordinates)}")
        lines.extend(f"note: {n}" for n in self.notes)
        return "\n".join(lines)


def transport_loop(section, path=DEFAULT_LOOP) -> LoopReport:
    """Carry a section around a loop of free theories, keeping only the section.

    Each base change nulls the base-relative coordinates, because a monotone
    cannot be re-derived from a number that no longer refers to a state.  The
    loop therefore does not close: the section returns to its starting chart
    stripped of exactly the coordinates that made it a section rather than a
    tuple.
    """
    start = float(section.q_resource)
    current = section
    lost: set = set()
    survived: set | None = None

    for theory in path[1:]:
        moved = current.transport_to(theory)
        lost.update(moved.lost)
        step = set(moved.preserved)
        survived = step if survived is None else survived & step
        current = moved.section
    survived = survived or set()

    end = float(current.q_resource)
    defect = math.inf if math.isnan(end) else abs(end - start)

    return LoopReport(
        path=tuple(t.name for t in path),
        anchored=False,
        start_value=start,
        end_value=end,
        defect=defect,
        surviving_coordinates=tuple(sorted(survived)),
        lost_coordinates=tuple(sorted(lost)),
        notes=["a monotone is computed from a state, not carried by a section; "
               "discard the state and the round trip cannot restore it"],
    )


def state_anchored_loop(state: np.ndarray, path=DEFAULT_LOOP) -> LoopReport:
    """Carry the *state* around the same loop, recomputing the monotone each time.

    Every base change is now recoverable, because the quantity is re-derived
    rather than transported.  The loop closes exactly.
    """
    values = [resource_over(state, theory) for theory in path]
    start, end = float(values[0]), float(values[-1])
    defect = abs(end - start)

    return LoopReport(
        path=tuple(t.name for t in path),
        anchored=True,
        start_value=start,
        end_value=end,
        defect=defect,
        surviving_coordinates=("all: recomputed at each chart",),
        lost_coordinates=(),
        notes=[f"profile around the loop: "
               f"{', '.join(f'{t.name}={v:.4f}' for t, v in zip(path, values))}"],
    )


def holonomy_defect(state: np.ndarray, section, path=DEFAULT_LOOP) -> dict:
    """Compare section-only and state-anchored transport around the same loop.

    Returns the pair of defects.  The gap between them is the price of keeping
    summary statistics instead of the thing they summarise.
    """
    sec = transport_loop(section, path)
    anc = state_anchored_loop(state, path)
    return {
        "section_only_defect": sec.defect,
        "state_anchored_defect": anc.defect,
        "section_only_trivial": sec.trivial,
        "state_anchored_trivial": anc.trivial,
        "lost_under_section_only": sec.lost_coordinates,
    }
