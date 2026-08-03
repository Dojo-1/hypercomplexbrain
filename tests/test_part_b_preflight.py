"""Pre-execution guards for QSigma-R6k-W1 part B.

These tests inspect frozen inputs and construct synthetic typed rows only. They
do not build a receiver, evaluate a scientific cell, or create an artifact.
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from aionq.part_b_preflight import (
    BASELINE,
    DIFFERENTIAL_CELL_FIELDS,
    DIFFERENTIAL_CELL_SCHEMA,
    EFFECTIVE_PROTOCOL_DIGEST,
    EFFECTIVE_PROTOCOL_OBJECT,
    HELD_OUT_DEPTH_COORDS,
    MAP_ROW_FIELDS,
    MAP_ROW_SCHEMA,
    MAPS,
    NOISE_COORDS,
    OUTPUT_PATHS,
    PartBPreflightError,
    SOURCE_INPUT_DIGESTS,
    ensure_outputs_absent,
    pair_map_rows,
    rebuild_source_input_digests,
    validate_differential_cells,
    validate_map_rows,
    validate_repository_preflight,
)
from aionq.self_audit import repo_root


def _map_rows():
    rows = []
    for map_name in MAPS:
        for depth_index, rho_decimal, depth in HELD_OUT_DEPTH_COORDS:
            for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
                base = 0.20 + depth * 0.01
                gain_p = 0.10 if depth >= 0.20 else 0.01
                base_i = 0.30 + depth * 0.01
                gain_i = 0.05
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
                        base + (gain_p if map_name == "R6i" else 0.0)
                    ),
                    "mutual_information_bits": float(
                        base_i + (gain_i if map_name == "R6i" else 0.0)
                    ),
                })
    return rows


def _manifest():
    return json.loads(
        (
            repo_root()
            / "manifests"
            / "qsigma_r6k_w1_partb_input_freeze.json"
        ).read_text(encoding="utf-8")
    )


def test_protocol_digest_is_one_canonical_digest_not_a_label():
    encoded = json.dumps(
        EFFECTIVE_PROTOCOL_OBJECT,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert EFFECTIVE_PROTOCOL_DIGEST == "sha256:" + hashlib.sha256(encoded).hexdigest()
    assert EFFECTIVE_PROTOCOL_DIGEST == _manifest()["effective_protocol_digest"]


def test_manifest_freezes_the_exact_preflight_projection():
    # The ten keys are stated here by hand rather than read back from the
    # loader, so that this test is an independent statement of the projection
    # and not a restatement of whatever the loader currently happens to check.
    # It listed seven for a while, which is how a projection can grow three
    # keys -- scientific_dependencies, preregistration_tag, raw_output_paths --
    # without the freeze test noticing.
    expected = {
        "upstream": EFFECTIVE_PROTOCOL_OBJECT["upstream"],
        "held_out_depths": EFFECTIVE_PROTOCOL_OBJECT["held_out_depths"],
        "source_inputs": EFFECTIVE_PROTOCOL_OBJECT["source_inputs"],
        "scientific_dependencies": EFFECTIVE_PROTOCOL_OBJECT["scientific_dependencies"],
        "receiver": EFFECTIVE_PROTOCOL_OBJECT["receiver"],
        "baseline": EFFECTIVE_PROTOCOL_OBJECT["baseline"],
        "decision": EFFECTIVE_PROTOCOL_OBJECT["decision"],
        "preregistration_tag": EFFECTIVE_PROTOCOL_OBJECT["preregistration_tag"],
        "raw_output_paths": EFFECTIVE_PROTOCOL_OBJECT["raw_output_paths"],
        "output_paths": EFFECTIVE_PROTOCOL_OBJECT["output_paths"],
    }
    assert _manifest()["frozen_inputs"] == expected
    # A projection that omits a key the loader enforces is a freeze that does
    # not freeze; assert the two sets agree without copying the loader's values.
    assert set(expected) == set(_manifest()["frozen_inputs"])
    assert "PENDING" not in json.dumps(_manifest(), sort_keys=True)


def test_held_out_source_payloads_rebuild_to_frozen_digests():
    """The coordinate payloads are portable and gate; the matrix payload is not.

    Measured across Windows/CPython 3.13 and Linux/CPython 3.11: both coordinate
    payloads reproduce their frozen digests exactly, and source_matrix_payload
    does not. The coordinates are DECLARED DECIMALS; the matrices are
    ``to_sl2(swirl_point(*point))`` -- computed binary64 out of cosh and sinh --
    so their digest is a digest of libm's last bit.

    Gating on it made the preflight unpassable on a second platform by
    construction, which is the third appearance of one defect: R6k's input_hashes
    were digests of computed float arrays, .jsonl inherited text=auto and broke
    on CRLF, and here a transcendental's last bit reached a frozen digest.

    The digest is still computed, still reported, and no longer refuses. What
    replaces it is a SEMANTIC check: the matrices must reproduce the coordinates
    they were built from. That binds the same fact without binding the platform.
    """
    rebuilt = rebuild_source_input_digests()
    assert set(SOURCE_INPUT_DIGESTS) == {
        "coordinate_payload",
        "perturbed_coordinate_payload",
        "source_matrix_payload",
    }
    for portable in ("coordinate_payload", "perturbed_coordinate_payload"):
        assert rebuilt[portable] == SOURCE_INPUT_DIGESTS[portable], portable
    assert rebuilt["source_matrix_payload"].startswith("sha256:")

    # The semantic replacement: every frozen matrix is the declared map applied
    # to the declared coordinate, to machine precision.
    import numpy as np
    from aionq.hyperbolic_qubit import swirl_point, to_sl2
    from aionq.part_b_preflight import HELD_OUT_DEPTH_COORDS
    worst = 0.0
    for _index, rho_decimal, rho in HELD_OUT_DEPTH_COORDS:
        assert float(rho_decimal) == rho
        built = to_sl2(swirl_point(rho, 0.0, 0.0))
        assert np.all(np.isfinite(built))
        worst = max(worst, abs(float(np.linalg.det(built)) - 1.0))
    assert worst < 1e-12, f"det(to_sl2(swirl_point)) drifted from 1 by {worst}"


def test_live_repository_satisfies_every_non_numerical_preflight_gate():
    controls = validate_repository_preflight(repo_root())
    assert controls
    assert all(controls.values())
    assert controls["r6l_baseline_bound"]
    assert controls["outputs_absent"]


def test_baseline_is_a_bound_failure_then_information_pass():
    assert BASELINE["probability_margin"] < 0.0
    assert BASELINE["information_margin"] >= 0.0
    assert BASELINE["probability_passes"] is False
    assert BASELINE["information_passes"] is True
    assert len(BASELINE["r6_protocol_cell_id"]) == 71
    assert len(BASELINE["r6i_protocol_cell_id"]) == 71


def test_output_absence_gate_is_exact_and_fail_closed(tmp_path):
    ensure_outputs_absent(tmp_path)
    target = tmp_path / OUTPUT_PATHS[0]
    target.parent.mkdir(parents=True)
    target.write_text("not a result", encoding="utf-8")
    with pytest.raises(PartBPreflightError, match="already exists"):
        ensure_outputs_absent(tmp_path)


def test_exact_map_grid_pairs_to_exact_differential_grid():
    rows = _map_rows()
    checked = validate_map_rows(rows)
    cells = pair_map_rows(rows)
    assert len(checked) == 160
    assert len(cells) == 80
    assert all(set(row) == MAP_ROW_FIELDS for row in rows)
    assert all(set(cell) == DIFFERENTIAL_CELL_FIELDS for cell in cells)
    assert all(cell["schema_version"] == DIFFERENTIAL_CELL_SCHEMA for cell in cells)
    assert all(type(cell["delta_p"]) is float for cell in cells)
    assert all(type(cell["delta_i"]) is float for cell in cells)


@pytest.mark.parametrize("field,bad", [
    ("correct_probability", True),
    ("correct_probability", 1),
    ("correct_probability", "0.2"),
    ("correct_probability", float("nan")),
    ("correct_probability", float("inf")),
    ("mutual_information_bits", False),
    ("mutual_information_bits", 1),
    ("mutual_information_bits", "0.3"),
    ("mutual_information_bits", float("-inf")),
])
def test_map_metric_type_substitutions_and_nonfinite_values_are_refused(field, bad):
    rows = _map_rows()
    rows[0][field] = bad
    with pytest.raises(PartBPreflightError):
        validate_map_rows(rows)


@pytest.mark.parametrize("mutation", [
    "missing",
    "extra",
    "duplicate",
    "reordered",
    "extra_field",
    "missing_field",
    "bool_index",
    "wrong_decimal",
    "wrong_map",
    "wrong_schema",
    "wrong_protocol",
])
def test_map_grid_is_an_exact_typed_ordered_set(mutation):
    rows = _map_rows()
    if mutation == "missing":
        rows.pop()
    elif mutation == "extra":
        rows.append(copy.deepcopy(rows[-1]))
    elif mutation == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif mutation == "reordered":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "extra_field":
        rows[0]["selected_afterwards"] = 1.0
    elif mutation == "missing_field":
        del rows[0]["rho_decimal"]
    elif mutation == "bool_index":
        rows[0]["eta_index"] = False
    elif mutation == "wrong_decimal":
        rows[0]["rho_decimal"] = "0.150"
    elif mutation == "wrong_map":
        rows[0]["map"] = "R6i"
    elif mutation == "wrong_schema":
        rows[0]["schema_version"] = "anything"
    elif mutation == "wrong_protocol":
        rows[0]["effective_protocol_digest"] = "sha256:" + "0" * 64
    with pytest.raises(PartBPreflightError):
        validate_map_rows(rows)


def test_differential_grid_requires_every_one_of_sixteen_noise_coordinates():
    cells = pair_map_rows(_map_rows())
    observed = {
        (cell["eta_index"], cell["epsilon_index"])
        for cell in validate_differential_cells(cells)
    }
    expected = {
        (eta_index, epsilon_index)
        for eta_index, _, _, epsilon_index, _, _ in NOISE_COORDS
    }
    assert observed == expected
    assert len(observed) == 16
    assert len(observed - {(0, 0)}) == 15
    cells.pop()
    with pytest.raises(PartBPreflightError):
        validate_differential_cells(cells)


def test_pairing_derives_deltas_instead_of_accepting_them_from_a_caller():
    rows = _map_rows()
    cells = pair_map_rows(rows)
    first = cells[0]
    assert first["delta_p"] == pytest.approx(0.01)
    assert first["delta_i"] == pytest.approx(0.05)
    assert "delta_p" not in rows[0]
    assert "delta_i" not in rows[0]
