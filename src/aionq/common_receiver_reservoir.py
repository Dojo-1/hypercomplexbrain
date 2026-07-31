"""QSigma-R6l map-blind common-receiver retrieval kernel.

The frozen protocol has a scalar planning layer and a numerical execution
layer.  Planning constructs portable store, receiver, and evaluation identities
before NumPy or the sealed R6k encoders are invoked.  Execution then glues the
R6 and R6i task fibers through one classwise pooled PGM per task.  The module
does not perform Git or filesystem evidence lifecycle operations; those belong
to ``experiments/run_common_receiver_reservoir.py``.

This is deterministic finite-grid associative retrieval.  It is not temporal
reservoir computing, a hardware experiment, a quantum-advantage result, or a
claim about cognition, consciousness, sentience, or AGI.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from aionq.coherent_dilation import density_state_diagnostics
from aionq.equal_resource_reservoir import (
    AMBIENT_DIM,
    CODEWORDS_PER_DEPTH,
    DEPTHS,
    PGMReceiver,
    ReservoirRecord,
    TaskEnsemble,
    build_map_tasks,
    build_pgm_receiver,
    depolarize,
)

__all__ = [
    "C_PRE_SHA",
    "EFFECTIVE_PROTOCOL_DIGEST",
    "LABEL_NOISE_STRENGTHS",
    "MANIFEST_SHA256",
    "PROVENANCE_CONTROL_NAMES",
    "SCIENTIFIC_CONTROL_NAMES",
    "STATE_NOISE_STRENGTHS",
    "CellSpec",
    "CommonReceiverBundle",
    "HashChainedEventLedger",
    "ProtocolPlan",
    "ProtocolRun",
    "ReceiverSpec",
    "StoreSpec",
    "apply_label_channel",
    "build_common_receiver_bundle",
    "build_label_channel",
    "canonical_bytes",
    "canonical_digest",
    "classify_protocol",
    "complex_array_record",
    "execute_protocol",
    "plan_protocol",
    "protocol_cell_id",
    "protocol_receiver_id",
    "protocol_store_id",
    "real_array_record",
    "validate_event_chain",
    "validate_catalog_artifact",
    "validate_protocol_plan",
    "validate_result_grid",
]

C_PRE_SHA = "350d03796a4021bc01c1814e9b71269d1ab63f6d"
MANIFEST_SHA256 = (
    "sha256:af0470284c19d857f347a541be5e54c00cd536b62b875cacee6d25b864811bef"
)
EFFECTIVE_PROTOCOL_DIGEST = (
    "sha256:ac13a2085a9319066b05e29b193469c430f1f1c205c0b735ce00133b80adbbab"
)
TOL = 1e-10
STATE_NOISE_STRENGTHS = (0.0, 0.01, 0.03, 0.1)
LABEL_NOISE_STRENGTHS = (0.0, 0.01, 0.03, 0.1)
DEPTH_COORDS = (
    ("0.1", 0.1),
    ("0.5", 0.5),
    ("1.0", 1.0),
    ("2.0", 2.0),
    ("4.0", 4.0),
)
NOISE_COORDS = (
    ("0", 0.0),
    ("0.01", 0.01),
    ("0.03", 0.03),
    ("0.1", 0.1),
)
MAPS = ("R6", "R6i")
GENESIS_DIGEST = "sha256:" + "0" * 64
PROVENANCE_CONTROL_NAMES = (
    "manifest_blob_matches_frozen_sha256",
    "freeze_receipt_matches_effective_protocol",
    "c_pre_is_remote_anchored",
    "c_exec_is_direct_manifest_descendant",
    "c_exec_has_exact_six_path_delta",
    "c_exec_tree_has_no_r6l_outputs",
    "clean_source_worktree",
    "exact_output_path_absent_before_run",
    "upstream_blobs_match_preregistration",
    "source_worktree_matches_c_exec_blobs",
    "r6l_event_path_has_exact_lf_attribute",
)
SCIENTIFIC_CONTROL_NAMES = (
    "portable_protocol_plan_valid",
    "source_matrices_byte_identical_between_maps",
    "source_coordinates_byte_identical_between_maps",
    "perturbed_coordinates_byte_identical_between_maps",
    "twelve_common_receivers_frozen",
    "all_receivers_and_naimark_controls_valid",
    "all_probability_rows_valid_without_repair",
    "exact_portable_result_grid",
    "exact_catalog_surface",
    "exact_event_chain",
    "event_keys_match_portable_plan",
    "ledger_root_is_final_event_digest",
)
SOURCE_BLOB_SHA256 = (
    "sha256:9978b8051d8b6afc1b7fa454a214bd49b3263efeb83bb7da9222ae6b17c02691"
)

_CELL_FIELDS = frozenset({
    "schema_version", "effective_protocol_digest", "map", "receiver_index",
    "task", "depth_index", "rho_decimal", "classes", "eta_index",
    "eta_decimal", "epsilon_index", "epsilon_decimal",
})
_RECEIVER_FIELDS = frozenset({
    "schema_version", "effective_protocol_digest", "receiver_index", "task",
    "depth_index", "rho_decimal", "classes",
})
_STORE_FIELDS = frozenset({
    "schema_version", "effective_protocol_digest", "map", "depth_index",
    "rho_decimal", "source_index",
})
_BINDING_FIELDS = (
    "clean_map_template_digest",
    "pooled_template_digest",
    "common_receiver_digest",
    "perturbed_query_digest",
    "state_noised_query_digest",
    "pre_label_probability_digest",
    "post_label_probability_digest",
    "state_channel_digest",
    "receiver_label_channel_digest",
    "receiver_label_matrix_digest",
    "structural_receiver_cost_digest",
    "prior_and_perturbation_definition_digest",
)
_METRIC_FIELDS = (
    "correct_probability",
    "mutual_information_bits",
    "mean_reject_probability",
    "conditional_correct_probability_given_nonreject",
    "minimum_pre_label_probability",
    "maximum_pre_label_probability",
    "minimum_post_label_probability",
    "maximum_post_label_probability",
    "maximum_pre_label_row_sum_defect",
    "maximum_post_label_row_sum_defect",
    "maximum_pre_label_imaginary_residual",
    "maximum_post_label_imaginary_residual",
)


def canonical_bytes(value: object) -> bytes:
    """Compact finite UTF-8 JSON bytes used by every R6l digest."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _canonical_json_equal(first: object, second: object) -> bool:
    """Compare JSON values without Python's bool/int/float equality aliases."""

    try:
        return canonical_bytes(first) == canonical_bytes(second)
    except (TypeError, ValueError):
        return False


def _require_sha256(value: object, *, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise ValueError(f"{name} must be a canonical lowercase SHA-256 string")
    return value


def _require_int(value: object, *, name: str, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer in [{lower},{upper}]")
    return value


def _require_finite_array(value: np.ndarray) -> None:
    if not np.all(np.isfinite(np.real(value))) or not np.all(
        np.isfinite(np.imag(value))
    ):
        raise ValueError("array contains a nonfinite value")


def complex_array_record(array: np.ndarray, *, index: int, role: str) -> dict:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise TypeError("array-record index must be a nonnegative integer")
    if not isinstance(role, str) or not role:
        raise TypeError("array-record role must be a nonempty string")
    value = np.ascontiguousarray(np.asarray(array, dtype="<c16"))
    _require_finite_array(value)
    return {
        "index": index,
        "role": role,
        "shape": [int(item) for item in value.shape],
        "dtype": "<c16",
        "array_digest": "sha256:" + hashlib.sha256(value.tobytes()).hexdigest(),
    }


def real_array_record(array: np.ndarray, *, index: int, role: str) -> dict:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise TypeError("array-record index must be a nonnegative integer")
    if not isinstance(role, str) or not role:
        raise TypeError("array-record role must be a nonempty string")
    value = np.ascontiguousarray(np.asarray(array, dtype="<f8"))
    if not np.all(np.isfinite(value)):
        raise ValueError("array contains a nonfinite value")
    return {
        "index": index,
        "role": role,
        "shape": [int(item) for item in value.shape],
        "dtype": "<f8",
        "array_digest": "sha256:" + hashlib.sha256(value.tobytes()).hexdigest(),
    }


@dataclass(frozen=True)
class StoreSpec:
    map_name: str
    depth_index: int
    rho_decimal: str
    source_index: int
    identity: dict
    protocol_store_id: str


@dataclass(frozen=True)
class ReceiverSpec:
    receiver_index: int
    task: str
    depth_index: int | None
    rho_decimal: str | None
    depth: float | None
    classes: int
    identity: dict
    protocol_receiver_id: str


@dataclass(frozen=True)
class CellSpec:
    map_name: str
    receiver: ReceiverSpec
    eta_index: int
    eta_decimal: str
    eta: float
    epsilon_index: int
    epsilon_decimal: str
    epsilon: float
    identity: dict
    protocol_cell_id: str


@dataclass(frozen=True)
class ProtocolPlan:
    effective_protocol_digest: str
    stores: tuple[StoreSpec, ...]
    receivers: tuple[ReceiverSpec, ...]
    cells: tuple[CellSpec, ...]


def _receiver_rows() -> tuple[tuple[str, int | None, str | None, float | None, int], ...]:
    rows: list[tuple[str, int | None, str | None, float | None, int]] = []
    rows.extend(
        ("signed_fixed_depth", index, decimal, value, 32)
        for index, (decimal, value) in enumerate(DEPTH_COORDS)
    )
    rows.extend(
        ("projective_fixed_depth", index, decimal, value, 16)
        for index, (decimal, value) in enumerate(DEPTH_COORDS)
    )
    rows.append(("radial", None, None, None, 5))
    rows.append(("joint_depth_projective", None, None, None, 80))
    return tuple(rows)


def _receiver_object(
    receiver_index: int,
    task: str,
    depth_index: int | None,
    rho_decimal: str | None,
    classes: int,
    effective_protocol_digest: str,
) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-receiver.v1",
        "effective_protocol_digest": effective_protocol_digest,
        "receiver_index": receiver_index,
        "task": task,
        "depth_index": depth_index,
        "rho_decimal": rho_decimal,
        "classes": classes,
    }


def protocol_receiver_id(identity: Mapping[str, object]) -> str:
    if set(identity) != _RECEIVER_FIELDS:
        raise ValueError("receiver identity field set is not closed")
    if identity["schema_version"] != "hypercomplexbrain.r6l-receiver.v1":
        raise ValueError("receiver identity schema version differs")
    _require_sha256(
        identity["effective_protocol_digest"], name="effective protocol digest"
    )
    receiver_index = _require_int(
        identity["receiver_index"], name="receiver index", lower=0, upper=11
    )
    task, depth_index, rho_decimal, _depth, classes = _receiver_rows()[receiver_index]
    expected = _receiver_object(
        receiver_index,
        task,
        depth_index,
        rho_decimal,
        classes,
        str(identity["effective_protocol_digest"]),
    )
    if not _canonical_json_equal(dict(identity), expected):
        raise ValueError("receiver identity coordinates differ from the frozen row")
    return canonical_digest(dict(identity))


def _store_object(
    map_name: str,
    depth_index: int,
    rho_decimal: str,
    source_index: int,
    effective_protocol_digest: str,
) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-store.v1",
        "effective_protocol_digest": effective_protocol_digest,
        "map": map_name,
        "depth_index": depth_index,
        "rho_decimal": rho_decimal,
        "source_index": source_index,
    }


def protocol_store_id(identity: Mapping[str, object]) -> str:
    if set(identity) != _STORE_FIELDS:
        raise ValueError("store identity field set is not closed")
    if identity["schema_version"] != "hypercomplexbrain.r6l-store.v1":
        raise ValueError("store identity schema version differs")
    _require_sha256(
        identity["effective_protocol_digest"], name="effective protocol digest"
    )
    if identity["map"] not in MAPS:
        raise ValueError("store identity map differs from the frozen map set")
    depth_index = _require_int(
        identity["depth_index"], name="depth index", lower=0, upper=4
    )
    if identity["rho_decimal"] != DEPTH_COORDS[depth_index][0]:
        raise ValueError("store identity depth coordinates disagree")
    _require_int(identity["source_index"], name="source index", lower=0, upper=31)
    expected = _store_object(
        str(identity["map"]),
        depth_index,
        DEPTH_COORDS[depth_index][0],
        int(identity["source_index"]),
        str(identity["effective_protocol_digest"]),
    )
    if not _canonical_json_equal(dict(identity), expected):
        raise ValueError("store identity scalar types differ from the frozen row")
    return canonical_digest(dict(identity))


def _cell_object(
    map_name: str,
    receiver: ReceiverSpec,
    eta_index: int,
    eta_decimal: str,
    epsilon_index: int,
    epsilon_decimal: str,
    effective_protocol_digest: str,
) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-cell.v2",
        "effective_protocol_digest": effective_protocol_digest,
        "map": map_name,
        "receiver_index": receiver.receiver_index,
        "task": receiver.task,
        "depth_index": receiver.depth_index,
        "rho_decimal": receiver.rho_decimal,
        "classes": receiver.classes,
        "eta_index": eta_index,
        "eta_decimal": eta_decimal,
        "epsilon_index": epsilon_index,
        "epsilon_decimal": epsilon_decimal,
    }


