"""Dimension-matched R6/R6i associative retrieval experiment.

This module implements the frozen QSigma-R6k protocol.  It compares two maps
of exactly the same SL(2,R) source matrices in one ambient ``D=16`` carrier:

* R6: the Bell-probe attempted-use density, including its erasure branch,
  embedded isometrically from ``C^5`` into ``C^16``;
* R6i: the pure Choi-vector state of the guarded Julia/Halmos dilation.

The object called a reservoir here is deliberately narrow: a deterministic,
volatile, four-shard associative store plus a fixed clean PGM receiver.  There
is no recurrent update law and therefore no temporal-reservoir or fading-memory
claim.  The positive/negative shard labels are storage lanes only; the
indefinite split form is not used as a retrieval metric.

Costs remain vector-valued.  Postselection, compiler gate counts, active
support, receiver synthesis, truncation tail, and two-mode energy are never
collapsed into one tunable score.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from aionq.coherent_dilation import (
    coherent_dilation_codeword,
    composition_defect_matrices,
    density_state_diagnostics,
    dilation_diagnostics,
    halmos_dilation,
    normalised_contraction,
)
from aionq.holevo_sandwich import holevo_chi
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state, p_bell

__all__ = [
    "AMBIENT_DIM",
    "CODEWORDS_PER_DEPTH",
    "DEPTHS",
    "NOISE_STRENGTHS",
    "FourShardAssociativeReservoir",
    "PGMReceiver",
    "TaskEnsemble",
    "build_map_tasks",
    "build_pgm_receiver",
    "classify_protocol",
    "compiler_cost_proxy",
    "depolarize",
    "encode_r6",
    "encode_r6i",
    "evaluate_receiver",
    "flagged_truncation_trace_distance",
    "required_cutoff",
    "run_protocol",
    "source_grid",
    "trace_distance",
    "truncated_two_mode_state",
    "truncation_cost_report",
    "validate_protocol_grid",
]

AMBIENT_DIM = 16
CODEWORDS_PER_DEPTH = 32
DEPTHS = (0.1, 0.5, 1.0, 2.0, 4.0)
NOISE_STRENGTHS = (0.0, 0.01, 0.03, 0.1)
TOL = 1e-10
PERTURBATIONS = (
    (0.01, math.pi / 64.0, -math.pi / 80.0),
    (-0.01, -math.pi / 64.0, math.pi / 80.0),
)

_R6_SUCCESS_INDICES = (12, 13, 14, 15)
_R6_ERASURE_INDEX = 0
_SHARD_NAMES = ("positive-0", "positive-1", "tension-0", "tension-1")


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _array_digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(np.asarray(array, dtype="<c16"))
    return "sha256:" + hashlib.sha256(value.tobytes()).hexdigest()


def _validated_density(state: np.ndarray, *, tol: float = TOL) -> np.ndarray:
    rho = np.asarray(state, dtype=complex)
    diagnostics = density_state_diagnostics(rho, tol=tol)
    if not diagnostics.get("valid", False):
        raise ValueError(f"invalid density state: {diagnostics}")
    return rho


def _mean(states: Sequence[np.ndarray]) -> np.ndarray:
    if not states:
        raise ValueError("at least one state is required")
    return sum((np.asarray(state, dtype=complex) for state in states),
               np.zeros_like(np.asarray(states[0], dtype=complex))) / len(states)


def source_grid(
    rho: float,
    n: int = CODEWORDS_PER_DEPTH,
) -> tuple[tuple[float, float, float], ...]:
    """Return the frozen deterministic source ring at one depth."""

    if n < 2 or n % 2:
        raise ValueError("the sign-paired grid needs a positive even size")
    return tuple(
        (
            float(rho),
            2.0 * math.pi * k / n,
            2.0 * math.pi * ((3 * k) % n) / n,
        )
        for k in range(n)
    )


def _source_matrix(point: tuple[float, float, float]) -> np.ndarray:
    return to_sl2(swirl_point(*point)).astype(complex)


def _paired_query_points(
    rho: float,
    class_index: int,
    *,
    n: int = CODEWORDS_PER_DEPTH,
) -> tuple[tuple[tuple[float, float, float], ...],
           tuple[tuple[float, float, float], ...]]:
    """Build paired jitter explicitly, so the second source is always ``-M``."""

    if not 0 <= class_index < n // 2:
        raise ValueError("projective class index is outside the half-grid")
    _, phi, psi = source_grid(rho, n)[class_index]
    positive = []
    negative = []
    for delta_rho, delta_phi, delta_psi in PERTURBATIONS:
        point = (rho + delta_rho, phi + delta_phi, psi + delta_psi)
        partner = (point[0], point[1] + math.pi, point[2] + math.pi)
        positive.append(point)
        negative.append(partner)
    return tuple(positive), tuple(negative)


def encode_r6(matrix: np.ndarray) -> np.ndarray:
    """Passively embed the full R6 attempted-use density into ``C^16``.

    The common erasure flag is placed at ``|0000>``.  The four-dimensional
    success block occupies indices 12..15, disjoint from that flag.  This basis
    convention does not affect the primary global-depolarizing channel.
    """

    native, _ = attempted_use_state(np.asarray(matrix).real)
    expanded = np.zeros((AMBIENT_DIM, AMBIENT_DIM), dtype=complex)
    expanded[_R6_ERASURE_INDEX, _R6_ERASURE_INDEX] = native[4, 4]
    expanded[np.ix_(_R6_SUCCESS_INDICES, _R6_SUCCESS_INDICES)] = native[:4, :4]
    return _validated_density(expanded)


def encode_r6i(matrix: np.ndarray) -> np.ndarray:
    """Encode the same matrix by the guarded coherent Julia/Halmos map."""

    return _validated_density(
        coherent_dilation_codeword(np.asarray(matrix, dtype=complex)),
    )


def _encoder(map_name: str):
    if map_name == "R6":
        return encode_r6
    if map_name == "R6i":
        return encode_r6i
    raise ValueError(f"unknown competing map {map_name!r}")


@dataclass(frozen=True)
class ReservoirRecord:
    key: str
    shard: str
    state: np.ndarray
    metadata: dict


class FourShardAssociativeReservoir:
    """A deterministic volatile store with an append-only JSONL event receipt."""

    def __init__(self, event_path: str | Path | None = None):
        self._shards: tuple[dict[str, ReservoirRecord], ...] = (
            {}, {}, {}, {}
        )
        self._events: list[dict] = []
        self._event_path = Path(event_path) if event_path is not None else None
        if self._event_path is not None:
            self._event_path.parent.mkdir(parents=True, exist_ok=True)
            self._event_path.touch(exist_ok=False)

    @staticmethod
    def shard_index(key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % 4

    def store(self, key: str, state: np.ndarray, metadata: dict) -> ReservoirRecord:
        if not key or any(key in shard for shard in self._shards):
            raise ValueError("reservoir keys must be nonempty and unique")
        rho = _validated_density(state).copy()
        rho.setflags(write=False)
        index = self.shard_index(key)
        record = ReservoirRecord(
            key=key,
            shard=_SHARD_NAMES[index],
            state=rho,
            metadata=dict(metadata),
        )
        self._shards[index][key] = record
        event = {
            "sequence": len(self._events),
            "action": "store",
            "key": key,
            "shard": record.shard,
            "state_digest": _array_digest(rho),
            "metadata": record.metadata,
        }
        self._events.append(event)
        if self._event_path is not None:
            with self._event_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, allow_nan=False, sort_keys=True) + "\n")
        return record

    def get(self, key: str) -> ReservoirRecord:
        index = self.shard_index(key)
        try:
            return self._shards[index][key]
        except KeyError as exc:
            raise KeyError(f"unknown reservoir key {key!r}") from exc

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def shard_counts(self) -> dict[str, int]:
        return {
            name: len(self._shards[index])
            for index, name in enumerate(_SHARD_NAMES)
        }

    @property
    def event_digest(self) -> str:
        return _canonical_digest(self._events)


@dataclass(frozen=True)
class TaskEnsemble:
    name: str
    templates: tuple[np.ndarray, ...]
    queries: tuple[np.ndarray, ...]
    depth: float | None

    @property
    def classes(self) -> int:
        return len(self.templates)


def _signed_codebooks(
    map_name: str,
    rho: float,
    reservoir: FourShardAssociativeReservoir | None,
) -> tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...], tuple[np.ndarray, ...]]:
    encode = _encoder(map_name)
    points = source_grid(rho)
    matrices = tuple(_source_matrix(point) for point in points)
    half = CODEWORDS_PER_DEPTH // 2
    for k in range(half):
        residual = float(np.linalg.norm(matrices[k + half] + matrices[k], "fro"))
        if residual > TOL:
            raise ValueError(f"central sign pairing failed at rho={rho}, k={k}")

    templates = tuple(encode(matrix) for matrix in matrices)
    queries: list[np.ndarray] = []
    for k in range(half):
        positive, negative = _paired_query_points(rho, k)
        positive_state = _mean([encode(_source_matrix(point)) for point in positive])
        negative_state = _mean([encode(_source_matrix(point)) for point in negative])
        queries.extend((_validated_density(positive_state),
                        _validated_density(negative_state)))

    # Interleave above gives [k,+], [k,-]; reorder to grid order [all +, all -].
    ordered_queries = tuple(queries[2 * k] for k in range(half)) + tuple(
        queries[2 * k + 1] for k in range(half)
    )
    if reservoir is not None:
        encoded_digests = []
        retrieved = []
        for k, state in enumerate(templates):
            key = f"{map_name}:rho={rho:.1f}:k={k:02d}"
            encoded_digests.append(_array_digest(state))
            reservoir.store(
                key,
                state,
                {"map": map_name, "rho": rho, "source_index": k},
            )
            retrieved.append(reservoir.get(key).state)
        retrieved_digests = [_array_digest(state) for state in retrieved]
        if retrieved_digests != encoded_digests:
            raise ValueError("reservoir retrieval changed a stored template")
        # Every downstream task is derived from the fetched shard records.
        templates = tuple(retrieved)
    return templates, ordered_queries, matrices


def _projective_task(
    templates: Sequence[np.ndarray],
    queries: Sequence[np.ndarray],
    rho: float,
) -> TaskEnsemble:
    half = len(templates) // 2
    projective_templates = tuple(
        _validated_density((templates[k] + templates[k + half]) / 2.0)
        for k in range(half)
    )
    projective_queries = tuple(
        _validated_density((queries[k] + queries[k + half]) / 2.0)
        for k in range(half)
    )
    return TaskEnsemble(
        name="projective_fixed_depth",
        templates=projective_templates,
        queries=projective_queries,
        depth=rho,
    )


def build_map_tasks(
    map_name: str,
    reservoir: FourShardAssociativeReservoir | None = None,
) -> tuple[tuple[TaskEnsemble, ...], dict]:
    """Build all frozen signed, projective, radial, and joint tasks for one map."""

    signed_tasks: list[TaskEnsemble] = []
    projective_tasks: list[TaskEnsemble] = []
    matrix_payload: list[dict] = []
    coordinate_payload: list[dict] = []
    perturbed_coordinate_payload: list[dict] = []
    max_pair_residual = 0.0
    for rho in DEPTHS:
        templates, queries, matrices = _signed_codebooks(map_name, rho, reservoir)
        for k, point in enumerate(source_grid(rho)):
            coordinate_payload.append({"rho": rho, "index": k, "point": point})
        for k in range(CODEWORDS_PER_DEPTH // 2):
            positive, negative = _paired_query_points(rho, k)
            perturbed_coordinate_payload.append({
                "rho": rho,
                "projective_index": k,
                "positive": positive,
                "negative": negative,
                "mixture_weights": (0.5, 0.5),
            })
        signed_tasks.append(
            TaskEnsemble(
                name="signed_fixed_depth",
                templates=templates,
                queries=queries,
                depth=rho,
            )
        )
        projective_tasks.append(_projective_task(templates, queries, rho))
        half = len(matrices) // 2
        max_pair_residual = max(
            max_pair_residual,
            max(float(np.linalg.norm(matrices[k + half] + matrices[k], "fro"))
                for k in range(half)),
        )
        matrix_payload.extend(
            {
                "rho": rho,
                "index": k,
                "matrix": [
                    [float(np.real(value)), float(np.imag(value))]
                    for value in matrix.reshape(-1)
                ],
            }
            for k, matrix in enumerate(matrices)
        )

    radial = TaskEnsemble(
        name="radial",
        templates=tuple(_mean(task.templates) for task in signed_tasks),
        queries=tuple(_mean(task.queries) for task in signed_tasks),
        depth=None,
    )
    joint = TaskEnsemble(
        name="joint_depth_projective",
        templates=tuple(
            state for task in projective_tasks for state in task.templates
        ),
        queries=tuple(
            state for task in projective_tasks for state in task.queries
        ),
        depth=None,
    )
    tasks = tuple(signed_tasks + projective_tasks + [radial, joint])
    return tasks, {
        "source_matrix_digest": _canonical_digest(matrix_payload),
        "source_coordinate_digest": _canonical_digest(coordinate_payload),
        "perturbed_coordinate_digest": _canonical_digest(
            perturbed_coordinate_payload
        ),
        "maximum_central_pair_residual": max_pair_residual,
        "task_count": len(tasks),
        "class_counts": {task.name: task.classes for task in tasks},
    }


@dataclass(frozen=True)
class PGMReceiver:
    effects: tuple[np.ndarray, ...]
    reject_effect: np.ndarray
    support_projector: np.ndarray
    diagnostics: dict


def build_pgm_receiver(
    templates: Sequence[np.ndarray],
    *,
    tol: float = TOL,
) -> PGMReceiver:
    """Construct a clean PGM and its explicit support-complement outcome."""

    states = tuple(_validated_density(state, tol=tol) for state in templates)
    count = len(states)
    if count < 1:
        raise ValueError("receiver needs at least one template")
    dimension = states[0].shape[0]
    if any(state.shape != (dimension, dimension) for state in states):
        raise ValueError("all receiver templates must share one dimension")
    priors = np.full(count, 1.0 / count)
    mean = sum(q * state for q, state in zip(priors, states))
    values, vectors = np.linalg.eigh((mean + mean.conj().T) / 2.0)
    maximum = max(0.0, float(np.max(np.real(values))))
    cutoff = 64.0 * np.finfo(float).eps * dimension * maximum
    mask = np.real(values) > cutoff
    support = vectors[:, mask]
    projector = support @ support.conj().T
    inverse_sqrt = (
        support
        @ np.diag(1.0 / np.sqrt(np.real(values[mask])))
        @ support.conj().T
    )
    effects = tuple(
        inverse_sqrt @ (q * state) @ inverse_sqrt
        for q, state in zip(priors, states)
    )
    reject = np.eye(dimension, dtype=complex) - projector
    completeness = sum(effects, np.zeros_like(reject)) + reject
    all_effects = effects + (reject,)
    minimum_effect_eigenvalue = min(
        float(np.min(np.linalg.eigvalsh((effect + effect.conj().T) / 2.0)))
        for effect in all_effects
    )
    hermiticity = max(
        float(np.linalg.norm(effect - effect.conj().T, "fro"))
        for effect in all_effects
    )
    diagnostics = {
        "classes": count,
        "ambient_dimension": dimension,
        "clean_mean_support_rank": int(np.sum(mask)),
        "support_cutoff": float(cutoff),
        "minimum_effect_eigenvalue": minimum_effect_eigenvalue,
        "maximum_effect_hermiticity_residual": hermiticity,
        "completeness_residual": float(
            np.linalg.norm(completeness - np.eye(dimension), 2)
        ),
        "support_projector_residual": float(
            np.linalg.norm(projector @ projector - projector, 2)
        ),
    }
    diagnostics["valid"] = bool(
        minimum_effect_eigenvalue >= -tol
        and hermiticity <= tol
        and diagnostics["completeness_residual"] <= tol
        and diagnostics["support_projector_residual"] <= tol
    )
    if not diagnostics["valid"]:
        raise ValueError(f"PGM receiver failed controls: {diagnostics}")
    return PGMReceiver(effects, reject, projector, diagnostics)


def depolarize(state: np.ndarray, strength: float) -> np.ndarray:
    """Apply the basis-invariant global depolarizing channel in the live dimension."""

    if not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
        raise ValueError("depolarizing strength must lie in [0,1]")
    rho = _validated_density(state)
    dimension = rho.shape[0]
    output = (1.0 - strength) * rho + strength * np.eye(dimension) / dimension
    return _validated_density(output)


def _mutual_information_without_row_repair(conditional: np.ndarray) -> float:
    """Mutual information of raw outcome rows, including reject as an outcome."""

    count = conditional.shape[0]
    joint = conditional / count
    px = np.sum(joint, axis=1)
    py = np.sum(joint, axis=0)
    information = 0.0
    for i in range(count):
        for j in range(conditional.shape[1]):
            probability = joint[i, j]
            if probability > 1e-15 and px[i] > 1e-15 and py[j] > 1e-15:
                information += probability * math.log2(probability / (px[i] * py[j]))
    return float(information)


def _hilbert_schmidt_oracle_accuracy(
    templates: Sequence[np.ndarray],
    queries: Sequence[np.ndarray],
    *,
    tie_tolerance: float = 1e-12,
) -> float:
    """Tie-aware Frobenius nearest-density oracle; tomography is uncharged."""

    credits = []
    for correct, query in enumerate(queries):
        distances = np.array([
            float(np.linalg.norm(template - query, "fro") ** 2)
            for template in templates
        ])
        best = float(np.min(distances))
        tied = np.flatnonzero(np.abs(distances - best) <= tie_tolerance)
        credits.append(1.0 / len(tied) if correct in tied else 0.0)
    return float(np.mean(credits))


def evaluate_receiver(
    receiver: PGMReceiver,
    templates: Sequence[np.ndarray],
    queries: Sequence[np.ndarray],
    *,
    noise_strength: float,
    tol: float = TOL,
) -> dict:
    """Apply one frozen clean receiver to noisy queries without row normalization."""

    if len(templates) != len(queries) or len(queries) != len(receiver.effects):
        raise ValueError("templates, query labels, and PGM effects must align")
    noisy = tuple(depolarize(query, noise_strength) for query in queries)
    outcomes = receiver.effects + (receiver.reject_effect,)
    complex_conditional = np.array([
        [np.einsum("ij,ji->", effect, query) for effect in outcomes]
        for query in noisy
    ], dtype=complex)
    conditional = np.real(complex_conditional)
    row_sums = np.sum(conditional, axis=1)
    minimum = float(np.min(conditional))
    maximum = float(np.max(conditional))
    row_defect = float(np.max(np.abs(row_sums - 1.0)))
    imaginary = float(np.max(np.abs(np.imag(complex_conditional))))
    if minimum < -tol or maximum > 1.0 + tol or row_defect > tol or imaginary > tol:
        raise ValueError(
            "raw PGM probabilities failed before any numerical clipping: "
            f"min={minimum}, max={maximum}, row={row_defect}, imag={imaginary}"
        )
    count = len(queries)
    correct = float(np.mean([conditional[i, i] for i in range(count)]))
    reject = float(np.mean(conditional[:, -1]))
    return {
        "correct_probability": correct,
        "mutual_information_bits": _mutual_information_without_row_repair(conditional),
        "abstention_probability": reject,
        "conditional_correct_given_response": (
            correct / (1.0 - reject) if reject < 1.0 - 1e-15 else 0.0
        ),
        "holevo_chi_bits": float(holevo_chi(noisy)),
        "hilbert_schmidt_tomography_oracle_accuracy": (
            _hilbert_schmidt_oracle_accuracy(templates, noisy)
        ),
        "minimum_raw_probability": minimum,
        "maximum_raw_probability": maximum,
        "maximum_raw_row_sum_defect": row_defect,
        "maximum_raw_imaginary_probability": imaginary,
        "confusion_digest": _array_digest(conditional),
        "receiver": dict(receiver.diagnostics),
    }


def trace_distance(first: np.ndarray, second: np.ndarray) -> float:
    """Trace distance between two Hermitian density states."""

    delta = _validated_density(first) - _validated_density(second)
    values = np.linalg.eigvalsh((delta + delta.conj().T) / 2.0)
    return float(0.5 * np.sum(np.abs(np.real(values))))


def truncated_two_mode_state(
    rho: float,
    theta: float,
    *,
    cutoff: int = 4,
    flag_index: int = 1,
) -> np.ndarray:
    """Exact projected two-mode-squeezed orbit plus an explicit tail flag.

    ``tau=tanh(rho)^(2 cutoff)`` is not discarded or renormalized.  The output
    lives in ``C^(cutoff^2)``; ``flag_index`` must be outside the correlated
    ``|n,n>`` sector.
    """

    if rho < 0.0 or not math.isfinite(rho):
        raise ValueError("rho must be finite and nonnegative")
    if cutoff < 2:
        raise ValueError("cutoff must be at least two")
    dimension = cutoff * cutoff
    diagonal_indices = {n * cutoff + n for n in range(cutoff)}
    if flag_index in diagonal_indices or not 0 <= flag_index < dimension:
        raise ValueError("tail flag must be an unused basis state")
    amplitude = np.zeros(dimension, dtype=complex)
    tanh = math.tanh(rho)
    sech = 1.0 / math.cosh(rho)
    for n in range(cutoff):
        amplitude[n * cutoff + n] = (
            sech * (tanh ** n) * np.exp(1j * n * theta)
        )
    tail = tanh ** (2 * cutoff)
    state = np.outer(amplitude, amplitude.conj())
    state[flag_index, flag_index] += tail
    return _validated_density(state)


def required_cutoff(rho: float, tail_budget: float) -> int:
    """Minimum per-mode cutoff with ``tanh(rho)^(2 cutoff)<=tail_budget``."""

    if rho < 0.0 or not math.isfinite(rho):
        raise ValueError("rho must be finite and nonnegative")
    if not 0.0 < tail_budget < 1.0:
        raise ValueError("tail budget must lie strictly between zero and one")
    base = math.tanh(rho) ** 2
    if base == 0.0:
        return 1
    return max(1, int(math.ceil(math.log(tail_budget) / math.log(base))))


def flagged_truncation_trace_distance(tail_probability: float) -> float:
    """Exact distance from the emitted flagged state to the infinite pure orbit.

    If ``v=P psi`` and the omitted vector ``w`` has norm squared ``tau``, the
    emitted state is ``|v><v| + tau |e><e|`` with an orthogonal flag ``e``.
    Direct diagonalisation on ``span(v,w,e)`` gives

        D = (tau + sqrt(4 tau - 3 tau^2)) / 2.

    ``sqrt(tau)`` is instead the distance to the *normalized pure projection*;
    both are reported, but only this flagged-state distance gates the control.
    """

    tau = float(tail_probability)
    if not math.isfinite(tau) or not 0.0 <= tau <= 1.0:
        raise ValueError("tail probability must lie in [0,1]")
    return 0.5 * (tau + math.sqrt(max(0.0, 4.0 * tau - 3.0 * tau * tau)))


def _trace_budget_to_tail_budget(trace_budget: float) -> float:
    if not math.isfinite(trace_budget) or not 0.0 < trace_budget < 1.0:
        raise ValueError("trace-distance budget must lie strictly between zero and one")
    return 0.5 * (
        1.0
        + trace_budget
        - math.sqrt(1.0 + 2.0 * trace_budget - 3.0 * trace_budget ** 2)
    )


def truncation_cost_report(
    depths: Iterable[float] = DEPTHS,
    *,
    cutoff: int = 4,
    trace_error_budgets: Sequence[float] = (0.01, 0.05, 0.1),
) -> dict:
    """Price the exact tail and energy wall without treating R6T as a competitor."""

    rows = []
    for rho in depths:
        tail = math.tanh(rho) ** (2 * cutoff)
        projection_trace_error = math.sqrt(tail)
        flagged_trace_error = flagged_truncation_trace_distance(tail)
        worst_query_rho = rho + max(delta[0] for delta in PERTURBATIONS)
        worst_query_tail = math.tanh(worst_query_rho) ** (2 * cutoff)
        worst_query_trace_error = flagged_truncation_trace_distance(worst_query_tail)
        required = {
            f"trace_error<={budget:g}": {
                "tail_probability_budget": _trace_budget_to_tail_budget(budget),
                "per_mode_cutoff": required_cutoff(
                    rho, _trace_budget_to_tail_budget(budget)
                ),
                "two_mode_dimension": required_cutoff(
                    rho, _trace_budget_to_tail_budget(budget)
                ) ** 2,
            }
            for budget in trace_error_budgets
        }
        rows.append({
            "rho": float(rho),
            "cutoff_per_mode": cutoff,
            "ambient_dimension": cutoff * cutoff,
            "active_correlated_sector_dimension": cutoff,
            "tail_probability": tail,
            "normalized_projection_trace_distance": projection_trace_error,
            "flagged_state_trace_distance": flagged_trace_error,
            "worst_perturbed_query_rho": worst_query_rho,
            "worst_perturbed_query_tail_probability": worst_query_tail,
            "worst_perturbed_query_flagged_trace_distance": worst_query_trace_error,
            "mean_total_photons_in_infinite_orbit": 2.0 * math.sinh(rho) ** 2,
            "cutoff_max_total_photons": 2 * (cutoff - 1),
            "inside_primary_trace_error_budget_0.05": (
                worst_query_trace_error <= 0.05
            ),
            "required_dimensions": required,
        })
    return {
        "map": "R6T",
        "competitor": False,
        "orbit": "SU(1,1)/U(1) lowest-weight two-mode-squeezed orbit",
        "lost_coordinate": "one compact SL(2,R) coordinate",
        "rows": rows,
    }


def _global_phase_residual(target: np.ndarray, observed: np.ndarray) -> float:
    inner = np.vdot(target.reshape(-1), observed.reshape(-1))
    if abs(inner) == 0.0:
        return float("inf")
    phase = inner / abs(inner)
    return float(np.linalg.norm(observed - phase * target, "fro"))


def compiler_cost_proxy(
    matrix: np.ndarray | None = None,
    *,
    optimization_level: int = 3,
    seed_transpiler: int = 11,
) -> dict:
    """Compile encoder circuits to ``u,cx`` as an environment-bound proxy."""

    from qiskit import QuantumCircuit, __version__ as qiskit_version, transpile
    from qiskit.quantum_info import Operator, Statevector

    if matrix is None:
        matrix = _source_matrix((1.0, 0.4, 0.7))
    contraction = normalised_contraction(matrix)
    unitary = halmos_dilation(contraction)

    core = QuantumCircuit(2, name="shared_halmos_core")
    core.unitary(unitary, [0, 1])

    r6 = QuantumCircuit(4, 1, name="R6_encoder_proxy")
    r6.h(0)
    r6.cx(0, 1)
    # q0 is the Bell data qubit, q1 its reference, and q2 the block ancilla.
    # With Qiskit's little-endian basis this makes the kept q2=0 branch equal
    # (I tensor A)|Phi+>, matching attempted_use_state.
    r6.unitary(unitary, [0, 2])
    r6.measure(2, 0)

    r6_unmeasured = QuantumCircuit(4, name="R6_encoder_state_control")
    r6_unmeasured.h(0)
    r6_unmeasured.cx(0, 1)
    r6_unmeasured.unitary(unitary, [0, 2])

    r6i = QuantumCircuit(4, name="R6i_encoder_proxy")
    r6i.h(0)
    r6i.cx(0, 2)
    r6i.h(1)
    r6i.cx(1, 3)
    # Low bits q0,q1 carry the row index i and high bits q2,q3 the column
    # index j.  Applying U to [q0,q1] therefore prepares vec_F(U)/2 exactly.
    r6i.unitary(unitary, [0, 1])

    settings = {
        "basis_gates": ["u", "cx"],
        "optimization_level": optimization_level,
        "seed_transpiler": seed_transpiler,
    }
    compiled_core = transpile(core, **settings)
    compiled_r6 = transpile(r6, **settings)
    compiled_r6i = transpile(r6i, **settings)
    target_operator = Operator(core).data
    observed_operator = Operator(compiled_core).data
    r6i_vector = np.asarray(Statevector.from_instruction(r6i).data)
    r6i_target = coherent_dilation_codeword(np.asarray(matrix, dtype=complex))
    r6i_observed = np.outer(r6i_vector, r6i_vector.conj())

    r6_vector = np.asarray(Statevector.from_instruction(r6_unmeasured).data)
    # q3 is idle and q2 is the block ancilla.  q2=0 occupies indices 0..3.
    success = r6_vector[:4]
    success_probability = float(np.vdot(success, success).real)
    r6_coarse_grained = np.zeros((AMBIENT_DIM, AMBIENT_DIM), dtype=complex)
    r6_coarse_grained[
        np.ix_(_R6_SUCCESS_INDICES, _R6_SUCCESS_INDICES)
    ] = np.outer(success, success.conj())
    r6_coarse_grained[_R6_ERASURE_INDEX, _R6_ERASURE_INDEX] = (
        1.0 - success_probability
    )
    r6_target = encode_r6(np.asarray(matrix))

    def circuit_row(circuit) -> dict:
        counts = {str(key): int(value) for key, value in circuit.count_ops().items()}
        return {
            "u": counts.get("u", 0),
            "cx": counts.get("cx", 0),
            "measure": counts.get("measure", 0),
            "depth": int(circuit.depth()),
            "size": int(circuit.size()),
            "all_counts": counts,
        }

    rows = {
        "shared_halmos_core": circuit_row(compiled_core),
        "R6": circuit_row(compiled_r6),
        "R6i": circuit_row(compiled_r6i),
    }
    return {
        "qiskit_version": qiskit_version,
        "settings": settings,
        "rows": rows,
        "shared_core_global_phase_residual": _global_phase_residual(
            target_operator, observed_operator
        ),
        "R6i_full_state_fidelity": float(np.real(np.trace(r6i_target @ r6i_observed))),
        "R6i_full_density_residual": float(
            np.linalg.norm(r6i_target - r6i_observed, "fro")
        ),
        "R6_coarse_grained_density_residual": float(
            np.linalg.norm(r6_target - r6_coarse_grained, "fro")
        ),
        "R6_common_erasure_coarse_graining_charged": False,
        "receiver_povm_synthesis_charged": False,
        "qualification": (
            "Encoder compiler proxy only; R6 common-erasure coarse graining, "
            "coupling, timing, calibration, Naimark receiver synthesis, and "
            "hardware execution are not priced."
        ),
    }


def _resource_ledger(compiler: dict) -> dict:
    rows = []
    for rho in DEPTHS:
        bell = p_bell(rho)
        minimum = math.exp(-4.0 * rho)
        rows.append({
            "rho": rho,
            "R6": {
                "ambient_dimension": AMBIENT_DIM,
                "allocated_qubits": 4,
                "active_encoder_qubits": 3,
                "shared_halmos_core_calls": 1,
                "bell_pairs": 1,
                "measurement": 1,
                "common_erasure_coarse_graining": True,
                "p_bell": bell,
                "p_min": minimum,
                "expected_attempts_bell_if_conditioning": 1.0 / bell,
                "expected_attempts_worst_if_conditioning": 1.0 / minimum,
                "one_shot_density_already_charges_erasure": True,
                "representation_truncation_error": None,
            },
            "R6i": {
                "ambient_dimension": AMBIENT_DIM,
                "allocated_qubits": 4,
                "active_encoder_qubits": 4,
                "shared_halmos_core_calls": 1,
                "bell_pairs": 2,
                "measurement": 0,
                "postselection": False,
                "expected_attempts": 1.0,
                "representation_truncation_error": None,
            },
        })
    identity_defect = composition_defect_matrices(np.eye(2), np.eye(2))
    generic_defect = composition_defect_matrices(
        _source_matrix((0.3, 0.2, -0.1)),
        _source_matrix((0.5, -0.4, 0.7)),
    )
    r6_cost = compiler["rows"]["R6"]
    r6i_cost = compiler["rows"]["R6i"]
    envelope = {
        "same_ambient_dimension": True,
        "same_allocated_qubits": True,
        "same_shared_core_calls": True,
        "additional_active_qubits": 1,
        "additional_bell_pairs": 1,
        "additional_compiled_cx": r6i_cost["cx"] - r6_cost["cx"],
        "shared_core_residual_within_tolerance": (
            compiler["shared_core_global_phase_residual"] <= TOL
        ),
        "R6i_full_state_matches_declared_codeword": (
            compiler["R6i_full_density_residual"] <= TOL
        ),
        "R6_success_erasure_instrument_matches_declared_state": (
            compiler["R6_coarse_grained_density_residual"] <= TOL
        ),
        "R6_common_erasure_coarse_graining_charged": compiler[
            "R6_common_erasure_coarse_graining_charged"
        ],
    }
    envelope["passed"] = bool(
        envelope["additional_active_qubits"] <= 1
        and envelope["additional_bell_pairs"] <= 1
        and envelope["additional_compiled_cx"] <= 1
        and envelope["shared_core_residual_within_tolerance"]
        and envelope["R6i_full_state_matches_declared_codeword"]
        and envelope["R6_success_erasure_instrument_matches_declared_state"]
    )
    return {
        "rule": "vector valued; no scalar resource score",
        "depth_rows": rows,
        "compiler_proxy": compiler,
        "R6i_identity_composition_defect": identity_defect,
        "R6i_generic_composition_defect": generic_defect,
        "resource_envelope": envelope,
    }


def _evaluate_task_rows(map_name: str, tasks: Sequence[TaskEnsemble]) -> list[dict]:
    rows = []
    for task in tasks:
        receiver = build_pgm_receiver(task.templates)
        template_digest = _canonical_digest([
            _array_digest(state) for state in task.templates
        ])
        query_digest = _canonical_digest([
            _array_digest(state) for state in task.queries
        ])
        per_codeword_ranks = [
            density_state_diagnostics(state)["rank"] for state in task.templates
        ]
        for noise in NOISE_STRENGTHS:
            metrics = evaluate_receiver(
                receiver,
                task.templates,
                task.queries,
                noise_strength=noise,
            )
            rows.append({
                "map": map_name,
                "task": task.name,
                "rho": task.depth,
                "classes": task.classes,
                "noise_strength": noise,
                "chance_probability": 1.0 / task.classes,
                "template_digest": template_digest,
                "query_digest": query_digest,
                "clean_per_codeword_rank_min": int(min(per_codeword_ranks)),
                "clean_per_codeword_rank_max": int(max(per_codeword_ranks)),
                **metrics,
            })
    return rows


def _difference(
    rows: Sequence[dict],
    task: str,
    noise: float,
    rho: float | None,
) -> dict:
    selected = {
        row["map"]: row
        for row in rows
        if row["task"] == task
        and row["noise_strength"] == noise
        and row["rho"] == rho
    }
    if set(selected) != {"R6", "R6i"}:
        raise ValueError(f"missing comparison cell {(task, noise, rho)}")
    first, second = selected["R6"], selected["R6i"]
    return {
        "correct_probability": (
            second["correct_probability"] - first["correct_probability"]
        ),
        "mutual_information_bits": (
            second["mutual_information_bits"] - first["mutual_information_bits"]
        ),
        "tomography_oracle_accuracy": (
            second["hilbert_schmidt_tomography_oracle_accuracy"]
            - first["hilbert_schmidt_tomography_oracle_accuracy"]
        ),
    }


def validate_protocol_grid(rows: Sequence[dict]) -> dict:
    """Require the exact frozen 96-cell finite comparison grid."""

    expected = set()
    for map_name in ("R6", "R6i"):
        for noise in NOISE_STRENGTHS:
            for task_name, classes in (
                ("signed_fixed_depth", 32),
                ("projective_fixed_depth", 16),
            ):
                for rho in DEPTHS:
                    expected.add((map_name, task_name, rho, noise, classes))
            expected.add((map_name, "radial", None, noise, 5))
            expected.add((map_name, "joint_depth_projective", None, noise, 80))

    reasons: list[str] = []
    observed = []
    numeric_fields = (
        "correct_probability",
        "mutual_information_bits",
        "abstention_probability",
        "holevo_chi_bits",
        "hilbert_schmidt_tomography_oracle_accuracy",
        "minimum_raw_probability",
        "maximum_raw_probability",
        "maximum_raw_row_sum_defect",
        "maximum_raw_imaginary_probability",
    )
    for index, row in enumerate(rows):
        try:
            classes_value = row["classes"]
            if isinstance(classes_value, bool) or int(classes_value) != classes_value:
                raise ValueError("classes is not an integer")
            key = (
                row["map"], row["task"], row["rho"],
                row["noise_strength"], int(classes_value),
            )
            observed.append(key)
            for field in numeric_fields:
                value = float(row[field])
                if not math.isfinite(value):
                    raise ValueError(f"{field} is nonfinite")
            for field in ("template_digest", "query_digest", "confusion_digest"):
                value = row[field]
                if not isinstance(value, str) or not value.startswith("sha256:"):
                    raise ValueError(f"{field} is not a SHA-256 binding")
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"row {index}: {exc}")

    observed_set = set(observed)
    if len(rows) != 96:
        reasons.append(f"expected 96 rows, observed {len(rows)}")
    if len(observed) != len(observed_set):
        reasons.append("comparison grid contains duplicate keys")
    missing = sorted(expected - observed_set, key=repr)
    extra = sorted(observed_set - expected, key=repr)
    if missing:
        reasons.append(f"missing keys: {missing}")
    if extra:
        reasons.append(f"extra keys: {extra}")
    return {
        "valid": not reasons,
        "expected_cells": 96,
        "observed_cells": len(rows),
        "unique_keys": len(observed_set),
        "reasons": reasons,
    }


def _validate_truncation_grid(rows: Sequence[dict]) -> dict:
    expected = {
        ("R6T", "projective_coset_truncation_control", rho, noise, 16)
        for rho in DEPTHS for noise in NOISE_STRENGTHS
    }
    observed = []
    reasons = []
    numeric_fields = (
        "correct_probability",
        "mutual_information_bits",
        "abstention_probability",
        "holevo_chi_bits",
        "tail_probability",
        "flagged_state_trace_distance",
        "worst_perturbed_query_flagged_trace_distance",
    )
    for index, row in enumerate(rows):
        try:
            classes_value = row["classes"]
            if isinstance(classes_value, bool) or int(classes_value) != classes_value:
                raise ValueError("classes is not an integer")
            observed.append((
                row["map"], row["task"], row["rho"],
                row["noise_strength"], int(classes_value),
            ))
            if not all(math.isfinite(float(row[field])) for field in numeric_fields):
                raise ValueError("nonfinite truncation metric")
            for field in ("template_digest", "query_digest", "confusion_digest"):
                if not str(row[field]).startswith("sha256:"):
                    raise ValueError(f"{field} is not bound")
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"row {index}: {exc}")
    observed_set = set(observed)
    if len(rows) != 20:
        reasons.append(f"expected 20 rows, observed {len(rows)}")
    if len(observed) != len(observed_set):
        reasons.append("truncation grid contains duplicate keys")
    if expected != observed_set:
        reasons.append("truncation key set differs from the frozen grid")
    return {
        "valid": not reasons,
        "expected_cells": 20,
        "observed_cells": len(rows),
        "unique_keys": len(observed_set),
        "reasons": reasons,
    }


def classify_protocol(
    rows: Sequence[dict],
    checks: dict[str, bool],
    resource_envelope: dict,
) -> dict:
    """Apply the frozen anisotropic decision rule without fitting results."""

    grid_validation = validate_protocol_grid(rows)
    if not grid_validation["valid"]:
        return {
            "verdict": "HOLD",
            "signed_survival": False,
            "projective_angular_survival": False,
            "radial_survival": False,
            "joint_depth_projective_survival": False,
            "controls_pass": False,
            "resource_envelope_pass": bool(resource_envelope.get("passed", False)),
            "grid_validation": grid_validation,
            "hold_reasons": grid_validation["reasons"],
            "global_winner": None,
            "decision_semantics": {
                "comparison": "R6i minus R6 differential gain",
                "legacy_survival_fields": (
                    "Every *_survival Boolean is a differential threshold, not "
                    "a statement that either map has or lacks absolute information."
                ),
                "absolute_information_inference_permitted": False,
            },
        }

    signed_counts = {}
    angular_counts = {}
    comparison_cells = []
    for noise in NOISE_STRENGTHS:
        signed_passes = 0
        angular_passes = 0
        for rho in DEPTHS:
            signed = _difference(rows, "signed_fixed_depth", noise, rho)
            projective = _difference(rows, "projective_fixed_depth", noise, rho)
            signed_pass = bool(
                signed["correct_probability"] >= 1.0 / 32.0
                and signed["mutual_information_bits"] >= 0.02
            )
            angular_pass = bool(
                projective["correct_probability"] >= 1.0 / 16.0
                and projective["mutual_information_bits"] >= 0.02
            )
            signed_passes += int(signed_pass)
            angular_passes += int(angular_pass)
            comparison_cells.extend([
                {"task": "signed_fixed_depth", "noise_strength": noise,
                 "rho": rho, "passes": signed_pass, **signed},
                {"task": "projective_fixed_depth", "noise_strength": noise,
                 "rho": rho, "passes": angular_pass, **projective},
            ])
        signed_counts[str(noise)] = signed_passes
        angular_counts[str(noise)] = angular_passes

    radial_cells = []
    joint_cells = []
    for noise in NOISE_STRENGTHS:
        radial = _difference(rows, "radial", noise, None)
        joint = _difference(rows, "joint_depth_projective", noise, None)
        radial_pass = bool(
            radial["correct_probability"] >= 1.0 / 5.0
            and radial["mutual_information_bits"] >= 0.02
        )
        joint_pass = bool(
            joint["correct_probability"] >= 1.0 / 80.0
            and joint["mutual_information_bits"] >= 0.02
        )
        radial_cells.append({"noise_strength": noise, "passes": radial_pass, **radial})
        joint_cells.append({"noise_strength": noise, "passes": joint_pass, **joint})

    signed_survival = all(value >= 3 for value in signed_counts.values())
    angular_survival = all(value >= 3 for value in angular_counts.values())
    radial_survival = all(cell["passes"] for cell in radial_cells)
    joint_survival = all(cell["passes"] for cell in joint_cells)
    controls_pass = all(bool(value) for value in checks.values())
    resources_pass = bool(resource_envelope.get("passed", False))

    if not controls_pass or not resources_pass:
        verdict = "HOLD"
    elif angular_survival and joint_survival and radial_survival:
        verdict = "ISOTROPIC_SURVIVAL_WITH_RESOURCE_TRADEOFF"
    elif angular_survival and joint_survival and not radial_survival:
        verdict = "ANISOTROPIC_ANGULAR_GAIN_NO_RADIAL_GAIN"
    elif signed_survival and not angular_survival and not radial_survival and not joint_survival:
        verdict = "SIGN_ONLY"
    elif not signed_survival and not angular_survival and not radial_survival and not joint_survival:
        verdict = "NO_SURVIVAL_FOR_THIS_MAP"
    else:
        verdict = "HOLD"
    return {
        "verdict": verdict,
        "signed_survival": signed_survival,
        "projective_angular_survival": angular_survival,
        "radial_survival": radial_survival,
        "joint_depth_projective_survival": joint_survival,
        "controls_pass": controls_pass,
        "resource_envelope_pass": resources_pass,
        "grid_validation": grid_validation,
        "signed_passing_depth_counts_by_noise": signed_counts,
        "projective_passing_depth_counts_by_noise": angular_counts,
        "radial_cells": radial_cells,
        "joint_cells": joint_cells,
        "fixed_depth_comparison_cells": comparison_cells,
        "global_winner": None,
        "reason_no_global_winner": (
            "R6i and R6 trade one active qubit/Bell preparation and compiler "
            "proxy gates against postselection/coarse-graining; there is no "
            "Pareto dominance across the full vector ledger."
        ),
        "decision_semantics": {
            "comparison": "R6i minus R6 differential gain",
            "legacy_survival_fields": (
                "Every *_survival Boolean is a differential threshold, not a "
                "statement that either map has or lacks absolute information."
            ),
            "no_survival_legacy_label": (
                "NO_SURVIVAL_FOR_THIS_MAP, if emitted, means no differential "
                "gain on any endpoint and does not mean zero absolute retrieval."
            ),
            "absolute_information_inference_permitted": False,
        },
    }


def _r6_padding_control() -> dict:
    rho = 2.0
    matrices = tuple(_source_matrix(point) for point in source_grid(rho))
    native = [attempted_use_state(matrix.real)[0].astype(complex) for matrix in matrices]
    embedded = [encode_r6(matrix) for matrix in matrices]
    native_chi = float(holevo_chi(native))
    embedded_chi = float(holevo_chi(embedded))
    native_receiver = build_pgm_receiver(native)
    embedded_receiver = build_pgm_receiver(embedded)
    native_metrics = evaluate_receiver(
        native_receiver, native, native, noise_strength=0.0
    )
    embedded_metrics = evaluate_receiver(
        embedded_receiver, embedded, embedded, noise_strength=0.0
    )
    native_spectra = [np.linalg.eigvalsh(state) for state in native]
    embedded_spectra = [np.linalg.eigvalsh(state) for state in embedded]
    maximum_spectrum_defect = max(
        float(np.max(np.abs(np.sort(np.pad(first, (0, 11))) - np.sort(second))))
        for first, second in zip(native_spectra, embedded_spectra)
    )
    return {
        "maximum_native_trace_defect": max(
            abs(complex(np.trace(state)) - 1.0) for state in native
        ),
        "maximum_embedded_trace_defect": max(
            abs(complex(np.trace(state)) - 1.0) for state in embedded
        ),
        "native_chi": native_chi,
        "embedded_chi": embedded_chi,
        "chi_defect": abs(native_chi - embedded_chi),
        "maximum_spectrum_defect": maximum_spectrum_defect,
        "native_clean_pgm": native_metrics,
        "embedded_clean_pgm": embedded_metrics,
        "clean_pgm_correct_probability_defect": abs(
            native_metrics["correct_probability"]
            - embedded_metrics["correct_probability"]
        ),
        "clean_pgm_mutual_information_defect": abs(
            native_metrics["mutual_information_bits"]
            - embedded_metrics["mutual_information_bits"]
        ),
        "clean_pgm_abstention_defect": abs(
            native_metrics["abstention_probability"]
            - embedded_metrics["abstention_probability"]
        ),
        "clean_pgm_completeness_max": max(
            native_receiver.diagnostics["completeness_residual"],
            embedded_receiver.diagnostics["completeness_residual"],
        ),
        "passed": bool(
            max(abs(complex(np.trace(state)) - 1.0) for state in native) <= TOL
            and max(abs(complex(np.trace(state)) - 1.0) for state in embedded) <= TOL
            and abs(native_chi - embedded_chi) <= TOL
            and maximum_spectrum_defect <= TOL
            and abs(
                native_metrics["correct_probability"]
                - embedded_metrics["correct_probability"]
            ) <= TOL
            and abs(
                native_metrics["mutual_information_bits"]
                - embedded_metrics["mutual_information_bits"]
            ) <= TOL
            and abs(
                native_metrics["abstention_probability"]
                - embedded_metrics["abstention_probability"]
            ) <= TOL
            and max(
                native_receiver.diagnostics["completeness_residual"],
                embedded_receiver.diagnostics["completeness_residual"],
            ) <= TOL
        ),
    }


def _truncation_retrieval_rows() -> list[dict]:
    rows = []
    for rho in DEPTHS:
        templates = []
        queries = []
        for k in range(CODEWORDS_PER_DEPTH // 2):
            _, phi, psi = source_grid(rho)[k]
            templates.append(truncated_two_mode_state(rho, psi - phi))
            perturbed = []
            for delta_rho, delta_phi, delta_psi in PERTURBATIONS:
                perturbed.append(truncated_two_mode_state(
                    rho + delta_rho,
                    (psi + delta_psi) - (phi + delta_phi),
                ))
            queries.append(_mean(perturbed))
        receiver = build_pgm_receiver(templates)
        template_digest = _canonical_digest([
            _array_digest(state) for state in templates
        ])
        query_digest = _canonical_digest([
            _array_digest(state) for state in queries
        ])
        tail = math.tanh(rho) ** 8
        flagged_distance = flagged_truncation_trace_distance(tail)
        worst_query_tail = math.tanh(rho + 0.01) ** 8
        worst_query_distance = flagged_truncation_trace_distance(worst_query_tail)
        for noise in NOISE_STRENGTHS:
            metrics = evaluate_receiver(
                receiver, templates, queries, noise_strength=noise
            )
            rows.append({
                "map": "R6T",
                "competitor": False,
                "task": "projective_coset_truncation_control",
                "rho": rho,
                "classes": len(templates),
                "noise_strength": noise,
                "template_digest": template_digest,
                "query_digest": query_digest,
                "tail_probability": tail,
                "normalized_projection_trace_distance": math.sqrt(tail),
                "flagged_state_trace_distance": flagged_distance,
                "worst_perturbed_query_tail_probability": worst_query_tail,
                "worst_perturbed_query_flagged_trace_distance": worst_query_distance,
                "inside_primary_error_budget": worst_query_distance <= 0.05,
                **metrics,
            })
    return rows


def run_protocol(event_path: str | Path | None = None) -> dict:
    """Execute the deterministic in-memory protocol and return a JSON-safe report."""

    reservoir = FourShardAssociativeReservoir(event_path)
    tasks_by_map = {}
    source_diagnostics = {}
    for map_name in ("R6", "R6i"):
        tasks, diagnostics = build_map_tasks(map_name, reservoir)
        tasks_by_map[map_name] = tasks
        source_diagnostics[map_name] = diagnostics

    rows = []
    for map_name in ("R6", "R6i"):
        rows.extend(_evaluate_task_rows(map_name, tasks_by_map[map_name]))

    compiler = compiler_cost_proxy()
    resources = _resource_ledger(compiler)
    truncation = truncation_cost_report()
    truncation["retrieval_rows"] = _truncation_retrieval_rows()
    primary_grid_validation = validate_protocol_grid(rows)
    truncation_grid_validation = _validate_truncation_grid(
        truncation["retrieval_rows"]
    )
    padding = _r6_padding_control()

    # Preflight every frozen R6i source block, independent of codeword validity.
    dilation_residuals = []
    for rho in DEPTHS:
        for point in source_grid(rho):
            contraction = normalised_contraction(_source_matrix(point))
            dilation_residuals.append(dilation_diagnostics(contraction))
    maximum_dilation_residual = max(
        max(row["left_unitarity_residual"], row["right_unitarity_residual"],
            row["intertwining_residual"])
        for row in dilation_residuals
    )

    maximum_receiver_residual = max(
        max(
            row["receiver"]["completeness_residual"],
            row["receiver"]["support_projector_residual"],
            row["maximum_raw_row_sum_defect"],
            row["maximum_raw_imaginary_probability"],
            max(0.0, -row["minimum_raw_probability"]),
        )
        for row in rows
    )
    radial_rows = {
        str(noise): {
            map_name: next(
                row for row in rows
                if row["map"] == map_name
                and row["task"] == "radial"
                and row["noise_strength"] == noise
            )
            for map_name in ("R6", "R6i")
        }
        for noise in NOISE_STRENGTHS
    }
    radial_templates = {
        map_name: next(
            task.templates for task in tasks_by_map[map_name]
            if task.name == "radial"
        )
        for map_name in ("R6", "R6i")
    }
    radial_adjacent_distances = {
        map_name: [
            trace_distance(states[index], states[index + 1])
            for index in range(len(states) - 1)
        ]
        for map_name, states in radial_templates.items()
    }

    checks = {
        "source_matrices_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_matrix_digest"]
            == source_diagnostics["R6i"]["source_matrix_digest"]
        ),
        "source_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["source_coordinate_digest"]
            == source_diagnostics["R6i"]["source_coordinate_digest"]
        ),
        "perturbed_coordinates_byte_identical_between_maps": (
            source_diagnostics["R6"]["perturbed_coordinate_digest"]
            == source_diagnostics["R6i"]["perturbed_coordinate_digest"]
        ),
        "central_sign_pairing": max(
            source_diagnostics["R6"]["maximum_central_pair_residual"],
            source_diagnostics["R6i"]["maximum_central_pair_residual"],
        ) <= TOL,
        "r6_passive_embedding": padding["passed"],
        "r6i_dilation_preflight": maximum_dilation_residual <= TOL,
        "r6i_identity_composition_known_answer": abs(
            resources["R6i_identity_composition_defect"] - 2.0 * math.sqrt(2.0)
        ) <= TOL,
        "receiver_and_probability_controls": maximum_receiver_residual <= TOL,
        "exact_finite_primary_grid": primary_grid_validation["valid"],
        "exact_finite_truncation_grid": truncation_grid_validation["valid"],
        "reservoir_event_count": reservoir.event_count == 2 * len(DEPTHS) * CODEWORDS_PER_DEPTH,
        "reservoir_all_shards_used": all(value > 0 for value in reservoir.shard_counts.values()),
        "truncation_density_and_tail": all(
            density_state_diagnostics(
                truncated_two_mode_state(row["rho"], 0.37)
            )["valid"]
            and abs(
                row["tail_probability"] - math.tanh(row["rho"]) ** 8
            ) <= TOL
            and abs(
                row["flagged_state_trace_distance"]
                - flagged_truncation_trace_distance(row["tail_probability"])
            ) <= TOL
            and abs(
                row["worst_perturbed_query_flagged_trace_distance"]
                - flagged_truncation_trace_distance(
                    row["worst_perturbed_query_tail_probability"]
                )
            ) <= TOL
            for row in truncation["rows"]
        ),
    }
    decision = classify_protocol(
        rows,
        checks,
        resources["resource_envelope"],
    )
    input_hashes = [
        _canonical_digest({
            "map": row["map"],
            "task": row["task"],
            "rho": row["rho"],
            "classes": row["classes"],
            "noise_strength": row["noise_strength"],
            "source_matrix_digest": source_diagnostics[row["map"]]["source_matrix_digest"],
            "source_coordinate_digest": source_diagnostics[row["map"]]["source_coordinate_digest"],
            "perturbed_coordinate_digest": source_diagnostics[row["map"]]["perturbed_coordinate_digest"],
            "template_digest": row["template_digest"],
            "query_digest": row["query_digest"],
            "query_perturbations": PERTURBATIONS,
            "receiver": "clean_complete_pgm_v1",
        })
        for row in rows
    ]
    truncation_input_hashes = [
        _canonical_digest({
            "map": row["map"],
            "task": row["task"],
            "rho": row["rho"],
            "classes": row["classes"],
            "noise_strength": row["noise_strength"],
            "template_digest": row["template_digest"],
            "query_digest": row["query_digest"],
            "cutoff_per_mode": 4,
            "tail_probability": row["tail_probability"],
            "receiver": "clean_complete_pgm_v1",
        })
        for row in truncation["retrieval_rows"]
    ]
    input_hashes.extend(truncation_input_hashes)
    return {
        "schema": "hypercomplexbrain.equal-resource-reservoir.v1",
        "round": "QSigma-R6k",
        "experiment_kind": "one-shot associative retrieval; not temporal QRC",
        "ambient_dimension": AMBIENT_DIM,
        "depths": list(DEPTHS),
        "codewords_per_depth": CODEWORDS_PER_DEPTH,
        "noise_strengths": list(NOISE_STRENGTHS),
        "source_diagnostics": source_diagnostics,
        "primary_grid_validation": primary_grid_validation,
        "truncation_grid_validation": truncation_grid_validation,
        "primary_cell_count": len(rows),
        "truncation_control_cell_count": len(truncation["retrieval_rows"]),
        "retrieval_rows": rows,
        "radial_absolute_summary_by_noise": radial_rows,
        "radial_adjacent_trace_distances": radial_adjacent_distances,
        "resource_ledger": resources,
        "truncation_stress_control": truncation,
        "r6_padding_control": padding,
        "reservoir": {
            "kind": "volatile deterministic four-shard associative store",
            "shard_counts": reservoir.shard_counts,
            "event_count": reservoir.event_count,
            "event_digest": reservoir.event_digest,
            "split_signature_used_for_retrieval": False,
        },
        "maximum_dilation_residual": maximum_dilation_residual,
        "maximum_receiver_or_probability_residual": maximum_receiver_residual,
        "checks": checks,
        "decision": decision,
        "input_hashes": input_hashes,
        "typed_remainders": [
            {
                "kind": "scope_remainder",
                "statement": "R6i is a point encoding with nonzero composition defect, not a finite-dimensional unitary representation."
            },
            {
                "kind": "capacity_remainder",
                "statement": "This is finite-grid associative retrieval, not a temporal memory-capacity or asymptotic coding theorem."
            },
            {
                "kind": "resource_remainder",
                "statement": "The clean PGM receiver is mathematically specified but its Naimark/circuit/tomography cost is not synthesized."
            },
            {
                "kind": "noise_remainder",
                "statement": "Global depolarization is a basis-invariant stress channel, not a device noise model."
            },
            {
                "kind": "truncation_remainder",
                "statement": "R6T covers only the SU(1,1)/U(1) lowest-weight orbit and is a non-competing truncation stress control."
            },
        ],
    }
