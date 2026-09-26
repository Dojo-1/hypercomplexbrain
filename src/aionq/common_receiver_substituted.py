"""The R6M fork with its one-decimal store key repaired by a declared substitution.

Round QSigma-R6N. Part B's first execution failed closed at the first held-out
depth: equal_resource_reservoir._signed_codebooks builds each store key with
``f"{rho:.1f}"``, and the store checks it against the frozen decimal label.
Every sealed depth has one decimal digit, so the format is exact there and
every check run at the sealed grid is blind to it.

R6M's fork (:mod:`aionq.common_receiver_parametric`) rebinds module-level
NAMES in namespaces it owns and executes the sealed bytes unchanged. That
cannot reach a format specification inside a function body. This module reads
the same sealed bytes, verifies them, and makes exactly ONE substitution in the
in-memory text before executing it::

    rho={rho:.1f}   ->   rho={_R6N_DEPTH_DECIMAL[rho]}

``_R6N_DEPTH_DECIMAL`` maps each grid value to its frozen decimal and is bound
in the fork's own namespace after execution, as DEPTHS is. No file on disk
changes. On the sealed grid every frozen decimal equals the one-decimal format
of its value, so the substitution claims to be the identity there; R6N's C2
tests that claim bitwise against the sealed module run fresh.

R6M's module is deliberately left untouched: its licence covers byte-identical
delegation, and editing it would blur which code that licence was about.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
import types
from pathlib import Path

from .common_receiver_parametric import (
    EQUAL_RESOURCE_IMPORTS, HELD_OUT_VALUES, SEALED_GRID, SEALED_SOURCES,
    ParametricFork, SealViolation)

__all__ = [
    "SUBSTITUTION_OLD", "SUBSTITUTION_NEW", "DECOY_GRID", "VERDICTS",
    "substituted_source", "build_substituted_fork", "licence_verdict",
    "exercise_the_frozen_rule",
]

SUBSTITUTION_OLD = "rho={rho:.1f}"
SUBSTITUTION_NEW = "rho={_R6N_DEPTH_DECIMAL[rho]}"

#: Neither sealed nor held-out, by binary64 value. Chosen to reproduce every way
#: the held-out grid breaks the key: 0.18 and 0.22 collide under .1f as 0.20 and
#: 0.25 do; 0.35 rounds DOWN through its binary64 value as 0.15 does; "0.60"
#: carries a trailing zero as "0.20" does. Its metrics mean nothing.
DECOY_GRID = (("0.12", 0.12), ("0.18", 0.18), ("0.22", 0.22), ("0.35", 0.35), ("0.60", 0.6))

VERDICTS = ("LICENSED", "NOT_LICENSED", "INVALID")

_SERIAL = itertools.count()


def substituted_source() -> tuple[str, dict]:
    """The sealed equal_resource source with exactly one span replaced.

    Verifies the sealed hash first; refuses unless the target occurs exactly
    once, so a second copy of the format -- added later, or already present --
    cannot be silently left unrepaired or silently repaired twice.
    """
    path, expected = SEALED_SOURCES["equal_resource_reservoir"]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise SealViolation(f"{path.name} is not the sealed bytes")
    sealed = raw.decode("utf-8")
    occurrences = sealed.count(SUBSTITUTION_OLD)
    if occurrences != 1:
        raise SealViolation(
            f"substitution target occurs {occurrences} times; the declared repair is exactly one span")
    executed = sealed.replace(SUBSTITUTION_OLD, SUBSTITUTION_NEW, 1)
    at = sealed.index(SUBSTITUTION_OLD)
    return executed, {
        "sealed_sha256": expected,
        "executed_sha256": hashlib.sha256(executed.encode("utf-8")).hexdigest(),
        "occurrences_of_old": occurrences,
        "line": sealed.count("\n", 0, at) + 1,
        "old": SUBSTITUTION_OLD,
        "new": SUBSTITUTION_NEW,
        "only_difference": (executed[:at] == sealed[:at]
                            and executed[at + len(SUBSTITUTION_NEW):] == sealed[at + len(SUBSTITUTION_OLD):]),
    }


def _exec_into(private: str, path: Path, text: str) -> types.ModuleType:
    if private in sys.modules:
        raise RuntimeError(f"{private} already exists; refusing to replace it")
    module = types.ModuleType(private)
    module.__file__ = str(path)
    module.__package__ = "aionq"
    sys.modules[private] = module          # dataclass resolves annotations through it
    exec(compile(text, str(path), "exec"), module.__dict__)
    return module


def _validate(grid, licence) -> tuple:
    grid = tuple((str(decimal), float(value)) for decimal, value in grid)
    if len(grid) != 5:
        raise ValueError("the sealed store count is a literal 320 = 2 maps x 5 depths x 32 codewords")
    if len({d for d, _ in grid}) != 5 or len({v for _, v in grid}) != 5:
        raise ValueError("grid repeats a depth")
    for decimal, value in grid:
        if float(decimal) != value or not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"depth {decimal!r} does not denote the binary64 {value!r}")
    held_out = sorted(v for _, v in grid if v in HELD_OUT_VALUES)
    if held_out:
        if licence is None:
            raise PermissionError(f"held-out depths {held_out} refused without an R6N licence")
        record = json.loads(Path(licence).read_text(encoding="utf-8"))
        if record.get("round") != "QSigma-R6N" or record.get("verdict") != "LICENSED":
            raise PermissionError(
                f"{licence} is not an R6N LICENSED verdict; held-out depths stay refused")
    return grid


def build_substituted_fork(grid=SEALED_GRID, *, licence=None) -> ParametricFork:
    """R6M's construction, with the declared substitution in equal_resource."""
    grid = _validate(grid, licence)
    serial = next(_SERIAL)
    err_path, _ = SEALED_SOURCES["equal_resource_reservoir"]
    text, _record = substituted_source()
    equal_resource = _exec_into(f"aionq._r6n_fork_{serial}.equal_resource_reservoir", err_path, text)
    equal_resource.DEPTHS = tuple(value for _, value in grid)
    equal_resource._R6N_DEPTH_DECIMAL = {value: decimal for decimal, value in grid}

    crr_path, crr_expected = SEALED_SOURCES["common_receiver_reservoir"]
    crr_raw = crr_path.read_bytes()
    if hashlib.sha256(crr_raw).hexdigest() != crr_expected:
        raise SealViolation(f"{crr_path.name} is not the sealed bytes")
    common_receiver = _exec_into(f"aionq._r6n_fork_{serial}.common_receiver_reservoir",
                                 crr_path, crr_raw.decode("utf-8"))
    for name in EQUAL_RESOURCE_IMPORTS:
        setattr(common_receiver, name, getattr(equal_resource, name))
    common_receiver.DEPTH_COORDS = grid
    return ParametricFork(grid=grid, equal_resource=equal_resource, common_receiver=common_receiver)


