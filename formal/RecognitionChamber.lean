/-
  S4-G100 — Reversible Recognition Chamber: theorem targets.

  Native formalization, now included in the pinned AION Lake build.
  Previously this file had no successful build and its P4 target contained
  an admitted proof. This revision closes that obligation but makes no
  claim of kernel verification until the dedicated Lean CI succeeds.

  Five targets.  P1 and P2 are definitional and are included because a
  formalisation surface that omits its trivial obligations is not a surface.  P3
  is the one whose failure would change a reported number.  P4 is a statement
  strictly inside the constant-rate reservoir model.  P5 is the governance rule
  that the deposit gate already enforces before any numeric threshold is read.
-/

import Mathlib

namespace RecognitionChamber

/-! ## Transport pairs and the round-trip defect -/

/-- A forward map with a declared inverse.  The inverse is *declared*, not
    assumed correct: that is exactly what the defect measures. -/
structure TransportPair (X Y : Type*) where
  forward  : X → Y
  backward : Y → X

variable {X Y : Type*}

/-- `[R]_loop (x; T, D) = D_X (x, T.backward (T.forward x))`.

    A **TransportDefect** and nothing else.  It is not a cohomology class, not a
    semantic incompleteness remainder, and not a scalar obstruction constant.
    The Python side carries this distinction in the type system
    (`aionq.recognition.types.TypedRemainder`); here it is carried by the name. -/
def loopDefect [PseudoMetricSpace X] (T : TransportPair X Y) (x : X) : ℝ :=
  dist x (T.backward (T.forward x))

/-! ## P1 — nonnegativity -/

/-- The defect is nonnegative for any pseudo-metric.  Immediate, and stated so
    that no implementation can return a negative "distance" unchallenged. -/
theorem loopDefect_nonneg [PseudoMetricSpace X] (T : TransportPair X Y) (x : X) :
    0 ≤ loopDefect T x :=
  dist_nonneg

/-! ## P2 — an exact left inverse gives exactly zero -/

/-- Zero, not merely small.  The numerical counterpart returns `0.0` at machine
    precision for identity transport, an exact permutation inverse, and an
    orthogonal gauge round trip. -/
theorem loopDefect_eq_zero_of_leftInverse [PseudoMetricSpace X]
    (T : TransportPair X Y) (x : X) (h : T.backward (T.forward x) = x) :
    loopDefect T x = 0 := by
  unfold loopDefect
  rw [h]
  exact dist_self x

/-- The converse holds only up to the pseudo-metric's own degeneracy: in a
    *pseudo*-metric space a zero defect does not force the round trip to be the
    identity.  Stated because assuming the converse is the likelier error. -/
theorem leftInverse_of_loopDefect_eq_zero_metric
    [MetricSpace X] (T : TransportPair X Y) (x : X) (h : loopDefect T x = 0) :
    T.backward (T.forward x) = x := by
  unfold loopDefect at h
  exact (dist_eq_zero.mp h).symm

/-! ## P3 — gauge invariance under an isometry -/

/-- Conjugation of a transport pair by a bijection of the carrier. -/
def conjugate (T : TransportPair X Y) (g : X → X) (g_inv : X → X) :
    TransportPair X Y where
  forward  := fun z => T.forward (g_inv z)
  backward := fun w => g (T.backward w)

/-- **The target with content.**  If `g` is an isometry with inverse `g_inv`,
    the defect at the transported point is the defect at the original point.

    This is what licenses comparing loop defects measured in different gauges,
    and it is why the chamber's output is bit-identical under an orthogonal
    frame change.

    NOTE the scope.  `g` here is an isometry *of the carrier*.  Relabelling the
    worldlets of a nerve is **not** an instance: it changes the fundamental cycle
    basis, and hence the transport pair itself, rather than conjugating a fixed
    pair.  The measured instability under relabelling is therefore not a
    counterexample to this theorem — and no theorem in this file covers basis
    change.  That is the smallest open bridge S4-G100 leaves behind. -/
