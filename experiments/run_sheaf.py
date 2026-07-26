"""Round S3: Sigma-infinity section 16 experiment 1, plus the QSigma query claim.

The thesis pre-registers this experiment verbatim, and it is the first one it
lists:

    Construct a synthetic multi-world task with known local sections, overlap
    inconsistencies, and hidden cycle obstructions.  Compare scalar, graph,
    sheaf, quaternionic, octonionic, and randomized coordinate systems on
    obstruction localization, not only task reward.

    Prediction: the sheaf and relation-mesh instruments should localize gluing
    failures more reliably; hypercomplex coordinates may improve diagnosis only
    on explicitly order-sensitive or null-channel cases.

    Kill condition: any advantage disappears under dimension- and
    compute-matched controls.

Four parts, in the order the evidence forces:

  1  GENERIC regime.  Transitions Haar in O(4).  Every instrument gets the same
     nerve, the same cycle basis and the same attribution rule, so a difference
     is attributable to the coordinate system and nothing else.
  2  COMMUTATOR regime.  Transitions in Q_8, defect = multiplication by -1, an
     element of the commutator subgroup.  This is the thesis's "explicitly
     order-sensitive" case, and the abelian instruments are blind to it as a
     matter of algebra rather than of sample size.
  3  FLATNESS LADDER.  Whether a vertex gauge induces a flat connection at all,
     per Cayley-Dickson dimension.  This decides whether the octonionic clause of
     the prediction is even well posed.
  4  QUERY COMPLEXITY.  The QSigma proposal's own first experiment: can quantum
     interference read a hidden cycle obstruction in fewer oracle queries than
     matched classical baselines?

Run with:  PYTHONPATH=src python3 experiments/run_sheaf.py
"""

from __future__ import annotations

import sys
import time

import numpy as np

sys.path.insert(0, "src")

from aionq.interference import (bv_success_rate, classical_query_cost,
                                crossover_noise, expected_quantum_queries,
                                minimum_weight_representative, obstruction_class,
                                oracle_construction_cost, query_report)
from aionq.sheaf import (INSTRUMENTS, Nerve, auroc, flatness_ladder, localise,
                         make_obstructed_sheaf, ring_of_worldlets)
from aionq.statistics import compare_groups, summarize

TRIALS = 300
N_WORLDLETS, N_EDGES, N_DEFECTS = 8, 13, 2
ORDER = ["graph", "scalar", "character", "shuffled", "quaternion", "octonion",
         "associator", "sheaf"]


def _random_nerve(rng, n=N_WORLDLETS, m=N_EDGES) -> Nerve:
    """A connected nerve: a random spanning tree plus random extra overlaps."""
    perm = rng.permutation(n)
    edges = {tuple(sorted((int(perm[k]), int(perm[rng.integers(0, k)]))))
             for k in range(1, n)}
    pool = [(i, j) for i in range(n) for j in range(i + 1, n)
            if (i, j) not in edges]
    rng.shuffle(pool)
    for e in pool[:max(0, m - len(edges))]:
        edges.add(e)
    return Nerve(n, tuple(sorted(edges)))


def _precision_at_k(scores, labels, k) -> float:
    top = np.argsort(-np.asarray(scores, dtype=float))[:k]
    return float(np.asarray(labels, dtype=bool)[top].sum()) / max(1, k)


