"""The part B outcome function, executable rather than prose.

Round QSigma-R6k-W1, part B.  The outcome table lived in a manifest as English,
and an external audit found four ways it contradicted itself:

* it claimed the upper endpoint 0.296392 lies inside the bracket (0.30, 0.40).
  It does not -- 0.296392 < 0.30, so only (0.25, 0.30) contains it.
* its prose made a first pass at rho = 0.40 INCONCLUSIVE while its lookup table
  made 0.40 REFUTED.  Both were in the same document.
* a B3 failure -- the information margin going non-positive at some held-out
  depth -- had no outcome at all.
* K9, a disagreement between the clean noise slice and the fifteen noisy
  coordinates, had no typed outcome either.

A table that disagrees with itself is decided by whoever reads it, which is the
same defect as an unfrozen threshold one level up.  So the table is a function
here, it is total over its declared inputs, and the manifest quotes it rather
than restating it.

The margins are R6l's, verbatim and INCLUSIVE
---------------------------------------------
R6l gates on

    m_P = delta_P - 1/16 >= 0        (probability margin)
    m_I = delta_I - 0.02 >= 0        (information margin)

The previous manifest wrote the probability gate as strictly positive.  A strict
gate is a different gate: at exactly delta_P = 1/16 the two disagree, and that
point is reachable because 1/16 is exact in binary floating point.  Inclusive,
in float64, unrounded, as R6l has it.
"""

from __future__ import annotations

import math

__all__ = [
    "PROBABILITY_GATE", "INFORMATION_GATE", "HELD_OUT_DEPTHS",
    "ADMISSIBLE_RHO_LOW", "ADMISSIBLE_RHO_HIGH", "J_PSI_LOW", "J_PSI_HIGH",
    "j_psi", "probability_margin", "information_margin", "passes",
    "bracket_for", "bracket_position", "part_b_outcome", "OUTCOMES",
]

#: R6l's own gates.  1/16 is exact in binary64; 0.02 is not, and is used as the
#: nearest double exactly as R6l uses it, with no rounding of either side.
PROBABILITY_GATE = 1.0 / 16.0
INFORMATION_GATE = 0.02

#: Frozen before execution.  None appears in the R6k or R6l grids.
HELD_OUT_DEPTHS = (0.15, 0.20, 0.25, 0.30, 0.40)

#: J_psi(rho) = (1 - e^{-2 rho})^2 in [0.05, 0.20].
J_PSI_LOW, J_PSI_HIGH = 0.05, 0.20
ADMISSIBLE_RHO_LOW = 0.126548
ADMISSIBLE_RHO_HIGH = 0.296392

#: Evaluated in this order.  The first whose condition holds decides.
OUTCOMES = ("INVALID", "REFUTED", "INCONCLUSIVE", "SUPPORTING")


def j_psi(rho: float) -> float:
    """The swirl-angle Fisher information, R6b's closed form."""
    return (1.0 - math.exp(-2.0 * rho)) ** 2


def probability_margin(delta_p: float) -> float:
    """``m_P = delta_P - 1/16``.  R6l's, unrounded."""
    return float(delta_p) - PROBABILITY_GATE


def information_margin(delta_i: float) -> float:
    """``m_I = delta_I - 0.02``.  R6l's, unrounded."""
    return float(delta_i) - INFORMATION_GATE


def passes(margin: float) -> bool:
    """INCLUSIVE, as R6l has it.  ``>= 0``, not ``> 0``.

    The distinction is reachable: delta_P exactly 1/16 is representable, and the
    two rules disagree there.  The earlier manifest wrote the strict form, which
    is simply a different gate from the one R6l applies.
    """
    return margin >= 0.0


def bracket_for(first_passing_depth, depths=HELD_OUT_DEPTHS):
    """The interval that localises the crossing, or None if nothing passed.

    The lower edge is the depth below the first pass in the grid; when the first
    pass is the lowest held-out depth, the lower edge is R6l's own 0.1, which is
    the nearest measured depth below it.
    """
    if first_passing_depth is None:
        return None
    ordered = tuple(sorted(depths))
    index = ordered.index(first_passing_depth)
    low = ordered[index - 1] if index > 0 else 0.1
    return (low, first_passing_depth)


def bracket_position(bracket) -> str:
    """``inside`` | ``straddling`` | ``outside``, and the trichotomy is total.

    The crossing lies somewhere in the bracket and nowhere else, so what matters
    is the bracket's relation to [ADMISSIBLE_RHO_LOW, ADMISSIBLE_RHO_HIGH]:

    * ``inside``      -- every point of the bracket is admissible. The crossing
                         is admissible wherever in it the crossing actually is.
    * ``straddling``  -- an endpoint falls within the bracket, so the grid cannot
                         say which side the crossing is on. INCONCLUSIVE.
    * ``outside``     -- no point of the bracket is admissible, so the crossing
                         is inadmissible wherever it is. REFUTED, not
                         INCONCLUSIVE: a bracket entirely above 0.296392 places
                         the crossing at J_psi > 0.2036 with certainty.

    The corrected arithmetic lives here. 0.296392 lies inside (0.25, 0.30) and
    does NOT lie inside (0.30, 0.40) -- the superseded manifest asserted both,
    which is what made a first pass at 0.40 read as INCONCLUSIVE in its prose
    and REFUTED in its lookup table. (0.30, 0.40) is entirely above the
    admissible interval, so it refutes.
    """
    low, high = bracket
    if any(low < endpoint < high
           for endpoint in (ADMISSIBLE_RHO_LOW, ADMISSIBLE_RHO_HIGH)):
        return "straddling"
    if high <= ADMISSIBLE_RHO_LOW or low >= ADMISSIBLE_RHO_HIGH:
        return "outside"
    return "inside"


