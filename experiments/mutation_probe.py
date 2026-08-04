"""Which guards are actually reached? Break a line and see if anything notices.

QSigma-R1a produced six instances of one defect: a guard whose witness could
not reach the case it asserted.  Four were in the metric -- a residency test
whose witness had no entangling gate, a K3 suite that missed a whole class of
identity, an equivalence-freeze test listing seven of ten projection keys, a
saturation equivalence never evaluated at n = 0 -- and two were in this round's
own new code, including a matrix conjugation that was a no-op on every input,
guarded by a test using two examples symmetric under exactly the operation the
conjugation performed.

The suite passed through all six.  It was never going to catch them, because a
test suite reports whether its witnesses FAIL and never whether its witnesses
REACH.  Saturation gave the portfolio an instrument for "no strategy applies
here".  This is the corresponding instrument for "no test applies here".

Method.  Apply one small, meaning-changing edit to the source -- flip a
comparison, negate a condition, replace a returned constant -- then run the
module's own tests.  If they still pass, no test in that file distinguishes the
mutated code from the real code, and whatever that line does is unguarded.  A
surviving mutant is not automatically a defect: the line may be genuinely
untestable, or the mutation may be semantically null.  It IS a place where the
suite is silent, and every one of the six defects above lived in such a place.

This is deliberately not a general mutation-testing framework.  It is a fixed
list of operators aimed at the four simulation strategies and the saturation
flag, small enough to read in full and to run in a few minutes.

Run:  PYTHONPATH=src:experiments python3 experiments/mutation_probe.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: (module, its own test file).  A mutant is "killed" only by the tests written
#: for the module it damages; borrowing another module's tests would measure the
#: suite as a whole and hide which file is silent.
TARGETS = [
    ("src/aionq/contraction.py", "tests/test_contraction.py"),
    ("src/aionq/matchgate.py", "tests/test_matchgate.py"),
]

#: Each operator is (name, pattern, replacement).  They are chosen to change
#: MEANING rather than syntax: a mutant that is semantically identical to the
#: original can never be killed and would be noise in the survivor count.
#: The ``-`` in the lookbehind matters: without it, ``> `` matches the arrow of
#: a ``-> str:`` annotation and produces ``->= str:``, which is a SyntaxError.
#: Those die on import for reasons unrelated to any test, so they inflate the
#: kill rate with mutants no suite could have survived. Measured before the fix:
#: 4 of the first 7 contraction mutants were annotation arrows.
OPERATORS = [
    ("cmp: < to <=", re.compile(r"(?<![<>=!\-])< (?!=)"), "<= "),
    ("cmp: > to >=", re.compile(r"(?<![<>=!\-])> (?!=)"), ">= "),
    ("cmp: >= to >", re.compile(r">= "), "> "),
    ("cmp: <= to <", re.compile(r"<= "), "< "),
    ("eq: == to !=", re.compile(r" == "), " != "),
    ("eq: != to ==", re.compile(r" != "), " == "),
    ("bool: and to or", re.compile(r" and "), " or "),
    ("bool: or to and", re.compile(r" or "), " and "),
    ("bool: drop not", re.compile(r"if not "), "if "),
    ("const: True to False", re.compile(r"return True\b"), "return False"),
    ("const: False to True", re.compile(r"return False\b"), "return True"),
    ("arith: width + 1", re.compile(r"width \+ 1"), "width + 0"),
    ("arith: 0.0 to 1.0", re.compile(r"= 0\.0\b"), "= 1.0"),
    ("tol: atol scale", re.compile(r"_ATOL = 1e-9"), "_ATOL = 1e9"),
    ("cutoff: 64.0 to 0.0", re.compile(r"64\.0 \*"), "0.0 *"),
]

#: Lines that must not be mutated: docstrings and comments carry no behaviour,
#: and mutating them produces survivors that mean nothing.
_SKIP_LINE = re.compile(r"^\s*(#|\"\"\"|'''|$)")


def _string_spans(text: str) -> dict:
    """Column ranges occupied by string literals and comments, per line.

    Skipping whole comment lines is not enough.  A mutation landing INSIDE a
    string literal -- ``" and "`` in an error message, or ``det A != det B`` in
    an explanation -- changes only the text a human reads, so no test can ever
    kill it and it appears as a survivor that means nothing.  Measured on the
    validation run: 3 of 13 matchgate survivors were message text, which is a
    23% noise floor in the number the whole instrument exists to report.
    """
    import io
    import tokenize

    spans: dict = {}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError):  # pragma: no cover
        return spans
    for token in tokens:
        if token.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        (start_row, start_col), (end_row, end_col) = token.start, token.end
        for row in range(start_row, end_row + 1):
            low = start_col if row == start_row else 0
            high = end_col if row == end_row else 10 ** 6
            spans.setdefault(row, []).append((low, high))
    return spans


@dataclass
class Mutant:
    module: str
    line_number: int
    operator: str
    before: str
    after: str
    survived: bool = False


def _candidate_lines(text: str) -> list:
    inside_docstring = False
    out = []
    for index, line in enumerate(text.splitlines(), start=1):
        fences = line.count('"""') + line.count("'''")
        if inside_docstring:
            if fences:
                inside_docstring = False
            continue
        if fences == 1:
            inside_docstring = True
            continue
        if _SKIP_LINE.match(line):
            continue
        out.append((index, line))
    return out


