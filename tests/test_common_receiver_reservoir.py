from __future__ import annotations

import ast
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import aionq.common_receiver_reservoir as r6l
import run_common_receiver_reservoir as runner
from aionq.equal_resource_reservoir import AMBIENT_DIM, TaskEnsemble


ROOT = Path(__file__).resolve().parent.parent
SHA = "sha256:" + "a" * 64


@pytest.fixture(autouse=True)
def _forbid_target_execution(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("the source-contract suite must not execute R6l numerics")

    monkeypatch.setattr(r6l, "build_map_tasks", forbidden)
    monkeypatch.setattr(r6l, "execute_protocol", forbidden)
    monkeypatch.setattr(runner, "execute_protocol", forbidden)
    monkeypatch.setattr(runner, "build_map_tasks", forbidden)


def _basis_density(index: int) -> np.ndarray:
    value = np.zeros((AMBIENT_DIM, AMBIENT_DIM), dtype=complex)
    value[index, index] = 1.0
    return value


def _radial_fixture() -> tuple[r6l.ReceiverSpec, dict[str, tuple[TaskEnsemble, ...]]]:
    spec = r6l.plan_protocol().receivers[10]
    first = tuple(_basis_density(index) for index in range(5))
    second = tuple(_basis_density(index + 5) for index in range(5))
    return spec, {
        "R6": (TaskEnsemble("radial", first, first, None),),
        "R6i": (TaskEnsemble("radial", second, second, None),),
    }


def _digest_for(*parts: object) -> str:
    return r6l.canonical_digest(list(parts))


def _bindings(cell: r6l.CellSpec) -> dict[str, str]:
    receiver = cell.receiver.receiver_index
    common_coordinates = {
        "pooled_template_digest": (receiver,),
        "common_receiver_digest": (receiver,),
        "state_channel_digest": (cell.eta_index,),
        "receiver_label_channel_digest": (receiver, cell.epsilon_index),
        "receiver_label_matrix_digest": (receiver, cell.epsilon_index),
        "structural_receiver_cost_digest": (receiver,),
        "prior_and_perturbation_definition_digest": (receiver,),
    }
    output: dict[str, str] = {}
    for field in r6l._BINDING_FIELDS:
        coordinates = common_coordinates.get(
            field,
            (
                cell.map_name,
                receiver,
                cell.eta_index,
                cell.epsilon_index,
            ),
        )
        output[field] = _digest_for(field, *coordinates)
    return output


def _metrics(*, correct: float, information: float) -> dict[str, float]:
    values = {field: 0.0 for field in r6l._METRIC_FIELDS}
    values["correct_probability"] = correct
    values["mutual_information_bits"] = information
    values["conditional_correct_probability_given_nonreject"] = correct
    return values


def _result_rows(pass_predicate) -> tuple[r6l.ProtocolPlan, list[dict]]:
    plan = r6l.plan_protocol()
    rows: list[dict] = []
    for cell in plan.cells:
        passes = bool(pass_predicate(cell))
        if cell.map_name == "R6":
            correct = 0.0
            information = 0.0
        elif passes:
            correct = 1.0 / cell.receiver.classes
            information = 0.02
        else:
            correct = max(0.0, 1.0 / cell.receiver.classes - 1e-9)
            information = 0.02
        rows.append({
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
            "producer_array_bindings": _bindings(cell),
            "metrics": _metrics(correct=correct, information=information),
            "validation": {
                "pre_label_valid": True,
                "post_label_valid": True,
            },
        })
    return plan, rows


def _store_payload(spec: r6l.StoreSpec) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-event-store.v1",
        "protocol_store_id": spec.protocol_store_id,
        "map": spec.map_name,
        "depth_index": spec.depth_index,
        "rho_decimal": spec.rho_decimal,
        "source_index": spec.source_index,
        "reservoir_key": (
            f"{spec.map_name}:rho={spec.rho_decimal}:k={spec.source_index:02d}"
        ),
        "stored_template_digest": _digest_for("store", spec.protocol_store_id),
    }


def _freeze_payload(spec: r6l.ReceiverSpec) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-event-receiver.v1",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "receiver_index": spec.receiver_index,
        "task": spec.task,
        "depth_index": spec.depth_index,
        "rho_decimal": spec.rho_decimal,
        "classes": spec.classes,
        "clean_map_template_digests": {
            map_name: _digest_for("clean", map_name, spec.receiver_index)
            for map_name in r6l.MAPS
        },
        "pooled_template_digest": _digest_for("pool", spec.receiver_index),
        "common_receiver_digest": _digest_for("receiver", spec.receiver_index),
        "structural_receiver_cost_digest": _digest_for(
            "structure", spec.receiver_index
        ),
        "prior_and_perturbation_definition_digest": _digest_for(
            "prior", spec.receiver_index
        ),
        "support_rank": 1,
        "effect_ranks": [1] * (spec.classes + 1),
        "outcomes_including_reject": spec.classes + 1,
        "padded_outcome_dimension": 1 << (spec.classes + 1).bit_length(),
        "signal_qubits": 4,
        "outcome_ancilla_qubits": (spec.classes + 1).bit_length(),
        "total_qubits": 4 + (spec.classes + 1).bit_length(),
        "residuals": {
            "completeness_spectral": 0.0,
            "support_projector_spectral": 0.0,
            "isometry_spectral": 0.0,
            "maximum_effect_reconstruction_fro": 0.0,
        },
        "controls": {
            "pooled_weights_exact": True,
            "receiver_valid": True,
            "naimark_valid": True,
        },
    }


def _evaluation_payload(cell: r6l.CellSpec) -> dict:
    return {
        "schema_version": "hypercomplexbrain.r6l-event-evaluation.v1",
        "protocol_cell_id": cell.protocol_cell_id,
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
        "producer_array_bindings": _bindings(cell),
        "metrics": _metrics(correct=0.0, information=0.0),
        "validation": {
            "pre_label_valid": True,
            "post_label_valid": True,
        },
    }


