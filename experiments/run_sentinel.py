"""Round S1: the Sigma-infinity Transcendence Sentinel, against its own kill condition.

The Sigma-infinity thesis (section 16, experiment 3) pre-registers this test and
states the kill condition itself.  It is reproduced verbatim:

    Generate streams with exact recurrence, dense noise, sparse random anomalies,
    and structured expanding-gap anomalies.

    Prediction: the sentinel separates structured sparse defects from both dense
    noise and fixed-rate anomalies.

    Kill condition: conventional change-point or compression methods match the
    result under equal tuning and cost.

The thesis rates itself H and says it "becomes M only after implementation and
controlled experiments".  This is that experiment.  The sentinel is retired for
this task if either matched baseline matches it.

Baselines (the two the thesis names)
  CHANGE-POINT   CUSUM-style maximum standardised cumulative deviation.
  COMPRESSION    an MDL proxy: gzip ratio of the quantised residual stream.
Both are given the same stream, the same preprocessing and comparable tuning.

Primary metric: AUROC separating the structured expanding-gap class from the
three other classes.  Reported with a bootstrap interval, per this repository's
M-tier rule.

Run with:  PYTHONPATH=src python3 experiments/run_sentinel.py
"""

from __future__ import annotations

import gzip
import sys

import numpy as np

sys.path.insert(0, "src")

from aionq.sentinel import fit_recurrence, filtered_residual, sentinel_score
from aionq.statistics import bootstrap_ci, summarize

LENGTH = 600
N_PER_CLASS = 120


# --------------------------------------------------------------------------
# Stream generators: the four classes the thesis names
# --------------------------------------------------------------------------

def exact_recurrence(rng) -> np.ndarray:
    """Fibonacci-like: exactly satisfies a linear recurrence."""
    u = np.zeros(LENGTH)
    u[0], u[1] = rng.normal(), rng.normal()
    for i in range(2, LENGTH):
        u[i] = 0.6 * u[i - 1] + 0.3 * u[i - 2]
    return u


def dense_noise(rng) -> np.ndarray:
    return rng.normal(size=LENGTH)


def sparse_fixed_rate(rng) -> np.ndarray:
    """Recurrent stream with anomalies at a CONSTANT rate: gaps do not expand."""
    u = exact_recurrence(rng)
    step = 17
    for m in range(step, LENGTH, step):
        u[m] += rng.normal() * 3.0
    return u


def sparse_expanding_gap(rng) -> np.ndarray:
    """Recurrent stream with anomalies whose GAPS EXPAND: the source condition."""
    u = exact_recurrence(rng)
    m, k, gap = 12, 1, 6
    while m < LENGTH:
        u[m] += rng.normal() * 3.0 * (k ** 0.5)     # polynomial magnitude variation
        gap = int(gap * 1.35) + 1                    # expanding gaps
        m += gap
        k += 1
    return u


CLASSES = {
    "exact recurrence": exact_recurrence,
    "dense noise": dense_noise,
    "sparse fixed-rate": sparse_fixed_rate,
    "sparse expanding-gap": sparse_expanding_gap,
}
TARGET = "sparse expanding-gap"


# --------------------------------------------------------------------------
# Matched baselines
# --------------------------------------------------------------------------

def changepoint_statistic(u: np.ndarray, order: int = 2, scale: int = 4) -> float:
    """CUSUM on the same filtered residual the sentinel sees. Equal preprocessing."""
    b = fit_recurrence(u, order=order, scale=scale)
    w = filtered_residual(u, b, scale)
    if w.size < 4:
        return 0.0
    z = (w - w.mean()) / (w.std() + 1e-12)
    cum = np.cumsum(z)
    return float(np.max(np.abs(cum)) / np.sqrt(w.size))


def compression_statistic(u: np.ndarray, order: int = 2, scale: int = 4) -> float:
    """MDL proxy: gzip ratio of the quantised residual. Equal preprocessing."""
    b = fit_recurrence(u, order=order, scale=scale)
    w = filtered_residual(u, b, scale)
    if w.size < 4:
        return 0.0
    scaled = w / (np.max(np.abs(w)) + 1e-12)
    q = np.clip((scaled * 127).astype(np.int8), -127, 127).tobytes()
    return float(len(gzip.compress(q, 9)) / max(1, len(q)))


