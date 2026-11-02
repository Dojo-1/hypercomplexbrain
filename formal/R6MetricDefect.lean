import R6Remainder

/-!
# R6 metric-pullback defect: retain anisotropy instead of scalar collapse

An explicit symmetric real quadratic form on R² is represented by three
coefficients, the symmetric 2×2 matrix [[xx,xy],[xy,yy]]. A transport is a
four-coefficient real matrix. This avoids smuggling an implicit choice of
metric into the word "norm".

Given T:X→Y and declared forms gX and gY, its pullback defect is
  D_T = Tᵀ gY T - gX.
The tensor-like form remembers simultaneous expansion and contraction even
where its scalar evaluation on one input vanishes.

This file works with arbitrary symmetric FORMS, not automatically
positive-definite Riemannian metrics. Compatible physical units, distinct
worldlet carriers, connections and quantum-resource meanings are NOT
provided by the coordinate notation. Neither hardware nor cognition
follows from these exact polynomial identities.
-/

namespace AionFormal.R6

/-- Symmetric bilinear form in coordinates, represented by
    [[xx,xy],[xy,yy]]. No positive-definiteness is asserted. -/
structure SymForm2 where
  xx : ℝ
  xy : ℝ
  yy : ℝ

/-- A real 2×2 linear map on coordinate pairs, with no isometry assumption. -/
structure RealMap2 where
  a : ℝ
  b : ℝ
  c : ℝ
  d : ℝ

def formEval (g : SymForm2) (v : ℝ × ℝ) : ℝ :=
  g.xx * v.1 ^ 2 + 2 * g.xy * v.1 * v.2 + g.yy * v.2 ^ 2

def mapApply (T : RealMap2) (v : ℝ × ℝ) : ℝ × ℝ :=
  (T.a * v.1 + T.b * v.2, T.c * v.1 + T.d * v.2)

/-- Matrix composition: S after T. -/
def mapComp (S T : RealMap2) : RealMap2 where
  a := S.a * T.a + S.b * T.c
  b := S.a * T.b + S.b * T.d
  c := S.c * T.a + S.d * T.c
  d := S.c * T.b + S.d * T.d

def formAdd (g h : SymForm2) : SymForm2 where
  xx := g.xx + h.xx
  xy := g.xy + h.xy
  yy := g.yy + h.yy

def formSub (g h : SymForm2) : SymForm2 where
  xx := g.xx - h.xx
  xy := g.xy - h.xy
  yy := g.yy - h.yy

/-- Pull back a symmetric form on Y along the declared map X→Y. -/
def formPullback (T : RealMap2) (g : SymForm2) : SymForm2 where
  xx := g.xx * T.a ^ 2 + 2 * g.xy * T.a * T.c + g.yy * T.c ^ 2
  xy := g.xx * T.a * T.b + g.xy * (T.a * T.d + T.b * T.c) +
    g.yy * T.c * T.d
  yy := g.xx * T.b ^ 2 + 2 * g.xy * T.b * T.d + g.yy * T.d ^ 2

/-- The source quadratic-form defect, not one measured scalar. -/
def metricPullbackDefect (T : RealMap2)
    (gX gY : SymForm2) : SymForm2 :=
  formSub (formPullback T gY) gX

/-- Equality of all three coefficients determines a symmetric form. -/
theorem symForm_eq_of_coordinates {g h : SymForm2}
    (hxx : g.xx = h.xx) (hxy : g.xy = h.xy)
    (hyy : g.yy = h.yy) : g = h := by
  cases g with
  | mk gx gy gz =>
    cases h with
    | mk hx hy hz =>
      dsimp at hxx hxy hyy
      cases hxx
      cases hxy
      cases hyy
      rfl

/-- Evaluation is additive in the form. -/
theorem formAdd_eval (g h : SymForm2) (v : ℝ × ℝ) :
    formEval (formAdd g h) v =
      formEval g v + formEval h v := by
  dsimp [formEval, formAdd]
  ring

/-- Evaluation respects difference of forms. -/
theorem formSub_eval (g h : SymForm2) (v : ℝ × ℝ) :
    formEval (formSub g h) v =
      formEval g v - formEval h v := by
  dsimp [formEval, formSub]
  ring

/-- Exactly the same quadratic observation before or after pullback. -/
theorem formPullback_eval (T : RealMap2) (g : SymForm2)
    (v : ℝ × ℝ) :
    formEval (formPullback T g) v =
      formEval g (mapApply T v) := by
  dsimp [formEval, formPullback, mapApply]
  ring

/-- The field-level meaning of the pullback defect at one input. -/
theorem metricPullbackDefect_eval (T : RealMap2)
    (gX gY : SymForm2) (v : ℝ × ℝ) :
    formEval (metricPullbackDefect T gX gY) v =
      formEval gY (mapApply T v) - formEval gX v := by
  rw [metricPullbackDefect, formSub_eval, formPullback_eval]

