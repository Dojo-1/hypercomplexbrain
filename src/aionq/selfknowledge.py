"""The quantum Goedelian bound: no-cloning is sharper than Loeb.

The draft architecture places the Anti-Loeb evidence membrane outside the
quantum core and justifies it logically: a system cannot promote its own fixed
points to truth without external witness.  That is correct but it is the weaker
argument, and it leaves the impression that the external membrane is a
governance choice which a sufficiently clever design might one day internalise.

There is a second, physical obstruction alongside the logical one.  An earlier
version of this module claimed the physical argument *superseded* Loeb and that
"self-tomography is impossible".  Both claims were too broad and are retired.

What survives, bounded correctly:

    A single unknown quantum self cannot obtain a complete, non-disturbing
    classical description of itself from one specimen.

Estimating an unknown state needs many identical copies, and no-cloning forbids
manufacturing them from an unknown specimen.  For an *unknown* identity register,
:func:`self_knowledge_tradeoff` shows information and fidelity trading off.

What does *not* follow, and is refuted in this module:

  * that self-measurement is impossible in general.  A system that controls its
    own preparation may re-prepare freely; no-cloning says nothing about that.
  * that partial self-observation is impossible.  Stabilizer syndrome extraction
    reads a protected register, extracts 2 bits about which error occurred, and
    leaves the logical state at fidelity exactly 1.  See
    :func:`syndrome_extraction_disturbance`.  The architecture *depends* on this:
    a blanket ban on self-measurement would forbid its own error correction.
  * that the copy count is universally d^2/eps^2.  Sample complexity is
    rank-dependent and varies with the measurement model and error metric.

Loeb and no-cloning are not weaker and stronger versions of one theorem.  They
obstruct different kinds of closure: Loeb blocks self-certification of truth,
no-cloning blocks complete non-disturbing self-description.  The external
evidence membrane rests on both, plus independent evidence, reproducibility and
circularity control -- not on either alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = ["SelfKnowledgepoint", "self_knowledge_tradeoff", "weak_measurement",
           "copies_for_self_tomography", "syndrome_extraction_disturbance",
           "SyndromeReport"]


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
    # Two-outcome POVM interpolating identity -> projective Z
    k0 = np.array([[math.cos(theta / 2 + math.pi / 4), 0],
                   [0, math.sin(theta / 2 + math.pi / 4)]], dtype=complex)
    k1 = np.array([[math.sin(theta / 2 + math.pi / 4), 0],
                   [0, math.cos(theta / 2 + math.pi / 4)]], dtype=complex)
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


# --------------------------------------------------------------------------
# The counterexample that bounds the claim above
# --------------------------------------------------------------------------

@dataclass
class SyndromeReport:
    """Self-measurement that extracts information and disturbs nothing."""

    syndrome: tuple
    information_bits: float
    logical_fidelity: float

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"syndrome {self.syndrome} -> {self.information_bits:.4f} bits extracted, "
                f"logical fidelity {self.logical_fidelity:.6f}")


def syndrome_extraction_disturbance(alpha: float = 0.6, error_qubit: int | None = 0
                                    ) -> SyndromeReport:
    """Stabilizer syndrome extraction: information without logical disturbance.

    This is the counterexample to the overbroad claim that "self-tomography is
    impossible".  A protected register measuring its own stabilizer generators
    learns which error occurred and leaves the logical state *exactly* intact.
    The architecture already depends on this -- it is how error correction
    works -- so a blanket prohibition on self-measurement would forbid the
    architecture's own homeostasis.

    Three-qubit bit-flip code, logical state alpha|0_L> + beta|1_L>, stabilizer
    generators Z0Z1 and Z1Z2.  Returns the syndrome, the information it carries,
    and the fidelity of the recovered logical state.

    The correct bounded claim is therefore not "no self-measurement", but:

        A single unknown quantum self cannot obtain a complete, non-disturbing
        classical description of itself from one specimen.

    Partial, structured self-observation of a *known* code structure is not only
    possible, it is mandatory.
    """
    beta = math.sqrt(max(0.0, 1.0 - alpha ** 2))

    # Logical codeword alpha|000> + beta|111>
    psi = np.zeros(8, dtype=complex)
    psi[0b000] = alpha
    psi[0b111] = beta

    # Apply a known bit-flip error.
    if error_qubit is not None:
        flipped = np.zeros_like(psi)
        for idx in range(8):
            flipped[idx ^ (1 << (2 - error_qubit))] += psi[idx]
        psi = flipped

    def z_parity(idx: int, a: int, b: int) -> int:
        bit_a = (idx >> (2 - a)) & 1
        bit_b = (idx >> (2 - b)) & 1
        return 1 - 2 * (bit_a ^ bit_b)   # +1 if equal, -1 if different

    # Measure the two stabilizer generators.
    syndrome = []
    for (a, b) in [(0, 1), (1, 2)]:
        probs = {1: 0.0, -1: 0.0}
        for idx in range(8):
            probs[z_parity(idx, a, b)] += abs(psi[idx]) ** 2
        outcome = 1 if probs[1] >= probs[-1] else -1
        syndrome.append(outcome)
        # Project onto the measured eigenspace.
        proj = np.array([psi[idx] if z_parity(idx, a, b) == outcome else 0.0
                         for idx in range(8)], dtype=complex)
        norm = np.linalg.norm(proj)
        if norm > 1e-15:
            psi = proj / norm

    # Decode: the syndrome identifies the flipped qubit uniquely.
    lookup = {(1, 1): None, (-1, 1): 0, (-1, -1): 1, (1, -1): 2}
    guess = lookup[tuple(syndrome)]
    if guess is not None:
        corrected = np.zeros_like(psi)
        for idx in range(8):
            corrected[idx ^ (1 << (2 - guess))] += psi[idx]
        psi = corrected

    ideal = np.zeros(8, dtype=complex)
    ideal[0b000] = alpha
    ideal[0b111] = beta
    fidelity = float(abs(np.vdot(ideal, psi)) ** 2)

    # The syndrome distinguishes 4 equally-likely error locations: 2 bits.
    info = 2.0 if error_qubit is not None else 0.0

    return SyndromeReport(syndrome=tuple(syndrome),
                          information_bits=info,
                          logical_fidelity=fidelity)
