"""QB2: a positive-chiral spin connection over the universal ``H4`` base.

This module keeps three carriers separate:

* points and Levi-Civita transport live on the Riemannian Poincare ``H4`` base;
* the positive-chiral spin fiber is one compact ``SU(2)`` qubit;
* the NNN sectional ``SO(2,2)`` carrier is an explicit nonunitary ablation.

The compact fiber is not a finite-dimensional unitary representation of the
noncompact ``H4`` isometry group.  It is the ``SU(2)+`` projection of tangent
frame holonomy along a declared path.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Sequence

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from ..hyperbolic import PoincareBallBase, UNIVERSAL_POINCARE_BASE
from ..hyperbolic_qubit import so22_generators
from .core import CarrierMismatch, RemainderEnvelope, _finite
from .quantum_base import (
    _numerical_tolerance,
    _readonly_complex,
    _readonly_real,
    quantum_root_fidelity,
    quantum_trace_distance,
)

__all__ = [
    "CentralLiftProbeReport",
    "ChiralCurvatureSpanReport",
    "ChiralSpinConnection",
    "ChiralSpinLink",
    "QiskitProjectionUnavailable",
    "QiskitSpinProjectionReport",
    "SectionalAcceleratorBoundary",
    "SectionalBoundaryReport",
    "SectionalRefinementReport",
    "SpinHolonomyReport",
    "SpinPathReport",
    "TriangleCurvatureReport",
    "probe_central_lift_qiskit",
    "project_spin_path_to_qiskit",
    "spinor_preparation_unitary",
]


_PAULI = np.array(
    [
        [[0.0, 1.0], [1.0, 0.0]],
        [[0.0, -1.0j], [1.0j, 0.0]],
        [[1.0, 0.0], [0.0, -1.0]],
    ],
    dtype=complex,
)
_LORENTZ_41 = np.diag([-1.0, 1.0, 1.0, 1.0, 1.0])
_SPLIT_22 = np.diag([1.0, 1.0, -1.0, -1.0])
_GEN100_PHASE = 1.2368
_GEN100_JITTER = 0.19685006
_GEN100_PERLIN_SEED = 0x0B62C6DD


def _universal_h4(base: PoincareBallBase, name: str) -> PoincareBallBase:
    """Require the one exact geometric base declared by the HB0 architecture."""

    if type(base) is not PoincareBallBase:
        raise CarrierMismatch(f"{name} requires a Poincare-ball base")
    if base.to_spec() != UNIVERSAL_POINCARE_BASE.to_spec():
        raise CarrierMismatch(
            f"{name} requires the exact AION universal Poincare H4 base"
        )
    return base


def _epsilon3(left: int, middle: int, right: int) -> float:
    if len({left, middle, right}) != 3:
        return 0.0
    inversions = int(left > middle) + int(left > right) + int(middle > right)
    return -1.0 if inversions % 2 else 1.0


def _self_dual_symbols() -> np.ndarray:
    """Self-dual 't Hooft symbols in the orientation ``epsilon_1234=+1``."""

    symbols = np.zeros((3, 4, 4), dtype=float)
    for index in range(3):
        for left in range(3):
            for right in range(3):
                symbols[index, left, right] = _epsilon3(index, left, right)
        symbols[index, index, 3] = 1.0
        symbols[index, 3, index] = -1.0
    return symbols


_SELF_DUAL = _self_dual_symbols()


def _su2(value, tolerance: float, name: str = "su2") -> np.ndarray:
    """Validate one matrix as ``SU(2)`` without repairing it."""

    tolerance = _numerical_tolerance(
        tolerance,
        f"{name}.tolerance",
        maximum=1e-10,
    )
    unitary = np.array(value, dtype=complex, copy=True)
    if unitary.shape != (2, 2) or not np.all(np.isfinite(unitary)):
        raise GovernanceError(f"{name} must be one finite 2 x 2 matrix")
    identity = np.eye(2, dtype=complex)
    defect = max(
        float(np.linalg.norm(unitary.conj().T @ unitary - identity, ord="fro")),
        float(np.linalg.norm(unitary @ unitary.conj().T - identity, ord="fro")),
    )
    determinant_defect = abs(complex(np.linalg.det(unitary)) - 1.0)
    if defect > tolerance:
        raise GovernanceError(f"{name} is not unitary")
    if determinant_defect > tolerance:
        raise GovernanceError(f"{name} does not have determinant one")
    return _readonly_complex(unitary)


def _strict_density(value, tolerance: float, name: str = "density") -> np.ndarray:
    """Validate a density without clipping, normalising, or symmetrising it."""

    tolerance = _numerical_tolerance(
        tolerance,
        f"{name}.tolerance",
        maximum=1e-10,
    )
    density = np.array(value, dtype=complex, copy=True)
    if density.ndim != 2 or density.shape[0] != density.shape[1]:
        raise GovernanceError(f"{name} must be a square matrix")
    if not np.all(np.isfinite(density)):
        raise GovernanceError(f"{name} contains a non-finite coordinate")
    hermitian_defect = float(
        np.linalg.norm(density - density.conj().T, ord="fro")
    )
    if hermitian_defect > tolerance:
        raise GovernanceError(f"{name} must be Hermitian")
    hermitian_view = 0.5 * (density + density.conj().T)
    if float(np.min(np.linalg.eigvalsh(hermitian_view))) < -tolerance:
        raise GovernanceError(f"{name} must be positive semidefinite")
    trace = complex(np.trace(density))
    if abs(trace.imag) > tolerance or abs(trace.real - 1.0) > tolerance:
        raise GovernanceError(f"{name} must have trace one")
    return _readonly_complex(density)


def _normalised_spinor(
    value,
    tolerance: float,
    name: str = "spinor",
) -> np.ndarray:
    tolerance = _numerical_tolerance(
        tolerance,
        f"{name}.tolerance",
        maximum=1e-10,
    )
    spinor = np.array(value, dtype=complex, copy=True)
    if spinor.shape != (2,) or not np.all(np.isfinite(spinor)):
        raise GovernanceError(f"{name} must be one finite two-amplitude spinor")
    norm = float(np.linalg.norm(spinor))
    if abs(norm - 1.0) > tolerance:
        raise GovernanceError(f"{name} must already be normalised")
    return _readonly_complex(spinor)


def _canonical_tetrad(base: PoincareBallBase, point) -> np.ndarray:
    """Canonical oriented orthonormal ``H4`` frame in the hyperboloid carrier."""

    point = base.point(point, "spin_tetrad.point")
    margin = 1.0 - float(point @ point)
    if margin <= 0.0:
        raise GovernanceError("spin tetrad needs an interior H4 point")
    frame = np.zeros((5, 4), dtype=float)
    frame[0, :] = 2.0 * point / margin
    frame[1:, :] = np.eye(4) + 2.0 * np.outer(point, point) / margin
    defect = float(
        np.linalg.norm(frame.T @ _LORENTZ_41 @ frame - np.eye(4), ord="fro")
    )
    if defect > 64.0 * base.tolerance:
        raise GovernanceError("canonical H4 tetrad failed orthonormality")
    return frame


def _frame_rotation(
    base: PoincareBallBase,
    source: np.ndarray,
    target: np.ndarray,
) -> np.ndarray:
    """Levi-Civita frame comparison built from the existing base transporter."""

    source_lift = base.to_hyperboloid(source)
    target_lift = base.to_hyperboloid(target)
    source_frame = _canonical_tetrad(base, source)
    target_frame = _canonical_tetrad(base, target)
    transported = np.column_stack(
        [
            base.parallel_transport(source_lift, target_lift, source_frame[:, index])
            for index in range(4)
        ]
    )
    rotation = target_frame.T @ _LORENTZ_41 @ transported
    return _readonly_real(rotation)


def _self_dual_rotation(rotation: np.ndarray) -> np.ndarray:
    """Positive-chiral ``SO(3)`` adjoint of one oriented ``SO(4)`` frame map."""

    output = np.empty((3, 3), dtype=float)
    for column in range(3):
        moved = rotation @ _SELF_DUAL[column] @ rotation.T
        for row in range(3):
            output[row, column] = 0.25 * float(
                np.sum(_SELF_DUAL[row] * moved)
            )
    return _readonly_real(output)


def _bloch_rotation(unitary: np.ndarray) -> tuple[np.ndarray, float]:
    output = np.empty((3, 3), dtype=float)
    imaginary_defect = 0.0
    for column in range(3):
        moved = unitary @ _PAULI[column] @ unitary.conj().T
        for row in range(3):
            value = 0.5 * complex(np.trace(_PAULI[row] @ moved))
            output[row, column] = value.real
            imaginary_defect = max(imaginary_defect, abs(value.imag))
    return _readonly_real(output), float(imaginary_defect)


def _omitted_chirality_remainder() -> RemainderEnvelope:
    return RemainderEnvelope(
        name="[R]_negative_chirality",
        channel="transport",
        carrier="Spin(4)->SU(2)-",
        evidence_tag=EvidenceTag.SEMANTIC,
        statement=(
            "QB2 instantiates only the positive self-dual SU(2)+ factor; the "
            "negative-chiral SU(2)- connection remains outside this slice"
        ),
        assumptions=(
            "oriented Riemannian H4 tangent bundle",
            "Spin(4)=SU(2)+ x SU(2)-",
        ),
        provenance="aionq.hb0.chiral_spin.ChiralSpinConnection",
    )


def _split_substrate_remainder() -> RemainderEnvelope:
    return RemainderEnvelope(
        name="[R]_split_signature_substrate",
        channel="transport",
        carrier="SO(2,2)->one-qubit-SU(2)",
        evidence_tag=EvidenceTag.PROVED,
        statement=(
            "a nonzero SO(2,2) boost preserves the split form but is not a "
            "finite-dimensional Hilbert-unitary qubit gate"
        ),
        assumptions=(
            "real split form diag(+,+,-,-)",
            "standard positive-definite qubit inner product",
        ),
        provenance=(
            "aionq.hb0.chiral_spin.SectionalAcceleratorBoundary.audit"
        ),
    )


