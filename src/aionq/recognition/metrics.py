"""Observables, each reported raw before any normalisation or clipping.

Six components make up the primary result and none of them is combined with
another:

    delta_auroc              discrimination of defective overlaps
    delta_brier              calibration, reported as a full distribution
    delta_diversity          candidate-population spread
    neg_delta_loop_defect    round-trip stability (lower defect is better)
    neg_delta_compute        wall clock and candidate evaluations
    neg_delta_instability    spread of AUROC under representation attacks

AUROC is imported from :mod:`aionq.sheaf` rather than re-implemented, so the S3
result and the S4 result are measured by exactly the same function -- including
its tie-averaging, without which a constant-score condition reads as a perfect 0
or 1 instead of the chance 0.5 it deserves.
"""

from __future__ import annotations

import resource
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field

import numpy as np

from ..sheaf import auroc
from ..statistics import bootstrap_ci, summarize

__all__ = ["auroc", "brier_score", "candidate_diversity", "ResourceLedger",
           "measure_resources", "ConditionResult", "effect_region_observed",
           "normalise_scores"]


def normalise_scores(scores) -> np.ndarray:
    """Map raw per-overlap scores into [0, 1] for calibration only.

    The AUROC is computed on the RAW scores; this projection exists solely so a
    Brier score is definable, and the raw values are retained alongside it.  A
    rank-preserving map cannot change AUROC, so calibration and discrimination
    stay separable -- which is the reason both are gated independently.
    """
    s = np.asarray(scores, dtype=float)
    lo, hi = float(s.min()), float(s.max())
    if hi - lo < 1e-15:
        return np.full(s.size, 0.5)
    return (s - lo) / (hi - lo)


def brier_score(scores, labels) -> float:
    """Mean squared error of the normalised score against the 0/1 label."""
    p = normalise_scores(scores)
    y = np.asarray(labels, dtype=float)
    return float(np.mean((p - y) ** 2))


def candidate_diversity(candidates) -> float:
    """Mean pairwise Hamming distance among candidate supports, normalised.

    Zero when the population has collapsed to one hypothesis; near 0.5 when it is
    uninformative noise.  Reported, never optimised: high diversity is not a good
    in itself and this round makes no claim that it is.
    """
    if len(candidates) < 2:
        return 0.0
    states = np.array([np.asarray(c.state, dtype=np.uint8) for c in candidates])
    n, m = states.shape
    total, pairs = 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            total += float(np.count_nonzero(states[i] != states[j]))
            pairs += 1
    return total / (pairs * m) if pairs else 0.0


# --------------------------------------------------------------------------
# Resource accounting
# --------------------------------------------------------------------------

@dataclass
class ResourceLedger:
    """Wall clock, peak memory and evaluation count, charged per condition."""

    wall_seconds: float = 0.0
    peak_kib: float = 0.0
    candidate_evaluations: int = 0
    parameter_count: int = 0
    max_rss_kib: float = 0.0

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"{self.wall_seconds:.3f}s  peak {self.peak_kib:.0f} KiB  "
                f"{self.candidate_evaluations} evals  {self.parameter_count} params")


@contextmanager
def measure_resources(ledger: ResourceLedger):
    """Wall clock via perf_counter, peak allocation via tracemalloc.

    psutil is absent in this environment, so peak *process* RSS is read from
    ``resource.getrusage`` as a coarse upper bound and the fine-grained figure
    comes from tracemalloc.  Both are reported; neither is presented as the other.
    """
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        yield ledger
    finally:
        ledger.wall_seconds += time.perf_counter() - t0
        _cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        ledger.peak_kib = max(ledger.peak_kib, peak / 1024.0)
        ledger.max_rss_kib = max(ledger.max_rss_kib,
                                 float(resource.getrusage(resource.RUSAGE_SELF)
                                       .ru_maxrss))


# --------------------------------------------------------------------------
# Per-condition results
# --------------------------------------------------------------------------

