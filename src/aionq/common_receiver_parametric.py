"""A depth-parametric fork of the sealed R6l common receiver, and its licence.

Round QSigma-R6M.  Part B of R6k-W1 needs R6l's pooled common receiver rebuilt
at held-out depths, and the sealed module cannot be evaluated there without
being edited -- which would break the seal Part B requires.  The route the
execution blocker recommended is a FORK carrying the identical recipe with the
depth grid as an argument, licensed as a stand-in only if it reproduces R6l's
384 committed retrieval rows at R6l's own five depths.

THE FORK NEEDS THREE DEPTH BINDINGS, NOT ONE.  The blocker named
``DEPTH_COORDS``.  Measured before this file existed
(``manifests/qsigma_r6m_prerun_implementation_note.json``):

    DEPTH_COORDS   common_receiver_reservoir   labels, identities, validators
    DEPTHS         equal_resource_reservoir    what the NUMERICS iterate
    ``!= 320``     execute_protocol            2 maps x 5 depths x 32 codewords

At the sealed grid all three coincide with their sealed values, so the
preregistered equivalence test passes a labels-only fork exactly as readily as
a correct one.  That is why :func:`build_fork` binds all of them, why the store
count is PINNED by refusing any grid whose length is not five rather than edited
out of the source, and why the wiring is tested separately from the
equivalence (``C_wiring``): the equivalence cannot see it.

THE IMPLEMENTATION CHOICE, EXPOSED AS THE MANIFEST REQUIRES.  Delegation by
verified re-execution.  The sealed source files are read, their SHA-256 checked
against the values at ``bedb574``, and each is executed into a FRESH module
namespace the fork owns.  The grid, and the names the second module imports
from the first, are rebound inside those namespaces only.

    avoided    copying: not one line of the recipe is duplicated, so nothing
               can drift, and the bytes are checked at every load
    avoided    hidden global state: the imported sealed modules are never
               touched, and no existing ``sys.modules`` entry is replaced.
               Each fork IS registered, under its own private unique name,
               because Python's ``dataclass`` resolves string annotations
               through ``sys.modules[cls.__module__]`` and cannot build a class
               in an unregistered namespace -- found when the first draft,
               which promised never to touch ``sys.modules`` at all, crashed
               on its first dataclass.
    NOT        anything bound at import time from a depth constant.  There is
    avoided    exactly one -- ``truncation_cost_report(depths=DEPTHS)``, a
               default argument -- and it is off R6l's path.  A test asserts
               that rather than this docstring.

THE KILL CONDITION IS A GUARD HERE, NOT A SENTENCE.  "No held-out Part B depth
may be evaluated, even interactively, before this round is sealed and its
equivalence verdict passes."  :func:`build_fork` refuses any held-out depth
unless it is handed a licence artifact whose verdict is
``EQUIVALENT_ON_SEALED_GRID``.  A promise in a manifest is not executed by
anything; a refusal in the constructor is executed by every caller.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
import types
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "SEALED_SOURCES",
    "SEALED_GRID",
    "HELD_OUT_DECIMALS",
    "HELD_OUT_VALUES",
    "EQUAL_RESOURCE_IMPORTS",
    "SealViolation",
    "ParametricFork",
    "build_fork",
    "run_fork",
    "equivalence_evidence",
    "equivalence_verdict",
    "VERDICTS",
    "exercise_the_frozen_rule",
]

_SRC = Path(__file__).resolve().parent

#: The bytes the fork is permitted to execute: their SHA-256 at the R6l source
#: commit ``bedb574``.  A mismatch refuses the load outright.
SEALED_SOURCES = {
    "equal_resource_reservoir": (
        _SRC / "equal_resource_reservoir.py",
        "9978b8051d8b6afc1b7fa454a214bd49b3263efeb83bb7da9222ae6b17c02691",
    ),
    "common_receiver_reservoir": (
        _SRC / "common_receiver_reservoir.py",
        "850bd22125b95c52d01e7a456e40cc0a5a31f4141ac3c0c0d6d6107f920abff3",
    ),
}

SEALED_GRID = (("0.1", 0.1), ("0.5", 0.5), ("1.0", 1.0), ("2.0", 2.0), ("4.0", 4.0))
HELD_OUT_DECIMALS = frozenset({"0.15", "0.20", "0.25", "0.30", "0.40"})

#: The guard keys on THESE, not on the decimals above. The first version matched
#: the spelling, so ("0.2", 0.2) walked straight past a guard that refused
#: ("0.20", 0.2) -- the kill condition enforced for one of two ways to write the
#: same number. A binary64 value has no second spelling.
HELD_OUT_VALUES = frozenset(float(decimal) for decimal in HELD_OUT_DECIMALS)

#: Every name common_receiver_reservoir imports from equal_resource_reservoir.
#: All are rebound to the fork's own copies, classes included, so a TaskEnsemble
#: built by the fork's build_map_tasks is the same class the fork's receiver
#: code expects.  Read off the sealed import statement, not chosen.
EQUAL_RESOURCE_IMPORTS = (
    "AMBIENT_DIM", "CODEWORDS_PER_DEPTH", "DEPTHS", "PGMReceiver",
    "ReservoirRecord", "TaskEnsemble", "build_map_tasks", "build_pgm_receiver",
    "depolarize",
)

#: execute_protocol checks ``len(events) != 320`` as a literal.  320 = 2 maps x
#: 5 depths x 32 codewords, so any other grid length would fail inside the
#: sealed code for a reason unrelated to the recipe.  Pinned, not edited out.
_PINNED_GRID_LENGTH = 5

VERDICTS = ("EQUIVALENT_ON_SEALED_GRID", "NOT_EQUIVALENT", "INVALID")


class SealViolation(RuntimeError):
    """The bytes offered for execution are not the sealed bytes."""


@dataclass(frozen=True)
class ParametricFork:
    grid: tuple
    equal_resource: types.ModuleType
    common_receiver: types.ModuleType


_FORK_SERIAL = itertools.count()


def _load_verified(name: str, serial: int) -> types.ModuleType:
    path, expected = SEALED_SOURCES[name]
    source = path.read_bytes()
    observed = hashlib.sha256(source).hexdigest()
    if observed != expected:
        raise SealViolation(
            f"{path.name}: sha256 {observed[:16]}... is not the sealed "
            f"{expected[:16]}... -- the fork executes sealed bytes or nothing")
    private = f"aionq._r6m_fork_{serial}.{name}"
    if private in sys.modules:
        raise RuntimeError(f"fork namespace {private} already exists; refusing to replace it")
    module = types.ModuleType(private)
    module.__file__ = str(path)
    module.__package__ = "aionq"
    # Registered because dataclass needs it; under a private name so that
    # nothing importing the sealed module can ever receive the fork.
    sys.modules[private] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _validate_grid(grid, licence) -> tuple:
    grid = tuple((str(decimal), float(value)) for decimal, value in grid)
    if len(grid) != _PINNED_GRID_LENGTH:
        raise ValueError(
            f"grid has {len(grid)} depths; the sealed execute_protocol checks a "
            f"literal store count of 320 = 2 maps x {_PINNED_GRID_LENGTH} depths "
            f"x 32 codewords, so only a five-depth grid runs the sealed recipe")
    decimals = [decimal for decimal, _ in grid]
    if len(set(decimals)) != len(decimals):
        raise ValueError("grid repeats a depth")
    for decimal, value in grid:
        if float(decimal) != value or not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"depth {decimal!r} does not denote the binary64 {value!r}")
    held_out = sorted(value for _, value in grid if value in HELD_OUT_VALUES)
    if held_out:
        if licence is None:
            raise PermissionError(
                f"held-out depths {held_out} refused: QSigma-R6M's kill condition "
                f"forbids evaluating them before an EQUIVALENT_ON_SEALED_GRID "
                f"verdict exists. Pass the licence artifact.")
        verdict = json.loads(Path(licence).read_text(encoding="utf-8")).get("verdict")
        if verdict != "EQUIVALENT_ON_SEALED_GRID":
            raise PermissionError(
                f"licence at {licence} carries verdict {verdict!r}, not "
                f"EQUIVALENT_ON_SEALED_GRID; held-out depths stay refused")
    return grid


def build_fork(grid=SEALED_GRID, *, licence=None) -> ParametricFork:
    """Load both sealed modules into namespaces the fork owns, then rebind depth.

    Order matters and is the whole design.  equal_resource_reservoir is loaded
    and its DEPTHS rebound first, so its build_map_tasks iterates the fork's
    grid.  common_receiver_reservoir is then loaded -- its import statement
    binds the SEALED equal_resource objects at exec time -- and every one of
    those names is immediately rebound to the fork's copy, along with
    DEPTH_COORDS.  Functions look up globals at call time, so from here on the
    fork's receiver code sees the fork's grid and the fork's tasks.
    """
    grid = _validate_grid(grid, licence)
    serial = next(_FORK_SERIAL)

    equal_resource = _load_verified("equal_resource_reservoir", serial)
    equal_resource.DEPTHS = tuple(value for _, value in grid)

    common_receiver = _load_verified("common_receiver_reservoir", serial)
    for name in EQUAL_RESOURCE_IMPORTS:
        setattr(common_receiver, name, getattr(equal_resource, name))
    common_receiver.DEPTH_COORDS = grid

    return ParametricFork(grid=grid, equal_resource=equal_resource,
                          common_receiver=common_receiver)


def run_fork(fork: ParametricFork, *,
             effective_protocol_digest: str) -> dict:
    """Plan and execute the protocol in the fork. Returns the report dict.

    The effective protocol digest is REQUIRED rather than defaulted: the sealed
    plan_protocol defaults it, and a defaulted knob is a choice the caller can
    silently inherit. R6M passes the sealed value explicitly.
    """
    crr = fork.common_receiver
    plan = crr.plan_protocol(effective_protocol_digest)
    run = crr.execute_protocol(plan)
    return run.report


def _rows_by_identity(rows) -> tuple[list, dict]:
    ids = [row.get("protocol_cell_id") for row in rows]
    counts: dict = {}
    for identity in ids:
        counts[identity] = counts.get(identity, 0) + 1
    ordered = sorted(rows, key=lambda row: str(row.get("protocol_cell_id")))
    return ordered, counts


def equivalence_evidence(committed_rows, fork_rows, *, tolerance: float,
                         references_verified: bool,
                         criterion_receipt_clean: bool) -> dict:
    """Everything the frozen rule's five conditions are decided on.

    Rows are ordered by protocol_cell_id on both sides before the leaf
    comparison, so a paths reads ``retrieval_rows[k].metrics.x`` rather than
    carrying a digest in it. Identity multiplicity is checked separately and
    exactly, because the comparator counts sha256-valued leaves rather than
    failing on them -- correct for a digest of floats, wrong for an identity
    that must appear exactly once.
    """
    from .semantic_reproduction import compare_results

    committed, committed_counts = _rows_by_identity(committed_rows)
    forked, fork_counts = _rows_by_identity(fork_rows)
    comparison = compare_results({"retrieval_rows": committed},
                                 {"retrieval_rows": forked}, tolerance)

    exactly_once = (set(committed_counts) == set(fork_counts)
                    and all(n == 1 for n in committed_counts.values())
                    and all(n == 1 for n in fork_counts.values()))
    return {
        "references_verified": bool(references_verified),
        "comparison_surface_complete": bool(committed_rows) and bool(fork_rows),
        "committed_rows": len(committed_rows),
        "fork_rows": len(fork_rows),
        "identities_exactly_once_each_side": exactly_once,
        "discrete_agree": not comparison["discrete_mismatches"],
        "numerical_within_tolerance": (
            comparison["scientific_leaves_compared"] > 0
            and not comparison["scientific_leaves_exceeding_tolerance"]
            and not comparison["non_finite_leaves"]),
        "no_undeclared_output": (not comparison["only_in_reproduced"]
                                 and not comparison["only_in_produced"]),
        "criterion_receipt_clean": bool(criterion_receipt_clean),
        "comparison": comparison,
    }


def equivalence_verdict(evidence: dict) -> str:
    """The frozen rule, read clause by clause from the preregistration.

    INVALID when the reference cannot be byte-verified or the comparison surface
    is incomplete; otherwise EQUIVALENT only when every required condition holds.
    The three regions are disjoint and exhaustive by construction, and that is
    exercised with aionq.criterion before any real row is compared.
    """
    if not (evidence.get("references_verified")
            and evidence.get("comparison_surface_complete")):
        return "INVALID"
    required = ("identities_exactly_once_each_side", "discrete_agree",
                "numerical_within_tolerance", "no_undeclared_output",
                "criterion_receipt_clean")
    if all(evidence.get(name) is True for name in required):
        return "EQUIVALENT_ON_SEALED_GRID"
    return "NOT_EQUIVALENT"


_REQUIRED_FLAGS = ("identities_exactly_once_each_side", "discrete_agree",
                   "numerical_within_tolerance", "no_undeclared_output",
                   "criterion_receipt_clean")
_GATE_FLAGS = ("references_verified", "comparison_surface_complete")


def _synthetic(**overrides) -> dict:
    evidence = {flag: True for flag in _GATE_FLAGS + _REQUIRED_FLAGS}
    evidence.update(overrides)
    return evidence


def exercise_the_frozen_rule(frozen_grid, frozen_licence) -> dict:
    """R2A, run on this round's own verdict function before any real comparison.

    Coverage: a witness for each of the three declared verdicts, supplied not
    searched for. Disjointness: the three regions stated as independent
    predicates over EVERY one of the 2^7 combinations of the seven flags, so an
    overlap or a gap anywhere in the space is found rather than sampled past.
    Parameters: the defaulted knobs of build_fork -- the grid and the licence --
    must each carry a value in the manifest.

    One limitation of the instrument, stated rather than inherited silently:
    the parameter check verifies that each knob is NAMED in the frozen record,
    not that the value used equals the value frozen. The runner asserts the
    binding separately.
    """
    import itertools as _it

    from .criterion import exercise

    def invalid(e):
        return not (e["references_verified"] and e["comparison_surface_complete"])

    def equivalent(e):
        return (not invalid(e)) and all(e[f] for f in _REQUIRED_FLAGS)

    def not_equivalent(e):
        return (not invalid(e)) and not all(e[f] for f in _REQUIRED_FLAGS)

    flags = _GATE_FLAGS + _REQUIRED_FLAGS
    samples = [dict(zip(flags, bits))
               for bits in _it.product((False, True), repeat=len(flags))]
    return exercise(
        verdict_fn=equivalence_verdict,
        witnesses={
            "EQUIVALENT_ON_SEALED_GRID": _synthetic(),
            "NOT_EQUIVALENT": _synthetic(numerical_within_tolerance=False),
            "INVALID": _synthetic(references_verified=False),
        },
        declared_verdicts=VERDICTS,
        predicates={"EQUIVALENT_ON_SEALED_GRID": equivalent,
                    "NOT_EQUIVALENT": not_equivalent,
                    "INVALID": invalid},
        samples=samples,
        entrypoint=build_fork,
        frozen={"grid": frozen_grid, "licence": frozen_licence},
        required_checks=("coverage", "disjointness", "parameters"),
    )