@dataclass(frozen=True)
class ChiralSpinLink:
    """One continuously signed positive-chiral geodesic link."""

    base_id: str
    curvature_radius: float
    source: np.ndarray
    target: np.ndarray
    unitary: np.ndarray
    tangent_rotation: np.ndarray
    chiral_rotation: np.ndarray
    base_distance: float
    scalar_part: float
    bivector: np.ndarray
    conditioning_error: float
    tangent_orthogonality_defect: float
    tangent_determinant_defect: float
    unitary_defect: float
    determinant_defect: float
    spin_intertwining_defect: float
    bloch_imaginary_defect: float
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "chiral_spin_link.tolerance",
            maximum=1e-10,
        )
        if self.base_id != UNIVERSAL_POINCARE_BASE.id:
            raise CarrierMismatch(
                "a chiral spin link must use the universal Poincare H4 base id"
            )
        radius = _finite(
            self.curvature_radius,
            "chiral_spin_link.curvature_radius",
        )
        if radius != UNIVERSAL_POINCARE_BASE.radius:
            raise CarrierMismatch(
                "a chiral spin link must use the universal Poincare H4 radius"
            )
        source = np.array(self.source, dtype=float, copy=True)
        target = np.array(self.target, dtype=float, copy=True)
        if (
            source.shape != (4,)
            or target.shape != (4,)
            or not np.all(np.isfinite(source))
            or not np.all(np.isfinite(target))
            or float(source @ source) >= 1.0
            or float(target @ target) >= 1.0
        ):
            raise GovernanceError("a chiral spin link needs two finite B4 points")
        products = [
            float(source[index]) * float(target[index]) for index in range(4)
        ]
        dot = math.fsum(products)
        scalar = math.fsum((1.0, -dot))
        absolute_dot_bound = math.fsum(abs(value) for value in products)
        conditioning = (
            4.0
            * np.finfo(float).eps
            * max(1.0, absolute_dot_bound)
            / scalar
        )
        raw_bivector = np.einsum(
            "iab,a,b->i",
            _SELF_DUAL,
            target,
            source,
        )
        scale = math.hypot(
            scalar,
            *(float(value) for value in raw_bivector),
        )
        expected_unitary = (scalar / scale) * np.eye(2, dtype=complex)
        for index in range(3):
            expected_unitary -= (
                1.0j * (float(raw_bivector[index]) / scale) * _PAULI[index]
            )
        unitary = _su2(
            self.unitary,
            tolerance,
            "chiral_spin_link.unitary",
        )
        if np.linalg.norm(unitary - expected_unitary, ord="fro") > tolerance:
            raise GovernanceError(
                "chiral spin-link unitary disagrees with its source and target"
            )
        tangent_rotation = np.array(
            self.tangent_rotation,
            dtype=float,
            copy=True,
        )
        chiral_rotation = np.array(
            self.chiral_rotation,
            dtype=float,
            copy=True,
        )
        if (
            tangent_rotation.shape != (4, 4)
            or chiral_rotation.shape != (3, 3)
            or not np.all(np.isfinite(tangent_rotation))
            or not np.all(np.isfinite(chiral_rotation))
        ):
            raise GovernanceError("chiral spin-link rotations have invalid shape")
        declared_base = PoincareBallBase(
            id=self.base_id,
            dimension=4,
            sectional_curvature=-1.0 / (radius * radius),
            tolerance=UNIVERSAL_POINCARE_BASE.tolerance,
        )
        if declared_base.to_spec() != UNIVERSAL_POINCARE_BASE.to_spec():
            raise CarrierMismatch(
                "a chiral spin link has a noncanonical H4 base specification"
            )
        expected_tangent = _frame_rotation(declared_base, source, target)
        if np.linalg.norm(
            tangent_rotation - expected_tangent,
            ord="fro",
        ) > tolerance:
            raise GovernanceError(
                "tangent rotation is not the declared H4 Levi-Civita transport"
            )
        expected_chiral = _self_dual_rotation(tangent_rotation)
        if np.linalg.norm(
            chiral_rotation - expected_chiral,
            ord="fro",
        ) > tolerance:
            raise GovernanceError(
                "chiral rotation disagrees with the declared tangent rotation"
            )
        bloch_rotation, bloch_imaginary = _bloch_rotation(unitary)
        computed = {
            "conditioning_error": float(conditioning),
            "tangent_orthogonality_defect": float(
                np.linalg.norm(
                    tangent_rotation.T @ tangent_rotation - np.eye(4),
                    ord="fro",
                )
            ),
            "tangent_determinant_defect": abs(
                float(np.linalg.det(tangent_rotation)) - 1.0
            ),
            "unitary_defect": float(
                np.linalg.norm(
                    unitary.conj().T @ unitary - np.eye(2),
                    ord="fro",
                )
            ),
            "determinant_defect": float(
                abs(complex(np.linalg.det(unitary)) - 1.0)
            ),
            "spin_intertwining_defect": float(
                np.linalg.norm(chiral_rotation - bloch_rotation, ord="fro")
            ),
            "bloch_imaginary_defect": float(bloch_imaginary),
        }
        for name, value in computed.items():
            supplied = _finite(getattr(self, name), f"chiral_spin_link.{name}")
            if supplied < 0.0 or abs(supplied - value) > tolerance:
                raise GovernanceError(
                    f"chiral spin-link {name} disagrees with its matrices"
                )
            object.__setattr__(self, name, value)
        expected_distance = declared_base.distance(source, target)
        supplied_distance = _finite(
            self.base_distance,
            "chiral_spin_link.base_distance",
        )
        if abs(supplied_distance - expected_distance) > tolerance * max(
            radius,
            expected_distance,
        ):
            raise GovernanceError(
                "chiral spin-link distance disagrees with its H4 endpoints"
            )
        supplied_scalar = _finite(
            self.scalar_part,
            "chiral_spin_link.scalar_part",
        )
        if abs(supplied_scalar - scalar / scale) > tolerance:
            raise GovernanceError(
                "chiral spin-link scalar part disagrees with its endpoints"
            )
        bivector = np.array(self.bivector, dtype=float, copy=True)
        if (
            bivector.shape != (3,)
            or not np.all(np.isfinite(bivector))
            or np.linalg.norm(bivector - raw_bivector / scale) > tolerance
        ):
            raise GovernanceError(
                "chiral spin-link bivector disagrees with its endpoints"
            )
        object.__setattr__(self, "curvature_radius", radius)
        object.__setattr__(self, "source", _readonly_real(source))
        object.__setattr__(self, "target", _readonly_real(target))
        object.__setattr__(self, "unitary", unitary)
        object.__setattr__(
            self,
            "tangent_rotation",
            _readonly_real(tangent_rotation),
        )
        object.__setattr__(
            self,
            "chiral_rotation",
            _readonly_real(chiral_rotation),
        )
        object.__setattr__(self, "base_distance", expected_distance)
        object.__setattr__(self, "scalar_part", float(scalar / scale))
        object.__setattr__(self, "bivector", _readonly_real(raw_bivector / scale))
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def passed(self) -> bool:
        return max(
            self.conditioning_error,
            self.tangent_orthogonality_defect,
            self.tangent_determinant_defect,
            self.unitary_defect,
            self.determinant_defect,
            self.spin_intertwining_defect,
            self.bloch_imaginary_defect,
        ) <= self.tolerance


@dataclass(frozen=True)
class SpinPathReport:
    """Ordered piecewise-geodesic spin transport."""

    points: tuple[np.ndarray, ...]
    links: tuple[ChiralSpinLink, ...]
    unitary: np.ndarray
    is_loop: bool
    signed_half_trace: float
    trace_imaginary_defect: float
    identity_distance: float
    negative_identity_distance: float
    projective_identity_distance: float
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "spin_path_report.tolerance",
            maximum=1e-10,
        )
        try:
            points = tuple(
                _readonly_real(
                    UNIVERSAL_POINCARE_BASE.point(
                        point,
                        f"spin_path_report.point[{index}]",
                    )
                )
                for index, point in enumerate(self.points)
            )
            links = tuple(self.links)
        except TypeError as exc:
            raise GovernanceError(
                "spin path points and links must be finite iterables"
            ) from exc
        if len(points) < 2 or len(links) != len(points) - 1:
            raise GovernanceError(
                "spin path report needs one typed link between every two points"
            )
        canonical_spec = UNIVERSAL_POINCARE_BASE.to_spec()
        for index, link in enumerate(links):
            if type(link) is not ChiralSpinLink:
                raise CarrierMismatch(
                    "spin path report accepts only typed chiral-spin links"
                )
            if (
                link.base_id != UNIVERSAL_POINCARE_BASE.id
                or abs(
                    link.curvature_radius - UNIVERSAL_POINCARE_BASE.radius
                )
                > tolerance
            ):
                raise CarrierMismatch(
                    "spin path link does not use the universal Poincare H4 base"
                )
            declared_spec = PoincareBallBase(
                id=link.base_id,
                dimension=4,
                sectional_curvature=(
                    -1.0 / (link.curvature_radius * link.curvature_radius)
                ),
                tolerance=UNIVERSAL_POINCARE_BASE.tolerance,
            ).to_spec()
            if declared_spec != canonical_spec:
                raise CarrierMismatch(
                    "spin path link has a noncanonical H4 specification"
                )
            if (
                np.linalg.norm(link.source - points[index]) > tolerance
                or np.linalg.norm(link.target - points[index + 1]) > tolerance
            ):
                raise CarrierMismatch(
                    "spin path link endpoints do not match the declared path"
                )
        expected_unitary = np.eye(2, dtype=complex)
        for link in links:
            expected_unitary = link.unitary @ expected_unitary
        expected_unitary = _su2(
            expected_unitary,
            tolerance,
            "spin_path_report.expected_unitary",
        )
        unitary = _su2(
            self.unitary,
            tolerance,
            "spin_path_report.unitary",
        )
        if np.linalg.norm(unitary - expected_unitary, ord="fro") > tolerance:
            raise GovernanceError(
                "spin path unitary disagrees with its ordered typed links"
            )
        half_trace = 0.5 * complex(np.trace(unitary))
        identity_distance = float(
            np.linalg.norm(unitary - np.eye(2), ord="fro")
        )
        negative_identity_distance = float(
            np.linalg.norm(unitary + np.eye(2), ord="fro")
        )
        projective_identity_distance = min(
            identity_distance,
            negative_identity_distance,
        )
        is_loop = bool(np.linalg.norm(points[0] - points[-1]) <= tolerance)
        expected_scalars = {
            "signed_half_trace": float(half_trace.real),
            "trace_imaginary_defect": float(abs(half_trace.imag)),
            "identity_distance": identity_distance,
            "negative_identity_distance": negative_identity_distance,
            "projective_identity_distance": projective_identity_distance,
        }
        for name, expected in expected_scalars.items():
            supplied = _finite(
                getattr(self, name),
                f"spin_path_report.{name}",
            )
            if supplied < 0.0 and name != "signed_half_trace":
                raise GovernanceError(f"spin path {name} must be non-negative")
            if abs(supplied - expected) > tolerance:
                raise GovernanceError(
                    f"spin path {name} disagrees with its ordered unitary"
                )
            object.__setattr__(self, name, expected)
        if self.is_loop is not is_loop:
            raise GovernanceError(
                "spin path loop flag disagrees with its endpoints"
            )
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "links", links)
        object.__setattr__(self, "unitary", unitary)
        object.__setattr__(self, "is_loop", is_loop)
        object.__setattr__(self, "tolerance", tolerance)


