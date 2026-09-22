"""Exercise a frozen decision procedure before the round it decides.

Four consecutive rounds were decided by their own frozen rules rather than by
what they measured, and in every case the defect was mechanical and visible
without any measurement at all:

    R1S   the verdict REGIONS OVERLAPPED.  ``C < 2`` for LOW and
          ``C > 0.7*sqrt(N)`` for HIGH are ordered the wrong way for
          ``N < 8.163``, so the band between them is not a gap but an OVERLAP.
          Eight of fifteen measured cells satisfied BOTH.
    R1X   a PARAMETER WAS LEFT FREE.  Two thresholds were frozen and the
          protocol then wrote "fixed step budget" without fixing it; 300 and
          900 steps answered the same preregistered question in opposite
          directions.
    R1Z   a VERDICT WAS UNREACHABLE.  ``BOUNDED`` required
          ``largest <= 2 * max(smallest, 1e-12)``, a ratio test on counts, and
          a genuinely bounded family sits at ZERO for small registers -- so the
          clause reduced to ``largest <= 2e-12`` and was False for exactly the
          families it existed to certify.

THIS MODULE'S SCOPE, STATED BEFORE ITS CLAIM IS OVERSOLD.  The recommendation
that produced it said these checks "would have caught R1S, R1X, R1Y and R1Z".
That was wrong and is corrected here: those are THREE defect classes, not one,
and R1Y is not among them at all -- R1Y amended R1X's causal diagnosis and
froze nothing that failed.  Two checks cover three rounds:

    verdict_regions_are_disjoint      R1S
    every_verdict_has_a_witness       R1Z
    frozen_parameters_cover_the_knobs R1X

Overstating a tool's reach one turn after auditing that exact move elsewhere is
recorded in the corrections ledger rather than quietly narrowed here.

NONE OF THIS IS A THEOREM ABOUT CRITERIA.  A criterion can pass all three and
still be the wrong criterion -- R1Z's zero count was reachable, disjoint and
fully parameterised, and was still the wrong observable, because Araki's
condition is about occupation and needs no degeneracy precondition.  These
checks remove three failure modes that have actually occurred here.  They do
not certify a rule.
"""

from __future__ import annotations

import inspect
import itertools

__all__ = [
    "every_verdict_has_a_witness",
    "verdict_regions_are_disjoint",
    "frozen_parameters_cover_the_knobs",
    "exercise",
]


def every_verdict_has_a_witness(verdict_fn, witnesses: dict,
                                declared_verdicts=None) -> dict:
    """Each verdict the rule can return must be produced by some input.

    ``witnesses`` maps a verdict name to a synthetic input the round author
    believes produces it.  The check runs them.  A verdict whose own intended
    witness does not reach it is UNREACHABLE, which is R1Z's defect: a rule can
    name a verdict it will never return, and nothing notices until the round it
    was written for comes back with the wrong answer.

    The witnesses must be supplied by the author rather than searched for.  A
    search would find whatever input happens to trigger the branch, which
    proves the branch is live and not that it is live for the reason the round
    intends.
    """
    declared = None if declared_verdicts is None else {
        str(name) for name in declared_verdicts}
    supplied = {str(name) for name in witnesses}
    declaration_matches = declared is not None and supplied == declared
    rows = []
    for name, witness in witnesses.items():
        try:
            produced = verdict_fn(witness)
            reached = produced == name
            reason = "" if reached else f"witness produced {produced!r}"
        except Exception as error:                       # a raising rule is a dead rule
            produced, reached, reason = None, False, f"{type(error).__name__}: {error}"
        rows.append({"verdict": name, "reached": reached,
                     "produced": produced, "reason": reason})

    unreachable = [row for row in rows if not row["reached"]]
    return {"verdicts": len(rows), "unreachable": unreachable,
            "declared_verdicts": None if declared is None else sorted(declared),
            "supplied_verdicts": sorted(supplied),
            "declaration_matches": declaration_matches,
            "all_reachable": declaration_matches and not unreachable,
            "rows": rows}


