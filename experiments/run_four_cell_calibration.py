#!/usr/bin/env python3
"""Execute the frozen QΣ-R3B-0 four-cell instrument calibration.

This producer emits a bounded simulator result, not a cognitive or quantum
advantage claim.  The preregistered final decision is HOLD because four
cone-constrained coordinates are unmeasured and independent audit strength is
zero.
"""

from __future__ import annotations

import ast
from hashlib import sha256
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.advantage import (  # noqa: E402
    OUTCOME_DIMENSIONS,
    AdvantageCone,
    Direction,
    EmpiricalEffectPosterior,
    promote,
)
from aionq.evidence import (  # noqa: E402
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
    verify,
)
from aionq.four_cell import (  # noqa: E402
    Arm,
    CALIBRATION_PHASES,
    COMMON_FRAMES,
    HELDOUT_PHASES,
    REPETITIONS_PER_FACTOR_CELL,
    TRIALS_PER_ARM_PER_SEED,
    Cell,
    Relation,
    analytic_click_probability,
    run_seed_calibration,
)


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "artifacts" / "r3b_four_cell"
RESULT = OUT_DIR / "four_cell_calibration.json"
ENVELOPE = OUT_DIR / "four_cell_calibration.envelope.json"
MANIFEST = (
    ROOT / "manifests" / "qsigma_r3b_four_cell_calibration_preregistration.json"
)
SOURCE = ROOT / "src" / "aionq" / "four_cell.py"
ADVANTAGE = ROOT / "src" / "aionq" / "advantage.py"
PACKAGE_INIT = ROOT / "src" / "aionq" / "__init__.py"
TEST = ROOT / "tests" / "test_four_cell.py"
DOC = ROOT / "docs" / "QSIGMA_R3B_FOUR_CELL.md"
ARCHITECTURE_DOC = ROOT / "docs" / "ARCHITECTURE.md"
RUNNER = Path(__file__).resolve()
COMMAND = "python experiments/run_four_cell_calibration.py"
PRODUCER_FILES = (
    MANIFEST,
    SOURCE,
    ADVANTAGE,
    PACKAGE_INIT,
    TEST,
    DOC,
    ARCHITECTURE_DOC,
    RUNNER,
)


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _native_bools(flags: dict[str, object]) -> dict[str, bool]:
    """Normalize NumPy predicate results for strict portable JSON."""
    return {
        name: bool(passed)
        for name, passed in flags.items()
    }


def _seed_input_hash(calibration) -> str:
    """Hash the actual factor schedule and variates, not the seed label."""
    schedule_and_stream = [
        {
            "phase": trial.spec.reference_phase,
            "relation": trial.spec.relation.name,
            "frame": trial.spec.frame,
            "repetition": trial.spec.repetition,
            "uniform": trial.uniform_draw,
        }
        for trial in calibration.target.trials
    ]
    return _canonical_digest(schedule_and_stream)


def _source_digests() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_digest(path)
        for path in PRODUCER_FILES
    }


