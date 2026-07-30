"""Strict, non-executing validation for the HB-0 architecture manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..governance import EvidenceTag, GovernanceError, registry
from ..hyperbolic import (
    EuclideanBaseControl,
    PoincareBallBase,
    UNIVERSAL_POINCARE_BASE,
)
from .core import LocalGeometry, QUALITY_ORDER, REMAINDER_CHANNELS


@dataclass(frozen=True)
class HB0ManifestReport:
    ok: bool
    checks_run: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: Mapping[str, Any]


def validate_hb0_manifest(blob: Mapping[str, Any], strict: bool = True) -> HB0ManifestReport:
    """Validate the HB-0 architecture contract without executing manifest data.

    This validator is intentionally separate from the S4-G100 validator: the
    latter has four fixed geometry names tied to a specific sheaf experiment.
    HB-0 declares a universal Poincare atlas while preserving heterogeneous
    Poincare/Fisher/Riemannian/Euclidean fiber geometries and a mandatory
    Euclidean ablation.
    """
    errors: list[str] = []
    warnings: list[str] = []
    checks = 0

    def check(condition: bool, message: str, hard: bool = True) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            (errors if hard else warnings).append(message)

    required = (
        "name", "evidence_floor", "worldlets", "tendrils", "identity",
        "clocks", "dynamics", "evidence", "observables", "falsifiers",
        "qualities", "controls", "universal_base",
    )
    for key in required:
        check(key in blob, f"missing required field {key!r}")
    if errors:
        return HB0ManifestReport(False, checks, tuple(errors), tuple(warnings), {})

    floor = blob["evidence_floor"]
    check(floor in (EvidenceTag.SEMANTIC, EvidenceTag.HYPOTHESIS),
          "HB-0 evidence floor must be S or H")
    check(blob.get("consciousness_claim") is not True,
          "HB-0 may not claim consciousness")
    check(blob.get("agi_claim") is not True, "HB-0 may not claim AGI")

    worldlets = list(blob["worldlets"])
    declared_count = int(blob.get("population", {}).get("worldlet_count", len(worldlets)))
    check(declared_count >= 8 and declared_count % 4 == 0,
          "worldlet population must be a multiple of four and at least eight")
    ids = [w.get("id") for w in worldlets]
    check(len(ids) == len(set(ids)), "worldlet template ids must be unique")
    regimes = {w.get("identity_regime") for w in worldlets}
    for regime in ("somatic", "episodic", "social", "prospective"):
        check(regime in regimes, f"missing identity regime {regime!r}")
    geometries = {w.get("local_geometry") for w in worldlets}
    check(len(geometries) >= 2, "HB-0 requires more than one local geometry")
    check(LocalGeometry.EUCLIDEAN_CONTROL in geometries,
          "a Euclidean capacity-matched control chart is mandatory")
    raw_base = blob["universal_base"]
    check(isinstance(raw_base, Mapping), "universal_base must be a mapping")
    base = raw_base if isinstance(raw_base, Mapping) else {}
    check(blob.get("base_geometry") == LocalGeometry.POINCARE_BALL,
          "base_geometry must reinstate the Poincare ball")
    check(base.get("model") == LocalGeometry.POINCARE_BALL,
          "universal base model must be poincare_ball")
    check(base.get("scope") == "universal_atlas",
          "Poincare base scope must be universal_atlas")
    base_claim_id = base.get("claim_id")
    check(base_claim_id == "AXIOM-HB0-UNIVERSAL_POINCARE_BASE",
          "universal base must bind the HB0 Poincare axiom claim")
    check(base.get("evidence_tag") == EvidenceTag.AXIOMATIZED,
          "universal Poincare base must be visibly AXIOMATIZED")
    if base_claim_id == "AXIOM-HB0-UNIVERSAL_POINCARE_BASE":
        check(registry[base_claim_id].tag == EvidenceTag.AXIOMATIZED,
              "universal base claim must remain A-tagged in governance")
    envelope_status = base.get("evidence_envelope_status")
    check(envelope_status in ("pending", "verified"),
          "universal base must declare its evidence-envelope status")
    if envelope_status == "verified":
        check(bool(base.get("evidence_envelope")),
              "verified envelope status requires an evidence_envelope path")
        check(
            base.get("evidence_envelope")
            == "artifacts/hb0_universal_base/universal_base.envelope.json",
            "verified universal base must name the canonical evidence envelope",
        )
        if base_claim_id == "AXIOM-HB0-UNIVERSAL_POINCARE_BASE":
            check(
                len(registry.envelopes(base_claim_id)) == 1,
                "verified universal-base claim must carry exactly one loaded envelope",
            )
    elif envelope_status == "pending":
        warnings.append(
            "universal-base A claim is structurally checked but has no "
            "commit-bound evidence envelope yet"
        )
    check(base.get("supersedes") == "RET-R3-HYPERBOLIC_BASE",
          "universal base must preserve the historical retirement pointer")
    check(base.get("heterogeneous_local_fibers") is True,
          "universal base must preserve heterogeneous local fibers")
    check(base.get("euclidean_ablation_required") is True,
          "universal base must retain a matched Euclidean ablation")
    parsed_base = None
    try:
        parsed_base = PoincareBallBase.from_spec(dict(base))
    except (GovernanceError, TypeError, ValueError, OverflowError) as exc:
        check(False, f"invalid universal Poincare specification: {exc}")
    if parsed_base is not None:
        check(
            parsed_base.to_spec() == UNIVERSAL_POINCARE_BASE.to_spec(),
            "manifest universal base must match the repository-wide H4 specification",
        )
    raw_control = base.get("euclidean_control")
    check(isinstance(raw_control, Mapping),
          "universal base needs a typed Euclidean control specification")
    if isinstance(raw_control, Mapping):
        try:
            control = EuclideanBaseControl.from_spec(dict(raw_control))
        except (GovernanceError, TypeError, ValueError) as exc:
            check(False, f"invalid Euclidean base-control specification: {exc}")
        else:
            check(
                raw_control.get("matching")
                == "same tangent metric at the Poincare origin",
                "Euclidean control must declare origin-tangent matching",
            )
            if parsed_base is not None:
                check(
                    control.dimension == parsed_base.dimension,
                    "Euclidean control dimension must match the universal base",
                )
                check(
                    abs(control.metric_scale - 2.0 * parsed_base.radius)
                    <= parsed_base.tolerance,
                    "Euclidean control scale must match the Poincare origin metric",
                )
    for worldlet in worldlets:
        wid = worldlet.get("id")
        check(worldlet.get("local_geometry") in LocalGeometry.ALL,
              f"worldlet {wid}: unknown local geometry")
        check(bool(worldlet.get("carrier")), f"worldlet {wid}: no carrier")
        check(bool(worldlet.get("clocks")), f"worldlet {wid}: no clock")
        check("remainder_channels" in worldlet,
              f"worldlet {wid}: remainder channels not declared")

    clocks = list(blob["clocks"])
    check(len(clocks) >= 3, "at least three clocks are required")
    periods = [c.get("period") for c in clocks]
    check(len(set(periods)) == len(periods), "clock periods must be distinct")
    clock_ids = {c.get("id") for c in clocks}
    for worldlet in worldlets:
        for clock in worldlet.get("clocks", ()):
            check(clock in clock_ids,
                  f"worldlet {worldlet.get('id')}: undeclared clock {clock!r}")

    tendrils = list(blob["tendrils"])
    check(bool(tendrils), "at least one tendril template is required")
    for tendril in tendrils:
        tid = tendril.get("id")
        check(bool(tendril.get("forward_transport")),
              f"tendril {tid}: no forward transport")
        check(bool(tendril.get("return_transport")) or
              bool(tendril.get("return_absent_reason")),
              f"tendril {tid}: no return path or loss reason")
        for field_name in ("preserved", "transformed", "lost"):
            check(field_name in tendril, f"tendril {tid}: {field_name} not declared")
        remainder = tendril.get("typed_remainder", {})
        check(str(remainder.get("name", "")).startswith("[R]_") ,
              f"tendril {tid}: untyped remainder name")
        check(remainder.get("channel") in REMAINDER_CHANNELS,
              f"tendril {tid}: unknown remainder channel")
        check(bool(remainder.get("carrier")),
              f"tendril {tid}: remainder carrier missing")

    identity = blob["identity"]
    local_holonomies = identity.get("local_holonomies", ())
    check(len(local_holonomies) >= 2, "polyholonomic identity needs multiple regimes")
    check(bool(identity.get("comparison_functors")),
          "identity comparison functors are required")
    check(bool(identity.get("higher_coherence")),
          "identity higher-coherence witnesses are required")
    check(identity.get("remainder", {}).get("name") == "[R]_id",
          "identity must preserve a typed [R]_id")

    dynamics = blob["dynamics"]
    for key in ("breathing", "weaving", "deweaving", "morphogenesis",
                "governance", "hyperedges", "gerbe_cells"):
        check(bool(dynamics.get(key)), f"dynamics missing {key!r}")
    breathing = dynamics.get("breathing", {})
    check(float(breathing.get("invariant_draw", 1.0)) <=
          float(breathing.get("refill_rate", 0.0)) + 1e-12,
          "invariant draw exceeds the Bordon refill ceiling")

    qualities = tuple(blob["qualities"])
    check(set(qualities) == set(QUALITY_ORDER),
          "the manifest must declare exactly the sixteen quality coordinates")
    controls = set(blob["controls"])
    required_controls = {
        "euclidean_capacity_matched",
        "hyperbolic_scalar_fibers",
        "dynamic_hypergraph_real",
        "hypercomplex_fixed_graph",
        "single_clock_polyholonomy",
        "full_hb0",
    }
    check(required_controls <= controls,
          f"missing matched controls {sorted(required_controls - controls)}")

    quantum = blob.get("quantum_transport", {})
    check(quantum.get("simulator_only") is True,
          "quantum transport must be marked simulator-only")
    check(quantum.get("advantage_claim") is False,
          "HB-0 may not promote a quantum advantage claim")
    check(bool(quantum.get("classical_known_state_control")),
          "quantum transport needs a matched classical known-state control")

    evidence = list(blob["evidence"])
    for entry in evidence:
        check(entry.get("tag") in EvidenceTag.ALL,
              f"evidence entry {entry.get('id')}: bad tag")
        if entry.get("tag") == EvidenceTag.HYPOTHESIS:
            check(bool(entry.get("kill_condition")),
                  f"H entry {entry.get('id')}: no kill condition")
    check(any(entry.get("id") == "SEM-HB0-NON_SENTIENCE" for entry in evidence),
          "the non-sentience boundary must be explicit")

    falsifiers = list(blob["falsifiers"])
    check(len(falsifiers) >= 5, "at least five independent falsifier classes are required")
    for falsifier in falsifiers:
        check(bool(falsifier.get("kill_if")),
              f"falsifier {falsifier.get('id')}: no kill_if")
    check(bool(blob["observables"]), "no observables declared")

    return HB0ManifestReport(
        ok=(not errors if strict else True),
        checks_run=checks,
        errors=tuple(errors),
        warnings=tuple(warnings),
        summary={
            "declared_worldlets": declared_count,
            "templates": len(worldlets),
            "geometries": tuple(sorted(g for g in geometries if g)),
            "clocks": len(clocks),
            "tendril_templates": len(tendrils),
            "falsifiers": len(falsifiers),
        },
    )
