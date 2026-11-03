import HeterogeneousWorldlet

/-!
# Positivity and faithfulness of heterogeneous geometric transports

Worldlet forms are symmetric but not necessarily positive. The explicit
strict-positivity predicate below requires positive squared reading for
every nonzero vector. For a strictly positive target form g and a linear
tendril T, its pullback is strictly positive if and only if T is injective.

Kernel directions are exactly where a pullback can lose positive length.
Nothing here certifies a quantum-resource cost, semantic equivalence,
full metric units, or smooth manifold structures.
-/

namespace AionFormal.Heterogeneous

/-- The strictly positive quadratic-form contract on a real carrier. -/
def StrictlyPositive {ι : Type*} (g : LocalForm ι) : Prop :=
  ∀ v : Carrier ι, v ≠ 0 → 0 < g v v

/-- The weaker positive-semidefinite contract. -/
def NonnegativeQuadratic {ι : Type*} (g : LocalForm ι) : Prop :=
  ∀ v : Carrier ι, 0 ≤ g v v

/-- A nonnegative target form remains nonnegative under any linear tendril. -/
theorem nonnegative_pullback {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (hg : NonnegativeQuadratic g) :
    NonnegativeQuadratic (pullback T g) := by
  intro v
  change 0 ≤ g (T v) (T v)
  exact hg (T v)

/-- Every kernel vector is invisible to the target quadratic instrument. -/
theorem pullback_zero_on_kernel {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (v : Carrier ι) (hv : T v = 0) :
    pullback T g v v = 0 := by
  simp [pullback, hv]

/-- Positive target geometry remains positive on the source when
the tendril cannot collapse a nonzero vector. -/
theorem strictlyPositive_pullback_of_injective {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (hg : StrictlyPositive g) (hT : Function.Injective T) :
    StrictlyPositive (pullback T g) := by
  intro v hv
  change 0 < g (T v) (T v)
  have hnonzero : T v ≠ 0 := by
    intro hz
    apply hv
    apply hT
    simpa using hz
  exact hg (T v) hnonzero

/-- A strictly positive pullback implies injectivity, even without
assuming positive definiteness for the target form. -/
theorem injective_of_strictlyPositive_pullback {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (hp : StrictlyPositive (pullback T g)) :
    Function.Injective T := by
  intro u v huv
  by_contra hne
  have hdiff : u - v ≠ 0 := by
    intro hz
    exact hne (sub_eq_zero.mp hz)
  have hker : T (u - v) = 0 := by
    rw [map_sub]
    exact sub_eq_zero.mpr huv
  have hpositive : 0 < (pullback T g) (u - v) (u - v) :=
    hp (u - v) hdiff
  have hzero : (pullback T g) (u - v) (u - v) = 0 :=
    pullback_zero_on_kernel T g (u - v) hker
  rw [hzero] at hpositive
  exact (lt_irrefl (0 : ℝ)) hpositive

/-- Exact positivity-injectivity threshold for a strictly positive target.
The source and target dimension types need not match. -/
theorem strictlyPositive_pullback_iff_injective {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (hg : StrictlyPositive g) :
    StrictlyPositive (pullback T g) ↔ Function.Injective T := by
  constructor
  · exact injective_of_strictlyPositive_pullback T g
  · exact strictlyPositive_pullback_of_injective T g hg

/-- Without injectivity the pulled-back form cannot be strictly positive,
regardless of the target form. -/
theorem noninjective_pullback_not_strictlyPositive {ι κ : Type*}
    (T : Tendril ι κ) (g : LocalForm κ)
    (hT : ¬ Function.Injective T) :
    ¬ StrictlyPositive (pullback T g) := by
  intro hp
  exact hT (injective_of_strictlyPositive_pullback T g hp)

/-- A certified positive Worldlet is an unrestricted Worldlet carrying an
additional proof, rather than pretending all symmetric forms are metrics. -/
structure PositiveWorldlet (ι : Type*) where
  underlying : Worldlet ι
  positive : StrictlyPositive underlying.form

/-- Construction of a positive source geometry requires a certified
injective tendril; it does not imply surjectivity or semantic equivalence. -/
def positiveRechart {ι κ : Type*}
    (Y : PositiveWorldlet κ) (T : Tendril ι κ)
    (hT : Function.Injective T) : PositiveWorldlet ι where
  underlying := rechart Y.underlying T
  positive := strictlyPositive_pullback_of_injective
    T Y.underlying.form Y.positive hT

/-- The recharted metric is positive exactly when the tendril is faithful. -/
theorem positive_rechart_iff_injective {ι κ : Type*}
    (Y : PositiveWorldlet κ) (T : Tendril ι κ) :
    StrictlyPositive (rechart Y.underlying T).form ↔
      Function.Injective T :=
  strictlyPositive_pullback_iff_injective T Y.underlying.form Y.positive

/-- A certified positive rechart still has exact zero source-typed defect. -/
theorem positiveRechart_defect_zero {ι κ : Type*}
    (Y : PositiveWorldlet κ) (T : Tendril ι κ)
    (hT : Function.Injective T) :
    defect (positiveRechart Y T hT).underlying Y.underlying T = 0 :=
  rechart_defect_zero Y.underlying T

/-- If a source metric is strictly positive and the transport defect is zero,
the tendril cannot have a nontrivial kernel, regardless of target positivity. -/
theorem compatible_positive_source_implies_injective {ι κ : Type*}
    (X : Worldlet ι) (Y : Worldlet κ) (T : Tendril ι κ)
    (hX : StrictlyPositive X.form) (hD : defect X Y T = 0) :
    Function.Injective T := by
  have hmetric : pullback T Y.form = X.form :=
    (defect_zero_iff_compatible X Y T).mp hD
  apply injective_of_strictlyPositive_pullback T Y.form
  rw [hmetric]
  exact hX

/-- Under exact metric matching with a positive target, strict positivity
of the source is equivalent to injectivity of the transport. -/
theorem compatible_positive_source_iff_injective {ι κ : Type*}
    (X : Worldlet ι) (Y : Worldlet κ) (T : Tendril ι κ)
    (hY : StrictlyPositive Y.form) (hD : defect X Y T = 0) :
    StrictlyPositive X.form ↔ Function.Injective T := by
  constructor
  · intro hX
    exact compatible_positive_source_implies_injective X Y T hX hD
  · intro hT
    have hp : StrictlyPositive (pullback T Y.form) :=
      strictlyPositive_pullback_of_injective T Y.form hY hT
    have hmetric : pullback T Y.form = X.form :=
      (defect_zero_iff_compatible X Y T).mp hD
    rw [hmetric] at hp
    exact hp

/-- A concrete nonzero vector on the one-coordinate source carrier. -/
def oneAxis : Carrier (Fin 1) := fun _ => 1

theorem oneAxis_nonzero : oneAxis ≠ 0 := by
  intro h
  have h0 := congrArg (fun v : Carrier (Fin 1) => v 0) h
  norm_num [oneAxis] at h0

/-- Negative control: the zero 1→2 tendril cannot pull back a strictly
positive source metric, regardless of its target form. -/
theorem zero_tendril_not_strictlyPositive
    (g : LocalForm (Fin 2)) :
    ¬ StrictlyPositive (pullback (0 : Tendril (Fin 1) (Fin 2)) g) := by
  intro hp
  have hpositive := hp oneAxis oneAxis_nonzero
  have hzero : pullback (0 : Tendril (Fin 1) (Fin 2)) g
      oneAxis oneAxis = 0 := by
    simp [pullback]
  rw [hzero] at hpositive
  exact (lt_irrefl (0 : ℝ)) hpositive

/-- Negative control: even an injective identity map cannot create
positivity from the zero target form. -/
theorem identity_zero_target_not_strictlyPositive :
    Function.Injective (LinearMap.id : Tendril (Fin 1) (Fin 1)) ∧
      ¬ StrictlyPositive
        (pullback (LinearMap.id : Tendril (Fin 1) (Fin 1))
          (0 : LocalForm (Fin 1))) := by
  constructor
  · intro u v h
    simpa using h
  · intro hp
    have hpositive := hp oneAxis oneAxis_nonzero
    have hzero : pullback (LinearMap.id : Tendril (Fin 1) (Fin 1))
        (0 : LocalForm (Fin 1)) oneAxis oneAxis = 0 := by
      simp [pullback]
    rw [hzero] at hpositive
    exact (lt_irrefl (0 : ℝ)) hpositive

/-- This is an actually type-distinct 2→3 transport, not one square 2×2 map. -/
theorem two_three_positive_pullback_iff_injective
    (T : Tendril (Fin 2) (Fin 3))
    (g : LocalForm (Fin 3))
    (hg : StrictlyPositive g) :
    StrictlyPositive (pullback T g) ↔ Function.Injective T :=
  strictlyPositive_pullback_iff_injective T g hg

/-- Two injective tendrils preserve positive-definite pullback geometry
when composed, regardless of their intermediate dimensions. -/
theorem composition_positive_pullback {ι κ ξ : Type*}
    (T : Tendril ι κ) (S : Tendril κ ξ)
    (g : LocalForm ξ) (hg : StrictlyPositive g)
    (hT : Function.Injective T) (hS : Function.Injective S) :
    StrictlyPositive (pullback (S.comp T) g) := by
  apply strictlyPositive_pullback_of_injective (S.comp T) g hg
  intro u v huv
  apply hT
  apply hS
  simpa using huv

end AionFormal.Heterogeneous
