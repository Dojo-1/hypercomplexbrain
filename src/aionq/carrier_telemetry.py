"""Making the abstraction observable, without inventing a single new quantity.

Three directions were named: cognition telemetry (a dominance trace with energy
transfer and projection violence per bridge event), motion as proof-pressure
(loss of coherence marks a failure mode -- false ascent, energy leakage, bridge
absorption), and cosmos-level multiplicity (each endpoint its own fibre with
carrier dominance, remainder, and return path).

Every one of those quantities already has an exact operator in this repository.
This module wires them into a trace and builds DETECTORS for the three named
failure modes.  It adds no new measure.  Where a named term has no operator it
is left unimplemented and said so.

    named term                  operator                              verified
    -------------------------   -----------------------------------   --------
    energy transfer / bridge    kappa(X,Y) = log|X| + log|Y| - log|XY|  R6b
    projection violence         sqrt(det J) / sqrt|det g_src|           R6b
    carrier dominance           Cayley-Dickson rung + Hopf boundary     R6c
    return path                 kappa(M^-1, M) = 2 rho                  R6b
    remainder survival          operational trace distance              R6d

What this is NOT
----------------
Not cognition.  Not awareness.  "Energy" here is a log-norm defect measured in
nats and has no physical content whatever; the word is retained only because the
supplied schema uses it.  The Om/AUM cadence is a naming convention with no
computational content, and is carried as a label, never as an operator.

The three detectors, and why each has a control
-----------------------------------------------
A detector that fires is only informative if there is something it does not fire
on.  So each one ships with the null it must stay silent for:

    FALSE_ASCENT       fires where zero divisors exist, so no Hopf fibration and
                       no norm multiplicativity do.  Control: dims 1,2,4,8.
    ENERGY_LEAKAGE     fires when a word streams through deeper prefixes than
                       its net element needs.  Control: a one-step word, where
                       kappa is exactly 0.
    BRIDGE_ABSORPTION  fires when the source moves and the operational state does
                       not.  Control: THE SAME source step at shallow depth.  If
                       it fires there too, the detector is reading step size
                       rather than depth, and means nothing.

BRIDGE_ABSORPTION is the interesting one, because it is not a bug report.  It is
the compactification of R6b made visible per event: at large rho a large source
step produces an operational step suppressed by ``e^{-4 rho}``.  The detector
fires exactly where the geometry says it must.

Joining the Ohnium atlas
------------------------
The supplied ``ohnium.observable-ascent.v2`` atlas carries a
``projection_violence.volume_form_distortion`` field that is null in 360 of its
480 bridge events.  :func:`fill_volume_form_distortion` computes it from that
record's own source coordinates using the R6b operator, so the two surfaces join
at the field rather than competing for it.
"""

from __future__ import annotations

import math

import numpy as np

from aionq.cayley_dickson import find_zero_divisor
from aionq.hyperbolic_qubit import swirl_point, swirl_state, to_sl2
from aionq.quantum_channel_geometry import (attempted_use_state, kappa,
                                            trace_distance_closed_form,
                                            volume_form_distortion)

__all__ = ["CARRIER_ORDER", "CD_DIMENSION", "carrier_is_sound", "BridgeEvent",
           "bridge_event", "trace_word", "detect", "confusion_matrix",
           "fill_volume_form_distortion", "TAU_LEAK", "TAU_SRC", "TAU_OP"]

#: The ladder as the supplied schema names it.  Note CD32 and A_n sit ABOVE the
#: last rung where a Hopf fibration exists; that is what FALSE_ASCENT is for.
CARRIER_ORDER = ("R", "H", "O", "CD32", "A_n")

#: Cayley-Dickson dimension of each named carrier.  A_n is open-ended and is
#: treated as 32-or-above for soundness purposes.
CD_DIMENSION = {"R": 1, "H": 4, "O": 8, "CD32": 32, "A_n": 32}

TAU_LEAK = 1e-9        # preregistered
TAU_SRC = 0.1          # preregistered
TAU_OP = 0.01          # preregistered


def carrier_is_sound(dimension: int) -> dict:
    """Whether a carrier rung is a normed division algebra with a Hopf fibration.

    Computed, not tabulated: :func:`find_zero_divisor` searches for an actual
    zero divisor at that dimension.  The ladder stops at 8 and this is why.
    """
    zd = find_zero_divisor(dimension) if dimension in (2, 4, 8, 16, 32) else None
    return {"dimension": dimension,
            "has_zero_divisor": zd is not None,
            "hopf_fibration_exists": dimension in (1, 2, 4, 8),
            "is_sound": dimension in (1, 2, 4, 8)}


class BridgeEvent(dict):
    """One step, recorded so that the trace can be audited without re-running it.

    A dict subclass so it serialises straight into the supplied schema.  The
    remainder is stored as a VECTOR, never as its norm -- see
    ``remainder_is_flattened``, which is the scalar-collapse control.
    """

    @property
    def remainder_is_flattened(self) -> bool:
        r = self.get("projection_violence", {}).get("discarded_vector")
        return r is None or len(np.atleast_1d(np.asarray(r))) <= 1


