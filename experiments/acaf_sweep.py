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

from aionq.residency import simulation_residency


@dataclass
class Sample:
    n: int
    t_density: float
    depth: int
    q_naive: float
    q_cert: float
    raw: float = 0.0

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
        r = simulation_residency(qc)
        samples.append(Sample(n, td, d, r.q_naive, r.q_sim_upper, r.raw_exponent))

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

    # K2 must inspect the RAW exponent, before clipping.  The previous version
    # tested the clipped value against the bounds the clip itself enforces --
    # a tautology that could never fire.
    raws = np.array([s.raw for s in samples])
    k2_fail = bool(np.any(~np.isfinite(raws)) or np.any(raws < -1e-9))
    print("\n  kill conditions")
    print(f"    K1 (correction does no work)   : {'FAILED' if k1_fail else 'survived'}"
          f"   mean gap {gaps.mean():.4f}")
    print(f"    K2 (raw exponent unsound)      : {'FAILED' if k2_fail else 'survived'}"
          f"   raw range [{np.nanmin(raws):.3f}, {np.nanmax(raws):.3f}] (pre-clip)")

    k3_fail = _equivalence_attacks()
    k4_fail = _structure_families()

    zero_cert = sum(1 for s in samples if s.q_cert < 1e-9)
    print(f"\n  {zero_cert}/{len(samples)} cores scored Q_naive = 1.00 but q_sim_upper = 0.00")
    print("  (fully stabilizer-simulable cores wearing full quantum notation)")
    print("\n  NOTE: this generator emits only H/S/T/CX and no measurements, resets")
    print("  or classical control. Q_naive = 1 is therefore largely guaranteed by")
    print("  the generator rather than discovered by it. The honest claim is that")
    print("  Q_naive is constant on all-unitary cores.")
    print("  Its T-density is also low enough that stabilizer rank is always the")
    print("  cheapest strategy, so the contraction strategy changes 0 of these 150")
    print("  cores. Low-treewidth families are exercised by K4 above, not here.")

    return 1 if (k1_fail or k2_fail or k3_fail or k4_fail) else 0


def _structure_families() -> bool:
    """K4: cores whose magic is real but whose connectivity is not.

    The random generator above cannot reach this regime.  Its T-density is low,
    so stabilizer rank is always the cheapest strategy and the structural one
    never fires -- measured, the contraction strategy changes 0 of its 150
    cores.  That is not evidence the strategy is idle; it is evidence the
    generator emits no low-treewidth families, which its own note already says.

    These families are the QSigma-R1a gate's "low-treewidth" case made
    explicit: high magic, low connectivity.  Each row reports what the metric
    charges with and without the contraction strategy, so the difference is
    visible rather than folded into one number.  A row FAILS when a core that
    is provably easy still scores as though no strategy could simulate it.
    """
    from aionq import contraction

    def disconnected_blocks(n: int) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        for base in range(0, n, 2):
            qc.h(base); qc.cx(base, base + 1)
            qc.t(base); qc.t(base + 1)
            qc.cx(base, base + 1); qc.h(base)
        return qc

    def single_qubit_chains(n: int) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        qc.h(range(n))
        for _ in range(7):
            qc.t(range(n)); qc.h(range(n))
        return qc

    def shallow_local_magic(n: int) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        for _ in range(2):
            qc.h(range(n)); qc.t(range(n))
            for q in range(0, n - 1, 2):
                qc.cx(q, q + 1)
        return qc

    def all_to_all_magic(n: int) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        for _ in range(3):
            qc.h(range(n)); qc.t(range(n))
            for a in range(n):
                for b in range(a + 1, n):
                    qc.cx(a, b)
        return qc

    families = [
        ("k disconnected 2-qubit blocks", disconnected_blocks, True),
        ("product of single-qubit chains", single_qubit_chains, True),
        ("shallow 1D local, full T-density", shallow_local_magic, True),
        ("all-to-all magic (control: hard)", all_to_all_magic, False),
    ]

    real_plan = contraction.contraction_plan
    print("\n  K4 structure families (magic that is not connected to anything)")
    print(f"    {'family':<34}{'n':>4}{'width':>7}{'2-strat':>10}{'3-strat':>10}  verdict")
    failed = False
    for name, build, should_be_easy in families:
        n = 12
        qc = build(n)
        contraction.contraction_plan = lambda c: contraction.ContractionPlan(
            valid=False, reason="disabled to measure the two-strategy baseline")
        try:
            before = simulation_residency(qc).q_sim_upper
        finally:
            contraction.contraction_plan = real_plan
        after = simulation_residency(qc).q_sim_upper
        width = real_plan(qc).width
        # An easy family must end up materially cheaper than dense; a hard
        # control must NOT be made cheap by a strategy that cannot help it.
        bad = (should_be_easy and after > 0.35) or (not should_be_easy and after < before - 1e-12)
        failed = failed or bad
        print(f"    {name:<34}{n:>4}{width:>7}{before:>10.4f}{after:>10.4f}"
              f"  {'FAILED' if bad else 'ok'}")
    return failed


def _equivalence_attacks() -> bool:
    """Circuits that are the identity but may be scored as quantum.

    A syntactic audit cannot see cancellation.  The compiler portfolio catches
    the cases some optimiser in the portfolio can see; this is not a solution to
    circuit equivalence, which is intractable in general.  Any surviving row is
    a live gaming vector and is reported as such.
    """
    from qiskit.quantum_info import Operator

    attacks: list[tuple[str, QuantumCircuit]] = []

    a1 = QuantumCircuit(1)
    a1.h(0); a1.t(0); a1.tdg(0); a1.h(0)
    attacks.append(("H T Tdg H", a1))

    a2 = QuantumCircuit(2)
    a2.h(0); a2.cx(0, 1)
    for _ in range(4):
        a2.t(1); a2.tdg(1)
    a2.cx(0, 1); a2.h(0)
    attacks.append(("entangle, 4 cancelling T pairs, disentangle", a2))

    a3 = QuantumCircuit(3)
    a3.h(range(3)); a3.ccx(0, 1, 2); a3.ccx(0, 1, 2); a3.h(range(3))
    attacks.append(("H CCX CCX H", a3))

    print("\n  K3 equivalence attacks (identity circuits scored as quantum?)")
    failed = False
    for name, qc in attacks:
        is_identity = np.allclose(Operator(qc).data,
                                  np.eye(2 ** qc.num_qubits), atol=1e-9)
        score = simulation_residency(qc).q_sim_upper
        bad = is_identity and score > 1e-9
        failed = failed or bad
        print(f"    {name:<44} identity={is_identity}  q_sim_upper={score:.4f}"
              f"  {'GAMED' if bad else 'ok'}")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
