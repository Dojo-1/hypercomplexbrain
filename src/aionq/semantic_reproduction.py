"""Comparing two runs of the same protocol on two platforms, by meaning.

Round QSigma-R6k-W1.  The repository already has a comparison mechanism for a
second party's run: :func:`aionq.witness.apply_witness` hashes the artifacts both
sides declare and compares digests.  For R6k that mechanism cannot work in either
direction, and both failures are measured rather than argued:

1.  R6k marks its two output artifacts ``environment_dependent``, so
    ``apply_witness`` removes them.  What is left to compare is eleven TRACKED
    REPOSITORY FILES -- one runner, two manifests, six modules, two test files.
    A verifier reproduces every one of them by cloning.  The existing guard fires
    only when the comparable set is EMPTY, and this set is not empty, so a
    verifier could be recorded as having recomputed R6k while comparing nothing
    it computed.

2.  Conversely, if those outputs were left comparable, the comparison would fail
    by construction.  R6k's ``input_hashes``, ``query_digest``,
    ``template_digest``, ``confusion_digest`` and ``source_matrix_digest`` are
    SHA-256 of computed floating-point arrays.  A last-bit difference in any
    array -- exactly what a different BLAS on a different platform produces --
    changes the digest completely.  Digest equality asks whether two machines
    performed identical rounding, which is not the scientific question.

So this module compares the two results LEAF BY LEAF, under a tolerance frozen
before it was written, and it separates three populations that the digest
mechanism conflates:

    scientific leaves   floats and integers that carry a result       -> tolerance
    discrete leaves     verdicts, flags, counts, schema strings       -> exact
    identity leaves     digests of floating-point arrays              -> counted

The failure mode this module must avoid
---------------------------------------
Agreement reached vacuously.  A comparator that compares zero scientific leaves
and reports CONFIRMED has made exactly the error it was built to expose, one
level up.  So :func:`compare_results` reports ``scientific_leaves_compared`` and
:func:`reproduction_verdict` refuses CONFIRMED below a declared floor.  The
preregistration sets that floor at 4000 and requires a perturbation control: one
scientific float moved by 1e-9 must come back CONTRADICTED.
"""

from __future__ import annotations

import copy
import math
import re
from pathlib import Path

__all__ = [
    "DIGEST_PATH_PATTERN", "ENVIRONMENT_METADATA_LEAVES", "flatten", "leaf_kind",
    "compare_results", "reproduction_verdict", "perturb_leaf",
    "structural_checks", "compare_event_traces",
]

#: A leaf is an IDENTITY leaf if its path names a digest field or its value is a
#: sha256 string.  Both tests are applied; a field that looks like a digest by
#: either route is excluded from the scientific population and counted.
DIGEST_PATH_PATTERN = re.compile(
    r"(\.input_hashes\[\d+\]$|_digest$|_sha256$|\.sha256$)")

#: Closed by amendment W1-C1.  A library version recorded inside the resource
#: ledger is provenance FOR the compiler cost proxy, not an output OF it -- the
#: same kind of fact as the python and numpy versions ``environment_digest``
#: already records separately and expects to differ.  Demanding it match is
#: demanding that the second platform be the first one.
#:
#: The list is closed: the amendment forbids adding to it once a reproduction
#: artifact exists, and a test asserts its exact contents, so widening it is a
#: visible edit to a frozen set rather than a quiet exclusion.
ENVIRONMENT_METADATA_LEAVES = frozenset({
    ".resource_ledger.compiler_proxy.qiskit_version",
})


def flatten(obj, prefix: str = "") -> dict:
    """Every scalar leaf of a JSON document, keyed by its full path.

    Lists are indexed rather than sorted, so a reordered list is a mismatch. For
    an event trace or a retrieval grid, order is part of the claim.
    """
    out: dict = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.update(flatten(value, f"{prefix}.{key}"))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            out.update(flatten(value, f"{prefix}[{index}]"))
    else:
        out[prefix] = obj
    return out


def leaf_kind(path: str, value) -> str:
    """``scientific`` | ``discrete`` | ``identity`` | ``environment``.

    ``bool`` is checked before ``int`` deliberately: in Python ``True`` is an
    ``int``, and a verdict flag compared under a numeric tolerance would let a
    FAILED check pass as 0.0 within 1e-10 of False. That is the same class of
    error as serialising ``np.bool_`` with ``default=str`` and writing the string
    "True" for a failure.
    """
    if path in ENVIRONMENT_METADATA_LEAVES:
        return "environment"
    if DIGEST_PATH_PATTERN.search(path):
        return "identity"
    if isinstance(value, str):
        return "identity" if value.startswith("sha256:") else "discrete"
    if isinstance(value, bool) or value is None:
        return "discrete"
    if isinstance(value, (int, float)):
        return "scientific"
    return "discrete"