def test_frozen_scalar_plan_has_exact_portable_surface_and_known_ids():
    plan = r6l.plan_protocol()
    validation = r6l.validate_protocol_plan(plan)
    assert validation["valid"], validation
    assert (len(plan.stores), len(plan.receivers), len(plan.cells)) == (320, 12, 384)
    assert plan.effective_protocol_digest == r6l.EFFECTIVE_PROTOCOL_DIGEST
    assert plan.receivers[0].protocol_receiver_id == (
        "sha256:9648af25cdeb883168254c0e309f4bb9dfec440d7283b57095b7a734dc20e516"
    )
    assert plan.receivers[-1].protocol_receiver_id == (
        "sha256:8b9531a6ea2f5cd153df595df673f454f30f3d6c905be6a470c567ef92d9a456"
    )
    assert plan.stores[0].protocol_store_id == (
        "sha256:fe97dfa285af337b1c0b4ea2f539b7c1c906297d0830ba7266bc21c04a2775cf"
    )
    assert plan.stores[-1].protocol_store_id == (
        "sha256:7031583146bb38afa0a0e2d5c649ea98c6c05c89bd08383c3bece9c32bac8d20"
    )
    assert plan.cells[0].protocol_cell_id == (
        "sha256:9d8d848673711f3fc43d65121b3bbf346d81b4bdcc2260cf24a27bce5158e862"
    )
    assert plan.cells[-1].protocol_cell_id == (
        "sha256:92164cd4a49946cb3b538f36f54982e6796eb799028138422cc1599a588ee95e"
    )
    with pytest.raises(ValueError):
        r6l.plan_protocol("sha256:x")


def test_plan_validator_rejects_self_consistent_identity_from_another_fiber():
    plan = r6l.plan_protocol()
    stores = list(plan.stores)
    stores[0] = replace(
        stores[0],
        identity=copy.deepcopy(stores[1].identity),
        protocol_store_id=stores[1].protocol_store_id,
    )
    altered = replace(plan, stores=tuple(stores))
    validation = r6l.validate_protocol_plan(altered)
    assert validation["valid"] is False
    assert any("bind its plan coordinates" in reason for reason in validation["reasons"])

    cells = list(plan.cells)
    cells[0] = replace(cells[0], eta=0.9)
    altered_noise = replace(plan, cells=tuple(cells))
    validation = r6l.validate_protocol_plan(altered_noise)
    assert validation["valid"] is False
    assert any("eta float" in reason for reason in validation["reasons"])

    cells = list(plan.cells)
    cells[0] = replace(cells[0], receiver=replace(cells[0].receiver, depth=9.0))
    altered_receiver = replace(plan, cells=tuple(cells))
    validation = r6l.validate_protocol_plan(altered_receiver)
    assert validation["valid"] is False
    assert any("receiver fiber" in reason for reason in validation["reasons"])


@pytest.mark.parametrize(
    ("kind", "mutation"),
    [
        ("receiver", {"receiver_index": True}),
        ("receiver", {"depth_index": False}),
        ("receiver", {"classes": 32.0}),
        ("receiver", {"task": "radial"}),
        ("store", {"rho_decimal": "1e-1"}),
        ("store", {"source_index": False}),
        ("store", {"source_index": 32}),
        ("cell", {"depth_index": False}),
        ("cell", {"classes": 32.0}),
        ("cell", {"eta_decimal": "0.00"}),
        ("cell", {"epsilon_index": False}),
    ],
)
def test_portable_identity_rejects_type_and_coordinate_aliases(kind, mutation):
    plan = r6l.plan_protocol()
    identity = copy.deepcopy({
        "receiver": plan.receivers[0].identity,
        "store": plan.stores[0].identity,
        "cell": plan.cells[0].identity,
    }[kind])
    identity.update(mutation)
    function = {
        "receiver": r6l.protocol_receiver_id,
        "store": r6l.protocol_store_id,
        "cell": r6l.protocol_cell_id,
    }[kind]
    with pytest.raises(ValueError):
        function(identity)


@pytest.mark.parametrize(
    ("surface", "index", "mutation"),
    [
        ("stores", 0, {"depth_index": False}),
        ("stores", 0, {"source_index": False}),
        ("receivers", 0, {"receiver_index": False}),
        ("receivers", 0, {"depth_index": False}),
        ("receivers", 2, {"depth": 1}),
        ("cells", 0, {"eta_index": False}),
        ("cells", 0, {"eta": False}),
        ("cells", 0, {"epsilon_index": False}),
        ("cells", 0, {"epsilon": False}),
        ("cells", 0, {"eta_index": 4}),
    ],
)
def test_plan_validator_rejects_scalar_aliases_without_throwing(
    surface, index, mutation,
):
    plan = r6l.plan_protocol()
    values = list(getattr(plan, surface))
    values[index] = replace(values[index], **mutation)
    altered = replace(plan, **{surface: tuple(values)})
    validation = r6l.validate_protocol_plan(altered)
    assert validation["valid"] is False
    assert validation["reasons"]


def test_canonical_json_and_array_records_are_byte_level_and_finite():
    assert r6l.canonical_bytes({"b": 1, "a": "μ"}) == (
        '{"a":"μ","b":1}'.encode("utf-8")
    )
    array = np.array([[1 + 2j, 3 - 4j]], dtype=np.complex64)
    little = np.ascontiguousarray(array, dtype="<c16")
    record = r6l.complex_array_record(array, index=2, role="fixture")
    assert record == {
        "index": 2,
        "role": "fixture",
        "shape": [1, 2],
        "dtype": "<c16",
        "array_digest": "sha256:" + hashlib.sha256(little.tobytes()).hexdigest(),
    }
    with pytest.raises(ValueError):
        r6l.real_array_record(np.array([np.nan]), index=0, role="bad")
    with pytest.raises(ValueError):
        r6l.canonical_bytes({"not_finite": float("inf")})


