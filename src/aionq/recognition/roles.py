"""The exploratory and verification operators, and the ordered-flow observable.

Two role potentials, both defined as ordinary operators on chamber state.  The
semantic handles ("Emperor", "Empress") are registered at S tier and carry no
authority here; what follows is what they denote.

    E : S -> CandidateSet(S)      exploratory / counterfactual
    M : Candidate -> typed tuple  gluing, certificate, consistency, support,
                                  recoverability, cost

Two constraints are structural rather than advisory:

**E does not promote.**  :meth:`Explorer.generate` returns candidates whose
evidence envelope is empty.  It cannot write an evidence tag, because it is not
given the ledger.

**M does not produce final truth.**  :meth:`Verifier.evaluate` returns a typed
tuple with six named components and no aggregate.  The collapse to a decision
happens only in :mod:`aionq.recognition.nest`, against a preregistered region.

The ordered-flow observable
---------------------------
    order_defect(x) = D( M(E(x)), E(M(x)) )

Both sides are pushed into the same carrier -- a per-overlap score vector in
R^E -- before D is applied, because comparing a candidate set to a score tuple
directly would be exactly the cross-frame comparison this package exists to
refuse.  The projection is lossy and says so.

**A nonzero order defect is an observable, not a benefit.**  Condition C5
(verify-then-reopen) exists precisely so that noncommutativity cannot be read as
evidence for the ordered interpretation: if C4 does not beat both C3 and C5, the
ordering has bought nothing regardless of how large the defect is.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .types import CandidateSection

__all__ = ["Explorer", "Verifier", "CandidateMetrics", "order_defect",
           "OrderDefectReport"]


# --------------------------------------------------------------------------
# The verification tuple
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidateMetrics:
    """Six named components.  Never collapsed here."""

    gluing_score: float            # obstruction mass left unexplained (lower better)
    certificate_status: str        # "none" | "exact" | "conditional"
    consistency_status: str        # "consistent" | "overdetermined" | "underdetermined"
    empirical_support: float       # fraction of obstructed cycles covered
    roundtrip_recoverability: float  # 1 - normalised loop defect
    resource_cost: float           # evaluations charged

    def as_tuple(self) -> tuple:
        return (self.gluing_score, self.certificate_status, self.consistency_status,
                self.empirical_support, self.roundtrip_recoverability,
                self.resource_cost)


# --------------------------------------------------------------------------
# E: the exploratory operator
# --------------------------------------------------------------------------

class Explorer:
    """Proposes alternative local sections.  Deterministic given a seed.

    Candidates are subsets of overlaps proposed as the defect support.  The
    proposal distribution is the current per-overlap belief, so exploration is
    informed but never *decides*: it writes no evidence tag and touches no
    ledger.
    """

    name = "explorer"

    def __init__(self, n_edges: int, rng, max_support: int = 4) -> None:
        self.n_edges = n_edges
        self.rng = rng
        self.max_support = max_support
        self.calls = 0

    def generate(self, belief, aperture, step: int = 0) -> list:
        """Return exactly ``aperture.branch_width`` candidates.

        The count is a hard contract, not a target: the resource accounting in
        every condition is stated per candidate evaluation, and a generator that
        quietly returned more would break parity silently.
        """
        self.calls += 1
        k = int(aperture.branch_width)
        p = np.asarray(belief, dtype=float).copy()
        p = np.clip(p, 1e-9, None)
        p = p / p.sum()
        out = []
        for i in range(k):
            size = int(self.rng.integers(1, self.max_support + 1))
            size = min(size, self.n_edges)
            support = self.rng.choice(self.n_edges, size=size, replace=False, p=p)
            state = np.zeros(self.n_edges, dtype=np.uint8)
            state[support] = 1
            out.append(CandidateSection(
                candidate_id=f"c{step}_{i}",
                state=state,
                source_worldlets=("W_explore", "W_memory"),
                transformations=("importance sample from current belief",),
                evidence_envelope={},          # E does not promote: this stays empty
                resource_cost=1.0,
                generated_by=frozenset({"W_explore", "W_memory"}),
            ))
        return out


# --------------------------------------------------------------------------
# M: the verification operator
# --------------------------------------------------------------------------

class Verifier:
    """Scores a candidate against the observed cycle obstruction.

    ``cycle_mass[c]`` is the observed obstruction magnitude of basis cycle c and
    ``incidence[c, e]`` says whether overlap e lies on it.

    The objective is a **non-negative least-squares fit**, not a set cover.  The
    first implementation of this class scored a candidate by how much obstruction
    mass it left uncovered, and that discards the strongest signal in the data: a
    cycle with *low* mass exonerates its overlaps.  Under a cover objective any
    small set meeting all five basis cycles scores perfectly, so the objective was
    badly under-identifying and no chamber condition beat the deterministic
    baseline.  The fit model

        m_c  ~  sum over e in c of x_e ,   x_e >= 0 supported on the candidate

    penalises a candidate for touching a clean cycle, which a cover cannot do.
    The residual, plus a parsimony charge, is the gluing score.

    This is a better use of the same evidence than the baseline's equal
    blame-spreading -- which is the point.  The question this round asks is not
    whether search beats blame-spreading (it should) but whether *adaptive
    aperture and ordered flow* beat a static ensemble doing the same search at the
    same cost.
    """

    name = "verifier"

    def __init__(self, cycle_mass, incidence, parsimony: float = 0.35) -> None:
        self.cycle_mass = np.asarray(cycle_mass, dtype=float)
        self.incidence = np.asarray(incidence, dtype=float)
        self.parsimony = float(parsimony)
        self.total_mass = float(self.cycle_mass.sum()) or 1.0
        self.mass_norm = float(self.cycle_mass @ self.cycle_mass) or 1.0
        self.evaluations = 0

    def _fit(self, support) -> tuple:
        """Least-squares magnitudes on the candidate's support, clipped at zero."""
        if support.size == 0:
            return np.zeros(0), float(self.mass_norm)
        a = self.incidence[:, support]
        x, *_ = np.linalg.lstsq(a, self.cycle_mass, rcond=None)
        x = np.clip(x, 0.0, None)
        resid = self.cycle_mass - a @ x
        return x, float(resid @ resid)

    def evaluate(self, candidate: CandidateSection) -> CandidateMetrics:
        self.evaluations += 1
        s = np.asarray(candidate.state, dtype=np.uint8)
        support = np.flatnonzero(s)
        _x, sse = self._fit(support)
        size = float(support.size)

        explained = max(0.0, 1.0 - sse / self.mass_norm)
        gluing = sse / self.mass_norm + self.parsimony * size / max(1.0, s.size)

        touched = (self.incidence[:, support].sum(axis=1) > 0) if support.size \
            else np.zeros(self.cycle_mass.size, dtype=bool)
        uncovered = float(self.cycle_mass[~touched].sum())

        if sse <= 1e-12:
            cert = "exact"
        elif explained > 0.9:
            cert = "conditional"
        else:
            cert = "none"
        if uncovered > 1e-9:
            cons = "underdetermined"
        elif size > self.cycle_mass.size:
            cons = "overdetermined"
        else:
            cons = "consistent"

        return CandidateMetrics(
            gluing_score=gluing,
            certificate_status=cert,
            consistency_status=cons,
            empirical_support=explained,
            roundtrip_recoverability=explained,
            resource_cost=1.0,
        )


