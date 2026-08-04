"""Two cone coordinates that are derivable rather than measurable.

Preregistered in `manifests/qsigma_r3b1_parity_derived_axes_preregistration.json`
and committed before this module existed.

R3B-0 left four of eight cone coordinates unmeasured, and two of them for a
reason that is a refusal rather than an absence:

    neg_energy   "Protocol operation counts are parity diagnostics, not an
                  energy measurement."
    neg_latency  "Protocol depth is a parity diagnostic, not a latency
                  measurement."

That refusal is correct and is not overturned here.  Counts are not energy.
What this module observes is that the cone does not ask for energy; it asks for
a *difference* in energy between two arms, and a difference can vanish for
reasons that hold under every naming of the quantity.

    THEOREM (parity-derived vanishing).
    Let P(arm) be the resource profile: trials, copies per trial, memory calls
    per trial, POVM outcomes, side registers, and the ordered schedule.  Let C
    be any cost function of the form C(arm) = f(P(arm)).  If
    P(target) = P(control) then C(target) = C(control), so

        delta_C = 0   exactly, for every such f.

    PROOF.  f is a function.  []

The proof is trivial and the content is entirely in the premise, which is why
the premise is re-checked here rather than assumed: `resource_parity` must hold
on every seed cluster, and the derivation is refused otherwise.

WHAT THIS EXCLUDES, stated because it is real.  The two arms differ in what
they do -- one coherent, one dephased -- while consuming the same amount.  A
physical cost model that charges differently for a coherent operation than for
a dephasing one at equal counts is NOT a function of the resource profile, and
this derivation is silent about it.  That is why `neg_energy` is the weaker of
the two.  `neg_latency` is stronger: the schedule is not merely equal across
arms but SHARED -- the identical ordered sequence of pair keys, consuming the
identical uniform draws -- so a latency model that separated the arms would
have to depend on something other than when operations occur.

A derived zero and a measured zero are not the same object.  This one is exact
and assumption-bearing; a measurement would be uncertain and assumption-free.
The cone cannot tell them apart, which is a fact about the cone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ParityDerivation",
    "derive_parity_axes",
    "PARITY_DERIVED_AXES",
    "PROFILE_COMPONENTS",
    "R3B_ARTIFACT",
]

R3B_ARTIFACT = "artifacts/r3b_four_cell/four_cell_calibration.json"

#: The coordinates this derivation can reach.  Both are `no_worse` in the R3B-0
#: cone, and both of the quantities R3B-0 names as their parity diagnostics are
#: functions of the resource profile.
PARITY_DERIVED_AXES = ("neg_energy", "neg_latency")

#: What "resource profile" means, matching `four_cell.ResourceParity` exactly.
#: A cost model that depends on nothing outside this list is covered.
PROFILE_COMPONENTS = (
    "trials",
    "copies_per_trial",
    "memory_calls_per_trial",
    "povm_outcomes",
    "side_registers",
    "schedule",
    "uniform_draws",
)


@dataclass
class ParityDerivation:
    """The derivation's premise, verdict, and refusals."""

    premise_holds: bool
    seeds_checked: int
    seeds_failing: tuple = ()
    derived: dict = field(default_factory=dict)
    refused: str = ""
    #: Cost models the derivation does NOT cover, by construction.
    excluded_models: tuple = ()

    @property
    def axes_closed(self) -> int:
        return len(self.derived)


def derive_parity_axes(root) -> ParityDerivation:
    """Derive `neg_energy` and `neg_latency` deltas from verified parity.

    Refuses -- returning no derived axes and a stated reason -- if any seed
    cluster's `resource_parity` control is not true.  The theorem is trivial;
    all of its force is in the premise, so an unverified premise must yield
    nothing rather than a zero.
    """
    artifact = json.loads(
        (Path(root) / R3B_ARTIFACT).read_text(encoding="utf-8"))
    clusters = artifact["seed_clusters"]

    failing = tuple(
        cluster.get("seed")
        for cluster in clusters
        if cluster.get("controls", {}).get("resource_parity") is not True
    )
    excluded = (
        "cost models that price coherence itself: the arms differ in what they "
        "do while consuming the same amount, so a model charging differently "
        "for a coherent operation than a dephasing one at equal counts is not "
        "a function of the resource profile and is not covered",
    )

    if failing or not clusters:
        return ParityDerivation(
            premise_holds=False,
            seeds_checked=len(clusters),
            seeds_failing=failing,
            refused=("resource parity does not hold on every seed, so the "
                     "premise of the derivation is unavailable and no "
                     "coordinate is derived"),
            excluded_models=excluded,
        )

    # The premise holds on every seed, so the difference vanishes exactly for
    # every profile-based cost model.  The value carries no uncertainty: it is
    # an identity between two equal numbers, not an estimate.
    derived = {
        axis: {
            "delta": 0.0,
            "exact": True,
            "basis": "resource-profile parity verified on every seed cluster",
            "quantified_over": "all cost models of the form f(resource profile)",
        }
        for axis in PARITY_DERIVED_AXES
    }
    return ParityDerivation(
        premise_holds=True,
        seeds_checked=len(clusters),
        seeds_failing=(),
        derived=derived,
        excluded_models=excluded,
    )
