"""The evidence-gated deposit predicate.

The gate is a **preregistered region in a partial order**, never a weighted
score.  This repository retired a weighted scalar promotion gate once already
(``RET-R3-SCALAR_PROMOTION``) and the failure mode was that a single number let a
large gain on a cheap axis pay for a loss on an expensive one.  So a candidate
crosses only if it meets *every* component gate: dominance, not aggregation.

Two rules are enforced in code rather than in review.

**No post-hoc weighting.**  :class:`EffectRegion` is constructed from the
preregistration file and is frozen.  :func:`nest_decision` takes the region as an
argument and has no other tuning surface.

**No self-promotion.**  A claim is authorised only by witnesses *outside* the
dependency closure of the nodes that generated it.  If the explorer, verifier,
formalizer and auditor share code, assumptions, data or authoring model, they are
one node for this purpose -- and in S4-G100 they do share all four, which is why
:func:`independent_witness_status` reports ``correlated`` and every S4 deposit is
capped accordingly.  That cap is the honest reading, not a formality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..governance import EvidenceTag, GovernanceError
from .types import DepositType, NestDeposit

__all__ = ["EffectRegion", "ComponentGate", "nest_decision", "DecisionReport",
           "dependency_closure", "independent_witness_status", "Nest"]


@dataclass(frozen=True)
class ComponentGate:
    """One axis of the effect region: a named threshold with a direction."""

    name: str
    threshold: float
    direction: str = "at_least"     # "at_least" | "at_most"
    unit: str = ""

    def passes(self, value: float) -> bool:
        if value is None:
            return False
        if self.direction == "at_least":
            return float(value) >= self.threshold
        if self.direction == "at_most":
            return float(value) <= self.threshold
        raise GovernanceError(f"unknown gate direction {self.direction!r}")

    def __str__(self) -> str:  # pragma: no cover - display only
        arrow = ">=" if self.direction == "at_least" else "<="
        return f"{self.name} {arrow} {self.threshold}{(' ' + self.unit) if self.unit else ''}"


@dataclass(frozen=True)
class EffectRegion:
    """A preregistered region.  Frozen, and never re-weighted after results."""

    name: str
    gates: tuple
    source: str = ""

    def evaluate(self, observed: dict) -> dict:
        return {g.name: bool(g.passes(observed.get(g.name))) for g in self.gates}

    def dominated(self, observed: dict) -> bool:
        """All components meet their gate.  No trade-offs, by construction."""
        return all(self.evaluate(observed).values())

    @classmethod
    def from_preregistration(cls, blob: dict, key: str = "primary_effect_region"):
        gates = tuple(ComponentGate(g["name"], float(g["threshold"]),
                                    g.get("direction", "at_least"), g.get("unit", ""))
                      for g in blob[key]["gates"])
        return cls(name=blob[key].get("name", key), gates=gates,
                   source=blob.get("preregistered_utc", "unknown"))


# --------------------------------------------------------------------------
# Independence
# --------------------------------------------------------------------------

def dependency_closure(nodes, edges) -> frozenset:
    """Everything reachable from ``nodes`` along ``edges`` (a dict node -> set)."""
    seen, stack = set(), list(nodes)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(edges.get(n, ()))
    return frozenset(seen)


def independent_witness_status(roles: dict) -> dict:
    """Are the witnesses independent?  Answered on four axes, not asserted.

    ``roles`` maps role name -> dict with ``code``, ``assumptions``, ``data`` and
    ``author`` identifiers.  Two roles are independent only if they differ on all
    four.  In S4-G100 they differ on none, and this function returns that fact
    rather than letting a document assert independence.
    """
    names = sorted(roles)
    shared = {axis: len({tuple(sorted([roles[n][axis]])) for n in names}) == 1
              for axis in ("code", "assumptions", "data", "author")}
    independent = not any(shared.values())
    return {
        "roles": names,
        "shared_axes": [a for a, s in shared.items() if s],
        "independent": independent,
        "status": "independent" if independent else "correlated",
        "consequence": ("deposits may claim MeasuredPattern at most; no deposit "
                        "from these roles is independent verification")
        if not independent else "",
    }


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionReport:
    """Why a candidate got the deposit type it got."""

    deposit_type: str
    evidence_tag: str
    per_gate: dict
    dominated: bool
    self_promotion_blocked: bool
    witness_status: str
    reason: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.deposit_type} [{self.evidence_tag}]: {self.reason}"


def nest_decision(candidate_metrics: dict, region: EffectRegion,
                  generated_by=frozenset(), authorized_by=frozenset(),
                  dependency_edges=None, witness_status: str = "correlated",
                  ) -> DecisionReport:
    """Decide a deposit type from a preregistered region and a witness check.

    Order matters and is deliberate: self-promotion is checked **first**, so a
    candidate that clears every numeric gate but has no external witness is
    reported as blocked rather than as a near miss.
    """
    edges = dependency_edges or {}
    closure = dependency_closure(generated_by, edges)
    external = frozenset(authorized_by) - closure
    self_promoting = len(external) == 0

    per_gate = region.evaluate(candidate_metrics)
    dominated = all(per_gate.values())

    if self_promoting:
        return DecisionReport(
            deposit_type=DepositType.UNRESOLVED,
            evidence_tag=EvidenceTag.HYPOTHESIS,
            per_gate=per_gate, dominated=dominated,
            self_promotion_blocked=True, witness_status=witness_status,
            reason=("every authorizing node lies inside the dependency closure of "
                    "the generating nodes; a claim cannot promote itself"))

    if not dominated:
        failed = [k for k, v in per_gate.items() if not v]
        return DecisionReport(
            deposit_type=DepositType.CONJECTURE,
            evidence_tag=EvidenceTag.HYPOTHESIS,
            per_gate=per_gate, dominated=False,
            self_promotion_blocked=False, witness_status=witness_status,
            reason=f"effect region not dominated; failed gates: {failed}")

    if witness_status != "independent":
        return DecisionReport(
            deposit_type=DepositType.MEASURED_PATTERN,
            evidence_tag=EvidenceTag.MEASURED,
            per_gate=per_gate, dominated=True,
            self_promotion_blocked=False, witness_status=witness_status,
            reason=("effect region dominated, but the witnesses are correlated "
                    "(shared code, assumptions, data and authoring model), so this "
                    "is a measured pattern and not independent verification"))

    return DecisionReport(
        deposit_type=DepositType.MEASURED_PATTERN,
        evidence_tag=EvidenceTag.MEASURED,
        per_gate=per_gate, dominated=True,
        self_promotion_blocked=False, witness_status=witness_status,
        reason="effect region dominated with independent witnesses")


@dataclass
class Nest:
    """Holds deposits.  Append-only: retirement supersedes, it never deletes."""

    deposits: dict = field(default_factory=dict)

    def deposit(self, d: NestDeposit) -> NestDeposit:
        if d.candidate_id in self.deposits:
            raise GovernanceError(f"duplicate deposit {d.candidate_id}")
        self.deposits[d.candidate_id] = d
        return d

    def supersede(self, old_id: str, new: NestDeposit) -> NestDeposit:
        old = self.deposits[old_id]
        if old.superseded_by:
            raise GovernanceError(f"{old_id} already superseded")
        new.supersedes = old_id
        self.deposit(new)
        old.superseded_by = new.candidate_id
        return new

    def active(self) -> list:
        return [d for d in self.deposits.values()
                if not d.superseded_by and d.evidence_tag != EvidenceTag.RETIRED]
