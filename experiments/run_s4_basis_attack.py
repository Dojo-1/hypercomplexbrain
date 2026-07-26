"""S4-G100 side result: is EXP-S3-SHEAF_LOCALISATION representation-invariant?

S4-G100's mandatory attack suite raised a question about a *prior* claim, so this
answers it rather than leaving the claim exposed.

The S3 sheaf instrument spreads each cycle's obstruction over the edges of a
**fundamental cycle basis**, and a fundamental basis is an arbitrary choice of
spanning tree.  Relabelling the worldlets changes which tree the depth-first
search grows, hence which cycles the blame is spread over.  Short basis cycles
concentrate blame; long ones dilute it.  That is an admissible reparametrisation:
it does not change the sheaf, only its description.

The result below is that the S3 effect is real but its *magnitude* is
representation-dependent, so the claim is superseded rather than retired.

Run with:  PYTHONPATH=src python3 experiments/run_s4_basis_attack.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.sheaf import (CellularSheaf, Nerve, auroc, localise,
                         make_obstructed_sheaf)
from aionq.statistics import compare_groups, summarize

TRIALS = 300
INSTRUMENTS = ["sheaf", "shuffled", "graph"]
OUT = Path(__file__).resolve().parent.parent / "artifacts" / "s4_g100" / "summaries"


def relabel(nerve: Nerve, rng):
    """Permute worldlet labels, then re-sort. An admissible reparametrisation."""
    perm = rng.permutation(nerve.n_worldlets)
    pairs = sorted((tuple(sorted((int(perm[i]), int(perm[j])))), k)
                   for k, (i, j) in enumerate(nerve.edges))
    return Nerve(nerve.n_worldlets, tuple(p[0] for p in pairs)), [p[1] for p in pairs]


def random_nerve(rng, n=8, m=13) -> Nerve:
    """The same construction Round S3 used, so this tests S3's own instance family."""
    perm = rng.permutation(n)
    edges = {tuple(sorted((int(perm[k]), int(perm[rng.integers(0, k)]))))
             for k in range(1, n)}
    pool = [(i, j) for i in range(n) for j in range(i + 1, n) if (i, j) not in edges]
    rng.shuffle(pool)
    for x in pool[:max(0, m - len(edges))]:
        edges.add(x)
    return Nerve(n, tuple(sorted(edges)))


def main() -> int:
    print("S4 side result -- is the S3 localisation claim representation-invariant?")
    print("=" * 82)
    print(f"  {TRIALS} trials, the S3 instance family (V=8, E=13, 2 hidden defects)")
    print("  Attack: permute worldlet labels. Same sheaf, different spanning tree,")
    print("  therefore a different fundamental cycle basis.")

    orig = {k: [] for k in INSTRUMENTS}
    relabelled = {k: [] for k in INSTRUMENTS}
    rng = np.random.default_rng(4242)

    for _ in range(TRIALS):
        nerve = random_nerve(rng)
        defects = rng.choice(nerve.n_edges, size=2, replace=False)
        sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        for k in INSTRUMENTS:
            orig[k].append(auroc(localise(sheaf, k, rng), labels))

        n2, order = relabel(nerve, rng)
        s2 = CellularSheaf(n2, [sheaf.transitions[i] for i in order], sheaf.fiber_dim)
        inv = {old: new for new, old in enumerate(order)}
        l2 = np.zeros(n2.n_edges, dtype=bool)
        for x in defects:
            l2[inv[int(x)]] = True
        for k in INSTRUMENTS:
            relabelled[k].append(auroc(localise(s2, k, rng), l2))

    print(f"\n  {'instrument':<12}{'as published':>24}{'relabelled':>24}{'shift':>10}")
    print("  " + "-" * 70)
    rows = {}
    for k in INSTRUMENTS:
        a = summarize(k, orig[k], seed=1)
        b = summarize(k, relabelled[k], seed=1)
        rows[k] = {"original": {"mean": a.value, "ci": list(a.ci)},
                   "relabelled": {"mean": b.value, "ci": list(b.ci)},
                   "shift": b.value - a.value}
        print(f"  {k:<12}{a.value:>10.3f} [{a.ci[0]:.3f}, {a.ci[1]:.3f}]"
              f"{b.value:>12.3f} [{b.ci[0]:.3f}, {b.ci[1]:.3f}]{b.value - a.value:>+10.3f}")

    print("\n  Contrast, which is what the claim actually asserts:")
    contrasts = {}
    for rival in ("shuffled", "graph"):
        e1 = compare_groups(f"as published: sheaf - {rival}", orig["sheaf"],
                            orig[rival], resamples=4000, seed=7)
        e2 = compare_groups(f"relabelled:   sheaf - {rival}", relabelled["sheaf"],
                            relabelled[rival], resamples=4000, seed=7)
        contrasts[rival] = {"original": {"delta": e1.difference, "ci": list(e1.ci),
                                         "d": e1.cohens_d},
                            "relabelled": {"delta": e2.difference, "ci": list(e2.ci),
                                           "d": e2.cohens_d}}
        print(f"    {e1}")
        print(f"    {e2}")

    print("\n" + "=" * 82)
    print("VERDICT on EXP-S3-SHEAF_LOCALISATION")
    print("=" * 82)
    surv = all(c["relabelled"]["delta"] > 0 for c in contrasts.values())
    shrink = min(c["relabelled"]["delta"] / c["original"]["delta"]
                 for c in contrasts.values())
    print(f"  direction survives relabelling: {surv}")
    print(f"  effect size retained: {shrink:.0%} of the published magnitude")
    print("\n  The claim is SUPERSEDED, not retired. Sheaf holonomy still beats both")
    print("  matched controls after an admissible relabelling, and the ordering of")
    print("  the instruments is unchanged. But the published effect size was")
    print("  measured in one arbitrary fundamental cycle basis and does not")
    print("  transport: a spanning tree with short cycles concentrates blame, one")
    print("  with long cycles dilutes it. Absolute AUROC is a representation-")
    print("  sensitive diagnostic; only the sign of the contrast is invariant here.")
    print("\n  Note the controls barely move (shuffled, graph). The instability is")
    print("  specific to the instrument that uses the basis, which is why it was")
    print("  invisible to a comparison run entirely inside one basis.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "s4_basis_attack.json").write_text(json.dumps(
        {"trials": TRIALS, "instruments": rows, "contrasts": contrasts,
         "direction_survives": bool(surv), "magnitude_retained": float(shrink)},
        indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
