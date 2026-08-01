"""The part B outcome function must be total, and must match its manifest.

The table it replaces contradicted itself in four ways inside one document: a
bracket arithmetic error, prose disagreeing with a lookup table about rho = 0.40,
a B3 failure with no outcome, and K9 with no outcome. Two copies of a rule drift.
These tests exist so the manifest and the function cannot.
"""

from __future__ import annotations

import json
import math

import pytest

from aionq.part_b_outcome import (ADMISSIBLE_RHO_HIGH, ADMISSIBLE_RHO_LOW,
                                  HELD_OUT_DEPTHS, INFORMATION_GATE, OUTCOMES,
                                  PROBABILITY_GATE, bracket_for,
                                  bracket_position, information_margin, j_psi,
                                  part_b_outcome, passes, probability_margin)
from aionq.self_audit import repo_root

MANIFEST = "qsigma_r6k_w1_partb_effective_protocol_v2.json"


def _rows(first_pass, *, delta_i=0.05, delta_p_pass=0.10, delta_p_fail=0.01):
    """Margins that pass from `first_pass` upward and fail below it."""
    return {d: {"delta_p": (delta_p_pass if (first_pass is not None and d >= first_pass)
                            else delta_p_fail),
                "delta_i": delta_i}
            for d in HELD_OUT_DEPTHS}


# ------------------------------------------------------------- the gates

def test_the_gates_are_r6ls_and_inclusive():
    """m_P = delta_P - 1/16 >= 0 and m_I = delta_I - 0.02 >= 0.

    The earlier manifest wrote the probability gate as strictly positive. That is
    a different gate, and the difference is reachable: 1/16 is exact in binary64,
    so delta_P == 1/16 lands exactly on the boundary and the two rules disagree
    there.
    """
    assert PROBABILITY_GATE == 0.0625
    assert INFORMATION_GATE == 0.02
    assert probability_margin(0.0625) == 0.0
    assert passes(0.0) is True, "the gate is inclusive"
    assert passes(-1e-18) is False
    assert information_margin(0.02) == 0.0


def test_the_boundary_case_is_reachable_and_passes():
    rows = _rows(0.20, delta_p_pass=1.0 / 16.0)
    assert part_b_outcome(rows)["outcome"] == "SUPPORTING"


# --------------------------------------------------- brackets, corrected

def test_the_upper_endpoint_is_not_inside_the_last_bracket():
    """The arithmetic error the whole amendment turns on.

    The superseded manifest asserted 0.296392 lies inside BOTH (0.25, 0.30) and
    (0.30, 0.40). It lies inside the first only, which is why a first pass at
    0.40 refutes rather than being inconclusive.
    """
    assert 0.25 < ADMISSIBLE_RHO_HIGH < 0.30
    assert not (0.30 < ADMISSIBLE_RHO_HIGH < 0.40)
    assert bracket_position((0.25, 0.30)) == "straddling"
    assert bracket_position((0.30, 0.40)) == "outside"


@pytest.mark.parametrize("bracket,expected", [
    ((0.10, 0.15), "straddling"),
    ((0.15, 0.20), "inside"),
    ((0.20, 0.25), "inside"),
    ((0.25, 0.30), "straddling"),
    ((0.30, 0.40), "outside"),
])
def test_bracket_positions_for_this_grid(bracket, expected):
    assert bracket_position(bracket) == expected


def test_the_lowest_bracket_uses_r6ls_own_depth_as_its_floor():
    assert bracket_for(0.15) == (0.1, 0.15)


# ------------------------------------------------- the table, exhaustively

@pytest.mark.parametrize("first,expected", [
    (0.15, "INCONCLUSIVE"),
    (0.20, "SUPPORTING"),
    (0.25, "SUPPORTING"),
    (0.30, "INCONCLUSIVE"),
    (0.40, "REFUTED"),
    (None, "REFUTED"),
])
def test_first_passing_depth_decides(first, expected):
    assert part_b_outcome(_rows(first))["outcome"] == expected


