from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.coherent_dilation import (
    RESCUE_MARGIN_BITS,
    classify_rescue,
    coherent_dilation_codeword,
    composition_defect,
    composition_defect_matrices,
    density_state_diagnostics,
    dilation_diagnostics,
    ensemble_information,
    halmos_dilation,
    matched_codebooks,
    normalised_contraction,
    source_grid,
)
from aionq.quantum_channel_geometry import attempted_use_state


def test_halmos_block_is_unitary_for_a_generic_contraction():
    source = np.array([[1.2, -0.4], [0.3, 0.8]], dtype=complex)
    contraction = normalised_contraction(source)
    unitary = halmos_dilation(contraction)
    assert unitary.shape == (4, 4)
    assert np.linalg.norm(unitary.conj().T @ unitary - np.eye(4), "fro") < 1e-10
    assert np.linalg.norm(unitary @ unitary.conj().T - np.eye(4), "fro") < 1e-10


@pytest.mark.parametrize("q", [0.0, 0.25, 1.0])
def test_halmos_diagonal_known_answer(q):
    defect = math.sqrt((1.0 - q) * (1.0 + q))
    expected = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, q, 0.0, defect],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, defect, 0.0, -q],
        ],
        dtype=complex,
    )
    assert halmos_dilation(np.diag([1.0, q])) == pytest.approx(
        expected, abs=1e-12
    )


def test_halmos_shared_svd_handles_a_nonnormal_contraction():
    contraction = np.array([[0.0, 1.0], [0.6, 0.0]], dtype=complex)
    unitary = halmos_dilation(contraction)
    assert unitary[:2, 2:] == pytest.approx(np.diag([0.0, 0.8]), abs=1e-12)
    assert unitary[2:, :2] == pytest.approx(np.diag([0.8, 0.0]), abs=1e-12)
    diagnostics = dilation_diagnostics(contraction, unitary, tol=1e-12)
    assert diagnostics["valid"]


def test_halmos_roundoff_guard_does_not_erase_a_true_small_defect():
    singular = 1.0 - 1e-11
    unitary = halmos_dilation(np.diag([singular, 0.25]))
    observed = float(np.real(unitary[2, 0]))
    expected = math.sqrt((1.0 - singular) * (1.0 + singular))
    assert observed > 1e-6
    assert observed == pytest.approx(expected, abs=1e-10, rel=5e-5)


def test_halmos_block_rejects_an_expansive_operator():
    with pytest.raises(ValueError, match="not a contraction"):
        halmos_dilation(np.diag([1.01, 0.5]))
    with pytest.raises(ValueError, match="not a contraction"):
        halmos_dilation(np.diag([1.0 + 1e-12, 0.5]))


def test_choi_vector_codeword_is_a_valid_pure_density_state():
    source = np.array([[math.cosh(0.7), math.sinh(0.7)],
                       [math.sinh(0.7), math.cosh(0.7)]])
    diagnostics = density_state_diagnostics(coherent_dilation_codeword(source))
    assert diagnostics["shape"] == [16, 16]
    assert diagnostics["valid"]
    assert diagnostics["purity"] == pytest.approx(1.0, abs=1e-10)


def test_source_grid_is_deterministic_and_shared_by_both_encodings():
    expected = source_grid(0.5, 8)
    r6, coherent, observed, matrices = matched_codebooks(0.5, 8)
    assert observed == expected
    assert len(r6) == len(coherent) == len(expected) == len(matrices)
    assert {state.shape for state in r6} == {(5, 5)}
    assert {state.shape for state in coherent} == {(16, 16)}
    for matrix, state in zip(matrices, r6):
        assert state == pytest.approx(
            attempted_use_state(matrix)[0].astype(complex), abs=0.0
        )


def test_canonical_dilation_lifts_the_r6_central_sign_alias():
    rho = 1.0
    r6, coherent, _, matrices = matched_codebooks(rho, 8)
    assert matrices[4] == pytest.approx(-matrices[0], abs=1e-15)
    assert np.linalg.norm(r6[4] - r6[0], "fro") <= 1e-15
    fidelity = float(np.real(np.trace(coherent[0] @ coherent[4])))
    assert fidelity == pytest.approx(math.exp(-8.0 * rho), abs=2e-12)
    assert fidelity < 1e-3


@pytest.mark.parametrize("q", [0.0, 0.25, 1.0])
def test_choi_overlap_identity_for_a_central_sign_pair(q):
    positive = coherent_dilation_codeword(np.diag([1.0, q]))
    negative = coherent_dilation_codeword(-np.diag([1.0, q]))
    density_fidelity = float(np.real(np.trace(positive @ negative)))
    assert density_fidelity == pytest.approx(q ** 4, abs=1e-12)


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
    assert forward["numerically_valid"]


