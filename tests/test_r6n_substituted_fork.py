"""QSigma-R6N: the substituted fork, and the guards around it.

Frozen in `manifests/qsigma_r6n_substituted_fork_preregistration.json` at
8a84bb4, before this file or `src/aionq/common_receiver_substituted.py` existed.
"""

import json

import pytest

from aionq.common_receiver_parametric import (HELD_OUT_VALUES, SEALED_GRID,
                                              SEALED_SOURCES, build_fork)
from aionq.common_receiver_substituted import (
    DECOY_GRID, SUBSTITUTION_NEW, SUBSTITUTION_OLD, build_substituted_fork,
    exercise_the_frozen_rule, licence_verdict, substituted_source)
from aionq.part_b_preflight import EFFECTIVE_PROTOCOL_DIGEST, HELD_OUT_DEPTH_COORDS
from aionq.self_audit import repo_root

MANIFEST = "manifests/qsigma_r6n_substituted_fork_preregistration.json"
R6M_LICENCE = repo_root() / "artifacts" / "r6m_parametric_equivalence" / "equivalence.json"
HELD_OUT = tuple((d, v) for _, d, v in HELD_OUT_DEPTH_COORDS)


def manifest():
    return json.loads((repo_root() / MANIFEST).read_text(encoding="utf-8"))


def _store(fork):
    crr = fork.common_receiver
    reservoir = crr._ProtocolReservoir(crr.plan_protocol(EFFECTIVE_PROTOCOL_DIGEST),
                                       crr.HashChainedEventLedger())
    fork.equal_resource.build_map_tasks("R6", reservoir)


# -- C1: one declared span, and nothing else ---------------------------------

def test_the_substitution_is_exactly_the_declared_span():
    frozen = manifest()["the_substitution"]
    assert (SUBSTITUTION_OLD, SUBSTITUTION_NEW) == (frozen["old"], frozen["new"])
    text, record = substituted_source()
    assert record["occurrences_of_old"] == 1
    assert record["only_difference"]
    assert SUBSTITUTION_OLD not in text and text.count(SUBSTITUTION_NEW) == 1


def test_no_file_on_disk_changes():
    import hashlib
    for name, (path, expected) in SEALED_SOURCES.items():
        substituted_source()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name


def test_the_substitution_is_the_identity_exactly_on_the_sealed_grid():
    """Why C2 can demand BITWISE equality: on the sealed grid the frozen decimal
    and the one-decimal format are the same string."""
    for decimal, value in SEALED_GRID:
        assert f"{value:.1f}" == decimal
    for decimal, value in HELD_OUT + DECOY_GRID:
        assert f"{value:.1f}" != decimal


# -- the decoy grid ----------------------------------------------------------

def test_the_decoy_grid_is_neither_sealed_nor_held_out_and_reproduces_each_failure_mode():
    assert [d for d, _ in DECOY_GRID] == manifest()["decoy_grid"]["depths"]
    sealed = {v for _, v in SEALED_GRID}
    for _, value in DECOY_GRID:
        assert value not in sealed and value not in HELD_OUT_VALUES
    formats = [f"{v:.1f}" for _, v in DECOY_GRID]
    assert len(set(formats)) < len(formats), "must contain a one-decimal collision, as 0.20/0.25 do"


def test_the_decoy_grid_reaches_the_defect_in_the_unrepaired_fork():
    """C3's control, cheap form. Without it a completing rehearsal could mean
    only that the decoy grid never reached the bug."""
    with pytest.raises(ValueError, match="reservoir key differs from the portable store identity"):
        _store(build_fork(DECOY_GRID))


def test_the_substituted_fork_stores_on_the_decoy_and_sealed_grids():
    _store(build_substituted_fork(DECOY_GRID))
    _store(build_substituted_fork(SEALED_GRID))


# -- the licence guard -------------------------------------------------------

def test_held_out_depths_need_an_r6n_licence_not_an_r6m_one():
    with pytest.raises(PermissionError, match="R6N licence"):
        build_substituted_fork(HELD_OUT)
    # refused by evidence now, not by label: an R6M licence is not the committed R6N one
    with pytest.raises(PermissionError, match="not the committed R6N licence"):
        build_substituted_fork(HELD_OUT, licence=R6M_LICENCE)


def test_respelling_a_held_out_depth_does_not_pass_the_guard():
    respelled = (("0.1", 0.1), ("0.2", 0.2), ("0.3", 0.3), ("0.4", 0.4), ("4.0", 4.0))
    with pytest.raises(PermissionError):
        build_substituted_fork(respelled)


# -- C4 ----------------------------------------------------------------------

def test_the_frozen_rule_is_exercised_clean_before_it_decides_anything():
    receipt = exercise_the_frozen_rule([d for d, _ in SEALED_GRID], None)
    assert receipt["clean"] and receipt["skipped"] == []
    assert receipt["disjointness"]["samples"] == 64
    assert receipt["parameters"]["knobs"] == ["grid", "licence"]


def test_the_verdict_function_on_its_witnesses():
    base = dict.fromkeys(("references_verified", "substitution_target_exactly_once",
                          "C1_substitution_exact", "C2_equivalence_on_sealed_grid",
                          "C3_decoy_rehearsal", "C4_criterion_receipt"), True)
    assert licence_verdict(base) == "LICENSED"
    assert licence_verdict({**base, "C2_equivalence_on_sealed_grid": False}) == "NOT_LICENSED"
    assert licence_verdict({**base, "substitution_target_exactly_once": False}) == "INVALID"
    assert licence_verdict({**base, "C3_decoy_rehearsal": 1}) == "NOT_LICENSED"


# -- the result --------------------------------------------------------------

def test_the_licence_is_licensed_and_nothing_held_out_was_evaluated():
    licence = json.loads((repo_root() / "artifacts" / "r6n_substituted_fork"
                          / "licence.json").read_text(encoding="utf-8"))
    assert licence["verdict"] == "LICENSED"
    assert licence["held_out_depths_evaluated"] == []
    assert all(licence["evidence"].values())
    bitwise = licence["C2"]["vs_sealed_fresh_bitwise"]
    assert bitwise["worst_absolute_difference"] == 0.0 and bitwise["identity_mismatches"] == 0
    assert bitwise["scientific_leaves_compared"] == 8320
    assert licence["C3"]["control_unrepaired_fork_on_decoy"]["failed"]
    rehearsal = licence["C3"]["rehearsal"]
    assert rehearsal["rho_decimal_labels"] == ["0.12", "0.18", "0.22", "0.35", "0.60"]
    assert rehearsal["rows"] == 384 and rehearsal["stores"] == 320
