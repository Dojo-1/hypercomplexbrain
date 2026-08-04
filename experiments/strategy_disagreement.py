"""Where do two independent simulation strategies AGREE?

`q_sim_upper` is a minimum over a portfolio.  QSigma-R1a established that the
minimum alone hides which strategy produced it, and that on the ACAF corpus the
answer is always the same one: all 150 cores are bounded by stabilizer rank,
with the other three inactive.  A number produced by exactly one algorithm has
nothing corroborating it, and that is the condition under which both of that
round's defects were possible.

Corroboration is the only check available here.  There is no ground truth to
compare against -- computing the true simulation cost is the problem the metric
exists to approximate -- so the only evidence that a bound is not an artefact of
one algorithm is that a DIFFERENT algorithm, pricing a different structural
property, lands in the same place.  Two strategies agreeing is weak evidence.
One strategy unopposed is none.

This sweep asks whether the agreeing region exists and how large it is.  It
generates cores on a cube that interpolates between the regimes the four
strategies are good at:

    magic_density  fraction of single-qubit slots filled with T   (stabilizer)
    locality       probability a two-qubit gate is nearest-neighbour (contraction)
    matchgate_frac fraction of two-qubit gates that are matchgates (free fermion)

and reports, per core, which strategies are APPLICABLE (finite cost), what each
charges, and the margin between the best and the second best.  A small margin is
a corroborated bound.  A large margin is a bound resting on one algorithm, with
the rest of the portfolio watching.

Run:  PYTHONPATH=src:experiments python3 experiments/strategy_disagreement.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from aionq.residency import simulation_residency


@dataclass
class Core:
    n: int
    depth: int
    magic: float
    locality: float
    matchgate: float
    costs: dict
    reported: float
    winner: str

    @property
    def applicable(self) -> list:
        """Strategies that produced a finite bound below brute force."""
        return sorted(name for name, cost in self.costs.items()
                      if math.isfinite(cost) and cost < float(self.n))

    @property
    def margin(self) -> float:
        """Bits between the best strategy and the runner-up.

        ``inf`` when fewer than two strategies apply: there is no runner-up, so
        there is nothing to compare the winner against.
        """
        finite = sorted(cost for cost in self.costs.values()
                        if math.isfinite(cost) and cost < float(self.n))
        if len(finite) < 2:
            return math.inf
        return finite[1] - finite[0]


def build(rng, n: int, depth: int, magic: float, locality: float,
          matchgate: float) -> QuantumCircuit:
    """One core from the interpolation cube.

    Single-qubit gates are T (magic, and also a Z-rotation so free-fermion
    friendly) or H (no magic, and fatal to the free-fermion path).  Two-qubit
    gates are matchgates or CX, placed nearest-neighbour or long-range.
    """
    circuit = QuantumCircuit(n)
    for _ in range(depth):
        for qubit in range(n):
            if rng.random() < magic:
                circuit.t(qubit)
            else:
                circuit.h(qubit)
        for qubit in range(0, n - 1, 2):
            if rng.random() < locality:
                first, second = qubit, qubit + 1
            else:
                first = int(rng.integers(n))
                second = int(rng.integers(n))
                if first == second:
                    continue
            if rng.random() < matchgate:
                circuit.append(XXPlusYYGate(0.3 + 0.05 * first), [first, second])
            else:
                circuit.cx(first, second)
    return circuit


def sweep(seed: int = 23) -> list:
    rng = np.random.default_rng(seed)
    cores: list[Core] = []
    for n in (6, 8, 10):
        for depth in (2, 4):
            for magic in (0.0, 0.25, 0.5, 1.0):
                for locality in (0.0, 0.5, 1.0):
                    for matchgate in (0.0, 0.5, 1.0):
                        circuit = build(rng, n, depth, magic, locality, matchgate)
                        report = simulation_residency(circuit)
                        cores.append(Core(
                            n=n, depth=depth, magic=magic, locality=locality,
                            matchgate=matchgate, costs=dict(report.strategy_costs),
                            reported=report.log2_sim_cost,
                            winner=report.bounding_strategy))
    return cores


def main() -> int:
    cores = sweep()
    print(f"strategy disagreement sweep: {len(cores)} cores\n")

    counts: dict[int, int] = {}
    for core in cores:
        counts[len(core.applicable)] = counts.get(len(core.applicable), 0) + 1
    print("  applicable strategies per core (below brute force)")
    for how_many in sorted(counts):
        share = 100.0 * counts[how_many] / len(cores)
        print(f"    {how_many} strategy/strategies : {counts[how_many]:4d}  ({share:5.1f}%)")

    winners: dict[str, int] = {}
    for core in cores:
        winners[core.winner] = winners.get(core.winner, 0) + 1
    print("\n  bounding strategy")
    for name, count in sorted(winners.items(), key=lambda kv: -kv[1]):
        print(f"    {name:<20} {count:4d}  ({100.0*count/len(cores):5.1f}%)")

    corroborated = [c for c in cores if len(c.applicable) >= 2]
    print(f"\n  cores with a runner-up at all: {len(corroborated)}/{len(cores)}")
    if corroborated:
        margins = np.array([c.margin for c in corroborated])
        print(f"    margin (bits) between best and second best:")
        print(f"      min {margins.min():.2f}   median {np.median(margins):.2f}"
              f"   max {margins.max():.2f}")
        for threshold in (0.5, 1.0, 2.0):
            tied = int((margins <= threshold).sum())
            print(f"      within {threshold:>3.1f} bits: {tied:4d}"
                  f"  ({100.0*tied/len(cores):5.1f}% of all cores)")

    # Which PAIRS of strategies ever come close?
    pairs: dict[tuple, list] = {}
    for core in cores:
        finite = {name: cost for name, cost in core.costs.items()
                  if math.isfinite(cost) and cost < float(core.n)}
        names = sorted(finite)
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                pairs.setdefault((left, right), []).append(
                    abs(finite[left] - finite[right]))
    if pairs:
        print("\n  closest approach by strategy pair (bits)")
        for pair, deltas in sorted(pairs.items(), key=lambda kv: min(kv[1])):
            array = np.array(deltas)
            print(f"    {pair[0]:<18} vs {pair[1]:<18} n={len(deltas):4d}"
                  f"  min {array.min():6.2f}  median {np.median(array):6.2f}")

    free_fermion_cores = [c for c in cores if "free_fermion" in c.applicable]
    print(f"\n  cores where the free-fermion path applies: "
          f"{len(free_fermion_cores)}/{len(cores)}")
    if free_fermion_cores:
        alone = sum(1 for c in free_fermion_cores if len(c.applicable) == 1)
        print(f"    of those, free-fermion is the ONLY applicable strategy in "
              f"{alone}/{len(free_fermion_cores)}")

    saturated = sum(1 for c in cores if not c.applicable)
    print(f"\n  saturated (no strategy beat dense): {saturated}/{len(cores)}"
          f"  ({100.0*saturated/len(cores):.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