@dataclass(frozen=True)
class SpinHolonomyReport:
    path: SpinPathReport
    flat_control_unitary: np.ndarray
    flat_control_identity_distance: float
    omitted_chirality: RemainderEnvelope

    def __post_init__(self) -> None:
        if type(self.path) is not SpinPathReport:
            raise CarrierMismatch("spin holonomy requires a typed spin path")
        if len(self.path.points) < 4 or not self.path.is_loop:
            raise GovernanceError(
                "spin holonomy requires a closed path with at least three edges"
            )
        flat = _su2(
            self.flat_control_unitary,
            self.path.tolerance,
            "spin_holonomy.flat_control",
        )
        expected_flat = np.eye(2, dtype=complex)
        if np.linalg.norm(flat - expected_flat, ord="fro") > self.path.tolerance:
            raise GovernanceError(
                "the declared flat R4 connection must have identity holonomy"
            )
        expected_distance = float(
            np.linalg.norm(flat - expected_flat, ord="fro")
        )
        supplied_distance = _finite(
            self.flat_control_identity_distance,
            "spin_holonomy.flat_control_identity_distance",
        )
        if (
            supplied_distance < 0.0
            or abs(supplied_distance - expected_distance) > self.path.tolerance
        ):
            raise GovernanceError(
                "flat-control distance disagrees with its unitary"
            )
        expected_remainder = _omitted_chirality_remainder()
        if self.omitted_chirality != expected_remainder:
            raise GovernanceError(
                "spin holonomy must retain the typed negative-chirality remainder"
            )
        object.__setattr__(self, "flat_control_unitary", _readonly_complex(flat))
        object.__setattr__(
            self,
            "flat_control_identity_distance",
            expected_distance,
        )
        object.__setattr__(self, "omitted_chirality", expected_remainder)


@dataclass(frozen=True)
class ChiralCurvatureSpanReport:
    planes: tuple[tuple[int, int], ...]
    curvature_components: np.ndarray
    singular_values: np.ndarray
    rank: int
    rank_cutoff: float

    def __post_init__(self) -> None:
        planes = tuple(
            (left, right)
            for left in range(4)
            for right in range(left + 1, 4)
        )
        if tuple(self.planes) != planes:
            raise GovernanceError(
                "chiral-curvature planes must be the complete oriented H4 basis"
            )
        expected_components = np.column_stack(
            [
                _SELF_DUAL[:, left, right]
                / UNIVERSAL_POINCARE_BASE.radius_squared
                for left, right in planes
            ]
        )
        components = np.array(
            self.curvature_components,
            dtype=float,
            copy=True,
        )
        if (
            components.shape != expected_components.shape
            or not np.all(np.isfinite(components))
            or np.linalg.norm(
                components - expected_components,
                ord="fro",
            )
            > UNIVERSAL_POINCARE_BASE.tolerance
        ):
            raise GovernanceError(
                "chiral-curvature components disagree with the universal H4 tensor"
            )
        singular_values = np.linalg.svd(expected_components, compute_uv=False)
        cutoff = (
            64.0
            * np.finfo(float).eps
            * max(expected_components.shape)
            * max(1.0, float(singular_values[0]))
        )
        rank = int(np.count_nonzero(singular_values > cutoff))
        supplied_singular_values = np.array(
            self.singular_values,
            dtype=float,
            copy=True,
        )
        if (
            supplied_singular_values.shape != singular_values.shape
            or not np.all(np.isfinite(supplied_singular_values))
            or np.linalg.norm(supplied_singular_values - singular_values)
            > UNIVERSAL_POINCARE_BASE.tolerance
        ):
            raise GovernanceError(
                "chiral-curvature singular values disagree with its tensor"
            )
        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, (int, np.integer))
            or int(self.rank) != rank
        ):
            raise GovernanceError("chiral-curvature rank was not recomputed")
        supplied_cutoff = _finite(
            self.rank_cutoff,
            "chiral_curvature.rank_cutoff",
        )
        if supplied_cutoff < 0.0 or abs(supplied_cutoff - cutoff) > 1e-15:
            raise GovernanceError("chiral-curvature rank cutoff is inconsistent")
        object.__setattr__(self, "planes", planes)
        object.__setattr__(
            self,
            "curvature_components",
            _readonly_real(expected_components),
        )
        object.__setattr__(
            self,
            "singular_values",
            _readonly_real(singular_values),
        )
        object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "rank_cutoff", float(cutoff))


@dataclass(frozen=True)
class TriangleCurvatureReport:
    epsilon: float
    hyperbolic_area: float
    spin_rotation_angle: float
    holonomy: SpinHolonomyReport
    expected_unitary: np.ndarray
    unitary_defect: float
    area_rotation_defect: float
    plus_x_trace_distance: float
    expected_plus_x_trace_distance: float
    plus_x_root_fidelity: float
    expected_plus_x_root_fidelity: float
    sigma3_blind_trace_distance: float

    def __post_init__(self) -> None:
        epsilon = _finite(self.epsilon, "triangle_report.epsilon")
        if epsilon <= 0.0 or epsilon >= 1.0:
            raise GovernanceError("triangle-report epsilon must lie in (0, 1)")
        if type(self.holonomy) is not SpinHolonomyReport:
            raise CarrierMismatch("triangle report requires typed spin holonomy")
        expected_points = (
            np.zeros(4),
            np.array([epsilon, 0.0, 0.0, 0.0]),
            np.array([0.0, epsilon, 0.0, 0.0]),
            np.zeros(4),
        )
        if any(
            np.linalg.norm(actual - expected) > self.holonomy.path.tolerance
            for actual, expected in zip(
                self.holonomy.path.points,
                expected_points,
            )
        ) or len(self.holonomy.path.points) != len(expected_points):
            raise GovernanceError(
                "triangle holonomy does not use the declared H4 triangle"
            )
        tolerance = self.holonomy.path.tolerance
        angle = math.atan(epsilon * epsilon)
        expected_unitary = (
            np.eye(2, dtype=complex)
            + 1.0j * epsilon * epsilon * _PAULI[2]
        ) / math.sqrt(1.0 + epsilon**4)
        expected_unitary = _su2(
            expected_unitary,
            tolerance,
            "triangle_report.expected_unitary",
        )
        supplied_unitary = _su2(
            self.expected_unitary,
            tolerance,
            "triangle_report.supplied_expected_unitary",
        )
        if (
            np.linalg.norm(
                supplied_unitary - expected_unitary,
                ord="fro",
            )
            > tolerance
        ):
            raise GovernanceError("triangle expected unitary was forged")
        area = (
            2.0
            * UNIVERSAL_POINCARE_BASE.radius_squared
            * angle
        )
        spin_rotation = -2.0 * angle
        unitary = self.holonomy.path.unitary
        plus_x = 0.5 * np.array(
            [[1.0, 1.0], [1.0, 1.0]],
            dtype=complex,
        )
        sigma3 = np.array(
            [[1.0, 0.0], [0.0, 0.0]],
            dtype=complex,
        )
        moved_plus_x = unitary @ plus_x @ unitary.conj().T
        moved_sigma3 = unitary @ sigma3 @ unitary.conj().T
        expected_trace = epsilon * epsilon / math.sqrt(1.0 + epsilon**4)
        expected_fidelity = 1.0 / math.sqrt(1.0 + epsilon**4)
        computed = {
            "hyperbolic_area": area,
            "spin_rotation_angle": spin_rotation,
            "unitary_defect": float(
                np.linalg.norm(unitary - expected_unitary, ord="fro")
            ),
            "area_rotation_defect": abs(
                spin_rotation
                + area / UNIVERSAL_POINCARE_BASE.radius_squared
            ),
            "plus_x_trace_distance": quantum_trace_distance(
                plus_x,
                moved_plus_x,
                tolerance,
            ),
            "expected_plus_x_trace_distance": expected_trace,
            "plus_x_root_fidelity": quantum_root_fidelity(
                plus_x,
                moved_plus_x,
                tolerance,
            ),
            "expected_plus_x_root_fidelity": expected_fidelity,
            "sigma3_blind_trace_distance": quantum_trace_distance(
                sigma3,
                moved_sigma3,
                tolerance,
            ),
        }
        for name, expected in computed.items():
            supplied = _finite(getattr(self, name), f"triangle_report.{name}")
            if (
                supplied < 0.0
                and name not in {"spin_rotation_angle"}
            ):
                raise GovernanceError(f"triangle {name} must be non-negative")
            if abs(supplied - expected) > tolerance:
                raise GovernanceError(
                    f"triangle {name} disagrees with its geometry"
                )
            object.__setattr__(self, name, expected)
        object.__setattr__(self, "epsilon", epsilon)
        object.__setattr__(self, "expected_unitary", expected_unitary)


