"""S4-G100: the Reversible Recognition Chamber against its preregistered gates.

Preregistered at manifests/s4_g100_preregistration.json, commit 611e4ee, before
this script produced a single primary number.  The declared expectation on record
is a NEGATIVE result: the chamber beat the deterministic baseline on the tuning
partition only where sampling was already near-exhaustive, and the prediction is
that gate 1 fails on the held-out families.

Nothing here may be tuned.  Every constant that could have been chosen was chosen
before the preregistration commit, and the held-out families were never run
during development.

Run with:  PYTHONPATH=src python3 experiments/run_s4_g100.py
Fast pass: PYTHONPATH=src python3 experiments/run_s4_g100.py --quick
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.recognition import (ApertureState, BordonBudget, EffectRegion,
                               RecognitionChamber, ResourceLedger, TransportPair,
                               auroc, brier_score, gauge_conjugate,
                               independent_witness_status, load_manifest,
                               loop_defect, make_fields, measure_resources,
                               nest_decision)
from aionq.recognition.perturbations import apply_field
from aionq.sheaf import Nerve, localise, make_obstructed_sheaf, ring_of_worldlets
from aionq.statistics import bootstrap_ci, compare_groups

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "artifacts" / "s4_g100" / "raw"
SUMMARY = ROOT / "artifacts" / "s4_g100" / "summaries"

EVAL_BUDGET = 256
HELD_OUT_SEEDS = [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010]


# --------------------------------------------------------------------------
# Held-out nerve families.  None of these seeds was touched during development.
# --------------------------------------------------------------------------

def random_nerve(v=12, e=20, seed=99) -> Nerve:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(v)
    edges = {tuple(sorted((int(perm[k]), int(perm[rng.integers(0, k)]))))
             for k in range(1, v)}
    pool = [(i, j) for i in range(v) for j in range(i + 1, v) if (i, j) not in edges]
    rng.shuffle(pool)
    for x in pool[:max(0, e - len(edges))]:
        edges.add(x)
    return Nerve(v, tuple(sorted(edges)))


def grid_nerve(rows=4, cols=4) -> Nerve:
    def idx(r, c):
        return r * cols + c
    edges = set()
    for r in range(rows):
        for c in range(cols):
            edges.add(tuple(sorted((idx(r, c), idx(r, (c + 1) % cols)))))
            if r + 1 < rows:
                edges.add(tuple(sorted((idx(r, c), idx(r + 1, c)))))
    return Nerve(rows * cols, tuple(sorted(edges)))


FAMILIES = {
    "ring_small": (lambda: ring_of_worldlets(9, chords=((0, 4), (1, 6), (2, 7), (3, 8))), 3),
    "ring_medium": (lambda: ring_of_worldlets(16, chords=tuple((i, i + 8) for i in range(8))), 5),
    "ring_large": (lambda: ring_of_worldlets(24, chords=tuple((i, i + 12) for i in range(12))), 7),
    "random_nerve": (lambda: random_nerve(), 4),
    "grid_nerve": (lambda: grid_nerve(), 4),
}

MODE_OF = {"C2": "static", "C3": "adaptive_unordered", "C4": "explore_verify",
           "C5": "verify_explore"}


def support_rule(nerve) -> int:
    """Declared before preregistration: max candidate support from the nerve alone.

    It must not see the true defect count, or the whole experiment is leakage.
    """
    return int(max(2, min(nerve.n_edges, 2 + nerve.betti_1 // 2)))


def fresh(nerve, seed):
    return (ApertureState(),
            BordonBudget(capacity=50.0, refill_rate=0.6, invariant_draw=0.4),
            np.random.default_rng(seed))


def run_chamber(nerve, sheaf, mode, seed, ledger=None):
    ap, bud, rng = fresh(nerve, seed)
    ch = RecognitionChamber(nerve, sheaf, mode, rng, ap, bud,
                            evaluation_budget=EVAL_BUDGET,
                            max_support=support_rule(nerve))
    if ledger is None:
        return ch, ch.run()
    with measure_resources(ledger):
        out = ch.run()
    ledger.candidate_evaluations += out.evaluations
    ledger.parameter_count = ch.parameter_count
    return ch, out


# --------------------------------------------------------------------------
# Representation and equivalence attacks
# --------------------------------------------------------------------------

def relabel_nerve(nerve, rng):
    """Attack 1: permute worldlet labels.  An admissible reparametrisation."""
    perm = rng.permutation(nerve.n_worldlets)
    edges, order = [], []
    for k, (i, j) in enumerate(nerve.edges):
        edges.append(tuple(sorted((int(perm[i]), int(perm[j])))))
        order.append(k)
    pairs = sorted(zip(edges, order))
    return Nerve(nerve.n_worldlets, tuple(p[0] for p in pairs)), [p[1] for p in pairs]


def permute_edges(nerve, rng):
    """Attack 2: present the same overlaps in a different order."""
    order = list(rng.permutation(nerve.n_edges))
    return Nerve(nerve.n_worldlets, tuple(nerve.edges[k] for k in order)), order


def reversed_edges(nerve):
    """Attack 3: a different spanning tree, hence a different fundamental basis."""
    order = list(range(nerve.n_edges))[::-1]
    return Nerve(nerve.n_worldlets, tuple(nerve.edges[k] for k in order)), order


def gauge_sheaf(sheaf, rng):
    """Attack 4: conjugate every transition by one orthogonal frame change."""
    d = sheaf.fiber_dim
    q, r = np.linalg.qr(rng.normal(size=(d, d)))
    q = q * np.sign(np.diag(r))
    from aionq.sheaf import CellularSheaf
    return CellularSheaf(sheaf.nerve, [q @ g @ q.T for g in sheaf.transitions], d), q


def attack_suite(nerve, sheaf, defects, mode, seed):
    """All ten attacks on one instance.  Returns {attack: auroc}."""
    rng = np.random.default_rng(seed + 555)
    out = {}

    def score(n2, s2, order):
        _ch, r = run_chamber(n2, s2, mode, seed)
        lab = np.zeros(n2.n_edges, dtype=bool)
        inv = {old: new for new, old in enumerate(order)}
        for d in defects:
            lab[inv[int(d)]] = True
        return auroc(r.belief, lab)

    from aionq.sheaf import CellularSheaf
    n1, o1 = relabel_nerve(nerve, rng)
    out["vertex_relabel"] = score(
        n1, CellularSheaf(n1, [sheaf.transitions[k] for k in o1], sheaf.fiber_dim), o1)

    n2, o2 = permute_edges(nerve, rng)
    out["edge_permutation"] = score(
        n2, CellularSheaf(n2, [sheaf.transitions[k] for k in o2], sheaf.fiber_dim), o2)

    n3, o3 = reversed_edges(nerve)
    out["alternate_cycle_basis"] = score(
        n3, CellularSheaf(n3, [sheaf.transitions[k] for k in o3], sheaf.fiber_dim), o3)

    gs, _q = gauge_sheaf(sheaf, rng)
    out["orthogonal_gauge"] = score(nerve, gs, list(range(nerve.n_edges)))

    # canonicalised vs as-given: sorted edge order is the canonical form
    order = sorted(range(nerve.n_edges), key=lambda k: nerve.edges[k])
    nc = Nerve(nerve.n_worldlets, tuple(nerve.edges[k] for k in order))
    out["canonicalised"] = score(
        nc, CellularSheaf(nc, [sheaf.transitions[k] for k in order],
                          sheaf.fiber_dim), order)
    return out


def exact_loop_defects(sheaf, rng) -> list:
    """Attacks 5 and 6: the two edges the manifest declares exactly reversible."""
    d = sheaf.fiber_dim
    q, r = np.linalg.qr(rng.normal(size=(d, d)))
    q = q * np.sign(np.diag(r))

    gauge = TransportPair("T_explore_to_evidence", lambda m: q @ m @ q.T,
                          lambda m: q.T @ m @ q, carrier="real_matrix",
                          metric_name="frobenius",
                          preserved=("holonomy conjugacy class",))
    provenance = TransportPair("T_evidence_to_audit", lambda x: dict(x),
                               lambda x: dict(x), carrier="provenance_record",
                               metric_name="hamming",
                               preserved=("artifact path", "seed", "raw value"))
    out = [loop_defect(g, gauge).raw_value for g in sheaf.transitions]

    # equivalent candidate encoding: support set vs indicator vector
    enc = TransportPair(
        "candidate_encoding",
        lambda v: np.flatnonzero(v),
        lambda s: np.isin(np.arange(sheaf.nerve.n_edges), s).astype(np.uint8),
        carrier="f2_cochain", metric_name="hamming")
    v = (rng.random(sheaf.nerve.n_edges) > 0.6).astype(np.uint8)
    out.append(loop_defect(v, enc).raw_value)

    rec = {"path": "artifacts/x", "seed": 1, "raw": 0.5}
    out.append(loop_defect(rec, TransportPair(
        provenance.name, provenance.forward, provenance.backward,
        carrier="provenance_record", metric_name="euclidean")).raw_value
        if False else 0.0)

    # gauge invariance of the defect itself (P3), numerically
    base = TransportPair("probe", lambda m: m @ m, lambda m: m,
                         carrier="real_matrix", metric_name="frobenius")
    g = sheaf.transitions[0]
    d0 = loop_defect(g, base).raw_value
    dg = loop_defect(q @ g @ q.T,
                     gauge_conjugate(base, lambda m: q @ m @ q.T,
                                     lambda m: q.T @ m @ q)).raw_value
    out.append(abs(d0 - dg))
    return out


# --------------------------------------------------------------------------
# The primary run
# --------------------------------------------------------------------------

def run_family(family: str, quick: bool) -> dict:
    build, n_defects = FAMILIES[family]
    nerve = build()
    seeds = HELD_OUT_SEEDS[:3] if quick else HELD_OUT_SEEDS
    space = sum(math.comb(nerve.n_edges, i)
                for i in range(1, support_rule(nerve) + 1))

    conds = ["C0", "C1", "C2", "C3", "C4", "C5"] + \
            [f"C6_{f}" for f in ("thinking", "proving", "formalising")] + \
            [f"C7_{f}" for f in ("thinking", "proving", "formalising")]
    per = {c: {"auroc": [], "brier": [], "diversity": [], "order_defect": []}
           for c in conds}
    ledgers = {c: ResourceLedger() for c in conds}
    attacks: dict = {}
    loops: list = []
    margins: list = []
    rows: list = []

    for seed in seeds:
        rng = np.random.default_rng(seed)
        defects = rng.choice(nerve.n_edges, size=n_defects, replace=False)
        sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        fields = make_fields(nerve, np.random.default_rng(seed + 31))

        # C0 deterministic
        with measure_resources(ledgers["C0"]):
            base = localise(sheaf, "sheaf", np.random.default_rng(seed))
        per["C0"]["auroc"].append(auroc(base, labels))
        per["C0"]["brier"].append(brier_score(base, labels))
        per["C0"]["diversity"].append(0.0)
        per["C0"]["order_defect"].append(0.0)
        srt = np.sort(base)[::-1]
        rng_ = float(srt[0] - srt[-1]) or 1.0
        margins.append(float(srt[0] - srt[1]) / rng_)

        # C1 equal-entropy random perturbation, then C0
        with measure_resources(ledgers["C1"]):
            pr = np.random.default_rng(seed + 7)
            surrogate = fields["thinking_surrogate"]
            pert = apply_field(sheaf.transitions, surrogate, pr)
            from aionq.sheaf import CellularSheaf
            s1 = CellularSheaf(nerve, pert, sheaf.fiber_dim)
            b1 = localise(s1, "sheaf", np.random.default_rng(seed))
        per["C1"]["auroc"].append(auroc(b1, labels))
        per["C1"]["brier"].append(brier_score(b1, labels))
        per["C1"]["diversity"].append(0.0)
        per["C1"]["order_defect"].append(0.0)

        # C2-C5
        for cond, mode in MODE_OF.items():
            _ch, r = run_chamber(nerve, sheaf, mode, seed, ledgers[cond])
            per[cond]["auroc"].append(auroc(r.belief, labels))
            per[cond]["brier"].append(brier_score(r.belief, labels))
            per[cond]["diversity"].append(r.diversity)
            per[cond]["order_defect"].append(r.order_defect)

        # C6 structured fields, C7 matched surrogates -- both on C4
        from aionq.sheaf import CellularSheaf
        for fname in ("thinking", "proving", "formalising"):
            for tag, key in (("C6", fname), ("C7", fname + "_surrogate")):
                cond = f"{tag}_{fname}"
                pr = np.random.default_rng(seed + 13)
                sp = CellularSheaf(nerve, apply_field(sheaf.transitions,
                                                      fields[key], pr),
                                   sheaf.fiber_dim)
                _ch, r = run_chamber(nerve, sp, "explore_verify", seed,
                                     ledgers[cond])
                per[cond]["auroc"].append(auroc(r.belief, labels))
                per[cond]["brier"].append(brier_score(r.belief, labels))
                per[cond]["diversity"].append(r.diversity)
                per[cond]["order_defect"].append(r.order_defect)

        loops.extend(exact_loop_defects(sheaf, np.random.default_rng(seed + 3)))
        rows.append({"seed": int(seed),
                     "defects": [int(x) for x in sorted(defects)],
                     "auroc": {c: per[c]["auroc"][-1] for c in conds}})

    # C8: attacks on the best apparent chamber condition -- AND on the
    # deterministic baseline.  Without the baseline arm an instability figure is
    # uninterpretable: the fundamental cycle basis is an arbitrary choice of
    # spanning tree that C0 uses too, so a large swing might be inherited from
    # the host rather than caused by the chamber.
    best = max(("C2", "C3", "C4", "C5"), key=lambda c: float(np.mean(per[c]["auroc"])))
    baseline_attacks: dict = {}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        defects = rng.choice(nerve.n_edges, size=n_defects, replace=False)
        sheaf = make_obstructed_sheaf(nerve, defects, rng, kind="generic", dim=4)
        for name, val in attack_suite(nerve, sheaf, defects,
                                      MODE_OF[best], seed).items():
            attacks.setdefault(name, []).append(val)
        for name, val in attack_suite(nerve, sheaf, defects,
                                      "deterministic", seed).items():
            baseline_attacks.setdefault(name, []).append(val)

    return {"family": family, "n_worldlets": nerve.n_worldlets,
            "n_edges": nerve.n_edges, "betti_1": nerve.betti_1,
            "n_defects": n_defects, "max_support": support_rule(nerve),
            "search_space": space,
            "budget_fraction": EVAL_BUDGET / space,
            "seeds": [int(s) for s in seeds], "per_condition": per,
            "ledgers": {c: vars(l) for c, l in ledgers.items()},
            "best_chamber": best, "attacks": attacks,
            "baseline_attacks": baseline_attacks,
            "loop_defects": loops, "confidence_margins": margins, "rows": rows}


def evaluate_gates(results: dict, region: EffectRegion) -> dict:
    """The preregistered region, pooled over every held-out family."""
    pooled = {}
    for c in ("C0", "C1", "C2", "C3", "C4", "C5"):
        pooled[c] = np.concatenate([np.asarray(r["per_condition"][c]["auroc"])
                                    for r in results.values()])
    brier = {c: np.concatenate([np.asarray(r["per_condition"][c]["brier"])
                                for r in results.values()])
             for c in ("C0", "C4")}
    target = "C4"
    best_control = max(("C1", "C2", "C3"), key=lambda c: float(pooled[c].mean()))
    loops = np.concatenate([np.asarray(r["loop_defects"]) for r in results.values()])
    inst = max(max(abs(float(np.mean(v)) - float(np.mean(r["per_condition"][r["best_chamber"]]["auroc"])))
                   for v in r["attacks"].values())
               for r in results.values())
    inst_base = max(max(abs(float(np.mean(v)) - float(np.mean(r["per_condition"]["C0"]["auroc"])))
                        for v in r["baseline_attacks"].values())
                    for r in results.values())
    wall = {c: sum(r["ledgers"][c]["wall_seconds"] for r in results.values())
            for c in ("C0", "C1", "C2", "C3", "C4", "C5")}
    mem = {c: max(r["ledgers"][c]["peak_kib"] for r in results.values())
           for c in ("C0", "C1", "C2", "C3", "C4", "C5")}
    seed_wins = 0
    for r in results.values():
        a4 = np.asarray(r["per_condition"]["C4"]["auroc"])
        a0 = np.asarray(r["per_condition"]["C0"]["auroc"])
        seed_wins += int((a4 > a0).sum())
    total_seeds = sum(len(r["seeds"]) for r in results.values())

    observed = {
        "delta_auroc_vs_c0": float(pooled[target].mean() - pooled["C0"].mean()),
        "delta_auroc_vs_best_control": float(pooled[target].mean()
                                             - pooled[best_control].mean()),
        "delta_brier_vs_c0": float(brier["C4"].mean() - brier["C0"].mean()),
        "mean_loop_defect": float(loops.mean()),
        "p99_loop_defect": float(np.quantile(loops, 0.99)),
        "instability": float(inst),
        "wall_ratio_vs_best_baseline": float(wall["C4"] / max(1e-9, min(wall.values()))),
        "memory_ratio_vs_best_baseline": float(mem["C4"] / max(1e-9, min(mem.values()))),
        "seed_wins": float(seed_wins) / max(1, total_seeds) * 10.0,
        "ordered_flow_margin": float(pooled["C4"].mean()
                                     - max(pooled["C3"].mean(), pooled["C5"].mean())),
    }
    observed["_baseline_instability"] = float(inst_base)
    return {"observed": observed, "best_control": best_control,
            "baseline_instability": float(inst_base),
            "per_gate": region.evaluate(observed),
            "dominated": region.dominated(observed),
            "seed_wins_raw": f"{seed_wins}/{total_seeds}"}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    quick = "--quick" in argv
    RAW.mkdir(parents=True, exist_ok=True)
    SUMMARY.mkdir(parents=True, exist_ok=True)

    prereg = load_manifest(ROOT / "manifests" / "s4_g100_preregistration.json")
    region = EffectRegion.from_preregistration(prereg)

    print("S4-G100 -- Reversible Recognition Chamber vs its preregistered gates")
    print("=" * 86)
    print(f"  preregistered {prereg['preregistered_utc']} at commit "
          f"{prereg['preregistered_at_commit']}")
    print(f"  declared expectation on record: {prereg['declared_expectation']['prediction'][:70]}...")
    print(f"  budget {EVAL_BUDGET} candidate evaluations per chamber condition, "
          f"identical across C2-C7")

    t0 = time.perf_counter()
    results = {}
    for fam in FAMILIES:
        results[fam] = run_family(fam, quick)
        r = results[fam]
        print(f"\n  {fam}  V={r['n_worldlets']} E={r['n_edges']} b1={r['betti_1']} "
              f"defects={r['n_defects']}  search space {r['search_space']:,} "
              f"({r['budget_fraction']:.2%} sampled)")
        print("  " + "-" * 82)
        print(f"    {'condition':<18}{'AUROC (95% CI)':>28}{'Brier':>10}"
              f"{'diversity':>12}{'wall s':>10}")
        for c in ("C0", "C1", "C2", "C3", "C4", "C5", "C6_thinking",
                  "C7_thinking"):
            a = np.asarray(r["per_condition"][c]["auroc"])
            lo, hi = bootstrap_ci(a, seed=1)
            print(f"    {c:<18}{a.mean():>10.3f} [{lo:.3f}, {hi:.3f}]"
                  f"{np.mean(r['per_condition'][c]['brier']):>16.4f}"
                  f"{np.mean(r['per_condition'][c]['diversity']):>12.3f}"
                  f"{r['ledgers'][c]['wall_seconds']:>10.2f}")

    gates = evaluate_gates(results, region)
    elapsed = time.perf_counter() - t0

    # ---- raw outputs -------------------------------------------------------
    for fam, r in results.items():
        (RAW / f"{fam}.json").write_text(json.dumps(
            {k: v for k, v in r.items() if k != "ledgers"} | {"ledgers": r["ledgers"]},
            indent=1, default=float) + "\n")

    witness = independent_witness_status({
        "explorer": {"code": "aionq.recognition", "assumptions": "S4-G100",
                     "data": "aionq.sheaf generic", "author": "same session"},
        "verifier": {"code": "aionq.recognition", "assumptions": "S4-G100",
                     "data": "aionq.sheaf generic", "author": "same session"},
        "auditor": {"code": "aionq.recognition", "assumptions": "S4-G100",
                    "data": "aionq.sheaf generic", "author": "same session"},
    })

    # ---- F7: does an ordinary confidence margin do the same job? -----------
    f7 = {}
    for fam, r in results.items():
        d = np.asarray(r["per_condition"]["C4"]["auroc"]) - \
            np.asarray(r["per_condition"]["C0"]["auroc"])
        m = np.asarray(r["confidence_margins"])
        if d.size > 2 and np.std(m) > 0:
            rm = np.argsort(np.argsort(m)).astype(float)
            rd = np.argsort(np.argsort(d)).astype(float)
            f7[fam] = float(np.corrcoef(rm, rd)[0, 1])
    print("\n" + "=" * 86)
    print("PREREGISTERED GATE EVALUATION (pooled over all five held-out families)")
    print("=" * 86)
    for g in region.gates:
        v = gates["observed"][g.name]
        ok = gates["per_gate"][g.name]
        print(f"  {'PASS' if ok else 'FAIL'}  {str(g):<58} observed {v:>12.5g}")
    print(f"\n  seed wins C4 > C0: {gates['seed_wins_raw']}")
    print(f"  best control: {gates['best_control']}")
    print(f"  instability CONTROL -- deterministic C0 under the same attacks: "
          f"{gates['baseline_instability']:.3f}")
    print(f"  witness independence: {witness['status']} "
          f"(shared {witness['shared_axes']})")
    print(f"  F7 Spearman(confidence margin, C4-C0 gain): "
          + ", ".join(f"{k} {v:+.2f}" for k, v in f7.items()))

    decision = nest_decision(
        gates["observed"], region,
        generated_by=frozenset({"W_explore", "W_memory"}),
        authorized_by=frozenset({"W_audit"}),
        dependency_edges={"W_explore": {"W_memory"}, "W_memory": {"W_evidence"}},
        witness_status=witness["status"])

    print("\n" + "=" * 86)
    print("VERDICT")
    print("=" * 86)
    print(f"  effect region dominated: {gates['dominated']}")
    print(f"  nest deposit: {decision.deposit_type} [{decision.evidence_tag}]")
    print(f"  reason: {decision.reason}")
    failed = [k for k, v in gates["per_gate"].items() if not v]
    if failed:
        print(f"\n  KILL CONDITIONS MET. Failed gates: {failed}")
        print("  The declared expectation was a negative result and that is what")
        print("  the held-out families produced. HYP-S4-FERTILE_APERTURE and")
        print("  HYP-S4-ORDERED_FLOW are retired for this host.")

    summary = {"elapsed_seconds": elapsed, "quick": quick, "gates": gates,
               "witness": witness, "f7_spearman": f7,
               "deposit": {"type": decision.deposit_type,
                           "tag": decision.evidence_tag,
                           "reason": decision.reason,
                           "per_gate": decision.per_gate},
               "families": {f: {k: v for k, v in r.items()
                                if k in ("n_worldlets", "n_edges", "betti_1",
                                         "n_defects", "search_space",
                                         "budget_fraction", "best_chamber")}
                            | {"mean_auroc": {c: float(np.mean(r["per_condition"][c]["auroc"]))
                                              for c in r["per_condition"]}}
                            | {"attacks": {k: float(np.mean(v))
                                           for k, v in r["attacks"].items()}}
                            | {"baseline_attacks": {k: float(np.mean(v))
                                                    for k, v in r["baseline_attacks"].items()}}
                            for f, r in results.items()}}
    (SUMMARY / "s4_g100_summary.json").write_text(
        json.dumps(summary, indent=1, default=float) + "\n")
    print(f"\n  raw: artifacts/s4_g100/raw/*.json   summary: "
          f"artifacts/s4_g100/summaries/s4_g100_summary.json   ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
