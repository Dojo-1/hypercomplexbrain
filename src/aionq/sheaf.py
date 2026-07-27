"""Cellular sheaves of worldlets, and instruments that localise gluing failure.

Specified in the Sigma-infinity thesis (section 16, experiment 1), the *first*
experiment the thesis pre-registers and the one it says targets "observability
rather than intelligence":

    Construct a synthetic multi-world task with known local sections, overlap
    inconsistencies, and hidden cycle obstructions.  Compare scalar, graph,
    sheaf, quaternionic, octonionic, and randomized coordinate systems on
    obstruction localization, not only task reward.

    Prediction: the sheaf and relation-mesh instruments should localize gluing
    failures more reliably; hypercomplex coordinates may improve diagnosis ONLY
    on explicitly order-sensitive or null-channel cases.

    Kill condition: any advantage disappears under dimension- and
    compute-matched controls.

The object
----------
A *nerve* is a graph whose vertices are worldlets and whose edges are overlaps.
A *cellular sheaf* on it assigns a fiber to each worldlet and an orthogonal
transition G_ij to each overlap.  A global section is a choice x_i in each fiber
with x_j = G_ij x_i on every overlap.  Around a cycle gamma the composite

    H(gamma) = G_{i_k i_1} ... G_{i_2 i_3} G_{i_1 i_2}

is the *holonomy*.  H(gamma) != I is an obstruction: no global section can be
consistent all the way round.

The construction here guarantees that **no single overlap is locally anomalous**.
A consistent sheaf is built first, as an exact coboundary from a vertex gauge, so
every cycle has trivial holonomy; the defect is then injected by replacing the
transition on hidden edges with another element of the same group drawn from the
same distribution.  An instrument that inspects overlaps one at a time therefore
has nothing to find.  Only the loop reveals the defect.  That is what makes
localisation a real task rather than an outlier scan, and it is what the thesis
means by a *hidden cycle obstruction*.

Why the instruments differ
--------------------------
Every instrument runs the *same* localisation algorithm: compute the holonomy of
each cycle in a fundamental cycle basis, score its deviation from the identity,
and spread the blame equally over that cycle's edges.  They differ only in the
coordinate system in which transitions are represented and composed.  That is
deliberate.  It is the only way the thesis's kill condition -- "any advantage
disappears under dimension- and compute-matched controls" -- can be tested at
all: if the attribution rule also changed, a win would be unattributable.

    graph       topology only; no transitions.  Ranks edges by cycle membership
                and nothing else.  The honest ceiling for a coordinate-free
                representation, not a strawman.
    scalar      each overlap compressed to one real number, tr(G)/d, combined
                additively around the cycle.
    character   the abelianisation det: O(d) -> {+1, -1}.  The only *homomorphic*
                scalar coordinate there is.
    sheaf       full matrix holonomy at the sheaf's own fiber dimension.
    quaternion  transitions projected to their nearest unit quaternion and
                composed in H (fiber dimension 4).
    octonion    transitions carried as unit octonions and composed in O,
                left-bracketed (fiber dimension 8).
    associator  the difference between the left- and right-bracketed octonionic
                products: a channel that is identically zero in every
                associative coordinate system.
    shuffled    the sheaf instrument on overlaps permuted across edges.  Same
                dimension, same arithmetic, destroyed correspondence.  This is
                the thesis's own "shuffled overlaps" control.

Two facts here are proved, not measured
---------------------------------------
1. **No scalar character can see a quaternionic obstruction.**  Every transition
   L_q for a unit quaternion q lies in SO(4), whose abelianisation is trivial: the
   only multiplicative character is the constant 1.  So for the commutator regime
   below, det(H(gamma)) = 1 for every cycle whether it is defective or not --
   not approximately, not with high probability, but identically.  No sample
   size, tuning or noise model can rescue a homomorphic scalar coordinate here.
   Locked by ``test_no_scalar_character_separates_the_commutator_regime``.

2. **Non-associativity is invisible to linear transport, and destroys the
   obstruction theory as soon as it is made visible.**  If transitions act as
   linear maps, composition is matrix composition, which is associative; the
   associator channel is then identically zero and the octonionic instrument
   degenerates *exactly* to the sheaf instrument.  Octonionic coordinates can
   only carry information if the architecture itself composes evidence in the
   algebra -- an assumption about the system, not a property of the data.  But
   once that assumption is made, a worse problem appears.  A vertex gauge g_v
   induces a flat connection -- transitions a_ij = g_j g_i^{-1} whose holonomy
   round every cycle is the identity -- if and only if left multiplication is a
   homomorphism, L_a L_b = L_{ab}.  :func:`flatness_ladder` measures that, and it
   holds **exactly through dimension 4**.  At dimension 8 the *clean* sheaf
   already has nonzero holonomy on every cycle, so "no obstruction" is not even
   definable and there is nothing for a defect to stand out against.  The reason
   is structural: unit octonions form a Moufang loop, not a group, and sheaf
   cohomology needs a group.  By Artin's theorem any two of them still generate
   an associative subalgebra, so the failure begins exactly at cycles that mix
   three independent directions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cayley_dickson import cd_multiply

__all__ = ["Nerve", "CellularSheaf", "ring_of_worldlets", "gluing_defect",
           "left_multiplication_matrix", "random_unit_hypercomplex",
           "quaternion_group", "make_obstructed_sheaf", "localise",
           "INSTRUMENTS", "auroc", "left_action_is_associative_on",
           "flatness_ladder"]


# --------------------------------------------------------------------------
# The nerve
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Nerve:
    """A cover's nerve: worldlets as vertices, overlaps as undirected edges."""

    n_worldlets: int
    edges: tuple

    def __post_init__(self) -> None:
        for (i, j) in self.edges:
            if not (0 <= i < self.n_worldlets and 0 <= j < self.n_worldlets):
                raise ValueError(f"edge ({i}, {j}) outside {self.n_worldlets} worldlets")
            if i == j:
                raise ValueError("a worldlet does not overlap itself in the nerve")

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    @property
    def betti_1(self) -> int:
        """Cycle rank E - V + C: the number of independent cycle obstructions.

        Over F_2 this is exactly dim H^1 of the constant sheaf, so it is the
        number of *bits* an observer must learn to know the obstruction class.
        That number, not the edge count, sets the query complexity in
        :mod:`aionq.interference`.
        """
        return self.n_edges - self.n_worldlets + self.n_components

    @property
    def n_components(self) -> int:
        seen, comps, adj = set(), 0, self.adjacency_list()
        for v in range(self.n_worldlets):
            if v in seen:
                continue
            comps += 1
            stack = [v]
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                stack.extend(adj[u])
        return comps

    def adjacency_list(self) -> dict:
        adj: dict = {v: [] for v in range(self.n_worldlets)}
        for (i, j) in self.edges:
            adj[i].append(j)
            adj[j].append(i)
        return adj

    def cycle_basis(self) -> list:
        """A fundamental cycle basis as lists of (edge index, traversal sign).

        A spanning forest is grown and each non-tree edge closes exactly one
        cycle.  The sign records direction, which matters the moment the
        transitions stop commuting.  Returns ``betti_1`` cycles.
        """
        parent: dict = {}
        tree: set = set()
        adj: dict = {v: [] for v in range(self.n_worldlets)}
        for k, (i, j) in enumerate(self.edges):
            adj[i].append((j, k))
            adj[j].append((i, k))

        for root in range(self.n_worldlets):
            if root in parent:
                continue
            parent[root] = None
            stack = [root]
            while stack:
                u = stack.pop()
                for (w, k) in adj[u]:
                    if w not in parent:
                        parent[w] = (u, k)
                        tree.add(k)
                        stack.append(w)

        cycles = []
        for k, (i, j) in enumerate(self.edges):
            if k in tree:
                continue
            path = self._tree_path(i, j, parent)
            if path is None:
                continue
            cycles.append(self._as_signed(path + [(j, i, k)]))
        return cycles

    def _tree_path(self, a: int, b: int, parent: dict):
        """Directed vertex path a -> b through the spanning forest, as triples."""
        up_a, up_b = self._to_root(a, parent), self._to_root(b, parent)
        anc = {v for v, _ in up_a} | {a}
        meet, tail = None, []
        cur = b
        while cur is not None:
            if cur in anc:
                meet = cur
                break
            up, e = parent[cur]
            tail.append((cur, up, e))
            cur = up
        if meet is None:
            return None
        out, cur = [], a
        while cur != meet:
            up, e = parent[cur]
            out.append((cur, up, e))
            cur = up
        out += [(v, u, e) for (u, v, e) in reversed(tail)]
        return out

    @staticmethod
    def _to_root(v: int, parent: dict) -> list:
        out, cur = [], v
        while parent.get(cur) is not None:
            up, e = parent[cur]
            out.append((up, e))
            cur = up
        return out

    def _as_signed(self, path) -> list:
        """Turn (from, to, edge) steps into (edge, +1 if edge is (from, to))."""
        signed = []
        for (u, v, e) in path:
            signed.append((e, 1 if self.edges[e] == (u, v) else -1))
        return signed


