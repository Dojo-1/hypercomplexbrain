"""Fast operator tests for the preregistered S9 FQHE instrument.

The expensive 6x4, three-boson, 7x7/9x9 target is intentionally absent here.
These tests exercise the construction and gauge instrument on smaller or
analytic controls.
"""

from __future__ import annotations

import itertools
import json
import math

import numpy as np
import pytest
from scipy import sparse
from scipy.sparse.linalg import ArpackNoConvergence

import aionq.fqhe as fqhe_module
import run_fqhe_probe as fqhe_runner
from aionq.fqhe import (
    EigensolverConfig,
    FQHEEigensolverError,
    HofstadterTorus,
    bundle_spectral_report,
    determinant_polar_link,
    deterministic_complex_v0,
    fhs_chern,
    fixed_particle_basis,
    haar_unitary,
    hard_core_hamiltonian,
    hermiticity_defect,
    maximum_plaquette_flux_defect,
    plaquette_phases,
    scramble_bundle_frames,
    single_particle_hamiltonian,
    twist_periodicity_defects,
)


def _qiwuzhang_rank_two_frames(mesh: int = 11) -> np.ndarray:
    """Lower QWZ band plus one constant trivial line."""

    sigma_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    sigma_y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)
    sigma_z = np.diag([1.0, -1.0]).astype(complex)
    frames = np.empty((mesh, mesh, 3, 2), dtype=complex)
    mass = -1.0
    for i in range(mesh):
        kx = 2.0 * np.pi * i / mesh
        for j in range(mesh):
            ky = 2.0 * np.pi * j / mesh
            hamiltonian = (
                np.sin(kx) * sigma_x
                + np.sin(ky) * sigma_y
                + (mass + np.cos(kx) + np.cos(ky)) * sigma_z
            )
            _, vectors = np.linalg.eigh(hamiltonian)
            frames[i, j, :, 0] = np.array(
                [vectors[0, 0], vectors[1, 0], 0.0]
            )
            frames[i, j, :, 1] = np.array([0.0, 0.0, 1.0])
    return frames


def test_fixed_particle_basis_preserves_exact_combination_order():
    basis = fixed_particle_basis(24, 3)
    expected = tuple(
        sum(1 << site for site in occupied)
        for occupied in itertools.combinations(range(24), 3)
    )

    assert len(basis.states) == math.comb(24, 3) == 2024
    assert basis.states == expected
    assert basis.states != tuple(sorted(basis.states))
    assert len(set(basis.states)) == len(basis.states)
    assert all(state.bit_count() == 3 for state in basis.states)
    assert all(basis.index[state] == i for i, state in enumerate(basis.states))


def test_hard_core_hamiltonian_is_hermitian_and_twist_periodic():
    model = HofstadterTorus(lx=4, ly=4)
    basis = fixed_particle_basis(model.n_sites, 2)
    theta_x, theta_y = 0.37, -0.29
    hamiltonian = hard_core_hamiltonian(
        model, basis, theta_x, theta_y
    )
    defects = twist_periodicity_defects(
        model, basis, theta_x, theta_y
    )

    assert hamiltonian.format == "csr"
    assert hamiltonian.dtype == np.complex128
    assert hermiticity_defect(hamiltonian) <= 1e-14
    assert defects["theta_x"] <= 1e-12
    assert defects["theta_y"] <= 1e-12


def test_every_interior_and_seam_plaquette_has_declared_flux():
    model = HofstadterTorus(lx=4, ly=4)
    phases = plaquette_phases(model, theta_x=0.41, theta_y=-0.73)

    assert phases.shape == (4, 4)
    assert np.allclose(phases, np.pi / 2.0, atol=1e-12)
    assert (
        maximum_plaquette_flux_defect(model, 0.41, -0.73) <= 1e-12
    )


@pytest.mark.parametrize(
    ("theta_x", "theta_y"),
    [(0.0, 0.0), (2.0 * np.pi / 7.0, 4.0 * np.pi / 7.0)],
)
def test_one_particle_hard_core_matrix_equals_dense_site_matrix(
    theta_x,
    theta_y,
):
    model = HofstadterTorus(lx=4, ly=4)
    basis = fixed_particle_basis(model.n_sites, 1)
    many_body = hard_core_hamiltonian(
        model, basis, theta_x, theta_y
    ).toarray()
    single_particle = single_particle_hamiltonian(
        model, theta_x, theta_y
    )

    assert basis.states == tuple(1 << site for site in range(model.n_sites))
    assert np.allclose(many_body, single_particle, atol=1e-14)
    assert np.allclose(
        np.linalg.eigvalsh(many_body),
        np.linalg.eigvalsh(single_particle),
        atol=1e-13,
    )


