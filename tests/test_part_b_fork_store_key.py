"""Part B execution attempt 1: why the fork cannot store at a held-out depth.

equal_resource_reservoir._signed_codebooks builds each store key with
f"{rho:.1f}" -- ONE decimal place -- and the store checks it against the
frozen decimal label. Every sealed depth has one decimal digit, so the format
is exact there and every check run at the sealed grid is blind to it. Every
held-out depth breaks it. The sealed code fails closed, so no wrong number was
ever computed; these tests pin the failure without computing any metric, and
must be revisited by whichever round repairs the key.
"""

import pytest

from aionq.common_receiver_parametric import SEALED_GRID, build_fork
from aionq.part_b_preflight import EFFECTIVE_PROTOCOL_DIGEST, HELD_OUT_DEPTH_COORDS
from aionq.self_audit import repo_root

LICENCE = repo_root() / "artifacts" / "r6m_parametric_equivalence" / "equivalence.json"
HELD_OUT = tuple((decimal, value) for _, decimal, value in HELD_OUT_DEPTH_COORDS)


def _store_path(grid, licence=None):
    fork = build_fork(grid, licence=licence)
    crr = fork.common_receiver
    reservoir = crr._ProtocolReservoir(crr.plan_protocol(EFFECTIVE_PROTOCOL_DIGEST),
                                       crr.HashChainedEventLedger())
    fork.equal_resource.build_map_tasks("R6", reservoir)


def test_the_one_decimal_key_is_exact_on_every_sealed_depth_and_no_held_out_one():
    for decimal, value in SEALED_GRID:
        assert f"{value:.1f}" == decimal
    for decimal, value in HELD_OUT:
        assert f"{value:.1f}" != decimal
    # and it cannot tell two held-out depths apart
    assert f"{0.20:.1f}" == f"{0.25:.1f}"


def test_the_fork_stores_at_the_sealed_grid():
    _store_path(SEALED_GRID)


def test_the_fork_cannot_store_at_a_held_out_depth():
    with pytest.raises(ValueError, match="reservoir key differs from the portable store identity"):
        _store_path(HELD_OUT, LICENCE)


def test_the_pre_run_check_took_the_path_that_does_not_store():
    """reservoir=None skips the store-key path entirely -- which is how the
    pre-run input check passed while the run could not."""
    fork = build_fork(HELD_OUT, licence=LICENCE)
    tasks, _ = fork.equal_resource.build_map_tasks("R6")
    assert tasks