def ring_of_worldlets(n: int, chords: tuple = ()) -> Nerve:
    """A ring of n worldlets plus optional chords.  betti_1 = 1 + len(chords)."""
    edges = [(i, (i + 1) % n) for i in range(n)]
    edges += [tuple(int(x) for x in c) for c in chords]
    return Nerve(n, tuple(edges))


# --------------------------------------------------------------------------
# Hypercomplex transitions
# --------------------------------------------------------------------------

def random_unit_hypercomplex(dim: int, rng) -> np.ndarray:
    """A unit-norm element of the dim-dimensional Cayley-Dickson algebra."""
    v = rng.normal(size=dim)
    return v / np.linalg.norm(v)


def left_multiplication_matrix(a: np.ndarray) -> np.ndarray:
    """The real matrix L_a: x -> a x for a Cayley-Dickson element a.

    For unit a this is orthogonal in every dimension, the octonions included:
    left multiplication by a unit octonion IS an orthogonal map.  What fails at
    dimension 8 is not orthogonality but *composition*: L_a L_b != L_{ab},
    because (ab)c != a(bc).  That failure is the only thing an octonionic
    instrument can see and no associative one can.
    """
    a = np.asarray(a, dtype=float)
    dim = a.size
    cols = []
    for k in range(dim):
        e = np.zeros(dim)
        e[k] = 1.0
        cols.append(cd_multiply(a, e))
    return np.stack(cols, axis=1)


