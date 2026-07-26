"""S4-G100: the Reversible Recognition Chamber.

An implementation, an experiment and a limited formalisation surface for one
bounded question:

    Can a controlled aperture plus ordered exploratory/verification operations
    reveal useful hidden structure beyond deterministic, static-ensemble and
    equal-entropy stochastic controls, while preserving round-trip and gauge
    stability under matched resource budgets?

The evidence floor is **H**.  Nothing in this package is a claim about
intelligence, consciousness, quantum advantage or asymptotic speedup, and the
governing negative results of Round S3 continue to apply: hypercomplex
coordinates are not automatically superior, a dimension-matched real
representation stays as a control, and no octonionic flat-sheaf construction may
be reintroduced.

The semantic handles are registered at S tier in :mod:`aionq.governance` and
denote ordinary operators:

    Emperor  -> :class:`~aionq.recognition.roles.Explorer`
    Empress  -> :class:`~aionq.recognition.roles.Verifier`
    Nest     -> :func:`~aionq.recognition.nest.nest_decision`
    Bordon   -> :class:`~aionq.recognition.budget.BordonBudget`
"""

from __future__ import annotations

from .aperture import (AdaptiveAperture, ApertureBounds, ApertureState,
                       FixedAperture, RandomAperture)
from .budget import BordonBudget, CollapseState, ThrottleEvent
from .chamber import MODES, ChamberRun, RecognitionChamber, RecognitionChamberState
from .loop_tomography import (LoopDefectReport, TransportPair, gauge_conjugate,
                              loop_defect)
from .manifest import ManifestError, load_manifest, validate_manifest
from .metrics import (ConditionResult, ResourceLedger, auroc, brier_score,
                      candidate_diversity, measure_resources)
from .nest import (EffectRegion, ComponentGate, Nest, independent_witness_status,
                   nest_decision)
from .perturbations import FIELD_SEEDS, make_fields, seed_int, structured_field
from .roles import CandidateMetrics, Explorer, Verifier, order_defect
from .types import (CandidateSection, DepositType, NestDeposit, TransportReport,
                    TypedRemainder)
from .worldlet import AlgebraRegime, Geometry, Polycosmos, Tendril, Worldlet

__all__ = [
    "AdaptiveAperture", "ApertureBounds", "ApertureState", "FixedAperture",
    "RandomAperture", "BordonBudget", "CollapseState", "ThrottleEvent",
    "MODES", "ChamberRun", "RecognitionChamber", "RecognitionChamberState",
    "LoopDefectReport", "TransportPair", "gauge_conjugate", "loop_defect",
    "ManifestError", "load_manifest", "validate_manifest",
    "ConditionResult", "ResourceLedger", "auroc", "brier_score",
    "candidate_diversity", "measure_resources",
    "EffectRegion", "ComponentGate", "Nest", "independent_witness_status",
    "nest_decision", "FIELD_SEEDS", "make_fields", "seed_int", "structured_field",
    "CandidateMetrics", "Explorer", "Verifier", "order_defect",
    "CandidateSection", "DepositType", "NestDeposit", "TransportReport",
    "TypedRemainder", "AlgebraRegime", "Geometry", "Polycosmos", "Tendril",
    "Worldlet",
]
