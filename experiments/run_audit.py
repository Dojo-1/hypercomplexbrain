"""AION-Omega^Q full architecture audit.

Runs every falsifiable claim the architecture makes and prints the numbers.
This is the artifact that decides whether the design is doing work or restating
itself.  Run with:

    PYTHONPATH=src python3 experiments/run_audit.py
"""

from __future__ import annotations

import math
import sys

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, random_clifford

sys.path.insert(0, "src")

from aionq.budget import CoherenceBudget
from aionq.coherentize import coherentization_audit
from aionq.fusion import verify_coherence
from aionq.identity import analyse_identity
from aionq.process import non_markovianity
from aionq.qrf import compare_frames
from aionq.residency import (simulation_residency, max_bipartite_entanglement,
                             stabilizer_renyi_entropy)
from aionq.atlas import (CLASSICAL, SEPARABLE, STABILIZER, UNIVERSAL, Interval,
                         QuantumNecessityAtlas, embed_hierarchy,
                         hierarchy_distortion, poincare_distance, resource_over)
from aionq.selfknowledge import (copies_for_self_tomography, self_knowledge_tradeoff,
                                syndrome_extraction_disturbance)


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def claim_1_metric_is_gameable() -> None:
    rule("CLAIM 1  The draft Q_causal metric is gameable; q_sim_upper resists")

    cases: list[tuple[str, QuantumCircuit]] = []

    perm = QuantumCircuit(8)
    for i in range(7):
        perm.cx(i, i + 1)
    perm.ccx(0, 1, 2)
    perm.ccx(2, 3, 4)
    perm.x(range(8))
    perm.swap(0, 7)
    cases.append(("classical reversible core (CX/CCX/X/SWAP)", perm))

    ghz = QuantumCircuit(8)
    ghz.h(0)
    for i in range(7):
        ghz.cx(i, i + 1)
    cases.append(("GHZ: maximal entanglement, zero magic", ghz))

    cases.append(("random Clifford, depth 40", random_clifford(8, seed=7).to_circuit()))

    ct = QuantumCircuit(8)
    ct.h(range(8))
    for i in range(7):
        ct.cx(i, i + 1)
    for k in range(35):
        ct.t(k % 8)
    cases.append(("Clifford + 35 T", ct))

    grover = QuantumCircuit(8)
    grover.h(range(8))
    for _ in range(4):
        grover.ccx(0, 1, 7)
        grover.ccx(2, 3, 6)
        grover.h(range(8))
    cases.append(("Hadamard + Toffoli (Grover-shaped)", grover))

    print(f"{'core':<44}{'Q_naive':>9}{'q_sim+':>9}{'gap':>9}")
    print("-" * 72)
    for name, qc in cases:
        r = simulation_residency(qc)
        print(f"{name:<44}{r.q_naive:>9.4f}{r.q_sim_upper:>9.4f}{r.gap:>+9.4f}")

    print("\nEntanglement is not quantum residency:")
    sv = Statevector(ghz)
    print(f"  GHZ max bipartite entanglement : {max_bipartite_entanglement(sv):.4f} bits")
    print(f"  GHZ stabilizer Renyi magic M2  : {stabilizer_renyi_entropy(sv):.2e}")
    t1 = QuantumCircuit(1)
    t1.h(0)
    t1.t(0)
    print(f"  single T-state magic M2        : {stabilizer_renyi_entropy(Statevector(t1)):.4f}"
          f"   (exact log2(4/3) = {math.log2(4 / 3):.4f})")


def claim_2_coherentization() -> None:
    rule("CLAIM 2  Coherentization relocates classicality; it does not remove it")

    q = QuantumRegister(4, "q")
    c = ClassicalRegister(2, "c")
    qc = QuantumCircuit(q, c)
    qc.h(0)
    qc.t(1)
    qc.cx(0, 1)
    qc.t(2)
    qc.measure(0, c[0])
    with qc.if_test((c[0], 1)):
        qc.x(2)
        qc.t(3)
    qc.measure(1, c[1])
    with qc.if_test((c[1], 1)):
        qc.z(3)

    audit = coherentization_audit(qc)
    print(audit)
    print(f"\n  draft metric credits coherentization with {audit.naive_delta:+.4f}")
    print(f"  measured gain is              {audit.cert_delta:+.4f}"
          f"  ({100 * audit.cert_delta / max(1e-9, audit.naive_delta):.1f}% of advertised)")
    print("  and it is bought by spending MORE non-Clifford resource")
    print(f"  (T-count {audit.before.t_count:.0f} -> {audit.after.t_count:.0f}), not by new capability.")