@dataclass(frozen=True)
class SectionalRefinementReport:
    """Exact geodesic subdivision control; not an adiabatic-theorem claim."""

    sections: int
    direct_unitary: np.ndarray
    refined_unitary: np.ndarray
    composition_defect: float
    maximum_segment_distance: float
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "sectional_refinement.tolerance",
            maximum=1e-10,
        )
        if isinstance(self.sections, bool) or not isinstance(self.sections, int):
            raise GovernanceError("sectional refinement count must be an integer")
        if self.sections < 1 or self.sections > 4096:
            raise GovernanceError("sectional refinement count lies outside its guard")
        direct = _su2(
            self.direct_unitary,
            tolerance,
            "sectional_refinement.direct",
        )
        refined = _su2(
            self.refined_unitary,
            tolerance,
            "sectional_refinement.refined",
        )
        computed = float(np.linalg.norm(refined - direct, ord="fro"))
        supplied = _finite(
            self.composition_defect,
            "sectional_refinement.composition_defect",
        )
        maximum_segment = _finite(
            self.maximum_segment_distance,
            "sectional_refinement.maximum_segment_distance",
        )
        if supplied < 0.0 or abs(supplied - computed) > tolerance:
            raise GovernanceError(
                "sectional refinement defect disagrees with its unitaries"
            )
        if maximum_segment < 0.0:
            raise GovernanceError(
                "sectional refinement segment distance must be non-negative"
            )
        object.__setattr__(self, "direct_unitary", direct)
        object.__setattr__(self, "refined_unitary", refined)
        object.__setattr__(self, "composition_defect", computed)
        object.__setattr__(self, "maximum_segment_distance", maximum_segment)
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def passed(self) -> bool:
        return self.composition_defect <= self.tolerance


@dataclass(frozen=True)
class SectionalBoundaryReport:
    hadamard4: np.ndarray
    hadamard4_orthogonality_defect: float
    hadamard_spin_gate: np.ndarray
    hadamard_spin_unitary_defect: float
    hadamard_spin_determinant_defect: float
    mobius_pair_distance_defect: float
    split_boost: np.ndarray
    split_signature_defect: float
    split_hilbert_unitarity_defect: float
    split_qiskit_eligible: bool
    fixed_phase: float
    fixed_phase_gate: np.ndarray
    fixed_phase_unitary_defect: float
    generation: int
    jitter: float
    perlin_seed: int
    jitter_operational: bool
    perlin_seed_operational: bool
    split_remainder: RemainderEnvelope
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "sectional_boundary_report.tolerance",
            maximum=1e-10,
        )
        expected_hadamard4 = 0.5 * np.array(
            [
                [1.0, 1.0, 1.0, 1.0],
                [1.0, -1.0, 1.0, -1.0],
                [1.0, 1.0, -1.0, -1.0],
                [1.0, -1.0, -1.0, 1.0],
            ]
        )
        hadamard4 = np.array(self.hadamard4, dtype=float, copy=True)
        if (
            hadamard4.shape != (4, 4)
            or not np.all(np.isfinite(hadamard4))
            or np.linalg.norm(hadamard4 - expected_hadamard4, ord="fro")
            > tolerance
        ):
            raise GovernanceError(
                "sectional report has a noncanonical four-lane Hadamard"
            )
        hadamard_spin = _su2(
            self.hadamard_spin_gate,
            tolerance,
            "sectional_boundary_report.hadamard_spin",
        )
        expected_hadamard_spin = (
            1.0j
            / math.sqrt(2.0)
            * np.array(
                [[1.0, 1.0], [1.0, -1.0]],
                dtype=complex,
            )
        )
        if (
            np.linalg.norm(
                hadamard_spin - expected_hadamard_spin,
                ord="fro",
            )
            > tolerance
        ):
            raise GovernanceError(
                "sectional report has a noncanonical SU(2) Hadamard control"
            )
        boost = np.array(self.split_boost, dtype=float, copy=True)
        if (
            boost.shape != (4, 4)
            or not np.all(np.isfinite(boost))
        ):
            raise GovernanceError(
                "sectional report split boost has the wrong carrier"
            )
        phase_gate = _su2(
            self.fixed_phase_gate,
            tolerance,
            "sectional_boundary_report.fixed_phase_gate",
        )
        expected_phase_gate = np.diag(
            [
                np.exp(-0.5j * _GEN100_PHASE),
                np.exp(0.5j * _GEN100_PHASE),
            ]
        )
        if (
            np.linalg.norm(phase_gate - expected_phase_gate, ord="fro")
            > tolerance
        ):
            raise GovernanceError(
                "sectional report has a noncanonical fixed-phase control"
            )
        computed = {
            "hadamard4_orthogonality_defect": float(
                np.linalg.norm(
                    hadamard4.T @ hadamard4 - np.eye(4),
                    ord="fro",
                )
            ),
            "hadamard_spin_unitary_defect": float(
                np.linalg.norm(
                    hadamard_spin.conj().T @ hadamard_spin - np.eye(2),
                    ord="fro",
                )
            ),
            "hadamard_spin_determinant_defect": float(
                abs(complex(np.linalg.det(hadamard_spin)) - 1.0)
            ),
            "split_signature_defect": float(
                np.linalg.norm(
                    boost.T @ _SPLIT_22 @ boost - _SPLIT_22,
                    ord="fro",
                )
            ),
            "split_hilbert_unitarity_defect": float(
                np.linalg.norm(boost.T @ boost - np.eye(4), ord="fro")
            ),
            "fixed_phase_unitary_defect": float(
                np.linalg.norm(
                    phase_gate.conj().T @ phase_gate - np.eye(2),
                    ord="fro",
                )
            ),
        }
        for name, expected in computed.items():
            supplied = _finite(
                getattr(self, name),
                f"sectional_boundary_report.{name}",
            )
            if supplied < 0.0 or abs(supplied - expected) > tolerance:
                raise GovernanceError(
                    f"sectional report {name} disagrees with its matrix"
                )
            object.__setattr__(self, name, expected)
        mobius_defect = _finite(
            self.mobius_pair_distance_defect,
            "sectional_boundary_report.mobius_pair_distance_defect",
        )
        if mobius_defect < 0.0 or mobius_defect > tolerance:
            raise GovernanceError(
                "sectional report Mobius isometry defect exceeds tolerance"
            )
        split_eligible = bool(
            computed["split_hilbert_unitarity_defect"] <= tolerance
        )
        if self.split_qiskit_eligible is not split_eligible:
            raise GovernanceError(
                "sectional report split/Qiskit eligibility was forged"
            )
        if (
            _finite(self.fixed_phase, "sectional_boundary_report.fixed_phase")
            != _GEN100_PHASE
            or self.generation != 100
            or _finite(self.jitter, "sectional_boundary_report.jitter")
            != _GEN100_JITTER
            or self.perlin_seed != _GEN100_PERLIN_SEED
            or self.jitter_operational is not False
            or self.perlin_seed_operational is not False
        ):
            raise GovernanceError(
                "sectional report metadata exceeds its declared inert scope"
            )
        expected_remainder = _split_substrate_remainder()
        if self.split_remainder != expected_remainder:
            raise GovernanceError(
                "sectional report must retain the split-signature remainder"
            )
        object.__setattr__(self, "hadamard4", _readonly_real(hadamard4))
        object.__setattr__(self, "hadamard_spin_gate", hadamard_spin)
        object.__setattr__(
            self,
            "mobius_pair_distance_defect",
            mobius_defect,
        )
        object.__setattr__(self, "split_boost", _readonly_real(boost))
        object.__setattr__(self, "split_qiskit_eligible", split_eligible)
        object.__setattr__(self, "fixed_phase", _GEN100_PHASE)
        object.__setattr__(self, "fixed_phase_gate", phase_gate)
        object.__setattr__(self, "generation", 100)
        object.__setattr__(self, "jitter", _GEN100_JITTER)
        object.__setattr__(self, "perlin_seed", _GEN100_PERLIN_SEED)
        object.__setattr__(self, "split_remainder", expected_remainder)
        object.__setattr__(self, "tolerance", tolerance)


class QiskitProjectionUnavailable(GovernanceError):
    """Raised when the defensive lazy Qiskit boundary cannot be loaded."""


