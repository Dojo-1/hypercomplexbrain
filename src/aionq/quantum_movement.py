"""QSigma-R8 dual-carrier quantum hyperbolic movement.

The source and attempted-use state deliberately remain different fibers:

* ``SourceMovement`` carries the indefinite ``SL(2,R)`` Cartan geometry and
  its absolute pseudo-volume.  Neither is an operational distance or bits.
* ``QuantumMovement`` carries the five-dimensional Bell-erasure density from
  QSigma-R7 and its trace/Bures/QFI geometry.

The bridge is ``q = exp(-2*rho)`` together with the normalization cocycle.  At
finite ``rho`` the density determines ``q`` (and therefore ``rho``) under exact
tomography; radial information is ill-conditioned in the additive ``rho``
coordinate, not literally deleted.  The exact projective loss is ``M ~ -M``.

``QuantumMovementOmniTool`` is only an S-tier telemetry facade.  It can observe
and change whether an AION Tendril participates in the active coalition.
``Tendril.deweave`` is never used as a physical inverse; the separately named
``echo_transport`` exposes the cost of an actual inverse word.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np

from .governance import GovernanceError, RemainderKind
from .hyperbolic_qubit import swirl_point, to_sl2
from .qsigma_r7_information import (
    BellCodeword,
    InformationMetrics,
    absolute_volume_density,
    bell_codeword,
    information_metrics,
    slab_volume,
    trace_distance,
)
from .quantities import Bits, Quantity
from .recognition.types import TransportReport, TypedRemainder
from .recognition.worldlet import (
    AlgebraRegime,
    Geometry,
    Polycosmos,
    Tendril,
    Worldlet,
)

__all__ = [
    "RankChangeBoundary",
    "SourceMovement",
    "QuantumMovement",
    "PairwiseQuantumGeometry",
    "WordMovement",
    "EchoTransport",
    "QuantumMovementObservation",
    "WeaveEvent",
    "OperationalInformationBracket",
    "QuantumMovementTrace",
    "analytic_qfi_rho",
    "analytic_qfi_q",
    "qfi_volume_density",
    "qfi_volume_exact",
    "qfi_volume_numeric",
    "source_to_qfi_volume_distortion",
    "density_root_fidelity",
    "pairwise_quantum_geometry",
    "bures_qfi_finite_difference",
    "depolarize_density",
    "normalization_cocycle",
    "cocycle_identity_defect",
    "compose_word",
    "echo_transport",
    "compact_frame",
    "build_quantum_polycosmos",
    "QuantumMovementOmniTool",
]

_MANIFEST = "manifests/qsigma_r8_quantum_movement_preregistration.json"
_SOURCE_WORLDLET = "r8:sl2-source-movement"
_QUANTUM_WORLDLET = "r8:bell-erasure-operational-movement"
_BRIDGE = "r8:source-to-operational-weave"
_BELL = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
_MAX_SOURCE_RHO = 350.0


class RankChangeBoundary(ValueError):
    """The interior SLD-QFI chart was requested at the rank-changing rho=0 edge."""


def _readonly(array: np.ndarray, dtype=None) -> np.ndarray:
    output = np.array(array, dtype=dtype, copy=True)
    output.setflags(write=False)
    return output


def _validate_density(density: np.ndarray, tolerance: float = 1e-10) -> np.ndarray:
    density = np.asarray(density, dtype=complex)
    if density.ndim != 2 or density.shape[0] != density.shape[1]:
        raise ValueError("density must be a square matrix")
    hermitian = (density + density.conj().T) / 2.0
    if float(np.max(np.abs(density - hermitian))) > tolerance:
        raise ValueError("density is not Hermitian")
    if float(np.min(np.linalg.eigvalsh(hermitian))) < -tolerance:
        raise ValueError("density is not positive semidefinite")
    if abs(float(np.trace(hermitian).real) - 1.0) > tolerance:
        raise ValueError("density does not have unit trace")
    return hermitian


@dataclass(frozen=True)
class SourceMovement:
    """One state on the source Cartan fiber."""

    rho: float
    phi: float
    psi: float
    matrix: np.ndarray
    singular_values: tuple[float, float]
    volume_density: Quantity
    slab_volume: Quantity

    @classmethod
    def from_coordinates(cls, rho: float, phi: float, psi: float) -> "SourceMovement":
        rho, phi, psi = float(rho), float(phi), float(psi)
        if not all(math.isfinite(value) for value in (rho, phi, psi)):
            raise ValueError("source coordinates must be finite")
        if rho < 0.0:
            raise ValueError("rho must be non-negative")
        if rho > _MAX_SOURCE_RHO:
            raise ValueError(
                f"rho exceeds the finite float source range ({_MAX_SOURCE_RHO:g})"
            )
        matrix = to_sl2(swirl_point(rho, phi, psi))
        singular = tuple(float(value) for value in np.linalg.svd(matrix, compute_uv=False))
        return cls(
            rho=rho,
            phi=phi,
            psi=psi,
            matrix=_readonly(matrix, float),
            singular_values=(singular[0], singular[1]),
            volume_density=Quantity(
                absolute_volume_density(rho),
                unit="absolute-pseudo-volume-density",
                base="SL2-Cartan-source",
            ),
            slab_volume=Quantity(
                slab_volume(rho),
                unit="absolute-pseudo-volume",
                base="SL2-Cartan-source",
            ),
        )


def analytic_qfi_rho(rho: float) -> np.ndarray:
    """Attempted-use SLD QFI in ``(rho, phi, psi)`` for the interior ``rho>0``."""
    rho = float(rho)
    if rho <= 0.0:
        raise RankChangeBoundary(
            "rho=0 changes rank; use finite fidelity/trace probes at the boundary"
        )
    if not math.isfinite(rho):
        raise ValueError("rho must be finite")
    q = math.exp(-2.0 * rho)
    q_squared = math.exp(-4.0 * rho)
    one_minus_q_squared = -math.expm1(-4.0 * rho)
    return np.diag(
        [
            8.0 * q_squared / one_minus_q_squared,
            (1.0 + q) ** 2,
            (1.0 - q) ** 2,
        ]
    )


def analytic_qfi_q(q: float) -> np.ndarray:
    """The same QFI in the regular operational radial coordinate ``q``."""
    q = float(q)
    if not math.isfinite(q) or not (0.0 <= q < 1.0):
        raise RankChangeBoundary(
            "q must lie in [0,1); q=1 is the rank-changing rho=0 boundary"
        )
    return np.diag(
        [
            2.0 / (1.0 - q * q),
            (1.0 + q) ** 2,
            (1.0 - q) ** 2,
        ]
    )


def qfi_volume_density(rho: float) -> float:
    """Continuous determinant density ``sqrt(det J_rho)``."""
    rho = float(rho)
    if not math.isfinite(rho) or rho < 0.0:
        raise ValueError("rho must be non-negative")
    q2 = math.exp(-4.0 * rho)
    one_minus_q2 = -math.expm1(-4.0 * rho)
    return math.sqrt(max(0.0, 8.0 * q2 * one_minus_q2))


def qfi_volume_exact() -> float:
    """Total attempted-use parameter volume before projective quotienting."""
    return math.sqrt(2.0) * math.pi**3


def qfi_volume_numeric(samples: int = 10001) -> float:
    """Independent Simpson integration after ``q=sin(theta)`` substitution."""
    if samples < 3 or samples % 2 == 0:
        raise ValueError("samples must be odd and at least three")
    theta = np.linspace(0.0, math.pi / 2.0, samples)
    values = math.sqrt(2.0) * np.cos(theta) ** 2
    step = float(theta[1] - theta[0])
    radial = step / 3.0 * (
        values[0]
        + values[-1]
        + 4.0 * float(np.sum(values[1:-1:2]))
        + 2.0 * float(np.sum(values[2:-1:2]))
    )
    return 4.0 * math.pi**2 * radial


def source_to_qfi_volume_distortion(rho: float) -> float:
    """Typed pullback-volume distortion, never a common metric or capacity ratio."""
    rho = float(rho)
    if not math.isfinite(rho):
        raise ValueError("rho must be finite")
    if rho <= 0.0:
        raise RankChangeBoundary("volume-form distortion is interior-only")
    q2 = math.exp(-4.0 * rho)
    one_minus_q2 = -math.expm1(-4.0 * rho)
    return 8.0 * math.sqrt(2.0) * q2 / math.sqrt(one_minus_q2)


def _binary_entropy(probability: float) -> float:
    probability = min(1.0, max(0.0, float(probability)))
    if probability in (0.0, 1.0):
        return 0.0
    return -probability * math.log2(probability) - (
        1.0 - probability
    ) * math.log2(1.0 - probability)


@dataclass(frozen=True)
class QuantumMovement:
    """Attempted-use quantum geometry paired with one source movement."""

    q: float
    codeword: BellCodeword
    bell_success_probability: float
    worst_success_probability: float
    qfi_rho: np.ndarray | None
    qfi_q: np.ndarray | None
    qfi_volume: Quantity
    volume_form_distortion: Quantity | None
    conditional_concurrence: float
    conditional_entanglement: Bits
    rank_change_boundary: bool

    @classmethod
    def from_source(cls, source: SourceMovement) -> "QuantumMovement":
        q = math.exp(-2.0 * source.rho)
        word = bell_codeword(source.matrix)
        boundary = source.rho == 0.0
        qfi_rho = None if boundary else _readonly(analytic_qfi_rho(source.rho), float)
        qfi_q = None if boundary else _readonly(analytic_qfi_q(q), float)
        probability = q * q / (1.0 + q * q)
        distortion = (
            None
            if boundary
            else Quantity(
                source_to_qfi_volume_distortion(source.rho),
                unit="pullback-volume-form-ratio",
                base="SL2-to-Bell-erasure",
            )
        )
        return cls(
            q=q,
            codeword=BellCodeword(
                _readonly(word.density, complex),
                word.success_probability,
                _readonly(word.encoded_matrix, complex),
            ),
            bell_success_probability=word.success_probability,
            worst_success_probability=q * q,
            qfi_rho=qfi_rho,
            qfi_q=qfi_q,
            qfi_volume=Quantity(
                qfi_volume_density(source.rho),
                unit="qfi-parameter-volume-density",
                base="Bell-erasure-attempted-use",
            ),
            volume_form_distortion=distortion,
            conditional_concurrence=2.0 * q / (1.0 + q * q),
            conditional_entanglement=Bits(
                _binary_entropy(probability),
                base="fixed-Bell-bipartition",
            ),
            rank_change_boundary=boundary,
        )


def density_root_fidelity(left: np.ndarray, right: np.ndarray) -> float:
    """Dense root fidelity ``||sqrt(left)sqrt(right)||_1``."""
    left = _validate_density(left)
    right = _validate_density(right)
    roots = []
    for density in (left, right):
        values, vectors = np.linalg.eigh(density)
        cutoff = 1e-13 * max(1.0, float(np.max(values)))
        if float(np.min(values)) < -1e-10:
            raise ValueError("fidelity input is not positive semidefinite")
        values = np.where(values > cutoff, values, 0.0)
        roots.append(vectors @ np.diag(np.sqrt(values)) @ vectors.conj().T)
    value = float(np.sum(np.linalg.svd(roots[0] @ roots[1], compute_uv=False)))
    if value < -1e-10 or value > 1.0 + 1e-8:
        raise ValueError("root fidelity fell outside [0,1]")
    return min(1.0, max(0.0, value))


@dataclass(frozen=True)
class PairwiseQuantumGeometry:
    trace_distance: float
    dense_trace_distance: float
    root_fidelity: float
    dense_root_fidelity: float
    bures_squared: float
    helstrom_equal_prior_error: float
    fuchs_lower: float
    fuchs_upper: float


def pairwise_quantum_geometry(
    left: BellCodeword, right: BellCodeword
) -> PairwiseQuantumGeometry:
    """Closed Bell-erasure pair geometry with dense independent checks."""
    overlap = np.trace(left.encoded_matrix.conj().T @ right.encoded_matrix) / 2.0
    p_left = float(left.success_probability)
    p_right = float(right.success_probability)
    radicand = (p_left + p_right) ** 2 - 4.0 * abs(overlap) ** 2
    closed_distance = 0.5 * (
        math.sqrt(max(0.0, radicand)) + abs(p_left - p_right)
    )
    closed_fidelity = abs(overlap) + math.sqrt(
        max(0.0, (1.0 - p_left) * (1.0 - p_right))
    )
    closed_fidelity = min(1.0, max(0.0, closed_fidelity))
    dense_distance = trace_distance(left.density, right.density)
    dense_fidelity = density_root_fidelity(left.density, right.density)
    return PairwiseQuantumGeometry(
        trace_distance=closed_distance,
        dense_trace_distance=dense_distance,
        root_fidelity=closed_fidelity,
        dense_root_fidelity=dense_fidelity,
        bures_squared=2.0 * (1.0 - closed_fidelity),
        helstrom_equal_prior_error=(1.0 - closed_distance) / 2.0,
        fuchs_lower=1.0 - closed_fidelity,
        fuchs_upper=math.sqrt(max(0.0, 1.0 - closed_fidelity**2)),
    )


DensityChannel = Callable[[np.ndarray], np.ndarray]


def bures_qfi_finite_difference(
    rho: float,
    phi: float,
    psi: float,
    *,
    step: float = 1e-4,
    channel: DensityChannel | None = None,
) -> np.ndarray:
    """Reconstruct QFI from centered Bures directional distances."""
    point = np.array([rho, phi, psi], dtype=float)
    step = float(step)
    if step <= 0.0 or point[0] <= step:
        raise ValueError("rho must exceed the positive finite-difference step")

    def attempted_use(coordinates: np.ndarray) -> tuple[BellCodeword, np.ndarray]:
        word = bell_codeword(to_sl2(swirl_point(*coordinates.tolist())))
        output = word.density
        if channel is not None:
            output = channel(output)
        return word, _validate_density(output)

    def directional(direction: np.ndarray) -> float:
        lower_word, lower = attempted_use(point - step * direction)
        upper_word, upper = attempted_use(point + step * direction)
        fidelity = (
            pairwise_quantum_geometry(lower_word, upper_word).root_fidelity
            if channel is None
            else density_root_fidelity(lower, upper)
        )
        distance_squared = 2.0 * (1.0 - fidelity)
        return max(0.0, distance_squared / (step * step))

    basis = np.eye(3)
    output = np.zeros((3, 3), dtype=float)
    for axis in range(3):
        output[axis, axis] = directional(basis[axis])
    for left in range(3):
        for right in range(left):
            pair = directional(basis[left] + basis[right])
            value = (
                pair - output[left, left] - output[right, right]
            ) / 2.0
            output[left, right] = output[right, left] = value
    return output


def depolarize_density(density: np.ndarray, strength: float) -> np.ndarray:
    """Five-dimensional parameter-independent depolarizing CPTP control."""
    density = _validate_density(density)
    strength = float(strength)
    if not (0.0 <= strength <= 1.0):
        raise ValueError("depolarizing strength must lie in [0,1]")
    dimension = density.shape[0]
    output = (1.0 - strength) * density + strength * np.eye(dimension) / dimension
    return _readonly(_validate_density(output), complex)


def _operator_scale(matrix: np.ndarray) -> float:
    matrix = np.asarray(matrix, dtype=complex)
    if matrix.shape != (2, 2):
        raise ValueError("movement matrices must be 2x2")
    scale = float(np.linalg.norm(matrix, 2))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("movement matrix must have a finite positive norm")
    return scale


def normalization_cocycle(left: np.ndarray, right: np.ndarray) -> float:
    """``log||X|| + log||Y|| - log||XY||`` with numerical nonnegativity guard."""
    value = (
        math.log(_operator_scale(left))
        + math.log(_operator_scale(right))
        - math.log(_operator_scale(np.asarray(left) @ np.asarray(right)))
    )
    if value < -1e-10:
        raise ValueError("operator norm submultiplicativity was violated")
    return max(0.0, value)


def cocycle_identity_defect(
    left: np.ndarray, middle: np.ndarray, right: np.ndarray
) -> float:
    lhs = normalization_cocycle(left, middle) + normalization_cocycle(
        np.asarray(left) @ np.asarray(middle), right
    )
    rhs = normalization_cocycle(middle, right) + normalization_cocycle(
        left, np.asarray(middle) @ np.asarray(right)
    )
    return abs(lhs - rhs)


@dataclass(frozen=True)
class WordMovement:
    source_product: np.ndarray
    normalized_product: np.ndarray
    direct_normalized_product: np.ndarray
    kappa: float
    transmissivity: float
    direct_codeword: BellCodeword
    streamed_density: np.ndarray
    direct_success_probability: float
    streamed_success_probability: float
    normalized_product_defect: float


def compose_word(matrices: Sequence[np.ndarray]) -> WordMovement:
    """Compare compiling a net word with materializing every normalized prefix."""
    if not matrices:
        raise ValueError("a movement word must contain at least one matrix")
    source_product = np.eye(2, dtype=complex)
    normalized_product = np.eye(2, dtype=complex)
    log_scale_sum = 0.0
    for matrix in matrices:
        matrix = np.asarray(matrix, dtype=complex)
        scale = _operator_scale(matrix)
        source_product = source_product @ matrix
        normalized_product = normalized_product @ (matrix / scale)
        log_scale_sum += math.log(scale)
    source_scale = _operator_scale(source_product)
    direct_normalized = source_product / source_scale
    kappa = log_scale_sum - math.log(source_scale)
    if kappa < -1e-10:
        raise ValueError("word cocycle became negative")
    kappa = max(0.0, kappa)
    transmissivity = math.exp(-2.0 * kappa)
    direct = bell_codeword(source_product)
    streamed_success = transmissivity * direct.success_probability
    streamed_density = np.zeros((5, 5), dtype=complex)
    streamed_density[:4, :4] = (
        transmissivity * direct.density[:4, :4]
    )
    streamed_density[4, 4] = 1.0 - streamed_success
    streamed_density = _validate_density(streamed_density)
    defect = float(
        np.linalg.norm(
            normalized_product - math.exp(-kappa) * direct_normalized,
            ord="fro",
        )
    )
    return WordMovement(
        source_product=_readonly(source_product, complex),
        normalized_product=_readonly(normalized_product, complex),
        direct_normalized_product=_readonly(direct_normalized, complex),
        kappa=kappa,
        transmissivity=transmissivity,
        direct_codeword=BellCodeword(
            _readonly(direct.density, complex),
            direct.success_probability,
            _readonly(direct.encoded_matrix, complex),
        ),
        streamed_density=_readonly(streamed_density, complex),
        direct_success_probability=direct.success_probability,
        streamed_success_probability=streamed_success,
        normalized_product_defect=defect,
    )


@dataclass(frozen=True)
class EchoTransport:
    rho: float
    source_return_defect: float
    conditional_return_fidelity: float
    direct_success_probability: float
    streamed_success_probability: float
    expected_streamed_success_probability: float
    kappa: float


def echo_transport(matrix: np.ndarray) -> EchoTransport:
    """Costed physical inverse word; deliberately separate from Tendril.deweave."""
    matrix = np.asarray(matrix, dtype=complex)
    rho = math.log(_operator_scale(matrix))
    movement = compose_word([matrix, np.linalg.inv(matrix)])
    identity_word = bell_codeword(np.eye(2))
    geometry = pairwise_quantum_geometry(
        movement.direct_codeword, identity_word
    )
    return EchoTransport(
        rho=rho,
        source_return_defect=float(
            np.linalg.norm(movement.source_product - np.eye(2), ord="fro")
        ),
        conditional_return_fidelity=geometry.root_fidelity,
        direct_success_probability=movement.direct_success_probability,
        streamed_success_probability=movement.streamed_success_probability,
        expected_streamed_success_probability=(
            movement.transmissivity * movement.direct_success_probability
        ),
        kappa=movement.kappa,
    )


def compact_frame(angle: float) -> np.ndarray:
    """Real ``SO(2)`` frame motion."""
    cosine, sine = math.cos(float(angle)), math.sin(float(angle))
    return np.array([[cosine, -sine], [sine, cosine]], dtype=float)


def _transport_report(quantum: QuantumMovement) -> TransportReport:
    remainder = TypedRemainder(
        remainder_type=RemainderKind.SCALAR,
        carrier="five-dimensional Bell-erasure density",
        metric_or_comparison="attempted-use erasure probability",
        raw_value=1.0 - quantum.bell_success_probability,
        assumptions=("fixed Bell probe", "no free classical norm side register"),
        provenance=_MANIFEST,
    )
    return TransportReport(
        edge=_BRIDGE,
        preserved=(
            "projective class [M]={M,-M}",
            "finite-rho exact-tomography coordinate",
            "compact SO(2) frame covariance",
            "success-erasure accounting",
        ),
        transformed=(
            "M -> A=M/||M||2 -> flagged density",
            "rho -> q=exp(-2rho)",
            "source chart -> pullback QFI chart",
        ),
        lost=("global sign",),
        remainder=remainder,
        evidence=_MANIFEST,
        cost=remainder.raw_value,
    )


def _validate_source_quantum_seam(
    source: SourceMovement,
    quantum: QuantumMovement,
    *,
    tolerance: float = 1e-10,
) -> None:
    """Reject local sections that do not glue to the declared R6 bridge."""
    if not isinstance(source, SourceMovement) or not isinstance(
        quantum, QuantumMovement
    ):
        raise TypeError("the quantum seam requires SourceMovement and QuantumMovement")
    expected_source = SourceMovement.from_coordinates(
        source.rho, source.phi, source.psi
    )
    source_matrix = np.asarray(source.matrix, dtype=complex)
    if (
        source_matrix.shape != (2, 2)
        or not np.all(np.isfinite(source_matrix))
        or float(np.max(np.abs(source_matrix.imag))) > tolerance
        or not np.allclose(
            source_matrix.real,
            expected_source.matrix,
            rtol=tolerance,
            atol=tolerance,
        )
        or not math.isclose(
            float(np.linalg.det(source_matrix).real),
            1.0,
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
    ):
        raise GovernanceError(
            "source section does not match its finite real SL(2,R) coordinates"
        )
    expected_quantum = QuantumMovement.from_source(expected_source)
    if (
        not math.isclose(
            quantum.q,
            expected_quantum.q,
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
        or not math.isclose(
            quantum.bell_success_probability,
            expected_quantum.bell_success_probability,
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
        or not np.allclose(
            quantum.codeword.density,
            expected_quantum.codeword.density,
            rtol=tolerance,
            atol=tolerance,
        )
    ):
        raise GovernanceError(
            "source and operational sections fail the R6 projective gluing law"
        )


def build_quantum_polycosmos(
    source: SourceMovement, quantum: QuantumMovement
) -> Polycosmos:
    """Build the smallest AION-compatible heterogeneous source/receiver seam."""
    _validate_source_quantum_seam(source, quantum)
    report = _transport_report(quantum)
    polycosmos = Polycosmos()
    polycosmos.add_worldlet(
        Worldlet(
            id=_SOURCE_WORLDLET,
            carrier="SL(2,R) Cartan movement",
            local_state=source,
            local_geometry=Geometry.SL2_ABSOLUTE_PSEUDO_VOLUME,
            algebra_regime=AlgebraRegime.REAL_MATRIX,
            clocks=("source-cartan-clock",),
            observers=("QuantumMovementOmniTool",),
            boundary="rho>=0; Q=+1 indefinite source",
            evidence_refs=(_MANIFEST,),
        )
    )
    polycosmos.add_worldlet(
        Worldlet(
            id=_QUANTUM_WORLDLET,
            carrier="5x5 Bell-erasure density",
            local_state=quantum,
            local_geometry=Geometry.DENSITY_OPERATOR_BURES,
            algebra_regime=AlgebraRegime.COMPLEX,
            clocks=("attempted-use-clock",),
            observers=("QuantumMovementOmniTool",),
            boundary="compact density-operator state space",
            energy_or_cost=report.cost,
            evidence_refs=(_MANIFEST,),
            typed_remainders=(report.remainder,),
        )
    )
    polycosmos.add_tendril(
        Tendril(
            id=_BRIDGE,
            source=_SOURCE_WORLDLET,
            target=_QUANTUM_WORLDLET,
            forward_transport="R6 Bell-erasure attempted-use instrument",
            return_transport=None,
            preserved_fields=report.preserved,
            transformed_fields=report.transformed,
            lost_fields=report.lost,
            transport_cost=report.cost,
            typed_remainder=TypedRemainder(
                remainder_type=RemainderKind.SCALAR,
                carrier="SL2-to-density projective fibre",
                metric_or_comparison="projective alias multiplicity minus one",
                raw_value=1.0,
                assumptions=("M and -M share one density",),
                provenance=_MANIFEST,
            ),
            return_absent_reason=(
                "The density identifies M with -M, and exact tomography is not a "
                "parameter-independent CPTP inverse. A physical inverse word is "
                "separately costed by echo_transport."
            ),
        )
    )
    return polycosmos


@dataclass(frozen=True)
class WeaveEvent:
    index: int
    action: str
    reason: str
    trace_distance: float | None
    evidence_tag: str = "S"
    physical_inverse: bool = False


@dataclass(frozen=True)
class QuantumMovementObservation:
    index: int
    source: SourceMovement
    quantum: QuantumMovement
    transport: TransportReport
    transition: PairwiseQuantumGeometry | None
    event: WeaveEvent
    materialization_mode: str = "compiled_whole"
    frame_id: str = "source-cartan/attempted-use"


@dataclass(frozen=True)
class OperationalInformationBracket:
    pgm: Bits
    holevo: Bits
    oracle_erasure: Bits
    log2_codewords: Bits
    codewords: int
    metrics: InformationMetrics


@dataclass(frozen=True)
class QuantumMovementTrace:
    observations: tuple[QuantumMovementObservation, ...]
    events: tuple[WeaveEvent, ...]
    information: OperationalInformationBracket
    ambient_source_slab_extent: Quantity
    manifest: str = _MANIFEST

    @property
    def source_extent(self) -> Quantity:
        """Compatibility alias; this is the ambient slab, not sampled path volume."""
        return self.ambient_source_slab_extent


class QuantumMovementOmniTool:
    """S-tier facade for dual-carrier observation and weave governance."""

    def __init__(self, weave_trace_threshold: float = 0.05):
        weave_trace_threshold = float(weave_trace_threshold)
        if not (0.0 <= weave_trace_threshold <= 1.0):
            raise ValueError("weave trace threshold must lie in [0,1]")
        self.weave_trace_threshold = weave_trace_threshold
        self.polycosmos: Polycosmos | None = None
        self._events: list[WeaveEvent] = []
        self._observations: list[QuantumMovementObservation] = []

    @property
    def events(self) -> tuple[WeaveEvent, ...]:
        return tuple(self._events)

    @property
    def observations(self) -> tuple[QuantumMovementObservation, ...]:
        return tuple(self._observations)

    def _require_bridge(self) -> Tendril:
        if self.polycosmos is None:
            raise GovernanceError("observe a movement before changing its weave")
        return self.polycosmos.tendrils[_BRIDGE]

    def weave(self, reason: str) -> WeaveEvent:
        if not reason:
            raise GovernanceError("OmniTool weave requires an audit reason")
        bridge = self._require_bridge()
        bridge.weave(reason)
        event = WeaveEvent(len(self._events), "weave", reason, None)
        self._events.append(event)
        return event

    def deweave(self, reason: str) -> WeaveEvent:
        if not reason:
            raise GovernanceError("OmniTool deweave requires an audit reason")
        bridge = self._require_bridge()
        bridge.deweave(reason)
        event = WeaveEvent(len(self._events), "deweave", reason, None)
        self._events.append(event)
        return event

    def observe(
        self,
        rho: float,
        phi: float,
        psi: float,
        *,
        materialization_mode: str = "compiled_whole",
    ) -> QuantumMovementObservation:
        if materialization_mode != "compiled_whole":
            raise ValueError(
                "only compiled_whole observations are implemented; "
                "materialized prefixes require compose_word telemetry"
            )
        source = SourceMovement.from_coordinates(rho, phi, psi)
        quantum = QuantumMovement.from_source(source)
        report = _transport_report(quantum)
        transition = None
        if not self._observations:
            action = "weave"
            reason = "initial dual-carrier observation"
        else:
            transition = pairwise_quantum_geometry(
                self._observations[-1].quantum.codeword, quantum.codeword
            )
            if transition.trace_distance >= self.weave_trace_threshold:
                action = "weave"
                reason = (
                    "operational transition "
                    f"{transition.trace_distance:.12g} >= "
                    f"{self.weave_trace_threshold:.12g}"
                )
            else:
                action = "deweave"
                reason = (
                    "operational transition "
                    f"{transition.trace_distance:.12g} < "
                    f"{self.weave_trace_threshold:.12g}"
                )
        event = WeaveEvent(
            index=len(self._events),
            action=action,
            reason=reason,
            trace_distance=(
                None if transition is None else transition.trace_distance
            ),
        )
        if self.polycosmos is None:
            self.polycosmos = build_quantum_polycosmos(source, quantum)
        else:
            self.polycosmos.worldlets[_SOURCE_WORLDLET].local_state = source
            operational = self.polycosmos.worldlets[_QUANTUM_WORLDLET]
            operational.local_state = quantum
            operational.energy_or_cost = report.cost
            operational.typed_remainders = (report.remainder,)
            bridge = self.polycosmos.tendrils[_BRIDGE]
            bridge.transport_cost = report.cost
            if action == "weave":
                bridge.weave(reason)
            else:
                bridge.deweave(reason)
        self._events.append(event)
        observation = QuantumMovementObservation(
            index=len(self._observations),
            source=source,
            quantum=quantum,
            transport=report,
            transition=transition,
            event=event,
            materialization_mode=materialization_mode,
        )
        self._observations.append(observation)
        return observation

    def observe_path(
        self,
        coordinates: Iterable[Sequence[float]],
        *,
        materialization_mode: str = "compiled_whole",
    ) -> QuantumMovementTrace:
        if self._events or self._observations or self.polycosmos is not None:
            raise GovernanceError(
                "movement traces are append-once; use a fresh OmniTool for a new path"
            )
        for coordinate in coordinates:
            if len(coordinate) != 3:
                raise ValueError("each path point must be (rho,phi,psi)")
            self.observe(
                float(coordinate[0]),
                float(coordinate[1]),
                float(coordinate[2]),
                materialization_mode=materialization_mode,
            )
        if not self._observations:
            raise ValueError("movement path must not be empty")
        unique: list[BellCodeword] = []
        for observation in self._observations:
            if all(
                trace_distance(observation.quantum.codeword.density, prior.density)
                >= 1e-10
                for prior in unique
            ):
                unique.append(observation.quantum.codeword)
        metrics = information_metrics(unique)
        base = "r8-frozen-uniform-path-ensemble"
        bracket = OperationalInformationBracket(
            pgm=Bits(metrics.pgm_mutual_information, base=base),
            holevo=Bits(metrics.holevo_information, base=base),
            oracle_erasure=Bits(metrics.oracle_erasure_information, base=base),
            log2_codewords=Bits(metrics.log2_codewords, base=base),
            codewords=len(unique),
            metrics=metrics,
        )
        maximum_rho = max(item.source.rho for item in self._observations)
        return QuantumMovementTrace(
            observations=tuple(self._observations),
            events=tuple(self._events),
            information=bracket,
            ambient_source_slab_extent=Quantity(
                slab_volume(maximum_rho),
                unit="absolute-pseudo-volume",
                base="SL2-Cartan-source",
            ),
        )
