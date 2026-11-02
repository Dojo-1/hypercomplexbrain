import R6Dilation

/-!
# Orthogonal frame covariance of the bounded R6 postselection cost

The carrier is R² with its ordinary squared Euclidean norm. A frame is
*explicitly* a real linear equivalence preserving that norm, so merely
changing coordinates is NOT a way to sneak a noncompact Cartan boost into
the cost-free subgroup.

The filter expressed in input frame F and output frame G is
  G ∘ Kρ ∘ F⁻¹,
where Kρ is the fixed normalized Cartan filter from R6Dilation.

The probability is invariant under a *joint* change of coordinates:
the state, input frame, and output frame must all move together.
It is NOT invariant under independently changing a physical input frame
while holding the state fixed.

These are exact real linear-algebra statements, not a full SO(2,2) action,
not an adiabatic theorem, not a claim of a quantum circuit advantage, and
not a statement about non-orthogonal Worldlet transport.
-/

namespace AionFormal.R6

/-- A genuinely linear, bijective, squared-norm-preserving frame in the
real two-dimensional carrier. Arbitrary nonlinear norm-preserving bijections
are deliberately excluded. -/
structure OrthogonalFrame where
  linearEquiv : (ℝ × ℝ) ≃ₗ[ℝ] (ℝ × ℝ)
  preserves_sqNorm : ∀ v : ℝ × ℝ,
    sqNorm (linearEquiv v) = sqNorm v

namespace OrthogonalFrame

/-- The identity is a cost-free frame. -/
def identity : OrthogonalFrame where
  linearEquiv := LinearEquiv.refl ℝ (ℝ × ℝ)
  preserves_sqNorm := by
    intro v
    rfl

/-- An orthogonal frame remains squared-norm preserving in reverse. -/
theorem inverse_preserves_sqNorm (F : OrthogonalFrame) (v : ℝ × ℝ) :
    sqNorm (F.linearEquiv.symm v) = sqNorm v := by
  have h := F.preserves_sqNorm (F.linearEquiv.symm v)
  simpa using h.symm

/-- Composition of orthogonal frames is another admissible frame. -/
def thenFrame (F G : OrthogonalFrame) : OrthogonalFrame where
  linearEquiv := F.linearEquiv.trans G.linearEquiv
  preserves_sqNorm := by
    intro v
    have h : sqNorm (G.linearEquiv (F.linearEquiv v)) =
        sqNorm v := by
      calc
        sqNorm (G.linearEquiv (F.linearEquiv v)) =
            sqNorm (F.linearEquiv v) := G.preserves_sqNorm _
        _ = sqNorm v := F.preserves_sqNorm v
    simpa only [LinearEquiv.trans_apply] using h

end OrthogonalFrame

/-- One *physical* normalized Cartan filter, displayed in distinct input and
output orthogonal frames. The output frame cannot change its acceptance weight. -/
noncomputable def frameFilter (ρ : ℝ) (F G : OrthogonalFrame)
    (v : ℝ × ℝ) : ℝ × ℝ :=
  G.linearEquiv (filter ρ (F.linearEquiv.symm v))

/-- The output-frame transformation leaves the acceptance weight unchanged. -/
theorem frameFilter_sqNorm (ρ : ℝ) (F G : OrthogonalFrame)
    (v : ℝ × ℝ) :
    sqNorm (frameFilter ρ F G v) =
      sqNorm (filter ρ (F.linearEquiv.symm v)) := by
  exact G.preserves_sqNorm _

/-- The input frame pulls the physical state back to Cartan coordinates;
the output is transported forward, without silently changing the norm. -/
theorem frameFilter_pullback (ρ : ℝ) (F G : OrthogonalFrame)
    (v : ℝ × ℝ) :
    frameFilter ρ F G (F.linearEquiv v) =
      G.linearEquiv (filter ρ v) := by
  simp [frameFilter]