def part_b_outcome(rows, clean_slice_rows=None) -> dict:
    """Total over its inputs.  One of INVALID, REFUTED, INCONCLUSIVE, SUPPORTING.

    `rows` maps depth -> {"delta_p": float, "delta_i": float}, from the CLEAN
    noise slice.  `clean_slice_rows` optionally carries the same mapping derived
    from the fifteen noisy coordinates; when supplied and disagreeing about the
    first passing depth, K9 fires.

    Every branch returns a reason, so no outcome is reachable without a stated
    cause, and the caller cannot supply the cause afterwards.
    """
    depths = tuple(sorted(rows))
    if not depths:
        return {"outcome": "INVALID", "reason": "no depths measured"}
    missing = [d for d in HELD_OUT_DEPTHS if d not in rows]
    if missing:
        return {"outcome": "INVALID",
                "reason": f"held-out depths not measured: {missing}"}

    m_p = {d: probability_margin(rows[d]["delta_p"]) for d in depths}
    m_i = {d: information_margin(rows[d]["delta_i"]) for d in depths}
    passing = {d: passes(m_p[d]) for d in depths}

    # --- INVALID ---------------------------------------------------------
    # Non-monotone means "the crossing" does not denote. Monotone here is
    # "once passing, always passing at greater depth".
    seen_pass = False
    for d in depths:
        if passing[d]:
            seen_pass = True
        elif seen_pass:
            return {"outcome": "INVALID", "reason": "non-monotone in depth",
                    "probability_margins": m_p, "passing": passing}

    # B3 failure now HAS an outcome. It had none, which made a whole branch of
    # the measurement unclassifiable.
    b3_failures = [d for d in depths if not passes(m_i[d])]

    if clean_slice_rows is not None:
        noisy_first = _first_pass(clean_slice_rows)
        clean_first = _first_pass(rows)
        if noisy_first != clean_first:
            # K9, given a type. A disagreement between slices IS the result and
            # may not be resolved by preferring one.
            return {"outcome": "INVALID", "reason": "K9: clean and noisy slices "
                    "disagree about the crossing",
                    "clean_first_pass": clean_first,
                    "noisy_first_pass": noisy_first}

    first = _first_pass(rows)

    # --- REFUTED ---------------------------------------------------------
    if first is None:
        return {"outcome": "REFUTED",
                "reason": "no held-out depth passes through 0.40",
                "probability_margins": m_p}
    if j_psi(first) < J_PSI_LOW:
        return {"outcome": "REFUTED",
                "reason": ("K5b: the crossing precedes the information level "
                           "said to cause it"),
                "first_passing_depth": first, "j_psi": j_psi(first)}
    if b3_failures:
        return {"outcome": "REFUTED",
                "reason": "B3: the information margin is negative at "
                          f"{b3_failures}",
                "information_margins": m_i}

    bracket = bracket_for(first)
    position = bracket_position(bracket)

    # --- REFUTED (continued): a bracket wholly outside the interval ------
    if position == "outside":
        return {"outcome": "REFUTED",
                "reason": ("the crossing bracket lies entirely outside "
                           "[0.126548, 0.296392], so the crossing is "
                           "inadmissible wherever in it it falls"),
                "first_passing_depth": first, "bracket": bracket,
                "bracket_position": position,
                "j_psi_at_bracket_low": j_psi(bracket[0]),
                "j_psi_at_bracket_high": j_psi(bracket[1])}

    # --- INCONCLUSIVE ----------------------------------------------------
    if position == "straddling":
        return {"outcome": "INCONCLUSIVE",
                "reason": ("K8: the bracket straddles an endpoint of the "
                           "admissible interval and the grid cannot localise "
                           "further. It may not be resolved by adding depths"),
                "first_passing_depth": first, "bracket": bracket,
                "bracket_position": position}

    # --- SUPPORTING ------------------------------------------------------
    return {"outcome": "SUPPORTING",
            "reason": ("the crossing is bracketed strictly inside "
                       "[0.126548, 0.296392] and the information margin holds "
                       "at every held-out depth"),
            "first_passing_depth": first, "bracket": bracket,
            "bracket_position": position, "j_psi": j_psi(first)}


def _first_pass(rows):
    for depth in sorted(rows):
        if passes(probability_margin(rows[depth]["delta_p"])):
            return depth
    return None
