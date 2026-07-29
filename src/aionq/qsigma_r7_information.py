"""QSigma-R7: source volume versus fixed-width operational information.

The split form ``Q_(2,2)`` supplies source geometry but is not a distance.
Operational codewords are instead the explicit five-dimensional density
matrices produced by the tested R6 block encoding acting on one fixed Bell
probe, with all failed postselections mapped to one common erasure symbol.

This module deliberately exposes a lower/upper-bound sandwich:

* deterministic greedy trace-distance codebooks are packing lower bounds;
* an erasure-aware pretty-good measurement gives an achievable information
  lower bound for the declared receiver;
* Holevo and oracle-erasure information give upper bounds.

The discarded classical scale ``||M||_2`` is not passed to the receiver.  No
function in this file treats source volume, stored records, or ``N*p`` as bits.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .hyperbolic_qubit import block_encode, q22, swirl_point, to_sl2

_ETA22 = np.diag([1.0, 1.0, -1.0, -1.0])
_BELL = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)


class InvalidOperationalMetric(ValueError):
    """The indefinite source form was requested as a packing metric."""


def source_metric(rho: float) -> np.ndarray:
    """Induced metric in coordinate order ``(rho, phi, psi)``."""
    c, s = math.cosh(float(rho)), math.sinh(float(rho))
    return np.diag([-1.0, c * c, -s * s])


def finite_difference_metric(
    rho: float, phi: float, psi: float, step: float = 1e-5
) -> np.ndarray:
    """Five-point chart derivative, independent of :func:`source_metric`."""
    point = np.array([rho, phi, psi], dtype=float)
    if rho <= 2.0 * step:
        raise ValueError("rho must exceed twice the finite-difference step")

    def chart(coordinates: np.ndarray) -> np.ndarray:
        return swirl_point(*[float(value) for value in coordinates])

    jacobian = np.empty((4, 3), dtype=float)
    for axis in range(3):
        direction = np.zeros(3)
        direction[axis] = step
        jacobian[:, axis] = (
            -chart(point + 2.0 * direction)
            + 8.0 * chart(point + direction)
            - 8.0 * chart(point - direction)
            + chart(point - 2.0 * direction)
        ) / (12.0 * step)
    return jacobian.T @ _ETA22 @ jacobian


def absolute_volume_density(rho: float) -> float:
    """``sqrt(abs(det g)) = cosh(rho)*sinh(rho)``."""
    rho = float(rho)
    if rho < 0.0:
        raise ValueError("rho must be non-negative")
    return math.cosh(rho) * math.sinh(rho)


def slab_volume(radius: float) -> float:
    """Absolute source volume of the Cartan slab ``0 <= rho <= radius``."""
    radius = float(radius)
    if radius < 0.0:
        raise ValueError("radius must be non-negative")
    return 2.0 * math.pi**2 * math.sinh(radius) ** 2


def projective_slab_volume(radius: float) -> float:
    """Source volume after the operational quotient ``M ~ -M``."""
    return slab_volume(radius) / 2.0


def null_separated_witness(t: float = 0.5) -> dict[str, object]:
    """Distinct source points with zero split interval."""
    if t == 0.0:
        raise ValueError("t must be non-zero")
    left = np.array([1.0, 0.0, 0.0, 0.0])
    right = np.array([1.0, float(t), float(t), 0.0])
    return {
        "left": left,
        "right": right,
        "distinct": True,
        "q_left": q22(left),
        "q_right": q22(right),
        "q_delta": q22(right - left),
    }


def reject_split_form_distance(_left, _right) -> float:
    """Forbid ``sqrt(abs(Q(x-y)))`` and related pseudo-distances."""
    raise InvalidOperationalMetric(
        "Q_(2,2) is indefinite and forbidden as an operational distance"
    )


def radial_rescaled_exponents(scale: float) -> dict[str, float]:
    """Both source and R6 cost exponents rescale under ``rho'=scale*rho``."""
    scale = float(scale)
    if scale <= 0.0:
        raise ValueError("scale must be positive")
    return {
        "source": 2.0 / scale,
        "worst_cost": 4.0 / scale,
        "source_to_cost_ratio": 0.5,
    }


