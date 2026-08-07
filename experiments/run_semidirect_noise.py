from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from aionq.projected_partition import (
    evaluate_partition,
    hidden_pairs,
    projected_state_direct,
    projection_weights,
)
from aionq.semidirect_noise import (
    apply_word,
    decode,
    generator,
    inverse,
    left_regular_permutation,
    multiply,
    noisy_word,
    permutation_disagreement,
    word_product,
)

PROFILES = ("ramp", "sinusoid", "burst")
SECRET = 1


def aligned_partition(secret: int):
    pairs = hidden_pairs(secret)
    return tuple(tuple(sorted(pairs[i] + pairs[i + 1])) for i in range(0, 8, 2))


def metric_vector(state, partition):
    m = evaluate_partition(state, partition, SECRET)
    return np.array([
        m.global_forbidden_mass,
        m.sector_forbidden_mass,
        m.offdiag_forbidden_real,
        m.closure_defect,
    ], dtype=float)


def run():
    e = (0, 0)
    a, b = generator("a"), generator("b")
    assert multiply(multiply(b, a, nonabelian=True), inverse(b, nonabelian=True), nonabelian=True) == inverse(a, nonabelian=True)
    assert word_product(("a", "b", "A", "B"), nonabelian=False) == e
    commutator = word_product(("a", "b", "A", "B"), nonabelian=True)
    assert commutator != e
    for nonabelian in (False, True):
        for x in range(16):
            g = decode(x)
            assert multiply(g, inverse(g, nonabelian=nonabelian), nonabelian=nonabelian) == e
            assert sorted(left_regular_permutation(g, nonabelian=nonabelian).tolist()) == list(range(16))

    partition = aligned_partition(SECRET)
    rows = []
    for projection_seed in range(8):
        state = projected_state_direct(SECRET, projection_weights(projection_seed))
        baseline = metric_vector(state, partition)
        assert np.max(np.abs(baseline)) <= 1e-12
        for noise_seed in range(8):
            for profile in PROFILES:
                word = noisy_word(noise_seed, profile, 24)
                reversed_word = tuple(reversed(word))
                for nonabelian, name in ((False, "abelian"), (True, "nonabelian")):
                    forward = apply_word(state, word, nonabelian=nonabelian)
                    reverse = apply_word(state, reversed_word, nonabelian=nonabelian)
                    mf = metric_vector(forward, partition)
                    mr = metric_vector(reverse, partition)
                    pf = left_regular_permutation(word_product(word, nonabelian=nonabelian), nonabelian=nonabelian)
                    pr = left_regular_permutation(word_product(reversed_word, nonabelian=nonabelian), nonabelian=nonabelian)
                    rows.append({
                        "projection_seed": projection_seed,
                        "noise_seed": noise_seed,
                        "profile": profile,
                        "group": name,
                        "word": "".join(word),
                        "permutation_disagreement": permutation_disagreement(pf, pr),
                        "global_defect": float(abs(mf[0] - mr[0])),
                        "sector_defect": float(abs(mf[1] - mr[1])),
                        "offdiag_defect": float(abs(mf[2] - mr[2])),
                        "max_closure": float(max(mf[3], mr[3])),
                        "forward": mf.tolist(),
                        "reverse": mr.tolist(),
                    })

    aggregate = {}
    for group in ("abelian", "nonabelian"):
        rr = [r for r in rows if r["group"] == group]
        aggregate[group] = {}
        for key in ("permutation_disagreement", "global_defect", "sector_defect", "offdiag_defect"):
            values = np.array([r[key] for r in rr], dtype=float)
            aggregate[group][key] = {
                "median": float(np.median(values)),
                "max": float(np.max(values)),
                "positive_frac": float(np.mean(values > 1e-8)),
            }
        aggregate[group]["max_closure"] = float(max(r["max_closure"] for r in rr))

    nonab = [r for r in rows if r["group"] == "nonabelian"]
    gates = {
        "nonabelian_perm_diff_frac": float(np.mean([r["permutation_disagreement"] > 0 for r in nonab])),
        "nonabelian_any_metric_diff_frac": float(np.mean([
            max(r["global_defect"], r["sector_defect"], r["offdiag_defect"]) > 1e-8
            for r in nonab
        ])),
        "commutator_element": list(commutator),
    }

    result = {
        "schema": "r1u.raw.v1",
        "round": "QSigma-R1U",
        "rows": rows,
        "aggregate": aggregate,
        "gates": gates,
        "verdict": "KILLED" if (
            gates["nonabelian_perm_diff_frac"] < 0.75
            or gates["nonabelian_any_metric_diff_frac"] < 0.50
        ) else "PASSED",
    }
    out = Path("artifacts/r1u_semidir_noise/semidirect_noise.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"aggregate": aggregate, "gates": gates, "verdict": result["verdict"]}, indent=2))


if __name__ == "__main__":
    run()
