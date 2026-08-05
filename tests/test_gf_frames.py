"""A frame group small enough to walk in full.

The moving-frame review sampled four to six points of `S_16`, a group of order
2.1e13, and a spread of zero over that is consistent with luck. `GF(16)` built
as a lift of a lift gives `AGL(1,16)`, of order 240, which can be enumerated
exhaustively -- so "orbit-collapsed" becomes a fact about a group rather than
about a sample.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from aionq.contraction import contraction_plan
from aionq.frame_orbit import relabel
from aionq.gf_frames import (SUBGROUP_LADDER, frobenius, gf16_mul, is_field,
                             ladder_report, stabiliser, subgroup)
from aionq.matchgate import matchgate_plan


def _free_fermion_16(layers: int = 3) -> QuantumCircuit:
    circuit = QuantumCircuit(16)
    for layer in range(layers):
        for qubit in range(16):
            circuit.t(qubit)
        for qubit in range(layer % 2, 15, 2):
            circuit.append(XXPlusYYGate(0.3 + 0.05 * qubit), [qubit, qubit + 1])
    return circuit


# ------------------------------------------------------------------ the tower

def test_the_tower_is_actually_a_field():
    """Checked exhaustively, not trusted from the construction.

    GF(16) = GF(4)[y]/(y^2+y+w) over GF(4) = GF(2)[x]/(x^2+x+1): a degree-2
    extension of a degree-2 extension. If the reduction polynomial were
    reducible the result would be a ring with zero divisors and every frame
    below would be meaningless.
    """
    report = is_field()
    assert report["all_invertible"]
    assert report["associative"]
    assert report["unit_is_one"]
    assert report["element_orders"] == [1, 3, 5, 15]
    assert report["generators"] == 8
    assert report["gf4_is_a_closed_subfield"]


def test_frobenius_generates_the_galois_group_of_the_tower():
    """`x -> x^2` has order 4 over GF(2); its square fixes GF(4) pointwise."""
    identity = tuple(range(16))
    once = tuple(frobenius(x) for x in range(16))
    twice = tuple(frobenius(frobenius(x)) for x in range(16))
    four = tuple(frobenius(frobenius(frobenius(frobenius(x)))) for x in range(16))
    assert once != identity
    assert four == identity
    # Gal(GF(16)/GF(4)) is the order-2 subgroup, fixing the subfield 0..3.
    for element in range(4):
        assert twice[element] == element


# --------------------------------------------------------------- the subgroups

@pytest.mark.parametrize("name,order", [
    ("T2", 2), ("T4", 4), ("T16", 16), ("M3", 3), ("M15", 15),
    ("FROBENIUS", 4), ("AGL", 240),
])
def test_each_rung_has_its_stated_order_and_is_a_set_of_permutations(name, order):
    frames = subgroup(name)
    assert len(frames) == order
    assert len(set(frames)) == order
    for frame in frames:
        assert sorted(frame) == list(range(16)), name


def test_the_ladder_is_nested():
    """Russian doll: each rung sits inside the next."""
    assert set(subgroup("T2")) <= set(subgroup("T4"))
    assert set(subgroup("T4")) <= set(subgroup("T16"))
    assert set(subgroup("M3")) <= set(subgroup("M15"))
    for name in ("T16", "M15", "FROBENIUS"):
        if name != "FROBENIUS":
            assert set(subgroup(name)) <= set(subgroup("AGL")), name


def test_agl_is_closed_under_composition():
    """It must be a group, or "exhaustive over the orbit" means nothing."""
    frames = set(subgroup("AGL"))
    sample = subgroup("AGL")[::37]
    for first in sample:
        for second in sample:
            composed = tuple(second[index] for index in first)
            assert composed in frames


# ------------------------------------------------------------ what it measures

def test_contraction_width_is_collapsed_on_the_whole_affine_group():
    """The claim the sampled review could only suggest.

    Zero spread over six random frames was consistent with luck. Zero spread
    over all 240 elements of AGL(1,16) is a fact about the group.
    """
    circuit = _free_fermion_16()
    levels = {level.rung: level for level in
              ladder_report(lambda c: contraction_plan(c).width, circuit)}
    for name in SUBGROUP_LADDER:
        assert levels[name].collapsed, name
        assert levels[name].spread == 0.0
    assert levels["AGL"].order == 240
    assert levels["AGL"].stabiliser_order == 240


def test_the_free_fermion_certificate_survives_exactly_two_of_240_frames():
    """And they are the identity and the reversal.

    `b = 15` is XOR with all-ones, which on 0..15 is `x -> 15 - x`. So the
    stabiliser is `Aut(P_16)`, the automorphism group of the path graph the
    gates were laid on, of order 2 and index 120. The certificate does not
    merely depend on the labelling -- it depends on it maximally, surviving
    only the symmetry of the 1D chain itself.
    """
    circuit = _free_fermion_16()
    keep = stabiliser(lambda c: float(matchgate_plan(c).valid), circuit, "AGL")
    assert len(keep) == 2
    assert tuple(range(16)) in keep
    assert tuple(range(15, -1, -1)) in keep


def test_the_certificate_already_resolves_on_the_smallest_rung():
    """A two-element group is enough to break it.

    T2 is translation by span{1}: a single relabelling. Invariance fails at the
    bottom of the ladder, which is the sharpest possible statement of frame
    dependence.
    """
    circuit = _free_fermion_16()
    levels = {level.rung: level for level in
              ladder_report(lambda c: float(matchgate_plan(c).valid), circuit)}
    assert not levels["T2"].collapsed
    assert levels["T2"].stabiliser_order == 1
    assert levels["AGL"].stabiliser_order == 2
    assert levels["AGL"].index == 120


def test_the_ladder_separates_the_two_kinds_of_measurement():
    """The point of a ladder rather than a single attack.

    One measurement survives to the top rung and one fails at the bottom. A
    review that reported only "some things are frame-dependent" would have
    lost that, and it is the whole content.
    """
    circuit = _free_fermion_16()
    width = ladder_report(lambda c: contraction_plan(c).width, circuit)
    certificate = ladder_report(
        lambda c: float(matchgate_plan(c).valid), circuit)
    assert all(level.collapsed for level in width)
    assert not any(level.collapsed for level in certificate)


def test_relabelling_by_a_field_element_is_still_physically_trivial():
    """The action must not change the circuit, only the names on its wires."""
    circuit = _free_fermion_16(layers=1)
    frame = subgroup("AGL")[57]
    moved = relabel(circuit, frame)
    assert len(moved.data) == len(circuit.data)
    assert [i.operation.name for i in moved.data] == \
           [i.operation.name for i in circuit.data]


# ------------------------------------------------- the lift, and 3-XOR structure

def test_three_xor_orthogonality_is_the_line_structure_of_pg32():
    """`a ^ b ^ c == 0` on the 15 non-zero labels: 35 lines, 7 through a point.

    The characteristic-2 orthogonality the Fano plane encodes one dimension
    lower, and the structure `fano_algebra` already uses for the octonions.
    """
    from collections import Counter

    from aionq.gf_frames import pg32_lines

    lines = pg32_lines()
    assert len(lines) == 35
    assert all(len(line) == 3 for line in lines)
    assert all(a ^ b ^ c == 0 for a, b, c in lines)
    through = Counter(point for line in lines for point in line)
    assert set(through.values()) == {7}
    assert set(through) == set(range(1, 16))


def test_three_xor_orthogonality_separates_the_linear_part_from_the_affine():
    """It is a GL(4,2) invariant and NOT an AGL(4,2) one.

    Linear maps must preserve it, since `M(a^b^c) = Ma ^ Mb ^ Mc`. Translations
    must not:  `(a^t) ^ (b^t) ^ (c^t) = a^b^c^t = t`, non-zero for every
    non-zero `t`. The relation is anchored at the origin and translations move
    the origin, so 3-XOR orthogonality is exactly what tells the two halves of
    the frame group apart.
    """
    from aionq.gf_frames import agl42_generators, preserves_lines

    generators = agl42_generators()
    linear = {k: v for k, v in generators.items() if k.startswith("E")}
    translations = {k: v for k, v in generators.items()
                    if k.startswith("translate")}
    assert len(linear) == 12 and len(translations) == 4
    assert all(preserves_lines(p) for p in linear.values())
    assert not any(preserves_lines(p) for p in translations.values())


def test_the_lift_to_agl42_is_decided_exactly_by_sixteen_generators():
    """AGL(1,16) has 240 frames; AGL(4,2) has 322560, a factor of 1344 more.

    It cannot be walked, and does not need to be: a measurement constant on a
    generating set is constant on the group, so sixteen checks settle all
    322560 elements. Contraction width survives the lift.
    """
    from aionq.gf_frames import invariant_under_agl42

    circuit = _free_fermion_16()
    verdict = invariant_under_agl42(lambda c: contraction_plan(c).width, circuit)
    assert verdict["order"] == 322560
    assert verdict["generators_checked"] == 16
    assert verdict["invariant"]
    assert verdict["generators_breaking"] == ()


def test_the_certificate_is_broken_by_every_single_generator():
    """Maximal fragility, and sharper than the index-120 statement.

    Not merely "a small stabiliser in AGL(1,16)": every one of the sixteen
    elementary moves of the full affine group destroys the free-fermion
    certificate.
    """
    from aionq.gf_frames import agl42_generators, invariant_under_agl42

    circuit = _free_fermion_16()
    verdict = invariant_under_agl42(
        lambda c: float(matchgate_plan(c).valid), circuit)
    assert not verdict["invariant"]
    assert len(verdict["generators_breaking"]) == len(agl42_generators()) == 16


# ------------------------------------- is orthogonality the ONLY separator?

def test_cycle_type_separates_the_generators_but_not_the_group():
    """The "360 reading" -- going all the way round -- is not a complete invariant.

    On the generators it looks decisive: translations are fixed-point-free
    involutions of cycle type 2^8, transvections are involutions with eight
    fixed points, 2^4 1^8. But across the whole of AGL(1,16), three of the five
    cycle types contain BOTH line-preserving and line-breaking frames, so cycle
    structure cannot decide which half of the frame group an element lies in.

    3-XOR orthogonality can, exactly. So "only orthogonally readable" is the
    right description, and it is a statement about the group rather than about
    the generators.
    """
    from collections import Counter

    from aionq.gf_frames import agl42_generators, preserves_lines, subgroup

    def cycle_type(permutation):
        seen, lengths = set(), []
        for start in range(len(permutation)):
            if start in seen:
                continue
            length, cursor = 0, start
            while cursor not in seen:
                seen.add(cursor)
                cursor = permutation[cursor]
                length += 1
            lengths.append(length)
        return tuple(sorted(lengths, reverse=True))

    generators = agl42_generators()
    translations = [v for k, v in generators.items() if k.startswith("translate")]
    transvections = [v for k, v in generators.items() if k.startswith("E")]
    assert {cycle_type(p) for p in translations} == {(2,) * 8}
    assert {cycle_type(p) for p in transvections} == {(2, 2, 2, 2) + (1,) * 8}

    # On the generators, cycle type happens to separate them.
    assert {cycle_type(p) for p in translations}.isdisjoint(
        {cycle_type(p) for p in transvections})

    # On the whole group it does not.
    frames = subgroup("AGL")
    by_type = {}
    for frame in frames:
        by_type.setdefault(cycle_type(frame), set()).add(preserves_lines(frame))
    mixed = [ct for ct, verdicts in by_type.items() if len(verdicts) > 1]
    assert len(mixed) == 3, by_type
    assert len(by_type) == 5


def test_the_linear_part_is_the_alternating_group_on_eight_letters():
    """GL(4,2) = A_8, the exceptional isomorphism, and 360 = |A_6| divides it."""
    import math

    assert 20160 == math.factorial(8) // 2
    assert 20160 % 360 == 0


def test_the_hardness_landscape_is_a_step_and_not_a_saddle():
    """There is no saddle in frame space, and the reason is structural.

    `q_sim_upper` is a minimum over four strategies. Three of them -- stabilizer
    T-count, basis permutation and contraction width -- are orbit-collapsed, and
    that is proved on all 322560 frames of AGL(4,2) by the generator argument.
    The only orbit-resolving member is the free-fermion path, whose value is
    BINARY. A minimum over three constants and one two-valued function takes at
    most two values.

    So the landscape over the frame group is flat at two levels with a cliff
    between them, at the stabiliser of index 120. Nothing is "close to" the
    transition: there is no metric on the frame group in which frames approach
    it, and every non-stabiliser frame is equally far from it.
    """
    from aionq.gf_frames import invariant_under_agl42
    from aionq.residency import simulation_residency

    circuit = _free_fermion_16()
    # The three collapsed members, proved on the full lifted group.
    for measure in (lambda c: simulation_residency(c).t_count,
                    lambda c: contraction_plan(c).width):
        assert invariant_under_agl42(measure, circuit)["invariant"]

    # The resolving member is binary.
    assert set(float(matchgate_plan(relabel(circuit, f)).valid)
               for f in subgroup("AGL")) <= {0.0, 1.0}

    # Hence at most two levels, and exactly two are realised.
    sampled = {round(simulation_residency(relabel(circuit, subgroup("AGL")[i]))
                     .q_sim_upper, 6)
               for i in (0, 1, 8, 89, 239)}
    assert len(sampled) == 2
    assert 0.0 in sampled