@dataclass(frozen=True)
class BellCodeword:
    density: np.ndarray
    success_probability: float
    encoded_matrix: np.ndarray


def bell_codeword(matrix: np.ndarray) -> BellCodeword:
    """R6-normalised Bell-probe state plus one common erasure outcome."""
    matrix = np.asarray(matrix, dtype=complex)
    if matrix.shape != (2, 2):
        raise ValueError("matrix must be 2x2")
    if float(np.linalg.norm(matrix, 2)) == 0.0:
        raise ValueError("cannot encode the zero matrix")
    if float(np.max(np.abs(matrix.imag))) < 1e-14:
        dilation, _ = block_encode(np.asarray(matrix.real, dtype=float))
        encoded = np.asarray(dilation[:2, :2], dtype=complex)
    else:
        encoded = matrix / float(np.linalg.norm(matrix, 2))
    vector = np.kron(np.eye(2, dtype=complex), encoded) @ _BELL
    success = float(np.real(np.vdot(vector, vector)))
    density = np.zeros((5, 5), dtype=complex)
    density[:4, :4] = np.outer(vector, vector.conj())
    density[4, 4] = 1.0 - success
    density = (density + density.conj().T) / 2.0
    if float(np.max(np.abs(density - density.conj().T))) > 1e-12:
        raise ValueError("codeword density is not Hermitian")
    if float(np.min(np.linalg.eigvalsh(density))) < -1e-12:
        raise ValueError("codeword density is not positive semidefinite")
    if abs(float(np.trace(density).real) - 1.0) > 1e-12:
        raise ValueError("codeword density does not have unit trace")
    return BellCodeword(density, success, encoded)


def trace_distance(left: np.ndarray, right: np.ndarray) -> float:
    """Dense trace distance; no cancellation-prone scalar shortcut."""
    left, right = np.asarray(left, complex), np.asarray(right, complex)
    if left.shape != right.shape or left.ndim != 2 or left.shape[0] != left.shape[1]:
        raise ValueError("densities must be equal-sized square matrices")
    difference = left - right
    difference = (difference + difference.conj().T) / 2.0
    value = 0.5 * float(np.sum(np.abs(np.linalg.eigvalsh(difference))))
    if value < -1e-12 or value > 1.0 + 1e-12:
        raise ValueError("trace distance fell outside [0,1]")
    return min(1.0, max(0.0, value))


def compact_su2(theta: float, phi: float, psi: float) -> np.ndarray:
    """``Rz(phi) Ry(theta) Rz(psi)`` matched compact control."""
    c, s = math.cos(theta / 2.0), math.sin(theta / 2.0)
    half_sum = (phi + psi) / 2.0
    half_difference = (phi - psi) / 2.0
    return np.array(
        [
            [
                np.exp(-1j * half_sum) * c,
                -np.exp(-1j * half_difference) * s,
            ],
            [
                np.exp(1j * half_difference) * s,
                np.exp(1j * half_sum) * c,
            ],
        ],
        dtype=complex,
    )


@dataclass(frozen=True)
class Candidate:
    key: str
    family: str
    rho_index: int
    rho: float
    phi_index: int
    psi_index: int
    codeword: BellCodeword


def candidate_grid(
    rhos: Sequence[float],
    n_phi: int = 8,
    n_psi: int = 8,
    *,
    family: str = "hyperbolic",
    phi_indices: Sequence[int] | None = None,
    psi_indices: Sequence[int] | None = None,
) -> list[Candidate]:
    """Frozen source or matched compact candidates."""
    if n_phi <= 0 or n_psi <= 0:
        raise ValueError("angular grid sizes must be positive")
    if family not in {"hyperbolic", "compact"}:
        raise ValueError("family must be hyperbolic or compact")
    phi_indices = list(range(n_phi)) if phi_indices is None else list(phi_indices)
    psi_indices = list(range(n_psi)) if psi_indices is None else list(psi_indices)
    if any(index < 0 or index >= n_phi for index in phi_indices):
        raise ValueError("phi index outside main grid")
    if any(index < 0 or index >= n_psi for index in psi_indices):
        raise ValueError("psi index outside main grid")
    output: list[Candidate] = []
    for rho_index, rho in enumerate(rhos):
        rho = float(rho)
        for phi_index in phi_indices:
            phi = 2.0 * math.pi * phi_index / n_phi
            for psi_index in psi_indices:
                psi = 2.0 * math.pi * psi_index / n_psi
                matrix = (
                    to_sl2(swirl_point(rho, phi, psi))
                    if family == "hyperbolic"
                    else compact_su2(2.0 * math.atan(rho), phi, psi)
                )
                key = f"{family}:{rho_index}:{phi_index}:{psi_index}"
                output.append(
                    Candidate(
                        key,
                        family,
                        rho_index,
                        rho,
                        phi_index,
                        psi_index,
                        bell_codeword(matrix),
                    )
                )
    return output