def test_common_receiver_is_exact_classwise_half_sum_and_shared_naimark_map():
    spec, tasks_by_map = _radial_fixture()
    bundle = r6l.build_common_receiver_bundle(spec, tasks_by_map)
    assert bundle.receiver.diagnostics["valid"] is True
    assert bundle.support_rank == 10
    assert bundle.effect_ranks == (2, 2, 2, 2, 2, 6)
    for index, pooled in enumerate(bundle.pooled_templates):
        assert np.array_equal(
            pooled,
            0.5 * tasks_by_map["R6"][0].templates[index]
            + 0.5 * tasks_by_map["R6i"][0].templates[index],
        )
    assert bundle.outcome_dimension == 8
    assert bundle.outcome_ancilla_qubits == 3
    assert bundle.naimark_isometry.shape == (8 * AMBIENT_DIM, AMBIENT_DIM)
    effects = bundle.receiver.effects + (bundle.receiver.reject_effect,)
    for outcome, effect in enumerate(effects):
        block = bundle.naimark_isometry[
            AMBIENT_DIM * outcome:AMBIENT_DIM * (outcome + 1)
        ]
        assert block @ block == pytest.approx(effect, abs=1e-12)
    assert bundle.naimark_isometry[6 * AMBIENT_DIM:] == pytest.approx(0.0)
    assert bundle.naimark_isometry.conj().T @ bundle.naimark_isometry == (
        pytest.approx(np.eye(AMBIENT_DIM), abs=1e-12)
    )


def test_principal_sqrt_clamps_only_tolerated_negative_and_uses_rank_cutoff():
    effect = np.zeros((AMBIENT_DIM, AMBIENT_DIM), dtype=complex)
    effect[0, 0] = 1.0
    effect[1, 1] = -5e-11
    effect[2, 2] = 1e-16
    root, residual, values = r6l._principal_psd_sqrt(effect)
    assert residual == pytest.approx(5e-11, rel=0.0, abs=1e-15)
    assert np.min(values) == 0.0
    assert r6l._effect_rank(values) == 1
    assert root[0, 0] == pytest.approx(1.0)
    rejected = effect.copy()
    rejected[1, 1] = -1.01e-10
    with pytest.raises(ValueError, match="below the frozen boundary"):
        r6l._principal_psd_sqrt(rejected)


