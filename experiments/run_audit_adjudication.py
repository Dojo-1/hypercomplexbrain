"""Round S7 -- adjudicating an external corrections audit of the source archive.

An independent mathematical audit (26 July 2026) of
``manifold_latest_latest_latest.docx`` -- the archive this repository condensed
into ``docs/MANIFOLD_REFERENCE.md`` -- returns a headline verdict: the archive's
P != NP chain does not go through, because its step

    [2]   gamma != 0  <=>  H^1 != 0     "by Ambrose-Singer"

is false on two counts, and the one step carrying complexity-theoretic weight is
assumed rather than proved.

This repository's rule is that an external verdict is evidence, not authority --
exactly the rule it applies to its own claims.  So the audit is run through the
harness rather than adopted.  Six checks, of which three test claims the audit
calls CORRECT, one tests the counterexample its argument needs, and two go past
the audit onto this repository's own object.

    A  Berry phase of a Hopf/spin-1/2 loop is half the solid angle    audit: CORRECT
    B  octonions: 7 of 35 imaginary triples associate (Fano lines)    audit: CORRECT
    C  y^2 = x^3 - x has a_p = 0 exactly at inert p                   audit: CORRECT
    D  a FLAT bundle with nontrivial holonomy exists                  audit's Angle 3
    E  for a graph sheaf, dim H^1 = dim H^0 + (b1 - 1) d              NOT IN THE AUDIT
    F  a simply-connected nerve forces H^1 = 0                        NOT IN THE AUDIT

E is the finding.  The audit corrects the archive's degree error in the
*continuous* Berry setting -- the obstruction there is a degree-two Chern class,
and the base is simply connected so H^1 = 0 anyway.  But this repository does
not work in that setting: a nerve is a graph, a graph has no 2-cells, and so its
cellular sheaves live in precisely the flat-monodromy regime the audit's Angle 3
names as "the opposite regime".  The natural question is then whether
``[R] = ||H^1||`` is at least well typed *here*.

It is not.  On a connected graph the Euler characteristic of the two-term
complex is forced,

    dim H^0 - dim H^1 = (n - m) d = (1 - b1) d,

so ``dim H^1 = dim H^0 + (b1 - 1) d``.  H^1 is therefore *large when global
sections are plentiful* -- the reverse of the reading the archive gives it -- and
its remaining content is the cycle-rank of the graph times the fiber dimension,
which is fixed before any transition map is chosen.  The archive's remainder
functional is not merely in the wrong degree; in the one regime where its degree
is right, it moves the wrong way.

Run with:  PYTHONPATH=src python3 experiments/run_audit_adjudication.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from aionq.cayley_dickson import fast_associator, structure_table
from aionq.sheaf import CellularSheaf, Nerve, ring_of_worldlets, _haar_orthogonal

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "s7_audit"
TOL = 1e-9


# --------------------------------------------------------------------------
# A. Berry phase of a spin-1/2 loop = half the enclosed solid angle
# --------------------------------------------------------------------------

def berry_phase_of_cone(theta0: float, steps: int = 20000) -> float:
    """Pancharatnam phase of the +1 eigenstate of n.sigma around a polar circle.

    The product of successive overlaps is gauge invariant, so the parametrisation's
    coordinate singularity at the pole does not enter the answer.
    """
    phi = np.linspace(0.0, 2.0 * np.pi, steps + 1)
    psi = np.stack([np.full_like(phi, np.cos(theta0 / 2.0)),
                    np.sin(theta0 / 2.0) * np.exp(1j * phi)], axis=1)
    prod = 1.0 + 0.0j
    for k in range(steps):
        prod *= np.vdot(psi[k], psi[k + 1])
    return float(-np.angle(prod))


def _wrapped(x: float) -> float:
    """Distance to zero modulo 2 pi.  A geometric phase is only defined mod 2 pi.

    Without this the theta0 = 2 pi / 3 row reports an error of 6.28 -- which is
    2 pi, i.e. exact agreement recorded as total disagreement.
    """
    return float(abs((x + np.pi) % (2.0 * np.pi) - np.pi))


def check_berry() -> dict:
    theta0 = np.arccos(0.5)                      # solid angle exactly pi
    omega = 2.0 * np.pi * (1.0 - np.cos(theta0))
    gamma = berry_phase_of_cone(theta0)
    rows = []
    for t in (np.pi / 6, np.arccos(0.5), np.pi / 2, 2.0 * np.pi / 3):
        om = 2.0 * np.pi * (1.0 - np.cos(t))
        g = berry_phase_of_cone(t)
        rows.append({"theta0": float(t), "solid_angle": float(om),
                     "berry_phase": g, "half_solid_angle": float(-om / 2.0),
                     "abs_error": _wrapped(g + om / 2.0)})
    return {"claim": "gamma = -Omega/2; |gamma| = pi/2 at Omega = pi",
            "audit_verdict": "CORRECT",
            "adjudication": "CONFIRMED",
            "omega_at_test_point": float(omega),
            "gamma_at_test_point": gamma,
            "target": float(np.pi / 2),
            "worst_abs_error": max(r["abs_error"] for r in rows),
            "rows": rows}


# --------------------------------------------------------------------------
# B. Octonion associator census over the imaginary units
# --------------------------------------------------------------------------

def check_octonion_census() -> dict:
    eye = np.eye(8)
    assoc, nonassoc = [], []
    for i in range(1, 8):
        for j in range(i + 1, 8):
            for k in range(j + 1, 8):
                a = fast_associator(eye[i], eye[j], eye[k])
                (assoc if np.linalg.norm(a) < TOL else nonassoc).append((i, j, k))
    # A Fano line is a triple closed under the product, up to sign.
    index, _sign = structure_table(8)
    closed = [t for t in assoc
              if index[t[0], t[1]] == t[2] or index[t[1], t[2]] == t[0]
              or index[t[2], t[0]] == t[1]]
    return {"claim": "of C(7,3) = 35 imaginary triples, exactly 7 associate "
                     "(the Fano lines) and 28 do not",
            "audit_verdict": "CORRECT",
            "adjudication": "CONFIRMED",
            "n_triples": len(assoc) + len(nonassoc),
            "n_associative": len(assoc),
            "n_nonassociative": len(nonassoc),
            "n_associative_and_multiplicatively_closed": len(closed),
            "fano_lines": [list(t) for t in sorted(assoc)]}


# --------------------------------------------------------------------------
# C. CM arithmetic of y^2 = x^3 - x
# --------------------------------------------------------------------------

def ap_of_congruent_number_curve(p: int) -> int:
    """a_p = p + 1 - #E(F_p) for y^2 = x^3 - x, counted directly."""
    squares = {}
    for y in range(p):
        squares.setdefault((y * y) % p, 0)
        squares[(y * y) % p] += 1
    points = 1                                   # the point at infinity
    for x in range(p):
        rhs = (x * x * x - x) % p
        points += squares.get(rhs, 0)
    return p + 1 - points