def protocol_cell_id(identity: Mapping[str, object]) -> str:
    if set(identity) != _CELL_FIELDS:
        raise ValueError("cell identity field set is not closed")
    if identity["schema_version"] != "hypercomplexbrain.r6l-cell.v2":
        raise ValueError("cell identity schema version differs")
    _require_sha256(
        identity["effective_protocol_digest"], name="effective protocol digest"
    )
    if identity["map"] not in MAPS:
        raise ValueError("cell identity map differs from the frozen map set")
    receiver_index = _require_int(
        identity["receiver_index"], name="receiver index", lower=0, upper=11
    )
    task, depth_index, rho_decimal, _depth, classes = _receiver_rows()[receiver_index]
    eta_index = _require_int(
        identity["eta_index"], name="eta index", lower=0, upper=3
    )
    epsilon_index = _require_int(
        identity["epsilon_index"], name="epsilon index", lower=0, upper=3
    )
    if identity["eta_decimal"] != NOISE_COORDS[eta_index][0]:
        raise ValueError("cell state-noise coordinates disagree")
    if identity["epsilon_decimal"] != NOISE_COORDS[epsilon_index][0]:
        raise ValueError("cell label-noise coordinates disagree")
    expected = {
        "schema_version": "hypercomplexbrain.r6l-cell.v2",
        "effective_protocol_digest": str(identity["effective_protocol_digest"]),
        "map": str(identity["map"]),
        "receiver_index": receiver_index,
        "task": task,
        "depth_index": depth_index,
        "rho_decimal": rho_decimal,
        "classes": classes,
        "eta_index": eta_index,
        "eta_decimal": NOISE_COORDS[eta_index][0],
        "epsilon_index": epsilon_index,
        "epsilon_decimal": NOISE_COORDS[epsilon_index][0],
    }
    if not _canonical_json_equal(dict(identity), expected):
        raise ValueError("cell identity scalar types differ from the frozen row")
    return canonical_digest(dict(identity))


def plan_protocol(
    effective_protocol_digest: str = EFFECTIVE_PROTOCOL_DIGEST,
) -> ProtocolPlan:
    """Construct the full scalar protocol surface before numerical work."""

    _require_sha256(
        effective_protocol_digest, name="effective protocol digest"
    )
    receivers: list[ReceiverSpec] = []
    for receiver_index, row in enumerate(_receiver_rows()):
        task, depth_index, rho_decimal, depth, classes = row
        identity = _receiver_object(
            receiver_index,
            task,
            depth_index,
            rho_decimal,
            classes,
            effective_protocol_digest,
        )
        receivers.append(
            ReceiverSpec(
                receiver_index,
                task,
                depth_index,
                rho_decimal,
                depth,
                classes,
                identity,
                protocol_receiver_id(identity),
            )
        )

    stores: list[StoreSpec] = []
    for map_name in MAPS:
        for depth_index, (rho_decimal, _) in enumerate(DEPTH_COORDS):
            for source_index in range(CODEWORDS_PER_DEPTH):
                identity = _store_object(
                    map_name,
                    depth_index,
                    rho_decimal,
                    source_index,
                    effective_protocol_digest,
                )
                stores.append(
                    StoreSpec(
                        map_name,
                        depth_index,
                        rho_decimal,
                        source_index,
                        identity,
                        protocol_store_id(identity),
                    )
                )

    cells: list[CellSpec] = []
    for map_name in MAPS:
        for receiver in receivers:
            for eta_index, (eta_decimal, eta) in enumerate(NOISE_COORDS):
                for epsilon_index, (epsilon_decimal, epsilon) in enumerate(NOISE_COORDS):
                    identity = _cell_object(
                        map_name,
                        receiver,
                        eta_index,
                        eta_decimal,
                        epsilon_index,
                        epsilon_decimal,
                        effective_protocol_digest,
                    )
                    cells.append(
                        CellSpec(
                            map_name,
                            receiver,
                            eta_index,
                            eta_decimal,
                            eta,
                            epsilon_index,
                            epsilon_decimal,
                            epsilon,
                            identity,
                            protocol_cell_id(identity),
                        )
                    )
    plan = ProtocolPlan(
        effective_protocol_digest,
        tuple(stores),
        tuple(receivers),
        tuple(cells),
    )
    validation = validate_protocol_plan(plan)
    if not validation["valid"]:
        raise ValueError(f"invalid protocol plan: {validation['reasons']}")
    return plan


def validate_protocol_plan(plan: ProtocolPlan) -> dict:
    """Independently rebuild the scalar products and reject identity drift."""

    reasons: list[str] = []
    try:
        _require_sha256(
            plan.effective_protocol_digest, name="plan effective protocol digest"
        )
    except ValueError as exc:
        reasons.append(str(exc))
    # Reconstruct with loops deliberately separate from ``plan_protocol``.
    expected_store_keys = [
        (map_name, depth_index, rho_decimal, source_index)
        for map_name in MAPS
        for depth_index, (rho_decimal, _) in enumerate(DEPTH_COORDS)
        for source_index in range(CODEWORDS_PER_DEPTH)
    ]
    observed_store_keys = [
        (row.map_name, row.depth_index, row.rho_decimal, row.source_index)
        for row in plan.stores
    ]
    if not _canonical_json_equal(observed_store_keys, expected_store_keys):
        reasons.append("store ordering or coordinates differ from the frozen product")
    expected_receiver_rows = list(enumerate(_receiver_rows()))
    observed_receiver_rows = [
        (
            row.receiver_index,
            (row.task, row.depth_index, row.rho_decimal, row.depth, row.classes),
        )
        for row in plan.receivers
    ]
    if not _canonical_json_equal(observed_receiver_rows, expected_receiver_rows):
        reasons.append("receiver ordering differs from the frozen twelve rows")
    expected_cell_keys = [
        (map_name, receiver_index, eta_index, epsilon_index)
        for map_name in MAPS
        for receiver_index in range(12)
        for eta_index in range(4)
        for epsilon_index in range(4)
    ]
    observed_cell_keys = [
        (
            row.map_name,
            row.receiver.receiver_index,
            row.eta_index,
            row.epsilon_index,
        )
        for row in plan.cells
    ]
    if not _canonical_json_equal(observed_cell_keys, expected_cell_keys):
        reasons.append("cell ordering differs from the frozen Cartesian product")
    for row in plan.stores:
        try:
            if type(row) is not StoreSpec or type(row.identity) is not dict:
                raise TypeError("store plan row must be a typed StoreSpec with plain identity")
            expected_identity = _store_object(
                row.map_name,
                row.depth_index,
                row.rho_decimal,
                row.source_index,
                plan.effective_protocol_digest,
            )
            if not _canonical_json_equal(row.identity, expected_identity):
                raise ValueError("store identity does not bind its plan coordinates")
            _require_sha256(row.protocol_store_id, name="store plan ID")
            if row.protocol_store_id != protocol_store_id(row.identity):
                raise ValueError("store ID mismatch")
        except (TypeError, ValueError) as exc:
            reasons.append(str(exc))
    for row in plan.receivers:
        try:
            if type(row) is not ReceiverSpec or type(row.identity) is not dict:
                raise TypeError(
                    "receiver plan row must be a typed ReceiverSpec with plain identity"
                )
            expected_identity = _receiver_object(
                row.receiver_index,
                row.task,
                row.depth_index,
                row.rho_decimal,
                row.classes,
                plan.effective_protocol_digest,
            )
            if not _canonical_json_equal(row.identity, expected_identity):
                raise ValueError("receiver identity does not bind its plan coordinates")
            _require_sha256(row.protocol_receiver_id, name="receiver plan ID")
            if row.protocol_receiver_id != protocol_receiver_id(row.identity):
                raise ValueError("receiver ID mismatch")
        except (TypeError, ValueError) as exc:
            reasons.append(str(exc))
    for row in plan.cells:
        try:
            if type(row) is not CellSpec or type(row.identity) is not dict:
                raise TypeError("cell plan row must be a typed CellSpec with plain identity")
            if type(row.receiver) is not ReceiverSpec:
                raise TypeError("cell receiver fiber must be a typed ReceiverSpec")
            if (
                type(row.receiver.receiver_index) is not int
                or not 0 <= row.receiver.receiver_index < len(plan.receivers)
            ):
                raise ValueError("cell receiver index is outside the frozen plan")
            expected_receiver = plan.receivers[row.receiver.receiver_index]
            observed_receiver = (
                row.receiver.receiver_index,
                row.receiver.task,
                row.receiver.depth_index,
                row.receiver.rho_decimal,
                row.receiver.depth,
                row.receiver.classes,
                row.receiver.identity,
                row.receiver.protocol_receiver_id,
            )
            frozen_receiver = (
                expected_receiver.receiver_index,
                expected_receiver.task,
                expected_receiver.depth_index,
                expected_receiver.rho_decimal,
                expected_receiver.depth,
                expected_receiver.classes,
                expected_receiver.identity,
                expected_receiver.protocol_receiver_id,
            )
            if not _canonical_json_equal(observed_receiver, frozen_receiver):
                raise ValueError("cell receiver fiber differs from the frozen plan receiver")
            eta_index = _require_int(
                row.eta_index, name="cell eta index", lower=0, upper=3
            )
            epsilon_index = _require_int(
                row.epsilon_index, name="cell epsilon index", lower=0, upper=3
            )
            if type(row.eta) is not float or row.eta != NOISE_COORDS[eta_index][1]:
                raise ValueError("cell eta float differs from its portable eta coordinate")
            if (
                type(row.epsilon) is not float
                or row.epsilon != NOISE_COORDS[epsilon_index][1]
            ):
                raise ValueError(
                    "cell epsilon float differs from its portable epsilon coordinate"
                )
            expected_identity = _cell_object(
                row.map_name,
                row.receiver,
                row.eta_index,
                row.eta_decimal,
                row.epsilon_index,
                row.epsilon_decimal,
                plan.effective_protocol_digest,
            )
            if not _canonical_json_equal(row.identity, expected_identity):
                raise ValueError("cell identity does not bind its plan coordinates")
            _require_sha256(row.protocol_cell_id, name="cell plan ID")
            if row.protocol_cell_id != protocol_cell_id(row.identity):
                raise ValueError("cell ID mismatch")
        except (TypeError, ValueError) as exc:
            reasons.append(str(exc))
    counts = {
        "stores": len(plan.stores),
        "receivers": len(plan.receivers),
        "cells": len(plan.cells),
        "unique_store_ids": len({row.protocol_store_id for row in plan.stores}),
        "unique_receiver_ids": len({row.protocol_receiver_id for row in plan.receivers}),
        "unique_cell_ids": len({row.protocol_cell_id for row in plan.cells}),
        "unique_cell_objects": len({canonical_bytes(row.identity) for row in plan.cells}),
    }
    if counts != {
        "stores": 320,
        "receivers": 12,
        "cells": 384,
        "unique_store_ids": 320,
        "unique_receiver_ids": 12,
        "unique_cell_ids": 384,
        "unique_cell_objects": 384,
    }:
        reasons.append(f"protocol cardinalities differ: {counts}")
    return {"valid": not reasons, "reasons": reasons, **counts}


def _validated_density(state: np.ndarray) -> np.ndarray:
    value = np.asarray(state, dtype=complex)
    diagnostics = density_state_diagnostics(value, tol=TOL)
    if value.shape != (AMBIENT_DIM, AMBIENT_DIM) or not diagnostics.get("valid", False):
        raise ValueError(f"invalid D16 density state: {diagnostics}")
    return value


def _task_for_spec(tasks: Sequence[TaskEnsemble], spec: ReceiverSpec) -> TaskEnsemble:
    matches = [
        task for task in tasks
        if task.name == spec.task and task.depth == spec.depth
    ]
    if len(matches) != 1:
        raise ValueError(f"task sequence does not realize receiver {spec.receiver_index}")
    task = matches[0]
    if task.classes != spec.classes or len(task.queries) != spec.classes:
        raise ValueError("task class cardinality differs from receiver specification")
    return task


def _complex_items(
    arrays: Sequence[np.ndarray], role: str,
) -> list[dict]:
    return [
        complex_array_record(array, index=index, role=role)
        for index, array in enumerate(arrays)
    ]


def _array_aggregate(
    *,
    kind: str,
    protocol_receiver_id_value: str | None,
    map_name: str | None,
    items: Sequence[dict],
    extra: Mapping[str, object] | None = None,
) -> tuple[dict, str]:
    value: dict[str, object] = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": kind,
    }
    if protocol_receiver_id_value is not None:
        value["protocol_receiver_id"] = protocol_receiver_id_value
    value["map"] = map_name
    if extra:
        value.update(extra)
    value["items"] = list(items)
    return value, canonical_digest(value)


def _clean_template_aggregate(
    spec: ReceiverSpec, map_name: str, templates: Sequence[np.ndarray],
) -> tuple[dict, str]:
    return _array_aggregate(
        kind="clean_map_templates",
        protocol_receiver_id_value=spec.protocol_receiver_id,
        map_name=map_name,
        items=_complex_items(templates, "clean_template"),
    )


def _query_aggregate(
    spec: ReceiverSpec,
    map_name: str,
    queries: Sequence[np.ndarray],
    *,
    noised: bool,
    eta_index: int | None = None,
    eta_decimal: str | None = None,
) -> tuple[dict, str]:
    extra = None
    kind = "perturbed_queries"
    role = "clean_query"
    if noised:
        kind = "state_noised_queries"
        role = "state_noised_query"
        if eta_index is None or eta_decimal is None:
            raise ValueError("noised queries require eta coordinates")
        extra = {"eta_index": eta_index, "eta_decimal": eta_decimal}
    return _array_aggregate(
        kind=kind,
        protocol_receiver_id_value=spec.protocol_receiver_id,
        map_name=map_name,
        items=_complex_items(queries, role),
        extra=extra,
    )


def _principal_psd_sqrt(effect: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    original = np.asarray(effect, dtype=complex)
    if original.shape != (AMBIENT_DIM, AMBIENT_DIM):
        raise ValueError("effect must be D16")
    _require_finite_array(original)
    antihermitian = float(np.linalg.norm(original - original.conj().T, "fro"))
    if antihermitian > TOL:
        raise ValueError(f"effect is not Hermitian: residual={antihermitian}")
    hermitian = (original + original.conj().T) / 2.0
    values, vectors = np.linalg.eigh(hermitian)
    values = np.real(values)
    minimum = float(np.min(values))
    if minimum < -TOL:
        raise ValueError(f"effect eigenvalue {minimum} is below the frozen boundary")
    clamped = np.where(values < 0.0, 0.0, values)
    root = vectors @ np.diag(np.sqrt(clamped)) @ vectors.conj().T
    residual = float(np.linalg.norm(root @ root - original, "fro"))
    if residual > TOL:
        raise ValueError(f"effect square-root reconstruction failed: {residual}")
    return np.asarray(root, dtype=complex), residual, clamped


def _effect_rank(clamped_values: np.ndarray) -> int:
    values = np.asarray(clamped_values, dtype=float)
    if values.size == 0:
        return 0
    maximum = max(0.0, float(np.max(values)))
    if maximum == 0.0:
        return 0
    cutoff = 64.0 * np.finfo(np.float64).eps * AMBIENT_DIM * maximum
    return int(np.count_nonzero(values > cutoff))


def _prior_perturbation_object(spec: ReceiverSpec) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-prior-perturbation.v1",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "source_blob_sha256": SOURCE_BLOB_SHA256,
        "uniform_class_prior": {"numerator": 1, "denominator": spec.classes},
        "query_mixture_weights": [
            {"numerator": 1, "denominator": 2},
            {"numerator": 1, "denominator": 2},
        ],
        "perturbations_symbolic": [
            {"delta_rho": "1/100", "delta_phi": "pi/64", "delta_psi": "-pi/80"},
            {"delta_rho": "-1/100", "delta_phi": "-pi/64", "delta_psi": "pi/80"},
        ],
    }


