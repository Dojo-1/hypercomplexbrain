"""HB-0 coupled event loop and the 32-worldlet reference factory."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Mapping
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from ..recognition.budget import BordonBudget
from .core import (CarrierMismatch, ChartFunctor, ClockSpec, CosmosCage,
                   FunctionalOrgan, GerbeCell, LocalGeometry,
                   ProfunctorTendril, RemainderEnvelope, WorldletState,
                   TransportObservation, _finite, _safe_exp_score,
                   _unit_interval)
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


TendrilMode = Literal[
    "active",
    "disabled_control",
    "shuffled_target_control",
]


@dataclass(frozen=True)
class TendrilTransactionReport:
    """One staged real-carrier transport and its vector-valued landing trace."""

    tick: int
    tendril_id: str
    mode: TendrilMode
    source: str
    declared_target: str
    selected_target: str
    accepted: bool
    committed: bool
    source_coordinates: tuple[float, ...]
    transported_output: tuple[float, ...]
    round_trip: tuple[float, ...]
    transport_remainder: RemainderEnvelope
    return_fidelity: float
    target_before: tuple[float, ...]
    staged_target: tuple[float, ...]
    target_after: tuple[float, ...]
    proposed_delta: tuple[float, ...]
    committed_delta: tuple[float, ...]
    proposed_delta_norm: float
    committed_delta_norm: float
    alignment_before: float
    alignment_if_committed: float
    alignment_after: float
    coupling: float
    permeability: float
    cost: float
    viability: ViabilityReport
    governance_reasons: tuple[str, ...]
    evidence_tag: str = EvidenceTag.MEASURED


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
    tendril_ledger: list[TendrilTransactionReport] = field(default_factory=list)

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

    @staticmethod
    def _strict_real_vector(value: object, name: str) -> np.ndarray:
        """Validate a real carrier without silently projecting away phase."""
        raw = np.asarray(value)
        if raw.ndim != 1:
            raise GovernanceError(f"{name} must be a one-dimensional carrier")
        if np.iscomplexobj(raw):
            imaginary = np.asarray(raw.imag, dtype=float)
            if np.any(imaginary != 0.0):
                raise CarrierMismatch(
                    f"{name} is complex-valued; HB0-T1 supports real carriers only"
                )
            raw = raw.real
        out = np.asarray(raw, dtype=float)
        if not np.all(np.isfinite(out)):
            raise GovernanceError(f"{name} contains a non-finite coordinate")
        return out.copy()

    @staticmethod
    def _retract_target(target: WorldletState, proposal: np.ndarray) -> np.ndarray:
        """Return a staged coordinate in the target's declared local chart."""
        out = PolycosmicKernel._strict_real_vector(
            proposal, f"{target.id}.staged_target"
        )
        if out.shape != target.coordinates.shape:
            raise CarrierMismatch(
                f"{target.id}: staged shape {out.shape} != "
                f"{target.coordinates.shape}"
            )
        if target.local_geometry == LocalGeometry.POINCARE_BALL:
            norm = float(np.linalg.norm(out))
            if norm >= 1.0:
                out = out * ((1.0 - 1e-9) / norm)
        return out

    def _budget_snapshot(self) -> tuple[float, float, list, str]:
        return (
            float(self.budget.speculative_draw),
            float(self.budget.level),
            list(self.budget.interventions),
            self.budget.state,
        )

    def _restore_budget(self, snapshot: tuple[float, float, list, str]) -> None:
        speculative_draw, level, interventions, state = snapshot
        self.budget.speculative_draw = speculative_draw
        self.budget.level = level
        self.budget.interventions = list(interventions)
        self.budget.state = state

    def transact_tendril(
        self,
        tendril_id: str,
        *,
        coupling: float,
        authorized_sources: Mapping[str, float],
        mode: TendrilMode = "active",
        control_target: str | None = None,
    ) -> TendrilTransactionReport:
        """Stage, govern, and optionally commit exactly one tendril landing.

        HB0-T1 deliberately supports only real-valued finite carriers.  The
        transported output and both delta vectors remain in the report; a norm
        is supplementary telemetry rather than a scalar replacement.
        """
        modes = {
            "active",
            "disabled_control",
            "shuffled_target_control",
        }
        if mode not in modes:
            raise GovernanceError(f"unknown tendril transaction mode {mode!r}")
        coupling = _unit_interval(coupling, "coupling")
        if tendril_id not in self.tendrils:
            raise GovernanceError(f"unknown tendril {tendril_id!r}")
        tendril = self.tendrils[tendril_id]
        if not tendril.woven and mode != "disabled_control":
            raise GovernanceError(f"{tendril_id}: a dewoven tendril cannot be active")

        source = self.worldlets[tendril.source]
        declared_target = self.worldlets[tendril.target]
        if tendril.chart.source_carrier != source.carrier:
            raise CarrierMismatch(
                f"{tendril_id}: chart source {tendril.chart.source_carrier!r} "
                f"!= worldlet carrier {source.carrier!r}"
            )
        if tendril.chart.target_carrier != declared_target.carrier:
            raise CarrierMismatch(
                f"{tendril_id}: chart target {tendril.chart.target_carrier!r} "
                f"!= worldlet carrier {declared_target.carrier!r}"
            )

        if mode == "shuffled_target_control":
            if control_target is None or control_target not in self.worldlets:
                raise GovernanceError(
                    "shuffled_target_control needs a known control_target"
                )
            if control_target == declared_target.id:
                raise GovernanceError(
                    "shuffled_target_control must differ from the declared target"
                )
            selected_target = self.worldlets[control_target]
            matched = (
                selected_target.carrier == declared_target.carrier
                and selected_target.local_geometry == declared_target.local_geometry
                and selected_target.dimension == declared_target.dimension
                and abs(
                    selected_target.permeability - declared_target.permeability
                )
                <= 1e-12
            )
            if not matched:
                raise CarrierMismatch(
                    "shuffled control target must match carrier, geometry, "
                    "dimension, and permeability"
                )
        else:
            if control_target is not None:
                raise GovernanceError(
                    "control_target is valid only for shuffled_target_control"
                )
            selected_target = declared_target

        sources: dict[str, float] = {}
        for component, value in authorized_sources.items():
            value = _finite(value, f"authorized_sources[{component!r}]")
            if value < 0.0:
                raise GovernanceError("authorized source terms must be non-negative")
            sources[str(component)] = value

        world_snapshot = self._snapshot()
        identity_snapshot = {
            regime_id: regime.section.copy()
            for regime_id, regime in self.identity.regimes.items()
        }
        budget_snapshot = self._budget_snapshot()
        tick_snapshot = self.tick
        ledger_size = len(self.tendril_ledger)

        try:
            source_coordinates = self._strict_real_vector(
                source.coordinates, f"{tendril_id}.source"
            )
            transported = self._strict_real_vector(
                tendril.chart.forward(source_coordinates.copy()),
                f"{tendril_id}.output",
            )
            if tendril.chart.backward is None:
                raise GovernanceError(
                    f"{tendril_id}: HB0-T1 needs an explicit return map"
                )
            round_trip = self._strict_real_vector(
                tendril.chart.backward(transported.copy()),
                f"{tendril_id}.round_trip",
            )
            if round_trip.shape != source_coordinates.shape:
                raise CarrierMismatch(
                    f"{tendril_id}: round-trip shape {round_trip.shape} != "
                    f"source shape {source_coordinates.shape}"
                )
            round_trip_defect = float(
                np.linalg.norm(round_trip - source_coordinates)
            )
            transport_remainder = RemainderEnvelope(
                name="[R]_transport",
                channel="transport",
                carrier=tendril.chart.source_carrier,
                evidence_tag=EvidenceTag.MEASURED,
                statement=(
                    "round-trip defect of the staged active-tendril "
                    "correspondence"
                ),
                instrument="l2_norm(backward(forward(x)) - x)",
                magnitude=round_trip_defect,
                provenance=tendril_id,
            )
            if transported.shape != selected_target.coordinates.shape:
                raise CarrierMismatch(
                    f"{tendril_id}: output shape {transported.shape} != "
                    f"selected target shape {selected_target.coordinates.shape}"
                )
            target_before = self._strict_real_vector(
                selected_target.coordinates, f"{selected_target.id}.target_before"
            )
            proposal = target_before + (
                coupling
                * selected_target.permeability
                * (transported - target_before)
            )
            staged_target = self._retract_target(selected_target, proposal)
            proposed_delta = staged_target - target_before
            alignment_before = float(np.linalg.norm(transported - target_before))
            alignment_if_committed = float(
                np.linalg.norm(transported - staged_target)
            )
            cost = float(tendril.cost)

            will_move = mode != "disabled_control"
            staged_alignment = (
                alignment_if_committed if will_move else alignment_before
            )
            before_coherence = alignment_before + round_trip_defect
            after_coherence = staged_alignment + round_trip_defect
            identity_defect = 1.0 - self.identity.identity_fidelity()
            before_envelope = HamiltonianEnvelope(
                compute=0.0,
                coherence=before_coherence,
                identity=identity_defect,
                absorption=0.0,
            )
            after_envelope = HamiltonianEnvelope(
                compute=cost,
                coherence=after_coherence,
                identity=identity_defect,
                absorption=0.0,
            )
            observed = {
                "gluing_defect": after_coherence,
                "identity_defect": identity_defect,
                "absorption": 0.0,
                "compute": cost,
                "plurality": self.identity.plurality(),
                "lob_trap": 0.0,
                "fragmentation": self.identity.fragmentation_risk(),
            }
            decision = self.governor.decide(
                before_envelope,
                after_envelope,
                sources,
                observed,
            )
            committed = bool(decision.accepted and will_move)
            committed_delta = (
                proposed_delta.copy()
                if committed
                else np.zeros_like(proposed_delta)
            )
            target_after = (
                staged_target.copy() if committed else target_before.copy()
            )
            alignment_after = (
                alignment_if_committed if committed else alignment_before
            )
            report = TendrilTransactionReport(
                tick=self.tick + 1,
                tendril_id=tendril_id,
                mode=mode,
                source=source.id,
                declared_target=declared_target.id,
                selected_target=selected_target.id,
                accepted=decision.accepted,
                committed=committed,
                source_coordinates=tuple(float(x) for x in source_coordinates),
                transported_output=tuple(float(x) for x in transported),
                round_trip=tuple(float(x) for x in round_trip),
                transport_remainder=transport_remainder,
                return_fidelity=_safe_exp_score(round_trip_defect),
                target_before=tuple(float(x) for x in target_before),
                staged_target=tuple(float(x) for x in staged_target),
                target_after=tuple(float(x) for x in target_after),
                proposed_delta=tuple(float(x) for x in proposed_delta),
                committed_delta=tuple(float(x) for x in committed_delta),
                proposed_delta_norm=float(np.linalg.norm(proposed_delta)),
                committed_delta_norm=float(np.linalg.norm(committed_delta)),
                alignment_before=alignment_before,
                alignment_if_committed=alignment_if_committed,
                alignment_after=alignment_after,
                coupling=coupling,
                permeability=float(selected_target.permeability),
                cost=cost,
                viability=decision.viability,
                governance_reasons=decision.reasons,
            )

            if committed:
                selected_target.coordinates = target_after.copy()
            self.tick += 1
            self.budget.charge(cost * 0.01)
            self.budget.tick(self.tick)
            self.tendril_ledger.append(report)
            return report
        except Exception:
            self._restore(world_snapshot)
            for regime_id, section in identity_snapshot.items():
                self.identity.regimes[regime_id] = replace(
                    self.identity.regimes[regime_id],
                    section=section.copy(),
                )
            self._restore_budget(budget_snapshot)
            self.tick = tick_snapshot
            del self.tendril_ledger[ledger_size:]
            raise

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
