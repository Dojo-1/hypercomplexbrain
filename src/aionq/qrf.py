"""Quantum reference frames: entanglement is frame-relative.

The draft asserts that whether a description shows entanglement can depend on
the quantum reference frame, and uses this to found the self/other distinction
relationally rather than by external fiat.  The assertion is correct and it has
a two-line demonstration, which is worth having in executable form because it is
the cleanest available refutation of "entanglement = quantumness".

Setup: three systems A, B, C carrying Z_2 positions, with the frame change
implemented by the discrete translation

    S_{A->B} : |x>_B |y>_C  ->  |-x>_A |y - x>_C

A state that is a product in A's perspective becomes maximally entangled in B's
perspective.  Entanglement therefore cannot be an invariant of the architecture,
and cannot be what Q_cert measures.  See :mod:`aionq.residency`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["frame_change_operator", "FrameComparison", "compare_frames",
           "entanglement_entropy"]


def entanglement_entropy(state: np.ndarray, d: int = 2) -> float:
    """Von Neumann entropy across the bipartition of a two-qudit pure state."""
    mat = np.asarray(state, dtype=complex).reshape(d, d)
    svals = np.linalg.svd(mat, compute_uv=False)
    probs = np.clip(svals ** 2, 1e-18, None)
    probs = probs / probs.sum()
    return float(-np.sum(probs * np.log2(probs)))


def frame_change_operator(d: int = 2) -> np.ndarray:
    """S_{A->B} for Z_d translations: |x>_B |y>_C -> |-x>_A |y-x>_C."""
    op = np.zeros((d * d, d * d), dtype=complex)
    for x in range(d):
        for y in range(d):
            src = x * d + y                       # |x>_B |y>_C
            dst = ((-x) % d) * d + ((y - x) % d)  # |-x>_A |y-x>_C
            op[dst, src] = 1.0
    return op


@dataclass
class FrameComparison:
    """Entanglement of the same physical situation seen from two frames."""

    entropy_in_a: float
    entropy_in_b: float

    @property
    def frame_dependent(self) -> bool:
        return abs(self.entropy_in_a - self.entropy_in_b) > 1e-9

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"entanglement seen from A : {self.entropy_in_a:.4f} bits",
            f"entanglement seen from B : {self.entropy_in_b:.4f} bits",
            f"frame dependent          : {self.frame_dependent}",
        ])


def compare_frames(state_in_a: np.ndarray | None = None, d: int = 2) -> FrameComparison:
    """Compare entanglement of `state_in_a` before and after a frame change.

    Default input is the product state (|0> + |1>)/sqrt(2) _B (x) |0>_C, which
    carries zero entanglement in A's frame and one full bit in B's frame.
    """
    if state_in_a is None:
        state_in_a = np.zeros(d * d, dtype=complex)
        state_in_a[0 * d + 0] = 1 / np.sqrt(2)  # |0>_B |0>_C
        state_in_a[1 * d + 0] = 1 / np.sqrt(2)  # |1>_B |0>_C

    state_in_a = np.asarray(state_in_a, dtype=complex)
    state_in_a = state_in_a / np.linalg.norm(state_in_a)
    state_in_b = frame_change_operator(d) @ state_in_a

    return FrameComparison(
        entropy_in_a=entanglement_entropy(state_in_a, d),
        entropy_in_b=entanglement_entropy(state_in_b, d),
    )