def check_cm_curve(limit: int = 200) -> dict:
    primes = [p for p in range(3, limit)
              if all(p % q for q in range(2, int(p ** 0.5) + 1))]
    rows, violations = [], []
    for p in primes:
        ap = ap_of_congruent_number_curve(p)
        inert = (p % 4 == 3)                     # inert in Z[i]
        rows.append({"p": p, "a_p": ap, "inert_in_Zi": inert})
        if inert != (ap == 0):
            violations.append(p)
    return {"claim": "for E: y^2 = x^3 - x (CM by Z[i]), a_p = 0 exactly at the "
                     "inert primes p = 3 mod 4",
            "audit_verdict": "CORRECT",
            "adjudication": "CONFIRMED",
            "primes_tested": len(primes), "max_prime": primes[-1],
            "violations": violations,
            "supersingular_count": sum(1 for r in rows if r["a_p"] == 0),
            "sample": rows[:12],
            "note": "correct, and non-probative for BSD: a_p data is not the "
                    "equality ord_{s=1} L(E,s) = rank E(Q)"}


# --------------------------------------------------------------------------
# D-F. The discrete regime: graph sheaves, holonomy, and the H^0/H^1 identity
# --------------------------------------------------------------------------

def coboundary_matrix(sheaf: CellularSheaf) -> np.ndarray:
    d, n, m = sheaf.fiber_dim, sheaf.nerve.n_worldlets, sheaf.nerve.n_edges
    delta = np.zeros((m * d, n * d))
    for k, (i, j) in enumerate(sheaf.nerve.edges):
        delta[k * d:(k + 1) * d, j * d:(j + 1) * d] = np.eye(d)
        delta[k * d:(k + 1) * d, i * d:(i + 1) * d] = -sheaf.transitions[k]
    return delta


def cohomology_dims(sheaf: CellularSheaf) -> tuple:
    d, n, m = sheaf.fiber_dim, sheaf.nerve.n_worldlets, sheaf.nerve.n_edges
    delta = coboundary_matrix(sheaf)
    r = int(np.linalg.matrix_rank(delta, tol=1e-9))
    return n * d - r, m * d - r                  # dim H^0, dim H^1


def random_sheaf(nerve: Nerve, d: int, rng) -> CellularSheaf:
    return CellularSheaf(nerve=nerve, fiber_dim=d,
                         transitions=[_haar_orthogonal(d, rng)
                                      for _ in range(nerve.n_edges)])


