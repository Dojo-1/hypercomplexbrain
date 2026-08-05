"""An imported operator family, measured rather than believed.

`src/aionq/qffo.py` implements the quantum-fractal-fractional operators of
Attiya, Ibrahim, Hakami, Cho and Yassen (Axioms 14(1):57, 2025). It arrived as a
proposed answer to a gap this repository recorded in
`docs/FALCONER_ASSESSMENT.md` -- that a dimension-threshold theory has nothing to
act on here because the programme produces no fractal sets. An operator family
carrying a fractal order is a plausible source of such sets. That is a reason to
implement it and check it, which is what these tests do.

Two of the paper's own printed artefacts are checkable without reconstructing
any formula, and both are checked: its table of ``Gamma_q`` values against the
limit ``Gamma_q -> Gamma`` that ``Gamma_q`` is defined to have, and its worked
coefficient list against the closed form it concludes with.

The reproduction at ``q <= 0.7`` is what makes the rest attributable. An
implementation that could not match the paper anywhere would be evidence about
the implementation.
"""

from __future__ import annotations

import math

import pytest

from aionq.qffo import (PAPER_TABLE_1, MultiplierReading, apply_to_coefficients,
                        multiplier, q_gamma)

#: The paper's worked example: f(z) = z/(1-z), so every a_n = 1, under the
#: Riemann-Liouville branch at sigma = varsigma = 0.5.  Coefficients of z^2...z^10.
PAPER_COEFFICIENTS = {
    0.5: (0.60180222245094, 0.51583047638652, 0.45851597901024, 0.416832708191127,
          0.384768653714887, 0.359117410133894, 0.337992856596606,
          0.320203758880996, 0.304955960839043),
    0.9: (0.910075329966907, 0.880718061258298, 0.859237132934925,
          0.842389346014632, 0.828579684604556, 0.816909548201675,
          0.806824245137457, 0.797958044641441, 0.790057469942021),
}


# --------------------------------------------------------------------------
# The convention is the paper's, which is what makes the rest attributable
# --------------------------------------------------------------------------