def test_label_channel_matches_frozen_orientation_and_preserves_reject():
    channel = r6l.build_label_channel(3, 0.3)
    expected_channel = np.array([
        [0.7, 0.15, 0.15, 0.0],
        [0.15, 0.7, 0.15, 0.0],
        [0.15, 0.15, 0.7, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    assert channel == pytest.approx(expected_channel)
    pre = np.array([[0.5, 0.2, 0.1, 0.2]])
    post = r6l.apply_label_channel(pre, channel)
    assert post[0] == pytest.approx([0.395, 0.23, 0.175, 0.2])
    assert np.sum(post) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        r6l.build_label_channel(True, 0.1)
    with pytest.raises(ValueError):
        r6l.build_label_channel(3, float("nan"))


def test_probability_validation_is_raw_and_never_repairs_rows():
    valid = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    returned, diagnostics = r6l._validate_probability_table(valid, expected_rows=2)
    assert np.array_equal(returned, valid)
    assert diagnostics["valid"] is True
    invalid = valid.copy()
    invalid[0, 0] = 1.0 + 2e-10
    with pytest.raises(ValueError, match="without repair"):
        r6l._validate_probability_table(invalid, expected_rows=2)


def test_hash_ledger_has_exact_716_event_blocks_and_canonical_lf(tmp_path):
    plan = r6l.plan_protocol()
    path = tmp_path / "events.jsonl"
    with r6l.HashChainedEventLedger(path) as ledger:
        for spec in plan.stores:
            ledger.append("store", f"store:{spec.protocol_store_id}", _store_payload(spec))
        for spec in plan.receivers:
            ledger.append(
                "common_receiver_freeze",
                f"common_receiver_freeze:{spec.protocol_receiver_id}",
                _freeze_payload(spec),
            )
        for cell in plan.cells:
            ledger.append(
                "evaluation",
                f"evaluation:{cell.protocol_cell_id}",
                _evaluation_payload(cell),
            )
        events = ledger.events
        root = ledger.root
    validation = r6l.validate_event_chain(events)
    assert validation == {
        "valid": True,
        "reasons": [],
        "event_count": 716,
        "unique_keys": 716,
        "ledger_root": root,
    }
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    lines = raw.splitlines(keepends=True)
    assert len(lines) == 716
    assert all(line == r6l.canonical_bytes(event) + b"\n" for line, event in zip(lines, events))
    tampered = [dict(event) for event in events]
    tampered[400]["previous_event_digest"] = SHA
    assert r6l.validate_event_chain(tampered)["valid"] is False


def test_event_chain_rejects_fully_rehashed_plan_reordering_and_snapshots_payload():
    plan = r6l.plan_protocol()
    first_payload = _store_payload(plan.stores[0])
    ledger = r6l.HashChainedEventLedger()
    ledger.append(
        "store", f"store:{plan.stores[0].protocol_store_id}", first_payload
    )
    first_payload["map"] = "R6i"
    assert ledger.events[0]["payload"]["map"] == "R6"

    records: list[tuple[str, str, dict]] = []
    for spec in plan.stores:
        records.append(("store", f"store:{spec.protocol_store_id}", _store_payload(spec)))
    for spec in plan.receivers:
        records.append((
            "common_receiver_freeze",
            f"common_receiver_freeze:{spec.protocol_receiver_id}",
            _freeze_payload(spec),
        ))
    for cell in plan.cells:
        payload = _evaluation_payload(cell)
        payload["producer_array_bindings"] = dict(
            reversed(list(payload["producer_array_bindings"].items()))
        )
        records.append((
            "evaluation", f"evaluation:{cell.protocol_cell_id}", payload
        ))
    records[0], records[1] = records[1], records[0]
    previous = r6l.GENESIS_DIGEST
    rehashed = []
    for sequence, (kind, key, payload) in enumerate(records):
        base = {
            "sequence": sequence,
            "previous_event_digest": previous,
            "kind": kind,
            "key": key,
            "payload": payload,
        }
        event = {**base, "event_digest": r6l.canonical_digest(base)}
        rehashed.append(event)
        previous = event["event_digest"]
    validation = r6l.validate_event_chain(rehashed, plan)
    assert validation["valid"] is False
    assert any("portable plan" in reason for reason in validation["reasons"])


@pytest.mark.parametrize(
    ("kind", "field", "alias"),
    [
        ("common_receiver_freeze", "depth_index", False),
        ("common_receiver_freeze", "classes", 32.0),
        ("common_receiver_freeze", "outcomes_including_reject", 33.0),
        ("common_receiver_freeze", "signal_qubits", 4.0),
        ("evaluation", "depth_index", False),
        ("evaluation", "classes", 32.0),
    ],
)
def test_event_payload_rejects_bool_int_and_float_int_aliases(kind, field, alias):
    plan = r6l.plan_protocol()
    if kind == "common_receiver_freeze":
        spec = plan.receivers[0]
        payload = _freeze_payload(spec)
        key = f"common_receiver_freeze:{spec.protocol_receiver_id}"
    else:
        spec = plan.cells[0]
        payload = _evaluation_payload(spec)
        key = f"evaluation:{spec.protocol_cell_id}"
    payload[field] = alias
    ledger = r6l.HashChainedEventLedger()
    with pytest.raises((TypeError, ValueError)):
        ledger.append(kind, key, payload)


def test_event_chain_rejects_rehashed_float_sequence_alias():
    plan = r6l.plan_protocol()
    spec = plan.stores[0]
    ledger = r6l.HashChainedEventLedger()
    event = copy.deepcopy(ledger.append(
        "store", f"store:{spec.protocol_store_id}", _store_payload(spec)
    ))
    event["sequence"] = 0.0
    base = {
        key: event[key]
        for key in ("sequence", "previous_event_digest", "kind", "key", "payload")
    }
    event["event_digest"] = r6l.canonical_digest(base)
    validation = r6l.validate_event_chain([event], plan)
    assert validation["valid"] is False
    assert any("sequence" in reason for reason in validation["reasons"])


def test_expected_npz_surface_is_exact_and_coordinate_named():
    keys = r6l._expected_npz_keys(r6l.plan_protocol())
    assert len(keys) == 1008
    assert "r00__R6__clean_templates" in keys
    assert "r10__naimark_isometry" in keys
    assert "r11__R6i__e03__l03__post_label_probabilities" in keys


def test_aggregate_identity_determines_its_exact_locator_coordinates():
    plan = r6l.plan_protocol()
    spec = plan.receivers[0]
    items = [
        r6l.complex_array_record(_basis_density(0), index=index, role="clean_template")
        for index in range(spec.classes)
    ]
    aggregate = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": "clean_map_templates",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "map": "R6",
        "items": items,
    }
    r6l._validate_aggregate_contract(aggregate, plan)
    locators = r6l._expected_aggregate_locators(aggregate, plan)
    assert locators[0] == {
        "npz_key": "r00__R6__clean_templates",
        "slice": [0],
    }
    assert all(locator["npz_key"].startswith("r00__R6") for locator in locators)


def test_aggregate_contract_rejects_typed_item_and_structural_aliases():
    plan = r6l.plan_protocol()
    spec = plan.receivers[0]
    items = [
        r6l.complex_array_record(_basis_density(0), index=index, role="clean_template")
        for index in range(spec.classes)
    ]
    aggregate = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": "clean_map_templates",
        "protocol_receiver_id": spec.protocol_receiver_id,
        "map": "R6",
        "items": items,
    }
    for field, alias in (("index", False), ("shape", [16.0, 16])):
        altered = copy.deepcopy(aggregate)
        altered["items"][0][field] = alias
        with pytest.raises((TypeError, ValueError)):
            r6l._validate_aggregate_contract(altered, plan)

    radial = plan.receivers[10]
    roots = [
        r6l.complex_array_record(
            _basis_density(0), index=index, role="sqrt_class_effect"
        )
        for index in range(radial.classes)
    ]
    roots.append(r6l.complex_array_record(
        _basis_density(0), index=radial.classes, role="sqrt_reject_effect"
    ))
    roots.append(r6l.complex_array_record(
        np.zeros((8 * AMBIENT_DIM, AMBIENT_DIM), dtype=complex),
        index=radial.classes + 1,
        role="naimark_isometry",
    ))
    structural = {
        "schema_version": "hypercomplexbrain.r6l-array-aggregate.v1",
        "kind": "structural_receiver_cost",
        "protocol_receiver_id": radial.protocol_receiver_id,
        "signal_dimension": AMBIENT_DIM,
        "classes": radial.classes,
        "outcome_dimension": 8,
        "signal_qubits": 4.0,
        "outcome_ancilla_qubits": 3,
        "total_qubits": 7,
        "effect_ranks": [1] * (radial.classes + 1),
        "items": roots,
    }
    with pytest.raises((TypeError, ValueError)):
        r6l._validate_aggregate_contract(structural, plan)


def test_catalog_artifact_rejects_float_alias_for_integer_key_count():
    catalog = {
        "schema_version": "hypercomplexbrain.r6l-receiver-catalog.v1",
        "npz_key_count": 1008.0,
        "arrays": {},
        "aggregate_locators": {},
        "semantic_objects": {},
        "npz_sha256": SHA,
    }
    validation = r6l.validate_catalog_artifact(
        catalog, {}, npz_sha256=SHA, plan=r6l.plan_protocol()
    )
    assert validation["valid"] is False
    assert any(
        "catalog NPZ key count" in reason for reason in validation["reasons"]
    )


def test_catalog_validator_rejects_complete_names_with_wrong_arrays_and_no_locators():
    plan = r6l.plan_protocol()
    builder = r6l._CatalogBuilder()
    for key in r6l._expected_npz_keys(plan):
        builder.arrays[key] = np.zeros(1, dtype=float)
        builder.array_metadata[key] = {
            "role": "wrong",
            "shape": [1],
            "dtype": "<f8",
            "array_digest": _digest_for(key),
        }
    validation = r6l._validate_catalog(builder, plan)
    assert validation["valid"] is False
    assert any("aggregate objects" in reason for reason in validation["reasons"])
    assert any("exactly once" in reason for reason in validation["reasons"])


def test_survival_verdict_accepts_exact_unrounded_thresholds():
    plan, rows = _result_rows(lambda _cell: True)
    decision = r6l.classify_protocol(rows, {"synthetic_controls": True}, plan=plan)
    assert decision["verdict"] == "COMMON_RECEIVER_PROJECTIVE_GAIN_SURVIVES"
    assert decision["controls_pass"] is True
    assert decision["projective_survival"] is True
    assert decision["clean_projective_passing_depth_count"] == 5
    assert len(decision["paired_differential_cells"]) == 192
    assert all(item["passes"] for item in decision["paired_differential_cells"])


def _assert_neutral_hold_shape(decision: dict, *, valid_grid: bool) -> None:
    assert decision["verdict"] == "HOLD"
    assert decision["controls_pass"] is False
    assert decision["failed_controls"] == sorted(decision["failed_controls"])
    assert all(
        decision[field] is False
        for field in (
            "signed_survival",
            "projective_survival",
            "radial_survival",
            "joint_survival",
        )
    )
    assert decision["clean_projective_passing_depth_count"] == 0
    assert decision["paired_differential_cells"] == []
    assert decision["radial_cells"] == []
    assert decision["joint_cells"] == []
    if valid_grid:
        zero_counts = {
            f"e{eta_index:02d}_l{epsilon_index:02d}": 0
            for eta_index in range(4)
            for epsilon_index in range(4)
        }
        assert decision["signed_passing_depth_counts_by_eta_epsilon"] == zero_counts
        assert decision["projective_passing_depth_counts_by_eta_epsilon"] == zero_counts
        assert decision["absolute_metrics_preserved_in_retrieval_rows"] is True
    else:
        assert decision["signed_passing_depth_counts_by_eta_epsilon"] == {}
        assert decision["projective_passing_depth_counts_by_eta_epsilon"] == {}
        assert decision["absolute_metrics_preserved_in_retrieval_rows"] is False


def test_empty_controls_and_valid_or_invalid_grid_hold_shapes_are_closed():
    plan, rows = _result_rows(lambda _cell: True)

    empty = r6l.classify_protocol(rows, {}, plan=plan)
    _assert_neutral_hold_shape(empty, valid_grid=True)
    assert empty["failed_controls"]

    controls = {
        "zeta_synthetic_control": False,
        "middle_synthetic_control": True,
        "alpha_synthetic_control": False,
    }
    valid_hold = r6l.classify_protocol(rows, controls, plan=plan)
    _assert_neutral_hold_shape(valid_hold, valid_grid=True)
    assert "alpha_synthetic_control" in valid_hold["failed_controls"]
    assert "zeta_synthetic_control" in valid_hold["failed_controls"]

    invalid_hold = r6l.classify_protocol(rows[:-1], controls, plan=plan)
    _assert_neutral_hold_shape(invalid_hold, valid_grid=False)
    assert "exact_portable_result_grid" in invalid_hold["failed_controls"]


@pytest.mark.parametrize("field", ["correct_probability", "mutual_information_bits"])
def test_nextafter_below_either_unrounded_threshold_fails_that_cell(field):
    plan, rows = _result_rows(lambda _cell: True)
    target = next(
        row for row in rows
        if row["map"] == "R6i"
        and row["receiver_index"] == 5
        and row["eta_index"] == 0
        and row["epsilon_index"] == 0
    )
    threshold = 1.0 / target["classes"] if field == "correct_probability" else 0.02
    target["metrics"][field] = float(np.nextafter(threshold, -np.inf))
    if field == "correct_probability":
        target["metrics"]["conditional_correct_probability_given_nonreject"] = target[
            "metrics"
        ][field]
    decision = r6l.classify_protocol(rows, {"synthetic_controls": True}, plan=plan)
    comparison = next(
        item for item in decision["paired_differential_cells"]
        if item["receiver_index"] == 5
        and item["eta_index"] == 0
        and item["epsilon_index"] == 0
    )
    assert comparison["passes"] is False


def test_fragile_absent_and_hold_have_frozen_precedence():
    def fragile(cell: r6l.CellSpec) -> bool:
        if cell.receiver.task != "projective_fixed_depth":
            return True
        limit = 2 if (cell.eta_index, cell.epsilon_index) == (3, 3) else 3
        return cell.receiver.depth_index < limit

    plan, fragile_rows = _result_rows(fragile)
    fragile_decision = r6l.classify_protocol(
        fragile_rows, {"synthetic_controls": True}, plan=plan
    )
    assert fragile_decision["verdict"] == "COMMON_RECEIVER_PROJECTIVE_GAIN_FRAGILE"
    assert fragile_decision["clean_projective_passing_depth_count"] == 3

    def absent(cell: r6l.CellSpec) -> bool:
        return not (
            cell.receiver.task == "projective_fixed_depth"
            and cell.receiver.depth_index >= 2
        )

    plan, absent_rows = _result_rows(absent)
    absent_decision = r6l.classify_protocol(
        absent_rows, {"synthetic_controls": True}, plan=plan
    )
    assert absent_decision["verdict"] == "COMMON_RECEIVER_PROJECTIVE_GAIN_ABSENT"
    assert absent_decision["clean_projective_passing_depth_count"] == 2

    hold = r6l.classify_protocol(
        fragile_rows, {"synthetic_controls": False}, plan=plan
    )
    assert hold["verdict"] == "HOLD"
    assert "synthetic_controls" in hold["failed_controls"]
    assert hold["projective_survival"] is False
    assert hold["clean_projective_passing_depth_count"] == 0
    assert hold["paired_differential_cells"] == []


def test_mismatched_common_binding_forces_hold():
    plan, rows = _result_rows(lambda _cell: True)
    altered = copy.deepcopy(rows)
    r6i_first = next(index for index, row in enumerate(altered) if row["map"] == "R6i")
    altered[r6i_first]["producer_array_bindings"]["common_receiver_digest"] = SHA
    decision = r6l.classify_protocol(
        altered, {"synthetic_controls": True}, plan=plan
    )
    assert decision["verdict"] == "HOLD"
    assert "paired_common_bindings_equal" in decision["failed_controls"]
    assert decision["paired_differential_cells"] == []


def test_failed_probability_control_and_nonhex_binding_force_hold():
    plan, rows = _result_rows(lambda _cell: True)
    failed = copy.deepcopy(rows)
    failed[0]["validation"]["pre_label_valid"] = False
    decision = r6l.classify_protocol(failed, {"synthetic_controls": True}, plan=plan)
    assert decision["verdict"] == "HOLD"
    assert "exact_portable_result_grid" in decision["failed_controls"]

    nonhex = copy.deepcopy(rows)
    nonhex[0]["producer_array_bindings"]["clean_map_template_digest"] = (
        "sha256:" + "g" * 64
    )
    decision = r6l.classify_protocol(nonhex, {"synthetic_controls": True}, plan=plan)
    assert decision["verdict"] == "HOLD"
    assert "exact_portable_result_grid" in decision["failed_controls"]


def test_result_grid_rejects_boolean_metric_and_coordinate_reordering():
    plan, rows = _result_rows(lambda _cell: True)
    broken = copy.deepcopy(rows)
    broken[0]["metrics"]["correct_probability"] = True
    validation = r6l.validate_result_grid(broken, plan)
    assert validation["valid"] is False
    assert any("finite JSON number" in reason for reason in validation["reasons"])
    reordered = list(reversed(rows))
    assert r6l.validate_result_grid(reordered, plan)["valid"] is False

    missing = copy.deepcopy(rows)
    del missing[0]["metrics"]
    hold = r6l.classify_protocol(missing, {"synthetic_controls": False}, plan=plan)
    assert hold["verdict"] == "HOLD"
    assert hold["paired_differential_cells"] == []


@pytest.mark.parametrize(
    ("container", "field", "alias"),
    [
        ("row", "receiver_index", False),
        ("row", "depth_index", False),
        ("row", "classes", 32.0),
        ("row", "eta_index", False),
        ("row", "epsilon_index", False),
        ("identity", "receiver_index", False),
        ("identity", "depth_index", False),
        ("identity", "classes", 32.0),
        ("identity", "eta_index", False),
    ],
)
def test_result_grid_rejects_typed_coordinate_and_identity_aliases(
    container, field, alias,
):
    plan, rows = _result_rows(lambda _cell: True)
    altered = copy.deepcopy(rows)
    if container == "row":
        altered[0][field] = alias
    else:
        altered[0]["identity"][field] = alias
    validation = r6l.validate_result_grid(altered, plan)
    assert validation["valid"] is False
    assert validation["reasons"]


def test_metric_semantics_reject_impossible_conditional_and_reversed_extrema():
    metrics = _metrics(correct=0.2, information=0.1)
    metrics["conditional_correct_probability_given_nonreject"] = 1.1
    with pytest.raises(ValueError, match="outside tolerance"):
        r6l._validate_metric_values(metrics)
    metrics = _metrics(correct=0.2, information=0.1)
    metrics["minimum_pre_label_probability"] = 0.8
    metrics["maximum_pre_label_probability"] = 0.2
    with pytest.raises(ValueError, match="extrema"):
        r6l._validate_metric_values(metrics)


def test_freeze_receipt_reconstructs_effective_digest_and_manifest_hash():
    manifest_path = ROOT / "manifests" / "qsigma_r6l_common_receiver_preregistration.json"
    receipt_path = ROOT / "manifests" / "qsigma_r6l_common_receiver_freeze_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest() == (
        r6l.MANIFEST_SHA256
    )
    assert receipt["preregistration"]["commit_sha"] == r6l.C_PRE_SHA
    assert receipt["preregistration"]["manifest_sha256"] == r6l.MANIFEST_SHA256
    assert receipt["correction_inventory"] == []
    effective = receipt["effective_protocol"]
    assert effective["digest"] == r6l.EFFECTIVE_PROTOCOL_DIGEST
    assert r6l.canonical_digest(effective["object"]) == effective["digest"]
    assert effective["canonical_json"] == r6l.canonical_bytes(
        effective["object"]
    ).decode("utf-8")


