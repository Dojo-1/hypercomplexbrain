"""Stokes-Thimble routing: basis mutation at a singular crossing.

Specified in the Sigma-infinity thesis (section 12), which imports the
*structural distinction* from Picard-Lefschetz / Stokes geometry and explicitly
disclaims the theorem:

    Ordinary attention reweights a fixed basis.  A Stokes-Thimble Router changes
    the basis when the system crosses a singular regime ray.

The source structure
--------------------
For an irregular connection d/dw - (U + V/w), solutions have sector-dependent
asymptotics.  Crossing a Stokes ray relates the left and right fundamental
solutions by Y_left = Y_right S, where S is unipotent upper-triangular in a
suitable ordering.  The braid group acts on such Stokes data, mutating the
distinguished basis of thimbles rather than merely reweighting it.

What is imported
----------------
The distinction between *reweighting* and *mutating*.  A gated mixture changes
which fixed directions are emphasised.  A Stokes crossing changes what the
directions **are**: a component that was independent in one sector becomes a
combination of others in the next.  The mutation is recorded as a transport
event with provenance rather than absorbed silently into updated weights.

What is not imported
--------------------
Any claim that cognition realises an irregular connection, that Stokes matrices
exist in a learned model, or that the braid group acts on anything here beyond
the finite construction below.  Section 12 of the thesis calls this "explicitly
analogical and hypothesis-generating"; the same applies to this module.

The thesis pre-registers the kill condition (section 16, experiment 4):

    Kill: a standard gated mixture matches all metrics.

Its prediction is conditional -- mutation should help *only when the transition
truly changes basis*.  That conditional is the actual test, and it requires a
control condition in which the basis does NOT change.  A router that wins in
both conditions has merely bought capacity.  See :mod:`experiments.run_stokes`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["stokes_matrix", "braid_action", "is_unipotent_upper", "StokesRouter",
           "MutationRecord"]


def stokes_matrix(n: int, entries: dict | None = None, rng=None,
                  scale: float = 1.0) -> np.ndarray:
    """A unipotent upper-triangular Stokes matrix.

    Unit diagonal, arbitrary strictly-upper entries.  This is the shape a Stokes
    matrix takes once the sectors are ordered, and the shape that makes the
    crossing a *basis change* rather than a rescaling: determinant 1, no
    direction is stretched, but directions mix.
    """
    s = np.eye(n)
    if entries:
        for (i, j), v in entries.items():
            if i >= j:
                raise ValueError("Stokes entries must be strictly upper-triangular")
            s[i, j] = v
    elif rng is not None:
        for i in range(n):
            for j in range(i + 1, n):
                s[i, j] = rng.normal() * scale
    return s


def is_unipotent_upper(s: np.ndarray, atol: float = 1e-9) -> bool:
    """Unit diagonal and zero below it."""
    return bool(np.allclose(np.diag(s), 1.0, atol=atol)
                and np.allclose(np.tril(s, -1), 0.0, atol=atol))


def braid_action(s: np.ndarray, i: int) -> np.ndarray:
    """Action of the braid generator sigma_i on Stokes data.

    Swaps sectors i and i+1 and re-triangularises, which is how a distinguished
    basis of thimbles mutates under monodromy.  Implemented as conjugation by
    the transposition followed by restoration of upper-triangular form.
    """
    n = s.shape[0]
    if not 0 <= i < n - 1:
        raise ValueError(f"braid generator index {i} out of range for n={n}")
    p = np.eye(n)
    p[[i, i + 1]] = p[[i + 1, i]]
    t = p @ s @ p
    # Restore unipotent upper form: keep the strict upper part, unit diagonal.
    out = np.triu(t, 1) + np.eye(n)
    return out


@dataclass
class MutationRecord:
    """A basis change carried out with provenance, not hidden in the weights."""

    at_step: int
    sector_from: int
    sector_to: int
    matrix: np.ndarray
    reason: str = ""

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"step {self.at_step}: sector {self.sector_from} -> {self.sector_to}"
                f"{f' ({self.reason})' if self.reason else ''}")


@dataclass
class StokesRouter:
    """Holds a basis and mutates it at declared sector crossings.

    The router is deliberately thin.  It owns one linear basis and a Stokes
    matrix per crossing; it does not add experts, capacity or gating. That is
    the point of the comparison: if a gated mixture matches it, the extra
    structure has bought nothing that capacity would not.
    """

    basis: np.ndarray
    sector: int = 0
    history: list = field(default_factory=list)

    def mutate(self, s: np.ndarray, at_step: int = 0, reason: str = "") -> np.ndarray:
        """Apply a Stokes matrix: the basis becomes a combination of itself."""
        if not is_unipotent_upper(s):
            raise ValueError("a Stokes crossing must be unipotent upper-triangular")
        self.basis = self.basis @ s
        self.history.append(MutationRecord(at_step, self.sector, self.sector + 1,
                                           s.copy(), reason))
        self.sector += 1
        return self.basis

    def project(self, x: np.ndarray) -> np.ndarray:
        """Coordinates of x in the current basis (least squares)."""
        coef, *_ = np.linalg.lstsq(self.basis, np.asarray(x, dtype=float).T, rcond=None)
        return coef.T

    @property
    def n_parameters(self) -> int:
        """Basis entries plus the strictly-upper entries of each mutation."""
        n = self.basis.shape[1]
        return int(self.basis.size + len(self.history) * n * (n - 1) // 2)