# --------------------------------------------------------------------------
# The ordered-flow observable
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderDefectReport:
    """D(M(E(x)), E(M(x))), with both sides named and the projection declared."""

    defect: float
    metric: str
    carrier: str
    projection_lossy: bool
    lost_in_projection: tuple
    forward_first: tuple
    verify_first: tuple

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"order defect {self.defect:.6f} ({self.metric} on {self.carrier}); "
                f"projection lost {list(self.lost_in_projection)}")


def _belief_from_candidates(candidates, metrics, n_edges: int,
                            temperature: float = 0.25) -> np.ndarray:
    """Softmax-weighted vote of candidate supports.  This is the lossy projection.

    A candidate set carries which overlaps co-occur; a per-overlap vector does
    not.  That co-occurrence structure is what the projection loses, and it is
    named in every report rather than left implicit.
    """
    if not candidates:
        return np.full(n_edges, 1.0 / max(1, n_edges))
    g = np.array([m.gluing_score for m in metrics], dtype=float)
    w = np.exp(-(g - g.min()) / max(1e-9, temperature))
    w = w / w.sum()
    belief = np.zeros(n_edges, dtype=float)
    for weight, c in zip(w, candidates):
        belief += weight * np.asarray(c.state, dtype=float)
    total = belief.sum()
    return belief / total if total > 0 else np.full(n_edges, 1.0 / max(1, n_edges))


def order_defect(belief, explorer: Explorer, verifier: Verifier, aperture,
                 step: int = 0) -> OrderDefectReport:
    """Measure whether explore-then-verify differs from verify-then-explore.

    Both orders are charged the same number of candidate evaluations, and both
    are projected into the same per-overlap carrier before comparison.
    """
    n = explorer.n_edges

    cands_a = explorer.generate(belief, aperture, step)
    mets_a = [verifier.evaluate(c) for c in cands_a]
    forward_first = _belief_from_candidates(cands_a, mets_a, n)

    # verify first: score the incumbent belief as a single candidate, then explore
    incumbent = CandidateSection(
        candidate_id=f"incumbent{step}",
        state=(np.asarray(belief, float) > np.median(belief)).astype(np.uint8),
        source_worldlets=("W_memory",),
        generated_by=frozenset({"W_memory"}),
    )
    m_inc = verifier.evaluate(incumbent)
    reopened = _belief_from_candidates([incumbent], [m_inc], n)
    cands_b = explorer.generate(reopened, aperture, step)
    mets_b = [verifier.evaluate(c) for c in cands_b[:-1]] if len(cands_b) > 1 else []
    verify_first = _belief_from_candidates(cands_b[:len(mets_b)], mets_b, n) \
        if mets_b else reopened

    d = float(np.abs(forward_first - verify_first).sum())
    return OrderDefectReport(
        defect=d,
        metric="L1 on the per-overlap belief simplex",
        carrier="real_vector[n_edges]",
        projection_lossy=True,
        lost_in_projection=("candidate co-occurrence structure",
                            "candidate support sizes",
                            "certificate and consistency status"),
        forward_first=tuple(float(v) for v in forward_first),
        verify_first=tuple(float(v) for v in verify_first),
    )
