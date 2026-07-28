"""The Hopf/Cartan layer: exact tests, because every claim here is an identity."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionq.cayley_dickson import find_zero_divisor
from aionq.hopf_layer import (bloch_vector, fibre_is_local_unitary, hopf_ladder,
                              hopf_map, kak_decompose, kak_reconstruct,
                              projective_volume, swirl_to_kak)
from aionq.hyperbolic_qubit import swirl_point, to_sl2
from aionq.quantum_channel_geometry import attempted_use_state

RNG = np.random.default_rng(20260728)
POINTS = [(RNG.uniform(0.05, 3.0), RNG.uniform(-math.pi, math.pi),
           RNG.uniform(-math.pi, math.pi)) for _ in range(40)]


# ------------------------------------------------- swirl coordinates are KAK

@pytest.mark.parametrize("point", POINTS[:20])
def test_kak_reconstructs_the_matrix(point):
    M = to_sl2(swirl_point(*point))
    d = kak_decompose(M)
    assert np.max(np.abs(kak_reconstruct(d["alpha"], d["rho"], d["beta"]) - M)) < 1e-12


@pytest.mark.parametrize("point", POINTS[:20])
def test_cartan_parameter_is_the_swirl_depth(point):
    rho, _, _ = point
    assert kak_decompose(to_sl2(swirl_point(*point)))["rho"] == pytest.approx(rho, abs=1e-12)


@pytest.mark.parametrize("point", POINTS)
def test_swirl_angles_are_the_cartan_angles(point):
    """alpha = -(phi-psi)/2 and beta = (phi+psi)/2, modulo pi.

    Compared on doubled angles because (U,V) -> (-U,-V) leaves M unchanged, so the
    KAK angles are only defined mod pi. Comparing them directly would fail for a
    reason that has nothing to do with the claim.
    """
    rho, phi, psi = point
    d = kak_decompose(to_sl2(swirl_point(*point)))
    a_pred, b_pred = swirl_to_kak(phi, psi)
    assert abs(np.exp(2j * d["alpha"]) - np.exp(2j * a_pred)) < 1e-12
    assert abs(np.exp(2j * d["beta"]) - np.exp(2j * b_pred)) < 1e-12


@pytest.mark.parametrize("point", POINTS[:15])
def test_compact_motion_preserves_the_spectrum(point):
    """The mechanism behind R6b's saturating angular Fisher information.

    A compact step is a local unitary: it moves the state within its unitary orbit
    and changes no singular value. The non-compact direction changes the singular
    values, which is what decays. If this failed, free-vs-costly would not be the
    compact/non-compact split.
    """
    M = to_sl2(swirl_point(*point))
    for delta in (0.1, 0.7, -1.3):
        r = fibre_is_local_unitary(M, delta)
        assert r["spectrum_preserved"]
        assert r["max_singular_value_change"] < 1e-12


def test_noncompact_motion_does_change_the_spectrum():
    """The contrast that makes the previous test mean something."""
    a = np.linalg.svd(to_sl2(swirl_point(1.0, 0.3, 0.7)), compute_uv=False)
    b = np.linalg.svd(to_sl2(swirl_point(1.4, 0.3, 0.7)), compute_uv=False)
    assert np.max(np.abs(a - b)) > 0.1


# ---------------------------------------------------------- the Hopf map itself

def test_hopf_map_is_the_bloch_vector():
    rng = np.random.default_rng(3)
    for _ in range(100):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi = psi / np.linalg.norm(psi)
        assert np.allclose(hopf_map(psi), bloch_vector(psi), atol=1e-12)


def test_the_hopf_fibre_is_the_global_phase():
    rng = np.random.default_rng(4)
    for _ in range(100):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi = psi / np.linalg.norm(psi)
        phased = np.exp(1j * rng.uniform(0, 2 * math.pi)) * psi
        assert np.allclose(hopf_map(psi), hopf_map(phased), atol=1e-12)


def test_hopf_image_lies_on_the_unit_sphere():
    rng = np.random.default_rng(5)
    for _ in range(50):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi = psi / np.linalg.norm(psi)
        assert np.linalg.norm(hopf_map(psi)) == pytest.approx(1.0, abs=1e-12)


# ------------------------------------------------------ the projective quotient

@pytest.mark.parametrize("point", POINTS[:15])
def test_the_state_cannot_see_the_sign_of_A(point):
    """Exactly 0.0, not 1e-16: |v><v| is quadratic in v, so the sign cancels."""
    M = to_sl2(swirl_point(*point))
    WA, pA = attempted_use_state(M)
    WB, pB = attempted_use_state(-M)
    assert np.max(np.abs(WA - WB)) == 0.0
    assert pA == pB


def test_projective_quotient_halves_the_operational_volume():
    """The step the external derivation reported as deferred."""
    v = projective_volume()
    assert v["quotient_order"] == 2
    assert v["quotiented"] == pytest.approx(math.pi ** 3 / math.sqrt(2.0), rel=1e-12)
    assert v["quotiented"] == pytest.approx(v["unquotiented"] / 2.0, rel=1e-12)
    assert math.isfinite(v["quotiented"])


# ------------------------------------------------------------------ the ladder

def test_the_ladder_has_exactly_four_rungs():
    rungs = [r for r in hopf_ladder() if r["fibration"] is not None]
    assert [r["dim"] for r in rungs] == [1, 2, 4, 8]
    assert all(r["is_division_algebra"] for r in rungs)


def test_the_ladder_stops_where_zero_divisors_start():
    """Not cited -- computed, by the module that already had the answer."""
    ladder = {r["dim"]: r for r in hopf_ladder()}
    assert ladder[16]["is_division_algebra"] is False
    assert ladder[16]["fibration"] is None
    assert find_zero_divisor(16) is not None      # sedenions: zero divisors exist
    assert find_zero_divisor(8) is None           # octonions: none


def test_associativity_fails_one_rung_before_the_ladder_ends():
    """Octonions are non-associative AND still a division algebra.

    The distinction matters for S8: losing associativity did not end the tower;
    losing the division property did. The Fano/octonion work sits on the last
    rung by necessity.
    """
    ladder = {r["dim"]: r for r in hopf_ladder()}
    assert ladder[8]["associative"] is False
    assert ladder[8]["is_division_algebra"] is True
