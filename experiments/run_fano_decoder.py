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
    left = basis.crosstalk[:, 0]
    right = basis.crosstalk[:, 1]
    left_matrix = so8_matrix(left)
    right_matrix = so8_matrix(right)
    return {
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
            "The two observations have the same scalar norm and different "
            "algebra-valued coordinates. A norm-only instrument identifies them "
            "even though the decoder carrier does not."
        ),
    }


def _verdicts(report, noiseless, noise_rows, alias) -> dict:
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
        "overall": {
            "pass": bool(h1_pass and h2_pass and h3_pass and h4_pass),
            "status": (
                "PREREGISTERED SLICE PASSED"
                if h1_pass and h2_pass and h3_pass and h4_pass
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
    verdicts = _verdicts(report, noiseless, noise_rows, alias)

    payload = {
        "schema": "hypercomplexbrain.s8_algebra_decoder.v1",
        "preregistration": PREREG,
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
        "rank_deficient_alias": alias,
        "scalar_collapse_attack": scalar_attack,
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
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )

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
        "matched controls with crosstalk rank 21: "
        f"{controls['full_crosstalk_rank_count']}/{controls['trials']}"
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
