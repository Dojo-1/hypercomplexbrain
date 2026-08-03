"""Outcome semantics for the still-unexecuted QSigma-R6k-W1 part B."""

from __future__ import annotations

import copy
import json
import math
import struct

import pytest

from aionq.part_b_outcome import (
    ADMISSIBLE_RHO_HIGH,
    ADMISSIBLE_RHO_LOW,
    HELD_OUT_DEPTHS,
    INFORMATION_GATE,
    J_PSI_HIGH,
    J_PSI_LOW,
    OUTCOMES,
    PROBABILITY_GATE,
    PartBPreflightError,
    bracket_for,
    bracket_position,
    information_margin,
    j_psi,
    part_b_outcome,
    passes,
    probability_margin,
)
from aionq.part_b_preflight import (
    DIFFERENTIAL_CELL_SCHEMA,
    EFFECTIVE_PROTOCOL_DIGEST,
    HELD_OUT_DEPTH_COORDS,
    MAP_ROW_SCHEMA,
    MAPS,
    NOISE_COORDS,
    pair_map_rows,
)
from aionq.self_audit import repo_root

HISTORICAL_MANIFEST = "qsigma_r6k_w1_partb_effective_protocol_v2.json"
FREEZE_MANIFEST = "qsigma_r6k_w1_partb_input_freeze.json"


def _map_rows(
    first_pass,
    *,
    delta_i=0.05,
    delta_p_pass=0.10,
    delta_p_fail=0.01,
):
    rows = []
    for map_name in MAPS:
        for depth_index, rho_decimal, depth in HELD_OUT_DEPTH_COORDS:
            for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
                delta_p = (
                    delta_p_pass
                    if first_pass is not None and depth >= first_pass
                    else delta_p_fail
                )
                rows.append({
                    "schema_version": MAP_ROW_SCHEMA,
                    "effective_protocol_digest": EFFECTIVE_PROTOCOL_DIGEST,
                    "map": map_name,
                    "depth_index": depth_index,
                    "rho_decimal": rho_decimal,
                    "eta_index": eta_index,
                    "eta_decimal": eta_decimal,
                    "epsilon_index": epsilon_index,
                    "epsilon_decimal": epsilon_decimal,
                    "correct_probability": float(
                        0.20 + (delta_p if map_name == "R6i" else 0.0)
                    ),
                    "mutual_information_bits": float(
                        0.30 + (delta_i if map_name == "R6i" else 0.0)
                    ),
                })
    return rows


def _row(rows, depth, map_name="R6i", eta_index=0, epsilon_index=0):
    return next(
        row for row in rows
        if HELD_OUT_DEPTHS[row["depth_index"]] == depth
        and row["map"] == map_name
        and row["eta_index"] == eta_index
        and row["epsilon_index"] == epsilon_index
    )


def _set_delta(rows, depth, field, value, eta_index=0, epsilon_index=0):
    r6 = _row(rows, depth, "R6", eta_index, epsilon_index)
    r6i = _row(rows, depth, "R6i", eta_index, epsilon_index)
    r6i[field] = float(r6[field] + value)


def _set_noise_first(rows, eta_index, epsilon_index, first):
    for depth in HELD_OUT_DEPTHS:
        delta = 0.10 if first is not None and depth >= first else 0.01
        _set_delta(
            rows,
            depth,
            "correct_probability",
            delta,
            eta_index,
            epsilon_index,
        )


def _manifest(name):
    return json.loads(
        (repo_root() / "manifests" / name).read_text(encoding="utf-8")
    )


def test_the_gates_are_r6ls_and_inclusive():
    assert PROBABILITY_GATE == 0.0625
    assert INFORMATION_GATE == 0.02
    assert probability_margin(0.0625) == 0.0
    assert passes(0.0) is True
    assert passes(-1e-18) is False
    assert information_margin(0.02) == 0.0


def test_the_boundary_case_is_reachable_and_passes():
    assert part_b_outcome(
        _map_rows(0.20, delta_p_pass=1.0 / 16.0)
    )["outcome"] == "SUPPORTING"


def _ulp_distance(left: float, right: float) -> int:
    """Signed distance in representable binary64 steps.

    Both endpoints here are positive normals, so the monotone integer ordering
    of the raw bit pattern is the ordering of the values and the subtraction is
    exactly the number of representable numbers between them.
    """
    to_int = lambda value: struct.unpack("<q", struct.pack("<d", value))[0]
    return to_int(left) - to_int(right)


