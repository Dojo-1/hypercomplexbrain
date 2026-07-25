"""Process tensors: temporal memory that a channel cannot hold.

The draft replaces channel-valued Tendrils

    E : rho_alpha -> rho_beta

with multi-time process tensors, on the grounds that cognition depends on
intervention histories.  That is right, and it is testable rather than merely
asserted: a process tensor is Markovian exactly when its Choi state factorises
across time slots.  The correlation that survives factorisation is the memory,
and it is measurable as a mutual information in bits.

This module builds the Choi state of a two-step process tensor by the standard
construction -- at the intervention time the system is swapped out into an
output leg and half of a maximally entangled pair is swapped in -- and reports

    N = I(o1 : i1, f)

the quantum mutual information between what the process delivered at t1 and
everything downstream.  N = 0 is consistent with Markovianity for this construction; it is a
witness, not a general certificate (see the scope note below). It means the
relation carries no measurable memory here, and the draft's Tendril lift buys nothing for that edge.  N > 0 is the
amount of temporal binding actually available.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["ProcessTensor", "build_two_step_process",
           "temporal_correlation_witness", "non_markovianity", "ProcessReport"]


def _dm(vec: np.ndarray) -> np.ndarray:
    return np.outer(vec, vec.conj())


def _partial_trace(rho: np.ndarray, dims: list[int], keep: list[int]) -> np.ndarray:
    """Partial trace of `rho` over all subsystems not in `keep`."""
    n = len(dims)
    keep = sorted(keep)
    rho_t = rho.reshape(dims + dims)
    trace_out = [i for i in range(n) if i not in keep]
    for offset, idx in enumerate(trace_out):
        cur = len(rho_t.shape) // 2
        ax1 = idx - sum(1 for t in trace_out[:offset] if t < idx)
        rho_t = np.trace(rho_t, axis1=ax1, axis2=ax1 + cur)
    d = int(np.prod([dims[i] for i in keep]))
    return rho_t.reshape(d, d)


def _von_neumann(rho: np.ndarray) -> float:
    vals = np.linalg.eigvalsh(rho)
    vals = np.clip(np.real(vals), 1e-15, None)
    vals = vals / vals.sum()
    return float(-np.sum(vals * np.log2(vals)))


@dataclass
class ProcessTensor:
    """Choi state of a two-step process on registers (o1, i1, f)."""

    choi: np.ndarray
    dims: list[int]

    def mutual_information(self) -> float:
        """I(o1 : i1 f) -- the memory the process carries across the slot."""
        rho_o1 = _partial_trace(self.choi, self.dims, [0])
        rho_rest = _partial_trace(self.choi, self.dims, [1, 2])
        return _von_neumann(rho_o1) + _von_neumann(rho_rest) - _von_neumann(self.choi)


@dataclass
class ProcessReport:
    coupling: float
    non_markovianity: float

    @property
    def markovian(self) -> bool:
        """No measurable temporal correlation *on this construction*."""
        return self.non_markovianity < 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"coupling {self.coupling:.3f} -> N = {self.non_markovianity:.6f} bits"
                f"  ({'Markovian' if self.markovian else 'memory present'})")


def _su4_coupling(theta: float) -> np.ndarray:
    """System-environment interaction exp(-i theta ZZ/2) . (partial swap-like)."""
    zz = np.kron(np.diag([1, -1]), np.diag([1, -1])).astype(complex)
    # exp(-i theta/2 * ZZ) is diagonal
    diag = np.exp(-1j * theta / 2 * np.diag(zz))
    u = np.diag(diag)
    # add a coherent exchange term so the environment genuinely stores information
    xx = np.kron(np.array([[0, 1], [1, 0]]), np.array([[0, 1], [1, 0]])).astype(complex)
    from scipy.linalg import expm
    return expm(-1j * theta / 2 * xx) @ u


def build_two_step_process(coupling: float) -> ProcessTensor:
    """Construct the Choi state of a two-step system+environment process.

    ``coupling = 0`` decouples the environment, giving an exactly Markovian
    process.  Larger couplings let the environment retain a record between the
    two steps, which is what a process tensor can represent and a channel cannot.
    """
    d = 2
    u = _su4_coupling(coupling)

    # Registers, in order: o1, i1, S, E   (each a qubit)
    # Initial: |0>_S |0>_E, o1 and i1 unset for now.
    psi_se = np.zeros(d * d, dtype=complex)
    psi_se[0] = 1.0  # |00>_SE

    # Step 1 dynamics.
    psi_se = u @ psi_se

    # Intervention slot: swap S out to o1, swap in half of a Bell pair (i1, S).
    bell = np.zeros(d * d, dtype=complex)
    bell[0] = bell[3] = 1 / np.sqrt(2)  # |Phi+>_{i1, S_new}

    # Full state on (o1, i1, S, E): o1 takes the old S, S takes the Bell half.
    psi_se_t = psi_se.reshape(d, d)  # [S, E]
    full = np.zeros((d, d, d, d), dtype=complex)  # [o1, i1, S, E]
    bell_t = bell.reshape(d, d)  # [i1, S_new]
    for s_old in range(d):
        for e in range(d):
            for i1 in range(d):
                for s_new in range(d):
                    full[s_old, i1, s_new, e] += psi_se_t[s_old, e] * bell_t[i1, s_new]

    # Step 2 dynamics on (S, E).
    full = full.reshape(d * d, d * d)          # [(o1,i1), (S,E)]
    full = full @ u.T
    full = full.reshape(d, d, d, d)            # [o1, i1, S, E]

    # Choi state on (o1, i1, f=S) after tracing out E.
    vec = full.reshape(d * d * d, d)           # [(o1,i1,S), E]
    choi = vec @ vec.conj().T
    choi = choi / np.trace(choi)

    return ProcessTensor(choi=choi, dims=[d, d, d])


def temporal_correlation_witness(coupling: float) -> ProcessReport:
    """Temporal-correlation witness for the two-step toy process.

    Not a general Markovianity certificate: see the module scope note.
    """
    pt = build_two_step_process(coupling)
    return ProcessReport(coupling=coupling,
                         non_markovianity=max(0.0, pt.mutual_information()))


def non_markovianity(coupling: float) -> ProcessReport:
    """Deprecated alias for :func:`temporal_correlation_witness`.

    The old name asserted more than the construction supports.
    """
    return temporal_correlation_witness(coupling)
