"""QSigma-R6M: the depth-parametric fork and the guards around it.

Frozen in `manifests/qsigma_r6m_parametric_receiver_equivalence_preregistration.json`
at 6f02fd8, before this file or `src/aionq/common_receiver_parametric.py`
existed; implementation choices recorded in
`manifests/qsigma_r6m_prerun_implementation_note.json` before any number.
"""

import ast
import json
import sys

import pytest

from aionq.common_receiver_parametric import (
    EQUAL_RESOURCE_IMPORTS, SEALED_GRID, SEALED_SOURCES, VERDICTS, SealViolation,
    build_fork, equivalence_verdict, exercise_the_frozen_rule)
from aionq.self_audit import repo_root

MANIFEST = "manifests/qsigma_r6m_parametric_receiver_equivalence_preregistration.json"


def manifest():
    return json.loads((repo_root() / MANIFEST).read_text(encoding="utf-8"))


# -- the seal ---------------------------------------------------------------

def test_the_fork_refuses_bytes_that_are_not_the_sealed_bytes(monkeypatch):
    """Delegation is only safe if what is delegated to is what was sealed."""
    path, _ = SEALED_SOURCES["equal_resource_reservoir"]
    monkeypatch.setitem(SEALED_SOURCES, "equal_resource_reservoir", (path, "0" * 64))
    with pytest.raises(SealViolation, match="sealed bytes or nothing"):
        build_fork(SEALED_GRID)


def test_the_sealed_hashes_are_the_ones_at_the_R6l_source_commit():
    import hashlib
    import subprocess

    for name, (path, expected) in SEALED_SOURCES.items():
        relative = path.relative_to(repo_root()).as_posix()
        blob = subprocess.run(["git", "show", f"bedb574:{relative}"],
                              capture_output=True, cwd=repo_root()).stdout
        assert blob, f"{relative} does not resolve at bedb574"
        assert hashlib.sha256(blob).hexdigest() == expected, name


# -- the kill condition, as a guard -----------------------------------------

def test_held_out_depths_are_refused_without_a_licence():
    """'No held-out Part B depth may be evaluated, even interactively.'

    A manifest sentence is executed by nothing. This refusal is executed by
    every caller, including an interactive one.
    """
    grid = tuple((d, float(d)) for d in ("0.15", "0.20", "0.25", "0.30", "0.40"))
    with pytest.raises(PermissionError, match="refused"):
        build_fork(grid)


def test_respelling_a_held_out_depth_does_not_get_past_the_guard():
    """The first version matched the decimal SPELLING.

    ("0.20", 0.2) was refused and ("0.2", 0.2) was accepted -- three held-out
    depths evaluated with no licence, by writing them the other way. The
    comment on the earlier version of the test above asserted that a
    respelling was "refused for a different reason below". It was not refused
    at all. The guard now keys on the binary64 value, which has one spelling.
    """
    respelled = (("0.1", 0.1), ("0.2", 0.2), ("0.3", 0.3), ("0.4", 0.4), ("4.0", 4.0))
    with pytest.raises(PermissionError, match="refused"):
        build_fork(respelled)
    for value in (0.15, 0.2, 0.25, 0.3, 0.4):
        grid = (("{!r}".format(value), value),) + SEALED_GRID[1:]
        with pytest.raises(PermissionError):
            build_fork(grid)


def test_a_licence_that_is_not_equivalent_does_not_unlock_them(tmp_path):
    licence = tmp_path / "licence.json"
    licence.write_text(json.dumps({"verdict": "NOT_EQUIVALENT"}), encoding="utf-8")
    grid = tuple((d, float(d)) for d in ("0.15", "0.20", "0.25", "0.30", "0.40"))
    with pytest.raises(PermissionError, match="stay refused"):
        build_fork(grid, licence=licence)


def test_a_grid_that_is_not_five_long_is_refused_rather_than_run():
    """The sealed store count is a literal 320 = 2 maps x 5 depths x 32.

    Pinned by refusal instead of edited out of the source, so the assumption is
    stated where a caller meets it rather than as a ValueError deep inside
    execute_protocol for a reason unrelated to the recipe.
    """
    with pytest.raises(ValueError, match="five-depth grid"):
        build_fork(SEALED_GRID[:4])


def test_a_depth_whose_decimal_does_not_denote_its_float_is_refused():
    bad = (("0.1", 0.1000001),) + SEALED_GRID[1:]
    with pytest.raises(ValueError, match="does not denote"):
        build_fork(bad)


# -- C_no_mutation ----------------------------------------------------------

