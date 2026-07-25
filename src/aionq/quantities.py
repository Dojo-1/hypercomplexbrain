"""Typed quantities.

Split out of :mod:`aionq.stack` so that :mod:`aionq.atlas` can use them without
a circular import.  That circularity is why the types were originally a sidecar:
they existed in a module the Atlas could not import, so the Atlas kept bare
floats and the typing never governed anything.

Every coordinate carries its unit, its uncertainty and its base-relativity, and
comparison across kinds, units or base points raises rather than silently
returning a number.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["IncommensurableError", "Quantity", "Fraction", "Bits", "Monotone",
           "Strength", "Effect", "coerce"]


class IncommensurableError(TypeError):
    """Raised when two quantities of different kind, unit or base are compared."""


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
            raise IncommensurableError(f"cannot compare {self.unit} with {other.unit}")
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

    # Numeric interop so that existing formatting and arithmetic keep working
    # without letting an untyped comparison through.
    def __float__(self) -> float:
        return float(self.value)

    def __format__(self, spec: str) -> str:
        return format(self.value, spec) if spec else str(self)

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


@dataclass(frozen=True)
class Effect(Quantity):
    """A task-level effect size against a matched control.  May be negative."""

    unit: str = "effect"


def coerce(value, kind, base: str | None = None):
    """Wrap a bare number in `kind`, or check an already-typed value.

    Accepting raw floats keeps call sites readable; storing them typed is what
    makes the comparison rules enforceable.
    """
    if isinstance(value, Quantity):
        if not isinstance(value, kind):
            raise IncommensurableError(
                f"expected {kind.__name__}, got {type(value).__name__}")
        if kind is Monotone and base is not None and value.base != base:
            raise IncommensurableError(
                f"monotone declares base '{value.base}' but the section is over '{base}'")
        return value
    return kind(float(value), base=base) if kind is Monotone else kind(float(value))
