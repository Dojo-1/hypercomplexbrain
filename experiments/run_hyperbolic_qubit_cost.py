#!/usr/bin/env python3
"""QSigma-R6: price the (2,2) cognitive substrate against a unitary machine.

Runs the four preregistered predictions and the six preregistered controls, in
that order, and writes a deterministic JSON artifact plus an evidence envelope.

    PYTHONPATH=src python3 experiments/run_hyperbolic_qubit_cost.py

Preregistration: manifests/qsigma_r6_unitary_price_preregistration.json,
committed at 47def35, before this file existed.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.hyperbolic_qubit import (block_encode, composed_success_probability,
                                    conjugacy_class, elliptic_fraction_analytic,
                                    generator_norm_diagnostic, is_orthogonal,
                                    q22, singular_values, so22_generators,
                                    success_probability, swirl_point,
                                    swirl_state, to_sl2)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "r6_unitary_price"

RHO_GRID = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
PHI_GRID = [0.0, 0.4, 0.9, 1.5708, 2.3, 3.0]
PSI_GRID = [0.0, 1.1, 2.7]
MC_SAMPLES = 200_000
MC_SEED = 20260728


# ---------------------------------------------------------------- P1

def p1_depth_is_the_bill() -> dict:
    """Singular values e^r, e^-r; orthogonal iff r = 0.

    The sweep is over all three coordinates because the claim is that only ONE
    of them matters.  Sweeping rho alone would leave open the possibility that
    phi or psi also breaks unitarity, which is precisely what is being denied.
    """
    rows, worst_sv, worst_det, worst_frob = [], 0.0, 0.0, 0.0
    orthogonal_with_depth = []
    for rho in RHO_GRID:
        for phi in PHI_GRID:
            for psi in PSI_GRID:
                x = swirl_point(rho, phi, psi)
                M = to_sl2(x)
                s = singular_values(M)
                det_err = abs(float(np.linalg.det(M)) - 1.0)
                sv_err = max(abs(s[0] - math.exp(rho)), abs(s[1] - math.exp(-rho)))
                frob_err = abs(float(np.sum(M * M)) - 2.0 * math.cosh(2.0 * rho))
                orth = is_orthogonal(M)
                if orth and rho > 1e-9:
                    orthogonal_with_depth.append({"rho": rho, "phi": phi, "psi": psi})
                worst_sv = max(worst_sv, sv_err)
                worst_det = max(worst_det, det_err)
                worst_frob = max(worst_frob, frob_err)
                rows.append({"rho": rho, "phi": phi, "psi": psi,
                             "sigma_max": s[0], "sigma_min": s[1],
                             "condition_number": s[0] / s[1],
                             "orthogonal": orth})
    zero_depth = [r for r in rows if r["rho"] == 0.0]
    return {
        "n_points": len(rows),
        "worst_singular_value_error": worst_sv,
        "worst_det_error": worst_det,
        "worst_frobenius_error": worst_frob,
        "orthogonal_points_with_positive_depth": orthogonal_with_depth,
        "all_zero_depth_points_orthogonal": all(r["orthogonal"] for r in zero_depth),
        "n_zero_depth_points": len(zero_depth),
        "verdict": ("SURVIVES" if (worst_sv < 1e-12 and worst_det < 1e-12
                                   and worst_frob < 1e-12
                                   and not orthogonal_with_depth
                                   and all(r["orthogonal"] for r in zero_depth))
                    else "FALSIFIED"),
    }


# ---------------------------------------------------------------- P2

def p2_elliptic_fraction() -> dict:
    """Monte Carlo the elliptic fraction against (2/pi) arcsin(sech rho)."""
    rng = np.random.default_rng(MC_SEED)
    rows, worst_z = [], 0.0
    for rho in RHO_GRID:
        phis = rng.uniform(-math.pi, math.pi, MC_SAMPLES)
        # tr M = 2 cosh(rho) cos(phi); elliptic iff |tr| < 2.
        traces = 2.0 * math.cosh(rho) * np.cos(phis)
        empirical = float(np.mean(np.abs(traces) < 2.0))
        analytic = elliptic_fraction_analytic(rho)
        se = math.sqrt(max(analytic * (1.0 - analytic), 1e-12) / MC_SAMPLES)
        z = abs(empirical - analytic) / se
        worst_z = max(worst_z, z)
        rows.append({"rho": rho, "empirical": empirical, "analytic": analytic,
                     "z_score": z,
                     "large_rho_asymptote": 4.0 / math.pi * math.exp(-rho)})
    return {"samples_per_rho": MC_SAMPLES, "seed": MC_SEED, "rows": rows,
            "worst_z_score": worst_z,
            "verdict": "SURVIVES" if worst_z < 4.0 else "FALSIFIED"}


# ---------------------------------------------------------------- P3

def p3_post_selection_cost() -> dict:
    """Average and worst-case post-selection, measured through Qiskit."""
    avg_rows, worst_avg = [], 0.0
    for rho in RHO_GRID:
        M = to_sl2(swirl_point(rho, 0.0, 0.0))
        measured = success_probability(M)
        predicted = (1.0 + math.exp(-4.0 * rho)) / 2.0
        worst_avg = max(worst_avg, abs(measured - predicted))
        avg_rows.append({"rho": rho, "measured": measured, "predicted": predicted})

    chain_rows, worst_chain = [], 0.0
    for rho in (0.2, 0.4, 0.8):
        M = to_sl2(swirl_point(rho, 0.0, 0.0))
        for L in (1, 2, 3, 4):
            # |1> is the contracting singular direction of diag(e^r, e^-r).
            measured = composed_success_probability([M] * L, [0.0, 1.0])
            predicted = math.exp(-4.0 * L * rho)
            worst_chain = max(worst_chain, abs(measured - predicted))
            chain_rows.append({"rho": rho, "L": L, "n_qubits": L + 1,
                               "measured": measured, "predicted": predicted})
    return {
        "average_case": avg_rows,
        "worst_case_chain": chain_rows,
        "worst_average_error": worst_avg,
        "worst_chain_error": worst_chain,
        # Stated explicitly because quoting one number without the other is the
        # available way to mislead here, in either direction.
        "note": ("average-case cost saturates at 1/2 and is NOT exponential; "
                 "the exponential is in the worst case and in the "
                 "subnormalisation, where L steps at depth rho cost e^{-4 L rho}"),
        "verdict": ("SURVIVES" if worst_avg < 1e-10 and worst_chain < 1e-10
                    else "FALSIFIED"),
    }


# ---------------------------------------------------------------- P4

def _sl2_from_generators(word, gens) -> np.ndarray:
    from scipy.linalg import expm
    acc = np.eye(4)
    for name, amount in word:
        acc = expm(amount * gens[name]) @ acc
    return acc


def p4_echo_the_weave() -> dict:
    """A loop with zero net depth is exactly free -- if you may compile the net.

    Two circuits for the same loop.  One materialises every intermediate state
    and pays at each; the other applies the net element and pays nothing.  The
    gap between them is the design constraint.
    """
    rng = np.random.default_rng(MC_SEED + 1)
    gens = so22_generators()
    boost_names = ["K02", "K03", "K12", "K13"]

    closed, checked = [], 0
    for _ in range(4000):
        length = int(rng.integers(2, 5))
        amounts = rng.uniform(-1.2, 1.2, length)
        names = [boost_names[int(i)] for i in rng.integers(0, 4, length)]
        # Echo: append the exact inverse word in reverse order, then perturb
        # nothing.  This closes the loop by construction rather than by search,
        # which is the honest way to get a non-empty sample at this dimension.
        word = list(zip(names, amounts))
        echo = [(n, -a) for n, a in reversed(word)]
        R = _sl2_from_generators(word + echo, gens)
        x = R @ swirl_point(0.0, 0.0, 0.0)
        st = swirl_state(x)
        if abs(st.rho) > 1e-9:
            continue
        checked += 1
        M_net = to_sl2(x)
        net_orthogonal = is_orthogonal(M_net, tol=1e-10)

        # Same loop, but every step materialised.
        step_matrices = [to_sl2(_sl2_from_generators([w], gens) @ swirl_point(0.0, 0.0, 0.0))
                         for w in (word + echo)[:4]]
        stepwise = composed_success_probability(step_matrices, [0.0, 1.0])
        closed.append({"word_length": 2 * length, "net_rho": st.rho,
                       "net_orthogonal": net_orthogonal,
                       "net_success_probability": 1.0 if net_orthogonal else None,
                       "stepwise_success_probability_first4": stepwise})
        if checked >= 200:
            break

    failures = [c for c in closed if not c["net_orthogonal"]]
    stepwise_vals = [c["stepwise_success_probability_first4"] for c in closed]
    return {
        "n_closed_loops": len(closed),
        "n_net_orthogonal": len(closed) - len(failures),
        "failures": failures[:5],
        "median_stepwise_success_first4": float(np.median(stepwise_vals)) if stepwise_vals else None,
        "min_stepwise_success_first4": float(np.min(stepwise_vals)) if stepwise_vals else None,
        "interpretation": ("the net element of an echoed loop is exactly a "
                           "rotation and costs nothing; the same loop with its "
                           "intermediate states materialised still pays at every "
                           "step, so echoing is a compilation constraint, not a "
                           "free win"),
        "verdict": "SURVIVES" if closed and not failures else "FALSIFIED",
    }


# ---------------------------------------------------------------- controls

def controls() -> dict:
    out = {}

    # C1: encoding fidelity.  If this fails nothing else in the round counts.
    from qiskit.quantum_info import Operator
    from aionq.hyperbolic_qubit import block_encoding_circuit
    worst = 0.0
    for rho in RHO_GRID:
        for phi in PHI_GRID[:3]:
            M = to_sl2(swirl_point(rho, phi, 0.0))
            U, s = block_encode(M)
            qc, _ = block_encoding_circuit(M)
            compiled = np.asarray(Operator(qc).data).real
            worst = max(worst, float(np.max(np.abs(compiled[:2, :2] - M / s))),
                        float(np.max(np.abs(compiled @ compiled.T - np.eye(4)))))
    out["C1_encoding_fidelity"] = {
        "worst_error": worst,
        "verdict": "PASS" if worst < 1e-12 else "FAIL (round is void)"}

    # C2: the compact directions are measurably free.
    free = []
    for phi in PHI_GRID:
        for psi in PSI_GRID:
            M = to_sl2(swirl_point(0.0, phi, psi))
            free.append({"phi": phi, "psi": psi, "orthogonal": is_orthogonal(M),
                         "success_probability": success_probability(M)})
    out["C2_compact_null"] = {
        "rows": free,
        "verdict": "PASS" if all(r["orthogonal"] and abs(r["success_probability"] - 1.0) < 1e-10
                                 for r in free) else "FAIL"}

    # C3: the wrong instrument, run on purpose.
    diag = [generator_norm_diagnostic(r) for r in (0.0, 0.5, 1.0, 2.0, 3.0)]
    gen_norms = diag[0]["generator_frobenius"]
    compact_flat = abs(diag[0]["group_frobenius_rotation_J01"]
                       - diag[-1]["group_frobenius_rotation_J01"]) < 1e-9
    boost_diverges = (diag[-1]["group_frobenius_boost_K02"]
                      > 10 * diag[0]["group_frobenius_boost_K02"])
    out["C3_wrong_instrument"] = {
        "generator_frobenius_norms": gen_norms,
        "generator_norms_all_equal": len(set(round(v, 12) for v in gen_norms.values())) == 1,
        "rows": diag,
        "finding": ("the generators are bounded and their norms are IDENTICAL for "
                    "compact and non-compact alike, so at the algebra level the "
                    "Frobenius norm cannot even distinguish the two kinds; at the "
                    "group level it diverges for boosts and is constant for "
                    "rotations, so it reports rapidity and nothing else. S8's "
                    "typed remainder said 'the generators are unbounded'. They "
                    "are not. The unboundedness is in the group."),
        "verdict": "PASS" if compact_flat and boost_diverges else "FAIL"}

    # C4: elliptic does not mean unitary.
    witnesses = []
    for rho in (0.3, 0.8, 1.5):
        phi = math.pi / 2.0          # tr = 0: as elliptic as it gets
        M = to_sl2(swirl_point(rho, phi, 0.4))
        witnesses.append({"rho": rho, "phi": phi,
                          "conjugacy_class": conjugacy_class(M),
                          "orthogonal": is_orthogonal(M),
                          "condition_number": singular_values(M)[0] / singular_values(M)[1]})
    out["C4_elliptic_is_not_unitary"] = {
        "witnesses": witnesses,
        "verdict": "PASS" if all(w["conjugacy_class"] == "elliptic" and not w["orthogonal"]
                                 for w in witnesses) else "FAIL"}

    # C5: determinant drift.
    worst_det = max(abs(float(np.linalg.det(to_sl2(swirl_point(r, p, s)))) - 1.0)
                    for r in RHO_GRID for p in PHI_GRID for s in PSI_GRID)
    worst_q = max(abs(q22(swirl_point(r, p, s)) - 1.0)
                  for r in RHO_GRID for p in PHI_GRID for s in PSI_GRID)
    out["C5_determinant_drift"] = {
        "worst_det_error": worst_det, "worst_q22_error": worst_q,
        "verdict": "PASS" if worst_det < 1e-12 and worst_q < 1e-12 else "FAIL"}

    # C6 is P4's own loop closure; recorded there.
    out["C6_randomised_loop_closure"] = {"see": "P4_echo_the_weave"}
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "round": "QSigma-R6",
        "preregistration": "manifests/qsigma_r6_unitary_price_preregistration.json",
        "P1_depth_is_the_bill": p1_depth_is_the_bill(),
        "P2_elliptic_fraction": p2_elliptic_fraction(),
        "P3_post_selection_cost": p3_post_selection_cost(),
        "P4_echo_the_weave": p4_echo_the_weave(),
        "controls": controls(),
    }
    verdicts = {k: v["verdict"] for k, v in report.items()
                if isinstance(v, dict) and "verdict" in v}
    verdicts.update({k: v.get("verdict") for k, v in report["controls"].items()
                     if isinstance(v, dict) and "verdict" in v})
    report["summary"] = verdicts

    path = OUT / "unitary_price.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    p1, p2, p3 = (report["P1_depth_is_the_bill"], report["P2_elliptic_fraction"],
                  report["P3_post_selection_cost"])
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6-UNITARY_PRICE",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_hyperbolic_qubit_cost.py",
        observed_result={
            # One observation per swept grid point, enumerated below.  Not the
            # number of predictions, and not the Monte Carlo sample count --
            # 200000 draws of phi certify one fraction, not 200000 observations.
            "sample_size": p1["n_points"],
            "worst_singular_value_error": p1["worst_singular_value_error"],
            "worst_elliptic_fraction_z": p2["worst_z_score"],
            "worst_post_selection_error": max(p3["worst_average_error"],
                                              p3["worst_chain_error"]),
            "orthogonal_points_with_positive_depth": len(
                p1["orthogonal_points_with_positive_depth"]),
            "verdicts": verdicts,
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[MC_SEED, MC_SEED + 1],
        input_hashes=[f"swirl:rho={r:.6f},phi={p:.6f},psi={s:.6f}"
                      for r in RHO_GRID for p in PHI_GRID for s in PSI_GRID],
        raw_artifacts={"artifacts/r6_unitary_price/unitary_price.json": file_digest(path)},
        # Exact linear algebra and statevector simulation: no timing, no device,
        # no thread count.  A digest mismatch across machines would be a real
        # disagreement, so this claim is a candidate for recomputation.
        environment_dependent=[],
        producer="experiments/run_hyperbolic_qubit_cost.py",
        verifier="",
        typed_remainders=[{
            "kind": "representation_remainder",
            "carrier": "infinite-dimensional unitary representations of SU(1,1)",
            "comparison": ("this round prices only the non-unitary branch, paid "
                           "for by post-selection. The other branch -- truncating "
                           "an infinite-dimensional unitary representation and "
                           "paying in truncation error instead -- is not measured "
                           "here and must not be assumed to be worse or better")},
            {"kind": "scope_remainder",
             "carrier": "hyperbolic memory capacity",
             "comparison": ("the claimed advantage of a hyperbolic reservoir is "
                            "exponential capacity in a ball of radius r. This "
                            "round measures an exponential cost in the same r. "
                            "Whether they cancel is NOT established here; no "
                            "reservoir was built or measured")}])
    save_envelope(envelope, OUT / "unitary_price.envelope.json")

    print(json.dumps(verdicts, indent=2, sort_keys=True))
    print(f"wrote {path}")
    print(f"wrote {OUT / 'unitary_price.envelope.json'}")
    return 0 if all(v and v.startswith(("SURVIVES", "PASS")) for v in verdicts.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
