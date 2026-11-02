import R6MetricDefect

/-!
# R6: coordinate-covariant metric-pullback defect

For a commuting square G ∘ Tnew = T ∘ F, the physical source and
target quadratic forms must be transported along F and G as well.
The form-valued defect then obeys

  D_Tnew(F* gX, G* gY) = F* D_T(gX,gY).

This is an algebraic equality for arbitrary real 2×2 maps F,G,T,Tnew.
Calling F or G a coordinate *equivalence* additionally requires inverses.
A right inverse of F is sufficient to reflect vanishing defect.
Nothing here certifies positive-definite metrics, physical energy,
quantum advantage, or semantic equivalence of distinct Worldlets.
-/

namespace AionFormal.R6

theorem formPullback_add (F : RealMap2) (g h : SymForm2) :
    formPullback F (formAdd g h) =
      formAdd (formPullback F g) (formPullback F h) := by
  apply symForm_eq_of_coordinates
  · dsimp [formPullback, formAdd]; ring
  · dsimp [formPullback, formAdd]; ring
  · dsimp [formPullback, formAdd]; ring

theorem formPullback_sub (F : RealMap2) (g h : SymForm2) :
    formPullback F (formSub g h) =
      formSub (formPullback F g) (formPullback F h) := by
  apply symForm_eq_of_coordinates
  · dsimp [formPullback, formSub]; ring
  · dsimp [formPullback, formSub]; ring
  · dsimp [formPullback, formSub]; ring

theorem formPullback_identity (g : SymForm2) :
    formPullback identityMap g = g := by
  apply symForm_eq_of_coordinates
  · dsimp [formPullback, identityMap]; ring
  · dsimp [formPullback, identityMap]; ring
  · dsimp [formPullback, identityMap]; ring

theorem formPullback_zero (F : RealMap2) :
    formPullback F zeroForm = zeroForm := by
  apply symForm_eq_of_coordinates
  · dsimp [formPullback, zeroForm]; ring
  · dsimp [formPullback, zeroForm]; ring
  · dsimp [formPullback, zeroForm]; ring

/-- Exact covariance of the whole symmetric-form defect, not only a
single state's squared-norm reading. -/
theorem metricDefect_commuting_square
    (F G T Tnew : RealMap2) (gX gY : SymForm2)
    (hcomm : mapComp G Tnew = mapComp T F) :
    metricPullbackDefect Tnew (formPullback F gX) (formPullback G gY) =
      formPullback F (metricPullbackDefect T gX gY) := by
  calc
    metricPullbackDefect Tnew (formPullback F gX) (formPullback G gY) =
        formSub (formPullback Tnew (formPullback G gY))
          (formPullback F gX) := rfl
    _ = formSub (formPullback (mapComp G Tnew) gY)
          (formPullback F gX) := by
            rw [formPullback_comp G Tnew gY]
    _ = formSub (formPullback (mapComp T F) gY)
          (formPullback F gX) := by rw [hcomm]
    _ = formSub (formPullback F (formPullback T gY))
          (formPullback F gX) := by
            rw [formPullback_comp T F gY]
    _ = formPullback F (formSub (formPullback T gY) gX) :=
      (formPullback_sub F (formPullback T gY) gX).symm
    _ = formPullback F (metricPullbackDefect T gX gY) := rfl

/-- The scalar observation covaries only when the observed input moves. -/
theorem metricDefect_commuting_square_eval
    (F G T Tnew : RealMap2) (gX gY : SymForm2)
    (hcomm : mapComp G Tnew = mapComp T F) (v : ℝ × ℝ) :
    formEval (metricPullbackDefect Tnew (formPullback F gX)
      (formPullback G gY)) v =
      formEval (metricPullbackDefect T gX gY) (mapApply F v) := by
  rw [metricDefect_commuting_square F G T Tnew gX gY hcomm,
    formPullback_eval]

/-- A transport can be metric-compatible even when its displayed matrix
is non-orthogonal with respect to the standard Euclidean coefficients. -/
theorem metricDefect_zero_of_matched_forms (T : RealMap2)
    (gY : SymForm2) :
    metricPullbackDefect T (formPullback T gY) gY = zeroForm := by
  apply symForm_eq_of_coordinates
  · dsimp [metricPullbackDefect, formSub, zeroForm]; ring
  · dsimp [metricPullbackDefect, formSub, zeroForm]; ring
  · dsimp [metricPullbackDefect, formSub, zeroForm]; ring

