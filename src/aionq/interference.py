"""Quantum interference as an instrument for reading a cycle obstruction.

The proposal this implements
----------------------------
A "Quantum Polycosmic Sheaf Memory" was proposed with its own first experiment
stated in advance:

    Four worldlets, two overlap cycles, three evidence classes and one controlled
    basis transition.  Its target would not be language-model superiority.  It
    would test whether quantum interference identifies a hidden cycle obstruction
    using fewer oracle queries or with greater diagnostic resolution than matched
    classical, tensor-network and randomized baselines.

That is a well-posed question, and it has an exact answer.  This module gives it.

The reduction
-------------
Let the nerve have V worldlets, E overlaps and cycle rank b = E - V + C.  A
defect is a 1-cochain s in F_2^E marking which overlaps are twisted.  The only
observable is holonomy: for a cycle c, the oracle returns

    f(c) = <c, s>  mod 2.

Two facts follow immediately, and neither is an experiment.

1.  **The observable is exactly b bits.**  Holonomy is linear in s and its kernel
    is the cut space, of dimension E - b.  Coboundaries are unobservable by
    construction -- that is what it means for the obstruction to be a cohomology
    class.  So the learner's target is t = C s in F_2^b, and nothing finer.

2.  **Classical needs exactly b queries; quantum needs exactly 1.**  Each query
    returns one bit, and t carries b bits, so b is an information-theoretic lower
    bound for deterministic and bounded-error classical strategies alike; b
    queries on a cycle basis achieve it.  The quantum side is Bernstein-Vazirani:
    one coherent query to the phase oracle recovers all b bits with certainty.

So the separation is b vs 1, and it is *proved*, not measured.  The measured
questions are the two that actually decide whether it means anything.

The two caveats that decide it
------------------------------
**The oracle must already be coherent.**  Bernstein-Vazirani spends one query on
a unitary U_f: |c>|y> -> |c>|y + f(c)>.  If the worldlet data is classical and
the oracle has to be *built* from it, building it reads every overlap -- E
classical accesses -- and the b queries saved were never the cost.  The
separation is real in the oracle model and vacuous outside it.  This is not a
hedge: it is the same reason Bernstein-Vazirani is a complexity-theoretic
landmark and not a database technology.  :func:`oracle_construction_cost` states
it in code so it cannot be quietly dropped from a summary.

**Recovering the class is not localising the defect.**  Quantum interference
returns t = C s.  Which *overlaps* are twisted is the minimum-weight coset
representative of s, a syndrome-decoding problem that is NP-hard in general and
**identical for both parties** -- the quantum step has already finished before it
begins.  :func:`minimum_weight_representative` runs it, and the query advantage
does not touch it.  The proposal says "identifies a hidden cycle obstruction",
which is the class; if what is wanted is the edge, the advantage stops one step
short.

What is measured here
---------------------
Noise.  One coherent query is worth b classical queries only while it succeeds.
:func:`bv_success_rate` simulates the Bernstein-Vazirani circuit under
depolarizing noise, and :func:`crossover_noise` finds the error rate at which the
expected number of coherent queries, 1/p_success, first exceeds the b the
classical learner pays.  That crossover falls as b grows, which is the opposite
of the direction an advantage claim needs: the harder the instance, the less
noise the quantum instrument can absorb before losing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["cycle_incidence", "obstruction_class", "classical_query_cost",
           "oracle_construction_cost", "bv_recover", "bv_success_rate",
           "expected_quantum_queries", "crossover_noise",
           "minimum_weight_representative", "QueryReport"]


# --------------------------------------------------------------------------
# The reduction: from a sheaf defect to a hidden bit-string
# --------------------------------------------------------------------------

def cycle_incidence(nerve) -> np.ndarray:
    """The b x E cycle-edge incidence matrix over F_2 for a fundamental basis."""
    cycles = nerve.cycle_basis()
    c = np.zeros((len(cycles), nerve.n_edges), dtype=np.uint8)
    for r, cyc in enumerate(cycles):
        for (k, _s) in cyc:
            c[r, k] ^= 1
    return c


def obstruction_class(nerve, defect_edges) -> np.ndarray:
    """t = C s: the holonomy bit of every basis cycle.

    This is the whole observable.  Two defects with the same t are
    indistinguishable to *any* number of holonomy queries, classical or quantum,
    because they differ by a coboundary.
    """
    s = np.zeros(nerve.n_edges, dtype=np.uint8)
    for e in defect_edges:
        s[int(e)] ^= 1
    return (cycle_incidence(nerve) @ s) % 2


def classical_query_cost(betti_1: int) -> int:
    """Exactly b, and this is tight in both directions.

    Lower: each holonomy query returns one bit and t carries b bits, so no
    deterministic or bounded-error classical strategy can use fewer.
    Upper: querying the b basis cycles returns t outright.
    """
    return int(betti_1)


def oracle_construction_cost(nerve) -> int:
    """Classical accesses needed to BUILD the coherent oracle from worldlet data.

    Every overlap must be read to encode its transition into the unitary, so this
    is E.  It dominates the b queries the quantum learner then saves.  Kept as a
    function, not a footnote, because the single-query result is meaningless
    without it.
    """
    return int(nerve.n_edges)


# --------------------------------------------------------------------------
# Bernstein-Vazirani under depolarizing noise
# --------------------------------------------------------------------------

def _h(state: np.ndarray, k: int, n: int) -> np.ndarray:
    state = state.reshape(-1, 2, 2 ** k)
    a, b = state[:, 0, :], state[:, 1, :]
    out = np.empty_like(state)
    out[:, 0, :] = (a + b) / np.sqrt(2.0)
    out[:, 1, :] = (a - b) / np.sqrt(2.0)
    return out.reshape(-1)


def _pauli(state: np.ndarray, k: int, n: int, which: int) -> np.ndarray:
    """which: 1 = X, 2 = Y, 3 = Z."""
    state = state.reshape(-1, 2, 2 ** k).copy()
    if which == 1:
        state = state[:, ::-1, :]
    elif which == 2:
        a, b = state[:, 0, :].copy(), state[:, 1, :].copy()
        state[:, 0, :] = -1j * b
        state[:, 1, :] = 1j * a
    else:
        state[:, 1, :] *= -1
    return state.reshape(-1)


def _cx(state: np.ndarray, control: int, target: int, n: int) -> np.ndarray:
    dim = state.size
    idx = np.arange(dim)
    mask = (idx >> control) & 1 == 1
    out = state.copy()
    out[idx[mask]] = state[idx[mask] ^ (1 << target)]
    return out


def _depolarize(state: np.ndarray, n: int, p: float, rng) -> np.ndarray:
    """Pauli-twirled depolarizing on every qubit: with probability p, a random
    non-identity Pauli.  Monte Carlo, so the sampled outcomes are exact."""
    if p <= 0.0:
        return state
    for k in range(n):
        if rng.random() < p:
            state = _pauli(state, k, n, int(rng.integers(1, 4)))
    return state


def bv_recover(hidden: np.ndarray, noise: float = 0.0, rng=None) -> np.ndarray:
    """One coherent query to the holonomy oracle; returns the measured b bits.

    Circuit: H^b on the query register, X then H on the phase qubit, a CNOT from
    each query qubit i with hidden[i] = 1 into the phase qubit, H^b again, measure.
    Depolarizing noise is applied after each of the three layers.
    """
    hidden = np.asarray(hidden, dtype=np.uint8)
    b = hidden.size
    rng = np.random.default_rng(0) if rng is None else rng
    if b == 0:
        return hidden.copy()
    n = b + 1                                     # qubit b is the phase qubit
    state = np.zeros(2 ** n, dtype=complex)
    state[0] = 1.0

    state = _pauli(state, b, n, 1)                # X on the phase qubit
    for k in range(n):
        state = _h(state, k, n)
    state = _depolarize(state, n, noise, rng)

    for k in range(b):                            # the single oracle call
        if hidden[k]:
            state = _cx(state, k, b, n)
    state = _depolarize(state, n, noise, rng)

    for k in range(b):
        state = _h(state, k, n)
    state = _depolarize(state, n, noise, rng)

    probs = np.abs(state) ** 2
    probs = probs / probs.sum()
    outcome = int(rng.choice(probs.size, p=probs))
    return np.array([(outcome >> k) & 1 for k in range(b)], dtype=np.uint8)


def bv_success_rate(betti_1: int, noise: float, trials: int = 400,
                    rng=None) -> float:
    """Fraction of single-query runs that return the hidden string exactly."""
    rng = np.random.default_rng(0) if rng is None else rng
    ok = 0
    for _ in range(trials):
        hidden = rng.integers(0, 2, size=betti_1).astype(np.uint8)
        ok += int(np.array_equal(bv_recover(hidden, noise, rng), hidden))
    return ok / trials


def expected_quantum_queries(success: float) -> float:
    """Repeat-until-correct cost of the coherent strategy.

    Optimistic on purpose: it assumes a run can be *recognised* as correct for
    free.  It cannot -- verifying a candidate costs classical queries -- so the
    real quantum cost is higher than this and the crossover below is an
    upper bound on where the advantage survives.
    """
    return float("inf") if success <= 0.0 else 1.0 / success


def crossover_noise(betti_1: int, grid=None, trials: int = 400, rng=None) -> float:
    """Smallest depolarizing rate at which 1/p_success first exceeds b.

    Above this rate the coherent instrument needs more expected queries than the
    classical learner simply pays up front, so the query advantage is gone.
    """
    rng = np.random.default_rng(0) if rng is None else rng
    grid = np.linspace(0.0, 0.30, 31) if grid is None else np.asarray(grid, float)
    for p in grid:
        s = bv_success_rate(betti_1, float(p), trials, rng)
        if expected_quantum_queries(s) > betti_1:
            return float(p)
    return float(grid[-1])


# --------------------------------------------------------------------------
# The step the advantage does not reach
# --------------------------------------------------------------------------

def minimum_weight_representative(nerve, class_bits) -> np.ndarray:
    """Lightest defect cochain consistent with the observed holonomy class.

    Exhaustive over F_2^E, which is honest about the cost: this is syndrome
    decoding, it is NP-hard in general, and **both** parties face it unchanged
    after the class is known.  The quantum query advantage ends one step before
    the question "which overlap is twisted" is answered.
    """
    c = cycle_incidence(nerve)
    target = np.asarray(class_bits, dtype=np.uint8) % 2
    e = nerve.n_edges
    if e > 24:
        raise ValueError("exhaustive decoding refused above 24 overlaps; the point "
                         "is that this step is hard, not that it should be hidden")
    best, best_w = None, e + 1
    for mask in range(1 << e):
        s = np.array([(mask >> i) & 1 for i in range(e)], dtype=np.uint8)
        if np.array_equal((c @ s) % 2, target):
            w = int(s.sum())
            if w < best_w:
                best, best_w = s, w
    return best if best is not None else np.zeros(e, dtype=np.uint8)


@dataclass
class QueryReport:
    """What one nerve costs each party, with the caveats attached."""

    n_worldlets: int
    n_edges: int
    betti_1: int
    classical_queries: int
    quantum_queries: int
    oracle_build_cost: int

    @property
    def query_ratio(self) -> float:
        return self.classical_queries / max(1, self.quantum_queries)

    @property
    def honest_ratio(self) -> float:
        """Ratio once the oracle has to be built from classical worldlet data."""
        return self.classical_queries / max(1, self.quantum_queries
                                            + self.oracle_build_cost)

    def __str__(self) -> str:  # pragma: no cover - display only
        return (f"V={self.n_worldlets} E={self.n_edges} b={self.betti_1}: "
                f"classical {self.classical_queries}, quantum {self.quantum_queries} "
                f"(ratio {self.query_ratio:.1f}x), "
                f"with oracle construction {self.honest_ratio:.2f}x")


def query_report(nerve) -> QueryReport:
    b = nerve.betti_1
    return QueryReport(nerve.n_worldlets, nerve.n_edges, b,
                       classical_query_cost(b), 1, oracle_construction_cost(nerve))