/-- The declared 2×2 coefficient map composes as ordinary functions. -/
theorem mapApply_comp (S T : RealMap2) (v : ℝ × ℝ) :
    mapApply (mapComp S T) v = mapApply S (mapApply T v) := by
  apply Prod.ext
  · dsimp [mapApply, mapComp]
    ring
  · dsimp [mapApply, mapComp]
    ring

/-- Pullback is contravariantly functorial as a symmetric FORM,
not merely as a scalar tested at one input. -/
theorem formPullback_comp (S T : RealMap2) (gZ : SymForm2) :
    formPullback (mapComp S T) gZ =
      formPullback T (formPullback S gZ) := by
  apply symForm_eq_of_coordinates
  · dsimp [formPullback, mapComp]
    ring
  · dsimp [formPullback, mapComp]
    ring
  · dsimp [formPullback, mapComp]
    ring

/-- With a consistent intermediate metric, defects compose as symmetric
forms: D_(S∘T) = D_T + T* D_S. No state-specific clipping is used. -/
theorem metricPullbackDefect_comp (S T : RealMap2)
    (gX gY gZ : SymForm2) :
    metricPullbackDefect (mapComp S T) gX gZ =
      formAdd (metricPullbackDefect T gX gY)
        (formPullback T (metricPullbackDefect S gY gZ)) := by
  apply symForm_eq_of_coordinates
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring

/-- If the two legs silently disagree on the intermediate form, the
missing correction is exactly T*(gYin - gYout). This is not zero
unless a compatibility contract makes it zero. -/
theorem metricPullbackDefect_middle_mismatch (S T : RealMap2)
    (gX gYout gYin gZ : SymForm2) :
    metricPullbackDefect (mapComp S T) gX gZ =
      formAdd
        (formAdd (metricPullbackDefect T gX gYout)
          (formPullback T (metricPullbackDefect S gYin gZ)))
        (formPullback T (formSub gYin gYout)) := by
  apply symForm_eq_of_coordinates
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring
  · dsimp [metricPullbackDefect, formAdd, formSub, formPullback, mapComp]
    ring

/-- Standard Euclidean form, used only as a matched carrier control. -/
def euclideanForm : SymForm2 := ⟨1, 0, 1⟩

def zeroForm : SymForm2 := ⟨0, 0, 0⟩

def identityMap : RealMap2 := ⟨1, 0, 0, 1⟩

theorem metricPullbackDefect_identity (g : SymForm2) :
    metricPullbackDefect identityMap g g = zeroForm := by
  apply symForm_eq_of_coordinates
  · dsimp [metricPullbackDefect, formSub, formPullback,
      identityMap, zeroForm]
    ring
  · dsimp [metricPullbackDefect, formSub, formPullback,
      identityMap, zeroForm]
    ring
  · dsimp [metricPullbackDefect, formSub, formPullback,
      identityMap, zeroForm]
    ring

/-- Bridge to the already formalized one-state signed norm remainder,
for this particular Euclidean metric only. -/
theorem euclideanDefect_agrees_normChange (T : RealMap2)
    (v : ℝ × ℝ) :
    formEval (metricPullbackDefect T euclideanForm euclideanForm) v =
      normChange (mapApply T) v := by
  rw [metricPullbackDefect_eval]
  simp [euclideanForm, formEval, normChange, sqNorm]

/-- A map with determinant one, nonzero anisotropic strain,
and a direction whose norm is accidentally preserved. -/
noncomputable def anisotropicMap : RealMap2 := ⟨2, 0, 0, (1 / 2 : ℝ)⟩

/-- The vector (1,2) has norm 5 both before and after this anisotropic map. -/
theorem anisotropic_zero_on_one_nonzero_input :
    formEval (metricPullbackDefect anisotropicMap
      euclideanForm euclideanForm) (1, 2) = 0 := by
  norm_num [formEval, metricPullbackDefect, formSub, formPullback,
    anisotropicMap, euclideanForm]

/-- Despite the previous zero reading, the pullback defect is not zero. -/
theorem anisotropic_defect_nonzero :
    metricPullbackDefect anisotropicMap euclideanForm euclideanForm ≠ zeroForm := by
  intro h
  have hx := congrArg SymForm2.xx h
  norm_num [metricPullbackDefect, formSub, formPullback,
    anisotropicMap, euclideanForm, zeroForm] at hx

/-- Simultaneous expansion and contraction live in *different directions*,
even when the net scalar on another direction is zero. -/
theorem anisotropic_opposite_axis_defects :
    0 < formEval (metricPullbackDefect anisotropicMap
        euclideanForm euclideanForm) (1, 0) ∧
      formEval (metricPullbackDefect anisotropicMap
        euclideanForm euclideanForm) (0, 1) < 0 := by
  constructor
  · norm_num [formEval, metricPullbackDefect, formSub, formPullback,
      anisotropicMap, euclideanForm]
  · norm_num [formEval, metricPullbackDefect, formSub, formPullback,
      anisotropicMap, euclideanForm]

end AionFormal.R6