@dataclass
class ConditionResult:
    """Everything one experimental condition produced, per seed, unaggregated."""

    condition: str
    description: str
    auroc: list = field(default_factory=list)
    brier: list = field(default_factory=list)
    diversity: list = field(default_factory=list)
    loop_defect: list = field(default_factory=list)
    order_defect: list = field(default_factory=list)
    attack_auroc: dict = field(default_factory=dict)
    resources: ResourceLedger = field(default_factory=ResourceLedger)
    seeds: list = field(default_factory=list)

    def summary(self, seed: int = 0) -> dict:
        out = {"condition": self.condition, "n": len(self.auroc)}
        for name, vals in (("auroc", self.auroc), ("brier", self.brier),
                           ("diversity", self.diversity),
                           ("loop_defect", self.loop_defect),
                           ("order_defect", self.order_defect)):
            if vals:
                m = summarize(name, vals, seed=seed)
                out[name] = {"mean": m.value, "ci": list(m.ci), "sd": m.std,
                             "quantiles": m.quantiles,
                             "min": float(np.min(vals)), "max": float(np.max(vals))}
        out["instability"] = self.instability
        out["resources"] = {"wall_seconds": self.resources.wall_seconds,
                            "peak_kib": self.resources.peak_kib,
                            "max_rss_kib": self.resources.max_rss_kib,
                            "candidate_evaluations":
                                self.resources.candidate_evaluations,
                            "parameter_count": self.resources.parameter_count}
        return out

    @property
    def instability(self) -> float:
        """Largest |AUROC change| across all representation attacks.

        Worst case, not mean: an invariant that holds on average and fails under
        one admissible relabeling is not an invariant.
        """
        if not self.attack_auroc or not self.auroc:
            return 0.0
        base = float(np.mean(self.auroc))
        return max(abs(float(np.mean(v)) - base) for v in self.attack_auroc.values())


def effect_region_observed(target: ConditionResult, baselines: dict,
                           seed: int = 0) -> dict:
    """The six-component DeltaY, against the preregistered comparators.

    ``delta_auroc_vs_c0`` is measured against the deterministic S3 localiser and
    ``delta_auroc_vs_best_control`` against the best of C1/C2/C3, exactly as
    preregistered -- so a win over the weak baseline cannot stand in for a win
    over the strong one.
    """
    c0 = baselines["C0"]
    controls = [baselines[k] for k in ("C1", "C2", "C3") if k in baselines]
    best_control = max(controls, key=lambda r: float(np.mean(r.auroc))) \
        if controls else c0

    t_auroc = float(np.mean(target.auroc))
    d_c0 = t_auroc - float(np.mean(c0.auroc))
    d_ctrl = t_auroc - float(np.mean(best_control.auroc))
    paired = None
    if len(target.auroc) == len(c0.auroc):
        diffs = np.asarray(target.auroc) - np.asarray(c0.auroc)
        paired = {"mean": float(diffs.mean()),
                  "ci": list(bootstrap_ci(diffs, seed=seed)),
                  "wins": int((diffs > 0).sum()), "n": int(diffs.size)}

    return {
        "delta_auroc_vs_c0": d_c0,
        "delta_auroc_vs_best_control": d_ctrl,
        "best_control": best_control.condition,
        "delta_brier_vs_c0": float(np.mean(target.brier)) - float(np.mean(c0.brier)),
        "delta_diversity_vs_c0": (float(np.mean(target.diversity))
                                  - float(np.mean(c0.diversity))),
        "mean_loop_defect": float(np.mean(target.loop_defect))
        if target.loop_defect else 0.0,
        "p99_loop_defect": float(np.quantile(target.loop_defect, 0.99))
        if target.loop_defect else 0.0,
        "instability": target.instability,
        "wall_ratio_vs_best_baseline": (
            target.resources.wall_seconds
            / max(1e-9, min(b.resources.wall_seconds for b in baselines.values()))),
        "memory_ratio_vs_best_baseline": (
            target.resources.peak_kib
            / max(1e-9, min(b.resources.peak_kib for b in baselines.values()))),
        "paired_vs_c0": paired,
    }
