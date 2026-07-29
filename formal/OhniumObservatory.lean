/-
  Ohnium Observatory — narrow discrete control surface.

  Scope:
  * the A/U/M cadence is a three-cycle;
  * an R40 trace has forty discrete frame indices;
  * the declared signal/crosstalk dimensions satisfy 7 + 21 = 28;
  * exact accounting and exact return follow from explicit hypotheses.

  This file does NOT formalize or prove the Hopf map, quantum Fisher
  information (QFI), adiabatic physics, quantum dynamics, cognition, or any
  physical interpretation of the observatory.  A/U/M are typed cadence labels
  in the Ohnium architecture.

  The artifact deliberately uses only Lean's core/prelude: no Mathlib import and
  no admitted theorem or placeholder proof.
-/

namespace OhniumObservatory

/-! ## A/U/M cadence -/

/-- The three typed cadence labels used by the Ohnium control clock. -/
inductive AUMPhase where
  | A
  | U
  | M
  deriving DecidableEq, Repr

/-- One deterministic cadence step. -/
def AUMPhase.next : AUMPhase → AUMPhase
  | .A => .U
  | .U => .M
  | .M => .A

/-- Three cadence steps return every phase to itself. -/
theorem AUMPhase.next_three (phase : AUMPhase) :
    phase.next.next.next = phase := by
  cases phase <;> rfl

/-! ## Fixed discrete audit dimensions -/

/-- R40 denotes exactly forty enumerated frame indices. -/
theorem r40_frame_count : (List.range 40).length = 40 := by
  decide

/-- The declared seven signal and twenty-one crosstalk coordinates fill 28
    discrete coordinate slots.  This is only an arithmetic identity; it does
    not prove a Lie-algebra decomposition. -/
theorem signal_crosstalk_dimension_count : 7 + 21 = 28 := by
  decide

/-! ## Hypothesis-driven accounting and return -/

/-- A minimal bridge carrying only the maps needed to state round-trip return. -/
structure Bridge (Source Landing : Type) where
  forward : Source → Landing
  backward : Landing → Source

/-- A bridge ledger records abstract natural-number accounting units.  These
    units are control telemetry, not physical energy. -/
structure Ledger where
  input : Nat
  landed : Nat
  discarded : Nat

/-- Exact control accounting means that landed plus discarded units reproduce
    the input units. -/
def Ledger.Exact (ledger : Ledger) : Prop :=
  ledger.input = ledger.landed + ledger.discarded

/-- If exact return and exact accounting are supplied as hypotheses, the paired
    control conclusion follows without strengthening either hypothesis. -/
theorem exact_return_and_accounting_of_hypotheses
    {Source Landing : Type}
    (bridge : Bridge Source Landing)
    (source : Source)
    (ledger : Ledger)
    (hReturn : bridge.backward (bridge.forward source) = source)
    (hAccounting : ledger.input = ledger.landed + ledger.discarded) :
    bridge.backward (bridge.forward source) = source ∧ ledger.Exact := by
  exact ⟨hReturn, hAccounting⟩

end OhniumObservatory