@dataclass(frozen=True)
class QiskitSpinProjectionReport:
    circuit: Any
    qiskit_version: str
    base_id: str
    link_count: int
    links: tuple[ChiralSpinLink, ...]
    preparation_unitary: np.ndarray
    path_unitary: np.ndarray
    expected_circuit_operator: np.ndarray
    circuit_operator: np.ndarray
    output_statevector: np.ndarray
    expected_statevector: np.ndarray
    output_density: np.ndarray
    expected_density: np.ndarray
    path_unitary_defect: float
    path_determinant_defect: float
    circuit_operator_defect: float
    statevector_defect: float
    density_intertwining_defect: float
    simulator_only: bool
    backend_executed: bool
    advantage_claim: bool
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "qiskit_projection_report.tolerance",
            maximum=1e-10,
        )
        if isinstance(self.link_count, bool) or not isinstance(self.link_count, int):
            raise GovernanceError("Qiskit projection link count must be an integer")
        if self.link_count < 0:
            raise GovernanceError("Qiskit projection link count must be non-negative")
        if self.base_id != UNIVERSAL_POINCARE_BASE.id:
            raise CarrierMismatch(
                "Qiskit spin projection must retain the universal H4 base id"
            )
        try:
            links = tuple(self.links)
        except TypeError as exc:
            raise CarrierMismatch(
                "Qiskit spin projection links must be a typed iterable"
            ) from exc
        if not links or len(links) != self.link_count:
            raise GovernanceError(
                "Qiskit spin projection needs a nonempty typed-link receipt"
            )
        for index, link in enumerate(links):
            if type(link) is not ChiralSpinLink:
                raise CarrierMismatch(
                    "Qiskit spin projection accepts only ChiralSpinLink values"
                )
            if (
                link.base_id != UNIVERSAL_POINCARE_BASE.id
                or abs(
                    link.curvature_radius - UNIVERSAL_POINCARE_BASE.radius
                )
                > tolerance
            ):
                raise CarrierMismatch(
                    "Qiskit spin link does not use the universal Poincare H4 base"
                )
            if (
                index
                and np.linalg.norm(links[index - 1].target - link.source)
                > tolerance
            ):
                raise CarrierMismatch(
                    "Qiskit spin links do not form one adjacent geometric path"
                )
        preparation = _su2(
            self.preparation_unitary,
            tolerance,
            "qiskit_projection_report.preparation",
        )
        path = _su2(
            self.path_unitary,
            tolerance,
            "qiskit_projection_report.path",
        )
        typed_path = np.eye(2, dtype=complex)
        for link in links:
            typed_path = link.unitary @ typed_path
        if np.linalg.norm(path - typed_path, ord="fro") > tolerance:
            raise GovernanceError(
                "Qiskit path unitary disagrees with its typed geometric links"
            )
        expected_operator = _readonly_complex(self.expected_circuit_operator)
        circuit_operator = _readonly_complex(self.circuit_operator)
        output_state = _readonly_complex(self.output_statevector)
        expected_state = _readonly_complex(self.expected_statevector)
        output_density = _strict_density(
            self.output_density,
            tolerance,
            "qiskit_projection_report.output_density",
        )
        expected_density = _strict_density(
            self.expected_density,
            tolerance,
            "qiskit_projection_report.expected_density",
        )
        if (
            expected_operator.shape != (2, 2)
            or circuit_operator.shape != (2, 2)
            or output_state.shape != (2,)
            or expected_state.shape != (2,)
            or output_density.shape != (2, 2)
            or expected_density.shape != (2, 2)
        ):
            raise GovernanceError("Qiskit projection report has an invalid carrier")
        derived_operator = path @ preparation
        derived_state = derived_operator @ np.array([1.0 + 0.0j, 0.0 + 0.0j])
        derived_density = np.outer(derived_state, derived_state.conj())
        if max(
            float(np.linalg.norm(expected_operator - derived_operator, ord="fro")),
            float(np.linalg.norm(expected_state - derived_state)),
            float(np.linalg.norm(expected_density - derived_density, ord="fro")),
        ) > tolerance:
            raise GovernanceError(
                "Qiskit projection expectations are not bound to path and preparation"
            )
        if (
            getattr(self.circuit, "num_qubits", None) != 1
            or getattr(self.circuit, "num_clbits", None) != 0
            or len(getattr(self.circuit, "data", ())) != self.link_count + 1
        ):
            raise GovernanceError(
                "Qiskit projection circuit shape/count disagrees with its receipt"
            )
        (
            qiskit,
            _QuantumCircuit,
            _UnitaryGate,
            DensityMatrix,
            Operator,
            Statevector,
        ) = _load_qiskit_projection_types()
        if self.qiskit_version != str(qiskit.__version__):
            raise GovernanceError(
                "Qiskit projection version receipt disagrees with the live library"
            )
        live_operator = np.asarray(Operator(self.circuit).data, dtype=complex)
        live_state = np.asarray(
            Statevector.from_instruction(self.circuit).data,
            dtype=complex,
        )
        live_density = np.asarray(
            DensityMatrix.from_instruction(self.circuit).data,
            dtype=complex,
        )
        if max(
            float(np.linalg.norm(live_operator - circuit_operator, ord="fro")),
            float(np.linalg.norm(live_state - output_state)),
            float(np.linalg.norm(live_density - output_density, ord="fro")),
        ) > tolerance:
            raise GovernanceError(
                "Qiskit projection artifacts disagree with the live circuit"
            )
        computed = {
            "path_unitary_defect": float(
                np.linalg.norm(path.conj().T @ path - np.eye(2), ord="fro")
            ),
            "path_determinant_defect": float(
                abs(complex(np.linalg.det(path)) - 1.0)
            ),
            "circuit_operator_defect": float(
                np.linalg.norm(
                    circuit_operator - expected_operator,
                    ord="fro",
                )
            ),
            "statevector_defect": float(
                np.linalg.norm(output_state - expected_state)
            ),
            "density_intertwining_defect": float(
                np.linalg.norm(
                    output_density - expected_density,
                    ord="fro",
                )
            ),
        }
        for name, value in computed.items():
            supplied = _finite(
                getattr(self, name),
                f"qiskit_projection_report.{name}",
            )
            if supplied < 0.0 or abs(supplied - value) > tolerance:
                raise GovernanceError(
                    f"Qiskit projection {name} disagrees with its artifacts"
                )
            object.__setattr__(self, name, value)
        if (
            self.simulator_only is not True
            or self.backend_executed is not False
            or self.advantage_claim is not False
        ):
            raise GovernanceError("Qiskit projection evidence flags are immutable")
        object.__setattr__(self, "links", links)
        object.__setattr__(self, "preparation_unitary", preparation)
        object.__setattr__(self, "path_unitary", path)
        object.__setattr__(self, "expected_circuit_operator", expected_operator)
        object.__setattr__(self, "circuit_operator", circuit_operator)
        object.__setattr__(self, "output_statevector", output_state)
        object.__setattr__(self, "expected_statevector", expected_state)
        object.__setattr__(self, "output_density", output_density)
        object.__setattr__(self, "expected_density", expected_density)
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def passed(self) -> bool:
        recorded = max(
            self.path_unitary_defect,
            self.path_determinant_defect,
            self.circuit_operator_defect,
            self.statevector_defect,
            self.density_intertwining_defect,
        )
        try:
            from qiskit.quantum_info import Operator

            live_operator = np.asarray(Operator(self.circuit).data, dtype=complex)
            live_defect = float(
                np.linalg.norm(
                    live_operator - self.expected_circuit_operator,
                    ord="fro",
                )
            )
        except Exception:
            return False
        return (
            max(recorded, live_defect) <= self.tolerance
            and getattr(self.circuit, "num_clbits", 1) == 0
            and getattr(self.circuit, "num_qubits", 0) == 1
            and len(getattr(self.circuit, "data", ())) == self.link_count + 1
        )


@dataclass(frozen=True)
class CentralLiftProbeReport:
    circuit: Any
    qiskit_version: str
    unitary: np.ndarray
    positive_identity_distance: float
    negative_identity_distance: float
    density_change: float
    control_one_probability: float
    simulator_only: bool
    backend_executed: bool
    tolerance: float

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "central_lift_report.tolerance",
            maximum=1e-10,
        )
        unitary = _su2(
            self.unitary,
            tolerance,
            "central_lift_report.unitary",
        )
        (
            qiskit,
            QuantumCircuit,
            UnitaryGate,
            DensityMatrix,
            Operator,
            Statevector,
        ) = _load_qiskit_projection_types()
        expected_circuit = QuantumCircuit(2, name="hb0_qb2_central_sign_expected")
        expected_circuit.h(0)
        expected_circuit.append(
            UnitaryGate(unitary, label="spin_lift").control(1),
            [0, 1],
        )
        expected_circuit.h(0)
        if (
            getattr(self.circuit, "num_qubits", None) != 2
            or getattr(self.circuit, "num_clbits", None) != 0
            or len(getattr(self.circuit, "data", ())) != 3
        ):
            raise GovernanceError(
                "central-lift circuit shape disagrees with its receipt"
            )
        live_operator = np.asarray(Operator(self.circuit).data, dtype=complex)
        expected_operator = np.asarray(
            Operator(expected_circuit).data,
            dtype=complex,
        )
        if (
            np.linalg.norm(live_operator - expected_operator, ord="fro")
            > tolerance
        ):
            raise GovernanceError(
                "central-lift circuit is not bound to its declared SU(2) operator"
            )
        state = np.asarray(
            Statevector.from_instruction(self.circuit).data,
            dtype=complex,
        )
        control_one_probability = float(
            sum(
                abs(state[index]) ** 2
                for index in range(state.size)
                if index & 1
            )
        )
        source_density = np.asarray(
            DensityMatrix([1.0 + 0.0j, 0.0 + 0.0j]).data,
            dtype=complex,
        )
        moved_density = unitary @ source_density @ unitary.conj().T
        computed = {
            "positive_identity_distance": float(
                np.linalg.norm(unitary - np.eye(2), ord="fro")
            ),
            "negative_identity_distance": float(
                np.linalg.norm(unitary + np.eye(2), ord="fro")
            ),
            "density_change": float(
                np.linalg.norm(moved_density - source_density, ord="fro")
            ),
            "control_one_probability": control_one_probability,
        }
        for name, expected in computed.items():
            supplied = _finite(
                getattr(self, name),
                f"central_lift_report.{name}",
            )
            if supplied < 0.0 or abs(supplied - expected) > tolerance:
                raise GovernanceError(
                    f"central-lift {name} disagrees with its live circuit"
                )
            object.__setattr__(self, name, expected)
        if (
            self.simulator_only is not True
            or self.backend_executed is not False
        ):
            raise GovernanceError("central-lift evidence flags are immutable")
        if (
            not isinstance(self.qiskit_version, str)
            or self.qiskit_version != str(qiskit.__version__)
        ):
            raise GovernanceError(
                "central-lift Qiskit version receipt is inconsistent"
            )
        object.__setattr__(self, "unitary", unitary)
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def passed(self) -> bool:
        """Revalidate the mutable Qiskit circuit against the frozen receipt."""

        try:
            tolerance = _numerical_tolerance(
                self.tolerance,
                "central_lift_report.live_tolerance",
                maximum=1e-10,
            )
            unitary = _su2(
                self.unitary,
                tolerance,
                "central_lift_report.live_unitary",
            )
            (
                qiskit,
                QuantumCircuit,
                UnitaryGate,
                DensityMatrix,
                Operator,
                Statevector,
            ) = _load_qiskit_projection_types()
            if (
                self.qiskit_version != str(qiskit.__version__)
                or self.simulator_only is not True
                or self.backend_executed is not False
                or getattr(self.circuit, "num_qubits", None) != 2
                or getattr(self.circuit, "num_clbits", None) != 0
                or len(getattr(self.circuit, "data", ())) != 3
            ):
                return False
            expected_circuit = QuantumCircuit(
                2,
                name="hb0_qb2_central_sign_live_expected",
            )
            expected_circuit.h(0)
            expected_circuit.append(
                UnitaryGate(unitary, label="spin_lift").control(1),
                [0, 1],
            )
            expected_circuit.h(0)
            live_operator = np.asarray(
                Operator(self.circuit).data,
                dtype=complex,
            )
            expected_operator = np.asarray(
                Operator(expected_circuit).data,
                dtype=complex,
            )
            live_state = np.asarray(
                Statevector.from_instruction(self.circuit).data,
                dtype=complex,
            )
            expected_state = np.asarray(
                Statevector.from_instruction(expected_circuit).data,
                dtype=complex,
            )
            if max(
                float(
                    np.linalg.norm(
                        live_operator - expected_operator,
                        ord="fro",
                    )
                ),
                float(np.linalg.norm(live_state - expected_state)),
            ) > tolerance:
                return False
            control_one_probability = float(
                sum(
                    abs(live_state[index]) ** 2
                    for index in range(live_state.size)
                    if index & 1
                )
            )
            source_density = np.asarray(
                DensityMatrix([1.0 + 0.0j, 0.0 + 0.0j]).data,
                dtype=complex,
            )
            moved_density = unitary @ source_density @ unitary.conj().T
            expected = {
                "positive_identity_distance": float(
                    np.linalg.norm(unitary - np.eye(2), ord="fro")
                ),
                "negative_identity_distance": float(
                    np.linalg.norm(unitary + np.eye(2), ord="fro")
                ),
                "density_change": float(
                    np.linalg.norm(
                        moved_density - source_density,
                        ord="fro",
                    )
                ),
                "control_one_probability": control_one_probability,
            }
            return all(
                math.isfinite(float(getattr(self, name)))
                and float(getattr(self, name)) >= 0.0
                and abs(float(getattr(self, name)) - value) <= tolerance
                for name, value in expected.items()
            )
        except Exception:
            return False