def compare_results(produced, reproduced, tolerance: float) -> dict:
    """Leaf-by-leaf comparison of two runs of one protocol.

    `produced` is the party of record's result; `reproduced` is this platform's.
    Keys present on one side only are reported separately and are NOT silently
    treated as agreement -- R6k's committed result carries 43 leaves that the
    library entry point does not emit, because its runner adds them, and a
    comparator that dropped them would be hiding the part it could not check.
    """
    left, right = flatten(produced), flatten(reproduced)
    shared = sorted(set(left) & set(right))

    scientific: list = []
    worst = {"delta": 0.0, "path": None}
    discrete_mismatches: list = []
    identity_mismatches: list = []
    environment_mismatches: list = []
    non_finite: list = []

    for path in shared:
        a, b = left[path], right[path]
        kind = leaf_kind(path, a)
        if leaf_kind(path, b) != kind:
            discrete_mismatches.append(
                {"path": path, "produced": repr(a)[:120],
                 "reproduced": repr(b)[:120], "note": "leaf kind changed"})
            continue
        if kind == "environment":
            if a != b:
                environment_mismatches.append(
                    {"path": path, "produced": a, "reproduced": b})
        elif kind == "identity":
            if a != b:
                identity_mismatches.append(path)
        elif kind == "discrete":
            if a != b:
                discrete_mismatches.append(
                    {"path": path, "produced": repr(a)[:120],
                     "reproduced": repr(b)[:120]})
        else:
            if not (math.isfinite(a) and math.isfinite(b)):
                non_finite.append(path)
                continue
            delta = abs(float(a) - float(b))
            scientific.append((path, delta))
            if delta > worst["delta"]:
                worst = {"delta": delta, "path": path}

    # Built inside the same loop that measured them. An earlier draft rebuilt
    # this list by re-scanning `shared` and zipping it against the deltas, which
    # desynchronises the moment any leaf takes the `continue` above -- the exact
    # off-by-one class that made kappa telescope over the wrong pairs in R6e.
    exceed = [path for path, delta in scientific if delta > tolerance]

    return {
        "tolerance": tolerance,
        "shared_leaves": len(shared),
        "only_in_produced": sorted(set(left) - set(right)),
        "only_in_reproduced": sorted(set(right) - set(left)),
        "scientific_leaves_compared": len(scientific),
        "worst_absolute_difference": worst["delta"],
        "worst_difference_path": worst["path"],
        "scientific_leaves_exceeding_tolerance": exceed,
        "discrete_mismatches": discrete_mismatches,
        "identity_leaves": sum(1 for p in shared
                               if leaf_kind(p, left[p]) == "identity"),
        "identity_mismatches": len(identity_mismatches),
        "identity_mismatch_paths": identity_mismatches[:20],
        "environment_mismatches": environment_mismatches,
        "non_finite_leaves": non_finite,
    }


def structural_checks(produced, reproduced) -> dict:
    """The things that must be exactly equal, checked by name rather than by scan.

    A tolerance comparison over 4000 leaves can drown a changed verdict in a sea
    of agreeing floats. These are pulled out and asserted individually so the
    load-bearing fields cannot pass by dilution.
    """
    def get(doc, *keys):
        cur = doc
        for key in keys:
            if not isinstance(cur, dict) or key not in cur:
                return None
            cur = cur[key]
        return cur

    pairs = {
        "schema": (get(produced, "schema"), get(reproduced, "schema")),
        "round": (get(produced, "round"), get(reproduced, "round")),
        "verdict": (get(produced, "decision", "verdict"),
                    get(reproduced, "decision", "verdict")),
        "ambient_dimension": (get(produced, "ambient_dimension"),
                              get(reproduced, "ambient_dimension")),
        "primary_cell_count": (get(produced, "primary_cell_count"),
                               get(reproduced, "primary_cell_count")),
        "codewords_per_depth": (get(produced, "codewords_per_depth"),
                                get(reproduced, "codewords_per_depth")),
        "depths": (get(produced, "depths"), get(reproduced, "depths")),
        "noise_strengths": (get(produced, "noise_strengths"),
                            get(reproduced, "noise_strengths")),
    }
    rows = {name: {"produced": a, "reproduced": b, "equal": a == b}
            for name, (a, b) in pairs.items()}
    return {"rows": rows, "all_equal": all(r["equal"] for r in rows.values())}