def _auroc_directed(pos, neg) -> float:
    """Raw AUROC, polarity as given."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if pos.size == 0 or neg.size == 0:
        return 0.5
    allv = np.concatenate([pos, neg])
    ranks = allv.argsort().argsort().astype(float) + 1
    rp = ranks[:pos.size].sum()
    return float((rp - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def _auroc(pos, neg) -> float:
    """Discrimination with the best polarity for the method.

    An unsupervised detector has no a-priori sign. Scoring one-directionally
    would have reported the compression baseline at AUROC 0.000 -- which is
    PERFECT separation with the decision rule inverted, not failure. Since
    polarity was not pre-registered for the baselines, each method is given its
    best direction. That is deliberately the most favourable reading for the
    baselines: a kill condition should give the null every chance.
    """
    a = _auroc_directed(pos, neg)
    return max(a, 1.0 - a)


def _auroc_ci(pos, neg, seed=0, resamples=4000):
    rng = np.random.default_rng(seed)
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    vals = np.empty(resamples)
    for i in range(resamples):
        vals[i] = _auroc(pos[rng.integers(0, pos.size, pos.size)],
                         neg[rng.integers(0, neg.size, neg.size)])
    return (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)))


def main() -> int:
    print("Round S1 -- Sigma-infinity Transcendence Sentinel vs its own kill condition")
    print("=" * 78)
    rng = np.random.default_rng(20260726)

    scores = {name: {"sentinel": [], "changepoint": [], "compression": []}
              for name in CLASSES}
    for name, gen in CLASSES.items():
        for _ in range(N_PER_CLASS):
            u = gen(rng)
            scores[name]["sentinel"].append(sentinel_score(u).score)
            scores[name]["changepoint"].append(changepoint_statistic(u))
            scores[name]["compression"].append(compression_statistic(u))

    print(f"\n  Per-class means (n = {N_PER_CLASS} each)\n")
    print(f"  {'class':<24}{'sentinel':>22}{'changepoint':>16}{'compression':>16}")
    print("  " + "-" * 76)
    for name in CLASSES:
        s = summarize("s", scores[name]["sentinel"])
        c = summarize("c", scores[name]["changepoint"])
        z = summarize("z", scores[name]["compression"])
        print(f"  {name:<24}{s.value:>8.4f} [{s.ci[0]:.3f},{s.ci[1]:.3f}]"
              f"{c.value:>16.4f}{z.value:>16.4f}")

    print("\n  Discrimination: target class vs each other class (AUROC, 95% CI)\n")
    print(f"  {'comparison':<34}{'sentinel':>20}{'changepoint':>20}{'compression':>20}")
    print("  " + "-" * 92)
    summary = {"sentinel": [], "changepoint": [], "compression": []}
    for other in CLASSES:
        if other == TARGET:
            continue
        row = f"  {TARGET[:14]} vs {other:<17}"
        for method in ("sentinel", "changepoint", "compression"):
            a = _auroc(scores[TARGET][method], scores[other][method])
            lo, hi = _auroc_ci(scores[TARGET][method], scores[other][method])
            summary[method].append(a)
            row += f"{a:>8.3f} [{lo:.2f},{hi:.2f}]"
        print(row)

    print("\n" + "=" * 78)
    print("VERDICT against the thesis's pre-registered kill condition")
    print("=" * 78)
    means = {m: float(np.mean(v)) for m, v in summary.items()}
    for m, v in means.items():
        print(f"  mean AUROC {m:<13} {v:.3f}")
    best_base = max(means["changepoint"], means["compression"])
    matched = best_base >= means["sentinel"] - 0.02
    print(f"\n  best matched baseline: {best_base:.3f}   sentinel: {means['sentinel']:.3f}")
    if matched:
        print("\n  KILL CONDITION MET. A conventional method matches the sentinel at")
        print("  equal preprocessing and cost. The sentinel is RETIRED for this task:")
        print("  it earns no place in the architecture on this evidence.")
    else:
        print("\n  Kill condition NOT met on this generator family: the sentinel")
        print("  separates the expanding-gap class better than either baseline.")
        print("  This promotes the operator from S to H only -- one synthetic")
        print("  generator is not a cognitive result, and the thesis's own ledger")
        print("  rates the whole architecture H until controlled experiments run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
