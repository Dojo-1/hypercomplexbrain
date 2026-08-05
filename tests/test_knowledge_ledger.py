"""What stands, not what is broken.

Every instrument in this repository measures a deficiency. None reports the
positive quantity, so a session can drive the correction count from 41 to 67
and never ask what is standing. These tests pin the answer, including the
reading error that nearly buried it.
"""

from __future__ import annotations

import pytest

from aionq.evidence import EvidenceTag_REQUIRING_EVIDENCE
from aionq.governance import registry
from aionq.knowledge_ledger import R4_BASELINE, knowledge_ledger


@pytest.fixture(scope="module")
def ledger():
    return knowledge_ledger()


def test_retirement_is_the_largest_single_category(ledger):
    """The programme demotes claims at very nearly the rate it proves them.

    26 RETIRED against 25 PROVED and 25 MEASURED. Whether that is unusual
    rigour or claims arriving faster than support, the ledger alone cannot
    say -- but it is the dominant movement and no round-level audit sees it.
    """
    assert ledger.by_tag["R"] >= ledger.by_tag["P"]
    assert ledger.by_tag["R"] >= ledger.by_tag["M"]
    assert ledger.retirement_rate > 0.25


def test_exactly_one_evidence_requiring_claim_is_witnessed_and_it_is_the_axiom(ledger):
    """The sharpest number in the repository.

    Of 57 live claims at an evidence-requiring tag, one carries a verified
    envelope, and it is the AXIOM -- the tag whose own definition is "passes
    via an explicit axiom or a weaker surrogate check". Zero PROVED and zero
    MEASURED claims have one.
    """
    assert ledger.evidence_requiring >= 50
    assert len(ledger.witnessed) == 1
    assert ledger.witnessed == ("AXIOM-HB0-UNIVERSAL_POINCARE_BASE",)
    assert ledger.coverage < 0.05


def test_no_proved_or_measured_claim_carries_an_envelope(ledger):
    unwitnessed = set(registry.unwitnessed())
    for claim in registry._claims.values():
        if claim.tag in ("P", "M"):
            assert claim.id in unwitnessed, claim.id


def test_hypotheses_and_metaphors_are_not_counted_as_witnessed(ledger):
    """The reading error that inverted the ledger.

    `registry.unwitnessed()` returns claims at an EVIDENCE-REQUIRING tag with
    no envelope, so HYPOTHESIS and SEMANTIC claims never appear in it. Their
    absence means the question does not apply -- a metaphor cannot carry an
    envelope. Reading it as "witnessed" turns 1-of-57 coverage into an
    apparent 11-of-67, which is a sixfold overstatement in the one direction
    that flatters the programme.
    """
    assert "H" not in EvidenceTag_REQUIRING_EVIDENCE
    assert "S" not in EvidenceTag_REQUIRING_EVIDENCE
    assert ledger.not_applicable == 10
    # The inflated reading would have been this, and it is not the coverage.
    inflated = (len(ledger.witnessed) + ledger.not_applicable) / ledger.live
    assert inflated > 5 * ledger.coverage


def test_the_gap_is_widening_not_closing(ledger):
    """A derivative, not a level, and the one that actually matters.

    A large deficit that is closing is a programme in progress. A smaller
    deficit that is widening is not. Since the R4 baseline recorded in
    ARCHITECTURE.md section 7 -- 48 of 81 claims carrying no envelope -- twelve
    claims were added and eight arrived bare.
    """
    trajectory = ledger.trajectory
    assert trajectory["baseline_claims"] == R4_BASELINE["claims"]
    assert trajectory["claims_added"] > 0
    assert trajectory["unwitnessed_added"] > 0
    assert trajectory["share_of_new_claims_unwitnessed"] > 0.5
    assert ledger.gap_is_widening


def test_the_ledger_partitions_the_registry_without_loss(ledger):
    """Every claim is retired, evidence-requiring, or not applicable."""
    assert ledger.retired + ledger.live == ledger.total
    assert ledger.evidence_requiring + ledger.not_applicable == ledger.live
    assert sum(ledger.by_tag.values()) == ledger.total


def test_coverage_would_move_if_a_single_envelope_were_attached(ledger):
    """Falsifiability: the number responds to the event that would change it.

    One verified envelope on any PROVED or MEASURED claim doubles the
    programme's evidence coverage. That is the scale of what is missing, and
    it is also how little it would take to register progress.
    """
    assert ledger.coverage == pytest.approx(
        len(ledger.witnessed) / ledger.evidence_requiring)
    hypothetical = (len(ledger.witnessed) + 1) / ledger.evidence_requiring
    assert hypothetical > 1.9 * ledger.coverage
