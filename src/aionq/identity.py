"""Polyholonomic identity, with the Gram theorem proved rather than posed.

The draft defines the identity signature as a hierarchy of holonomy overlaps

    G_{rs} = Tr(rho H_r^dagger H_s)

and lists "prove G is Hermitian positive semidefinite" as a theorem target.  The
proof is two lines and is worth stating, because it settles what the object is:

    Write rho = sum_k p_k |k><k| with p_k >= 0.  Then
        G_{rs} = sum_k p_k <k| H_r^dagger H_s |k> = sum_k <v_r^k | v_s^k>
    where v_r^k = sqrt(p_k) H_r |k>.  So G is the Gram matrix of the vector
    family {v_r}, hence Hermitian PSD, with rank equal to the dimension of
    span{v_r}.

Two consequences the draft does not draw:

1.  ``rank(G)`` is the number of genuinely independent identity loops.  A brain
    that accumulates a thousand holonomies with rank(G) = 3 has three
    distinguishable identity structures and 997 restatements.  Rank, not count,
    is the identity capacity.

2.  G is invariant under a global unitary change of logical frame
    H_r -> U H_r U^dagger with rho -> U rho U^dagger.  That invariance is
    precisely what lets identity survive code deformation and substrate
    migration, and it is checkable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["holonomy_gram", "GramReport", "analyse_identity",
           "berry_holonomy", "frame_invariance_defect"]


def holonomy_gram(rho: np.ndarray, holonomies: list[np.ndarray]) -> np.ndarray:
    """G_{rs} = Tr(rho H_r^dagger H_s)."""
    k = len(holonomies)
    g = np.zeros((k, k), dtype=complex)
    for r in range(k):
        for s in range(k):
            g[r, s] = np.trace(rho @ holonomies[r].conj().T @ holonomies[s])
    return g


def berry_holonomy(hamiltonian_path: list[np.ndarray]) -> np.ndarray:
    """Path-ordered transport along a loop of Hamiltonians (adiabatic limit).

    Each step projects onto the instantaneous ground space and transports; the
    accumulated operator is the holonomy of the loop.
    """
    dim = hamiltonian_path[0].shape[0]
    holo = np.eye(dim, dtype=complex)
    prev = None
    for ham in hamiltonian_path:
        _, vecs = np.linalg.eigh(ham)
        if prev is not None:
            overlap = prev.conj().T @ vecs
            # Remove the non-geometric part by polar projection.
            u, _, vh = np.linalg.svd(overlap)
            holo = (u @ vh) @ holo
        prev = vecs
    return holo


def frame_invariance_defect(rho: np.ndarray, holonomies: list[np.ndarray],
                            frame: np.ndarray) -> float:
    """How much G changes under a logical frame change by `frame`.

    Should be zero to machine precision: this is the invariance that lets
    identity survive code deformation.
    """
    g0 = holonomy_gram(rho, holonomies)
    rho_u = frame @ rho @ frame.conj().T
    holo_u = [frame @ h @ frame.conj().T for h in holonomies]
    g1 = holonomy_gram(rho_u, holo_u)
    return float(np.linalg.norm(g0 - g1))


@dataclass
class GramReport:
    gram: np.ndarray
    eigenvalues: np.ndarray
    rank: int
    hermitian_defect: float
    min_eigenvalue: float
    frame_defect: float

    @property
    def psd(self) -> bool:
        return self.min_eigenvalue > -1e-9

    @property
    def identity_capacity(self) -> int:
        """Independent identity structures, as opposed to restatements."""
        return self.rank

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"holonomies supplied  : {self.gram.shape[0]}",
            f"identity capacity    : {self.rank} (rank of G)",
            f"hermitian defect     : {self.hermitian_defect:.3e}",
            f"min eigenvalue       : {self.min_eigenvalue:.3e}",
            f"positive semidefinite: {self.psd}",
            f"frame-change defect  : {self.frame_defect:.3e}",
        ])


def analyse_identity(rho: np.ndarray, holonomies: list[np.ndarray],
                     frame: np.ndarray | None = None,
                     tol: float = 1e-9) -> GramReport:
    """Audit an identity signature: PSD, rank, and frame invariance."""
    g = holonomy_gram(rho, holonomies)
    herm_defect = float(np.linalg.norm(g - g.conj().T))
    evals = np.linalg.eigvalsh((g + g.conj().T) / 2)
    rank = int(np.sum(evals > tol * max(1.0, float(np.max(np.abs(evals))))))

    if frame is None:
        dim = rho.shape[0]
        rng = np.random.default_rng(0)
        mat = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
        frame, _ = np.linalg.qr(mat)

    return GramReport(
        gram=g,
        eigenvalues=evals,
        rank=rank,
        hermitian_defect=herm_defect,
        min_eigenvalue=float(np.min(evals)),
        frame_defect=frame_invariance_defect(rho, holonomies, frame),
    )
