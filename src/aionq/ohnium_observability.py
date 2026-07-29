"""Ohnium V2: observable ascent under motion.

This module turns the requested carrier sequence

    R -> H -> O -> CD32 -> A_n

into a deterministic telemetry object.  The symbols are engineering carrier
labels, not a hierarchy of intelligence:

``R``
    A normalized real coordinate view of an ``SL(2,R)`` source movement.
``H``
    The Hopf/Bloch image of a normalized two-component complex spinor.
``O``
    An eight-coordinate octonion *coordinate carrier*.  Fano ``so(8)`` audit
    data is kept algebra-valued beside it; no octonionic quantum hardware is
    claimed.
``CD32``
    A 32-coordinate Cayley--Dickson carrier.  It is explicitly non-division and
    non-flat; it is not another Hopf rung.
``A_n``
    The active ``n``-coordinate projection of CD32.  ``A_n`` is defined here,
    rather than guessed from the name.

``OHM`` means **Ohnium**.  ``A/U/M`` are typed cadence labels whose operators
are ordinary SU(2) rotations.  Their names acknowledge the three phonetic
phases of Om/AUM, but no chant, meditation practice, spiritual proposition,
consciousness, or physical quantum effect is encoded by those labels.

The observatory keeps projection loss algebra-valued: every lossy bridge stores
the full landing vector, its rank loss, and its scalar energy diagnostic.  The
scalar never replaces the vector.  A return path must reweave the landing vector
and close, or the frame is classified as bridge absorption.
"""

from __future__ import annotations

import itertools
import json
import math
import numbers
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .fano_decoder import (
    algebra_basis,
    channel_generator,
    fano_lines,
    so8_coordinates,
)
from .governance import GovernanceError, RemainderKind
from .hopf_layer import hopf_map
from .quantities import Quantity
from .quantum_movement import QuantumMovementOmniTool, SourceMovement
from .recognition.types import TypedRemainder
from .recognition.worldlet import (
    AlgebraRegime,
    Geometry,
    Polycosmos,
    Tendril,
    Worldlet,
)

__all__ = [
    "AUMPhase",
    "CARRIER_ORDER",
    "MAX_STABLE_RHO",
    "EndpointConfig",
    "ProjectionViolence",
    "ReturnPath",
    "BridgeTelemetry",
    "CarrierSnapshot",
    "ProofPressure",
    "FrameTelemetry",
    "EndpointTrace",
    "FaultProbe",
    "HamiltonianQualityAudit",
    "OhniumAtlas",
    "phase_operator",
    "poincare_disk_point",
    "run_endpoint",
    "build_ohnium_atlas",
    "atlas_payload",
]

MANIFEST = "manifests/ohnium_v2_observability_preregistration.json"
PREREGISTRATION_PATH = Path(__file__).resolve().parents[2] / MANIFEST
SEED = 20260728
FRAMES = 40
CARRIER_ORDER = ("R", "H", "O", "CD32", "A_n")
FAULTS = ("false_ascent", "energy_leakage", "bridge_absorption")
FAULT_SCHEDULE = {
    "false_ascent": 16,
    "energy_leakage": 24,
    "bridge_absorption": 32,
}
TOLERANCE = 1e-12
RHO_MODULATION = 0.08
MAX_STABLE_RHO = 6.0


class AUMPhase(str, Enum):
    """Typed Ohnium cadence; labels have no physical or spiritual semantics."""

    A = "A"
    U = "U"
    M = "M"


@dataclass(frozen=True)
class EndpointConfig:
    id: str
    rho: float
    phi: float
    psi: float
    active_dimension: int
    phase_offset: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("an endpoint needs a non-empty string id")
        if not all(
            isinstance(value, numbers.Real)
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in (self.rho, self.phi, self.psi)
        ):
            raise ValueError("rho, phi, and psi must be finite real numbers")
        if not (
            RHO_MODULATION
            <= float(self.rho)
            <= MAX_STABLE_RHO - RHO_MODULATION
        ):
            raise ValueError(
                "Ohnium endpoint rho must keep the full R40 modulation "
                f"inside [0,{MAX_STABLE_RHO:g}], the strict finite-float "
                "SL(2,R) determinant seam validated by this observatory"
            )
        if (
            isinstance(self.active_dimension, bool)
            or not isinstance(self.active_dimension, numbers.Integral)
            or not 1 <= self.active_dimension < 32
        ):
            raise ValueError("active_dimension must lie in [1,31]")
        if (
            isinstance(self.phase_offset, bool)
            or not isinstance(self.phase_offset, numbers.Integral)
        ):
            raise ValueError("phase_offset must be an integer")