@dataclass(frozen=True)
class CommonReceiverBundle:
    spec: ReceiverSpec
    tasks: Mapping[str, TaskEnsemble]
    pooled_templates: tuple[np.ndarray, ...]
    receiver: PGMReceiver
    square_roots: tuple[np.ndarray, ...]
    naimark_isometry: np.ndarray
    clean_template_objects: Mapping[str, dict]
    clean_template_digests: Mapping[str, str]
    query_objects: Mapping[str, dict]
    query_digests: Mapping[str, str]
    pooled_object: dict
    pooled_digest: str
    receiver_object: dict
    receiver_digest: str
    structural_object: dict
    structural_digest: str
    prior_object: dict
    prior_digest: str
    residuals: Mapping[str, float]
    effect_ranks: tuple[int, ...]
    support_rank: int
    outcome_dimension: int
    outcome_ancilla_qubits: int


def build_common_receiver_bundle(
    spec: ReceiverSpec,
    tasks_by_map: Mapping[str, Sequence[TaskEnsemble]],
) -> CommonReceiverBundle:
    """Glue the two map fibers with classwise equal-weight pooling in J=I16."""

    if set(tasks_by_map) != set(MAPS):
        raise ValueError("common receiver requires exactly the R6 and R6i fibers")
    tasks = {map_name: _task_for_spec(tasks_by_map[map_name], spec) for map_name in MAPS}
    pooled: list[np.ndarray] = []
    for index in range(spec.classes):
        first = _validated_density(tasks["R6"].templates[index])
        second = _validated_density(tasks["R6i"].templates[index])
        value = _validated_density(0.5 * first + 0.5 * second)
        if not np.array_equal(value, 0.5 * first + 0.5 * second):
            raise ValueError("pooling changed the exact classwise half sum")
        pooled.append(value)
    pooled_templates = tuple(pooled)
    receiver = build_pgm_receiver(pooled_templates, tol=TOL)
    effects = receiver.effects + (receiver.reject_effect,)
    roots: list[np.ndarray] = []
    reconstruction: list[float] = []
    ranks: list[int] = []
    for effect in effects:
        root, residual, values = _principal_psd_sqrt(effect)
        roots.append(root)
        reconstruction.append(residual)
        ranks.append(_effect_rank(values))
    outcomes = spec.classes + 1
    outcome_ancilla_qubits = int(math.ceil(math.log2(outcomes)))
    outcome_dimension = 1 << outcome_ancilla_qubits
    isometry = np.zeros((AMBIENT_DIM * outcome_dimension, AMBIENT_DIM), dtype=complex)
    for outcome_index, root in enumerate(roots):
        start = AMBIENT_DIM * outcome_index
        isometry[start:start + AMBIENT_DIM, :] = root
    isometry_residual = float(
        np.linalg.norm(
            isometry.conj().T @ isometry - np.eye(AMBIENT_DIM),
            2,
        )
    )
    if isometry_residual > TOL:
        raise ValueError(f"Naimark isometry failed: {isometry_residual}")

    clean_objects: dict[str, dict] = {}
    clean_digests: dict[str, str] = {}
    query_objects: dict[str, dict] = {}
    query_digests: dict[str, str] = {}
    for map_name in MAPS:
        clean_objects[map_name], clean_digests[map_name] = _clean_template_aggregate(
            spec, map_name, tasks[map_name].templates
        )
        query_objects[map_name], query_digests[map_name] = _query_aggregate(
            spec, map_name, tasks[map_name].queries, noised=False
        )
    pooled_object, pooled_digest = _array_aggregate(
        kind="pooled_templates",
        protocol_receiver_id_value=spec.protocol_receiver_id,
        map_name=None,
        items=_complex_items(pooled_templates, "pooled_template"),
    )
    receiver_items = _complex_items(receiver.effects, "class_effect")
    receiver_items.append(
        complex_array_record(receiver.reject_effect, index=spec.classes, role="reject_effect")
    )
    receiver_object, receiver_digest = _array_aggregate(
        kind="common_receiver_effects",
        protocol_receiver_id_value=spec.protocol_receiver_id,
        map_name=None,
        items=receiver_items,
    )
    structural_items = _complex_items(roots[:-1], "sqrt_class_effect")
    structural_items.append(
        complex_array_record(roots[-1], index=spec.classes, role="sqrt_reject_effect")
    )
    structural_items.append(
        complex_array_record(
            isometry,
            index=spec.classes + 1,
            role="naimark_isometry",
        )
    )
    structural_object = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": "structural_receiver_cost",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "signal_dimension": AMBIENT_DIM,
        "classes": spec.classes,
        "outcome_dimension": outcome_dimension,
        "signal_qubits": 4,
        "outcome_ancilla_qubits": outcome_ancilla_qubits,
        "total_qubits": 4 + outcome_ancilla_qubits,
        "effect_ranks": ranks,
        "items": structural_items,
    }
    structural_digest = canonical_digest(structural_object)
    prior_object = _prior_perturbation_object(spec)
    residuals = {
        "completeness_spectral": float(receiver.diagnostics["completeness_residual"]),
        "support_projector_spectral": float(
            receiver.diagnostics["support_projector_residual"]
        ),
        "isometry_spectral": isometry_residual,
        "maximum_effect_reconstruction_fro": max(reconstruction, default=0.0),
    }
    if not all(value <= TOL for value in residuals.values()):
        raise ValueError(f"receiver residual control failed: {residuals}")
    return CommonReceiverBundle(
        spec=spec,
        tasks=tasks,
        pooled_templates=pooled_templates,
        receiver=receiver,
        square_roots=tuple(roots),
        naimark_isometry=isometry,
        clean_template_objects=clean_objects,
        clean_template_digests=clean_digests,
        query_objects=query_objects,
        query_digests=query_digests,
        pooled_object=pooled_object,
        pooled_digest=pooled_digest,
        receiver_object=receiver_object,
        receiver_digest=receiver_digest,
        structural_object=structural_object,
        structural_digest=structural_digest,
        prior_object=prior_object,
        prior_digest=canonical_digest(prior_object),
        residuals=residuals,
        effect_ranks=tuple(ranks),
        support_rank=int(receiver.diagnostics["clean_mean_support_rank"]),
        outcome_dimension=outcome_dimension,
        outcome_ancilla_qubits=outcome_ancilla_qubits,
    )


def _state_channel_object(eta_index: int, eta_decimal: str) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-channel.v1",
        "kind": "global_depolarization",
        "dimension": AMBIENT_DIM,
        "eta_index": eta_index,
        "eta_decimal": eta_decimal,
        "definition": "(1-eta)*rho+eta*I/16",
    }


def _label_channel_object(spec: ReceiverSpec, epsilon_index: int, epsilon_decimal: str) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-channel.v1",
        "kind": "symmetric_class_label_confusion",
        "classes": spec.classes,
        "epsilon_index": epsilon_index,
        "epsilon_decimal": epsilon_decimal,
        "reject_rule": "fixed",
        "definition": "diag=1-epsilon;offdiag=epsilon/(C-1)",
    }


def build_label_channel(classes: int, epsilon: float) -> np.ndarray:
    """Return the frozen row-stochastic class-label channel with fixed reject."""

    if isinstance(classes, bool) or not isinstance(classes, int) or classes < 2:
        raise ValueError("classes must be an integer at least two")
    if not math.isfinite(epsilon) or not 0.0 <= epsilon <= 1.0:
        raise ValueError("epsilon must be finite and lie in [0,1]")
    matrix = np.zeros((classes + 1, classes + 1), dtype=float)
    off_diagonal = epsilon / (classes - 1)
    matrix[:classes, :classes] = off_diagonal
    np.fill_diagonal(matrix[:classes, :classes], 1.0 - epsilon)
    matrix[classes, classes] = 1.0
    if not np.all(np.isfinite(matrix)) or np.max(
        np.abs(np.sum(matrix, axis=1) - 1.0)
    ) > 1e-12:
        raise ValueError("label channel is not row stochastic")
    if (
        np.any(matrix[:classes, classes] != 0.0)
        or np.any(matrix[classes, :classes] != 0.0)
        or matrix[classes, classes] != 1.0
    ):
        raise ValueError("label channel does not fix reject")
    return matrix


def apply_label_channel(pre_label: np.ndarray, channel: np.ndarray) -> np.ndarray:
    source = np.asarray(pre_label)
    matrix = np.asarray(channel)
    if source.ndim != 2 or matrix.shape != (source.shape[1], source.shape[1]):
        raise ValueError("probability table and label channel shapes do not align")
    return source @ matrix


def _validate_probability_table(
    table: np.ndarray,
    *,
    expected_rows: int,
) -> tuple[np.ndarray, dict]:
    complex_value = np.asarray(table, dtype=complex)
    if complex_value.shape != (expected_rows, expected_rows + 1):
        raise ValueError("conditional table has the wrong shape")
    _require_finite_array(complex_value)
    real_value = np.real(complex_value)
    minimum = float(np.min(real_value))
    maximum = float(np.max(real_value))
    row_defect = float(np.max(np.abs(np.sum(real_value, axis=1) - 1.0)))
    imaginary = float(np.max(np.abs(np.imag(complex_value))))
    valid = bool(
        minimum >= -TOL
        and maximum <= 1.0 + TOL
        and row_defect <= TOL
        and imaginary <= TOL
    )
    diagnostics = {
        "minimum": minimum,
        "maximum": maximum,
        "row_sum_defect": row_defect,
        "imaginary_residual": imaginary,
        "valid": valid,
    }
    if not valid:
        raise ValueError(f"probability table failed without repair: {diagnostics}")
    return np.ascontiguousarray(real_value, dtype="<f8"), diagnostics


def _mutual_information(conditional: np.ndarray) -> float:
    count = conditional.shape[0]
    joint = conditional / count
    px = np.sum(joint, axis=1)
    py = np.sum(joint, axis=0)
    information = 0.0
    for input_index in range(count):
        for output_index in range(conditional.shape[1]):
            probability = float(joint[input_index, output_index])
            if (
                probability > 1e-15
                and px[input_index] > 1e-15
                and py[output_index] > 1e-15
            ):
                information += probability * math.log2(
                    probability / (px[input_index] * py[output_index])
                )
    return float(information)


def _evaluate_probability_tables(
    bundle: CommonReceiverBundle,
    queries: Sequence[np.ndarray],
    label_channel: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict, dict]:
    effects = bundle.receiver.effects + (bundle.receiver.reject_effect,)
    complex_pre = np.asarray([
        [np.einsum("ij,ji->", effect, query) for effect in effects]
        for query in queries
    ], dtype=complex)
    pre, pre_diagnostics = _validate_probability_table(
        complex_pre, expected_rows=bundle.spec.classes
    )
    complex_post = apply_label_channel(complex_pre, label_channel)
    post, post_diagnostics = _validate_probability_table(
        complex_post, expected_rows=bundle.spec.classes
    )
    correct = float(np.mean(np.diag(post[:, :bundle.spec.classes])))
    reject = float(np.mean(post[:, -1]))
    nonreject = 1.0 - reject
    conditional_correct = None if nonreject <= 1e-15 else float(correct / nonreject)
    metrics = {
        "correct_probability": correct,
        "mutual_information_bits": _mutual_information(post),
        "mean_reject_probability": reject,
        "conditional_correct_probability_given_nonreject": conditional_correct,
        "minimum_pre_label_probability": pre_diagnostics["minimum"],
        "maximum_pre_label_probability": pre_diagnostics["maximum"],
        "minimum_post_label_probability": post_diagnostics["minimum"],
        "maximum_post_label_probability": post_diagnostics["maximum"],
        "maximum_pre_label_row_sum_defect": pre_diagnostics["row_sum_defect"],
        "maximum_post_label_row_sum_defect": post_diagnostics["row_sum_defect"],
        "maximum_pre_label_imaginary_residual": pre_diagnostics[
            "imaginary_residual"
        ],
        "maximum_post_label_imaginary_residual": post_diagnostics[
            "imaginary_residual"
        ],
    }
    validation = {
        "pre_label_valid": bool(pre_diagnostics["valid"]),
        "post_label_valid": bool(post_diagnostics["valid"]),
    }
    return pre, post, metrics, validation


class HashChainedEventLedger:
    """Canonical closed-schema SHA-256 ledger with optional binary LF output."""

    def __init__(self, path: str | Path | None = None):
        self._events: list[dict] = []
        self._previous = GENESIS_DIGEST
        self._handle = None
        if path is not None:
            value = Path(path)
            value.parent.mkdir(parents=True, exist_ok=True)
            self._handle = value.open("xb")

    def append(self, kind: str, key: str, payload: dict) -> dict:
        # Canonical JSON round-tripping rejects non-JSON/nonfinite values and
        # snapshots the caller's mutable dictionaries before hashing.
        payload_value = json.loads(canonical_bytes(payload).decode("utf-8"))
        _validate_event_payload(kind, key, payload_value)
        base = {
            "sequence": len(self._events),
            "previous_event_digest": self._previous,
            "kind": kind,
            "key": key,
            "payload": payload_value,
        }
        event = {**base, "event_digest": canonical_digest(base)}
        self._events.append(event)
        self._previous = event["event_digest"]
        if self._handle is not None:
            self._handle.write(canonical_bytes(event) + b"\n")
            self._handle.flush()
        return event

    @property
    def events(self) -> tuple[dict, ...]:
        return tuple(self._events)

    @property
    def root(self) -> str:
        return self._previous

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "HashChainedEventLedger":
        return self

    def __exit__(self, *_args) -> None:
        self.close()