def test_runner_surface_is_six_source_paths_and_strict_json(tmp_path):
    assert set(runner.C_EXEC_DELTA_PATHS) == {
        ".gitattributes",
        "manifests/qsigma_r6l_common_receiver_freeze_receipt.json",
        "src/aionq/common_receiver_reservoir.py",
        "tests/test_common_receiver_reservoir.py",
        "experiments/run_common_receiver_reservoir.py",
        "docs/QSIGMA_R6L_COMMON_RECEIVER.md",
    }
    assert len(runner.DECLARED_RAW_PATHS) == 13
    assert runner._parser().parse_args([
        "run", "--output-dir", "artifacts/r6l_common_receiver"
    ]).command == "run"
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        runner._load_json(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"a":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="nonfinite JSON constant"):
        runner._load_json(nonfinite)


@pytest.mark.parametrize(
    ("observed", "expected"),
    [(False, 0), (32.0, 32), ([0], [0.0]), ({"valid": 1}, {"valid": True})],
)
def test_runner_json_exact_rejects_python_scalar_aliases(observed, expected):
    with pytest.raises(ValueError, match="JSON value or type"):
        runner._require_json_exact(observed, expected, name="synthetic alias")


def test_canonical_decision_projection_is_exact_at_threshold_and_hold_first():
    plan, canonical_rows = _result_rows(lambda _cell: True)
    reported_rows = copy.deepcopy(canonical_rows)
    target = next(
        row for row in reported_rows
        if row["map"] == "R6i"
        and row["receiver_index"] == 5
        and row["eta_index"] == 0
        and row["epsilon_index"] == 0
    )
    threshold = 1.0 / target["classes"]
    target["metrics"]["correct_probability"] = float(
        np.nextafter(threshold, -np.inf)
    )
    target["metrics"]["conditional_correct_probability_given_nonreject"] = target[
        "metrics"
    ]["correct_probability"]

    controls = {"synthetic_controls": True}
    canonical = r6l.classify_protocol(canonical_rows, controls, plan=plan)
    reported = r6l.classify_protocol(reported_rows, controls, plan=plan)
    with pytest.raises(ValueError, match="discrete decision"):
        runner._require_json_exact(
            runner._decision_discrete_projection(reported),
            runner._decision_discrete_projection(canonical),
            name="discrete decision",
        )

    failed_controls = {"synthetic_controls": False}
    canonical_hold = r6l.classify_protocol(
        canonical_rows, failed_controls, plan=plan
    )
    reported_hold = r6l.classify_protocol(
        reported_rows, failed_controls, plan=plan
    )
    runner._require_json_exact(
        runner._decision_discrete_projection(reported_hold),
        runner._decision_discrete_projection(canonical_hold),
        name="controls-first HOLD projection",
    )