DEFAULT_ENDPOINTS = (
    EndpointConfig("cosmos.north", 0.5, 0.2, 0.7, 8, 0),
    EndpointConfig("cosmos.equator", 1.25, -0.4, 1.1, 12, 1),
    EndpointConfig("cosmos.deep", 2.0, 0.8, -1.0, 16, 2),
)


@dataclass(frozen=True)
class ProjectionViolence:
    """Where a projection lands, plus secondary scalar diagnostics."""

    landing_carrier: str
    discarded_vector: tuple[float, ...]
    rank_loss: int
    energy_loss: float
    volume_form_distortion: Quantity | None

    @property
    def discarded_energy(self) -> float:
        vector = np.asarray(self.discarded_vector, dtype=float)
        return float(vector @ vector)


@dataclass(frozen=True)
class ReturnPath:
    source_carrier: str
    target_carrier: str
    sidecar: tuple[float, ...]
    reconstruction_defect: float
    closes_with_sidecar: bool


@dataclass(frozen=True)
class BridgeTelemetry:
    source: str
    target: str
    source_energy: float
    target_energy: float
    transferred_energy: float
    energy_balance_defect: float
    remainder_record_defect: float
    violence: ProjectionViolence
    return_path: ReturnPath


@dataclass(frozen=True)
class CarrierSnapshot:
    carrier: str
    dimension: int
    vector: tuple[float, ...]
    energy: float
    evidence_tag: str = "M"


