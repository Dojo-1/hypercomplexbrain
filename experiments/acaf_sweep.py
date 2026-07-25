"""ACAF sweep: fuzz the residency metric across the architecture's parameter space.

Actor-Critic-Ambigator-Fuzzer discipline.  The Ambigator generates random
cognitive cores across (n_qubits, t_density, clifford_depth, coherentization);
the Fuzzer runs the residency audit on each; the Critic reports the distribution
of the gap between the draft metric and the certified one.

The purpose is falsification, not confirmation.  Two kill conditions are checked:

  K1  If Q_naive and Q_cert agree across the sweep, the correction is not
      doing work and should be dropped.
  K2  If Q_cert ever exceeds the number of qubits' worth of simulation cost,
      the metric is unsound.

Run with:  PYTHONPATH=src python3 experiments/acaf_sweep.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit

sys.path.insert(0, "src")

from aionq.residency import certified_residency


@dataclass
class Sample:
    n: int
    t_density: float
    depth: int
    q_naive: float
    q_cert: float

    @property
    def gap(self) -> float:
        return self.q_naive - self.q_cert


class Ambigator:
    """Generates random cognitive cores spanning the architecture's regimes."""

    def __init__(self, n_values, t_densities, depths, seed: int = 0):
        self.n_values = list(n_values)
        self.t_densities = list(t_densities)
        self.depths = list(depths)
        self.rng = np.random.default_rng(seed)

    def core(self, n: int, t_density: float, depth: int) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        n_t = 0
        for _ in range(depth):
            for q in range(n):
                roll = self.rng.random()
                if roll < t_density:
                    qc.t(q)
                    n_t += 1
                elif roll < t_density + 0.35:
                    qc.h(q)
                else:
                    qc.s(q)
            for q in range(0, n - 1, 2):
                qc.cx(q, q + 1)
            for q in range(1, n - 1, 2):
                qc.cx(q, q + 1)
        return qc

    def sweep(self, samples_per_config: int = 2):
        for n in self.n_values:
            for td in self.t_densities:
                for d in self.depths:
                    for _ in range(samples_per_config):
                        yield n, td, d, self.core(n, td, d)


def main() -> int:
    amb = Ambigator(
        n_values=[4, 6, 8, 10, 12],
        t_densities=[0.0, 0.02, 0.05, 0.1, 0.25],
        depths=[2, 4, 8],
        seed=17,
    )

    samples: list[Sample] = []
    for n, td, d, qc in amb.sweep(samples_per_config=2):
        r = certified_residency(qc)
        samples.append(Sample(n, td, d, r.q_naive, r.q_cert))

    gaps = np.array([s.gap for s in samples])
    certs = np.array([s.q_cert for s in samples])
    naives = np.array([s.q_naive for s in samples])

    print(f"ACAF sweep: {len(samples)} random cognitive cores\n")
    print(f"  Q_naive : mean {naives.mean():.4f}  min {naives.min():.4f}  max {naives.max():.4f}")
    print(f"  Q_cert  : mean {certs.mean():.4f}  min {certs.min():.4f}  max {certs.max():.4f}")
    print(f"  gap     : mean {gaps.mean():.4f}  min {gaps.min():.4f}  max {gaps.max():.4f}")

    print("\n  Q_cert by T-density (mean over n and depth):")
    for td in amb.t_densities:
        sel = [s.q_cert for s in samples if s.t_density == td]
        print(f"    t_density {td:<6.2f} -> Q_cert {np.mean(sel):.4f}")

    print("\n  Q_cert by width at t_density=0.05 (the saturation frontier):")
    for n in amb.n_values:
        sel = [s.q_cert for s in samples if s.n == n and s.t_density == 0.05]
        if sel:
            print(f"    n = {n:<3d} -> Q_cert {np.mean(sel):.4f}")

    k1_fail = bool(np.allclose(gaps, 0.0, atol=1e-6))
    k2_fail = bool(np.any(certs > 1.0 + 1e-9) or np.any(certs < -1e-9))

    print("\n  kill conditions")
    print(f"    K1 (correction does no work)  : {'FAILED' if k1_fail else 'survived'}"
          f"   mean gap {gaps.mean():.4f}")
    print(f"    K2 (metric out of bounds)     : {'FAILED' if k2_fail else 'survived'}")

    zero_cert = sum(1 for s in samples if s.q_cert < 1e-9)
    print(f"\n  {zero_cert}/{len(samples)} cores scored Q_naive = 1.00 but Q_cert = 0.00")
    print("  (fully stabilizer-simulable cores wearing full quantum notation)")

    return 1 if (k1_fail or k2_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())
