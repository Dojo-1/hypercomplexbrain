from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.coherent_dilation import (
    coherent_dilation_codeword,
    composition_defect_matrices,
    density_state_diagnostics,
    dilation_diagnostics,
    halmos_dilation,
    normalised_contraction,
)


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


def test_shared_svd_preserves_nonnormal_intertwining():
    contraction = np.array([[0.0, 1.0], [0.6, 0.0]], dtype=complex)
    unitary = halmos_dilation(contraction)
    diagnostics = dilation_diagnostics(contraction, unitary, tol=1e-12)
    assert unitary[:2, 2:] == pytest.approx(np.diag([0.0, 0.8]), abs=1e-12)
    assert unitary[2:, :2] == pytest.approx(np.diag([0.8, 0.0]), abs=1e-12)
    assert diagnostics["valid"]


def test_roundoff_guard_keeps_a_true_small_defect():
    singular = 1.0 - 1e-11
    unitary = halmos_dilation(np.diag([singular, 0.25]))
    expected = math.sqrt((1.0 - singular) * (1.0 + singular))
    assert float(np.real(unitary[2, 0])) > 1e-6
    assert float(np.real(unitary[2, 0])) == pytest.approx(
        expected, abs=1e-10, rel=5e-5
    )


def test_expansive_and_nonfinite_sources_fail_closed():
    with pytest.raises(ValueError, match="not a contraction"):
        halmos_dilation(np.diag([1.01, 0.5]))
    with pytest.raises(ValueError, match="finite"):
        normalised_contraction(np.diag([math.nan, 1.0]))


def test_choi_codeword_is_a_pure_d16_density():
    source = np.array(
        [[math.cosh(0.7), math.sinh(0.7)],
         [math.sinh(0.7), math.cosh(0.7)]]
    )
    diagnostics = density_state_diagnostics(
        coherent_dilation_codeword(source), require_pure=True
    )
    assert diagnostics["shape"] == [16, 16]
    assert diagnostics["rank"] == 1
    assert diagnostics["valid"]


@pytest.mark.parametrize("q", [0.0, 0.25, 1.0])
def test_central_sign_overlap_is_q_to_four(q):
    positive = coherent_dilation_codeword(np.diag([1.0, q]))
    negative = coherent_dilation_codeword(-np.diag([1.0, q]))
    density_fidelity = float(np.real(np.trace(positive @ negative)))
    assert density_fidelity == pytest.approx(q ** 4, abs=1e-12)


def test_identity_composition_defect_prevents_representation_claim():
    defect = composition_defect_matrices(np.eye(2), np.eye(2))
    assert defect == pytest.approx(2.0 * math.sqrt(2.0), abs=1e-12)

