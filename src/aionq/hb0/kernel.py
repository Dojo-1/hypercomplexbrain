"""HB-0 coupled event loop and the 32-worldlet reference factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from ..recognition.budget import BordonBudget
from .core import (CarrierMismatch, ChartFunctor, ClockSpec, CosmosCage,
                   FunctionalOrgan, GerbeCell, LocalGeometry, ProfunctorTendril,
                   RemainderEnvelope, WorldletState, TransportObservation,
                   _as_vector, _finite, _unit_interval)
from .identity import IdentityEcology, IdentityRegime
from .hyperbolic import (
    EuclideanBaseControl,
    HyperbolicBaseReview,
    PoincareBallBase,
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
)
from .mind import (ContactHamiltonianGovernor, HamiltonianEnvelope, ViabilityBounds,
                   ViabilityReport)


@dataclass(frozen=True)
class KernelStepReport:
    tick: int
    accepted: bool
    transport_remainders: tuple[RemainderEnvelope, ...]
    coherence_remainders: tuple[RemainderEnvelope, ...]
    viability: ViabilityReport
    governance_reasons: tuple[str, ...]
    evidence_tag: str = EvidenceTag.HYPOTHESIS


@dataclass(frozen=True)
class UniversalBaseCoverageReview:
    """Structural audit of the universal base/fiber separation."""

    base_id: str
    point_count: int
    affine_rank: int
    hyperboloid_rank: int
    tangent_rank: int
    local_fiber_geometries: tuple[str, ...]
    euclidean_ablation_present: bool
    cages_share_base: bool
    intrinsic_geometry: HyperbolicBaseReview
    passed: bool
    violations: tuple[str, ...]


@dataclass
class PolycosmicKernel:
    """The HB-0 event loop over a shared base and heterogeneous local fibers."""

    base: PoincareBallBase
    euclidean_base_control: EuclideanBaseControl
    base_points: Mapping[str, np.ndarray]
    worldlets: dict[str, WorldletState]
    tendrils: dict[str, ProfunctorTendril]
    gerbe_cells: dict[str, GerbeCell]
    cages: CosmosCage
    organs: dict[str, FunctionalOrgan]
    clocks: dict[str, ClockSpec]
    identity: IdentityEcology
    governor: ContactHamiltonianGovernor
    budget: BordonBudget
    tick: int = 0
    evidence_ledger: list[KernelStepReport] = field(default_factory=list)
    _contract_locked: bool = field(default=False, init=False, repr=False)

    def __setattr__(self, name, value) -> None:
        if (
            name in {"base", "euclidean_base_control", "base_points"}
            and getattr(self, "_contract_locked", False)
        ):
            raise AttributeError(f"{name} is an immutable universal-base contract")
        super().__setattr__(name, value)

    def __post_init__(self) -> None:
        if not isinstance(self.base, PoincareBallBase):
            raise GovernanceError("HB-0 requires the typed universal Poincare base")
        if self.base.scope != "universal_atlas":
            raise GovernanceError("HB-0 base must be the universal Poincare atlas")
        if (
            not isinstance(self.euclidean_base_control, EuclideanBaseControl)
            or self.euclidean_base_control.dimension != self.base.dimension
        ):
            raise GovernanceError(
                "HB-0 requires a dimension-matched Euclidean base control"
            )
        if not np.allclose(
            self.euclidean_base_control.metric_tensor,
            self.base.metric_tensor(np.zeros(self.base.dimension)),
            rtol=self.base.tolerance,
            atol=self.base.tolerance,
        ):
            raise GovernanceError(
                "Euclidean base control must match the Poincare tangent metric at origin"
            )
        if len(self.worldlets) < 4:
            raise GovernanceError("HB-0 requires at least four worldlets")
        for label, objects in (
            ("worldlet", self.worldlets),
            ("tendril", self.tendrils),
            ("gerbe cell", self.gerbe_cells),
            ("organ", self.organs),
            ("clock", self.clocks),
        ):
            mismatched = sorted(
                key
                for key, value in objects.items()
                if key != getattr(value, "id", None)
            )
            if mismatched:
                raise GovernanceError(
                    f"{label} mapping keys must equal object ids: {mismatched}"
                )
        if set(self.base_points) != set(self.worldlets):
            raise GovernanceError("every worldlet needs exactly one universal-base point")
        self.base_points = MappingProxyType(
            {
                worldlet_id: self.base.point(point, f"{worldlet_id}.base_point")
                for worldlet_id, point in self.base_points.items()
            }
        )
        geometries = {w.local_geometry for w in self.worldlets.values()}
        if len(geometries) < 2:
            raise GovernanceError("HB-0 collapsed to one local geometry")
        if len(self.clocks) < 3 or len({c.period for c in self.clocks.values()}) < 3:
            raise GovernanceError("HB-0 requires three genuinely distinct clocks")
        undeclared_clocks = {
            clock
            for worldlet in self.worldlets.values()
            for clock in worldlet.clocks
            if clock not in self.clocks
        }
        if undeclared_clocks:
            raise GovernanceError(
                f"worldlets reference undeclared clocks: {sorted(undeclared_clocks)}"
            )
        for tendril in self.tendrils.values():
            if tendril.source not in self.worldlets or tendril.target not in self.worldlets:
                raise GovernanceError(f"{tendril.id}: unknown endpoint")
        cage_worldlets = {wid for cage in self.cages.walk() for wid in cage.worldlet_ids}
        missing = set(self.worldlets) - cage_worldlets
        if missing:
            raise GovernanceError(f"worldlets outside the Russian-doll cover: {sorted(missing)}")
        wrong_base = {
            cage.id for cage in self.cages.walk() if cage.base_id != self.base.id
        }
        if wrong_base:
            raise GovernanceError(
                f"cosmos cages missing universal base identity: {sorted(wrong_base)}"
            )
        self._contract_locked = True

    def base_distance(self, left_worldlet: str, right_worldlet: str) -> float:
        """Distance on the shared base; local fiber metrics remain separate."""

        try:
            left = self.base_points[left_worldlet]
            right = self.base_points[right_worldlet]
        except KeyError as exc:
            raise GovernanceError(f"unknown base-point worldlet {exc.args[0]!r}") from exc
        return self.base.distance(left, right)

    def euclidean_base_distance(
        self,
        left_worldlet: str,
        right_worldlet: str,
    ) -> float:
        """Matched ``R^n`` distance on the same coordinate observations."""

        try:
            left = self.base_points[left_worldlet]
            right = self.base_points[right_worldlet]
        except KeyError as exc:
            raise GovernanceError(f"unknown base-point worldlet {exc.args[0]!r}") from exc
        return self.euclidean_base_control.distance(left, right)

    def review_universal_base(self) -> UniversalBaseCoverageReview:
        """Review coverage without inferring curvature from the fiber graph."""

        points = tuple(self.base_points.values())
        stacked = np.stack(points)
        affine_rank = int(np.linalg.matrix_rank(stacked[1:] - stacked[0]))
        lifts = np.stack(tuple(self.base.to_hyperboloid(point) for point in points))
        hyperboloid_rank = int(np.linalg.matrix_rank(lifts))
        tangent_vectors = np.stack(
            tuple(
                self.base.log(lifts[0], lift)
                for lift in lifts[1:]
            )
        )
        tangent_rank = int(np.linalg.matrix_rank(tangent_vectors))
        local_geometries = tuple(
            sorted({worldlet.local_geometry for worldlet in self.worldlets.values()})
        )
        euclidean_present = (
            isinstance(self.euclidean_base_control, EuclideanBaseControl)
            and self.euclidean_base_control.dimension == self.base.dimension
            and np.allclose(
                self.euclidean_base_control.metric_tensor,
                self.base.metric_tensor(np.zeros(self.base.dimension)),
                rtol=self.base.tolerance,
                atol=self.base.tolerance,
            )
        )
        cages_share_base = all(
            cage.base_id == self.base.id for cage in self.cages.walk()
        )
        intrinsic = self.base.review(points)
        violations = []
        if hyperboloid_rank != self.base.dimension + 1:
            violations.append("hyperboloid_lifts_do_not_span_ambient_carrier")
        if tangent_rank != self.base.dimension:
            violations.append("logarithmic_tangents_do_not_span_base")
        if len(local_geometries) < 2:
            violations.append("local_fiber_geometry_collapsed")
        if not euclidean_present:
            violations.append("missing_or_mismatched_euclidean_ablation")
        if not cages_share_base:
            violations.append("cage_base_identity_mismatch")
        if not intrinsic.passed:
            violations.append("intrinsic_hyperbolic_review_failed")
        return UniversalBaseCoverageReview(
            base_id=self.base.id,
            point_count=len(points),
            affine_rank=affine_rank,
            hyperboloid_rank=hyperboloid_rank,
            tangent_rank=tangent_rank,
            local_fiber_geometries=local_geometries,
            euclidean_ablation_present=euclidean_present,
            cages_share_base=cages_share_base,
            intrinsic_geometry=intrinsic,
            passed=not violations,
            violations=tuple(violations),
        )

    def _snapshot(self) -> dict[str, np.ndarray]:
        return {wid: worldlet.coordinates.copy() for wid, worldlet in self.worldlets.items()}

    def _restore(self, snapshot: Mapping[str, np.ndarray]) -> None:
        for wid, coordinates in snapshot.items():
            self.worldlets[wid].coordinates = coordinates.copy()

    def _transport_observations(self) -> list[TransportObservation]:
        observations = []
        for tendril in self.tendrils.values():
            if tendril.woven:
                observations.append(tendril.transport(self.worldlets[tendril.source].coordinates))
        return observations

    def step(
        self,
        deltas: Mapping[str, np.ndarray],
        *,
        absorption: float = 0.0,
        lob_trap: float = 0.0,
        authorized_sources: Mapping[str, float] | None = None,
    ) -> KernelStepReport:
        unknown = set(deltas) - set(self.worldlets)
        if unknown:
            raise GovernanceError(f"deltas supplied for unknown worldlets {sorted(unknown)}")
        absorption = _unit_interval(absorption, "absorption")
        lob_trap = _unit_interval(lob_trap, "lob_trap")
        cleaned_deltas = {}
        for wid, delta in deltas.items():
            cleaned = _as_vector(delta, f"{wid}.delta")
            if cleaned.shape != self.worldlets[wid].coordinates.shape:
                raise CarrierMismatch(
                    f"{wid}: delta shape {cleaned.shape} != "
                    f"{self.worldlets[wid].coordinates.shape}"
                )
            cleaned_deltas[wid] = cleaned
        allowed_sources = {"compute", "coherence", "identity", "absorption"}
        unknown_sources = set(authorized_sources or {}) - allowed_sources
        if unknown_sources:
            raise GovernanceError(
                f"unknown authorized source channels {sorted(unknown_sources)}"
            )
        cleaned_sources = {}
        for name, value in (authorized_sources or {}).items():
            cleaned = _finite(value, f"authorized_source.{name}")
            if cleaned < 0.0:
                raise GovernanceError(
                    f"authorized_source.{name} must be non-negative"
                )
            cleaned_sources[name] = cleaned

        previous_tick = self.tick
        snapshot = self._snapshot()
        budget_snapshot = (
            self.budget.level,
            self.budget.speculative_draw,
            self.budget.state,
            list(self.budget.interventions),
        )
        try:
            self.tick = previous_tick + 1
            before_transport = self._transport_observations()
            before_glue = (
                float(np.mean([
                    o.remainder.magnitude
                    for o in before_transport
                    if o.remainder.magnitude is not None
                ]))
                if before_transport
                else 0.0
            )
            before_identity_defect = 1.0 - self.identity.identity_fidelity()
            before_envelope = HamiltonianEnvelope(
                compute=0.0,
                coherence=before_glue,
                identity=before_identity_defect,
                absorption=absorption,
            )

            for wid, delta in cleaned_deltas.items():
                worldlet = self.worldlets[wid]
                active_rates = [
                    self.clocks[clock].rate
                    for clock in worldlet.clocks
                    if self.clocks[clock].due(self.tick)
                ]
                if active_rates:
                    worldlet.apply_delta(delta, rate=min(active_rates))

            observations = self._transport_observations()
            transport_remainders = tuple(o.remainder for o in observations)
            coherence_remainders = tuple(
                cell.remainder() for cell in self.gerbe_cells.values()
            )
            glue_defect = (
                float(np.mean([
                    remainder.magnitude
                    for remainder in transport_remainders
                    if remainder.magnitude is not None
                ]))
                if transport_remainders
                else 0.0
            )
            gerbe_defect = (
                float(np.mean([
                    remainder.magnitude
                    for remainder in coherence_remainders
                    if remainder.magnitude is not None
                ]))
                if coherence_remainders
                else 0.0
            )
            identity_defect = 1.0 - self.identity.identity_fidelity()
            compute = float(sum(observation.cost for observation in observations)
                            + len(cleaned_deltas))
            observed = {
                "gluing_defect": glue_defect + gerbe_defect,
                "identity_defect": identity_defect,
                "absorption": absorption,
                "compute": compute,
                "plurality": self.identity.plurality(),
                "lob_trap": lob_trap,
                "fragmentation": self.identity.fragmentation_risk(),
            }
            after_envelope = HamiltonianEnvelope(
                compute=compute,
                coherence=glue_defect + gerbe_defect,
                identity=identity_defect,
                absorption=absorption,
            )
            sources = dict(cleaned_sources)
            sources.setdefault("compute", compute)
            sources.setdefault(
                "coherence",
                max(0.0, after_envelope.coherence - before_envelope.coherence),
            )
            sources.setdefault(
                "identity",
                max(0.0, after_envelope.identity - before_envelope.identity),
            )
            sources.setdefault("absorption", 0.0)
            decision = self.governor.decide(
                before_envelope,
                after_envelope,
                sources,
                observed,
            )
            if not decision.accepted:
                self._restore(snapshot)
            self.budget.charge(compute * 0.01)
            self.budget.tick(self.tick)
            report = KernelStepReport(
                tick=self.tick,
                accepted=decision.accepted,
                transport_remainders=transport_remainders,
                coherence_remainders=coherence_remainders,
                viability=decision.viability,
                governance_reasons=decision.reasons,
            )
            self.evidence_ledger.append(report)
            return report
        except Exception:
            self._restore(snapshot)
            self.tick = previous_tick
            (
                self.budget.level,
                self.budget.speculative_draw,
                self.budget.state,
                interventions,
            ) = budget_snapshot
            self.budget.interventions[:] = interventions
            raise


def _orthogonal(dim: int, rng: np.random.Generator) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(dim, dim)))
    return q * np.sign(np.diag(r))


def build_hb0(
    seed: int = 0,
    n_worldlets: int = 32,
    dim: int = 4,
    base_dim: int | None = None,
) -> PolycosmicKernel:
    """Construct the minimal 32-worldlet HB-0 reference system.

    Four identity regimes receive eight local worlds each.  Every worldlet has a
    point in one universal ``H^n`` Poincare atlas, while Poincare,
    Fisher/Riemannian, and Euclidean-control structures remain heterogeneous
    fiber geometries.  Universal base does not collapse those fibers.
    """
    if n_worldlets < 8 or n_worldlets % 4:
        raise GovernanceError("n_worldlets must be a multiple of four and at least eight")
    if dim < 1:
        raise GovernanceError("worldlet fiber dimension must be positive")
    if base_dim is None:
        base_dim = max(3, dim)
    if isinstance(base_dim, bool) or not isinstance(base_dim, (int, np.integer)):
        raise GovernanceError("universal Poincare base dimension must be an integer")
    base_dim = int(base_dim)
    if base_dim < 3 or base_dim >= n_worldlets:
        raise GovernanceError(
            "universal Poincare base dimension must lie in [3, n_worldlets)"
        )
    rng = np.random.default_rng(seed)
    base_rng = np.random.default_rng(seed ^ 0xA10)
    if base_dim == UNIVERSAL_POINCARE_BASE.dimension:
        base = UNIVERSAL_POINCARE_BASE
        euclidean_base_control = UNIVERSAL_EUCLIDEAN_CONTROL
    else:
        base = PoincareBallBase(
            f"AION-universal-H{base_dim}",
            base_dim,
            sectional_curvature=-1.0,
            scope="universal_atlas",
            euclidean_control_declared=True,
        )
        euclidean_base_control = EuclideanBaseControl(
            f"AION-universal-euclidean-control-R{base_dim}",
            base_dim,
            metric_scale=2.0 * base.radius,
        )
    clocks = {
        "fast": ClockSpec("fast", period=1, rate=1.0, role="local inference"),
        "meso": ClockSpec("meso", period=4, rate=0.1, role="coalition consolidation"),
        "slow": ClockSpec("slow", period=16, rate=0.01, role="identity and evidence"),
    }
    regime_names = ("somatic", "episodic", "social", "prospective")
    geometries = (
        LocalGeometry.POINCARE_BALL,
        LocalGeometry.FISHER_METRIC,
        LocalGeometry.EUCLIDEAN_CONTROL,
        LocalGeometry.RIEMANNIAN_CHART,
    )
    worldlets: dict[str, WorldletState] = {}
    base_points: dict[str, np.ndarray] = {}
    regime_members: dict[str, list[str]] = {name: [] for name in regime_names}
    per_regime = n_worldlets // 4
    for regime_index, regime in enumerate(regime_names):
        for local_index in range(per_regime):
            wid = f"W_{regime}_{local_index:02d}"
            coordinates = rng.normal(scale=0.08, size=dim)
            if geometries[regime_index] == LocalGeometry.POINCARE_BALL:
                coordinates = coordinates / max(1.0, 2.0 * np.linalg.norm(coordinates))
            metric = None
            if geometries[regime_index] in (
                LocalGeometry.FISHER_METRIC,
                LocalGeometry.RIEMANNIAN_CHART,
            ):
                diagonal = 1.0 + rng.random(dim)
                metric = np.diag(diagonal)
            clocks_for_worldlet = (
                ("fast", "meso")
                if regime in ("somatic", "social")
                else ("meso", "slow")
            )
            worldlets[wid] = WorldletState(
                id=wid,
                carrier=f"section_R{dim}",
                local_geometry=geometries[regime_index],
                algebra_regime=("quaternion_diagnostic" if local_index % 4 == 0 else "real_control"),
                coordinates=coordinates,
                clocks=clocks_for_worldlet,
                observers=("self", "auditor"),
                boundary="permeability-gated local chart",
                metric_tensor=metric,
                permeability=0.35 + 0.1 * regime_index,
                phase=2.0 * math.pi * local_index / per_regime,
                evidence_refs=("SEM-HB0-WORLDLET",),
            )
            direction = base_rng.normal(size=base_dim)
            direction /= np.linalg.norm(direction)
            base_radius = 0.12 + 0.10 * regime_index + 0.02 * (
                local_index / max(1, per_regime - 1)
            )
            base_points[wid] = base.point(
                base_radius * direction,
                f"{wid}.base_point",
            )
            regime_members[regime].append(wid)
    lifts = np.stack(
        tuple(base.to_hyperboloid(point) for point in base_points.values())
    )
    hyperboloid_rank = int(np.linalg.matrix_rank(lifts))
    tangent_vectors = np.stack(
        tuple(base.log(lifts[0], lift) for lift in lifts[1:])
    )
    tangent_rank = int(np.linalg.matrix_rank(tangent_vectors))
    if hyperboloid_rank != base_dim + 1 or tangent_rank != base_dim:
        raise GovernanceError(
            "universal-base placement failed its intrinsic ambient/tangent span"
        )

    tendrils: dict[str, ProfunctorTendril] = {}
    ids = list(worldlets)
    for index, source in enumerate(ids):
        target = ids[(index + 1) % len(ids)]
        matrix = _orthogonal(dim, rng)
        chart = ChartFunctor(
            id=f"F_{index:02d}",
            source_carrier=worldlets[source].carrier,
            target_carrier=worldlets[target].carrier,
            forward=lambda x, matrix=matrix: matrix @ x,
            backward=lambda y, matrix=matrix: matrix.T @ y,
            preserved=("dimension", "l2_norm", "provenance"),
            transformed=("local_coordinates",),
            lost=(),
        )
        tendrils[f"T_{index:02d}"] = ProfunctorTendril(
            id=f"T_{index:02d}",
            source=source,
            target=target,
            chart=chart,
            phase=worldlets[target].phase - worldlets[source].phase,
            cost=0.1,
        )

    comparisons: dict[tuple[str, str], ChartFunctor] = {}
    regimes: dict[str, IdentityRegime] = {}
    for regime in regime_names:
        section = np.mean([worldlets[wid].coordinates for wid in regime_members[regime]], axis=0)
        holonomies = (_orthogonal(dim, rng).astype(complex), np.eye(dim, dtype=complex))
        regimes[regime] = IdentityRegime(regime, section, holonomies, tuple(regime_members[regime]))
    for index, source in enumerate(regime_names):
        target = regime_names[(index + 1) % len(regime_names)]
        matrix = _orthogonal(dim, rng)
        comparisons[(source, target)] = ChartFunctor(
            id=f"J_{source}_{target}",
            source_carrier=f"identity:{source}",
            target_carrier=f"identity:{target}",
            forward=lambda x, matrix=matrix: matrix @ x,
            backward=lambda y, matrix=matrix: matrix.T @ y,
            preserved=("norm", "regime provenance"),
            transformed=("identity chart",),
            lost=(),
        )

    gerbe_cells = {}
    identity_matrix = np.eye(dim, dtype=complex)
    triples = (
        (regime_names[0], regime_names[1], regime_names[2]),
        (regime_names[1], regime_names[2], regime_names[3]),
    )
    for index, members in enumerate(triples):
        gerbe_cells[f"G_{index}"] = GerbeCell(
            id=f"G_{index}",
            members=members,
            g_ij=identity_matrix,
            g_jk=identity_matrix,
            g_ki=identity_matrix,
            eta_ijk=identity_matrix,
        )

    identity = IdentityEcology(
        regimes=regimes,
        comparisons=comparisons,
        higher_coherence=tuple(gerbe_cells.values()),
    )
    root = CosmosCage("C_root", "dynamic_cover", base_id=base.id)
    for regime in regime_names:
        root.add_child(
            CosmosCage(
                id=f"C_{regime}",
                geometry=worldlets[regime_members[regime][0]].local_geometry,
                worldlet_ids=tuple(regime_members[regime]),
                base_id=base.id,
            )
        )
    organs = {
        "perception": FunctionalOrgan(
            "perception", tuple(regime_members["somatic"]), "sensor boundary", 0.25, 0.5
        ),
        "memory": FunctionalOrgan(
            "memory", tuple(regime_members["episodic"]), "consolidation boundary", 0.25, 0.5
        ),
        "other_model": FunctionalOrgan(
            "other_model", tuple(regime_members["social"]), "non-absorption boundary", 0.25, 0.5
        ),
        "auditor": FunctionalOrgan(
            "auditor", tuple(regime_members["prospective"]), "anti-Lob boundary", 0.25, 0.5
        ),
    }
    return PolycosmicKernel(
        base=base,
        euclidean_base_control=euclidean_base_control,
        base_points=base_points,
        worldlets=worldlets,
        tendrils=tendrils,
        gerbe_cells=gerbe_cells,
        cages=root,
        organs=organs,
        clocks=clocks,
        identity=identity,
        governor=ContactHamiltonianGovernor(ViabilityBounds()),
        budget=BordonBudget(capacity=50.0, refill_rate=0.6, invariant_draw=0.4),
    )