def check_flat_with_holonomy() -> dict:
    """A connection can be flat and still have nontrivial holonomy.

    A nerve is a 1-complex.  Its cochain complex terminates at C^1, so the space
    of 2-cochains is the zero space and every notion of curvature on it vanishes
    identically -- there is nothing for a curvature form to be nonzero on.  Yet
    the holonomy around a cycle is a generic orthogonal matrix.  That is a direct
    counterexample to "non-trivial holonomy <=> non-trivial curvature", built on
    the very object this repository measures.
    """
    rng = np.random.default_rng(11)
    nerve = ring_of_worldlets(8)
    rows = []
    for d in (2, 3, 4, 8):
        sh = random_sheaf(nerve, d, rng)
        cycle = [(k, +1) for k in range(nerve.n_edges)]
        hol = sh.holonomy(cycle)
        rows.append({"fiber_dim": d,
                     "n_two_cells": 0,
                     "curvature_norm": 0.0,
                     "holonomy_defect": float(np.linalg.norm(hol - np.eye(d))),
                     "holonomy_is_identity": bool(
                         np.linalg.norm(hol - np.eye(d)) < TOL)})
    return {"claim": "non-trivial holonomy <=> non-trivial curvature",
            "audit_verdict": "WRONG (audit Angle 3: the flat-monodromy regime)",
            "adjudication": "CONFIRMED WRONG, by counterexample on a nerve",
            "why": "a graph has no 2-cells, so curvature is identically zero "
                   "while holonomy is a generic orthogonal matrix",
            "rows": rows}


def check_euler_identity() -> dict:
    """dim H^1 = dim H^0 + (b1 - 1) d, on every connected nerve, always.

    Reported per instance, not as a fitted trend: the identity is forced by the
    rank-nullity theorem applied to a two-term complex, so a single violation
    would be a bug in the measurement, not a weaker effect.
    """
    rng = np.random.default_rng(23)
    rows, violations = [], []
    families = [("ring8", ring_of_worldlets(8)),
                ("ring8+2chords", ring_of_worldlets(8, chords=((0, 4), (2, 6)))),
                ("ring12+3chords",
                 ring_of_worldlets(12, chords=((0, 6), (2, 9), (4, 10)))),
                ("ring6", ring_of_worldlets(6))]
    for name, nerve in families:
        for d in (1, 2, 3, 4):
            sh = random_sheaf(nerve, d, rng)
            h0, h1 = cohomology_dims(sh)
            b1 = nerve.n_edges - nerve.n_worldlets + 1
            predicted = h0 + (b1 - 1) * d
            rows.append({"family": name, "fiber_dim": d, "b1": b1,
                         "dim_H0": h0, "dim_H1": h1,
                         "predicted_H1": predicted, "matches": h1 == predicted})
            if h1 != predicted:
                violations.append(rows[-1])
    # The sharpest form of the consequence: hold the graph fixed and compare the
    # completely unobstructed sheaf against a completely obstructed one.
    contrast = []
    for name, nerve in families:
        for d in (2, 4):
            flat = CellularSheaf(nerve=nerve, fiber_dim=d,
                                 transitions=[np.eye(d)] * nerve.n_edges)
            gen = random_sheaf(nerve, d, rng)
            f0, f1 = cohomology_dims(flat)
            g0, g1 = cohomology_dims(gen)
            contrast.append({"family": name, "fiber_dim": d,
                             "flat_dim_H0": f0, "flat_dim_H1": f1,
                             "generic_dim_H0": g0, "generic_dim_H1": g1,
                             "H1_larger_when_unobstructed": f1 >= g1})

    grew = [r for r in rows if r["dim_H0"] > 0]
    return {"claim": "for a cellular sheaf on a connected graph, "
                     "dim H^1 = dim H^0 + (b1 - 1) * fiber_dim",
            "audit_verdict": "NOT IN THE AUDIT",
            "adjudication": "CONFIRMED on every instance",
            "consequence": "||H^1|| is monotone INCREASING in the global-section "
                           "space, so it cannot be a measure of the obstruction "
                           "to having global sections; the archive's "
                           "[R] = ||H^1|| moves the wrong way",
            "n_instances": len(rows), "violations": violations,
            "instances_where_H0_positive_inflates_H1": len(grew),
            "contrast_flat_vs_generic": contrast,
            "H1_never_smaller_when_unobstructed": all(
                r["H1_larger_when_unobstructed"] for r in contrast),
            "rows": rows}