_OUTER_EVENT_FIELDS = frozenset({
    "sequence", "previous_event_digest", "kind", "key", "payload",
    "event_digest",
})
_STORE_PAYLOAD_FIELDS = frozenset({
    "schema_version", "protocol_store_id", "map", "depth_index",
    "rho_decimal", "source_index", "reservoir_key", "stored_template_digest",
})
_FREEZE_PAYLOAD_FIELDS = frozenset({
    "schema_version", "protocol_receiver_id", "receiver_index", "task",
    "depth_index", "rho_decimal", "classes", "clean_map_template_digests",
    "pooled_template_digest", "common_receiver_digest",
    "structural_receiver_cost_digest", "prior_and_perturbation_definition_digest",
    "support_rank", "effect_ranks", "outcomes_including_reject",
    "padded_outcome_dimension", "signal_qubits", "outcome_ancilla_qubits",
    "total_qubits", "residuals", "controls",
})
_EVALUATION_PAYLOAD_FIELDS = frozenset({
    "schema_version", "protocol_cell_id", "protocol_receiver_id", "map",
    "receiver_index", "task", "depth_index", "rho_decimal", "classes",
    "eta_index", "eta_decimal", "epsilon_index", "epsilon_decimal",
    "producer_array_bindings", "metrics", "validation",
})


def _plain_dict(value: object, *, name: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a plain dictionary")
    return value


def _finite_number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _validate_metric_values(metrics: Mapping[str, object]) -> None:
    if not isinstance(metrics, dict) or set(metrics) != set(_METRIC_FIELDS):
        raise ValueError("metric field set differs")
    for field, value in metrics.items():
        if field == "conditional_correct_probability_given_nonreject" and value is None:
            continue
        _finite_number(value, name=f"metric {field}")
    probability_fields = (
        "correct_probability", "mean_reject_probability",
        "minimum_pre_label_probability", "maximum_pre_label_probability",
        "minimum_post_label_probability", "maximum_post_label_probability",
    )
    if any(
        not -TOL <= float(metrics[field]) <= 1.0 + TOL
        for field in probability_fields
    ):
        raise ValueError("probability metric lies outside tolerance")
    if float(metrics["mutual_information_bits"]) < -TOL:
        raise ValueError("mutual information is negative")
    conditional = metrics["conditional_correct_probability_given_nonreject"]
    if conditional is not None and not -TOL <= float(conditional) <= 1.0 + TOL:
        raise ValueError("conditional correct probability lies outside tolerance")
    if (
        float(metrics["minimum_pre_label_probability"])
        > float(metrics["maximum_pre_label_probability"])
        or float(metrics["minimum_post_label_probability"])
        > float(metrics["maximum_post_label_probability"])
    ):
        raise ValueError("probability extrema are reversed")
    for field in (
        "maximum_pre_label_row_sum_defect",
        "maximum_post_label_row_sum_defect",
        "maximum_pre_label_imaginary_residual",
        "maximum_post_label_imaginary_residual",
    ):
        if not 0.0 <= float(metrics[field]) <= TOL:
            raise ValueError(f"residual metric exceeds tolerance: {field}")
    nonreject = 1.0 - float(metrics["mean_reject_probability"])
    if nonreject <= 1e-15:
        if conditional is not None:
            raise ValueError("conditional correct probability must be null")
    elif conditional is None or abs(
        float(conditional) - float(metrics["correct_probability"]) / nonreject
    ) > TOL:
        raise ValueError("conditional correct probability is inconsistent")
    if float(metrics["correct_probability"]) > nonreject + TOL:
        raise ValueError("correct probability exceeds non-reject mass")


def _validate_event_payload(kind: str, key: str, payload: Mapping[str, object]) -> None:
    if not isinstance(payload, dict):
        raise TypeError("event payload must be a plain dictionary")
    expected: frozenset[str]
    identity_key: object
    if kind == "store":
        expected = _STORE_PAYLOAD_FIELDS
        identity_key = payload.get("protocol_store_id", "")
        if payload.get("schema_version") != "hypercomplexbrain.r6l-event-store.v1":
            raise ValueError("wrong store-event schema")
        _require_sha256(payload.get("protocol_store_id"), name="store event ID")
        if payload.get("map") not in MAPS:
            raise ValueError("store event map differs from the frozen map set")
        depth_index = _require_int(
            payload.get("depth_index"), name="store depth index", lower=0, upper=4
        )
        if payload.get("rho_decimal") != DEPTH_COORDS[depth_index][0]:
            raise ValueError("store event depth coordinates disagree")
        _require_int(
            payload.get("source_index"), name="store source index", lower=0, upper=31
        )
        if not isinstance(payload.get("reservoir_key"), str) or not payload.get(
            "reservoir_key"
        ):
            raise ValueError("store event reservoir key is empty or non-string")
        _require_sha256(
            payload.get("stored_template_digest"), name="stored template digest"
        )
    elif kind == "common_receiver_freeze":
        expected = _FREEZE_PAYLOAD_FIELDS
        identity_key = payload.get("protocol_receiver_id", "")
        if payload.get("schema_version") != "hypercomplexbrain.r6l-event-receiver.v1":
            raise ValueError("wrong receiver-event schema")
        _require_sha256(
            payload.get("protocol_receiver_id"), name="receiver event ID"
        )
        receiver_index = _require_int(
            payload.get("receiver_index"), name="receiver index", lower=0, upper=11
        )
        task, depth_index, rho_decimal, _depth, classes = _receiver_rows()[receiver_index]
        observed_coordinates = (
            payload.get("task"),
            payload.get("depth_index"),
            payload.get("rho_decimal"),
            payload.get("classes"),
        )
        if not _canonical_json_equal(
            observed_coordinates, (task, depth_index, rho_decimal, classes)
        ):
            raise ValueError("receiver event coordinates differ from the frozen row")
        clean_digests = _plain_dict(
            payload.get("clean_map_template_digests"),
            name="clean map template digests",
        )
        if set(clean_digests) != set(MAPS):
            raise ValueError("receiver event map-template digest set is not closed")
        for map_name, digest in clean_digests.items():
            _require_sha256(digest, name=f"{map_name} clean template digest")
        for field in (
            "pooled_template_digest",
            "common_receiver_digest",
            "structural_receiver_cost_digest",
            "prior_and_perturbation_definition_digest",
        ):
            _require_sha256(payload.get(field), name=field)
        support_rank = _require_int(
            payload.get("support_rank"), name="receiver support rank", lower=0, upper=16
        )
        effect_ranks = payload.get("effect_ranks")
        if not isinstance(effect_ranks, list) or len(effect_ranks) != classes + 1:
            raise ValueError("receiver effect-rank vector has the wrong length")
        for index, rank in enumerate(effect_ranks):
            _require_int(rank, name=f"effect rank {index}", lower=0, upper=16)
        outcomes = classes + 1
        ancilla_qubits = int(math.ceil(math.log2(outcomes)))
        frozen_integer_fields = {
            "outcomes_including_reject": outcomes,
            "padded_outcome_dimension": 1 << ancilla_qubits,
            "signal_qubits": 4,
            "outcome_ancilla_qubits": ancilla_qubits,
            "total_qubits": 4 + ancilla_qubits,
        }
        for field, expected_value in frozen_integer_fields.items():
            _require_int(
                payload.get(field),
                name=f"receiver event {field}",
                lower=expected_value,
                upper=expected_value,
            )
        residuals = _plain_dict(payload.get("residuals"), name="receiver residuals")
        if set(residuals) != {
            "completeness_spectral", "support_projector_spectral",
            "isometry_spectral", "maximum_effect_reconstruction_fro",
        }:
            raise ValueError("receiver residual field set is not closed")
        for name, value in residuals.items():
            if not 0.0 <= _finite_number(value, name=name) <= TOL:
                raise ValueError(f"receiver residual {name} exceeds tolerance")
        controls = _plain_dict(payload.get("controls"), name="receiver controls")
        if set(controls) != {
            "pooled_weights_exact", "receiver_valid", "naimark_valid",
        }:
            raise ValueError("receiver control field set is not closed")
        if not all(value is True for value in controls.values()):
            raise ValueError("receiver event contains a failed or non-Boolean control")
    elif kind == "evaluation":
        expected = _EVALUATION_PAYLOAD_FIELDS
        identity_key = payload.get("protocol_cell_id", "")
        if payload.get("schema_version") != "hypercomplexbrain.r6l-event-evaluation.v1":
            raise ValueError("wrong evaluation-event schema")
        _require_sha256(payload.get("protocol_cell_id"), name="evaluation cell ID")
        _require_sha256(
            payload.get("protocol_receiver_id"), name="evaluation receiver ID"
        )
        if payload.get("map") not in MAPS:
            raise ValueError("evaluation map differs from the frozen map set")
        receiver_index = _require_int(
            payload.get("receiver_index"), name="receiver index", lower=0, upper=11
        )
        task, depth_index, rho_decimal, _depth, classes = _receiver_rows()[receiver_index]
        observed_coordinates = (
            payload.get("task"),
            payload.get("depth_index"),
            payload.get("rho_decimal"),
            payload.get("classes"),
        )
        if not _canonical_json_equal(
            observed_coordinates, (task, depth_index, rho_decimal, classes)
        ):
            raise ValueError("evaluation receiver coordinates differ")
        eta_index = _require_int(
            payload.get("eta_index"), name="eta index", lower=0, upper=3
        )
        epsilon_index = _require_int(
            payload.get("epsilon_index"), name="epsilon index", lower=0, upper=3
        )
        if payload.get("eta_decimal") != NOISE_COORDS[eta_index][0]:
            raise ValueError("evaluation state-noise coordinates disagree")
        if payload.get("epsilon_decimal") != NOISE_COORDS[epsilon_index][0]:
            raise ValueError("evaluation label-noise coordinates disagree")
        bindings = _plain_dict(
            payload.get("producer_array_bindings"), name="evaluation bindings"
        )
        if set(bindings) != set(_BINDING_FIELDS):
            raise ValueError("evaluation binding field set differs")
        for field, value in bindings.items():
            _require_sha256(value, name=f"evaluation binding {field}")
        metrics = _plain_dict(payload.get("metrics"), name="evaluation metrics")
        _validate_metric_values(metrics)
        validation = _plain_dict(
            payload.get("validation"), name="evaluation validation"
        )
        if set(validation) != {
            "pre_label_valid", "post_label_valid",
        }:
            raise ValueError("evaluation validation field set differs")
        if not all(value is True for value in validation.values()):
            raise ValueError("evaluation contains a failed or non-Boolean validation")
    else:
        raise ValueError(f"unknown event kind {kind!r}")
    if set(payload) != expected:
        raise ValueError(f"{kind} payload field set is not closed")
    if key != f"{kind}:{identity_key}":
        raise ValueError("event key does not bind its portable identity")
    canonical_bytes(payload)


def _validate_event_plan_binding(
    index: int,
    event: Mapping[str, object],
    plan: ProtocolPlan,
) -> None:
    kind = event["kind"]
    key = event["key"]
    payload = event["payload"]
    if index < 320:
        spec = plan.stores[index]
        if kind != "store" or key != f"store:{spec.protocol_store_id}":
            raise ValueError("store event order/key differs from the portable plan")
        observed = (
            payload["protocol_store_id"], payload["map"], payload["depth_index"],
            payload["rho_decimal"], payload["source_index"], payload["reservoir_key"],
        )
        expected = (
            spec.protocol_store_id, spec.map_name, spec.depth_index,
            spec.rho_decimal, spec.source_index,
            f"{spec.map_name}:rho={spec.rho_decimal}:k={spec.source_index:02d}",
        )
    elif index < 332:
        spec = plan.receivers[index - 320]
        if (
            kind != "common_receiver_freeze"
            or key != f"common_receiver_freeze:{spec.protocol_receiver_id}"
        ):
            raise ValueError("receiver event order/key differs from the portable plan")
        observed = (
            payload["protocol_receiver_id"], payload["receiver_index"],
            payload["task"], payload["depth_index"], payload["rho_decimal"],
            payload["classes"],
        )
        expected = (
            spec.protocol_receiver_id, spec.receiver_index, spec.task,
            spec.depth_index, spec.rho_decimal, spec.classes,
        )
    elif index < 716:
        spec = plan.cells[index - 332]
        if kind != "evaluation" or key != f"evaluation:{spec.protocol_cell_id}":
            raise ValueError("evaluation event order/key differs from the portable plan")
        observed = (
            payload["protocol_cell_id"], payload["protocol_receiver_id"],
            payload["map"], payload["receiver_index"], payload["task"],
            payload["depth_index"], payload["rho_decimal"], payload["classes"],
            payload["eta_index"], payload["eta_decimal"],
            payload["epsilon_index"], payload["epsilon_decimal"],
        )
        expected = (
            spec.protocol_cell_id, spec.receiver.protocol_receiver_id,
            spec.map_name, spec.receiver.receiver_index, spec.receiver.task,
            spec.receiver.depth_index, spec.receiver.rho_decimal,
            spec.receiver.classes, spec.eta_index, spec.eta_decimal,
            spec.epsilon_index, spec.epsilon_decimal,
        )
    else:
        raise ValueError("event lies outside the frozen 716-event surface")
    if not _canonical_json_equal(observed, expected):
        raise ValueError("event payload coordinates differ from the portable plan")


def validate_event_chain(
    events: Sequence[Mapping[str, object]],
    plan: ProtocolPlan | None = None,
) -> dict:
    plan_value = plan if plan is not None else plan_protocol()
    reasons: list[str] = []
    previous = GENESIS_DIGEST
    keys: list[str] = []
    for index, event in enumerate(events):
        try:
            if set(event) != _OUTER_EVENT_FIELDS:
                raise ValueError("outer event field set is not closed")
            if type(event["sequence"]) is not int or event["sequence"] != index:
                raise ValueError("event sequence is not the contiguous integer index")
            if type(event["kind"]) is not str or type(event["key"]) is not str:
                raise TypeError("event kind and key must be strings")
            _require_sha256(
                event["previous_event_digest"], name="previous event digest"
            )
            _require_sha256(event["event_digest"], name="event digest")
            if event["previous_event_digest"] != previous:
                raise ValueError("event chain link mismatch")
            _validate_event_payload(event["kind"], event["key"], event["payload"])
            _validate_event_plan_binding(index, event, plan_value)
            base = {key: event[key] for key in (
                "sequence", "previous_event_digest", "kind", "key", "payload"
            )}
            if event["event_digest"] != canonical_digest(base):
                raise ValueError("event digest mismatch")
            previous = event["event_digest"]
            keys.append(event["key"])
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"event {index}: {exc}")
    if len(keys) != len(set(keys)):
        reasons.append("event keys are not unique")
    if len(events) != 716:
        reasons.append(f"expected 716 events, observed {len(events)}")
    kinds = [event.get("kind") for event in events]
    if kinds[:320] != ["store"] * min(320, len(kinds)):
        reasons.append("store event block differs")
    if len(kinds) >= 332 and kinds[320:332] != ["common_receiver_freeze"] * 12:
        reasons.append("receiver-freeze event block differs")
    if len(kinds) >= 716 and kinds[332:716] != ["evaluation"] * 384:
        reasons.append("evaluation event block differs")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "event_count": len(events),
        "unique_keys": len(set(keys)),
        "ledger_root": previous,
    }