theorem metricDefect_zero_iff_matched_forms
    (T : RealMap2) (gX gY : SymForm2) :
    metricPullbackDefect T gX gY = zeroForm ↔
      formPullback T gY = gX := by
  constructor
  · intro h
    apply symForm_eq_of_coordinates
    · have hx := congrArg SymForm2.xx h
      change (formPullback T gY).xx - gX.xx = 0 at hx
      linarith
    · have hxy := congrArg SymForm2.xy h
      change (formPullback T gY).xy - gX.xy = 0 at hxy
      linarith
    · have hy := congrArg SymForm2.yy h
      change (formPullback T gY).yy - gX.yy = 0 at hy
      linarith
  · intro h
    rw [← h]
    exact metricDefect_zero_of_matched_forms T gY

/-- A pullback by F reflects zero when F admits a verified right inverse.
A singular coordinate projection can conceal a nonzero form. -/
theorem pullback_zero_reflect_of_right_inverse
    (F Finv : RealMap2) (hinv : mapComp F Finv = identityMap)
    (g : SymForm2) (hz : formPullback F g = zeroForm) :
    g = zeroForm := by
  have hp : formPullback Finv (formPullback F g) = zeroForm := by
    rw [hz, formPullback_zero]
  rw [← formPullback_comp F Finv g, hinv, formPullback_identity] at hp
  exact hp

theorem metricDefect_zero_covariant_iff
    (F Finv G T Tnew : RealMap2) (gX gY : SymForm2)
    (hinv : mapComp F Finv = identityMap)
    (hcomm : mapComp G Tnew = mapComp T F) :
    metricPullbackDefect Tnew (formPullback F gX) (formPullback G gY) =
        zeroForm ↔
      metricPullbackDefect T gX gY = zeroForm := by
  rw [metricDefect_commuting_square F G T Tnew gX gY hcomm]
  constructor
  · intro h
    exact pullback_zero_reflect_of_right_inverse F Finv hinv
      (metricPullbackDefect T gX gY) h
  · intro h
    rw [h, formPullback_zero]

theorem realMap_eq_of_coordinates {A B : RealMap2}
    (ha : A.a = B.a) (hb : A.b = B.b)
    (hc : A.c = B.c) (hd : A.d = B.d) : A = B := by
  cases A with
  | mk aa ab ac ad =>
    cases B with
    | mk ba bb bc bd =>
      dsimp at ha hb hc hd
      cases ha
      cases hb
      cases hc
      cases hd
      rfl

/-- Explicit reverse coordinate map for diag(2,1/2). -/
noncomputable def anisotropicInverse : RealMap2 :=
  ⟨(1 / 2 : ℝ), 0, 0, 2⟩

theorem anisotropic_inverse_certified :
    mapComp anisotropicInverse anisotropicMap = identityMap ∧
      mapComp anisotropicMap anisotropicInverse = identityMap := by
  constructor
  · apply realMap_eq_of_coordinates
    all_goals norm_num [mapComp, anisotropicInverse, anisotropicMap, identityMap]
  · apply realMap_eq_of_coordinates
    all_goals norm_num [mapComp, anisotropicMap, anisotropicInverse, identityMap]

theorem anisotropic_reparametrized_metric :
    formPullback anisotropicMap euclideanForm =
      ⟨4, 0, (1 / 4 : ℝ)⟩ := by
  apply symForm_eq_of_coordinates
  · norm_num [formPullback, anisotropicMap, euclideanForm]
  · norm_num [formPullback, anisotropicMap, euclideanForm]
  · norm_num [formPullback, anisotropicMap, euclideanForm]

/-- Same 2×2 matrix: zero defect when the source metric is transported,
nonzero defect if both sides are (incorrectly) reset to Euclidean. -/
theorem anisotropic_matched_vs_unmatched_metrics :
    metricPullbackDefect anisotropicMap
        (formPullback anisotropicMap euclideanForm)
        euclideanForm = zeroForm ∧
      metricPullbackDefect anisotropicMap
        euclideanForm euclideanForm ≠ zeroForm := by
  exact ⟨metricDefect_zero_of_matched_forms anisotropicMap
    euclideanForm, anisotropic_defect_nonzero⟩

def singularProjection : RealMap2 := ⟨1, 0, 0, 0⟩
def invisibleUnderProjection : SymForm2 := ⟨0, 0, 1⟩

/-- Negative control: a nonzero form can pull back to zero along a
singular map. Algebraic covariance alone does not make a chart invertible. -/
theorem singular_projection_hides_nonzero_form :
    formPullback singularProjection invisibleUnderProjection = zeroForm ∧
      invisibleUnderProjection ≠ zeroForm := by
  constructor
  · apply symForm_eq_of_coordinates
    · norm_num [formPullback, singularProjection,
        invisibleUnderProjection, zeroForm]
    · norm_num [formPullback, singularProjection,
        invisibleUnderProjection, zeroForm]
    · norm_num [formPullback, singularProjection,
        invisibleUnderProjection, zeroForm]
  · intro h
    have hy := congrArg SymForm2.yy h
    norm_num [invisibleUnderProjection, zeroForm] at hy

end AionFormal.R6