@dataclass(frozen=True)
class ProofPressure:
    fano_signal_rank: int
    fano_crosstalk_rank: int
    fano_joint_rank: int
    fano_cross_gram: float
    fano_surface: str
    fano_probe_definition: str
    fano_probe_coefficients: tuple[float, ...]
    fano_probe_landing: tuple[float, ...]
    fano_probe_signal_projection: tuple[float, ...]
    fano_braid_defect: float
    light_cone_defect: float
    swirl_defect: float
    carrier_ring_defect: float
    disk_point: tuple[float, float]
    failures: tuple[str, ...]

    @property
    def coherent(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class FrameTelemetry:
    index: int
    phase: str
    dominant_carrier: str
    source_coordinates: tuple[float, float, float]
    operational_success_probability: float
    source_operational_volume_distortion: Quantity | None
    carrier_trace: tuple[CarrierSnapshot, ...]
    bridges: tuple[BridgeTelemetry, ...]
    proof_pressure: ProofPressure
    weave_action: str
    weave_reason: str


@dataclass(frozen=True)
class EndpointTrace:
    id: str
    active_dimension: int
    frames: tuple[FrameTelemetry, ...]
    dominance_trace: tuple[str, ...]
    active_remainder: TypedRemainder
    active_discarded_vector: tuple[float, ...]
    return_path: ReturnPath


@dataclass(frozen=True)
class FaultProbe:
    fault: str
    frame: int
    caught: bool
    observed_failures: tuple[str, ...]
    telemetry: FrameTelemetry


@dataclass(frozen=True)
class HamiltonianQualityAudit:
    """Eight quality coordinates and their scheduling energy.

    ``total_energy`` may prioritize repairs.  It is not a promotion score and
    cannot turn an M/S artifact into P evidence.
    """

    qualities: tuple[tuple[str, float], ...]
    energy_components: tuple[tuple[str, float], ...]
    total_energy: float
    promotion_forbidden: bool = True


@dataclass(frozen=True)
class OhniumAtlas:
    endpoints: tuple[EndpointTrace, ...]
    polycosmos: Polycosmos
    fault_probes: tuple[FaultProbe, ...]
    governance: HamiltonianQualityAudit
    frames: int = FRAMES
    carrier_order: tuple[str, ...] = CARRIER_ORDER
    manifest: str = MANIFEST
    attribution: str = (
        "(c) Jesús Vilela Jato, all rights reserved. 21/05/2026"
    )


def _energy(vector: np.ndarray) -> float:
    vector = np.asarray(vector)
    return float(np.vdot(vector, vector).real)


def _real_spinor(spinor: np.ndarray) -> np.ndarray:
    return np.array(
        [spinor[0].real, spinor[0].imag, spinor[1].real, spinor[1].imag],
        dtype=float,
    )


def _normalise(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm <= 1e-15:
        raise ValueError("cannot normalize a zero or non-finite carrier")
    return vector / norm


def phase_operator(phase: AUMPhase | str, tau: float) -> np.ndarray:
    """Return the registered SU(2) operator for one A/U/M cadence label."""

    phase = AUMPhase(phase)
    tau = float(tau)
    if not math.isfinite(tau):
        raise ValueError("phase time must be finite")
    sigma_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    sigma_y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)
    sigma_z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
    generator = {
        AUMPhase.A: sigma_x,
        AUMPhase.U: sigma_y,
        AUMPhase.M: sigma_z,
    }[phase]
    return (
        math.cos(tau / 2.0) * np.eye(2, dtype=complex)
        - 1j * math.sin(tau / 2.0) * generator
    )


def poincare_disk_point(rho: float, theta: float) -> tuple[float, float]:
    radius = math.tanh(float(rho) / 2.0)
    return (radius * math.cos(float(theta)), radius * math.sin(float(theta)))


def _spinor(source: SourceMovement, phase: AUMPhase, tau: float) -> np.ndarray:
    theta = 2.0 * math.atan(math.exp(-source.rho))
    base = np.array(
        [
            math.cos(theta / 2.0) * np.exp(-0.5j * source.phi),
            math.sin(theta / 2.0) * np.exp(0.5j * source.psi),
        ],
        dtype=complex,
    )
    return _normalise(phase_operator(phase, tau) @ base)


def _hopf_return(spinor: np.ndarray, image: np.ndarray) -> tuple[np.ndarray, tuple]:
    x, y, z = (float(value) for value in image)
    first = math.sqrt(max(0.0, (1.0 + z) / 2.0))
    if first > 1e-12:
        canonical = np.array(
            [first, complex(x, y) / (2.0 * first)], dtype=complex
        )
        gamma = float(np.angle(spinor[0]))
    else:
        canonical = np.array([0.0, 1.0], dtype=complex)
        gamma = float(np.angle(spinor[1]))
    recovered = np.exp(1j * gamma) * canonical
    return recovered, (math.cos(gamma), math.sin(gamma))


def _octonion_coordinate(hopf: np.ndarray) -> np.ndarray:
    output = np.zeros(8, dtype=float)
    output[1:4] = np.asarray(hopf, dtype=float)
    return output


def _cd32_kernel(theta: float, phase: AUMPhase) -> np.ndarray:
    shift = {AUMPhase.A: 0.0, AUMPhase.U: 2.0, AUMPhase.M: 4.0}[phase]
    values = np.array(
        [
            1.0,
            1.0 + 0.2 * math.cos(theta + shift),
            1.0 + 0.2 * math.sin(theta + shift),
            1.0 + 0.1 * math.cos(2.0 * theta - shift),
        ],
        dtype=float,
    )
    return _normalise(values)


def _snapshot(name: str, vector: np.ndarray, dimension: int | None = None) -> CarrierSnapshot:
    flat = np.asarray(vector).real.astype(float).ravel()
    return CarrierSnapshot(
        name,
        int(dimension if dimension is not None else flat.size),
        tuple(float(value) for value in flat),
        _energy(flat),
    )


def _violence(
    landing: str,
    discarded: np.ndarray,
    rank_loss: int,
    energy_loss: float,
    distortion: Quantity | None = None,
) -> ProjectionViolence:
    return ProjectionViolence(
        landing,
        tuple(float(value) for value in np.asarray(discarded, dtype=float).ravel()),
        int(rank_loss),
        float(energy_loss),
        distortion,
    )


def _bridge(
    source_name: str,
    target_name: str,
    source: np.ndarray,
    target: np.ndarray,
    violence: ProjectionViolence,
    return_sidecar: Sequence[float],
    recovered: np.ndarray,
    *,
    source_for_return: np.ndarray | None = None,
    discarded_vector_carries_amplitude_energy: bool = True,
) -> BridgeTelemetry:
    source = np.asarray(source)
    target = np.asarray(target)
    expected = source if source_for_return is None else np.asarray(source_for_return)
    source_energy = _energy(source)
    target_energy = _energy(target)
    recorded_energy = (
        violence.discarded_energy
        if discarded_vector_carries_amplitude_energy
        else violence.energy_loss
    )
    return_defect = float(np.linalg.norm(np.asarray(recovered) - expected))
    return_path = ReturnPath(
        source_name,
        target_name,
        tuple(float(value) for value in return_sidecar),
        return_defect,
        return_defect <= TOLERANCE,
    )
    return BridgeTelemetry(
        source_name,
        target_name,
        source_energy,
        target_energy,
        target_energy - source_energy,
        abs(source_energy - target_energy - violence.energy_loss),
        abs(recorded_energy - violence.energy_loss),
        violence,
        return_path,
    )


def _carrier_bridges(
    spinor: np.ndarray,
    hopf: np.ndarray,
    octonion: np.ndarray,
    cd32: np.ndarray,
    active_dimension: int,
    volume_form_distortion: Quantity | None,
    fault: str | None,
) -> tuple[tuple[CarrierSnapshot, ...], tuple[BridgeTelemetry, ...]]:
    real = _real_spinor(spinor)
    hopf_recovered, phase_sidecar = _hopf_return(spinor, hopf)
    bridge_rh = _bridge(
        "R",
        "H",
        real,
        hopf,
        _violence("U(1) Hopf fibre", np.asarray(phase_sidecar), 1, 0.0),
        phase_sidecar,
        _real_spinor(hopf_recovered),
        discarded_vector_carries_amplitude_energy=False,
    )

    bridge_ho = _bridge(
        "H",
        "O",
        hopf,
        octonion,
        _violence("none; isometric coordinate lift", np.zeros(0), 0, 0.0),
        (),
        octonion[1:4],
    )

    kernel = _normalise(
        np.array(
            [
                np.linalg.norm(cd32.reshape(4, 8)[row])
                for row in range(4)
            ],
            dtype=float,
        )
    )
    moved_cd32 = np.asarray(cd32, dtype=float)
    if fault == "energy_leakage":
        moved_cd32 = 0.9 * moved_cd32
    recovered_octonion = np.sum(
        kernel[:, None] * moved_cd32.reshape(4, 8), axis=0
    )
    bridge_ocd = _bridge(
        "O",
        "CD32",
        octonion,
        moved_cd32,
        _violence("unaccounted amplitude lane", np.zeros(0), 0, 0.0),
        kernel,
        recovered_octonion,
    )

    retained = np.zeros(32, dtype=float)
    retained[:active_dimension] = moved_cd32[:active_dimension]
    actual_discarded = moved_cd32 - retained
    recorded_discarded = (
        np.zeros_like(actual_discarded)
        if fault == "bridge_absorption"
        else actual_discarded
    )
    recovered_cd32 = retained + recorded_discarded
    lost_energy = _energy(actual_discarded)
    bridge_cda = _bridge(
        "CD32",
        "A_n",
        moved_cd32,
        retained,
        _violence(
            "CD32 orthogonal complement",
            recorded_discarded,
            32 - active_dimension,
            lost_energy,
            volume_form_distortion,
        ),
        recorded_discarded,
        recovered_cd32,
    )

    snapshots = (
        _snapshot("R", real, 4),
        _snapshot("H", hopf, 3),
        _snapshot("O", octonion, 8),
        _snapshot("CD32", moved_cd32, 32),
        _snapshot("A_n", retained, active_dimension),
    )
    return snapshots, (bridge_rh, bridge_ho, bridge_ocd, bridge_cda)


def _normalised_columns(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=0)
    output = np.zeros_like(matrix)
    good = norms > 1e-14
    output[:, good] = matrix[:, good] / norms[good]
    return output


@lru_cache(maxsize=2)
def _fano_report(collapsed: bool) -> dict:
    if collapsed:
        triples = list(fano_lines())
        triples[-1] = triples[0]
        generators = [channel_generator(triple) for triple in triples]
        signal = _normalised_columns(
            np.column_stack(
                [so8_coordinates(generator) for generator in generators]
            )
        )
        pairs = tuple(itertools.combinations(range(7), 2))
        crosstalk = _normalised_columns(
            np.column_stack(
                [
                    so8_coordinates(
                        generators[left] @ generators[right]
                        - generators[right] @ generators[left]
                    )
                    for left, right in pairs
                ]
            )
        )
        surface = "duplicated_channel_control"
    else:
        basis = algebra_basis(fano_lines())
        triples = list(basis.triples)
        pairs = basis.pairs
        signal = basis.signal
        crosstalk = basis.crosstalk
        surface = "baseline"
    joint = np.column_stack((signal, crosstalk))
    return {
        "surface": surface,
        "triples": tuple(tuple(value for value in triple) for triple in triples),
        "pairs": pairs,
        "coordinate_contract": (
            "28 isometric upper-triangle coordinates; Euclidean inner "
            "product equals the so(8) Frobenius inner product"
        ),
        "signal_coordinates": signal.T.copy(),
        "signal_matrix": signal.copy(),
        "crosstalk_coordinates": crosstalk.T.copy(),
        "crosstalk_matrix": crosstalk.copy(),
        "signal_rank": int(np.linalg.matrix_rank(signal)),
        "crosstalk_rank": int(np.linalg.matrix_rank(crosstalk)),
        "joint_rank": int(np.linalg.matrix_rank(joint)),
        "max_abs_cross_gram": float(np.max(np.abs(signal.T @ crosstalk))),
    }


def _proof_pressure(
    source: SourceMovement,
    hopf: np.ndarray,
    bridges: tuple[BridgeTelemetry, ...],
    dominant: str,
    frame: int,
    fano_fault: bool,
) -> ProofPressure:
    fano = _fano_report(fano_fault)
    theta = 2.0 * math.pi * frame / FRAMES
    coefficients = np.array(
        [
            (
                float(hopf[left % 3])
                - float(hopf[right % 3])
                + 0.25 * math.cos((index + 1) * theta)
            )
            for index, (left, right) in enumerate(fano["pairs"])
        ],
        dtype=float,
    )
    coefficients = _normalise(coefficients)
    landing = fano["crosstalk_matrix"] @ coefficients
    signal_projection = fano["signal_matrix"].T @ landing
    fano_defect = (
        (28 - int(fano["joint_rank"])) / 28.0
        + float(fano["max_abs_cross_gram"])
    )
    determinant_defect = abs(float(np.linalg.det(source.matrix)) - 1.0)
    singular_defect = abs(
        source.singular_values[0] * source.singular_values[1] - 1.0
    )
    balance_defect = max(bridge.energy_balance_defect for bridge in bridges)
    light_cone_defect = max(determinant_defect, singular_defect, balance_defect)
    swirl_defect = abs(float(np.linalg.norm(hopf)) - 1.0)
    ring_defect = max(bridge.return_path.reconstruction_defect for bridge in bridges)
    remainder_defect = max(bridge.remainder_record_defect for bridge in bridges)

    failures: list[str] = []
    if fano_defect > TOLERANCE and CARRIER_ORDER.index(dominant) >= 2:
        failures.append("false_ascent")
    if balance_defect > TOLERANCE:
        failures.append("energy_leakage")
    if remainder_defect > TOLERANCE:
        failures.append("bridge_absorption")
    if swirl_defect > TOLERANCE:
        failures.append("swirl_decoherence")
    if ring_defect > TOLERANCE and not failures:
        failures.append("carrier_ring_break")

    return ProofPressure(
        fano_signal_rank=int(fano["signal_rank"]),
        fano_crosstalk_rank=int(fano["crosstalk_rank"]),
        fano_joint_rank=int(fano["joint_rank"]),
        fano_cross_gram=float(fano["max_abs_cross_gram"]),
        fano_surface=str(fano["surface"]),
        fano_probe_definition=(
            "normalised deterministic 21-coordinate diagnostic probe: "
            "c_i = hopf[left_i mod 3] - hopf[right_i mod 3] "
            "+ 0.25*cos((i+1)*2*pi*frame/40); landing = "
            "fano_crosstalk_basis @ c. It is not measured active-operator "
            "commutator telemetry."
        ),
        fano_probe_coefficients=tuple(
            float(value) for value in coefficients
        ),
        fano_probe_landing=tuple(float(value) for value in landing),
        fano_probe_signal_projection=tuple(
            float(value) for value in signal_projection
        ),
        fano_braid_defect=fano_defect,
        light_cone_defect=light_cone_defect,
        swirl_defect=swirl_defect,
        carrier_ring_defect=ring_defect,
        disk_point=poincare_disk_point(source.rho, theta),
        failures=tuple(failures),
    )


def run_endpoint(
    config: EndpointConfig,
    faults: Mapping[int, str] | None = None,
) -> EndpointTrace:
    """Run one immutable 40-frame endpoint fiber."""

    faults = dict(faults or {})
    unknown = set(faults.values()) - set(FAULTS)
    if unknown:
        raise ValueError(f"unknown Ohnium faults: {sorted(unknown)}")
    if any(
        isinstance(index, bool)
        or not isinstance(index, numbers.Integral)
        or not 0 <= index < FRAMES
        for index in faults
    ):
        raise ValueError("fault frame lies outside R40")

    tool = QuantumMovementOmniTool(weave_trace_threshold=0.05)
    output: list[FrameTelemetry] = []
    tau = 2.0 * math.pi / FRAMES
    for index in range(FRAMES):
        angle = 2.0 * math.pi * index / FRAMES
        rho = config.rho + RHO_MODULATION * math.sin(angle)
        phi = config.phi + angle
        psi = config.psi - 0.5 * angle
        observation = tool.observe(rho, phi, psi)
        phase = tuple(AUMPhase)[(index + config.phase_offset) % 3]
        spinor = _spinor(observation.source, phase, tau * (index + 1))
        hopf = hopf_map(spinor)
        octonion = _octonion_coordinate(hopf)
        kernel = _cd32_kernel(angle, phase)
        cd32 = np.kron(kernel, octonion)
        fault = faults.get(index)
        snapshots, bridges = _carrier_bridges(
            spinor,
            hopf,
            octonion,
            cd32,
            config.active_dimension,
            observation.quantum.volume_form_distortion,
            fault,
        )
        dominant = CARRIER_ORDER[min(4, index // 8)]
        pressure = _proof_pressure(
            observation.source,
            hopf,
            bridges,
            dominant,
            index,
            fano_fault=fault == "false_ascent",
        )
        output.append(
            FrameTelemetry(
                index=index,
                phase=phase.value,
                dominant_carrier=dominant,
                source_coordinates=(rho, phi, psi),
                operational_success_probability=(
                    observation.quantum.bell_success_probability
                ),
                source_operational_volume_distortion=(
                    observation.quantum.volume_form_distortion
                ),
                carrier_trace=snapshots,
                bridges=bridges,
                proof_pressure=pressure,
                weave_action=observation.event.action,
                weave_reason=observation.event.reason,
            )
        )

    final_bridge = output[-1].bridges[-1]
    active = TypedRemainder(
        remainder_type=RemainderKind.EMPIRICAL,
        carrier=f"{config.id}: CD32 orthogonal complement of A_{config.active_dimension}",
        metric_or_comparison="full discarded coordinate vector plus L2 energy",
        raw_value=final_bridge.violence.energy_loss,
        assumptions=(
            "deterministic CD32 coordinate lift",
            f"active projection keeps coordinates [0,{config.active_dimension})",
            "telemetry energy is normalized squared amplitude, not physical energy",
        ),
        provenance=MANIFEST,
    )
    return EndpointTrace(
        config.id,
        config.active_dimension,
        tuple(output),
        tuple(frame.dominant_carrier for frame in output),
        active,
        final_bridge.violence.discarded_vector,
        final_bridge.return_path,
    )


def _polycosmos(endpoints: tuple[EndpointTrace, ...]) -> Polycosmos:
    cosmos = Polycosmos()
    for endpoint in endpoints:
        cosmos.add_worldlet(
            Worldlet(
                id=endpoint.id,
                carrier=(
                    f"Ohnium R40 fiber R->H->O->CD32->A_{endpoint.active_dimension}"
                ),
                local_state=endpoint,
                local_geometry=Geometry.CAYLEY_DICKSON_L2,
                algebra_regime=AlgebraRegime.CD32,
                clocks=("R40", "A/U/M cadence", "attempted-use clock"),
                observers=("OhniumObservatory", "QuantumMovementOmniTool"),
                boundary="CD32 is non-division and not a Hopf rung",
                energy_or_cost=endpoint.active_remainder.raw_value,
                evidence_refs=(MANIFEST,),
                typed_remainders=(endpoint.active_remainder,),
            )
        )
    ids = [endpoint.id for endpoint in endpoints]
    for index, source in enumerate(ids):
        target = ids[(index + 1) % len(ids)]
        cosmos.add_tendril(
            Tendril(
                id=f"mutual-recognition:{source}->{target}",
                source=source,
                target=target,
                forward_transport="compare registered carrier/proof-pressure schema",
                return_transport="reverse lookup with endpoint-local sidecar",
                preserved_fields=(
                    "frame index",
                    "carrier label",
                    "evidence tag",
                    "typed remainder provenance",
                ),
                transformed_fields=("endpoint-local coordinates",),
                lost_fields=(),
                transport_cost=0.0,
            )
        )
    cosmos.hyperedges = (tuple(ids),)
    return cosmos


def _fault_probes(config: EndpointConfig) -> tuple[FaultProbe, ...]:
    output = []
    for fault, frame in FAULT_SCHEDULE.items():
        trace = run_endpoint(config, {frame: fault})
        telemetry = trace.frames[frame]
        observed = telemetry.proof_pressure.failures
        output.append(
            FaultProbe(fault, frame, fault in observed, observed, telemetry)
        )
    return tuple(output)


def _endpoint_contract(config: EndpointConfig) -> dict[str, object]:
    return {
        "id": config.id,
        "rho": float(config.rho),
        "phi": float(config.phi),
        "psi": float(config.psi),
        "active_dimension": config.active_dimension,
        "phase_offset": config.phase_offset,
    }


def _preregistered_scope_verified(
    configs: tuple[EndpointConfig, ...],
) -> bool:
    """Check executable scope equality against the frozen contract.

    This is a contract check, not a scientific promotion gate.  Operator
    identities and numerical behavior remain separate test and runner gates.
    """

    try:
        manifest = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return bool(
        manifest.get("status") == "FROZEN_BEFORE_IMPLEMENTATION"
        and manifest.get("seed") == SEED
        and manifest.get("frames") == FRAMES
        and manifest.get("phase_order")
        == [phase.value for phase in AUMPhase]
        and manifest.get("carrier_order") == list(CARRIER_ORDER)
        and manifest.get("endpoints")
        == [_endpoint_contract(config) for config in configs]
    )


def _governance(
    configs: tuple[EndpointConfig, ...],
    endpoints: tuple[EndpointTrace, ...],
    probes: tuple[FaultProbe, ...],
) -> HamiltonianQualityAudit:
    frames = tuple(frame for endpoint in endpoints for frame in endpoint.frames)
    values = (
        (
            "stratified_recognition",
            float(
                all(
                    tuple(item.carrier for item in frame.carrier_trace)
                    == CARRIER_ORDER
                    for frame in frames
                )
            ),
        ),
        (
            "multi_angle_epistemics",
            float(all(frame.proof_pressure.coherent for frame in frames)),
        ),
        (
            "preregistered_scope",
            float(_preregistered_scope_verified(configs)),
        ),
        (
            "self_similar_structure",
            float(
                all(
                    len(endpoint.frames) == FRAMES
                    and tuple(frame.index for frame in endpoint.frames)
                    == tuple(range(FRAMES))
                    for endpoint in endpoints
                )
            ),
        ),
        (
            "geometric_substrate",
            float(
                all(
                    math.hypot(*frame.proof_pressure.disk_point) < 1.0
                    and frame.proof_pressure.swirl_defect <= TOLERANCE
                    for frame in frames
                )
            ),
        ),
        (
            "negative_result_recording",
            float(all(probe.observed_failures for probe in probes)),
        ),
        (
            "adversarial_pre_mortem",
            float(all(probe.caught for probe in probes)),
        ),
        (
            "composer_complicity",
            float(
                all(
                    frame.proof_pressure.carrier_ring_defect <= TOLERANCE
                    for frame in frames
                )
            ),
        ),
    )
    components = tuple((name, 1.0 - value) for name, value in values)
    return HamiltonianQualityAudit(
        values,
        components,
        float(sum(value for _, value in components)),
    )


def build_ohnium_atlas(
    configs: Sequence[EndpointConfig] = DEFAULT_ENDPOINTS,
) -> OhniumAtlas:
    configs = tuple(configs)
    if len(configs) < 2:
        raise GovernanceError("cosmos-level multiplicity requires at least two fibers")
    if len({config.id for config in configs}) != len(configs):
        raise GovernanceError("Ohnium endpoint ids must be unique")
    endpoints = tuple(run_endpoint(config) for config in configs)
    probes = _fault_probes(configs[0])
    return OhniumAtlas(
        endpoints,
        _polycosmos(endpoints),
        probes,
        _governance(configs, endpoints, probes),
    )


def _quantity_payload(quantity: Quantity | None) -> dict | None:
    if quantity is None:
        return None
    return {
        "value": float(quantity.value),
        "unit": quantity.unit,
        "uncertainty": float(quantity.uncertainty),
        "base": quantity.base,
    }


def _proof_pressure_payload(pressure: ProofPressure) -> dict:
    return {
        "fano_signal_rank": pressure.fano_signal_rank,
        "fano_crosstalk_rank": pressure.fano_crosstalk_rank,
        "fano_joint_rank": pressure.fano_joint_rank,
        "fano_cross_gram": pressure.fano_cross_gram,
        "fano_surface": pressure.fano_surface,
        "fano_probe_definition": pressure.fano_probe_definition,
        "fano_probe_coefficients": list(
            pressure.fano_probe_coefficients
        ),
        "fano_probe_landing": list(pressure.fano_probe_landing),
        "fano_probe_signal_projection": list(
            pressure.fano_probe_signal_projection
        ),
        "fano_braid_defect": pressure.fano_braid_defect,
        "light_cone_defect": pressure.light_cone_defect,
        "swirl_defect": pressure.swirl_defect,
        "carrier_ring_defect": pressure.carrier_ring_defect,
        "disk_point": list(pressure.disk_point),
        "failures": list(pressure.failures),
    }


def atlas_payload(atlas: OhniumAtlas) -> dict:
    """JSON-safe, full-vector payload for the live atlas."""

    endpoint_payload = []
    for endpoint in atlas.endpoints:
        frames = []
        for frame in endpoint.frames:
            frames.append(
                {
                    "index": frame.index,
                    "phase": frame.phase,
                    "dominant_carrier": frame.dominant_carrier,
                    "source_coordinates": list(frame.source_coordinates),
                    "operational_success_probability": (
                        frame.operational_success_probability
                    ),
                    "source_operational_volume_distortion": _quantity_payload(
                        frame.source_operational_volume_distortion
                    ),
                    "weave": {
                        "action": frame.weave_action,
                        "reason": frame.weave_reason,
                    },
                    "carriers": [
                        {
                            "carrier": item.carrier,
                            "dimension": item.dimension,
                            "vector": list(item.vector),
                            "energy": item.energy,
                            "evidence_tag": item.evidence_tag,
                        }
                        for item in frame.carrier_trace
                    ],
                    "bridges": [
                        {
                            "source": bridge.source,
                            "target": bridge.target,
                            "source_energy": bridge.source_energy,
                            "target_energy": bridge.target_energy,
                            "transferred_energy": bridge.transferred_energy,
                            "energy_balance_defect": bridge.energy_balance_defect,
                            "remainder_record_defect": (
                                bridge.remainder_record_defect
                            ),
                            "projection_violence": {
                                "landing_carrier": (
                                    bridge.violence.landing_carrier
                                ),
                                "discarded_vector": list(
                                    bridge.violence.discarded_vector
                                ),
                                "rank_loss": bridge.violence.rank_loss,
                                "energy_loss": bridge.violence.energy_loss,
                                "volume_form_distortion": (
                                    _quantity_payload(
                                        bridge.violence.volume_form_distortion
                                    )
                                ),
                            },
                            "return_path": {
                                "sidecar": list(bridge.return_path.sidecar),
                                "reconstruction_defect": (
                                    bridge.return_path.reconstruction_defect
                                ),
                                "closes_with_sidecar": (
                                    bridge.return_path.closes_with_sidecar
                                ),
                            },
                        }
                        for bridge in frame.bridges
                    ],
                    "proof_pressure": _proof_pressure_payload(
                        frame.proof_pressure
                    ),
                }
            )
        endpoint_payload.append(
            {
                "id": endpoint.id,
                "active_dimension": endpoint.active_dimension,
                "dominance_trace": list(endpoint.dominance_trace),
                "active_remainder": {
                    "type": endpoint.active_remainder.remainder_type,
                    "carrier": endpoint.active_remainder.carrier,
                    "comparison": (
                        endpoint.active_remainder.metric_or_comparison
                    ),
                    "value": endpoint.active_remainder.raw_value,
                    "discarded_vector": list(
                        endpoint.active_discarded_vector
                    ),
                },
                "return_path": {
                    "reconstruction_defect": (
                        endpoint.return_path.reconstruction_defect
                    ),
                    "closes_with_sidecar": endpoint.return_path.closes_with_sidecar,
                },
                "frames": frames,
            }
        )
    return {
        "schema": "ohnium.observable-ascent.v2",
        "name": "OHM / Ohnium",
        "aum_boundary": (
            "A/U/M are typed cadence labels acknowledging Om/AUM phonetics; "
            "they are not spiritual or physical quantum claims."
        ),
        "frames": atlas.frames,
        "carrier_order": list(atlas.carrier_order),
        "endpoints": endpoint_payload,
        "fault_probes": [
            {
                "fault": probe.fault,
                "frame": probe.frame,
                "caught": probe.caught,
                "observed_failures": list(probe.observed_failures),
                "telemetry": {
                    "frame": probe.telemetry.index,
                    "dominant_carrier": probe.telemetry.dominant_carrier,
                    "proof_pressure": _proof_pressure_payload(
                        probe.telemetry.proof_pressure
                    ),
                },
            }
            for probe in atlas.fault_probes
        ],
        "governance": {
            "qualities": dict(atlas.governance.qualities),
            "energy_components": dict(atlas.governance.energy_components),
            "total_energy": atlas.governance.total_energy,
            "promotion_forbidden": atlas.governance.promotion_forbidden,
        },
        "polycosmos": {
            "worldlets": list(atlas.polycosmos.worldlets),
            "tendrils": list(atlas.polycosmos.tendrils),
            "hyperedges": [list(edge) for edge in atlas.polycosmos.hyperedges],
        },
        "manifest": atlas.manifest,
        "evidence_ceiling": (
            "repository-internal exact identities and deterministic measurements; "
            "not hardware evidence, consciousness, AGI, or independent proof"
        ),
        "attribution": atlas.attribution,
    }
