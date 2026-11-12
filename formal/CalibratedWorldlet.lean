import MonotoneClocks

/-!
# Calibrated Worldlet: the three-channel contract made explicit

A *measured* Worldlet has a certified positive local geometry, an
observer whose reading is indexed by a seven-base SI dimension, and
a separately tagged local clock.

A calibrated bridge must present:
  (1) a linear state tendril,
  (2) a positive SAME-DIMENSION observation conversion, and
  (3) a typed monotone clock correspondence with affine calibration.

Joint compatibility means THREE independently checked zero remainders.
The clock side is a monotone discrete affine model, NOT a physical
oscillator accuracy claim, nor a semantics/quantum/cognition theorem.
-/

namespace AionFormal.Calibrated

open AionFormal.Heterogeneous
open AionFormal.Units

/-- A positive geometric Worldlet with an independently dimensioned
single linear observation and a separately identified local clock. -/
structure MeasuredWorldlet (S Tag : Type*) (d : Dimension) where
  world : PositiveWorldlet S
  observed : Tendril S (Fin 1)
  clock : Clocks.LocalClock Tag

/-- All three calibrated transport maps must be supplied. Conversion
factors are declared; their external SI calibration is not proved. -/
structure Bridge (S T TA TB : Type*) (d : Dimension) where
  state : Tendril S T
  observable : UnitFactor d
  clocks : Clocks.ClockBridge TA TB

def compose {A B C TA TB TC : Type*} {d : Dimension}
    (f : Bridge B C TB TC d) (e : Bridge A B TA TB d) :
    Bridge A C TA TC d where
  state := f.state.comp e.state
  observable := Units.compose f.observable e.observable
  clocks := Clocks.composeBridge f.clocks e.clocks

/-- The geometric observation has a bilinear-form source carrier. -/
def geometricRemainder {S T TA TB : Type*} {d : Dimension}
    (X : MeasuredWorldlet S TA d)
    (Y : MeasuredWorldlet T TB d)
    (e : Bridge S T TA TB d) : LocalForm S :=
  defect X.world.underlying Y.world.underlying e.state

/-- The unit-converted observer difference is still a separate REAL
instrument, attached to one specified SI dimension. -/
def observableRemainder {S T TA TB : Type*} {d : Dimension}
    (X : MeasuredWorldlet S TA d)
    (Y : MeasuredWorldlet T TB d)
    (e : Bridge S T TA TB d) (v : Carrier S) : ℝ :=
  e.observable.factor * (X.observed v 0) -
    Y.observed (e.state v) 0

/-- The clock difference is a separate, indexed, typed time instrument. -/
def clockRemainder {S T TA TB : Type*} {d : Dimension}
    (X : MeasuredWorldlet S TA d)
    (Y : MeasuredWorldlet T TB d)
    (e : Bridge S T TA TB d) (n : Clocks.LocalTick TA) : ℝ :=
  Clocks.residual X.clock Y.clock e.clocks n

/-- A complete bridge compatibility certificate has three parts.
No one zero remainder can erase the other two. -/
def JointlyCompatible {S T TA TB : Type*} {d : Dimension}
    (X : MeasuredWorldlet S TA d)
    (Y : MeasuredWorldlet T TB d)
    (e : Bridge S T TA TB d) : Prop :=
  geometricRemainder X Y e = 0 ∧
    (∀ v : Carrier S, observableRemainder X Y e v = 0) ∧
      Clocks.Exact X.clock Y.clock e.clocks

/-- The geometric composition law remains form-valued and source-typed. -/
theorem geometricRemainder_comp {A B C TA TB TC : Type*} {d : Dimension}
    (X : MeasuredWorldlet A TA d)
    (Y : MeasuredWorldlet B TB d)
    (Z : MeasuredWorldlet C TC d)
    (e : Bridge A B TA TB d)
    (f : Bridge B C TB TC d) :
    geometricRemainder X Z (compose f e) =
      geometricRemainder X Y e +
        pullback e.state (geometricRemainder Y Z f) :=
  defect_comp X.world.underlying Y.world.underlying
    Z.world.underlying e.state f.state

/-- The unit-converted observer remainder has a separate composition law:
outer factor times inner error, plus the outer error on transported state. -/
theorem observableRemainder_comp {A B C TA TB TC : Type*} {d : Dimension}
    (X : MeasuredWorldlet A TA d)
    (Y : MeasuredWorldlet B TB d)
    (Z : MeasuredWorldlet C TC d)
    (e : Bridge A B TA TB d)
    (f : Bridge B C TB TC d) (v : Carrier A) :
    observableRemainder X Z (compose f e) v =
      f.observable.factor * observableRemainder X Y e v +
        observableRemainder Y Z f (e.state v) := by
  dsimp [observableRemainder, compose, Units.compose]
  ring

/-- The clock remainder obeys its own rate-scaled composition law.
It is not identified with a metric or observer error. -/
theorem clockRemainder_comp {A B C TA TB TC : Type*} {d : Dimension}
    (X : MeasuredWorldlet A TA d)
    (Y : MeasuredWorldlet B TB d)
    (Z : MeasuredWorldlet C TC d)
    (e : Bridge A B TA TB d)
    (f : Bridge B C TB TC d) (n : Clocks.LocalTick TA) :
    clockRemainder X Z (compose f e) n =
      f.clocks.calibration.rate * clockRemainder X Y e n +
        clockRemainder Y Z f (e.clocks.ticks.forward n) :=
  Clocks.residual_comp X.clock Y.clock Z.clock e.clocks f.clocks n

/-- If both legs are exactly compatible in ALL THREE instruments,
the composed bridge is compatible, without scalarizing their remainders. -/
theorem jointlyCompatible_comp {A B C TA TB TC : Type*} {d : Dimension}
    (X : MeasuredWorldlet A TA d)
    (Y : MeasuredWorldlet B TB d)
    (Z : MeasuredWorldlet C TC d)
    (e : Bridge A B TA TB d)
    (f : Bridge B C TB TC d)
    (he : JointlyCompatible X Y e)
    (hf : JointlyCompatible Y Z f) :
    JointlyCompatible X Z (compose f e) := by
  rcases he with ⟨hge, hoe, hce⟩
  rcases hf with ⟨hgf, hof, hcf⟩
  constructor
  · rw [geometricRemainder_comp, hge, hgf, pullback_zero]
    simp
  constructor
  · intro v
    rw [observableRemainder_comp, hoe v, hof (e.state v)]
    ring
  · exact Clocks.exact_comp X.clock Y.clock Z.clock
      e.clocks f.clocks hce hcf

/-- Geometric exactness plus a strictly positive source forces a
kernel-free tendril, independently of observer and clock comparisons. -/
theorem jointlyCompatible_requires_injective
    {S T TA TB : Type*} {d : Dimension}
    (X : MeasuredWorldlet S TA d)
    (Y : MeasuredWorldlet T TB d)
    (e : Bridge S T TA TB d)
    (h : JointlyCompatible X Y e) :
    Function.Injective e.state := by
  exact compatible_positive_source_implies_injective
    X.world.underlying Y.world.underlying e.state
    X.world.positive h.1

/-- The typed observer dimension cannot be switched from length to time.
This is an index-level non-equality, not an empirical calibration result. -/
theorem incompatible_length_time_observation_types :
    lengthDim ≠ timeDim :=
  length_not_time

end AionFormal.Calibrated