def test_primary_j_interval_defines_exact_inverse_endpoints():
    # The endpoints are PINNED by bit pattern, not recomputed, so this test
    # must not assert bit equality with the live libm -- that is the assertion
    # that made the suite pass on one operating system and fail on the next.
    #
    # Measured: Windows/CPython 3.13 libm returns 0x1.032ba5565697dp-3 for the
    # low endpoint and Linux/CPython 3.11 returns 0x1.032ba5565697cp-3, one ulp
    # apart. The pinned value is the former, which is also the value the
    # input-freeze manifest declared as rho_low_binary64_hex before either
    # platform ran, so the pin follows the preregistration rather than a host.
    #
    # What is actually required of the pin is that it is the correctly rounded
    # inverse to within the error any conforming libm may introduce. One ulp is
    # the tolerance; two would admit a genuinely wrong endpoint.
    assert abs(_ulp_distance(
        ADMISSIBLE_RHO_LOW, -0.5 * math.log1p(-math.sqrt(J_PSI_LOW)))) <= 1
    assert abs(_ulp_distance(
        ADMISSIBLE_RHO_HIGH, -0.5 * math.log1p(-math.sqrt(J_PSI_HIGH)))) <= 1
    assert ADMISSIBLE_RHO_LOW.hex() == "0x1.032ba5565697dp-3"
    assert ADMISSIBLE_RHO_HIGH.hex() == "0x1.2f8155055de49p-2"
    assert ADMISSIBLE_RHO_LOW != 0.126548
    assert ADMISSIBLE_RHO_HIGH != 0.296392
    assert j_psi(ADMISSIBLE_RHO_LOW) == pytest.approx(J_PSI_LOW, abs=1e-16)
    assert j_psi(ADMISSIBLE_RHO_HIGH) == pytest.approx(J_PSI_HIGH, abs=1e-16)


@pytest.mark.parametrize("bracket,expected", [
    ((0.10, 0.15), "straddling"),
    ((0.15, 0.20), "inside"),
    ((0.20, 0.25), "inside"),
    ((0.25, 0.30), "straddling"),
    ((0.30, 0.40), "outside"),
])
def test_bracket_positions_are_decided_in_primary_j_space(bracket, expected):
    assert bracket_position(bracket) == expected


def test_the_lowest_bracket_uses_the_bound_r6l_depth_as_its_floor():
    assert bracket_for(0.15) == (0.1, 0.15)


@pytest.mark.parametrize("first,expected", [
    (0.15, "INCONCLUSIVE"),
    (0.20, "SUPPORTING"),
    (0.25, "SUPPORTING"),
    (0.30, "INCONCLUSIVE"),
    (0.40, "REFUTED"),
    (None, "REFUTED"),
])
def test_first_passing_depth_decides(first, expected):
    assert part_b_outcome(_map_rows(first))["outcome"] == expected


def test_clean_non_monotonicity_is_invalid():
    rows = _map_rows(0.20)
    _set_delta(rows, 0.30, "correct_probability", 0.01)
    result = part_b_outcome(rows)
    assert result["outcome"] == "INVALID"
    assert "non-monotone" in result["reason"]


def test_b3_failure_has_a_frozen_refuted_outcome():
    rows = _map_rows(0.20)
    _set_delta(rows, 0.25, "mutual_information_bits", 0.001)
    result = part_b_outcome(rows)
    assert result["outcome"] == "REFUTED"
    assert result["reason"].startswith("B3")


def test_one_of_fifteen_noisy_crossing_disagreements_fires_k9():
    rows = _map_rows(0.20)
    _set_noise_first(rows, 3, 3, 0.30)
    result = part_b_outcome(rows)
    assert result["outcome"] == "INVALID"
    assert "K9" in result["reason"]
    assert result["disagreements"] == {"eta=0.1,epsilon=0.1": 0.30}


def test_noisy_coordinates_are_not_aggregated_or_voted():
    rows = _map_rows(0.20)
    # Fourteen agree; one disagrees. A majority or mean would erase the one.
    _set_noise_first(rows, 0, 1, 0.25)
    assert part_b_outcome(rows)["outcome"] == "INVALID"


def test_a_non_monotone_noisy_coordinate_has_no_crossing():
    rows = _map_rows(0.20)
    _set_delta(rows, 0.30, "correct_probability", 0.01, 2, 1)
    result = part_b_outcome(rows)
    assert result["outcome"] == "INVALID"
    assert "K9" in result["reason"]
    assert "no single crossing" in result["reason"]


