"""The Reversible Recognition Chamber: the five conditions, one code path.

Every experimental condition runs through :meth:`RecognitionChamber.run`.  They
differ only in three switches -- which aperture controller is installed, whether
the explorer's proposal distribution is fed by the verifier, and in which order
the two roles are applied.  That is deliberate: if each condition had its own
loop, a difference between them would be unattributable, which is the same
failure Round S3 avoided by giving all eight instruments one algorithm.

    C0  deterministic          the S3 localiser; no chamber at all
    C2  static ensemble        fixed aperture, no feedback from verification
    C3  adaptive, unordered    adaptive aperture, still no verify -> explore edge
    C4  explore -> verify      the ordered flow
    C5  verify -> explore      the reversed flow

Resource parity is enforced by construction: every condition is given the same
``evaluation_budget`` and the loop stops when it is spent, so an adaptive
controller that widens the branch buys fewer steps rather than more compute.

Three clocks run at different rates, as the manifest declares:

    fast    one tick per candidate batch    generation
    meso    every ``meso_period`` batches   aperture update, nest evaluation
    slow    every ``slow_period`` batches   evidence retention, provenance write

The slow clock is funded from the invariant channel and is never throttled.  The
fast clock is funded from the speculative channel and is throttled first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..sheaf import localise
from .aperture import AdaptiveAperture, ApertureState, FixedAperture, RandomAperture
from .budget import BordonBudget
from .metrics import candidate_diversity
from .roles import Explorer, Verifier, order_defect
from .types import CandidateSection
from .worldlet import Polycosmos

__all__ = ["RecognitionChamberState", "RecognitionChamber", "ChamberRun", "MODES"]

MODES = ("deterministic", "static", "adaptive_unordered", "explore_verify",
         "verify_explore")


@dataclass
class RecognitionChamberState:
    """Everything the chamber carries between ticks."""

    polycosmos: Polycosmos
    aperture: ApertureState
    budget: BordonBudget
    belief: np.ndarray
    clock: dict = field(default_factory=lambda: {"fast": 0, "meso": 0, "slow": 0})
    evidence_ledger: list = field(default_factory=list)
    role_potentials: dict = field(default_factory=lambda: {
        "explore": 1.0, "verify": 1.0, "witness": 1.0, "audit": 1.0, "memory": 1.0})


@dataclass
class ChamberRun:
    """One condition on one instance, with everything it produced."""

    mode: str
    belief: np.ndarray
    evaluations: int
    steps: int
    diversity: float
    order_defect: float
    aperture_history: list
    throttles: list
    final_aperture: tuple
    surviving_candidates: list = field(default_factory=list)
    instrument_evaluations: int = 0
    parameter_count: int = 0


class RecognitionChamber:
    """One loop, five switch settings."""

    def __init__(self, nerve, sheaf, mode: str, rng, aperture: ApertureState,
                 budget: BordonBudget, evaluation_budget: int = 256,
                 meso_period: int = 4, slow_period: int = 16,
                 parsimony: float = 0.35, max_support: int = 4,
                 exploration_floor: float = 0.25) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; have {MODES}")
        self.nerve = nerve
        self.sheaf = sheaf
        self.mode = mode
        self.rng = rng
        self.evaluation_budget = int(evaluation_budget)
        self.meso_period = meso_period
        self.slow_period = slow_period
        # Feeding the raw belief back as the proposal distribution makes zero an
        # absorbing state: an overlap that drops out can never be resampled, and
        # the first run of this chamber collapsed onto five overlaps with the
        # three true defects at probability exactly 0 (AUROC 0.250, below chance).
        # The floor is the minimum fix that makes the feedback condition a fair
        # test rather than a self-defeating one, and it is counted as a parameter.
        self.exploration_floor = float(exploration_floor)
        #: Instrument cost, kept OUT of the method's evaluation budget.  The
        #: order-defect probe measures the chamber; it is not part of it, and
        #: charging it to the method would have handicapped exactly the two
        #: conditions the round exists to test.
        self.instrument_evaluations = 0

        cycles = nerve.cycle_basis()
        eye = np.eye(sheaf.fiber_dim)
        self.cycle_mass = np.array(
            [float(np.linalg.norm(sheaf.holonomy(c) - eye, "fro")) for c in cycles])
        self.incidence = np.zeros((len(cycles), nerve.n_edges))
        for r, c in enumerate(cycles):
            for (k, _s) in c:
                self.incidence[r, k] = 1.0

        self.explorer = Explorer(nerve.n_edges, rng, max_support=max_support)
        self.verifier = Verifier(self.cycle_mass, self.incidence, parsimony)
        self.state = RecognitionChamberState(
            polycosmos=Polycosmos(), aperture=aperture, budget=budget,
            belief=np.full(nerve.n_edges, 1.0 / nerve.n_edges))

        if mode == "static":
            self.controller = FixedAperture(aperture)
        elif mode in ("adaptive_unordered", "explore_verify", "verify_explore"):
            self.controller = AdaptiveAperture(aperture)
        else:
            self.controller = FixedAperture(aperture)

    # -- parameter accounting -------------------------------------------------

    @property
    def parameter_count(self) -> int:
        """Free parameters this configuration carries.

        The aperture triple plus the parsimony weight and softmax temperature,
        plus the exploration floor for the two feedback conditions.  Reported so
        that a win cannot be attributed to unstated capacity; the deterministic
        baseline carries zero, which is stated rather than hidden.

        C4 and C5 carry **one more parameter than C2 and C3**.  That is a real
        asymmetry and it is reported rather than smoothed over: if the ordered
        conditions win by a margin comparable to what one extra parameter buys,
        the ordered interpretation is not supported.
        """
        if self.mode == "deterministic":
            return 0
        base = 2 + 3                               # parsimony, temperature, aperture
        return base + (1 if self.mode in ("explore_verify", "verify_explore") else 0)

    # -- the loop -------------------------------------------------------------

    def run(self) -> ChamberRun:
        if self.mode == "deterministic":
            belief = localise(self.sheaf, "sheaf", self.rng)
            return ChamberRun(mode=self.mode, belief=belief, evaluations=0, steps=0,
                              diversity=0.0, order_defect=0.0, aperture_history=[],
                              throttles=[], final_aperture=self.state.aperture.as_tuple(),
                              parameter_count=self.parameter_count)

        n = self.nerve.n_edges
        pool: list = []
        pool_metrics: list = []
        pool_age: list = []
        evaluations = 0
        steps = 0
        order_defects: list = []
        uniform = np.full(n, 1.0 / n)

        while evaluations < self.evaluation_budget:
            width = int(self.state.aperture.branch_width)
            width = max(1, min(width, self.evaluation_budget - evaluations))
            probe = ApertureState(self.state.aperture.unresolved_lifetime, width,
                                  self.state.aperture.crystallisation_barrier,
                                  self.state.aperture.bounds)

            # Switch 2: does the explorer see the verifier's belief?
            if self.mode in ("static", "adaptive_unordered"):
                proposal = uniform
            else:
                eps = self.exploration_floor
                proposal = (1.0 - eps) * self.state.belief + eps * uniform

            # Switch 3: the order of the two roles.
            if self.mode == "verify_explore":
                # verify the incumbent first, reopen from it, then explore
                incumbent = CandidateSection(
                    candidate_id=f"inc{steps}",
                    state=(np.asarray(proposal) >= np.median(proposal)).astype(np.uint8),
                    source_worldlets=("W_memory",),
                    generated_by=frozenset({"W_memory"}))
                m_inc = self.verifier.evaluate(incumbent)
                evaluations += 1
                reopened = np.asarray(incumbent.state, float) + 1e-3
                reopened = reopened / reopened.sum()
                if evaluations >= self.evaluation_budget:
                    pool.append(incumbent)
                    pool_metrics.append(m_inc)
                    pool_age.append(0)
                    break
                width = max(1, min(width, self.evaluation_budget - evaluations))
                probe = ApertureState(probe.unresolved_lifetime, width,
                                      probe.crystallisation_barrier, probe.bounds)
                cands = self.explorer.generate(reopened, probe, steps)
                mets = [self.verifier.evaluate(c) for c in cands]
                evaluations += len(cands)
                cands.append(incumbent)
                mets.append(m_inc)
            else:
                cands = self.explorer.generate(proposal, probe, steps)
                mets = [self.verifier.evaluate(c) for c in cands]
                evaluations += len(cands)

            pool.extend(cands)
            pool_metrics.extend(mets)
            pool_age.extend([0] * len(cands))
            pool_age = [a + 1 for a in pool_age]

            # unresolved lifetime: retire candidates older than tau
            tau = self.state.aperture.unresolved_lifetime
            keep = [i for i, a in enumerate(pool_age) if a <= tau]
            if keep:
                pool = [pool[i] for i in keep]
                pool_metrics = [pool_metrics[i] for i in keep]
                pool_age = [pool_age[i] for i in keep]

            self.state.belief = self._belief(pool, pool_metrics, n)
            steps += 1
            self.state.clock["fast"] += 1

            # meso clock: aperture update and resource charge
            if steps % self.meso_period == 0:
                self.state.clock["meso"] += 1
                self.state.budget.charge(0.02 * width)
                self.state.budget.tick(steps, self.state.aperture)
                susceptibility, instability = self._signals(pool, pool_metrics)
                self.controller.update(steps, susceptibility, instability,
                                       self.state.budget.pressure)
                if self.mode in ("explore_verify", "verify_explore"):
                    before = self.verifier.evaluations
                    rep = order_defect(self.state.belief, self.explorer,
                                       self.verifier, probe, steps)
                    order_defects.append(rep.defect)
                    # charged to the instrument, not to the method: see __init__
                    self.instrument_evaluations += (self.verifier.evaluations - before)

            # slow clock: evidence retention, funded from the invariant channel
            if steps % self.slow_period == 0:
                self.state.clock["slow"] += 1
                self.state.evidence_ledger.append({
                    "step": steps, "evaluations": evaluations,
                    "aperture": self.state.aperture.as_tuple(),
                    "budget_state": self.state.budget.state})

        return ChamberRun(
            mode=self.mode,
            belief=self.state.belief,
            evaluations=evaluations,
            steps=steps,
            diversity=candidate_diversity(pool),
            order_defect=float(np.mean(order_defects)) if order_defects else 0.0,
            aperture_history=list(self.state.aperture.history),
            throttles=list(self.state.budget.interventions),
            final_aperture=self.state.aperture.as_tuple(),
            surviving_candidates=pool,
            instrument_evaluations=self.instrument_evaluations,
            parameter_count=self.parameter_count,
        )

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _belief(pool, metrics, n, temperature: float = 0.25) -> np.ndarray:
        if not pool:
            return np.full(n, 1.0 / n)
        g = np.array([m.gluing_score for m in metrics], dtype=float)
        w = np.exp(-(g - g.min()) / max(1e-9, temperature))
        w = w / w.sum()
        b = np.zeros(n, dtype=float)
        for weight, c in zip(w, pool):
            b += weight * np.asarray(c.state, dtype=float)
        total = b.sum()
        return b / total if total > 0 else np.full(n, 1.0 / n)

    @staticmethod
    def _signals(pool, metrics) -> tuple:
        """Structured susceptibility and instability, separately.

        Susceptibility: the population disagrees *while* some candidates are
        explaining real obstruction mass -- dispersion of gluing scores weighted
        by mean empirical support.  Dispersion alone is noise, and the
        :class:`RandomAperture` ablation is what distinguishes the two.

        Instability: the fraction of candidates whose consistency status is
        underdetermined.
        """
        if len(metrics) < 2:
            return 0.0, 0.0
        g = np.array([m.gluing_score for m in metrics], dtype=float)
        support = float(np.mean([m.empirical_support for m in metrics]))
        spread = float(np.std(g)) / max(1e-9, float(np.mean(g)))
        susceptibility = float(min(1.0, spread * support * 2.0))
        under = float(np.mean([m.consistency_status == "underdetermined"
                               for m in metrics]))
        return susceptibility, under


def make_random_aperture_chamber(nerve, sheaf, rng, aperture, budget, **kw):
    """C1's controller: matched random walk over the same box, ignoring signals."""
    ch = RecognitionChamber(nerve, sheaf, "explore_verify", rng, aperture, budget, **kw)
    ch.controller = RandomAperture(aperture, rng)
    ch.mode_label = "random_aperture"
    return ch
