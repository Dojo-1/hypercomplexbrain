r"""Finite-size Hofstadter-torus operators for the preregistered S9 probe.

This module implements the numerical instrument, not a claim of a
thermodynamic fractional quantum Hall phase.  The target observable is the
first Chern number of a finite-dimensional, rank-two low-energy bundle over
boundary twists.  Individual eigenvector phases (and rotations inside a
nearly-degenerate eigenspace) are deliberately not treated as observables.

The hopping convention is the one fixed before the S9 target run:

.. math::

   c_x(x,y) = \exp(-2\pi i\alpha y)
              \exp(i\theta_x\,1[x=L_x-1]),

   c_y(x,y) = \exp(i\theta_y\,1[y=L_y-1]).

For every positive bond ``source -> destination`` the matrix contains
``-t*c`` and its Hermitian conjugate exactly once.  The positive plaquette
product ``+x,+y,-x,-y`` is therefore ``exp(+2*pi*i*alpha)``.

The non-Abelian Chern instrument follows the determinant-link discretization
of Fukui, Hatsugai, and Suzuki.  It uses the unitary polar factor of each
neighbor overlap and reports, rather than silently adjudicates, the overlap,
branch, and integrality diagnostics needed by the runner.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import ArpackNoConvergence, eigsh

__all__ = [
    "ChernReport",
    "EigensolverConfig",
    "Eigensystem",
    "FQHEEigensolverError",
    "FQHEResourceLimit",
    "FixedParticleBasis",
    "HofstadterTorus",
    "PolarLink",
    "bundle_spectral_report",
    "determinant_polar_link",
    "deterministic_complex_v0",
    "fhs_chern",
    "fixed_particle_basis",
    "haar_unitary",
    "hard_core_hamiltonian",
    "hermiticity_defect",
    "lowest_eigensystem",
    "maximum_plaquette_flux_defect",
    "plaquette_phases",
    "positive_bond_phase",
    "scramble_bundle_frames",
    "single_particle_hamiltonian",
    "site_index",
    "twist_periodicity_defects",
]


_TWO_PI = 2.0 * math.pi


class FQHEEigensolverError(RuntimeError):
    """Typed failure for a missing or non-converged required eigensystem.

    A caller should classify this as inconclusive numerical execution.  It is
    not evidence against the physical hypothesis and must not trigger an
    undeclared solver-parameter retry.
    """

    def __init__(
        self,
        message: str,
        *,
        partial_eigenpairs: int = 0,
        failure_kind: str = "EIGENSOLVER",
    ) -> None:
        super().__init__(message)
        self.partial_eigenpairs = int(partial_eigenpairs)
        self.failure_kind = str(failure_kind)


class FQHEResourceLimit(RuntimeError):
    """Typed stop used by the integration runner for its declared budget."""


def _require_plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    return int(value)


def _require_finite_twists(theta_x: float, theta_y: float) -> tuple[float, float]:
    theta_x = float(theta_x)
    theta_y = float(theta_y)
    if not math.isfinite(theta_x) or not math.isfinite(theta_y):
        raise ValueError("boundary twists must be finite")
    return theta_x, theta_y


@dataclass(frozen=True)
class HofstadterTorus:
    """Rectangular Hofstadter torus in the preregistered Landau gauge."""

    lx: int = 6
    ly: int = 4
    flux_numerator: int = 1
    flux_denominator: int = 4
    hopping: float = 1.0

    def __post_init__(self) -> None:
        lx = _require_plain_int(self.lx, "lx")
        ly = _require_plain_int(self.ly, "ly")
        numerator = _require_plain_int(self.flux_numerator, "flux_numerator")
        denominator = _require_plain_int(
            self.flux_denominator, "flux_denominator"
        )
        hopping = float(self.hopping)
        if lx < 2 or ly < 2:
            raise ValueError("a plaquette torus requires lx >= 2 and ly >= 2")
        if denominator <= 0:
            raise ValueError("flux_denominator must be positive")
        if not math.isfinite(hopping):
            raise ValueError("hopping must be finite")
        if (numerator * ly) % denominator != 0:
            raise ValueError(
                "selected Landau gauge is not periodic in y: "
                "flux_numerator*ly must be divisible by flux_denominator"
            )
        object.__setattr__(self, "lx", lx)
        object.__setattr__(self, "ly", ly)
        object.__setattr__(self, "flux_numerator", numerator)
        object.__setattr__(self, "flux_denominator", denominator)
        object.__setattr__(self, "hopping", hopping)

    @property
    def n_sites(self) -> int:
        return self.lx * self.ly

    @property
    def alpha(self) -> float:
        return self.flux_numerator / self.flux_denominator

    @property
    def total_flux_quanta(self) -> float:
        return self.alpha * self.n_sites


@dataclass(frozen=True)
class FixedParticleBasis:
    """Fixed-occupation hard-core basis in exact combination order."""

    n_sites: int
    n_particles: int
    states: tuple[int, ...]
    index: dict[int, int]


@dataclass(frozen=True)
class EigensolverConfig:
    """ARPACK settings fixed by the S9 preregistration."""

    k: int = 3
    which: str = "SA"
    tolerance: float = 1e-11
    max_iterations: int = 20_000
    ncv: int = 40

    def __post_init__(self) -> None:
        k = _require_plain_int(self.k, "k")
        max_iterations = _require_plain_int(
            self.max_iterations, "max_iterations"
        )
        ncv = _require_plain_int(self.ncv, "ncv")
        tolerance = float(self.tolerance)
        which = str(self.which)
        if k <= 0:
            raise ValueError("k must be positive")
        if which not in {"LM", "SM", "LA", "SA", "BE"}:
            raise ValueError(f"unsupported eigsh selector: {which!r}")
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("tolerance must be finite and positive")
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if ncv <= k:
            raise ValueError("ncv must be greater than k")
        object.__setattr__(self, "k", k)
        object.__setattr__(self, "which", which)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "max_iterations", max_iterations)
        object.__setattr__(self, "ncv", ncv)


@dataclass(frozen=True)
class Eigensystem:
    """Rayleigh--Ritz eigenpairs and their recomputed diagnostics."""

    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    residual_norms: np.ndarray
    orthonormality_defect: float
    span_preservation_sine: float


@dataclass(frozen=True)
class PolarLink:
    """Determinant of the unitary polar factor of one frame overlap."""

    value: complex
    singular_values: np.ndarray


@dataclass(frozen=True)
class ChernReport:
    """Raw FHS field and the diagnostics required for gate adjudication."""

    chern: float
    rounded_chern: int
    integer_residual: float
    links_x: np.ndarray
    links_y: np.ndarray
    plaquette_phases: np.ndarray
    minimum_overlap_singular_value: float
    maximum_absolute_plaquette_phase: float


def fixed_particle_basis(
    n_sites: int,
    n_particles: int,
) -> FixedParticleBasis:
    """Construct the exact ``itertools.combinations`` bit-mask basis.

    The resulting masks are intentionally *not* integer-sorted.  For more than
    one particle, sorting by mask would differ from the preregistered
    lexicographic order of occupied-site tuples.
    """

    n_sites = _require_plain_int(n_sites, "n_sites")
    n_particles = _require_plain_int(n_particles, "n_particles")
    if n_sites <= 0:
        raise ValueError("n_sites must be positive")
    if not 0 <= n_particles <= n_sites:
        raise ValueError("n_particles must lie in [0, n_sites]")
    states = tuple(
        sum(1 << site for site in occupied)
        for occupied in itertools.combinations(range(n_sites), n_particles)
    )
    return FixedParticleBasis(
        n_sites=n_sites,
        n_particles=n_particles,
        states=states,
        index={state: position for position, state in enumerate(states)},
    )


def _validate_basis(basis: FixedParticleBasis) -> None:
    n_sites = _require_plain_int(basis.n_sites, "basis.n_sites")
    n_particles = _require_plain_int(
        basis.n_particles, "basis.n_particles"
    )
    if n_sites <= 0 or not 0 <= n_particles <= n_sites:
        raise ValueError("malformed fixed-particle basis dimensions")
    expected_count = math.comb(n_sites, n_particles)
    if len(basis.states) != expected_count or len(basis.index) != expected_count:
        raise ValueError("basis cardinality does not match the declared sector")
    expected_states = fixed_particle_basis(n_sites, n_particles).states
    if tuple(basis.states) != expected_states:
        raise ValueError(
            "basis states are not in the required itertools.combinations order"
        )
    if any(
        basis.index.get(state) != position
        for position, state in enumerate(basis.states)
    ):
        raise ValueError("basis index does not invert the state sequence")


def site_index(model: HofstadterTorus, x: int, y: int) -> int:
    """Map an in-range lattice coordinate to its declared site index."""

    x = _require_plain_int(x, "x")
    y = _require_plain_int(y, "y")
    if not 0 <= x < model.lx or not 0 <= y < model.ly:
        raise ValueError(f"site coordinate {(x, y)} is outside the torus")
    return x + model.lx * y


def positive_bond_phase(
    model: HofstadterTorus,
    x: int,
    y: int,
    direction: str,
    theta_x: float,
    theta_y: float,
) -> complex:
    """Return the coefficient phase on one positive-oriented lattice bond."""

    theta_x, theta_y = _require_finite_twists(theta_x, theta_y)
    x = _require_plain_int(x, "x")
    y = _require_plain_int(y, "y")
    if not 0 <= x < model.lx or not 0 <= y < model.ly:
        raise ValueError(f"site coordinate {(x, y)} is outside the torus")
    if direction == "x":
        phase = np.exp(-1j * _TWO_PI * model.alpha * y)
        if x == model.lx - 1:
            phase *= np.exp(1j * theta_x)
        return complex(phase)
    if direction == "y":
        return complex(np.exp(1j * theta_y) if y == model.ly - 1 else 1.0)
    raise ValueError("direction must be 'x' or 'y'")


def _positive_bonds(
    model: HofstadterTorus,
    theta_x: float,
    theta_y: float,
) -> tuple[tuple[int, int, complex], ...]:
    bonds: list[tuple[int, int, complex]] = []
    for y in range(model.ly):
        for x in range(model.lx):
            source = site_index(model, x, y)
            x_destination = site_index(model, (x + 1) % model.lx, y)
            y_destination = site_index(model, x, (y + 1) % model.ly)
            bonds.append(
                (
                    source,
                    x_destination,
                    positive_bond_phase(
                        model, x, y, "x", theta_x, theta_y
                    ),
                )
            )
            bonds.append(
                (
                    source,
                    y_destination,
                    positive_bond_phase(
                        model, x, y, "y", theta_x, theta_y
                    ),
                )
            )
    return tuple(bonds)


def _onsite_vector(
    onsite: np.ndarray | Sequence[float] | None,
    n_sites: int,
) -> np.ndarray | None:
    if onsite is None:
        return None
    raw = np.asarray(onsite)
    if raw.shape != (n_sites,):
        raise ValueError(f"onsite must have shape ({n_sites},)")
    if not np.all(np.isfinite(raw)):
        raise ValueError("onsite energies must be finite")
    if np.iscomplexobj(raw):
        if np.max(np.abs(np.imag(raw)), initial=0.0) > 1e-14:
            raise ValueError("onsite energies must be real")
        raw = np.real(raw)
    return np.asarray(raw, dtype=float)


def hard_core_hamiltonian(
    model: HofstadterTorus,
    basis: FixedParticleBasis,
    theta_x: float,
    theta_y: float,
    *,
    onsite: np.ndarray | Sequence[float] | None = None,
) -> sparse.csr_matrix:
    """Build the fixed-occupation hard-core-boson Hamiltonian as CSR."""

    theta_x, theta_y = _require_finite_twists(theta_x, theta_y)
    _validate_basis(basis)
    if basis.n_sites != model.n_sites:
        raise ValueError(
            "basis site count does not match the Hofstadter lattice"
        )
    onsite_vector = _onsite_vector(onsite, model.n_sites)
    bonds = _positive_bonds(model, theta_x, theta_y)

    rows: list[int] = []
    columns: list[int] = []
    data: list[complex] = []
    for column, state in enumerate(basis.states):
        if onsite_vector is not None:
            diagonal = 0.0
            occupied = state
            while occupied:
                least_bit = occupied & -occupied
                diagonal += onsite_vector[least_bit.bit_length() - 1]
                occupied ^= least_bit
            rows.append(column)
            columns.append(column)
            data.append(complex(diagonal))

        for source, destination, phase in bonds:
            source_bit = 1 << source
            destination_bit = 1 << destination
            source_occupied = bool(state & source_bit)
            destination_occupied = bool(state & destination_bit)
            if source_occupied and not destination_occupied:
                moved = state ^ source_bit ^ destination_bit
                rows.append(basis.index[moved])
                columns.append(column)
                data.append(complex(-model.hopping * phase))
            elif destination_occupied and not source_occupied:
                moved = state ^ source_bit ^ destination_bit
                rows.append(basis.index[moved])
                columns.append(column)
                data.append(complex(-model.hopping * np.conjugate(phase)))

    dimension = len(basis.states)
    hamiltonian = sparse.coo_matrix(
        (
            np.asarray(data, dtype=np.complex128),
            (
                np.asarray(rows, dtype=np.int64),
                np.asarray(columns, dtype=np.int64),
            ),
        ),
        shape=(dimension, dimension),
        dtype=np.complex128,
    ).tocsr()
    hamiltonian.sum_duplicates()
    hamiltonian.sort_indices()
    return hamiltonian


def single_particle_hamiltonian(
    model: HofstadterTorus,
    theta_x: float,
    theta_y: float,
) -> np.ndarray:
    """Build the dense one-particle Hamiltonian in site-index order."""

    theta_x, theta_y = _require_finite_twists(theta_x, theta_y)
    hamiltonian = np.zeros(
        (model.n_sites, model.n_sites), dtype=np.complex128
    )
    for source, destination, phase in _positive_bonds(
        model, theta_x, theta_y
    ):
        coefficient = -model.hopping * phase
        hamiltonian[destination, source] += coefficient
        hamiltonian[source, destination] += np.conjugate(coefficient)
    return hamiltonian


def hermiticity_defect(
    matrix: sparse.spmatrix | np.ndarray,
) -> float:
    """Return ``max(abs(H-H^dagger))`` for a dense or sparse matrix."""

    if sparse.issparse(matrix):
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError("matrix must be square")
        difference = (matrix - matrix.getH()).tocsr()
        difference.eliminate_zeros()
        if difference.nnz == 0:
            return 0.0
        return float(np.max(np.abs(difference.data)))
    dense = np.asarray(matrix)
    if dense.ndim != 2 or dense.shape[0] != dense.shape[1]:
        raise ValueError("matrix must be square")
    if not np.all(np.isfinite(dense)):
        raise ValueError("matrix entries must be finite")
    return float(np.max(np.abs(dense - dense.conj().T), initial=0.0))


def _sparse_max_abs_difference(
    left: sparse.spmatrix,
    right: sparse.spmatrix,
) -> float:
    if left.shape != right.shape:
        raise ValueError("matrix shapes differ")
    difference = (left - right).tocsr()
    difference.eliminate_zeros()
    if difference.nnz == 0:
        return 0.0
    return float(np.max(np.abs(difference.data)))


def twist_periodicity_defects(
    model: HofstadterTorus,
    basis: FixedParticleBasis,
    theta_x: float,
    theta_y: float,
    *,
    onsite: np.ndarray | Sequence[float] | None = None,
) -> dict[str, float]:
    """Measure both ``2*pi`` boundary-twist periodicity defects."""

    theta_x, theta_y = _require_finite_twists(theta_x, theta_y)
    reference = hard_core_hamiltonian(
        model, basis, theta_x, theta_y, onsite=onsite
    )
    shifted_x = hard_core_hamiltonian(
        model, basis, theta_x + _TWO_PI, theta_y, onsite=onsite
    )
    shifted_y = hard_core_hamiltonian(
        model, basis, theta_x, theta_y + _TWO_PI, onsite=onsite
    )
    return {
        "theta_x": _sparse_max_abs_difference(reference, shifted_x),
        "theta_y": _sparse_max_abs_difference(reference, shifted_y),
    }


def plaquette_phases(
    model: HofstadterTorus,
    theta_x: float,
    theta_y: float,
) -> np.ndarray:
    """Return every positive-oriented plaquette phase on the torus."""

    theta_x, theta_y = _require_finite_twists(theta_x, theta_y)
    phases = np.empty((model.lx, model.ly), dtype=float)
    for x in range(model.lx):
        for y in range(model.ly):
            next_x = (x + 1) % model.lx
            next_y = (y + 1) % model.ly
            product = (
                positive_bond_phase(
                    model, x, y, "x", theta_x, theta_y
                )
                * positive_bond_phase(
                    model, next_x, y, "y", theta_x, theta_y
                )
                * np.conjugate(
                    positive_bond_phase(
                        model, x, next_y, "x", theta_x, theta_y
                    )
                )
                * np.conjugate(
                    positive_bond_phase(
                        model, x, y, "y", theta_x, theta_y
                    )
                )
            )
            phases[x, y] = float(np.angle(product))
    return phases


def maximum_plaquette_flux_defect(
    model: HofstadterTorus,
    theta_x: float,
    theta_y: float,
) -> float:
    """Return the largest principal-angle error from ``+2*pi*alpha``."""

    measured = plaquette_phases(model, theta_x, theta_y)
    target = _TWO_PI * model.alpha
    errors = np.angle(np.exp(1j * (measured - target)))
    return float(np.max(np.abs(errors), initial=0.0))


def deterministic_complex_v0(
    dimension: int,
    *,
    base_seed: int,
    mesh_shape: tuple[int, int],
    point: tuple[int, int],
    sector_code: int,
) -> np.ndarray:
    """Return the declared point-local deterministic complex ARPACK seed."""

    dimension = _require_plain_int(dimension, "dimension")
    base_seed = _require_plain_int(base_seed, "base_seed")
    sector_code = _require_plain_int(sector_code, "sector_code")
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    if base_seed < 0 or sector_code < 0:
        raise ValueError("seed components must be non-negative")
    if len(mesh_shape) != 2 or len(point) != 2:
        raise ValueError("mesh_shape and point must be two-tuples")
    nx = _require_plain_int(mesh_shape[0], "mesh Nx")
    ny = _require_plain_int(mesh_shape[1], "mesh Ny")
    i = _require_plain_int(point[0], "mesh i")
    j = _require_plain_int(point[1], "mesh j")
    if nx <= 0 or ny <= 0 or not 0 <= i < nx or not 0 <= j < ny:
        raise ValueError("mesh shape or point is invalid")
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [base_seed, nx, ny, i, j, sector_code]
        )
    )
    vector = rng.standard_normal(dimension) + 1j * rng.standard_normal(
        dimension
    )
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("deterministic seed unexpectedly produced zero")
    return np.asarray(vector / norm, dtype=np.complex128)


def lowest_eigensystem(
    hamiltonian: sparse.spmatrix,
    config: EigensolverConfig,
    *,
    v0: np.ndarray,
) -> Eigensystem:
    """Compute and deterministically repair the returned full Ritz span.

    Exactly one ARPACK call supplies ``config.k`` raw vectors.  The committed
    S9 correction then performs reduced QR on that *complete* span, checks its
    numerical rank, diagonalizes ``Q† H Q``, and recomputes every Ritz value,
    residual, and Gram diagnostic.  No retry or solver-parameter change occurs.
    """

    if not sparse.issparse(hamiltonian):
        raise ValueError("hamiltonian must be a SciPy sparse matrix")
    if (
        hamiltonian.ndim != 2
        or hamiltonian.shape[0] != hamiltonian.shape[1]
    ):
        raise ValueError("hamiltonian must be square")
    dimension = hamiltonian.shape[0]
    if config.k >= dimension:
        raise ValueError("eigsh requires k smaller than the matrix dimension")
    if config.ncv > dimension:
        raise ValueError("ncv cannot exceed the matrix dimension")
    vector = np.asarray(v0, dtype=np.complex128)
    if vector.shape != (dimension,):
        raise ValueError(f"v0 must have shape ({dimension},)")
    if not np.all(np.isfinite(vector)) or np.linalg.norm(vector) == 0.0:
        raise ValueError("v0 must be finite and nonzero")
    matrix = hamiltonian.astype(np.complex128).tocsr()
    if not np.all(np.isfinite(matrix.data)):
        raise ValueError("hamiltonian entries must be finite")

    try:
        eigenvalues, eigenvectors = eigsh(
            matrix,
            k=config.k,
            which=config.which,
            tol=config.tolerance,
            maxiter=config.max_iterations,
            ncv=config.ncv,
            v0=vector,
            return_eigenvectors=True,
        )
    except ArpackNoConvergence as error:
        partial = (
            0
            if error.eigenvalues is None
            else int(np.size(error.eigenvalues))
        )
        raise FQHEEigensolverError(
            "ARPACK did not converge to the required eigensystem",
            partial_eigenpairs=partial,
        ) from error

    raw_eigenvalues = np.asarray(eigenvalues, dtype=float)
    raw_eigenvectors = np.asarray(eigenvectors, dtype=np.complex128)
    if (
        raw_eigenvalues.shape != (config.k,)
        or raw_eigenvectors.shape != (dimension, config.k)
    ):
        raise FQHEEigensolverError(
            "eigensolver returned fewer eigenpairs than required",
            partial_eigenpairs=int(raw_eigenvalues.size),
            failure_kind="MISSING_EIGENPAIRS",
        )
    if not np.all(np.isfinite(raw_eigenvalues)) or not np.all(
        np.isfinite(raw_eigenvectors)
    ):
        raise FQHEEigensolverError(
            "eigensolver returned non-finite values",
            partial_eigenpairs=config.k,
            failure_kind="NONFINITE_RITZ_OUTPUT",
        )

    # The SVD is used only to evaluate numerical rank and to obtain an
    # independent orthonormal basis for the principal-angle diagnostic.  The
    # repaired frame itself is the deterministic reduced QR frame required by
    # the correction manifest.
    try:
        raw_left_singular, raw_singular_values, _ = np.linalg.svd(
            raw_eigenvectors,
            full_matrices=False,
        )
        numerical_rank = int(np.linalg.matrix_rank(raw_eigenvectors))
        q, _ = np.linalg.qr(raw_eigenvectors, mode="reduced")
    except np.linalg.LinAlgError as error:
        raise FQHEEigensolverError(
            "Ritz-span factorization failed",
            partial_eigenpairs=config.k,
            failure_kind="RITZ_SPAN_FACTORIZATION",
        ) from error
    if numerical_rank != config.k:
        raise FQHEEigensolverError(
            "returned Ritz span lost numerical rank: "
            f"expected {config.k}, measured {numerical_rank}",
            partial_eigenpairs=config.k,
            failure_kind="RITZ_SPAN_RANK_LOSS",
        )
    if (
        raw_singular_values.shape != (config.k,)
        or q.shape != (dimension, config.k)
        or not np.all(np.isfinite(raw_singular_values))
        or not np.all(np.isfinite(q))
    ):
        raise FQHEEigensolverError(
            "Ritz-span factorization returned non-finite output",
            partial_eigenpairs=config.k,
            failure_kind="NONFINITE_RITZ_SPAN",
        )

    raw_span_basis = raw_left_singular[:, : config.k]
    span_residual = q - raw_span_basis @ (
        raw_span_basis.conj().T @ q
    )
    span_preservation_sine = float(np.linalg.norm(span_residual, ord=2))
    span_roundoff_limit = (
        128.0
        * float(np.finfo(np.float64).eps)
        * max(raw_eigenvectors.shape)
    )
    if (
        not math.isfinite(span_preservation_sine)
        or span_preservation_sine > span_roundoff_limit
    ):
        raise FQHEEigensolverError(
            "QR did not preserve the returned Ritz span within numerical "
            f"roundoff: sine={span_preservation_sine:.3e}, "
            f"limit={span_roundoff_limit:.3e}",
            partial_eigenpairs=config.k,
            failure_kind="RITZ_SPAN_NOT_PRESERVED",
        )

    projected = q.conj().T @ (matrix @ q)
    projected = 0.5 * (projected + projected.conj().T)
    if not np.all(np.isfinite(projected)):
        raise FQHEEigensolverError(
            "projected Ritz Hamiltonian is non-finite",
            partial_eigenpairs=config.k,
            failure_kind="NONFINITE_PROJECTED_HAMILTONIAN",
        )
    try:
        eigenvalues, rotations = np.linalg.eigh(projected)
    except np.linalg.LinAlgError as error:
        raise FQHEEigensolverError(
            "Rayleigh--Ritz diagonalization failed",
            partial_eigenpairs=config.k,
            failure_kind="RAYLEIGH_RITZ_DIAGONALIZATION",
        ) from error
    eigenvalues = np.asarray(eigenvalues, dtype=float)
    eigenvectors = np.asarray(q @ rotations, dtype=np.complex128)
    if not np.all(np.isfinite(eigenvalues)) or not np.all(
        np.isfinite(eigenvectors)
    ):
        raise FQHEEigensolverError(
            "Rayleigh--Ritz repair returned non-finite output",
            partial_eigenpairs=config.k,
            failure_kind="NONFINITE_RAYLEIGH_RITZ_OUTPUT",
        )
    order = np.argsort(eigenvalues, kind="stable")
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    residual_norms = np.asarray(
        [
            np.linalg.norm(
                matrix @ eigenvectors[:, position]
                - eigenvalues[position] * eigenvectors[:, position]
            )
            for position in range(config.k)
        ],
        dtype=float,
    )
    gram = eigenvectors.conj().T @ eigenvectors
    orthonormality_defect = float(
        np.max(np.abs(gram - np.eye(config.k)), initial=0.0)
    )
    return Eigensystem(
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        residual_norms=residual_norms,
        orthonormality_defect=orthonormality_defect,
        span_preservation_sine=span_preservation_sine,
    )


def bundle_spectral_report(eigenvalues: np.ndarray) -> dict:
    """Compute the preregistered rank-two width and isolation metrics."""

    values = np.asarray(eigenvalues, dtype=float)
    if values.ndim < 1 or values.shape[-1] < 3:
        raise ValueError("eigenvalues must contain at least three levels")
    if not np.all(np.isfinite(values)):
        raise ValueError("eigenvalues must be finite")
    if np.any(np.diff(values, axis=-1) < -1e-12):
        raise ValueError("eigenvalues must be sorted ascending at each point")
    internal = values[..., 1] - values[..., 0]
    width = float(np.max(values[..., 1]) - np.min(values[..., 0]))
    gap = float(np.min(values[..., 2] - values[..., 1]))
    ratio = float(width / gap) if gap > 0.0 else None
    return {
        "internal_splittings": np.asarray(internal, dtype=float),
        "maximum_internal_splitting": float(np.max(internal)),
        "global_bundle_width": width,
        "isolation_gap": gap,
        "isolation_ratio": ratio,
    }


def _validate_frame_pair(
    frame_left: np.ndarray,
    frame_right: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(frame_left, dtype=np.complex128)
    right = np.asarray(frame_right, dtype=np.complex128)
    if left.ndim != 2 or right.ndim != 2 or left.shape != right.shape:
        raise ValueError("neighbor frames must be equal-shape matrices")
    if left.shape[0] < left.shape[1] or left.shape[1] <= 0:
        raise ValueError("frame rank must be positive and no larger than ambient")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("frame entries must be finite")
    return left, right


def determinant_polar_link(
    frame_left: np.ndarray,
    frame_right: np.ndarray,
    *,
    singularity_atol: float = 1e-14,
) -> PolarLink:
    """Compute one gauge-covariant determinant link from neighboring frames."""

    singularity_atol = float(singularity_atol)
    if not math.isfinite(singularity_atol) or singularity_atol < 0.0:
        raise ValueError("singularity_atol must be finite and non-negative")
    left, right = _validate_frame_pair(frame_left, frame_right)
    overlap = left.conj().T @ right
    u, singular_values, vh = np.linalg.svd(overlap, full_matrices=False)
    if singular_values.size == 0 or float(np.min(singular_values)) <= singularity_atol:
        raise ValueError("neighbor overlap is numerically singular")
    unitary_polar = u @ vh
    determinant = complex(np.linalg.det(unitary_polar))
    magnitude = abs(determinant)
    if not math.isfinite(magnitude) or magnitude <= singularity_atol:
        raise ValueError("polar determinant cannot be normalized")
    return PolarLink(
        value=determinant / magnitude,
        singular_values=np.asarray(singular_values, dtype=float),
    )


def fhs_chern(
    frames: np.ndarray,
    *,
    singularity_atol: float = 1e-14,
) -> ChernReport:
    """Evaluate the determinant-link FHS Chern number on a periodic mesh."""

    frames = np.asarray(frames, dtype=np.complex128)
    if frames.ndim != 4:
        raise ValueError("frames must have shape (Nx, Ny, ambient, rank)")
    nx, ny, ambient, rank = frames.shape
    if nx < 2 or ny < 2:
        raise ValueError("the twist mesh must be at least 2x2")
    if rank <= 0 or ambient < rank:
        raise ValueError("frame dimensions are invalid")
    if not np.all(np.isfinite(frames)):
        raise ValueError("frame entries must be finite")

    links_x = np.empty((nx, ny), dtype=np.complex128)
    links_y = np.empty((nx, ny), dtype=np.complex128)
    minimum_singular = math.inf
    for i in range(nx):
        for j in range(ny):
            link_x = determinant_polar_link(
                frames[i, j],
                frames[(i + 1) % nx, j],
                singularity_atol=singularity_atol,
            )
            link_y = determinant_polar_link(
                frames[i, j],
                frames[i, (j + 1) % ny],
                singularity_atol=singularity_atol,
            )
            links_x[i, j] = link_x.value
            links_y[i, j] = link_y.value
            minimum_singular = min(
                minimum_singular,
                float(np.min(link_x.singular_values)),
                float(np.min(link_y.singular_values)),
            )

    field = np.empty((nx, ny), dtype=float)
    for i in range(nx):
        for j in range(ny):
            plaquette = (
                links_x[i, j]
                * links_y[(i + 1) % nx, j]
                * np.conjugate(links_x[i, (j + 1) % ny])
                * np.conjugate(links_y[i, j])
            )
            field[i, j] = float(np.angle(plaquette))
    chern = float(np.sum(field, dtype=float) / _TWO_PI)
    rounded = int(np.rint(chern))
    return ChernReport(
        chern=chern,
        rounded_chern=rounded,
        integer_residual=abs(chern - rounded),
        links_x=links_x,
        links_y=links_y,
        plaquette_phases=field,
        minimum_overlap_singular_value=float(minimum_singular),
        maximum_absolute_plaquette_phase=float(
            np.max(np.abs(field), initial=0.0)
        ),
    )


def haar_unitary(
    rank: int,
    seed_components: tuple[int, ...],
) -> np.ndarray:
    """Draw one deterministic Haar unitary from explicit seed components."""

    rank = _require_plain_int(rank, "rank")
    if rank <= 0:
        raise ValueError("rank must be positive")
    if not seed_components:
        raise ValueError("seed_components cannot be empty")
    normalized_seed = tuple(
        _require_plain_int(component, "seed component")
        for component in seed_components
    )
    if any(component < 0 for component in normalized_seed):
        raise ValueError("seed components must be non-negative")
    rng = np.random.default_rng(np.random.SeedSequence(normalized_seed))
    z = rng.standard_normal((rank, rank)) + 1j * rng.standard_normal(
        (rank, rank)
    )
    q, r = np.linalg.qr(z)
    diagonal = np.diag(r)
    magnitudes = np.abs(diagonal)
    if np.any(magnitudes == 0.0):
        raise ValueError("QR draw was unexpectedly rank deficient")
    phase = diagonal / magnitudes
    return np.asarray(q * phase[np.newaxis, :], dtype=np.complex128)


def scramble_bundle_frames(
    frames: np.ndarray,
    *,
    base_seed: int,
    replicate: int,
    sector_code: int,
) -> np.ndarray:
    """Apply the preregistered independent local ``U(q)`` frame field."""

    frames = np.asarray(frames, dtype=np.complex128)
    if frames.ndim != 4:
        raise ValueError("frames must have shape (Nx, Ny, ambient, rank)")
    nx, ny, ambient, rank = frames.shape
    if nx <= 0 or ny <= 0 or rank <= 0 or ambient < rank:
        raise ValueError("frame dimensions are invalid")
    if not np.all(np.isfinite(frames)):
        raise ValueError("frame entries must be finite")
    base_seed = _require_plain_int(base_seed, "base_seed")
    replicate = _require_plain_int(replicate, "replicate")
    sector_code = _require_plain_int(sector_code, "sector_code")
    if min(base_seed, replicate, sector_code) < 0:
        raise ValueError("scramble seed components must be non-negative")

    scrambled = np.empty_like(frames)
    for i in range(nx):
        for j in range(ny):
            local = haar_unitary(
                rank,
                (
                    base_seed,
                    nx,
                    ny,
                    replicate,
                    i,
                    j,
                    sector_code,
                ),
            )
            scrambled[i, j] = frames[i, j] @ local
    return scrambled