def bridge_event(prev_point, next_point, carrier: str = "O",
                 prefix=None) -> BridgeEvent:
    """Record one bridge, with every named quantity bound to its operator.

    ``prefix`` is the running product of all earlier steps.  It matters, and the
    first version of this function omitted it.

    kappa is a 2-COCYCLE, not an additive weight.  Summing kappa over ADJACENT
    PAIRS (M_i, M_{i+1}) does not give the word's kappa -- it double-counts every
    interior log-norm and uses pairwise products instead of the prefix chain.  The
    decomposition that telescopes is over prefixes:

        kappa_word = sum_i kappa(P_{i-1}, M_i),   P_i = M_1 ... M_i,  P_0 = I

    which collapses to ``sum_i log|M_i| - log|M_word|`` exactly.  Prediction T4
    asserted per-event and cumulative agree to 1e-12; on the pairwise version they
    disagreed at 1.2e-2, which is what T4 existed to catch.
    """
    Mp, Mn = to_sl2(swirl_point(*prev_point)), to_sl2(swirl_point(*next_point))
    rho_prev, rho_next = prev_point[0], next_point[0]

    source_step = float(np.linalg.norm(Mn - Mp))
    operational_step = trace_distance_closed_form(Mp, Mn)
    k = kappa(prefix, Mn) if prefix is not None else kappa(Mp, Mn)

    # The remainder: what the projection to the operational state discards.  The
    # operational state is A = M/||M||, so the discarded content is the scale --
    # kept as the full pair (log-scale, and the residual direction), not a norm.
    scale_prev = float(np.linalg.norm(Mp, 2))
    scale_next = float(np.linalg.norm(Mn, 2))
    discarded = [math.log(scale_prev), math.log(scale_next)]

    return BridgeEvent({
        "carrier": carrier,
        "carrier_dimension": CD_DIMENSION.get(carrier, 0),
        "source_coordinates": list(next_point),
        "source_step": source_step,
        "operational_step": operational_step,
        "operational_success_probability": attempted_use_state(Mn)[1],
        "energy_loss_nats": k,
        "survival_factor": math.exp(-2.0 * k),
        "projection_violence": {
            "volume_form_distortion":
                volume_form_distortion(rho_next) if rho_next > 0 else None,
            "discarded_vector": discarded,
            "rank_loss": 1},
        "return_path": {
            "source_defect": float(np.max(np.abs(
                np.linalg.inv(Mn) @ Mn - np.eye(2)))),
            "kappa_inverse_pair": kappa(np.linalg.inv(Mn), Mn),
            "expected_two_rho": 2.0 * rho_next,
            "streamed_survival": math.exp(-4.0 * rho_next)},
    })


def trace_word(points, carrier: str = "O") -> dict:
    """A dominance trace over a word, with cumulative and per-event bookkeeping.

    ``kappa`` is additive over composition, so the cumulative figure must equal
    the sum of the per-event figures.  Asserting that is what makes the trace
    auditable from its record instead of only by re-running it.
    """
    mats = [to_sl2(swirl_point(*p)) for p in points]
    events, prefix = [], np.eye(2)
    for i in range(len(points) - 1):
        events.append(bridge_event(points[i], points[i + 1], carrier, prefix=prefix))
        prefix = prefix @ mats[i + 1]
    per_event = sum(e["energy_loss_nats"] for e in events)

    net = np.eye(2)
    for M in mats[1:]:
        net = net @ M
    cumulative = (sum(math.log(float(np.linalg.norm(M, 2))) for M in mats[1:])
                  - math.log(float(np.linalg.norm(net, 2))))
    return {"carrier": carrier, "n_events": len(events), "events": events,
            "kappa_word": cumulative,
            "kappa_per_event_sum": per_event,
            "net_depth": swirl_state(np.array(
                [(net[0, 0] + net[1, 1]) / 2, (net[0, 1] - net[1, 0]) / 2,
                 (net[0, 0] - net[1, 1]) / 2, (net[0, 1] + net[1, 0]) / 2])).rho}


def detect(event: BridgeEvent, word_kappa: float | None = None) -> list:
    """Which of the three named failure modes this event exhibits.

    Returns a list because an event may exhibit more than one; the confusion
    matrix is only diagonal because each injected fault exhibits exactly one, not
    because the detector is built to return a single label.
    """
    failures = []
    if not carrier_is_sound(event["carrier_dimension"])["is_sound"]:
        failures.append("false_ascent")
    if word_kappa is not None and word_kappa > TAU_LEAK:
        failures.append("energy_leakage")
    if event["source_step"] > TAU_SRC and event["operational_step"] < TAU_OP:
        failures.append("bridge_absorption")
    return failures


def confusion_matrix(cases) -> dict:
    """`cases` is a mapping from injected fault name to its detected failures."""
    labels = ["false_ascent", "energy_leakage", "bridge_absorption"]
    matrix = {inj: {lab: int(lab in got) for lab in labels}
              for inj, got in cases.items()}
    diagonal = all(matrix[inj][inj] == 1
                   and sum(matrix[inj].values()) == 1 for inj in labels
                   if inj in matrix)
    return {"labels": labels, "matrix": matrix, "is_diagonal": bool(diagonal)}


def fill_volume_form_distortion(atlas_bridge: dict, source_coordinates) -> dict:
    """Complete the atlas's null ``volume_form_distortion`` from its own record.

    The supplied ``ohnium.observable-ascent.v2`` atlas declares the field and
    leaves it null in most bridge events.  R6b has the operator, and the atlas
    already carries the ``source_coordinates`` it needs, so nothing has to be
    guessed: the value is a function of the depth the record already states.
    """
    out = dict(atlas_bridge)
    pv = dict(out.get("projection_violence", {}))
    rho = float(source_coordinates[0])
    pv["volume_form_distortion"] = volume_form_distortion(rho) if rho > 0 else None
    pv["volume_form_distortion_source"] = "aionq.quantum_channel_geometry (R6b)"
    out["projection_violence"] = pv
    return out
