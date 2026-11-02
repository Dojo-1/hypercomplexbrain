import R6MetricCompatibility

/-!
# Typed transport of heterogeneous local quadratic geometries

A local Worldlet carries a *proof-bearing symmetric bilinear form* on
its own real coordinate carrier. Source and target carriers are indexed
by different types and may have different dimensions:
    Fin 2 → ℝ   vs   Fin 3 → ℝ   vs   Fin 4 → ℝ.

A tendril is an actual real linear map between those carriers. Its
form-valued defect lives in the SOURCE carrier:

    D_T = T* gY - gX.

Composition accounts for the intermediate metric, while mismatched
intermediate metrics contribute a separately typed pullback remainder.

This does NOT require positive definiteness or certify compatible
physical units, time, semantics, quantum resources, or cognition.
Finite-dimensional examples are explicit; the generic statements
are algebraic for indexed real function modules.
-/

namespace AionFormal.Heterogeneous

/-- A Worldlet's own state space, indexed by its own coordinate type. -/
abbrev Carrier (ι : Type*) := ι → ℝ

/-- A genuine bilinear form, not an arbitrary scalar-valued oracle. -/
abbrev LocalForm (ι : Type*) := LinearMap.BilinForm ℝ (Carrier ι)

/-- The transport is linear; source and target coordinate types may differ. -/
abbrev Tendril (ι κ : Type*) := Carrier ι →ₗ[ℝ] Carrier κ

/-- Geometry with a certified symmetric bilinear form. It need not be
positive definite, nondegenerate, or semantically unit-compatible. -/
structure Worldlet (ι : Type*) where
  form : LocalForm ι
  symmetric : ∀ u v : Carrier ι, form u v = form v u

/-- Pull a target bilinear form back through a typed linear tendril. -/
def pullback {ι κ : Type*} (T : Tendril ι κ)
    (g : LocalForm κ) : LocalForm ι :=
  g.compl₁₂ T T

/-- Symmetric form-valued remainder on the *source* Worldlet. -/
def defect {ι κ : Type*} (X : Worldlet ι)
    (Y : Worldlet κ) (T : Tendril ι κ) : LocalForm ι :=
  pullback T Y.form - X.form

/-- The defect is observable on two directions, not just one diagonal scalar. -/
theorem defect_eval {ι κ : Type*} (X : Worldlet ι)
    (Y : Worldlet κ) (T : Tendril ι κ)
    (u v : Carrier ι) :
    defect X Y T u v = Y.form (T u) (T v) - X.form u v := by
  simp [defect, pullback]

/-- Symmetry of the source and target forms survives the transport defect. -/
theorem defect_symmetric {ι κ : Type*} (X : Worldlet ι)
    (Y : Worldlet κ) (T : Tendril ι κ)
    (u v : Carrier ι) :
    defect X Y T u v = defect X Y T v u := by
  rw [defect_eval, defect_eval, Y.symmetric (T u) (T v),
    X.symmetric u v]

/-- Pullback is additive at the level of whole bilinear forms. -/
theorem pullback_add {ι κ : Type*} (T : Tendril ι κ)
    (g h : LocalForm κ) :
    pullback T (g + h) = pullback T g + pullback T h := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [pullback]

/-- Pullback respects the signed difference of two forms. -/
theorem pullback_sub {ι κ : Type*} (T : Tendril ι κ)
    (g h : LocalForm κ) :
    pullback T (g - h) = pullback T g - pullback T h := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [pullback]

/-- Different-dimensional pullback is contravariantly compositional. -/
theorem pullback_comp {ι κ λ : Type*}
    (T : Tendril ι κ) (S : Tendril κ λ)
    (g : LocalForm λ) :
    pullback (S.comp T) g = pullback T (pullback S g) := by
  apply LinearMap.BilinForm.ext
  intro u v
  rfl

/-- Pulling back a zero form cannot reveal information. -/
theorem pullback_zero {ι κ : Type*} (T : Tendril ι κ) :
    pullback T (0 : LocalForm κ) = 0 := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [pullback]

/-- A faithful real geometry cannot be inferred from arbitrary transports:
a zero tendril conceals *every* target form. -/
theorem zero_tendril_hides_form {ι κ : Type*} (g : LocalForm κ) :
    pullback (0 : Tendril ι κ) g = 0 := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [pullback]

/-- A typed pullback Worldlet carries its symmetry proof. It may acquire
degeneracy if T loses directions, so this is NOT automatic equivalence. -/
def rechart {ι κ : Type*} (Y : Worldlet κ)
    (T : Tendril ι κ) : Worldlet ι where
  form := pullback T Y.form
  symmetric := by
    intro u v
    change Y.form (T u) (T v) = Y.form (T v) (T u)
    exact Y.symmetric _ _

