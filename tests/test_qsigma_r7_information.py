"""Frozen controls for the corrected QSigma-R7 information instrument."""

import math

import numpy as np
import pytest

from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.qsigma_r7_information import (
    BellCodeword,
    InvalidOperationalMetric,
    absolute_volume_density,
    bell_codeword,
    candidate_grid,
    candidate_order,
    compact_su2,
    deduplicate_candidates,
    distance_matrix,
    exact_packing_size,
    finite_difference_metric,
    greedy_codebook,
    information_metrics,
    null_separated_witness,
    projective_slab_volume,
    radial_rescaled_exponents,
    reject_split_form_distance,
    slab_volume,
    source_metric,
    trace_distance,
)


@pytest.mark.parametrize("rho", [0.5, 1.0, 2.0])
def test_source_metric_reconstructs_by_five_point_stencil(rho):
    analytic = source_metric(rho)
    measured = finite_difference_metric(rho, 0.37, 1.11)
    scale = max(1.0, float(np.max(np.abs(analytic))))
    assert np.max(np.abs(analytic - measured)) / scale < 1e-10
    assert absolute_volume_density(rho) == pytest.approx(
        math.sqrt(abs(np.linalg.det(analytic))), rel=1e-12
    )


@pytest.mark.parametrize("radius", [0.0, 0.5, 1.0, 3.0])
def test_source_and_projective_volumes(radius):
    expected = 2.0 * math.pi**2 * math.sinh(radius) ** 2
    assert slab_volume(radius) == pytest.approx(expected)
    assert projective_slab_volume(radius) == pytest.approx(expected / 2.0)


def test_indefinite_source_form_is_rejected_as_distance():
    witness = null_separated_witness()
    assert witness["distinct"]
    assert witness["q_left"] == pytest.approx(1.0)
    assert witness["q_right"] == pytest.approx(1.0)
    assert witness["q_delta"] == pytest.approx(0.0)
    with pytest.raises(InvalidOperationalMetric, match="indefinite"):
        reject_split_form_distance(witness["left"], witness["right"])


@pytest.mark.parametrize("rho", [0.0, 0.5, 1.0, 3.0])
def test_bell_codeword_density_and_r6_probability(rho):
    matrix = to_sl2(swirl_point(rho, 0.37, 1.11))
    word = bell_codeword(matrix)
    assert np.max(np.abs(word.density - word.density.conj().T)) < 1e-12
    assert np.min(np.linalg.eigvalsh(word.density)) >= -1e-12
    assert np.trace(word.density).real == pytest.approx(1.0, abs=1e-12)
    assert word.success_probability == pytest.approx(
        (1.0 + math.exp(-4.0 * rho)) / 2.0, abs=1e-12
    )
    assert trace_distance(
        word.density, bell_codeword(-matrix).density
    ) < 1e-12


def test_dense_trace_distance_laws():
    candidates = candidate_grid([0.0, 0.5, 1.0], 3, 3)
    retained, _ = deduplicate_candidates(candidates)
    left, middle, right = [candidate.codeword.density for candidate in retained[:3]]
    assert trace_distance(left, left) == pytest.approx(0.0, abs=1e-12)
    assert trace_distance(left, middle) == pytest.approx(
        trace_distance(middle, left), abs=1e-12
    )
    assert trace_distance(left, right) <= (
        trace_distance(left, middle) + trace_distance(middle, right) + 1e-12
    )


@pytest.mark.parametrize("rho", [0.0, 0.5, 2.0, 6.0])
def test_matched_compact_family_is_unitary_and_cost_free(rho):
    matrix = compact_su2(2.0 * math.atan(rho), 0.37, 1.11)
    assert np.max(np.abs(matrix.conj().T @ matrix - np.eye(2))) < 1e-12
    assert np.linalg.det(matrix) == pytest.approx(1.0 + 0.0j, abs=1e-12)
    assert bell_codeword(matrix).success_probability == pytest.approx(
        1.0, abs=1e-12
    )


def test_projective_dedup_and_orders_are_deterministic():
    candidates = candidate_grid([0.0, 1.0], 8, 8)
    retained, aliases = deduplicate_candidates(candidates)
    assert len(aliases) == len(candidates)
    assert len(retained) < len(candidates)
    policies = [
        "lexicographic_rho_phi_psi",
        "reverse_rho_then_phi_psi",
        "sha256_order_seed_20260728",
        "sha256_order_seed_271828",
    ]
    for policy in policies:
        first = candidate_order(retained, policy)
        assert first == candidate_order(retained, policy)
        assert sorted(first) == list(range(len(retained)))


@pytest.mark.parametrize("epsilon", [0.05, 0.1, 0.2])
def test_small_grid_greedy_is_bounded_by_exact_packing(epsilon):
    candidates = candidate_grid(
        [0.0, 1.0],
        8,
        8,
        phi_indices=[0, 1],
        psi_indices=[0, 1],
    )
    retained, _ = deduplicate_candidates(candidates)
    distances = distance_matrix(retained)
    exact = exact_packing_size(distances, epsilon)
    for policy in [
        "lexicographic_rho_phi_psi",
        "reverse_rho_then_phi_psi",
        "sha256_order_seed_20260728",
        "sha256_order_seed_271828",
    ]:
        selected = greedy_codebook(
            distances, epsilon, candidate_order(retained, policy)
        )
        assert len(selected) <= exact


def test_erasure_aware_information_is_p_log_n_for_orthogonal_successes():
    probability = 0.4
    words = []
    for index in range(4):
        density = np.zeros((5, 5), dtype=complex)
        density[index, index] = probability
        density[4, 4] = 1.0 - probability
        words.append(
            BellCodeword(density, probability, np.eye(2, dtype=complex))
        )
    metrics = information_metrics(words)
    expected = probability * math.log2(4)
    assert metrics.pgm_mutual_information == pytest.approx(expected, abs=1e-12)
    assert metrics.holevo_information == pytest.approx(expected, abs=1e-12)
    assert metrics.oracle_erasure_information == pytest.approx(
        expected, abs=1e-12
    )


def test_information_sandwich_for_source_codebook():
    candidates = candidate_grid([0.0, 0.5, 1.0], 3, 3)
    retained, _ = deduplicate_candidates(candidates)
    distances = distance_matrix(retained)
    selected = greedy_codebook(
        distances,
        0.2,
        candidate_order(retained, "sha256_order_seed_20260728"),
    )
    metrics = information_metrics(
        [retained[index].codeword for index in selected]
    )
    assert metrics.pgm_mutual_information >= -1e-9
    assert (
        metrics.pgm_mutual_information
        <= metrics.holevo_information + 1e-9
    )
    assert (
        metrics.holevo_information
        <= metrics.oracle_erasure_information + 1e-9
    )
    assert (
        metrics.oracle_erasure_information
        <= metrics.log2_codewords + 1e-9
    )
    assert metrics.pgm_maximum_row_defect <= 1e-10
    assert metrics.pgm_minimum_raw_probability >= -1e-12
    assert metrics.pgm_support_projector_defect <= 1e-10


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0, 7.0])
def test_radial_reparameterisation_rescales_both_exponents(scale):
    exponents = radial_rescaled_exponents(scale)
    assert exponents["source"] == pytest.approx(2.0 / scale)
    assert exponents["worst_cost"] == pytest.approx(4.0 / scale)
    assert exponents["source_to_cost_ratio"] == pytest.approx(0.5)
