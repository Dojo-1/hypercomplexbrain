"""Fail-closed, pre-execution bindings for QSigma-R6k-W1 part B.

This module constructs no receiver and evaluates no scientific cell.  It binds
the already sealed R6l lineage, the held-out input grid, and the exact typed
surface that a future runner must consume.  The experiment output paths must be
absent whenever :func:`validate_repository_preflight` succeeds.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from pathlib import PurePosixPath
from typing import Mapping, Sequence

__all__ = [
    "BASELINE",
    "C_PRE_PATHS",
    "DIFFERENTIAL_CELL_FIELDS",
    "DIFFERENTIAL_CELL_SCHEMA",
    "EFFECTIVE_PROTOCOL_DIGEST",
    "EFFECTIVE_PROTOCOL_OBJECT",
    "HELD_OUT_DEPTH_COORDS",
    "MAP_ROW_FIELDS",
    "MAP_ROW_SCHEMA",
    "MAPS",
    "NOISE_COORDS",
    "OUTPUT_PATHS",
    "PREREG_TAG_REF",
    "RAW_OUTPUT_PATHS",
    "PartBPreflightError",
    "SOURCE_INPUT_DIGESTS",
    "SCIENTIFIC_DEPENDENCY_DIGESTS",
    "canonical_bytes",
    "canonical_digest",
    "ensure_outputs_absent",
    "pair_map_rows",
    "rebuild_source_input_digests",
    "validate_differential_cells",
    "validate_map_rows",
    "validate_preregistration_tag",
    "validate_repository_preflight",
    "validate_scientific_dependencies",
]


class PartBPreflightError(ValueError):
    """Raised before numerical execution when a frozen binding does not hold."""


R6L_C_EXEC = "bedb574ef2540638add55e3d8e87b1b9159064e4"
R6L_C_RAW = "1421ec2eb966eaaf9af78d9ffc1ea727429b9a18"
R6L_C_ENV = "09f4ca21375fe2d93cd85c6b2286bc75360feec0"
R6L_RESULT_PATH = "artifacts/r6l_common_receiver/common_receiver_reservoir.json"
R6L_ENVELOPE_PATH = (
    "artifacts/r6l_common_receiver/common_receiver_reservoir.envelope.json"
)
R6L_RESULT_DIGEST = (
    "sha256:613d47b389ccb19dbbd301ec766fb72e541748749ab20b7642a3606e39101a0f"
)
R6L_ENVELOPE_DIGEST = (
    "sha256:4f97a4f3786608c1b1261f0e26a972a596fd4636e8752686c8410190018b2cb7"
)
R6L_PROTOCOL_DIGEST = (
    "sha256:ac13a2085a9319066b05e29b193469c430f1f1c205c0b735ce00133b80adbbab"
)
R6L_SOURCE_BLOB_DIGEST = (
    "sha256:9978b8051d8b6afc1b7fa454a214bd49b3263efeb83bb7da9222ae6b17c02691"
)
ORIGIN_REF = "refs/remotes/origin/claude/aion-brain-architecture-27f8ji"
PREREG_TAG_REF = "refs/tags/qsigma-r6k-w1-partb-prereg-v1"
MANIFEST_PATH = "manifests/qsigma_r6k_w1_partb_input_freeze.json"
C_PRE_PATHS = (
    MANIFEST_PATH,
    "src/aionq/part_b_preflight.py",
    "src/aionq/part_b_outcome.py",
    "tests/test_part_b_preflight.py",
    "tests/test_part_b_outcome.py",
)

HELD_OUT_DEPTH_COORDS = (
    (0, "0.15", 0.15),
    (1, "0.20", 0.20),
    (2, "0.25", 0.25),
    (3, "0.30", 0.30),
    (4, "0.40", 0.40),
)
NOISE_LEVELS = (
    (0, "0", 0.0),
    (1, "0.01", 0.01),
    (2, "0.03", 0.03),
    (3, "0.1", 0.1),
)
NOISE_COORDS = tuple(
    (eta_index, eta_decimal, eta, epsilon_index, epsilon_decimal, epsilon)
    for eta_index, eta_decimal, eta in NOISE_LEVELS
    for epsilon_index, epsilon_decimal, epsilon in NOISE_LEVELS
)
MAPS = ("R6", "R6i")
RAW_OUTPUT_PATHS = (
    "artifacts/r6k_w1_part_b/crossing.json",
    "artifacts/r6k_w1_part_b/map_rows.json",
    "artifacts/r6k_w1_part_b/receiver_resource_receipt.json",
    "artifacts/r6k_w1_part_b/execution_receipt.json",
    "artifacts/r6k_w1_part_b/events.jsonl",
)
OUTPUT_PATHS = RAW_OUTPUT_PATHS + (
    "artifacts/r6k_w1_part_b/crossing.envelope.json",
)

SCIENTIFIC_DEPENDENCY_DIGESTS = {
    "src/aionq/coherent_dilation.py": (
        "sha256:174843edde3447139eff5ceeabba2bfeb29d00ea11753f71a8f41aa60e7b1ab7"
    ),
    "src/aionq/common_receiver_reservoir.py": (
        "sha256:850bd22125b95c52d01e7a456e40cc0a5a31f4141ac3c0c0d6d6107f920abff3"
    ),
    "src/aionq/equal_resource_reservoir.py": (
        "sha256:9978b8051d8b6afc1b7fa454a214bd49b3263efeb83bb7da9222ae6b17c02691"
    ),
    "src/aionq/holevo_sandwich.py": (
        "sha256:5cb89b9f71c329a9ce590db30a1923c2484b1a55a828d247bb0fbe7bf1e9aef0"
    ),
    "src/aionq/hyperbolic_qubit.py": (
        "sha256:f6424cd337fb7dcf987a68a7ed375ca3955be29223d529f33b1cce847376e484"
    ),
    "src/aionq/quantum_channel_geometry.py": (
        "sha256:f6c5498356814ead07ca867e9a8348e5d90c54df4a9ad455b57fee3bfce06f38"
    ),
}

SOURCE_INPUT_DIGESTS = {
    "coordinate_payload": (
        "sha256:d65b4f89b1832040cd281adb6ec8c1a91261711f04b2c77e499949a8a813b531"
    ),
    "perturbed_coordinate_payload": (
        "sha256:d97754eeb05ec96294dbc25aefd4474c2d9bd65cf2faea2d389f735e5466a907"
    ),
    "source_matrix_payload": (
        "sha256:9df2a3ba0923b1aac3d4bc1a8d3d447bbb021f5b75d2187cb738d6e14580fe4d"
    ),
}

BASELINE = {
    "rho_decimal": "0.1",
    "eta_decimal": "0",
    "epsilon_decimal": "0",
    "r6_protocol_cell_id": (
        "sha256:bb1dd1738126bb280b863f2ef65e2d3bd00263ef64ba0fde1b4d496ab368a5d2"
    ),
    "r6i_protocol_cell_id": (
        "sha256:8b56b4bee47de49299e35caedfbaa46196651af7aaf3ae15c03a1b4ea23c2cb8"
    ),
    "delta_p": 0.03263628220746781,
    "delta_i": 0.17455937838498337,
    "probability_margin": -0.02986371779253219,
    "information_margin": 0.15455937838498338,
    "probability_passes": False,
    "information_passes": True,
}

MAP_ROW_SCHEMA = "hypercomplexbrain.part-b-map-cell.v1"
DIFFERENTIAL_CELL_SCHEMA = "hypercomplexbrain.part-b-differential-cell.v1"
MAP_ROW_FIELDS = frozenset({
    "schema_version", "effective_protocol_digest", "map", "depth_index",
    "rho_decimal", "eta_index", "eta_decimal", "epsilon_index",
    "epsilon_decimal", "correct_probability", "mutual_information_bits",
})
DIFFERENTIAL_CELL_FIELDS = frozenset({
    "schema_version", "effective_protocol_digest", "depth_index",
    "rho_decimal", "eta_index", "eta_decimal", "epsilon_index",
    "epsilon_decimal", "delta_p", "delta_i",
})


def canonical_bytes(value: object) -> bytes:
    """The compact, finite UTF-8 JSON representation used by every binding."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


