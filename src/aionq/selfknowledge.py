"""The quantum Goedelian bound: no-cloning is sharper than Loeb.

The draft architecture places the Anti-Loeb evidence membrane outside the
quantum core and justifies it logically: a system cannot promote its own fixed
points to truth without external witness.  That is correct but it is the weaker
argument, and it leaves the impression that the external membrane is a
governance choice which a sufficiently clever design might one day internalise.

It cannot be internalised, and the reason is physical rather than logical.

A quantum system cannot determine its own state by internal measurement.
Estimating an unknown state requires many identically prepared copies; no-cloning
forbids the system from producing them from itself.  Any internal measurement
that extracts information about the identity register necessarily disturbs it.
So for a quantum brain:

    self-knowledge and self-preservation are complementary.

The identity signature J_t of the draft is therefore not something the brain can
read off itself.  It is a quantity that only an external party -- or a past
self that has already paid the disturbance -- can estimate.  This is the correct
quantum lift of the Anti-Loeb membrane, and it is stronger than the logical
version: Loeb says self-certification is unsound, no-cloning says self-tomography
is impossible.

This module makes the trade-off numerical via a weak-measurement family.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = ["SelfKnowledgepoint", "self_knowledge_tradeoff", "weak_measurement",
           "copies_for_self_tomography"]


def _entropy(probs: np.ndarray) -> float:
    p = np.clip(np.asarray(probs, dtype=float), 1e-18, None)
    p = p / p.sum()
    return float(-np.sum(p * np.log2(p)))


def weak_measurement(strength: float) -> list[np.ndarray]:
    """Kraus operators of a weak Z measurement of the given strength.

    ``strength = 0`` is the identity channel (no information, no disturbance);
    ``strength = 1`` is a projective Z measurement (maximal information, maximal
    disturbance to any X-basis identity observable).
    """
    lam = float(np.clip(strength, 0.0, 1.0))
    theta = math.asin(math.sqrt(lam)) if lam <= 1.0 else math.pi / 2
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    # Two-outcome POVM interpolating identity -> projective Z
    k0 = np.array([[math.cos(theta / 2 + math.pi / 4), 0],
                   [0, math.sin(theta / 2 + math.pi / 4)]], dtype=complex)
    k1 = np.array([[math.sin(theta / 2 + math.pi / 4), 0],
                   [0, math.cos(theta / 2 + math.pi / 4)]], dtype=complex)
    del c, s
    return [k0, k1]


@dataclass
class SelfKnowledgePoint:
    """One point on the information/disturbance frontier."""

    strength: float
    info_gain_bits: float     # mutual information about the identity bit
    fidelity_retained: float  # fidelity of the post-measurement identity state

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"strength {self.strength:.2f} -> "
                f"{self.info_gain_bits:.4f} bits self-knowledge, "
                f"identity fidelity {self.fidelity_retained:.4f}")


# Backwards-compatible alias for the dataclass name used in __all__.
SelfKnowledgepoint = SelfKnowledgePoint


def self_knowledge_tradeoff(strengths=None) -> list[SelfKnowledgePoint]:
    """Information/disturbance frontier for a cell measuring its own identity.

    The identity register is prepared in one of two non-orthogonal states -- the
    realistic case, since a cell that already knew which orthogonal state it was
    in would have nothing to learn.  Internal measurement then trades knowledge
    against the very structure it is trying to certify.
    """
    if strengths is None:
        strengths = np.linspace(0.0, 1.0, 11)

    # Two non-orthogonal candidate identity states.
    plus = np.array([1, 1], dtype=complex) / math.sqrt(2)
    zero = np.array([1, 0], dtype=complex)
    ensemble = [(0.5, plus), (0.5, zero)]

    points: list[SelfKnowledgePoint] = []
    for lam in strengths:
        kraus = weak_measurement(float(lam))

        # Outcome distribution per candidate, and post-measurement fidelity.
        joint = np.zeros((len(ensemble), len(kraus)))
        fid_total = 0.0
        for i, (prior, vec) in enumerate(ensemble):
            rho = np.outer(vec, vec.conj())
            for j, k in enumerate(kraus):
                post = k @ rho @ k.conj().T
                p = float(np.real(np.trace(post)))
                joint[i, j] = prior * p
                if p > 1e-15:
                    post_n = post / p
                    # Average over outcomes: weight by the outcome probability.
                    fid_total += prior * p * float(np.real(vec.conj() @ post_n @ vec))

        px = joint.sum(axis=1)
        py = joint.sum(axis=0)
        info = _entropy(px) + _entropy(py) - _entropy(joint.ravel())

        points.append(SelfKnowledgePoint(
            strength=float(lam),
            info_gain_bits=max(0.0, info),
            fidelity_retained=fid_total,
        ))

    return points


def copies_for_self_tomography(dim: int, epsilon: float) -> int:
    """Copies needed to estimate a d-dimensional state to trace distance eps.

    Optimal full state tomography needs Theta(d^2 / eps^2) copies.  A brain
    cannot manufacture these copies of itself: no-cloning forbids it.  The number
    is reported to make the impossibility quantitative -- it is the size of the
    external witness burden the architecture must budget for, per identity audit.
    """
    return int(math.ceil(dim ** 2 / (epsilon ** 2)))
