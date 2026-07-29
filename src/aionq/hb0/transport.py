"""Boundary reconstruction and simulator-only quantum transport for HB-0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from .core import CarrierMismatch, RemainderEnvelope, _as_vector, _normalised, _safe_exp_score, _finite


@dataclass(frozen=True)
class ReconstructionReport:
    reconstruction: np.ndarray
    boundary_prediction: np.ndarray
    fidelity: float
    remainder: RemainderEnvelope
    nullity: int


class HoloportiveReconstructor:
    """Reconstruct a local section from boundary invariants via a declared map."""

    @staticmethod
    def reconstruct(boundary_map: Any, boundary_value: Any, reference: Any | None = None) -> ReconstructionReport:
        matrix = np.asarray(boundary_map, dtype=float)
        boundary = _as_vector(boundary_value, "boundary_value")
        if matrix.ndim != 2 or matrix.shape[0] != boundary.size:
            raise GovernanceError("boundary map rows must match the boundary observation")
        reconstruction = np.linalg.pinv(matrix) @ boundary
        prediction = matrix @ reconstruction
        boundary_error = float(np.linalg.norm(prediction - boundary))
        if reference is None:
            fidelity = _safe_exp_score(boundary_error)
            statement = "boundary reconstruction defect; interior null-space is unresolved"
            carrier = "boundary_observation"
            instrument = "l2_norm(B pinv(B) y - y)"
            magnitude = boundary_error
        else:
            reference_vec = _as_vector(reference, "reference")
            if reference_vec.shape != reconstruction.shape:
                raise CarrierMismatch("reference and reconstruction carriers differ")
            interior_error = float(np.linalg.norm(reconstruction - reference_vec))
            fidelity = _safe_exp_score(interior_error)
            statement = "interior reconstruction error against a held-out reference"
            carrier = "interior_section"
            instrument = "l2_norm(pinv(B) y - x_reference)"
            magnitude = interior_error
        rank = int(np.linalg.matrix_rank(matrix))
        nullity = int(matrix.shape[1] - rank)
        remainder = RemainderEnvelope(
            name="[R]_transport",
            channel="transport",
            carrier=carrier,
            evidence_tag=EvidenceTag.MEASURED,
            statement=statement,
            instrument=instrument,
            magnitude=magnitude,
            assumptions=("linear boundary map", "Moore-Penrose reconstruction"),
            provenance="HoloportiveReconstructor.reconstruct",
        )
        return ReconstructionReport(reconstruction, prediction, fidelity, remainder, nullity)


@dataclass(frozen=True)
class QuantumBranch:
    classical_bits: tuple[int, int]
    probability: float
    corrected_state: np.ndarray
    fidelity: float


@dataclass(frozen=True)
class QuantumHoloportationReport:
    branches: tuple[QuantumBranch, ...]
    average_fidelity: float
    bell_entropy_bits: float
    simulator_only: bool = True
    advantage_claim: bool = False


@dataclass(frozen=True)
class TunnellingReport:
    final_state: np.ndarray
    transfer_probability: float
    norm_defect: float
    simulator_only: bool = True
    advantage_claim: bool = False


def _kron(*matrices: np.ndarray) -> np.ndarray:
    out = np.asarray([[1.0 + 0.0j]])
    for matrix in matrices:
        out = np.kron(out, matrix)
    return out


def _entanglement_entropy_two_qubit(state: np.ndarray) -> float:
    psi = _normalised(state, "two_qubit_state")
    if psi.size != 4:
        raise GovernanceError("two-qubit entropy requires four amplitudes")
    matrix = psi.reshape(2, 2)
    rho = matrix @ matrix.conj().T
    values = np.clip(np.linalg.eigvalsh(rho).real, 0.0, 1.0)
    values = values[values > 1e-15]
    return float(-np.sum(values * np.log2(values)))


def teleport_qubit(state: Any) -> QuantumHoloportationReport:
    """Ideal three-qubit teleportation, simulated branch by branch.

    The result is intentionally accompanied by ``advantage_claim=False``.  For a
    classically known state, copying its two amplitudes is a matched zero-error
    control; this routine demonstrates the quantum protocol, not superiority.
    """
    psi = _normalised(state, "qubit")
    if psi.size != 2:
        raise GovernanceError("teleportation currently accepts exactly one qubit")
    zero = np.array([1.0, 0.0], dtype=complex)
    bell = _normalised(np.array([1.0, 0.0, 0.0, 1.0], dtype=complex), "bell")
    total = np.kron(psi, bell)
    h = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / math.sqrt(2.0)
    x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
    cnot_01 = np.zeros((8, 8), dtype=complex)
    for q0 in range(2):
        for q1 in range(2):
            for q2 in range(2):
                src = 4 * q0 + 2 * q1 + q2
                dst_q1 = q1 ^ q0
                dst = 4 * q0 + 2 * dst_q1 + q2
                cnot_01[dst, src] = 1.0
    state_after = _kron(h, np.eye(2), np.eye(2)) @ (cnot_01 @ total)
    branches: list[QuantumBranch] = []
    for m0 in range(2):
        for m1 in range(2):
            raw = np.array(
                [state_after[4 * m0 + 2 * m1 + q2] for q2 in range(2)],
                dtype=complex,
            )
            probability = float(np.vdot(raw, raw).real)
            if probability <= 1e-15:
                corrected = zero.copy()
                fidelity = 0.0
            else:
                conditional = raw / math.sqrt(probability)
                correction = np.eye(2, dtype=complex)
                if m1:
                    correction = x @ correction
                if m0:
                    correction = z @ correction
                corrected = correction @ conditional
                fidelity = float(abs(np.vdot(psi, corrected)) ** 2)
            branches.append(QuantumBranch((m0, m1), probability, corrected, fidelity))
    average = float(sum(branch.probability * branch.fidelity for branch in branches))
    return QuantumHoloportationReport(
        branches=tuple(branches),
        average_fidelity=average,
        bell_entropy_bits=_entanglement_entropy_two_qubit(bell),
    )


def tunnel_two_level(
    initial_state: Any,
    coupling: float,
    barrier: float,
    duration: float,
) -> TunnellingReport:
    """Unitary evolution of a two-level barrier model, not a hardware experiment."""
    psi = _normalised(initial_state, "two_level_state")
    if psi.size != 2:
        raise GovernanceError("the tunnelling toy model needs two amplitudes")
    coupling = _finite(coupling, "coupling")
    barrier = _finite(barrier, "barrier")
    duration = _finite(duration, "duration")
    hamiltonian = np.array([[0.0, -coupling], [-coupling, barrier]], dtype=complex)
    values, vectors = np.linalg.eigh(hamiltonian)
    unitary = vectors @ np.diag(np.exp(-1j * values * duration)) @ vectors.conj().T
    final = unitary @ psi
    norm_defect = abs(float(np.vdot(final, final).real) - 1.0)
    return TunnellingReport(
        final_state=final,
        transfer_probability=float(abs(final[1]) ** 2),
        norm_defect=norm_defect,
    )