def test_ensemble_information_known_answers_and_guards():
    orthogonal = [
        np.diag([1.0 if row == column else 0.0 for column in range(3)]).astype(
            complex
        )
        for row in range(3)
    ]
    orthogonal_metrics = ensemble_information(orthogonal)
    assert orthogonal_metrics["I_PGM"] == pytest.approx(math.log2(3), abs=1e-12)
    assert orthogonal_metrics["chi"] == pytest.approx(math.log2(3), abs=1e-12)
    assert orthogonal_metrics["mean_state_rank"] == 3
    assert orthogonal_metrics["numerically_valid"]

    identical = [orthogonal[0], orthogonal[0], orthogonal[0]]
    identical_metrics = ensemble_information(identical)
    assert identical_metrics["I_PGM"] == pytest.approx(0.0, abs=1e-12)
    assert identical_metrics["chi"] == pytest.approx(0.0, abs=1e-12)
    assert identical_metrics["mean_state_rank"] == 1
    assert identical_metrics["numerically_valid"]


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
        assert observed["pgm_support_projector_defect"] <= 1e-10
        assert observed["pgm_minimum_raw_probability"] >= -1e-10
        assert observed["pgm_maximum_row_sum_defect"] <= 1e-10


def test_r6_passive_embedding_from_five_to_sixteen_is_information_invariant():
    r6, _, _, _ = matched_codebooks(2.0, 8)
    padded = []
    for state in r6:
        expanded = np.zeros((16, 16), dtype=complex)
        expanded[:5, :5] = state
        padded.append(expanded)
    baseline = ensemble_information(r6)
    observed = ensemble_information(padded)
    assert observed["chi"] == pytest.approx(baseline["chi"], abs=1e-12)
    assert observed["I_PGM"] == pytest.approx(baseline["I_PGM"], abs=1e-12)


_EXPECTED_DEPTHS = (0.5, 1.0)
_EXPECTED_SIZES = (8, 64, 100, 256)


def _synthetic_rows(chi_gain: float, pgm_gain: float):
    return [
        {
            "rho": rho,
            "n": n,
            "chi_improvement": chi_gain,
            "pgm_improvement": pgm_gain,
        }
        for rho in _EXPECTED_DEPTHS
        for n in _EXPECTED_SIZES
    ]


def test_frozen_decision_rule_requires_both_metrics_at_all_three_large_sizes():
    keywords = {
        "expected_depths": _EXPECTED_DEPTHS,
        "expected_sizes": _EXPECTED_SIZES,
    }
    rescue = classify_rescue(_synthetic_rows(0.01, 0.01), **keywords)
    assert rescue["verdict"] == "RESCUE_FOR_THIS_MAP"

    no_rescue = classify_rescue(
        _synthetic_rows(RESCUE_MARGIN_BITS, 0.0), **keywords
    )
    assert no_rescue["verdict"] == "NO_RESCUE_FOR_THIS_MAP"

    mixed = _synthetic_rows(0.01, 0.01)
    mixed[-1]["pgm_improvement"] = 0.0
    mixed[-5]["pgm_improvement"] = 0.0
    assert classify_rescue(mixed, **keywords)["verdict"] == "HOLD"


@pytest.mark.parametrize(
    "mutation",
    ["empty", "missing", "duplicate", "extra", "nan", "fractional_size"],
)
def test_frozen_decision_rule_holds_on_an_invalid_grid(mutation):
    rows = _synthetic_rows(0.01, 0.01)
    if mutation == "empty":
        rows = []
    elif mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(dict(rows[-1]))
    elif mutation == "extra":
        rows.append(
            {
                "rho": 2.0,
                "n": 8,
                "chi_improvement": 0.01,
                "pgm_improvement": 0.01,
            }
        )
    elif mutation == "nan":
        rows[-1]["chi_improvement"] = math.nan
    else:
        rows[1]["n"] = 64.5
    decision = classify_rescue(
        rows,
        expected_depths=_EXPECTED_DEPTHS,
        expected_sizes=_EXPECTED_SIZES,
    )
    assert decision["verdict"] == "HOLD"
    assert not decision["grid_valid"]
    assert decision["hold_reasons"]


def test_composition_defect_is_finite_and_explicitly_not_assumed_zero():
    defect = composition_defect((0.3, 0.2, -0.1), (0.5, -0.4, 0.7))
    assert math.isfinite(defect)
    assert defect >= 0.0
    identity_defect = composition_defect_matrices(np.eye(2), np.eye(2))
    assert identity_defect == pytest.approx(2.0 * math.sqrt(2.0), abs=1e-12)