@dataclass(frozen=True)
class ChiralSpinConnection:
    """The exact positive-chiral Levi-Civita spin connection on ``H4``."""

    base: PoincareBallBase = UNIVERSAL_POINCARE_BASE
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "chiral_spin.tolerance",
            maximum=1e-10,
        )
        _universal_h4(self.base, "the chiral Spin(4) connection")
        object.__setattr__(self, "tolerance", tolerance)

    def link(self, source, target) -> ChiralSpinLink:
        """Return the exact ``SU(2)+`` lift of the unique geodesic edge."""

        source = self.base.point(source, "chiral_link.source")
        target = self.base.point(target, "chiral_link.target")
        products = [
            float(source[index]) * float(target[index]) for index in range(4)
        ]
        dot = math.fsum(products)
        scalar = math.fsum((1.0, -dot))
        absolute_dot_bound = math.fsum(abs(value) for value in products)
        if scalar <= 0.0:
            raise GovernanceError("chiral-link scalar part must be positive")
        conditioning_error = (
            4.0
            * np.finfo(float).eps
            * max(1.0, absolute_dot_bound)
            / scalar
        )
        if not math.isfinite(conditioning_error) or conditioning_error > self.tolerance:
            raise GovernanceError(
                "chiral link is outside the conditioned float64 chart"
            )
        bivector = np.einsum(
            "iab,a,b->i",
            _SELF_DUAL,
            target,
            source,
        )
        scale = math.hypot(scalar, *(float(value) for value in bivector))
        if not math.isfinite(scale) or scale <= 0.0:
            raise GovernanceError("chiral-link normalisation is not representable")
        unitary = (scalar / scale) * np.eye(2, dtype=complex)
        for index in range(3):
            unitary -= 1.0j * (float(bivector[index]) / scale) * _PAULI[index]
        unitary = _su2(unitary, self.tolerance, "chiral_link.unitary")

        tangent_rotation = _frame_rotation(self.base, source, target)
        tangent_orthogonality_defect = float(
            np.linalg.norm(
                tangent_rotation.T @ tangent_rotation - np.eye(4),
                ord="fro",
            )
        )
        tangent_determinant_defect = abs(
            float(np.linalg.det(tangent_rotation)) - 1.0
        )
        chiral_rotation = _self_dual_rotation(tangent_rotation)
        bloch_rotation, bloch_imaginary_defect = _bloch_rotation(unitary)
        spin_intertwining_defect = float(
            np.linalg.norm(chiral_rotation - bloch_rotation, ord="fro")
        )
        unitary_defect = float(
            np.linalg.norm(
                unitary.conj().T @ unitary - np.eye(2),
                ord="fro",
            )
        )
        determinant_defect = abs(complex(np.linalg.det(unitary)) - 1.0)
        if max(
            tangent_orthogonality_defect,
            tangent_determinant_defect,
            spin_intertwining_defect,
            bloch_imaginary_defect,
        ) > self.tolerance:
            raise GovernanceError(
                "closed-form chiral link failed its independent frame control"
            )
        return ChiralSpinLink(
            base_id=self.base.id,
            curvature_radius=self.base.radius,
            source=_readonly_real(source),
            target=_readonly_real(target),
            unitary=unitary,
            tangent_rotation=tangent_rotation,
            chiral_rotation=chiral_rotation,
            base_distance=self.base.distance(source, target),
            scalar_part=float(scalar / scale),
            bivector=_readonly_real(bivector / scale),
            conditioning_error=float(conditioning_error),
            tangent_orthogonality_defect=tangent_orthogonality_defect,
            tangent_determinant_defect=tangent_determinant_defect,
            unitary_defect=unitary_defect,
            determinant_defect=float(determinant_defect),
            spin_intertwining_defect=spin_intertwining_defect,
            bloch_imaginary_defect=bloch_imaginary_defect,
            tolerance=self.tolerance,
        )

    def transport_spinor(self, source, target, spinor) -> np.ndarray:
        spinor = _normalised_spinor(
            spinor,
            self.tolerance,
            "spin_transport.spinor",
        )
        return _readonly_complex(self.link(source, target).unitary @ spinor)

    def transport_density(self, source, target, density) -> np.ndarray:
        density = _strict_density(
            density,
            self.tolerance,
            "spin_transport.density",
        )
        if density.shape != (2, 2):
            raise CarrierMismatch("chiral spin transport requires a qubit density")
        unitary = self.link(source, target).unitary
        return _strict_density(
            unitary @ density @ unitary.conj().T,
            self.tolerance,
            "spin_transport.output_density",
        )

    def lift_qutrit_unitary(self, unitary) -> np.ndarray:
        unitary = _su2(
            unitary,
            self.tolerance,
            "spin_transport.qutrit_lift",
        )
        lifted = np.eye(3, dtype=complex)
        lifted[1:, 1:] = unitary
        return _readonly_complex(lifted)

    def transport_qutrit_density(self, source, target, density) -> np.ndarray:
        density = _strict_density(
            density,
            self.tolerance,
            "spin_transport.qutrit_density",
        )
        if density.shape != (3, 3):
            raise CarrierMismatch("the radial-flag lift requires a qutrit density")
        lifted = self.lift_qutrit_unitary(self.link(source, target).unitary)
        return _strict_density(
            lifted @ density @ lifted.conj().T,
            self.tolerance,
            "spin_transport.output_qutrit_density",
        )

    def path(self, points: Iterable[Sequence[float]]) -> SpinPathReport:
        points = tuple(
            _readonly_real(self.base.point(point, "spin_path.point"))
            for point in points
        )
        if len(points) < 2:
            raise GovernanceError("a spin path needs at least two points")
        links = tuple(
            self.link(points[index], points[index + 1])
            for index in range(len(points) - 1)
        )
        unitary = np.eye(2, dtype=complex)
        for link in links:
            unitary = link.unitary @ unitary
        unitary = _su2(unitary, self.tolerance, "spin_path.unitary")
        half_trace = 0.5 * complex(np.trace(unitary))
        identity_distance = float(np.linalg.norm(unitary - np.eye(2), ord="fro"))
        negative_identity_distance = float(
            np.linalg.norm(unitary + np.eye(2), ord="fro")
        )
        is_loop = bool(
            np.linalg.norm(points[0] - points[-1]) <= self.tolerance
        )
        return SpinPathReport(
            points=points,
            links=links,
            unitary=unitary,
            is_loop=is_loop,
            signed_half_trace=float(half_trace.real),
            trace_imaginary_defect=float(abs(half_trace.imag)),
            identity_distance=identity_distance,
            negative_identity_distance=negative_identity_distance,
            projective_identity_distance=min(
                identity_distance,
                negative_identity_distance,
            ),
            tolerance=self.tolerance,
        )

    def loop(self, points: Iterable[Sequence[float]]) -> SpinHolonomyReport:
        path = self.path(points)
        if len(path.points) < 4 or not path.is_loop:
            raise GovernanceError(
                "a spin holonomy witness needs a closed polygon with three edges"
            )
        flat = _readonly_complex(np.eye(2, dtype=complex))
        return SpinHolonomyReport(
            path=path,
            flat_control_unitary=flat,
            flat_control_identity_distance=0.0,
            omitted_chirality=_omitted_chirality_remainder(),
        )

    def curvature_span(self) -> ChiralCurvatureSpanReport:
        planes = tuple(
            (left, right)
            for left in range(4)
            for right in range(left + 1, 4)
        )
        components = np.column_stack(
            [
                _SELF_DUAL[:, left, right] / self.base.radius_squared
                for left, right in planes
            ]
        )
        singular_values = np.linalg.svd(components, compute_uv=False)
        cutoff = (
            64.0
            * np.finfo(float).eps
            * max(components.shape)
            * max(1.0, float(singular_values[0]))
        )
        rank = int(np.count_nonzero(singular_values > cutoff))
        if rank != 3:
            raise GovernanceError("positive-chiral curvature did not span su(2)")
        return ChiralCurvatureSpanReport(
            planes=planes,
            curvature_components=_readonly_real(components),
            singular_values=_readonly_real(singular_values),
            rank=rank,
            rank_cutoff=float(cutoff),
        )

    def triangle_curvature(self, epsilon: float) -> TriangleCurvatureReport:
        epsilon = _finite(epsilon, "triangle.epsilon")
        if epsilon <= 0.0 or epsilon >= 1.0:
            raise GovernanceError("triangle epsilon must lie in (0, 1)")
        origin = np.zeros(4)
        first = np.array([epsilon, 0.0, 0.0, 0.0])
        second = np.array([0.0, epsilon, 0.0, 0.0])
        holonomy = self.loop((origin, first, second, origin))
        angle = math.atan(epsilon * epsilon)
        expected = (
            np.eye(2, dtype=complex)
            + 1.0j * epsilon * epsilon * _PAULI[2]
        ) / math.sqrt(1.0 + epsilon**4)
        expected = _su2(expected, self.tolerance, "triangle.expected_unitary")
        unitary_defect = float(
            np.linalg.norm(holonomy.path.unitary - expected, ord="fro")
        )
        area = 2.0 * self.base.radius_squared * angle
        spin_rotation = -2.0 * angle
        area_rotation_defect = abs(
            spin_rotation + area / self.base.radius_squared
        )

        plus_x = 0.5 * np.array(
            [[1.0, 1.0], [1.0, 1.0]],
            dtype=complex,
        )
        sigma3 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
        unitary = holonomy.path.unitary
        moved_plus_x = unitary @ plus_x @ unitary.conj().T
        moved_sigma3 = unitary @ sigma3 @ unitary.conj().T
        trace = quantum_trace_distance(
            plus_x,
            moved_plus_x,
            self.tolerance,
        )
        fidelity = quantum_root_fidelity(
            plus_x,
            moved_plus_x,
            self.tolerance,
        )
        sigma3_trace = quantum_trace_distance(
            sigma3,
            moved_sigma3,
            self.tolerance,
        )
        expected_trace = epsilon * epsilon / math.sqrt(1.0 + epsilon**4)
        expected_fidelity = 1.0 / math.sqrt(1.0 + epsilon**4)
        if max(
            unitary_defect,
            area_rotation_defect,
            abs(trace - expected_trace),
            abs(fidelity - expected_fidelity),
            sigma3_trace,
        ) > self.tolerance:
            raise GovernanceError("exact H4 triangle curvature control failed")
        return TriangleCurvatureReport(
            epsilon=epsilon,
            hyperbolic_area=area,
            spin_rotation_angle=spin_rotation,
            holonomy=holonomy,
            expected_unitary=expected,
            unitary_defect=unitary_defect,
            area_rotation_defect=area_rotation_defect,
            plus_x_trace_distance=trace,
            expected_plus_x_trace_distance=expected_trace,
            plus_x_root_fidelity=fidelity,
            expected_plus_x_root_fidelity=expected_fidelity,
            sigma3_blind_trace_distance=sigma3_trace,
        )


