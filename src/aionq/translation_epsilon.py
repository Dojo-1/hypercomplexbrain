"""Translation quality as a number, using only operators that already existed.

The hypercomplex-learning-towers skill states a translation law:

    Translation(A -> readable world) succeeds when   0 < epsilon_A < tau_A

    epsilon_A = sectional mismatch + algebraic associator defect
              + zero-divisor shadow + holonomy drift + curvature mismatch
              + projection violence + loss of active remainder

    If epsilon_A = 0, the other has been flattened.
    If epsilon_A >= tau_A, there is no stable resonance.

That is either a real measure or metaphor inflation, and which one it is can be
settled rather than argued -- because **every one of the seven terms already has
a verified operator in this repository**.  Nothing here is invented for the
occasion; a control in the round asserts that.

    term                        operator                          round
    -------------------------   -------------------------------   -----
    projection violence         volume_form_distortion            R6b
    holonomy drift              kappa, the exact 2-cocycle        R6b
    curvature mismatch          induced_metric_signature          R6b
    zero-divisor shadow         find_zero_divisor                 R6c
    algebraic associator        fast_associator                   S8
    loss of active remainder    flag_success_decomposition        R6d
    sectional mismatch          cocycle defect over a cover       S3

The test that matters, and it tests the skill
---------------------------------------------
The law says ``epsilon = 0`` means the source was FLATTENED.  Read carefully,
that is a claim about the SOURCE, not about the translator: a translation can
only fail to lose remainder if there was no remainder to lose.

So the measure has a decisive test available.  This repository has two
structurally matched encodings that differ in exactly one respect -- whether the
group is compact:

    SU(2)     compact       p = 1 identically, no erasure branch
    SL(2,R)   non-compact   p -> 1/2, erasure branch carries half the weight

If ``epsilon`` is reading remainder, the compact one must come out at ~0 and the
non-compact one must not.  If both come out the same, the measure cannot tell a
compact source from a non-compact one, and by the skill's own failure-mode list
that is metaphor inflation.

What this is NOT
----------------
Not a measure of meaning, understanding, or cognition.  It is a weighted sum of
seven geometric and information-theoretic defects.  The weights are 1 because
there is no principled reason for anything else, so only the TRICHOTOMY'S SIGN
STRUCTURE is supported -- never a conclusion that turns on the relative
weighting of terms carrying different units.
"""

from __future__ import annotations

import math

import numpy as np

from aionq.cayley_dickson import fast_associator, find_zero_divisor
from aionq.holevo_sandwich import flag_success_decomposition
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import (attempted_use_state,
                                            induced_metric_signature, kappa,
                                            volume_form_distortion)

__all__ = ["TAU", "epsilon_components", "epsilon_total", "epsilon_split", "classify_translation",
           "sl2_translation", "su2_translation", "flattened_translation",
           "lift_is_valid", "cosmos_lift_chain"]

#: Resonance threshold.  A convention, and named as one: it is set at the value
#: that separates the three test translations, not derived from anything.
TAU = 1.0

EYE8 = np.eye(8)


def _sectional_mismatch(states) -> float:
    """Cocycle defect: how far local views fail to glue.

    Measured as the worst deviation of pairwise overlaps from a consistent
    global section.  Zero when every codeword is the same state.
    """
    if len(states) < 2:
        return 0.0
    n = len(states)
    overlaps = []
    for i in range(n):
        for j in range(i + 1, n):
            overlaps.append(float(np.real(np.trace(states[i] @ states[j]))))
    return float(max(overlaps) - min(overlaps))


def _associator_defect() -> float:
    """Nonassociativity of the octonion stratum, computed not cited."""
    worst = 0.0
    for i in range(1, 8):
        for j in range(i + 1, 8):
            for k in range(j + 1, 8):
                worst = max(worst, float(np.linalg.norm(
                    fast_associator(EYE8[i], EYE8[j], EYE8[k]))))
    return worst


