import UnitDimensions

/-!
# Ordered local clock readouts with typed synchronization remainders

Each clock has a separate tag type, its own indexed reading, and a proof
of strict monotonicity. An interclock bridge explicitly provides a
strictly order-preserving tick map and a positive-rate affine
calibration (rate, epoch offset).

Residual zero is an INDEPENDENT requirement. A positive rate and
strictly increasing clocks do not imply synchronized epochs.
These are discrete, monotone real readouts, not certified physical
oscillators, relativity, drift uncertainty, or an SI-traceable clock.
-/

namespace AionFormal.Clocks

/-- A clock with its own identity-tag and ordered real local readings. -/
structure LocalClock (Tag : Type*) where
  read : ℕ → ℝ
  increasing : StrictMono read

/-- A strictly increasing correspondence between tick indices.
The tags prevent accidental identification of unrelated clocks. -/
structure TickBridge (A B : Type*) where
  forward : ℕ → ℕ
  increasing : StrictMono forward

/-- A positive-rate affine change of units and epoch of a clock reading. -/
structure AffineCalibration where
  rate : ℝ
  rate_pos : 0 < rate
  offset : ℝ

def applyCalibration (a : AffineCalibration) (x : ℝ) : ℝ :=
  a.rate * x + a.offset

def composeCalibration (outer inner : AffineCalibration) :
    AffineCalibration where
  rate := outer.rate * inner.rate
  rate_pos := mul_pos outer.rate_pos inner.rate_pos
  offset := outer.rate * inner.offset + outer.offset

theorem applyCalibration_comp (outer inner : AffineCalibration)
    (x : ℝ) :
    applyCalibration (composeCalibration outer inner) x =
      applyCalibration outer (applyCalibration inner x) := by
  dsimp [applyCalibration, composeCalibration]
  ring

/-- A positive-rate affine calibration preserves strict reading order. -/
theorem calibrated_order (a : AffineCalibration) :
    StrictMono (applyCalibration a) := by
  intro x y hxy
  have hm := mul_lt_mul_of_pos_left hxy a.rate_pos
  dsimp [applyCalibration]
  linarith

/-- Compose typed monotone index correspondences in their given order. -/
def composeTicks {A B C : Type*}
    (f : TickBridge B C) (e : TickBridge A B) : TickBridge A C where
  forward := fun n => f.forward (e.forward n)
  increasing := by
    intro i j hij
    exact f.increasing (e.increasing hij)

/-- A clock bridge explicitly carries independent tick and calibration maps. -/
structure ClockBridge (A B : Type*) where
  ticks : TickBridge A B
  calibration : AffineCalibration

def composeBridge {A B C : Type*}
    (f : ClockBridge B C) (e : ClockBridge A B) : ClockBridge A C where
  ticks := composeTicks f.ticks e.ticks
  calibration := composeCalibration f.calibration e.calibration

/-- Difference between calibrated source readout and target readout
at the declared corresponding tick. The sign convention is explicit. -/
def residual {A B : Type*}
    (X : LocalClock A) (Y : LocalClock B)
    (e : ClockBridge A B) (n : ℕ) : ℝ :=
  applyCalibration e.calibration (X.read n) -
    Y.read (e.ticks.forward n)

/-- Synchronization is an independent exact condition on ALL source ticks. -/
def Exact {A B : Type*}
    (X : LocalClock A) (Y : LocalClock B)
    (e : ClockBridge A B) : Prop :=
  ∀ n : ℕ, residual X Y e n = 0

theorem residual_zero_iff {A B : Type*}
    (X : LocalClock A) (Y : LocalClock B)
    (e : ClockBridge A B) (n : ℕ) :
    residual X Y e n = 0 ↔
      applyCalibration e.calibration (X.read n) =
        Y.read (e.ticks.forward n) := by
  unfold residual
  exact sub_eq_zero

/-- Composition keeps the clock remainder rather than erasing it.
The source error is scaled by the outer calibration rate. -/
theorem residual_comp {A B C : Type*}
    (X : LocalClock A) (Y : LocalClock B) (Z : LocalClock C)
    (e : ClockBridge A B) (f : ClockBridge B C) (n : ℕ) :
    residual X Z (composeBridge f e) n =
      f.calibration.rate * residual X Y e n +
        residual Y Z f (e.ticks.forward n) := by
  dsimp [residual, composeBridge, composeTicks,
    composeCalibration, applyCalibration]
  ring

/-- Exact synchronization is closed under composition, with independently
provided exactness certificates on both legs. -/
theorem exact_comp {A B C : Type*}
    (X : LocalClock A) (Y : LocalClock B) (Z : LocalClock C)
    (e : ClockBridge A B) (f : ClockBridge B C)
    (he : Exact X Y e) (hf : Exact Y Z f) :
    Exact X Z (composeBridge f e) := by
  intro n
  rw [residual_comp, he n, hf (e.ticks.forward n)]
  ring

/-- The target clock remains ordered along a declared monotone bridge,
regardless of whether the calibration residual vanishes. -/
theorem target_readout_ordered {A B : Type*}
    (Y : LocalClock B) (e : ClockBridge A B) :
    StrictMono (fun n : ℕ => Y.read (e.ticks.forward n)) := by
  intro i j hij
  exact Y.increasing (e.ticks.increasing hij)

/-- An explicit monotone clock, using its own local Nat tick coordinate. -/
def natClock (Tag : Type*) : LocalClock Tag where
  read := fun n => (n : ℝ)
  increasing := by
    intro i j hij
    change (i : ℝ) < (j : ℝ)
    exact_mod_cast hij

def identityTicks (Tag : Type*) : TickBridge Tag Tag where
  forward := fun n => n
  increasing := by
    intro i j hij
    exact hij

/-- Increasing and positive-rate but deliberately epoch-shifted. -/
def shiftedBridge (Tag : Type*) : ClockBridge Tag Tag where
  ticks := identityTicks Tag
  calibration := {
    rate := 1
    rate_pos := by norm_num
    offset := 1
  }

/-- Monotonicity does NOT entail exact synchronization. The +1 epoch
shift is a verified counterexample even though both clocks increase. -/
theorem epoch_shift_not_exact (Tag : Type*) :
    ¬ Exact (natClock Tag) (natClock Tag) (shiftedBridge Tag) := by
  intro h
  have hzero := h 0
  norm_num [residual, natClock, shiftedBridge, identityTicks,
    applyCalibration] at hzero

end AionFormal.Clocks