@dataclass(frozen=True)
class SectionalAcceleratorBoundary:
    """Typed controls adapted from the pinned NNN sectional accelerator."""

    base: PoincareBallBase = UNIVERSAL_POINCARE_BASE
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        tolerance = _numerical_tolerance(
            self.tolerance,
            "sectional_boundary.tolerance",
            maximum=1e-10,
        )
        _universal_h4(self.base, "the sectional boundary")
        object.__setattr__(self, "tolerance", tolerance)

    @staticmethod
    def hadamard4() -> np.ndarray:
        matrix = 0.5 * np.array(
            [
                [1.0, 1.0, 1.0, 1.0],
                [1.0, -1.0, 1.0, -1.0],
                [1.0, 1.0, -1.0, -1.0],
                [1.0, -1.0, -1.0, 1.0],
            ]
        )
        return _readonly_real(matrix)

    def hadamard_spin_gate(self) -> np.ndarray:
        gate = 1.0j / math.sqrt(2.0) * np.array(
            [[1.0, 1.0], [1.0, -1.0]],
            dtype=complex,
        )
        return _su2(gate, self.tolerance, "sectional.hadamard_spin_gate")

    def fixed_phase_gate(self) -> np.ndarray:
        phase = _GEN100_PHASE
        gate = np.diag(
            [
                np.exp(-0.5j * phase),
                np.exp(0.5j * phase),
            ]
        )
        return _su2(gate, self.tolerance, "sectional.fixed_phase_gate")

    def mobius_add(self, left, right) -> np.ndarray:
        """Strict unit-ball Mobius addition; unlike the source, never clip."""

        left = self.base.point(left, "sectional.mobius.left")
        right = self.base.point(right, "sectional.mobius.right")
        # Mobius translations can amplify an otherwise representable ball
        # coordinate into a chart point whose distance is not certifiable.
        # Reuse the base's stronger hyperboloid conditioning gate on both
        # operands and the result instead of accepting a coordinate-only pass.
        self.base.to_hyperboloid(left)
        self.base.to_hyperboloid(right)
        if np.array_equal(right, -left):
            return self.base.point(
                np.zeros(4),
                "sectional.mobius.exact_inverse",
            )
        left_sq = math.fsum(float(value) ** 2 for value in left)
        right_sq = math.fsum(float(value) ** 2 for value in right)
        inner = math.fsum(
            float(left[index]) * float(right[index]) for index in range(4)
        )
        product = left_sq * right_sq
        denominator = math.fsum((1.0, 2.0 * inner, product))
        if not math.isfinite(denominator) or denominator <= 0.0:
            raise GovernanceError("Mobius denominator must be finite and positive")
        denominator_scale = math.fsum(
            (1.0, 2.0 * abs(inner), abs(product))
        )
        left_coefficient = math.fsum((1.0, 2.0 * inner, right_sq))
        right_coefficient = math.fsum((1.0, -left_sq))
        numerator = np.array(
            [
                math.fsum(
                    (
                        left_coefficient * float(left[index]),
                        right_coefficient * float(right[index]),
                    )
                )
                for index in range(4)
            ]
        )
        numerator_scale = (
            abs(left_coefficient) * float(np.linalg.norm(left))
            + abs(right_coefficient) * float(np.linalg.norm(right))
        )
        machine = np.finfo(float).eps
        denominator_error = 16.0 * machine * denominator_scale
        numerator_error = 16.0 * machine * numerator_scale
        numerator_norm = float(np.linalg.norm(numerator))
        absolute_output_error_bound = (
            numerator_error / denominator
            + numerator_norm * denominator_error / (denominator * denominator)
        )
        if (
            not math.isfinite(absolute_output_error_bound)
            or absolute_output_error_bound > self.tolerance / 8.0
        ):
            raise GovernanceError(
                "Mobius addition is outside the conditioned float64 chart"
            )
        output = numerator / denominator
        output = self.base.point(output, "sectional.mobius.output")
        self.base.to_hyperboloid(output)
        return output

    def mobius_scalar(self, scalar: float, point) -> np.ndarray:
        scalar = _finite(scalar, "sectional.mobius.scalar")
        point = self.base.point(point, "sectional.mobius.scalar_point")
        norm = float(np.linalg.norm(point))
        if norm == 0.0:
            return point
        radial = math.tanh(scalar * math.atanh(norm))
        return self.base.point(
            radial * point / norm,
            "sectional.mobius.scalar_output",
        )

    def geodesic_section(self, source, target, parameter: float) -> np.ndarray:
        parameter = _finite(parameter, "sectional.geodesic.parameter")
        if parameter < 0.0 or parameter > 1.0:
            raise GovernanceError("geodesic parameter must lie in [0, 1]")
        source = self.base.point(source, "sectional.geodesic.source")
        target = self.base.point(target, "sectional.geodesic.target")
        displacement = self.mobius_add(-source, target)
        return self.mobius_add(
            source,
            self.mobius_scalar(parameter, displacement),
        )

    def split_boost(self, rapidity: float) -> np.ndarray:
        rapidity = _finite(rapidity, "sectional.split_rapidity")
        maximum_conditioned_rapidity = 0.5 * math.log(
            self.tolerance / (8.0 * np.finfo(float).eps)
        )
        if abs(rapidity) > maximum_conditioned_rapidity:
            raise GovernanceError(
                "split boost exceeds the conditioned float64 audit domain"
            )
        generator = so22_generators()["K02"]
        cosine = math.cosh(rapidity)
        sine = math.sinh(rapidity)
        boost = np.eye(4)
        boost[0, 0] = cosine
        boost[2, 2] = cosine
        boost[0, 2] = sine
        boost[2, 0] = sine
        expected = (
            np.eye(4)
            + sine * generator
            + (cosine - 1.0) * (generator @ generator)
        )
        if np.linalg.norm(boost - expected, ord="fro") > 1e-12:
            raise GovernanceError("split boost disagrees with its declared generator")
        return _readonly_real(boost)

    def refine(
        self,
        connection: ChiralSpinConnection,
        source,
        target,
        sections: int = 100,
    ) -> SectionalRefinementReport:
        if type(connection) is not ChiralSpinConnection:
            raise GovernanceError("sectional refinement needs a chiral connection")
        if connection.base.to_spec() != self.base.to_spec():
            raise CarrierMismatch("sectional refinement and spin link need one H4 base")
        if isinstance(sections, bool) or not isinstance(sections, int):
            raise GovernanceError("refinement sections must be an integer")
        if sections < 1 or sections > 4096:
            raise GovernanceError("refinement sections must lie in [1, 4096]")
        points = tuple(
            self.geodesic_section(source, target, index / sections)
            for index in range(sections + 1)
        )
        refined = connection.path(points)
        direct = connection.link(source, target)
        defect = float(np.linalg.norm(refined.unitary - direct.unitary, ord="fro"))
        maximum_segment = max(link.base_distance for link in refined.links)
        if defect > self.tolerance:
            raise GovernanceError("geodesic refinement changed the signed spin lift")
        return SectionalRefinementReport(
            sections=sections,
            direct_unitary=direct.unitary,
            refined_unitary=refined.unitary,
            composition_defect=defect,
            maximum_segment_distance=maximum_segment,
            tolerance=self.tolerance,
        )

    def audit(
        self,
        connection: ChiralSpinConnection,
        left,
        right,
        translation,
        rapidity: float,
    ) -> SectionalBoundaryReport:
        if type(connection) is not ChiralSpinConnection:
            raise GovernanceError("sectional audit needs a chiral connection")
        if connection.base.to_spec() != self.base.to_spec():
            raise CarrierMismatch("sectional audit and spin link need one H4 base")
        left = self.base.point(left, "sectional.audit.left")
        right = self.base.point(right, "sectional.audit.right")
        translation = self.base.point(
            translation,
            "sectional.audit.translation",
        )
        moved_left = self.mobius_add(translation, left)
        moved_right = self.mobius_add(translation, right)
        mobius_defect = abs(
            self.base.distance(left, right)
            - self.base.distance(moved_left, moved_right)
        )
        hadamard4 = self.hadamard4()
        h4_defect = float(
            np.linalg.norm(hadamard4.T @ hadamard4 - np.eye(4), ord="fro")
        )
        hadamard_spin = self.hadamard_spin_gate()
        h_unitary_defect = float(
            np.linalg.norm(
                hadamard_spin.conj().T @ hadamard_spin - np.eye(2),
                ord="fro",
            )
        )
        h_determinant_defect = abs(
            complex(np.linalg.det(hadamard_spin)) - 1.0
        )
        boost = self.split_boost(rapidity)
        split_defect = float(
            np.linalg.norm(boost.T @ _SPLIT_22 @ boost - _SPLIT_22, ord="fro")
        )
        hilbert_defect = float(
            np.linalg.norm(boost.T @ boost - np.eye(4), ord="fro")
        )
        phase_gate = self.fixed_phase_gate()
        phase_defect = float(
            np.linalg.norm(
                phase_gate.conj().T @ phase_gate - np.eye(2),
                ord="fro",
            )
        )
        if max(
            mobius_defect,
            h4_defect,
            h_unitary_defect,
            h_determinant_defect,
            split_defect,
            phase_defect,
        ) > self.tolerance:
            raise GovernanceError("sectional carrier-boundary audit failed")
        split_eligible = bool(hilbert_defect <= self.tolerance)
        if abs(rapidity) > self.tolerance and split_eligible:
            raise GovernanceError("a nonzero split boost was misclassified as unitary")
        return SectionalBoundaryReport(
            hadamard4=hadamard4,
            hadamard4_orthogonality_defect=h4_defect,
            hadamard_spin_gate=hadamard_spin,
            hadamard_spin_unitary_defect=h_unitary_defect,
            hadamard_spin_determinant_defect=float(h_determinant_defect),
            mobius_pair_distance_defect=mobius_defect,
            split_boost=boost,
            split_signature_defect=split_defect,
            split_hilbert_unitarity_defect=hilbert_defect,
            split_qiskit_eligible=split_eligible,
            fixed_phase=_GEN100_PHASE,
            fixed_phase_gate=phase_gate,
            fixed_phase_unitary_defect=phase_defect,
            generation=100,
            jitter=_GEN100_JITTER,
            perlin_seed=_GEN100_PERLIN_SEED,
            jitter_operational=False,
            perlin_seed_operational=False,
            split_remainder=_split_substrate_remainder(),
            tolerance=self.tolerance,
        )