def test_canonical_decision_projection_excludes_only_declared_numeric_differences():
    plan, first_rows = _result_rows(lambda _cell: True)
    second_rows = copy.deepcopy(first_rows)
    target = next(
        row for row in second_rows
        if row["map"] == "R6i"
        and row["receiver_index"] == 5
        and row["eta_index"] == 0
        and row["epsilon_index"] == 0
    )
    target["metrics"]["correct_probability"] += 5e-11
    target["metrics"]["conditional_correct_probability_given_nonreject"] = target[
        "metrics"
    ]["correct_probability"]
    controls = {"synthetic_controls": True}
    first = r6l.classify_protocol(first_rows, controls, plan=plan)
    second = r6l.classify_protocol(second_rows, controls, plan=plan)
    runner._require_json_exact(
        runner._decision_discrete_projection(first),
        runner._decision_discrete_projection(second),
        name="same discrete decision",
    )
    altered = copy.deepcopy(second)
    altered["paired_differential_cells"][0]["passes"] = False
    with pytest.raises(ValueError):
        runner._require_json_exact(
            runner._decision_discrete_projection(first),
            runner._decision_discrete_projection(altered),
            name="tampered discrete decision",
        )


def test_semantic_tree_tolerance_is_explicitly_path_whitelisted():
    delta, count = runner._compare_tree(
        0.25,
        0.25 + 5e-11,
        path="decision.paired_differential_cells[0].correct_probability",
    )
    assert delta == pytest.approx(5e-11)
    assert count == 1
    with pytest.raises(ValueError, match="exact numeric value/type"):
        runner._compare_tree(384, 384.0, path="result.sample_size")
    with pytest.raises(ValueError, match="exact numeric value/type"):
        runner._compare_tree(
            0.0,
            5e-11,
            path="result.state_noise_strengths[0]",
        )
    with pytest.raises(ValueError, match="numeric/type mismatch"):
        runner._compare_tree(
            False,
            0.0,
            path="decision.paired_differential_cells[0].correct_probability",
        )


