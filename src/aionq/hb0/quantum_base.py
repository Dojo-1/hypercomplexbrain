"""A fixed-width quantum shadow of the universal Poincare ``H4`` base.

The base, its Euclidean curvature control, and quantum distinguishability are
different carriers.  This module supplies a typed bridge between them; it does
not identify their metrics.

For ``x = r u`` in the open four-ball, identify ``u in S3`` with the normalized
spinor ``z = (u0 + i u1, u2 + i u3)`` and encode

    rho_x = (1-r)|flag><flag| (+) r |z><z|.

The radius is exactly recoverable.  The global phase of ``z`` is not: this is
the Hopf quotient ``S3 -> CP1`` and gives an explicit one-dimensional kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from .core import CarrierMismatch, RemainderEnvelope, _finite
from .hyperbolic import (
    EuclideanBaseControl,
    PoincareBallBase,
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
)

__all__ = [
    "DataProcessingReport",
    "HopfDifferentialReport",
    "HopfKernelReport",
    "HopfUnitaryChart",
    "HyperbolicQuantumBase",
    "HyperbolicQuantumPoint",
    "QuantumPairGeometry",
    "TransportCovarianceReport",
    "quantum_root_fidelity",
    "quantum_trace_distance",
]


def _readonly_complex(value) -> np.ndarray:
    contiguous = np.ascontiguousarray(value, dtype=complex)
    return np.frombuffer(
        contiguous.tobytes(),
        dtype=complex,
    ).reshape(contiguous.shape)


def _readonly_real(value) -> np.ndarray:
    contiguous = np.ascontiguousarray(value, dtype=float)
    return np.frombuffer(contiguous.tobytes(), dtype=float).reshape(contiguous.shape)


def _numerical_tolerance(
    value: float,
    name: str = "tolerance",
    maximum: float = 1e-6,
) -> float:
    tolerance = _finite(value, name)
    if tolerance <= 0.0 or tolerance > maximum:
        raise GovernanceError(f"{name} must lie in (0, {maximum}]")
    return tolerance


def _density(value, tolerance: float, name: str = "density") -> np.ndarray:
    tolerance = _numerical_tolerance(tolerance, f"{name}.tolerance")
    density = np.array(value, dtype=complex, copy=True)
    if density.ndim != 2 or density.shape[0] != density.shape[1]:
        raise GovernanceError(f"{name} must be a square matrix")
    if not np.all(np.isfinite(density)):
        raise GovernanceError(f"{name} contains a non-finite coordinate")
    hermitian_defect = float(np.linalg.norm(density - density.conj().T, ord="fro"))
    if hermitian_defect > tolerance:
        raise GovernanceError(f"{name} must be Hermitian")
    density = 0.5 * (density + density.conj().T)
    eigenvalues = np.linalg.eigvalsh(density)
    if float(np.min(eigenvalues)) < -tolerance:
        raise GovernanceError(f"{name} must be positive semidefinite")
    trace = complex(np.trace(density))
    if abs(trace.imag) > tolerance or abs(trace.real - 1.0) > tolerance:
        raise GovernanceError(f"{name} must have trace one")
    return _readonly_complex(density)


def _psd_sqrt(value: np.ndarray, tolerance: float) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(
        0.5 * (value + value.conj().T)
    )
    if float(np.min(eigenvalues)) < -tolerance:
        raise GovernanceError("PSD square root received a non-positive matrix")
    # Tolerance governs rejection of negative roundoff, not erasure of small
    # positive spectral weight.  The latter carries real low-probability
    # distinguishability near the compactified boundary.
    clipped = np.maximum(eigenvalues, 0.0)
    return (eigenvectors * np.sqrt(clipped)) @ eigenvectors.conj().T


def quantum_trace_distance(left, right, tolerance: float = 1e-10) -> float:
    tolerance = _numerical_tolerance(tolerance, "trace_distance.tolerance")
    left = _density(left, tolerance, "trace_distance.left")
    right = _density(right, tolerance, "trace_distance.right")
    if left.shape != right.shape:
        raise CarrierMismatch("trace-distance densities need the same dimension")
    eigenvalues = np.linalg.eigvalsh(left - right)
    return _finite(0.5 * float(np.sum(np.abs(eigenvalues))), "trace distance")


def quantum_root_fidelity(left, right, tolerance: float = 1e-10) -> float:
    tolerance = _numerical_tolerance(tolerance, "root_fidelity.tolerance")
    left = _density(left, tolerance, "root_fidelity.left")
    right = _density(right, tolerance, "root_fidelity.right")
    if left.shape != right.shape:
        raise CarrierMismatch("fidelity densities need the same dimension")
    root_left = _psd_sqrt(left, tolerance)
    root_right = _psd_sqrt(right, tolerance)
    value = float(
        np.sum(
            np.linalg.svd(
                root_left @ root_right,
                compute_uv=False,
            )
        )
    )
    if value < -tolerance or value > 1.0 + 64.0 * tolerance:
        raise GovernanceError("root fidelity left its physical interval")
    return float(min(1.0, max(0.0, value)))


@dataclass(frozen=True)
class HyperbolicQuantumPoint:
    base_id: str
    base_point: np.ndarray
    density: np.ndarray
    ball_radius: float
    hyperbolic_radius: float
    curvature_radius: float

    def __post_init__(self) -> None:
        if self.base_id != UNIVERSAL_POINCARE_BASE.id:
            raise CarrierMismatch(
                "a hyperbolic quantum point must be bound to the canonical "
                f"{UNIVERSAL_POINCARE_BASE.id!r} base"
            )
        point = np.array(self.base_point, dtype=float, copy=True)
        if point.shape != (4,) or not np.all(np.isfinite(point)):
            raise GovernanceError("a hyperbolic quantum point needs one finite R4 point")
        radius = _finite(self.ball_radius, "quantum_point.ball_radius")
        hyperbolic = _finite(
            self.hyperbolic_radius,
            "quantum_point.hyperbolic_radius",
        )
        curvature_radius = _finite(
            self.curvature_radius,
            "quantum_point.curvature_radius",
        )
        if radius < 0.0 or radius >= 1.0:
            raise GovernanceError("quantum-point radius must lie in [0, 1)")
        if abs(float(np.linalg.norm(point)) - radius) > 1e-9:
            raise GovernanceError("quantum-point radius disagrees with its base point")
        if hyperbolic < 0.0:
            raise GovernanceError("quantum-point hyperbolic radius must be non-negative")
        if curvature_radius != UNIVERSAL_POINCARE_BASE.radius:
            raise CarrierMismatch(
                "quantum-point curvature radius does not belong to the canonical "
                "Poincare H4 base"
            )
        if radius == 0.0:
            spinor = np.array([1.0 + 0.0j, 0.0 + 0.0j])
        else:
            direction = point / radius
            spinor = np.array(
                [
                    direction[0] + 1j * direction[1],
                    direction[2] + 1j * direction[3],
                ]
            )
        expected_density = np.zeros((3, 3), dtype=complex)
        expected_density[0, 0] = 1.0 - radius
        expected_density[1:, 1:] = radius * np.outer(spinor, spinor.conj())
        supplied_density = _density(self.density, 1e-9)
        if np.linalg.norm(supplied_density - expected_density, ord="fro") > 1e-9:
            raise GovernanceError(
                "quantum-point density disagrees with the declared Hopf encoding"
            )
        expected_hyperbolic = 2.0 * curvature_radius * math.atanh(radius)
        if abs(hyperbolic - expected_hyperbolic) > 1e-9 * max(
            1.0,
            expected_hyperbolic,
        ):
            raise GovernanceError(
                "quantum-point hyperbolic radius disagrees with its base point"
            )
        object.__setattr__(self, "base_point", _readonly_real(point))
        object.__setattr__(self, "density", _readonly_complex(expected_density))
        object.__setattr__(self, "ball_radius", radius)
        object.__setattr__(self, "hyperbolic_radius", expected_hyperbolic)
        object.__setattr__(self, "curvature_radius", curvature_radius)


@dataclass(frozen=True)
class QuantumPairGeometry:
    """Heterogeneous observations; deliberately no aggregate score."""

    hyperbolic_distance: float
    euclidean_control_distance: float
    trace_distance: float
    root_fidelity: float
    bures_distance: float


@dataclass(frozen=True)
class HopfKernelReport:
    phase: float
    source_hyperbolic_distance: float
    source_euclidean_distance: float
    quantum_trace_distance: float
    quantum_root_fidelity: float
    remainder: RemainderEnvelope


@dataclass(frozen=True)
class HopfDifferentialReport:
    rank: int
    singular_values: np.ndarray
    rank_cutoff: float
    phase_tangent: np.ndarray
    phase_directional_defect: float
    finite_difference_step: float
    finite_difference_defect: float


@dataclass(frozen=True)
class TransportCovarianceReport:
    left_hyperbolic_defect: float
    pair_hyperbolic_defect: float
    pair_euclidean_defect: float
    density_intertwining_defect: float
    trace_distance_defect: float
    root_fidelity_defect: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return max(
            self.left_hyperbolic_defect,
            self.pair_hyperbolic_defect,
            self.pair_euclidean_defect,
            self.density_intertwining_defect,
            self.trace_distance_defect,
            self.root_fidelity_defect,
        ) <= self.tolerance


@dataclass(frozen=True)
class DataProcessingReport:
    input_trace_distance: float
    output_trace_distance: float
    input_root_fidelity: float
    output_root_fidelity: float
    tolerance: float

    @property
    def contractive(self) -> bool:
        return (
            self.output_trace_distance <= self.input_trace_distance + self.tolerance
            and self.output_root_fidelity + self.tolerance >= self.input_root_fidelity
        )


@dataclass(frozen=True)
class HopfUnitaryChart:
    """An origin-preserving ``U(2)`` subgroup acting on the Hopf spinor."""

    unitary: np.ndarray
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "hopf_chart.tolerance",
            maximum=1e-10,
        )
        unitary = np.array(self.unitary, dtype=complex, copy=True)
        if unitary.shape != (2, 2) or not np.all(np.isfinite(unitary)):
            raise GovernanceError("a Hopf chart needs one finite 2 x 2 matrix")
        eye = np.eye(2)
        if max(
            float(np.linalg.norm(unitary.conj().T @ unitary - eye, ord="fro")),
            float(np.linalg.norm(unitary @ unitary.conj().T - eye, ord="fro")),
        ) > tolerance:
            raise GovernanceError("a Hopf chart must be unitary")
        object.__setattr__(self, "unitary", _readonly_complex(unitary))
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def real_matrix(self) -> np.ndarray:
        columns = []
        for index in range(4):
            basis = np.zeros(4)
            basis[index] = 1.0
            spinor = np.array(
                [basis[0] + 1j * basis[1], basis[2] + 1j * basis[3]]
            )
            moved = self.unitary @ spinor
            columns.append(
                np.array([moved[0].real, moved[0].imag, moved[1].real, moved[1].imag])
            )
        return _readonly_real(np.column_stack(columns))

    @property
    def qutrit_unitary(self) -> np.ndarray:
        lifted = np.eye(3, dtype=complex)
        lifted[1:, 1:] = self.unitary
        return _readonly_complex(lifted)


@dataclass(frozen=True)
class HyperbolicQuantumBase:
    base: PoincareBallBase = UNIVERSAL_POINCARE_BASE
    euclidean_control: EuclideanBaseControl = UNIVERSAL_EUCLIDEAN_CONTROL
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "hyperbolic_quantum_base.tolerance",
            maximum=1e-10,
        )
        if (
            type(self.base) is not PoincareBallBase
            or self.base.to_spec() != UNIVERSAL_POINCARE_BASE.to_spec()
        ):
            raise CarrierMismatch(
                "the Hopf quantum shadow requires the exact canonical "
                "universal Poincare H4 specification"
            )
        if (
            type(self.euclidean_control) is not EuclideanBaseControl
            or self.euclidean_control.to_spec()
            != UNIVERSAL_EUCLIDEAN_CONTROL.to_spec()
        ):
            raise CarrierMismatch(
                "the Hopf quantum shadow requires the exact canonical "
                "origin-matched Euclidean R4 control specification"
            )
        if not np.allclose(
            self.base.metric_tensor(np.zeros(4)),
            self.euclidean_control.metric_tensor,
            rtol=0.0,
            atol=tolerance,
        ):
            raise GovernanceError(
                "the Euclidean control must match the hyperbolic origin tangent metric"
            )
        object.__setattr__(self, "tolerance", tolerance)

    @staticmethod
    def _spinor(point: np.ndarray) -> tuple[float, np.ndarray]:
        radius = math.hypot(*(float(coordinate) for coordinate in point))
        if radius == 0.0:
            return radius, np.array([1.0 + 0.0j, 0.0 + 0.0j])
        direction = point / radius
        return radius, np.array(
            [direction[0] + 1j * direction[1], direction[2] + 1j * direction[3]]
        )

    def encode(self, point) -> HyperbolicQuantumPoint:
        point = self.base.point(point, "hyperbolic_quantum.point")
        radius, spinor = self._spinor(point)
        density = np.zeros((3, 3), dtype=complex)
        density[0, 0] = 1.0 - radius
        density[1:, 1:] = radius * np.outer(spinor, spinor.conj())
        density = _density(density, self.tolerance, "hyperbolic_quantum.density")
        hyperbolic_radius = self.base.distance(np.zeros(4), point)
        return HyperbolicQuantumPoint(
            base_id=self.base.id,
            base_point=point,
            density=density,
            ball_radius=radius,
            hyperbolic_radius=hyperbolic_radius,
            curvature_radius=self.base.radius,
        )

    def _hopf_image_radius(
        self,
        value: HyperbolicQuantumPoint | np.ndarray,
    ) -> float:
        """Recover ``r`` only from a point or density on this exact open image."""

        if isinstance(value, HyperbolicQuantumPoint):
            if value.base_id != self.base.id:
                raise CarrierMismatch(
                    "typed quantum point belongs to a different hyperbolic base"
                )
            return value.ball_radius

        density = _density(value, self.tolerance, "recover_radius.density")
        if density.shape != (3, 3):
            raise CarrierMismatch("the Hopf shadow uses qutrit densities")
        radius = _finite(
            float(np.trace(density[1:, 1:]).real),
            "recovered radius",
        )
        if radius < 0.0 or radius >= 1.0:
            raise CarrierMismatch(
                "density lies outside the open radial range of the Hopf image"
            )

        structural_tolerance = (
            256.0
            * np.finfo(float).eps
            * max(1.0, float(np.linalg.norm(density, ord="fro")))
        )
        coherence_defect = float(
            max(
                np.linalg.norm(density[0, 1:]),
                np.linalg.norm(density[1:, 0]),
            )
        )
        if coherence_defect > structural_tolerance:
            raise CarrierMismatch(
                "density has flag-spin coherences outside the Hopf image"
            )
        if abs(float(density[0, 0].real) - (1.0 - radius)) > structural_tolerance:
            raise CarrierMismatch(
                "density flag weight disagrees with its radial spin weight"
            )

        spin_eigenvalues = np.linalg.eigvalsh(density[1:, 1:])
        if abs(float(spin_eigenvalues[0])) > structural_tolerance:
            raise CarrierMismatch(
                "density spin block has rank greater than one and is outside "
                "the Hopf image"
            )
        return radius

    def recover_ball_radius(
        self,
        value: HyperbolicQuantumPoint | np.ndarray,
    ) -> float:
        return self._hopf_image_radius(value)

    def recover_hyperbolic_radius(
        self,
        value: HyperbolicQuantumPoint | np.ndarray,
    ) -> float:
        radius = self._hopf_image_radius(value)
        return _finite(
            2.0 * self.base.radius * math.atanh(radius),
            "recovered hyperbolic radius",
        )

    def compare(self, left, right) -> QuantumPairGeometry:
        left_encoded = self.encode(left)
        right_encoded = self.encode(right)
        trace = quantum_trace_distance(
            left_encoded.density,
            right_encoded.density,
            self.tolerance,
        )
        fidelity = quantum_root_fidelity(
            left_encoded.density,
            right_encoded.density,
            self.tolerance,
        )
        return QuantumPairGeometry(
            hyperbolic_distance=self.base.distance(left, right),
            euclidean_control_distance=self.euclidean_control.distance(left, right),
            trace_distance=trace,
            root_fidelity=fidelity,
            bures_distance=math.sqrt(max(0.0, 2.0 * (1.0 - fidelity))),
        )

    def phase_rotate(self, point, phase: float) -> np.ndarray:
        point = self.base.point(point, "hopf_phase.point")
        phase = _finite(phase, "hopf_phase.phase")
        radius, spinor = self._spinor(point)
        if radius == 0.0:
            return point
        moved = np.exp(1j * phase) * spinor
        return self.base.point(
            radius
            * np.array(
                [moved[0].real, moved[0].imag, moved[1].real, moved[1].imag]
            ),
            "hopf_phase.output",
        )

    def hopf_kernel(self, point, phase: float) -> HopfKernelReport:
        point = self.base.point(point, "hopf_kernel.point")
        moved = self.phase_rotate(point, phase)
        source_h = self.base.distance(point, moved)
        source_e = self.euclidean_control.distance(point, moved)
        if source_h <= self.tolerance:
            raise GovernanceError(
                "a Hopf-kernel witness needs a nontrivial source phase orbit"
            )
        left = self.encode(point).density
        right = self.encode(moved).density
        trace = quantum_trace_distance(left, right, self.tolerance)
        fidelity = quantum_root_fidelity(left, right, self.tolerance)
        if trace > 64.0 * self.tolerance:
            raise GovernanceError("the declared Hopf phase did not lie in the quantum kernel")
        remainder = RemainderEnvelope(
            name="[R]_hopf_phase",
            channel="transport",
            carrier=f"{self.base.id}->qutrit-density",
            evidence_tag=EvidenceTag.MEASURED,
            statement=(
                "the physical density aliases a U(1) orbit of distinct H4 base points"
            ),
            instrument="source-distance-versus-density-trace-distance",
            magnitude=source_h,
            assumptions=(
                "open Poincare H4 ball",
                "fixed qutrit Hopf encoding",
                "global spinor phase is not an observable",
            ),
            provenance="aionq.hb0.quantum_base.HyperbolicQuantumBase.hopf_kernel",
        )
        return HopfKernelReport(
            phase=_finite(phase, "hopf_kernel.phase"),
            source_hyperbolic_distance=source_h,
            source_euclidean_distance=source_e,
            quantum_trace_distance=trace,
            quantum_root_fidelity=fidelity,
            remainder=remainder,
        )

    def differential(self, point, step: float = 1e-6) -> HopfDifferentialReport:
        point = self.base.point(point, "hopf_differential.point")
        step = _finite(step, "hopf_differential.step")
        radius = float(np.linalg.norm(point))
        if step <= 0.0 or radius <= 32.0 * step or radius + 32.0 * step >= 1.0:
            raise GovernanceError("differential point/step is outside the interior chart")
        radius, spinor = self._spinor(point)
        analytic_columns = []
        finite_columns = []
        for index in range(4):
            direction = np.zeros(4)
            direction[index] = 1.0
            dr = float(point @ direction) / radius
            direction_spinor = np.array(
                [
                    direction[0] + 1j * direction[1],
                    direction[2] + 1j * direction[3],
                ]
            )
            dz = (direction_spinor - spinor * dr) / radius
            derivative = np.zeros((3, 3), dtype=complex)
            derivative[0, 0] = -dr
            derivative[1:, 1:] = (
                dr * np.outer(spinor, spinor.conj())
                + radius
                * (
                    np.outer(dz, spinor.conj())
                    + np.outer(spinor, dz.conj())
                )
            )
            analytic_columns.append(
                np.concatenate(
                    (derivative.real.reshape(-1), derivative.imag.reshape(-1))
                )
            )
            delta = step * direction
            finite = (
                self.encode(point + delta).density
                - self.encode(point - delta).density
            ) / (2.0 * step)
            finite_columns.append(
                np.concatenate((finite.real.reshape(-1), finite.imag.reshape(-1)))
            )
        jacobian = np.column_stack(analytic_columns)
        finite_jacobian = np.column_stack(finite_columns)
        singular_values = np.linalg.svd(jacobian, compute_uv=False)
        cutoff = (
            512.0
            * np.finfo(float).eps
            * max(jacobian.shape)
            * max(1.0, float(singular_values[0]))
        )
        rank = int(np.count_nonzero(singular_values > cutoff))
        phase_tangent = np.array([-point[1], point[0], -point[3], point[2]])
        directional = jacobian @ phase_tangent
        return HopfDifferentialReport(
            rank=rank,
            singular_values=_readonly_real(singular_values),
            rank_cutoff=float(cutoff),
            phase_tangent=_readonly_real(phase_tangent),
            phase_directional_defect=float(np.linalg.norm(directional)),
            finite_difference_step=step,
            finite_difference_defect=float(
                np.linalg.norm(finite_jacobian - jacobian, ord=2)
            ),
        )

    def transport_point(self, point, chart: HopfUnitaryChart) -> np.ndarray:
        if not isinstance(chart, HopfUnitaryChart):
            raise GovernanceError("quantum-base transport needs a HopfUnitaryChart")
        point = self.base.point(point, "hopf_transport.point")
        return self.base.point(chart.real_matrix @ point, "hopf_transport.output")

    def transport_density(self, density, chart: HopfUnitaryChart) -> np.ndarray:
        density = _density(density, self.tolerance, "hopf_transport.density")
        if density.shape != (3, 3):
            raise CarrierMismatch("Hopf transport acts on qutrit densities")
        lifted = chart.qutrit_unitary
        return _density(
            lifted @ density @ lifted.conj().T,
            self.tolerance,
            "hopf_transport.output_density",
        )

    def covariance(
        self,
        left,
        right,
        chart: HopfUnitaryChart,
    ) -> TransportCovarianceReport:
        left = self.base.point(left, "covariance.left")
        right = self.base.point(right, "covariance.right")
        moved_left = self.transport_point(left, chart)
        moved_right = self.transport_point(right, chart)
        before = self.compare(left, right)
        after = self.compare(moved_left, moved_right)
        encoded_left = self.encode(left)
        transported_density = self.transport_density(encoded_left.density, chart)
        moved_density = self.encode(moved_left).density
        return TransportCovarianceReport(
            left_hyperbolic_defect=abs(
                self.base.distance(np.zeros(4), left)
                - self.base.distance(np.zeros(4), moved_left)
            ),
            pair_hyperbolic_defect=abs(
                before.hyperbolic_distance - after.hyperbolic_distance
            ),
            pair_euclidean_defect=abs(
                before.euclidean_control_distance
                - after.euclidean_control_distance
            ),
            density_intertwining_defect=float(
                np.linalg.norm(transported_density - moved_density, ord="fro")
            ),
            trace_distance_defect=abs(before.trace_distance - after.trace_distance),
            root_fidelity_defect=abs(before.root_fidelity - after.root_fidelity),
            tolerance=self.tolerance,
        )

    def dephase(self, density) -> np.ndarray:
        density = _density(density, self.tolerance, "dephase.input")
        if density.shape != (3, 3):
            raise CarrierMismatch("the fixed dephasing control acts on qutrits")
        return _density(
            np.diag(np.diag(density)),
            self.tolerance,
            "dephase.output",
        )

    def data_processing(self, left, right) -> DataProcessingReport:
        left_density = self.encode(left).density
        right_density = self.encode(right).density
        out_left = self.dephase(left_density)
        out_right = self.dephase(right_density)
        return DataProcessingReport(
            input_trace_distance=quantum_trace_distance(
                left_density, right_density, self.tolerance
            ),
            output_trace_distance=quantum_trace_distance(
                out_left, out_right, self.tolerance
            ),
            input_root_fidelity=quantum_root_fidelity(
                left_density, right_density, self.tolerance
            ),
            output_root_fidelity=quantum_root_fidelity(
                out_left, out_right, self.tolerance
            ),
            tolerance=self.tolerance,
        )
