import R6Compact

/-!
# R6: a finite real dilation and its state-dependent postselection cost

This file fixes a *particular* encoding of the noncompact 2D Cartan boost
from R6Compact. For radial depth ρ ≥ 0, normalize
diag(exp ρ, exp (-ρ)) by its largest singular value exp ρ, obtaining
Kρ = diag(1, exp (-2ρ)). We construct an explicit norm-preserving real
four-dimensional dilation with Kρ as its zero-ancilla block.

No theorem here says that every possible encoding incurs the same cost, that
the real dilation has been executed on quantum hardware, or that a cognitive
advantage follows. A squared Euclidean norm is a probability only after
interpreting this real map as a block of a normalized quantum isometry and
measuring its ancilla in the specified basis.
-/

namespace AionFormal.R6

/-- The contracting singular value of the operator-norm-normalized boost. -/
noncomputable def contraction (ρ : ℝ) : ℝ :=
  Real.exp (-2 * ρ)

/-- The complementary amplitude required to complete a norm-preserving dilation. -/
noncomputable def leakage (ρ : ℝ) : ℝ :=
  Real.sqrt (1 - (contraction ρ) ^ 2)

/-- Top-left, zero-ancilla block of our explicitly specified dilation. -/
noncomputable def filter (ρ : ℝ) (v : ℝ × ℝ) : ℝ × ℝ :=
  (v.1, contraction ρ * v.2)

/-- A four-dimensional real linear map, expressed as an ordered pair of pairs.

For v = (x,y) and w = (a,b), it sends (v,w) to
((x, k*y+s*b), (-a, s*y-k*b)), where k = exp(-2ρ) and s = sqrt(1-k²).
For nonnegative ρ the resulting real matrix is orthogonal. -/
noncomputable def dilation (ρ : ℝ) (v w : ℝ × ℝ) :
    (ℝ × ℝ) × (ℝ × ℝ) :=
  ((v.1, contraction ρ * v.2 + leakage ρ * w.2),
   (-w.1, leakage ρ * v.2 - contraction ρ * w.2))

/-- The squared Euclidean norm of the system and ancilla together. -/
def combinedSqNorm (v w : ℝ × ℝ) : ℝ :=
  sqNorm v + sqNorm w

theorem contraction_pos (ρ : ℝ) : 0 < contraction ρ := by
  unfold contraction
  exact Real.exp_pos _

theorem contraction_le_one (ρ : ℝ) (hρ : 0 ≤ ρ) :
    contraction ρ ≤ 1 := by
  have harg : -2 * ρ ≤ (0 : ℝ) := by linarith
  have hexp := (Real.exp_le_exp).mpr harg
  simpa [contraction] using hexp

theorem contraction_sq_le_one (ρ : ℝ) (hρ : 0 ≤ ρ) :
    (contraction ρ) ^ 2 ≤ 1 := by
  have hp : 0 ≤ contraction ρ := le_of_lt (contraction_pos ρ)
  have hl : contraction ρ ≤ 1 := contraction_le_one ρ hρ
  have hprod : 0 ≤ contraction ρ * (1 - contraction ρ) :=
    mul_nonneg hp (sub_nonneg.mpr hl)
  nlinarith

theorem leakage_sq_add_contraction_sq (ρ : ℝ) (hρ : 0 ≤ ρ) :
    (leakage ρ) ^ 2 + (contraction ρ) ^ 2 = 1 := by
  have hnonneg : 0 ≤ 1 - (contraction ρ) ^ 2 :=
    sub_nonneg.mpr (contraction_sq_le_one ρ hρ)
  unfold leakage
  rw [Real.sq_sqrt hnonneg]
  ring

/-- The normalized Cartan block is exactly the original boost scaled by
its largest singular value, provided the real radial depth is nonnegative. -/
theorem filter_eq_scaled_boost (ρ : ℝ) (v : ℝ × ℝ) :
    filter ρ v =
      (Real.exp (-ρ) * (boost ρ v).1,
       Real.exp (-ρ) * (boost ρ v).2) := by
  have hcancel : Real.exp (-ρ) * Real.exp ρ = 1 := by
    rw [← Real.exp_add]
    simp
  have hpair : Real.exp (-ρ) * Real.exp (-ρ) = contraction ρ := by
    change Real.exp (-ρ) * Real.exp (-ρ) = Real.exp (-2 * ρ)
    rw [← Real.exp_add]
    congr 1
    ring
  apply Prod.ext
  · change v.1 = Real.exp (-ρ) * (Real.exp ρ * v.1)
    rw [← mul_assoc, hcancel, one_mul]
  · change contraction ρ * v.2 = Real.exp (-ρ) * (Real.exp (-ρ) * v.2)
    rw [← mul_assoc, hpair]