def test_building_a_fork_never_touches_the_sealed_modules():
    """The imported sealed modules keep their grids by value AND identity, and
    keep their own sys.modules entries.

    The first draft promised never to modify sys.modules at all and crashed on
    its first dataclass, which resolves string annotations through
    sys.modules[cls.__module__]. What survives, and is what mattered: forks are
    registered under private unique names and no existing entry is replaced.
    """
    import aionq.common_receiver_reservoir as sealed_crr
    import aionq.equal_resource_reservoir as sealed_err

    before = (sealed_err.DEPTHS, id(sealed_err.DEPTHS),
              sealed_crr.DEPTH_COORDS, id(sealed_crr.DEPTH_COORDS),
              sys.modules["aionq.equal_resource_reservoir"],
              sys.modules["aionq.common_receiver_reservoir"])

    permuted = tuple(SEALED_GRID[i] for i in (3, 0, 4, 1, 2))
    fork = build_fork(permuted)
    fork.equal_resource.build_map_tasks("R6")

    after = (sealed_err.DEPTHS, id(sealed_err.DEPTHS),
             sealed_crr.DEPTH_COORDS, id(sealed_crr.DEPTH_COORDS),
             sys.modules["aionq.equal_resource_reservoir"],
             sys.modules["aionq.common_receiver_reservoir"])
    assert before == after
    assert fork.equal_resource is not sealed_err
    assert fork.equal_resource.__name__.startswith("aionq._r6m_fork_")


# -- C_wiring: the one thing the preregistered test cannot see ---------------

def test_the_grid_reaches_the_numerics_and_not_only_the_labels():
    """Three depth bindings, and the equivalence test is blind to two of them.

    DEPTH_COORDS labels the rows; DEPTHS in a different module is what
    build_map_tasks iterates. At the sealed grid both coincide with their sealed
    values, so a fork that rebinds only the labels reproduces all 384 rows.
    This test uses a PERMUTED order of the sealed depths -- evaluating no
    held-out depth -- and requires the numerics to follow it.
    """
    permuted = tuple(SEALED_GRID[i] for i in (3, 0, 4, 1, 2))
    fork = build_fork(permuted)

    tasks, _ = fork.equal_resource.build_map_tasks("R6")
    emitted = [task.depth for task in tasks if task.name == "signed_fixed_depth"]
    assert emitted == [value for _, value in permuted]

    for name in EQUAL_RESOURCE_IMPORTS:
        assert getattr(fork.common_receiver, name) is getattr(fork.equal_resource, name), name
    assert fork.common_receiver.DEPTH_COORDS == permuted


def test_the_wiring_test_can_fail_on_a_labels_only_fork():
    """A check that has never reported a problem has not been tested.

    Rebind DEPTH_COORDS alone -- the fork the execution blocker described --
    and the numerics keep the SEALED order while the labels say otherwise.
    """
    permuted = tuple(SEALED_GRID[i] for i in (3, 0, 4, 1, 2))
    fork = build_fork(permuted)
    fork.equal_resource.DEPTHS = tuple(value for _, value in SEALED_GRID)   # undo one binding

    tasks, _ = fork.equal_resource.build_map_tasks("R6")
    emitted = [task.depth for task in tasks if task.name == "signed_fixed_depth"]
    assert emitted != [value for _, value in permuted]
    assert fork.common_receiver.DEPTH_COORDS == permuted


# -- the one import-time binding --------------------------------------------

