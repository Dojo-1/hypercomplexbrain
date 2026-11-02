import Mathlib

/-!
# The R6 radial boost: a small exact formalization

This models only the Cartan diagonal stretch in the **real two-dimensional**
source carrier. It does not implement physical quantum dynamics, an arbitrary
SO(2,2) representation, or an operator-norm/postselection bound.

The core claim is that a nonzero real radial stretch cannot preserve the
Euclidean quadratic norm of every vector. Orthogonal pre- and post-rotations
are not included in this file; the full R6 encoding remains a separate target.
-/

namespace AionFormal.R6

/-- Euclidean squared norm in the two-dimensional source carrier. -/
def sqNorm (v : ℝ × ℝ) : ℝ := v.1 ^ 2 + v.2 ^ 2

/-- The diagonal, determinant-one Cartan boost
    `diag(exp ρ, exp (-ρ))`, as its action on a pair. -/
noncomputable def boost (ρ : ℝ) (v : ℝ × ℝ) : ℝ × ℝ :=
  (Real.exp ρ * v.1, Real.exp (-ρ) * v.2)

/-- A positive stretch with squared stretch factor one has zero radial depth. -/
theorem radial_stretch_sq_eq_one_iff_zero (ρ : ℝ) :
    (Real.exp ρ) ^ 2 = 1 ↔ ρ = 0 := by
  constructor
  · intro h
    have hpos : 0 < Real.exp ρ := Real.exp_pos ρ
    have heq : Real.exp ρ = 1 := by nlinarith
    exact Real.exp_injective (by simpa using heq)
  · intro h
    subst ρ
    simp

/-- The R6 diagonal Cartan boost is norm preserving on every real pair
    exactly when its radial coordinate is zero. -/
theorem boost_preserves_sqNorm_iff_zero (ρ : ℝ) :
    (∀ v : ℝ × ℝ, sqNorm (boost ρ v) = sqNorm v) ↔ ρ = 0 := by
  constructor
  · intro hall
    have he1 : (Real.exp ρ) ^ 2 = 1 := by
      simpa [sqNorm, boost] using hall ((1 : ℝ), (0 : ℝ))
    exact (radial_stretch_sq_eq_one_iff_zero ρ).mp he1
  · intro hρ
    subst ρ
    intro v
    simp [boost, sqNorm]

/-- The negative control: a nonzero radial boost fails the norm-preservation
    condition. This is a contrapositive of the precisely scoped theorem. -/
theorem boost_nonzero_not_isometric (ρ : ℝ) (hρ : ρ ≠ 0) :
    ¬ ∀ v : ℝ × ℝ, sqNorm (boost ρ v) = sqNorm v := by
  intro hall
  exact hρ ((boost_preserves_sqNorm_iff_zero ρ).mp hall)

end AionFormal.R6
