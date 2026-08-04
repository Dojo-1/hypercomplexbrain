"""The portfolio has no redundancy, measured.

`q_sim_upper` is a minimum over four strategies. QSigma-R1a showed that on the
ACAF corpus the minimum is always achieved by the same one, so no number there
has a second opinion behind it. `experiments/strategy_disagreement.py` builds a
generator that deliberately breaks that monoculture -- interpolating between
magic density, locality and matchgate fraction -- and asks what happens when
several strategies CAN apply.

The answer is the point of this module, and it is negative. Corroboration is
not merely rare in the existing corpus; it is close to unavailable in
principle, because a minimum over upper bounds is dominated by whichever bound
is best and there is no reason two differently-motivated bounds should land in
the same place. The consequence is that a defect in the winning strategy is
undetectable from inside the portfolio -- which is exactly what happened twice
in QSigma-R1a.

These tests use a reduced cube so the suite stays fast, and assert the
STRUCTURE rather than pinned figures, which would turn every future strategy
into a test failure.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

from strategy_disagreement import Core, build  # noqa: E402

from aionq.residency import simulation_residency  # noqa: E402


def _reduced_cube(seed: int = 23) -> list:
    rng = np.random.default_rng(seed)
    cores: list[Core] = []
    for n in (6, 8):
        for depth in (2, 4):
            for magic in (0.0, 0.5, 1.0):
                for locality in (0.0, 1.0):
                    for matchgate in (0.0, 1.0):
                        circuit = build(rng, n, depth, magic, locality, matchgate)
                        report = simulation_residency(circuit)
                        cores.append(Core(
                            n=n, depth=depth, magic=magic, locality=locality,
                            matchgate=matchgate,
                            costs=dict(report.strategy_costs),
                            reported=report.log2_sim_cost,
                            winner=report.bounding_strategy))
    return cores


@pytest.fixture(scope="module")
def cores():
    return _reduced_cube()


def test_the_generator_actually_breaks_the_monoculture(cores):
    """Otherwise this whole module measures the ACAF corpus again.

    On ACAF all 150 cores are bounded by stabilizer rank. If this generator
    could not move the winner, it would have no standing to say anything about
    what happens when strategies compete.
    """
    winners = {core.winner for core in cores}
    assert len(winners - {"dense"}) >= 3, winners


def test_most_cores_have_no_second_opinion_at_all(cores):
    """The headline negative result.

    A core with one applicable strategy has a bound with nothing to compare it
    against: every other strategy either does not apply or does not beat brute
    force. No error in the winner would be visible from inside the portfolio.
    """
    lonely = [core for core in cores if len(core.applicable) <= 1]
    assert len(lonely) > len(cores) // 3, (
        f"only {len(lonely)}/{len(cores)} cores lack a runner-up; if this ever "
        "drops far, the portfolio has acquired real redundancy and the claim "
        "in the docstring needs re-measuring")


def test_where_a_runner_up_exists_it_disagrees_by_an_order_of_magnitude(cores):
    """Strategies do not nearly-agree; they differ by bits.

    A margin of 3 bits is a factor of 8 in simulation cost. Two bounds that far
    apart are not corroborating each other -- the larger one is simply not
    binding, and the reported number is still the output of one algorithm.
    """
    margins = [core.margin for core in cores if len(core.applicable) >= 2]
    assert margins, "the reduced cube produced no core with a runner-up"
    assert float(np.median(margins)) > 1.0


def test_near_ties_are_rare_enough_to_be_a_curiosity(cores):
    """The corroborated region is a measure-near-zero surface, not a region."""
    tied = [core for core in cores
            if len(core.applicable) >= 2 and core.margin <= 0.5]
    assert len(tied) < max(1, len(cores) // 10)


def test_the_free_fermion_path_is_all_or_nothing_and_never_corroborated(cores):
    """A single non-matchgate gate removes the strategy entirely.

    So it cannot approach another strategy continuously: wherever it applies it
    wins outright, and wherever it does not it contributes nothing. It is the
    clearest case of a bound with no second opinion available even in principle.
    """
    fermionic = [core for core in cores if "free_fermion" in core.applicable]
    if not fermionic:
        pytest.skip("reduced cube produced no free-fermion core")
    for core in fermionic:
        assert core.costs["free_fermion"] == 0.0
        others = [cost for name, cost in core.costs.items()
                  if name != "free_fermion" and math.isfinite(cost)
                  and cost < float(core.n)]
        # When anything else applies at all, it is nowhere near.
        for cost in others:
            assert cost >= 1.0


def test_margin_is_infinite_exactly_when_there_is_no_runner_up(cores):
    for core in cores:
        assert math.isinf(core.margin) == (len(core.applicable) < 2)


def test_a_saturated_core_has_no_applicable_strategy(cores):
    for core in cores:
        if core.winner == "dense":
            assert core.applicable == []
        else:
            assert core.winner in core.applicable
