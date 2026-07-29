"""HB-0 coupled event loop and the 32-worldlet reference factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from ..recognition.budget import BordonBudget
from .core import (ChartFunctor, ClockSpec, CosmosCage, FunctionalOrgan, GerbeCell,
                   LocalGeometry, ProfunctorTendril, RemainderEnvelope, WorldletState,
                   TransportObservation, _unit_interval)
from .identity import IdentityEcology, IdentityRegime
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


@dataclass
class PolycosmicKernel:
    """The HB-0 coupled event loop over heterogeneous local worlds."""

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

    def __post_init__(self) -> None:
        if len(self.worldlets) < 4:
            raise GovernanceError("HB-0 requires at least four worldlets")
        geometries = {w.local_geometry for w in self.worldlets.values()}
        if len(geometries) < 2:
            raise GovernanceError("HB-0 collapsed to one local geometry")
        if len(self.clocks) < 3 or len({c.period for c in self.clocks.values()}) < 3:
            raise GovernanceError("HB-0 requires three genuinely distinct clocks")
        for tendril in self.tendrils.values():
            if tendril.source not in self.worldlets or tendril.target not in self.worldlets:
                raise GovernanceError(f"{tendril.id}: unknown endpoint")
        cage_worldlets = {wid for cage in self.cages.walk() for wid in cage.worldlet_ids}
        missing = set(self.worldlets) - cage_worldlets
        if missing:
            raise GovernanceError(f"worldlets outside the Russian-doll cover: {sorted(missing)}")

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
        self.tick += 1
        snapshot = self._snapshot()
        before_transport = self._transport_observations()
        before_glue = (
            float(np.mean([o.remainder.magnitude for o in before_transport if o.remainder.magnitude is not None]))
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

        for wid, delta in deltas.items():
            worldlet = self.worldlets[wid]
            active_rates = [self.clocks[c].rate for c in worldlet.clocks if self.clocks[c].due(self.tick)]
            if active_rates:
                worldlet.apply_delta(delta, rate=min(active_rates))

        observations = self._transport_observations()
        transport_remainders = tuple(o.remainder for o in observations)
        coherence_remainders = tuple(cell.remainder() for cell in self.gerbe_cells.values())
        glue_defect = (
            float(np.mean([r.magnitude for r in transport_remainders if r.magnitude is not None]))
            if transport_remainders
            else 0.0
        )
        gerbe_defect = (
            float(np.mean([r.magnitude for r in coherence_remainders if r.magnitude is not None]))
            if coherence_remainders
            else 0.0
        )
        identity_defect = 1.0 - self.identity.identity_fidelity()
        compute = float(sum(o.cost for o in observations) + len(deltas))
        fragmentation = self.identity.fragmentation_risk()
        plurality = self.identity.plurality()
        observed = {
            "gluing_defect": glue_defect + gerbe_defect,
            "identity_defect": identity_defect,
            "absorption": _unit_interval(absorption, "absorption"),
            "compute": compute,
            "plurality": plurality,
            "lob_trap": _unit_interval(lob_trap, "lob_trap"),
            "fragmentation": fragmentation,
        }
        after_envelope = HamiltonianEnvelope(
            compute=compute,
            coherence=glue_defect + gerbe_defect,
            identity=identity_defect,
            absorption=absorption,
        )
        sources = dict(authorized_sources or {})
        sources.setdefault("compute", compute)
        sources.setdefault("coherence", max(0.0, after_envelope.coherence - before_envelope.coherence))
        sources.setdefault("identity", max(0.0, after_envelope.identity - before_envelope.identity))
        sources.setdefault("absorption", 0.0)
        decision = self.governor.decide(before_envelope, after_envelope, sources, observed)
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


def _orthogonal(dim: int, rng: np.random.Generator) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(dim, dim)))
    return q * np.sign(np.diag(r))


def build_hb0(seed: int = 0, n_worldlets: int = 32, dim: int = 4) -> PolycosmicKernel:
    """Construct the minimal 32-worldlet HB-0 reference system.

    Four identity regimes receive eight local worlds each.  Their geometry is
    deliberately heterogeneous: local Poincare, Fisher/Riemannian, and Euclidean
    control charts coexist.  Every chart has a matched real-valued representation;
    no hypercomplex superiority is encoded in the factory.
    """
    if n_worldlets < 8 or n_worldlets % 4:
        raise GovernanceError("n_worldlets must be a multiple of four and at least eight")
    rng = np.random.default_rng(seed)
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
            regime_members[regime].append(wid)

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
    root = CosmosCage("C_root", "dynamic_cover")
    for regime in regime_names:
        root.add_child(
            CosmosCage(
                id=f"C_{regime}",
                geometry=worldlets[regime_members[regime][0]].local_geometry,
                worldlet_ids=tuple(regime_members[regime]),
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
