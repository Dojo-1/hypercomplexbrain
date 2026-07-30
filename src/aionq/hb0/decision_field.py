"""N-ary hypercomplex decision cells over the universal hyperbolic base.

The primary object is a complete simplex of at least three alternatives.  A
binary ``WallObservation`` is available only as an explicitly labelled edge
restriction; its ``CONTINUE``/``STOP`` label is never promoted to a global
decision.

Quaternion multiplication is load-bearing here: relations and ternary
orientation channels use the repository's Cayley-Dickson product.  Ordered
quality and Hamiltonian channels remain separate because quaternions have no
natural componentwise order.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
import re
from types import MappingProxyType
from typing import Mapping

import numpy as np

from ..cayley_dickson import cd_conjugate, cd_multiply
from ..governance import EvidenceTag, GovernanceError, registry
from ..sheaf import left_multiplication_matrix
from .core import (
    CarrierMismatch,
    FlatCollapseError,
    MindQualityField,
    RemainderEnvelope,
    _as_vector,
    _finite,
)
from .hyperbolic import LorentzIsometry, PoincareBallBase
from .mind import HamiltonianEnvelope
from .wall import OrthogonalWallChart, WallObservation, WallReport

__all__ = [
    "AlternativeSection",
    "BinaryFaceProjection",
    "DecisionCellReport",
    "DecisionFieldGluingReport",
    "DecisionFieldReport",
    "DecisionGluingTolerance",
    "EvidenceBinding",
    "HypercomplexAdiabaticCriterion",
    "HypercomplexDecisionField",
    "HypercomplexFieldPathReport",
    "HypercomplexFieldPathSample",
    "ObservationChannel",
    "QuaternionFieldChart",
    "glue_decision_fields",
    "trace_hypercomplex_field_path",
]


_QUATERNION_DIMENSION = 4
_MAX_ALTERNATIVES = 8
_MAX_FIELD_TOLERANCE = 1e-6
INFEASIBLE = "INFEASIBLE"
PARETO_SINGLETON_CANDIDATE = "PARETO_SINGLETON_CANDIDATE"
OPEN_MULTISECTION = "OPEN_MULTISECTION"


def _readonly(value) -> np.ndarray:
    contiguous = np.ascontiguousarray(value, dtype=float)
    return np.frombuffer(contiguous.tobytes(), dtype=float).reshape(contiguous.shape)


def _readonly_complex(value) -> np.ndarray:
    contiguous = np.ascontiguousarray(value, dtype=complex)
    return np.frombuffer(
        contiguous.tobytes(),
        dtype=complex,
    ).reshape(contiguous.shape)


def _mapping(values: Mapping) -> Mapping:
    return MappingProxyType(dict(values))


def _helmert(arity: int) -> np.ndarray:
    """Orthonormal coordinates for the zero-sum contrast subspace."""

    out = np.zeros((arity, arity - 1))
    for column in range(arity - 1):
        denominator = math.sqrt((column + 1) * (column + 2))
        out[: column + 1, column] = 1.0 / denominator
        out[column + 1, column] = -(column + 1) / denominator
    return out


def _svd_active_basis(
    matrix: np.ndarray,
    cutoff: float,
) -> tuple[int, np.ndarray, np.ndarray]:
    """Return rank, active right basis, and singular values at one shared cutoff."""

    _left, singular_values, right = np.linalg.svd(matrix, full_matrices=True)
    rank = int(np.count_nonzero(singular_values > cutoff))
    return rank, right[:rank, :].T, singular_values


def _hamiltonian_vector(envelope: HamiltonianEnvelope) -> np.ndarray:
    raw = np.array(
        [
            envelope.compute,
            envelope.coherence,
            envelope.identity,
            envelope.absorption,
            envelope.exploration_credit,
            envelope.integration_credit,
        ],
        dtype=float,
    )
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise GovernanceError("Hamiltonian components must be finite and non-negative")
    return raw


_SHA256_REFERENCE = re.compile(r"sha256:[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class EvidenceBinding:
    """Typed, citable evidence reference; not a verified witness.

    The binding does not resolve or rerun an artifact. It prevents arbitrary
    prose from masquerading as a reference, but it cannot make an alternative
    globally eligible. A decision report therefore remains open until a
    separate resolver and an explicit n-ary policy are supplied.
    """

    claim_id: str
    evidence_tag: str
    artifact_digest: str
    verification_mode: str

    def __post_init__(self) -> None:
        try:
            claim = registry.cite(self.claim_id)
        except (KeyError, GovernanceError) as exc:
            raise GovernanceError(
                f"evidence binding names a non-citable claim {self.claim_id!r}"
            ) from exc
        if self.evidence_tag != claim.tag:
            raise GovernanceError("evidence binding tag disagrees with the registry")
        if not _SHA256_REFERENCE.fullmatch(self.artifact_digest):
            raise GovernanceError("evidence binding needs a sha256 artifact digest")
        allowed_modes = {
            EvidenceTag.PROVED: {"kernel_checked", "recomputed"},
            EvidenceTag.AXIOMATIZED: {"recomputed"},
            EvidenceTag.MEASURED: {"recomputed"},
            EvidenceTag.HYPOTHESIS: {"recomputed"},
        }
        if self.verification_mode not in allowed_modes.get(self.evidence_tag, set()):
            raise GovernanceError(
                "evidence verification mode is incompatible with its evidence tag"
            )

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.claim_id,
            self.evidence_tag,
            self.artifact_digest,
            self.verification_mode,
        )

    @property
    def runtime_verified(self) -> bool:
        """Bindings are descriptors; verification belongs to an envelope resolver."""

        return False


@dataclass(frozen=True)
class AlternativeSection:
    """One vertex of the n-ary cell."""

    id: str
    base_point: np.ndarray
    quaternion: np.ndarray
    qualities: MindQualityField
    hamiltonian: HamiltonianEnvelope
    evidence_refs: tuple[EvidenceBinding, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise GovernanceError("an alternative section needs an id")
        base_point = _as_vector(self.base_point, f"{self.id}.base_point")
        quaternion = _as_vector(self.quaternion, f"{self.id}.quaternion")
        if quaternion.size != _QUATERNION_DIMENSION:
            raise CarrierMismatch("the first hypercomplex field slice uses quaternion fibers")
        if not isinstance(self.qualities, MindQualityField):
            raise GovernanceError("an alternative needs a typed MindQualityField")
        if not isinstance(self.hamiltonian, HamiltonianEnvelope):
            raise GovernanceError("an alternative needs a vector HamiltonianEnvelope")
        _hamiltonian_vector(self.hamiltonian)
        evidence_refs = tuple(self.evidence_refs)
        if any(not isinstance(item, EvidenceBinding) for item in evidence_refs):
            raise GovernanceError(
                "alternative evidence must use typed EvidenceBinding objects"
            )
        if len({item.key for item in evidence_refs}) != len(evidence_refs):
            raise GovernanceError("alternative evidence bindings must be unique")
        object.__setattr__(self, "base_point", _readonly(base_point))
        object.__setattr__(self, "quaternion", _readonly(quaternion))
        object.__setattr__(self, "evidence_refs", evidence_refs)


@dataclass(frozen=True)
class ObservationChannel:
    """A named linear observation operator on the quaternion fiber."""

    name: str
    operator: np.ndarray

    def __post_init__(self) -> None:
        if not self.name:
            raise GovernanceError("an observation channel needs a name")
        operator = np.array(self.operator, dtype=float, copy=True)
        if (
            operator.ndim != 2
            or operator.shape[1] != _QUATERNION_DIMENSION
            or operator.shape[0] < 1
            or not np.all(np.isfinite(operator))
        ):
            raise GovernanceError(
                "an observation operator must be a finite m x 4 matrix"
            )
        gain = float(np.linalg.norm(operator, ord=2))
        if not math.isfinite(gain) or gain > 1.0 + _MAX_FIELD_TOLERANCE:
            raise GovernanceError(
                "an observation channel must be a non-amplifying contraction"
            )
        object.__setattr__(self, "operator", _readonly(operator))

    @property
    def metric(self) -> np.ndarray:
        return _readonly(self.operator.T @ self.operator)


@dataclass(frozen=True)
class DecisionCellReport:
    """Rank-loss geometry of one simplex face."""

    members: tuple[str, ...]
    intrinsic_rank: int
    intrinsic_positive_gap: float | None
    intrinsic_null_projector: np.ndarray
    observed_ranks: Mapping[str, int]
    rank_losses: Mapping[str, int]
    positive_observed_gaps: Mapping[str, float | None]
    action_wall_projectors: Mapping[str, np.ndarray]
    contrast_witnesses: Mapping[str, tuple[np.ndarray, ...]]

    @property
    def degenerate_channels(self) -> tuple[str, ...]:
        return tuple(
            name for name, loss in self.rank_losses.items() if int(loss) > 0
        )

    @property
    def degenerate(self) -> bool:
        return bool(self.degenerate_channels)

    @property
    def intrinsic_nullity(self) -> int:
        return len(self.members) - 1 - self.intrinsic_rank


@dataclass(frozen=True)
class BinaryFaceProjection:
    first_id: str
    second_id: str
    channel: str
    report: WallReport
    global_decision_permitted: bool = False


@dataclass(frozen=True)
class DecisionFieldReport:
    field_id: str
    alternative_ids: tuple[str, ...]
    status: str
    frontier: tuple[str, ...]
    ineligible_ids: tuple[str, ...]
    dominance: Mapping[tuple[str, str], bool]
    pairwise_base_distances: Mapping[tuple[str, str], float]
    base_exterior_cells: Mapping[tuple[str, ...], np.ndarray]
    oriented_base_cells: Mapping[tuple[str, ...], float]
    quaternion_relations: Mapping[tuple[str, str], np.ndarray]
    ternary_omega: Mapping[tuple[str, str, str], np.ndarray]
    sector_order: tuple[str, ...]
    sector_coefficients: Mapping[int, np.ndarray]
    observed_sector_coefficients: Mapping[str, Mapping[int, np.ndarray]]
    sector_reconstruction_defect: float
    sector_parseval_defect: float
    cells: Mapping[tuple[str, ...], DecisionCellReport]
    intrinsic_collapses: tuple[tuple[str, ...], ...]
    irreducible_degeneracies: tuple[tuple[tuple[str, ...], str], ...]
    pareto_projection: tuple[str, ...]
    promotion_blockers: tuple[str, ...]
    remainders: tuple[RemainderEnvelope, ...]
    global_decision_permitted: bool = False

    @property
    def binary_faces_insufficient(self) -> bool:
        return any(
            len(cell) >= 3 for cell, _channel in self.irreducible_degeneracies
        )

    @property
    def irreducible_degeneracy_cells(self) -> tuple[tuple[str, ...], ...]:
        """Compatibility projection; channel-indexed data is authoritative."""

        return tuple(
            dict.fromkeys(cell for cell, _channel in self.irreducible_degeneracies)
        )

    def weighted_sum(self, *_args, **_kwargs):
        raise FlatCollapseError(
            "an n-ary hypercomplex field has no scalar promotion; inspect its "
            "frontier, channel ranks, relations, and higher cells"
        )


@dataclass(frozen=True)
class DecisionGluingTolerance:
    """Channel-typed overlap bounds; unlike units never share one epsilon."""

    base_distance: float = 1e-9
    fiber_norm: float = 1e-9
    quality_coordinate: float = 1e-12
    hamiltonian_component: float = 1e-12
    operator_norm: float = 1e-9
    coframe_norm: float = 1e-9
    sector_coefficient: float = 1e-9
    triple_cocycle: float = 1e-9

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = _finite(getattr(self, name), f"decision_gluing.{name}")
            if value <= 0.0:
                raise GovernanceError(
                    f"decision_gluing.{name} must be positive"
                )
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class HypercomplexDecisionField:
    """A complete n-ary quaternionic cell over the shared ``H^p`` atlas."""

    id: str
    carrier: str
    base: PoincareBallBase
    alternatives: tuple[AlternativeSection, ...]
    channels: tuple[ObservationChannel, ...]
    tolerance: float = 1e-10
    connection: str = "trivial_product"
    fiber_order_coframe: np.ndarray | None = None
    sector_order: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.carrier:
            raise GovernanceError("a hypercomplex decision field needs id and carrier")
        if not isinstance(self.base, PoincareBallBase):
            raise GovernanceError("a decision field needs the declared hyperbolic atlas")
        alternatives = tuple(self.alternatives)
        if not (3 <= len(alternatives) <= _MAX_ALTERNATIVES):
            raise GovernanceError(
                f"the n-ary field requires 3..{_MAX_ALTERNATIVES} alternatives"
            )
        ids = [alternative.id for alternative in alternatives]
        if len(ids) != len(set(ids)):
            raise GovernanceError("alternative ids must be unique")
        for alternative in alternatives:
            self.base._ball_point(  # validated copy already belongs to the section
                alternative.base_point,
                f"{alternative.id}.base_point",
            )
        channels = tuple(self.channels)
        if not channels:
            raise GovernanceError("a decision field needs at least one observation channel")
        channel_names = [channel.name for channel in channels]
        if len(channel_names) != len(set(channel_names)):
            raise GovernanceError("observation channel names must be unique")
        tolerance = _finite(self.tolerance, "decision_field.tolerance")
        if tolerance <= 0.0 or tolerance > _MAX_FIELD_TOLERANCE:
            raise GovernanceError(
                f"decision-field tolerance must lie in (0, {_MAX_FIELD_TOLERANCE}]"
            )
        if self.connection != "trivial_product":
            raise GovernanceError(
                "this slice implements only an explicit trivial-product fiber connection"
            )
        coframe = (
            np.eye(_QUATERNION_DIMENSION)
            if self.fiber_order_coframe is None
            else np.array(self.fiber_order_coframe, dtype=float, copy=True)
        )
        if coframe.shape != (_QUATERNION_DIMENSION, _QUATERNION_DIMENSION):
            raise GovernanceError("fiber order coframe must be a 4 x 4 matrix")
        if not np.all(np.isfinite(coframe)):
            raise GovernanceError("fiber order coframe must be finite")
        if float(np.linalg.norm(coframe @ coframe.T - np.eye(4), ord="fro")) > tolerance:
            raise GovernanceError("fiber order coframe must be orthogonal")
        sector_order = (
            tuple(sorted(ids))
            if self.sector_order is None
            else tuple(self.sector_order)
        )
        if len(sector_order) != len(ids) or set(sector_order) != set(ids):
            raise GovernanceError(
                "sector order must be one complete permutation of the alternatives"
            )
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "fiber_order_coframe", _readonly(coframe))
        object.__setattr__(self, "sector_order", sector_order)

    @property
    def alternative_ids(self) -> tuple[str, ...]:
        return tuple(alternative.id for alternative in self.alternatives)

    def _alternative_map(self) -> dict[str, AlternativeSection]:
        return {alternative.id: alternative for alternative in self.alternatives}

    def _cell_report(self, members: tuple[str, ...]) -> DecisionCellReport:
        alternatives = self._alternative_map()
        values = np.stack([alternatives[member].quaternion for member in members])
        helmert = _helmert(len(members))
        intrinsic_contrasts = values.T @ helmert
        intrinsic_singular_values = np.linalg.svd(
            intrinsic_contrasts,
            compute_uv=False,
        )
        shared_scale = max(
            1.0,
            float(intrinsic_singular_values[0])
            if intrinsic_singular_values.size
            else 0.0,
        )
        cutoff = self.tolerance * shared_scale
        intrinsic_rank, active_basis, intrinsic_singular_values = _svd_active_basis(
            intrinsic_contrasts,
            cutoff,
        )
        contrast_dimension = len(members) - 1
        intrinsic_null = np.eye(contrast_dimension) - active_basis @ active_basis.T
        intrinsic_action_null = helmert @ intrinsic_null @ helmert.T
        intrinsic_positive = intrinsic_singular_values[
            intrinsic_singular_values > cutoff
        ]
        observed_ranks = {}
        rank_losses = {}
        positive_observed_gaps = {}
        action_projectors = {}
        witnesses = {}
        for channel in self.channels:
            observed_on_active = (
                channel.operator @ intrinsic_contrasts @ active_basis
            )
            observed_rank, observed_active_basis, singular_values = _svd_active_basis(
                observed_on_active,
                cutoff,
            )
            positive_singular_values = singular_values[singular_values > cutoff]
            loss = intrinsic_rank - observed_rank
            hidden_active = (
                np.eye(intrinsic_rank)
                - observed_active_basis @ observed_active_basis.T
            )
            hidden_eigenvalues, hidden_eigenvectors = np.linalg.eigh(
                0.5 * (hidden_active + hidden_active.T)
            )
            hidden_basis = active_basis @ hidden_eigenvectors[
                :,
                hidden_eigenvalues > 0.5,
            ]
            contrast_projector = hidden_basis @ hidden_basis.T
            action_projector = helmert @ contrast_projector @ helmert.T
            channel_witnesses = tuple(
                _readonly(helmert @ hidden_basis[:, index])
                for index in range(hidden_basis.shape[1])
            )
            projector_defect = float(
                np.linalg.norm(
                    action_projector @ action_projector - action_projector,
                    ord="fro",
                )
            )
            projector_minimum = float(
                np.min(np.linalg.eigvalsh(action_projector))
            )
            if (
                hidden_basis.shape[1] != loss
                or projector_defect > 100.0 * self.tolerance
                or projector_minimum < -100.0 * self.tolerance
            ):
                raise GovernanceError(
                    "action-wall construction failed its rank/projector invariants"
                )
            observed_ranks[channel.name] = observed_rank
            rank_losses[channel.name] = loss
            positive_observed_gaps[channel.name] = (
                None
                if positive_singular_values.size == 0
                else float(np.min(positive_singular_values))
            )
            action_projectors[channel.name] = _readonly(action_projector)
            witnesses[channel.name] = channel_witnesses
        return DecisionCellReport(
            members=members,
            intrinsic_rank=intrinsic_rank,
            intrinsic_positive_gap=(
                None
                if intrinsic_positive.size == 0
                else float(np.min(intrinsic_positive))
            ),
            intrinsic_null_projector=_readonly(intrinsic_action_null),
            observed_ranks=_mapping(observed_ranks),
            rank_losses=_mapping(rank_losses),
            positive_observed_gaps=_mapping(positive_observed_gaps),
            action_wall_projectors=_mapping(action_projectors),
            contrast_witnesses=_mapping(witnesses),
        )

    def restrict_binary_face(
        self,
        first_id: str,
        second_id: str,
        channel: str,
        *,
        order_coframe: np.ndarray | None = None,
    ) -> BinaryFaceProjection:
        """Project one edge; the resulting label cannot govern the full cell."""

        if first_id == second_id:
            raise GovernanceError("a binary face needs two distinct alternatives")
        alternatives = self._alternative_map()
        if first_id not in alternatives or second_id not in alternatives:
            raise GovernanceError("binary face names an unknown alternative")
        channels = {item.name: item for item in self.channels}
        if channel not in channels:
            raise GovernanceError(f"unknown observation channel {channel!r}")
        first = alternatives[first_id]
        second = alternatives[second_id]
        edge_coframe = (
            self.fiber_order_coframe
            if order_coframe is None
            else order_coframe
        )
        observation = WallObservation(
            section_id=f"{self.id}:{first_id}>{second_id}:{channel}",
            carrier=f"{self.carrier}:edge:{channel}",
            continue_coordinates=first.quaternion,
            stop_coordinates=second.quaternion,
            metric=channels[channel].metric,
            evidence_refs=tuple(
                sorted(
                    {
                        f"{binding.claim_id}@{binding.artifact_digest}"
                        for binding in first.evidence_refs + second.evidence_refs
                    }
                )
            ),
            tolerance=self.tolerance,
            order_coframe=edge_coframe,
        )
        return BinaryFaceProjection(
            first_id=first_id,
            second_id=second_id,
            channel=channel,
            report=observation.analyse(),
        )

    def _dominates(
        self,
        first: AlternativeSection,
        second: AlternativeSection,
    ) -> bool:
        first_quality = first.qualities.as_array()
        second_quality = second.qualities.as_array()
        first_h = _hamiltonian_vector(first.hamiltonian)
        second_h = _hamiltonian_vector(second.hamiltonian)
        quality_ok = bool(np.all(first_quality >= second_quality - self.tolerance))
        cost_ok = bool(np.all(first_h[:4] <= second_h[:4] + self.tolerance))
        credit_ok = bool(np.all(first_h[4:] >= second_h[4:] - self.tolerance))
        strict = bool(
            np.any(first_quality > second_quality + self.tolerance)
            or np.any(first_h[:4] < second_h[:4] - self.tolerance)
            or np.any(first_h[4:] > second_h[4:] + self.tolerance)
        )
        return quality_ok and cost_ok and credit_ok and strict

    def analyse(self) -> DecisionFieldReport:
        alternatives = self._alternative_map()
        ids = self.alternative_ids
        bound = tuple(
            alternative.id for alternative in self.alternatives if alternative.evidence_refs
        )
        ineligible = tuple(item for item in ids if item not in bound)
        dominance = {}
        for first_id, second_id in combinations(ids, 2):
            first_dominates = self._dominates(
                alternatives[first_id],
                alternatives[second_id],
            )
            second_dominates = self._dominates(
                alternatives[second_id],
                alternatives[first_id],
            )
            dominance[(first_id, second_id)] = first_dominates
            dominance[(second_id, first_id)] = second_dominates
        pareto_projection = tuple(
            candidate
            for candidate in ids
            if not any(
                dominance.get((other, candidate), False)
                for other in ids
                if other != candidate
            )
        )

        base_distances = {}
        for left, right in combinations(ids, 2):
            base_distances[(left, right)] = self.base.distance(
                alternatives[left].base_point,
                alternatives[right].base_point,
            )

        base_exterior_cells = {}
        oriented_base_cells = {}
        maximum_base_arity = min(self.base.dimension + 1, len(ids))
        for arity in range(3, maximum_base_arity + 1):
            for members in combinations(ids, arity):
                lifts = np.stack([
                    self.base.to_hyperboloid(alternatives[member].base_point)
                    for member in members
                ])
                plucker = np.asarray([
                    np.linalg.det(lifts[:, columns])
                    for columns in combinations(
                        range(self.base.dimension + 1),
                        arity,
                    )
                ])
                base_exterior_cells[members] = _readonly(plucker)
                if arity == self.base.dimension + 1:
                    oriented_base_cells[members] = float(plucker[0])

        relations = {}
        for first in ids:
            for second in ids:
                if first == second:
                    continue
                relations[(first, second)] = _readonly(
                    cd_multiply(
                        alternatives[first].quaternion,
                        cd_conjugate(alternatives[second].quaternion),
                    )
                )

        ternary_omega = {}
        for first, second, third in combinations(ids, 3):
            first_difference = (
                alternatives[first].quaternion - alternatives[third].quaternion
            )
            second_difference = (
                alternatives[second].quaternion - alternatives[third].quaternion
            )
            omega = cd_multiply(
                first_difference,
                cd_conjugate(second_difference),
            ) - cd_multiply(
                second_difference,
                cd_conjugate(first_difference),
            )
            ternary_omega[(first, second, third)] = _readonly(omega)

        sector_values = np.stack([
            alternatives[alternative_id].quaternion
            for alternative_id in self.sector_order
        ])
        sector_matrix = np.fft.fft(sector_values, axis=0, norm="ortho")
        sector_reconstruction = np.fft.ifft(
            sector_matrix,
            axis=0,
            norm="ortho",
        )
        sector_reconstruction_defect = float(
            np.linalg.norm(sector_reconstruction - sector_values, ord="fro")
        )
        sector_parseval_defect = abs(
            float(np.sum(np.abs(sector_values) ** 2))
            - float(np.sum(np.abs(sector_matrix) ** 2))
        )
        sector_coefficients = _mapping({
            sector: _readonly_complex(sector_matrix[sector])
            for sector in range(len(self.sector_order))
        })
        observed_sector_coefficients = {}
        for channel in self.channels:
            observed_values = np.stack([
                channel.operator @ alternatives[alternative_id].quaternion
                for alternative_id in self.sector_order
            ])
            observed_matrix = np.fft.fft(
                observed_values,
                axis=0,
                norm="ortho",
            )
            observed_sector_coefficients[channel.name] = _mapping({
                sector: _readonly_complex(observed_matrix[sector])
                for sector in range(len(self.sector_order))
            })

        cells = {}
        for arity in range(2, len(ids) + 1):
            for members in combinations(ids, arity):
                cells[members] = self._cell_report(members)
        irreducible = []
        for members, report in cells.items():
            if len(members) < 3:
                continue
            for channel, loss in report.rank_losses.items():
                if loss <= 0:
                    continue
                proper_degenerate = any(
                    cells[subcell].rank_losses[channel] > 0
                    for arity in range(2, len(members))
                    for subcell in combinations(members, arity)
                )
                if not proper_degenerate:
                    irreducible.append((members, channel))

        higher_obstructions = tuple(
            (members, channel)
            for members, report in cells.items()
            if len(members) >= 3
            for channel, loss in report.rank_losses.items()
            if loss > 0
        )
        intrinsic_collapses = tuple(
            members
            for members, report in cells.items()
            if len(members) >= 3 and report.intrinsic_nullity > 0
        )
        promotion_blockers = [
            "nary_decision_policy_absent",
            "evidence_bindings_not_runtime_verified",
        ]
        if ineligible:
            promotion_blockers.append("unbound_evidence")
        if higher_obstructions:
            promotion_blockers.append("higher_cell_observation_loss")
        if intrinsic_collapses:
            promotion_blockers.append("intrinsic_quaternion_carrier_collapse")
        if not pareto_projection:
            status = INFEASIBLE
            frontier = ()
        elif len(pareto_projection) == 1:
            status = PARETO_SINGLETON_CANDIDATE
            frontier = pareto_projection
        else:
            status = OPEN_MULTISECTION
            frontier = pareto_projection

        remainders = []
        remainders.append(
            RemainderEnvelope(
                name="[R]_decision_frontier",
                channel="formal",
                carrier=f"{self.carrier}:frontier",
                evidence_tag=EvidenceTag.HYPOTHESIS,
                statement=(
                    "no Pareto candidate is available"
                    if status == INFEASIBLE
                    else (
                        "global decision remains open: Pareto is only a projection, "
                        "bindings are unresolved, and no n-ary policy is registered"
                    )
                ),
                assumptions=(
                    "all Fourier sectors Fin(n) remain explicit",
                    "Pareto dominance is only a governance projection",
                    "quality benefits, Hamiltonian costs, and credits remain separate",
                ),
                provenance="aionq.hb0.decision_field.HypercomplexDecisionField.analyse",
            )
        )
        for members in intrinsic_collapses:
            remainders.append(
                RemainderEnvelope(
                    name="[R]_intrinsic_cell_collapse",
                    channel="formal",
                    carrier=f"{self.carrier}:cell:{'/'.join(members)}",
                    evidence_tag=EvidenceTag.MEASURED,
                    statement=(
                        "this quaternion R4 fiber cannot carry every independent "
                        "zero-sum contrast of the complete simplex face"
                    ),
                    instrument="contrast-dimension-minus-intrinsic-rank",
                    magnitude=float(cells[members].intrinsic_nullity),
                    assumptions=(
                        "fixed four-real-dimensional quaternion carrier",
                        "complete n-ary Helmert contrast space",
                    ),
                    provenance=(
                        "aionq.hb0.decision_field."
                        "HypercomplexDecisionField._cell_report"
                    ),
                )
            )
        for members, report in cells.items():
            for channel, loss in report.rank_losses.items():
                if loss <= 0:
                    continue
                remainders.append(
                    RemainderEnvelope(
                        name="[R]_decision_cell",
                        channel="formal",
                        carrier=f"{self.carrier}:cell:{'/'.join(members)}:{channel}",
                        evidence_tag=EvidenceTag.MEASURED,
                        statement=(
                            "the observation channel loses an intrinsic zero-sum "
                            "contrast of this complete simplex face"
                        ),
                        instrument="intrinsic-contrast-rank-minus-observed-rank",
                        magnitude=float(loss),
                        assumptions=(
                            "finite quaternion coordinate carrier",
                            "declared linear observation channel",
                            "Helmert-centered n-ary contrasts",
                        ),
                        provenance=(
                            "aionq.hb0.decision_field."
                            "HypercomplexDecisionField._cell_report"
                        ),
                    )
                )

        return DecisionFieldReport(
            field_id=self.id,
            alternative_ids=ids,
            status=status,
            frontier=frontier,
            ineligible_ids=ineligible,
            dominance=_mapping(dominance),
            pairwise_base_distances=_mapping(base_distances),
            base_exterior_cells=_mapping(base_exterior_cells),
            oriented_base_cells=_mapping(oriented_base_cells),
            quaternion_relations=_mapping(relations),
            ternary_omega=_mapping(ternary_omega),
            sector_order=self.sector_order,
            sector_coefficients=sector_coefficients,
            observed_sector_coefficients=_mapping(observed_sector_coefficients),
            sector_reconstruction_defect=sector_reconstruction_defect,
            sector_parseval_defect=sector_parseval_defect,
            cells=_mapping(cells),
            intrinsic_collapses=intrinsic_collapses,
            irreducible_degeneracies=tuple(irreducible),
            pareto_projection=pareto_projection,
            promotion_blockers=tuple(promotion_blockers),
            remainders=tuple(remainders),
            global_decision_permitted=False,
        )

    def weighted_sum(self, *_args, **_kwargs):
        raise FlatCollapseError(
            "a hypercomplex decision field cannot be collapsed to one score"
        )


@dataclass(frozen=True)
class QuaternionFieldChart:
    """Product chart: a base isometry and associative quaternion left action."""

    source_carrier: str
    atlas_carrier: str
    unit_quaternion: np.ndarray
    base_isometry: LorentzIsometry | None = None
    tolerance: float = 1e-10

    def __post_init__(self) -> None:
        if not self.source_carrier or not self.atlas_carrier:
            raise GovernanceError("a quaternion field chart needs source and atlas carriers")
        tolerance = _finite(self.tolerance, "quaternion_chart.tolerance")
        if tolerance <= 0.0 or tolerance > _MAX_FIELD_TOLERANCE:
            raise GovernanceError(
                f"quaternion-chart tolerance must lie in (0, {_MAX_FIELD_TOLERANCE}]"
            )
        unit = _as_vector(self.unit_quaternion, "unit_quaternion")
        if unit.size != _QUATERNION_DIMENSION:
            raise CarrierMismatch("quaternion field charts require a 4-vector unit")
        norm = float(np.linalg.norm(unit))
        if abs(norm - 1.0) > tolerance:
            raise GovernanceError("quaternion field chart label must have unit norm")
        matrix = left_multiplication_matrix(unit)
        defect = float(np.linalg.norm(matrix.T @ matrix - np.eye(4), ord="fro"))
        if defect > tolerance:
            raise GovernanceError("unit quaternion did not produce an orthogonal action")
        object.__setattr__(self, "unit_quaternion", _readonly(unit))
        object.__setattr__(self, "tolerance", tolerance)

    @property
    def fiber_matrix(self) -> np.ndarray:
        return _readonly(left_multiplication_matrix(self.unit_quaternion))

    def transport(self, field: HypercomplexDecisionField) -> HypercomplexDecisionField:
        if field.carrier != self.source_carrier:
            raise CarrierMismatch("quaternion chart source does not match the field")
        if self.base_isometry is not None and (
            self.base_isometry.dimension != field.base.dimension
        ):
            raise CarrierMismatch("base isometry dimension does not match the field")
        matrix = self.fiber_matrix
        alternatives = []
        for alternative in field.alternatives:
            if self.base_isometry is None:
                base_point = alternative.base_point
            else:
                lift = field.base.to_hyperboloid(alternative.base_point)
                moved = field.base.apply_isometry(self.base_isometry, lift)
                base_point = field.base.from_hyperboloid(moved)
            alternatives.append(
                AlternativeSection(
                    id=alternative.id,
                    base_point=base_point,
                    quaternion=matrix @ alternative.quaternion,
                    qualities=alternative.qualities,
                    hamiltonian=alternative.hamiltonian,
                    evidence_refs=alternative.evidence_refs,
                )
            )
        channels = tuple(
            ObservationChannel(channel.name, channel.operator @ matrix.T)
            for channel in field.channels
        )
        return HypercomplexDecisionField(
            id=field.id,
            carrier=self.atlas_carrier,
            base=field.base,
            alternatives=tuple(alternatives),
            channels=channels,
            tolerance=max(field.tolerance, self.tolerance),
            connection=field.connection,
            fiber_order_coframe=field.fiber_order_coframe @ matrix.T,
            sector_order=field.sector_order,
        )


@dataclass(frozen=True)
class DecisionFieldGluingReport:
    local_reports: Mapping[str, DecisionFieldReport]
    overlap_defects: Mapping[tuple[str, str], Mapping[str, float]]
    channel_maxima: Mapping[str, float]
    channel_gates: Mapping[str, bool]
    triple_cocycle_defects: Mapping[tuple[str, str, str], float]
    glued: bool
    remainders: tuple[RemainderEnvelope, ...]


def glue_decision_fields(
    fields: Mapping[str, HypercomplexDecisionField],
    charts: Mapping[str, QuaternionFieldChart],
    tolerances: DecisionGluingTolerance | None = None,
) -> DecisionFieldGluingReport:
    """Glue complete fields; no edge label is aggregated into a global decision."""

    tolerances = tolerances or DecisionGluingTolerance()
    if not isinstance(tolerances, DecisionGluingTolerance):
        raise GovernanceError(
            "field gluing requires channel-typed DecisionGluingTolerance"
        )
    if len(fields) < 2 or set(fields) != set(charts):
        raise GovernanceError(
            "field gluing needs at least two local fields and one chart per field"
        )
    transported = {
        name: charts[name].transport(field) for name, field in fields.items()
    }
    carriers = {field.carrier for field in transported.values()}
    if len(carriers) != 1:
        raise CarrierMismatch("transported decision fields need one atlas carrier")
    base_specs = {repr(field.base.to_spec()) for field in transported.values()}
    if len(base_specs) != 1:
        raise CarrierMismatch("transported decision fields use different hyperbolic bases")
    id_sets = {frozenset(field.alternative_ids) for field in transported.values()}
    channel_sets = {
        frozenset(channel.name for channel in field.channels)
        for field in transported.values()
    }
    if len(id_sets) != 1 or len(channel_sets) != 1:
        raise CarrierMismatch("local fields must share alternatives and observation channels")

    reports = {name: field.analyse() for name, field in transported.items()}
    overlap_defects = {}
    channel_names = (
        "base",
        "fiber",
        "qualities",
        "quality_policy",
        "hamiltonian",
        "evidence",
        "operator",
        "connection",
        "coframe",
        "sector",
        "sector_order",
        "cell_structure",
        "triple_cocycle",
    )
    maxima = {name: 0.0 for name in channel_names}
    for (left_name, left), (right_name, right) in combinations(
        transported.items(),
        2,
    ):
        left_alternatives = left._alternative_map()
        right_alternatives = right._alternative_map()
        defects = {name: 0.0 for name in channel_names}
        for alternative_id in sorted(left_alternatives):
            left_alt = left_alternatives[alternative_id]
            right_alt = right_alternatives[alternative_id]
            defects["base"] = max(
                defects["base"],
                left.base.distance(left_alt.base_point, right_alt.base_point),
            )
            defects["fiber"] = max(
                defects["fiber"],
                float(np.linalg.norm(left_alt.quaternion - right_alt.quaternion)),
            )
            defects["qualities"] = max(
                defects["qualities"],
                float(
                    np.max(
                        np.abs(
                            left_alt.qualities.as_array()
                            - right_alt.qualities.as_array()
                        )
                    )
                ),
            )
            defects["quality_policy"] = max(
                defects["quality_policy"],
                float(
                    left_alt.qualities.obligations
                    != right_alt.qualities.obligations
                    or left_alt.qualities.kill_conditions
                    != right_alt.qualities.kill_conditions
                ),
            )
            defects["hamiltonian"] = max(
                defects["hamiltonian"],
                float(
                    np.max(
                        np.abs(
                            _hamiltonian_vector(left_alt.hamiltonian)
                            - _hamiltonian_vector(right_alt.hamiltonian)
                        )
                    )
                ),
            )
            defects["evidence"] = max(
                defects["evidence"],
                float(
                    {item.key for item in left_alt.evidence_refs}
                    != {item.key for item in right_alt.evidence_refs}
                ),
            )
        left_report = reports[left_name]
        right_report = reports[right_name]
        defects["sector_order"] = float(
            left_report.sector_order != right_report.sector_order
        )
        if not defects["sector_order"]:
            defects["sector"] = max(
                float(
                    np.linalg.norm(
                        left_report.sector_coefficients[sector]
                        - right_report.sector_coefficients[sector]
                    )
                )
                for sector in left_report.sector_coefficients
            )
        left_channels = {channel.name: channel for channel in left.channels}
        right_channels = {channel.name: channel for channel in right.channels}
        for channel_name in left_channels:
            defects["operator"] = max(
                defects["operator"],
                float(
                    np.linalg.norm(
                        left_channels[channel_name].operator
                        - right_channels[channel_name].operator,
                        ord="fro",
                    )
                ),
            )
        defects["connection"] = float(left.connection != right.connection)
        defects["coframe"] = float(
            np.linalg.norm(
                left.fiber_order_coframe - right.fiber_order_coframe,
                ord="fro",
            )
        )
        left_cells = reports[left_name].cells
        right_cells = reports[right_name].cells
        left_cells_by_members = {
            frozenset(members): report for members, report in left_cells.items()
        }
        right_cells_by_members = {
            frozenset(members): report for members, report in right_cells.items()
        }
        defects["cell_structure"] = float(
            any(
                left_cells_by_members[members].rank_losses
                != right_cells_by_members[members].rank_losses
                or left_cells_by_members[members].intrinsic_rank
                != right_cells_by_members[members].intrinsic_rank
                for members in left_cells_by_members
            )
        )
        overlap_defects[(left_name, right_name)] = _mapping(defects)
        for name, value in defects.items():
            maxima[name] = max(maxima[name], value)

    triple_cocycle_defects = {}
    for first_name, second_name, third_name in combinations(
        sorted(transported),
        3,
    ):
        first_matrix = charts[first_name].fiber_matrix
        second_matrix = charts[second_name].fiber_matrix
        third_matrix = charts[third_name].fiber_matrix
        first_to_second = second_matrix.T @ first_matrix
        second_to_third = third_matrix.T @ second_matrix
        third_to_first = first_matrix.T @ third_matrix
        defect = float(
            np.linalg.norm(
                third_to_first @ second_to_third @ first_to_second
                - np.eye(_QUATERNION_DIMENSION),
                ord="fro",
            )
        )
        triple_cocycle_defects[
            (first_name, second_name, third_name)
        ] = defect
        maxima["triple_cocycle"] = max(maxima["triple_cocycle"], defect)

    bounds = {
        "base": tolerances.base_distance,
        "fiber": tolerances.fiber_norm,
        "qualities": tolerances.quality_coordinate,
        "hamiltonian": tolerances.hamiltonian_component,
        "operator": tolerances.operator_norm,
        "coframe": tolerances.coframe_norm,
        "sector": tolerances.sector_coefficient,
        "triple_cocycle": tolerances.triple_cocycle,
    }
    exact_channels = {
        "quality_policy",
        "evidence",
        "connection",
        "sector_order",
        "cell_structure",
    }
    gates = {
        name: (
            value == 0.0
            if name in exact_channels
            else value <= bounds[name]
        )
        for name, value in maxima.items()
    }
    remainders = tuple(
        RemainderEnvelope(
            name="[R]_decision_gluing",
            channel="coherence",
            carrier=f"{next(iter(carriers))}:{channel}",
            evidence_tag=EvidenceTag.MEASURED,
            statement=f"complete n-ary fields disagree on the {channel} channel",
            instrument=f"all-pairs-{channel}-overlap-defect",
            magnitude=value,
            assumptions=("no cross-channel scalar compensation",),
            provenance="aionq.hb0.decision_field.glue_decision_fields",
        )
        for channel, value in maxima.items()
        if not gates[channel]
    )
    return DecisionFieldGluingReport(
        local_reports=_mapping(reports),
        overlap_defects=_mapping(overlap_defects),
        channel_maxima=_mapping(maxima),
        channel_gates=_mapping(gates),
        triple_cocycle_defects=_mapping(triple_cocycle_defects),
        glued=all(gates.values()),
        remainders=remainders,
    )


@dataclass(frozen=True)
class HypercomplexFieldPathSample:
    parameter: float
    field: HypercomplexDecisionField

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "parameter",
            _finite(self.parameter, "hypercomplex_path.parameter"),
        )
        if not isinstance(self.field, HypercomplexDecisionField):
            raise GovernanceError("a hypercomplex path sample needs a decision field")


@dataclass(frozen=True)
class HypercomplexAdiabaticCriterion:
    """Separate finite-path budgets; no universal rate or energy scalar."""

    parameter_name: str
    parameter_unit: str
    min_singular_gap: float
    max_base_speed: float
    max_omega_rate: float
    max_quality_speed: float
    max_hamiltonian_speed: float
    max_fiber_load: float
    max_operator_load: float
    max_projector_load: float

    def __post_init__(self) -> None:
        if not self.parameter_name or not self.parameter_unit:
            raise GovernanceError("a hypercomplex path criterion must name its parameter")
        for name in (
            "min_singular_gap",
            "max_base_speed",
            "max_omega_rate",
            "max_quality_speed",
            "max_hamiltonian_speed",
            "max_fiber_load",
            "max_operator_load",
            "max_projector_load",
        ):
            value = _finite(getattr(self, name), f"hypercomplex_criterion.{name}")
            if value <= 0.0:
                raise GovernanceError(f"{name} must be positive")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class HypercomplexFieldPathReport:
    criterion: HypercomplexAdiabaticCriterion
    parameters: tuple[float, ...]
    frontiers: tuple[tuple[str, ...], ...]
    intrinsic_ranks: tuple[int, ...]
    observed_ranks: Mapping[str, tuple[int, ...]]
    wall_ranks: Mapping[str, tuple[int, ...]]
    minimum_intrinsic_gap: float | None
    minimum_singular_gaps: Mapping[str, float | None]
    maximum_base_speed: float
    maximum_omega_rate: float
    maximum_quality_speed: float
    maximum_hamiltonian_speed: float
    maximum_fiber_loads: Mapping[str, float | None]
    maximum_operator_loads: Mapping[str, float | None]
    maximum_projector_loads: Mapping[str, float | None]
    frontier_stable: bool
    evidence_stable: bool
    quality_policy_stable: bool
    channel_gates: Mapping[str, bool]
    adiabatic_certified_under_policy: bool
    violations: tuple[str, ...]


def trace_hypercomplex_field_path(
    samples: tuple[HypercomplexFieldPathSample, ...],
    criterion: HypercomplexAdiabaticCriterion,
) -> HypercomplexFieldPathReport:
    """Certify an n-ary path by independent geometric and channel budgets.

    All samples must already be transported to one atlas carrier.  The full
    simplex wall rank must stay fixed.  Fiber, operator, and wall-projector
    rates are divided by the squared positive singular gap of each observation
    channel; base and quaternion-orientation rates retain separate direct
    budgets.
    """

    if len(samples) < 2:
        raise GovernanceError("a hypercomplex field path needs at least two samples")
    if not isinstance(criterion, HypercomplexAdiabaticCriterion):
        raise GovernanceError("a hypercomplex field path needs a typed criterion")
    parameters = tuple(sample.parameter for sample in samples)
    if any(right <= left for left, right in zip(parameters, parameters[1:])):
        raise GovernanceError("hypercomplex path parameters must be strictly increasing")
    fields = tuple(sample.field for sample in samples)
    carriers = {field.carrier for field in fields}
    alternative_orders = {field.alternative_ids for field in fields}
    channel_orders = {
        tuple(channel.name for channel in field.channels) for field in fields
    }
    base_specs = {repr(field.base.to_spec()) for field in fields}
    connections = {field.connection for field in fields}
    if len(carriers) != 1 or len(alternative_orders) != 1:
        raise CarrierMismatch("path fields must share one carrier and alternative order")
    if len(channel_orders) != 1 or len(base_specs) != 1 or len(connections) != 1:
        raise CarrierMismatch("path fields must share channels and hyperbolic base")

    reports = tuple(field.analyse() for field in fields)
    full_members = fields[0].alternative_ids
    full_cells = tuple(report.cells[full_members] for report in reports)
    channel_names = tuple(channel.name for channel in fields[0].channels)
    intrinsic_ranks = tuple(cell.intrinsic_rank for cell in full_cells)
    intrinsic_gaps = tuple(cell.intrinsic_positive_gap for cell in full_cells)
    minimum_intrinsic_gap = (
        None
        if any(gap is None for gap in intrinsic_gaps)
        else min(float(gap) for gap in intrinsic_gaps)
    )
    observed_ranks = {
        channel: tuple(cell.observed_ranks[channel] for cell in full_cells)
        for channel in channel_names
    }
    wall_ranks = {
        channel: tuple(cell.rank_losses[channel] for cell in full_cells)
        for channel in channel_names
    }
    gap_sequences = {
        channel: tuple(cell.positive_observed_gaps[channel] for cell in full_cells)
        for channel in channel_names
    }
    minimum_gaps = {
        channel: (
            None
            if any(gap is None for gap in gaps)
            else min(float(gap) for gap in gaps)
        )
        for channel, gaps in gap_sequences.items()
    }

    base_speeds = []
    omega_rates = []
    fiber_rates = []
    quality_speeds = []
    hamiltonian_speeds = []
    evidence_stable = True
    quality_policy_stable = True
    operator_rates = {channel: [] for channel in channel_names}
    projector_rates = {channel: [] for channel in channel_names}
    fiber_loads = {channel: [] for channel in channel_names}
    operator_loads = {channel: [] for channel in channel_names}
    projector_loads = {channel: [] for channel in channel_names}
    for index, (left, right) in enumerate(zip(fields, fields[1:])):
        delta_parameter = parameters[index + 1] - parameters[index]
        left_alternatives = left._alternative_map()
        right_alternatives = right._alternative_map()
        base_speed = max(
            left.base.distance(
                left_alternatives[alternative].base_point,
                right_alternatives[alternative].base_point,
            )
            / delta_parameter
            for alternative in full_members
        )
        fiber_rate = max(
            float(
                np.linalg.norm(
                    right_alternatives[alternative].quaternion
                    - left_alternatives[alternative].quaternion
                )
            )
            / delta_parameter
            for alternative in full_members
        )
        base_speeds.append(base_speed)
        fiber_rates.append(fiber_rate)
        quality_speeds.append(
            max(
                float(
                    np.linalg.norm(
                        right_alternatives[alternative].qualities.as_array()
                        - left_alternatives[alternative].qualities.as_array(),
                        ord=np.inf,
                    )
                )
                / delta_parameter
                for alternative in full_members
            )
        )
        hamiltonian_speeds.append(
            max(
                float(
                    np.linalg.norm(
                        _hamiltonian_vector(
                            right_alternatives[alternative].hamiltonian
                        )
                        - _hamiltonian_vector(
                            left_alternatives[alternative].hamiltonian
                        ),
                        ord=np.inf,
                    )
                )
                / delta_parameter
                for alternative in full_members
            )
        )
        for alternative in full_members:
            left_alternative = left_alternatives[alternative]
            right_alternative = right_alternatives[alternative]
            evidence_stable = evidence_stable and (
                {item.key for item in left_alternative.evidence_refs}
                == {item.key for item in right_alternative.evidence_refs}
            )
            quality_policy_stable = quality_policy_stable and (
                left_alternative.qualities.obligations
                == right_alternative.qualities.obligations
                and left_alternative.qualities.kill_conditions
                == right_alternative.qualities.kill_conditions
            )

        left_omega = reports[index].ternary_omega
        right_omega = reports[index + 1].ternary_omega
        omega_rate = max(
            (
                float(np.linalg.norm(right_omega[cell] - left_omega[cell]))
                / delta_parameter
                for cell in left_omega
            ),
            default=0.0,
        )
        omega_rates.append(omega_rate)

        left_channels = {channel.name: channel for channel in left.channels}
        right_channels = {channel.name: channel for channel in right.channels}
        for channel in channel_names:
            operator_rate = (
                float(
                    np.linalg.norm(
                        right_channels[channel].operator
                        - left_channels[channel].operator,
                        ord=2,
                    )
                )
                / delta_parameter
            )
            projector_rate = (
                float(
                    np.linalg.norm(
                        full_cells[index + 1].action_wall_projectors[channel]
                        - full_cells[index].action_wall_projectors[channel],
                        ord=2,
                    )
                )
                / delta_parameter
            )
            operator_rates[channel].append(operator_rate)
            projector_rates[channel].append(projector_rate)
            left_gap = gap_sequences[channel][index]
            right_gap = gap_sequences[channel][index + 1]
            if left_gap is None or right_gap is None:
                continue
            pair_gap = min(float(left_gap), float(right_gap))
            fiber_loads[channel].append(fiber_rate / pair_gap**2)
            operator_loads[channel].append(operator_rate / pair_gap**2)
            projector_loads[channel].append(projector_rate / pair_gap**2)

    maximum_base_speed = max(base_speeds)
    maximum_omega_rate = max(omega_rates)
    maximum_quality_speed = max(quality_speeds)
    maximum_hamiltonian_speed = max(hamiltonian_speeds)
    maximum_fiber_loads = {
        channel: (
            None
            if len(fiber_loads[channel]) != len(samples) - 1
            else max(fiber_loads[channel])
        )
        for channel in channel_names
    }
    maximum_operator_loads = {
        channel: (
            None
            if len(operator_loads[channel]) != len(samples) - 1
            else max(operator_loads[channel])
        )
        for channel in channel_names
    }
    maximum_projector_loads = {
        channel: (
            None
            if len(projector_loads[channel]) != len(samples) - 1
            else max(projector_loads[channel])
        )
        for channel in channel_names
    }

    gates = {
        "base_speed": maximum_base_speed <= criterion.max_base_speed,
        "omega_rate": maximum_omega_rate <= criterion.max_omega_rate,
        "quality_speed": (
            maximum_quality_speed <= criterion.max_quality_speed
        ),
        "hamiltonian_speed": (
            maximum_hamiltonian_speed <= criterion.max_hamiltonian_speed
        ),
        "intrinsic_rank_constant": len(set(intrinsic_ranks)) == 1,
        "intrinsic_singular_gap": (
            minimum_intrinsic_gap is not None
            and minimum_intrinsic_gap >= criterion.min_singular_gap
        ),
        "frontier_stable": len(
            {
                (report.status, report.frontier, report.promotion_blockers)
                for report in reports
            }
        )
        == 1,
        "evidence_stable": evidence_stable,
        "quality_policy_stable": quality_policy_stable,
    }
    violations = []
    for gate, passed in gates.items():
        if not passed:
            violations.append(f"{gate}_exceeds_bound")
    for channel in channel_names:
        gap = minimum_gaps[channel]
        rank_constant = len(set(wall_ranks[channel])) == 1
        observed_rank_constant = len(set(observed_ranks[channel])) == 1
        channel_gates = {
            f"{channel}:wall_rank_constant": rank_constant,
            f"{channel}:observed_rank_constant": observed_rank_constant,
            f"{channel}:singular_gap": (
                gap is not None and gap >= criterion.min_singular_gap
            ),
            f"{channel}:fiber_load": (
                maximum_fiber_loads[channel] is not None
                and maximum_fiber_loads[channel] <= criterion.max_fiber_load
            ),
            f"{channel}:operator_load": (
                maximum_operator_loads[channel] is not None
                and maximum_operator_loads[channel] <= criterion.max_operator_load
            ),
            f"{channel}:projector_load": (
                maximum_projector_loads[channel] is not None
                and maximum_projector_loads[channel]
                <= criterion.max_projector_load
            ),
        }
        gates.update(channel_gates)
        violations.extend(
            name.replace(":", "_")
            for name, passed in channel_gates.items()
            if not passed
        )

    return HypercomplexFieldPathReport(
        criterion=criterion,
        parameters=parameters,
        frontiers=tuple(report.frontier for report in reports),
        intrinsic_ranks=intrinsic_ranks,
        observed_ranks=_mapping(observed_ranks),
        wall_ranks=_mapping(wall_ranks),
        minimum_intrinsic_gap=minimum_intrinsic_gap,
        minimum_singular_gaps=_mapping(minimum_gaps),
        maximum_base_speed=maximum_base_speed,
        maximum_omega_rate=maximum_omega_rate,
        maximum_quality_speed=maximum_quality_speed,
        maximum_hamiltonian_speed=maximum_hamiltonian_speed,
        maximum_fiber_loads=_mapping(maximum_fiber_loads),
        maximum_operator_loads=_mapping(maximum_operator_loads),
        maximum_projector_loads=_mapping(maximum_projector_loads),
        frontier_stable=gates["frontier_stable"],
        evidence_stable=evidence_stable,
        quality_policy_stable=quality_policy_stable,
        channel_gates=_mapping(gates),
        adiabatic_certified_under_policy=all(gates.values()),
        violations=tuple(violations),
    )