def test_atomic_product_frame_is_twist_independent_and_zero_chern():
    model = HofstadterTorus(lx=4, ly=4, hopping=0.0)
    basis = fixed_particle_basis(model.n_sites, 3)
    onsite = np.arange(model.n_sites, dtype=float) / model.n_sites
    first = hard_core_hamiltonian(
        model, basis, 0.0, 0.0, onsite=onsite
    )
    second = hard_core_hamiltonian(
        model, basis, 0.81, -1.17, onsite=onsite
    )
    ground_index = int(np.argmin(first.diagonal().real))
    frame = np.zeros((len(basis.states), 1), dtype=complex)
    frame[ground_index, 0] = 1.0
    frames = np.tile(frame, (4, 4, 1, 1))
    report = fhs_chern(frames)

    assert np.array_equal(first.toarray(), second.toarray())
    assert report.chern == 0.0
    assert report.rounded_chern == 0
    assert report.minimum_overlap_singular_value == 1.0


def test_deterministic_v0_is_point_and_sector_local():
    arguments = {
        "dimension": 17,
        "base_seed": 2026072801,
        "mesh_shape": (7, 7),
        "point": (2, 3),
        "sector_code": 3,
    }
    first = deterministic_complex_v0(**arguments)
    repeated = deterministic_complex_v0(**arguments)
    other_point = deterministic_complex_v0(
        **{**arguments, "point": (2, 4)}
    )
    other_sector = deterministic_complex_v0(
        **{**arguments, "sector_code": 1}
    )

    assert np.array_equal(first, repeated)
    assert np.isclose(np.linalg.norm(first), 1.0, atol=1e-15)
    assert not np.array_equal(first, other_point)
    assert not np.array_equal(first, other_sector)


def test_sparse_eigensystem_reports_residuals_and_orthonormality():
    matrix = sparse.diags(
        [4.0, -1.0, 2.0, 0.5, 3.0],
        format="csr",
        dtype=np.complex128,
    )
    config = EigensolverConfig(k=2, ncv=4)
    result = fqhe_module.lowest_eigensystem(
        matrix,
        config,
        v0=deterministic_complex_v0(
            5,
            base_seed=7,
            mesh_shape=(2, 2),
            point=(0, 1),
            sector_code=1,
        ),
    )

    assert np.allclose(result.eigenvalues, [-1.0, 0.5], atol=1e-12)
    assert np.max(result.residual_norms) <= 1e-11
    assert result.orthonormality_defect <= 1e-12


def test_nearly_degenerate_eigenspace_is_compared_by_projector():
    matrix = sparse.diags(
        [0.0, 1e-5, 2.0, 3.0, 4.0],
        format="csr",
        dtype=np.complex128,
    )
    config = EigensolverConfig(k=2, ncv=4)
    left = fqhe_module.lowest_eigensystem(
        matrix,
        config,
        v0=deterministic_complex_v0(
            5,
            base_seed=11,
            mesh_shape=(2, 2),
            point=(0, 0),
            sector_code=2,
        ),
    )
    right = fqhe_module.lowest_eigensystem(
        matrix,
        config,
        v0=deterministic_complex_v0(
            5,
            base_seed=13,
            mesh_shape=(2, 2),
            point=(1, 0),
            sector_code=2,
        ),
    )

    projector_left = left.eigenvectors @ left.eigenvectors.conj().T
    projector_right = right.eigenvectors @ right.eigenvectors.conj().T
    assert np.allclose(projector_left, projector_right, atol=1e-11)


def test_bundle_spectral_report_uses_global_width_and_minimum_gap():
    levels = np.array(
        [
            [[0.0, 0.1, 2.0], [0.2, 0.3, 1.8]],
            [[-0.1, 0.0, 1.9], [0.1, 0.4, 1.7]],
        ]
    )
    report = bundle_spectral_report(levels)

    assert np.allclose(
        report["internal_splittings"],
        [[0.1, 0.1], [0.1, 0.3]],
    )
    assert np.isclose(report["global_bundle_width"], 0.5)
    assert np.isclose(report["isolation_gap"], 1.3)
    assert np.isclose(report["isolation_ratio"], 0.5 / 1.3)


