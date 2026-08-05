"""Transport fibers: which directions stay in the certified class, and which leave.

`matchgate_defect` showed that a boolean certificate is a threshold on residuals
that were always there, and that over a FINITE frame group -- relabelling, the
240 frames of AGL(1,16) -- exactly one residual moves.  A finite group cannot do
more than that.  Its orbit is 240 isolated points, its union of orbits is a
finite union of varieties of the same dimension, and no Kakeya-type phenomenon
can occur in it: dimension does not grow under finite unions.  The step measured
over AGL(1,16) is that fact, not a fact about hardness.

The geometry is in the CONTINUOUS frame group.  Take a gate on the certified
class and transport it along a one-parameter subgroup ``G(s) = G0 exp(i s H)``.
Some directions ``H`` keep it on the class for all ``s`` -- the class is a
subgroup, so containment is exact, not approximate.  Others leave immediately.
The first are the transport fibers; the second are the directions transverse to
them.  This is the Kakeya dichotomy in its proper setting: a tube is a fiber,
its direction is ``H``, and the question is how the fibers can be arranged.

MEASURED, on the nearest-neighbour matchgate class inside U(4):

    ambient dimension                        16
    tangent dimension of the class            7   (rank 9 Jacobian, clean gap)
    codimension                               9
    escape order in every transverse direction 1  (200 random directions, all 1.000)
    directions of order >= 2                   0

The 7 is not fitted: block-diagonal in the parity split gives ``U(2) x U(2)``,
dimension 8, and ``det A = det B`` is one real condition, so 7 exactly.  The
Jacobian's singular values are ``{2, sqrt2 x 8, 0 x 7}`` with a gap of ten orders
of magnitude, so the class is smooth at these points and its defining functions
are non-degenerate there.

THE PART THAT MATTERS FOR ANY HARMONIC-ANALYSIS PROGRAMME.  Escape order 1 in
every direction means the residual map is a SUBMERSION onto its image: the
constraint functions have surjective differential, with no direction in which
the class curves back and the first-order defect vanishes.  That is exactly the
non-degeneracy hypothesis a Falconer- or Kakeya-type estimate assumes (in the
Phong-Stein sense: non-degenerate mixed differential), and here it is not
assumed but verified, uniformly, at every point tested.  Whether anything
further follows is a separate question this module does not answer; see
`manifests/qsigma_r1c_transport_fiber_finding.json` for what is and is not
claimed.

WHY EXACT CONTAINMENT MATTERS.  The 7 tangent directions do not merely osculate
the class -- they lie in it exactly, because the class is a group and
``exp(i s H)`` stays in a subgroup when ``H`` is in its algebra.  A fiber here is
a geodesic of the class, not a curve tangent to it, so the "tube" has zero
thickness in the transverse residual and the dichotomy is sharp with nothing
in between.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "hermitian_basis",
    "defining_functions",
    "monomial_defining_functions",
    "CONSTRAINTS",
    "constraint_jacobian",
    "tangent_dimension",
    "escape_order",
    "fiber_report",
]

#: Entries coupling the even-parity subspace to the odd-parity one.
_OFF_BLOCK = ((0, 1), (0, 2), (3, 1), (3, 2), (1, 0), (2, 0), (1, 3), (2, 3))


def hermitian_basis(n: int = 4) -> tuple:
    """A real basis of the Hermitian ``n x n`` matrices, ``n**2`` of them.

    These generate the one-parameter subgroups ``exp(i s H)``, so they are the
    directions in which a gate can be transported.  The basis is the standard
    one and is deliberately NOT adapted to the class: how many of its elements
    happen to lie in the tangent space is a measurement, not a construction.
    """
    out = []
    for index in range(n):
        entry = np.zeros((n, n), dtype=complex)
        entry[index, index] = 1.0
        out.append(entry)
    for row in range(n):
        for column in range(row + 1, n):
            real = np.zeros((n, n), dtype=complex)
            real[row, column] = 1.0
            real[column, row] = 1.0
            out.append(real)
            imaginary = np.zeros((n, n), dtype=complex)
            imaginary[row, column] = -1j
            imaginary[column, row] = 1j
            out.append(imaginary)
    return tuple(out)


def defining_functions(matrix) -> np.ndarray:
    """The 18 real functions whose common zero set is the matchgate class.

    Sixteen from the eight off-block entries -- real and imaginary parts, each a
    LINEAR function of the matrix -- and two from ``det A - det B``, which is
    quadratic.  These are the smooth defining functions; `matchgate_defect`'s
    residuals are norms of them, which is the right object for reporting a
    distance and the wrong one for differentiating, since a norm is not smooth
    at its zero.  Both are needed and they are not the same map.
    """
    matrix = np.asarray(matrix)
    values = []
    for row, column in _OFF_BLOCK:
        values.append(matrix[row, column].real)
        values.append(matrix[row, column].imag)
    even = np.array([[matrix[0, 0], matrix[0, 3]],
                     [matrix[3, 0], matrix[3, 3]]])
    odd = np.array([[matrix[1, 1], matrix[1, 2]],
                    [matrix[2, 1], matrix[2, 2]]])
    difference = np.linalg.det(even) - np.linalg.det(odd)
    values.extend((difference.real, difference.imag))
    return np.array(values, dtype=float)


def monomial_defining_functions(matrix) -> np.ndarray:
    """The class `basis_permutation` certifies: one nonzero entry per row.

    A unitary is monomial -- a permutation times phases -- exactly when every
    pairwise product ``U[i,j] * U[i,k]`` within a row vanishes, and those
    products are the smooth defining functions.  Written this way to make the
    comparison with the matchgate class exact: same template, same instrument,
    different variety, and the two answers come out different in a way that is
    the point rather than a nuisance.

    Like the matchgate class, the monomial unitaries form a GROUP, so transport
    along its algebra is exact containment rather than osculation.
    """
    from itertools import combinations

    matrix = np.asarray(matrix)
    size = matrix.shape[0]
    values = []
    for row in range(size):
        for left, right in combinations(range(size), 2):
            product = matrix[row, left] * matrix[row, right]
            values.extend((product.real, product.imag))
    return np.array(values, dtype=float)


#: The two boolean strategies whose refusal decomposes into polynomial
#: constraints.  `stabilizer_rank` is absent on purpose: it charges
#: ``alpha * T`` and never refuses, so it has no threshold to decompose and
#: nothing here applies to it.  `contraction` is absent for the opposite reason:
#: its cost is already graded, and its boolean part refuses categorically (no
#: unitary, control flow) rather than metrically.
CONSTRAINTS = {
    "free_fermion": defining_functions,
    "basis_permutation": monomial_defining_functions,
}


def constraint_jacobian(matrix, defining=defining_functions,
                        step: float = 1e-6) -> np.ndarray:
    """Differential of `defining_functions` along each one-parameter subgroup.

    Central differences on ``F(G exp(+-i h H))``, so the derivative is taken
    along the group and not in the ambient linear space -- transporting a
    unitary by matrix addition would leave the group at first order and measure
    the wrong thing.
    """
    from scipy.linalg import expm

    matrix = np.asarray(matrix)
    columns = []
    for generator in hermitian_basis(matrix.shape[0]):
        forward = defining(matrix @ expm(1j * step * generator))
        backward = defining(matrix @ expm(-1j * step * generator))
        columns.append((forward - backward) / (2.0 * step))
    return np.array(columns).T


def tangent_dimension(matrix, defining=defining_functions,
                      tolerance: float = 1e-7) -> dict:
    """Dimension of the class through ``matrix``, from the rank of its Jacobian.

    Returns the singular values too, because the claim "rank 9" is only worth
    anything if there is a gap: a numerical rank read off a spectrum with no gap
    is a choice of tolerance wearing the costume of a measurement.  Measured
    here the spectrum is ``{2, sqrt2 x 8, ~1e-16 x 7}``.
    """
    matrix = np.asarray(matrix)
    ambient = matrix.shape[0] ** 2
    spectrum = np.linalg.svd(constraint_jacobian(matrix, defining),
                             compute_uv=False)
    largest = float(spectrum[0]) if spectrum.size else 0.0
    rank = int((spectrum > tolerance * max(largest, 1.0)).sum())
    smallest_kept = float(spectrum[rank - 1]) if rank else math.inf
    largest_dropped = float(spectrum[rank]) if rank < spectrum.size else 0.0
    return {
        "ambient": ambient,
        "rank": rank,
        "tangent": ambient - rank,
        "codimension": rank,
        "singular_values": tuple(float(value) for value in spectrum),
        "gap": (smallest_kept / largest_dropped) if largest_dropped else math.inf,
        "on_the_class": float(np.linalg.norm(defining(matrix))),
    }


def escape_order(matrix, generator, residual, low: float = 1e-5,
                 high: float = 1e-3, samples: int = 9,
                 floor: float = 1e-13) -> float:
    """How fast a residual grows when ``matrix`` is transported along ``generator``.

    Log-log slope of ``residual(G exp(i s H))`` against ``s``.  ``inf`` means the
    residual never left the floor, which for a subgroup is exact containment
    rather than a small number: the transported point is in the class for every
    ``s``, not merely for small ``s``.
    """
    from scipy.linalg import expm

    matrix = np.asarray(matrix)
    scales = np.geomspace(low, high, samples)
    values = np.array([residual(matrix @ expm(1j * scale * generator))
                       for scale in scales])
    if values.max() < floor:
        return math.inf
    slope = np.polyfit(np.log(scales), np.log(np.maximum(values, 1e-300)), 1)[0]
    return float(slope)


def fiber_report(matrix, residual, defining=defining_functions,
                 random_directions: int = 200, seed: int = 3) -> dict:
    """The full dichotomy at one point: what stays, what leaves, and how fast.

    Random directions are sampled in addition to the basis because the standard
    Hermitian basis is not adapted to the class -- how many of its elements land
    in the tangent space is an accident of coordinates.  A uniform sample of
    Hermitian directions almost surely misses the tangent space entirely, so it
    measures the escape order of the GENERIC direction, which is the quantity a
    transversality claim is about.
    """
    matrix = np.asarray(matrix)
    dimension = matrix.shape[0]
    basis_orders = tuple(escape_order(matrix, generator, residual)
                         for generator in hermitian_basis(dimension))

    generator = np.random.default_rng(seed)
    sampled = []
    for _ in range(random_directions):
        raw = (generator.normal(size=(dimension, dimension))
               + 1j * generator.normal(size=(dimension, dimension)))
        sampled.append(escape_order(matrix, (raw + raw.conj().T) / 2.0, residual))

    finite = [value for value in basis_orders + tuple(sampled) if math.isfinite(value)]
    return {
        "geometry": tangent_dimension(matrix, defining),
        "basis_directions": len(basis_orders),
        "basis_contained": sum(1 for value in basis_orders if math.isinf(value)),
        "basis_orders": basis_orders,
        "random_directions": random_directions,
        "random_contained": sum(1 for value in sampled if math.isinf(value)),
        "escape_order_min": min(finite) if finite else math.nan,
        "escape_order_max": max(finite) if finite else math.nan,
        "directions_of_order_two_or_more": sum(1 for value in finite if value > 1.5),
    }