def verdict_regions_are_disjoint(predicates: dict, samples) -> dict:
    """No input may satisfy two verdicts at once.

    R1S froze ``C < 2`` and ``C > 0.7*sqrt(N)`` and described what lay between
    them as indeterminate.  For ``N < 8.163`` the thresholds are ordered the
    wrong way and there is no between -- there is an overlap, and a cell inside
    it satisfies both.  The implementation returned whichever was tested first,
    so the reported verdict depended on the order of two ``if`` statements.

    Takes the PREDICATES separately rather than the composed rule, because a
    rule that returns one value cannot exhibit its own ambiguity: the overlap is
    invisible from the outside and visible the moment the branches are asked
    independently.
    """
    collisions = []
    errors = []
    samples = list(samples)
    for sample in samples:
        satisfied = []
        for name, predicate in predicates.items():
            try:
                if predicate(sample):
                    satisfied.append(name)
            except Exception as error:
                errors.append({"sample": sample, "verdict": name,
                               "reason": f"{type(error).__name__}: {error}"})
        if len(satisfied) > 1:
            collisions.append({"sample": sample, "verdicts": sorted(satisfied)})

    uncovered = [s for s in samples
                 if not any(_safe(p, s) for p in predicates.values())]
    return {
        "samples": len(samples),
        "collisions": collisions,
        "disjoint": bool(samples) and bool(predicates) and not collisions,
        "uncovered": uncovered,
        "errors": errors,
        "exhaustive": bool(samples) and bool(predicates) and not uncovered
                      and not errors,
    }


def _safe(predicate, sample) -> bool:
    try:
        return bool(predicate(sample))
    except Exception:
        return False


def frozen_parameters_cover_the_knobs(entrypoint, frozen) -> dict:
    """Every tunable of the entry point must carry a value in the manifest.

    R1X froze two thresholds and wrote "fixed step budget" with no number.  A
    free parameter inside a frozen protocol is a threshold in disguise, and the
    two budgets that were eventually run answered the same preregistered
    question in opposite directions -- either reportable alone without breaking
    a single frozen clause.

    A keyword argument with a default IS a knob: it is a choice the author made
    and can silently remake.  The check is mechanical, on the signature, so it
    cannot be satisfied by prose.
    """
    signature = inspect.signature(entrypoint)
    knobs = [name for name, parameter in signature.parameters.items()
             if parameter.default is not inspect.Parameter.empty]
    named = {str(key) for key in frozen}
    missing = [knob for knob in knobs if knob not in named]
    return {
        "entrypoint": getattr(entrypoint, "__qualname__", repr(entrypoint)),
        "knobs": knobs,
        "frozen": sorted(named),
        "missing": missing,
        "all_frozen": not missing,
    }


def exercise(verdict_fn=None, witnesses=None, declared_verdicts=None,
             predicates=None, samples=None, entrypoint=None, frozen=None,
             required_checks=None) -> dict:
    """Run whichever of the three checks the round supplies material for.

    Fail closed unless ``required_checks`` explicitly declares the exact checks
    supplied by the caller. A non-applicable check is omitted deliberately, not
    silently; an omitted declaration, an empty exercise, an uncovered sample,
    a predicate exception, or a missing declared verdict prevents ``clean``.
    """
    known_checks = {"coverage", "disjointness", "parameters"}
    required = None if required_checks is None else {
        str(name) for name in required_checks}
    report: dict = {"skipped": [],
                    "required_checks": None if required is None
                    else sorted(required)}
    if verdict_fn is not None and witnesses:
        report["coverage"] = every_verdict_has_a_witness(
            verdict_fn, witnesses, declared_verdicts)
    else:
        report["skipped"].append("coverage")
    if predicates and samples is not None:
        report["disjointness"] = verdict_regions_are_disjoint(predicates, samples)
    else:
        report["skipped"].append("disjointness")
    if entrypoint is not None and frozen is not None:
        report["parameters"] = frozen_parameters_cover_the_knobs(entrypoint, frozen)
    else:
        report["skipped"].append("parameters")

    supplied = known_checks - set(report["skipped"])
    declaration_valid = (required is not None and required <= known_checks
                         and required == supplied)
    verdicts = [
        report.get("coverage", {}).get("all_reachable", False),
        (report.get("disjointness", {}).get("disjoint", False)
         and report.get("disjointness", {}).get("exhaustive", False)),
        report.get("parameters", {}).get("all_frozen", False),
    ]
    evaluated = [verdict for name, verdict in zip(
        ("coverage", "disjointness", "parameters"), verdicts)
        if name in supplied]
    report["declaration_valid"] = declaration_valid
    report["clean"] = declaration_valid and bool(evaluated) and all(evaluated)
    return report