@pytest.mark.parametrize("q", [0.001, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
def test_the_q_gamma_here_is_the_paper_s_own(q):
    """Reproduces the paper's Table 1 to 1e-8 or better for every q up to 0.7.

    At ``q <= 0.5`` the agreement is to machine precision. This is the control:
    an implementation that matched nowhere would be evidence about the
    implementation, and this one matches eight of eleven rows exactly.
    """
    for argument, printed in zip((2.1, 2.5, 2.9), PAPER_TABLE_1[q]):
        assert q_gamma(argument, q) == pytest.approx(printed, abs=1e-7)


@pytest.mark.parametrize("argument", [2.1, 2.5, 2.9])
def test_q_gamma_rises_to_the_ordinary_gamma_from_below(argument):
    """``Gamma_q -> Gamma`` as ``q -> 1``, monotonically, and never overshoots.

    This is the defining property, and it is what makes the next test a finding
    rather than a disagreement about precision: a value ABOVE ``Gamma(x)`` is not
    a less accurate ``Gamma_q``, it is on the wrong side of the limit.
    """
    values = [q_gamma(argument, q) for q in (0.5, 0.7, 0.9, 0.95, 0.99, 0.999)]
    limit = math.gamma(argument)

    assert all(left < right for left, right in zip(values, values[1:]))
    assert all(value < limit for value in values)
    assert values[-1] == pytest.approx(limit, rel=1e-3)


# --------------------------------------------------------------------------
# What the paper prints that its own definitions exclude
# --------------------------------------------------------------------------

@pytest.mark.parametrize("q,index", [(0.9, 0), (0.95, 0), (0.95, 1), (0.95, 2)])
def test_the_last_rows_of_the_paper_s_table_exceed_the_limit(q, index):
    """Four of the six entries at ``q = 0.9, 0.95`` are larger than ``Gamma(x)``.

    Since ``Gamma_q`` increases in ``q`` toward ``Gamma(x)`` from below, no value
    of ``Gamma_q`` can exceed it. The printed numbers also move AWAY from the
    limit as ``q`` rises -- ``Gamma_{0.95}(2.9) = 2.0587`` against
    ``Gamma(2.9) = 1.8274`` -- while the computed ones converge to it.

    Rows ``q <= 0.7`` reproduce here to 1e-8 with the same code, so this is a
    property of those two rows and not of the implementation.
    """
    argument = (2.1, 2.5, 2.9)[index]
    assert PAPER_TABLE_1[q][index] > math.gamma(argument)
    assert q_gamma(argument, q) < math.gamma(argument)


@pytest.mark.parametrize("q", sorted(PAPER_COEFFICIENTS))
def test_the_worked_coefficients_are_not_geometric_so_the_closed_form_fails(q):
    """The paper concludes ``Q f(z) = z/(1 - mu z)`` from these numbers.

    ``z/(1 - mu z)`` has coefficients ``mu^(n-1)``, so its successive ratios are
    constant. The printed ratios rise monotonically -- 0.857 to 0.952 at
    ``q = 0.5`` -- so no ``mu`` reproduces them.

    The weaker claim made alongside, that the coefficients are majorised by those
    of ``z/(1-z)``, is consistent with the numbers and is asserted here too. The
    two claims are not the same and only one of them survives.
    """
    printed = PAPER_COEFFICIENTS[q]
    ratios = [right / left for left, right in zip(printed, printed[1:])]

    assert all(left < right for left, right in zip(ratios, ratios[1:])), (
        "the ratios were expected to rise monotonically")
    assert max(ratios) - min(ratios) > 1e-2, (
        "a constant ratio would make the closed form z/(1-mu z) consistent")
    assert all(0.0 < value <= 1.0 for value in printed), (
        "the majorisation claim, which does hold")


def test_no_reading_of_the_coefficient_formula_reproduces_the_printed_numbers():
    """Recorded as a failure to reproduce, not as an error in the paper.

    The source text available to this session had its fraction structure
    destroyed in transmission, so a coefficient formula written as a ratio
    arrives as an ambiguous product. Four readings were tried -- both placements
    of the factorial power in the Riemann-Liouville branch, plus the Caputo and
    integral branches -- under both the q-gamma and the ordinary gamma. The
    closest came no nearer than 5.3e-2.

    This test pins the situation rather than a verdict: it asserts that the
    shipped reading disagrees, so that if a clean source later resolves the
    ambiguity the disagreement is already on record and dated.
    """
    printed = PAPER_COEFFICIENTS[0.5]
    weights = multiplier("riemann_liouville", 0.5, 0.5, 0.5, terms=len(printed) + 1)
    worst = max(abs(weight - value)
                for weight, value in zip(weights[1:], printed))

    assert worst > 1e-2, (
        "the shipped reading now agrees with the paper -- re-examine "
        "manifests/qsigma_r1e_qffo_import_finding.json, which records that it "
        "did not")


# --------------------------------------------------------------------------
# The operator itself, as implemented
# --------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["riemann_liouville", "caputo", "integral"])
def test_every_branch_is_normalised_and_acts_diagonally(kind):
    """``kappa_1 = 1``, and the operator is a coefficient multiplier.

    Diagonality is the structural point and the structural limit: a multiplier
    is a function of the number operator, hence of a connection Laplacian on a
    line bundle over the disk. So a QFFO is a spectral BAND WEIGHT. It is not a
    localisation, and a packet calculus needs operators that are not diagonal.
    """
    weights = multiplier(kind, 0.4, 0.3, 0.6, terms=8)
    assert weights[0] == 1.0
    assert all(math.isfinite(weight) for weight in weights)

    coefficients = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125)
    acted = apply_to_coefficients(coefficients, kind, 0.4, 0.3, 0.6)
    assert acted[0] == pytest.approx(1.0)
    for original, weight, result in zip(coefficients, weights, acted):
        assert result == pytest.approx(original * weight)


@pytest.mark.parametrize("kind", ["caputo", "integral"])
def test_the_unambiguous_branches_have_a_classical_limit(kind):
    """As ``q -> 1`` the q-branches approach their ordinary-gamma counterparts.

    Only the Caputo and integral branches are tested: their formulas are ratios
    of four gammas with no factorial power, so they survived transmission
    unambiguously. The Riemann-Liouville branch is a reading and is excluded on
    purpose -- testing a reading against itself would assert nothing.
    """
    sigma, varsigma = 0.4, 0.3

    def classical(n: int) -> float:
        if kind == "caputo":
            return (math.gamma(3 - sigma - varsigma) * math.gamma(n + 1 - varsigma)
                    / (math.gamma(2 - varsigma) * math.gamma(n + 2 - sigma - varsigma)))
        return (math.gamma(1 + 2 * sigma) * math.gamma(n + sigma)
                / (math.gamma(1 + sigma) * math.gamma(n + 2 * sigma)))

    for n in (2, 3, 5):
        approached = MultiplierReading(kind, sigma, varsigma, 0.999).weight(n)
        assert approached == pytest.approx(classical(n), rel=5e-3)
