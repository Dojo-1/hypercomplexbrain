#!/usr/bin/env python3
"""QSigma-R6c: the Hopf/Cartan layer, and the projective quotient R6b deferred.

    PYTHONPATH=src python3 experiments/run_hopf_layer.py

Three results, all identities rather than measurements:

  1. the TELOS swirl coordinates ARE the Cartan KAK decomposition of SL(2,R);
  2. S^1 -> SL(2,R) -> H^2 is the Lorentzian sibling of the Hopf fibration, and
     the Hopf map S^3 -> S^2 is exactly the density-matrix map;
  3. omega(A) = omega(-A) exactly, so the operational space is PSL(2,R) and the
     operational Fisher volume halves to pi^3 / sqrt(2).

(3) closes an item the external derivation explicitly left open ("before
projective quotienting").  (1) explains why R6b's QFI was diagonal at all.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.cayley_dickson import find_zero_divisor
from aionq.hopf_layer import (bloch_vector, fibre_is_local_unitary, hopf_ladder,
                              hopf_map, kak_decompose, kak_reconstruct,
                              projective_volume, swirl_to_kak)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "r6c_hopf_layer"
SEED = 20260728
N = 400


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    points = [(rng.uniform(0.05, 3.0), rng.uniform(-math.pi, math.pi),
               rng.uniform(-math.pi, math.pi)) for _ in range(N)]

    # 1 -- swirl == KAK
    worst_rec = worst_rho = worst_a = worst_b = 0.0
    for rho, phi, psi in points:
        M = to_sl2(swirl_point(rho, phi, psi))
        d = kak_decompose(M)
        worst_rec = max(worst_rec, float(np.max(np.abs(
            kak_reconstruct(d["alpha"], d["rho"], d["beta"]) - M))))
        worst_rho = max(worst_rho, abs(d["rho"] - rho))
        a_pred, b_pred = swirl_to_kak(phi, psi)
        worst_a = max(worst_a, abs(np.exp(2j * d["alpha"]) - np.exp(2j * a_pred)))
        worst_b = max(worst_b, abs(np.exp(2j * d["beta"]) - np.exp(2j * b_pred)))

    # the mechanism: compact motion is a local unitary
    worst_spec = 0.0
    for rho, phi, psi in points[:100]:
        M = to_sl2(swirl_point(rho, phi, psi))
        for delta in (0.1, 0.7, -1.3, 2.4):
            worst_spec = max(worst_spec,
                             fibre_is_local_unitary(M, delta)["max_singular_value_change"])
    noncompact = float(np.max(np.abs(
        np.linalg.svd(to_sl2(swirl_point(1.0, 0.3, 0.7)), compute_uv=False)
        - np.linalg.svd(to_sl2(swirl_point(1.4, 0.3, 0.7)), compute_uv=False))))

    # 2 -- Hopf map is the Bloch map, fibre is the global phase
    worst_hopf = worst_phase = worst_norm = 0.0
    for _ in range(N):
        v = rng.normal(size=2) + 1j * rng.normal(size=2)
        v = v / np.linalg.norm(v)
        h = hopf_map(v)
        worst_hopf = max(worst_hopf, float(np.max(np.abs(h - bloch_vector(v)))))
        worst_norm = max(worst_norm, abs(float(np.linalg.norm(h)) - 1.0))
        ph = np.exp(1j * rng.uniform(0, 2 * math.pi)) * v
        worst_phase = max(worst_phase, float(np.max(np.abs(h - hopf_map(ph)))))

    # 3 -- the projective quotient
    sign_blind = max(float(np.max(np.abs(attempted_use_state(to_sl2(swirl_point(*p)))[0]
                                         - attempted_use_state(-to_sl2(swirl_point(*p)))[0])))
                     for p in points[:100])
    vol = projective_volume()

    # the ladder, computed rather than cited
    ladder = hopf_ladder()
    zero_divisors = {d: find_zero_divisor(d) is not None for d in (2, 4, 8, 16)}

    report = {
        "round": "QSigma-R6c", "seed": SEED, "samples": N,
        "swirl_is_kak": {
            "worst_reconstruction_error": worst_rec,
            "worst_depth_error": worst_rho,
            "worst_alpha_error_doubled_angle": float(worst_a),
            "worst_beta_error_doubled_angle": float(worst_b),
            "worst_reconstruction": float(worst_rec),
            "relation": "alpha = -(phi-psi)/2, beta = (phi+psi)/2  (mod pi)",
            "consequence": ("R6b's QFI is diagonal in (rho,phi,psi) because the "
                            "Cartan decomposition is orthogonal, not by luck")},
        "compact_is_isometry": {
            "worst_singular_value_change_under_compact_step": worst_spec,
            "singular_value_change_under_noncompact_step": noncompact,
            "mechanism": ("compact directions act by local unitaries and move a "
                          "state inside its unitary orbit, changing no singular "
                          "value, so their Fisher information saturates; the "
                          "non-compact direction moves BETWEEN orbits by changing "
                          "the singular values, and that is what decays as "
                          "e^{-4 rho}")},
        "hopf": {
            "worst_hopf_minus_bloch": worst_hopf,
            "worst_phase_variation": worst_phase,
            "worst_norm_deviation": worst_norm,
            "fibration": "S^1 -> SL(2,R) -> H^2, the Lorentzian sibling of "
                         "S^1 -> S^3 -> S^2",
            "finding": ("the Hopf map IS the density-matrix map and its fibre IS "
                        "the global phase; quotienting by the fibre is what "
                        "taking a density matrix means")},
        "projective_quotient": {
            "worst_sign_sensitivity": sign_blind,
            "volume": vol,
            "closes": "the external derivation's 'before projective quotienting'"},
        "ladder": {"rungs": ladder, "zero_divisors_by_dimension": {str(k): bool(v) for k, v in zero_divisors.items()}},
    }
    # bool(...) on every entry: numpy comparisons return np.bool_, which is not
    # JSON-serialisable. The first run of this script died here, and the tempting
    # fix -- default=str on the dump -- would have written the string "True" into
    # the artifact instead of a boolean, so a downstream reader would see a
    # truthy value for a FAILED check. Cast at the source.
    checks = {
        "kak_reconstructs": worst_rec < 1e-12,
        "cartan_parameter_is_depth": worst_rho < 1e-12,
        "swirl_angles_are_cartan_angles": max(worst_a, worst_b) < 1e-12,
        "compact_motion_is_isometric": worst_spec < 1e-12,
        "noncompact_motion_is_not": noncompact > 0.1,
        "hopf_is_bloch": worst_hopf < 1e-12,
        "hopf_fibre_is_global_phase": worst_phase < 1e-12,
        "state_is_sign_blind_exactly": sign_blind == 0.0,
        "quotient_volume_finite": math.isfinite(vol["quotiented"]),
        "ladder_stops_at_zero_divisors": (zero_divisors[8] is False
                                          and zero_divisors[16] is True),
    }
    checks = {k: bool(v) for k, v in checks.items()}
    report["checks"] = checks
    report["verdict"] = "ALL IDENTITIES HOLD" if all(checks.values()) else "DISCREPANCY"

    path = OUT / "hopf_layer.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="MATH-R6C-HOPF_CARTAN",
        evidence_tag="P",
        command="PYTHONPATH=src python3 experiments/run_hopf_layer.py",
        observed_result={
            "sample_size": N,
            "worst_kak_angle_error": float(max(worst_a, worst_b)),
            "worst_hopf_minus_bloch": worst_hopf,
            "sign_sensitivity": sign_blind,
            "quotiented_volume": vol["quotiented"],
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[SEED],
        input_hashes=[f"swirl:rho={r:.9f},phi={p:.9f},psi={s:.9f}"
                      for r, p, s in points],
        raw_artifacts={"artifacts/r6c_hopf_layer/hopf_layer.json": file_digest(path)},
        environment_dependent=[],
        producer="experiments/run_hopf_layer.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {"kind": "scope_remainder",
             "carrier": "the Lorentzian fibration",
             "comparison": ("S^1 -> SL(2,R) -> H^2 is a principal U(1) bundle over "
                            "a constant-curvature surface, like the Hopf fibration. "
                            "It is NOT a Hopf fibration: the total space is not a "
                            "sphere and the base has curvature -1. The analogy is "
                            "structural and is not claimed to be more")},
            {"kind": "scope_remainder",
             "carrier": "Om / AUM",
             "comparison": ("named by the user as a three-phase cadence, not as an "
                            "operator. Nothing in this module is derived from it "
                            "and no quantum quantity is attached to it. The "
                            "three-fold structure that IS here -- K, A, K -- is the "
                            "Cartan decomposition, which stands on its own")}])
    save_envelope(envelope, OUT / "hopf_layer.envelope.json")

    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "volume": vol}, indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
