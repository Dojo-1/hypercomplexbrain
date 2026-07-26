"""ACAF sweep of the S5 moving-frame result: hunt for where it breaks.

Round S5 found that a basis-free Laplacian instrument is exactly orbit-collapsed
and also the strongest localiser.  That was measured on one nerve family.  The
open bridge was to replicate on families it has never seen.

This applies the ACAF discipline: the **Ambigator** spans the parameter space
looking for boundary conditions where the harness fails, and the **Fuzzer** runs
the harness at scale.  The posture is adversarial -- the goal is to break the S5
result, not to confirm it.

The specific attack
-------------------
The instrument sums per-overlap Dirichlet energy over the bottom ``k = fiber_dim``
eigenvectors of the sheaf Laplacian.  Its invariance argument requires summing
over a **whole eigenspace**: an orthogonal mixing inside the eigenspace must not
change the score.  So the exposed failure is a closed spectral gap at the k-cut,
where the truncation splits an eigenspace and invariance should break.

The sweep therefore records ``gap_k = lambda_k - lambda_{k-1}`` on every instance
and correlates it with any invariance failure.  A hunt that finds nothing is
reported as finding nothing; a hunt that finds the predicted boundary is the more
interesting outcome.

Run with:  PYTHONPATH=src python3 experiments/run_acaf_frame_sweep.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.movingframe import equivariance_defect, orbit_report, random_frame
from aionq.sheaf import Nerve, auroc, localise, make_obstructed_sheaf

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "s4_g100" / "summaries"


@dataclass
class Ambigator:
    """Spans the parameter space, per the ACAF pattern.

    ``n`` is reinterpreted for this problem as the **fiber dimension**, which is
    the axis the suspected failure lives on; ``node_counts`` and ``densities``
    keep their usual meaning.
    """

    n_values: list          # fiber dimensions
    node_counts: list
    densities: list
    defect_counts: list
    families: list

    def build(self, family, num_nodes, density, rng) -> Nerve:
        if family == "erdos_renyi":
            edges = {tuple(sorted((int(p[k]), int(p[rng.integers(0, k)]))))
                     for p in [rng.permutation(num_nodes)] for k in range(1, num_nodes)}
            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    if rng.random() < density:
                        edges.add((i, j))
            return Nerve(num_nodes, tuple(sorted(edges)))
        if family == "ring_chords":
            n_ch = max(1, int(density * num_nodes))
            edges = {(i, (i + 1) % num_nodes) for i in range(num_nodes)}
            for _ in range(n_ch):
                a, b = int(rng.integers(num_nodes)), int(rng.integers(num_nodes))
                if a != b:
                    edges.add(tuple(sorted((a, b))))
            return Nerve(num_nodes, tuple(sorted(edges)))
        if family == "grid":
            r = max(2, int(np.sqrt(num_nodes)))
            c = max(2, num_nodes // r)
            idx = lambda a, b: (a % r) * c + (b % c)
            edges = set()
            for a in range(r):
                for b in range(c):
                    edges.add(tuple(sorted((idx(a, b), idx(a, b + 1)))))
                    if a + 1 < r:
                        edges.add(tuple(sorted((idx(a, b), idx(a + 1, b)))))
            edges = {e for e in edges if e[0] != e[1]}
            return Nerve(r * c, tuple(sorted(edges)))
        if family == "star_chords":                   # hub-and-spoke, low girth
            edges = {(0, i) for i in range(1, num_nodes)}
            for _ in range(max(1, int(density * num_nodes))):
                a, b = int(rng.integers(1, num_nodes)), int(rng.integers(1, num_nodes))
                if a != b:
                    edges.add(tuple(sorted((a, b))))
            return Nerve(num_nodes, tuple(sorted(edges)))
        raise ValueError(family)

    def sweep(self, samples_per_config, rng):
        for fam in self.families:
            for dim in self.n_values:
                for nn in self.node_counts:
                    for dens in self.densities:
                        for k in self.defect_counts:
                            for _ in range(samples_per_config):
                                nerve = self.build(fam, nn, dens, rng)
                                if nerve.n_edges <= k + 1 or nerve.betti_1 < 1:
                                    continue
                                yield fam, dim, nn, dens, k, nerve


def spectral_gap_at_cut(sheaf, k) -> float:
    vals = np.linalg.eigvalsh(sheaf.sheaf_laplacian())
    k = min(k, vals.size - 1)
    return float(vals[k] - vals[k - 1]) if k >= 1 else float("inf")


def main() -> int:
    rng = np.random.default_rng(31337)
    amb = Ambigator(n_values=[2, 3, 4, 6, 8],
                    node_counts=[6, 9, 14, 20],
                    densities=[0.15, 0.35, 0.6],
                    defect_counts=[1, 3],
                    families=["erdos_renyi", "ring_chords", "grid", "star_chords"])

    print("ACAF sweep: hunting for where the S5 invariance result breaks")
    print("=" * 84)
    print("  Ambigator spans family x fiber_dim x nodes x density x defects.")
    print("  Attack: a closed spectral gap at the k-cut should split an eigenspace")
    print("  and break the invariance argument. Recorded on every instance.")

    rows, breaks, eq_fail = [], [], 0
    n_inst = 0
    for fam, dim, nn, dens, k, nerve in amb.sweep(2, rng):
        defects = rng.choice(nerve.n_edges, size=min(k, nerve.n_edges - 1),
                             replace=False)
        sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=dim)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        frames = [random_frame(nerve.n_worldlets, dim, rng, nerve.n_edges)
                  for _ in range(12)]

        if equivariance_defect(nerve, sheaf, frames[0], frames[1]) > 1e-9:
            eq_fail += 1
            continue

        gap = spectral_gap_at_cut(sheaf, dim)
        rec = {"family": fam, "dim": dim, "nodes": nerve.n_worldlets,
               "edges": nerve.n_edges, "b1": nerve.betti_1, "density": dens,
               "defects": int(len(defects)), "gap_k": gap}
        for name in ("laplacian", "sheaf", "shuffled", "graph"):
            m = (lambda n2, s2, l2, nm=name:
                 auroc(localise(s2, nm, np.random.default_rng(7)), l2))
            r = orbit_report(name, m, nerve, sheaf, labels, frames)
            rec[f"{name}_auroc"] = r.identity_value
            rec[f"{name}_maxdev"] = r.max_deviation
        rows.append(rec)
        n_inst += 1
        if rec["laplacian_maxdev"] > 1e-9:
            breaks.append(rec)

    lap_dev = np.array([r["laplacian_maxdev"] for r in rows])
    lap_a = np.array([r["laplacian_auroc"] for r in rows])
    sh_a = np.array([r["sheaf_auroc"] for r in rows])
    sh_dev = np.array([r["sheaf_maxdev"] for r in rows])

    print(f"\n  {n_inst} instances survived generation; equivariance failures: {eq_fail}")
    print("\n  INVARIANCE HUNT")
    print("  " + "-" * 80)
    print(f"    laplacian max orbit deviation:  max {lap_dev.max():.2e}  "
          f"mean {lap_dev.mean():.2e}")
    print(f"    sheaf     max orbit deviation:  max {sh_dev.max():.3f}  "
          f"mean {sh_dev.mean():.3f}")
    print(f"    instances where laplacian invariance BROKE: {len(breaks)}")
    if breaks:
        print("    boundary conditions found:")
        for b in breaks[:8]:
            print(f"      {b['family']:<12} dim={b['dim']} V={b['nodes']:>2} "
                  f"E={b['edges']:>3} gap_k={b['gap_k']:.2e} "
                  f"dev={b['laplacian_maxdev']:.4f}")
        gaps_b = np.array([b["gap_k"] for b in breaks])
        gaps_ok = np.array([r["gap_k"] for r in rows if r["laplacian_maxdev"] <= 1e-9])
        print(f"    median gap_k where it broke: {np.median(gaps_b):.2e}")
        print(f"    median gap_k where it held : {np.median(gaps_ok):.2e}")
    else:
        print("    NONE. The predicted failure mode did not occur anywhere in the")
        print("    swept space, including at the smallest spectral gaps sampled")
        print(f"    (min gap_k = {min(r['gap_k'] for r in rows):.2e}).")

    print("\n  ACCURACY, per family (does invariance still buy accuracy?)")
    print("  " + "-" * 80)
    print(f"    {'family':<14}{'n':>5}{'laplacian':>12}{'sheaf':>10}{'delta':>10}"
          f"{'wins':>8}")
    fam_rows = {}
    for r in rows:
        fam_rows.setdefault(r["family"], []).append(r)
    for fam, rs in sorted(fam_rows.items()):
        la = np.array([x["laplacian_auroc"] for x in rs])
        sa = np.array([x["sheaf_auroc"] for x in rs])
        print(f"    {fam:<14}{len(rs):>5}{la.mean():>12.3f}{sa.mean():>10.3f}"
              f"{la.mean() - sa.mean():>+10.3f}{(la > sa).mean():>8.0%}")
    print(f"    {'ALL':<14}{len(rows):>5}{lap_a.mean():>12.3f}{sh_a.mean():>10.3f}"
          f"{lap_a.mean() - sh_a.mean():>+10.3f}{(lap_a > sh_a).mean():>8.0%}")

    print("\n  ACCURACY by fiber dimension (the axis the attack targeted)")
    print("  " + "-" * 80)
    for dim in sorted({r["dim"] for r in rows}):
        rs = [r for r in rows if r["dim"] == dim]
        la = np.array([x["laplacian_auroc"] for x in rs])
        sa = np.array([x["sheaf_auroc"] for x in rs])
        dv = max(x["laplacian_maxdev"] for x in rs)
        print(f"    dim {dim:<3} n={len(rs):<4} laplacian {la.mean():.3f}  "
              f"sheaf {sa.mean():.3f}  delta {la.mean()-sa.mean():+.3f}  "
              f"maxdev {dv:.1e}")

    print("\n" + "=" * 84)
    print("VERDICT")
    print("=" * 84)
    held = len(breaks) == 0
    wins = float((lap_a > sh_a).mean())
    print(f"  invariance held on {n_inst - len(breaks)}/{n_inst} instances across "
          f"{len(fam_rows)} families")
    print(f"  laplacian beat sheaf on {wins:.0%} of instances, "
          f"delta {lap_a.mean()-sh_a.mean():+.3f}")
    if held and wins > 0.5:
        print("\n  The S5 result REPLICATES on families it has never seen, and the")
        print("  attack designed to break it did not. Invariance is structural, not")
        print("  a property of the family it was found on.")
    elif held:
        print("\n  Invariance replicates, but the ACCURACY advantage does not hold")
        print("  everywhere. The invariance claim survives; the accuracy claim must")
        print("  be scoped to the regimes where it holds.")
    else:
        print("\n  BOUNDARY FOUND. The invariance claim must be scoped, and")
        print("  MATH-S5-LAPLACIAN_INVARIANT narrowed to the regime where it holds.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "acaf_frame_sweep.json").write_text(json.dumps(
        {"instances": n_inst, "equivariance_failures": eq_fail,
         "invariance_breaks": len(breaks),
         "laplacian_max_deviation": float(lap_dev.max()),
         "laplacian_mean_auroc": float(lap_a.mean()),
         "sheaf_mean_auroc": float(sh_a.mean()),
         "win_rate": wins, "rows": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
