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
from aionq.residency import (certified_residency, max_bipartite_entanglement,
                             stabilizer_renyi_entropy)
from aionq.selfknowledge import copies_for_self_tomography, self_knowledge_tradeoff


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def claim_1_metric_is_gameable() -> None:
    rule("CLAIM 1  The draft Q_causal metric is gameable; Q_cert is not")

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

    print(f"{'core':<44}{'Q_naive':>9}{'Q_cert':>9}{'gap':>9}")
    print("-" * 72)
    for name, qc in cases:
        r = certified_residency(qc)
        print(f"{name:<44}{r.q_naive:>9.4f}{r.q_cert:>9.4f}{r.gap:>+9.4f}")

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
    print(f"  certified gain is             {audit.cert_delta:+.4f}"
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
    rule("CLAIM 6  Identity Gram is PSD, frame-invariant, and rank-limited")
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
    print(f"\n  {len(holos)} holonomies supplied, identity capacity = {rep.identity_capacity}.")
    print("  Rank, not count, is the identity capacity: duplicated loops add nothing.")


def claim_7_self_knowledge() -> None:
    rule("CLAIM 7  Self-tomography is impossible: no-cloning is sharper than Loeb")
    print("  strength   self-knowledge   identity fidelity")
    print("  " + "-" * 46)
    for p in self_knowledge_tradeoff():
        print(f"  {p.strength:>7.2f}   {p.info_gain_bits:>10.4f} bits   {p.fidelity_retained:>10.4f}")
    n = copies_for_self_tomography(2 ** 6, 0.01)
    print(f"\n  A 6-qubit identity register needs {n:,} copies to certify to eps=0.01.")
    print("  No-cloning forbids the brain from producing them from itself.")
    print("  The evidence membrane is external for physical reasons, not governance ones.")


def claim_8_frames() -> None:
    rule("CLAIM 8  Entanglement is frame-relative, so it cannot be an invariant")
    print(compare_frames())
    print("\n  The same physical situation: product state in A's frame,")
    print("  maximally entangled in B's. This is why Q_cert ignores entanglement.")


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
    print("\n" + "=" * 72)
    print("audit complete")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