def deduplicate_candidates(
    candidates: Sequence[Candidate], tolerance: float = 1e-10
) -> tuple[list[Candidate], dict[str, str]]:
    """Canonical dense-trace-distance quotient."""
    retained: list[Candidate] = []
    aliases: dict[str, str] = {}
    for candidate in candidates:
        match = next(
            (
                prior
                for prior in retained
                if trace_distance(
                    candidate.codeword.density, prior.codeword.density
                )
                < tolerance
            ),
            None,
        )
        if match is None:
            retained.append(candidate)
            aliases[candidate.key] = candidate.key
        else:
            aliases[candidate.key] = match.key
    return retained, aliases


def distance_matrix(candidates: Sequence[Candidate]) -> np.ndarray:
    size = len(candidates)
    output = np.zeros((size, size), dtype=float)
    for left in range(size):
        for right in range(left):
            output[left, right] = output[right, left] = trace_distance(
                candidates[left].codeword.density,
                candidates[right].codeword.density,
            )
    return output


def candidate_order(candidates: Sequence[Candidate], policy: str) -> list[int]:
    indices = list(range(len(candidates)))
    canonical = lambda index: (
        candidates[index].rho_index,
        candidates[index].phi_index,
        candidates[index].psi_index,
    )
    if policy == "lexicographic_rho_phi_psi":
        return sorted(indices, key=canonical)
    if policy == "reverse_rho_then_phi_psi":
        return sorted(
            indices,
            key=lambda index: (
                -candidates[index].rho_index,
                candidates[index].phi_index,
                candidates[index].psi_index,
            ),
        )
    prefix = "sha256_order_seed_"
    if policy.startswith(prefix):
        seed = policy[len(prefix) :]
        return sorted(
            indices,
            key=lambda index: (
                hashlib.sha256(
                    (
                        f"{seed}:{candidates[index].rho_index}:"
                        f"{candidates[index].phi_index}:"
                        f"{candidates[index].psi_index}"
                    ).encode("ascii")
                ).digest(),
                canonical(index),
            ),
        )
    raise ValueError(f"unknown order policy: {policy}")


def greedy_codebook(
    distances: np.ndarray,
    epsilon: float,
    order: Iterable[int],
    tolerance: float = 1e-12,
) -> list[int]:
    """Conservative deterministic epsilon-packing lower bound."""
    distances = np.asarray(distances, dtype=float)
    if distances.ndim != 2 or distances.shape[0] != distances.shape[1]:
        raise ValueError("distance matrix must be square")
    order = list(order)
    if sorted(order) != list(range(distances.shape[0])):
        raise ValueError("order must contain each candidate exactly once")
    accepted: list[int] = []
    for index in order:
        if all(
            distances[index, prior] >= epsilon + tolerance
            for prior in accepted
        ):
            accepted.append(index)
    return accepted


def exact_packing_size(
    distances: np.ndarray,
    epsilon: float,
    *,
    maximum_candidates: int = 20,
) -> int:
    """Exact subset enumeration for the declared small-grid control."""
    distances = np.asarray(distances, dtype=float)
    size = distances.shape[0]
    if distances.shape != (size, size) or size > maximum_candidates:
        raise ValueError("exact packing is restricted to the small square control")
    for subset_size in range(size, -1, -1):
        for subset in itertools.combinations(range(size), subset_size):
            if all(
                distances[left, right] >= epsilon + 1e-12
                for left, right in itertools.combinations(subset, 2)
            ):
                return subset_size
    return 0