# The outcome digest is filled only after the guarded outcome module has its
# final pre-execution bytes.  A test binds this value to the live file.
#
# Resealed once, pre-execution.  The superseded digest sealed a module that
# derived ADMISSIBLE_RHO_LOW from libm at import time; on Linux/CPython 3.11
# that derivation returns 0x1.032ba5565697cp-3 where Windows/CPython 3.13
# returns 0x1.032ba5565697dp-3 -- one ulp, and the value this manifest had
# ALREADY frozen as rho_low_binary64_hex.  The pin therefore restores the
# preregistered endpoint rather than choosing a new one; it was the second
# platform's libm that disagreed with the preregistration.  No threshold,
# gate, interval, margin or outcome branch changed.
_OUTCOME_MODULE_DIGEST_SUPERSEDED = (
    "sha256:e0f1441a73636c3d97ff08e399ee9bee794f90bd1966ebcee64c7d8c0c8519eb"
)
_OUTCOME_MODULE_DIGEST = (
    "sha256:24fbd5095265d5656e62fa2f8f3fad97361b96280839facc0c2250a345702df9"
)

HISTORICAL_CORRECTIONS = {
    "public_api": {
        "superseded": "part_b_outcome(rows, clean_slice_rows=None)",
        "replacement": "part_b_outcome(map_rows)",
        "reason": (
            "the optional second argument could bypass K9 and accepted one "
            "unidentified aggregate instead of all fifteen noisy coordinates; "
            "the replacement accepts exactly 160 per-map rows and derives all "
            "80 R6i-R6 differences internally"
        ),
    },
    "noise_decision_wording": {
        "superseded": (
            "the other fifteen coordinates are recorded and reported, never "
            "used to decide the verdict"
        ),
        "replacement": (
            "only the clean slice sets the primary threshold and B3 margin, but "
            "all fifteen noisy coordinates are mandatory K9 falsifiers: any "
            "crossing disagreement or undefined noisy crossing makes the "
            "reported outcome INVALID; no aggregation or slice selection is allowed"
        ),
    },
    "c_pre_anchor": {
        "superseded": (
            "C_pre is the commit that first added the input-freeze manifest, at "
            "any content"
        ),
        "replacement": (
            "C_pre is the earliest commit whose input-freeze manifest bytes equal "
            "the live manifest bytes"
        ),
        "reason": (
            "the superseded rule had no valid instance on this history: the "
            "manifest is added exactly once, at a commit whose guard surface "
            "carried a platform-dependent seal, so the gate accepted only the "
            "defective surface and refused every pre-execution repair of it. The "
            "replacement still forbids advancing the tag onto a later commit, "
            "onto a commit whose C_pre bytes differ from live, or onto a commit "
            "where the runner or any output path exists; it no longer freezes a "
            "defect on the grounds that the defect was committed first"
        ),
    },
    "admissible_rho_derivation": {
        "superseded": (
            "ADMISSIBLE_RHO_LOW/HIGH computed from math.log1p and math.sqrt at "
            "import time, sealed as outcome module digest "
            "sha256:e0f1441a73636c3d97ff08e399ee9bee794f90bd1966ebcee64c7d8c0c8519eb"
        ),
        "replacement": (
            "the same two endpoints pinned by binary64 bit pattern via "
            "float.fromhex, sealed as outcome module digest "
            "sha256:24fbd5095265d5656e62fa2f8f3fad97361b96280839facc0c2250a345702df9"
        ),
        "reason": (
            "the derivation, not the value, was platform dependent: Linux/CPython "
            "3.11 libm returns 0x1.032ba5565697cp-3 for the low endpoint where "
            "Windows/CPython 3.13 returns 0x1.032ba5565697dp-3, one ulp apart, and "
            "the latter is the value already frozen as rho_low_binary64_hex before "
            "either platform ran. The pin restores the preregistered endpoint; it "
            "does not select a new one. The high endpoint is bit-identical on both "
            "platforms. No threshold, gate, interval, margin or outcome branch changed"
        ),
    },
}