class _ProtocolReservoir:
    """Minimal store/get adapter that emits the frozen R6l store events."""

    def __init__(self, plan: ProtocolPlan, ledger: HashChainedEventLedger):
        self._specs = {
            (row.map_name, row.depth_index, row.source_index): row
            for row in plan.stores
        }
        self._records: dict[str, ReservoirRecord] = {}
        self._ledger = ledger

    def store(self, key: str, state: np.ndarray, metadata: dict) -> ReservoirRecord:
        if key in self._records:
            raise ValueError("reservoir key is not unique")
        map_name = metadata.get("map")
        rho = metadata.get("rho")
        source_index = metadata.get("source_index")
        if map_name not in MAPS or rho not in DEPTHS:
            raise ValueError("store metadata is outside the sealed grid")
        depth_index = DEPTHS.index(rho)
        if isinstance(source_index, bool) or not isinstance(source_index, int):
            raise ValueError("source index is not an integer")
        spec = self._specs[(map_name, depth_index, source_index)]
        expected_key = f"{map_name}:rho={spec.rho_decimal}:k={source_index:02d}"
        if key != expected_key:
            raise ValueError("reservoir key differs from the portable store identity")
        value = _validated_density(state).copy()
        value.setflags(write=False)
        record = ReservoirRecord(key=key, shard="protocol", state=value, metadata=dict(metadata))
        self._records[key] = record
        stored_digest = complex_array_record(
            value, index=source_index, role="clean_template"
        )["array_digest"]
        payload = {
            "schema_version": "hypercomplexbrain.r6l-event-store.v1",
            "protocol_store_id": spec.protocol_store_id,
            "map": map_name,
            "depth_index": depth_index,
            "rho_decimal": spec.rho_decimal,
            "source_index": source_index,
            "reservoir_key": key,
            "stored_template_digest": stored_digest,
        }
        self._ledger.append("store", f"store:{spec.protocol_store_id}", payload)
        return record

    def get(self, key: str) -> ReservoirRecord:
        try:
            return self._records[key]
        except KeyError as exc:
            raise KeyError(f"unknown reservoir key {key!r}") from exc


class _CatalogBuilder:
    def __init__(self):
        self.arrays: dict[str, np.ndarray] = {}
        self.array_metadata: dict[str, dict] = {}
        self.aggregate_locators: dict[str, dict] = {}
        self.semantic_objects: dict[str, dict] = {}

    def add_array(self, key: str, array: np.ndarray, *, role: str) -> None:
        if key in self.arrays:
            raise ValueError(f"duplicate NPZ key {key}")
        source = np.asarray(array)
        if source.dtype.hasobject:
            raise ValueError("object-dtype arrays are forbidden")
        if np.iscomplexobj(source):
            value = np.ascontiguousarray(source, dtype="<c16")
            digest = complex_array_record(value, index=0, role=role)["array_digest"]
            dtype = "<c16"
        else:
            value = np.ascontiguousarray(source, dtype="<f8")
            digest = real_array_record(value, index=0, role=role)["array_digest"]
            dtype = "<f8"
        self.arrays[key] = value
        self.array_metadata[key] = {
            "role": role,
            "shape": [int(item) for item in value.shape],
            "dtype": dtype,
            "array_digest": digest,
        }

    def bind_aggregate(
        self,
        digest: str,
        aggregate_object: dict,
        locators: Sequence[dict],
    ) -> None:
        items = aggregate_object.get("items")
        if not isinstance(items, list) or len(items) != len(locators):
            raise ValueError("aggregate item/locator cardinality mismatch")
        value = {
            "aggregate_object": aggregate_object,
            "items": [
                {**dict(locator), "item": item}
                for item, locator in zip(items, locators)
            ],
        }
        existing = self.aggregate_locators.get(digest)
        if existing is not None and not _canonical_json_equal(existing, value):
            raise ValueError("one aggregate digest has conflicting locators")
        self.aggregate_locators[digest] = value

    def bind_semantic(self, digest: str, value: dict) -> None:
        if canonical_digest(value) != digest:
            raise ValueError("semantic digest/object mismatch")
        existing = self.semantic_objects.get(digest)
        if existing is not None and not _canonical_json_equal(existing, value):
            raise ValueError("one semantic digest has conflicting objects")
        self.semantic_objects[digest] = value

    def finalize(self) -> dict:
        return {
            "schema_version": "hypercomplexbrain.r6l-receiver-catalog.v1",
            "npz_key_count": len(self.arrays),
            "arrays": self.array_metadata,
            "aggregate_locators": self.aggregate_locators,
            "semantic_objects": self.semantic_objects,
        }


def _slice_locators(key: str, count: int) -> list[dict]:
    return [{"npz_key": key, "slice": [index]} for index in range(count)]


def _register_bundle(catalog: _CatalogBuilder, bundle: CommonReceiverBundle) -> None:
    token = f"r{bundle.spec.receiver_index:02d}"
    for map_name in MAPS:
        task = bundle.tasks[map_name]
        template_key = f"{token}__{map_name}__clean_templates"
        query_key = f"{token}__{map_name}__clean_queries"
        catalog.add_array(template_key, np.stack(task.templates), role="clean_templates")
        catalog.add_array(query_key, np.stack(task.queries), role="clean_queries")
        catalog.bind_aggregate(
            bundle.clean_template_digests[map_name],
            bundle.clean_template_objects[map_name],
            _slice_locators(template_key, bundle.spec.classes),
        )
        catalog.bind_aggregate(
            bundle.query_digests[map_name],
            bundle.query_objects[map_name],
            _slice_locators(query_key, bundle.spec.classes),
        )
    pooled_key = f"{token}__pooled_templates"
    effects_key = f"{token}__receiver_effects"
    roots_key = f"{token}__sqrt_effects"
    isometry_key = f"{token}__naimark_isometry"
    effects = bundle.receiver.effects + (bundle.receiver.reject_effect,)
    catalog.add_array(pooled_key, np.stack(bundle.pooled_templates), role="pooled_templates")
    catalog.add_array(effects_key, np.stack(effects), role="receiver_effects")
    catalog.add_array(roots_key, np.stack(bundle.square_roots), role="sqrt_effects")
    catalog.add_array(isometry_key, bundle.naimark_isometry, role="naimark_isometry")
    catalog.bind_aggregate(
        bundle.pooled_digest,
        bundle.pooled_object,
        _slice_locators(pooled_key, bundle.spec.classes),
    )
    catalog.bind_aggregate(
        bundle.receiver_digest,
        bundle.receiver_object,
        _slice_locators(effects_key, bundle.spec.classes + 1),
    )
    structural_locators = _slice_locators(roots_key, bundle.spec.classes + 1)
    structural_locators.append({"npz_key": isometry_key, "slice": None})
    catalog.bind_aggregate(
        bundle.structural_digest,
        bundle.structural_object,
        structural_locators,
    )
    catalog.bind_semantic(bundle.prior_digest, bundle.prior_object)


def _freeze_payload(bundle: CommonReceiverBundle) -> dict:
    spec = bundle.spec
    controls = {
        "pooled_weights_exact": True,
        "receiver_valid": bool(bundle.receiver.diagnostics["valid"]),
        "naimark_valid": bool(bundle.residuals["isometry_spectral"] <= TOL),
    }
    return {
        "schema_version": "hypercomplexbrain.r6l-event-receiver.v1",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "receiver_index": spec.receiver_index,
        "task": spec.task,
        "depth_index": spec.depth_index,
        "rho_decimal": spec.rho_decimal,
        "classes": spec.classes,
        "clean_map_template_digests": {
            map_name: bundle.clean_template_digests[map_name] for map_name in MAPS
        },
        "pooled_template_digest": bundle.pooled_digest,
        "common_receiver_digest": bundle.receiver_digest,
        "structural_receiver_cost_digest": bundle.structural_digest,
        "prior_and_perturbation_definition_digest": bundle.prior_digest,
        "support_rank": bundle.support_rank,
        "effect_ranks": list(bundle.effect_ranks),
        "outcomes_including_reject": spec.classes + 1,
        "padded_outcome_dimension": bundle.outcome_dimension,
        "signal_qubits": 4,
        "outcome_ancilla_qubits": bundle.outcome_ancilla_qubits,
        "total_qubits": 4 + bundle.outcome_ancilla_qubits,
        "residuals": dict(bundle.residuals),
        "controls": controls,
    }


@dataclass(frozen=True)
class ProtocolRun:
    report: dict
    catalog: dict
    arrays: Mapping[str, np.ndarray]
    decision: dict
    events: tuple[dict, ...]


def _probability_aggregate(
    kind: str,
    cell_id: str,
    table: np.ndarray,
) -> tuple[dict, str]:
    role = "conditional_probability_table"
    value = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": kind,
        "protocol_cell_id": cell_id,
        "items": [real_array_record(table, index=0, role=role)],
    }
    return value, canonical_digest(value)


def _label_matrix_aggregate(
    spec: ReceiverSpec,
    epsilon_index: int,
    epsilon_decimal: str,
    matrix: np.ndarray,
) -> tuple[dict, str]:
    value = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": "receiver_label_matrix",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "epsilon_index": epsilon_index,
        "epsilon_decimal": epsilon_decimal,
        "items": [real_array_record(matrix, index=0, role="label_channel_matrix")],
    }
    return value, canonical_digest(value)


def _expected_npz_keys(plan: ProtocolPlan) -> set[str]:
    keys: set[str] = set()
    for spec in plan.receivers:
        token = f"r{spec.receiver_index:02d}"
        for map_name in MAPS:
            keys.add(f"{token}__{map_name}__clean_templates")
            keys.add(f"{token}__{map_name}__clean_queries")
        keys.update({
            f"{token}__pooled_templates",
            f"{token}__receiver_effects",
            f"{token}__sqrt_effects",
            f"{token}__naimark_isometry",
        })
        for map_name in MAPS:
            for eta_index in range(4):
                keys.add(f"{token}__{map_name}__e{eta_index:02d}__state_noised_queries")
        for epsilon_index in range(4):
            keys.add(f"{token}__l{epsilon_index:02d}__label_matrix")
        for map_name in MAPS:
            for eta_index in range(4):
                for epsilon_index in range(4):
                    prefix = (
                        f"{token}__{map_name}__e{eta_index:02d}__l{epsilon_index:02d}"
                    )
                    keys.add(f"{prefix}__pre_label_probabilities")
                    keys.add(f"{prefix}__post_label_probabilities")
    return keys


def _expected_npz_schema(plan: ProtocolPlan) -> dict[str, dict]:
    schema: dict[str, dict] = {}

    def add(key: str, role: str, shape: tuple[int, ...], dtype: str) -> None:
        if key in schema:
            raise ValueError(f"duplicate expected NPZ key {key}")
        schema[key] = {"role": role, "shape": list(shape), "dtype": dtype}

    for spec in plan.receivers:
        token = f"r{spec.receiver_index:02d}"
        classes = spec.classes
        outcomes = classes + 1
        outcome_dimension = 1 << int(math.ceil(math.log2(outcomes)))
        for map_name in MAPS:
            add(
                f"{token}__{map_name}__clean_templates",
                "clean_templates",
                (classes, AMBIENT_DIM, AMBIENT_DIM),
                "<c16",
            )
            add(
                f"{token}__{map_name}__clean_queries",
                "clean_queries",
                (classes, AMBIENT_DIM, AMBIENT_DIM),
                "<c16",
            )
        add(
            f"{token}__pooled_templates",
            "pooled_templates",
            (classes, AMBIENT_DIM, AMBIENT_DIM),
            "<c16",
        )
        add(
            f"{token}__receiver_effects",
            "receiver_effects",
            (outcomes, AMBIENT_DIM, AMBIENT_DIM),
            "<c16",
        )
        add(
            f"{token}__sqrt_effects",
            "sqrt_effects",
            (outcomes, AMBIENT_DIM, AMBIENT_DIM),
            "<c16",
        )
        add(
            f"{token}__naimark_isometry",
            "naimark_isometry",
            (AMBIENT_DIM * outcome_dimension, AMBIENT_DIM),
            "<c16",
        )
        for map_name in MAPS:
            for eta_index in range(4):
                add(
                    f"{token}__{map_name}__e{eta_index:02d}__state_noised_queries",
                    "state_noised_queries",
                    (classes, AMBIENT_DIM, AMBIENT_DIM),
                    "<c16",
                )
        for epsilon_index in range(4):
            add(
                f"{token}__l{epsilon_index:02d}__label_matrix",
                "label_channel_matrix",
                (outcomes, outcomes),
                "<f8",
            )
        for map_name in MAPS:
            for eta_index in range(4):
                for epsilon_index in range(4):
                    prefix = (
                        f"{token}__{map_name}__e{eta_index:02d}"
                        f"__l{epsilon_index:02d}"
                    )
                    add(
                        f"{prefix}__pre_label_probabilities",
                        "pre_label_probabilities",
                        (classes, outcomes),
                        "<f8",
                    )
                    add(
                        f"{prefix}__post_label_probabilities",
                        "post_label_probabilities",
                        (classes, outcomes),
                        "<f8",
                    )
    return schema


