"""The coherence budget: the periodic breath model.

.. note::
   **Superseded as a respiration model by** :mod:`aionq.bordon`.  This module
   treats breathing as a single global period that interrupts cognition.  The
   Bordon (Galician gaita) model is structurally better: a *fol* reservoir
   decouples intake from expenditure, a *bordon* drone channel is never
   interrupted, and channels breathe at different rates.  The ancilla accounting
   below remains valid as a *capacity* argument; the periodic schedule does not
   survive as a model of how an organ actually respires.

The coherence budget: why entropy export is forced, not chosen.

The draft architecture treats breathing as a design aesthetic -- inhalation
expands the code, exhalation measures and consolidates -- and motivates it by
appeal to cognitive metaphor.  It does not need the metaphor.  Exhalation is a
theorem about any agent that computes coherently with finite hardware.

The argument
------------
1.  Coherent control means deferring measurement (see :mod:`aionq.coherentize`).
2.  Every deferred decision retains its branch record.  Ancilla count grows
    monotonically, one qubit per decision, and quantum states cannot be
    overwritten in place -- no-deleting forbids it.
3.  Therefore a brain with a fixed logical qubit budget B and a working set of
    n_data qubits can defer at most ``B - n_data`` decisions before it runs out
    of room.
4.  Recovering room without measuring requires *uncomputation*, which requires
    the branch to be recomputable.  Bennett's reversible pebble game gives the
    trade: with k pebbles one can reversibly traverse ``2^k`` computation
    steps at a cost of ``3^k`` operations, i.e. traversing L steps with
    ``log2 L`` ancillas costs ``L^log2(3) ~ L^1.585`` time.
5.  Cognition is not reversible in general -- abstraction discards -- so some
    branches are not uncomputable at any price.  Those must be measured.

The consequence is quantitative: the breath period is set by the pebbling
budget, not by taste.  A brain that inhales past its coherent horizon does not
become more quantum; it becomes unable to allocate.

This module computes the horizon and the forced breath period.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["CoherenceBudget", "BreathSchedule", "bennett_time_cost",
           "pebbles_for_horizon", "magic_budget", "MagicBudget"]


@dataclass
class MagicBudget:
    """What a simulation-hardness target actually costs in magic.

    q_sim_upper = alpha * t / n, so demanding hardness q over n logical qubits
    requires t = q n / alpha non-Clifford operations per coherent episode.
    Dividing a machine's total operation budget by that gives the number of
    coherent cognitive episodes the machine can support.
    """

    logical_qubits: int
    target_residency: float
    t_per_episode: float
    total_operations: float
    episodes: float

    def __str__(self) -> str:  # pragma: no cover - display only
        return "\n".join([
            f"logical qubits             : {self.logical_qubits}",
            f"target q_sim_upper         : {self.target_residency:.2f}",
            f"non-Clifford ops / episode : {self.t_per_episode:,.0f}",
            f"machine operation budget   : {self.total_operations:,.0f}",
            f"coherent episodes supported: {self.episodes:,.0f}",
        ])


def magic_budget(logical_qubits: int, target_residency: float,
                 total_operations: float, alpha: float = 0.2284) -> MagicBudget:
    """Translate a residency target into a magic-state and episode budget.

    Assumes every non-Clifford operation consumes one distilled magic state and
    that the machine's quoted operation budget is spent on them.  Both are
    optimistic, so `episodes` is an upper bound.
    """
    t_per = target_residency * logical_qubits / alpha
    return MagicBudget(
        logical_qubits=logical_qubits,
        target_residency=target_residency,
        t_per_episode=t_per,
        total_operations=total_operations,
        episodes=total_operations / t_per if t_per > 0 else math.inf,
    )


def bennett_time_cost(horizon: int, pebbles: int) -> float:
    """Time cost of reversibly traversing `horizon` steps with `pebbles` ancillas.

    Bennett's pebble game gives the anchor point: k pebbles reach 2^k steps in
    3^k operations.  The interpolation used here for intermediate pebble budgets
    is a PROJECT-SPECIFIC HEURISTIC, not a derivation of the reversible
    pebble-game optimum.  The literature establishes a reversible
    time-space-erasure tradeoff; it does not establish this particular schedule.
    Every overhead figure downstream inherits that status (tagged A in
    :mod:`aionq.governance`).
    """
    if horizon <= 1:
        return float(horizon)
    if pebbles <= 0:
        return math.inf
    k_needed = math.log2(horizon)
    if pebbles >= horizon:
        return float(horizon)  # enough room to keep every intermediate
    if pebbles < 1:
        return math.inf
    # Segmented Bennett: split into 2^pebbles chunks, recurse.
    return float(horizon ** (math.log2(3) / max(1e-9, min(1.0, pebbles / k_needed))))


def pebbles_for_horizon(horizon: int) -> int:
    """Minimum ancillas to reversibly reach `horizon` steps at Bennett's rate."""
    return max(1, math.ceil(math.log2(max(2, horizon))))


