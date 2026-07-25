"""Coherentization and its price.

The draft architecture proposes replacing measurement-driven classical control
with coherent dilation:

    measure -> host decision -> new circuit
        becomes
    coherent branch register -> controlled superposition of policies

That move is sound as physics and is exactly Stinespring dilation.  What the
draft does not price is that it is not free and does not, by itself, make the
core more quantum.  Two costs are charged here.

Cost 1: it does not raise certified quantum residency
-----------------------------------------------------
Deferring a measurement replaces a classically-mediated edge with a controlled
unitary.  Under the draft's additive metric this raises Q_causal.  Under
:mod:`aionq.residency` it does not move Q_cert at all, because the stabilizer
rank of the core is unchanged: the same non-Clifford resources are being spent
either way.  Coherentization *relocates* classicality; it does not remove it.
The draft listed this as a theorem target ("quantum residency monotonicity");
:func:`coherentization_audit` decides it numerically.

Cost 2: it accrues ancillas monotonically
-----------------------------------------
Every deferred branch keeps its record qubit.  A brain that never measures
accumulates one qubit of garbage per decision.  This is the uncomputation
problem, and it is what forces exhalation to exist.  See :mod:`aionq.budget`.
"""

from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import ControlFlowOp, Measure
from qiskit.quantum_info import Kraus, Operator, Stinespring

from .residency import ResidencyReport, simulation_residency

__all__ = ["coherentize", "coherentization_audit", "CoherentizationAudit",
           "stinespring_dilation"]


def stinespring_dilation(kraus_ops) -> Stinespring:
    """Return the Stinespring isometry of a channel given by Kraus operators.

    Every internal CPTP cognitive operation admits such a realisation, so the
    environment register can in principle stay quantum until the declared
    boundary.  This is the constructive core of the draft's "coherentization
    theorem" -- it is a restatement of Stinespring, not a new result.
    """
    return Stinespring(Kraus(kraus_ops))


def coherentize(circuit: QuantumCircuit) -> QuantumCircuit:
    """Replace measurement + classical feedforward with coherent control.

    Each ``IfElseOp`` conditioned on a measured bit becomes a controlled unitary
    on a retained branch register; the mid-circuit ``Measure`` that fed it is
    dropped.  The branch record is *kept*, not erased: that retention is the
    whole point, and the whole cost.

    Only the common single-condition-bit shape is handled; anything else is
    passed through unchanged so the audit stays honest about what it converted.
    """
    branch = QuantumRegister(max(1, circuit.num_clbits), "branch")
    out = QuantumCircuit(*circuit.qregs, branch, *circuit.cregs)

    # Map each classical bit to the branch qubit that now carries it coherently.
    clbit_to_branch = {cb: branch[i] for i, cb in enumerate(circuit.clbits)}

    for inst in circuit.data:
        op, qargs, cargs = inst.operation, inst.qubits, inst.clbits

        if isinstance(op, Measure):
            # Coherent copy into the branch register instead of a projection.
            target = clbit_to_branch[cargs[0]]
            out.cx(qargs[0], target)
            continue

        if isinstance(op, ControlFlowOp) and op.name == "if_else":
            cond = op.condition
            cond_bits = [cond[0]] if not hasattr(cond[0], "__iter__") else list(cond[0])
            if len(cond_bits) == 1 and cond_bits[0] in clbit_to_branch:
                ctrl = clbit_to_branch[cond_bits[0]]
                body = op.blocks[0]
                for sub in body.data:
                    gate = sub.operation
                    try:
                        controlled = gate.control(1)
                    except Exception:
                        out.append(gate, [out.qubits[circuit.find_bit(q).index]
                                          for q in sub.qubits])
                        continue
                    targets = [out.qubits[circuit.find_bit(q).index] for q in sub.qubits]
                    out.append(controlled, [ctrl] + targets)
                continue

        out.append(op, qargs, cargs)

    return out


@dataclass
class CoherentizationAudit:
    """Before/after comparison of a coherentization step."""

    before: ResidencyReport
    after: ResidencyReport
    ancillas_added: int

    @property
    def naive_delta(self) -> float:
        return self.after.q_naive - self.before.q_naive

    @property
    def cert_delta(self) -> float:
        return self.after.q_sim_upper - self.before.q_sim_upper

    @property
    def monotone(self) -> bool:
        """Did coherentization actually buy certified quantum residency?"""
        return self.cert_delta > 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"Q_naive : {self.before.q_naive:.4f} -> {self.after.q_naive:.4f}  "
            f"(delta {self.naive_delta:+.4f})",
            f"q_sim+  : {self.before.q_sim_upper:.4f} -> {self.after.q_sim_upper:.4f}  "
            f"(delta {self.cert_delta:+.4f})",
            f"ancillas retained : +{self.ancillas_added}",
            f"raised simulation hardness : {self.monotone}",
        ])


def coherentization_audit(circuit: QuantumCircuit) -> CoherentizationAudit:
    """Coherentize `circuit` and report what it bought and what it cost."""
    after_circuit = coherentize(circuit)
    return CoherentizationAudit(
        before=simulation_residency(circuit),
        after=simulation_residency(after_circuit),
        ancillas_added=after_circuit.num_qubits - circuit.num_qubits,
    )
