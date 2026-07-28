"""Tests for the preregistered algebra-valued S8 decoder slice."""

from __future__ import annotations

import numpy as np
import pytest

from aionq.fano_decoder import (
    algebra_basis,
    algebra_report,
    decode_coefficients,
    decode_split,
    encode_coefficients,
    fano_lines,
    find_rank_deficient_control,
    noise_benchmark,
    random_control_summary,
    so8_coordinates,
    so8_matrix,
)


@pytest.fixture(scope="module")
def fano_basis():
    return algebra_basis(fano_lines())


def test_so8_coordinate_map_is_a_frobenius_isometry():
    rng = np.random.default_rng(17)
    raw_a = rng.normal(size=(8, 8))
    raw_b = rng.normal(size=(8, 8))
    a = raw_a - raw_a.T
    b = raw_b - raw_b.T
    a_coordinates = so8_coordinates(a)
    b_coordinates = so8_coordinates(b)

    assert a_coordinates.shape == (28,)
    assert np.allclose(
        a_coordinates @ b_coordinates,
        np.trace(a.T @ b),
        atol=1e-12,
    )
    assert np.allclose(so8_matrix(a_coordinates), a, atol=1e-12)


def test_so8_coordinate_map_rejects_scalar_or_non_skew_inputs():
    with pytest.raises(ValueError, match="8x8"):
        so8_coordinates(np.ones(8))
    with pytest.raises(ValueError, match="not skew-symmetric"):
        so8_coordinates(np.eye(8))
    with pytest.raises(ValueError, match="28 coordinates"):
        so8_matrix(np.ones(27))


def test_fano_basis_passes_preregistered_rank_and_orthogonality_gates(fano_basis):
    report = algebra_report(fano_basis)
    assert len(fano_basis.triples) == 7
    assert len(fano_basis.pairs) == 21
    assert report["signal_rank"] == 7
    assert report["crosstalk_rank"] == 21
    assert report["joint_rank"] == 28
    assert report["max_abs_cross_gram"] <= 1e-12
    assert report["zero_crosstalk_columns"] == 0


def test_noiseless_joint_and_split_decoders_recover_all_coefficients(fano_basis):
    rng = np.random.default_rng(20260728)
    signal = rng.normal(size=(256, 7))
    crosstalk = rng.normal(size=(256, 21))
    observations = encode_coefficients(fano_basis, signal, crosstalk)

    signal_joint, crosstalk_joint = decode_coefficients(
        fano_basis, observations
    )
    signal_split, crosstalk_split = decode_split(
        fano_basis, observations
    )

    assert np.max(np.abs(signal_joint - signal)) <= 1e-10
    assert np.max(np.abs(crosstalk_joint - crosstalk)) <= 1e-10
    assert np.allclose(signal_split, signal_joint, atol=1e-11)
    assert np.allclose(crosstalk_split, crosstalk_joint, atol=1e-11)


def test_scalar_norm_collapses_distinct_algebra_directions(fano_basis):
    left = fano_basis.crosstalk[:, 0]
    right = fano_basis.crosstalk[:, 1]
    assert np.isclose(np.linalg.norm(left), np.linalg.norm(right), atol=1e-14)
    assert np.linalg.norm(left - right) > 0.5


def test_basis_permutation_changes_coordinates_not_observation(fano_basis):
    rng = np.random.default_rng(29)
    signal = rng.normal(size=7)
    crosstalk = rng.normal(size=21)
    original = encode_coefficients(fano_basis, signal, crosstalk)

    signal_permutation = rng.permutation(7)
    crosstalk_permutation = rng.permutation(21)
    permuted_basis = type(fano_basis)(
        triples=tuple(fano_basis.triples[index] for index in signal_permutation),
        pairs=tuple(fano_basis.pairs[index] for index in crosstalk_permutation),
        signal=fano_basis.signal[:, signal_permutation],
        crosstalk=fano_basis.crosstalk[:, crosstalk_permutation],
        signal_raw_norms=fano_basis.signal_raw_norms[signal_permutation],
        crosstalk_raw_norms=fano_basis.crosstalk_raw_norms[
            crosstalk_permutation
        ],
    )
    permuted = encode_coefficients(
        permuted_basis,
        signal[signal_permutation],
        crosstalk[crosstalk_permutation],
    )
    signal_hat, crosstalk_hat = decode_coefficients(
        permuted_basis, permuted
    )

    assert np.allclose(permuted, original, atol=1e-12)
    assert np.allclose(signal_hat, signal[signal_permutation], atol=1e-11)
    assert np.allclose(
        crosstalk_hat, crosstalk[crosstalk_permutation], atol=1e-11
    )


def test_noise_rmse_matches_the_actual_decoder_covariance(fano_basis):
    rows = noise_benchmark(
        fano_basis,
        sigma=(0.0, 0.0001, 0.001, 0.01, 0.1),
        samples=4096,
        seed=20260728,
    )
    assert rows[0]["maximum_absolute_error"] <= 1e-10
    for row in rows[1:]:
        assert abs(row["empirical_over_expected"] - 1.0) <= 0.15


def test_rank_deficient_control_has_an_exact_coefficient_alias():
    summary = random_control_summary(trials=1000, seed=20260727)
    alias = find_rank_deficient_control(summary)
    assert alias["crosstalk_rank"] < 21
    assert alias["nullity"] >= 1
    assert alias["coefficient_distance"] >= 1.0 - 1e-12
    assert alias["observation_distance"] <= 1e-10
