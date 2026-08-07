from __future__ import annotations

import numpy as np

from aionq.semidirect_noise import (
    apply_word,
    decode,
    generator,
    inverse,
    left_regular_permutation,
    multiply,
    noisy_word,
    word_product,
)


def test_group_presentations_and_regular_actions():
    e = (0, 0)
    a, b = generator("a"), generator("b")
    assert multiply(multiply(b, a, nonabelian=True), inverse(b, nonabelian=True), nonabelian=True) == inverse(a, nonabelian=True)
    assert word_product(("a", "b", "A", "B"), nonabelian=False) == e
    assert word_product(("a", "b", "A", "B"), nonabelian=True) != e
    for nonabelian in (False, True):
        for x in range(16):
            g = decode(x)
            assert multiply(g, inverse(g, nonabelian=nonabelian), nonabelian=nonabelian) == e
            assert sorted(left_regular_permutation(g, nonabelian=nonabelian).tolist()) == list(range(16))


def test_abelian_forward_reverse_endpoint_is_identical():
    for profile in ("ramp", "sinusoid", "burst"):
        for seed in range(8):
            word = noisy_word(seed, profile, 24)
            assert word_product(word, nonabelian=False) == word_product(tuple(reversed(word)), nonabelian=False)


def test_zero_word_is_identity():
    rng = np.random.default_rng(11)
    state = rng.normal(size=16) + 1j * rng.normal(size=16)
    state /= np.linalg.norm(state)
    assert np.allclose(apply_word(state, (), nonabelian=True), state)
