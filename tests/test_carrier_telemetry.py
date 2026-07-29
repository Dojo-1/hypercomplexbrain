"""Carrier telemetry: the three detectors, and the nulls they must stay silent on.

A detector that always fires is not an instrument. Every test that asserts a
detection has a sibling asserting silence.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.carrier_telemetry import (CARRIER_ORDER, CD_DIMENSION, TAU_LEAK,
                                     bridge_event, carrier_is_sound,
                                     confusion_matrix, detect,
                                     fill_volume_form_distortion, trace_word)
from aionq.quantum_channel_geometry import volume_form_distortion

CLEAN = [(0.20, 0.0, 0.0), (0.25, 0.3, 0.2), (0.30, 0.6, 0.4), (0.35, 0.9, 0.6)]


# --------------------------------------------------------------- the ladder

@pytest.mark.parametrize("carrier,dim", [("R", 1), ("H", 4), ("O", 8)])
def test_ladder_is_sound_through_octonions(carrier, dim):
    assert CD_DIMENSION[carrier] == dim
    s = carrier_is_sound(dim)
    assert s["is_sound"] and s["hopf_fibration_exists"] and not s["has_zero_divisor"]


@pytest.mark.parametrize("carrier", ["CD32", "A_n"])
def test_ladder_is_unsound_above_octonions(carrier):
    """Computed by an actual zero-divisor search, not tabulated."""
    s = carrier_is_sound(CD_DIMENSION[carrier])
    assert s["has_zero_divisor"]
    assert not s["hopf_fibration_exists"]
    assert not s["is_sound"]


def test_carrier_order_matches_the_supplied_schema():
    assert CARRIER_ORDER == ("R", "H", "O", "CD32", "A_n")


# -------------------------------------------------------- prefix telescoping

@pytest.mark.parametrize("n", [1, 2, 3, 5, 8])
def test_kappa_telescopes_over_prefixes_exactly(n):
    """kappa is a 2-cocycle: it telescopes over prefixes, not adjacent pairs.

    The first implementation summed kappa(M_i, M_{i+1}) and disagreed with the
    word total at 1.2e-2, double-counting every interior log-norm. The prefix
    decomposition sum_i kappa(P_{i-1}, M_i) collapses to
    sum_i log|M_i| - log|M_word| exactly.
    """
    rng = np.random.default_rng(100 + n)
    pts = [(rng.uniform(0.05, 1.5), rng.uniform(-3, 3), rng.uniform(-3, 3))
           for _ in range(n + 1)]
    t = trace_word(pts, "O")
    assert t["kappa_word"] == pytest.approx(t["kappa_per_event_sum"], abs=1e-12)


def test_single_step_word_leaks_nothing():
    """The reduced-word control: one step cannot leak."""
    t = trace_word([(0.4, 0.1, 0.2), (0.9, 1.0, -0.3)], "O")
    assert t["kappa_word"] == pytest.approx(0.0, abs=1e-12)


def test_compounding_steps_do_not_leak():
    """The injection that was NOT a fault, pinned.

    Two depth-2 steps at phi = +1 and phi = -1 COMPOUND to depth 4. kappa_word is
    exactly zero and the detector must stay silent. The first version of the
    experiment injected this as 'energy leakage' and the empty confusion-matrix
    row was the detector being right.
    """
    t = trace_word([(0.1, 0.0, 0.0), (2.0, 1.0, 0.0), (2.0, -1.0, 0.0)], "O")
    assert t["kappa_word"] == pytest.approx(0.0, abs=1e-12)
    assert t["net_depth"] == pytest.approx(4.0, abs=1e-9)
    assert "energy_leakage" not in detect(t["events"][-1], t["kappa_word"])


def test_cancelling_steps_do_leak_and_the_amount_is_exact():
    """The real leak: phi = 0 against phi = pi gives kappa_word = 2 rho exactly."""
    t = trace_word([(0.1, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, math.pi, 0.0)], "O")
    assert t["kappa_word"] == pytest.approx(4.0, abs=1e-9)
    assert t["net_depth"] == pytest.approx(0.0, abs=1e-9)
    assert "energy_leakage" in detect(t["events"][-1], t["kappa_word"])


# ------------------------------------------------------------ the detectors

def test_clean_trace_fires_nothing():
    clean = trace_word(CLEAN, "O")
    for e in clean["events"]:
        assert detect(e, word_kappa=0.0) == []


def test_false_ascent_fires_only_above_the_ladder():
    assert detect(bridge_event(CLEAN[0], CLEAN[1], "CD32"), 0.0) == ["false_ascent"]
    for sound in ("R", "H", "O"):
        assert detect(bridge_event(CLEAN[0], CLEAN[1], sound), 0.0) == []


def test_bridge_absorption_reads_depth_not_step_size():
    """The control that makes the detector mean something.

    The same kind of source step fires deep and stays silent shallow, because the
    operational response is suppressed by e^{-4 rho}. If it fired at both, the
    detector would be reading step size.
    """
    deep = bridge_event((3.0, 0.0, 0.0), (3.2, 0.02, 0.0), "O")
    shallow = bridge_event((0.05, 0.0, 0.0), (0.25, 0.02, 0.0), "O")
    assert "bridge_absorption" in detect(deep, 0.0)
    assert "bridge_absorption" not in detect(shallow, 0.0)
    assert deep["source_step"] > shallow["source_step"]
    assert deep["operational_step"] < shallow["operational_step"]


def test_confusion_matrix_is_diagonal():
    leak = trace_word([(0.1, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, math.pi, 0.0)], "O")
    cases = {
        "false_ascent": detect(bridge_event(CLEAN[0], CLEAN[1], "CD32"), 0.0),
        "energy_leakage": detect(leak["events"][-1], leak["kappa_word"]),
        "bridge_absorption": detect(
            bridge_event((3.0, 0.0, 0.0), (3.2, 0.02, 0.0), "O"), 0.0),
    }
    assert confusion_matrix(cases)["is_diagonal"]


# ------------------------------------------------- return path and remainder

@pytest.mark.parametrize("rho", [0.2, 0.5, 1.0, 2.0])
def test_return_path_costs_two_rho(rho):
    e = bridge_event((0.1, 0.0, 0.0), (rho, 0.3, 0.2), "O")
    r = e["return_path"]
    assert r["kappa_inverse_pair"] == pytest.approx(2.0 * rho, abs=1e-9)
    assert r["source_defect"] < 1e-12
    assert r["streamed_survival"] == pytest.approx(math.exp(-4.0 * rho), abs=1e-12)


def test_remainder_is_a_vector_not_a_norm():
    """The scalar-collapse control: the record must not be flattened."""
    e = bridge_event(CLEAN[0], CLEAN[1], "O")
    assert not e.remainder_is_flattened
    assert len(e["projection_violence"]["discarded_vector"]) > 1


def test_projection_violence_is_the_r6b_operator():
    for rho in (0.5, 1.0, 2.0):
        e = bridge_event((0.1, 0.0, 0.0), (rho, 0.2, 0.3), "O")
        assert e["projection_violence"]["volume_form_distortion"] == pytest.approx(
            volume_form_distortion(rho), rel=1e-12)


def test_projection_violence_decays_with_depth():
    vals = [bridge_event((0.1, 0.0, 0.0), (r, 0.2, 0.3), "O")
            ["projection_violence"]["volume_form_distortion"]
            for r in (0.5, 1.0, 2.0, 3.0)]
    assert vals == sorted(vals, reverse=True)


# ------------------------------------------------------------ the atlas join

def test_fill_completes_a_null_volume_form_distortion():
    """The field the supplied atlas declares and leaves null in most events."""
    bridge = {"projection_violence": {"volume_form_distortion": None,
                                      "discarded_vector": [0.1, 0.2]}}
    out = fill_volume_form_distortion(bridge, [1.5, 0.0, 0.0])
    assert out["projection_violence"]["volume_form_distortion"] == pytest.approx(
        volume_form_distortion(1.5), rel=1e-12)
    assert "R6b" in out["projection_violence"]["volume_form_distortion_source"]
    # the original is not mutated
    assert bridge["projection_violence"]["volume_form_distortion"] is None