def _regime(title: str, kind: str, dim: int, seed: int, note: str = "") -> dict:
    rng = np.random.default_rng(seed)
    aur = {name: [] for name in ORDER}
    prec = {name: [] for name in ORDER}
    cost = {name: 0.0 for name in ORDER}

    for _ in range(TRIALS):
        nerve = _random_nerve(rng)
        defects = rng.choice(nerve.n_edges, size=N_DEFECTS, replace=False)
        sheaf = make_obstructed_sheaf(nerve, defects, rng, kind=kind, dim=dim)
        labels = np.zeros(nerve.n_edges, dtype=bool)
        labels[defects] = True
        cycles = nerve.cycle_basis()
        for name in ORDER:
            t0 = time.perf_counter()
            s = localise(sheaf, name, rng, cycles=cycles)
            cost[name] += time.perf_counter() - t0
            aur[name].append(auroc(s, labels))
            prec[name].append(_precision_at_k(s, labels, N_DEFECTS))

    print(f"\n  {title}")
    if note:
        print(f"  {note}")
    print("  " + "-" * 82)
    print(f"    {'instrument':<14}{'AUROC (95% CI)':>30}{'precision@2':>16}"
          f"{'compute':>14}")
    print("  " + "-" * 82)
    base = cost["sheaf"] or 1.0
    for name in ORDER:
        m = summarize(name, aur[name], seed=seed)
        p = float(np.mean(prec[name]))
        print(f"    {name:<14}{m.value:>10.3f} [{m.ci[0]:.3f}, {m.ci[1]:.3f}]"
              f"{p:>22.3f}{cost[name] / base:>12.2f}x")
    return {"auroc": aur, "precision": prec, "cost": cost}


def part_1_and_2():
    print("=" * 84)
    print("PARTS 1-2 -- obstruction localisation across coordinate systems")
    print("=" * 84)
    print(f"  {TRIALS} trials, {N_WORLDLETS} worldlets, {N_EDGES} overlaps, "
          f"{N_DEFECTS} hidden defects, fiber dimension 4 throughout")
    print("  Every instrument receives the same nerve, the same cycle basis and the")
    print("  same blame-spreading rule.  Only the coordinate system differs.")

    generic = _regime(
        "REGIME 1 (generic): transitions Haar-orthogonal in O(4)",
        kind="generic", dim=4, seed=101,
        note="the defect replaces one transition with another from the same "
             "distribution,\n  so no overlap is locally anomalous")
    commutator = _regime(
        "REGIME 2 (order-sensitive): transitions in Q_8, defect = -1 in [Q_8, Q_8]",
        kind="commutator", dim=4, seed=202,
        note="the injected element lies in the commutator subgroup, so it is "
             "invisible\n  to every abelian coordinate as a matter of algebra")

    print("\n" + "-" * 84)
    print("  Effect sizes against the dimension- and compute-matched controls")
    print("-" * 84)
    for label, res in (("generic", generic), ("commutator", commutator)):
        for rival in ("shuffled", "graph", "quaternion"):
            eff = compare_groups(f"{label}: sheaf - {rival}",
                                 res["auroc"]["sheaf"], res["auroc"][rival],
                                 resamples=4000, seed=7)
            print(f"    {eff}")
    return generic, commutator


def part_3():
    print("\n" + "=" * 84)
    print("PART 3 -- does a vertex gauge induce a FLAT connection?")
    print("=" * 84)
    print("  Clean sheaves only: a_ij = g_j g_i^-1 from random unit elements, NO")
    print("  defect anywhere.  Any holonomy that remains is the algebra's, not the")
    print("  data's.  This decides whether the octonionic clause is well posed.")
    nerve = ring_of_worldlets(6, chords=((0, 3), (1, 4)))
    ladder = flatness_ladder(nerve, dims=(1, 2, 4, 8, 16), samples=120,
                             rng=np.random.default_rng(303))
    print(f"\n    {'algebra':<14}{'dim':>5}{'mean ||H - I||_F':>22}{'max':>12}")
    print("  " + "-" * 60)
    names = {1: "real", 2: "complex", 4: "quaternion", 8: "octonion",
             16: "sedenion"}
    for d, (mean, mx) in ladder.items():
        print(f"    {names[d]:<14}{d:>5}{mean:>22.6f}{mx:>12.6f}")
    return ladder


