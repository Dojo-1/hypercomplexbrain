"""R1U: exact regular actions of Z4 x Z4 and Z4 semidirect Z4.

The non-abelian action is the inversion semidirect product

    a^4 = b^4 = e,   b a b^-1 = a^-1.

Both groups have 16 elements and therefore act on exactly the same 16-label
carrier by the left-regular representation.  Time-dependent noise is represented
by a frozen generator word; the same realized word is used for both groups.
"""
from __future__ import annotations

import numpy as np

N = 4
LABELS = 16
TOKENS = ("a", "b", "A", "B")


def encode(g: tuple[int, int]) -> int:
    i, j = g
    return (j % N) * N + (i % N)


def decode(x: int) -> tuple[int, int]:
    return (int(x) % N, (int(x) // N) % N)


def multiply(g, h, *, nonabelian: bool) -> tuple[int, int]:
    i, j = g
    k, l = h
    if nonabelian and (j % 2):
        k = -k
    return ((i + k) % N, (j + l) % N)


def inverse(g, *, nonabelian: bool) -> tuple[int, int]:
    for i in range(N):
        for j in range(N):
            h = (i, j)
            if (multiply(g, h, nonabelian=nonabelian) == (0, 0)
                    and multiply(h, g, nonabelian=nonabelian) == (0, 0)):
                return h
    raise AssertionError("group inverse not found")


def generator(token: str) -> tuple[int, int]:
    return {"a": (1, 0), "A": (3, 0), "b": (0, 1), "B": (0, 3)}[token]


def word_product(word, *, nonabelian: bool) -> tuple[int, int]:
    g = (0, 0)
    for token in word:
        g = multiply(g, generator(token), nonabelian=nonabelian)
    return g


def left_regular_permutation(g, *, nonabelian: bool) -> np.ndarray:
    perm = np.empty(LABELS, dtype=int)
    for x in range(LABELS):
        perm[x] = encode(multiply(g, decode(x), nonabelian=nonabelian))
    return perm


def apply_permutation(state: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    out = np.zeros_like(np.asarray(state, dtype=np.complex128))
    out[np.asarray(permutation, dtype=int)] = state
    return out


def apply_word(state: np.ndarray, word, *, nonabelian: bool) -> np.ndarray:
    out = np.asarray(state, dtype=np.complex128)
    for token in word:
        out = apply_permutation(
            out,
            left_regular_permutation(generator(token), nonabelian=nonabelian),
        )
    return out


def base_word(length: int = 24) -> tuple[str, ...]:
    motif = ("a", "b", "A", "B", "a", "b", "a", "B")
    return tuple(motif[i % len(motif)] for i in range(length))


def noise_probability(profile: str, t: int, length: int) -> float:
    if profile == "ramp":
        return 0.05 + 0.45 * (t / max(1, length - 1))
    if profile == "sinusoid":
        return 0.05 + 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * t / max(1, length - 1)))
    if profile == "burst":
        centre = (length - 1) / 2
        return 0.65 if abs(t - centre) <= 2.5 else 0.05
    raise ValueError(f"unknown profile {profile!r}")


def noisy_word(seed: int, profile: str, length: int = 24) -> tuple[str, ...]:
    rng = np.random.default_rng(seed)
    out = []
    for t, token in enumerate(base_word(length)):
        if rng.random() < noise_probability(profile, t, length):
            choices = [candidate for candidate in TOKENS if candidate != token]
            token = choices[int(rng.integers(len(choices)))]
        out.append(token)
    return tuple(out)


def permutation_disagreement(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.asarray(a) != np.asarray(b)))
