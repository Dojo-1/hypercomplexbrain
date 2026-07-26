"""The Transcendence Sentinel: a sparse expanding-gap novelty diagnostic.

Specified in the Sigma-infinity thesis (section 13) and rated there as an
architectural transport from Luca, Ouaknine & Worrell, "Transcendence of
Hecke-Mahler series" (Bull. LMS 2025) -- explicitly *not* a transferred theorem.

The source condition
--------------------
For a sequence u that almost satisfies a linear recurrence, apply a recurrence
filter at a growing scale r_n:

    w_{n,m} = sum_{i=0..sigma} b_i u_{m + i r_n},   Delta_n = { m : w_{n,m} != 0 }

The arithmetic argument needs Delta_n to stay infinite while its *gaps expand*,
with the nonzero residual magnitudes varying polynomially.  Combined with a
p-adic subspace theorem this supports transcendence in the source domain.

What is imported, and what is not
---------------------------------
Imported: the shape of the diagnostic.  Structure that is genuinely compressible
gives residuals that mostly vanish.  Dense noise gives residuals that are dense
and unstable.  The interesting middle -- sparse residuals whose gaps *expand*
coherently, with controlled magnitude variation -- is what the sentinel flags.

Not imported: any transcendence claim, any irreducibility claim, any statement
about cognition.  A high score means "protect this from premature compression
and route it to a witness", nothing more.

Measured outcome (Round S1)
---------------------------
The sentinel was killed against the thesis's own kill condition: a gzip MDL
proxy on the identical residual reaches AUROC 1.000 where the sentinel reaches
0.865.  A second finding is recorded here because it bears on the transport
itself: what weakly separates the expanding-gap class from the fixed-rate class
is the *magnitude variation* component, **not** the gap-expansion component.
Gap expansion -- the part actually imported from Hecke-Mahler -- does not order
individual streams reliably, because the recurrence filter smears each isolated
anomaly across several residual positions.  So even the surviving signal is not
coming from the imported structure.

The thesis pre-registers the kill condition (section 16, experiment 3):

    Kill: conventional change-point or compression methods match the result
    under equal tuning and cost.

:mod:`experiments.run_sentinel` runs exactly that comparison.  The sentinel is
scored against matched baselines and is retired for this task if they match it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

__all__ = ["SentinelScore", "filtered_residual", "gap_expansion_score",
           "variation_regularity", "sentinel_score", "fit_recurrence"]


def fit_recurrence(u: np.ndarray, order: int = 2, scale: int = 1) -> np.ndarray:
    """Least-squares linear-recurrence coefficients at a given stride.

    Returns b with b[0] = 1 normalised, so that w = sum_i b_i u_{m + i*scale}
    is the residual after removing the best recurrence of this order and stride.
    """
    u = np.asarray(u, dtype=float)
    span = order * scale
    if u.size <= span + 1:
        return np.array([1.0] + [0.0] * order)
    rows = np.stack([u[i * scale: u.size - span + i * scale] for i in range(order)], axis=1)
    target = u[span:]
    coef, *_ = np.linalg.lstsq(rows, target, rcond=None)
    return np.concatenate([-coef, [1.0]])


def filtered_residual(u: np.ndarray, b: np.ndarray, scale: int) -> np.ndarray:
    """w_{n,m} = sum_i b_i u_{m + i*scale}."""
    u = np.asarray(u, dtype=float)
    order = b.size - 1
    span = order * scale
    if u.size <= span:
        return np.zeros(0)
    out = np.zeros(u.size - span)
    for i, coeff in enumerate(b):
        out += coeff * u[i * scale: u.size - span + i * scale]
    return out


def _support(w: np.ndarray, tol: float) -> np.ndarray:
    return np.flatnonzero(np.abs(w) > tol)


def gap_expansion_score(support: np.ndarray) -> float:
    """Do the gaps between nonzero residuals grow?

    Regresses log(gap) on log(index).  Positive slope means expanding gaps --
    the source condition.  Constant-rate anomalies give slope ~ 0; dense noise
    gives a near-empty gap structure.
    """
    if support.size < 4:
        return 0.0
    gaps = np.diff(support).astype(float)
    gaps = np.clip(gaps, 1.0, None)
    idx = np.arange(1, gaps.size + 1, dtype=float)
    slope = np.polyfit(np.log(idx), np.log(gaps), 1)[0]
    return float(slope)


def variation_regularity(w: np.ndarray, support: np.ndarray) -> float:
    """Is the magnitude variation controlled (polynomial-ish) rather than wild?

    Returns a value in [0, 1]: 1 when the log-magnitudes are well explained by a
    log-linear trend, 0 when they are erratic.
    """
    if support.size < 4:
        return 0.0
    mags = np.abs(w[support])
    mags = mags[mags > 0]
    if mags.size < 4:
        return 0.0
    y = np.log(mags)
    x = np.log(np.arange(1, y.size + 1, dtype=float))
    fit = np.polyfit(x, y, 1)
    resid = y - np.polyval(fit, x)
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return 1.0
    return float(max(0.0, 1.0 - np.sum(resid ** 2) / ss_tot))


@dataclass
class SentinelScore:
    """Three separately reported quantities, never collapsed before reporting."""

    sparsity: float             # fraction of residuals that vanish
    gap_expansion: float        # slope of log gap vs log index
    variation: float            # regularity of magnitudes in [0, 1]
    support_size: int
    scale: int
    score: float = 0.0
    notes: list = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"sparsity {self.sparsity:.3f}  gap-slope {self.gap_expansion:+.3f}  "
                f"variation {self.variation:.3f}  |support| {self.support_size}  "
                f"score {self.score:.3f}")


def sentinel_score(u, order: int = 2, scale: int = 4, tol: float | None = None
                   ) -> SentinelScore:
    """Score a stream for sparse expanding-gap structure.

    The three components are reported separately as well as combined, because a
    single number would hide which condition fired -- the same flattening this
    repository has retired three times.
    """
    u = np.asarray(u, dtype=float)
    b = fit_recurrence(u, order=order, scale=scale)
    w = filtered_residual(u, b, scale)
    if w.size == 0:
        return SentinelScore(0.0, 0.0, 0.0, 0, scale, 0.0,
                             ["stream too short for this order and scale"])

    if tol is None:
        tol = max(1e-9, 1e-3 * float(np.max(np.abs(w))))
    sup = _support(w, tol)

    sparsity = 1.0 - sup.size / w.size
    gap = gap_expansion_score(sup)
    var = variation_regularity(w, sup)

    notes = []
    if sparsity < 0.2:
        notes.append("residual is dense: consistent with noise, not sparse novelty")
    if sup.size == 0:
        notes.append("residual vanishes entirely: exactly recurrent, nothing to protect")

    # Combined only after the parts are reported.  Sparse AND expanding AND regular.
    score = float(max(0.0, sparsity) * max(0.0, gap) * max(0.0, var))
    return SentinelScore(sparsity, gap, var, int(sup.size), scale, score, notes)