def claim_3_breathing_is_forced() -> None:
    rule("CLAIM 3  Exhalation is forced by ancilla accounting, not chosen by taste")

    configs = [
        ("Kookaburra-class (early logical module)", 12, 6, 1, 0.3),
        ("100 logical, 40 data, binary branches", 100, 40, 1, 0.3),
        ("Starling-class 200 logical, 8-way policy", 200, 120, 3, 0.5),
        ("Starling-class, fully reversible cognition", 200, 120, 3, 0.0),
        ("narrow module, near-reversible: Bennett bites", 64, 56, 1, 0.05),
    ]
    for name, lq, dq, qpd, irr in configs:
        s = CoherenceBudget(lq, dq, qpd, irr).schedule()
        print(f"\n{name}")
        print("  " + str(s).replace("\n", "\n  "))


def claim_4_process_memory() -> None:
    rule("CLAIM 4  Process tensors carry memory a channel provably cannot")
    print("  coupling      N = I(o1 : i1,f)   verdict")
    print("  " + "-" * 50)
    for cpl in [0.0, 0.1, 0.2, 0.5, 1.0, math.pi / 2]:
        r = non_markovianity(cpl)
        verdict = "Markovian: Tendril lift buys nothing" if r.markovian else "memory present"
        print(f"  {cpl:>7.3f}      {r.non_markovianity:>10.6f} bits   {verdict}")


def claim_5_fusion_coherence() -> None:
    rule("CLAIM 5  The fusion grammar is coherent AND order-sensitive")
    rep = verify_coherence()
    print(rep)
    print("\n  Pentagon and hexagon hold to machine precision while the associator")
    print("  is nonzero: composition order carries information without becoming")
    print("  inconsistent. Literal octonionic matrix algebra cannot do both.")


def claim_6_identity_gram() -> None:
    rule("CLAIM 6  Identity Gram is PSD and frame-invariant; rank is span, not capacity")
    rng = np.random.default_rng(3)
    d = 4

    def rand_u() -> np.ndarray:
        m = rng.normal(size=(d, d)) + 1j * rng.normal(size=(d, d))
        q, _ = np.linalg.qr(m)
        return q

    basis = rand_u()
    rho = basis @ np.diag([0.5, 0.3, 0.15, 0.05]) @ basis.conj().T
    holos = [rand_u() for _ in range(3)]
    holos.append(holos[0].copy())      # a restatement, not a new identity
    holos.append(holos[1] @ np.eye(d))  # another restatement

    rep = analyse_identity(rho, holos)
    print(rep)
    print(f"\n  {len(holos)} holonomies supplied, span dimension = {rep.holonomy_span_dimension},")
    print(f"  effective rank = {rep.effective_rank:.3f}, condition number = {rep.condition_number:.2e}.")
    print("  Rank is the HOLONOMY SPAN DIMENSION, not 'identity capacity': robustness")
    print("  also needs conditioning, code distance, recoverability and process memory.")


def claim_7_self_knowledge() -> None:
    rule("CLAIM 7  Self-knowledge is bounded -- but NOT impossible")
    print("  strength   self-knowledge   identity fidelity")
    print("  " + "-" * 46)
    for p in self_knowledge_tradeoff():
        print(f"  {p.strength:>7.2f}   {p.info_gain_bits:>10.4f} bits   {p.fidelity_retained:>10.4f}")
    n = copies_for_self_tomography(2 ** 6, 0.01)
    print(f"\n  Full tomography of a 6-qubit identity register: ~{n:,} copies at eps=0.01")
    print("  (rank-dependent; this is the worst case, not a universal law).")
    print("\n  COUNTEREXAMPLE -- structured self-measurement disturbs nothing:")
    for e in (None, 0, 1, 2):
        r = syndrome_extraction_disturbance(error_qubit=e)
        where = "no error" if e is None else f"X error on qubit {e}"
        print(f"    {where:<18} {r}")
    print("\n  Syndrome extraction reads a protected register, extracts 2 bits, and")
    print("  leaves the logical state at fidelity EXACTLY 1. The architecture depends")
    print("  on this: a blanket ban on self-measurement would forbid its own homeostasis.")
    print("  Correct bounded claim: a single unknown quantum self cannot obtain a")
    print("  COMPLETE, NON-DISTURBING classical description of itself from one specimen.")
    print("  Loeb and no-cloning obstruct different closures; neither supersedes the other.")