/-- The sharp success-probability interval survives arbitrary orthogonal
input and output frames, when the physical input is normalized. -/
theorem frameFilter_weight_bounds_exp (ρ : ℝ) (hρ : 0 ≤ ρ)
    (F G : OrthogonalFrame) (v : ℝ × ℝ) (hv : sqNorm v = 1) :
    Real.exp (-4 * ρ) ≤ sqNorm (frameFilter ρ F G v) ∧
      sqNorm (frameFilter ρ F G v) ≤ 1 := by
  have hunit : sqNorm (F.linearEquiv.symm v) = 1 :=
    (F.inverse_preserves_sqNorm v).trans hv
  simpa only [frameFilter_sqNorm] using
    (filter_weight_bounds_exp ρ hρ (F.linearEquiv.symm v) hunit)

/-- The sharp lower probability is still attained by the *transported*
contracting direction, not generally by a fixed coordinate axis. -/
theorem frameFilter_contracting_axis_weight (ρ : ℝ)
    (F G : OrthogonalFrame) :
    sqNorm (frameFilter ρ F G (F.linearEquiv (0, 1))) =
      Real.exp (-4 * ρ) := by
  calc
    sqNorm (frameFilter ρ F G (F.linearEquiv (0, 1))) =
        sqNorm (G.linearEquiv (filter ρ (0, 1))) :=
      congrArg sqNorm (frameFilter_pullback ρ F G (0, 1))
    _ = sqNorm (filter ρ (0, 1)) := G.preserves_sqNorm _
    _ = (contraction ρ) ^ 2 := filter_contracting_axis_weight ρ
    _ = Real.exp (-4 * ρ) := contraction_sq_eq_exp ρ

/-- The sharp upper probability is attained by the transported uncontracted
direction. -/
theorem frameFilter_uncontracted_axis_weight (ρ : ℝ)
    (F G : OrthogonalFrame) :
    sqNorm (frameFilter ρ F G (F.linearEquiv (1, 0))) = 1 := by
  calc
    sqNorm (frameFilter ρ F G (F.linearEquiv (1, 0))) =
        sqNorm (G.linearEquiv (filter ρ (1, 0))) :=
      congrArg sqNorm (frameFilter_pullback ρ F G (1, 0))
    _ = sqNorm (filter ρ (1, 0)) := G.preserves_sqNorm _
    _ = 1 := filter_uncontracted_axis_weight ρ

/-- A joint ambient orthogonal coordinate change acts covariantly:
changing the physical state and both frames together conjugates the
filtered output, instead of changing its meaning. -/
theorem frameFilter_joint_change (ρ : ℝ) (F G H : OrthogonalFrame)
    (v : ℝ × ℝ) :
    frameFilter ρ (F.thenFrame H) (G.thenFrame H)
        (H.linearEquiv v) =
      H.linearEquiv (frameFilter ρ F G v) := by
  simp [frameFilter, OrthogonalFrame.thenFrame]

/-- Acceptance weight, not merely the expression for the filtered state,
is gauge-invariant under the correctly paired change of frame. -/
theorem frameFilter_joint_change_sqNorm (ρ : ℝ)
    (F G H : OrthogonalFrame) (v : ℝ × ℝ) :
    sqNorm (frameFilter ρ (F.thenFrame H) (G.thenFrame H)
      (H.linearEquiv v)) =
    sqNorm (frameFilter ρ F G v) := by
  rw [frameFilter_joint_change]
  exact H.preserves_sqNorm _

/-- The identity-frame baseline reproduces the original filter exactly. -/
theorem frameFilter_identity (ρ : ℝ) (v : ℝ × ℝ) :
    frameFilter ρ OrthogonalFrame.identity
      OrthogonalFrame.identity v = filter ρ v := by
  simp [frameFilter, OrthogonalFrame.identity]

/-- Negative control: a real nonzero Cartan stretch cannot be passed off as
an orthogonal frame simply by calling it a coordinate change. -/
theorem nonzero_boost_is_not_an_orthogonal_frame (ρ : ℝ) (hρ : ρ ≠ 0) :
    ¬ ∃ F : OrthogonalFrame, ∀ v : ℝ × ℝ,
        F.linearEquiv v = boost ρ v := by
  rintro ⟨F, hF⟩
  apply boost_nonzero_not_isometric ρ hρ
  intro v
  calc
    sqNorm (boost ρ v) = sqNorm (F.linearEquiv v) :=
      congrArg sqNorm (hF v).symm
    _ = sqNorm v := F.preserves_sqNorm v

end AionFormal.R6
