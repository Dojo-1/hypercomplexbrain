"""Measurements that carry their own uncertainty.

Several numbers in this repository were reported as point estimates from thin
samples: a control slope from 7 means of 6 seeds each, a Cayley-Dickson
associator norm from one seed, an ACAF sweep at 2 samples per configuration.
None of them carried a dispersion, so none of them could be checked for
significance, and a reader could not tell a real effect from sampling noise.

The Atlas's own promotion rule for the M tier is explicit:

    M - MEASURED: numerical result with code, data, seeds, controls, and an
        identified instrument.  *Report sample size, null, effect, and scope.*

:mod:`aionq.governance` stated that rule and did not enforce it.  This module
supplies the machinery, and the governance module now refuses an M-tagged claim
that lacks a sample size and an interval.

Everything here is non-parametric.  The quantities being measured -- ranks,
integer depths, associator norms -- are not normally distributed, and several
are bounded or discrete, so bootstrap percentile intervals are used rather than
mean +/- 1.96 sigma.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

__all__ = ["Measurement", "bootstrap_ci", "summarize", "compare_groups",
           "slope_with_ci", "EffectSize"]


def bootstrap_ci(samples, statistic=np.mean, confidence: float = 0.95,
                 resamples: int = 10000, seed: int = 0) -> tuple:
    """Percentile bootstrap interval for `statistic` of `samples`.

    Non-parametric on purpose: rank and depth statistics are discrete and
    bounded, so a normal-theory interval would misreport the tails.
    """
    data = np.asarray(samples, dtype=float)
    if data.size == 0:
        return (float("nan"), float("nan"))
    if data.size == 1:
        v = float(statistic(data))
        return (v, v)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, data.size, size=(resamples, data.size))
    stats = np.apply_along_axis(statistic, 1, data[idx])
    lo = (1.0 - confidence) / 2.0
    return (float(np.quantile(stats, lo)), float(np.quantile(stats, 1.0 - lo)))


@dataclass
class Measurement:
    """A number that knows how well it is known."""

    name: str
    value: float
    n: int
    ci: tuple
    std: float = 0.0
    quantiles: dict = field(default_factory=dict)
    unit: str = ""
    note: str = ""

    @property
    def half_width(self) -> float:
        return (self.ci[1] - self.ci[0]) / 2.0

    @property
    def relative_precision(self) -> float:
        """Half-width as a fraction of the value; inf when the value is 0."""
        return abs(self.half_width / self.value) if self.value else math.inf

    def excludes(self, null: float) -> bool:
        """Does the interval exclude a null value?  This is the significance test."""
        return not (self.ci[0] <= null <= self.ci[1])

    def agrees_with(self, other: float, tol: float = 0.0) -> bool:
        """Is a reported external value inside this interval (optionally widened)?"""
        return self.ci[0] - tol <= other <= self.ci[1] + tol

    def __str__(self) -> str:  # pragma: no cover - display only
        u = f" {self.unit}" if self.unit else ""
        s = (f"{self.name}: {self.value:.4f}{u} "
             f"[{self.ci[0]:.4f}, {self.ci[1]:.4f}] 95% CI, n={self.n:,}")
        if self.std:
            s += f", sd={self.std:.4f}"
        if self.quantiles:
            qs = " ".join(f"p{int(k * 100)}={v:.3f}" for k, v in sorted(self.quantiles.items()))
            s += f"\n    {qs}"
        if self.note:
            s += f"\n    note: {self.note}"
        return s


def summarize(name: str, samples, unit: str = "", confidence: float = 0.95,
              seed: int = 0, note: str = "") -> Measurement:
    """Full distributional summary, not just a mean."""
    data = np.asarray(samples, dtype=float)
    qs = {q: float(np.quantile(data, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)} \
        if data.size > 1 else {}
    return Measurement(
        name=name,
        value=float(data.mean()),
        n=int(data.size),
        ci=bootstrap_ci(data, np.mean, confidence, seed=seed),
        std=float(data.std(ddof=1)) if data.size > 1 else 0.0,
        quantiles=qs,
        unit=unit,
        note=note,
    )


@dataclass
class EffectSize:
    """A difference between two groups, with an interval and a standardised size."""

    name: str
    difference: float
    ci: tuple
    cohens_d: float
    n_a: int
    n_b: int

    @property
    def significant(self) -> bool:
        """Interval excludes zero."""
        return not (self.ci[0] <= 0.0 <= self.ci[1])

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"{self.name}: delta = {self.difference:+.4f} "
               f"[{self.ci[0]:+.4f}, {self.ci[1]:+.4f}], d = {self.cohens_d:+.3f}, "
               f"n = {self.n_a}/{self.n_b}, "
               f"{'significant' if self.significant else 'NOT significant'}")


def compare_groups(name: str, a, b, confidence: float = 0.95,
                   resamples: int = 10000, seed: int = 0) -> EffectSize:
    """Bootstrap the difference of means, with Cohen's d."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    diffs = np.empty(resamples)
    for i in range(resamples):
        ra = a[rng.integers(0, a.size, a.size)]
        rb = b[rng.integers(0, b.size, b.size)]
        diffs[i] = ra.mean() - rb.mean()
    lo = (1.0 - confidence) / 2.0
    pooled = math.sqrt(((a.size - 1) * a.var(ddof=1) + (b.size - 1) * b.var(ddof=1))
                       / max(1, a.size + b.size - 2)) if a.size > 1 and b.size > 1 else 0.0
    return EffectSize(
        name=name,
        difference=float(a.mean() - b.mean()),
        ci=(float(np.quantile(diffs, lo)), float(np.quantile(diffs, 1 - lo))),
        cohens_d=float((a.mean() - b.mean()) / pooled) if pooled else math.inf,
        n_a=int(a.size), n_b=int(b.size),
    )


def slope_with_ci(x, y_groups, confidence: float = 0.95, resamples: int = 5000,
                  seed: int = 0) -> Measurement:
    """Bootstrap the slope of a trend, resampling *within* each x group.

    The earlier control analysis fitted a line through 7 group means and reported
    the slope as though it were exact.  Resampling within groups propagates the
    per-group sampling error into the slope, which is what makes "the control
    does not track n" a checkable statement rather than an impression.
    """
    x = np.asarray(x, dtype=float)
    groups = [np.asarray(g, dtype=float) for g in y_groups]
    rng = np.random.default_rng(seed)
    slopes = np.empty(resamples)
    for i in range(resamples):
        means = [g[rng.integers(0, g.size, g.size)].mean() for g in groups]
        slopes[i] = np.polyfit(x, means, 1)[0]
    lo = (1.0 - confidence) / 2.0
    observed = float(np.polyfit(x, [g.mean() for g in groups], 1)[0])
    return Measurement(
        name="slope",
        value=observed,
        n=int(sum(g.size for g in groups)),
        ci=(float(np.quantile(slopes, lo)), float(np.quantile(slopes, 1 - lo))),
        std=float(slopes.std(ddof=1)),
        unit="per unit x",
    )