def part_4():
    print("\n" + "=" * 84)
    print("PART 4 -- quantum interference vs classical queries on the same class")
    print("=" * 84)
    print("  The QSigma proposal's own first experiment, run as specified.")

    proposed = ring_of_worldlets(4, chords=((0, 2),))
    rep = query_report(proposed)
    print(f"\n  The proposed instance -- four worldlets, two overlap cycles:")
    print(f"    {rep}")
    cls = obstruction_class(proposed, [1])
    print(f"    obstruction class of a defect on overlap 1: {cls.tolist()}")
    print(f"    lightest cochain with that class: "
          f"{minimum_weight_representative(proposed, cls).tolist()}")

    print(f"\n  Scaling: classical cost is the cycle rank b, quantum cost is 1.")
    print(f"    {'V':>4}{'E':>5}{'b':>4}{'classical':>12}{'quantum':>10}"
          f"{'ratio':>9}{'with oracle build':>20}")
    print("  " + "-" * 66)
    for n_ring, chords in ((4, ((0, 2),)), (6, ((0, 3), (1, 4))),
                           (8, ((0, 4), (1, 5), (2, 6))),
                           (12, tuple((i, i + 6) for i in range(6)))):
        nerve = ring_of_worldlets(n_ring, chords=chords)
        r = query_report(nerve)
        print(f"    {r.n_worldlets:>4}{r.n_edges:>5}{r.betti_1:>4}"
              f"{r.classical_queries:>12}{r.quantum_queries:>10}"
              f"{r.query_ratio:>8.1f}x{r.honest_ratio:>19.2f}x")

    print("\n  Noise: one coherent query is worth b classical queries only while")
    print("  it succeeds.  Depolarizing rate p on every qubit after every layer.")
    rng = np.random.default_rng(404)
    grid = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20)
    fine = np.arange(0.0, 0.301, 0.005)
    print(f"\n    {'b':>4}" + "".join(f"{f'p={p}':>11}" for p in grid)
          + f"{'crossover':>12}")
    print("  " + "-" * 84)
    crossovers = {}
    for b in (2, 4, 6, 8, 12):
        row = f"    {b:>4}"
        for p in grid:
            row += f"{bv_success_rate(b, p, 400, rng):>11.3f}"
        xo = crossover_noise(b, grid=fine, trials=500, rng=rng)
        crossovers[b] = xo
        print(row + f"{xo:>12.3f}")
    print("\n    crossover = smallest p where the expected coherent cost 1/p_success")
    print("    first exceeds the b queries the classical learner simply pays.")
    return crossovers