def test_non_monotone_is_invalid_not_a_crossing():
    rows = _rows(0.20)
    rows[0.30]["delta_p"] = 0.01          # passes, then fails again
    result = part_b_outcome(rows)
    assert result["outcome"] == "INVALID"
    assert "non-monotone" in result["reason"]


def test_a_b3_failure_has_an_outcome_at_all():
    """It had none. A whole branch of the measurement was unclassifiable."""
    rows = _rows(0.20)
    rows[0.25]["delta_i"] = 0.001         # information margin negative
    result = part_b_outcome(rows)
    assert result["outcome"] == "REFUTED"
    assert result["reason"].startswith("B3")


def test_k9_slice_disagreement_has_an_outcome_at_all():
    """It had none either. A disagreement between slices IS the result."""
    result = part_b_outcome(_rows(0.20), clean_slice_rows=_rows(0.30))
    assert result["outcome"] == "INVALID"
    assert "K9" in result["reason"]


def test_agreeing_slices_do_not_fire_k9():
    """Or K9 is just a way of never returning anything."""
    assert part_b_outcome(_rows(0.20),
                          clean_slice_rows=_rows(0.20))["outcome"] == "SUPPORTING"


def test_a_missing_held_out_depth_is_invalid_not_ignored():
    rows = _rows(0.20)
    del rows[0.40]
    result = part_b_outcome(rows)
    assert result["outcome"] == "INVALID"
    assert "not measured" in result["reason"]


def test_the_function_is_total_and_always_states_a_reason():
    """No input reaches a default, and no outcome arrives without a cause.

    A verdict with no reason is one the caller supplies a reason for afterwards.
    """
    cases = [_rows(f) for f in (0.15, 0.20, 0.25, 0.30, 0.40, None)]
    broken = _rows(0.20); broken[0.30]["delta_p"] = 0.01
    starved = _rows(0.20); starved[0.25]["delta_i"] = 0.0
    cases += [broken, starved, {}]
    for rows in cases:
        result = part_b_outcome(rows)
        assert result["outcome"] in OUTCOMES
        assert result.get("reason")


# ----------------------------------------- the manifest quotes, never restates

def _manifest():
    return json.loads((repo_root() / "manifests" / MANIFEST).read_text(
        encoding="utf-8"))


def test_the_manifest_and_the_function_agree_on_every_row():
    """The defect being prevented: two copies of a rule that drift apart."""
    table = _manifest()["expected_classification_by_first_passing_depth"]
    for first in HELD_OUT_DEPTHS:
        key = f"{first:.2f}"
        assert table[key] == part_b_outcome(_rows(first))["outcome"], key
    assert table["none through 0.40"] == part_b_outcome(_rows(None))["outcome"]


def test_the_manifest_records_the_same_gates_the_code_uses():
    m = _manifest()["frozen_margins"]
    assert m["constants_in_code"]["PROBABILITY_GATE"] == PROBABILITY_GATE
    assert m["constants_in_code"]["INFORMATION_GATE"] == INFORMATION_GATE
    assert "INCLUSIVE" in m["gate"]


def test_the_manifest_requires_c_env_not_c_raw():
    """Part B may not consume upstream evidence weaker than it intends to produce."""
    pre = _manifest()["execution_precondition"]
    assert "C_env" in pre["requirement"]
    assert "not sufficient" in pre["requirement"]


def test_part_b_is_still_blocked_by_pending_inputs():
    """Mechanical, not a promise: the fields read PENDING and execution is barred."""
    inputs = _manifest()["measurement_inputs_that_must_be_frozen_before_execution"]
    pending = [k for k, v in inputs.items()
               if isinstance(v, str) and v.startswith("PENDING")]
    assert len(pending) >= 5
    assert "MAY NOT EXECUTE" in inputs["rule"]


def test_j_psi_endpoints_are_what_the_interval_claims():
    assert j_psi(ADMISSIBLE_RHO_LOW) == pytest.approx(0.05, abs=1e-6)
    assert j_psi(ADMISSIBLE_RHO_HIGH) == pytest.approx(0.20, abs=1e-6)
    assert j_psi(0.40) == pytest.approx(0.3032385898, abs=1e-9)