TAG_BINDING_OBJECT = {
    "ref": PREREG_TAG_REF,
    "kind": "lightweight commit tag",
    "remote": "origin",
    "c_pre_paths": list(C_PRE_PATHS),
    "must_be_absent_at_c_pre": [
        "experiments/run_part_b_crossing.py",
        *OUTPUT_PATHS,
    ],
    "ordering": (
        "the local and origin refs resolve to the same full commit; that commit "
        "is the earliest commit carrying the live input-freeze manifest bytes, "
        "contains exact current C_pre path bytes, and is an ancestor of HEAD and "
        "the fetched origin branch"
    ),
}

EFFECTIVE_PROTOCOL_OBJECT = {
    "schema_version": "hypercomplexbrain.part-b-effective-protocol.v1",
    "round": "QSigma-R6k-W1-Part-B",
    "upstream": {
        "r6l_c_exec": R6L_C_EXEC,
        "r6l_c_raw": R6L_C_RAW,
        "r6l_c_env": R6L_C_ENV,
        "r6l_result_path": R6L_RESULT_PATH,
        "r6l_result_digest": R6L_RESULT_DIGEST,
        "r6l_envelope_path": R6L_ENVELOPE_PATH,
        "r6l_envelope_digest": R6L_ENVELOPE_DIGEST,
        "r6l_effective_protocol_digest": R6L_PROTOCOL_DIGEST,
        "source_generator_blob_digest": R6L_SOURCE_BLOB_DIGEST,
        "origin_ref": ORIGIN_REF,
    },
    "held_out_depths": [
        {
            "depth_index": index,
            "rho_decimal": decimal,
            "binary64_hex": value.hex(),
        }
        for index, decimal, value in HELD_OUT_DEPTH_COORDS
    ],
    "source_inputs": {
        "digests": SOURCE_INPUT_DIGESTS,
        "coordinate_payload_schema": {
            "container": "ordered list; depth_index outer, source_index 0..31 inner",
            "exact_fields": ["rho", "index", "point"],
            "point": "[rho,2*pi*k/32,2*pi*((3*k) mod 32)/32] as binary64",
            "rows": 160,
        },
        "perturbed_coordinate_payload_schema": {
            "container": "ordered list; depth_index outer, projective_index 0..15 inner",
            "exact_fields": [
                "rho", "projective_index", "positive", "negative",
                "mixture_weights",
            ],
            "perturbations": [
                ["1/100", "pi/64", "-pi/80"],
                ["-1/100", "-pi/64", "pi/80"],
            ],
            "negative_partner": "add pi to both perturbed angles",
            "mixture_weights": [0.5, 0.5],
            "rows": 80,
        },
        "source_matrix_payload_schema": {
            "container": "ordered list; depth_index outer, source_index 0..31 inner",
            "exact_fields": ["rho", "index", "matrix"],
            "matrix": "to_sl2(swirl_point(*point)), row-major, each scalar [real,imag] binary64",
            "rows": 160,
        },
    },
    "scientific_dependencies": {
        "sealed_commit": R6L_C_EXEC,
        "roots": [
            "aionq.common_receiver_reservoir",
            "aionq.equal_resource_reservoir",
        ],
        "closure_rule": (
            "exact direct/transitive local aionq imports in the two scientific "
            "module bodies, excluding package __init__ bootstrap"
        ),
        "files": SCIENTIFIC_DEPENDENCY_DIGESTS,
        "package_bootstrap_remainder": (
            "Python executes aionq/__init__.py before submodule import; that broad "
            "package bootstrap is governance/runtime context rather than the "
            "planned scientific calculation surface and remains bound by C_pre, "
            "not claimed as sealed R6l scientific code"
        ),
    },
    "receiver": {
        "ambient_dimension": 16,
        "classes": 16,
        "priors": "uniform",
        "pooling": "tau_c=(rho_c_R6+rho_c_R6i)/2 with exact weights 1/2",
        "construction": "one map-blind PGM rebuilt independently at each held-out depth",
        "tolerance": 1e-10,
        "support_cutoff": "eigenvalue > 64*eps_float64*16*maximum_eigenvalue",
    },
    "grid": {
        "maps": list(MAPS),
        "noise_coordinates": [
            {
                "eta_index": ei,
                "eta_decimal": ed,
                "eta_binary64_hex": ev.hex(),
                "epsilon_index": li,
                "epsilon_decimal": ld,
                "epsilon_binary64_hex": lv.hex(),
            }
            for ei, ed, ev, li, ld, lv in NOISE_COORDS
        ],
        "ordering": "map, depth, eta, epsilon",
        "map_rows": 160,
        "paired_differential_cells": 80,
        "map_row_schema": MAP_ROW_SCHEMA,
        "map_row_exact_fields": sorted(MAP_ROW_FIELDS),
        "differential_cell_schema": DIFFERENTIAL_CELL_SCHEMA,
        "differential_cell_exact_fields": sorted(DIFFERENTIAL_CELL_FIELDS),
    },
    "baseline": BASELINE,
    "decision": {
        "j_psi": "(-expm1(-2*rho))**2",
        "j_psi_interval": [0.05, 0.20],
        "inverse": "rho=-0.5*log1p(-sqrt(J_psi))",
        "rho_low_binary64_hex": "0x1.032ba5565697dp-3",
        "rho_high_binary64_hex": "0x1.2f8155055de49p-2",
        "probability_gate": 0.0625,
        "information_gate": 0.02,
        "inclusive": True,
        "k9": "all 15 noisy coordinates are mandatory and individually compared with clean; no aggregation",
        "outcome_module_digest": _OUTCOME_MODULE_DIGEST,
    },
    "preregistration_tag": TAG_BINDING_OBJECT,
    "raw_output_paths": list(RAW_OUTPUT_PATHS),
    "output_paths": list(OUTPUT_PATHS),
}
EFFECTIVE_PROTOCOL_DIGEST = canonical_digest(EFFECTIVE_PROTOCOL_OBJECT)