# Exhalation is entropy export, and measurement is only one channel for it.
# Equating the two was an overreach: the general statement is that finite
# coherent computation eventually requires uncomputation, resource expansion or
# entropy export -- not that cognition must periodically measure itself on one
# Bennett-derived period.
EXHALATION_CHANNELS = (
    "uncompute",        # reversible, costs time (Bennett)
    "measure",          # irreversible, costs coherence
    "reset",            # irreversible, costs a thermodynamic kT ln2 per bit
    "swap_out",         # move to colder/slower storage, costs bandwidth
    "dissipate",        # engineered dissipation to an attractor
    "compress",         # lossy re-encoding into fewer logical qubits
    "error_correct",    # export entropy as syndrome, preserves logical state
)


@dataclass
class BreathSchedule:
    """A forced inhale/exhale cycle.

    ``exhale_period`` is when *some* entropy-export channel must fire, not when
    a measurement must.  See :data:`EXHALATION_CHANNELS`.
    """

    horizon: int              # decisions deferrable before allocation failure
    pebbles: int              # ancillas available for uncomputation
    irreversible_fraction: float
    exhale_period: float      # decisions between forced measurement rounds
    time_overhead: float      # multiplicative cost of staying coherent

    def __str__(self) -> str:  # pragma: no cover - display only
        period = ("never (allocation-bound); limited only by Bennett time cost"
                  if math.isinf(self.exhale_period)
                  else f"every {int(self.exhale_period)} decisions")
        return "\n".join([
            f"coherent horizon      : {self.horizon} decisions",
            f"pebbles (ancillas)    : {self.pebbles}",
            f"irreversible fraction : {self.irreversible_fraction:.2f}",
            f"forced exhale period  : {period}",
            f"time overhead to stay coherent : {self.time_overhead:.2f}x",
        ])


@dataclass
class CoherenceBudget:
    """Hardware envelope for a coherent cognitive episode.

    Parameters
    ----------
    logical_qubits:
        Total logical qubits available to the causal core.
    data_qubits:
        Qubits occupied by the working state (not reclaimable).
    qubits_per_decision:
        Branch-record qubits retained per deferred decision.  One for a binary
        branch; ``ceil(log2 m)`` for an m-way policy selection.
    irreversible_fraction:
        Fraction of decisions whose branch record cannot be uncomputed because
        the step discarded information (abstraction, coarse-graining, any
        many-to-one map).  These *must* be measured.
    """

    logical_qubits: int
    data_qubits: int
    qubits_per_decision: int = 1
    irreversible_fraction: float = 0.3

    @property
    def free_qubits(self) -> int:
        return max(0, self.logical_qubits - self.data_qubits)

    @property
    def horizon(self) -> int:
        """Deferrable decisions before allocation failure."""
        return self.free_qubits // max(1, self.qubits_per_decision)

    def schedule(self) -> BreathSchedule:
        """Compute the forced breath cycle."""
        horizon = self.horizon
        pebbles = self.free_qubits

        # Reversible branches can be uncomputed and their qubits reused;
        # irreversible ones consume a slot permanently.  After D decisions the
        # permanently consumed count is f * D, so allocation fails at
        # D = horizon / f.  A fully reversible cognition is never *forced* to
        # exhale by allocation -- only by the Bennett time cost of staying so.
        if self.irreversible_fraction <= 0:
            exhale = math.inf
        else:
            exhale = max(1, int(horizon / self.irreversible_fraction))

        finite_exhale = horizon if math.isinf(exhale) else exhale
        overhead = (bennett_time_cost(max(2, finite_exhale), pebbles) / max(1, finite_exhale)
                    if pebbles > 0 else math.inf)

        return BreathSchedule(
            horizon=horizon,
            pebbles=pebbles,
            irreversible_fraction=self.irreversible_fraction,
            exhale_period=exhale,
            time_overhead=overhead,
        )
