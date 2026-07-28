"""Run the corrected preregistered S9 finite-size fractional-Hall probe.

The immutable experiment specification is
``manifests/s9_fqhe_preregistration.json``, committed at ``91777d9`` before
this numerical instrument existed. The committed correction amendment is
``manifests/s9_fqhe_instrument_correction.json``. It preserves the first
artifact and authorizes one rerun with deterministic full-span
QR/Rayleigh--Ritz repair and tri-state result reporting. Execution is
fail-closed:

1. construction, atomic, one-particle, and integer-Hall controls;
2. the 7x7 many-body twist mesh;
3. the 9x9 confirmation mesh only if the coarse instrument remains valid;
4. 32 local U(2) frame attacks on every completed target mesh.

A passing run is a finite-size numerical signature at one fixed parameter
point.  It is not a thermodynamic phase proof or a transport measurement.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.evidence import (  # noqa: E402
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
)
from aionq.fqhe import (  # noqa: E402
    ChernReport,
    EigensolverConfig,
    FQHEEigensolverError,
    FQHEResourceLimit,
    HofstadterTorus,
    bundle_spectral_report,
    deterministic_complex_v0,
    fhs_chern,
    fixed_particle_basis,
    hard_core_hamiltonian,
    hermiticity_defect,
    lowest_eigensystem,
    maximum_plaquette_flux_defect,
    scramble_bundle_frames,
    single_particle_hamiltonian,
    twist_periodicity_defects,
)


PREREGISTRATION = ROOT / "manifests" / "s9_fqhe_preregistration.json"
PREREGISTRATION_COMMIT = "91777d9"
CORRECTION = ROOT / "manifests" / "s9_fqhe_instrument_correction.json"
CORRECTION_COMMIT = "6d12fd3702d474ed7351eb54b4791555d5399cd2"
OUT_DIR = ROOT / "artifacts" / "s9_fqhe"
INITIAL_OUT_FILE = OUT_DIR / "fqhe_probe.json"
INITIAL_ENVELOPE_FILE = OUT_DIR / "fqhe_probe.envelope.json"
OUT_FILE = OUT_DIR / "fqhe_probe.corrected.json"
ENVELOPE_FILE = OUT_DIR / "fqhe_probe.corrected.envelope.json"

EIGENSOLVER_SEED = 2026072801
GAUGE_SCRAMBLE_SEED = 2026072802
GAUGE_SCRAMBLES = 32

HERMITICITY_LIMIT = 1e-12
PERIODICITY_LIMIT = 1e-12
FLUX_LIMIT = 1e-12
RESIDUAL_LIMIT = 1e-9
ORTHONORMALITY_LIMIT = 1e-10
ISOLATION_FLOOR = 1e-6
ISOLATION_RESIDUAL_FACTOR = 100.0
OVERLAP_FLOOR = 1e-6
BRANCH_MARGIN = 1e-3
INTEGRALITY_LIMIT = 1e-8
MESH_AGREEMENT_LIMIT = 1e-8
GAUGE_VARIANCE_LIMIT = 1e-8
ATOMIC_CHERN_LIMIT = 1e-10
ONE_PARTICLE_LIMIT = 1e-11
IQH_GAP_FLOOR = 1e-8


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _git_blob_at(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"cannot read preregistration blob at {commit}:{relative_path}"
        )
    return result.stdout


def _load_preregistration(path: Path) -> tuple[dict, str]:
    if path.resolve() != PREREGISTRATION.resolve():
        raise ValueError("S9 may run only from its committed preregistration")
    current_bytes = path.read_bytes()
    frozen_bytes = _git_blob_at(
        PREREGISTRATION_COMMIT,
        "manifests/s9_fqhe_preregistration.json",
    )
    normalized_current = current_bytes.replace(b"\r\n", b"\n")
    normalized_frozen = frozen_bytes.replace(b"\r\n", b"\n")
    if normalized_current != normalized_frozen:
        raise ValueError(
            "the S9 preregistration differs from its pre-experiment commit"
        )
    manifest = json.loads(current_bytes.decode("utf-8"))
    lattice = manifest["formal_model"]["lattice"]
    particles = manifest["formal_model"]["particles"]
    if (
        lattice["Lx"],
        lattice["Ly"],
        lattice["magnetic_flux_per_plaquette"],
        particles["particle_number"],
        particles["hilbert_dimension"],
    ) != (6, 4, "alpha = 1/4", 3, 2024):
        raise ValueError("the S9 target no longer matches the frozen model")
    if manifest["randomness"]["eigensolver_seed"] != EIGENSOLVER_SEED:
        raise ValueError("the eigensolver seed differs from preregistration")
    if manifest["randomness"]["gauge_scramble_seed"] != GAUGE_SCRAMBLE_SEED:
        raise ValueError("the gauge-scramble seed differs from preregistration")
    if manifest["randomness"]["gauge_scrambles"] != GAUGE_SCRAMBLES:
        raise ValueError("the gauge-scramble count differs from preregistration")
    meshes = [
        (entry["Nx"], entry["Ny"])
        for entry in manifest["formal_model"]["twist_meshes"]
    ]
    if meshes != [(7, 7), (9, 9)]:
        raise ValueError("the twist meshes differ from preregistration")
    return manifest, _sha256_bytes(normalized_frozen)


def _load_correction(path: Path) -> tuple[dict, str]:
    if path.resolve() != CORRECTION.resolve():
        raise ValueError(
            "S9 corrected execution may use only its committed amendment"
        )
    current_bytes = path.read_bytes()
    frozen_bytes = _git_blob_at(
        CORRECTION_COMMIT,
        "manifests/s9_fqhe_instrument_correction.json",
    )
    normalized_current = current_bytes.replace(b"\r\n", b"\n")
    normalized_frozen = frozen_bytes.replace(b"\r\n", b"\n")
    if normalized_current != normalized_frozen:
        raise ValueError(
            "the S9 instrument correction differs from its committed amendment"
        )
    correction = json.loads(current_bytes.decode("utf-8"))
    prior = correction["prior_record"]
    if file_digest(INITIAL_OUT_FILE) != prior["initial_artifact_digest"]:
        raise ValueError("the preserved initial S9 artifact digest changed")
    if not INITIAL_ENVELOPE_FILE.is_file():
        raise ValueError("the preserved initial S9 envelope is missing")
    if correction["corrected_execution_and_ledger"]["rerun_count"] != 1:
        raise ValueError("the correction amendment must authorize one rerun")
    expected = correction["versioned_outputs"]
    if (
        expected["artifact"],
        expected["envelope"],
    ) != (
        "artifacts/s9_fqhe/fqhe_probe.corrected.json",
        "artifacts/s9_fqhe/fqhe_probe.corrected.envelope.json",
    ):
        raise ValueError("the corrected S9 output paths changed")
    return correction, _sha256_bytes(normalized_frozen)


class _ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def _resident_bytes() -> int | None:
    if os.name == "nt":
        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = ctypes.c_void_p
        get_process_memory_info = psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCountersEx),
            ctypes.c_ulong,
        ]
        get_process_memory_info.restype = ctypes.c_int
        handle = get_current_process()
        ok = get_process_memory_info(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        return int(counters.WorkingSetSize) if ok else None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):
        return None
    multiplier = 1 if sys.platform == "darwin" else 1024
    return int(usage * multiplier)


@dataclass
class BudgetGuard:
    max_seconds: float = 30.0 * 60.0
    max_resident_bytes: int = 2 * 1024**3

    def __post_init__(self) -> None:
        self.started = time.monotonic()
        initial = _resident_bytes()
        if initial is None:
            raise FQHEResourceLimit(
                "resident-memory monitoring is unavailable"
            )
        self.peak_resident_bytes = initial

    def check(self, stage: str) -> None:
        elapsed = time.monotonic() - self.started
        resident = _resident_bytes()
        if resident is None:
            raise FQHEResourceLimit(
                f"resident-memory monitoring failed at {stage}"
            )
        self.peak_resident_bytes = max(self.peak_resident_bytes, resident)
        if elapsed > self.max_seconds:
            raise FQHEResourceLimit(
                f"elapsed-time budget exceeded at {stage}"
            )
        if resident > self.max_resident_bytes:
            raise FQHEResourceLimit(
                f"resident-memory budget exceeded at {stage}"
            )

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started


def _budget_payload(
    guard: BudgetGuard,
    *,
    status: str = "WITHIN_LIMITS",
) -> dict:
    return {
        "status": status,
        "configured_maximum_elapsed_seconds": guard.max_seconds,
        "configured_maximum_resident_bytes": guard.max_resident_bytes,
        "observed_elapsed_seconds": guard.elapsed_seconds,
        "observed_peak_resident_bytes": guard.peak_resident_bytes,
    }


def _finite(value: float) -> float | None:
    value = float(value)
    return value if math.isfinite(value) else None


def _chern_payload(report: ChernReport) -> dict:
    return {
        "chern": float(report.chern),
        "rounded_chern": int(report.rounded_chern),
        "integer_residual": float(report.integer_residual),
        "minimum_overlap_singular_value": float(
            report.minimum_overlap_singular_value
        ),
        "maximum_absolute_plaquette_phase": float(
            report.maximum_absolute_plaquette_phase
        ),
        "plaquette_phases": np.asarray(
            report.plaquette_phases, dtype=float
        ).tolist(),
    }


def _environment_provenance() -> dict:
    blas = {}
    config = getattr(np.__config__, "CONFIG", {})
    if isinstance(config, dict):
        dependency = config.get("Build Dependencies", {}).get("blas", {})
        if isinstance(dependency, dict):
            blas = {
                key: dependency.get(key)
                for key in ("name", "version")
                if dependency.get(key)
            }
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "blas": blas,
        "thread_environment": {
            key: os.environ.get(key)
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
            )
        },
    }


def _static_controls(
    model: HofstadterTorus,
    basis,
    guard: BudgetGuard,
) -> dict:
    guard.check("static-control:start")
    combinations = tuple(
        sum(1 << site for site in occupied)
        for occupied in itertools.combinations(range(model.n_sites), 3)
    )
    exact_basis = (
        len(basis.states) == 2024
        and basis.states == combinations
        and len(set(basis.states)) == 2024
        and all(state.bit_count() == 3 for state in basis.states)
    )
    theta_x, theta_y = 0.371, -0.913
    hamiltonian = hard_core_hamiltonian(
        model, basis, theta_x, theta_y
    )
    periodicity = twist_periodicity_defects(
        model, basis, theta_x, theta_y
    )
    result = {
        "basis_dimension": len(basis.states),
        "basis_exact_combination_order": bool(exact_basis),
        "hermiticity_defect": hermiticity_defect(hamiltonian),
        "twist_periodicity_defects": periodicity,
        "maximum_plaquette_flux_defect": (
            maximum_plaquette_flux_defect(
                model, theta_x, theta_y
            )
        ),
    }
    result["gates"] = {
        "S9-G1": result["hermiticity_defect"] <= HERMITICITY_LIMIT,
        "S9-G2": max(periodicity.values()) <= PERIODICITY_LIMIT,
        "S9-G3": (
            result["maximum_plaquette_flux_defect"] <= FLUX_LIMIT
        ),
        "S9-G4": bool(exact_basis),
    }
    result["pass"] = all(result["gates"].values())
    guard.check("static-control:end")
    return result


def _constant_atomic_frames(
    dimension: int,
    ground_index: int,
    nx: int,
    ny: int,
) -> np.ndarray:
    frames = np.zeros((nx, ny, dimension, 1), dtype=np.complex128)
    frames[:, :, ground_index, 0] = 1.0
    return frames


def _atomic_control(
    model: HofstadterTorus,
    basis,
    guard: BudgetGuard,
) -> dict:
    atomic_model = replace(model, hopping=0.0)
    onsite = np.arange(model.n_sites, dtype=float) / model.n_sites
    h0 = hard_core_hamiltonian(
        atomic_model, basis, 0.0, 0.0, onsite=onsite
    )
    h1 = hard_core_hamiltonian(
        atomic_model, basis, 0.83, -1.17, onsite=onsite
    )
    twist_defect = float(
        np.max(np.abs((h0 - h1).data), initial=0.0)
        if (h0 - h1).nnz
        else 0.0
    )
    diagonal = np.asarray(h0.diagonal().real, dtype=float)
    order = np.argsort(diagonal, kind="stable")
    ground_index = int(order[0])
    unique_gap = float(diagonal[order[1]] - diagonal[order[0]])
    meshes = {}
    for nx, ny in ((7, 7), (9, 9)):
        guard.check(f"atomic:{nx}x{ny}")
        frames = _constant_atomic_frames(
            len(basis.states), ground_index, nx, ny
        )
        meshes[f"{nx}x{ny}"] = _chern_payload(fhs_chern(frames))
    passed = (
        twist_defect <= PERIODICITY_LIMIT
        and unique_gap > 0.0
        and all(
            abs(mesh["chern"]) <= ATOMIC_CHERN_LIMIT
            for mesh in meshes.values()
        )
    )
    return {
        "onsite": "epsilon_r = r/24",
        "twist_independence_defect": twist_defect,
        "ground_index": ground_index,
        "unique_product_ground_gap": unique_gap,
        "meshes": meshes,
        "pass": bool(passed),
    }


def _one_particle_control(
    model: HofstadterTorus,
    guard: BudgetGuard,
) -> dict:
    basis = fixed_particle_basis(model.n_sites, 1)
    twists = [
        (0.0, 0.0),
        (2.0 * math.pi / 7.0, 4.0 * math.pi / 7.0),
        (8.0 * math.pi / 9.0, 2.0 * math.pi / 9.0),
    ]
    rows = []
    for position, (theta_x, theta_y) in enumerate(twists):
        guard.check(f"one-particle:{position}")
        many_body = hard_core_hamiltonian(
            model, basis, theta_x, theta_y
        ).toarray()
        single_particle = single_particle_hamiltonian(
            model, theta_x, theta_y
        )
        matrix_defect = float(
            np.max(np.abs(many_body - single_particle), initial=0.0)
        )
        spectrum_defect = float(
            np.max(
                np.abs(
                    np.linalg.eigvalsh(many_body)
                    - np.linalg.eigvalsh(single_particle)
                ),
                initial=0.0,
            )
        )
        rows.append(
            {
                "theta_x": theta_x,
                "theta_y": theta_y,
                "matrix_defect": matrix_defect,
                "spectrum_defect": spectrum_defect,
            }
        )
    maximum = max(row["spectrum_defect"] for row in rows)
    return {
        "twists": rows,
        "maximum_spectrum_defect": maximum,
        "pass": maximum <= ONE_PARTICLE_LIMIT,
    }


def _single_particle_bundle(
    model: HofstadterTorus,
    nx: int,
    ny: int,
    rank: int,
    guard: BudgetGuard,
) -> tuple[dict, np.ndarray]:
    frames = np.empty(
        (nx, ny, model.n_sites, rank), dtype=np.complex128
    )
    gaps = np.empty((nx, ny), dtype=float)
    maximum_residual = 0.0
    maximum_orthonormality = 0.0
    for i in range(nx):
        for j in range(ny):
            guard.check(f"iqh:{nx}x{ny}:{i},{j}")
            theta_x = 2.0 * math.pi * i / nx
            theta_y = 2.0 * math.pi * j / ny
            hamiltonian = single_particle_hamiltonian(
                model, theta_x, theta_y
            )
            eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
            occupied = eigenvectors[:, :rank]
            frames[i, j] = occupied
            gaps[i, j] = eigenvalues[rank] - eigenvalues[rank - 1]
            residual = (
                hamiltonian @ occupied
                - occupied * eigenvalues[:rank][np.newaxis, :]
            )
            maximum_residual = max(
                maximum_residual,
                float(np.max(np.linalg.norm(residual, axis=0))),
            )
            maximum_orthonormality = max(
                maximum_orthonormality,
                float(
                    np.max(
                        np.abs(
                            occupied.conj().T @ occupied
                            - np.eye(rank)
                        ),
                        initial=0.0,
                    )
                ),
            )
    report = fhs_chern(frames)
    payload = {
        "mesh": [nx, ny],
        "occupied_rank": rank,
        "minimum_band_gap": float(np.min(gaps)),
        "maximum_eigenpair_residual": maximum_residual,
        "maximum_orthonormality_defect": maximum_orthonormality,
        "chern": _chern_payload(report),
    }
    payload["pass"] = bool(
        payload["minimum_band_gap"] > IQH_GAP_FLOOR
        and report.minimum_overlap_singular_value >= OVERLAP_FLOOR
        and report.maximum_absolute_plaquette_phase
        < math.pi - BRANCH_MARGIN
        and report.integer_residual <= INTEGRALITY_LIMIT
        and abs(report.rounded_chern) == 1
    )
    return payload, frames


def _integer_hall_control(
    model: HofstadterTorus,
    guard: BudgetGuard,
) -> dict:
    meshes = {}
    for nx, ny in ((7, 7), (9, 9)):
        payload, _frames = _single_particle_bundle(
            model, nx, ny, rank=6, guard=guard
        )
        meshes[f"{nx}x{ny}"] = payload
    coarse = meshes["7x7"]["chern"]
    confirmation = meshes["9x9"]["chern"]
    mesh_agreement = (
        coarse["rounded_chern"] == confirmation["rounded_chern"]
        and abs(coarse["chern"] - confirmation["chern"])
        <= MESH_AGREEMENT_LIMIT
    )
    passed = (
        all(mesh["pass"] for mesh in meshes.values())
        and mesh_agreement
        and coarse["rounded_chern"] != 0
    )
    return {
        "meshes": meshes,
        "mesh_agreement": bool(mesh_agreement),
        "orientation": int(coarse["rounded_chern"]),
        "pass": bool(passed),
    }


def _target_mesh(
    model: HofstadterTorus,
    basis,
    nx: int,
    ny: int,
    guard: BudgetGuard,
) -> tuple[dict, np.ndarray | None]:
    config = EigensolverConfig(
        k=3,
        which="SA",
        tolerance=1e-11,
        max_iterations=20_000,
        ncv=40,
    )
    frames = np.empty(
        (nx, ny, len(basis.states), 2), dtype=np.complex128
    )
    eigenvalues = np.empty((nx, ny, 3), dtype=float)
    residuals = np.empty((nx, ny, 3), dtype=float)
    orthonormality = np.empty((nx, ny), dtype=float)
    span_preservation = np.empty((nx, ny), dtype=float)
    for i in range(nx):
        for j in range(ny):
            guard.check(f"target:{nx}x{ny}:{i},{j}:start")
            theta_x = 2.0 * math.pi * i / nx
            theta_y = 2.0 * math.pi * j / ny
            hamiltonian = hard_core_hamiltonian(
                model, basis, theta_x, theta_y
            )
            v0 = deterministic_complex_v0(
                len(basis.states),
                base_seed=EIGENSOLVER_SEED,
                mesh_shape=(nx, ny),
                point=(i, j),
                sector_code=3,
            )
            try:
                eigensystem = lowest_eigensystem(
                    hamiltonian, config, v0=v0
                )
            except FQHEEigensolverError as error:
                return (
                    {
                        "mesh": [nx, ny],
                        "status": "INCONCLUSIVE_EIGENSOLVER",
                        "failed_point": [i, j],
                        "partial_eigenpairs": error.partial_eigenpairs,
                        "failure_kind": error.failure_kind,
                        "error": str(error),
                    },
                    None,
                )
            eigenvalues[i, j] = eigensystem.eigenvalues
            residuals[i, j] = eigensystem.residual_norms
            orthonormality[i, j] = eigensystem.orthonormality_defect
            span_preservation[i, j] = (
                eigensystem.span_preservation_sine
            )
            frames[i, j] = eigensystem.eigenvectors[:, :2]
            guard.check(f"target:{nx}x{ny}:{i},{j}:end")

    spectral = bundle_spectral_report(eigenvalues)
    maximum_residual = float(np.max(residuals))
    maximum_orthonormality = float(np.max(orthonormality))
    maximum_span_preservation_sine = float(
        np.max(span_preservation)
    )
    try:
        chern = fhs_chern(frames)
    except ValueError as error:
        return (
            {
                "mesh": [nx, ny],
                "status": "KILLED_OVERLAP",
                "error": str(error),
                "eigenvalues": eigenvalues.tolist(),
                "maximum_eigenpair_residual": maximum_residual,
                "maximum_orthonormality_defect": (
                    maximum_orthonormality
                ),
                "maximum_span_preservation_sine": (
                    maximum_span_preservation_sine
                ),
                "global_bundle_width": spectral["global_bundle_width"],
                "isolation_gap": spectral["isolation_gap"],
                "isolation_ratio": _finite(
                    spectral["isolation_ratio"]
                    if spectral["isolation_ratio"] is not None
                    else math.inf
                ),
            },
            None,
        )

    required_gap = max(
        ISOLATION_FLOOR,
        ISOLATION_RESIDUAL_FACTOR * maximum_residual,
    )
    gates = {
        "S9-G5": (
            maximum_residual <= RESIDUAL_LIMIT
            and maximum_orthonormality <= ORTHONORMALITY_LIMIT
        ),
        "S9-G6": (
            spectral["isolation_gap"] > required_gap
            and spectral["isolation_ratio"] is not None
            and spectral["isolation_ratio"] < 1.0
        ),
        "S9-G7": (
            chern.minimum_overlap_singular_value >= OVERLAP_FLOOR
        ),
        "S9-G8": (
            chern.maximum_absolute_plaquette_phase
            < math.pi - BRANCH_MARGIN
        ),
        "S9-G9": chern.integer_residual <= INTEGRALITY_LIMIT,
    }
    payload = {
        "mesh": [nx, ny],
        "status": "MEASURED",
        "eigenvalues": eigenvalues.tolist(),
        "maximum_eigenpair_residual": maximum_residual,
        "maximum_orthonormality_defect": maximum_orthonormality,
        "maximum_span_preservation_sine": (
            maximum_span_preservation_sine
        ),
        "maximum_internal_splitting": (
            spectral["maximum_internal_splitting"]
        ),
        "global_bundle_width": spectral["global_bundle_width"],
        "isolation_gap": spectral["isolation_gap"],
        "required_isolation_gap": required_gap,
        "isolation_ratio": _finite(
            spectral["isolation_ratio"]
            if spectral["isolation_ratio"] is not None
            else math.inf
        ),
        "minimum_overlap_singular_value": (
            chern.minimum_overlap_singular_value
        ),
        "chern": _chern_payload(chern),
        "gates": gates,
        "instrument_and_isolation_pass": bool(all(gates.values())),
    }
    return payload, frames


def _gauge_attack(
    frames: np.ndarray,
    baseline: ChernReport,
    nx: int,
    ny: int,
    guard: BudgetGuard,
) -> dict:
    rows = []
    passed = True
    for replicate in range(GAUGE_SCRAMBLES):
        guard.check(f"gauge:{nx}x{ny}:{replicate}")
        scrambled = scramble_bundle_frames(
            frames,
            base_seed=GAUGE_SCRAMBLE_SEED,
            replicate=replicate,
            sector_code=3,
        )
        report = fhs_chern(scrambled)
        difference = abs(report.chern - baseline.chern)
        row_pass = (
            difference <= GAUGE_VARIANCE_LIMIT
            and report.minimum_overlap_singular_value >= OVERLAP_FLOOR
            and report.maximum_absolute_plaquette_phase
            < math.pi - BRANCH_MARGIN
        )
        passed = passed and row_pass
        rows.append(
            {
                "replicate": replicate,
                "chern": report.chern,
                "difference_from_unscrambled": difference,
                "minimum_overlap_singular_value": (
                    report.minimum_overlap_singular_value
                ),
                "maximum_absolute_plaquette_phase": (
                    report.maximum_absolute_plaquette_phase
                ),
                "pass": bool(row_pass),
            }
        )
    return {
        "mesh": [nx, ny],
        "replicates": rows,
        "maximum_chern_difference": max(
            row["difference_from_unscrambled"] for row in rows
        ),
        "pass": bool(passed),
    }


TARGET_MESH_GATES = (
    "S9-G5",
    "S9-G6",
    "S9-G7",
    "S9-G8",
    "S9-G9",
)
GATE_STATES = {"PASS", "FAIL", "NOT_RUN", "INCOMPLETE"}


def _gate_state(
    status: str,
    *,
    reason: str = "",
    mesh_states: dict | None = None,
) -> dict:
    if status not in GATE_STATES:
        raise ValueError(f"invalid S9 gate state: {status}")
    payload = {
        "status": status,
        "pass": (
            True
            if status == "PASS"
            else False
            if status == "FAIL"
            else None
        ),
    }
    if reason:
        payload["reason"] = reason
    if mesh_states is not None:
        payload["mesh_states"] = mesh_states
    return payload


def _not_run_gates(reason: str) -> dict:
    return {
        gate: _gate_state("NOT_RUN", reason=reason)
        for gate in (*TARGET_MESH_GATES, "S9-G10", "S9-G11")
    }


def _mesh_gate_state(payload: dict, gate: str) -> dict:
    status = payload.get("status")
    if status == "MEASURED":
        passed = bool(payload["gates"][gate])
        return _gate_state("PASS" if passed else "FAIL")
    if status == "KILLED_OVERLAP":
        if gate == "S9-G5":
            passed = (
                payload["maximum_eigenpair_residual"] <= RESIDUAL_LIMIT
                and payload["maximum_orthonormality_defect"]
                <= ORTHONORMALITY_LIMIT
            )
            return _gate_state("PASS" if passed else "FAIL")
        if gate == "S9-G6":
            ratio = payload.get("isolation_ratio")
            gap = payload.get("isolation_gap")
            required = max(
                ISOLATION_FLOOR,
                ISOLATION_RESIDUAL_FACTOR
                * payload["maximum_eigenpair_residual"],
            )
            passed = (
                gap is not None
                and gap > required
                and ratio is not None
                and ratio < 1.0
            )
            return _gate_state("PASS" if passed else "FAIL")
        if gate == "S9-G7":
            return _gate_state(
                "FAIL",
                reason="neighbor overlap was singular",
            )
    return _gate_state(
        "NOT_RUN",
        reason=payload.get("reason", f"mesh status was {status}"),
    )


def _aggregate_mesh_gate(
    gate: str,
    coarse: dict,
    confirmation: dict,
) -> dict:
    mesh_states = {
        "7x7": _mesh_gate_state(coarse, gate),
        "9x9": _mesh_gate_state(confirmation, gate),
    }
    evaluated = [
        state["status"]
        for state in mesh_states.values()
        if state["status"] in {"PASS", "FAIL"}
    ]
    if "FAIL" in evaluated:
        return _gate_state(
            "FAIL",
            reason="at least one evaluated mesh failed",
            mesh_states=mesh_states,
        )
    if len(evaluated) == 2 and all(
        status == "PASS" for status in evaluated
    ):
        return _gate_state("PASS", mesh_states=mesh_states)
    if evaluated:
        return _gate_state(
            "INCOMPLETE",
            reason="an evaluated mesh passed but a required mesh was not run",
            mesh_states=mesh_states,
        )
    return _gate_state(
        "NOT_RUN",
        reason="no target mesh evaluated this gate",
        mesh_states=mesh_states,
    )


def _hypothesis_state(status: str, *, reason: str = "") -> dict:
    payload = {
        "status": status,
        "pass": (
            True
            if status == "CONFIRMED"
            else False
            if status == "KILLED"
            else None
        ),
    }
    if reason:
        payload["reason"] = reason
    return payload


def _triggered_kills(
    gate_ledger: dict,
    *,
    h1_status: str,
    h2_status: str,
) -> list[str]:
    kill_by_gate = {
        "S9-G5": "KILLED_EIGENSYSTEM_FRAME",
        "S9-G6": "KILLED_BUNDLE_ISOLATION",
        "S9-G7": "KILLED_OVERLAP",
        "S9-G8": "KILLED_BRANCH",
        "S9-G9": "KILLED_NONINTEGRAL_CHERN",
        "S9-G10": "KILLED_MESH_DISAGREEMENT",
        "S9-G11": "KILLED_GAUGE_VARIANCE",
    }
    kills = [
        kill
        for gate, kill in kill_by_gate.items()
        if gate_ledger[gate]["status"] == "FAIL"
    ]
    if h1_status == "CONFIRMED" and h2_status == "KILLED":
        kills.append("KILLED_TOPOLOGICAL_SIGNATURE")
    return kills


def run_probe(
    manifest: dict,
    manifest_digest: str,
    correction: dict,
    correction_digest: str,
) -> dict:
    guard = BudgetGuard()
    model = HofstadterTorus(
        lx=6,
        ly=4,
        flux_numerator=1,
        flux_denominator=4,
        hopping=1.0,
    )
    basis = fixed_particle_basis(model.n_sites, 3)
    static = _static_controls(model, basis, guard)
    atomic = _atomic_control(model, basis, guard)
    one_particle = _one_particle_control(model, guard)
    iqh = _integer_hall_control(model, guard)
    controls = {
        "static_construction": static,
        "atomic_zero_chern": atomic,
        "one_particle_representation": one_particle,
        "integer_hall_orientation": iqh,
    }
    controls_pass = (
        static["pass"]
        and atomic["pass"]
        and one_particle["pass"]
        and iqh["pass"]
    )

    artifact = {
        "schema": "hypercomplexbrain.s9_fqhe_probe.v2",
        "preregistration": (
            "manifests/s9_fqhe_preregistration.json"
        ),
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_digest": manifest_digest,
        "instrument_correction": (
            "manifests/s9_fqhe_instrument_correction.json"
        ),
        "instrument_correction_commit": CORRECTION_COMMIT,
        "instrument_correction_digest": correction_digest,
        "initial_artifact": correction["prior_record"]["initial_artifact"],
        "initial_artifact_digest": (
            correction["prior_record"]["initial_artifact_digest"]
        ),
        "implementation_commit": current_commit(ROOT),
        "environment": _environment_provenance(),
        "model": {
            "Lx": model.lx,
            "Ly": model.ly,
            "alpha": [model.flux_numerator, model.flux_denominator],
            "sites": model.n_sites,
            "particles": 3,
            "hilbert_dimension": len(basis.states),
            "twist_meshes": [[7, 7], [9, 9]],
            "eigensolver_seed": EIGENSOLVER_SEED,
            "gauge_scramble_seed": GAUGE_SCRAMBLE_SEED,
            "gauge_scrambles": GAUGE_SCRAMBLES,
        },
        "controls_first": controls,
        "controls_pass": bool(controls_pass),
        "target": {},
        "gauge_attacks": {},
        "gate_ledger": {},
        "hypotheses": {},
        "triggered_kill_conditions": [],
        "typed_remainder": manifest["typed_remainder"],
        "interpretation_ceiling": manifest["evidence_floor"],
    }

    for gate, passed in static["gates"].items():
        artifact["gate_ledger"][gate] = _gate_state(
            "PASS" if passed else "FAIL"
        )
    artifact["gate_ledger"]["S9-C1"] = _gate_state(
        "PASS" if atomic["pass"] else "FAIL"
    )
    artifact["gate_ledger"]["S9-C2"] = _gate_state(
        "PASS" if one_particle["pass"] else "FAIL"
    )
    artifact["gate_ledger"]["S9-C3"] = _gate_state(
        "PASS" if iqh["pass"] else "FAIL"
    )

    if not controls_pass:
        artifact["status"] = "VOID_INSTRUMENT"
        artifact["target"] = {
            "status": "NOT_RUN",
            "reason": "one or more preregistered controls failed",
        }
        artifact["gate_ledger"].update(
            _not_run_gates("instrument voided by controls")
        )
        artifact["hypotheses"] = {
            key: _hypothesis_state(
                "VOID",
                reason="instrument controls failed",
            )
            for key in ("S9-FQH-H1", "S9-FQH-H2", "S9-FQH-H3")
        }
        artifact["triggered_kill_conditions"].append(
            "VOID_INSTRUMENT_CONTROLS"
        )
        artifact["resource_budget"] = _budget_payload(guard)
        return artifact

    coarse, coarse_frames = _target_mesh(
        model, basis, 7, 7, guard
    )
    artifact["target"]["7x7"] = coarse
    if coarse["status"] == "INCONCLUSIVE_EIGENSOLVER":
        artifact["status"] = "INCONCLUSIVE_EIGENSOLVER"
        artifact["target"]["9x9"] = {
            "status": "NOT_RUN",
            "reason": "coarse eigensolver did not converge",
        }
        artifact["gate_ledger"].update(
            _not_run_gates("coarse eigensolver inconclusive")
        )
        artifact["hypotheses"] = {
            key: _hypothesis_state(
                "INCONCLUSIVE",
                reason="required eigensystem unavailable",
            )
            for key in ("S9-FQH-H1", "S9-FQH-H2", "S9-FQH-H3")
        }
        artifact["resource_budget"] = _budget_payload(guard)
        return artifact

    coarse_pass = bool(
        coarse.get("instrument_and_isolation_pass", False)
    )
    if coarse_pass:
        confirmation, confirmation_frames = _target_mesh(
            model, basis, 9, 9, guard
        )
    else:
        confirmation = {
            "status": "NOT_RUN",
            "reason": "coarse instrument or isolation gate failed",
        }
        confirmation_frames = None
    artifact["target"]["9x9"] = confirmation

    both_measured = all(
        payload.get("status") == "MEASURED"
        for payload in (coarse, confirmation)
    )
    if both_measured:
        coarse_chern = coarse["chern"]
        confirmation_chern = confirmation["chern"]
        mesh_agreement = (
            coarse_chern["rounded_chern"]
            == confirmation_chern["rounded_chern"]
            and abs(
                coarse_chern["chern"] - confirmation_chern["chern"]
            )
            <= MESH_AGREEMENT_LIMIT
        )
    else:
        mesh_agreement = False

    for gate in TARGET_MESH_GATES:
        artifact["gate_ledger"][gate] = _aggregate_mesh_gate(
            gate, coarse, confirmation
        )
    artifact["gate_ledger"]["S9-G10"] = (
        _gate_state("PASS" if mesh_agreement else "FAIL")
        if both_measured
        else _gate_state(
            "NOT_RUN",
            reason="both target meshes were not measured",
        )
    )

    attack_inputs = {
        "7x7": (coarse, coarse_frames, 7, 7),
        "9x9": (confirmation, confirmation_frames, 9, 9),
    }
    gauge_mesh_states = {}
    executed_attacks = {}
    for label, (payload, frames, nx, ny) in attack_inputs.items():
        if payload.get("status") == "MEASURED" and frames is not None:
            attack = _gauge_attack(
                frames,
                fhs_chern(frames),
                nx,
                ny,
                guard,
            )
            executed_attacks[label] = attack
            gauge_mesh_states[label] = _gate_state(
                "PASS" if attack["pass"] else "FAIL"
            )
        else:
            gauge_mesh_states[label] = _gate_state(
                "NOT_RUN",
                reason=payload.get(
                    "reason",
                    f"target mesh status was {payload.get('status')}",
                ),
            )
    artifact["gauge_attacks"] = {
        **executed_attacks,
        "not_run": {
            label: state
            for label, state in gauge_mesh_states.items()
            if state["status"] == "NOT_RUN"
        },
    }
    gauge_statuses = [
        state["status"] for state in gauge_mesh_states.values()
    ]
    if "FAIL" in gauge_statuses:
        artifact["gate_ledger"]["S9-G11"] = _gate_state(
            "FAIL",
            reason="an executed local-frame attack failed",
            mesh_states=gauge_mesh_states,
        )
    elif gauge_statuses == ["PASS", "PASS"]:
        artifact["gate_ledger"]["S9-G11"] = _gate_state(
            "PASS",
            mesh_states=gauge_mesh_states,
        )
    elif "PASS" in gauge_statuses:
        artifact["gate_ledger"]["S9-G11"] = _gate_state(
            "INCOMPLETE",
            reason="completed meshes passed, but a required mesh was not run",
            mesh_states=gauge_mesh_states,
        )
    else:
        artifact["gate_ledger"]["S9-G11"] = _gate_state(
            "NOT_RUN",
            reason="no completed target frame was available",
            mesh_states=gauge_mesh_states,
        )

    h1_gate_states = [
        artifact["gate_ledger"][gate]["status"]
        for gate in ("S9-G5", "S9-G6", "S9-G7")
    ]
    if "FAIL" in h1_gate_states:
        h1_status = "KILLED"
        h1_reason = "an evaluated frame or isolation gate failed"
    elif all(status == "PASS" for status in h1_gate_states):
        h1_status = "CONFIRMED"
        h1_reason = ""
    else:
        h1_status = "INCOMPLETE"
        h1_reason = "both admitted target meshes are required"

    target_chern = (
        coarse["chern"]["rounded_chern"]
        if coarse.get("status") == "MEASURED"
        else None
    )
    iqh_orientation = iqh["orientation"]
    if h1_status == "CONFIRMED":
        h2_pass = (
            all(
                artifact["gate_ledger"][gate]["status"] == "PASS"
                for gate in ("S9-G8", "S9-G9", "S9-G10")
            )
            and target_chern is not None
            and abs(target_chern) == 1
            and target_chern == iqh_orientation
        )
        h2_status = "CONFIRMED" if h2_pass else "KILLED"
        h2_reason = "" if h2_pass else "evaluated topological gates failed"
    else:
        h2_status = "NOT_RUN"
        h2_reason = "H1 did not establish an isolated rank-two bundle"

    if artifact["gate_ledger"]["S9-G11"]["status"] == "FAIL":
        h3_status = "KILLED"
        h3_reason = "an executed local-frame attack failed"
    elif (
        h1_status == "CONFIRMED"
        and artifact["gate_ledger"]["S9-G11"]["status"] == "PASS"
    ):
        h3_status = "CONFIRMED"
        h3_reason = ""
    elif executed_attacks:
        h3_status = "INCOMPLETE"
        h3_reason = "coarse gauge telemetry cannot replace both meshes"
    else:
        h3_status = "NOT_RUN"
        h3_reason = "no completed target frame was available"

    artifact["hypotheses"] = {
        "S9-FQH-H1": _hypothesis_state(
            h1_status,
            reason=h1_reason,
        ),
        "S9-FQH-H2": _hypothesis_state(
            h2_status,
            reason=h2_reason,
        ),
        "S9-FQH-H3": _hypothesis_state(
            h3_status,
            reason=h3_reason,
        ),
    }

    if h2_status == "CONFIRMED":
        artifact["bundle_normalized_response"] = {
            "value": coarse["chern"]["chern"] / 2.0,
            "magnitude": abs(coarse["chern"]["chern"] / 2.0),
            "interpretation_authorized": True,
            "scope": "finite-size determinant-bundle label",
        }
    else:
        artifact["bundle_normalized_response"] = {
            "value": None,
            "magnitude": None,
            "interpretation_authorized": False,
            "reason": "the preregistered topological signature did not pass",
        }

    if all(
        status == "CONFIRMED"
        for status in (h1_status, h2_status, h3_status)
    ):
        artifact["status"] = "CONFIRMED_FINITE_SIZE_SIGNATURE"
    elif confirmation.get("status") == "INCONCLUSIVE_EIGENSOLVER":
        artifact["status"] = "INCONCLUSIVE_EIGENSOLVER"
    elif "KILLED" in (h1_status, h2_status, h3_status):
        artifact["status"] = "KILLED_PARAMETER_POINT"
    else:
        artifact["status"] = "INCONCLUSIVE_INCOMPLETE"

    artifact["triggered_kill_conditions"] = _triggered_kills(
        artifact["gate_ledger"],
        h1_status=h1_status,
        h2_status=h2_status,
    )

    artifact["resource_budget"] = _budget_payload(guard)
    return artifact


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _commit_timestamp() -> str:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%cI", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _write_envelope(
    artifact: dict,
    manifest_digest: str,
    correction_digest: str,
) -> None:
    measured_meshes = [
        label
        for label, payload in artifact.get("target", {}).items()
        if isinstance(payload, dict)
        and payload.get("status") == "MEASURED"
    ]
    measured_scope = (
        ", ".join(measured_meshes) if measured_meshes else "none"
    )
    envelope = EvidenceEnvelope(
        claim_id="FQHE-S9-PROBE_RESULT-CORRECTED",
        evidence_tag="M",
        command=(
            "python experiments/run_fqhe_probe.py "
            "--manifest manifests/s9_fqhe_preregistration.json "
            "--correction manifests/s9_fqhe_instrument_correction.json"
        ),
        observed_result={
            "status": artifact["status"],
            "sample_size": 1,
            "controls_pass": artifact.get("controls_pass", False),
            "target_chern": (
                artifact.get("target", {})
                .get("7x7", {})
                .get("chern", {})
                .get("chern")
            ),
            "bundle_normalized_response": artifact.get(
                "bundle_normalized_response"
            ),
        },
        commit_sha=current_commit(ROOT),
        working_directory=".",
        platform=platform.system().lower(),
        environment=environment_digest(),
        input_hashes=[manifest_digest, correction_digest],
        seeds=[EIGENSOLVER_SEED, GAUGE_SCRAMBLE_SEED],
        raw_artifacts={
            "artifacts/s9_fqhe/fqhe_probe.corrected.json": (
                file_digest(OUT_FILE)
            )
        },
        uncertainty={
            "scope": (
                "one finite 6x4 parameter point; target meshes actually "
                f"measured: {measured_scope}"
            ),
            "independence": "not independently witnessed",
            "transport": (
                "C/2 is a bundle-normalized label, not measured conductance"
            ),
            "initial_artifact": artifact.get("initial_artifact_digest"),
        },
        producer="local-s9-runner",
        verifier="",
        timestamp=_commit_timestamp(),
        typed_remainders=[
            {
                "kind": "empirical_residual",
                "statement": (
                    "Thermodynamic scaling, continuum transport, fractional "
                    "charge, and anyon statistics remain unmeasured."
                ),
            }
        ],
        verification_mode="not_requested",
    )
    save_envelope(envelope, ENVELOPE_FILE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the immutable S9 finite-size FQH probe."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PREREGISTRATION,
        help="must resolve to manifests/s9_fqhe_preregistration.json",
    )
    parser.add_argument(
        "--correction",
        type=Path,
        default=CORRECTION,
        help="must resolve to manifests/s9_fqhe_instrument_correction.json",
    )
    args = parser.parse_args()
    manifest_path = (
        args.manifest
        if args.manifest.is_absolute()
        else ROOT / args.manifest
    )
    manifest, manifest_digest = _load_preregistration(manifest_path)
    correction_path = (
        args.correction
        if args.correction.is_absolute()
        else ROOT / args.correction
    )
    correction, correction_digest = _load_correction(correction_path)
    if OUT_FILE.exists() or ENVELOPE_FILE.exists():
        raise FileExistsError(
            "the one authorized corrected S9 output already exists"
        )
    try:
        artifact = run_probe(
            manifest,
            manifest_digest,
            correction,
            correction_digest,
        )
    except FQHEResourceLimit as error:
        artifact = {
            "schema": "hypercomplexbrain.s9_fqhe_probe.v2",
            "preregistration": (
                "manifests/s9_fqhe_preregistration.json"
            ),
            "preregistration_commit": PREREGISTRATION_COMMIT,
            "preregistration_digest": manifest_digest,
            "instrument_correction": (
                "manifests/s9_fqhe_instrument_correction.json"
            ),
            "instrument_correction_commit": CORRECTION_COMMIT,
            "instrument_correction_digest": correction_digest,
            "initial_artifact": (
                correction["prior_record"]["initial_artifact"]
            ),
            "initial_artifact_digest": (
                correction["prior_record"]["initial_artifact_digest"]
            ),
            "implementation_commit": current_commit(ROOT),
            "environment": _environment_provenance(),
            "status": "INCONCLUSIVE_RESOURCE_LIMIT",
            "error": str(error),
            "controls_pass": False,
            "target": {"status": "NOT_COMPLETED"},
            "gate_ledger": _not_run_gates(
                "resource budget stopped execution"
            ),
            "hypotheses": {
                key: _hypothesis_state(
                    "INCONCLUSIVE",
                    reason="resource budget stopped execution",
                )
                for key in (
                    "S9-FQH-H1",
                    "S9-FQH-H2",
                    "S9-FQH-H3",
                )
            },
            "triggered_kill_conditions": [],
            "typed_remainder": manifest["typed_remainder"],
            "resource_budget": {
                "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                "configured_maximum_elapsed_seconds": 30.0 * 60.0,
                "configured_maximum_resident_bytes": 2 * 1024**3,
                "observed_elapsed_seconds": None,
                "observed_peak_resident_bytes": None,
            },
        }
    _write_json(OUT_FILE, artifact)
    _write_envelope(artifact, manifest_digest, correction_digest)
    print(json.dumps(
        {
            "artifact": str(OUT_FILE.relative_to(ROOT)),
            "envelope": str(ENVELOPE_FILE.relative_to(ROOT)),
            "status": artifact["status"],
            "controls_pass": artifact.get("controls_pass", False),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0 if artifact["status"] == "CONFIRMED_FINITE_SIZE_SIGNATURE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
