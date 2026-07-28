"""Algebra-valued coordinates and a local decoder for the S8 Fano design.

The scalar experiment in :mod:`experiments.run_fano_multiplex` measures only
``||[G_i, G_j]||_F``.  A norm cannot say where a commutator lands.  This module
keeps each skew-symmetric matrix as an element of ``so(8)`` and makes the
observation model explicit:

    y = S a + C b + epsilon

``S`` contains the seven normalized channel generators and ``C`` contains the
twenty-one normalized pairwise commutators.  The declared decoder is ordinary
least squares in the 28-dimensional real vector space ``so(8)``.  It is a local,
linearized identifiability result, not a finite-group receiver and not a
physical channel-capacity claim.

The strict-upper-triangle coordinate map is scaled by ``sqrt(2)`` so that its
Euclidean inner product is exactly the Frobenius inner product on real
skew-symmetric matrices.  No scalar norm is used as the observation.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np

from .cayley_dickson import fast_associator, fast_multiply

__all__ = [
    "AlgebraBasis",
    "algebra_basis",
    "algebra_report",
    "channel_generator",
    "decode_coefficients",
    "decode_split",
    "encode_coefficients",
    "fano_lines",
    "find_rank_deficient_control",
    "noise_benchmark",
    "random_control_summary",
    "so8_coordinates",
    "so8_matrix",
]


_DIM = 8
_EYE = np.eye(_DIM)
_SO8_UPPER = np.triu_indices(_DIM, 1)
_SQRT2 = np.sqrt(2.0)


def so8_coordinates(matrix: np.ndarray, *, atol: float = 1e-10) -> np.ndarray:
    """Return the 28 isometric coordinates of a real ``so(8)`` element.

    For skew matrices ``A`` and ``B`` this normalization gives

    ``so8_coordinates(A) @ so8_coordinates(B) == trace(A.T @ B)``.
    """

    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (_DIM, _DIM):
        raise ValueError(f"expected an 8x8 matrix, got {matrix.shape}")
    defect = float(np.linalg.norm(matrix + matrix.T, ord="fro"))
    if defect > atol:
        raise ValueError(
            f"matrix is not skew-symmetric: Frobenius defect {defect:.3e}"
        )
    return _SQRT2 * matrix[_SO8_UPPER]


def so8_matrix(coordinates: np.ndarray) -> np.ndarray:
    """Invert :func:`so8_coordinates` exactly up to floating-point roundoff."""

    coordinates = np.asarray(coordinates, dtype=float)
    if coordinates.shape != (28,):
        raise ValueError(f"expected 28 coordinates, got {coordinates.shape}")
    matrix = np.zeros((_DIM, _DIM), dtype=float)
    matrix[_SO8_UPPER] = coordinates / _SQRT2
    matrix[(_SO8_UPPER[1], _SO8_UPPER[0])] = -coordinates / _SQRT2
    return matrix


@lru_cache(maxsize=1)
def _fano_lines_cached() -> tuple[tuple[int, int, int], ...]:
    lines = []
    for triple in itertools.combinations(range(1, _DIM), 3):
        associator = fast_associator(
            _EYE[triple[0]], _EYE[triple[1]], _EYE[triple[2]]
        )
        if np.linalg.norm(associator) < 1e-9:
            lines.append(triple)
    return tuple(lines)


def fano_lines() -> tuple[tuple[int, int, int], ...]:
    """Compute the seven associative triples of the imaginary octonions."""

    return _fano_lines_cached()


@lru_cache(maxsize=None)
def _left_multiplication(unit: int) -> np.ndarray:
    if not 0 <= unit < _DIM:
        raise ValueError(f"basis unit must be in [0, 7], got {unit}")
    return np.stack(
        [fast_multiply(_EYE[unit], _EYE[column]) for column in range(_DIM)],
        axis=1,
    )


@lru_cache(maxsize=None)
def _channel_generator_cached(triple: tuple[int, int, int]) -> np.ndarray:
    if len(set(triple)) != 3 or any(unit not in range(1, _DIM) for unit in triple):
        raise ValueError(f"expected three distinct imaginary units, got {triple}")
    generator = sum(_left_multiplication(unit) for unit in triple) / len(triple)
    skew_defect = np.linalg.norm(generator + generator.T, ord="fro")
    if skew_defect > 1e-10:
        raise ValueError(
            f"channel generator is not in so(8): defect {skew_defect:.3e}"
        )
    return generator


def channel_generator(triple: Sequence[int]) -> np.ndarray:
    """Return the skew channel generator associated with one triple."""

    key = tuple(sorted(int(unit) for unit in triple))
    return _channel_generator_cached(key).copy()


def _normalize_columns(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    norms = np.linalg.norm(matrix, axis=0)
    normalized = np.zeros_like(matrix)
    nonzero = norms > 1e-14
    normalized[:, nonzero] = matrix[:, nonzero] / norms[nonzero]
    return normalized, norms


@dataclass(frozen=True)
class AlgebraBasis:
    """The normalized signal/crosstalk coordinate matrices for one design."""

    triples: tuple[tuple[int, int, int], ...]
    pairs: tuple[tuple[int, int], ...]
    signal: np.ndarray
    crosstalk: np.ndarray
    signal_raw_norms: np.ndarray
    crosstalk_raw_norms: np.ndarray

    @property
    def joint(self) -> np.ndarray:
        return np.column_stack((self.signal, self.crosstalk))

    @property
    def n_signal(self) -> int:
        return self.signal.shape[1]

    @property
    def n_crosstalk(self) -> int:
        return self.crosstalk.shape[1]


def algebra_basis(triples: Iterable[Sequence[int]]) -> AlgebraBasis:
    """Build normalized algebra-valued signal and commutator matrices."""

    normalized_triples = tuple(
        tuple(sorted(int(unit) for unit in triple)) for triple in triples
    )
    if len(normalized_triples) != 7 or len(set(normalized_triples)) != 7:
        raise ValueError("a matched design must contain seven distinct triples")

    generators = [channel_generator(triple) for triple in normalized_triples]
    signal_raw = np.column_stack(
        [so8_coordinates(generator) for generator in generators]
    )
    pairs = tuple(itertools.combinations(range(len(generators)), 2))
    crosstalk_raw = np.column_stack(
        [
            so8_coordinates(
                generators[left] @ generators[right]
                - generators[right] @ generators[left]
            )
            for left, right in pairs
        ]
    )
    signal, signal_norms = _normalize_columns(signal_raw)
    crosstalk, crosstalk_norms = _normalize_columns(crosstalk_raw)
    return AlgebraBasis(
        triples=normalized_triples,
        pairs=pairs,
        signal=signal,
        crosstalk=crosstalk,
        signal_raw_norms=signal_norms,
        crosstalk_raw_norms=crosstalk_norms,
    )


def _matrix_rank(matrix: np.ndarray) -> int:
    return int(np.linalg.matrix_rank(matrix))


def _condition_number(matrix: np.ndarray) -> float | None:
    if _matrix_rank(matrix) < matrix.shape[1]:
        return None
    return float(np.linalg.cond(matrix))


def algebra_report(basis: AlgebraBasis) -> dict:
    """Report ranks, singular values, orthogonality, and conditioning."""

    signal_singular = np.linalg.svd(basis.signal, compute_uv=False)
    crosstalk_singular = np.linalg.svd(basis.crosstalk, compute_uv=False)
    joint_singular = np.linalg.svd(basis.joint, compute_uv=False)
    cross_gram = basis.signal.T @ basis.crosstalk
    return {
        "signal_rank": _matrix_rank(basis.signal),
        "crosstalk_rank": _matrix_rank(basis.crosstalk),
        "joint_rank": _matrix_rank(basis.joint),
        "max_abs_cross_gram": float(np.max(np.abs(cross_gram))),
        "signal_singular_values": signal_singular.tolist(),
        "crosstalk_singular_values": crosstalk_singular.tolist(),
        "joint_singular_values": joint_singular.tolist(),
        "signal_condition_number": _condition_number(basis.signal),
        "crosstalk_condition_number": _condition_number(basis.crosstalk),
        "joint_condition_number": _condition_number(basis.joint),
        "zero_crosstalk_columns": int(
            np.count_nonzero(basis.crosstalk_raw_norms <= 1e-14)
        ),
    }


def _coefficient_samples(
    signal_coefficients: np.ndarray,
    crosstalk_coefficients: np.ndarray,
    basis: AlgebraBasis,
) -> tuple[np.ndarray, np.ndarray, bool]:
    signal_coefficients = np.asarray(signal_coefficients, dtype=float)
    crosstalk_coefficients = np.asarray(crosstalk_coefficients, dtype=float)
    was_vector = signal_coefficients.ndim == 1
    if was_vector:
        signal_coefficients = signal_coefficients[None, :]
    if crosstalk_coefficients.ndim == 1:
        crosstalk_coefficients = crosstalk_coefficients[None, :]
    if signal_coefficients.ndim != 2 or crosstalk_coefficients.ndim != 2:
        raise ValueError("coefficients must be vectors or sample matrices")
    if signal_coefficients.shape[1] != basis.n_signal:
        raise ValueError(
            f"expected {basis.n_signal} signal coefficients, "
            f"got {signal_coefficients.shape[1]}"
        )
    if crosstalk_coefficients.shape[1] != basis.n_crosstalk:
        raise ValueError(
            f"expected {basis.n_crosstalk} crosstalk coefficients, "
            f"got {crosstalk_coefficients.shape[1]}"
        )
    if signal_coefficients.shape[0] != crosstalk_coefficients.shape[0]:
        raise ValueError("signal and crosstalk sample counts differ")
    return signal_coefficients, crosstalk_coefficients, was_vector


def encode_coefficients(
    basis: AlgebraBasis,
    signal_coefficients: np.ndarray,
    crosstalk_coefficients: np.ndarray,
) -> np.ndarray:
    """Encode coefficient vectors into full algebra-valued observations."""

    signal, crosstalk, was_vector = _coefficient_samples(
        signal_coefficients, crosstalk_coefficients, basis
    )
    observations = signal @ basis.signal.T + crosstalk @ basis.crosstalk.T
    return observations[0] if was_vector else observations


def _observation_samples(
    observations: np.ndarray, basis: AlgebraBasis
) -> tuple[np.ndarray, bool]:
    observations = np.asarray(observations, dtype=float)
    was_vector = observations.ndim == 1
    if was_vector:
        observations = observations[None, :]
    if observations.ndim != 2 or observations.shape[1] != basis.joint.shape[0]:
        raise ValueError(
            f"expected observations with 28 coordinates, got {observations.shape}"
        )
    return observations, was_vector


def decode_coefficients(
    basis: AlgebraBasis, observations: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Joint least-squares decoder for the declared linear observation model."""

    observations, was_vector = _observation_samples(observations, basis)
    decoded = observations @ np.linalg.pinv(basis.joint).T
    signal = decoded[:, : basis.n_signal]
    crosstalk = decoded[:, basis.n_signal :]
    if was_vector:
        return signal[0], crosstalk[0]
    return signal, crosstalk


