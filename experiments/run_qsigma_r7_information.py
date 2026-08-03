#!/usr/bin/env python3
"""Append-once execution of the corrected QSigma-R7 information round."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.evidence import (  # noqa: E402
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
    verify,
)
from aionq.hyperbolic_qubit import q22, swirl_point, to_sl2  # noqa: E402
from aionq.qsigma_r7_information import (  # noqa: E402
    absolute_volume_density,
    bell_codeword,
    candidate_grid,
    candidate_order,
    deduplicate_candidates,
    distance_matrix,
    exact_packing_size,
    finite_difference_metric,
    greedy_codebook,
    information_metrics,
    null_separated_witness,
    projective_slab_volume,
    radial_rescaled_exponents,
    slab_volume,
    source_metric,
    trace_distance,
)

PREREG = ROOT / "manifests" / "qsigma_r7_operational_rate_preregistration.json"
PREREG_SHA = "839a2bf5208c73163c888ed6934db6f1de4b3bc7e42ffc615151ebe1f498f2ec"
CLARIFICATION = ROOT / "manifests" / "qsigma_r7_instrument_clarification.json"
CLARIFICATION_SHA = "d4e1f737131e35e20861f81adf32f2c53b63dd7a9556a821ea08cad4cbaf62bc"
R6 = ROOT / "artifacts" / "r6_unitary_price" / "unitary_price.json"
SOURCE = ROOT / "src" / "aionq" / "qsigma_r7_information.py"
TEST = ROOT / "tests" / "test_qsigma_r7_information.py"
RUNNER = Path(__file__).resolve()
OUT_DIR = ROOT / "artifacts" / "r7_source_information"
OUT = OUT_DIR / "source_information.json"
ENVELOPE = OUT_DIR / "source_information.envelope.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def density_digest(density: np.ndarray) -> str:
    payload = np.asarray(density, dtype="<c16").tobytes(order="C")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def metrics_dict(metrics) -> dict:
    return {
        key: float(value) if isinstance(value, np.floating) else value
        for key, value in asdict(metrics).items()
    }


def frozen_manifest() -> dict:
    observed = {PREREG: sha256(PREREG), CLARIFICATION: sha256(CLARIFICATION)}
    expected = {PREREG: PREREG_SHA, CLARIFICATION: CLARIFICATION_SHA}
    failures = [
        f"{path.name}: {observed[path]} != {expected[path]}"
        for path in expected
        if observed[path] != expected[path]
    ]
    if failures:
        raise RuntimeError("frozen manifest changed: " + "; ".join(failures))
    return json.loads(PREREG.read_text(encoding="utf-8"))


def controls(manifest: dict) -> tuple[dict, list[str]]:
    failures: list[str] = []
    algebra_tolerance = float(manifest["frozen_grid"]["algebra_tolerance"])
    density_tolerance = float(manifest["frozen_grid"]["density_tolerance"])
    information_tolerance = float(
        manifest["frozen_grid"]["information_tolerance_bits"]
    )

    metric_rows = []
    for rho in (0.5, 1.0, 2.0):
        analytic = source_metric(rho)
        measured = finite_difference_metric(rho, 0.37, 1.11)
        scale = max(1.0, float(np.max(np.abs(analytic))))
        metric_error = float(np.max(np.abs(analytic - measured)) / scale)
        density_error = abs(
            absolute_volume_density(rho)
            - math.sqrt(abs(float(np.linalg.det(analytic))))
        ) / max(1.0, absolute_volume_density(rho))
        metric_rows.append(
            {
                "rho": rho,
                "metric_relative_error": metric_error,
                "density_relative_error": density_error,
            }
        )
    if max(row["metric_relative_error"] for row in metric_rows) >= 1e-10:
        failures.append("C1 finite-difference metric")
    if max(row["density_relative_error"] for row in metric_rows) >= algebra_tolerance:
        failures.append("C1 volume density")

    witness = null_separated_witness()
    null_pass = (
        witness["distinct"]
        and abs(float(witness["q_left"]) - 1.0) < algebra_tolerance
        and abs(float(witness["q_right"]) - 1.0) < algebra_tolerance
        and abs(float(witness["q_delta"])) < algebra_tolerance
    )
    if not null_pass:
        failures.append("C2 null-separated split-form witness")

    r6 = json.loads(R6.read_text(encoding="utf-8"))
    r6_rows = []
    for row in r6["P3_post_selection_cost"]["average_case"]:
        word = bell_codeword(
            to_sl2(swirl_point(float(row["rho"]), 0.37, 1.11))
        )
        r6_rows.append(
            {
                "rho": float(row["rho"]),
                "r6": float(row["measured"]),
                "r7": word.success_probability,
                "error": abs(word.success_probability - float(row["measured"])),
            }
        )
    r6_pass = (
        r6["P3_post_selection_cost"]["verdict"] == "SURVIVES"
        and max(row["error"] for row in r6_rows) < algebra_tolerance
    )
    if not r6_pass:
        failures.append("C3 R6 block-encoding binding")

    sample = candidate_grid([0.0, 0.5, 1.0, 2.0], 4, 4)
    defects = {
        "hermiticity": 0.0,
        "negative_eigenvalue": 0.0,
        "trace": 0.0,
        "global_phase": 0.0,
        "q22": 0.0,
    }
    for candidate in sample:
        density = candidate.codeword.density
        defects["hermiticity"] = max(
            defects["hermiticity"],
            float(np.max(np.abs(density - density.conj().T))),
        )
        defects["negative_eigenvalue"] = max(
            defects["negative_eigenvalue"],
            max(0.0, -float(np.min(np.linalg.eigvalsh(density)))),
        )
        defects["trace"] = max(
            defects["trace"], abs(float(np.trace(density).real) - 1.0)
        )
        phi = 2.0 * math.pi * candidate.phi_index / 4
        psi = 2.0 * math.pi * candidate.psi_index / 4
        point = swirl_point(candidate.rho, phi, psi)
        matrix = to_sl2(point)
        defects["q22"] = max(defects["q22"], abs(q22(point) - 1.0))
        defects["global_phase"] = max(
            defects["global_phase"],
            trace_distance(density, bell_codeword(-matrix).density),
        )
    if max(defects.values()) >= density_tolerance:
        failures.append("C4/C5 density or projective quotient")

    retained, _ = deduplicate_candidates(sample)
    distances = distance_matrix(retained)
    symmetry = float(np.max(np.abs(distances - distances.T)))
    diagonal = float(np.max(np.abs(np.diag(distances))))
    triangle = 0.0
    limit = min(12, len(retained))
    for left in range(limit):
        for middle in range(limit):
            for right in range(limit):
                triangle = max(
                    triangle,
                    float(
                        distances[left, right]
                        - distances[left, middle]
                        - distances[middle, right]
                    ),
                )
    if max(symmetry, diagonal, triangle) >= density_tolerance:
        failures.append("C4 trace-distance laws")

    policies = list(manifest["frozen_grid"]["candidate_orders"])
    exact_rows = {}
    for family in ("hyperbolic", "compact"):
        small = candidate_grid(
            [0.0, 1.0],
            8,
            8,
            family=family,
            phi_indices=[0, 1],
            psi_indices=[0, 1],
        )
        small, _ = deduplicate_candidates(small)
        small_distances = distance_matrix(small)
        family_rows = {}
        for epsilon in manifest["frozen_grid"]["epsilon"]:
            exact = exact_packing_size(small_distances, float(epsilon))
            greedy = {
                policy: len(
                    greedy_codebook(
                        small_distances,
                        float(epsilon),
                        candidate_order(small, policy),
                    )
                )
                for policy in policies
            }
            if max(greedy.values()) > exact:
                failures.append(f"C6 exact packing {family} {epsilon}")
            family_rows[str(epsilon)] = {
                "operational_candidates": len(small),
                "exact": exact,
                "greedy": greedy,
            }
        exact_rows[family] = family_rows

    probe = candidate_grid([0.0, 0.5, 1.0], 3, 3)
    probe, _ = deduplicate_candidates(probe)
    probe_distances = distance_matrix(probe)
    selected = greedy_codebook(
        probe_distances,
        0.2,
        candidate_order(probe, "sha256_order_seed_20260728"),
    )
    probe_metrics = information_metrics(
        [probe[index].codeword for index in selected]
    )
    info_pass = (
        -information_tolerance <= probe_metrics.pgm_mutual_information
        <= probe_metrics.holevo_information + information_tolerance
        and probe_metrics.holevo_information
        <= probe_metrics.oracle_erasure_information + information_tolerance
        and probe_metrics.oracle_erasure_information
        <= probe_metrics.log2_codewords + information_tolerance
    )
    if not info_pass:
        failures.append("C8 information sandwich")

    compact = candidate_grid(manifest["frozen_grid"]["rho"], 8, 8, family="compact")
    hyperbolic = candidate_grid(
        manifest["frozen_grid"]["rho"], 8, 8, family="hyperbolic"
    )
    compact_pass = (
        len(compact) == len(hyperbolic) == 448
        and all(item.codeword.density.shape == (5, 5) for item in compact + hyperbolic)
        and max(abs(item.codeword.success_probability - 1.0) for item in compact)
        < algebra_tolerance
    )
    if not compact_pass:
        failures.append("C9 compact parity")

    rescaling = [
        radial_rescaled_exponents(scale) for scale in (0.5, 1.0, 2.0, 7.0)
    ]
    if any(
        abs(row["source_to_cost_ratio"] - 0.5) >= algebra_tolerance
        for row in rescaling
    ):
        failures.append("C10 radial reparameterisation")

    return {
        "C1_source_geometry": {
            "metric_rows": metric_rows,
            "slab_volume_R6": slab_volume(6.0),
            "projective_slab_volume_R6": projective_slab_volume(6.0),
            "source_exponent": 2.0,
        },
        "C2_indefinite_metric": {
            "witness": {
                key: value.tolist() if isinstance(value, np.ndarray) else value
                for key, value in witness.items()
            },
            "passed": null_pass,
        },
        "C3_r6_binding": {"rows": r6_rows, "passed": r6_pass},
        "C4_C5_density_distance_projective": {
            "defects": defects,
            "symmetry_defect": symmetry,
            "diagonal_defect": diagonal,
            "maximum_tested_triangle_violation": triangle,
        },
        "C6_exact_small_packing": exact_rows,
        "C7_orders": policies,
        "C8_information_probe": {
            "metrics": metrics_dict(probe_metrics),
            "passed": info_pass,
        },
        "C9_compact_parity": {
            "raw_candidates_per_family": len(compact),
            "density_dimension": 5,
            "passed": compact_pass,
        },
        "C10_radial_reparameterisation": rescaling,
    }, failures


def run_family(manifest: dict, family: str) -> dict:
    rhos = [float(value) for value in manifest["frozen_grid"]["rho"]]
    epsilons = [float(value) for value in manifest["frozen_grid"]["epsilon"]]
    policies = list(manifest["frozen_grid"]["candidate_orders"])
    raw = candidate_grid(rhos, 8, 8, family=family)
    retained, aliases = deduplicate_candidates(
        raw,
        float(manifest["frozen_grid"]["operational_equality_tolerance"]),
    )
    full_distances = distance_matrix(retained)
    prefixes = []
    inequality_failures = []
    for radius in rhos:
        full_indices = [
            index for index, item in enumerate(retained) if item.rho <= radius
        ]
        candidates = [retained[index] for index in full_indices]
        distances = full_distances[np.ix_(full_indices, full_indices)]
        epsilon_rows = []
        for epsilon in epsilons:
            order_rows = []
            best = None
            for policy_index, policy in enumerate(policies):
                selected = greedy_codebook(
                    distances,
                    epsilon,
                    candidate_order(candidates, policy),
                )
                selection_digest = hashlib.sha256(
                    "\n".join(candidates[index].key for index in selected).encode()
                ).hexdigest()
                order_rows.append(
                    {
                        "policy": policy,
                        "count": len(selected),
                        "selection_digest": f"sha256:{selection_digest}",
                    }
                )
                candidate_best = (len(selected), -policy_index, policy, selected)
                if best is None or candidate_best[:2] > best[:2]:
                    best = candidate_best
            assert best is not None
            count, _, best_policy, selected = best
            info = information_metrics(
                [candidates[index].codeword for index in selected]
            )
            tolerance = float(
                manifest["frozen_grid"]["information_tolerance_bits"]
            )
            inequalities_hold = (
                -tolerance <= info.pgm_mutual_information
                <= info.holevo_information + tolerance
                and info.holevo_information
                <= info.oracle_erasure_information + tolerance
                and info.oracle_erasure_information
                <= info.log2_codewords + tolerance
            )
            if not inequalities_hold:
                inequality_failures.append(
                    {"radius": radius, "epsilon": epsilon}
                )
            epsilon_rows.append(
                {
                    "epsilon": epsilon,
                    "order_results": order_rows,
                    "order_count_spread": max(row["count"] for row in order_rows)
                    - min(row["count"] for row in order_rows),
                    "lower_bound": count,
                    "selected_policy": best_policy,
                    "information": metrics_dict(info),
                    "information_inequalities_hold": inequalities_hold,
                }
            )
        prefixes.append(
            {
                "radius": radius,
                "raw_candidates": sum(item.rho <= radius for item in raw),
                "operational_candidates": len(candidates),
                "epsilon_rows": epsilon_rows,
            }
        )
    hashes = sorted(
        {density_digest(item.codeword.density) for item in retained}
    )
    return {
        "family": family,
        "raw_candidates": len(raw),
        "operational_candidates": len(retained),
        "operational_aliases": len(aliases) - len(retained),
        "candidate_density_hashes": hashes,
        "prefixes": prefixes,
        "information_inequality_failures": inequality_failures,
    }


def epsilon_row(result: dict, radius: float, epsilon: float) -> dict:
    prefix = next(row for row in result["prefixes"] if row["radius"] == radius)
    return next(
        row for row in prefix["epsilon_rows"] if row["epsilon"] == epsilon
    )


def main() -> int:
    if OUT.exists() or ENVELOPE.exists():
        raise FileExistsError("corrected R7 outputs already exist; run is append-once")
    manifest = frozen_manifest()
    control_results, failures = controls(manifest)
    if failures:
        raise RuntimeError("control failure before target: " + "; ".join(failures))

    hyperbolic = run_family(manifest, "hyperbolic")
    compact = run_family(manifest, "compact")
    slopes = []
    h1_pass = True
    for epsilon in manifest["frozen_grid"]["epsilon"]:
        n4 = epsilon_row(hyperbolic, 4.0, float(epsilon))["lower_bound"]
        n6 = epsilon_row(hyperbolic, 6.0, float(epsilon))["lower_bound"]
        slope = (math.log(n6) - math.log(n4)) / 2.0
        passed = slope <= 0.25 + 1e-12
        h1_pass = h1_pass and passed
        slopes.append(
            {
                "epsilon": float(epsilon),
                "N_at_4": n4,
                "N_at_6": n6,
                "natural_log_slope": slope,
                "gate": 0.25,
                "passed": passed,
            }
        )
    info_failures = (
        hyperbolic["information_inequality_failures"]
        + compact["information_inequality_failures"]
    )
    h2_pass = not info_failures
    status = "COMPLETED" if h2_pass else "VOID_INFORMATION_INSTRUMENT"
    verdicts = {
        "P1_source_volume": "SURVIVES",
        "P2_indefinite_metric_rejection": "SURVIVES",
        "P3_density_and_r6_binding": "SURVIVES",
        "H1_operational_high_depth_slope": (
            "SURVIVES" if h1_pass else "FALSIFIED"
        ),
        "H2_information_bounds": "SURVIVES" if h2_pass else "VOID",
        "H3_catalogue_proxy_separated": "SURVIVES",
    }
    source_digests = {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_digest(path)
        for path in (PREREG, CLARIFICATION, R6, SOURCE, TEST, RUNNER)
    }
    remainders = [
        "Greedy epsilon-codebooks are lower bounds, not maximum packings.",
        "The finite grid does not establish asymptotic Shannon capacity.",
        "The PGM is one receiver, not optimized accessible information.",
        "The classical scale is excluded; retaining it requires precision and description-length charges.",
        "No device, physical noise, quantum advantage, memory advantage, or cognition claim.",
        "This is a first-party repository run; commit publication follows explicit verification and scoped staging.",
        "Only the files enumerated by source_digests participate in this result; external and concurrent artifacts are excluded.",
        "No independent witness."
    ]
    payload = {
        "schema": "hypercomplexbrain.qsigma_r7.source_information.v1",
        "round": "QSigma-R7",
        "status": status,
        "preregistration": {
            "path": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
            "sha256": f"sha256:{PREREG_SHA}",
            "clarification_path": str(CLARIFICATION.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "clarification_sha256": f"sha256:{CLARIFICATION_SHA}",
        },
        "source_digests": source_digests,
        "source_geometry": {
            "slab_volume": "2*pi^2*sinh(R)^2",
            "projective_slab_volume": "pi^2*sinh(R)^2",
            "source_exponent": 2.0,
            "operational_distance": "dense trace distance on 5x5 Bell-probe erasure densities",
            "split_form_used_as_distance": False,
            "classical_scale_side_channel": "excluded",
        },
        "controls": control_results,
        "control_failures": [],
        "families": {
            "hyperbolic": hyperbolic,
            "compact_control": compact,
        },
        "H1_high_depth_slopes": slopes,
        "H2_information_inequality_failures": info_failures,
        "verdicts": verdicts,
        "interpretation": {
            "bounded": "Exact source exponent two versus finite fixed-width operational lower bounds and information brackets.",
            "catalogue_proxy": "N*p_min remains an A-tier count surrogate, never bits.",
            "k_greater_than_4": "Not tested or claimed; changing k requires a jointly priced family."
        },
        "typed_remainders": remainders,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    envelope = EvidenceEnvelope(
        claim_id="QSIGMA-R7-SOURCE-INFORMATION",
        evidence_tag="M",
        command="python experiments/run_qsigma_r7_information.py",
        observed_result={
            "status": status,
            "sample_size": len(hyperbolic["candidate_density_hashes"]),
            "H1": verdicts["H1_operational_high_depth_slope"],
            "H2": verdicts["H2_information_bounds"],
            "null": "source exponent two does not survive as the frozen high-depth operational count slope",
            "interval": "deterministic finite grid; no sampling interval",
        },
        commit_sha=current_commit(ROOT),
        working_directory=".",
        platform=platform.system().lower(),
        environment=environment_digest(),
        input_hashes=hyperbolic["candidate_density_hashes"],
        seeds=[],
        raw_artifacts={
            str(OUT.relative_to(ROOT)).replace("\\", "/"): file_digest(OUT)
        },
        uncertainty={
            "packing": "four frozen orders; exact only on small control",
            "receiver": "erasure-aware PGM with Holevo and oracle upper bounds",
            "independence": False,
        },
        producer="codex-gpt5.6",
        verifier="",
        signature_status="unsigned",
        typed_remainders=remainders,
        verification_mode="not_requested",
    )
    save_envelope(envelope, ENVELOPE)
    check = verify(envelope, repo_root=ROOT, check_commit=False)
    if not check.ok:
        raise RuntimeError("envelope verification failed: " + "; ".join(check.failures))
    print(status)
    for row in slopes:
        print(
            f"epsilon={row['epsilon']:.2f} N4={row['N_at_4']} "
            f"N6={row['N_at_6']} slope={row['natural_log_slope']:.6f}"
        )
    print(f"information_failures={len(info_failures)} independent={check.independent}")
    print(OUT)
    return 0 if status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