def _assert_clean_producer_state() -> str:
    """Fail before writing if filesystem code cannot be attributed to HEAD."""
    head = current_commit(ROOT)
    if head == "unknown":
        raise RuntimeError("R3B-0 producer requires a readable Git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if status.returncode != 0:
        raise RuntimeError(
            "could not inspect producer worktree: " + status.stderr.strip()
        )
    if status.stdout.strip():
        raise RuntimeError(
            "R3B-0 producer requires a clean worktree; refusing dirty "
            "provenance:\n" + status.stdout.rstrip()
        )
    for path in PRODUCER_FILES:
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        tracked = subprocess.run(
            ["git", "cat-file", "-e", f"{head}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if tracked.returncode != 0:
            raise RuntimeError(
                f"producer input {relative} is not committed at HEAD {head[:12]}"
            )
    return head


def _assigns_retired_scalar(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and node.id == "q_causal"
        )
        or (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Store)
            and node.attr == "q_causal"
        )
        for node in ast.walk(tree)
    )


def _manifest_contract(manifest: dict) -> bool:
    protocol = manifest["protocol"]
    outcome = manifest["outcome_contract"]
    return bool(
        manifest["status"] == "FROZEN_BEFORE_EXECUTION_AND_RESULTS"
        and tuple(protocol["calibration_phases"]) == CALIBRATION_PHASES
        and tuple(protocol["heldout_phases"]) == HELDOUT_PHASES
        and tuple(protocol["common_frames"]) == COMMON_FRAMES
        and protocol["repetitions_per_factor_cell"]
        == REPETITIONS_PER_FACTOR_CELL
        and protocol["trials_per_arm_per_seed"] == TRIALS_PER_ARM_PER_SEED
        and tuple(outcome["coordinate_order"]) == OUTCOME_DIMENSIONS
        and manifest["advantage_cone"]["registered_outcome"] == "HOLD"
    )


def _registered_cone(manifest: dict) -> AdvantageCone:
    registered = manifest["advantage_cone"]
    constraints = {
        dimension: {
            "improve": Direction.IMPROVE,
            "no_worse": Direction.NO_WORSE,
            "free": Direction.FREE,
        }[direction]
        for dimension, direction in registered["constraints"].items()
    }
    return AdvantageCone(
        name=registered["name"],
        constraints=constraints,
        margins={
            dimension: float(margin)
            for dimension, margin in registered["margins"].items()
        },
        tolerance=float(registered["no_worse_tolerance"]),
    )


def _as_seed_record(calibration, input_hash: str) -> dict:
    return {
        "seed": calibration.seed,
        "input_hash": input_hash,
        "target": calibration.target.outcome.to_dict(),
        "control": calibration.control.outcome.to_dict(),
        "paired_effect": calibration.paired_outcome.delta.to_dict(),
        "controls": {
            "resource_parity": calibration.parity.holds,
            "analytic_auditor": calibration.auditor.holds,
            "common_frame_covariance": calibration.basis_attack.covariant,
            "basis_attack_detected": calibration.basis_attack.attack_detected,
            "role_ablation_holds": all(
                item.decision == "HOLD"
                and bool(item.typed_refusal)
                and set(item.attempted_roles) == set(Cell) - {item.role}
                for item in calibration.role_ablations
            ),
            "registered_decision": calibration.registered_decision,
        },
    }


def main() -> int:
    existing = [path for path in (RESULT, ENVELOPE) if path.exists()]
    if existing:
        raise FileExistsError(
            "R3B-0 artifacts are append-once; refusing to overwrite: "
            + ", ".join(str(path) for path in existing)
        )
    producer_commit = _assert_clean_producer_state()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seeds = tuple(int(seed) for seed in manifest["protocol"]["seeds"])
    if seeds != tuple(range(73001, 73033)):
        raise RuntimeError("frozen seed cluster list drifted")

    calibrations = tuple(run_seed_calibration(seed) for seed in seeds)
    input_hashes = tuple(_seed_input_hash(item) for item in calibrations)
    target = tuple(item.target.outcome for item in calibrations)
    control = tuple(item.control.outcome for item in calibrations)
    posterior = EmpiricalEffectPosterior.from_paired(
        target,
        control,
        draws=int(manifest["uncertainty"]["draws"]),
        seed=int(manifest["uncertainty"]["bootstrap_seed"]),
    )
    cone = _registered_cone(manifest)
    decision = promote(
        posterior,
        cone,
        alpha=float(manifest["advantage_cone"]["alpha"]),
        audit=float(manifest["advantage_cone"]["audit_strength"]),
        audit_threshold=float(manifest["advantage_cone"]["audit_threshold"]),
        compute_parity=all(item.parity.holds for item in calibrations),
        constraints_ok=all(item.controls_hold for item in calibrations),
        samples=int(manifest["uncertainty"]["draws"]),
        seed=int(manifest["uncertainty"]["promotion_sampling_seed"]),
    )
    intervals = posterior.interval(0.99)
    mean = posterior.mean
    index = {dimension: i for i, dimension in enumerate(OUTCOME_DIMENSIONS)}

    observed_dimensions = tuple(
        dimension
        for dimension in OUTCOME_DIMENSIONS
        if dimension not in posterior.missing_dimensions
    )
    expected_probabilities = {
        f"{arm.value}_{relation.name.lower()}": analytic_click_probability(
            CALIBRATION_PHASES[0], relation, arm
        )
        for arm in Arm
        for relation in Relation
    }
    oracle_expected = {
        "coherent_same": 1.0,
        "coherent_orthogonal": 0.0,
        "dephased_same": 0.5,
        "dephased_orthogonal": 0.5,
    }
    interval_clears_margin = {
        dimension: (
            intervals[dimension] is not None
            and intervals[dimension][0]
            > float(manifest["advantage_cone"]["margins"][dimension])
        )
        for dimension in ("accuracy", "generalization", "robustness", "calibration")
    }

    replay = run_seed_calibration(seeds[0])
    replay_hash = _seed_input_hash(replay)
    bootstrap_rng = np.random.default_rng(
        int(manifest["uncertainty"]["bootstrap_seed"])
    )
    bootstrap_indices = bootstrap_rng.integers(
        0,
        len(seeds),
        size=(int(manifest["uncertainty"]["draws"]), len(seeds)),
        endpoint=False,
    )
    expected_joint_bootstrap = np.full_like(
        posterior.bootstrap_draws, np.nan
    )
    expected_joint_bootstrap[:, posterior.observed] = posterior.cluster_effects[
        bootstrap_indices
    ][:, :, posterior.observed].mean(axis=1)
    controls = {
        "C0_density_and_operator_contract": all(
            item.auditor.holds for item in calibrations
        ),
        "C1_analytic_click_probabilities": all(
            abs(expected_probabilities[key] - expected) <= 1e-12
            for key, expected in oracle_expected.items()
        ),
        "C2_phase_sets_disjoint": set(CALIBRATION_PHASES).isdisjoint(
            HELDOUT_PHASES
        ),
        "C3_common_frame_covariance": all(
            item.basis_attack.covariant for item in calibrations
        ),
        "C4_matched_resource_and_stream_parity": all(
            item.parity.holds for item in calibrations
        ),
        "C5_seed_replay_exact": (
            replay_hash == input_hashes[0]
            and replay.target.outcome.as_dict()
            == calibrations[0].target.outcome.as_dict()
            and replay.control.outcome.as_dict()
            == calibrations[0].control.outcome.as_dict()
        ),
        "C6_required_role_ablations_hold": all(
            len(item.role_ablations) == len(Cell)
            and all(
                ablation.decision == "HOLD"
                and bool(ablation.typed_refusal)
                and set(ablation.attempted_roles)
                == set(Cell) - {ablation.role}
                for ablation in item.role_ablations
            )
            for item in calibrations
        ),
        "C7_untransported_povm_attack_detected": all(
            item.basis_attack.attack_detected for item in calibrations
        ),
        "C8_outcome_scalarization_refused": False,
        "C9_joint_seed_cluster_bootstrap": (
            posterior.cluster_effects.shape == (len(seeds), 8)
            and posterior.bootstrap_draws.shape
            == (int(manifest["uncertainty"]["draws"]), 8)
            and np.allclose(
                posterior.bootstrap_draws[:, posterior.observed],
                expected_joint_bootstrap[:, posterior.observed],
                atol=0.0,
                rtol=0.0,
            )
            and np.all(np.isnan(
                posterior.bootstrap_draws[:, ~posterior.observed]
            ))
        ),
        "C10_constrained_missing_axes_block": (
            decision.probability is None
            and not decision.promoted
            and set(posterior.missing_dimensions)
            == {"sample_efficiency", "neg_energy", "neg_latency", "recovery"}
            and any("unmeasured" in blocker for blocker in decision.blockers)
        ),
        "C11_legacy_scalar_untouched": not any(
            _assigns_retired_scalar(path)
            for path in (SOURCE, ADVANTAGE, RUNNER)
        ),
        "C12_registered_outcome_is_hold": (
            manifest["advantage_cone"]["registered_outcome"] == "HOLD"
            and not decision.promoted
        ),
        "manifest_binding": _manifest_contract(manifest),
        "distinct_seed_streams": len(set(input_hashes)) == len(seeds),
    }
    try:
        float(target[0])
    except TypeError:
        controls["C8_outcome_scalarization_refused"] = True
    controls = _native_bools(controls)

    instrument_controls = {
        name: passed
        for name, passed in controls.items()
        if name
        not in {
            "C12_registered_outcome_is_hold",
        }
    }
    calibration_survives = all(interval_clears_margin.values())
    if not all(instrument_controls.values()):
        status = "VOID_INSTRUMENT"
    elif not calibration_survives:
        status = "FALSIFIED_CALIBRATION"
    else:
        status = "CALIBRATED_HOLD"
    controls["C12_registered_outcome_is_hold"] = bool(
        controls["C12_registered_outcome_is_hold"]
        and status == "CALIBRATED_HOLD"
    )

    if _assert_clean_producer_state() != producer_commit:
        raise RuntimeError("Git HEAD changed during the frozen R3B-0 run")
    source_digests = _source_digests()
    seed_records = [
        _as_seed_record(calibration, input_hash)
        for calibration, input_hash in zip(calibrations, input_hashes)
    ]
    remainders = [
        "sample_efficiency is unmeasured; no learning curve was run.",
        "neg_energy is unmeasured; operation-count parity is not joules.",
        "neg_latency is unmeasured; logical depth is not device latency.",
        "recovery is unmeasured; no interruption-and-recovery protocol was run.",
        "The coherent-versus-dephased split is a simulator positive control, not a quantum or causal advantage result.",
        "No hardware, real dataset, cognitive system, or external intervention was measured.",
        "The run is first-party and has no independent recomputation.",
        "A future full R3B organ experiment must preregister and measure all constrained axes.",
    ]
    payload = {
        "schema": "hypercomplexbrain.qsigma_r3b.four_cell_calibration.v1",
        "round": manifest["round"],
        "status": status,
        "registered_final_decision": "HOLD",
        "evidence_ceiling": manifest["evidence_ceiling"],
        "implementation_commit": producer_commit,
        "preregistration": {
            "path": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "digest": file_digest(MANIFEST),
            "frozen_commit": "aa2bf291d8733161b66fe317b4dd812db7800020",
        },
        "source_digests": source_digests,
        "protocol": {
            "seeds": list(seeds),
            "effective_seed_clusters": len(seeds),
            "trials_per_arm_per_seed": TRIALS_PER_ARM_PER_SEED,
            "total_trial_rows": (
                len(seeds) * TRIALS_PER_ARM_PER_SEED * len(Arm)
            ),
            "copies_per_trial": 1,
            "memory_calls_per_trial": 1,
            "povm_outcomes": 2,
            "side_registers": 0,
            "common_frames": list(COMMON_FRAMES),
            "calibration_phases": list(CALIBRATION_PHASES),
            "heldout_phases": list(HELDOUT_PHASES),
        },
        "analytic_contract": {
            "click_probabilities": expected_probabilities,
            "target_outcome": {
                "accuracy": 1.0,
                "generalization": 1.0,
                "robustness": 1.0,
                "sample_efficiency": None,
                "calibration": 1.0,
                "neg_energy": None,
                "neg_latency": None,
                "recovery": None,
            },
            "control_expected_outcome": {
                "accuracy": 0.5,
                "generalization": 0.5,
                "robustness": 0.5,
                "sample_efficiency": None,
                "calibration": 0.75,
                "neg_energy": None,
                "neg_latency": None,
                "recovery": None,
            },
            "expected_effect": {
                "accuracy": 0.5,
                "generalization": 0.5,
                "robustness": 0.5,
                "sample_efficiency": None,
                "calibration": 0.25,
                "neg_energy": None,
                "neg_latency": None,
                "recovery": None,
            },
        },
        "outcome_contract": {
            "coordinate_order": list(OUTCOME_DIMENSIONS),
            "observed_dimensions": list(observed_dimensions),
            "missing_dimensions": list(posterior.missing_dimensions),
            "scalarization": "forbidden",
        },
        "seed_clusters": seed_records,
        "paired_seed_cluster_posterior": {
            "mean_effect": {
                dimension: (
                    float(mean[index[dimension]])
                    if dimension in observed_dimensions
                    else None
                )
                for dimension in OUTCOME_DIMENSIONS
            },
            "interval_level": 0.99,
            "intervals": {
                dimension: (
                    list(intervals[dimension])
                    if intervals[dimension] is not None
                    else None
                )
                for dimension in OUTCOME_DIMENSIONS
            },
            "bootstrap_draws": int(manifest["uncertainty"]["draws"]),
            "bootstrap_seed": int(manifest["uncertainty"]["bootstrap_seed"]),
            "draw_digest": "sha256:" + posterior.draw_digest,
            "unit": "paired seed cluster",
        },
        "advantage_cone": {
            "name": cone.name,
            "alpha": float(manifest["advantage_cone"]["alpha"]),
            "constraints": manifest["advantage_cone"]["constraints"],
            "margins": manifest["advantage_cone"]["margins"],
            "no_worse_tolerance": cone.tolerance,
            "interval_clears_margin": interval_clears_margin,
            "probability": decision.probability,
            "promoted": decision.promoted,
            "blockers": list(decision.blockers),
        },
        "controls": controls,
        "control_failures": [
            name for name, passed in controls.items() if not passed
        ],
        "verdict_ledger": {
            "instrument": (
                "VALID" if all(instrument_controls.values()) else "VOID"
            ),
            "positive_calibration": (
                "SURVIVES" if calibration_survives else "FALSIFIED"
            ),
            "promotion": "HOLD",
            "audit": "NOT_INDEPENDENTLY_WITNESSED",
            "final": status,
        },
        "typed_remainders": remainders,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    envelope = EvidenceEnvelope(
        claim_id="QSIGMA-R3B-0-FOUR-CELL-CALIBRATION",
        evidence_tag="M",
        command=COMMAND,
        observed_result={
            "status": status,
            "sample_size": len(seeds),
            "registered_final_decision": "HOLD",
            "observed_dimensions": list(observed_dimensions),
            "missing_dimensions": list(posterior.missing_dimensions),
            "null": (
                "the coherent identity-memory arm does not clear the frozen "
                "instrument margins over complete dephasing"
            ),
            "interval": "paired seed-cluster percentile 99% intervals",
        },
        commit_sha=producer_commit,
        working_directory=".",
        platform=platform.system().lower(),
        environment=environment_digest(),
        input_hashes=list(input_hashes),
        seeds=list(seeds),
        raw_artifacts={
            str(RESULT.relative_to(ROOT)).replace("\\", "/"): file_digest(RESULT)
        },
        uncertainty={
            "unit": "paired seed cluster",
            "bootstrap_draws": int(manifest["uncertainty"]["draws"]),
            "bootstrap_seed": int(manifest["uncertainty"]["bootstrap_seed"]),
            "independence": False,
        },
        producer="experiments/run_four_cell_calibration.py",
        verifier="",
        signature_status="unsigned",
        typed_remainders=remainders,
        verification_mode="not_requested",
    )
    save_envelope(envelope, ENVELOPE)
    # The append-once producer runs before an artifact commit exists. This is a
    # provisional worktree check; evidence.v2 promotion requires a later
    # envelope phase bound to the raw commit.
    check = verify(envelope, repo_root=ROOT, check_commit=False)
    if not check.ok:
        raise RuntimeError(
            "local evidence-envelope verification failed: "
            + "; ".join(check.failures)
        )

    print(
        json.dumps(
            {
                "status": status,
                "registered_final_decision": "HOLD",
                "controls": controls,
                "mean_effect": payload["paired_seed_cluster_posterior"][
                    "mean_effect"
                ],
                "intervals": payload["paired_seed_cluster_posterior"]["intervals"],
                "missing_dimensions": list(posterior.missing_dimensions),
                "independent": check.independent,
                "result": str(RESULT),
                "envelope": str(ENVELOPE),
            },
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "CALIBRATED_HOLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