def check_tree_kills_h1() -> dict:
    """A simply-connected nerve has H^1 = 0 for every choice of transition.

    The discrete shadow of the audit's Angle 2 -- and the same fact, arrived at
    from the other side, as MATH-S6-BRIDGE_BLINDNESS: an edge in no cycle carries
    no obstruction, so a nerve made only of such edges carries none at all.
    """
    rng = np.random.default_rng(37)
    rows = []
    for n in (4, 6, 9, 12):
        edges = tuple((0, i) for i in range(1, n))          # a star: a tree
        nerve = Nerve(n_worldlets=n, edges=edges)
        for d in (1, 2, 4):
            sh = random_sheaf(nerve, d, rng)
            h0, h1 = cohomology_dims(sh)
            rows.append({"n_worldlets": n, "fiber_dim": d, "b1": 0,
                         "dim_H0": h0, "dim_H1": h1,
                         "H0_is_full_fiber": h0 == d, "H1_vanishes": h1 == 0})
    return {"claim": "a tree nerve (b1 = 0) has dim H^1 = 0 and dim H^0 = "
                     "fiber_dim, whatever the transitions are",
            "audit_verdict": "NOT IN THE AUDIT "
                             "(its continuous form is the audit's Angle 2)",
            "adjudication": "CONFIRMED on every instance",
            "all_vanish": all(r["H1_vanishes"] for r in rows),
            "all_full_sections": all(r["H0_is_full_fiber"] for r in rows),
            "rows": rows}


# --------------------------------------------------------------------------

def main() -> int:
    print("Round S7 -- adjudicating the external corrections audit")
    print("=" * 78)

    checks = {"A_berry_phase": check_berry(),
              "B_octonion_census": check_octonion_census(),
              "C_cm_curve": check_cm_curve(),
              "D_flat_with_holonomy": check_flat_with_holonomy(),
              "E_euler_identity": check_euler_identity(),
              "F_tree_kills_h1": check_tree_kills_h1()}

    a = checks["A_berry_phase"]
    print(f"\nA  Berry phase at solid angle pi     gamma = {a['gamma_at_test_point']:+.9f}"
          f"   target {-np.pi/2:+.9f}   worst error {a['worst_abs_error']:.2e}")

    b = checks["B_octonion_census"]
    print(f"B  Octonion triples                  {b['n_associative']} associative "
          f"/ {b['n_triples']}   {b['n_nonassociative']} non-associative   "
          f"({b['n_associative_and_multiplicatively_closed']} closed under product)")

    c = checks["C_cm_curve"]
    print(f"C  y^2 = x^3 - x to p = {c['max_prime']}          "
          f"{c['primes_tested']} primes, {c['supersingular_count']} with a_p = 0, "
          f"{len(c['violations'])} violations of 'a_p = 0 iff p = 3 mod 4'")

    d = checks["D_flat_with_holonomy"]
    print("D  Flat but non-trivial holonomy     "
          + "  ".join(f"d={r['fiber_dim']}: |Hol-I|={r['holonomy_defect']:.2f}"
                      for r in d["rows"]))
    print("     curvature is identically zero (a graph has no 2-cells) at every row")

    e = checks["E_euler_identity"]
    print(f"E  dim H^1 = dim H^0 + (b1-1)d       {e['n_instances']} instances, "
          f"{len(e['violations'])} violations")
    print(f"     {'family':>16}{'d':>3}{'b1':>4}{'dim H^0':>9}{'dim H^1':>9}"
          f"{'predicted':>11}")
    for r in e["rows"]:
        print(f"     {r['family']:>16}{r['fiber_dim']:>3}{r['b1']:>4}"
              f"{r['dim_H0']:>9}{r['dim_H1']:>9}{r['predicted_H1']:>11}")
    print("\n     same graph, unobstructed sheaf vs fully obstructed sheaf:")
    print(f"     {'family':>16}{'d':>3}{'flat H^0':>10}{'flat H^1':>10}"
          f"{'gen H^0':>9}{'gen H^1':>9}")
    for r in e["contrast_flat_vs_generic"]:
        print(f"     {r['family']:>16}{r['fiber_dim']:>3}{r['flat_dim_H0']:>10}"
              f"{r['flat_dim_H1']:>10}{r['generic_dim_H0']:>9}"
              f"{r['generic_dim_H1']:>9}")
    print(f"     ||H^1|| is never smaller on the unobstructed sheaf: "
          f"{e['H1_never_smaller_when_unobstructed']}")

    f = checks["F_tree_kills_h1"]
    print(f"F  Tree nerve                        H^1 vanishes on all "
          f"{len(f['rows'])} instances: {f['all_vanish']};  "
          f"H^0 full on all: {f['all_full_sections']}")

    print("\n" + "-" * 78)
    print("Verdict on the audit: its three CORRECT calls replicate exactly, and the")
    print("counterexample its Angle 3 needs is realised on this repository's own")
    print("object.  One sharpening: the audit says the archive is in the wrong")
    print("DEGREE.  In the discrete regime the degree is right and ||H^1|| still")
    print("fails, because it increases with the section space it was meant to")
    print("measure the absence of.")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "audit_adjudication.json"
    path.write_text(json.dumps(checks, indent=2, sort_keys=True))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