def decode_split(
    basis: AlgebraBasis,
    observations: np.ndarray,
    *,
    orthogonality_tolerance: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    """Decode the two blocks separately after verifying their orthogonality."""

    cross_defect = float(np.max(np.abs(basis.signal.T @ basis.crosstalk)))
    if cross_defect > orthogonality_tolerance:
        raise ValueError(
            "split decoding requires orthogonal signal/crosstalk spaces; "
            f"measured cross Gram {cross_defect:.3e}"
        )
    observations, was_vector = _observation_samples(observations, basis)
    signal = observations @ np.linalg.pinv(basis.signal).T
    crosstalk = observations @ np.linalg.pinv(basis.crosstalk).T
    if was_vector:
        return signal[0], crosstalk[0]
    return signal, crosstalk


def noise_benchmark(
    basis: AlgebraBasis,
    *,
    sigma: Sequence[float],
    samples: int,
    seed: int,
) -> list[dict]:
    """Measure decoder error against its analytic least-squares covariance."""

    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=(samples, basis.n_signal))
    crosstalk = rng.normal(size=(samples, basis.n_crosstalk))
    target = np.column_stack((signal, crosstalk))
    clean = encode_coefficients(basis, signal, crosstalk)
    decoder = np.linalg.pinv(basis.joint)
    expected_scale = float(np.linalg.norm(decoder, ord="fro") / np.sqrt(28.0))
    standard_noise = rng.normal(size=clean.shape)

    rows = []
    for level in sigma:
        level = float(level)
        if level < 0:
            raise ValueError("noise sigma must be non-negative")
        observations = clean + level * standard_noise
        signal_hat, crosstalk_hat = decode_coefficients(basis, observations)
        estimate = np.column_stack((signal_hat, crosstalk_hat))
        error = estimate - target
        empirical = float(np.sqrt(np.mean(error**2)))
        predicted = level * expected_scale
        rows.append(
            {
                "sigma": level,
                "combined_coefficient_rmse": empirical,
                "signal_coefficient_rmse": float(
                    np.sqrt(np.mean(error[:, : basis.n_signal] ** 2))
                ),
                "crosstalk_coefficient_rmse": float(
                    np.sqrt(np.mean(error[:, basis.n_signal :] ** 2))
                ),
                "analytic_expected_rmse": predicted,
                "empirical_over_expected": (
                    empirical / predicted if predicted > 0.0 else None
                ),
                "maximum_absolute_error": float(np.max(np.abs(error))),
            }
        )
    return rows