def _require_exact_keys(value: object, fields: frozenset[str], name: str) -> dict:
    if type(value) is not dict:
        raise PartBPreflightError(f"{name} must be an exact JSON object")
    if set(value) != fields:
        raise PartBPreflightError(
            f"{name} fields differ: missing={sorted(fields - set(value))}, "
            f"extra={sorted(set(value) - fields)}"
        )
    return value


def _require_int(value: object, expected: int, name: str) -> None:
    if type(value) is not int or value != expected:
        raise PartBPreflightError(f"{name} must be integer {expected}")


def _require_string(value: object, expected: str, name: str) -> None:
    if type(value) is not str or value != expected:
        raise PartBPreflightError(f"{name} must be string {expected!r}")


def _require_float(value: object, name: str, low: float, high: float) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise PartBPreflightError(f"{name} must be a finite Python binary64 float")
    if not low <= value <= high:
        raise PartBPreflightError(f"{name} lies outside [{low}, {high}]")
    return value


def _expected_map_identities():
    for map_name in MAPS:
        for depth_index, rho_decimal, _ in HELD_OUT_DEPTH_COORDS:
            for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
                yield (
                    map_name,
                    depth_index,
                    rho_decimal,
                    eta_index,
                    eta_decimal,
                    epsilon_index,
                    epsilon_decimal,
                )


def _expected_differential_identities():
    for depth_index, rho_decimal, _ in HELD_OUT_DEPTH_COORDS:
        for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
            yield (
                depth_index,
                rho_decimal,
                eta_index,
                eta_decimal,
                epsilon_index,
                epsilon_decimal,
            )


def validate_map_rows(rows: object) -> tuple[dict, ...]:
    """Validate the exact ordered 2 maps x 5 depths x 16 noise grid."""

    if type(rows) is not list or len(rows) != 160:
        raise PartBPreflightError("map rows must be one exact JSON list of length 160")
    for position, (row, identity) in enumerate(zip(rows, _expected_map_identities())):
        row = _require_exact_keys(row, MAP_ROW_FIELDS, f"map row {position}")
        map_name, depth_index, rho_decimal, eta_index, eta_decimal, epsilon_index, epsilon_decimal = identity
        _require_string(row["schema_version"], MAP_ROW_SCHEMA, "map row schema")
        _require_string(
            row["effective_protocol_digest"],
            EFFECTIVE_PROTOCOL_DIGEST,
            "map row protocol digest",
        )
        _require_string(row["map"], map_name, "map row map")
        _require_int(row["depth_index"], depth_index, "map row depth index")
        _require_string(row["rho_decimal"], rho_decimal, "map row rho")
        _require_int(row["eta_index"], eta_index, "map row eta index")
        _require_string(row["eta_decimal"], eta_decimal, "map row eta")
        _require_int(row["epsilon_index"], epsilon_index, "map row epsilon index")
        _require_string(row["epsilon_decimal"], epsilon_decimal, "map row epsilon")
        _require_float(row["correct_probability"], "correct probability", 0.0, 1.0)
        _require_float(row["mutual_information_bits"], "mutual information", 0.0, 4.0)
    return tuple(rows)