def _expected_locator_tokens(plan: ProtocolPlan) -> set[tuple[str, int | None]]:
    stacked_roles = {
        "clean_templates", "clean_queries", "pooled_templates",
        "receiver_effects", "sqrt_effects", "state_noised_queries",
    }
    tokens: set[tuple[str, int | None]] = set()
    for key, entry in _expected_npz_schema(plan).items():
        if entry["role"] in stacked_roles:
            tokens.update((key, index) for index in range(entry["shape"][0]))
        else:
            tokens.add((key, None))
    return tokens


def _expected_semantic_objects(plan: ProtocolPlan) -> dict[str, dict]:
    values: dict[str, dict] = {}
    for spec in plan.receivers:
        prior = _prior_perturbation_object(spec)
        values[canonical_digest(prior)] = prior
        for epsilon_index, (epsilon_decimal, _epsilon) in enumerate(NOISE_COORDS):
            label = _label_channel_object(spec, epsilon_index, epsilon_decimal)
            values[canonical_digest(label)] = label
    for eta_index, (eta_decimal, _eta) in enumerate(NOISE_COORDS):
        state = _state_channel_object(eta_index, eta_decimal)
        values[canonical_digest(state)] = state
    return values


def _validate_aggregate_contract(value: Mapping[str, object], plan: ProtocolPlan) -> None:
    if not isinstance(value, dict):
        raise TypeError("aggregate object must be a plain dictionary")
    kind = value.get("kind")
    base = {"schema_version", "kind", "items"}
    receiver_by_id = {row.protocol_receiver_id: row for row in plan.receivers}
    cell_ids = {row.protocol_cell_id for row in plan.cells}
    receiver_kinds = {
        "clean_map_templates", "pooled_templates", "common_receiver_effects",
        "perturbed_queries", "state_noised_queries", "structural_receiver_cost",
        "receiver_label_matrix",
    }
    if kind in receiver_kinds:
        receiver_id = value.get("protocol_receiver_id")
        if receiver_id not in receiver_by_id:
            raise ValueError("aggregate receiver ID is outside the frozen plan")
        spec = receiver_by_id[receiver_id]
    else:
        spec = None
    if kind in {
        "clean_map_templates", "pooled_templates", "common_receiver_effects",
        "perturbed_queries",
    }:
        expected_fields = base | {"protocol_receiver_id", "map"}
    elif kind == "state_noised_queries":
        expected_fields = base | {
            "protocol_receiver_id", "map", "eta_index", "eta_decimal",
        }
    elif kind == "structural_receiver_cost":
        expected_fields = base | {
            "protocol_receiver_id", "signal_dimension", "classes",
            "outcome_dimension", "signal_qubits", "outcome_ancilla_qubits",
            "total_qubits", "effect_ranks",
        }
    elif kind == "receiver_label_matrix":
        expected_fields = base | {
            "protocol_receiver_id", "epsilon_index", "epsilon_decimal",
        }
    elif kind in {"pre_label_probabilities", "post_label_probabilities"}:
        expected_fields = base | {"protocol_cell_id"}
        if value.get("protocol_cell_id") not in cell_ids:
            raise ValueError("probability aggregate cell ID is outside the frozen plan")
    else:
        raise ValueError(f"unknown aggregate kind {kind!r}")
    if set(value) != expected_fields:
        raise ValueError(f"aggregate field set differs for {kind}")
    items = value.get("items")
    if not isinstance(items, list):
        raise TypeError("aggregate items must be a list")

    expected_roles: list[str]
    if kind in {"clean_map_templates", "perturbed_queries", "state_noised_queries"}:
        if value.get("map") not in MAPS:
            raise ValueError("map-local aggregate has an invalid map")
        expected_roles = [{
            "clean_map_templates": "clean_template",
            "perturbed_queries": "clean_query",
            "state_noised_queries": "state_noised_query",
        }[str(kind)]] * spec.classes
    elif kind == "pooled_templates":
        if value.get("map") is not None:
            raise ValueError("pooled-template aggregate map must be null")
        expected_roles = ["pooled_template"] * spec.classes
    elif kind == "common_receiver_effects":
        if value.get("map") is not None:
            raise ValueError("common-receiver aggregate map must be null")
        expected_roles = ["class_effect"] * spec.classes + ["reject_effect"]
    elif kind == "structural_receiver_cost":
        outcomes = spec.classes + 1
        ancilla = int(math.ceil(math.log2(outcomes)))
        ranks = value.get("effect_ranks")
        frozen_dimensions = {
            "signal_dimension": AMBIENT_DIM,
            "classes": spec.classes,
            "outcome_dimension": 1 << ancilla,
            "signal_qubits": 4,
            "outcome_ancilla_qubits": ancilla,
            "total_qubits": 4 + ancilla,
        }
        for field, expected_value in frozen_dimensions.items():
            _require_int(
                value.get(field),
                name=f"structural aggregate {field}",
                lower=expected_value,
                upper=expected_value,
            )
        if (
            not isinstance(ranks, list)
            or len(ranks) != outcomes
            or any(type(rank) is not int or not 0 <= rank <= 16 for rank in ranks)
        ):
            raise ValueError("structural aggregate dimensions/ranks differ")
        expected_roles = (
            ["sqrt_class_effect"] * spec.classes
            + ["sqrt_reject_effect", "naimark_isometry"]
        )
    elif kind == "receiver_label_matrix":
        epsilon_index = _require_int(
            value.get("epsilon_index"), name="epsilon index", lower=0, upper=3
        )
        if value.get("epsilon_decimal") != NOISE_COORDS[epsilon_index][0]:
            raise ValueError("label-matrix aggregate epsilon coordinates disagree")
        expected_roles = ["label_channel_matrix"]
    else:
        expected_roles = ["conditional_probability_table"]
    if kind == "state_noised_queries":
        eta_index = _require_int(
            value.get("eta_index"), name="eta index", lower=0, upper=3
        )
        if value.get("eta_decimal") != NOISE_COORDS[eta_index][0]:
            raise ValueError("noised-query aggregate eta coordinates disagree")
    if len(items) != len(expected_roles):
        raise ValueError(f"aggregate item count differs for {kind}")
    for index, (item, role) in enumerate(zip(items, expected_roles)):
        if not isinstance(item, dict) or set(item) != {
            "index", "role", "shape", "dtype", "array_digest",
        }:
            raise ValueError("aggregate item field set differs")
        _require_int(
            item.get("index"),
            name="aggregate item index",
            lower=index,
            upper=index,
        )
        if type(item.get("role")) is not str or item.get("role") != role:
            raise ValueError("aggregate item index/role order differs")
        shape = item.get("shape")
        if not isinstance(shape, list) or not shape:
            raise ValueError("aggregate item shape must be a nonempty list")
        for dimension_index, dimension in enumerate(shape):
            _require_int(
                dimension,
                name=f"aggregate item shape dimension {dimension_index}",
                lower=1,
                upper=2**31 - 1,
            )
        if type(item.get("dtype")) is not str or item.get("dtype") not in {
            "<c16", "<f8",
        }:
            raise ValueError("aggregate item dtype differs from the closed set")
        _require_sha256(item.get("array_digest"), name="aggregate item digest")


def _expected_aggregate_locators(
    value: Mapping[str, object], plan: ProtocolPlan,
) -> list[dict]:
    kind = value["kind"]
    if "protocol_receiver_id" in value:
        spec = next(
            row for row in plan.receivers
            if row.protocol_receiver_id == value["protocol_receiver_id"]
        )
        token = f"r{spec.receiver_index:02d}"
    if kind == "clean_map_templates":
        return _slice_locators(
            f"{token}__{value['map']}__clean_templates", spec.classes
        )
    if kind == "perturbed_queries":
        return _slice_locators(
            f"{token}__{value['map']}__clean_queries", spec.classes
        )
    if kind == "pooled_templates":
        return _slice_locators(f"{token}__pooled_templates", spec.classes)
    if kind == "common_receiver_effects":
        return _slice_locators(f"{token}__receiver_effects", spec.classes + 1)
    if kind == "state_noised_queries":
        return _slice_locators(
            f"{token}__{value['map']}__e{value['eta_index']:02d}"
            "__state_noised_queries",
            spec.classes,
        )
    if kind == "structural_receiver_cost":
        locators = _slice_locators(f"{token}__sqrt_effects", spec.classes + 1)
        locators.append({"npz_key": f"{token}__naimark_isometry", "slice": None})
        return locators
    if kind == "receiver_label_matrix":
        return [{
            "npz_key": f"{token}__l{value['epsilon_index']:02d}__label_matrix",
            "slice": None,
        }]
    if kind in {"pre_label_probabilities", "post_label_probabilities"}:
        cell = next(
            row for row in plan.cells
            if row.protocol_cell_id == value["protocol_cell_id"]
        )
        token = f"r{cell.receiver.receiver_index:02d}"
        key = (
            f"{token}__{cell.map_name}__e{cell.eta_index:02d}"
            f"__l{cell.epsilon_index:02d}__{kind}"
        )
        return [{"npz_key": key, "slice": None}]
    raise ValueError(f"unknown aggregate kind {kind!r}")


def _validate_catalog(builder: _CatalogBuilder, plan: ProtocolPlan) -> dict:
    reasons: list[str] = []
    expected_schema = _expected_npz_schema(plan)
    expected_keys = set(expected_schema)
    if set(builder.arrays) != expected_keys:
        reasons.append("NPZ key set differs from the frozen 1008-key surface")
    if len(builder.arrays) != 1008:
        reasons.append(f"expected 1008 NPZ keys, observed {len(builder.arrays)}")
    if set(builder.arrays) != set(builder.array_metadata):
        reasons.append("array metadata does not cover the exact NPZ key set")
    for key in sorted(set(builder.arrays) & expected_keys):
        array = np.asarray(builder.arrays[key])
        expected = expected_schema[key]
        if list(array.shape) != expected["shape"]:
            reasons.append(f"array shape differs for {key}")
        if array.dtype.str != expected["dtype"]:
            reasons.append(f"array dtype differs for {key}")
        try:
            _require_finite_array(array)
            if expected["dtype"] == "<c16":
                digest = complex_array_record(
                    array, index=0, role=expected["role"]
                )["array_digest"]
            else:
                digest = real_array_record(
                    array, index=0, role=expected["role"]
                )["array_digest"]
            expected_metadata = {**expected, "array_digest": digest}
            if not _canonical_json_equal(
                builder.array_metadata.get(key), expected_metadata
            ):
                reasons.append(f"array metadata differs for {key}")
        except (TypeError, ValueError) as exc:
            reasons.append(f"array {key}: {exc}")
    if len(builder.aggregate_locators) != 996:
        reasons.append(
            f"expected 996 aggregate objects, observed {len(builder.aggregate_locators)}"
        )
    observed_tokens: list[tuple[str, int | None]] = []
    for digest, entry_value in builder.aggregate_locators.items():
        try:
            _require_sha256(digest, name="aggregate digest")
            entry = _plain_dict(entry_value, name="aggregate locator entry")
            if set(entry) != {"aggregate_object", "items"}:
                raise ValueError("aggregate locator entry field set is not closed")
            aggregate = _plain_dict(
                entry.get("aggregate_object"), name="aggregate object"
            )
            if aggregate.get("schema_version") != (
                "hypercomplexbrain.r6l-array-aggregate.v1"
            ):
                raise ValueError("aggregate object schema differs")
            _validate_aggregate_contract(aggregate, plan)
            if canonical_digest(aggregate) != digest:
                raise ValueError(f"aggregate digest mismatch {digest}")
            aggregate_items = aggregate.get("items")
            items = entry.get("items")
            if not isinstance(aggregate_items, list) or not isinstance(items, list):
                raise ValueError("aggregate items must be lists")
            if len(aggregate_items) != len(items):
                raise ValueError("aggregate item/locator cardinality differs")
            observed_locators = [
                {"npz_key": item.get("npz_key"), "slice": item.get("slice")}
                for item in items
            ]
            if not _canonical_json_equal(
                observed_locators, _expected_aggregate_locators(aggregate, plan)
            ):
                raise ValueError("aggregate locators do not bind the object coordinates")
        except (TypeError, ValueError) as exc:
            reasons.append(f"aggregate {digest}: {exc}")
            continue
        for item_index, item_entry in enumerate(items):
            if not isinstance(item_entry, dict):
                reasons.append("aggregate locator item must be a plain dictionary")
                continue
            item = item_entry.get("item", {})
            key = item_entry.get("npz_key")
            slice_value = item_entry.get("slice")
            if set(item_entry) != {"npz_key", "slice", "item"}:
                reasons.append(f"aggregate locator fields differ for {key}")
                continue
            if not _canonical_json_equal(item, aggregate_items[item_index]):
                reasons.append(f"aggregate item order differs for {key}")
                continue
            if key not in builder.arrays:
                reasons.append(f"aggregate locator references missing key {key}")
                continue
            array = builder.arrays[key]
            if slice_value is None:
                located = array
                observed_tokens.append((key, None))
            elif (
                isinstance(slice_value, list)
                and len(slice_value) == 1
                and isinstance(slice_value[0], int)
                and not isinstance(slice_value[0], bool)
            ):
                try:
                    located = array[slice_value[0]]
                    observed_tokens.append((key, slice_value[0]))
                except IndexError:
                    reasons.append(f"aggregate locator is out of range for {key}")
                    continue
            else:
                reasons.append(f"aggregate locator has invalid slice for {key}")
                continue
            try:
                if item.get("dtype") == "<c16":
                    rebuilt = complex_array_record(
                        located,
                        index=item["index"],
                        role=item["role"],
                    )
                elif item.get("dtype") == "<f8":
                    rebuilt = real_array_record(
                        located,
                        index=item["index"],
                        role=item["role"],
                    )
                else:
                    raise ValueError("unknown item dtype")
                if not _canonical_json_equal(rebuilt, item):
                    raise ValueError("located array does not reproduce item record")
            except (KeyError, TypeError, ValueError) as exc:
                reasons.append(f"locator {key}: {exc}")
    expected_tokens = _expected_locator_tokens(plan)
    if set(observed_tokens) != expected_tokens or len(observed_tokens) != len(
        expected_tokens
    ):
        reasons.append("aggregate locators do not cover every frozen array item exactly once")
    expected_semantics = _expected_semantic_objects(plan)
    if not _canonical_json_equal(builder.semantic_objects, expected_semantics):
        reasons.append("semantic object surface differs from the frozen 64-object set")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "npz_key_count": len(builder.arrays),
        "aggregate_count": len(builder.aggregate_locators),
        "semantic_object_count": len(builder.semantic_objects),
    }