def random_control_summary(
    *,
    trials: int,
    seed: int,
) -> dict:
    """Run the preregistered random-support control.

    The control matches the Fano construction only on the number of distinct
    triple supports.  It is not conditioned on signal rank.  The joint
    signal/crosstalk rank contingency is therefore part of the returned
    evidence rather than something inferred from marginal rank counts.
    """

    if trials <= 0:
        raise ValueError("trials must be positive")
    rng = np.random.default_rng(seed)
    all_triples = tuple(itertools.combinations(range(1, _DIM), 3))
    signal_ranks = []
    crosstalk_ranks = []
    joint_ranks = []
    cross_grams = []
    finite_condition_numbers = []
    rank_contingency: dict[tuple[int, int], int] = {}
    exterior_square_rank_mismatches = 0
    joint_sum_rank_mismatches = 0
    first_rank_deficient = None

    for trial in range(trials):
        indices = rng.choice(len(all_triples), size=7, replace=False)
        triples = tuple(all_triples[int(index)] for index in indices)
        basis = algebra_basis(triples)
        report = algebra_report(basis)
        signal_ranks.append(report["signal_rank"])
        crosstalk_ranks.append(report["crosstalk_rank"])
        joint_ranks.append(report["joint_rank"])
        rank_key = (report["signal_rank"], report["crosstalk_rank"])
        rank_contingency[rank_key] = rank_contingency.get(rank_key, 0) + 1
        expected_crosstalk_rank = (
            report["signal_rank"] * (report["signal_rank"] - 1) // 2
        )
        exterior_square_rank_mismatches += int(
            report["crosstalk_rank"] != expected_crosstalk_rank
        )
        joint_sum_rank_mismatches += int(
            report["joint_rank"]
            != report["signal_rank"] + report["crosstalk_rank"]
        )
        cross_grams.append(report["max_abs_cross_gram"])
        if report["joint_condition_number"] is not None:
            finite_condition_numbers.append(report["joint_condition_number"])
        if first_rank_deficient is None and report["crosstalk_rank"] < 21:
            first_rank_deficient = {
                "trial": trial,
                "triples": [list(triple) for triple in triples],
                "signal_rank": report["signal_rank"],
                "crosstalk_rank": report["crosstalk_rank"],
                "joint_rank": report["joint_rank"],
            }

    def counts(values: Sequence[int]) -> dict[str, int]:
        unique, frequency = np.unique(values, return_counts=True)
        return {
            str(int(value)): int(count)
            for value, count in zip(unique, frequency)
        }

    return {
        "trials": trials,
        "seed": seed,
        "matching_scope": (
            "Seven distinct 3-subsets sampled without replacement; not "
            "conditioned on signal rank."
        ),
        "signal_rank_counts": counts(signal_ranks),
        "crosstalk_rank_counts": counts(crosstalk_ranks),
        "joint_rank_counts": counts(joint_ranks),
        "signal_crosstalk_rank_contingency": [
            {
                "signal_rank": signal_rank,
                "crosstalk_rank": crosstalk_rank,
                "count": count,
            }
            for (signal_rank, crosstalk_rank), count
            in sorted(rank_contingency.items())
        ],
        "observed_rank_relation": {
            "relation": "rank(C) = choose(rank(S), 2)",
            "mismatch_count": exterior_square_rank_mismatches,
            "scope": f"the {trials} seeded random-support controls only",
        },
        "observed_joint_rank_relation": {
            "relation": "rank([S C]) = rank(S) + rank(C)",
            "mismatch_count": joint_sum_rank_mismatches,
            "scope": f"the {trials} seeded random-support controls only",
        },
        "full_signal_rank_count": int(
            np.count_nonzero(np.asarray(signal_ranks) == 7)
        ),
        "full_crosstalk_rank_count": int(
            np.count_nonzero(np.asarray(crosstalk_ranks) == 21)
        ),
        "full_joint_rank_count": int(np.count_nonzero(np.asarray(joint_ranks) == 28)),
        "median_crosstalk_rank": float(np.median(crosstalk_ranks)),
        "max_cross_gram": float(np.max(cross_grams)),
        "finite_joint_condition_count": len(finite_condition_numbers),
        "finite_joint_condition_minimum": (
            float(np.min(finite_condition_numbers))
            if finite_condition_numbers
            else None
        ),
        "finite_joint_condition_median": (
            float(np.median(finite_condition_numbers))
            if finite_condition_numbers
            else None
        ),
        "finite_joint_condition_maximum": (
            float(np.max(finite_condition_numbers))
            if finite_condition_numbers
            else None
        ),
        "finite_joint_condition_numbers": [
            float(value) for value in finite_condition_numbers
        ],
        "first_rank_deficient": first_rank_deficient,
    }


def find_rank_deficient_control(summary: dict) -> dict:
    """Exhibit coefficient aliasing for the first rank-deficient control."""

    record = summary.get("first_rank_deficient")
    if not record:
        raise ValueError("control summary contains no rank-deficient design")
    basis = algebra_basis(record["triples"])
    _u, singular, vh = np.linalg.svd(basis.crosstalk, full_matrices=True)
    rank = _matrix_rank(basis.crosstalk)
    if rank >= basis.n_crosstalk:
        raise ValueError("selected control is not rank-deficient")
    null_vector = vh[rank]
    null_vector = null_vector / np.linalg.norm(null_vector)
    residual = basis.crosstalk @ null_vector
    return {
        "trial": record["trial"],
        "triples": record["triples"],
        "signal_rank": int(record["signal_rank"]),
        "crosstalk_rank": rank,
        "joint_rank": int(record["joint_rank"]),
        "nullity": basis.n_crosstalk - rank,
        "smallest_reported_singular_value": float(singular[-1]),
        "coefficient_distance": float(np.linalg.norm(null_vector)),
        "observation_distance": float(np.linalg.norm(residual)),
    }