theorem loopDefect_conjugate_of_isometry [PseudoMetricSpace X]
    (T : TransportPair X Y) (g g_inv : X → X)
    (hg : ∀ a b : X, dist (g a) (g b) = dist a b)
    (hinv : ∀ a : X, g_inv (g a) = a) (x : X) :
    loopDefect (conjugate T g g_inv) (g x) = loopDefect T x := by
  unfold loopDefect conjugate
  simp only [hinv]
  exact hg x (T.backward (T.forward x))

/-! ## P4 — the reservoir ceiling, inside the constant-rate model -/

/-- Reservoir level after `n` ticks at constant refill `ρ` and constant draw `d`,
    ignoring the cap (the cap only lowers the level, so it cannot rescue a
    deficit). -/
def level (cap ρ d : ℝ) : ℕ → ℝ
  | 0     => cap
  | n + 1 => level cap ρ d n + ρ - d

theorem level_eq (cap ρ d : ℝ) (n : ℕ) :
    level cap ρ d n = cap + n * (ρ - d) := by
  induction n with
  | zero => simp [level]
  | succ k ih => simp [level, ih]; ring

/-- **The drone ceiling.**  If the continuous draw exceeds the refill rate, a
    finite reservoir empties in finite time — for *any* capacity.  Therefore
    indefinite survival of the invariant channel requires `d ≤ ρ`.

    This is a statement about the model, not about respiration, cognition or any
    physical brain.  Its architectural content is only this: an invariant carrier
    must be funded out of steady income, never out of buffer. -/
theorem finite_depletion_of_draw_gt_refill
    (cap ρ d : ℝ) (_hcap : 0 ≤ cap) (h : ρ < d) :
    ∃ n : ℕ, level cap ρ d n ≤ 0 := by
  have hpos : 0 < d - ρ := sub_pos.mpr h
  obtain ⟨n, hn⟩ := exists_nat_gt (cap / (d - ρ))
  refine ⟨n, ?_⟩
  rw [level_eq]
  have hbudget : cap < (n : ℝ) * (d - ρ) := by
    exact (div_lt_iff₀ hpos).mp hn
  nlinarith

/-! ## P5 — no self-promotion -/

/-- A claim, with the nodes that generated it and the nodes authorising it. -/
structure ClaimNode (Node : Type*) where
  generatedBy  : Set Node
  authorizedBy : Set Node

/-- Reachability along a dependency relation. -/
inductive Reaches {Node : Type*} (dep : Node → Node → Prop) : Node → Node → Prop
  | refl  (a : Node) : Reaches dep a a
  | step  {a b c : Node} : Reaches dep a b → dep b c → Reaches dep a c

/-- The dependency closure of a set of nodes. -/
def closure {Node : Type*} (dep : Node → Node → Prop) (S : Set Node) : Set Node :=
  { c | ∃ a ∈ S, Reaches dep a c }

/-- Promotion requires an authorising node outside the generating closure. -/
def MayPromote {Node : Type*} (dep : Node → Node → Prop) (C : ClaimNode Node) : Prop :=
  ∃ w ∈ C.authorizedBy, w ∉ closure dep C.generatedBy

/-- **No self-promotion.**  If every authorising node lies inside the dependency
    closure of the generating nodes, the claim cannot be promoted.

    In S4-G100 the explorer, verifier, formalizer and auditor share code,
    assumptions, data and authoring model, so they collapse to a single node
    under any honest reading of `dep` — which is why every S4 deposit is capped at
    MeasuredPattern and none is called independent verification. -/
theorem not_mayPromote_of_authorized_within_closure
    {Node : Type*} (dep : Node → Node → Prop) (C : ClaimNode Node)
    (h : ∀ w ∈ C.authorizedBy, w ∈ closure dep C.generatedBy) :
    ¬ MayPromote dep C := by
  rintro ⟨w, hw_auth, hw_out⟩
  exact hw_out (h w hw_auth)

end RecognitionChamber
