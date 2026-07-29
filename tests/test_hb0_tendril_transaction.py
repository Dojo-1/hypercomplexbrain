from __future__ import annotations

import numpy as np
import pytest

from aionq.governance import GovernanceError
from aionq.hb0 import (
    CarrierMismatch,
    ChartFunctor,
    build_hb0,
)


def _world_snapshot(kernel) -> dict[str, np.ndarray]:
    return {
        worldlet_id: worldlet.coordinates.copy()
        for worldlet_id, worldlet in kernel.worldlets.items()
    }


def _identity_snapshot(kernel) -> dict[str, np.ndarray]:
    return {
        regime_id: regime.section.copy()
        for regime_id, regime in kernel.identity.regimes.items()
    }


def _assert_vectors_equal(
    expected: dict[str, np.ndarray],
    actual: dict[str, object],
) -> None:
    assert set(expected) == set(actual)
    for key, vector in expected.items():
        candidate = (
            actual[key].coordinates
            if hasattr(actual[key], "coordinates")
            else actual[key].section
        )
        assert np.array_equal(vector, candidate), key


def _authorization(kernel, tendril_id: str = "T_00") -> dict[str, float]:
    return {"compute": kernel.tendrils[tendril_id].cost}


def _changed_worldlets(
    before: dict[str, np.ndarray],
    kernel,
) -> set[str]:
    return {
        worldlet_id
        for worldlet_id, coordinates in before.items()
        if not np.array_equal(
            coordinates,
            kernel.worldlets[worldlet_id].coordinates,
        )
    }


def test_active_tendril_transaction_moves_only_declared_target():
    kernel = build_hb0(seed=0)
    before = _world_snapshot(kernel)
    identity_before = _identity_snapshot(kernel)

    report = kernel.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(kernel),
    )

    assert report.accepted
    assert report.committed
    assert report.mode == "active"
    assert report.declared_target == "W_somatic_01"
    assert report.selected_target == report.declared_target
    assert _changed_worldlets(before, kernel) == {report.declared_target}
    assert report.committed_delta_norm > 0.0
    np.testing.assert_allclose(
        report.committed_delta,
        kernel.worldlets[report.declared_target].coordinates
        - before[report.declared_target],
        atol=0.0,
        rtol=0.0,
    )
    assert report.alignment_after < report.alignment_before
    assert report.alignment_after == pytest.approx(
        report.alignment_if_committed
    )
    assert report.transport_remainder.name == "[R]_transport"
    assert report.transport_remainder.magnitude == pytest.approx(0.0, abs=1e-12)
    assert report.return_fidelity == pytest.approx(1.0, abs=1e-12)
    _assert_vectors_equal(identity_before, kernel.identity.regimes)
    assert kernel.tick == 1
    assert kernel.tendril_ledger == [report]


def test_disabled_tendril_control_has_zero_committed_delta_with_matched_cost():
    active = build_hb0(seed=1)
    disabled = build_hb0(seed=1)
    active_report = active.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(active),
    )
    before = _world_snapshot(disabled)

    report = disabled.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(disabled),
        mode="disabled_control",
    )

    assert report.accepted
    assert not report.committed
    assert report.proposed_delta_norm > 0.0
    assert report.committed_delta_norm == 0.0
    assert report.alignment_after == report.alignment_before
    assert report.transported_output == active_report.transported_output
    assert report.cost == active_report.cost
    assert report.proposed_delta == active_report.proposed_delta
    _assert_vectors_equal(before, disabled.worldlets)


def test_shuffled_target_control_does_not_move_declared_target():
    active = build_hb0(seed=2)
    shuffled = build_hb0(seed=2)
    active_report = active.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(active),
    )
    before = _world_snapshot(shuffled)

    report = shuffled.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(shuffled),
        mode="shuffled_target_control",
        control_target="W_somatic_02",
    )

    assert report.accepted and report.committed
    assert report.declared_target == "W_somatic_01"
    assert report.selected_target == "W_somatic_02"
    assert np.array_equal(
        before[report.declared_target],
        shuffled.worldlets[report.declared_target].coordinates,
    )
    assert _changed_worldlets(before, shuffled) == {report.selected_target}
    assert report.transported_output == active_report.transported_output
    assert report.cost == active_report.cost
    assert report.coupling == active_report.coupling
    assert report.permeability == active_report.permeability