/-- If the source metric is exactly the pulled-back target metric,
its recorded defect vanishes. This does not certify T injective. -/
theorem rechart_defect_zero {ι κ : Type*} (Y : Worldlet κ)
    (T : Tendril ι κ) :
    defect (rechart Y T) Y T = 0 := by
  change pullback T Y.form - pullback T Y.form = 0
  exact sub_self _

/-- Zero form-valued defect is precisely equality of the compared forms. -/
theorem defect_zero_iff_compatible {ι κ : Type*}
    (X : Worldlet ι) (Y : Worldlet κ)
    (T : Tendril ι κ) :
    defect X Y T = 0 ↔ pullback T Y.form = X.form := by
  simp [defect]

/-- Three Worldlets can have distinct carrier types and dimensions.
The second defect must be pulled back through the first tendril. -/
theorem defect_comp {ι κ λ : Type*}
    (X : Worldlet ι) (Y : Worldlet κ) (Z : Worldlet λ)
    (T : Tendril ι κ) (S : Tendril κ λ) :
    defect X Z (S.comp T) =
      defect X Y T + pullback T (defect Y Z S) := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [defect, pullback] <;> ring

/-- A disagreement about the intermediate Worldlet metric produces
an explicit form-valued remainder in the original source carrier. -/
theorem defect_middle_mismatch {ι κ λ : Type*}
    (X : Worldlet ι) (Yout Yin : Worldlet κ) (Z : Worldlet λ)
    (T : Tendril ι κ) (S : Tendril κ λ) :
    defect X Z (S.comp T) =
      (defect X Yout T + pullback T (defect Yin Z S)) +
        pullback T (Yin.form - Yout.form) := by
  apply LinearMap.BilinForm.ext
  intro u v
  simp [defect, pullback] <;> ring

/-- A commuting square with transported source and target forms preserves
the *entire* typed defect, not merely one scalar evaluation. -/
theorem defect_commuting_square {ι κ ι' κ' : Type*}
    (X : Worldlet ι) (Y : Worldlet κ)
    (T : Tendril ι κ)
    (F : Tendril ι' ι) (G : Tendril κ' κ)
    (Tnew : Tendril ι' κ')
    (hcomm : G.comp Tnew = T.comp F) :
    defect (rechart X F) (rechart Y G) Tnew =
      pullback F (defect X Y T) := by
  apply LinearMap.BilinForm.ext
  intro u v
  have hu : G (Tnew u) = T (F u) := by
    have h := congrArg (fun L : Tendril ι' κ => L u) hcomm
    simpa using h
  have hv : G (Tnew v) = T (F v) := by
    have h := congrArg (fun L : Tendril ι' κ => L v) hcomm
    simpa using h
  simp [defect, rechart, pullback, hu, hv]

/-- A surjective chart is faithful for bilinear-form pullback.
No invertibility claim is made without the separate right hypotheses. -/
theorem pullback_injective_of_surjective {ι κ : Type*}
    (F : Tendril ι κ) (hF : Function.Surjective F) :
    Function.Injective (pullback F) := by
  intro g h heq
  apply LinearMap.BilinForm.ext
  intro u v
  obtain ⟨u', hu⟩ := hF u
  obtain ⟨v', hv⟩ := hF v
  have hval := congrArg (fun B : LocalForm ι => B u' v') heq
  simpa [pullback, hu, hv] using hval

/-- Zero defect is reflected across a genuinely faithful source chart.
A singular chart may erase nonzero geometry, so surjectivity matters. -/
theorem defect_zero_under_faithful_chart_iff {ι κ ι' κ' : Type*}
    (X : Worldlet ι) (Y : Worldlet κ)
    (T : Tendril ι κ) (F : Tendril ι' ι)
    (G : Tendril κ' κ) (Tnew : Tendril ι' κ')
    (hcomm : G.comp Tnew = T.comp F)
    (hF : Function.Surjective F) :
    defect (rechart X F) (rechart Y G) Tnew = 0 ↔
      defect X Y T = 0 := by
  rw [defect_commuting_square X Y T F G Tnew hcomm]
  constructor
  · intro hz
    apply pullback_injective_of_surjective F hF
    simpa [pullback_zero] using hz
  · intro hz
    rw [hz, pullback_zero]

/-- A kernel-visible 2→3→4 instantiation, demonstrating that the carrier
types genuinely differ across the two compositions. -/
theorem two_three_four_defect_comp
    (X : Worldlet (Fin 2)) (Y : Worldlet (Fin 3))
    (Z : Worldlet (Fin 4))
    (T : Tendril (Fin 2) (Fin 3))
    (S : Tendril (Fin 3) (Fin 4)) :
    defect X Z (S.comp T) =
      defect X Y T + pullback T (defect Y Z S) :=
  defect_comp X Y Z T S

end AionFormal.Heterogeneous
