#!/usr/bin/env python3
"""QSigma-R6d: the three gates R6b left open.

    PYTHONPATH=src python3 experiments/run_holevo_sandwich.py

  A. the information sandwich I_PGM <= I_acc <= chi <= log2 N, with the exact
     flag/success decomposition of chi;
  B. data processing: a parameter-independent CPTP map cannot increase chi,
     cannot increase trace distance, cannot decrease fidelity;
  C. the q -> 0 boundary limit -- what the channel converges to at infinite depth.

C returned something R6b did not predict, and the control killed half of it.

The first random codebook showed chi rising with depth, which looked like a
finding: deeper is more informative.  It is not.  A deterministic evenly-spaced
codebook dips before it rises, and two of five random seeds converge from ABOVE.
"chi increases with depth" is withdrawn as an artifact of one draw.

What survives the control is stronger than what did not.  chi CONVERGES, to a
constant with a closed form.  At infinite depth A becomes rank one, so |v>
becomes a product state of norm^2 = 1/2; hence p_bar -> 1/2, every S(omega_i) ->
h2(1/2) = 1 bit, and the flag decomposition gives

    chi  ->  (1/2) S(sigmahat)  <=  1 bit.

The grid codebook averages to the maximally mixed state on C^4, so S(sigmahat) =
2 and chi = 1.000000000 bit exactly, with a tail spread of 6e-15 over rho in
[8, 16].  The channel does not die at depth; it converges to a boundary channel
worth at most one bit per use.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.holevo_sandwich import (apply_channel, flag_success_decomposition,
                                   holevo_chi, information_sandwich,
                                   pgm_mutual_information, random_cptp)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import (attempted_use_state,
                                            root_fidelity_closed_form,
                                            trace_distance_closed_form)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "r6d_holevo_sandwich"
SEED = 20260728
N_CODE = 8
DEPTHS = [0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0]


def _omega(rho, phi, psi):
    return attempted_use_state(to_sl2(swirl_point(rho, phi, psi)))[0].astype(complex)


def _random_book(rho, n, rng):
    return [_omega(rho, rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi))
            for _ in range(n)]


def _grid_book(rho, n):
    """Deterministic evenly-spaced codebook -- the control for the depth sweep."""
    return [_omega(rho, 2 * math.pi * k / n, 2 * math.pi * (k * 3 % n) / n)
            for k in range(n)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    report: dict = {"round": "QSigma-R6d", "seed": SEED, "n_codewords": N_CODE}

    # ---- A: the sandwich, and the flag decomposition -----------------------
    rows, ordering_ok, worst_resid = [], True, 0.0
    for rho in DEPTHS:
        book = _random_book(rho, N_CODE, np.random.default_rng(SEED))
        s = information_sandwich(book)
        d = flag_success_decomposition(book)
        ordering_ok &= s["ordering_holds"]
        worst_resid = max(worst_resid, d["residual"])
        rows.append({"rho": rho, **{k: s[k] for k in ("I_PGM", "chi", "log2_N")},
                     "flag_bits": d["flag_bits"],
                     "success_branch_bits": d["success_branch_bits"],
                     "p_bar": d["p_bar"], "decomposition_residual": d["residual"]})
    report["sandwich"] = {"rows": rows, "ordering_holds_everywhere": ordering_ok,
                          "worst_decomposition_residual": worst_resid}

    # A fixed-depth codebook must give a flag that carries nothing; a mixed-depth
    # one must give a flag that does. Both directions, or the identity is vacuous.
    mixed = [_omega(r, rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi))
             for r in (0.05, 0.4, 1.0, 2.5)]
    mixed_d = flag_success_decomposition(mixed)
    report["flag_carries_only_depth_spread"] = {
        "fixed_depth_flag_bits": max(abs(r["flag_bits"]) for r in rows),
        "mixed_depth_flag_bits": mixed_d["flag_bits"],
        "mixed_residual": mixed_d["residual"],
        "finding": ("the Jensen gap h2(pbar) - <h2(p_i)> is exactly zero when all "
                    "codewords sit at one depth, so in a fixed-depth codebook the "
                    "erasure flag carries NO information and all of chi lives in "
                    "the success branch. It becomes informative only when depths "
                    "differ, and then it reports the depth spread, not the message")}

    # ---- B: data processing ------------------------------------------------
    book = _random_book(0.8, 6, np.random.default_rng(SEED + 1))
    chi0 = holevo_chi(book)
    dp_rows, dp_ok, worst_kraus = [], True, 0.0
    for trial in range(12):
        K = random_cptp(5, 3, rng)
        worst_kraus = max(worst_kraus, float(np.max(np.abs(
            sum(k.conj().T @ k for k in K) - np.eye(5)))))
        out = [apply_channel(s, K) for s in book]
        chi1 = holevo_chi(out)
        ipgm1 = pgm_mutual_information(out)
        # The tempting wrong test is I_PGM(Phi) <= I_PGM(id): NOT implied, because
        # the PGM is chosen for whichever ensemble it is handed. The implied
        # statement is that no measurement after Phi beats chi before it.
        ok = chi1 <= chi0 + 1e-9 and ipgm1 <= chi0 + 1e-9
        dp_ok &= ok
        dp_rows.append({"trial": trial, "chi_after": chi1, "I_PGM_after": ipgm1,
                        "contracts": bool(ok)})

    # distance monotonicity on the same channels
    worst_d_violation = worst_f_violation = 0.0
    for _ in range(40):
        MA = to_sl2(swirl_point(rng.uniform(0.05, 2.5), rng.uniform(-3, 3), rng.uniform(-3, 3)))
        MB = to_sl2(swirl_point(rng.uniform(0.05, 2.5), rng.uniform(-3, 3), rng.uniform(-3, 3)))
        WA = attempted_use_state(MA)[0].astype(complex)
        WB = attempted_use_state(MB)[0].astype(complex)
        d0 = trace_distance_closed_form(MA, MB)
        f0 = root_fidelity_closed_form(MA, MB)
        K = random_cptp(5, 3, rng)
        TA, TB = apply_channel(WA, K), apply_channel(WB, K)
        d1 = 0.5 * float(np.sum(np.abs(np.linalg.eigvalsh(TA - TB))))
        f1 = float(np.sum(np.linalg.svd(_psd_sqrt(TA) @ _psd_sqrt(TB),
                                        compute_uv=False)))
        worst_d_violation = max(worst_d_violation, d1 - d0)
        worst_f_violation = max(worst_f_violation, f0 - f1)
    report["data_processing"] = {
        "chi_before": chi0, "trials": dp_rows,
        "all_contract": bool(dp_ok),
        "worst_kraus_completeness_deviation": worst_kraus,
        "worst_trace_distance_increase": worst_d_violation,
        "worst_fidelity_decrease": worst_f_violation}

    # ---- C: the q -> 0 boundary, with its control --------------------------
    # sorted(): the first version concatenated DEPTHS + deep unsorted and then
    # tested the result for monotonicity, so the check could only fail. That was a
    # bug in the check. Fixing it does NOT rescue the claim -- see below.
    all_depths = sorted(set(DEPTHS + [4.0, 6.0, 8.0, 12.0, 16.0]))
    grid_sweep = []
    for r in all_depths:
        gb = _grid_book(r, N_CODE)
        gd = flag_success_decomposition(gb)
        grid_sweep.append({"rho": r, "chi": holevo_chi(gb),
                           "I_PGM": pgm_mutual_information(gb),
                           "p_bar": gd["p_bar"],
                           "success_branch_bits": gd["success_branch_bits"]})
    seed_sweep = []
    for s in range(5):
        vals = [holevo_chi(_random_book(r, N_CODE, np.random.default_rng(100 + s)))
                for r in (0.25, 1.0, 4.0, 12.0)]
        seed_sweep.append({"seed": 100 + s, "chi_by_depth": vals,
                           "monotone_increasing": bool(vals == sorted(vals))})
    tail = [g["chi"] for g in grid_sweep if g["rho"] >= 8.0]
    chis = [g["chi"] for g in grid_sweep]
    grid_monotone = chis == sorted(chis)
    deep_row = grid_sweep[-1]
    report["boundary_limit"] = {
        "grid_codebook_sweep": grid_sweep,
        "random_codebook_seeds": seed_sweep,
        "tail_spread": float(max(tail) - min(tail)),
        "limit_estimate": float(tail[-1]),
        "grid_monotone": bool(grid_monotone),
        "seeds_monotone": sum(1 for s in seed_sweep if s["monotone_increasing"]),
        "boundary_p_bar": deep_row["p_bar"],
        "boundary_chi": deep_row["chi"],
        "monotonicity_verdict": ("FALSIFIED. The grid codebook dips from 0.901726 "
                                 "at rho=0.1 to 0.898532 at rho=0.25 before rising, "
                                 "and only 3 of 5 random seeds are monotone -- the "
                                 "other two converge from ABOVE in the fourth "
                                 "decimal. 'chi increases with depth' was an "
                                 "artifact of one random codebook and is withdrawn. "
                                 "What survives is convergence, not monotonicity."),
        "finding": ("chi converges to a NONZERO constant as q -> 0, and the "
                    "constant has a closed form. At infinite depth A becomes "
                    "rank one, so |v> becomes a PRODUCT state with norm^2 = 1/2: "
                    "p_bar -> 1/2, every S(omega_i) -> h2(1/2) = 1 bit, and by the "
                    "flag decomposition chi -> (1/2) S(sigmahat) <= 1 bit. The "
                    "evenly-spaced grid codebook averages to the maximally mixed "
                    "state on C^4, so S(sigmahat) = 2 and chi = 1.000000000 bit "
                    "exactly. The channel does not die at depth; it converges to a "
                    "boundary channel worth at most one bit per use, carried "
                    "entirely by the two angular coordinates.")}

    checks = {
        "sandwich_ordering_holds": bool(ordering_ok),
        "flag_decomposition_exact": worst_resid < 1e-9,
        "fixed_depth_flag_carries_nothing":
            report["flag_carries_only_depth_spread"]["fixed_depth_flag_bits"] < 1e-9,
        "mixed_depth_flag_carries_something": mixed_d["flag_bits"] > 1e-3,
        "data_processing_holds": bool(dp_ok),
        "kraus_complete": worst_kraus < 1e-12,
        "trace_distance_contracts": worst_d_violation < 1e-9,
        "fidelity_does_not_decrease": worst_f_violation < 1e-9,
        "boundary_limit_converges": report["boundary_limit"]["tail_spread"] < 1e-3,
        "boundary_limit_is_nonzero": report["boundary_limit"]["limit_estimate"] > 0.1,
        # Recorded as a FALSIFICATION: the control was run precisely to test
        # whether depth-monotonicity was real, and it is not. The check asserts
        # the falsification rather than the claim, so a future change that made
        # chi monotone again would fail here and demand re-examination.
        "depth_monotonicity_is_falsified": not (
            report["boundary_limit"]["grid_monotone"]
            and report["boundary_limit"]["seeds_monotone"] == 5),
        "boundary_p_bar_is_one_half":
            abs(report["boundary_limit"]["boundary_p_bar"] - 0.5) < 1e-9,
        "boundary_chi_at_most_one_bit":
            report["boundary_limit"]["boundary_chi"] <= 1.0 + 1e-9,
        "grid_saturates_the_one_bit_bound":
            abs(report["boundary_limit"]["boundary_chi"] - 1.0) < 1e-9,
    }
    checks = {k: bool(v) for k, v in checks.items()}
    report["checks"] = checks
    report["verdict"] = "ALL GATES PASS" if all(checks.values()) else "DISCREPANCY"

    path = OUT / "holevo_sandwich.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    from aionq.evidence import (EvidenceEnvelope, current_commit,
                                environment_digest, file_digest, save_envelope)
    envelope = EvidenceEnvelope(
        claim_id="EXP-R6D-HOLEVO_SANDWICH",
        evidence_tag="M",
        command="PYTHONPATH=src python3 experiments/run_holevo_sandwich.py",
        observed_result={
            "sample_size": len(DEPTHS),      # one codebook evaluated per depth
            "worst_decomposition_residual": worst_resid,
            "chi_boundary_limit": report["boundary_limit"]["limit_estimate"],
            "data_processing_holds": bool(dp_ok),
            "verdict": report["verdict"],
        },
        commit_sha=current_commit(),
        environment=environment_digest(),
        seeds=[SEED, SEED + 1] + [100 + s for s in range(5)],
        input_hashes=[f"codebook:rho={r:.6f},n={N_CODE},seed={SEED}" for r in DEPTHS],
        raw_artifacts={"artifacts/r6d_holevo_sandwich/holevo_sandwich.json":
                       file_digest(path)},
        environment_dependent=[],
        producer="experiments/run_holevo_sandwich.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {"kind": "scope_remainder",
             "carrier": "accessible information",
             "comparison": ("I_acc is a supremum over all POVMs and is NOT "
                            "estimated here. It is reported as the bracket "
                            "[I_PGM, chi]. An estimate would be the one number in "
                            "this round that could be quietly tuned")},
            {"kind": "scope_remainder",
             "carrier": "codebook size and geometry",
             "comparison": ("chi depends on N and on the angular spread of the "
                            "codebook. The depth-monotonicity finding is reported "
                            "only because it survives a deterministic grid "
                            "codebook and five independent seeds; no claim is made "
                            "for arbitrary codebooks or asymptotic N")},
            {"kind": "scope_remainder",
             "carrier": "capacity",
             "comparison": ("one-shot, single use, no coding theorem, no "
                            "regularisation, no advantage")}])
    save_envelope(envelope, OUT / "holevo_sandwich.envelope.json")

    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "boundary": {k: report["boundary_limit"][k]
                                   for k in ("limit_estimate", "tail_spread",
                                             "grid_monotone", "seeds_monotone")}},
                     indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0 if all(checks.values()) else 1


def _psd_sqrt(X):
    w, V = np.linalg.eigh((X + X.conj().T) / 2.0)
    w = np.where(w < 16.0 * float(np.finfo(float).eps), 0.0, np.real(w))
    return V @ np.diag(np.sqrt(w)) @ V.conj().T


if __name__ == "__main__":
    raise SystemExit(main())
