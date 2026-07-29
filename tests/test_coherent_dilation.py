from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.coherent_dilation import (
    RESCUE_MARGIN_BITS,
    classify_rescue,
    coherent_dilation_codeword,
    composition_defect,
    density_state_diagnostics,
    ensemble_information,
    halmos_dilation,
    matched_codebooks,
    normalised_contraction,
    source_grid,
)


def test_halmos_block_is_unitary_for_a_generic_contraction():
    source = np.array([[1.2, -0.4], [0.3, 0.8]], dtype=complex)
    contraction = normalised_contraction(source)
    unitary = halmos_dilation(contraction)
    assert unitary.shape == (4, 4)
    assert np.linalg.norm(unitary.conj().T @ unitary - np.eye(4), "fro") < 1e-10
    assert np.linalg.norm(unitary @ unitary.conj().T - np.eye(4), "fro") < 1e-10


def test_halmos_block_rejects_an_expansive_operator():
    with pytest.raises(ValueError, match="not a contraction"):
        halmos_dilation(np.diag([1.01, 0.5]))


def test_choi_vector_codeword_is_a_valid_pure_density_state():
    source = np.array([[math.cosh(0.7), math.sinh(0.7)],
                       [math.sinh(0.7), math.cosh(0.7)]])
    diagnostics = density_state_diagnostics(coherent_dilation_codeword(source))
    assert diagnostics["shape"] == [16, 16]
    assert diagnostics["valid"]
    assert diagnostics["purity"] == pytest.approx(1.0, abs=1e-10)


def test_source_grid_is_deterministic_and_shared_by_both_encodings():
    expected = source_grid(0.5, 8)
    r6, coherent, observed = matched_codebooks(0.5, 8)
    assert observed == expected
    assert len(r6) == len(coherent) == len(expected)
    assert {state.shape for state in r6} == {(5, 5)}
    assert {state.shape for state in coherent} == {(16, 16)}


def test_ensemble_information_is_permutation_invariant():
    states = [
        np.diag([1.0, 0.0, 0.0]).astype(complex),
        np.diag([0.0, 1.0, 0.0]).astype(complex),
        np.diag([0.0, 0.0, 1.0]).astype(complex),
    ]
    forward = ensemble_information(states)
    reverse = ensemble_information(list(reversed(states)))
    assert reverse["chi"] == pytest.approx(forward["chi"], abs=1e-12)
    assert reverse["I_PGM"] == pytest.approx(forward["I_PGM"], abs=1e-12)


def test_ensemble_information_is_common_unitary_and_padding_invariant():
    states = [
        np.diag([1.0, 0.0]).astype(complex),
        np.diag([0.0, 1.0]).astype(complex),
    ]
    hadamard = np.array([[1.0, 1.0], [1.0, -1.0]]) / math.sqrt(2.0)
    conjugated = [hadamard @ state @ hadamard.conj().T for state in states]
    padded = []
    for state in states:
        expanded = np.zeros((5, 5), dtype=complex)
        expanded[:2, :2] = state
        padded.append(expanded)
    baseline = ensemble_information(states)
    for candidate in (conjugated, padded):
        observed = ensemble_information(candidate)
        assert observed["chi"] == pytest.approx(baseline["chi"], abs=1e-12)
        assert observed["I_PGM"] == pytest.approx(baseline["I_PGM"], abs=1e-12)


def _synthetic_rows(chi_gain: float, pgm_gain: float):
    return [
        {
            "rho": rho,
            "n": n,
            "chi_improvement": chi_gain,
            "pgm_improvement": pgm_gain,
        }
        for rho in (0.5, 1.0)
        for n in (8, 64, 100, 256)
    ]


def test_frozen_decision_rule_requires_both_metrics_at_all_three_large_sizes():
    rescue = classify_rescue(_synthetic_rows(0.01, 0.01))
    assert rescue["verdict"] == "RESCUE_FOR_THIS_MAP"

    no_rescue = classify_rescue(_synthetic_rows(RESCUE_MARGIN_BITS, 0.0))
    assert no_rescue["verdict"] == "NO_RESCUE_FOR_THIS_MAP"

    mixed = _synthetic_rows(0.01, 0.01)
    mixed[-1]["pgm_improvement"] = 0.0
    mixed[-5]["pgm_improvement"] = 0.0
    assert classify_rescue(mixed)["verdict"] == "HOLD"


def test_composition_defect_is_finite_and_explicitly_not_assumed_zero():
    defect = composition_defect((0.3, 0.2, -0.1), (0.5, -0.4, 0.7))
    assert math.isfinite(defect)
    assert defect >= 0.0