def main() -> int:
    print("Round S3 -- sheaf obstruction localisation, and the QSigma query claim")
    generic, commutator = part_1_and_2()
    ladder = part_3()
    crossovers = part_4()

    print("\n" + "=" * 84)
    print("VERDICT against the pre-registered kill conditions")
    print("=" * 84)

    g, c = generic["auroc"], commutator["auroc"]
    sheaf_vs_shuffled = compare_groups("x", g["sheaf"], g["shuffled"], seed=7)
    sheaf_vs_graph = compare_groups("x", g["sheaf"], g["graph"], seed=7)
    quat_generic = compare_groups("x", g["quaternion"], g["sheaf"], seed=7)
    quat_commut = compare_groups("x", c["quaternion"], c["sheaf"], seed=7)
    char_commut = summarize("x", c["character"], seed=7)

    print("\n  (a) Does sheaf structure localise better than matched controls?")
    if sheaf_vs_shuffled.significant and sheaf_vs_shuffled.difference > 0 \
            and sheaf_vs_graph.significant and sheaf_vs_graph.difference > 0:
        print("      YES. The sheaf instrument beats both the shuffled-overlap control")
        print("      and the topology-only control at equal dimension and equal")
        print(f"      attribution: +{sheaf_vs_shuffled.difference:.3f} over shuffled, "
              f"+{sheaf_vs_graph.difference:.3f} over graph.")
        print("      The thesis's kill condition for the sheaf clause is NOT met.")
    else:
        print("      NO. The advantage does not survive the matched controls.")
        print("      KILL CONDITION MET for the sheaf clause.")

    print("\n  (b) Do hypercomplex coordinates help, and only where predicted?")
    print(f"      generic regime:    quaternion - sheaf = {quat_generic.difference:+.3f} "
          f"[{quat_generic.ci[0]:+.3f}, {quat_generic.ci[1]:+.3f}]")
    print(f"      order-sensitive:   quaternion - sheaf = {quat_commut.difference:+.3f} "
          f"[{quat_commut.ci[0]:+.3f}, {quat_commut.ci[1]:+.3f}]")
    if quat_generic.difference < 0 and quat_generic.significant \
            and not quat_commut.significant:
        print("      The PREDICTED PATTERN holds in shape: quaternionic coordinates")
        print("      lose on generic transitions -- projection to H discards two of")
        print("      O(4)'s six parameters -- and match exactly on their home ground.")
        print("      But 'match' is not 'improve'. The thesis says hypercomplex")
        print("      coordinates 'may improve diagnosis' on order-sensitive cases.")
        print("      They do not improve anything here: they tie. Under the stated")
        print("      kill condition -- advantage vanishes under matched controls --")
        print("      the hypercomplex clause is KILLED, and what survives is the")
        print("      weaker true statement that they cost nothing on their own ground.")
    else:
        print("      The predicted conditional pattern does NOT reproduce.")

    print("\n  (c) Is the abelian instrument blind where the algebra says it must be?")
    print(f"      character AUROC in the order-sensitive regime: {char_commut.value:.3f} "
          f"[{char_commut.ci[0]:.3f}, {char_commut.ci[1]:.3f}]")
    print("      Chance is 0.500 and the interval brackets it. This is not a")
    print("      measurement result: det is a homomorphism into an abelian group and")
    print("      every L_q lies in SO(4), so det(H) = 1 identically. The experiment")
    print("      confirms an algebraic fact rather than discovering one.")

    print("\n  (d) Is the octonionic clause well posed?")
    print(f"      clean-sheaf holonomy: dim 4 -> {ladder[4][0]:.6f}, "
          f"dim 8 -> {ladder[8][0]:.6f}, dim 16 -> {ladder[16][0]:.6f}")
    print("      NO. Above the quaternions a vertex gauge no longer induces a flat")
    print("      connection, because L_a L_b != L_{ab}. The clean sheaf already")
    print("      carries holonomy on every cycle, so there is no zero for a defect")
    print("      to stand out against. Unit octonions are a Moufang loop, not a")
    print("      group, and sheaf cohomology needs a group. The octonionic clause")
    print("      is not falsified -- it is ILL-POSED, which is a stronger objection.")

    print("\n  (e) Does quantum interference read the obstruction in fewer queries?")
    print("      YES in the oracle model, and it is proved rather than measured:")
    print("      b classical queries against 1, because holonomy is linear and the")
    print("      class carries exactly b bits. Three things bound what that means.")
    print("        1. The proposed instance -- 4 worldlets, 2 cycles -- gives b = 2.")
    print("           A factor of two, with no room for an interval. Underpowered by")
    print("           construction; the separation needs cycle rank to grow.")
    print("        2. Building the coherent oracle from classical worldlet data costs")
    print("           E accesses, which exceeds the b queries saved on every instance")
    print("           tested. Outside the oracle model the advantage is negative.")
    print("        3. Recovering the CLASS is not localising the DEFECT. The lightest")
    print("           cochain in the coset is a syndrome-decoding problem, NP-hard in")
    print("           general, and identical for both parties afterwards.")
    print("      Under noise the advantage is bounded but not fragile. Crossover")
    print("      depolarizing rate: "
          + ", ".join(f"b={b}: {p:.3f}" for b, p in crossovers.items()) + ".")
    small = [p for b, p in crossovers.items() if b <= 6]
    large = [p for b, p in crossovers.items() if b >= 8]
    if large and small and max(large) < min(small):
        print("      It is roughly flat to b = 6 and then falls, which is what the")
        print("      arithmetic requires: 1/p_success grows exponentially in b while")
        print("      the classical cost grows only linearly, so tolerable noise must")
        print("      decay like log(b)/b. The advantage is asymptotically fragile even")
        print("      though it looks comfortable at the sizes actually simulated --")
        print("      and the sizes actually simulated are the ones a proposal is most")
        print("      likely to quote.")
    else:
        print("      The trend across b is not clean at these sizes and no scaling")
        print("      claim is made from it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
