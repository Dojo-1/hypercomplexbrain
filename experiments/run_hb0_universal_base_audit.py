"""Produce the deterministic structural artifact for the HB0 Poincare axiom.

This audit verifies the implemented surrogate. It does not measure cognitive
benefit, quantum advantage, or empirical superiority over the Euclidean control.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.atlas import (  # noqa: E402
    FREE_THEORIES,
    compare_embeddings_on_real_hierarchy,
    place_free_theories_on_universal_base,
)
from aionq.hb0 import build_hb0, validate_hb0_manifest  # noqa: E402
from aionq.hyperbolic import (  # noqa: E402
    UNIVERSAL_EUCLIDEAN_CONTROL,
    UNIVERSAL_POINCARE_BASE,
)


CLAIM_ID = "AXIOM-HB0-UNIVERSAL_POINCARE_BASE"
SCHEMA = "aionq.hb0-universal-base-audit.v1"


def _json_native(value):
    """Recursively remove NumPy scalar wrappers from the evidence payload."""

    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_native(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {key: _json_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    return value


def produce_audit(seed: int = 5) -> dict:
    """Return one deterministic audit of the declared architectural surrogate."""

    manifest_path = ROOT / "manifests" / "hb0_polycosmic_architecture.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_review = validate_hb0_manifest(manifest)
    kernel = build_hb0(seed=seed)
    coverage = kernel.review_universal_base()
    k13 = compare_embeddings_on_real_hierarchy()
    atlas_points = place_free_theories_on_universal_base()
    origin = UNIVERSAL_POINCARE_BASE.to_hyperboloid(
        np.zeros(UNIVERSAL_POINCARE_BASE.dimension)
    )
    atlas_tangents = np.stack([
        UNIVERSAL_POINCARE_BASE.log(
            origin,
            UNIVERSAL_POINCARE_BASE.to_hyperboloid(atlas_points[theory.name]),
        )
        for theory in FREE_THEORIES
    ])
    atlas_tangent_rank = int(np.linalg.matrix_rank(atlas_tangents))
    pair_distances = [
        UNIVERSAL_POINCARE_BASE.distance(
            atlas_points[left.name],
            atlas_points[right.name],
        )
        for index, left in enumerate(FREE_THEORIES)
        for right in FREE_THEORIES[index + 1 :]
    ]

    checks = {
        "manifest_strict": manifest_review.ok,
        "kernel_coverage": coverage.passed,
        "canonical_base_spec": (
            kernel.base.to_spec() == UNIVERSAL_POINCARE_BASE.to_spec()
        ),
        "matched_euclidean_control": (
            kernel.euclidean_base_control.to_spec()
            == UNIVERSAL_EUCLIDEAN_CONTROL.to_spec()
        ),
        "atlas_tangent_rank_full": (
            atlas_tangent_rank == UNIVERSAL_POINCARE_BASE.dimension
        ),
        "atlas_placement_injective": (
            min(pair_distances) > UNIVERSAL_POINCARE_BASE.tolerance
        ),
        "k13_measurement_preserved": (
            k13["delta_over_diameter"] == 0.5
            and abs(k13["hyperbolic_distortion"] - 5.289745803610123) < 1e-12
            and abs(k13["euclidean_distortion"] - 6.635501481435628) < 1e-12
        ),
        "heterogeneous_local_fibers": (
            len(coverage.local_fiber_geometries) >= 2
        ),
    }
    return _json_native({
        "schema": SCHEMA,
        "claim_id": CLAIM_ID,
        "evidence_tag": "A",
        "seed": seed,
        "all_structural_checks_passed": all(checks.values()),
        "checks": checks,
        "base": UNIVERSAL_POINCARE_BASE.to_spec(),
        "euclidean_control": UNIVERSAL_EUCLIDEAN_CONTROL.to_spec(),
        "coverage": asdict(coverage),
        "atlas": {
            "free_theory_count": len(FREE_THEORIES),
            "tangent_rank": atlas_tangent_rank,
            "minimum_pair_distance": min(pair_distances),
        },
        "historical_k13": k13,
        "manifest": {
            "checks_run": manifest_review.checks_run,
            "warnings": list(manifest_review.warnings),
        },
        "scope_boundary": {
            "architectural_contract": True,
            "negative_curvature_inferred_from_k13": False,
            "cognitive_benefit_measured": False,
            "euclidean_superiority_claim": False,
            "independent_witness": False,
        },
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = produce_audit(args.seed)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["all_structural_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