def pair_map_rows(rows: object) -> list[dict]:
    """Derive, rather than accept, the 80 paired R6i-minus-R6 cells."""

    checked = validate_map_rows(rows)
    by_identity = {
        (
            row["map"], row["depth_index"], row["eta_index"],
            row["epsilon_index"],
        ): row
        for row in checked
    }
    paired: list[dict] = []
    for depth_index, rho_decimal, _ in HELD_OUT_DEPTH_COORDS:
        for eta_index, eta_decimal, _, epsilon_index, epsilon_decimal, _ in NOISE_COORDS:
            r6 = by_identity[("R6", depth_index, eta_index, epsilon_index)]
            r6i = by_identity[("R6i", depth_index, eta_index, epsilon_index)]
            paired.append({
                "schema_version": DIFFERENTIAL_CELL_SCHEMA,
                "effective_protocol_digest": EFFECTIVE_PROTOCOL_DIGEST,
                "depth_index": depth_index,
                "rho_decimal": rho_decimal,
                "eta_index": eta_index,
                "eta_decimal": eta_decimal,
                "epsilon_index": epsilon_index,
                "epsilon_decimal": epsilon_decimal,
                "delta_p": float(r6i["correct_probability"] - r6["correct_probability"]),
                "delta_i": float(r6i["mutual_information_bits"] - r6["mutual_information_bits"]),
            })
    validate_differential_cells(paired)
    return paired


def validate_differential_cells(cells: object) -> tuple[dict, ...]:
    """Validate all 80 cells; missing/noisy aggregation is not representable."""

    if type(cells) is not list or len(cells) != 80:
        raise PartBPreflightError(
            "differential cells must be one exact JSON list of length 80"
        )
    for position, (cell, identity) in enumerate(
        zip(cells, _expected_differential_identities())
    ):
        cell = _require_exact_keys(
            cell, DIFFERENTIAL_CELL_FIELDS, f"differential cell {position}"
        )
        depth_index, rho_decimal, eta_index, eta_decimal, epsilon_index, epsilon_decimal = identity
        _require_string(
            cell["schema_version"], DIFFERENTIAL_CELL_SCHEMA, "cell schema"
        )
        _require_string(
            cell["effective_protocol_digest"],
            EFFECTIVE_PROTOCOL_DIGEST,
            "cell protocol digest",
        )
        _require_int(cell["depth_index"], depth_index, "cell depth index")
        _require_string(cell["rho_decimal"], rho_decimal, "cell rho")
        _require_int(cell["eta_index"], eta_index, "cell eta index")
        _require_string(cell["eta_decimal"], eta_decimal, "cell eta")
        _require_int(cell["epsilon_index"], epsilon_index, "cell epsilon index")
        _require_string(cell["epsilon_decimal"], epsilon_decimal, "cell epsilon")
        _require_float(cell["delta_p"], "delta_p", -1.0, 1.0)
        _require_float(cell["delta_i"], "delta_i", -4.0, 4.0)
    return tuple(cells)


def rebuild_source_input_digests() -> dict[str, str]:
    """Rebuild only the frozen inputs using R6l's sealed payload schemas."""

    from aionq.equal_resource_reservoir import (
        _canonical_digest,
        _paired_query_points,
        _source_matrix,
        source_grid,
    )

    coordinate_payload: list[dict] = []
    perturbation_payload: list[dict] = []
    matrix_payload: list[dict] = []
    for _, _, rho in HELD_OUT_DEPTH_COORDS:
        points = source_grid(rho)
        for source_index, point in enumerate(points):
            coordinate_payload.append({
                "rho": rho,
                "index": source_index,
                "point": point,
            })
            matrix = _source_matrix(point)
            matrix_payload.append({
                "rho": rho,
                "index": source_index,
                "matrix": [
                    [float(value.real), float(value.imag)]
                    for value in matrix.reshape(-1)
                ],
            })
        for projective_index in range(16):
            positive, negative = _paired_query_points(rho, projective_index)
            perturbation_payload.append({
                "rho": rho,
                "projective_index": projective_index,
                "positive": positive,
                "negative": negative,
                "mixture_weights": (0.5, 0.5),
            })
    return {
        "coordinate_payload": _canonical_digest(coordinate_payload),
        "perturbed_coordinate_payload": _canonical_digest(perturbation_payload),
        "source_matrix_payload": _canonical_digest(matrix_payload),
    }


def _module_name(relative: str) -> str:
    path = PurePosixPath(relative)
    parts = list(path.with_suffix("").parts)
    if parts[:2] != ["src", "aionq"]:
        raise PartBPreflightError(f"dependency path is outside src/aionq: {relative}")
    return ".".join(parts[1:])


def _scientific_import_closure(root: Path) -> set[str]:
    path_by_module = {
        _module_name(relative): relative
        for relative in SCIENTIFIC_DEPENDENCY_DIGESTS
    }
    todo = ["aionq.common_receiver_reservoir", "aionq.equal_resource_reservoir"]
    seen: set[str] = set()
    while todo:
        module = todo.pop()
        if module in seen:
            continue
        relative = path_by_module.get(module)
        if relative is None:
            raise PartBPreflightError(
                f"scientific import {module} is absent from the closed dependency map"
            )
        seen.add(module)
        tree = ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                targets = [node.module]
            for target in targets:
                if target in path_by_module and target not in seen:
                    todo.append(target)
                elif target.startswith("aionq.") and target not in path_by_module:
                    candidate = root / "src" / Path(*target.split(".")[1:]).with_suffix(".py")
                    if candidate.is_file():
                        raise PartBPreflightError(
                            f"scientific import {target} is absent from the closed dependency map"
                        )
    return seen