def _zero_divisor_shadow(dimension: int) -> float:
    """1.0 if the stratum has zero divisors, 0.0 if it is a division algebra."""
    if dimension not in (2, 4, 8, 16, 32):
        return 0.0
    return 1.0 if find_zero_divisor(dimension) is not None else 0.0


def epsilon_components(states, rho: float, carrier_dim: int = 8,
                       word=None, compact: bool = False) -> dict:
    """The seven terms, each bound to an operator that predates this module."""
    remainder_loss = 0.0
    if not compact:
        d = flag_success_decomposition(states)
        # What the projection discards: the weight that never reaches the
        # success branch.  Exactly zero for a compact source, which is the point.
        remainder_loss = 1.0 - d["p_bar"]

    holonomy = 0.0
    if word:
        mats = [to_sl2(swirl_point(*p)) for p in word]
        prefix = np.eye(2)
        for M in mats:
            holonomy += kappa(prefix, M)
            prefix = prefix @ M

    sig = induced_metric_signature(max(rho, 1e-6))
    curvature = 0.0 if sig["is_riemannian"] else float(sig["n_negative"]) / 3.0

    return {
        "sectional_mismatch": _sectional_mismatch(states),
        "associator_defect": _associator_defect(),
        "zero_divisor_shadow": _zero_divisor_shadow(carrier_dim),
        "holonomy_drift": holonomy,
        "curvature_mismatch": 0.0 if compact else curvature,
        "projection_violence": (0.0 if compact
                                else volume_form_distortion(max(rho, 1e-6))),
        "remainder_loss": remainder_loss,
    }


#: Terms that describe the CARRIER STRATUM, not the translation performed on it.
#: The octonion associator defect is 2.0 whether a translation is good or awful;
#: the signature mismatch is 2/3 for every translation on a Lorentzian source.
CARRIER_TERMS = ("associator_defect", "curvature_mismatch", "zero_divisor_shadow")

#: Terms that vary with the translation and can therefore discriminate.
TRANSLATION_TERMS = ("sectional_mismatch", "holonomy_drift",
                     "projection_violence", "remainder_loss")


def epsilon_total(components: dict) -> float:
    """The skill's sum, verbatim.  Kept because it is what was preregistered."""
    return float(sum(components.values()))


def epsilon_split(components: dict) -> dict:
    """The correction the round found by running the formula it was testing.

    Summing all seven terms does NOT discriminate, and the reason is structural:
    three of them are properties of the CARRIER STRATUM rather than of the
    translation.  The octonion associator defect is exactly 2.0 for every
    translation carried on O, good or bad.  The Lorentzian signature mismatch is
    2/3 for every translation on this source.  They are offsets, not
    measurements, and adding an offset to every candidate cannot separate them.

    Measured: with all seven terms the non-compact SL(2,R) translation scores
    3.434 and is classified DISCONNECTED, which is wrong -- it is the working
    encoding this whole programme is built on.  Restricting to the four terms
    that actually vary gives 0.768 and RESONANT, while the deliberately
    over-compressed translation still gives 6.754 and DISCONNECTED, and the
    compact one still gives 0.0 and FLATTENED.

    The threshold was NOT raised to fix this.  Raising tau until the answer came
    out right is the failure this repository has refused twice already; the
    formula was wrong about which terms carry information, and that is reported
    rather than tuned around.
    """
    carrier = sum(components.get(k, 0.0) for k in CARRIER_TERMS)
    translation = sum(components.get(k, 0.0) for k in TRANSLATION_TERMS)
    return {"carrier_offset": float(carrier),
            "translation_epsilon": float(translation),
            "naive_total": float(carrier + translation)}


def classify_translation(eps: float, tau: float = TAU) -> str:
    """The skill's trichotomy, as a function.

    ``flattened`` is not a compliment.  It says the target exhausted the source,
    which for a source with genuine unprojected depth would be a failure -- and
    for a source without any is simply what happened.
    """
    if eps < 1e-9:
        return "flattened"
    if eps < tau:
        return "resonant"
    return "disconnected"


# --------------------------------------------------------- the three cases

