from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import numpy as np

from .gf_frames import gf16_mul

TOL = 1e-12


def parity(x: int) -> int:
    return x.bit_count() & 1


def hidden_pairs(secret: int) -> list[tuple[int, int]]:
    if not 0 < secret < 16:
        raise ValueError("secret must be a nonzero 4-bit integer")
    seen = set()
    pairs = []
    for x in range(16):
        if x in seen:
            continue
        y = x ^ secret
        a, b = sorted((x, y))
        pairs.append((a, b))
        seen.add(a); seen.add(b)
    return sorted(pairs)


def quotient_map(secret: int) -> tuple[dict[int, int], list[tuple[int, int]]]:
    pairs = hidden_pairs(secret)
    qmap = {}
    for qi, (a, b) in enumerate(pairs):
        qmap[a] = qi
        qmap[b] = qi
    return qmap, pairs


def projection_weights(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    w = rng.normal(size=8) + 1j * rng.normal(size=8)
    # Deterministically avoid degenerate/near-zero quotient fibers.
    phases = np.exp(1j * np.arange(8) * (np.pi / 17.0))
    w = w + 0.35 * phases
    w /= np.linalg.norm(w)
    return w.astype(np.complex128)


def substrate_state(secret: int) -> tuple[np.ndarray, dict[int, int]]:
    qmap, _ = quotient_map(secret)
    psi = np.zeros((16, 8), dtype=np.complex128)
    for x in range(16):
        psi[x, qmap[x]] = 0.25
    return psi, qmap


def projected_state_explicit(secret: int, weights: np.ndarray) -> np.ndarray:
    substrate, _ = substrate_state(secret)
    # Projection by bra <w| on quotient register.
    raw = substrate @ np.conjugate(weights)
    norm = np.linalg.norm(raw)
    if norm <= TOL:
        raise ValueError("degenerate projection")
    return raw / norm


def projected_state_direct(secret: int, weights: np.ndarray) -> np.ndarray:
    qmap, _ = quotient_map(secret)
    raw = np.array([0.25 * np.conjugate(weights[qmap[x]]) for x in range(16)], dtype=np.complex128)
    norm = np.linalg.norm(raw)
    if norm <= TOL:
        raise ValueError("degenerate projection")
    return raw / norm


def walsh4(state: np.ndarray) -> np.ndarray:
    state = np.asarray(state, dtype=np.complex128)
    if state.shape != (16,):
        raise ValueError("state must have 16 amplitudes")
    out = np.empty(16, dtype=np.complex128)
    for y in range(16):
        out[y] = sum(((-1) ** parity(x & y)) * state[x] for x in range(16)) / 4.0
    return out


def forbidden_mask(secret: int) -> np.ndarray:
    return np.array([parity(y & secret) == 1 for y in range(16)], dtype=bool)


def _canonical_partition(cells) -> tuple[tuple[int, ...], ...]:
    canon = tuple(sorted((tuple(sorted(map(int, c))) for c in cells)))
    flat = [x for c in canon for x in c]
    if len(canon) != 4 or any(len(c) != 4 for c in canon):
        raise ValueError("partition must contain four cells of four labels")
    if sorted(flat) != list(range(16)) or len(set(flat)) != 16:
        raise ValueError("partition must be disjoint and exhaustive over 0..15")
    return canon


def additive_coset_partition(subspace) -> tuple[tuple[int, ...], ...]:
    h = set(map(int, subspace))
    if len(h) != 4 or 0 not in h:
        raise ValueError("subspace must contain four elements including zero")
    cells = []
    unseen = set(range(16))
    while unseen:
        r = min(unseen)
        cell = {r ^ h0 for h0 in h}
        cells.append(tuple(sorted(cell)))
        unseen -= cell
    return _canonical_partition(cells)


def gf4_scaled_subspaces() -> tuple[tuple[int, ...], ...]:
    base = (0, 1, 2, 3)
    seen = set()
    out = []
    for a in range(1, 16):
        h = tuple(sorted({gf16_mul(a, z) for z in base}))
        if h not in seen:
            seen.add(h)
            out.append(h)
    if len(out) != 5:
        raise AssertionError(f"expected five scaled GF(4) subspaces, got {len(out)}")
    return tuple(sorted(out))


def random_aligned_partition(secret: int, seed: int) -> tuple[tuple[int, ...], ...]:
    rng = np.random.default_rng(seed)
    pairs = hidden_pairs(secret)
    order = rng.permutation(len(pairs))
    cells = []
    for i in range(0, 8, 2):
        p1, p2 = pairs[int(order[i])], pairs[int(order[i+1])]
        cells.append(tuple(sorted(p1 + p2)))
    return _canonical_partition(cells)


def random_transverse_partition(secret: int, seed: int) -> tuple[tuple[int, ...], ...]:
    # Constructively split every hidden pair while maintaining 4x4 cell sizes.
    rng = np.random.default_rng(seed)
    pairs = hidden_pairs(secret)
    cells = [[] for _ in range(4)]
    cell_pairs = [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2),(0,1),(2,3)]
    perm = rng.permutation(4)
    cell_pairs = [(int(perm[a]), int(perm[b])) for a,b in cell_pairs]
    pair_order = rng.permutation(8)
    for pair_idx, (ca, cb) in zip(pair_order, cell_pairs):
        a,b = pairs[int(pair_idx)]
        if rng.integers(2):
            a,b = b,a
        cells[ca].append(a)
        cells[cb].append(b)
    return _canonical_partition(cells)