/-- The four-dimensional real dilation preserves total squared norm for
arbitrary system and ancilla inputs, not only for the zero-ancilla case. -/
theorem dilation_preserves_combined_sqNorm (ρ : ℝ) (hρ : 0 ≤ ρ)
    (v w : ℝ × ℝ) :
    combinedSqNorm (dilation ρ v w).1 (dilation ρ v w).2 =
      combinedSqNorm v w := by
  have hsum : (contraction ρ) ^ 2 + (leakage ρ) ^ 2 = 1 := by
    linarith [leakage_sq_add_contraction_sq ρ hρ]
  calc
    combinedSqNorm (dilation ρ v w).1 (dilation ρ v w).2 =
        v.1 ^ 2 + w.1 ^ 2 +
          ((contraction ρ) ^ 2 + (leakage ρ) ^ 2) *
            (v.2 ^ 2 + w.2 ^ 2) := by
              simp only [combinedSqNorm, dilation, sqNorm]
              ring
    _ = combinedSqNorm v w := by
      rw [hsum]
      simp only [combinedSqNorm, sqNorm]
      ring

/-- Conditioning on the empty ancilla retrieves exactly the stated filter. -/
theorem dilation_zero_ancilla_block (ρ : ℝ) (v : ℝ × ℝ) :
    (dilation ρ v (0, 0)).1 = filter ρ v := by
  simp [dilation, filter]

/-- The specified filter has state-dependent acceptance weights bounded by
the contracting squared singular value and by one, for every unit input. -/
theorem filter_weight_bounds (ρ : ℝ) (hρ : 0 ≤ ρ)
    (v : ℝ × ℝ) (hv : sqNorm v = 1) :
    (contraction ρ) ^ 2 ≤ sqNorm (filter ρ v) ∧
      sqNorm (filter ρ v) ≤ 1 := by
  have hco : 0 ≤ 1 - (contraction ρ) ^ 2 :=
    sub_nonneg.mpr (contraction_sq_le_one ρ hρ)
  have hx : 0 ≤ (1 - (contraction ρ) ^ 2) * v.1 ^ 2 :=
    mul_nonneg hco (sq_nonneg v.1)
  have hy : 0 ≤ (1 - (contraction ρ) ^ 2) * v.2 ^ 2 :=
    mul_nonneg hco (sq_nonneg v.2)
  dsimp [sqNorm] at hv
  constructor
  · change (contraction ρ) ^ 2 ≤
        v.1 ^ 2 + (contraction ρ * v.2) ^ 2
    nlinarith [hx]
  · change v.1 ^ 2 + (contraction ρ * v.2) ^ 2 ≤ 1
    nlinarith [hy]

/-- The lower bound is attained on the contracting coordinate axis. -/
theorem filter_contracting_axis_weight (ρ : ℝ) :
    sqNorm (filter ρ (0, 1)) = (contraction ρ) ^ 2 := by
  simp [filter, sqNorm]

/-- The upper bound is attained on the uncontracted coordinate axis. -/
theorem filter_uncontracted_axis_weight (ρ : ℝ) :
    sqNorm (filter ρ (1, 0)) = 1 := by
  simp [filter, sqNorm]

/-- The exact exponentially small weight is e^(-4ρ) for this encoding. -/
theorem contraction_sq_eq_exp (ρ : ℝ) :
    (contraction ρ) ^ 2 = Real.exp (-4 * ρ) := by
  change (Real.exp (-2 * ρ)) ^ 2 = Real.exp (-4 * ρ)
  calc
    (Real.exp (-2 * ρ)) ^ 2 =
        Real.exp (-2 * ρ) * Real.exp (-2 * ρ) := by ring
    _ = Real.exp ((-2 * ρ) + (-2 * ρ)) :=
      (Real.exp_add _ _).symm
    _ = Real.exp (-4 * ρ) := by congr 1; ring

/-- Sharp, analytic acceptance interval for the specified normalized filter. -/
theorem filter_weight_bounds_exp (ρ : ℝ) (hρ : 0 ≤ ρ)
    (v : ℝ × ℝ) (hv : sqNorm v = 1) :
    Real.exp (-4 * ρ) ≤ sqNorm (filter ρ v) ∧
      sqNorm (filter ρ v) ≤ 1 := by
  rw [← contraction_sq_eq_exp]
  exact filter_weight_bounds ρ hρ v hv

/-- Zero depth is the compact, no-loss control for this filter. -/
theorem filter_zero_depth (v : ℝ × ℝ) :
    filter 0 v = v := by
  simp [filter, contraction]

end AionFormal.R6