_GATES = ("references_verified", "substitution_target_exactly_once")
_CONDITIONS = ("C1_substitution_exact", "C2_equivalence_on_sealed_grid",
               "C3_decoy_rehearsal", "C4_criterion_receipt")


def licence_verdict(evidence: dict) -> str:
    if not all(evidence.get(g) is True for g in _GATES):
        return "INVALID"
    if all(evidence.get(c) is True for c in _CONDITIONS):
        return "LICENSED"
    return "NOT_LICENSED"


def exercise_the_frozen_rule(frozen_grid, frozen_licence) -> dict:
    """R2A on R6N's own rule, before any real comparison: every verdict reached,
    the three regions checked over all 2^6 flag combinations, both knobs of
    build_substituted_fork named in the manifest."""
    from .criterion import exercise

    flags = _GATES + _CONDITIONS
    base = {f: True for f in flags}
    gate = lambda e: all(e[g] for g in _GATES)
    return exercise(
        verdict_fn=licence_verdict,
        witnesses={"LICENSED": base,
                   "NOT_LICENSED": {**base, "C3_decoy_rehearsal": False},
                   "INVALID": {**base, "references_verified": False}},
        declared_verdicts=VERDICTS,
        predicates={"INVALID": lambda e: not gate(e),
                    "LICENSED": lambda e: gate(e) and all(e[c] for c in _CONDITIONS),
                    "NOT_LICENSED": lambda e: gate(e) and not all(e[c] for c in _CONDITIONS)},
        samples=[dict(zip(flags, bits)) for bits in itertools.product((False, True), repeat=len(flags))],
        entrypoint=build_substituted_fork,
        frozen={"grid": frozen_grid, "licence": frozen_licence},
        required_checks=("coverage", "disjointness", "parameters"),
    )