def relabel_partition(partition, seed: int) -> tuple[tuple[int, ...], ...]:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(16)
    cells = [tuple(int(perm[x]) for x in cell) for cell in partition]
    return _canonical_partition(cells)


def pair_cut_fraction(partition, secret: int) -> float:
    cells = _canonical_partition(partition)
    owner = {x: ai for ai, cell in enumerate(cells) for x in cell}
    pairs = hidden_pairs(secret)
    return sum(owner[a] != owner[b] for a,b in pairs) / len(pairs)


def translation_commutator_defect(partition, secret: int) -> float:
    cells = _canonical_partition(partition)
    T = np.zeros((16,16), dtype=np.float64)
    for x in range(16):
        T[x ^ secret, x] = 1.0
    sq = 0.0
    for cell in cells:
        p = np.zeros(16)
        p[list(cell)] = 1.0
        P = np.diag(p)
        C = P @ T - T @ P
        sq += float(np.linalg.norm(C, "fro") ** 2)
    # Maximum is 32 for a four-cell partition under a fixed-point-free involution.
    return float(np.sqrt(sq / 32.0))


@dataclass(frozen=True)
class PartitionMetrics:
    global_forbidden_mass: float
    sector_forbidden_mass: float
    offdiag_forbidden_real: float
    closure_defect: float
    pair_cut_fraction: float
    translation_commutator_defect: float
    sector_norm_sum: float


def evaluate_partition(state: np.ndarray, partition, secret: int) -> PartitionMetrics:
    state = np.asarray(state, dtype=np.complex128)
    cells = _canonical_partition(partition)
    mask = forbidden_mask(secret)
    full_w = walsh4(state)
    global_forbidden = float(np.sum(np.abs(full_w[mask]) ** 2).real)

    sectors = []
    sector_norm_sum = 0.0
    for cell in cells:
        s = np.zeros(16, dtype=np.complex128)
        s[list(cell)] = state[list(cell)]
        sectors.append(walsh4(s))
        sector_norm_sum += float(np.vdot(s, s).real)

    diag = float(sum(np.sum(np.abs(w[mask]) ** 2).real for w in sectors))
    off = 0.0 + 0.0j
    for a in range(len(sectors)):
        for b in range(len(sectors)):
            if a == b:
                continue
            off += np.sum(sectors[a][mask] * np.conjugate(sectors[b][mask]))
    closure = abs(global_forbidden - (diag + float(off.real)))
    return PartitionMetrics(
        global_forbidden_mass=global_forbidden,
        sector_forbidden_mass=diag,
        offdiag_forbidden_real=float(off.real),
        closure_defect=float(closure),
        pair_cut_fraction=pair_cut_fraction(cells, secret),
        translation_commutator_defect=translation_commutator_defect(cells, secret),
        sector_norm_sum=sector_norm_sum,
    )