def test_tendril_governance_rejection_rolls_back_all_domain_state():
    kernel = build_hb0(seed=3)
    worlds_before = _world_snapshot(kernel)
    identity_before = _identity_snapshot(kernel)

    report = kernel.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources={},
    )

    assert not report.accepted
    assert not report.committed
    assert "compute" in report.governance_reasons
    assert report.committed_delta_norm == 0.0
    _assert_vectors_equal(worlds_before, kernel.worldlets)
    _assert_vectors_equal(identity_before, kernel.identity.regimes)


def test_tendril_commit_exception_is_atomic_and_creates_no_partial_ledger_entry():
    kernel = build_hb0(seed=4)
    worlds_before = _world_snapshot(kernel)
    identity_before = _identity_snapshot(kernel)
    budget_before = kernel._budget_snapshot()
    tick_before = kernel.tick
    ledger_before = tuple(kernel.tendril_ledger)

    def fail_after_commit(_step: int) -> str:
        kernel.budget.level -= 1.0
        raise RuntimeError("synthetic budget failure after target assignment")

    kernel.budget.tick = fail_after_commit  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="after target assignment"):
        kernel.transact_tendril(
            "T_00",
            coupling=0.5,
            authorized_sources=_authorization(kernel),
        )

    _assert_vectors_equal(worlds_before, kernel.worldlets)
    _assert_vectors_equal(identity_before, kernel.identity.regimes)
    assert kernel.tick == tick_before
    assert kernel._budget_snapshot() == budget_before
    assert tuple(kernel.tendril_ledger) == ledger_before


def test_tendril_transaction_rejects_complex_output_without_casting():
    kernel = build_hb0(seed=5)
    tendril = kernel.tendrils["T_00"]
    original = tendril.chart
    tendril.chart = ChartFunctor(
        id=original.id,
        source_carrier=original.source_carrier,
        target_carrier=original.target_carrier,
        forward=lambda x: x.astype(complex) + 1j * np.ones_like(x),
        backward=original.backward,
        preserved=original.preserved,
        transformed=original.transformed,
        lost=original.lost,
    )
    worlds_before = _world_snapshot(kernel)
    identity_before = _identity_snapshot(kernel)
    budget_before = kernel._budget_snapshot()

    with pytest.raises(CarrierMismatch, match="complex-valued"):
        kernel.transact_tendril(
            "T_00",
            coupling=0.5,
            authorized_sources=_authorization(kernel),
        )

    _assert_vectors_equal(worlds_before, kernel.worldlets)
    _assert_vectors_equal(identity_before, kernel.identity.regimes)
    assert kernel.tick == 0
    assert kernel._budget_snapshot() == budget_before
    assert kernel.tendril_ledger == []


def test_tendril_transaction_requires_a_return_map():
    kernel = build_hb0(seed=5)
    tendril = kernel.tendrils["T_00"]
    original = tendril.chart
    tendril.chart = ChartFunctor(
        id=original.id,
        source_carrier=original.source_carrier,
        target_carrier=original.target_carrier,
        forward=original.forward,
        backward=None,
        preserved=original.preserved,
        transformed=original.transformed,
        lost=original.lost,
        return_absent_reason="one-way control used to test the transaction gate",
    )
    worlds_before = _world_snapshot(kernel)

    with pytest.raises(GovernanceError, match="explicit return map"):
        kernel.transact_tendril(
            "T_00",
            coupling=0.5,
            authorized_sources=_authorization(kernel),
        )

    _assert_vectors_equal(worlds_before, kernel.worldlets)
    assert kernel.tick == 0
    assert kernel.tendril_ledger == []


def test_tendril_transaction_requires_explicit_compute_authorization():
    kernel = build_hb0(seed=6)
    rejected = kernel.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources={"coherence": 10.0},
    )
    assert not rejected.accepted
    assert rejected.viability.feasible
    assert rejected.governance_reasons == ("compute",)


def test_tendril_transaction_is_seed_deterministic():
    first = build_hb0(seed=7)
    second = build_hb0(seed=7)

    first_report = first.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(first),
    )
    second_report = second.transact_tendril(
        "T_00",
        coupling=0.5,
        authorized_sources=_authorization(second),
    )

    assert first_report == second_report
    for worldlet_id in first.worldlets:
        assert np.array_equal(
            first.worldlets[worldlet_id].coordinates,
            second.worldlets[worldlet_id].coordinates,
        )