def left_action_is_associative_on(a, b, dim: int = 8, tol: float = 1e-9) -> bool:
    """Check L_a L_b == L_{ab} for specific elements, rather than assuming it.

    True for a, b in an associative subalgebra (H inside O), false in general.
    Used to keep the "clean" part of the octonionic regime honestly consistent.
    """
    lhs = left_multiplication_matrix(a) @ left_multiplication_matrix(b)
    rhs = left_multiplication_matrix(cd_multiply(np.asarray(a, float),
                                                 np.asarray(b, float)))
    return bool(np.allclose(lhs, rhs, atol=tol))


def quaternion_group() -> list:
    """The eight elements of Q_8 as 4-vectors: +-1, +-i, +-j, +-k."""
    units = []
    for k in range(4):
        e = np.zeros(4)
        e[k] = 1.0
        units += [e, -e]
    return units


def _conjugate(a: np.ndarray) -> np.ndarray:
    out = -np.asarray(a, dtype=float).copy()
    out[0] = a[0]
    return out


def _one(dim: int) -> np.ndarray:
    e = np.zeros(dim)
    e[0] = 1.0
    return e


# --------------------------------------------------------------------------
# The sheaf
# --------------------------------------------------------------------------

@dataclass
class CellularSheaf:
    """A nerve with an orthogonal transition on every overlap.

    ``labels`` optionally carries the hypercomplex element behind each
    transition.  It is present only when the *architecture* is hypercomplex --
    that is, when the system composes evidence in the algebra rather than by
    matrix multiplication.  Instruments that use it say so.
    """

    nerve: Nerve
    transitions: list
    fiber_dim: int
    labels: list | None = None

    def __post_init__(self) -> None:
        if len(self.transitions) != self.nerve.n_edges:
            raise ValueError("one transition per overlap is required")
        for g in self.transitions:
            if g.shape != (self.fiber_dim, self.fiber_dim):
                raise ValueError(f"transition is not {self.fiber_dim}x{self.fiber_dim}")

    def edge_map(self, k: int, sign: int) -> np.ndarray:
        g = self.transitions[k]
        return g if sign > 0 else g.T

    def holonomy(self, cycle) -> np.ndarray:
        """Composite transition around a cycle of (edge index, sign) pairs."""
        h = np.eye(self.fiber_dim)
        for (k, s) in cycle:
            h = self.edge_map(k, s) @ h
        return h

    def label_holonomy(self, cycle, bracket: str = "left") -> np.ndarray:
        """Composite of the algebra labels around a cycle, with stated bracketing.

        ``left``  a(b(c ...))   ``right``  (... (ab)c)
        These agree in every associative algebra and differ in O.  The difference
        is the associator channel, and it is the entire hypercomplex claim.
        """
        if self.labels is None:
            raise ValueError("this sheaf carries no algebra labels")
        dim = self.labels[0].size
        elems = [self.labels[k] if s > 0 else _conjugate(self.labels[k])
                 for (k, s) in cycle]
        if bracket == "left":
            h = _one(dim)
            for a in elems:
                h = cd_multiply(a, h)
            return h
        h = _one(dim)
        for a in reversed(elems):
            h = cd_multiply(h, a)
        return h

    def coboundary(self, sections) -> list:
        """Per-edge disagreement x_j - G_ij x_i of a candidate assignment."""
        return [np.asarray(sections[j], dtype=float)
                - self.transitions[k] @ np.asarray(sections[i], dtype=float)
                for k, (i, j) in enumerate(self.nerve.edges)]

    def sheaf_laplacian(self) -> np.ndarray:
        """L = delta^T delta.  PSD by construction; its kernel is the sections."""
        d, n, m = self.fiber_dim, self.nerve.n_worldlets, self.nerve.n_edges
        delta = np.zeros((m * d, n * d))
        for k, (i, j) in enumerate(self.nerve.edges):
            delta[k * d:(k + 1) * d, j * d:(j + 1) * d] = np.eye(d)
            delta[k * d:(k + 1) * d, i * d:(i + 1) * d] = -self.transitions[k]
        return delta.T @ delta


