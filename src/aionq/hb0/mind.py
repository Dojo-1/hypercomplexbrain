"""Sixteen mind-quality operators, viability governance, and adiabatic dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from .core import (CarrierMismatch, MindQualityField, QUALITY_ORDER,
                   RemainderEnvelope, _as_vector, _finite, _safe_exp_score,
                   _unit_interval)
from .identity import RecognitionReport


@dataclass(frozen=True)
class OperatorContext:
    evidence_tag: str = EvidenceTag.SEMANTIC
    evidence_refs: tuple[str, ...] = ()
    operation: np.ndarray = field(default_factory=lambda: np.zeros(1))
    self_model: np.ndarray = field(default_factory=lambda: np.ones(1))
    identity_remainder: RemainderEnvelope | None = None
    recognition: RecognitionReport | None = None
    fast_delta_norm: float = 1.0
    slow_delta_norm: float = 0.0
    coverage_gain: float = 0.0
    information_gain: float = 0.0
    diversity_gain: float = 0.0
    compute_cost: float = 1.0
    coherence_loss: float = 0.0
    identity_risk: float = 0.0
    integration_completed: int = 0
    integration_required: int = 1
    resource_headroom: float = 1.0
    distinct_clocks: int = 1
    clock_desynchronisation: float = 0.0
    associator_defect: float = 0.0
    gluing_defect: float = 0.0
    reconstruction_fidelity: float = 0.0
    metaplastic_gain: float = 0.0
    rule_change_norm: float = 0.0
    corrections_retained: int = 0
    corrections_required: int = 1
    typed_remainders: int = 0
    total_remainders: int = 1

    def __post_init__(self) -> None:
        for name in (
            "fast_delta_norm",
            "slow_delta_norm",
            "coverage_gain",
            "information_gain",
            "diversity_gain",
            "compute_cost",
            "coherence_loss",
            "identity_risk",
            "resource_headroom",
            "clock_desynchronisation",
            "associator_defect",
            "gluing_defect",
            "reconstruction_fidelity",
            "metaplastic_gain",
            "rule_change_norm",
        ):
            value = _finite(getattr(self, name), f"operator_context.{name}")
            if value < 0.0:
                raise GovernanceError(f"operator_context.{name} must be non-negative")
            object.__setattr__(self, name, value)
        for name, minimum in (
            ("integration_completed", 0),
            ("integration_required", 1),
            ("distinct_clocks", 0),
            ("corrections_retained", 0),
            ("corrections_required", 1),
            ("typed_remainders", 0),
            ("total_remainders", 1),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GovernanceError(f"operator_context.{name} must be an integer")
            if int(value) < minimum:
                raise GovernanceError(
                    f"operator_context.{name} must be at least {minimum}"
                )
            object.__setattr__(self, name, int(value))
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise GovernanceError("operator_context evidence refs must be non-empty strings")


@dataclass(frozen=True)
class OperatorReport:
    field: MindQualityField
    risks: Mapping[str, float]
    obligations: Mapping[str, tuple[str, ...]]
    kill_conditions: Mapping[str, tuple[str, ...]]
    explanations: Mapping[str, str]


class MindOperatorBank:
    """Executable instrumentation for Q0..Q7 and their eight conjugates."""

    _EVIDENCE_STRENGTH = {
        EvidenceTag.PROVED: 1.0,
        EvidenceTag.AXIOMATIZED: 0.75,
        EvidenceTag.MEASURED: 0.70,
        EvidenceTag.HYPOTHESIS: 0.45,
        EvidenceTag.SEMANTIC: 0.25,
        EvidenceTag.RETIRED: 0.0,
    }

    @staticmethod
    def _bounded_ratio(numerator: float, denominator: float) -> float:
        numerator = max(0.0, _finite(numerator, "bounded_ratio.numerator"))
        denominator = max(1e-12, _finite(denominator, "bounded_ratio.denominator"))
        raw = numerator / denominator
        return float(raw / (1.0 + raw))

    def evaluate(self, ctx: OperatorContext) -> OperatorReport:
        if ctx.evidence_tag not in EvidenceTag.ALL:
            raise GovernanceError(f"unknown evidence tag {ctx.evidence_tag!r}")
        operation = _as_vector(ctx.operation, "operation")
        self_model = _as_vector(ctx.self_model, "self_model")
        if operation.shape != self_model.shape:
            raise CarrierMismatch("self-reflection requires a shared observable carrier")
        self_gap = float(np.linalg.norm(operation - self_model))
        recognition = ctx.recognition
        rec_quality = 0.0 if recognition is None else recognition.mutual_recognition / (1.0 + recognition.mutual_recognition)
        resonance = 0.0 if recognition is None else max(0.0, min(1.0, 0.5 * (recognition.resonance + 1.0)))
        remainder_ok = bool(
            ctx.identity_remainder
            and ctx.identity_remainder.channel == "identity"
            and ctx.identity_remainder.carrier
        )
        adiabatic = max(
            0.0,
            1.0 - max(0.0, ctx.slow_delta_norm) / max(1e-12, ctx.fast_delta_norm),
        )
        exploration = self._bounded_ratio(
            ctx.coverage_gain + ctx.information_gain + ctx.diversity_gain,
            ctx.compute_cost + ctx.coherence_loss + ctx.identity_risk,
        )
        return_ratio = min(
            1.0,
            max(0.0, ctx.integration_completed / max(1, ctx.integration_required)),
        )
        values = {
            "grounding": self._EVIDENCE_STRENGTH[ctx.evidence_tag]
            * (1.0 if ctx.evidence_refs else 0.5),
            "self_reflection": _safe_exp_score(self_gap),
            "godelian_identity": 1.0 if remainder_ok else 0.0,
            "other_recognition": rec_quality,
            "mutual_resonance": resonance,
            "adiabatic_patience": min(1.0, adiabatic),
            "ergocetic_exploration": exploration,
            "erdodetic_return": return_ratio,
            "embodiment": _unit_interval(ctx.resource_headroom, "resource_headroom"),
            "temporal_polyphony": min(1.0, ctx.distinct_clocks / 3.0)
            * _safe_exp_score(ctx.clock_desynchronisation),
            "contextual_composition": _safe_exp_score(ctx.associator_defect),
            "local_global_literacy": _safe_exp_score(ctx.gluing_defect),
            "holoportive_reconstruction": _unit_interval(
                ctx.reconstruction_fidelity, "reconstruction_fidelity"
            ),
            "metaplasticity": self._bounded_ratio(
                ctx.metaplastic_gain,
                1.0 + ctx.rule_change_norm,
            ),
            "judicial_correction": min(
                1.0,
                max(0.0, ctx.corrections_retained / max(1, ctx.corrections_required)),
            ),
            "remainder_stewardship": min(
                1.0,
                max(0.0, ctx.typed_remainders / max(1, ctx.total_remainders)),
            ),
        }
        obligations = {
            "grounding": ("attach source, artifact, or explicit S/H status",),
            "godelian_identity": ("retain [R]_id without promoting it to cohomology",),
            "other_recognition": ("measure viewpoint swap and preserved difference",),
            "ergocetic_exploration": ("return discoveries to controls and provenance",),
            "holoportive_reconstruction": ("report null-space information loss",),
            "remainder_stewardship": ("type every active remainder",),
        }
        kills = {
            "mutual_resonance": ("kill if high similarity is produced by absorption",),
            "adiabatic_patience": ("kill if slow identity changes as fast as inference",),
            "metaplasticity": ("kill if rule change adds no held-out gain",),
        }
        risks = {
            "self_model_gap": self_gap,
            "absorption": 0.0 if recognition is None else recognition.absorption_pressure,
            "coherence_loss": max(0.0, ctx.coherence_loss),
            "identity_risk": max(0.0, ctx.identity_risk),
        }
        explanations = {
            "grounding": "Q0 binds the section to an evidence envelope.",
            "self_reflection": "Q1 compares the operation with a bounded self-model.",
            "godelian_identity": "Q2 preserves a typed non-closure channel.",
            "other_recognition": "Q3 rewards useful modelling with preserved alterity.",
            "mutual_resonance": "Q4 requires return fidelity and non-absorption.",
            "adiabatic_patience": "Q5 separates fast adaptation from slow identity.",
            "ergocetic_exploration": "Q6 trades coverage for compute and coherence risk.",
            "erdodetic_return": "Q7 integrates, tests, glues, or retires discoveries.",
        }
        return OperatorReport(
            field=MindQualityField(values, obligations=obligations, kill_conditions=kills),
            risks=risks,
            obligations=obligations,
            kill_conditions=kills,
            explanations=explanations,
        )


@dataclass(frozen=True)
class ViabilityBounds:
    max_gluing_defect: float = 0.5
    max_identity_defect: float = 0.5
    max_absorption: float = 0.4
    max_compute: float = 100.0
    min_plurality: float = 0.1
    max_lob_trap: float = 0.2
    max_fragmentation: float = 0.5

    def __post_init__(self) -> None:
        for name in (
            "max_gluing_defect",
            "max_identity_defect",
            "max_absorption",
            "max_compute",
            "max_lob_trap",
            "max_fragmentation",
        ):
            value = _finite(getattr(self, name), f"viability_bounds.{name}")
            if value < 0.0:
                raise GovernanceError(f"viability_bounds.{name} must be non-negative")
            object.__setattr__(self, name, value)
        object.__setattr__(
            self,
            "min_plurality",
            _unit_interval(self.min_plurality, "viability_bounds.min_plurality"),
        )


@dataclass(frozen=True)
class ViabilityReport:
    gates: Mapping[str, bool]
    observed: Mapping[str, float]

    @property
    def feasible(self) -> bool:
        return all(self.gates.values())


@dataclass(frozen=True)
class HamiltonianEnvelope:
    """A vector resource/instability envelope, not one universal energy scalar."""

    compute: float
    coherence: float
    identity: float
    absorption: float
    exploration_credit: float = 0.0
    integration_credit: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "compute",
            "coherence",
            "identity",
            "absorption",
            "exploration_credit",
            "integration_credit",
        ):
            value = _finite(getattr(self, name), f"hamiltonian.{name}")
            if value < 0.0:
                raise GovernanceError(f"hamiltonian.{name} must be non-negative")
            object.__setattr__(self, name, value)

    def components(self) -> dict[str, float]:
        return {
            "compute": self.compute,
            "coherence": self.coherence,
            "identity": self.identity,
            "absorption": self.absorption,
            "exploration_credit": self.exploration_credit,
            "integration_credit": self.integration_credit,
        }


@dataclass(frozen=True)
class GovernanceDecision:
    accepted: bool
    viability: ViabilityReport
    component_budget: Mapping[str, bool]
    reasons: tuple[str, ...]


class ContactHamiltonianGovernor:
    """Constrained dissipative governance with explicit source terms.

    The controller uses componentwise bounds.  It does not assert literal energy
    conservation in a learning system and does not let one credit cancel an
    unrelated identity or absorption violation.
    """

    def __init__(self, bounds: ViabilityBounds) -> None:
        self.bounds = bounds

    def viability(self, observed: Mapping[str, float]) -> ViabilityReport:
        required = {
            "gluing_defect",
            "identity_defect",
            "absorption",
            "compute",
            "plurality",
            "lob_trap",
            "fragmentation",
        }
        missing = required - set(observed)
        if missing:
            raise GovernanceError(f"viability observation missing {sorted(missing)}")
        clean = {
            name: _finite(observed[name], f"viability.{name}")
            for name in required
        }
        gates = {
            "gluing": clean["gluing_defect"] <= self.bounds.max_gluing_defect,
            "identity": clean["identity_defect"] <= self.bounds.max_identity_defect,
            "non_absorption": clean["absorption"] <= self.bounds.max_absorption,
            "compute": clean["compute"] <= self.bounds.max_compute,
            "plurality": clean["plurality"] >= self.bounds.min_plurality,
            "anti_lob": clean["lob_trap"] <= self.bounds.max_lob_trap,
            "fragmentation": clean["fragmentation"] <= self.bounds.max_fragmentation,
        }
        return ViabilityReport(gates=gates, observed=clean)

    def decide(
        self,
        before: HamiltonianEnvelope,
        after: HamiltonianEnvelope,
        authorized: Mapping[str, float],
        observed: Mapping[str, float],
    ) -> GovernanceDecision:
        b = before.components()
        a = after.components()
        component_budget = {}
        for component in ("compute", "coherence", "identity", "absorption"):
            source = _finite(
                authorized.get(component, 0.0),
                f"authorized_source.{component}",
            )
            if source < 0.0:
                raise GovernanceError(
                    f"authorized_source.{component} must be non-negative"
                )
            component_budget[component] = a[component] <= b[component] + source + 1e-12
        viability = self.viability(observed)
        reasons = [name for name, ok in component_budget.items() if not ok]
        reasons.extend(name for name, ok in viability.gates.items() if not ok)
        return GovernanceDecision(
            accepted=not reasons,
            viability=viability,
            component_budget=component_budget,
            reasons=tuple(reasons),
        )

    @staticmethod
    def contact_flow(
        phase_state: np.ndarray,
        gradient: np.ndarray,
        dt: float,
        damping: float,
    ) -> np.ndarray:
        """One symplectic/contact-style step for an even-dimensional phase state."""
        z = _as_vector(phase_state, "phase_state")
        grad = _as_vector(gradient, "gradient")
        if z.shape != grad.shape or z.size % 2:
            raise GovernanceError("contact flow needs equal even-dimensional state and gradient")
        n = z.size // 2
        j = np.block(
            [[np.zeros((n, n)), np.eye(n)], [-np.eye(n), np.zeros((n, n))]]
        )
        return z + float(dt) * (j @ grad - float(damping) * z)


@dataclass
class AdiabaticState:
    fast: np.ndarray
    meso: np.ndarray
    slow: np.ndarray

    def __post_init__(self) -> None:
        self.fast = _as_vector(self.fast, "fast")
        self.meso = _as_vector(self.meso, "meso")
        self.slow = _as_vector(self.slow, "slow")
        if not (self.fast.shape == self.meso.shape == self.slow.shape):
            raise CarrierMismatch("adiabatic strata must share the declared comparison carrier")


@dataclass(frozen=True)
class AdiabaticController:
    fast_rate: float = 1.0
    meso_rate: float = 0.1
    slow_rate: float = 0.01
    meso_period: int = 4
    slow_period: int = 16

    def __post_init__(self) -> None:
        if not (0.0 < self.slow_rate < self.meso_rate < self.fast_rate):
            raise GovernanceError("adiabatic rates must satisfy slow < meso < fast")

    def step(self, state: AdiabaticState, delta: Any, tick: int) -> AdiabaticState:
        delta = _as_vector(delta, "adiabatic_delta")
        if delta.shape != state.fast.shape:
            raise CarrierMismatch("adiabatic delta has the wrong carrier")
        fast = state.fast + self.fast_rate * delta
        meso = state.meso.copy()
        slow = state.slow.copy()
        if tick % self.meso_period == 0:
            meso = meso + self.meso_rate * delta
        if tick % self.slow_period == 0:
            slow = slow + self.slow_rate * delta
        return AdiabaticState(fast, meso, slow)


@dataclass(frozen=True)
class MorphogenesisDecision:
    spawn: bool
    reasons: tuple[str, ...]
    topology_utility_components: Mapping[str, float]


@dataclass(frozen=True)
class MorphogenesisGate:
    persistence_threshold: float = 0.75
    heldout_gain_threshold: float = 0.02
    max_fragmentation_risk: float = 0.2

    def decide(
        self,
        remainder_persistence: float,
        heldout_gain_vs_width_control: float,
        compute_cost: float,
        fragmentation_risk: float,
    ) -> MorphogenesisDecision:
        persistence = _unit_interval(remainder_persistence, "remainder_persistence")
        fragmentation = _unit_interval(fragmentation_risk, "fragmentation_risk")
        reasons: list[str] = []
        if persistence < self.persistence_threshold:
            reasons.append("remainder_not_persistent")
        if heldout_gain_vs_width_control < self.heldout_gain_threshold:
            reasons.append("no_gain_over_width_control")
        if fragmentation > self.max_fragmentation_risk:
            reasons.append("fragmentation_risk")
        if compute_cost < 0:
            reasons.append("invalid_compute_cost")
        return MorphogenesisDecision(
            spawn=not reasons,
            reasons=tuple(reasons),
            topology_utility_components={
                "heldout_gain": float(heldout_gain_vs_width_control),
                "compute_cost": max(0.0, float(compute_cost)),
                "fragmentation_risk": fragmentation,
                "remainder_persistence": persistence,
            },
        )