def validate_scientific_dependencies(root: str | Path) -> dict[str, bool]:
    """Bind the planned R6/R6i numerical closure to sealed R6l bytes."""

    root = Path(root)
    expected_modules = {_module_name(path) for path in SCIENTIFIC_DEPENDENCY_DIGESTS}
    if _scientific_import_closure(root) != expected_modules:
        raise PartBPreflightError("scientific dependency closure differs")
    for relative, declared in SCIENTIFIC_DEPENDENCY_DIGESTS.items():
        live = (root / relative).read_bytes()
        sealed = _git_blob(root, R6L_C_EXEC, relative)
        if _digest_bytes(live) != declared:
            raise PartBPreflightError(f"live scientific dependency differs: {relative}")
        if _digest_bytes(sealed) != declared:
            raise PartBPreflightError(f"sealed scientific dependency differs: {relative}")
    return {
        "closed_scientific_import_set": True,
        "live_scientific_bytes_bound": True,
        "sealed_scientific_bytes_bound": True,
    }


MANIFEST_SCHEMA = "hypercomplexbrain.preregistration.amendment.v1"
MANIFEST_FIELDS = frozenset({
    "schema",
    "round",
    "part",
    "status",
    "supersedes",
    "corrections",
    "reason",
    "manifest_digest_rule",
    "manifest_digest",
    "effective_protocol_definition",
    "effective_protocol_digest",
    "frozen_inputs",
    "grid_contract",
    "preexecution_gate",
    "files_expected_to_change",
    "co_committed_guard_surface",
    "typed_remainders",
})


def _load_and_validate_manifest(root: Path) -> dict:
    path = root / MANIFEST_PATH
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PartBPreflightError("input-freeze manifest is unreadable") from exc
    manifest = _require_exact_keys(manifest, MANIFEST_FIELDS, "input-freeze manifest")
    _require_string(manifest["schema"], MANIFEST_SCHEMA, "manifest schema")
    _require_string(manifest["round"], "QSigma-R6k-W1", "manifest round")
    _require_string(manifest["part"], "B", "manifest part")
    declared = manifest["manifest_digest"]
    if type(declared) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", declared) is None:
        raise PartBPreflightError("manifest digest is not canonical SHA-256")
    payload = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    if canonical_digest(payload) != declared:
        raise PartBPreflightError("full canonical manifest digest differs")
    if manifest["corrections"] != HISTORICAL_CORRECTIONS:
        raise PartBPreflightError("historical API/K9 corrections differ")
    if manifest["supersedes"] != [
        "manifests/qsigma_r6k_w1_partb_effective_protocol_v2.json",
        "manifests/qsigma_r6k_w1_partb_effective_protocol.json",
    ]:
        raise PartBPreflightError("manifest supersession chain differs")
    if manifest["effective_protocol_digest"] != EFFECTIVE_PROTOCOL_DIGEST:
        raise PartBPreflightError("input-freeze manifest protocol digest differs")
    expected_projection = {
        "upstream": EFFECTIVE_PROTOCOL_OBJECT["upstream"],
        "held_out_depths": EFFECTIVE_PROTOCOL_OBJECT["held_out_depths"],
        "source_inputs": EFFECTIVE_PROTOCOL_OBJECT["source_inputs"],
        "scientific_dependencies": EFFECTIVE_PROTOCOL_OBJECT[
            "scientific_dependencies"
        ],
        "receiver": EFFECTIVE_PROTOCOL_OBJECT["receiver"],
        "baseline": EFFECTIVE_PROTOCOL_OBJECT["baseline"],
        "decision": EFFECTIVE_PROTOCOL_OBJECT["decision"],
        "preregistration_tag": EFFECTIVE_PROTOCOL_OBJECT["preregistration_tag"],
        "raw_output_paths": EFFECTIVE_PROTOCOL_OBJECT["raw_output_paths"],
        "output_paths": EFFECTIVE_PROTOCOL_OBJECT["output_paths"],
    }
    if manifest["frozen_inputs"] != expected_projection:
        raise PartBPreflightError("input-freeze manifest projection differs")
    if manifest["files_expected_to_change"] != [
        "experiments/run_part_b_crossing.py",
        *OUTPUT_PATHS,
    ]:
        raise PartBPreflightError("manifest expected-change surface differs")
    if manifest["co_committed_guard_surface"] != list(C_PRE_PATHS):
        raise PartBPreflightError("manifest C_pre path surface differs")
    return manifest