def gluing_defect(sheaf: CellularSheaf, sections) -> float:
    """Total squared disagreement of an assignment.  Nonnegative, always.

    The thesis's formalisation programme asks for exactly this to be proved --
    "gluing defect is nonnegative".  It is a sum of squared norms, so it is, and
    it vanishes precisely when the assignment is a global section.
    """
    return float(sum(float(r @ r) for r in sheaf.coboundary(sections)))


# --------------------------------------------------------------------------
# Obstruction generators
# --------------------------------------------------------------------------

def _haar_orthogonal(dim: int, rng) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(dim, dim)))
    return q * np.sign(np.diag(r))


def _interpolate_orthogonal(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """Move t of the way from a to b, staying orthogonal (polar retraction)."""
    u, _, vt = np.linalg.svd((1.0 - t) * a + t * b)
    return u @ vt


def make_obstructed_sheaf(nerve: Nerve, defect_edges, rng, kind: str = "generic",
                          dim: int = 4, strength: float = 1.0) -> CellularSheaf:
    """A sheaf whose obstruction is hidden in cycles, never in single overlaps.

    kind:
      ``generic``     transitions Haar-orthogonal in O(dim); the defect replaces
                      a transition with another Haar element.
      ``commutator``  transitions L_q for q in Q_8; the defect multiplies by -1,
                      the generator of the commutator subgroup [Q_8, Q_8].  Every
                      L_q lies in SO(4), so every multiplicative character is
                      identically 1 on defective and clean cycles alike.
      ``hypercomplex`` transitions L_a for unit elements a of the ``dim``-
                      dimensional Cayley-Dickson algebra, built from a vertex
                      gauge exactly as above.  For dim <= 4 this is an exact
                      coboundary; for dim >= 8 it is NOT, because L stops being a
                      homomorphism, and the clean sheaf carries holonomy of its
                      own.  That is the point of the regime, not a bug in it --
                      see :func:`flatness_ladder`.
    """
    defect = {int(e) for e in defect_edges}

    if kind == "generic":
        gauge = [_haar_orthogonal(dim, rng) for _ in range(nerve.n_worldlets)]
        trans = [gauge[j] @ gauge[i].T for (i, j) in nerve.edges]
        for k in sorted(defect):
            trans[k] = _interpolate_orthogonal(
                trans[k], _haar_orthogonal(dim, rng) @ trans[k], strength)
        return CellularSheaf(nerve, trans, dim)

    if kind == "commutator":
        q8 = quaternion_group()
        gauge = [q8[int(rng.integers(len(q8)))] for _ in range(nerve.n_worldlets)]
        labels = [cd_multiply(gauge[j], _conjugate(gauge[i]))
                  for (i, j) in nerve.edges]
        for k in sorted(defect):
            labels[k] = -labels[k]                       # multiply by -1 in [Q_8, Q_8]
        return CellularSheaf(nerve, [left_multiplication_matrix(a) for a in labels],
                             4, labels=labels)

    if kind == "hypercomplex":
        gauge = [random_unit_hypercomplex(dim, rng) for _ in range(nerve.n_worldlets)]
        labels = [cd_multiply(gauge[j], _conjugate(gauge[i]))
                  for (i, j) in nerve.edges]
        for k in sorted(defect):
            labels[k] = random_unit_hypercomplex(dim, rng)
        return CellularSheaf(nerve, [left_multiplication_matrix(a) for a in labels],
                             dim, labels=labels)

    raise ValueError(f"unknown obstruction kind {kind!r}")


def flatness_ladder(nerve: Nerve, dims=(1, 2, 4, 8, 16), samples: int = 200,
                    rng=None) -> dict:
    """Does a vertex gauge induce a FLAT connection?  Answered per dimension.

    Build the clean sheaf a_ij = g_j g_i^{-1} from random unit elements of the
    dim-dimensional Cayley-Dickson algebra, with **no defect at all**, and measure
    the holonomy that remains.  It vanishes exactly when L_a L_b = L_{ab}.

    Returns {dim: (mean ||H - I||_F, max ||H - I||_F)}.  The mean is 0 through
    dimension 4 and positive from dimension 8 on, and that single fact is what
    limits the thesis's hypercomplex clause: above the quaternions there is no
    zero to measure a defect against.
    """
    rng = np.random.default_rng(0) if rng is None else rng
    cycles = nerve.cycle_basis()
    out = {}
    for dim in dims:
        norms = []
        for _ in range(samples):
            s = make_obstructed_sheaf(nerve, [], rng, kind="hypercomplex", dim=dim)
            eye = np.eye(dim)
            norms += [float(np.linalg.norm(s.holonomy(c) - eye, "fro")) for c in cycles]
        out[dim] = (float(np.mean(norms)), float(np.max(norms)))
    return out


# --------------------------------------------------------------------------
# Instruments: one algorithm, several coordinate systems
# --------------------------------------------------------------------------

def _incidence(nerve: Nerve, cycles) -> np.ndarray:
    inc = np.zeros((len(cycles), nerve.n_edges))
    for c, cycle in enumerate(cycles):
        for (k, _s) in cycle:
            inc[c, k] = 1.0
    return inc


def _spread_blame(vals: np.ndarray, inc: np.ndarray) -> np.ndarray:
    """Share each cycle's obstruction equally among its edges.

    Deliberately the crudest defensible attribution rule, so that no instrument
    can win through a cleverer inference step.  The only thing that varies
    between instruments is the coordinate system that produced ``vals``.
    """
    lengths = np.maximum(inc.sum(axis=1), 1.0)
    return (inc * (vals / lengths)[:, None]).sum(axis=0)


def _scored(sheaf, cycles, score):
    inc = _incidence(sheaf.nerve, cycles)
    vals = np.array([score(c) for c in cycles], dtype=float)
    return _spread_blame(vals, inc)


def _instr_graph(sheaf, cycles, rng):
    """Topology only: an edge is suspect in proportion to how many cycles use it."""
    return _incidence(sheaf.nerve, cycles).sum(axis=0)


def _instr_scalar(sheaf, cycles, rng):
    """One real number per overlap, tr(G)/d, aggregated around the cycle."""
    d = sheaf.fiber_dim
    s = np.array([np.trace(g) / d for g in sheaf.transitions])
    return _scored(sheaf, cycles,
                   lambda c: abs(sum(s[k] for (k, _) in c) - len(c)))


def _instr_character(sheaf, cycles, rng):
    """The abelianisation det: O(d) -> {+1, -1}: the only homomorphic scalar."""
    dets = np.array([np.linalg.det(g) for g in sheaf.transitions])

    def score(cycle):
        p = 1.0
        for (k, _s) in cycle:
            p *= dets[k]
        return abs(p - 1.0)

    return _scored(sheaf, cycles, score)


def _instr_sheaf(sheaf, cycles, rng):
    """Full matrix holonomy at the sheaf's own fiber dimension."""
    eye = np.eye(sheaf.fiber_dim)
    return _scored(sheaf, cycles,
                   lambda c: float(np.linalg.norm(sheaf.holonomy(c) - eye, "fro")))


_QUATERNION_BASIS: np.ndarray | None = None
_QUATERNION_BASIS_BUILDS: int = 0


def _quaternion_basis() -> np.ndarray:
    """The (16, 4) matrix whose columns are vec(L_1), vec(L_i), vec(L_j), vec(L_k).

    Cached, because rebuilding it per edge is measurably more expensive.

    An earlier docstring asserted "131x the cost of the matrix one" and "13x
    cached".  Neither number was ever measured -- an external reviewer flagged
    them as prose presented as a result, and the flag was correct.  Benchmarked
    (200 reps, V=9, E=13, dim 4):

        sheaf (baseline)       79.6 us    1.00x
        quaternion, cached   1371.1 us   17.22x
        quaternion, uncached 2214.9 us   27.81x

    So caching buys about 1.6x, and the quaternionic instrument costs ~17x the
    matrix one either way.  That is still worth reporting in a compute-matched
    comparison, but it is a sixth of what was claimed.

    R4-B.  Those figures are HISTORICAL AND ENVIRONMENT-SPECIFIC, not constants.
    They are reproduced by ``experiments/run_instrument_benchmark.py``, which
    emits raw timings plus a Python/NumPy/BLAS/CPU envelope; a wall-clock ratio
    is not asserted anywhere in the correctness suite, because a loaded CI runner
    would then fail a test about arithmetic.  What the suite proves instead is
    the functional claim -- one construction, then reuse -- via the counter
    below.
    """
    global _QUATERNION_BASIS, _QUATERNION_BASIS_BUILDS
    if _QUATERNION_BASIS is None:
        _QUATERNION_BASIS_BUILDS += 1
        _QUATERNION_BASIS = np.stack(
            [left_multiplication_matrix(e).reshape(-1) for e in np.eye(4)], axis=1)
    return _QUATERNION_BASIS


def quaternion_basis_builds() -> int:
    """How many times the cached basis has actually been constructed.

    R4-B.  The previous test timed cached-quaternion against sheaf and accepted
    any ratio in (3, 60).  That checks neither the uncached path nor reuse: a
    cache that silently rebuilt every call would sit comfortably inside the
    interval.  Reuse is a counting question, so it is counted.
    """
    return _QUATERNION_BASIS_BUILDS


def reset_quaternion_basis() -> None:
    """Drop the cache AND the build counter.  For tests; restores global state."""
    global _QUATERNION_BASIS, _QUATERNION_BASIS_BUILDS
    _QUATERNION_BASIS = None
    _QUATERNION_BASIS_BUILDS = 0


def _nearest_unit_quaternion(g: np.ndarray) -> np.ndarray:
    """The unit quaternion q minimising ||L_q - g||_F.

    L_q is linear in q, so this is one least-squares projection followed by a
    normalisation: no iteration, and the same cost for every edge.  For a
    genuinely quaternionic transition it is exact; for a generic O(4) element it
    discards two of the six parameters, which is precisely the loss the thesis
    predicts should make hypercomplex coordinates unhelpful off their home
    ground.
    """
    basis = _quaternion_basis()
    coef = basis.T @ g.reshape(-1) / 4.0        # columns are orthogonal, norm 2
    nrm = float(np.linalg.norm(coef))
    return _one(4) if nrm < 1e-12 else coef / nrm


def _instr_quaternion(sheaf, cycles, rng):
    """Compose in H after projecting each transition to its nearest quaternion."""
    if sheaf.fiber_dim != 4:
        return _instr_sheaf(sheaf, cycles, rng)
    qs = [_nearest_unit_quaternion(g) for g in sheaf.transitions]
    one = _one(4)

    def score(cycle):
        h = one.copy()
        for (k, s) in cycle:
            h = cd_multiply(qs[k] if s > 0 else _conjugate(qs[k]), h)
        return float(np.linalg.norm(h - one))

    return _scored(sheaf, cycles, score)


def _instr_octonion(sheaf, cycles, rng):
    """Compose the labels in O, left-bracketed.

    Requires the architectural assumption that the system transports evidence by
    multiplying in the algebra rather than by composing linear maps.  Without
    that assumption this instrument is exactly ``sheaf`` and is reported as such.
    """
    if sheaf.labels is None:
        return _instr_sheaf(sheaf, cycles, rng)
    one = _one(sheaf.labels[0].size)
    return _scored(sheaf, cycles,
                   lambda c: float(np.linalg.norm(sheaf.label_holonomy(c, "left") - one)))


def _instr_associator(sheaf, cycles, rng):
    """The left- minus right-bracketed product: zero in any associative algebra.

    This is the only channel in this module that no associative coordinate system
    can express.  It is also, on the evidence of Round S3, not a localisation
    advantage -- it separates *bracketing sensitivity*, which is a different
    question from *where the defect is*.
    """
    if sheaf.labels is None:
        return np.zeros(sheaf.nerve.n_edges)
    return _scored(sheaf, cycles,
                   lambda c: float(np.linalg.norm(sheaf.label_holonomy(c, "left")
                                                  - sheaf.label_holonomy(c, "right"))))


def _degeneracy_safe_cut(vals: np.ndarray, k: int, rtol: float = 1e-8) -> int:
    """Extend k until it falls in a real spectral gap, never inside an eigenspace.

    The invariance of :func:`_instr_laplacian` rests on summing over a **whole**
    eigenspace, so that an orthogonal mixing inside it cannot change the score.
    Cutting at a fixed ``k = fiber_dim`` violates that precondition exactly when
    ``lambda_k == lambda_{k-1}``, and an ACAF sweep found it: 9 of 950 instances
    broke invariance, all of them at cycle rank 1, with median gap at the cut of
    6e-16 against 6e-1 where invariance held.

    So the cut is moved to the end of whatever degenerate block it lands in.  The
    tolerance is relative to the spectral scale, because the Laplacian's scale
    varies with fiber dimension and graph size.
    """
    if vals.size == 0:
        return 0
    k = max(1, min(k, vals.size))
    scale = max(float(np.max(np.abs(vals))), 1e-300)
    while k < vals.size and (vals[k] - vals[k - 1]) <= rtol * scale:
        k += 1
    return k


def _instr_laplacian(sheaf, cycles, rng):
    """Per-overlap Dirichlet energy of the sheaf Laplacian's lowest eigenspace.

    **This instrument never mentions a cycle basis.**  That is its entire point.
    Every other instrument here spreads blame over a *fundamental* cycle basis,
    which is an arbitrary choice of spanning tree, and Round S4 measured what that
    costs: the sheaf instrument's AUROC moves 0.789 -> 0.551 under an admissible
    worldlet relabelling because a different tree yields different cycles.

    Here the score is built from the sheaf Laplacian L = delta^T delta alone:

        r_e = sum over an orthonormal basis {x^k} of the lowest eigenspace of
              || x_j^k - G_e x_i^k ||^2

    Two invariances hold by construction rather than by measurement.  Relabelling
    worldlets conjugates L by a block permutation, so its eigenvectors permute and
    each edge carries its own residual along.  An orthogonal gauge Q sends
    x_j - G x_i to Q(x_j - G x_i), which preserves the norm.  And summing over a
    whole eigenspace rather than one eigenvector makes the score independent of
    which orthonormal basis diagonalisation happened to return, which is what
    makes it well defined when the eigenvalue is degenerate -- and it is degenerate
    exactly when the sheaf is flat.
    """
    d, n = sheaf.fiber_dim, sheaf.nerve.n_worldlets
    lap = sheaf.sheaf_laplacian()
    vals, vecs = np.linalg.eigh(lap)
    k = _degeneracy_safe_cut(vals, min(d, vals.size))
    basis = vecs[:, :k]                       # a WHOLE eigenspace, never a part

    scores = np.zeros(sheaf.nerve.n_edges)
    for e, (i, j) in enumerate(sheaf.nerve.edges):
        xi = basis[i * d:(i + 1) * d, :]
        xj = basis[j * d:(j + 1) * d, :]
        resid = xj - sheaf.transitions[e] @ xi
        scores[e] = float(np.sum(resid * resid))
    return scores


def _instr_shuffled(sheaf, cycles, rng):
    """The sheaf instrument on overlaps permuted across edges.

    Same dimension, same arithmetic, same attribution rule, destroyed
    correspondence.  Anything above chance here is an artefact of the scoring.
    """
    perm = rng.permutation(sheaf.nerve.n_edges)
    return _instr_sheaf(CellularSheaf(sheaf.nerve,
                                      [sheaf.transitions[p] for p in perm],
                                      sheaf.fiber_dim), cycles, rng)


INSTRUMENTS = {
    "graph": _instr_graph,
    "scalar": _instr_scalar,
    "character": _instr_character,
    "sheaf": _instr_sheaf,
    "laplacian": _instr_laplacian,
    "quaternion": _instr_quaternion,
    "octonion": _instr_octonion,
    "associator": _instr_associator,
    "shuffled": _instr_shuffled,
}


def localise(sheaf: CellularSheaf, instrument: str, rng=None, cycles=None):
    """Per-edge suspicion scores from one coordinate system.

    Every instrument sees the same nerve, the same cycle basis and the same
    attribution rule.  Only the representation of the transitions differs.
    """
    if instrument not in INSTRUMENTS:
        raise ValueError(f"unknown instrument {instrument!r}; have {sorted(INSTRUMENTS)}")
    rng = np.random.default_rng(0) if rng is None else rng
    cycles = sheaf.nerve.cycle_basis() if cycles is None else cycles
    return INSTRUMENTS[instrument](sheaf, cycles, rng)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def auroc(scores, labels) -> float:
    """Rank AUROC for edge localisation, with ties averaged.

    Polarity is fixed here, unlike Round S1: an instrument's contract is that a
    HIGHER score means more suspect, and every instrument above is written that
    way.  Giving each its best direction post hoc -- correct in S1, where the
    baselines carried no pre-registered sign -- would be cheating here, because
    the sign is part of the instrument's specification.

    Ties are averaged rather than broken, or a constant-score instrument (the
    graph instrument on a vertex-transitive nerve, for one) would read as a
    perfect 0 or 1 instead of the chance 0.5 it deserves.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    pos, neg = scores[labels], scores[~labels]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    allv = np.concatenate([pos, neg])
    order = allv.argsort()
    raw = np.empty(allv.size, dtype=float)
    raw[order] = np.arange(1, allv.size + 1, dtype=float)
    _, inv, counts = np.unique(np.round(allv, 12), return_inverse=True,
                              return_counts=True)
    sums = np.zeros(counts.size)
    np.add.at(sums, inv, raw)
    ranks = (sums / counts)[inv]
    rp = float(ranks[:pos.size].sum())
    return float((rp - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))