def spinor_preparation_unitary(
    spinor,
    tolerance: float = 1e-10,
) -> np.ndarray:
    """Return the unique declared ``SU(2)`` preparation with first column ``z``."""

    tolerance = _numerical_tolerance(
        tolerance,
        "spinor_preparation.tolerance",
        maximum=1e-10,
    )
    spinor = _normalised_spinor(
        spinor,
        tolerance,
        "spinor_preparation.spinor",
    )
    output = np.array(
        [
            [spinor[0], -np.conj(spinor[1])],
            [spinor[1], np.conj(spinor[0])],
        ],
        dtype=complex,
    )
    return _su2(output, tolerance, "spinor_preparation.unitary")


def _load_qiskit_projection_types():
    try:
        import qiskit
        from qiskit import QuantumCircuit
        from qiskit.circuit.library import UnitaryGate
        from qiskit.quantum_info import DensityMatrix, Operator, Statevector
    except (ImportError, ModuleNotFoundError) as exc:
        raise QiskitProjectionUnavailable(
            "QB2 Qiskit projection requires the repository's qiskit>=2.0 dependency"
        ) from exc
    return (
        qiskit,
        QuantumCircuit,
        UnitaryGate,
        DensityMatrix,
        Operator,
        Statevector,
    )


def _typed_spin_links(
    path_or_links: SpinPathReport | ChiralSpinLink | Iterable[ChiralSpinLink],
    tolerance: float,
) -> tuple[ChiralSpinLink, ...]:
    """Normalize a geometric path without accepting detached SU(2) matrices."""

    if type(path_or_links) is SpinPathReport:
        links = path_or_links.links
    elif type(path_or_links) is ChiralSpinLink:
        links = (path_or_links,)
    else:
        try:
            links = tuple(path_or_links)
        except TypeError as exc:
            raise CarrierMismatch(
                "Qiskit projection requires a SpinPathReport or typed spin links"
            ) from exc
    if not links:
        raise GovernanceError(
            "Qiskit projection needs at least one typed geometric spin link"
        )
    for index, link in enumerate(links):
        if type(link) is not ChiralSpinLink:
            raise CarrierMismatch(
                "detached SU(2) matrices are not geometric spin-link carriers"
            )
        if (
            link.base_id != UNIVERSAL_POINCARE_BASE.id
            or abs(link.curvature_radius - UNIVERSAL_POINCARE_BASE.radius)
            > tolerance
        ):
            raise CarrierMismatch(
                "Qiskit spin link does not use the universal Poincare H4 base"
            )
        if (
            index
            and np.linalg.norm(links[index - 1].target - link.source)
            > tolerance
        ):
            raise CarrierMismatch(
                "typed spin links do not form one adjacent geometric path"
            )
    return tuple(links)


def project_spin_path_to_qiskit(
    path_or_links: SpinPathReport | ChiralSpinLink | Iterable[ChiralSpinLink],
    initial_spinor=(1.0 + 0.0j, 0.0 + 0.0j),
    tolerance: float = 1e-10,
) -> QiskitSpinProjectionReport:
    """Compile certified ``SU(2)`` links into one deterministic Qiskit qubit."""

    tolerance = _numerical_tolerance(
        tolerance,
        "qiskit_spin_projection.tolerance",
        maximum=1e-10,
    )
    links = _typed_spin_links(path_or_links, tolerance)
    spinor = _normalised_spinor(
        initial_spinor,
        tolerance,
        "qiskit_spin_projection.initial_spinor",
    )
    preparation = spinor_preparation_unitary(spinor, tolerance)
    path_unitary = np.eye(2, dtype=complex)
    for link in links:
        path_unitary = link.unitary @ path_unitary
    path_unitary = _su2(
        path_unitary,
        tolerance,
        "qiskit_spin_projection.path_unitary",
    )

    (
        qiskit,
        QuantumCircuit,
        UnitaryGate,
        DensityMatrix,
        Operator,
        Statevector,
    ) = _load_qiskit_projection_types()
    circuit = QuantumCircuit(1, name="hb0_qb2_spin")
    circuit.append(UnitaryGate(preparation, label="prepare_z"), [0])
    for index, link in enumerate(links):
        circuit.append(
            UnitaryGate(link.unitary, label=f"lc_plus_{index}"),
            [0],
        )

    expected_operator = path_unitary @ preparation
    circuit_operator = np.asarray(Operator(circuit).data, dtype=complex)
    output_statevector = np.asarray(
        Statevector.from_instruction(circuit).data,
        dtype=complex,
    )
    output_density = np.asarray(
        DensityMatrix.from_instruction(circuit).data,
        dtype=complex,
    )
    expected_statevector = path_unitary @ spinor
    expected_density = np.outer(
        expected_statevector,
        expected_statevector.conj(),
    )
    unitary_defect = float(
        np.linalg.norm(
            path_unitary.conj().T @ path_unitary - np.eye(2),
            ord="fro",
        )
    )
    determinant_defect = abs(complex(np.linalg.det(path_unitary)) - 1.0)
    operator_defect = float(
        np.linalg.norm(circuit_operator - expected_operator, ord="fro")
    )
    statevector_defect = float(
        np.linalg.norm(output_statevector - expected_statevector)
    )
    density_defect = float(
        np.linalg.norm(output_density - expected_density, ord="fro")
    )
    if max(
        unitary_defect,
        determinant_defect,
        operator_defect,
        statevector_defect,
        density_defect,
    ) > tolerance:
        raise GovernanceError("Qiskit did not realize the certified spin path")
    return QiskitSpinProjectionReport(
        circuit=circuit,
        qiskit_version=str(qiskit.__version__),
        base_id=UNIVERSAL_POINCARE_BASE.id,
        link_count=len(links),
        links=links,
        preparation_unitary=preparation,
        path_unitary=path_unitary,
        expected_circuit_operator=_readonly_complex(expected_operator),
        circuit_operator=_readonly_complex(circuit_operator),
        output_statevector=_readonly_complex(output_statevector),
        expected_statevector=_readonly_complex(expected_statevector),
        output_density=_readonly_complex(output_density),
        expected_density=_readonly_complex(expected_density),
        path_unitary_defect=unitary_defect,
        path_determinant_defect=float(determinant_defect),
        circuit_operator_defect=operator_defect,
        statevector_defect=statevector_defect,
        density_intertwining_defect=density_defect,
        simulator_only=True,
        backend_executed=False,
        advantage_claim=False,
        tolerance=tolerance,
    )


def probe_central_lift_qiskit(
    unitary,
    tolerance: float = 1e-10,
) -> CentralLiftProbeReport:
    """Expose the ``+I/-I`` Spin-lift sign with a controlled-unitary circuit."""

    tolerance = _numerical_tolerance(
        tolerance,
        "central_lift_probe.tolerance",
        maximum=1e-10,
    )
    unitary = _su2(unitary, tolerance, "central_lift_probe.unitary")
    (
        qiskit,
        QuantumCircuit,
        UnitaryGate,
        DensityMatrix,
        _Operator,
        Statevector,
    ) = _load_qiskit_projection_types()
    circuit = QuantumCircuit(2, name="hb0_qb2_central_sign")
    circuit.h(0)
    circuit.append(UnitaryGate(unitary, label="spin_lift").control(1), [0, 1])
    circuit.h(0)
    state = np.asarray(Statevector.from_instruction(circuit).data, dtype=complex)
    control_one_probability = float(
        sum(
            abs(state[index]) ** 2
            for index in range(state.size)
            if index & 1
        )
    )
    source_density = np.asarray(
        DensityMatrix([1.0 + 0.0j, 0.0 + 0.0j]).data,
        dtype=complex,
    )
    moved_density = unitary @ source_density @ unitary.conj().T
    density_change = float(
        np.linalg.norm(moved_density - source_density, ord="fro")
    )
    return CentralLiftProbeReport(
        circuit=circuit,
        qiskit_version=str(qiskit.__version__),
        unitary=unitary,
        positive_identity_distance=float(
            np.linalg.norm(unitary - np.eye(2), ord="fro")
        ),
        negative_identity_distance=float(
            np.linalg.norm(unitary + np.eye(2), ord="fro")
        ),
        density_change=density_change,
        control_one_probability=control_one_probability,
        simulator_only=True,
        backend_executed=False,
        tolerance=tolerance,
    )