def build_mutants(module: str) -> list:
    text = (ROOT / module).read_text(encoding="utf-8")
    spans = _string_spans(text)
    mutants: list[Mutant] = []
    for line_number, line in _candidate_lines(text):
        protected = spans.get(line_number, ())
        for name, pattern, replacement in OPERATORS:
            match = pattern.search(line)
            if match is None:
                continue
            if any(low <= match.start() < high for low, high in protected):
                continue        # inside a string literal or trailing comment
            mutated = line[:match.start()] + replacement + line[match.end():]
            if mutated != line:
                mutants.append(Mutant(module, line_number, name, line, mutated))
    return mutants


def _apply(module: str, mutant: Mutant) -> str:
    path = ROOT / module
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    target = lines[mutant.line_number - 1]
    ending = "\n" if target.endswith("\n") else ""
    lines[mutant.line_number - 1] = mutant.after + ending
    path.write_text("".join(lines), encoding="utf-8")
    return original


def run(module: str, tests: str, limit: int | None = None) -> list:
    mutants = build_mutants(module)
    if limit:
        mutants = mutants[:limit]
    path = ROOT / module
    print(f"\n{module}: {len(mutants)} mutants against {tests}")
    survivors = []
    for position, mutant in enumerate(mutants, start=1):
        original = _apply(module, mutant)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", tests, "-x", "-q",
                 "--no-header", "-p", "no:cacheprovider"],
                cwd=ROOT, capture_output=True, timeout=900,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT/'src'}:{ROOT/'experiments'}"},
            )
        finally:
            path.write_text(original, encoding="utf-8")
        mutant.survived = result.returncode == 0
        if mutant.survived:
            survivors.append(mutant)
        marker = "SURVIVED" if mutant.survived else "killed"
        print(f"  [{position:3d}/{len(mutants)}] line {mutant.line_number:4d} "
              f"{mutant.operator:<22} {marker}")
    return survivors


def main() -> int:
    all_survivors = []
    total = 0
    for module, tests in TARGETS:
        mutants = build_mutants(module)
        total += len(mutants)
        all_survivors.extend(run(module, tests))

    print("\n" + "=" * 72)
    killed = total - len(all_survivors)
    print(f"mutants {total}   killed {killed}   SURVIVED {len(all_survivors)}")
    if total:
        print(f"kill rate {100.0 * killed / total:.1f}%")
    if all_survivors:
        print("\nsurviving mutants -- lines no test in the module's own file "
              "distinguishes from the original:")
        for mutant in all_survivors:
            print(f"\n  {mutant.module}:{mutant.line_number}  [{mutant.operator}]")
            print(f"    was: {mutant.before.strip()}")
            print(f"    now: {mutant.after.strip()}")
        print("\nA survivor is not automatically a defect. It is a place where "
              "the suite is silent,\nand every one of this round's six defects "
              "lived in such a place.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
