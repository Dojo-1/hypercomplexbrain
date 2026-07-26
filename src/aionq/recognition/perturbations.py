"""Three reproducible structured perturbation fields, and their matched controls.

The three seeds are fixed in advance and are recorded here so that no later run
can quietly retune them:

    thinking     7a8c4a8d
    proving      8cad443b
    formalising  450deccc

They are hexadecimal strings converted to integers.  Their only meaning is
*reproducible structured perturbation on three distinct experimental channels*.
They are not Calabi-Yau geometry, they are not a physical field, and they encode
nothing about thinking, proving or formalising beyond being three separate
streams that can be told apart in a log.

What makes a field "structured"
-------------------------------
A field is drawn on the nerve's *line graph* -- overlaps are adjacent when they
share a worldlet -- and smoothed by the heat kernel of that graph's Laplacian.
The result is spatially correlated in a way that is tied to the nerve, which is
the only property that could plausibly matter: a perturbation that respects the
overlap structure can, in principle, probe basin stability along directions the
obstruction actually lives in.

The matched control
-------------------
The correct null is **not** white noise, which would be trivially
distinguishable, and **not** a shuffle, which destroys the spectrum along with
the structure.  It is a phase-randomised surrogate: expand the structured field
in the same Laplacian eigenbasis, randomise the signs of the coefficients, and
transform back.  This preserves the power spectrum *exactly* -- same variance,
same correlation length -- while destroying the specific alignment between the
field and the defect.  If the structured field beats its own surrogate, the
alignment did the work; if it does not, the spectrum did, and the "structure" is
decoration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["FIELD_SEEDS", "seed_int", "line_graph_laplacian", "structured_field",
           "matched_surrogate", "PerturbationField", "make_fields"]

#: Frozen before any result was observed.  Do not retune.
FIELD_SEEDS = {
    "thinking": "7a8c4a8d",
    "proving": "8cad443b",
    "formalising": "450deccc",
}


def seed_int(name_or_hex: str) -> int:
    """Hex string (or field name) to a reproducible non-negative integer seed."""
    h = FIELD_SEEDS.get(name_or_hex, name_or_hex)
    return int(h, 16)


def line_graph_laplacian(nerve) -> np.ndarray:
    """Laplacian of the overlap adjacency graph: overlaps sharing a worldlet.

    This is the structure the field is correlated along.  It is a property of the
    nerve alone -- it never sees the defect -- so a field built from it cannot
    leak the answer.
    """
    m = nerve.n_edges
    a = np.zeros((m, m), dtype=float)
    for i in range(m):
        for j in range(i + 1, m):
            if set(nerve.edges[i]) & set(nerve.edges[j]):
                a[i, j] = a[j, i] = 1.0
    return np.diag(a.sum(axis=1)) - a


@dataclass(frozen=True)
class PerturbationField:
    """One reproducible field, with its provenance and its own surrogate."""

    name: str
    seed_hex: str
    values: np.ndarray
    structured: bool
    spectrum: np.ndarray

    @property
    def variance(self) -> float:
        return float(np.var(self.values))

    def __str__(self) -> str:  # pragma: no cover - display only
        kind = "structured" if self.structured else "matched surrogate"
        return f"{self.name} ({kind}, seed {self.seed_hex}, var {self.variance:.5f})"


def _eigenbasis(nerve):
    lap = line_graph_laplacian(nerve)
    vals, vecs = np.linalg.eigh(lap)
    return vals, vecs


def structured_field(nerve, name: str, scale: float = 0.12,
                     diffusion: float = 0.8) -> PerturbationField:
    """A heat-smoothed random field on the overlap adjacency graph."""
    vals, vecs = _eigenbasis(nerve)
    rng = np.random.default_rng(seed_int(name))
    white = rng.normal(size=nerve.n_edges)
    coef = vecs.T @ white
    coef = coef * np.exp(-diffusion * vals)          # heat kernel: low-pass
    field = vecs @ coef
    nrm = float(np.linalg.norm(field))
    field = field / nrm * np.sqrt(nerve.n_edges) * scale if nrm > 0 else field
    return PerturbationField(name=name, seed_hex=FIELD_SEEDS.get(name, name),
                             values=field, structured=True,
                             spectrum=np.abs(vecs.T @ field))


def matched_surrogate(nerve, base: PerturbationField, rng) -> PerturbationField:
    """Sign-randomised surrogate: identical power spectrum, destroyed alignment."""
    _vals, vecs = _eigenbasis(nerve)
    coef = vecs.T @ base.values
    signs = rng.choice(np.array([-1.0, 1.0]), size=coef.size)
    field = vecs @ (coef * signs)
    return PerturbationField(name=base.name + "_surrogate", seed_hex=base.seed_hex,
                             values=field, structured=False,
                             spectrum=np.abs(vecs.T @ field))


def make_fields(nerve, rng, scale: float = 0.12) -> dict:
    """All three structured fields and their matched surrogates."""
    out = {}
    for name in FIELD_SEEDS:
        f = structured_field(nerve, name, scale=scale)
        out[name] = f
        out[name + "_surrogate"] = matched_surrogate(nerve, f, rng)
    return out


def apply_field(transitions, field: PerturbationField, rng=None) -> list:
    """Perturb each overlap's transition by a rotation of the field's magnitude.

    The perturbation stays inside the group: a skew-symmetric generator scaled by
    the local field value, exponentiated, applied on the left.  So the perturbed
    sheaf is still a sheaf, and the probe measures basin stability rather than
    type violation.
    """
    rng = np.random.default_rng(0) if rng is None else rng
    out = []
    for k, g in enumerate(transitions):
        d = g.shape[0]
        a = rng.normal(size=(d, d))
        skew = (a - a.T) / 2.0
        nrm = np.linalg.norm(skew) or 1.0
        gen = skew / nrm * float(field.values[k])
        # exp of a small skew matrix via scaling-and-squaring-free series
        e, term = np.eye(d), np.eye(d)
        for n in range(1, 12):
            term = term @ gen / n
            e = e + term
        u, _, vt = np.linalg.svd(e)
        out.append((u @ vt) @ g)
    return out
