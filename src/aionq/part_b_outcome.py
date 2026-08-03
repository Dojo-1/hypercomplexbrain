"""Typed outcome function for the unexecuted QSigma-R6k-W1 part B.

The scientific table is unchanged: INVALID -> REFUTED -> INCONCLUSIVE ->
SUPPORTING.  The input boundary is now closed.  A caller must supply the exact
160 per-map measurement rows.  The public function derives all eighty R6i-R6
differences itself, so a caller cannot substitute an unbound delta table.  All
sixteen noise coordinates remain present, so K9 cannot be bypassed or replaced
by an outcome-dependent aggregate.
"""

from __future__ import annotations

import math

from aionq.part_b_preflight import (
    HELD_OUT_DEPTH_COORDS,
    NOISE_COORDS,
    PartBPreflightError,
    pair_map_rows,
    validate_differential_cells,
)

__all__ = [
    "PROBABILITY_GATE",
    "INFORMATION_GATE",
    "HELD_OUT_DEPTHS",
    "ADMISSIBLE_RHO_LOW",
    "ADMISSIBLE_RHO_HIGH",
    "J_PSI_LOW",
    "J_PSI_HIGH",
    "PartBPreflightError",
    "j_psi",
    "probability_margin",
    "information_margin",
    "passes",
    "bracket_for",
    "bracket_position",
    "part_b_outcome",
    "OUTCOMES",
]

PROBABILITY_GATE = 1.0 / 16.0
INFORMATION_GATE = 0.02
HELD_OUT_DEPTHS = tuple(value for _, _, value in HELD_OUT_DEPTH_COORDS)

# J_psi is primary.  These are the binary64 evaluations of the exact inverse,
# not six-decimal numbers promoted into authoritative endpoints.
J_PSI_LOW, J_PSI_HIGH = 0.05, 0.20

#: PINNED BY BIT PATTERN, not recomputed at import.
#:
#: These were ``-0.5 * math.log1p(-math.sqrt(J_PSI))`` evaluated at import, and
#: that is not portable: ``log1p`` and ``sqrt`` are libm, and libm's last bit is
#: a platform fact.  Measured -- ADMISSIBLE_RHO_LOW comes out
#: ``0x1.032ba5565697dp-3`` on Windows/CPython 3.13 and ``0x1.032ba5565697cp-3``
#: on Linux/CPython 3.11, **exactly one ulp apart**.  ADMISSIBLE_RHO_HIGH happens
#: to agree on both.
#:
#: That one bit was not confined to a comparison.  ``part_b_preflight`` freezes
#: ``rho_low_binary64_hex`` as a literal and hashes payloads built from these
#: doubles, so a single differing bit propagated into the protocol digest, the
#: source-matrix payload digest and the frozen preflight projection -- five test
#: failures from one ulp.  This is the CRLF defect one level deeper: an evidence
#: chain that holds on one operating system is not an evidence chain, and here
#: the operating system entered through the last bit of a transcendental rather
#: than through a line ending.
#:
#: The values adopted are the ones the committed artifacts are already anchored
#: to.  Choosing the other platform's bit would invalidate every frozen digest to
#: gain nothing: both round-trip to the declared interval within 1e-16, at
#: J_psi = 0.05000000000000001 and 0.19999999999999998.
#:
#: The closed form remains the DEFINITION; these are its frozen evaluation. A
#: test asserts they agree with a live recomputation to within one ulp, which is
#: the honest relation between a definition and a pinned double.
ADMISSIBLE_RHO_LOW = float.fromhex("0x1.032ba5565697dp-3")
ADMISSIBLE_RHO_HIGH = float.fromhex("0x1.2f8155055de49p-2")

OUTCOMES = ("INVALID", "REFUTED", "INCONCLUSIVE", "SUPPORTING")
_CLEAN_COORDINATE = (0, 0)


def _finite_float(value: object, name: str) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise PartBPreflightError(f"{name} must be a finite Python binary64 float")
    return value


def j_psi(rho: float) -> float:
    """The swirl-angle Fisher information using a stable binary64 form."""

    rho = _finite_float(rho, "rho")
    return math.expm1(-2.0 * rho) ** 2


def probability_margin(delta_p: float) -> float:
    return _finite_float(delta_p, "delta_p") - PROBABILITY_GATE


def information_margin(delta_i: float) -> float:
    return _finite_float(delta_i, "delta_i") - INFORMATION_GATE


def passes(margin: float) -> bool:
    return _finite_float(margin, "margin") >= 0.0


def bracket_for(first_passing_depth, depths=HELD_OUT_DEPTHS):
    """Localise a crossing, using sealed R6l rho=0.1 as the lower anchor."""

    if first_passing_depth is None:
        return None
    first_passing_depth = _finite_float(first_passing_depth, "first passing depth")
    if tuple(depths) != HELD_OUT_DEPTHS:
        raise PartBPreflightError("the held-out depth grid may not be replaced")
    index = HELD_OUT_DEPTHS.index(first_passing_depth)
    low = HELD_OUT_DEPTHS[index - 1] if index > 0 else 0.1
    return (low, first_passing_depth)


def bracket_position(bracket) -> str:
    """Classify a bracket against the primary closed J_psi interval.

    Monotonicity of J_psi for nonnegative rho lets us do this in J-space and
    avoids treating rounded rho endpoints as exact inverses.
    """

    if type(bracket) not in (tuple, list) or len(bracket) != 2:
        raise PartBPreflightError("bracket must have exactly two endpoints")
    low = _finite_float(bracket[0], "bracket low")
    high = _finite_float(bracket[1], "bracket high")
    if not 0.0 <= low < high:
        raise PartBPreflightError("bracket endpoints must be finite and increasing")
    j_low, j_high = j_psi(low), j_psi(high)
    if j_high < J_PSI_LOW or j_low > J_PSI_HIGH:
        return "outside"
    if j_low >= J_PSI_LOW and j_high <= J_PSI_HIGH:
        return "inside"
    return "straddling"