def compare_event_traces(produced_path, reproduced_path,
                         tolerance: float = 1e-10) -> dict:
    """Compare the traces by VALUE, row by row, not by field name.

    The first version compared ``[tuple(r.keys()) for r in rows]`` -- the field
    NAMES -- plus the ``sequence`` column, and nothing else.  ``action``, ``key``,
    ``shard`` and every value inside ``metadata`` were never looked at.  An
    external audit altered those semantic values and still obtained CONFIRMED,
    which is the whole class of defect this module was written to expose,
    committed inside the module itself.

    Every field is now compared with the same :func:`leaf_kind` machinery the
    result documents use, so ``state_digest`` -- a SHA-256 of a computed state --
    is classified IDENTITY and counted rather than demanded, while
    ``metadata.rho`` is scientific and compared under tolerance and ``action``,
    ``key`` and ``shard`` are discrete and must be exactly equal.
    """
    import json

    def rows(path):
        text = Path(path).read_text(encoding="utf-8").strip()
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    a, b = rows(produced_path), rows(reproduced_path)
    key_order_equal = ([tuple(r.keys()) for r in a] == [tuple(r.keys()) for r in b])
    seq_a = [r.get("sequence") for r in a]
    seq_b = [r.get("sequence") for r in b]

    value_mismatches: list = []
    identity_differences = 0
    compared = 0
    worst = {"delta": 0.0, "path": None}
    for index, (left_row, right_row) in enumerate(zip(a, b)):
        left, right = flatten(left_row), flatten(right_row)
        for path in sorted(set(left) | set(right)):
            if path not in left or path not in right:
                value_mismatches.append(
                    {"row": index, "path": path, "note": "field present on one side only"})
                continue
            x, y = left[path], right[path]
            kind = leaf_kind(path, x)
            if kind == "identity":
                identity_differences += (x != y)
                continue
            compared += 1
            if kind == "scientific" and leaf_kind(path, y) == "scientific":
                if not (math.isfinite(x) and math.isfinite(y)):
                    value_mismatches.append({"row": index, "path": path,
                                             "note": "non-finite"})
                    continue
                delta = abs(float(x) - float(y))
                if delta > worst["delta"]:
                    worst = {"delta": delta, "path": f"[{index}]{path}"}
                if delta > tolerance:
                    value_mismatches.append(
                        {"row": index, "path": path, "produced": x, "reproduced": y})
            elif x != y:
                value_mismatches.append(
                    {"row": index, "path": path, "produced": repr(x)[:80],
                     "reproduced": repr(y)[:80]})

    return {
        "produced_rows": len(a),
        "reproduced_rows": len(b),
        "row_count_equal": len(a) == len(b),
        "key_order_equal": key_order_equal,
        "sequence_equal": seq_a == seq_b,
        "sequences_contiguous": seq_b == list(range(len(seq_b))),
        "semantic_fields_compared": compared,
        "semantic_value_mismatches": value_mismatches[:20],
        "semantic_value_mismatch_count": len(value_mismatches),
        "identity_fields_differing": identity_differences,
        "worst_absolute_difference": worst["delta"],
        "worst_difference_path": worst["path"],
    }


def perturb_leaf(document, path: str, delta: float):
    """A deep copy with one scientific leaf moved by `delta`.

    The control this exists for was got wrong once already in this repository:
    an earlier tamper helper recursed into a dict COPY, mutated the copy, and so
    validated an untampered document -- which read as "the check is decorative"
    when the check was fine. This mutates the copy IN PLACE along the real path
    and a test asserts the returned document actually differs.
    """
    out = copy.deepcopy(document)
    tokens = [t for t in re.split(r"\.|(\[\d+\])", path) if t]
    cursor = out
    for token in tokens[:-1]:
        if token.startswith("["):
            cursor = cursor[int(token[1:-1])]
        else:
            cursor = cursor[token]
    last = tokens[-1]
    if last.startswith("["):
        index = int(last[1:-1])
        cursor[index] = cursor[index] + delta
    else:
        cursor[last] = cursor[last] + delta
    return out


#: Amendment W1-C2.  The floor is RELATIVE, because "not vacuous" is a statement
#: about the comparison and not about one pair of files: most of what is not a
#: digest must be a compared number.  The absolute value it replaced was guessed
#: from the total leaf count before a comparator existed that could tell the
#: populations apart, and was unreachable by construction.
MINIMUM_SCIENTIFIC_FRACTION = 0.75
MINIMUM_SCIENTIFIC_BACKSTOP = 1000


#: Every mismatch population :func:`compare_results` can produce.  The verdict
#: function asserts it has consulted all of them, so adding a population without
#: deciding what it means raises instead of defaulting to "agreement".
_MISMATCH_POPULATIONS = frozenset({
    "scientific_leaves_exceeding_tolerance",
    "discrete_mismatches",
    "non_finite_leaves",
    "identity_mismatches",
    "environment_mismatches",
    "only_in_produced",
    "only_in_reproduced",
})