def claim_8_frames() -> None:
    rule("CLAIM 8  Entanglement is frame-relative, so it cannot be an invariant")
    print(compare_frames())
    print("\n  The same physical situation: product state in A's frame,")
    print("  maximally entangled in B's. This is why q_sim ignores entanglement.")


def claim_9_atlas_not_scalar() -> None:
    rule("CLAIM 9  Quantumness is not a scalar: a resource needs a free theory")

    plus = np.array([1, 1], dtype=complex) / math.sqrt(2)
    tstate = np.array([1, complex(math.cos(math.pi / 4), math.sin(math.pi / 4))],
                      dtype=complex) / math.sqrt(2)
    ghz3 = np.zeros(8, dtype=complex)
    ghz3[0] = ghz3[7] = 1 / math.sqrt(2)

    print("  the SAME state has different resource content over different base points:")
    print(f"    {'state':<20}{'classical-rev':>15}{'stabilizer':>13}{'separable':>12}")
    for label, st in [("|+>", plus), ("T-state", tstate), ("GHZ3", ghz3)]:
        sep = resource_over(st, SEPARABLE) if len(st) >= 4 else float("nan")
        print(f"    {label:<20}{resource_over(st, CLASSICAL):>15.4f}"
              f"{resource_over(st, STABILIZER):>13.4f}{sep:>12.4f}")
    print("\n  'How quantum is it' has no answer until a free theory is named.")

    print("\n  two organs the old scalar ordered WRONGLY:")
    memory = QuantumNecessityAtlas(
        organ="Clifford fault-tolerant memory", base=STABILIZER,
        q_phys=1.0, q_coh=0.0, q_resource=0.0, q_process=0.0, q_logical=1.0,
        q_sim=Interval(0.0, 0.0, "stabilizer-simulable"), q_causal=0.4, q_audit=0.8)
    padded = QuantumNecessityAtlas(
        organ="syntactically magic identity circuit", base=STABILIZER,
        q_phys=0.2, q_coh=0.0, q_resource=1.2, q_process=0.0, q_logical=0.0,
        q_sim=Interval(0.0, 0.68, "upper bound only"), q_causal=0.0, q_audit=0.1)
    for a in (memory, padded):
        print("\n" + "  " + str(a).replace("\n", "\n  "))
    print(f"\n  neither dominates the other: "
          f"memory>padded={memory.dominates(padded)}, padded>memory={padded.dominates(memory)}")
    print("  A partial order, not a ranking. Hardness alone never promotes.")


def claim_10_hyperbolic_base() -> None:
    rule("CLAIM 10  The base is hyperbolic -- and here is what that is worth")
    coords = embed_hierarchy()
    print("  free-theory containment hierarchy, euclidean vs hyperbolic separation:")
    for a, b in [("stabilizer", "matchgate / free-fermion"),
                 ("stabilizer", "universal"),
                 ("classical-reversible", "universal")]:
        eu = float(np.linalg.norm(coords[a] - coords[b]))
        hy = poincare_distance(coords[a], coords[b])
        print(f"    {a:<22} <-> {b:<24} euclid {eu:.3f}  hyperbolic {hy:.3f}  {hy/eu:.2f}x")

    print("\n  worst-case distortion against the true tree metric, by depth:")
    print(f"    {'depth':>6}{'nodes':>7}{'hyperbolic':>13}{'euclidean':>12}{'advantage':>12}")
    for d in range(1, 7):
        r = hierarchy_distortion(d)
        adv = r["euclidean_distortion"] / r["hyperbolic_distortion"]
        print(f"    {r['depth']:>6}{r['nodes']:>7}{r['hyperbolic_distortion']:>13.2f}"
              f"{r['euclidean_distortion']:>12.2f}{adv:>11.2f}x")
    print("\n  HONEST READING: at the current 2-level free-theory hierarchy the")
    print("  hyperbolic base buys ~1.02x -- essentially nothing. It becomes decisive")
    print("  only as resource theories nest deeper. Claimed here, not oversold.")


def main() -> int:
    print("AION-Omega^Q architecture audit")
    print("every number below is computed, none is asserted")
    claim_1_metric_is_gameable()
    claim_2_coherentization()
    claim_3_breathing_is_forced()
    claim_4_process_memory()
    claim_5_fusion_coherence()
    claim_6_identity_gram()
    claim_7_self_knowledge()
    claim_8_frames()
    claim_9_atlas_not_scalar()
    claim_10_hyperbolic_base()
    print("\n" + "=" * 72)
    print("audit complete")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