def _rows_by_noise(cells: list[dict]) -> dict[tuple[int, int], dict[float, dict]]:
    grouped = {
        (eta_index, epsilon_index): {}
        for eta_index, _, _, epsilon_index, _, _ in NOISE_COORDS
    }
    depth_values = {
        index: value for index, _, value in HELD_OUT_DEPTH_COORDS
    }
    for cell in cells:
        coordinate = (cell["eta_index"], cell["epsilon_index"])
        grouped[coordinate][depth_values[cell["depth_index"]]] = {
            "delta_p": cell["delta_p"],
            "delta_i": cell["delta_i"],
        }
    return grouped


def _passing(rows: dict[float, dict]) -> dict[float, bool]:
    return {
        depth: passes(probability_margin(rows[depth]["delta_p"]))
        for depth in HELD_OUT_DEPTHS
    }


def _is_monotone(passing: dict[float, bool]) -> bool:
    seen_pass = False
    for depth in HELD_OUT_DEPTHS:
        if passing[depth]:
            seen_pass = True
        elif seen_pass:
            return False
    return True


def _first_pass(rows: dict[float, dict]):
    passing = _passing(rows)
    for depth in HELD_OUT_DEPTHS:
        if passing[depth]:
            return depth
    return None


def part_b_outcome(map_rows: list[dict]) -> dict:
    """Return one outcome after deriving 80 deltas from 160 exact map rows.

    Schema failures raise :class:`PartBPreflightError`; they are not scientific
    INVALID results.  Clean non-monotonicity and K9 disagreements are scientific
    INVALID outcomes because their complete, well-typed measurements exist but
    do not denote one crossing.
    """

    checked = list(validate_differential_cells(pair_map_rows(map_rows)))
    by_noise = _rows_by_noise(checked)
    clean = by_noise[_CLEAN_COORDINATE]
    clean_passing = _passing(clean)

    if not _is_monotone(clean_passing):
        return {
            "outcome": "INVALID",
            "reason": "non-monotone in depth on the clean coordinate",
            "passing": clean_passing,
        }

    clean_first = _first_pass(clean)
    noisy_first_passes: dict[str, float | None] = {}
    for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
        coordinate = (eta_index, epsilon_index)
        if coordinate == _CLEAN_COORDINATE:
            continue
        noisy = by_noise[coordinate]
        noisy_passing = _passing(noisy)
        label = f"eta={eta_decimal},epsilon={epsilon_decimal}"
        if not _is_monotone(noisy_passing):
            return {
                "outcome": "INVALID",
                "reason": f"K9: noisy coordinate {label} has no single crossing",
                "coordinate": label,
                "passing": noisy_passing,
            }
        noisy_first_passes[label] = _first_pass(noisy)

    disagreements = {
        coordinate: first
        for coordinate, first in noisy_first_passes.items()
        if first != clean_first
    }
    if disagreements:
        return {
            "outcome": "INVALID",
            "reason": "K9: clean and noisy coordinates disagree about the crossing",
            "clean_first_pass": clean_first,
            "noisy_first_passes": noisy_first_passes,
            "disagreements": disagreements,
        }

    probability_margins = {
        depth: probability_margin(clean[depth]["delta_p"])
        for depth in HELD_OUT_DEPTHS
    }
    information_margins = {
        depth: information_margin(clean[depth]["delta_i"])
        for depth in HELD_OUT_DEPTHS
    }
    b3_failures = [
        depth for depth in HELD_OUT_DEPTHS
        if not passes(information_margins[depth])
    ]

    if clean_first is None:
        return {
            "outcome": "REFUTED",
            "reason": "no held-out depth passes through 0.40",
            "probability_margins": probability_margins,
        }
    if j_psi(clean_first) < J_PSI_LOW:
        return {
            "outcome": "REFUTED",
            "reason": "K5b: the crossing precedes the information level said to cause it",
            "first_passing_depth": clean_first,
            "j_psi": j_psi(clean_first),
        }
    if b3_failures:
        return {
            "outcome": "REFUTED",
            "reason": f"B3: the information margin is negative at {b3_failures}",
            "information_margins": information_margins,
        }

    bracket = bracket_for(clean_first)
    position = bracket_position(bracket)
    if position == "outside":
        return {
            "outcome": "REFUTED",
            "reason": "the crossing bracket lies entirely outside J_psi in [0.05, 0.20]",
            "first_passing_depth": clean_first,
            "bracket": bracket,
            "bracket_position": position,
            "j_psi_at_bracket_low": j_psi(bracket[0]),
            "j_psi_at_bracket_high": j_psi(bracket[1]),
        }
    if position == "straddling":
        return {
            "outcome": "INCONCLUSIVE",
            "reason": (
                "K8: the bracket straddles an endpoint of J_psi in [0.05, 0.20] "
                "and may not be refined after seeing the data"
            ),
            "first_passing_depth": clean_first,
            "bracket": bracket,
            "bracket_position": position,
        }
    return {
        "outcome": "SUPPORTING",
        "reason": (
            "the crossing is bracketed strictly inside J_psi in [0.05, 0.20] "
            "and the clean information margin holds at every held-out depth"
        ),
        "first_passing_depth": clean_first,
        "bracket": bracket,
        "bracket_position": position,
        "j_psi": j_psi(clean_first),
    }
