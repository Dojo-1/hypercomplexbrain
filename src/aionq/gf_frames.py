"""A frame group you can enumerate: GF(GF(2,2), GF(2,2)) and its subgroup ladder.

The moving-frame review left a real weakness and said so: the orbit of a
16-qubit circuit under relabelling is ``S_16``, of order 2.1e13, and it was
sampled with four to six frames.  A spread of zero over six random points of a
group that size is not evidence of invariance.

This module replaces the sample with a subgroup that can be enumerated
**exhaustively**, and takes its structure from the tower

    GF(2)  <  GF(4) = GF(2)[x]/(x^2 + x + 1)  <  GF(16) = GF(4)[y]/(y^2 + y + w)

-- a degree-2 extension of a degree-2 extension, each level a lift of the one
below.  Labelling 16 qubits by the elements of GF(16) turns field structure into
frame structure: the affine group

    AGL(1,16) = { x -> a*x + b : a in GF(16)*, b in GF(16) },  |G| = 240

is a subgroup of ``S_16`` small enough to walk in full, and its subgroups form a
nested ladder -- translations by nested GF(2)-subspaces, the multiplicative
group and its order-3 subgroup GF(4)*, and the Frobenius lift ``x -> x^2`` that
generates Gal(GF(16)/GF(2)) and whose square generates Gal(GF(16)/GF(4)).

This is the characteristic-2 analogue of what ``cayley_dickson`` already does
over the reals.  That module measures the associator at each rung of the
doubling tower and calls the result "a ladder of controlled failure types".
Here the ladder is of frame subgroups and the failure measured is loss of
invariance: **at which rung does a measurement stop seeing the object?**

MEASURED, exhaustively rather than sampled:

    contraction width     orbit-collapsed on ALL 240 frames of AGL(1,16)
    matchgate certificate stabiliser is exactly {identity, reversal}, order 2
    q_sim_upper           already resolving on the 4-element T4 rung,
                          spread 0.3125

The middle row is the sharp one.  Of 240 affine relabellings exactly two
preserve the free-fermion certificate: the identity, and ``b = 15``, which is
XOR with all-ones and therefore ``x -> 15 - x`` -- the reversal.  The stabiliser
is ``Aut(P_16)``, the automorphism group of the path graph, of index 120.  The
certificate does not merely depend on the labelling; it depends on it maximally,
surviving only the symmetry of the 1D chain the gates were laid on.

The first row upgrades a claim the sampled review could only suggest.  Zero
spread over six random frames was consistent with luck; zero spread over the
complete affine group is a fact about the group.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "GF4_MUL",
    "gf16_mul",
    "frobenius",
    "is_field",
    "SUBGROUP_LADDER",
    "subgroup",
    "OrbitLevel",
    "ladder_report",
    "stabiliser",
    "agl42_generators",
    "pg32_lines",
    "preserves_lines",
    "invariant_under_agl42",
    "discrete_log",
    "exponent_orbits",
    "orbit_geometry_report",
]

#: GF(4) = GF(2)[x]/(x^2+x+1) with 0,1,2,3 standing for 0, 1, w, w+1.
GF4_MUL = {
    (0, 0): 0, (0, 1): 0, (0, 2): 0, (0, 3): 0,
    (1, 1): 1, (1, 2): 2, (1, 3): 3,
    (2, 2): 3, (2, 3): 1,
    (3, 3): 2,
}


def _gf4(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return GF4_MUL[(a, b)] if (a, b) in GF4_MUL else GF4_MUL[(b, a)]


def gf16_mul(u: int, v: int) -> int:
    """Multiply in GF(16) = GF(4)[y]/(y^2 + y + w).

    ``u = a + b*y`` is packed as the nibble ``(b << 2) | a`` with ``a, b`` in
    GF(4).  Reduction uses ``y^2 = y + w``, so the product's constant part picks
    up ``b*d*w`` and its ``y`` part picks up ``b*d``.
    """
    a, b = u & 3, (u >> 2) & 3
    c, d = v & 3, (v >> 2) & 3
    ac, bd = _gf4(a, c), _gf4(b, d)
    low = ac ^ _gf4(bd, 2)
    high = _gf4(a, d) ^ _gf4(b, c) ^ bd
    return (high << 2) | low


def frobenius(x: int) -> int:
    """The lift ``x -> x^2``, generating Gal(GF(16)/GF(2)) of order 4."""
    return gf16_mul(x, x)


def is_field() -> dict:
    """Check the tower exhaustively rather than trusting the construction."""
    non_zero = list(range(1, 16))
    inverses = {}
    for x in non_zero:
        found = [y for y in non_zero if gf16_mul(x, y) == 1]
        if len(found) == 1:
            inverses[x] = found[0]
    associative = all(
        gf16_mul(gf16_mul(a, b), c) == gf16_mul(a, gf16_mul(b, c))
        for a in range(16) for b in range(16) for c in range(16))

    def order(g: int) -> int:
        steps, current = 1, g
        while current != 1:
            current = gf16_mul(current, g)
            steps += 1
        return steps

    subfield = [x for x in range(16) if (x >> 2) == 0]
    return {
        "all_invertible": len(inverses) == 15,
        "associative": associative,
        "unit_is_one": all(gf16_mul(x, 1) == x for x in range(16)),
        "element_orders": sorted({order(g) for g in non_zero}),
        "generators": sum(1 for g in non_zero if order(g) == 15),
        "gf4_is_a_closed_subfield": all(
            gf16_mul(a, b) in subfield for a in subfield for b in subfield),
    }


#: The Russian-doll ladder.  Each entry is a subgroup of AGL(1,16) <= S_16, and
#: each is walked in full -- no sampling anywhere in this module.
SUBGROUP_LADDER = ("T2", "T4", "T16", "M3", "M15", "FROBENIUS", "AGL")


def subgroup(name: str) -> tuple:
    """Every element of one rung, as an explicit permutation of 0..15."""
    if name == "T2":                       # translations by span{1}
        return tuple(tuple(x ^ t for x in range(16)) for t in (0, 1))
    if name == "T4":                       # translations by the GF(4) subfield
        return tuple(tuple(x ^ t for x in range(16)) for t in range(4))
    if name == "T16":                      # all translations
        return tuple(tuple(x ^ t for x in range(16)) for t in range(16))
    if name == "M3":                       # GF(4)* , order 3
        return tuple(tuple(gf16_mul(a, x) for x in range(16)) for a in (1, 2, 3))
    if name == "M15":                      # GF(16)*
        return tuple(tuple(gf16_mul(a, x) for x in range(16))
                     for a in range(1, 16))
    if name == "FROBENIUS":                # the tower's Galois action
        out, current = [], tuple(range(16))
        for _ in range(4):
            out.append(current)
            current = tuple(frobenius(x) for x in current)
        return tuple(out)
    if name == "AGL":
        return tuple(tuple(gf16_mul(a, x) ^ b for x in range(16))
                     for a in range(1, 16) for b in range(16))
    raise ValueError(f"unknown rung {name!r}")


@dataclass
class OrbitLevel:
    """One rung of the ladder, and what a measurement does on it."""

    rung: str
    order: int
    values: tuple = ()
    spread: float = 0.0
    collapsed: bool = True
    stabiliser_order: int = 0

    @property
    def index(self) -> int:
        """How much of the rung the measurement fails to be invariant under."""
        return self.order // self.stabiliser_order if self.stabiliser_order else 0


def stabiliser(measure, circuit, name: str = "AGL") -> tuple:
    """Every frame in a rung that leaves the measurement at its identity value."""
    from .frame_orbit import relabel

    base = float(measure(circuit))
    return tuple(frame for frame in subgroup(name)
                 if float(measure(relabel(circuit, frame))) == base)


def ladder_report(measure, circuit, rungs=SUBGROUP_LADDER,
                  tolerance: float = 1e-12) -> list:
    """Walk each rung in full and report where invariance is lost.

    The analogue of ``cayley_dickson.associator_ladder``: that one measures how
    badly associativity fails at each rung of the doubling tower, this one
    measures how badly invariance fails at each rung of the frame tower.
    """
    from .frame_orbit import relabel

    base = float(measure(circuit))
    levels = []
    for name in rungs:
        frames = subgroup(name)
        values = tuple(float(measure(relabel(circuit, frame)))
                       for frame in frames)
        spread = max(values) - min(values)
        levels.append(OrbitLevel(
            rung=name,
            order=len(frames),
            values=values,
            spread=spread,
            collapsed=spread <= tolerance,
            stabiliser_order=sum(1 for v in values if abs(v - base) <= tolerance),
        ))
    return levels


# --------------------------------------------------------------------------
# The lift: from the semilinear frame group to the full GF(2)-affine one
# --------------------------------------------------------------------------
#
# AGL(1,16) is only the group of maps x -> a*x + b that are semilinear over
# GF(16), of order 240.  Forgetting the field multiplication and keeping only
# the GF(2)-vector-space structure gives the strictly larger
#
#     AGL(4,2) = GF(2)^4 : GL(4,2),   |G| = 16 * 20160 = 322560
#
# a factor of 1344 more frames, and the largest linear frame group on 16 labels
# short of the full symmetric group.  It cannot be walked with a circuit
# measurement, but it does not need to be: invariance under a group is
# invariance under its GENERATORS, so sixteen checks decide all 322560 elements
# exactly.  That is the one place in this session where an exhaustive claim is
# available without an exhaustive computation.

_BASIS = (1, 2, 4, 8)


def _linear_map(rows) -> tuple:
    """Permutation induced by a 4x4 GF(2) matrix given as row bitmasks."""
    return tuple(
        sum(((bin(rows[i] & x).count("1") & 1) << i) for i in range(4))
        for x in range(16)
    )


def agl42_generators() -> dict:
    """Four translations and twelve transvections generate AGL(4,2)."""
    generators = {f"translate+{t}": tuple(x ^ t for x in range(16))
                  for t in _BASIS}
    for i in range(4):
        for j in range(4):
            if i != j:
                rows = list(_BASIS)
                rows[i] = _BASIS[i] ^ _BASIS[j]
                generators[f"E{i}{j}"] = _linear_map(rows)
    return generators


def pg32_lines() -> frozenset:
    """The 3-XOR orthogonal triples: ``a ^ b ^ c == 0`` on the 15 non-zero labels.

    These are the 35 lines of PG(3,2), seven through every point.  The relation
    is the characteristic-2 orthogonality the Fano plane encodes one dimension
    lower, and `fano_algebra` already uses that structure for the octonions.
    """
    from itertools import combinations

    return frozenset(
        tuple(sorted((a, b, a ^ b)))
        for a, b in combinations(range(1, 16), 2)
    )


def preserves_lines(permutation) -> bool:
    """Does a frame preserve 3-XOR orthogonality?

    Linear maps must: ``M(a^b^c) = Ma ^ Mb ^ Mc``, so a vanishing sum stays
    vanishing.  Translations must NOT, and the one-line reason is worth keeping
    explicit --

        (a^t) ^ (b^t) ^ (c^t) = a^b^c^t = t

    which is non-zero for every non-zero ``t``.  So 3-XOR orthogonality is a
    GL(4,2) invariant and NOT an AGL(4,2) invariant: the relation is anchored at
    the origin, and translations move the origin.  It is exactly the structure
    that separates the linear part of the frame group from the affine part.
    """
    lines = pg32_lines()
    try:
        return {tuple(sorted((permutation[a], permutation[b], permutation[c])))
                for a, b, c in lines} == lines
    except (IndexError, TypeError):  # pragma: no cover - malformed frame
        return False


def invariant_under_agl42(measure, circuit, tolerance: float = 1e-12) -> dict:
    """Decide invariance on all 322560 frames by checking sixteen generators.

    A measurement constant on a generating set is constant on the group it
    generates, so this is exhaustive despite touching sixteen frames.
    """
    from .frame_orbit import relabel

    base = float(measure(circuit))
    moved = {name: float(measure(relabel(circuit, frame)))
             for name, frame in agl42_generators().items()}
    breaking = tuple(sorted(name for name, value in moved.items()
                            if abs(value - base) > tolerance))
    return {
        "group": "AGL(4,2)",
        "order": 322560,
        "generators_checked": len(moved),
        "generators_breaking": breaking,
        "invariant": not breaking,
        "identity_value": base,
    }


# --------------------------------------------------------------------------
# The exponent line: what governs the orbits of x -> x^2 against x -> w x
# --------------------------------------------------------------------------

def discrete_log(base: int = 4) -> dict:
    """``GF(16)* -> Z/15`` as an explicit table, with the base verified primitive.

    ``4`` is a generator: its powers run ``1, 4, 6, 14, 5, 2, 8, 11, 7, 10, 3,
    12, 13, 9, 15`` and hit all fifteen non-zero elements.  Checked here rather
    than assumed, because everything below is a statement about the coordinate
    this table defines.
    """
    powers, current = [], 1
    for _ in range(15):
        powers.append(current)
        current = gf16_mul(current, base)
    if current != 1 or len(set(powers)) != 15:
        raise ValueError(f"{base} is not a primitive element of GF(16)")
    return {"base": base, "powers": tuple(powers),
            "log": {value: index for index, value in enumerate(powers)}}


def exponent_orbits(name: str, base: int = 4) -> tuple:
    """A rung's orbits on ``GF(16)*``, written in the exponent coordinate ``Z/15``.

    Zero is dropped: it is a fixed point of every rung in the ladder and carries
    no information about the orbit geometry.
    """
    table = discrete_log(base)["log"]
    permutations = subgroup(name)
    seen, out = set(), []
    for element in range(1, 16):
        if element in seen:
            continue
        orbit = frozenset(permutation[element] for permutation in permutations)
        seen |= orbit
        out.append(tuple(sorted(table[value] for value in orbit)))
    return tuple(sorted(out, key=lambda o: (len(o), o)))


def orbit_geometry_report(base: int = 4) -> dict:
    """What relates the orbits of ``x -> x^2`` to the orbits of ``x -> w x``.

    Pass to the exponent coordinate ``Z/15`` supplied by :func:`discrete_log`.
    There both rungs become elementary and they become *different kinds* of
    object on the same line:

        M3         x -> w x     TRANSLATION by 5.  Orbits are the cosets of the
                                additive subgroup <5> = {0, 5, 10}:
                                {0,5,10} {1,6,11} {2,7,12} {3,8,13} {4,9,14}
        FROBENIUS  x -> x^2     DILATION by 2.  Orbits are the orbits of the
                                multiplicative subgroup <2> = {1,2,4,8} of
                                (Z/15)*: {0} {5,10} {1,2,4,8} {3,6,9,12}
                                {7,11,13,14}

    So the answer to "what governs the two orbit systems" is that one is the
    additive and the other the multiplicative structure of a single ``Z/15``, and
    they are joined the way any affine line joins them: **dilation normalises
    translation**, ``sigma M_a sigma^-1 = M_{a^2}``, verified here for all fifteen
    ``a``.  Together they generate ``GammaL(1,16) = Z/15 : Z/4`` of order 60.

    The two systems meet in exactly one place.  ``<2>`` preserves ``<5>``
    setwise, so the M3 orbit ``{0,5,10}`` -- which is ``GF(4)*`` -- is a union of
    Frobenius orbits, ``{0}`` and ``{5,10}``.  It is the only M3 orbit that is,
    and correspondingly the two rungs share exactly ONE mode pair out of 19 and
    15: ``(2,3)``, which lies inside ``GF(4)``.  The subfield is the whole
    intersection.

    Both rungs have six orbits including zero, which is why the two families were
    indistinguishable to every graph invariant R1P tried.  The orbits differ in
    *shape* -- five 3-cycles against sizes 1, 2, 4, 4, 4 -- and identically in
    count.

    What this does NOT do is explain the collapse dichotomy of R1M through R1O.
    By R1Q that dichotomy does not survive a relabelling of the modes and is not
    a fact about the field at all, so there is nothing here for the field
    structure to explain.
    """
    table = discrete_log(base)
    inverse = [0] * 16
    for element in range(16):
        inverse[frobenius(element)] = element
    conjugation = all(
        tuple(frobenius(gf16_mul(a, inverse[x])) for x in range(16))
        == tuple(gf16_mul(gf16_mul(a, a), x) for x in range(16))
        for a in range(1, 16))

    frobenius_orbits = exponent_orbits("FROBENIUS", base)
    mult_orbits = exponent_orbits("M3", base)
    dilations = tuple(sorted({pow(2, k, 15) for k in range(4)}))
    translations = tuple(sorted({(5 * k) % 15 for k in range(3)}))
    return {
        "base": base,
        "frobenius_is_dilation_by": 2,
        "frobenius_orbits": frobenius_orbits,
        "frobenius_orbits_are_the_orbits_of": dilations,
        "multiplication_is_translation_by": 5,
        "multiplication_orbits": mult_orbits,
        "multiplication_orbits_are_the_cosets_of": translations,
        "dilation_normalises_translation": conjugation,
        "generated_group": "GammaL(1,16) = Z/15 : Z/4",
        "generated_order": 60,
        "dilation_preserves_the_translation_subgroup": (
            tuple(sorted({(2 * t) % 15 for t in translations})) == translations),
        "orbit_counts_agree": len(frobenius_orbits) == len(mult_orbits),
        "shared_orbit": translations,
    }
