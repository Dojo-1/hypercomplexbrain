"""Strict validation of an architecture manifest.

No ``jsonschema`` is available in this environment, so rather than skip
validation the checks are written here and tested directly.  That is the better
outcome anyway: several of these rules are repository-specific and no generic
schema language would express them.

Loading is deliberately narrow.  :func:`load_manifest` uses ``json`` only, refuses
paths outside the repository root, and refuses files above a size bound.  There
is no YAML, no pickle and no ``eval``: a manifest is data, and an architecture
description that can execute is a vulnerability rather than a feature.

Strict mode enforces, beyond well-formedness:

  * at least four worldlet roles, covering evidence, memory, exploration, audit;
  * at least two genuinely distinct local geometries;
  * at least three clocks at different rates;
  * forward AND return transport on every tendril, or a stated reason;
  * a typed remainder on every tendril, drawn from the governance kinds;
  * preserved / transformed / lost declared on every tendril;
  * at least one hyperedge joining three or more worldlets;
  * breathing with ``invariant_draw <= refill_rate``;
  * weaving and deweaving both present;
  * matched controls and explicit falsifiers;
  * **no octonionic or sedenion regime in a flat-sheaf role** -- the standing
    consequence of ``RET-S3-OCTONIONIC_SHEAF``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..governance import EvidenceTag, RemainderKind
from .worldlet import AlgebraRegime, Geometry

__all__ = ["ManifestError", "load_manifest", "validate_manifest",
           "ValidationReport", "REQUIRED_TOP_LEVEL", "REQUIRED_ROLES"]

MAX_MANIFEST_BYTES = 1_000_000

REQUIRED_TOP_LEVEL = ("name", "evidence_floor", "worldlets", "tendrils",
                      "identity", "clocks", "dynamics", "evidence", "observables",
                      "falsifiers")

REQUIRED_ROLES = ("local_evidence_carrier", "candidate_memory",
                  "exploratory_counterfactual", "auditor_verification")


class ManifestError(ValueError):
    """Raised when a manifest fails strict validation."""


@dataclass
class ValidationReport:
    ok: bool
    checks_run: int
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - display only
        head = (f"{'PASS' if self.ok else 'FAIL'}  {self.checks_run} checks, "
                f"{len(self.errors)} errors, {len(self.warnings)} warnings")
        return "\n".join([head] + [f"  ERROR   {e}" for e in self.errors]
                         + [f"  warning {w}" for w in self.warnings])


def load_manifest(path, root=None) -> dict:
    """Read a manifest as data.  JSON only, inside the repo, size-bounded."""
    root = Path(root or Path(__file__).resolve().parents[3]).resolve()
    p = Path(path).resolve()
    try:
        p.relative_to(root)
    except ValueError as exc:
        raise ManifestError(f"refusing to read {p}: outside the repository root "
                            f"{root}") from exc
    if p.suffix != ".json":
        raise ManifestError(f"refusing to read {p}: manifests are JSON only, so "
                            "that loading cannot execute anything")
    if not p.is_file():
        raise ManifestError(f"no such manifest: {p}")
    size = p.stat().st_size
    if size > MAX_MANIFEST_BYTES:
        raise ManifestError(f"refusing to read {p}: {size} bytes exceeds the "
                            f"{MAX_MANIFEST_BYTES} byte bound")
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_manifest(blob: dict, strict: bool = True) -> ValidationReport:
    errors: list = []
    warnings: list = []
    checks = 0

    def check(cond, msg, hard=True):
        nonlocal checks
        checks += 1
        if not cond:
            (errors if hard else warnings).append(msg)

    # ---- top level ----------------------------------------------------------
    for key in REQUIRED_TOP_LEVEL:
        check(key in blob, f"missing required top-level field {key!r}")
    if errors:
        return ValidationReport(False, checks, errors, warnings)

    check(blob["evidence_floor"] in EvidenceTag.ALL,
          f"evidence_floor {blob['evidence_floor']!r} is not an evidence tag")
    check(blob["evidence_floor"] in (EvidenceTag.HYPOTHESIS, EvidenceTag.SEMANTIC),
          "S4-G100 must start at H or S; a higher floor would presume its own result")

    # ---- worldlets ----------------------------------------------------------
    ws = blob["worldlets"]
    check(len(ws) >= 4, f"at least four worldlet roles required, found {len(ws)}")
    ids = [w.get("id") for w in ws]
    check(len(set(ids)) == len(ids), f"duplicate worldlet ids in {ids}")
    roles = {w.get("role") for w in ws}
    for r in REQUIRED_ROLES:
        check(r in roles, f"no worldlet carries the required role {r!r}")

    geoms = {w.get("local_geometry") for w in ws}
    check(len(geoms) >= 2,
          f"at least two distinct local geometries required, found {sorted(geoms)}")
    for w in ws:
        check(w.get("local_geometry") in Geometry.ALL,
              f"worldlet {w.get('id')}: unknown geometry {w.get('local_geometry')!r}")
        check(w.get("algebra_regime") in AlgebraRegime.ALL,
              f"worldlet {w.get('id')}: unknown algebra regime "
              f"{w.get('algebra_regime')!r}")
        check(bool(w.get("clocks")), f"worldlet {w.get('id')}: no clock declared")
        # RET-S3-OCTONIONIC_SHEAF is a governing constraint, not a preference.
        if w.get("algebra_regime") in AlgebraRegime.NON_FLAT:
            check(not w.get("flat_sheaf_role", False),
                  f"worldlet {w.get('id')}: algebra regime "
                  f"{w.get('algebra_regime')!r} in a flat-sheaf role; "
                  "RET-S3-OCTONIONIC_SHEAF established that a vertex gauge induces "
                  "no flat connection above dimension 4")

    # ---- clocks -------------------------------------------------------------
    clocks = blob["clocks"]
    check(len(clocks) >= 3, f"at least three clocks required, found {len(clocks)}")
    periods = [c.get("period") for c in clocks]
    check(len(set(periods)) == len(periods),
          f"clocks must run at different rates; periods {periods}")
    declared = {c.get("name") for c in clocks}
    for w in ws:
        for c in w.get("clocks", ()):
            check(c in declared, f"worldlet {w.get('id')} uses undeclared clock {c!r}")

    # ---- tendrils -----------------------------------------------------------
    ts = blob["tendrils"]
    check(len(ts) >= 3, f"at least three tendrils required, found {len(ts)}")
    for t in ts:
        tid = t.get("id")
        for end in ("source", "target"):
            check(t.get(end) in ids, f"tendril {tid}: {end} {t.get(end)!r} is not a "
                                     "declared worldlet")
        check(bool(t.get("forward_transport")),
              f"tendril {tid}: no forward transport")
        check(bool(t.get("return_transport")) or bool(t.get("return_absent_reason")),
              f"tendril {tid}: no return transport and no reason given")
        for fieldname in ("preserved_fields", "transformed_fields", "lost_fields"):
            check(fieldname in t,
                  f"tendril {tid}: {fieldname} not declared")
        rem = t.get("typed_remainder") or {}
        check(rem.get("remainder_type") in RemainderKind.ALL,
              f"tendril {tid}: remainder type {rem.get('remainder_type')!r} is not "
              f"one of {RemainderKind.ALL}")
        check(bool(rem.get("carrier")) and bool(rem.get("metric_or_comparison")),
              f"tendril {tid}: remainder must name its carrier and comparison")
        if t.get("claims_exact_inverse"):
            check(not t.get("lost_fields"),
                  f"tendril {tid}: claims an exact inverse but declares lost fields")

    # ---- higher-order relations --------------------------------------------
    hyper = blob["dynamics"].get("hyperedges", [])
    check(len(hyper) >= 1, "at least one hyperedge is required: some constraint must "
                           "involve three or more worldlets jointly")
    for h in hyper:
        check(len(h.get("members", ())) >= 3,
              f"hyperedge {h.get('id')!r} joins fewer than three worldlets")
        for m in h.get("members", ()):
            check(m in ids, f"hyperedge {h.get('id')!r}: unknown member {m!r}")

    # ---- breathing, weaving -------------------------------------------------
    dyn = blob["dynamics"]
    br = dyn.get("breathing", {})
    check(bool(br), "no breathing dynamics declared")
    if br:
        check(float(br.get("invariant_draw", 1.0)) <= float(br.get("refill_rate", 0.0))
              + 1e-12,
              f"invariant_draw {br.get('invariant_draw')} exceeds refill_rate "
              f"{br.get('refill_rate')}: the drone ceiling theorem says the "
              "invariant channel cannot then survive indefinitely")
    check(bool(dyn.get("weaving")), "no weaving rule declared")
    check(bool(dyn.get("deweaving")), "no deweaving rule declared")

    # ---- governance, controls, falsifiers ------------------------------------
    check(bool(blob["evidence"]), "no evidence governance entries")
    for e in blob["evidence"]:
        check(e.get("tag") in EvidenceTag.ALL,
              f"evidence entry {e.get('id')!r}: bad tag {e.get('tag')!r}")
        if e.get("tag") == EvidenceTag.HYPOTHESIS:
            check(bool(e.get("kill_condition")),
                  f"H-tagged entry {e.get('id')!r} has no kill condition")
        if e.get("tag") == EvidenceTag.AXIOMATIZED:
            check(bool(e.get("surrogate")),
                  f"A-tagged entry {e.get('id')!r} names no surrogate")

    check(bool(blob.get("controls")) or bool(dyn.get("controls")),
          "no matched controls declared")
    check(len(blob["falsifiers"]) >= 3,
          f"at least three falsifiers required, found {len(blob['falsifiers'])}")
    for f in blob["falsifiers"]:
        check(bool(f.get("kill_if")), f"falsifier {f.get('id')!r} states no kill_if")

    check(bool(blob["observables"]), "no observables declared")
    check(bool(blob["identity"]), "no identity block declared")

    ok = not errors if strict else True
    return ValidationReport(
        ok=ok, checks_run=checks, errors=errors, warnings=warnings,
        summary={"worldlets": len(ws), "tendrils": len(ts), "clocks": len(clocks),
                 "geometries": sorted(g for g in geoms if g),
                 "hyperedges": len(hyper), "falsifiers": len(blob["falsifiers"])})