def test_all_fifteen_agreeing_noisy_coordinates_do_not_fire_k9():
    assert part_b_outcome(_map_rows(0.20))["outcome"] == "SUPPORTING"


@pytest.mark.parametrize("mutation", [
    "missing_cell",
    "extra_cell",
    "extra_field",
    "missing_field",
    "wrong_protocol",
    "bool_identity",
    "string_value",
    "integer_value",
    "nan_value",
    "positive_infinity",
    "negative_infinity",
])
def test_malformed_or_incomplete_inputs_raise_before_scientific_classification(mutation):
    rows = _map_rows(0.20)
    if mutation == "missing_cell":
        rows.pop()
    elif mutation == "extra_cell":
        rows.append(copy.deepcopy(rows[-1]))
    elif mutation == "extra_field":
        rows[0]["after_the_fact"] = True
    elif mutation == "missing_field":
        del rows[0]["mutual_information_bits"]
    elif mutation == "wrong_protocol":
        rows[0]["effective_protocol_digest"] = "sha256:" + "0" * 64
    elif mutation == "bool_identity":
        rows[0]["depth_index"] = False
    elif mutation == "string_value":
        rows[0]["correct_probability"] = "0.1"
    elif mutation == "integer_value":
        rows[0]["correct_probability"] = 1
    elif mutation == "nan_value":
        rows[0]["correct_probability"] = float("nan")
    elif mutation == "positive_infinity":
        rows[0]["mutual_information_bits"] = float("inf")
    elif mutation == "negative_infinity":
        rows[0]["mutual_information_bits"] = float("-inf")
    with pytest.raises(PartBPreflightError):
        part_b_outcome(rows)


def test_k9_cannot_be_omitted_with_an_optional_argument():
    with pytest.raises(TypeError):
        part_b_outcome()  # type: ignore[call-arg]
    with pytest.raises(PartBPreflightError):
        part_b_outcome([])


def test_public_outcome_refuses_precomputed_differential_cells():
    differential = pair_map_rows(_map_rows(0.20))
    assert len(differential) == 80
    assert differential[0]["schema_version"] == DIFFERENTIAL_CELL_SCHEMA
    with pytest.raises(PartBPreflightError, match="map rows"):
        part_b_outcome(differential)


def test_every_scientific_branch_states_a_reason():
    cases = [_map_rows(first) for first in (0.15, 0.20, 0.25, 0.30, 0.40, None)]
    broken = _map_rows(0.20)
    _set_delta(broken, 0.30, "correct_probability", 0.01)
    starved = _map_rows(0.20)
    _set_delta(starved, 0.25, "mutual_information_bits", 0.0)
    noisy = _map_rows(0.20)
    _set_noise_first(noisy, 1, 1, 0.30)
    cases += [broken, starved, noisy]
    for cells in cases:
        result = part_b_outcome(cells)
        assert result["outcome"] in OUTCOMES
        assert result.get("reason")


def test_historical_table_and_guarded_function_still_agree():
    table = _manifest(HISTORICAL_MANIFEST)[
        "expected_classification_by_first_passing_depth"
    ]
    for first in HELD_OUT_DEPTHS:
        assert table[f"{first:.2f}"] == part_b_outcome(_map_rows(first))["outcome"]
    assert table["none through 0.40"] == part_b_outcome(_map_rows(None))["outcome"]


def test_input_freeze_supersedes_the_historical_pending_fields():
    historical = _manifest(HISTORICAL_MANIFEST)
    assert any(
        isinstance(value, str) and value.startswith("PENDING")
        for value in historical[
            "measurement_inputs_that_must_be_frozen_before_execution"
        ].values()
    )
    frozen = _manifest(FREEZE_MANIFEST)
    # The single-string ``supersedes_pending_inputs_from`` became an ordered
    # ``supersedes`` chain, newest superseded document first, when the second
    # historical protocol was folded in. The chain must still name the document
    # carrying the PENDING fields, and must name it as the most recent one it
    # supersedes -- a chain that merely mentions it somewhere would let a later
    # document quietly re-open the frozen inputs.
    assert frozen["supersedes"][0].endswith(HISTORICAL_MANIFEST)
    assert "PENDING" not in json.dumps(frozen, sort_keys=True)


def test_j_psi_at_point_four_retains_the_correct_value():
    assert j_psi(0.40) == pytest.approx(0.3032385898, abs=1e-9)
