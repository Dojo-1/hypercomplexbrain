"""The Part B C_pre anchor, guarded from OUTSIDE the surface it anchors.

The preflight's tag gate checks that C_pre -- the earliest commit carrying the
live input-freeze bytes -- holds the current bytes of all five guard files. But
it only runs once a tag exists, and the tag cannot be published from this
environment, so the preflight test skips before reaching it. That skip
concealed a real failure for seven weeks: a6d8b99 edited
tests/test_part_b_preflight.py without touching the manifest, after which NO
commit satisfied the rule and the gate could never pass, tag or no tag.

These checks need no tag, and they live in a file that is not a C_pre path, so
running them cannot move the anchor they protect.
"""

import subprocess
import sys
from pathlib import Path

from aionq.part_b_preflight import C_PRE_PATHS, MANIFEST_PATH, TAG_BINDING_OBJECT
from aionq.self_audit import repo_root


def _git(*args):
    return subprocess.run(["git", *args], cwd=repo_root(), capture_output=True)


def _earliest_carrier() -> str:
    live = (repo_root() / MANIFEST_PATH).read_bytes()
    touching = _git("log", "--format=%H", "--", MANIFEST_PATH).stdout.decode().split()
    carriers = [commit for commit in touching
                if _git("show", f"{commit}:{MANIFEST_PATH}").stdout == live]
    assert carriers, "no commit carries the live input-freeze bytes"
    return carriers[-1]


def test_a_valid_c_pre_exists_whether_or_not_the_tag_does():
    """The failure a6d8b99 introduced, and that nothing reported."""
    c_pre = _earliest_carrier()
    stale = [path for path in C_PRE_PATHS
             if _git("show", f"{c_pre}:{path}").stdout != (repo_root() / path).read_bytes()]
    assert stale == [], (
        f"C_pre {c_pre[:12]} does not hold the current bytes of {stale}: a guard "
        f"file was edited without re-freezing the manifest, and the preregistration "
        f"tag gate can no longer pass for anyone")
    forbidden = [path for path in TAG_BINDING_OBJECT["must_be_absent_at_c_pre"]
                 if _git("cat-file", "-e", f"{c_pre}:{path}").returncode == 0]
    assert forbidden == []


def test_c_pre_is_the_repair_commit():
    """d0650f0: the pre-execution repair that made a valid C_pre exist again."""
    assert _earliest_carrier().startswith("d0650f02c67a")


def test_the_outcome_function_passed_r2a_before_it_was_anchored():
    """part_b_outcome.py is a C_pre path, so a defect found after tagging could not
    be repaired without moving the anchor. R2A therefore ran before d0650f0.

    Disjointness is declared and omitted rather than faked: for one total
    single-valued function it is structural, and restating the regions as
    independent predicates would create a second copy of the rule -- the drift
    the effective protocol v2 was written to remove.
    """
    sys.path.insert(0, str(repo_root() / "tests"))
    import test_part_b_outcome as t

    from aionq.criterion import exercise
    from aionq.part_b_outcome import OUTCOMES, part_b_outcome

    invalid = t._map_rows(0.20)
    t._set_noise_first(invalid, 1, 0, 0.25)
    receipt = exercise(
        verdict_fn=lambda rows: part_b_outcome(rows)["outcome"],
        witnesses={"SUPPORTING": t._map_rows(0.20),
                   "INCONCLUSIVE": t._map_rows(0.15),
                   "REFUTED": t._map_rows(0.40),
                   "INVALID": invalid},
        declared_verdicts=OUTCOMES,
        entrypoint=part_b_outcome, frozen={},
        required_checks=("coverage", "parameters"))

    assert receipt["clean"]
    assert receipt["skipped"] == ["disjointness"]
    assert receipt["parameters"]["knobs"] == []
