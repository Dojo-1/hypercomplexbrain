"""A second axis: is the spectrum integrable, and it is not the axis already measured.

R1G measured a QFFO applied to the many-body spectrum of a free-fermion
Hamiltonian, found the free-fermion defect rise from 3e-15 to 1.02, and recorded
it as supplying "the parameterised transverse departure the portfolio lacks".

That claim is true on one axis and empty on another, and the second axis is the
one that matters for hardness.  A spectral multiplier ``f(H)`` has the **same
eigenvectors** as ``H``.  Same eigenvectors means the same conserved quantities,
so ``f(H)`` is exactly as integrable as ``H`` was.  It leaves the free-fermion
class algebraically -- the operator stops being quadratic in Majoranas -- while
changing nothing whatever about the dynamics.

The instrument that sees this is the level-spacing **ratio statistic**
(Oganesyan-Huse), ``<r> = <min(s_n, s_{n+1}) / max(s_n, s_{n+1})>`` over
consecutive gaps.  It needs no unfolding, which is what makes it usable on
spectra of very different scales -- a many-body Hamiltonian and the ordinates of
the Riemann zeta zeros, in the same units of nothing.

MEASURED, ``n = 10`` qubits, even-parity sector, 512 levels:

    free-fermion (quadratic Majorana)          <r> = 0.3090
    QFFO-excited f(H), same eigenvectors       <r> = 0.3086      <-- moves by 4e-4
    quadratic + quartic, g = 0.05              <r> = 0.5395
    quadratic + quartic, g = 0.2               <r> = 0.5773
    quadratic + quartic, g = 1.0               <r> = 0.5955

    Poisson reference (uncorrelated levels)          0.3853
    GUE reference (random Hermitian, 800x800)        0.5929
    RIEMANN ZETA ZEROS, first 400, measured          0.6166

So a quartic term carries the spectrum from the integrable end to the
Wigner-Dyson end, landing where the zeta zeros are -- the Montgomery-Odlyzko
correspondence, measured here rather than cited.  The QFFO carries it 0.0004.

WHY THE QFFO CANNOT MOVE IT, MECHANISTICALLY.  Two reasons, and the second was
found by fixing an overflow.  A function of ``H`` shares its eigenbasis, so no
reweighting of eigenvalues can change which quantities are conserved.  And the
QFFO's weights **saturate**: at ``sigma = 0.4``, ``varsigma = 0.3``, ``q = 0.5``
the Caputo branch gives 0.77473093 at ``n = 10`` and 0.77441397 at both ``n =
100`` and ``n = 2048``, identical to eight decimals.  On a spectrum of 512 levels
the multiplier is a constant times a transient in the first twenty, and a
constant rescaling cannot change ``<r>`` at all, because ``<r>`` is
scale-invariant by construction.

THE TWO AXES, WHICH ARE NOT THE SAME AXIS.

    gaussian_defect   ALGEBRAIC   is the operator quadratic in the Majoranas?
    <r>               DYNAMICAL   do the levels repel?

    QFFO excitation   moves the first, not the second.
    quartic term      moves both.

R1G reported one and generalised to the other.  This module measures both and
keeps them apart.

ON SECTORS.  A Majorana Hamiltonian commutes with the parity ``P = Z^(x)n``, so
its spectrum is the union of two sectors.  Statistics taken across an unresolved
symmetry look Poissonian whatever the dynamics, because independent sequences
interleave without repelling.  Everything above is computed inside the
even-parity sector alone; skipping that step is the standard way to measure
integrability that is not there.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

__all__ = [
    "POISSON",
    "GOE",
    "GUE",
    "ratio_statistic",
    "zeta_zeros",
    "parity_sector",
    "free_fermion_spectrum",
    "quartic_perturbation",
    "spectral_axis_report",
]

#: Analytic reference values for the ratio statistic.
POISSON = 0.38629      # 2 ln 2 - 1, uncorrelated levels
GOE = 0.5307
GUE = 0.5996

_ZEROS = Path(__file__).resolve().parents[2] / "artifacts" / "riemann_zeta_zeros_500.json"


def ratio_statistic(levels) -> float:
    """``<min(s_n, s_{n+1}) / max(s_n, s_{n+1})>`` over consecutive gaps.

    The reason to prefer this to the spacing distribution is that it requires no
    unfolding: it is invariant under any affine rescaling of the spectrum, so a
    512-level many-body spectrum and 400 zeta ordinates spanning 14 to 811 can be
    compared without choosing a smoothing of either density.  The same property
    is what makes it blind to the QFFO, whose action on a long spectrum is
    asymptotically a constant.
    """
    ordered = np.sort(np.asarray(levels, dtype=float))
    gaps = np.diff(ordered)
    gaps = gaps[gaps > 1e-10]
    if len(gaps) < 3:
        return float("nan")
    ratios = np.minimum(gaps[:-1], gaps[1:]) / np.maximum(gaps[:-1], gaps[1:])
    return float(np.mean(ratios))


def zeta_zeros(count: int = 400) -> np.ndarray:
    """Imaginary parts of the first nontrivial zeros, from a cached artifact.

    Cached rather than computed because ``mpmath.zetazero`` takes 87 seconds for
    500 of them, which does not belong in a test suite.  The cache is checked
    against a live recomputation of a handful in
    `tests/test_spectral_slice.py`, so it is pinned rather than trusted.
    """
    payload = json.loads(_ZEROS.read_text(encoding="utf-8"))
    return np.array(payload["zeros"][:count], dtype=float)


def parity_sector(matrix, qubits: int, even: bool = True) -> np.ndarray:
    """Restrict to one eigenspace of ``P = Z^(x)n``.

    Not optional.  A Majorana Hamiltonian commutes with the parity, so its
    spectrum is two interleaved sequences; statistics taken across them look
    Poissonian for any dynamics whatever, because independent sequences do not
    repel each other.  Measuring integrability that is not there is the standard
    failure of this instrument and this function is how it is avoided.
    """
    from .majorana import parity_operator

    diagonal = np.diag(parity_operator(qubits)).real
    keep = np.where(np.isclose(diagonal, 1.0 if even else -1.0))[0]
    return np.asarray(matrix)[np.ix_(keep, keep)]


def free_fermion_spectrum(qubits: int = 10, seed: int = 3):
    """A random quadratic Majorana Hamiltonian and its even-sector spectrum."""
    from .majorana import majorana_operators

    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(modes, modes))
    generator = (raw - raw.T) / 2.0
    hamiltonian = sum(
        1j * generator[left, right] * (operators[left] @ operators[right])
        for left in range(modes) for right in range(modes) if left < right)
    hamiltonian = (hamiltonian + hamiltonian.conj().T) / 2.0
    return hamiltonian, np.linalg.eigvalsh(parity_sector(hamiltonian, qubits))


def quartic_perturbation(qubits: int = 10, terms: int = 120, seed: int = 3):
    """A random quartic Majorana term: the interaction that breaks integrability.

    Quartic rather than quadratic is the whole distinction.  Quadratic terms
    generate the free-fermion group; quartic ones do not, and they are what carry
    the spectrum to Wigner-Dyson.
    """
    from .majorana import majorana_operators

    operators = majorana_operators(qubits)
    modes = 2 * qubits
    rng = np.random.default_rng(seed + 1)
    total = np.zeros((2 ** qubits, 2 ** qubits), dtype=complex)
    for quadruple in rng.choice(modes, size=(terms, 4)):
        if len(set(quadruple.tolist())) < 4:
            continue
        product = operators[quadruple[0]]
        for index in quadruple[1:]:
            product = product @ operators[index]
        total = total + float(rng.normal()) * product
    return (total + total.conj().T) / 2.0


def spectral_axis_report(qubits: int = 10, couplings=(0.05, 0.2, 1.0),
                         seed: int = 3) -> dict:
    """Both axes on the same family: algebraic departure and dynamical departure.

    Reporting them together is the point.  Either alone supports a conclusion the
    other refutes, which is exactly what happened in R1G.
    """
    from .qffo import MultiplierReading

    hamiltonian, spectrum = free_fermion_spectrum(qubits, seed)
    reading = MultiplierReading("caputo", 0.4, 0.3, 0.5)
    weights = np.array([reading.weight(index + 2) for index in range(len(spectrum))])

    rows = {
        "free_fermion": ratio_statistic(spectrum),
        "qffo_excited": ratio_statistic(weights * np.sort(spectrum)),
    }
    quartic = quartic_perturbation(qubits, seed=seed)
    for coupling in couplings:
        moved = parity_sector(hamiltonian + coupling * quartic, qubits)
        rows[f"quartic_g{coupling}"] = ratio_statistic(np.linalg.eigvalsh(moved))

    rows["zeta_zeros"] = ratio_statistic(zeta_zeros(400))
    rows["_qffo_shift"] = abs(rows["qffo_excited"] - rows["free_fermion"])
    rows["_quartic_shift"] = abs(rows[f"quartic_g{couplings[-1]}"] - rows["free_fermion"])
    rows["_weights_saturate"] = abs(reading.weight(100) - reading.weight(2048))
    return rows
