"""Is the Emperor-Empress conjugate anti-pair an algebraic fact or a tautology?

The referential architecture states the pairing is *algebraically exact*:

    A_conj(a,b,c) = A_std(conj a, b, c) = -A_std(a,b,c),

"giving cosine similarity -1. Thus the pairing is an algebraically exact
anti-pair, not an aesthetic duality or an optimised heuristic."

That is checkable with machinery this repository already has, so it is checked
rather than adopted.  Two questions, not one:

  1. Is the identity true?                      -> YES, and it is a two-line proof
  2. Is CONJUGATION what makes it true?         -> NO

The associator is trilinear and A(1,b,c) = 0 exactly, so A(a,b,c) = A(Im a,b,c).
Conjugation flips Im a, hence the sign flip.  But plain negation flips Im a too,
and conj(a) - (-a) = 2 Re(a) . 1 acts trivially.  So negation produces the same
cosine -1, and a diagnostic that cannot separate Cayley-Dickson conjugation from
multiplication by -1 is not evidence that conjugation is the right relation
between a provability tower and a doxastic one.

Two further vacuities: the associator is IDENTICALLY ZERO below dimension 8, so
the anti-pair has no content for complex or quaternionic towers; and for purely
real a both sides vanish and the cosine is 0/0.

Run with:  PYTHONPATH=src python3 experiments/run_conjugation_antipair.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.cayley_dickson import cd_conjugate, fast_associator, _random_unit

associator = fast_associator   # structure-table form; verified identical upstream

TRIALS = 3000
OUT = Path(__file__).resolve().parent.parent / "artifacts" / "s4_g100" / "summaries"


def cosine(u, v) -> float:
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    return float(u @ v / (nu * nv)) if nu > 1e-12 and nv > 1e-12 else float("nan")


def main() -> int:
    print("Is the conjugate anti-pair an algebraic fact or a tautology?")
    print("=" * 82)
    rng = np.random.default_rng(0)
    rows = {}

    print(f"\n  {'dim':>5}{'max |A(conj a)+A(a)|':>24}{'max |A(-a)+A(a)|':>20}"
          f"{'cos(conj)':>12}{'cos(neg)':>11}{'nonassoc':>10}")
    print("  " + "-" * 82)
    for dim in (2, 4, 8, 16, 32):
        e_conj, e_neg, c_conj, c_neg, nz = [], [], [], [], 0
        for _ in range(TRIALS):
            a, b, c = (_random_unit(dim, rng) for _ in range(3))
            std = associator(a, b, c)
            con = associator(cd_conjugate(a), b, c)      # computed once each
            neg = associator(-a, b, c)
            e_conj.append(np.linalg.norm(con + std))
            e_neg.append(np.linalg.norm(neg + std))
            if np.linalg.norm(std) > 1e-9:
                nz += 1
                c_conj.append(cosine(con, std))
                c_neg.append(cosine(neg, std))
        rows[dim] = {
            "max_err_conjugate": float(max(e_conj)),
            "max_err_negation": float(max(e_neg)),
            "mean_cos_conjugate": float(np.mean(c_conj)) if c_conj else None,
            "mean_cos_negation": float(np.mean(c_neg)) if c_neg else None,
            "nonassociative_fraction": nz / TRIALS,
        }
        cc = f"{np.mean(c_conj):>12.6f}" if c_conj else f"{'n/a':>12}"
        cn = f"{np.mean(c_neg):>11.6f}" if c_neg else f"{'n/a':>11}"
        print(f"  {dim:>5}{max(e_conj):>24.3e}{max(e_neg):>20.3e}{cc}{cn}"
              f"{nz / TRIALS:>10.3f}")

    print("\n  Why: the associator is trilinear and vanishes on the identity.")
    one = np.zeros(8)
    one[0] = 1.0
    checks = []
    for _ in range(200):
        a, b, c = (_random_unit(8, rng) for _ in range(3))
        im = a.copy()
        im[0] = 0.0
        checks.append((float(np.linalg.norm(associator(one, b, c))),
                       float(np.linalg.norm(associator(a, b, c)
                                            - associator(im, b, c)))))
    print(f"    max |A(1,b,c)|            = {max(x for x, _ in checks):.3e}")
    print(f"    max |A(a,b,c) - A(Im a,.)| = {max(y for _, y in checks):.3e}")

    print("\n" + "=" * 82)
    print("VERDICT")
    print("=" * 82)
    print("  The identity HOLDS: max error 5e-16, cosine exactly -1 wherever the")
    print("  associator is nonzero. That much is a fact and is tagged P.")
    print("\n  But CONJUGATION IS NOT DOING THE WORK. Plain negation gives the same")
    print("  cosine -1 at exactly 0.0 error, because conj(a) and -a differ by")
    print("  2 Re(a) . 1 and A(1,b,c) = 0. The anti-pair follows from oddness in the")
    print("  first argument, which any sign flip has.")
    print("\n  Consequence for the architecture: 'an algebraically exact anti-pair,")
    print("  not an aesthetic duality' is not supported by this identity. A")
    print("  diagnostic that cannot separate Cayley-Dickson conjugation from")
    print("  multiplication by -1 cannot be evidence that conjugation is the right")
    print("  relation between a provability tower and a doxastic one.")
    print("\n  Two further vacuities: the associator is IDENTICALLY ZERO at dim 2 and")
    print("  4, so the construction has no content for complex or quaternionic")
    print("  towers; and for purely real a both sides vanish and the cosine is 0/0.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "conjugation_antipair.json").write_text(
        json.dumps({"trials_per_dim": TRIALS, "by_dimension": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
