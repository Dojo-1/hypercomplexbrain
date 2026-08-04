"""The instrument that edits the code it measures.

`experiments/mutation_probe.py` rewrites a source file in place, runs the
tests, and restores it.  That is a dangerous shape, and it failed exactly the
way dangerous shapes do: an interrupted run left `residency.py` carrying a live
mutation -- `informative` returning `bounding_strategy == "dense"`, the precise
inversion of its contract -- because a ``finally`` does not survive SIGKILL.

Two things made that worse than a stray edit.  The probe reads the file as
``original`` at mutation time, so a later run would have adopted the corruption
as its baseline and restored *to* it.  And a corrupted source is one
``git commit -a`` from being published.

These tests guard the probe's own safety properties.  They are cheap, and the
alternative is an instrument that can silently poison the thing it audits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

import mutation_probe as probe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def scratch_module(tmp_path_factory):
    """A throwaway module under the repo root, never a real source file.

    These tests must not write to `src/aionq/*`. The probe rewrites its targets
    in place, so a test that also rewrote them could collide with a probe run in
    progress -- and colliding in-place writers is the hazard this whole file
    exists to guard. The scratch file lives under ROOT so the probe's
    ROOT-relative paths and `git status` checks behave normally, and it is
    untracked, which is exactly the "dirty" state one test needs.
    """
    directory = ROOT / ".mutation-probe-scratch"
    directory.mkdir(exist_ok=True)
    path = directory / "sample.py"
    path.write_text(
        "def classify(value):\n"
        "    if value > 3:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8")
    relative = str(path.relative_to(ROOT))
    yield relative, path
    path.unlink(missing_ok=True)
    try:
        directory.rmdir()
    except OSError:  # pragma: no cover - other files present
        pass


def test_a_clean_tracked_target_is_accepted():
    """Read-only: naming a real module here must not write to it."""
    probe.assert_clean("src/aionq/residency.py")


def test_a_dirty_target_is_refused_before_any_mutation(scratch_module):
    """The precondition that would have prevented the corruption compounding.

    The probe cannot tell a leftover mutation from deliberate work in progress,
    so it refuses both rather than guessing -- and refuses BEFORE writing, so a
    dirty file is never read as a baseline. An untracked file is dirty by the
    same `git status` test, which is what makes this checkable without touching
    a real source.
    """
    relative, _ = scratch_module
    with pytest.raises(SystemExit) as raised:
        probe.assert_clean(relative)
    assert "refusing to mutate" in str(raised.value)
    assert relative in str(raised.value)


def test_every_mutant_restores_the_file_exactly(scratch_module):
    """Applying and reverting a mutant must be byte-identical to a no-op."""
    relative, path = scratch_module
    before = path.read_text(encoding="utf-8")

    mutants = probe.build_mutants(relative)
    assert mutants, "no mutants generated, so this test proves nothing"

    for mutant in mutants:
        original = probe._apply(relative, mutant)
        try:
            assert path.read_text(encoding="utf-8") != before, (
                "the mutation did not change the file, so it could never be "
                "killed and should not have been generated")
        finally:
            path.write_text(original, encoding="utf-8")
        assert path.read_text(encoding="utf-8") == before


def test_no_mutant_is_a_syntax_error():
    """A SyntaxError dies on import for reasons unrelated to any test.

    Those inflate the kill rate with mutants no suite could have survived. The
    first version mutated the arrow of ``-> str:`` into ``->= str:``; 4 of the
    first 7 contraction mutants were annotation arrows.
    """
    import ast

    for module, _ in probe.TARGETS:
        source = (ROOT / module).read_text(encoding="utf-8").splitlines()
        for mutant in probe.build_mutants(module):
            lines = list(source)
            lines[mutant.line_number - 1] = mutant.after
            try:
                ast.parse("\n".join(lines))
            except SyntaxError:  # pragma: no cover - the assertion is the point
                pytest.fail(f"{module}:{mutant.line_number} [{mutant.operator}] "
                            f"is a syntax error: {mutant.after.strip()}")


def test_no_mutant_lands_inside_a_string_literal_or_comment():
    """Those change only the text a human reads, so nothing can kill them.

    Measured before this was fixed: 3 of 13 matchgate survivors were message
    text, a 23% noise floor in the number the instrument exists to report.
    """
    for module, _ in probe.TARGETS:
        text = (ROOT / module).read_text(encoding="utf-8")
        spans = probe._string_spans(text)
        for mutant in probe.build_mutants(module):
            protected = spans.get(mutant.line_number, ())
            # Find where the two versions first diverge.
            column = next(index for index, (left, right)
                          in enumerate(zip(mutant.before, mutant.after))
                          if left != right)
            assert not any(low <= column < high for low, high in protected), (
                f"{module}:{mutant.line_number} mutates inside a string")
