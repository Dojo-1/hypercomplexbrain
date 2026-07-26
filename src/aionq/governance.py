"""Executable epistemic governance: the evidence lattice as CI policy.

Imported from the Manifold Research Atlas v0.1 (Vilela, 25 July 2026), which
consolidates Rounds 30-185 and lists under "Epistemic governance" the open
bridge: *institutionalize as executable CI policy*.  This module closes that
bridge for this repository.

Three things come across from the Atlas, and each fixes a real defect here.

**1. The A tier.**  This repository's ledger used P / M / H / S / R.  The Atlas
uses P / **A** / M / H / S / R, where

    A - AXIOMATIZED: the artifact compiles or passes because a bridge is an
        explicit axiom, or because the formalization encodes a *weaker
        surrogate*.  Never describe it as the external claim being proved.

That tier is exactly what was missing.  Several headline numbers here are
verified by a check strictly weaker than the claim they support -- a compiler
portfolio is not circuit equivalence, an asymptotic exponent is not a finite-t
cost -- and calling them M overstated them.  :data:`CLAIMS` retags them.

**2. Typed remainders.**  The Atlas formal queue: *"Give [R] a type every time
it appears: cohomology class, empirical residual, scalar constant, or semantic
remainder.  Prohibit untyped transport between them."*  This repository carried
``Transport.remainder`` as a bare string.  :class:`Remainder` types it and
:meth:`Remainder.transport_to` refuses conversions between kinds.

**3. Preservation, not overwrite.**  The Atlas artifact contract: *"A corrected
object receives a new version, not an overwritten history."*  The self-review in
this repository rewrote docstrings in place, destroying the record of what the
claim used to say.  :class:`Claim` carries ``supersedes`` / ``superseded_by``
and a correction list, and the registry refuses to delete.

The publication gate is the Atlas's: a paper may cite only P, A, M and H objects
with their tags visible; S may appear in motivation; R only in correction
history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "EvidenceTag", "PROMOTION_RULES", "Claim", "Remainder", "RemainderKind",
    "UntypedTransportError", "GovernanceError", "Registry", "CLAIMS", "registry",
]


class GovernanceError(Exception):
    """Raised when a governance rule is violated."""


class UntypedTransportError(GovernanceError):
    """Raised when a remainder is moved between incompatible kinds."""


class EvidenceTag:
    """The Atlas evidence lattice."""

    PROVED = "P"        # kernel-checked / exactly computed, with explicit assumptions
    AXIOMATIZED = "A"   # passes via an explicit axiom or a weaker surrogate check
    MEASURED = "M"      # numerical result with code, seeds, controls, instrument
    HYPOTHESIS = "H"    # bridge or scaling conjecture; needs prereg + kill condition
    SEMANTIC = "S"      # productive metaphor; cannot inherit theorem status
    RETIRED = "R"       # demoted by correction, bug, matched null or stronger control

    ALL = (PROVED, AXIOMATIZED, MEASURED, HYPOTHESIS, SEMANTIC, RETIRED)
    CITABLE = (PROVED, AXIOMATIZED, MEASURED, HYPOTHESIS)


PROMOTION_RULES = {
    EvidenceTag.PROVED: "May be used as a premise, but only with its exact formal statement.",
    EvidenceTag.AXIOMATIZED: "Never describe as the external mathematical claim being proved. "
                             "State the surrogate and the gap it leaves.",
    EvidenceTag.MEASURED: "Report sample size, null, effect and scope.",
    EvidenceTag.HYPOTHESIS: "Requires pre-registration and a kill condition.",
    EvidenceTag.SEMANTIC: "May guide model design; cannot inherit theorem status.",
    EvidenceTag.RETIRED: "Preserve in the ledger; never silently delete.",
}


# --------------------------------------------------------------------------
# Typed remainders
# --------------------------------------------------------------------------

class RemainderKind:
    """The four types [R] is allowed to have.  Transport between them is illegal."""

    COHOMOLOGY = "cohomology_class"
    EMPIRICAL = "empirical_residual"
    SCALAR = "scalar_constant"
    SEMANTIC = "semantic_remainder"

    ALL = (COHOMOLOGY, EMPIRICAL, SCALAR, SEMANTIC)


@dataclass(frozen=True)
class Remainder:
    """A typed [R].

    The Atlas prohibits untyped transport between remainder kinds: an empirical
    residual is not a cohomology class, and neither is a semantic leftover.
    Conflating them is how a measured shortfall silently becomes an obstruction
    theory.
    """

    kind: str
    statement: str
    magnitude: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in RemainderKind.ALL:
            raise GovernanceError(
                f"untyped remainder: {self.kind!r} is not one of {RemainderKind.ALL}")

    def transport_to(self, kind: str) -> "Remainder":
        """Refuse to reinterpret a remainder as a different kind."""
        if kind != self.kind:
            raise UntypedTransportError(
                f"cannot transport a {self.kind} into a {kind}: the Atlas formal "
                "queue prohibits untyped transport between remainder types. "
                "Re-derive it in the target type or keep them separate.")
        return self

    def __str__(self) -> str:  # pragma: no cover - display only
        mag = f" (|R| = {self.magnitude})" if self.magnitude is not None else ""
        return f"[{self.kind}] {self.statement}{mag}"


# --------------------------------------------------------------------------
# Claims
# --------------------------------------------------------------------------

_ID_RE = re.compile(r"^[A-Z]{2,6}-[A-Z0-9]{2,8}-[A-Z0-9_]{2,40}$")


@dataclass
class Claim:
    """One registered artifact, with provenance that survives correction."""

    id: str
    tag: str
    statement: str
    artifact: str = ""              # file / function that carries it
    surrogate: str = ""             # for A: what is actually checked
    assumptions: tuple = ()
    kill_condition: str = ""
    corrections: tuple = ()
    supersedes: str | None = None
    superseded_by: str | None = None
    sample_size: int | None = None      # required for M
    interval: tuple | None = None       # required for M: (lo, hi) at 95%
    null: str = ""                      # required for M: what it is measured against

    def __post_init__(self) -> None:
        if not _ID_RE.match(self.id):
            raise GovernanceError(
                f"bad artifact id {self.id!r}: expected DOMAIN-ROUND-NAME, "
                "e.g. METRIC-R3-QSIM_UPPER")
        if self.tag not in EvidenceTag.ALL:
            raise GovernanceError(f"unknown evidence tag {self.tag!r}")
        if self.tag == EvidenceTag.AXIOMATIZED and not self.surrogate:
            raise GovernanceError(
                f"{self.id}: an A-tagged claim must state the surrogate actually "
                "checked, so the gap to the external claim stays visible")
        if self.tag == EvidenceTag.HYPOTHESIS and not self.kill_condition:
            raise GovernanceError(
                f"{self.id}: an H-tagged claim requires a kill condition")
        if self.tag == EvidenceTag.MEASURED:
            # The Atlas M rule -- "report sample size, null, effect and scope" --
            # was stated here and not enforced, so several claims were point
            # estimates from thin samples with no dispersion.  It is enforced now.
            missing = [f for f, v in (("sample_size", self.sample_size),
                                      ("interval", self.interval),
                                      ("null", self.null)) if not v]
            if missing:
                raise GovernanceError(
                    f"{self.id}: an M-tagged claim must report {', '.join(missing)}. "
                    "A measurement without a sample size, an interval and a stated "
                    "null cannot be checked for significance.")
            if len(self.interval) != 2 or self.interval[0] > self.interval[1]:
                raise GovernanceError(f"{self.id}: malformed interval {self.interval}")

    @property
    def citable(self) -> bool:
        return self.tag in EvidenceTag.CITABLE

    def __str__(self) -> str:  # pragma: no cover - display only
        s = f"[{self.tag}] {self.id}: {self.statement}"
        if self.surrogate:
            s += f"\n      surrogate: {self.surrogate}"
        if self.kill_condition:
            s += f"\n      kill: {self.kill_condition}"
        return s


class Registry:
    """Holds claims and enforces the promotion and publication rules."""

    def __init__(self, claims=()) -> None:
        self._claims: dict[str, Claim] = {}
        for c in claims:
            self.add(c)

    def add(self, claim: Claim) -> Claim:
        if claim.id in self._claims:
            raise GovernanceError(f"duplicate artifact id {claim.id}")
        self._claims[claim.id] = claim
        return claim

    def __getitem__(self, cid: str) -> Claim:
        return self._claims[cid]

    def __len__(self) -> int:
        return len(self._claims)

    def by_tag(self, tag: str) -> list:
        return [c for c in self._claims.values() if c.tag == tag]

    def supersede(self, old_id: str, new: Claim) -> Claim:
        """Correct a claim by adding a new version. History is never deleted."""
        old = self._claims[old_id]
        if old.superseded_by:
            raise GovernanceError(f"{old_id} is already superseded by {old.superseded_by}")
        new.supersedes = old_id
        self.add(new)
        old.superseded_by = new.id
        return new

    def cite(self, cid: str, section: str = "results") -> Claim:
        """The Atlas publication gate.

        Results may cite only P, A, M, H with tags visible.  S belongs in
        motivation or design.  R belongs only in correction history.
        """
        c = self._claims[cid]
        if section == "correction_history":
            return c
        if c.tag == EvidenceTag.RETIRED:
            raise GovernanceError(
                f"{cid} is RETIRED and may appear only in correction history")
        if c.tag == EvidenceTag.SEMANTIC and section not in ("motivation", "design"):
            raise GovernanceError(
                f"{cid} is SEMANTIC and may appear only in motivation or design, "
                f"not in {section}")
        if not c.citable and c.tag != EvidenceTag.SEMANTIC:
            raise GovernanceError(f"{cid} is not citable in {section}")
        return c

    def audit(self) -> dict:
        """Summary for CI."""
        counts = {t: len(self.by_tag(t)) for t in EvidenceTag.ALL}
        return {
            "total": len(self),
            "counts": counts,
            "superseded": [c.id for c in self._claims.values() if c.superseded_by],
            "untestable_hypotheses": [c.id for c in self.by_tag(EvidenceTag.HYPOTHESIS)
                                      if not c.kill_condition],
        }


# --------------------------------------------------------------------------
# This repository's claims, retagged honestly against the Atlas lattice
# --------------------------------------------------------------------------

CLAIMS = [
    # --- P: exactly computed or two-line proofs -----------------------------
    Claim("MATH-R1-GRAM_PSD", EvidenceTag.PROVED,
          "G_rs = Tr(rho H_r^dag H_s) is Hermitian PSD; rank = holonomy span dimension.",
          artifact="aionq.identity.analyse_identity",
          assumptions=("rho is a density operator", "H_r are bounded operators")),
    Claim("MATH-R1-FUSION_COHERENCE", EvidenceTag.PROVED,
          "Fibonacci F/R data satisfy pentagon and hexagon; associator is nonzero.",
          artifact="aionq.fusion.verify_coherence",
          assumptions=("canonical Fibonacci category",)),
    Claim("MATH-R1-TSTATE_MAGIC", EvidenceTag.PROVED,
          "Single T-state stabilizer Renyi magic M2 = log2(4/3), computed exactly.",
          artifact="aionq.residency.stabilizer_renyi_entropy"),
    Claim("MATH-R2-FRAME_ENTANGLEMENT", EvidenceTag.PROVED,
          "Entanglement is frame-relative: 0 bits in A's frame, 1 bit in B's.",
          artifact="aionq.qrf.compare_frames"),
    Claim("MATH-R2-SYNDROME_NONDISTURBING", EvidenceTag.PROVED,
          "Stabilizer syndrome extraction yields 2 bits at logical fidelity exactly 1.",
          artifact="aionq.selfknowledge.syndrome_extraction_disturbance",
          assumptions=("3-qubit bit-flip code", "single bit-flip error model")),

    # --- A: passes a surrogate weaker than the claim -------------------------
    Claim("METRIC-R3-QSIM_UPPER", EvidenceTag.AXIOMATIZED,
          "q_sim_upper resists gaming by syntax and cannot be inflated by notation.",
          artifact="aionq.residency.simulation_residency",
          surrogate="a compiler portfolio at optimization levels 0-3, which is "
                    "strictly weaker than circuit equivalence (intractable in "
                    "general). Residual gaming vectors exist and are undetected.",
          assumptions=("Bravyi-Gosset alpha applies at finite t",
                       "Ross-Selinger slope 3 log2(1/eps) is exact")),
    Claim("METRIC-R3-ALPHA_BG", EvidenceTag.AXIOMATIZED,
          "Simulation cost of a Clifford+t-T core is 2^(0.2284 t).",
          artifact="aionq.residency.ALPHA_BG",
          surrogate="an ASYMPTOTIC stabilizer-rank exponent applied at finite t; "
                    "the finite-t constant is not established here."),
    Claim("BUDGET-R2-BENNETT", EvidenceTag.AXIOMATIZED,
          "The forced breath period follows from Bennett reversible pebbling.",
          artifact="aionq.budget.bennett_time_cost",
          surrogate="an ad-hoc interpolation horizon^(log2(3)/f), not Bennett's "
                    "theorem. The 1.0x-22.2x overheads inherit that status.",
          assumptions=("irreversible_fraction is supplied externally, not derived",)),
    Claim("SELF-R2-TOMOGRAPHY_COST", EvidenceTag.AXIOMATIZED,
          "Self-certifying a 6-qubit identity register needs ~4.1e7 copies.",
          artifact="aionq.selfknowledge.copies_for_self_tomography",
          surrogate="the worst-case d^2/eps^2 bound; true sample complexity is "
                    "rank-dependent and varies with the measurement model."),
    Claim("STACK-R3-HOLONOMY_LOSSY", EvidenceTag.AXIOMATIZED,
          "Section-only transport around a free-theory loop is lossy (defect inf).",
          artifact="aionq.stack.transport_loop",
          surrogate="follows from THIS module's transport rule, which nulls "
                    "base-relative coordinates because no free-conversion map is "
                    "implemented. With a real d_conv the loss would likely be "
                    "partial, not total. The qualitative asymmetry survives; the "
                    "infinity does not."),

    # --- M: measured with code, seeds and controls ---------------------------
    Claim("EXP-R1-QNAIVE_CONSTANT", EvidenceTag.MEASURED,
          "Q_naive is constant at 1.0000 (min = max) over random all-unitary cores.",
          artifact="experiments/acaf_sweep.py",
          sample_size=150, interval=(1.0, 1.0),
          null="a metric with discriminating power would show min < max",
          assumptions=("generator emits only H/S/T/CX",
                       "no measurements, resets or classical control sampled")),
    Claim("EXP-R1-COHERENTIZATION_GAIN", EvidenceTag.MEASURED,
          "Coherentization delivers +0.019 against an advertised +0.36, and raises "
          "T-count 3 -> 5.",
          artifact="aionq.coherentize.coherentization_audit",
          sample_size=1, interval=(0.0190, 0.0190),
          null="the advertised gain of +0.3636 under the draft metric",
          assumptions=("single deterministic circuit; exact, not sampled",)),
    Claim("EXP-R3-REAL_BASE_NOT_TREELIKE", EvidenceTag.MEASURED,
          "The live free-theory structure has Gromov delta/diameter = 0.5, the "
          "maximum possible for any metric space.",
          artifact="aionq.atlas.compare_embeddings_on_real_hierarchy",
          sample_size=5, interval=(0.5, 0.5),
          null="a tree metric would give delta/diameter = 0",
          assumptions=("exhaustive over all quadruples of the 5-node graph; "
                       "exact, not sampled",)),
    Claim("EXP-R2-PROCESS_MEMORY", EvidenceTag.MEASURED,
          "Temporal-correlation witness rises 0.000 -> 2.000 bits with coupling.",
          artifact="aionq.process.temporal_correlation_witness",
          sample_size=6, interval=(0.0, 2.0),
          null="a Markovian process would give N = 0 at every coupling",
          assumptions=("deterministic two-step toy construction; exact per point",)),

    Claim("EXP-V1-GHZ_HIDES_ONE_BIT", EvidenceTag.MEASURED,
          "GHZ_n hides exactly one stabilizer generator from every probe of depth "
          "r < n: g_r = 1/n exactly for 1 < r < n, verified n = 3..9.",
          artifact="experiments/run_visibility.py",
          sample_size=7, interval=(1.0, 1.0),
          null="g_r would vary with r if the hidden structure were not a single "
               "generator; ratio g_r/(1/n) tested against 1",
          assumptions=("stabilizer states only", "exact rank computation, not sampled")),
    Claim("EXP-V3-SPLIT_FORM_SHARED", EvidenceTag.PROVED,
          "The real (2,2) form and the F_2 stabilizer phase space are both SPLIT: "
          "Q = x0^2+x1^2-x2^2-x3^2 becomes uv+st (two hyperbolic planes), and "
          "F_2^{2n} with the symplectic form is n hyperbolic planes, one per qubit.",
          artifact="aionq.splitform.real_split_planes, aionq.splitform.symplectic_basis",
          assumptions=("exact change of basis; verified numerically",)),
    Claim("EXP-V3-DISTANCE_COMPUTED", EvidenceTag.MEASURED,
          "Stabilizer distance computed from logical cosets: Steane 3, [[5,1,3]] 3, "
          "[[4,2,2]] 2, and the n-qubit bit-flip repetition code 1 for every n.",
          artifact="aionq.splitform.code_distance",
          sample_size=7, interval=(1.0, 3.0),
          null="the distances asserted by each code's conventional name",
          assumptions=("exhaustive over logical x stabilizer cosets; exact")),

    Claim("EXP-V1-RSTAR_IS_NOT_DISTANCE", EvidenceTag.MEASURED,
          "Visibility depth r* is the minimum generating weight of the stabilizer "
          "group, NOT the code distance: Steane [[7,1,3]] has r* = 4 while d = 3.",
          artifact="experiments/run_visibility.py",
          sample_size=1, interval=(4.0, 4.0),
          null="r* = d = 3 under the naive reading",
          assumptions=("generators supplied explicitly and checked to commute",
                       "exact GF(2) rank; a single code, not a sampled family")),
    Claim("EXP-V1-CD_LADDER_PARTIAL", EvidenceTag.MEASURED,
          "Replication of the Atlas Cayley-Dickson ladder: S16 basis-triple mean "
          "1.3538 vs reported 1.356; O gives 1.6000 vs reported 0.359 under the "
          "same convention. Associativity boundary and zero-divisor onset replicate "
          "exactly.",
          artifact="experiments/run_replication.py",
          sample_size=2730, interval=(1.3187, 1.3883),
          null="the Atlas reported values 0.359 / 1.356 / 1.4",
          assumptions=("basis-triple convention, exhaustive over ordered triples "
                       "of distinct imaginary units at dim 8 and 16",
                       "dim 32 subsampled at n=40,000: 1.1815 [1.1719, 1.1912], "
                       "which does NOT contain the reported 1.4",
                       "random-unit convention gives 1.0929 / 1.3123 / 1.3777, "
                       "missing all three reported values")),

    # --- H: bridges with kill conditions -------------------------------------
    Claim("EXP-V2-CONTROL_SLOPE", EvidenceTag.MEASURED,
          "Random-Clifford visibility depth grows with width at slope 0.3200, far "
          "below the 1:1 tracking that would make the repetition r* = n result "
          "uninformative.",
          artifact="experiments/run_replication.py",
          sample_size=1400, interval=(0.3059, 0.3341),
          null="slope >= 0.8 would mean the control tracks n and the signature is "
               "not diagnostic; slope = 0 would mean r* is width-independent",
          assumptions=("200 seeds per width, widths 3..9",
                       "bootstrap resampled within width groups, 5000 resamples")),
    Claim("EXP-V2-REPETITION_EFFECT", EvidenceTag.MEASURED,
          "At n = 9 the repetition family exceeds the random-Clifford control by "
          "4.915 in r*, Cohen's d = 22.2.",
          artifact="experiments/run_replication.py",
          sample_size=400, interval=(4.8700, 4.9550),
          null="zero difference between designed and undesigned stabilizer states",
          assumptions=("200 per group at n=9", "4000 bootstrap resamples")),

    Claim("EXP-S1-SENTINEL_KILLED", EvidenceTag.MEASURED,
          "The Sigma-infinity Transcendence Sentinel is beaten by a gzip MDL proxy "
          "on the thesis's own four-class generator family: mean AUROC 0.865 vs "
          "1.000 for compression and 0.754 for change-point.",
          artifact="experiments/run_sentinel.py",
          sample_size=480, interval=(0.52, 1.00),
          null="the thesis's pre-registered kill condition: conventional "
               "change-point or compression matching the sentinel at equal cost",
          assumptions=("120 streams per class, length 600",
                       "all three methods share the same recurrence filter and "
                       "residual preprocessing",
                       "polarity not pre-registered, so each method is scored with "
                       "its best direction -- the reading most favourable to the "
                       "baselines")),

    Claim("EXP-S2-STOKES_CONDITIONAL", EvidenceTag.MEASURED,
          "The Stokes router matches a refitting gated mixture ZERO-SHOT where the "
          "latent basis truly mutates (delta +0.0004, not significant, 6 params vs "
          "14), and fails completely in the weights-only control (delta +5.777, "
          "d = 1.88). The conditional pattern of thesis section 12 holds.",
          artifact="experiments/run_stokes.py",
          sample_size=120, interval=(-0.0060, 0.0065),
          null="the thesis kill condition: a standard gated mixture matching all "
               "metrics; and the control regime where no basis change occurs",
          assumptions=("60 trials per regime, latent dim 3, observed dim 6",
                       "router is zero-shot: fitted on regime 1 only, carried "
                       "across by the declared mutation; the mixture refits on "
                       "regime-2 labels",
                       "the mutation matrix is SUPPLIED, not learned -- the router "
                       "is told where the crossing is and what it is",
                       "MSE only: the thesis also predicts an interpretability "
                       "gain, which is NOT tested here")),

    Claim("MATH-S3-CHARACTER_BLIND", EvidenceTag.PROVED,
          "No multiplicative character can detect a commutator obstruction: every "
          "L_q for a unit quaternion q lies in SO(4), whose abelianisation is "
          "trivial, so det(H) = 1 identically on defective and clean cycles alike.",
          artifact="src/aionq/sheaf.py::_instr_character"),
    Claim("MATH-S3-NO_FLAT_ABOVE_H", EvidenceTag.PROVED,
          "A vertex gauge a_ij = g_j g_i^-1 induces a FLAT connection iff left "
          "multiplication is a homomorphism, L_a L_b = L_{ab}, which holds exactly "
          "through Cayley-Dickson dimension 4. From dimension 8 the clean sheaf "
          "already carries holonomy on every cycle, so 'no obstruction' is not "
          "definable and octonionic sheaf cohomology is ill-posed, not merely "
          "unhelpful. Unit octonions form a Moufang loop, not a group.",
          artifact="src/aionq/sheaf.py::flatness_ladder"),
    Claim("MATH-S3-BV_QUERY_SEPARATION", EvidenceTag.PROVED,
          "In the holonomy-oracle model a cycle obstruction class costs exactly b "
          "= E - V + C classical queries and exactly 1 quantum query. Lower bound: "
          "one bit per query against b bits of class. Upper: a cycle basis, and "
          "Bernstein-Vazirani.",
          artifact="src/aionq/interference.py::classical_query_cost",
          assumptions=("the oracle is already coherent; building it from classical "
                       "worldlet data costs E accesses, which exceeds b on every "
                       "instance tested (see BRIDGE-S3-COHERENT_ORACLE)",
                       "recovering the CLASS is not localising the DEFECT: the "
                       "lightest cochain in the coset is syndrome decoding, "
                       "NP-hard in general and identical for both parties")),

    Claim("EXP-S3-SHEAF_LOCALISATION", EvidenceTag.MEASURED,
          "Sheaf holonomy localises hidden cycle obstructions better than "
          "dimension- and compute-matched controls: AUROC 0.797 vs 0.511 for "
          "shuffled overlaps and 0.508 for topology-only, at identical nerve, "
          "cycle basis and attribution rule.",
          artifact="experiments/run_sheaf.py",
          sample_size=300, interval=(0.2583, 0.3158),
          null="the thesis kill condition (section 16, experiment 1): any "
               "advantage disappears under dimension- and compute-matched controls",
          assumptions=("8 worldlets, 13 overlaps, 2 hidden defects, fiber "
                       "dimension 4, 300 trials",
                       "the defect replaces a transition with another drawn from "
                       "the same distribution, so no overlap is locally anomalous",
                       "every instrument shares the blame-spreading attribution "
                       "rule; only the coordinate system differs")),
    Claim("EXP-S3-BV_NOISE_CROSSOVER", EvidenceTag.MEASURED,
          "The single-query advantage survives depolarizing noise up to 0.17 per "
          "qubit per layer at cycle rank 4, falling to 0.105 at rank 12 and 0.090 "
          "at rank 16 -- flat to b = 6 and then decaying, as log(b)/b requires.",
          artifact="src/aionq/interference.py::crossover_noise",
          sample_size=500, interval=(0.090, 0.170),
          null="the classical learner's b queries, paid up front with certainty",
          assumptions=("Pauli-twirled depolarizing on every qubit after each of "
                       "three circuit layers; Monte Carlo, so sampled outcomes "
                       "are exact",
                       "1/p_success assumes a correct run can be recognised for "
                       "free, which it cannot -- so this OVERSTATES the quantum "
                       "side and the crossover is an upper bound",
                       "b = 16 comes from an independent-seed replication run "
                       "separately (17 qubits, ~10 min per point); reproduce with "
                       "run_sheaf.py --deep --seed 1")),

    Claim("BRIDGE-S3-COHERENT_ORACLE", EvidenceTag.HYPOTHESIS,
          "A cognitive architecture could hold its overlap relations in a form "
          "that IS the coherent holonomy oracle, rather than one built from "
          "classical reads -- which is the only way the b-to-1 query separation "
          "is not paid for twice.",
          kill_condition="exhibit no construction in which the oracle's "
                         "preparation cost is below E classical overlap accesses; "
                         "or show the preparation is itself the expensive step in "
                         "any realisable memory"),

    Claim("BRIDGE-R3-QCAUSAL", EvidenceTag.HYPOTHESIS,
          "Some quantum organ shows a causal advantage inside a pre-registered cone.",
          artifact="aionq.advantage.promote",
          kill_condition="Pr(DeltaY in K) < 1-alpha against a matched free-theory "
                         "control at compute, parameter and sampling parity."),
    Claim("BRIDGE-R1-RANK_ROBUSTNESS", EvidenceTag.HYPOTHESIS,
          "Holonomy span dimension predicts identity robustness under drift.",
          artifact="aionq.identity.analyse_identity",
          kill_condition="effective rank and conditioning predict robustness as "
                         "well or better at matched cost."),

    Claim("MODEL-R4-DRONE_CEILING", EvidenceTag.PROVED,
          "An uninterrupted channel can be funded only by steady refill, never by a "
          "finite reservoir: drone_ceiling = refill_rate.",
          artifact="aionq.bordon.BordonBreath.drone_ceiling",
          assumptions=("constant draw", "constant refill", "finite capacity")),
    Claim("MODEL-R4-BORDON", EvidenceTag.HYPOTHESIS,
          "Reservoir respiration (fol/puntero/bordon) models cognitive breathing "
          "better than a single global period.",
          artifact="aionq.bordon",
          kill_condition="a periodic model reproduces drone protection, "
                         "asynchronous per-channel rates and uninterrupted sustain "
                         "at matched parameters."),

    # --- S: scaffolding ------------------------------------------------------
    Claim("SEM-R0-BREATHING", EvidenceTag.SEMANTIC,
          "Inhalation/exhalation as a description of code expansion and entropy export.",
          artifact="aionq.budget"),
    Claim("SEM-R0-REALITY_CELL", EvidenceTag.SEMANTIC,
          "Reality Cell, polycosmos, weave/deweave as design vocabulary.",
          artifact="docs/ARCHITECTURE.md"),

    # --- R: retired, preserved --------------------------------------------
    Claim("RET-V1-RSTAR_EQUALS_D", EvidenceTag.RETIRED,
          "Visibility depth equals code distance.",
          corrections=("Steane [[7,1,3]] gives r* = 4 with d = 3",
                       "Round V3: falsified on the repetition family as well. V1 "
                       "scored that family as 'survived' using d taken from the "
                       "code's NAME. With d computed from the logical cosets the "
                       "bit-flip repetition code has stabilizer distance 1 for "
                       "every n (Z_1 is a weight-1 logical), not n. r* == d now "
                       "holds in 1 of 6 cases and that one is a coincidence.")),
    Claim("RET-V1-REPETITION_DISTANCE_N", EvidenceTag.RETIRED,
          "The n-qubit repetition codeword has stabilizer distance n.",
          corrections=("that is the X-distance convention; the true stabilizer "
                       "distance is 1, verified independently: Z_1 commutes with "
                       "every Z_iZ_j check and is not in the stabilizer group",)),
    Claim("RET-V1-WEIGHT_IS_VISIBILITY", EvidenceTag.RETIRED,
          "Pauli weight above r measures invisibility at probe depth r.",
          corrections=("product state |+>^6 scored g_1 = 0.891 when it must be 0; "
                       "<X1X2> = <X1><X2> is 1-locally determined despite weight 2",)),
    Claim("RET-S2-STOKES_ROUTER_ACCURACY", EvidenceTag.RETIRED,
          "The Stokes-Thimble Router earns its place by beating a gated mixture "
          "on accuracy.",
          corrections=("the thesis kill condition as written is met: the mixture "
                       "matches it on MSE where the basis truly changes",
                       "what survives is narrower and is kept as "
                       "EXP-S2-STOKES_CONDITIONAL -- parity reached zero-shot at "
                       "fewer parameters, plus correct failure in the control",
                       "the mutation matrix is supplied rather than learned, so "
                       "this does not show a system could FIND the crossing")),
    Claim("RET-S3-HYPERCOMPLEX_DIAGNOSIS", EvidenceTag.RETIRED,
          "Hypercomplex coordinates improve obstruction diagnosis on "
          "order-sensitive cases.",
          corrections=("measured against the thesis's own kill condition "
                       "(section 16, experiment 1): quaternionic coordinates TIE "
                       "with the matched real sheaf on their home ground "
                       "(delta +0.000 [-0.018, +0.017]) and LOSE on generic "
                       "transitions (delta -0.231 [-0.257, -0.204])",
                       "the predicted conditional SHAPE does reproduce, and that "
                       "much is kept: they cost nothing where the structure is "
                       "genuinely quaternionic and cost a great deal elsewhere",
                       "'may improve diagnosis' is not supported by a tie; the "
                       "advantage vanishes under matched controls exactly as the "
                       "kill condition anticipated")),
    Claim("RET-S3-OCTONIONIC_SHEAF", EvidenceTag.RETIRED,
          "Octonionic fibers give a sheaf-cohomological obstruction theory that "
          "diagnoses order-sensitive gluing failure.",
          corrections=("not falsified but ILL-POSED, which is stronger: above "
                       "dimension 4 a vertex gauge induces no flat connection, so "
                       "the clean sheaf already has holonomy 3.19 on every cycle "
                       "and there is no zero for a defect to stand out against",
                       "the cause is structural -- unit octonions are a Moufang "
                       "loop, not a group, and H^1 needs a group",
                       "by Artin's theorem any two of them still associate, so the "
                       "failure begins exactly at cycles mixing three independent "
                       "directions; see MATH-S3-NO_FLAT_ABOVE_H")),
    Claim("RET-S1-TRANSCENDENCE_SENTINEL", EvidenceTag.RETIRED,
          "The Hecke-Mahler-inspired sparse expanding-gap sentinel earns a place "
          "in the architecture as a novelty diagnostic.",
          corrections=("retired against the Sigma-infinity thesis's OWN "
                       "pre-registered kill condition (section 16, experiment 3): "
                       "a gzip MDL proxy on the identical residual separates the "
                       "four classes at AUROC 1.000 vs the sentinel's 0.865",
                       "the module and experiment are kept so the negative result "
                       "is reproducible, per the Atlas rule that R is preserved "
                       "and never deleted")),
    Claim("RET-R1-QCAUSAL_ADDITIVE", EvidenceTag.RETIRED,
          "Additive Q_causal over edges measures quantumness.",
          corrections=("constant on all-unitary cores; permutation and Clifford "
                       "cores score 1.00 while classically simulable",)),
    Claim("RET-R2-QCERT_CERTIFICATE", EvidenceTag.RETIRED,
          "Q_cert is the fraction a classical simulator is forced to pay.",
          corrections=("upper bound, not a certificate; renamed q_sim_upper",)),
    Claim("RET-R3-HYPERBOLIC_BASE", EvidenceTag.RETIRED,
          "The free-theory base is hyperbolic and the Poincare ball is its geometry.",
          corrections=("delta/diameter = 0.5 on the live diamond DAG: maximally "
                       "non-tree-like; no geometry assigned",)),
    Claim("RET-R2-SELF_TOMOGRAPHY_IMPOSSIBLE", EvidenceTag.RETIRED,
          "No-cloning makes self-tomography impossible.",
          corrections=("syndrome extraction: 2 bits at logical fidelity 1.0",)),
    Claim("RET-R3-SCALAR_PROMOTION", EvidenceTag.RETIRED,
          "q_causal > 0 is the promotion gate.",
          corrections=("replaced by a pre-registered advantage cone; the scalar "
                       "gate was still the live code path until D14c",)),
    Claim("RET-R1-ENTANGLEMENT_QUANTUMNESS", EvidenceTag.RETIRED,
          "Entanglement measures quantum residency.",
          corrections=("GHZ: 1.0 bit entanglement, zero magic, q_sim_upper 0.0; "
                       "and entanglement is frame-relative",)),
]

registry = Registry(CLAIMS)