def test_the_only_import_time_depth_read_stays_off_the_R6l_path():
    """truncation_cost_report(depths=DEPTHS) binds the sealed grid at definition.

    The pre-run note's first draft said no depth read happened at import time;
    an AST check before committing found this one. It is harmless only while
    nothing on R6l's path calls it. That is asserted here with a static
    name-based call graph -- an approximation that would miss a function passed
    as a value -- so the day it becomes reachable, this fails instead of the
    fork quietly computing one quantity at the wrong grid.
    """
    root = repo_root() / "src" / "aionq"
    graph: dict = {}
    import_time = []
    for module in ("equal_resource_reservoir.py", "common_receiver_reservoir.py"):
        tree = ast.parse((root / module).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                graph[node.name] = {
                    call.func.id if isinstance(call.func, ast.Name)
                    else getattr(call.func, "attr", None)
                    for call in ast.walk(node) if isinstance(call, ast.Call)}
                for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                    if any(isinstance(n, ast.Name) and n.id in ("DEPTHS", "DEPTH_COORDS")
                           for n in ast.walk(default)):
                        import_time.append((module, node.name))

    assert import_time == [("equal_resource_reservoir.py", "truncation_cost_report")]

    seen, stack = set(), ["execute_protocol", "plan_protocol", "classify_protocol"]
    while stack:
        name = stack.pop()
        if name in seen or name not in graph:
            continue
        seen.add(name)
        stack.extend(graph[name])
    assert "truncation_cost_report" not in seen
    assert len(seen) > 50, "the call graph must actually have been walked"


# -- R2A on this round's own rule -------------------------------------------

def test_the_frozen_rule_is_exercised_clean_before_the_round_runs():
    """R6M lists a clean criterion receipt among its own required conditions.

    All three verdicts reached by their witnesses; the three regions checked
    over every one of the 2^7 flag combinations rather than a sample; both
    defaulted knobs of build_fork named in the manifest.
    """
    frozen = manifest()["scope"]["sealed_reference_depths"]
    receipt = exercise_the_frozen_rule(frozen, None)

    assert receipt["clean"]
    assert receipt["declaration_valid"] and receipt["skipped"] == []
    assert receipt["coverage"]["declared_verdicts"] == sorted(VERDICTS)
    assert receipt["disjointness"]["samples"] == 128
    assert not receipt["disjointness"]["collisions"]
    assert not receipt["disjointness"]["uncovered"]
    assert receipt["parameters"]["knobs"] == ["grid", "licence"]


def test_the_manifest_grid_is_the_grid_the_fork_runs():
    """The limitation R2A's parameter check carries: it verifies a knob is NAMED
    in the frozen record, not that the value used equals the value frozen.
    Bound here instead.
    """
    frozen = manifest()["scope"]["sealed_reference_depths"]
    assert [decimal for decimal, _ in SEALED_GRID] == frozen


def test_the_verdict_function_on_its_own_three_witnesses():
    base = {flag: True for flag in (
        "references_verified", "comparison_surface_complete",
        "identities_exactly_once_each_side", "discrete_agree",
        "numerical_within_tolerance", "no_undeclared_output",
        "criterion_receipt_clean")}
    assert equivalence_verdict(base) == "EQUIVALENT_ON_SEALED_GRID"
    assert equivalence_verdict({**base, "discrete_agree": False}) == "NOT_EQUIVALENT"
    assert equivalence_verdict({**base, "references_verified": False}) == "INVALID"
    # a flag that is merely truthy is not True
    assert equivalence_verdict({**base, "discrete_agree": 1}) == "NOT_EQUIVALENT"


# -- the result -------------------------------------------------------------

def test_the_fork_is_equivalent_on_the_sealed_grid_and_nowhere_else_was_evaluated():
    """EQUIVALENT_ON_SEALED_GRID, and the residual is not the fork's.

    8,320 scientific leaves over 384/384 identities, worst difference 3.44e-15
    against 1e-10. The fork is BITWISE identical to the sealed module run fresh
    on the same platform, and that fresh run shows the same 3.44e-15 and the
    same 3,072 digest mismatches against the committed rows -- so both belong to
    the platform, not to the fork. A 1e-9 perturbation of one leaf flips the
    verdict, so the comparison is not one that agrees with everything.
    """
    artifact = json.loads((repo_root() / "artifacts" / "r6m_parametric_equivalence"
                           / "equivalence.json").read_text(encoding="utf-8"))
    evidence = artifact["evidence"]
    controls = artifact["post_freeze_controls"]

    assert artifact["verdict"] == "EQUIVALENT_ON_SEALED_GRID"
    assert artifact["held_out_depths_evaluated"] == []
    assert artifact["grid"] == manifest()["scope"]["sealed_reference_depths"]

    assert evidence["committed_rows"] == evidence["fork_rows"] == 384
    assert evidence["comparison"]["scientific_leaves_compared"] == 8320
    assert evidence["comparison"]["worst_absolute_difference"] < 1e-13
    assert evidence["comparison"]["discrete_mismatches"] == 0

    assert controls["C_perturbation"]["detected"]
    bitwise = controls["C_fork_vs_sealed_fresh_bitwise"]
    assert bitwise["worst_absolute_difference"] == 0.0
    assert bitwise["identity_mismatches"] == 0
    platform = controls["C_platform_sealed_fresh_vs_committed"]["evidence"]["comparison"]
    assert platform["identity_mismatches"] == evidence["comparison"]["identity_mismatches"]
    assert platform["worst_absolute_difference"] == evidence["comparison"]["worst_absolute_difference"]

    assert artifact["references"]["envelope_bound_artifacts_verified_at_raw_commit"] == 27
    assert artifact["references"]["envelope_bytes_identical_to_seal_commit"] is False, (
        "the schema migration is recorded, not hidden; if this flips, re-read the reading")
