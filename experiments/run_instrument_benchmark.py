"""Instrument cost, as a distribution with an environment attached.

Round QSigma-R4, part B.  The 17.2x / 27.8x figures in ``sheaf._quaternion_basis``
were measured once, on one machine, and then written into a docstring where they
read like constants.  This script is where they come from, so the claim is
reconstructible instead of remembered.

Three deliberate choices:

* **Randomised condition order per batch.** A fixed order lets a warming cache,
  a turbo-clock ramp or a noisy neighbour attach itself to whichever condition
  runs first, and that artefact is indistinguishable from an effect.
* **Median and a bootstrap interval, not a mean.** One descheduled batch moves a
  mean and not a median, and a ratio quoted without an interval invites exactly
  the over-reading that produced "131x".
* **No pass/fail.** A wall-clock ratio is not a correctness property. Gating CI
  on one makes a loaded runner fail a test about arithmetic; the functional
  claim -- one construction, then reuse -- is tested separately by counting.

Run with:  PYTHONPATH=src python3 experiments/run_instrument_benchmark.py
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq import sheaf as S
from aionq.evidence import (EvidenceEnvelope, current_commit, environment_digest,
                            file_digest, save_envelope)
from aionq.sheaf import make_obstructed_sheaf, ring_of_worldlets
from aionq.statistics import bootstrap_ci

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "r4"
BATCHES, REPS, WARMUP = 12, 40, 5


def blas_info() -> dict:
    try:
        cfg = np.__config__.show(mode="dicts")           # numpy >= 1.25
        blas = next(iter(cfg.get("Build Dependencies", {}).get("blas", {}).items()), None)
        return {"numpy_blas": str(cfg.get("Build Dependencies", {}).get("blas", {}))[:200]}
    except Exception as exc:                             # noqa: BLE001 - metadata only
        return {"numpy_blas": f"unavailable: {type(exc).__name__}"}


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _time(fn, reps: int) -> float:
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t0) / reps


def main() -> int:
    rng = np.random.default_rng(0)
    nerve = ring_of_worldlets(9, chords=((0, 4), (2, 7), (5, 8)))
    sh = make_obstructed_sheaf(nerve, [3], rng, kind="hypercomplex", dim=4)
    cycles = nerve.cycle_basis()

    def sheaf_run():
        S.INSTRUMENTS["sheaf"](sh, cycles, np.random.default_rng(1))

    def quat_cached():
        S.INSTRUMENTS["quaternion"](sh, cycles, np.random.default_rng(1))

    def quat_uncached():
        S.reset_quaternion_basis()
        S.INSTRUMENTS["quaternion"](sh, cycles, np.random.default_rng(1))

    conditions = {"sheaf": sheaf_run,
                  "quaternion_cached": quat_cached,
                  "quaternion_uncached": quat_uncached}

    for fn in conditions.values():                       # warm-up, discarded
        _time(fn, WARMUP)

    raw: dict = {k: [] for k in conditions}
    order_rng = np.random.default_rng(7)
    for _ in range(BATCHES):
        names = list(conditions)
        order_rng.shuffle(names)                         # randomised each batch
        for name in names:
            S._QUATERNION_BASIS = None if name == "quaternion_uncached" \
                else S._quaternion_basis()
            raw[name].append(_time(conditions[name], REPS))

    stats = {}
    base = float(np.median(raw["sheaf"]))
    for name, vals in raw.items():
        arr = np.asarray(vals)
        lo, hi = bootstrap_ci(arr, seed=3)
        stats[name] = {
            "median_seconds": float(np.median(arr)),
            "median_ratio_vs_sheaf": float(np.median(arr) / base),
            "bootstrap_ci_seconds": [float(lo), float(hi)],
            "min_seconds": float(arr.min()), "max_seconds": float(arr.max()),
            "n_batches": int(arr.size), "reps_per_batch": REPS,
        }

    env = environment_digest()
    payload = {
        "schema": "hypercomplexbrain.benchmark.v1",
        "commit_sha": current_commit(),
        "environment": env,
        "cpu": cpu_model(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        **blas_info(),
        "protocol": {"batches": BATCHES, "reps_per_batch": REPS,
                     "warmup_reps": WARMUP, "order": "randomised per batch",
                     "statistic": "median with bootstrap CI"},
        "instance": {"worldlets": nerve.n_worldlets, "edges": nerve.n_edges,
                     "fiber_dim": 4, "cycles": len(cycles)},
        "raw_seconds": raw,
        "statistics": stats,
        "note": "Ratios are environment-specific measurements, not constants. "
                "No CI job gates on them.",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "instrument_benchmark.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    print("Instrument cost -- median over "
          f"{BATCHES} randomised batches of {REPS} reps")
    print("=" * 74)
    print(f"  {'condition':>22}{'median':>13}{'ratio':>9}"
          f"{'bootstrap CI (s)':>28}")
    for name, s in stats.items():
        lo, hi = s["bootstrap_ci_seconds"]
        print(f"  {name:>22}{s['median_seconds']*1e6:>10.1f} us"
              f"{s['median_ratio_vs_sheaf']:>8.2f}x"
              f"   [{lo*1e6:>8.1f}, {hi*1e6:>8.1f}] us")
    print(f"\n  cpu    : {payload['cpu']}")
    print(f"  python : {payload['python']}   numpy {payload['numpy']}")
    print(f"  commit : {payload['commit_sha'][:12]}")

    envelope = EvidenceEnvelope(
        claim_id="METRIC-R4-INSTRUMENT_COST",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_instrument_benchmark.py",
        observed_result={
            # NOT `BATCHES`.  The first version of this envelope declared
            # sample_size = 12 and the verifier rejected it: 12 timing batches on
            # ONE instance are repeated measurements, not twelve experiments.
            # That is the borrowed m1-bordon rule firing on its own author.
            "sample_size": 1,
            "timing_batches": BATCHES,
            "median_ratio_quaternion_cached": stats["quaternion_cached"]
                ["median_ratio_vs_sheaf"],
            "median_ratio_quaternion_uncached": stats["quaternion_uncached"]
                ["median_ratio_vs_sheaf"],
        },
        commit_sha=current_commit(),
        platform=platform.system().lower(),
        environment=env,
        seeds=[0],
        # One instance, many timing batches: the batches are repeated
        # MEASUREMENTS of one input, not distinct inputs, and the envelope says
        # so rather than letting 12 batches read as 12 experiments.
        input_hashes=["instance:ring9+3chords:dim4"],
        raw_artifacts={"artifacts/r4/instrument_benchmark.json": file_digest(path)},
        uncertainty={"statistic": "median", "interval": "bootstrap 95%"},
        producer="experiments/run_instrument_benchmark.py",
        verifier="",
        typed_remainders=[{
            "kind": "scalar_constant",
            "carrier": "median_ratio_vs_sheaf",
            "comparison": "one machine, one BLAS, one instance; the ratio is not "
                          "a property of the algorithms"}],
    )
    save_envelope(envelope, OUT / "instrument_benchmark.envelope.json")
    print(f"\nwrote {path}")
    print(f"wrote {OUT / 'instrument_benchmark.envelope.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