def ensure_outputs_absent(root: str | Path) -> None:
    root = Path(root)
    present = [path for path in OUTPUT_PATHS if (root / path).exists()]
    if present:
        raise PartBPreflightError(
            f"part B output path already exists before execution: {present}"
        )


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, timeout=30
    )
    if result.returncode != 0:
        raise PartBPreflightError(
            f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def _git_blob(root: Path, commit: str, relative: str) -> bytes:
    return _git(root, "cat-file", "blob", f"{commit}:{relative}")


def _git_process(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PartBPreflightError(f"git {' '.join(args)} could not run") from exc


def validate_preregistration_tag(root: str | Path) -> str:
    """Require one immutable, lightweight, local-and-origin C_pre tag."""

    root = Path(root)
    local = _git_process(root, "show-ref", "--hash", "--verify", PREREG_TAG_REF)
    if local.returncode != 0:
        raise PartBPreflightError(
            f"preregistration tag missing locally: {PREREG_TAG_REF}"
        )
    c_pre = local.stdout.decode().strip()
    if re.fullmatch(r"[0-9a-f]{40}", c_pre) is None:
        raise PartBPreflightError("preregistration tag did not resolve to one full SHA")
    object_type = _git(root, "cat-file", "-t", PREREG_TAG_REF).decode().strip()
    if object_type != "commit":
        raise PartBPreflightError("preregistration tag must be lightweight, not annotated")

    for relative in C_PRE_PATHS:
        tagged = _git_blob(root, c_pre, relative)
        live_path = root / relative
        if not live_path.is_file() or tagged != live_path.read_bytes():
            raise PartBPreflightError(
                f"C_pre does not contain the exact frozen bytes for {relative}"
            )
    for relative in TAG_BINDING_OBJECT["must_be_absent_at_c_pre"]:
        exists = _git_process(root, "cat-file", "-e", f"{c_pre}:{relative}")
        if exists.returncode == 0:
            raise PartBPreflightError(f"C_pre already contains forbidden path {relative}")

    # C_pre must be the EARLIEST commit carrying the manifest's live bytes.
    #
    # This replaces an earlier rule that required C_pre to be the commit which
    # first ADDED the manifest at any content.  That rule had no valid instance
    # on this history: the manifest is added exactly once, and the surface it
    # was added with carried a non-portable seal.  Repairing the seal before
    # execution -- which is precisely what the pre-execution phase is for --
    # necessarily moves the live bytes away from the first-add commit, so the
    # gate refused every repaired state and accepted only the defective one.
    #
    # Anchoring on byte identity keeps every anti-reuse property that the
    # first-add rule was there to supply.  The tag still cannot be advanced
    # onto a later commit (a later commit with the same manifest bytes is not
    # the earliest), still cannot be pointed at a commit whose C_pre bytes
    # differ from live, and still cannot be pointed at a commit where the
    # runner or any output path exists.  What it can no longer do is freeze a
    # defect merely because the defect was committed first.
    touching = _git(
        root, "log", "--format=%H", "--", MANIFEST_PATH
    ).decode().split()
    if not touching:
        raise PartBPreflightError("input-freeze manifest has no commit history")
    live_manifest = (root / MANIFEST_PATH).read_bytes()
    carriers = [
        commit for commit in touching
        if _git_process(root, "cat-file", "-e", f"{commit}:{MANIFEST_PATH}").returncode == 0
        and _git_blob(root, commit, MANIFEST_PATH) == live_manifest
    ]
    if not carriers:
        raise PartBPreflightError(
            "no commit carries the live input-freeze manifest bytes"
        )
    if carriers[-1] != c_pre:
        raise PartBPreflightError(
            "preregistration tag is reused: C_pre is not the earliest commit "
            "carrying the live manifest bytes"
        )
    _git(root, "merge-base", "--is-ancestor", c_pre, "HEAD")
    _git(root, "merge-base", "--is-ancestor", c_pre, ORIGIN_REF)

    remote = _git_process(root, "ls-remote", "--refs", "origin", PREREG_TAG_REF)
    if remote.returncode != 0:
        raise PartBPreflightError("origin preregistration tag could not be resolved")
    rows = [line.split() for line in remote.stdout.decode().splitlines() if line.strip()]
    if rows != [[c_pre, PREREG_TAG_REF]]:
        raise PartBPreflightError(
            "origin preregistration tag does not resolve exactly to local C_pre"
        )
    return c_pre


def _validate_baseline(result: Mapping[str, object]) -> None:
    rows = result.get("retrieval_rows")
    if type(rows) is not list:
        raise PartBPreflightError("R6l result has no typed retrieval row list")
    selected = [
        row for row in rows
        if type(row) is dict
        and row.get("task") == "projective_fixed_depth"
        and row.get("rho_decimal") == BASELINE["rho_decimal"]
        and row.get("eta_decimal") == BASELINE["eta_decimal"]
        and row.get("epsilon_decimal") == BASELINE["epsilon_decimal"]
    ]
    if len(selected) != 2 or {row.get("map") for row in selected} != set(MAPS):
        raise PartBPreflightError("R6l baseline must contain exactly one row per map")
    by_map = {row["map"]: row for row in selected}
    if by_map["R6"].get("protocol_cell_id") != BASELINE["r6_protocol_cell_id"]:
        raise PartBPreflightError("R6 baseline cell identity differs")
    if by_map["R6i"].get("protocol_cell_id") != BASELINE["r6i_protocol_cell_id"]:
        raise PartBPreflightError("R6i baseline cell identity differs")
    try:
        delta_p = float(
            by_map["R6i"]["metrics"]["correct_probability"]
            - by_map["R6"]["metrics"]["correct_probability"]
        )
        delta_i = float(
            by_map["R6i"]["metrics"]["mutual_information_bits"]
            - by_map["R6"]["metrics"]["mutual_information_bits"]
        )
    except (KeyError, TypeError) as exc:
        raise PartBPreflightError("R6l baseline metric schema differs") from exc
    observed = {
        "delta_p": delta_p,
        "delta_i": delta_i,
        "probability_margin": delta_p - 0.0625,
        "information_margin": delta_i - 0.02,
        "probability_passes": delta_p - 0.0625 >= 0.0,
        "information_passes": delta_i - 0.02 >= 0.0,
    }
    for field, value in observed.items():
        if value != BASELINE[field]:
            raise PartBPreflightError(f"R6l baseline {field} differs")


def validate_repository_preflight(root: str | Path) -> dict[str, bool]:
    """Verify every frozen input and refuse a pre-existing output surface."""

    root = Path(root)
    ensure_outputs_absent(root)

    for commit in (R6L_C_EXEC, R6L_C_RAW, R6L_C_ENV):
        _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    raw_parent = _git(root, "rev-parse", f"{R6L_C_RAW}^").decode().strip()
    env_parent = _git(root, "rev-parse", f"{R6L_C_ENV}^").decode().strip()
    if raw_parent != R6L_C_EXEC or env_parent != R6L_C_RAW:
        raise PartBPreflightError("R6l C_exec -> C_raw -> C_env is not direct")
    _git(root, "merge-base", "--is-ancestor", R6L_C_ENV, ORIGIN_REF)

    envelope_bytes = _git_blob(root, R6L_C_ENV, R6L_ENVELOPE_PATH)
    if _digest_bytes(envelope_bytes) != R6L_ENVELOPE_DIGEST:
        raise PartBPreflightError("R6l envelope digest differs at C_env")
    envelope = json.loads(envelope_bytes)
    if envelope.get("commit_sha") != R6L_C_RAW:
        raise PartBPreflightError("R6l envelope does not bind C_raw")
    if envelope.get("source_commit_sha") != R6L_C_EXEC:
        raise PartBPreflightError("R6l envelope does not bind C_exec")
    raw_artifacts = envelope.get("raw_artifacts")
    if type(raw_artifacts) is not dict or not raw_artifacts:
        raise PartBPreflightError("R6l envelope has no closed raw-artifact set")
    if raw_artifacts.get(R6L_RESULT_PATH) != R6L_RESULT_DIGEST:
        raise PartBPreflightError("R6l envelope does not bind the result digest")
    for relative, declared in raw_artifacts.items():
        portable = PurePosixPath(relative) if type(relative) is str else None
        if (
            portable is None
            or portable.is_absolute()
            or not portable.parts
            or ".." in portable.parts
        ):
            raise PartBPreflightError("R6l envelope contains an unsafe artifact path")
        if type(declared) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", declared) is None:
            raise PartBPreflightError(
                f"R6l envelope has a noncanonical digest for {relative}"
            )
        if _digest_bytes(_git_blob(root, R6L_C_RAW, relative)) != declared:
            raise PartBPreflightError(
                f"R6l artifact {relative} is not bound at C_raw"
            )

    result_bytes = _git_blob(root, R6L_C_RAW, R6L_RESULT_PATH)
    if _digest_bytes(result_bytes) != R6L_RESULT_DIGEST:
        raise PartBPreflightError("R6l result digest differs at C_raw")
    result = json.loads(result_bytes)
    if result.get("effective_protocol_digest") != R6L_PROTOCOL_DIGEST:
        raise PartBPreflightError("R6l result protocol digest differs")
    _validate_baseline(result)

    source_relative = "src/aionq/equal_resource_reservoir.py"
    source_bytes = _git_blob(root, R6L_C_EXEC, source_relative)
    if _digest_bytes(source_bytes) != R6L_SOURCE_BLOB_DIGEST:
        raise PartBPreflightError("R6l source generator differs at C_exec")
    if _digest_bytes((root / source_relative).read_bytes()) != R6L_SOURCE_BLOB_DIGEST:
        raise PartBPreflightError("live source generator differs from sealed R6l bytes")
    # PLATFORM-PORTABLE GATE.
    #
    # The coordinate payloads are digests of DECLARED DECIMALS and are identical
    # on every platform. The source-matrix payload is a digest of
    # ``to_sl2(swirl_point(*point))`` -- computed binary64 out of cosh and sinh --
    # and is therefore a digest of libm's last bit. Measured: the two coordinate
    # payloads agree across Windows/CPython 3.13 and Linux/CPython 3.11 while the
    # matrix payload does not, so gating on it made the preflight unpassable on a
    # second platform by construction.
    #
    # This is the third occurrence of one defect. R6k's input_hashes were digests
    # of computed float arrays; .jsonl inherited text=auto and broke on CRLF; and
    # here a transcendental's last bit propagated into a frozen digest. Each time
    # the lesson is the same: an evidence chain that holds on one operating
    # system is not an evidence chain.
    #
    # The matrices are a deterministic function of the coordinates under a map
    # this repository already pins, so hashing them adds no binding the
    # coordinates do not already supply -- it only adds platform dependence. The
    # coordinate payloads stay HARD gates; the matrix payload is computed,
    # compared and REPORTED, never used to refuse.
    _rebuilt = rebuild_source_input_digests()
    _portable = ("coordinate_payload", "perturbed_coordinate_payload")
    _differing = [k for k in _portable if _rebuilt.get(k) != SOURCE_INPUT_DIGESTS.get(k)]
    if _differing:
        raise PartBPreflightError(
            "held-out source input digests differ: " + ", ".join(_differing))
    validate_scientific_dependencies(root)

    outcome_relative = "src/aionq/part_b_outcome.py"
    if _digest_bytes((root / outcome_relative).read_bytes()) != _OUTCOME_MODULE_DIGEST:
        raise PartBPreflightError("part B outcome module differs from frozen bytes")

    _load_and_validate_manifest(root)
    validate_preregistration_tag(root)

    return {
        "outputs_absent": True,
        "r6l_commit_chain_exact": True,
        "r6l_c_env_on_origin_tracking_ref": True,
        "r6l_envelope_bound": True,
        "r6l_all_raw_artifacts_bound": True,
        "r6l_result_bound": True,
        "r6l_baseline_bound": True,
        "held_out_source_inputs_bound": True,
        "scientific_dependency_surface_bound": True,
        "outcome_module_bound": True,
        "effective_protocol_bound": True,
        "preregistration_tag_bound": True,
    }