def von_neumann_entropy(density: np.ndarray, tolerance: float = 1e-12) -> float:
    density = (np.asarray(density, complex) + np.asarray(density, complex).conj().T) / 2
    values = np.linalg.eigvalsh(density)
    if float(np.min(values)) < -tolerance:
        raise ValueError("density is not positive semidefinite")
    values = np.clip(values, 0.0, None)
    values /= float(np.sum(values))
    values = values[values > tolerance]
    return -float(np.sum(values * np.log2(values)))


def _mutual_information(conditional: np.ndarray) -> float:
    conditional = np.asarray(conditional, dtype=float)
    output = np.mean(conditional, axis=0)
    joint = conditional / conditional.shape[0]
    value = 0.0
    for row, column in itertools.product(
        range(conditional.shape[0]), range(conditional.shape[1])
    ):
        if joint[row, column] > 0.0 and output[column] > 0.0:
            value += joint[row, column] * math.log2(
                conditional[row, column] / output[column]
            )
    return float(value)


@dataclass(frozen=True)
class InformationMetrics:
    pgm_mutual_information: float
    holevo_information: float
    oracle_erasure_information: float
    log2_codewords: float
    catalogue_proxy: float
    minimum_success_probability: float
    pgm_maximum_row_defect: float
    pgm_minimum_raw_probability: float
    pgm_support_projector_defect: float
    confusion_digest: str


def information_metrics(codewords: Sequence[BellCodeword]) -> InformationMetrics:
    """Erasure-aware PGM plus Holevo and oracle-erasure upper bounds."""
    if not codewords:
        raise ValueError("at least one codeword is required")
    densities = np.asarray([word.density for word in codewords], complex)
    success_blocks = densities[:, :4, :4]
    count = len(codewords)
    average_success = np.mean(success_blocks, axis=0)
    values, vectors = np.linalg.eigh(
        (average_success + average_success.conj().T) / 2.0
    )
    cutoff = 1e-12 * max(1.0, float(np.max(values)))
    mask = values > cutoff
    support = vectors[:, mask]
    projector = support @ support.conj().T
    inverse_sqrt = (
        support @ np.diag(1.0 / np.sqrt(values[mask])) @ support.conj().T
    )
    effects = np.asarray(
        [
            inverse_sqrt @ (success / count) @ inverse_sqrt
            for success in success_blocks
        ]
    )
    support_defect = float(np.max(np.abs(np.sum(effects, axis=0) - projector)))
    raw = np.empty((count, count + 1), dtype=float)
    for input_index, success in enumerate(success_blocks):
        raw[input_index, :count] = [
            float(np.real(np.trace(effect @ success))) for effect in effects
        ]
        raw[input_index, count] = 1.0 - codewords[input_index].success_probability
    minimum_raw = float(np.min(raw))
    maximum_row_defect = float(np.max(np.abs(np.sum(raw, axis=1) - 1.0)))
    if (
        minimum_raw < -1e-12
        or maximum_row_defect > 1e-10
        or support_defect > 1e-10
    ):
        raise ValueError("erasure-aware PGM failed its numerical guards")
    conditional = np.clip(raw, 0.0, None)
    conditional /= np.sum(conditional, axis=1, keepdims=True)
    pgm = _mutual_information(conditional)
    average_density = np.mean(densities, axis=0)
    holevo = von_neumann_entropy(average_density) - float(
        np.mean([von_neumann_entropy(density) for density in densities])
    )
    success = np.asarray(
        [word.success_probability for word in codewords], dtype=float
    )
    failure = 1.0 - success
    failure_probability = float(np.mean(failure))
    log_count = math.log2(count)
    if failure_probability <= 1e-15:
        oracle = log_count
    else:
        posterior = failure / float(np.sum(failure))
        positive = posterior[posterior > 1e-15]
        oracle = log_count + failure_probability * float(
            np.sum(positive * np.log2(positive))
        )
    digest = hashlib.sha256(
        np.asarray(conditional, dtype="<f8").tobytes(order="C")
    ).hexdigest()
    return InformationMetrics(
        max(0.0, pgm),
        max(0.0, holevo),
        max(0.0, oracle),
        log_count,
        count * float(np.min(success)),
        float(np.min(success)),
        maximum_row_defect,
        minimum_raw,
        support_defect,
        f"sha256:{digest}",
    )