def validate_catalog_artifact(
    catalog: Mapping[str, object],
    arrays: Mapping[str, np.ndarray],
    *,
    npz_sha256: str,
    plan: ProtocolPlan | None = None,
) -> dict:
    """Validate a decoded catalog and NPZ surface without trusting the producer."""

    reasons: list[str] = []
    plan_value = plan if plan is not None else plan_protocol()
    expected_fields = {
        "schema_version", "npz_key_count", "arrays", "aggregate_locators",
        "semantic_objects", "npz_sha256",
    }
    try:
        if not isinstance(catalog, dict) or set(catalog) != expected_fields:
            raise ValueError("catalog outer field set is not closed")
        if catalog["schema_version"] != "hypercomplexbrain.r6l-receiver-catalog.v1":
            raise ValueError("catalog schema version differs")
        _require_sha256(npz_sha256, name="NPZ file digest")
        if catalog["npz_sha256"] != npz_sha256:
            raise ValueError("catalog NPZ digest differs from the file bytes")
        _require_int(
            catalog["npz_key_count"],
            name="catalog NPZ key count",
            lower=1008,
            upper=1008,
        )
        metadata = _plain_dict(catalog["arrays"], name="catalog arrays")
        aggregates = _plain_dict(
            catalog["aggregate_locators"], name="catalog aggregate locators"
        )
        semantics = _plain_dict(
            catalog["semantic_objects"], name="catalog semantic objects"
        )
        if not all(type(key) is str for key in arrays):
            raise TypeError("decoded NPZ keys must be strings")
        builder = _CatalogBuilder()
        builder.arrays = {key: np.asarray(value) for key, value in arrays.items()}
        builder.array_metadata = metadata
        builder.aggregate_locators = aggregates
        builder.semantic_objects = semantics
        inner = _validate_catalog(builder, plan_value)
        if not inner["valid"]:
            reasons.extend(inner["reasons"])
    except (KeyError, TypeError, ValueError) as exc:
        reasons.append(str(exc))
        inner = {
            "npz_key_count": len(arrays),
            "aggregate_count": 0,
            "semantic_object_count": 0,
        }
    return {
        "valid": not reasons,
        "reasons": reasons,
        "npz_key_count": inner["npz_key_count"],
        "aggregate_count": inner["aggregate_count"],
        "semantic_object_count": inner["semantic_object_count"],
    }


def execute_protocol(
    plan: ProtocolPlan,
    *,
    ledger: HashChainedEventLedger | None = None,
    additional_controls: Mapping[str, bool] | None = None,
) -> ProtocolRun:
    """Perform the first numerical step after a complete portable plan exists."""

    plan_validation = validate_protocol_plan(plan)
    if not plan_validation["valid"]:
        raise ValueError(f"protocol plan failed before numerics: {plan_validation}")
    active_ledger = ledger if ledger is not None else HashChainedEventLedger()
    reservoir = _ProtocolReservoir(plan, active_ledger)
    tasks_by_map: dict[str, tuple[TaskEnsemble, ...]] = {}
    source_diagnostics: dict[str, dict] = {}
    for map_name in MAPS:
        tasks, diagnostics = build_map_tasks(map_name, reservoir)
        tasks_by_map[map_name] = tasks
        source_diagnostics[map_name] = diagnostics
    if len(active_ledger.events) != 320:
        raise ValueError("sealed task construction did not emit exactly 320 stores")

    catalog_builder = _CatalogBuilder()
    bundles: list[CommonReceiverBundle] = []
    receiver_summaries: list[dict] = []
    for spec in plan.receivers:
        bundle = build_common_receiver_bundle(spec, tasks_by_map)
        bundles.append(bundle)
        _register_bundle(catalog_builder, bundle)
        payload = _freeze_payload(bundle)
        active_ledger.append(
            "common_receiver_freeze",
            f"common_receiver_freeze:{spec.protocol_receiver_id}",
            payload,
        )
        receiver_summaries.append(payload)

    rows: list[dict] = []
    noised_cache: dict[tuple[str, int, int], tuple[np.ndarray, ...]] = {}
    noised_binding_cache: dict[tuple[str, int, int], tuple[dict, str]] = {}
    label_cache: dict[tuple[int, int], np.ndarray] = {}
    label_binding_cache: dict[tuple[int, int], tuple[dict, str, dict, str]] = {}
    bundle_by_index = {bundle.spec.receiver_index: bundle for bundle in bundles}

    for cell in plan.cells:
        bundle = bundle_by_index[cell.receiver.receiver_index]
        token = f"r{cell.receiver.receiver_index:02d}"
        noised_key = (cell.map_name, cell.receiver.receiver_index, cell.eta_index)
        if noised_key not in noised_cache:
            noised = tuple(
                depolarize(query, cell.eta)
                for query in bundle.tasks[cell.map_name].queries
            )
            noised_cache[noised_key] = noised
            noised_object, noised_digest = _query_aggregate(
                cell.receiver,
                cell.map_name,
                noised,
                noised=True,
                eta_index=cell.eta_index,
                eta_decimal=cell.eta_decimal,
            )
            noised_binding_cache[noised_key] = (noised_object, noised_digest)
            npz_key = (
                f"{token}__{cell.map_name}__e{cell.eta_index:02d}"
                "__state_noised_queries"
            )
            catalog_builder.add_array(
                npz_key, np.stack(noised), role="state_noised_queries"
            )
            catalog_builder.bind_aggregate(
                noised_digest,
                noised_object,
                _slice_locators(npz_key, cell.receiver.classes),
            )
        noised = noised_cache[noised_key]
        noised_object, noised_digest = noised_binding_cache[noised_key]

        label_key = (cell.receiver.receiver_index, cell.epsilon_index)
        if label_key not in label_cache:
            matrix = build_label_channel(cell.receiver.classes, cell.epsilon)
            label_cache[label_key] = matrix
            semantic_object = _label_channel_object(
                cell.receiver, cell.epsilon_index, cell.epsilon_decimal
            )
            semantic_digest = canonical_digest(semantic_object)
            matrix_object, matrix_digest = _label_matrix_aggregate(
                cell.receiver,
                cell.epsilon_index,
                cell.epsilon_decimal,
                matrix,
            )
            label_binding_cache[label_key] = (
                semantic_object, semantic_digest, matrix_object, matrix_digest
            )
            npz_key = f"{token}__l{cell.epsilon_index:02d}__label_matrix"
            catalog_builder.add_array(npz_key, matrix, role="label_channel_matrix")
            catalog_builder.bind_aggregate(
                matrix_digest,
                matrix_object,
                [{"npz_key": npz_key, "slice": None}],
            )
            catalog_builder.bind_semantic(semantic_digest, semantic_object)
        label_matrix = label_cache[label_key]
        label_object, label_digest, matrix_object, matrix_digest = (
            label_binding_cache[label_key]
        )

        pre, post, metrics, validation = _evaluate_probability_tables(
            bundle, noised, label_matrix
        )
        pre_object, pre_digest = _probability_aggregate(
            "pre_label_probabilities", cell.protocol_cell_id, pre
        )
        post_object, post_digest = _probability_aggregate(
            "post_label_probabilities", cell.protocol_cell_id, post
        )
        prefix = (
            f"{token}__{cell.map_name}__e{cell.eta_index:02d}"
            f"__l{cell.epsilon_index:02d}"
        )
        pre_key = f"{prefix}__pre_label_probabilities"
        post_key = f"{prefix}__post_label_probabilities"
        catalog_builder.add_array(pre_key, pre, role="pre_label_probabilities")
        catalog_builder.add_array(post_key, post, role="post_label_probabilities")
        catalog_builder.bind_aggregate(
            pre_digest, pre_object, [{"npz_key": pre_key, "slice": None}]
        )
        catalog_builder.bind_aggregate(
            post_digest, post_object, [{"npz_key": post_key, "slice": None}]
        )
        state_object = _state_channel_object(cell.eta_index, cell.eta_decimal)
        state_digest = canonical_digest(state_object)
        catalog_builder.bind_semantic(state_digest, state_object)
        bindings = {
            "clean_map_template_digest": bundle.clean_template_digests[cell.map_name],
            "pooled_template_digest": bundle.pooled_digest,
            "common_receiver_digest": bundle.receiver_digest,
            "perturbed_query_digest": bundle.query_digests[cell.map_name],
            "state_noised_query_digest": noised_digest,
            "pre_label_probability_digest": pre_digest,
            "post_label_probability_digest": post_digest,
            "state_channel_digest": state_digest,
            "receiver_label_channel_digest": label_digest,
            "receiver_label_matrix_digest": matrix_digest,
            "structural_receiver_cost_digest": bundle.structural_digest,
            "prior_and_perturbation_definition_digest": bundle.prior_digest,
        }
        row = {
            "protocol_cell_id": cell.protocol_cell_id,
            "identity": cell.identity,
            "protocol_receiver_id": cell.receiver.protocol_receiver_id,
            "map": cell.map_name,
            "receiver_index": cell.receiver.receiver_index,
            "task": cell.receiver.task,
            "depth_index": cell.receiver.depth_index,
            "rho_decimal": cell.receiver.rho_decimal,
            "classes": cell.receiver.classes,
            "eta_index": cell.eta_index,
            "eta_decimal": cell.eta_decimal,
            "epsilon_index": cell.epsilon_index,
            "epsilon_decimal": cell.epsilon_decimal,
            "producer_array_bindings": bindings,
            "metrics": metrics,
            "validation": validation,
        }
        rows.append(row)
        event_payload = {key: value for key, value in row.items() if key != "identity"}
        event_payload["schema_version"] = "hypercomplexbrain.r6l-event-evaluation.v1"
        active_ledger.append(
            "evaluation",
            f"evaluation:{cell.protocol_cell_id}",
            event_payload,
        )

    catalog_validation = _validate_catalog(catalog_builder, plan)
    event_validation = validate_event_chain(active_ledger.events, plan)
    expected_event_keys = (
        [f"store:{row.protocol_store_id}" for row in plan.stores]
        + [
            f"common_receiver_freeze:{row.protocol_receiver_id}"
            for row in plan.receivers
        ]
        + [f"evaluation:{row.protocol_cell_id}" for row in plan.cells]
    )
    event_keys_match = [event["key"] for event in active_ledger.events] == expected_event_keys
    grid_validation = validate_result_grid(rows, plan)
    controls: dict[str, bool] = {
        "portable_protocol_plan_valid": bool(plan_validation["valid"]),
        "source_matrices_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_matrix_digest"]
            == source_diagnostics["R6i"]["source_matrix_digest"]
        ),
        "source_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_coordinate_digest"]
            == source_diagnostics["R6i"]["source_coordinate_digest"]
        ),
        "perturbed_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["perturbed_coordinate_digest"]
            == source_diagnostics["R6i"]["perturbed_coordinate_digest"]
        ),
        "twelve_common_receivers_frozen": len(bundles) == 12,
        "all_receivers_and_naimark_controls_valid": all(
            bundle.receiver.diagnostics["valid"]
            and all(value <= TOL for value in bundle.residuals.values())
            for bundle in bundles
        ),
        "all_probability_rows_valid_without_repair": all(
            row["validation"]["pre_label_valid"]
            and row["validation"]["post_label_valid"]
            for row in rows
        ),
        "exact_portable_result_grid": bool(grid_validation["valid"]),
        "exact_catalog_surface": bool(catalog_validation["valid"]),
        "exact_event_chain": bool(event_validation["valid"]),
        "event_keys_match_portable_plan": event_keys_match,
        "ledger_root_is_final_event_digest": (
            bool(active_ledger.events)
            and active_ledger.root == active_ledger.events[-1]["event_digest"]
        ),
    }
    if set(controls) != set(SCIENTIFIC_CONTROL_NAMES):
        raise AssertionError("scientific control surface drifted from its closed schema")
    if additional_controls is not None:
        if set(additional_controls) != set(PROVENANCE_CONTROL_NAMES):
            raise ValueError("external provenance control set differs from the frozen set")
        collisions = set(additional_controls) & set(controls)
        if collisions:
            raise ValueError(f"external controls collide with scientific controls: {collisions}")
        if not all(type(value) is bool for value in additional_controls.values()):
            raise TypeError("external provenance controls must be Booleans")
        controls.update(additional_controls)
    decision = classify_protocol(rows, controls, plan=plan)
    catalog = catalog_builder.finalize()
    report = {
        "schema_version": "hypercomplexbrain.r6l-common-receiver.v1",
        "round": "QSigma-R6l",
        "experiment_kind": "deterministic one-shot associative retrieval with a common receiver",
        "effective_protocol_digest": plan.effective_protocol_digest,
        "ambient_dimension": AMBIENT_DIM,
        "state_noise_strengths": list(STATE_NOISE_STRENGTHS),
        "receiver_label_noise_strengths": list(LABEL_NOISE_STRENGTHS),
        "sample_size": len(rows),
        "sample_unit": (
            "distinct deterministic map/task/depth/state-noise/label-noise "
            "protocol cells; not trials, replicates, seeds, or inferential observations"
        ),
        "input_hashes": [row["protocol_cell_id"] for row in rows],
        "source_diagnostics": source_diagnostics,
        "receiver_summaries": receiver_summaries,
        "retrieval_rows": rows,
        "grid_validation": grid_validation,
        "catalog_validation": catalog_validation,
        "event_validation": event_validation,
        "ledger_root": active_ledger.root,
        "event_count": len(active_ledger.events),
        "checks": controls,
        "decision": decision,
        "global_winner": None,
        "architecture_or_hardware_claim_authorized": False,
        "typed_remainders": [
            {
                "kind": "decoder_remainder",
                "statement": "The conclusion is specific to the frozen shared computational basis and pooled PGM."
            },
            {
                "kind": "capacity_remainder",
                "statement": "This finite-grid retrieval is not temporal memory capacity or an asymptotic coding theorem."
            },
            {
                "kind": "noise_remainder",
                "statement": "The two frozen channels are controlled stresses, not a device noise model."
            },
            {
                "kind": "resource_remainder",
                "statement": "The canonical full-system Lueders dilation is a structural allocation, not minimum circuit complexity."
            },
            {
                "kind": "independence_remainder",
                "statement": "A producer run remains independent=false until a separate semantic recomputation sidecar passes."
            },
        ],
    }
    return ProtocolRun(
        report=report,
        catalog=catalog,
        arrays=dict(catalog_builder.arrays),
        decision=decision,
        events=active_ledger.events,
    )