def test_lf_attributes_bind_the_attribute_file_and_event_stream():
    lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "/.gitattributes text eol=lf" in lines
    assert "artifacts/r6l_common_receiver/events.jsonl text eol=lf" in lines
    output = runner._run_git(
        "check-attr",
        "-z",
        "text",
        "eol",
        "--",
        ".gitattributes",
        "artifacts/r6l_common_receiver/events.jsonl",
        text=False,
    )
    parts = bytes(output).split(b"\0")
    triples = {
        tuple(part.decode("utf-8") for part in parts[index:index + 3])
        for index in range(0, len(parts) - 2, 3)
    }
    assert (".gitattributes", "text", "set") in triples
    assert (".gitattributes", "eol", "lf") in triples
    assert (
        "artifacts/r6l_common_receiver/events.jsonl",
        "text",
        "set",
    ) in triples
    assert (
        "artifacts/r6l_common_receiver/events.jsonl",
        "eol",
        "lf",
    ) in triples


def test_production_entrypoint_is_not_invoked_by_this_contract_suite():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "execute_protocol" not in called_names | called_attributes
    assert "build_map_tasks" not in called_names | called_attributes


# ------------------------------------------------------- square-root conditioning

def _cutoff_sqrt(effect: np.ndarray) -> np.ndarray:
    """``_principal_psd_sqrt`` with the module's OWN support cutoff applied.

    This is not a proposed rewrite of the sealed module. It is the control
    against which the shipped square root is measured below, and it differs from
    ``_principal_psd_sqrt`` by exactly one line: the cutoff that
    ``_effect_rank`` already computes is used to zero the noise eigenvalues
    before the square root instead of only to report a rank.
    """
    hermitian = (effect + effect.conj().T) / 2.0
    values, vectors = np.linalg.eigh(hermitian)
    values = np.real(values)
    clamped = np.where(values < 0.0, 0.0, values)
    maximum = max(0.0, float(clamped.max()))
    cutoff = 64.0 * np.finfo(np.float64).eps * AMBIENT_DIM * maximum
    supported = np.where(clamped > cutoff, clamped, 0.0)
    return vectors @ np.diag(np.sqrt(supported)) @ vectors.conj().T


