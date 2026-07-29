"""Run the preregistered algebra-valued S8 decoder experiment.

Preregistration:
    manifests/s8_algebra_decoder_preregistration.json

This experiment keeps the full 28 coordinates of each ``so(8)`` observation.
It tests local identifiability for the explicitly declared linear model

    y = S a + C b + epsilon,

where ``S`` holds seven normalized Fano channel generators and ``C`` holds their
twenty-one normalized pairwise commutators.  It does not test a finite-angle
receiver, a physical channel, split signature, or quantum advantage.

Run with:
    python experiments/run_fano_decoder.py
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.fano_decoder import (
    algebra_basis,
    algebra_report,
    decode_coefficients,
    encode_coefficients,
    fano_lines,
    find_rank_deficient_control,
    noise_benchmark,
    random_control_summary,
    so8_matrix,
)


OUT = ROOT / "artifacts" / "s8_decoder" / "fano_decoder.json"
PREREG = "manifests/s8_algebra_decoder_preregistration.json"


def _noiseless_recovery(basis, *, samples: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=(samples, basis.n_signal))
    crosstalk = rng.normal(size=(samples, basis.n_crosstalk))
    observations = encode_coefficients(basis, signal, crosstalk)
    signal_hat, crosstalk_hat = decode_coefficients(basis, observations)
    error = np.column_stack(
        (signal_hat - signal, crosstalk_hat - crosstalk)
    )
    reconstructed = encode_coefficients(basis, signal_hat, crosstalk_hat)
    return {
        "samples": samples,
        "seed": seed,
        "maximum_absolute_coefficient_error": float(np.max(np.abs(error))),
        "coefficient_rmse": float(np.sqrt(np.mean(error**2))),
        "maximum_observation_reconstruction_error": float(
            np.max(np.linalg.norm(reconstructed - observations, axis=1))
        ),
    }


def _scalar_collapse_attack(basis) -> dict:
    left_index = 0
    right_index = 1
    left = (
        basis.crosstalk[:, left_index]
        * basis.crosstalk_raw_norms[left_index]
    )
    right = (
        basis.crosstalk[:, right_index]
        * basis.crosstalk_raw_norms[right_index]
    )
    left_matrix = so8_matrix(left)
    right_matrix = so8_matrix(right)
    return {
        "comparison": "raw unnormalized pairwise commutators",
        "left_channel_pair": list(basis.pairs[left_index]),
        "right_channel_pair": list(basis.pairs[right_index]),
        "left_triple_supports": [
            list(basis.triples[index]) for index in basis.pairs[left_index]
        ],
        "right_triple_supports": [
            list(basis.triples[index]) for index in basis.pairs[right_index]
        ],
        "left_norm": float(np.linalg.norm(left)),
        "right_norm": float(np.linalg.norm(right)),
        "equal_scalar_norms": bool(
            np.isclose(np.linalg.norm(left), np.linalg.norm(right), atol=1e-14)
        ),
        "algebra_coordinate_distance": float(np.linalg.norm(left - right)),
        "matrix_frobenius_distance": float(
            np.linalg.norm(left_matrix - right_matrix, ord="fro")
        ),
        "finding": (
            "Two raw Fano commutators reproduce the legacy equal norm while "
            "remaining distinct in all 28 algebra-valued coordinates. This "
            "comparison is not an artefact of unit-column normalization."
        ),
    }


def _basis_order_attack(basis, *, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    signal = rng.normal(size=basis.n_signal)
    crosstalk = rng.normal(size=basis.n_crosstalk)
    original = encode_coefficients(basis, signal, crosstalk)
    signal_permutation = rng.permutation(basis.n_signal)
    crosstalk_permutation = rng.permutation(basis.n_crosstalk)
    permuted_basis = type(basis)(
        triples=tuple(
            basis.triples[index] for index in signal_permutation
        ),
        pairs=tuple(
            basis.pairs[index] for index in crosstalk_permutation
        ),
        signal=basis.signal[:, signal_permutation],
        crosstalk=basis.crosstalk[:, crosstalk_permutation],
        signal_raw_norms=basis.signal_raw_norms[signal_permutation],
        crosstalk_raw_norms=basis.crosstalk_raw_norms[
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
    coefficient_error = np.concatenate(
        (
            signal_hat - signal[signal_permutation],
            crosstalk_hat - crosstalk[crosstalk_permutation],
        )
    )
    return {
        "seed": seed,
        "signal_permutation": signal_permutation.tolist(),
        "crosstalk_permutation": crosstalk_permutation.tolist(),
        "observation_distance": float(np.linalg.norm(permuted - original)),
        "maximum_decoded_coefficient_error": float(
            np.max(np.abs(coefficient_error))
        ),
        "finding": (
            "Permuting the declared basis and the corresponding coefficients "
            "changes coordinate order but not the algebra-valued observation."
        ),
    }


def _post_hoc_conditioning(report, controls) -> dict:
    fano_condition = float(report["joint_condition_number"])
    random_conditions = np.asarray(
        controls["finite_joint_condition_numbers"], dtype=float
    )
    return {
        "status": "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED",
        "fano_joint_condition_number": fano_condition,
        "full_rank_random_support_count": int(random_conditions.size),
        "random_support_condition_minimum": float(
            np.min(random_conditions)
        ),
        "random_support_condition_median": float(
            np.median(random_conditions)
        ),
        "random_support_condition_maximum": float(
            np.max(random_conditions)
        ),
        "random_support_count_at_or_below_fano": int(
            np.count_nonzero(
                random_conditions <= fano_condition * (1.0 + 1e-12)
            )
        ),
        "interpretation": (
            "Conditioning, not full-rank frequency, is the design-specific "
            "difference visible in this sampled control. This comparison was "
            "noticed after the preregistered run and is descriptive only."
        ),
    }


def _runtime_provenance() -> dict:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "numpy_version": np.__version__,
        "numpy_bit_generator": type(
            np.random.default_rng(0).bit_generator
        ).__name__,
        "seeds": {
            "random_support_control": 20260727,
            "coefficient_and_noise_samples": 20260728,
            "basis_order_attack": 29,
        },
        "note": (
            "Exact seeded control counts are interpreted with the recorded "
            "NumPy version and bit generator."
        ),
    }


def _verdicts(
    report,
    noiseless,
    noise_rows,
    alias,
    scalar_attack,
    basis_order_attack,
) -> dict:
    h1_pass = (
        report["signal_rank"] == 7
        and report["crosstalk_rank"] == 21
        and report["joint_rank"] == 28
        and report["max_abs_cross_gram"] <= 1e-12
    )
    h2_pass = noiseless["maximum_absolute_coefficient_error"] <= 1e-10
    nonzero_noise = [
        row for row in noise_rows if row["analytic_expected_rmse"] > 0.0
    ]
    h3_pass = all(
        abs(row["empirical_over_expected"] - 1.0) <= 0.15
        for row in nonzero_noise
    )
    h4_pass = (
        alias["coefficient_distance"] >= 1.0 - 1e-12
        and alias["observation_distance"] <= 1e-10
    )
    scalar_pass = (
        scalar_attack["equal_scalar_norms"]
        and scalar_attack["algebra_coordinate_distance"] > 1e-10
        and abs(
            scalar_attack["algebra_coordinate_distance"]
            - scalar_attack["matrix_frobenius_distance"]
        )
        <= 1e-12
    )
    basis_order_pass = (
        basis_order_attack["observation_distance"] <= 1e-12
        and basis_order_attack["maximum_decoded_coefficient_error"]
        <= 1e-10
    )
    primary_pass = h1_pass and h2_pass and h3_pass and h4_pass
    controls_pass = scalar_pass and basis_order_pass
    overall_pass = primary_pass and controls_pass
    return {
        "S8-DEC-H1": {
            "pass": h1_pass,
            "status": "CONFIRMED" if h1_pass else "FALSIFIED",
            "gate": "ranks 7/21/28 and max cross Gram <= 1e-12",
        },
        "S8-DEC-H2": {
            "pass": h2_pass,
            "status": "CONFIRMED" if h2_pass else "FALSIFIED",
            "gate": "noiseless max coefficient error <= 1e-10",
        },
        "S8-DEC-H3": {
            "pass": h3_pass,
            "status": "CONFIRMED" if h3_pass else "FALSIFIED",
            "gate": "empirical RMSE within 15% of analytic least-squares RMSE",
        },
        "S8-DEC-H4": {
            "pass": h4_pass,
            "status": "CONFIRMED" if h4_pass else "FALSIFIED",
            "gate": "unit coefficient alias with observation distance <= 1e-10",
        },
        "S8-DEC-C1": {
            "pass": scalar_pass,
            "status": "PASSED" if scalar_pass else "FAILED",
            "gate": (
                "raw equal-norm commutators remain distinct in isometric "
                "algebra coordinates"
            ),
        },
        "S8-DEC-C2": {
            "pass": basis_order_pass,
            "status": "PASSED" if basis_order_pass else "FAILED",
            "gate": (
                "basis permutation preserves observation to 1e-12 and "
                "decoded coefficients to 1e-10"
            ),
        },
        "overall": {
            "primary_hypotheses_pass": bool(primary_pass),
            "executed_controls_pass": bool(controls_pass),
            "pass": bool(overall_pass),
            "status": (
                "PREREGISTERED PRIMARY GATES AND EXECUTED CONTROLS PASSED"
                if overall_pass
                else "PREREGISTERED SLICE FAILED"
            ),
        },
    }


def main() -> int:
    basis = algebra_basis(fano_lines())
    report = algebra_report(basis)
    noiseless = _noiseless_recovery(
        basis, samples=256, seed=20260728
    )
    noise_rows = noise_benchmark(
        basis,
        sigma=(0.0, 0.0001, 0.001, 0.01, 0.1),
        samples=4096,
        seed=20260728,
    )
    controls = random_control_summary(trials=1000, seed=20260727)
    alias = find_rank_deficient_control(controls)
    scalar_attack = _scalar_collapse_attack(basis)
    basis_order_attack = _basis_order_attack(basis, seed=29)
    post_hoc_conditioning = _post_hoc_conditioning(report, controls)
    # The per-trial condition vector is an internal reduction input. Persist
    # only its preregistered counts and descriptive summaries so the artifact
    # stays reviewable without discarding the reported comparison.
    controls.pop("finite_joint_condition_numbers")
    controls["rank_interpretation"] = {
        "status": "SIGNAL_RANK_CONFOUNDED",
        "statement": (
            "In this sample every full-signal-rank control also has full "
            "crosstalk rank, and every crosstalk rank equals choose(signal "
            "rank, 2). The control does not show that Fano uniquely buys "
            "crosstalk rank 21."
        ),
    }
    verdicts = _verdicts(
        report,
        noiseless,
        noise_rows,
        alias,
        scalar_attack,
        basis_order_attack,
    )

    payload = {
        "schema": "hypercomplexbrain.s8_algebra_decoder.v1",
        "preregistration": PREREG,
        "runtime_provenance": _runtime_provenance(),
        "model": {
            "carrier": "so(8), 28 isometric strict-upper-triangle coordinates",
            "observation": "y = S a + C b + epsilon",
            "decoder": "Moore-Penrose joint least squares on B=[S C]",
            "basis_normalization": "unit Euclidean norm in isometric so(8) coordinates",
            "scope": (
                "Local linearized identifiability only. No finite group-product "
                "receiver, physical channel, capacity, split-signature, or "
                "quantum-advantage claim."
            ),
        },
        "fano": {
            "triples": [list(triple) for triple in basis.triples],
            "channel_pairs": [list(pair) for pair in basis.pairs],
            "signal_basis_28_by_7": basis.signal.tolist(),
            "crosstalk_basis_28_by_21": basis.crosstalk.tolist(),
            "signal_raw_frobenius_norms": basis.signal_raw_norms.tolist(),
            "crosstalk_raw_frobenius_norms": basis.crosstalk_raw_norms.tolist(),
            "report": report,
        },
        "noiseless_recovery": noiseless,
        "noise_benchmark": noise_rows,
        "matched_random_control": controls,
        "post_hoc_conditioning": post_hoc_conditioning,
        "rank_deficient_alias": alias,
        "scalar_collapse_attack": scalar_attack,
        "basis_order_attack": basis_order_attack,
        "verdicts": verdicts,
        "typed_remainder": {
            "kind": "model_boundary",
            "statement": (
                "Full rank in this linearized compact so(8) carrier does not "
                "establish global finite-angle decoding, performance under a "
                "physical noise process, or a split-signature SU(1,1) result."
            ),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as artifact:
        artifact.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        artifact.write("\n")

    print("S8 algebra-valued Fano decoder")
    print("=" * 72)
    print(
        "ranks signal/crosstalk/joint: "
        f"{report['signal_rank']}/{report['crosstalk_rank']}/"
        f"{report['joint_rank']}"
    )
    print(f"max |S^T C|: {report['max_abs_cross_gram']:.3e}")
    print(
        "joint condition number: "
        f"{report['joint_condition_number']:.6g}"
    )
    print(
        "noiseless max coefficient error: "
        f"{noiseless['maximum_absolute_coefficient_error']:.3e}"
    )
    print(
        "random-support controls with signal/crosstalk rank 7/21: "
        f"{controls['full_signal_rank_count']}/"
        f"{controls['full_crosstalk_rank_count']}/{controls['trials']}"
    )
    print(
        "rank(C)=choose(rank(S),2) mismatches: "
        f"{controls['observed_rank_relation']['mismatch_count']}"
    )
    print(
        "post-hoc joint conditioning Fano/random minimum: "
        f"{post_hoc_conditioning['fano_joint_condition_number']:.6g}/"
        f"{post_hoc_conditioning['random_support_condition_minimum']:.6g}"
    )
    print(
        "rank-deficient alias observation distance: "
        f"{alias['observation_distance']:.3e}"
    )
    print(verdicts["overall"]["status"])
    print(f"wrote {OUT}")
    return 0 if verdicts["overall"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
