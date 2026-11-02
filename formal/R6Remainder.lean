import R6Frames

/-!
# Signed R6 transport remainders

This is a scoped squared-Euclidean-norm diagnostic on real pairs.
It measures neither physical energy nor information-theoretic cost.
Retain expansion and contraction separately; a net-zero closed route
may conceal non-isometric intermediate steps. Frame invariance requires
genuinely orthogonal input/output coordinate transformations.
-/

namespace AionFormal.R6

/-- At an actual input, record output squared norm minus input squared norm. -/
def normChange (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) : ℝ :=
  sqNorm (T v) - sqNorm v

noncomputable def expansionPart (T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) : ℝ := max (normChange T v) 0

noncomputable def contractionPart (T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) : ℝ := max (-normChange T v) 0

/-- A signed defect is expansion minus contraction, never their sum. -/
theorem normChange_split (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) :
    normChange T v = expansionPart T v - contractionPart T v := by
  dsimp [expansionPart, contractionPart]
  rcases le_total 0 (normChange T v) with h | h
  · rw [max_eq_left h, max_eq_right (by linarith)]
    ring
  · rw [max_eq_right h, max_eq_left (by linarith)]
    ring

theorem expansionPart_nonneg (T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) : 0 ≤ expansionPart T v := by
  unfold expansionPart
  exact le_max_right _ _

theorem contractionPart_nonneg (T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) : 0 ≤ contractionPart T v := by
  unfold contractionPart
  exact le_max_right _ _

/-- Both signs cannot be strictly positive for this one scalar instrument. -/
theorem one_signed_part_is_zero (T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) :
    expansionPart T v = 0 ∨ contractionPart T v = 0 := by
  rcases le_total 0 (normChange T v) with h | h
  · right
    unfold contractionPart
    exact max_eq_right (by linarith)
  · left
    unfold expansionPart
    exact max_eq_right h

/-- A typed observation: before, after, gain, loss, and a balance witness.
These are not semantically or physically complete transport invariants. -/
structure SignedNormRemainder where
  beforeSqNorm : ℝ
  afterSqNorm : ℝ
  expansion : ℝ
  contraction : ℝ
  expansion_nonneg : 0 ≤ expansion
  contraction_nonneg : 0 ≤ contraction
  balance : afterSqNorm - beforeSqNorm = expansion - contraction

noncomputable def signedNormRemainder
    (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) :
    SignedNormRemainder where
  beforeSqNorm := sqNorm v
  afterSqNorm := sqNorm (T v)
  expansion := expansionPart T v
  contraction := contractionPart T v
  expansion_nonneg := expansionPart_nonneg T v
  contraction_nonneg := contractionPart_nonneg T v
  balance := by
    change normChange T v = expansionPart T v - contractionPart T v
    exact normChange_split T v

/-- Exact composition law, using the actual intermediate transported state. -/
theorem normChange_comp (S T : (ℝ × ℝ) → (ℝ × ℝ))
    (v : ℝ × ℝ) :
    normChange (S ∘ T) v =
      normChange T v + normChange S (T v) := by
  unfold normChange
  simp only [Function.comp_apply]
  ring

/-- An exact inverse closes the net defect, regardless of intermediate cost. -/
theorem normChange_zero_of_roundtrip (S T : (ℝ × ℝ) → (ℝ × ℝ))
    (h : ∀ v : ℝ × ℝ, S (T v) = v) (v : ℝ × ℝ) :
    normChange (S ∘ T) v = 0 := by
  simp [normChange, Function.comp_apply, h]

/-- The frame is norm preserving; the transported physical map need not be. -/
theorem normChange_orthogonalFrame (F : OrthogonalFrame)
    (v : ℝ × ℝ) :
    normChange F.linearEquiv v = 0 := by
  unfold normChange
  rw [F.preserves_sqNorm]
  ring

def reframeTransport (F G : OrthogonalFrame)
    (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) : ℝ × ℝ :=
  G.linearEquiv (T (F.linearEquiv.symm v))

/-- Orthogonal input/output re-expression preserves this signed instrument. -/
theorem normChange_reframeTransport (F G : OrthogonalFrame)
    (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) :
    normChange (reframeTransport F G T) (F.linearEquiv v) =
      normChange T v := by
  change sqNorm (G.linearEquiv (T (F.linearEquiv.symm (F.linearEquiv v)))) -
      sqNorm (F.linearEquiv v) = sqNorm (T v) - sqNorm v
  rw [F.linearEquiv.symm_apply_apply, G.preserves_sqNorm, F.preserves_sqNorm]