_RESULT_ROW_FIELDS = frozenset({
    "protocol_cell_id", "identity", "protocol_receiver_id", "map",
    "receiver_index", "task", "depth_index", "rho_decimal", "classes",
    "eta_index", "eta_decimal", "epsilon_index", "epsilon_decimal",
    "producer_array_bindings", "metrics", "validation",
})


def validate_result_grid(
    rows: Sequence[Mapping[str, object]],
    plan: ProtocolPlan | None = None,
) -> dict:
    plan_value = plan if plan is not None else plan_protocol()
    reasons: list[str] = []
    if len(rows) != 384:
        reasons.append(f"expected 384 rows, observed {len(rows)}")
    for index, (row, cell) in enumerate(zip(rows, plan_value.cells)):
        try:
            if type(row) is not dict:
                raise TypeError("result row must be a plain dictionary")
            if set(row) != _RESULT_ROW_FIELDS:
                raise ValueError("result row field set is not closed")
            identity = _plain_dict(row["identity"], name="portable result identity")
            if not _canonical_json_equal(identity, cell.identity):
                raise ValueError("portable identity object mismatch")
            if protocol_cell_id(identity) != cell.protocol_cell_id:
                raise ValueError("portable identity digest mismatch")
            _require_sha256(row["protocol_cell_id"], name="result cell ID")
            if row["protocol_cell_id"] != cell.protocol_cell_id:
                raise ValueError("portable cell ID mismatch")
            _require_sha256(row["protocol_receiver_id"], name="result receiver ID")
            if row["protocol_receiver_id"] != cell.receiver.protocol_receiver_id:
                raise ValueError("portable receiver ID mismatch")
            coordinate_values = (
                row["map"], row["receiver_index"], row["task"],
                row["depth_index"], row["rho_decimal"], row["classes"],
                row["eta_index"], row["eta_decimal"], row["epsilon_index"],
                row["epsilon_decimal"],
            )
            expected_values = (
                cell.map_name, cell.receiver.receiver_index, cell.receiver.task,
                cell.receiver.depth_index, cell.receiver.rho_decimal,
                cell.receiver.classes, cell.eta_index, cell.eta_decimal,
                cell.epsilon_index, cell.epsilon_decimal,
            )
            if not _canonical_json_equal(coordinate_values, expected_values):
                raise ValueError("result coordinates differ from portable plan")
            bindings = _plain_dict(
                row["producer_array_bindings"], name="producer array bindings"
            )
            if set(bindings) != set(_BINDING_FIELDS):
                raise ValueError("producer binding field set is not closed")
            for name, value in bindings.items():
                _require_sha256(value, name=f"producer binding {name}")
            metrics = _plain_dict(row["metrics"], name="result metrics")
            _validate_metric_values(metrics)
            validation = _plain_dict(row["validation"], name="result validation")
            if set(validation) != {"pre_label_valid", "post_label_valid"}:
                raise ValueError("validation field set is not closed")
            if not all(type(value) is bool for value in validation.values()):
                raise ValueError("validation fields are not Booleans")
            if not all(value is True for value in validation.values()):
                raise ValueError("probability validation contains a failed control")
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            reasons.append(f"row {index}: {exc}")
    ids = [
        row.get("protocol_cell_id")
        for row in rows
        if isinstance(row, Mapping) and type(row.get("protocol_cell_id")) is str
    ]
    if len(ids) != len(set(ids)):
        reasons.append("result cell IDs are not unique")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "expected_cells": 384,
        "observed_cells": len(rows),
        "unique_protocol_cell_ids": len(set(ids)),
    }


def _cell_difference(first: Mapping[str, object], second: Mapping[str, object]) -> dict:
    first_metrics = first["metrics"]
    second_metrics = second["metrics"]
    return {
        "correct_probability": float(second_metrics["correct_probability"])
        - float(first_metrics["correct_probability"]),
        "mutual_information_bits": float(second_metrics["mutual_information_bits"])
        - float(first_metrics["mutual_information_bits"]),
        "mean_reject_probability": float(second_metrics["mean_reject_probability"])
        - float(first_metrics["mean_reject_probability"]),
    }


def _differential_pass(
    first_metrics: Mapping[str, object],
    second_metrics: Mapping[str, object],
    classes: int,
) -> bool:
    """Frozen zero-extra-tolerance R6i-minus-R6 cell predicate."""

    return bool(
        float(second_metrics["correct_probability"])
        - float(first_metrics["correct_probability"])
        >= 1.0 / classes
        and float(second_metrics["mutual_information_bits"])
        - float(first_metrics["mutual_information_bits"])
        >= 0.02
    )


def _hold_decision(
    typed_controls: Mapping[str, bool], *, valid_grid: bool = False,
) -> dict:
    neutral_counts = (
        {
            f"e{eta_index:02d}_l{epsilon_index:02d}": 0
            for eta_index in range(4)
            for epsilon_index in range(4)
        }
        if valid_grid
        else {}
    )
    return {
        "schema_version": "hypercomplexbrain.r6l-decision.v1",
        "verdict": "HOLD",
        "controls_pass": False,
        "failed_controls": sorted(
            key for key, value in typed_controls.items() if value is not True
        ),
        "signed_survival": False,
        "projective_survival": False,
        "radial_survival": False,
        "joint_survival": False,
        "clean_projective_passing_depth_count": 0,
        "signed_passing_depth_counts_by_eta_epsilon": dict(neutral_counts),
        "projective_passing_depth_counts_by_eta_epsilon": dict(neutral_counts),
        "radial_cells": [],
        "joint_cells": [],
        "paired_differential_cells": [],
        "absolute_metrics_preserved_in_retrieval_rows": valid_grid,
        "global_winner": None,
        "decision_semantics": (
            "Every survival field is an R6i-minus-R6 differential predicate; "
            "it is not an absolute-information or global-winner statement."
        ),
    }


def classify_protocol(
    rows: Sequence[Mapping[str, object]],
    controls: Mapping[str, bool],
    *,
    plan: ProtocolPlan | None = None,
) -> dict:
    """Apply HOLD precedence and the frozen unrounded differential thresholds."""

    plan_value = plan if plan is not None else plan_protocol()
    grid = validate_result_grid(rows, plan_value)
    caller_controls_present = bool(controls)
    control_keys_are_strings = all(type(key) is str for key in controls)
    typed_controls = {
        key: value if type(value) is bool else False
        for key, value in controls.items()
        if type(key) is str
    }
    if not caller_controls_present:
        typed_controls["caller_control_surface_present"] = False
    if not control_keys_are_strings:
        typed_controls["caller_control_keys_are_strings"] = False
    typed_controls["exact_portable_result_grid"] = bool(grid["valid"])
    if not grid["valid"]:
        typed_controls["paired_common_bindings_equal"] = False
        return _hold_decision(typed_controls)
    by_key = {
        (
            row["map"], row["receiver_index"], row["eta_index"],
            row["epsilon_index"],
        ): row
        for row in rows
        if all(
            field in row
            for field in ("map", "receiver_index", "eta_index", "epsilon_index")
        )
    }
    common_binding_fields = (
        "pooled_template_digest",
        "common_receiver_digest",
        "state_channel_digest",
        "receiver_label_channel_digest",
        "receiver_label_matrix_digest",
        "structural_receiver_cost_digest",
        "prior_and_perturbation_definition_digest",
    )
    common_bindings_equal = True
    for spec in plan_value.receivers:
        for eta_index, (eta_decimal, _) in enumerate(NOISE_COORDS):
            for epsilon_index, (epsilon_decimal, _) in enumerate(NOISE_COORDS):
                first = by_key.get(("R6", spec.receiver_index, eta_index, epsilon_index))
                second = by_key.get(("R6i", spec.receiver_index, eta_index, epsilon_index))
                if first is None or second is None:
                    continue
                first_bindings = first["producer_array_bindings"]
                second_bindings = second["producer_array_bindings"]
                if any(
                    first_bindings[field] != second_bindings[field]
                    for field in common_binding_fields
                ):
                    common_bindings_equal = False
    typed_controls["paired_common_bindings_equal"] = common_bindings_equal
    if not caller_controls_present or not all(
        value is True for value in typed_controls.values()
    ):
        return _hold_decision(typed_controls, valid_grid=True)

    comparisons: list[dict] = []
    for spec in plan_value.receivers:
        for eta_index, (eta_decimal, _) in enumerate(NOISE_COORDS):
            for epsilon_index, (epsilon_decimal, _) in enumerate(NOISE_COORDS):
                first = by_key[("R6", spec.receiver_index, eta_index, epsilon_index)]
                second = by_key[("R6i", spec.receiver_index, eta_index, epsilon_index)]
                difference = _cell_difference(first, second)
                passes = _differential_pass(
                    first["metrics"], second["metrics"], spec.classes
                )
                comparisons.append({
                    "receiver_index": spec.receiver_index,
                    "task": spec.task,
                    "depth_index": spec.depth_index,
                    "rho_decimal": spec.rho_decimal,
                    "classes": spec.classes,
                    "eta_index": eta_index,
                    "eta_decimal": eta_decimal,
                    "epsilon_index": epsilon_index,
                    "epsilon_decimal": epsilon_decimal,
                    "passes": passes,
                    "R6_protocol_cell_id": first["protocol_cell_id"],
                    "R6i_protocol_cell_id": second["protocol_cell_id"],
                    **difference,
                })

    signed_counts: dict[str, int] = {}
    projective_counts: dict[str, int] = {}
    radial_cells: list[dict] = []
    joint_cells: list[dict] = []
    for eta_index in range(4):
        for epsilon_index in range(4):
            key = f"e{eta_index:02d}_l{epsilon_index:02d}"
            selected = [
                row for row in comparisons
                if row["eta_index"] == eta_index
                and row["epsilon_index"] == epsilon_index
            ]
            signed_counts[key] = sum(
                int(row["passes"])
                for row in selected if row["task"] == "signed_fixed_depth"
            )
            projective_counts[key] = sum(
                int(row["passes"])
                for row in selected if row["task"] == "projective_fixed_depth"
            )
            radial_cells.extend(row for row in selected if row["task"] == "radial")
            joint_cells.extend(
                row for row in selected if row["task"] == "joint_depth_projective"
            )
    signed_survival = len(signed_counts) == 16 and all(
        count >= 3 for count in signed_counts.values()
    )
    projective_survival = len(projective_counts) == 16 and all(
        count >= 3 for count in projective_counts.values()
    )
    radial_survival = len(radial_cells) == 16 and all(row["passes"] for row in radial_cells)
    joint_survival = len(joint_cells) == 16 and all(row["passes"] for row in joint_cells)
    clean_projective_passing_depth_count = sum(
        int(row["passes"])
        for row in comparisons
        if row["task"] == "projective_fixed_depth"
        and row["eta_index"] == 0
        and row["epsilon_index"] == 0
    )
    controls_pass = bool(typed_controls) and all(
        value is True for value in typed_controls.values()
    )
    if not controls_pass:
        verdict = "HOLD"
    elif projective_survival:
        verdict = "COMMON_RECEIVER_PROJECTIVE_GAIN_SURVIVES"
    elif clean_projective_passing_depth_count >= 3:
        verdict = "COMMON_RECEIVER_PROJECTIVE_GAIN_FRAGILE"
    else:
        verdict = "COMMON_RECEIVER_PROJECTIVE_GAIN_ABSENT"
    return {
        "schema_version": "hypercomplexbrain.r6l-decision.v1",
        "verdict": verdict,
        "controls_pass": controls_pass,
        "failed_controls": sorted(
            key for key, value in typed_controls.items() if value is not True
        ),
        "signed_survival": signed_survival,
        "projective_survival": projective_survival,
        "radial_survival": radial_survival,
        "joint_survival": joint_survival,
        "clean_projective_passing_depth_count": clean_projective_passing_depth_count,
        "signed_passing_depth_counts_by_eta_epsilon": signed_counts,
        "projective_passing_depth_counts_by_eta_epsilon": projective_counts,
        "radial_cells": radial_cells,
        "joint_cells": joint_cells,
        "paired_differential_cells": comparisons,
        "absolute_metrics_preserved_in_retrieval_rows": True,
        "global_winner": None,
        "decision_semantics": (
            "Every survival field is an R6i-minus-R6 differential predicate; "
            "it is not an absolute-information or global-winner statement."
        ),
    }