def test_polar_link_matches_known_unitary_and_endpoint_covariance():
    frame = np.eye(4, 2, dtype=complex)
    left_gauge = haar_unitary(2, (2, 3, 5))
    right_gauge = haar_unitary(2, (7, 11, 13))
    direct = determinant_polar_link(frame, frame @ right_gauge)
    transformed = determinant_polar_link(
        frame @ left_gauge,
        frame @ right_gauge,
    )
    expected = (
        np.conjugate(np.linalg.det(left_gauge))
        * np.linalg.det(right_gauge)
    )

    assert np.isclose(abs(direct.value), 1.0, atol=1e-14)
    assert np.allclose(direct.value, np.linalg.det(right_gauge), atol=1e-13)
    assert np.allclose(transformed.value, expected, atol=1e-13)


def test_rank_two_topological_bundle_and_all_scrambles_preserve_chern():
    frames = _qiwuzhang_rank_two_frames()
    reference = fhs_chern(frames)

    assert abs(reference.rounded_chern) == 1
    assert reference.integer_residual <= 1e-12
    assert reference.minimum_overlap_singular_value > 0.5
    for replicate in range(32):
        scrambled = scramble_bundle_frames(
            frames,
            base_seed=2026072802,
            replicate=replicate,
            sector_code=2,
        )
        report = fhs_chern(scrambled)
        assert np.isclose(report.chern, reference.chern, atol=1e-12)
        assert (
            report.minimum_overlap_singular_value
            == pytest.approx(
                reference.minimum_overlap_singular_value, abs=1e-12
            )
        )


def test_singular_neighbor_overlap_is_rejected_before_normalization():
    left = np.array([[1.0], [0.0]], dtype=complex)
    right = np.array([[0.0], [1.0]], dtype=complex)

    with pytest.raises(ValueError, match="numerically singular"):
        determinant_polar_link(left, right)


def test_arpack_nonconvergence_is_typed_and_not_retried(monkeypatch):
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise ArpackNoConvergence(
            "declared failure",
            eigenvalues=np.array([0.0]),
            eigenvectors=np.ones((5, 1), dtype=complex),
        )

    monkeypatch.setattr(fqhe_module, "eigsh", fail_once)
    matrix = sparse.eye(5, format="csr", dtype=np.complex128)
    config = EigensolverConfig(k=2, ncv=4)

    with pytest.raises(FQHEEigensolverError) as captured:
        fqhe_module.lowest_eigensystem(
            matrix,
            config,
            v0=np.ones(5, dtype=complex),
        )
    assert calls == 1
    assert captured.value.partial_eigenpairs == 1


def test_preregistration_blob_is_frozen_before_the_runner():
    manifest, digest = fqhe_runner._load_preregistration(
        fqhe_runner.PREREGISTRATION
    )

    assert manifest["committed_before_any_fqhe_control_or_target_run"]
    assert manifest["formal_model"]["lattice"]["Lx"] == 6
    assert manifest["formal_model"]["particles"]["hilbert_dimension"] == 2024
    assert digest.startswith("sha256:")


def test_preregistered_control_stack_passes_without_running_target():
    guard = fqhe_runner.BudgetGuard()
    model = HofstadterTorus()
    basis = fixed_particle_basis(model.n_sites, 3)

    static = fqhe_runner._static_controls(model, basis, guard)
    atomic = fqhe_runner._atomic_control(model, basis, guard)
    one_particle = fqhe_runner._one_particle_control(model, guard)
    integer_hall = fqhe_runner._integer_hall_control(model, guard)

    assert static["pass"], static
    assert atomic["pass"], atomic
    assert one_particle["pass"], one_particle
    assert integer_hall["pass"], integer_hall
    assert abs(integer_hall["orientation"]) == 1


def test_runner_json_is_canonical_utf8_with_no_nan(tmp_path):
    target = tmp_path / "artifact.json"
    fqhe_runner._write_json(target, {"z": 2, "a": [1.0]})
    raw = target.read_bytes()

    assert raw.endswith(b"\n")
    assert raw.index(b'"a"') < raw.index(b'"z"')
    assert json.loads(raw.decode("utf-8")) == {"a": [1.0], "z": 2}
    with pytest.raises(ValueError):
        fqhe_runner._write_json(target, {"invalid": float("nan")})