def _rank_deficient_effect(rng, rank: int) -> np.ndarray:
    """A PSD effect of exact rank ``rank`` in the D16 ambient space.

    R6l's own effects are rank 2 to 14 of 16 -- every one of them is rank
    deficient -- so the deficient case is the ordinary case, not a corner.
    """
    basis = rng.normal(size=(AMBIENT_DIM, rank)) + 1j * rng.normal(size=(AMBIENT_DIM, rank))
    effect = basis @ basis.conj().T
    return effect / float(np.linalg.norm(effect, "fro"))


def test_the_psd_square_root_is_not_stable_under_a_machine_epsilon_perturbation():
    """The operation that makes R6l unreproducible on a second machine.

    Measured, by running the sealed module's own recompute gate on Linux against
    the artifact produced on Windows: of 13479 matrix comparisons, 11180 are bit
    identical and 258 exceed the module's 1e-10 tolerance. Every one of the 258
    is a matrix square root. The next-worst category of comparison differs by at
    most 2.79e-14, six orders of magnitude below the failures.

    The cause is not the platform, it is the conditioning. sqrt has derivative
    1/(2*sqrt(x)), so an eigenvalue known only to absolute precision eps has a
    square root known only to precision sqrt(eps) ~ 1e-8. A rank-deficient
    effect has eigenvalues whose true value is 0 and whose computed value is
    anything in [-eps, +eps]; their square roots are then anything in
    [0, 1e-8]. That is the observed scale, and no platform is at fault for it.

    This test asserts the defect rather than describing it, on synthetic
    matrices, so it holds on any machine and does not depend on the 30 MB
    artifact.
    """
    rng = np.random.default_rng(20260803)
    shipped, controlled = [], []
    for rank in (2, 6, 10, 14):
        for _ in range(8):
            effect = _rank_deficient_effect(rng, rank)
            noise = rng.normal(size=effect.shape) + 1j * rng.normal(size=effect.shape)
            noise = (noise + noise.conj().T) / 2.0
            perturbed = effect + noise * (
                np.finfo(np.float64).eps
                * np.linalg.norm(effect, "fro")
                / np.linalg.norm(noise, "fro")
            )
            shipped.append(np.linalg.norm(
                r6l._principal_psd_sqrt(effect)[0]
                - r6l._principal_psd_sqrt(perturbed)[0], "fro"))
            controlled.append(np.linalg.norm(
                _cutoff_sqrt(effect) - _cutoff_sqrt(perturbed), "fro"))

    shipped_worst = max(shipped)
    controlled_worst = max(controlled)

    # As shipped, a perturbation at the last bit moves the square root by far
    # more than the tolerance the module then checks it against.
    assert shipped_worst > 1e-10, shipped_worst
    assert shipped_worst > 100.0 * r6l.TOL

    # With the cutoff the module already computes, the same perturbation moves
    # the square root by less than the tolerance, with orders of margin.
    assert controlled_worst < 1e-12, controlled_worst

    # The separation is the finding: this is not a tolerance that needs
    # loosening, it is an operation that needs its own support cutoff applied.
    assert shipped_worst > 1e3 * controlled_worst


def test_every_r6l_effect_is_rank_deficient_so_the_deficient_case_is_the_normal_one():
    """If the effects were full rank the conditioning above would be harmless."""
    rng = np.random.default_rng(11)
    templates = np.stack([
        (lambda m: m @ m.conj().T / float(np.trace(m @ m.conj().T).real))(
            rng.normal(size=(AMBIENT_DIM, 3)) + 1j * rng.normal(size=(AMBIENT_DIM, 3)))
        for _ in range(AMBIENT_DIM)
    ])
    receiver = r6l.build_pgm_receiver(templates, tol=r6l.TOL)
    for effect in receiver.effects + (receiver.reject_effect,):
        values = np.real(np.linalg.eigvalsh((effect + effect.conj().T) / 2.0))
        assert r6l._effect_rank(np.where(values < 0.0, 0.0, values)) < AMBIENT_DIM


def test_the_square_root_divergence_is_quadratically_suppressed_in_the_effect():
    """Why R6l's science survives an unreproducible square root.

    Measured against the committed Windows artifact from Linux: the square roots
    differ by up to 2.281e-08, the effects they square back to differ by only
    4.392e-15, and the scientific leaves of the whole report agree to 7.623e-14
    with none exceeding 1e-9.

    The reason is that the divergence lives entirely in the eigendirections whose
    eigenvalue is below the noise floor. Rotating the difference into the
    effect's own eigenbasis and splitting on the module's support cutoff gives
    2.921e-15 inside the supported subspace against 2.281e-08 touching the noise
    subspace -- a factor of 7.8e6. In those directions the root contributes
    O(sqrt(eps)) to itself and O(eps) to the effect.

    So the square root is a representation choice on the noise subspace, and
    every R6l observable is a function of the effect rather than of its root.
    A gate that compares the root as though it were an observable refuses
    reproductions in which every measured quantity agrees.
    """
    rng = np.random.default_rng(4242)
    root_deltas, effect_deltas = [], []
    for rank in (2, 6, 10, 14):
        for _ in range(8):
            effect = _rank_deficient_effect(rng, rank)
            noise = rng.normal(size=effect.shape) + 1j * rng.normal(size=effect.shape)
            noise = (noise + noise.conj().T) / 2.0
            perturbed = effect + noise * (
                np.finfo(np.float64).eps
                * np.linalg.norm(effect, "fro")
                / np.linalg.norm(noise, "fro"))
            a = r6l._principal_psd_sqrt(effect)[0]
            b = r6l._principal_psd_sqrt(perturbed)[0]
            root_deltas.append(np.linalg.norm(a - b, "fro"))
            effect_deltas.append(np.linalg.norm(a @ a - b @ b, "fro"))

    worst_root = max(root_deltas)
    worst_effect = max(effect_deltas)

    # The root is unstable; the effect it squares back to is not.
    assert worst_root > 1e-10
    assert worst_effect < 1e-12

    # Squaring is what suppresses it, so the suppression must be large.
    assert worst_root > 1e3 * worst_effect