def reproduction_verdict(comparison: dict, structural: dict, events: dict,
                         minimum_fraction: float = MINIMUM_SCIENTIFIC_FRACTION,
                         backstop: int = MINIMUM_SCIENTIFIC_BACKSTOP,
                         allowed_only_in_produced=None) -> dict:
    """CONFIRMED, CONTRADICTED, or VACUOUS.

    VACUOUS is a distinct outcome and not a flavour of failure. A comparison
    that agreed on nothing measurable has not disagreed; it has established
    nothing, and calling that CONFIRMED is the defect this whole round exists to
    avoid reproducing.

    FAIL CLOSED.  The first version of this consulted five of the seven mismatch
    populations :func:`compare_results` produces, and defaulted to agreement on
    the other two:

    * ``events["sequence_equal"]`` was never read, so a trace with the right row
      count and the right keys in the right ORDER but the wrong sequence numbers
      returned CONFIRMED.
    * ``only_in_reproduced`` was never read, so a reproduction emitting leaves
      the producer never had returned CONFIRMED, and ``only_in_produced`` was
      tolerated wholesale rather than checked against a declared allowance --
      which means a reproduction that silently stopped emitting a whole section
      would have agreed with the producer about the part it still emitted.

    Both were found by an external audit of the published branch, and both are
    the same defect: a comparison that says nothing about a population is not
    evidence that the population agrees.  `allowed_only_in_produced` must now be
    declared by the caller; anything outside it contradicts.
    """
    allowed = frozenset(allowed_only_in_produced or ())
    undeclared_produced = [p for p in comparison["only_in_produced"]
                           if p not in allowed]

    compared = comparison["scientific_leaves_compared"]
    comparable = comparison["shared_leaves"] - comparison["identity_leaves"]
    fraction = (compared / comparable) if comparable else 0.0
    enough = fraction >= minimum_fraction and compared >= backstop

    # Named, so that every population is visibly consulted rather than implied.
    reasons = {
        "scientific_leaves_exceeding_tolerance":
            bool(comparison["scientific_leaves_exceeding_tolerance"]),
        "discrete_mismatches": bool(comparison["discrete_mismatches"]),
        "non_finite_leaves": bool(comparison["non_finite_leaves"]),
        "structural_fields_differ": not structural["all_equal"],
        "event_row_count_differs": not events["row_count_equal"],
        "event_key_order_differs": not events["key_order_equal"],
        "event_sequence_differs": not events.get("sequence_equal", False),
        "event_sequences_not_contiguous": not events.get("sequences_contiguous", False),
        "event_semantic_values_differ":
            bool(events.get("semantic_value_mismatch_count", 1)),
        "no_event_field_was_compared":
            not events.get("semantic_fields_compared", 0),
        "leaves_only_in_reproduced": bool(comparison["only_in_reproduced"]),
        "undeclared_leaves_only_in_produced": bool(undeclared_produced),
    }
    # identity_mismatches and environment_mismatches are the two populations
    # the preregistration and its amendment EXCLUDE by name. Listing them here
    # is what makes that a decision rather than an omission.
    consulted = {"identity_mismatches", "environment_mismatches",
                 "only_in_produced", "only_in_reproduced",
                 "scientific_leaves_exceeding_tolerance", "discrete_mismatches",
                 "non_finite_leaves"}
    missing = _MISMATCH_POPULATIONS - consulted
    if missing:
        raise AssertionError(
            "mismatch populations not consulted by the verdict: " + repr(sorted(missing)))

    contradicted = any(reasons.values())
    # CONTRADICTED outranks VACUOUS, and the order is the claim. A comparison
    # that compared too little to confirm anything may still have found a real
    # disagreement in what it did compare; reporting VACUOUS there would file a
    # detected contradiction under "inconclusive". Vacuity bounds what can be
    # CONFIRMED. It says nothing about what has been refuted.
    #
    # Caught by the toy-document tests, which trip the backstop and were
    # expecting CONTRADICTED. Written the other way round first.
    if contradicted:
        verdict = "CONTRADICTED"
    elif not enough:
        verdict = "VACUOUS"
    else:
        verdict = "CONFIRMED"
    return {
        "verdict": verdict,
        "scientific_leaves_compared": compared,
        "non_digest_leaves": comparable,
        "scientific_fraction": fraction,
        "minimum_fraction": minimum_fraction,
        "backstop": backstop,
        "enough_compared": enough,
        "worst_absolute_difference": comparison["worst_absolute_difference"],
        "identity_leaves_total": comparison["identity_leaves"],
        "identity_mismatches_excluded_by_preregistration":
            comparison["identity_mismatches"],
        "environment_mismatches_excluded_by_amendment":
            len(comparison["environment_mismatches"]),
        "declared_only_in_produced": sorted(allowed),
        "undeclared_only_in_produced": undeclared_produced,
        "contradiction_reasons": {k: v for k, v in reasons.items() if v},
    }
