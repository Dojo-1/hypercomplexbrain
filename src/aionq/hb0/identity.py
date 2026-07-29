"""Polyholonomic identity and non-absorptive mutual recognition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import numpy as np

from ..governance import EvidenceTag, GovernanceError
from .core import (CarrierMismatch, ChartFunctor, GerbeCell, RemainderEnvelope,
                   _as_vector, _finite, _safe_exp_score, _unit_interval)


@dataclass(frozen=True)
class IdentityRegime:
    id: str
    section: np.ndarray
    holonomies: tuple[np.ndarray, ...]
    worldlets: tuple[str, ...]

    def __post_init__(self) -> None:
        section = _as_vector(self.section, f"{self.id}.section")
        holonomies = tuple(np.asarray(h, dtype=complex) for h in self.holonomies)
        if not holonomies:
            raise GovernanceError(f"{self.id}: at least one holonomy is required")
        dim = holonomies[0].shape[0]
        if any(h.shape != (dim, dim) for h in holonomies):
            raise GovernanceError(f"{self.id}: holonomies must have one square dimension")
        object.__setattr__(self, "section", section)
        object.__setattr__(self, "holonomies", holonomies)


@dataclass
class IdentityEcology:
    regimes: dict[str, IdentityRegime]
    comparisons: dict[tuple[str, str], ChartFunctor]
    higher_coherence: tuple[GerbeCell, ...] = ()

    def __post_init__(self) -> None:
        if len(self.regimes) < 2:
            raise GovernanceError("polyholonomic identity requires at least two regimes")
        for (source, target), functor in self.comparisons.items():
            if source not in self.regimes or target not in self.regimes:
                raise GovernanceError(f"identity comparison {source}->{target} has an unknown regime")
            if functor.backward is None:
                raise GovernanceError("identity comparisons require an explicit return map")

    def round_trip_defects(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for (source, target), functor in self.comparisons.items():
            section = self.regimes[source].section
            mapped = _as_vector(functor.forward(section), f"{source}->{target}")
            returned = _as_vector(functor.backward(mapped), f"{target}->{source}")  # type: ignore[misc]
            if returned.shape != section.shape:
                raise CarrierMismatch(f"identity comparison {source}->{target} changes return dimension")
            out[f"{source}->{target}->{source}"] = float(np.linalg.norm(returned - section))
        return out

    def identity_fidelity(self) -> float:
        defects = list(self.round_trip_defects().values())
        return 1.0 if not defects else float(np.mean([_safe_exp_score(x) for x in defects]))

    def plurality(self) -> float:
        """Effective rank in the declared common section dimension.

        The method refuses regimes with different section dimensions; callers must
        supply comparison functors and transport them to a common carrier first.
        """
        sections = [regime.section for regime in self.regimes.values()]
        dims = {section.size for section in sections}
        if len(dims) != 1:
            raise CarrierMismatch("identity plurality requires a declared common section carrier")
        matrix = np.stack(sections)
        gram = matrix @ matrix.T
        values = np.clip(np.linalg.eigvalsh((gram + gram.T) / 2.0), 0.0, None)
        total = float(values.sum())
        if total <= 1e-15:
            return 0.0
        probabilities = np.clip(values / total, 1e-18, None)
        effective_rank = float(np.exp(-np.sum(probabilities * np.log(probabilities))))
        return float((effective_rank - 1.0) / max(1.0, len(sections) - 1.0))

    def fragmentation_risk(self) -> float:
        n = len(self.regimes)
        possible = n * (n - 1)
        connectivity_gap = 1.0 - min(1.0, len(self.comparisons) / max(1, possible))
        defects = list(self.round_trip_defects().values())
        transport_risk = 0.0 if not defects else float(np.mean([1.0 - _safe_exp_score(x) for x in defects]))
        coherence = [cell.coherence_defect() for cell in self.higher_coherence]
        coherence_risk = 0.0 if not coherence else float(np.mean([1.0 - _safe_exp_score(x) for x in coherence]))
        return float(min(1.0, (connectivity_gap + transport_risk + coherence_risk) / 3.0))

    def godelian_remainder(self, operation: Any, self_model: Any) -> RemainderEnvelope:
        actual = _as_vector(operation, "operation")
        model = _as_vector(self_model, "self_model")
        if actual.shape != model.shape:
            raise CarrierMismatch("operation and self-model must share a declared carrier")
        gap = float(np.linalg.norm(actual - model))
        return RemainderEnvelope(
            name="[R]_id",
            channel="identity",
            carrier="identity_ecology/self_model_observable",
            evidence_tag=EvidenceTag.MEASURED,
            statement=(
                "bounded observed self-model gap; a zero value closes this instrument "
                "only, not identity description in general"
            ),
            instrument="l2_norm(operation - self_model)",
            magnitude=gap,
            provenance="IdentityEcology.godelian_remainder",
        )


@dataclass(frozen=True)
class RecognitionInput:
    gluing: float
    useful_update: float
    preserved_difference: float
    absorption_pressure: float
    projection_violence: float
    phase_delta: float
    geometric_distance: float
    gluing_defect: float
    return_fidelity: float
    telos_alignment: float

    def __post_init__(self) -> None:
        for name in (
            "gluing",
            "useful_update",
            "preserved_difference",
            "absorption_pressure",
            "projection_violence",
            "return_fidelity",
            "telos_alignment",
        ):
            object.__setattr__(self, name, _unit_interval(getattr(self, name), name))
        for name in ("phase_delta", "geometric_distance", "gluing_defect"):
            value = _finite(getattr(self, name), name)
            if name != "phase_delta" and value < 0:
                raise GovernanceError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class RecognitionReport:
    directional_ab: float
    directional_ba: float
    mutual_recognition: float
    resonance: float
    deck_defect: float
    preserved_alterity: float
    absorption_pressure: float


class MutualRecognitionCoupler:
    def __init__(self, absorption_weight: float = 1.0, violence_weight: float = 1.0) -> None:
        self.absorption_weight = float(absorption_weight)
        self.violence_weight = float(violence_weight)

    def _directional(self, x: RecognitionInput) -> float:
        positive = x.gluing + x.useful_update + x.preserved_difference
        negative = (
            self.absorption_weight * x.absorption_pressure
            + self.violence_weight * x.projection_violence
        )
        return max(0.0, float(positive - negative))

    def evaluate(
        self,
        ab: RecognitionInput,
        ba: RecognitionInput,
        deck_defect: float | None = None,
    ) -> RecognitionReport:
        rec_ab = self._directional(ab)
        rec_ba = self._directional(ba)
        if deck_defect is None:
            deck_defect = abs(rec_ab - rec_ba)
        deck_defect = max(0.0, _finite(deck_defect, "deck_defect"))
        mutual = float(math.sqrt(rec_ab * rec_ba) * math.exp(-deck_defect))
        phase = math.cos(ab.phase_delta - ba.phase_delta)
        distance = 0.5 * (ab.geometric_distance + ba.geometric_distance)
        glue = 0.5 * (ab.gluing_defect + ba.gluing_defect)
        return_fidelity = math.sqrt(ab.return_fidelity * ba.return_fidelity)
        telos = math.sqrt(ab.telos_alignment * ba.telos_alignment)
        absorption = max(ab.absorption_pressure, ba.absorption_pressure)
        resonance = float(
            phase
            * math.exp(-distance)
            * math.exp(-glue)
            * return_fidelity
            * telos
            * (1.0 - absorption)
        )
        return RecognitionReport(
            directional_ab=rec_ab,
            directional_ba=rec_ba,
            mutual_recognition=mutual,
            resonance=resonance,
            deck_defect=deck_defect,
            preserved_alterity=min(ab.preserved_difference, ba.preserved_difference),
            absorption_pressure=absorption,
        )
