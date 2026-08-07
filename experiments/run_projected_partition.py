from __future__ import annotations
import hashlib, json, os, platform, sys
from pathlib import Path
import numpy as np

from aionq.projected_partition import (
    TOL, additive_coset_partition, evaluate_partition, gf4_scaled_subspaces,
    projected_state_direct, projected_state_explicit, projection_weights,
    random_aligned_partition, random_transverse_partition, relabel_partition,
)

BASE_COMMIT = "a090939cb72519d2b0af49fafc4e772d71740f56"
PREREG_COMMIT = "f5a98eb3c05f048f230b643b49c31916e188d1b4"
IMPLEMENTATION_COMMIT = os.environ.get("R1T_IMPLEMENTATION_COMMIT", "unbound-local")
SECRET = 1
PROJECTION_SEEDS = list(range(8))
CONTROL_SEEDS = list(range(8))


def sha256_json(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def row(family, variant, pseed, partition, metrics):
    return {
        "family": family, "variant": variant, "projection_seed": pseed,
        "partition": [list(c) for c in partition],
        **{k: float(v) for k,v in metrics.__dict__.items()},
    }


def summarize(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r["family"], []).append(r)
    out = {}
    for name, rs in sorted(groups.items()):
        vals = np.array([r["sector_forbidden_mass"] for r in rs], float)
        cuts = np.array([r["pair_cut_fraction"] for r in rs], float)
        offs = np.array([r["offdiag_forbidden_real"] for r in rs], float)
        out[name] = {
            "n": len(rs),
            "sector_forbidden_min": float(vals.min()),
            "sector_forbidden_median": float(np.median(vals)),
            "sector_forbidden_max": float(vals.max()),
            "pair_cut_min": float(cuts.min()),
            "pair_cut_median": float(np.median(cuts)),
            "pair_cut_max": float(cuts.max()),
            "offdiag_forbidden_median": float(np.median(offs)),
            "max_closure_defect": float(max(r["closure_defect"] for r in rs)),
            "max_global_forbidden": float(max(r["global_forbidden_mass"] for r in rs)),
        }
    return out


def main():
    subspaces = gf4_scaled_subspaces()
    field_parts = [(h, additive_coset_partition(h)) for h in subspaces]
    aligned_field = [(h,p) for h,p in field_parts if SECRET in h]
    transverse_field = [(h,p) for h,p in field_parts if SECRET not in h]
    assert len(aligned_field) == 1 and len(transverse_field) == 4
    base_field = aligned_field[0][1]

    rows = []
    projection_checks = []
    for pseed in PROJECTION_SEEDS:
        w = projection_weights(pseed)
        s1 = projected_state_explicit(SECRET, w)
        s2 = projected_state_direct(SECRET, w)
        proj_defect = float(np.linalg.norm(s1-s2))
        pair_sym = max(abs(s1[x]-s1[x ^ SECRET]) for x in range(16))
        projection_checks.append({"seed": pseed, "projection_defect": proj_defect, "pair_symmetry_defect": float(pair_sym)})
        if proj_defect > TOL or pair_sym > TOL:
            raise SystemExit(f"projection gate failed at seed {pseed}")

        h,p = aligned_field[0]
        rows.append(row("FIELD-ALIGNED", str(list(h)), pseed, p, evaluate_partition(s1,p,SECRET)))
        for h,p in transverse_field:
            rows.append(row("FIELD-TRANSVERSE", str(list(h)), pseed, p, evaluate_partition(s1,p,SECRET)))
        for cseed in CONTROL_SEEDS:
            p = random_aligned_partition(SECRET, 1000+pseed*32+cseed)
            rows.append(row("ALIGNED-RANDOM", f"seed-{cseed}", pseed, p, evaluate_partition(s1,p,SECRET)))
            p = random_transverse_partition(SECRET, 2000+pseed*32+cseed)
            rows.append(row("TRANSVERSE-RANDOM", f"seed-{cseed}", pseed, p, evaluate_partition(s1,p,SECRET)))
            p = relabel_partition(base_field, 3000+pseed*32+cseed)
            rows.append(row("RELABELLED-FIELD", f"seed-{cseed}", pseed, p, evaluate_partition(s1,p,SECRET)))

    # Frozen gates.
    failures = []
    for r in rows:
        if r["global_forbidden_mass"] > 1e-12:
            failures.append(["global_forbidden", r])
        if r["closure_defect"] > 1e-12:
            failures.append(["closure", r])
        if r["family"] in {"FIELD-ALIGNED","ALIGNED-RANDOM"} and r["sector_forbidden_mass"] > 1e-12:
            failures.append(["aligned_leakage", r])
        if r["family"] == "TRANSVERSE-RANDOM" and r["sector_forbidden_mass"] <= 1e-8:
            failures.append(["transverse_no_leakage", r])
        if r["family"] in {"FIELD-TRANSVERSE","TRANSVERSE-RANDOM"} and r["offdiag_forbidden_real"] >= -1e-12:
            failures.append(["transverse_no_negative_cancellation", r])
    if failures:
        print(json.dumps(failures[:3], indent=2))
        raise SystemExit(f"preregistered gate failures: {len(failures)}")

    artifact = {
        "schema": "hypercomplexbrain.r1t.projected_partition.v1",
        "base_commit": BASE_COMMIT,
        "preregistration_commit": PREREG_COMMIT,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "secret": SECRET,
        "projection_seeds": PROJECTION_SEEDS,
        "control_seeds": CONTROL_SEEDS,
        "projection_checks": projection_checks,
        "rows": rows,
        "summary": summarize(rows),
        "status": "MEASURED_SELF_ATTESTED",
        "independent": False,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform()},
        "typed_remainders": ["[R]_projection", "[R]_partition", "[R]_measurement", "[R]_witness"],
        "interpretation_ceiling": "finite 16-state transversality/interference result only",
    }
    artifact["content_hash_without_self"] = sha256_json(artifact)
    out = Path("artifacts/r1t_projected_partition/projected_partition.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True)+"\n")
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
