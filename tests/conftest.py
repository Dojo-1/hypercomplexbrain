"""Repository-wide pytest hooks.

Part B's pre-execution gate after Part B executed
-------------------------------------------------
tests/test_part_b_preflight.py::test_live_repository_satisfies_every_non_numerical_preflight_gate
asserts that the full Part B preflight PASSES. It was written for the world
before execution, and it is one of the five C_pre paths: editing it would move
the preregistration anchor off d0650f0 -- exactly the defect a6d8b99
introduced, which tests/test_part_b_anchor.py now catches.

Part B executed (C_exec e96fa24 -> C_raw de60129 -> C_env 140dbe8). The
preflight now correctly REFUSES, because its outputs exist; refusing a second
execution is the gate doing its job. So once the outputs exist, that one test
is marked as a STRICT expected failure from here, outside the C_pre surface.
Strict: if it ever passes again while outputs exist, the suite fails. And
tests/test_part_b_result.py asserts the refusal has exactly one cause and that
every other preregistration gate still holds -- so this cannot hide a second
failure behind the first, which is how the preflight test's own skip once hid
an unsatisfiable anchor for seven weeks.
"""

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_FROZEN_TEST = "test_live_repository_satisfies_every_non_numerical_preflight_gate"


def _part_b_outputs_exist() -> bool:
    try:
        from aionq.part_b_preflight import OUTPUT_PATHS
    except Exception:
        return False
    return all((_ROOT / path).exists() for path in OUTPUT_PATHS)


def pytest_collection_modifyitems(config, items):
    if not _part_b_outputs_exist():
        return
    for item in items:
        if item.name == _FROZEN_TEST and item.fspath.basename == "test_part_b_preflight.py":
            item.add_marker(pytest.mark.xfail(
                strict=True,
                reason=("Part B has executed (C_env 140dbe8); the pre-execution gate now correctly "
                        "refuses because its outputs exist. Its single cause and the integrity of every "
                        "other gate are asserted in tests/test_part_b_result.py.")))