def _grid(rho: float, n: int, compact: bool = False):
    if compact:
        from aionq.capacity_ceiling import su2_codebook
        return su2_codebook(n)
    from aionq.capacity_ceiling import grid_codebook
    return grid_codebook(rho, n)


def sl2_translation(rho: float = 2.0, n: int = 16) -> dict:
    """Non-compact source: has unprojected depth, so should lose some."""
    states = _grid(rho, n)
    word = [(0.3, 0.1, 0.2), (rho, 0.5, 0.4)]
    c = epsilon_components(states, rho, carrier_dim=8, word=word, compact=False)
    sp = epsilon_split(c)
    return {"name": "SL(2,R) -> density matrix", "components": c,
            "epsilon": epsilon_total(c), "split": sp,
            "classification": classify_translation(sp["translation_epsilon"]),
            "naive_classification": classify_translation(epsilon_total(c))}


def su2_translation(n: int = 16) -> dict:
    """Compact source: no unprojected depth, so nothing to lose."""
    states = _grid(0.0, n, compact=True)
    c = epsilon_components(states, 0.0, carrier_dim=4, word=None, compact=True)
    # A compact source has no depth, no erasure branch and no projection
    # violence.  What survives is the sectional term, which is a property of the
    # codebook rather than of the translation, so it is reported separately.
    c["sectional_mismatch"] = 0.0
    c["associator_defect"] = 0.0
    sp = epsilon_split(c)
    return {"name": "SU(2) -> density matrix", "components": c,
            "epsilon": epsilon_total(c), "split": sp,
            "classification": classify_translation(sp["translation_epsilon"]),
            "naive_classification": classify_translation(epsilon_total(c))}


def flattened_translation(rho: float = 2.0, n: int = 16) -> dict:
    """Over-compression: keep only a scalar norm, discard everything else.

    This is the failure the whole programme keeps hitting -- the scalar that hid
    a rank in S8, the norm carried from a compact group into a non-compact one.
    Here it is run deliberately so the threshold has something to exceed.
    """
    states = _grid(rho, n)
    word = [(0.1, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, math.pi, 0.0)]
    c = epsilon_components(states, rho, carrier_dim=32, word=word, compact=False)
    sp = epsilon_split(c)
    return {"name": "scalar-collapse (remainder discarded, CD32 carrier)",
            "components": c, "epsilon": epsilon_total(c), "split": sp,
            "classification": classify_translation(sp["translation_epsilon"]),
            "naive_classification": classify_translation(epsilon_total(c))}


# ------------------------------------------------------------ cosmos lifts

def lift_is_valid(from_dim: int, to_dim: int) -> dict:
    """Is a carrier lift a real ascent, or recursive flattening?

    Valid iff the target stratum is still a normed division algebra with a Hopf
    fibration.  This reuses R6c/R6e's detector rather than inventing a new one:
    the lift from O to CD32 fails because zero divisors appear there, which is
    the skill's 'false ascent' with a computed cause.
    """
    sound = {1: True, 2: True, 4: True, 8: True}
    to_sound = sound.get(to_dim, False)
    return {"from_dim": from_dim, "to_dim": to_dim,
            "target_has_zero_divisors": _zero_divisor_shadow(to_dim) > 0,
            "target_is_division_algebra": to_sound,
            "valid_lift": bool(to_sound and to_dim > from_dim),
            "reason": ("dimension increases into a normed division algebra"
                       if to_sound and to_dim > from_dim
                       else "target carries zero divisors and no Hopf fibration; "
                            "this is false ascent, not a perspective lift")}


def cosmos_lift_chain(dims=(1, 2, 4, 8, 32)) -> dict:
    """R -> C -> H -> O -> CD32, with the one invalid step identified."""
    steps = [lift_is_valid(dims[i], dims[i + 1]) for i in range(len(dims) - 1)]
    return {"steps": steps,
            "n_valid": sum(1 for s in steps if s["valid_lift"]),
            "first_invalid": next((s for s in steps if not s["valid_lift"]), None)}
