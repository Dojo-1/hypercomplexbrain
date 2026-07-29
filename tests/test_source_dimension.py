"""Which dimension the ceiling counts (QSigma-R6j)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.holevo_sandwich import holevo_chi
from aionq.source_dimension import (decay_exponent, encode_at_size,
                                    sl2c_element, sl2r_element,
                                    source_gap_sweep)


def test_the_two_sources_really_do_differ_in_dimension():
    """SL(2,C) must actually be complex, or the whole comparison is vacuous."""
    M = sl2c_element(1.0, 0.4, 0.9, 1.1)
    assert np.max(np.abs(M.imag)) > 1e-6
    assert np.max(np.abs(sl2r_element(1.0, 0.4, 0.9).imag)) < 1e-12
    for X in (M, sl2r_element(1.0, 0.4, 0.9)):
        assert abs(abs(np.linalg.det(X)) - 1.0) < 1e-9


def test_carrier_is_identical_for_both_sources():
    """Same five dimensions. Only the source manifold grows."""
    for M in (sl2r_element(1.0, 0.3, 0.2), sl2c_element(1.0, 0.3, 0.2, 0.7)):
        W, _ = encode_at_size(M, 2)
        assert W.shape == (5, 5)


def test_richer_source_does_help_at_finite_depth():
    """The part I first denied. My summary said 'zero'; my own table said 9.3e-02."""
    s = source_gap_sweep()
    assert s["richer_source_helps_at_finite_depth"]
    assert s["rows"][0]["gap"] > 1e-2


def test_the_advantage_is_consumed_at_the_compactification_rate():
    """The gap decays as e^{-4 rho} -- R6b's radial-QFI exponent."""
    e = decay_exponent(source_gap_sweep())
    assert e["matches_four"]
    assert e["final"] == pytest.approx(4.0, abs=1e-3)


def test_at_the_boundary_source_dimension_is_invisible():
    """Twice the source dimension, identical chi to 1e-13."""
    two_pi, N, rho = 2.0 * math.pi, 64, 8.0
    bR = [encode_at_size(sl2r_element(rho, two_pi * k / N, two_pi * (3 * k % N) / N), 2)[0]
          for k in range(N)]
    bC = [encode_at_size(sl2c_element(rho, two_pi * k / N, two_pi * (3 * k % N) / N,
                                      two_pi * (5 * k % N) / N), 2)[0]
          for k in range(N)]
    assert holevo_chi(bR) == pytest.approx(1.0, abs=1e-9)
    assert holevo_chi(bC) == pytest.approx(holevo_chi(bR), abs=1e-13)