/-- Both directional readings survive a correctly paired change of frames. -/
theorem signed_parts_reframeTransport (F G : OrthogonalFrame)
    (T : (ℝ × ℝ) → (ℝ × ℝ)) (v : ℝ × ℝ) :
    expansionPart (reframeTransport F G T) (F.linearEquiv v) =
        expansionPart T v ∧
      contractionPart (reframeTransport F G T) (F.linearEquiv v) =
        contractionPart T v := by
  constructor
  · unfold expansionPart
    rw [normChange_reframeTransport]
  · unfold contractionPart
    rw [normChange_reframeTransport]

/-- The chosen normalized Cartan filter cannot increase squared norm. -/
theorem normChange_filter_nonpos (ρ : ℝ) (hρ : 0 ≤ ρ)
    (v : ℝ × ℝ) :
    normChange (filter ρ) v ≤ 0 := by
  have hco : 0 ≤ 1 - (contraction ρ) ^ 2 :=
    sub_nonneg.mpr (contraction_sq_le_one ρ hρ)
  have hp : 0 ≤ (1 - (contraction ρ) ^ 2) * v.2 ^ 2 :=
    mul_nonneg hco (sq_nonneg v.2)
  dsimp [normChange, filter, sqNorm]
  nlinarith

theorem expansionPart_filter_zero (ρ : ℝ) (hρ : 0 ≤ ρ)
    (v : ℝ × ℝ) :
    expansionPart (filter ρ) v = 0 := by
  unfold expansionPart
  exact max_eq_right (normChange_filter_nonpos ρ hρ v)

/-- The non-normalized boost strictly expands the first coordinate axis. -/
theorem boost_expanding_axis_positive (ρ : ℝ) (hρ : 0 < ρ) :
    0 < normChange (boost ρ) (1, 0) := by
  have he : (1 : ℝ) < Real.exp ρ := by
    have hh : Real.exp 0 < Real.exp ρ := (Real.exp_lt_exp).mpr hρ
    simpa using hh
  have hp : 0 < Real.exp ρ := Real.exp_pos ρ
  have hs : 1 < (Real.exp ρ) ^ 2 := by nlinarith
  have hd : 0 < (Real.exp ρ) ^ 2 - 1 := by linarith
  simpa [normChange, boost, sqNorm] using hd

/-- The same boost strictly contracts the other coordinate axis. -/
theorem boost_contracting_axis_negative (ρ : ℝ) (hρ : 0 < ρ) :
    normChange (boost ρ) (0, 1) < 0 := by
  have harg : -ρ < (0 : ℝ) := by linarith
  have he : Real.exp (-ρ) < (1 : ℝ) := by
    have hh : Real.exp (-ρ) < Real.exp 0 := (Real.exp_lt_exp).mpr harg
    simpa using hh
  have hp : 0 < Real.exp (-ρ) := Real.exp_pos (-ρ)
  have hs : (Real.exp (-ρ)) ^ 2 < 1 := by nlinarith
  have hd : (Real.exp (-ρ)) ^ 2 - 1 < 0 := by linarith
  simpa [normChange, boost, sqNorm] using hd

/-- The inverse radial boost closes the loop exactly. -/
theorem boost_reverse_roundtrip (ρ : ℝ) (v : ℝ × ℝ) :
    boost (-ρ) (boost ρ v) = v := by
  have hx : Real.exp (-ρ) * Real.exp ρ = 1 := by
    rw [← Real.exp_add]
    simp
  have hy : Real.exp (-(-ρ)) * Real.exp (-ρ) = 1 := by
    rw [← Real.exp_add]
    simp
  apply Prod.ext
  · change Real.exp (-ρ) * (Real.exp ρ * v.1) = v.1
    rw [← mul_assoc, hx, one_mul]
  · change Real.exp (-(-ρ)) * (Real.exp (-ρ) * v.2) = v.2
    rw [← mul_assoc, hy, one_mul]

/-- Kill the inference "zero net defect means every step is an isometry". -/
theorem closed_boost_loop_hides_local_expansion
    (ρ : ℝ) (hρ : 0 < ρ) :
    normChange (boost (-ρ) ∘ boost ρ) (1, 0) = 0 ∧
      0 < normChange (boost ρ) (1, 0) := by
  constructor
  · exact normChange_zero_of_roundtrip
      (boost (-ρ)) (boost ρ) (boost_reverse_roundtrip ρ) (1, 0)
  · exact boost_expanding_axis_positive ρ hρ

end AionFormal.R6
