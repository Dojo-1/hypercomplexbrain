import PositiveWorldletMetric

/-!
# Typed observable and clock-readout compatibility

A geometric Worldlet may have separate observer channels and clock
readouts. The observation carriers and clock carriers are independent
types; a bridge must declare conversion maps for BOTH.

Three different remainder types are intentionally retained:
  metric    : source bilinear form
  observer  : linear source -> target observation map
  clock     : linear source -> target clock-readout map

None may be promoted to another remainder without an explicit
comparison map. Clock readouts here are LINEAR state observations,
not an order-preserving physical clock synchronization, and the
observation conversion does not prove physical unit consistency.
-/

namespace AionFormal.Instrumented

open AionFormal.Heterogeneous

/-- Independent state, observation, and clock-readout carriers. -/
structure ObservedWorldlet (S O C : Type*) where
  local : Worldlet S
  observe : Tendril S O
  clockReadout : Tendril S C

/-- The bridge needs three declared linear maps; one geometric tendril
alone cannot certify preservation of external observations or clocks. -/
structure ReadoutBridge (S T O P C D : Type*) where
  state : Tendril S T
  observation : Tendril O P
  clock : Tendril C D

/-- Compose only bridges with precisely matching intermediate carriers. -/
def bridgeComp {A B C OA OB OC TA TB TC : Type*}
    (f : ReadoutBridge B C OB OC TB TC)
    (e : ReadoutBridge A B OA OB TA TB) :
    ReadoutBridge A C OA OC TA TC where
  state := f.state.comp e.state
  observation := f.observation.comp e.observation
  clock := f.clock.comp e.clock

/-- The metric defect retains its bilinear source carrier and is never
identified with observation or clock-readout differences. -/
def metricRemainder {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) : LocalForm S :=
  defect A.local B.local e.state

/-- A typed linear remainder in the target observation carrier. -/
def observationRemainder {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) : Tendril S P :=
  e.observation.comp A.observe - B.observe.comp e.state

/-- A separately typed linear remainder in the target clock carrier. -/
def clockRemainder {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) : Tendril S D :=
  e.clock.comp A.clockReadout - B.clockReadout.comp e.state

/-- The observation square commutes exactly when its *own* remainder is zero. -/
theorem observationRemainder_zero_iff_commutes {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) :
    observationRemainder A B e = 0 ↔
      e.observation.comp A.observe = B.observe.comp e.state := by
  unfold observationRemainder
  exact sub_eq_zero

/-- Clock-readout compatibility is independent of observation compatibility. -/
theorem clockRemainder_zero_iff_commutes {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) :
    clockRemainder A B e = 0 ↔
      e.clock.comp A.clockReadout = B.clockReadout.comp e.state := by
  unfold clockRemainder
  exact sub_eq_zero

/-- The geometric remainder still composes in the source bilinear carrier. -/
theorem metricRemainder_comp {A B C OA OB OC TA TB TC : Type*}
    (X : ObservedWorldlet A OA TA)
    (Y : ObservedWorldlet B OB TB)
    (Z : ObservedWorldlet C OC TC)
    (e : ReadoutBridge A B OA OB TA TB)
    (f : ReadoutBridge B C OB OC TB TC) :
    metricRemainder X Z (bridgeComp f e) =
      metricRemainder X Y e + pullback e.state (metricRemainder Y Z f) :=
  defect_comp X.local Y.local Z.local e.state f.state

/-- When readout bridges compose, the observer remainder follows a typed
two-term law rather than being conflated with the metric defect. -/
theorem observationRemainder_comp {A B C OA OB OC TA TB TC : Type*}
    (X : ObservedWorldlet A OA TA)
    (Y : ObservedWorldlet B OB TB)
    (Z : ObservedWorldlet C OC TC)
    (e : ReadoutBridge A B OA OB TA TB)
    (f : ReadoutBridge B C OB OC TB TC) :
    observationRemainder X Z (bridgeComp f e) =
      f.observation.comp (observationRemainder X Y e) +
        (observationRemainder Y Z f).comp e.state := by
  apply LinearMap.ext
  intro v
  change f.observation (e.observation (X.observe v)) -
      Z.observe (f.state (e.state v)) =
    f.observation (e.observation (X.observe v) - Y.observe (e.state v)) +
      (f.observation (Y.observe (e.state v)) -
        Z.observe (f.state (e.state v)))
  rw [map_sub]
  abel

/-- Clock readout remainders compose independently in their target type.
This does NOT assert actual synchronized physical time. -/
theorem clockRemainder_comp {A B C OA OB OC TA TB TC : Type*}
    (X : ObservedWorldlet A OA TA)
    (Y : ObservedWorldlet B OB TB)
    (Z : ObservedWorldlet C OC TC)
    (e : ReadoutBridge A B OA OB TA TB)
    (f : ReadoutBridge B C OB OC TB TC) :
    clockRemainder X Z (bridgeComp f e) =
      f.clock.comp (clockRemainder X Y e) +
        (clockRemainder Y Z f).comp e.state := by
  apply LinearMap.ext
  intro v
  change f.clock (e.clock (X.clockReadout v)) -
      Z.clockReadout (f.state (e.state v)) =
    f.clock (e.clock (X.clockReadout v) - Y.clockReadout (e.state v)) +
      (f.clock (Y.clockReadout (e.state v)) -
        Z.clockReadout (f.state (e.state v)))
  rw [map_sub]
  abel

/-- The three remainders remain distinct, with their own zero conditions. -/
def JointlyCompatible {S T O P C D : Type*}
    (A : ObservedWorldlet S O C) (B : ObservedWorldlet T P D)
    (e : ReadoutBridge S T O P C D) : Prop :=
  metricRemainder A B e = 0 ∧
    observationRemainder A B e = 0 ∧
      clockRemainder A B e = 0

/-- Compatibility survives a two-bridge composition only when all three
separate geometric, observation and clock obligations vanish on both legs. -/
theorem jointlyCompatible_comp {A B C OA OB OC TA TB TC : Type*}
    (X : ObservedWorldlet A OA TA)
    (Y : ObservedWorldlet B OB TB)
    (Z : ObservedWorldlet C OC TC)
    (e : ReadoutBridge A B OA OB TA TB)
    (f : ReadoutBridge B C OB OC TB TC)
    (he : JointlyCompatible X Y e)
    (hf : JointlyCompatible Y Z f) :
    JointlyCompatible X Z (bridgeComp f e) := by
  rcases he with ⟨hge, hoe, hce⟩
  rcases hf with ⟨hgf, hof, hcf⟩
  constructor
  · rw [metricRemainder_comp, hge, hgf, pullback_zero]
    simp
  constructor
  · rw [observationRemainder_comp, hoe, hof]
    simp
  · rw [clockRemainder_comp, hce, hcf]
    simp

end AionFormal.Instrumented
