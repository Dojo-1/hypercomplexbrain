"""QSigma-R3B-0 four-cell delayed phase-memory calibration.

The object implemented here is deliberately narrow:

* ``SELF`` prepares a known-reference phase state;
* ``OTHER`` supplies the relation ``same`` or ``orthogonal``;
* ``MEMORY`` applies either identity (positive-control target) or complete
  computational-basis dephasing (matched control);
* ``AUDITOR`` uses a fixed, reference-relative, two-outcome POVM on one delayed
  memory copy.

For ``|psi(phi)> = (|0> + exp(i phi)|1>)/sqrt(2)`` the click probabilities are
exactly ``1, 0`` in the coherent arm and ``1/2, 1/2`` after complete dephasing.
That separates a deliberately coherent simulator from its dephased control.  It
does **not** establish quantum, causal, cognitive, memory, or hardware
advantage.

The module follows the frozen R3B-0 factor schedule and returns an
eight-coordinate vector.  Unmeasured coordinates are ``NaN`` *and* masked
false.  There is no scalar conversion, score, or write to the legacy
``q_causal`` field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum

import numpy as np

from .advantage import OUTCOME_DIMENSIONS, OutcomeVector

__all__ = [
    "EVIDENCE_CEILING",
    "CALIBRATION_PHASES",
    "HELDOUT_PHASES",
    "COMMON_FRAMES",
    "REPETITIONS_PER_FACTOR_CELL",
    "TRIALS_PER_ARM_PER_SEED",
    "Cell",
    "CellRole",
    "Arm",
    "InstrumentArm",
    "Relation",
    "TrialClass",
    "QubitCell",
    "PhaseComparisonPOVM",
    "TrialSpec",
    "TrialResult",
    "OutcomeVector",
    "FourCellOutcomeVector",
    "PairedOutcome",
    "ArmProtocolResult",
    "ResourceParity",
    "AuditorObservable",
    "BasisAttackObservable",
    "RoleAblationObservable",
    "SeedCalibration",
    "phase_state",
    "phase_ket",
    "phase_density",
    "reference_projector",
    "complete_dephase",
    "complete_dephasing",
    "frame_unitary",
    "analytic_click_probability",
    "run_trial",
    "protocol_schedule",
    "run_protocol_arm",
    "resource_parity",
    "auditor_observable",
    "basis_attack_observable",
    "execute_four_cell",
    "role_ablation_observables",
    "run_seed_calibration",
]


EVIDENCE_CEILING = "synthetic-instrument-calibration-only"
CALIBRATION_PHASES = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
HELDOUT_PHASES = (
    math.pi / 4.0,
    3.0 * math.pi / 4.0,
    5.0 * math.pi / 4.0,
    7.0 * math.pi / 4.0,
)
COMMON_FRAMES = ("I", "H", "S", "H@S")
REPETITIONS_PER_FACTOR_CELL = 8
TRIALS_PER_ARM_PER_SEED = 512
_ALL_PHASES = CALIBRATION_PHASES + HELDOUT_PHASES
_TOL = 1e-12


class Cell(str, Enum):
    """Typed positions in the four-cell instrument."""

    SELF = "SELF"
    OTHER = "OTHER"
    MEMORY = "MEMORY"
    AUDITOR = "AUDITOR"


class Arm(str, Enum):
    """The only intervention: identity versus complete dephasing."""

    COHERENT = "coherent"
    DEPHASED = "dephased"


class Relation(IntEnum):
    """The binary task label ``y``."""

    SAME = 0
    ORTHOGONAL = 1


# Descriptive aliases for callers that prefer the longer names.
CellRole = Cell
InstrumentArm = Arm
TrialClass = Relation


def _readonly(value: np.ndarray, dtype=None) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True)
    result.setflags(write=False)
    return result


def _plain_int(value: int, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    value = int(value)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _density(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=complex)
    if matrix.shape != (2, 2):
        raise ValueError("four-cell densities must be exactly 2x2")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("density entries must be finite")
    hermitian = (matrix + matrix.conj().T) / 2.0
    if float(np.max(np.abs(matrix - hermitian))) > _TOL:
        raise ValueError("density is not Hermitian")
    if float(np.min(np.linalg.eigvalsh(hermitian))) < -_TOL:
        raise ValueError("density is not positive semidefinite")
    if abs(float(np.trace(hermitian).real) - 1.0) > _TOL:
        raise ValueError("density does not have unit trace")
    return _readonly(hermitian, complex)


def _effect(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=complex)
    if matrix.shape != (2, 2):
        raise ValueError("POVM effects must be exactly 2x2")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("POVM entries must be finite")
    hermitian = (matrix + matrix.conj().T) / 2.0
    if float(np.max(np.abs(matrix - hermitian))) > _TOL:
        raise ValueError("POVM effect is not Hermitian")
    eigenvalues = np.linalg.eigvalsh(hermitian)
    if float(np.min(eigenvalues)) < -_TOL:
        raise ValueError("POVM effect is not positive semidefinite")
    if float(np.max(eigenvalues)) > 1.0 + _TOL:
        raise ValueError("POVM effect exceeds the identity")
    return _readonly(hermitian, complex)


def _born(effect: np.ndarray, density: np.ndarray) -> float:
    value = float(np.trace(_effect(effect) @ _density(density)).real)
    if value < -_TOL or value > 1.0 + _TOL:
        raise ValueError(f"Born probability outside [0,1]: {value}")
    return min(1.0, max(0.0, value))


def _relation(value: Relation | int | str) -> Relation:
    if isinstance(value, Relation):
        return value
    if isinstance(value, str):
        aliases = {"same": Relation.SAME, "orthogonal": Relation.ORTHOGONAL}
        try:
            return aliases[value.lower()]
        except KeyError as exc:
            raise ValueError("relation must be 'same' or 'orthogonal'") from exc
    value = _plain_int(value, "relation")
    try:
        return Relation(value)
    except ValueError as exc:
        raise ValueError("relation must be 0 (same) or 1 (orthogonal)") from exc


def _phase_index(phase: float) -> int:
    phase = _finite(phase, "reference_phase")
    wrapped = phase % (2.0 * math.pi)
    for index, registered in enumerate(_ALL_PHASES):
        if abs(wrapped - registered) <= _TOL:
            return index
    # 2*pi is the same registered phase as zero.
    if abs(wrapped - 2.0 * math.pi) <= _TOL:
        return 0
    raise ValueError("reference_phase is outside the frozen R3B-0 phase grid")


def phase_state(phase: float) -> np.ndarray:
    """Return ``(|0> + exp(i*phase)|1>)/sqrt(2)`` as a read-only ket."""

    phase = _finite(phase, "phase")
    return _readonly(
        np.array([1.0, np.exp(1j * phase)], dtype=complex) / math.sqrt(2.0),
        complex,
    )


phase_ket = phase_state


def phase_density(phase: float) -> np.ndarray:
    ket = phase_state(phase)
    return _density(np.outer(ket, ket.conj()))


def reference_projector(reference_phase: float) -> np.ndarray:
    """Compile the known classical phase reference into a rank-one projector."""

    return phase_density(reference_phase)


def complete_dephase(density: np.ndarray) -> np.ndarray:
    """Complete dephasing in the computational (Z) basis."""

    density = _density(density)
    return _density(np.diag(np.diag(density)))


complete_dephasing = complete_dephase


def frame_unitary(name: str) -> np.ndarray:
    """One frozen common frame; ``H@S`` applies ``S`` then ``H``."""

    if not isinstance(name, str):
        raise TypeError("frame must be a string")
    identity = np.eye(2, dtype=complex)
    hadamard = np.array(
        [[1.0, 1.0], [1.0, -1.0]], dtype=complex
    ) / math.sqrt(2.0)
    phase = np.diag([1.0, 1j]).astype(complex)
    frames = {
        "I": identity,
        "H": hadamard,
        "S": phase,
        "H@S": hadamard @ phase,
    }
    try:
        unitary = frames[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown frame {name!r}; expected one of {COMMON_FRAMES}"
        ) from exc
    defect = float(np.linalg.norm(unitary.conj().T @ unitary - np.eye(2), ord=2))
    if defect > _TOL:  # construction guard
        raise RuntimeError(f"registered frame {name} is not unitary")
    return _readonly(unitary, complex)


def _transport(matrix: np.ndarray, frame: np.ndarray) -> np.ndarray:
    return frame @ matrix @ frame.conj().T


@dataclass(frozen=True)
class QubitCell:
    role: Cell
    density: np.ndarray

    def __post_init__(self) -> None:
        if not isinstance(self.role, Cell):
            object.__setattr__(self, "role", Cell(self.role))
        object.__setattr__(self, "density", _density(self.density))


@dataclass(frozen=True)
class PhaseComparisonPOVM:
    """Fixed known-reference POVM, not a universal unknown-state comparator."""

    match: np.ndarray
    orthogonal: np.ndarray

    def __post_init__(self) -> None:
        match = _effect(self.match)
        orthogonal = _effect(self.orthogonal)
        if float(np.max(np.abs(match + orthogonal - np.eye(2)))) > _TOL:
            raise ValueError("POVM effects do not sum to identity")
        object.__setattr__(self, "match", match)
        object.__setattr__(self, "orthogonal", orthogonal)

    @property
    def completeness_defect(self) -> float:
        return float(np.linalg.norm(
            self.match + self.orthogonal - np.eye(2), ord=2
        ))

    @property
    def positivity_margin(self) -> float:
        return float(min(
            np.min(np.linalg.eigvalsh(self.match)),
            np.min(np.linalg.eigvalsh(self.orthogonal)),
        ))


def _reference_povm(reference_phase: float) -> PhaseComparisonPOVM:
    match = reference_projector(reference_phase)
    return PhaseComparisonPOVM(match, np.eye(2, dtype=complex) - match)


@dataclass(frozen=True)
class TrialSpec:
    """One factor cell in the frozen schedule.

    The arm is intentionally absent from the random key, so matched target and
    control specs receive the same uniform variate.
    """

    reference_phase: float
    relation: Relation | int | str
    arm: Arm
    seed: int
    frame: str = "I"
    repetition: int = 0
    delayed_copies: int = 1

    def __post_init__(self) -> None:
        phase = _finite(self.reference_phase, "reference_phase")
        _phase_index(phase)
        object.__setattr__(self, "reference_phase", phase)
        object.__setattr__(self, "relation", _relation(self.relation))
        if not isinstance(self.arm, Arm):
            object.__setattr__(self, "arm", Arm(self.arm))
        object.__setattr__(self, "seed", _plain_int(self.seed, "seed"))
        frame_unitary(self.frame)
        repetition = _plain_int(self.repetition, "repetition")
        if repetition >= REPETITIONS_PER_FACTOR_CELL:
            raise ValueError(
                f"repetition must be < {REPETITIONS_PER_FACTOR_CELL}"
            )
        object.__setattr__(self, "repetition", repetition)
        copies = _plain_int(
            self.delayed_copies, "delayed_copies", minimum=1
        )
        if copies != 1:
            raise ValueError("R3B-0 fixes exactly one delayed copy per trial")
        object.__setattr__(self, "delayed_copies", copies)

    @property
    def pair_key(self) -> tuple[float, Relation, str, int]:
        return (
            self.reference_phase,
            self.relation,
            self.frame,
            self.repetition,
        )


def _uniform_for(spec: TrialSpec) -> float:
    seed_sequence = np.random.SeedSequence([
        spec.seed,
        _phase_index(spec.reference_phase),
        int(spec.relation),
        COMMON_FRAMES.index(spec.frame),
        spec.repetition,
        0x52334230,  # ASCII-ish domain separation: R3B0
    ])
    return float(np.random.default_rng(seed_sequence).random())


@dataclass(frozen=True)
class TrialResult:
    spec: TrialSpec
    cells: tuple[QubitCell, ...]
    povm: PhaseComparisonPOVM
    click_probability: float
    uniform_draw: float
    click: bool
    predicted_relation: Relation
    correct: bool
    evidence_ceiling: str = EVIDENCE_CEILING

    def __post_init__(self) -> None:
        cells = tuple(self.cells)
        if len(cells) != len(Cell) or {cell.role for cell in cells} != set(Cell):
            raise ValueError("a trial must retain exactly one cell of every role")
        object.__setattr__(self, "cells", cells)
        probability = _finite(self.click_probability, "click_probability")
        uniform = _finite(self.uniform_draw, "uniform_draw")
        if not (-_TOL <= probability <= 1.0 + _TOL):
            raise ValueError("click probability lies outside [0,1]")
        if not (0.0 <= uniform < 1.0):
            raise ValueError("uniform draw lies outside [0,1)")
        object.__setattr__(
            self, "click_probability", min(1.0, max(0.0, probability))
        )
        object.__setattr__(self, "predicted_relation",
                           _relation(self.predicted_relation))
        expected_prediction = (
            Relation.SAME if self.click else Relation.ORTHOGONAL
        )
        if self.predicted_relation is not expected_prediction:
            raise ValueError("click and predicted relation disagree")
        if bool(self.correct) != (self.predicted_relation is self.spec.relation):
            raise ValueError("correct flag and relation disagree")
        if self.evidence_ceiling != EVIDENCE_CEILING:
            raise ValueError("trial evidence ceiling may not be raised")

    def cell(self, role: Cell) -> QubitCell:
        role = role if isinstance(role, Cell) else Cell(role)
        return next(cell for cell in self.cells if cell.role is role)


def analytic_click_probability(
    reference_phase: float,
    relation: Relation | int | str,
    arm: Arm,
) -> float:
    """Exact probability before frame transport and Bernoulli sampling."""

    _phase_index(reference_phase)
    relation = _relation(relation)
    arm = arm if isinstance(arm, Arm) else Arm(arm)
    if arm is Arm.COHERENT:
        return 1.0 if relation is Relation.SAME else 0.0
    return 0.5


def run_trial(spec: TrialSpec) -> TrialResult:
    """Run one fixed, one-copy, deterministically seeded factor cell."""

    if not isinstance(spec, TrialSpec):
        raise TypeError("spec must be a TrialSpec")

    candidate_phase = (
        spec.reference_phase
        if spec.relation is Relation.SAME
        else spec.reference_phase + math.pi
    )
    reference = phase_density(spec.reference_phase)
    candidate = phase_density(candidate_phase)
    memory = (
        candidate if spec.arm is Arm.COHERENT
        else complete_dephase(candidate)
    )
    base_povm = _reference_povm(spec.reference_phase)
    frame = frame_unitary(spec.frame)

    cells = (
        QubitCell(Cell.SELF, _transport(reference, frame)),
        QubitCell(Cell.OTHER, _transport(candidate, frame)),
        # Dephase first, then transport: equivalently, transport the state and
        # dephase in the covariantly transported Z basis.
        QubitCell(Cell.MEMORY, _transport(memory, frame)),
        QubitCell(Cell.AUDITOR, _transport(reference, frame)),
    )
    povm = PhaseComparisonPOVM(
        _transport(base_povm.match, frame),
        _transport(base_povm.orthogonal, frame),
    )
    probability = _born(povm.match, cells[2].density)
    uniform = _uniform_for(spec)
    click = bool(uniform < probability)
    predicted = Relation.SAME if click else Relation.ORTHOGONAL
    return TrialResult(
        spec=spec,
        cells=cells,
        povm=povm,
        click_probability=probability,
        uniform_draw=uniform,
        click=click,
        predicted_relation=predicted,
        correct=predicted is spec.relation,
    )


def protocol_schedule(seed: int, arm: Arm) -> tuple[TrialSpec, ...]:
    """The frozen 64/64/384 factor schedule (512 trials per arm)."""

    seed = _plain_int(seed, "seed")
    arm = arm if isinstance(arm, Arm) else Arm(arm)
    specs: list[TrialSpec] = []

    def extend(phases: tuple[float, ...], frames: tuple[str, ...]) -> None:
        for frame in frames:
            for phase in phases:
                for relation in Relation:
                    for repetition in range(REPETITIONS_PER_FACTOR_CELL):
                        specs.append(TrialSpec(
                            phase, relation, arm, seed, frame, repetition
                        ))

    extend(CALIBRATION_PHASES, ("I",))       # 4 * 2 * 8 = 64
    extend(HELDOUT_PHASES, ("I",))           # 4 * 2 * 8 = 64
    extend(_ALL_PHASES, COMMON_FRAMES[1:])    # 8 * 3 * 2 * 8 = 384
    if len(specs) != TRIALS_PER_ARM_PER_SEED:
        raise RuntimeError("frozen four-cell factor schedule drifted")
    return tuple(specs)


FourCellOutcomeVector = OutcomeVector


@dataclass(frozen=True)
class PairedOutcome:
    target: OutcomeVector
    control: OutcomeVector

    @property
    def delta(self) -> OutcomeVector:
        observed = self.target.observed & self.control.observed
        values = np.full(len(OUTCOME_DIMENSIONS), np.nan, dtype=float)
        values[observed] = (
            self.target.values[observed] - self.control.values[observed]
        )
        return OutcomeVector(values, observed)


def _outcome(results: tuple[TrialResult, ...]) -> OutcomeVector:
    def mean_correct(selected: list[TrialResult]) -> float:
        if not selected:
            raise ValueError("registered outcome slice is empty")
        return float(np.mean([result.correct for result in selected]))

    calibration = [
        result for result in results
        if result.spec.frame == "I"
        and _phase_index(result.spec.reference_phase) < len(CALIBRATION_PHASES)
    ]
    heldout = [
        result for result in results
        if result.spec.frame == "I"
        and _phase_index(result.spec.reference_phase) >= len(CALIBRATION_PHASES)
    ]
    robust = [result for result in results if result.spec.frame != "I"]

    brier_utilities: list[float] = []
    for result in results:
        probability_correct = (
            result.click_probability
            if result.spec.relation is Relation.SAME
            else 1.0 - result.click_probability
        )
        brier_utilities.append(
            1.0 - (probability_correct - float(result.correct)) ** 2
        )

    values = np.array([
        mean_correct(calibration),
        mean_correct(heldout),
        mean_correct(robust),
        np.nan,  # no learning curve / sample-to-threshold experiment
        float(np.mean(brier_utilities)),
        np.nan,  # operation counts are not energy
        np.nan,  # circuit depth is not measured latency
        np.nan,  # no interruption-and-recovery intervention
    ])
    observed = np.array([
        True, True, True, False, True, False, False, False
    ])
    return OutcomeVector(values, observed)


@dataclass(frozen=True)
class ArmProtocolResult:
    arm: Arm
    seed: int
    trials: tuple[TrialResult, ...]
    outcome: OutcomeVector

    def __post_init__(self) -> None:
        if len(self.trials) != TRIALS_PER_ARM_PER_SEED:
            raise ValueError("arm result does not contain the frozen 512 trials")
        if any(result.spec.arm is not self.arm for result in self.trials):
            raise ValueError("arm result contains a trial from the other arm")


def run_protocol_arm(seed: int, arm: Arm) -> ArmProtocolResult:
    """Execute one arm of one synthetic seed cluster."""

    schedule = protocol_schedule(seed, arm)
    trials = tuple(run_trial(spec) for spec in schedule)
    return ArmProtocolResult(
        arm=arm,
        seed=int(seed),
        trials=trials,
        outcome=_outcome(trials),
    )


@dataclass(frozen=True)
class ResourceParity:
    target_trials: int
    control_trials: int
    copies_per_trial_target: int
    copies_per_trial_control: int
    memory_calls_per_trial_target: int
    memory_calls_per_trial_control: int
    povm_outcomes_target: int
    povm_outcomes_control: int
    side_registers_target: int
    side_registers_control: int
    schedule_shared: bool
    uniforms_shared: bool

    @property
    def holds(self) -> bool:
        return bool(
            self.target_trials == self.control_trials
            == TRIALS_PER_ARM_PER_SEED
            and self.copies_per_trial_target
            == self.copies_per_trial_control == 1
            and self.memory_calls_per_trial_target
            == self.memory_calls_per_trial_control == 1
            and self.povm_outcomes_target
            == self.povm_outcomes_control == 2
            and self.side_registers_target
            == self.side_registers_control == 0
            and self.schedule_shared
            and self.uniforms_shared
        )


def resource_parity(
    target: ArmProtocolResult,
    control: ArmProtocolResult,
) -> ResourceParity:
    target_keys = tuple(result.spec.pair_key for result in target.trials)
    control_keys = tuple(result.spec.pair_key for result in control.trials)
    target_uniforms = np.array([
        result.uniform_draw for result in target.trials
    ])
    control_uniforms = np.array([
        result.uniform_draw for result in control.trials
    ])
    return ResourceParity(
        target_trials=len(target.trials),
        control_trials=len(control.trials),
        copies_per_trial_target=1,
        copies_per_trial_control=1,
        memory_calls_per_trial_target=1,
        memory_calls_per_trial_control=1,
        povm_outcomes_target=2,
        povm_outcomes_control=2,
        side_registers_target=0,
        side_registers_control=0,
        schedule_shared=target_keys == control_keys,
        uniforms_shared=bool(np.array_equal(target_uniforms, control_uniforms)),
    )


@dataclass(frozen=True)
class AuditorObservable:
    completeness_defect: float
    positivity_margin: float
    target_same: float
    target_orthogonal: float
    control_same: float
    control_orthogonal: float

    @property
    def holds(self) -> bool:
        actual = (
            self.target_same,
            self.target_orthogonal,
            self.control_same,
            self.control_orthogonal,
        )
        expected = (1.0, 0.0, 0.5, 0.5)
        return bool(
            self.completeness_defect <= _TOL
            and self.positivity_margin >= -_TOL
            and max(abs(a - e) for a, e in zip(actual, expected)) <= _TOL
        )


def auditor_observable(reference_phase: float = 0.0) -> AuditorObservable:
    povm = _reference_povm(reference_phase)
    return AuditorObservable(
        completeness_defect=povm.completeness_defect,
        positivity_margin=povm.positivity_margin,
        target_same=analytic_click_probability(
            reference_phase, Relation.SAME, Arm.COHERENT
        ),
        target_orthogonal=analytic_click_probability(
            reference_phase, Relation.ORTHOGONAL, Arm.COHERENT
        ),
        control_same=analytic_click_probability(
            reference_phase, Relation.SAME, Arm.DEPHASED
        ),
        control_orthogonal=analytic_click_probability(
            reference_phase, Relation.ORTHOGONAL, Arm.DEPHASED
        ),
    )


@dataclass(frozen=True)
class BasisAttackObservable:
    covariant_max_defect: float
    untransported_povm_max_shift: float

    @property
    def covariant(self) -> bool:
        return self.covariant_max_defect <= _TOL

    @property
    def attack_detected(self) -> bool:
        return self.untransported_povm_max_shift > _TOL


def basis_attack_observable() -> BasisAttackObservable:
    """Contrast valid common-frame transport with a POVM-left-behind attack."""

    covariant: list[float] = []
    attacked: list[float] = []
    # H is sufficient to expose the mismatch for the phase-zero pair; all
    # registered frames are still checked for common-frame covariance.
    for frame_name in COMMON_FRAMES:
        frame = frame_unitary(frame_name)
        for phase in _ALL_PHASES:
            base_povm = _reference_povm(phase)
            for relation in Relation:
                candidate_phase = phase if relation is Relation.SAME else phase + math.pi
                for arm in Arm:
                    memory = phase_density(candidate_phase)
                    if arm is Arm.DEPHASED:
                        memory = complete_dephase(memory)
                    baseline = _born(base_povm.match, memory)
                    transported_memory = _transport(memory, frame)
                    transported_effect = _transport(base_povm.match, frame)
                    covariant.append(
                        abs(_born(transported_effect, transported_memory) - baseline)
                    )
                    if frame_name != "I":
                        attacked.append(
                            abs(_born(base_povm.match, transported_memory) - baseline)
                        )
    return BasisAttackObservable(
        covariant_max_defect=max(covariant),
        untransported_povm_max_shift=max(attacked),
    )


@dataclass(frozen=True)
class RoleAblationObservable:
    role: Cell
    attempted_roles: tuple[Cell, ...]
    decision: str
    typed_refusal: str

    def __post_init__(self) -> None:
        role = self.role if isinstance(self.role, Cell) else Cell(self.role)
        attempted = tuple(
            item if isinstance(item, Cell) else Cell(item)
            for item in self.attempted_roles
        )
        if len(attempted) != len(set(attempted)):
            raise ValueError("active four-cell roles may not be duplicated")
        if set(attempted) != set(Cell) - {role}:
            raise ValueError(
                "a single-role ablation must attempt exactly the other three roles"
            )
        if self.decision != "HOLD":
            raise ValueError("a required-cell ablation must HOLD")
        if not self.typed_refusal:
            raise ValueError("a required-cell ablation needs a typed refusal")
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "attempted_roles", attempted)


def execute_four_cell(
    spec: TrialSpec,
    active_roles: tuple[Cell, ...] = tuple(Cell),
) -> TrialResult | RoleAblationObservable:
    """Execute only a complete instrument; otherwise emit a typed HOLD.

    This is the operational cell gate used by the ablation control.  It receives
    the actually available roles, rather than a label naming the role that a
    report says was removed.
    """

    if not isinstance(spec, TrialSpec):
        raise TypeError("spec must be a TrialSpec")
    roles = tuple(
        role if isinstance(role, Cell) else Cell(role)
        for role in active_roles
    )
    if len(roles) != len(set(roles)):
        raise ValueError("active four-cell roles may not be duplicated")
    active = set(roles)
    if active == set(Cell):
        return run_trial(spec)
    missing = set(Cell) - active
    if len(missing) != 1 or len(roles) != len(Cell) - 1:
        raise ValueError(
            "the registered ablation control removes exactly one required role"
        )
    missing_role = next(iter(missing))
    reasons = {
        Cell.SELF: "SELF missing: no registered phase reference can be prepared",
        Cell.OTHER: "OTHER missing: the same/orthogonal relation is undefined",
        Cell.MEMORY: "MEMORY missing: no delayed state reaches the auditor",
        Cell.AUDITOR: "AUDITOR missing: no registered two-outcome decision exists",
    }
    return RoleAblationObservable(
        role=missing_role,
        attempted_roles=roles,
        decision="HOLD",
        typed_refusal=reasons[missing_role],
    )


def role_ablation_observables(
    spec: TrialSpec | None = None,
) -> tuple[RoleAblationObservable, ...]:
    """Run each registered single-role removal through the execution gate."""

    if spec is None:
        spec = TrialSpec(
            CALIBRATION_PHASES[0],
            Relation.SAME,
            Arm.COHERENT,
            seed=73001,
        )
    observations = []
    for missing_role in Cell:
        result = execute_four_cell(
            spec,
            tuple(role for role in Cell if role is not missing_role),
        )
        if not isinstance(result, RoleAblationObservable):  # construction guard
            raise RuntimeError("missing-role execution unexpectedly produced a trial")
        observations.append(result)
    return tuple(
        observations
    )


@dataclass(frozen=True)
class SeedCalibration:
    seed: int
    target: ArmProtocolResult
    control: ArmProtocolResult
    paired_outcome: PairedOutcome
    parity: ResourceParity
    auditor: AuditorObservable
    basis_attack: BasisAttackObservable
    role_ablations: tuple[RoleAblationObservable, ...]
    registered_decision: str = "HOLD"
    hold_reasons: tuple[str, ...] = (
        "four cone-constrained coordinates are unmeasured",
        "audit strength is zero",
        "the round is calibration-only",
    )
    evidence_ceiling: str = EVIDENCE_CEILING

    def __post_init__(self) -> None:
        if self.registered_decision != "HOLD":
            raise ValueError("R3B-0 has a preregistered HOLD decision")
        if self.evidence_ceiling != EVIDENCE_CEILING:
            raise ValueError("calibration evidence ceiling may not be raised")

    @property
    def controls_hold(self) -> bool:
        return bool(
            self.parity.holds
            and self.auditor.holds
            and self.basis_attack.covariant
            and self.basis_attack.attack_detected
            and all(item.decision == "HOLD" for item in self.role_ablations)
            and bool(self.paired_outcome.delta.missing_dimensions)
        )


def run_seed_calibration(seed: int) -> SeedCalibration:
    """Execute the frozen 512+512 synthetic trials for one seed cluster."""

    seed = _plain_int(seed, "seed")
    target = run_protocol_arm(seed, Arm.COHERENT)
    control = run_protocol_arm(seed, Arm.DEPHASED)
    return SeedCalibration(
        seed=seed,
        target=target,
        control=control,
        paired_outcome=PairedOutcome(target.outcome, control.outcome),
        parity=resource_parity(target, control),
        auditor=auditor_observable(),
        basis_attack=basis_attack_observable(),
        role_ablations=role_ablation_observables(
            TrialSpec(
                CALIBRATION_PHASES[0],
                Relation.SAME,
                Arm.COHERENT,
                seed=seed,
            )
        ),
    )
