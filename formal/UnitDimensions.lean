import InstrumentedWorldlet

/-!
# Physical dimension labels and positive calibration factors

A quantity is indexed by a SEVEN-component integer dimension vector
(length, mass, time, current, temperature, amount, luminous intensity).
This is a syntactic type discipline, not a laboratory calibration.
Conversions are permitted only inside one identical dimension type,
and require a strictly positive, explicitly supplied scale.

No coercion from length to time, or from energy to temperature, is
manufactured. Physical calibration and offset-sensitive temperature
units require additional contracts.
-/

namespace AionFormal.Units

/-- Exponents of the seven SI base dimensions, not one global scalar. -/
abbrev Dimension := Fin 7 → ℤ

def dimensionless : Dimension := fun _ => 0

/-- Standard basis for dimensional exponents. -/
def basisDim (i : Fin 7) : Dimension :=
  fun j => if j = i then 1 else 0

def lengthDim : Dimension := basisDim 0
def massDim : Dimension := basisDim 1
def timeDim : Dimension := basisDim 2

/-- Dimensional exponents of a product add pointwise. -/
def dimProduct (a b : Dimension) : Dimension :=
  fun i => a i + b i

/-- Dimensional exponents of a quotient subtract pointwise. -/
def dimQuotient (a b : Dimension) : Dimension :=
  fun i => a i - b i

/-- These are provably distinct types of readings, not convertible units. -/
theorem length_not_time : lengthDim ≠ timeDim := by
  intro h
  have h0 := congrArg (fun d : Dimension => d (0 : Fin 7)) h
  norm_num [lengthDim, timeDim, basisDim] at h0
  omega

theorem dimProduct_comm (a b : Dimension) :
    dimProduct a b = dimProduct b a := by
  funext i
  simp [dimProduct, add_comm]

theorem dimProduct_assoc (a b c : Dimension) :
    dimProduct (dimProduct a b) c = dimProduct a (dimProduct b c) := by
  funext i
  simp [dimProduct, add_assoc]

theorem dimProduct_dimensionless (d : Dimension) :
    dimProduct d dimensionless = d := by
  funext i
  simp [dimProduct, dimensionless]

theorem dimQuotient_self (d : Dimension) :
    dimQuotient d d = dimensionless := by
  funext i
  simp [dimQuotient, dimensionless]

/-- A magnitude together with its dimension-level index. -/
structure Quantity (d : Dimension) where
  magnitude : ℝ

/-- Addition is only defined when both quantities have the SAME dimension. -/
def add {d : Dimension} (x y : Quantity d) : Quantity d :=
  ⟨x.magnitude + y.magnitude⟩

/-- Multiplication changes the dimension in the result's TYPE. -/
def multiply {a b : Dimension}
    (x : Quantity a) (y : Quantity b) :
    Quantity (dimProduct a b) :=
  ⟨x.magnitude * y.magnitude⟩

/-- A user-supplied conversion factor between representations of one
dimension, with strict positivity as an explicit proof obligation. -/
structure UnitFactor (d : Dimension) where
  factor : ℝ
  positive : 0 < factor

/-- Converting units cannot change the physical dimension index. -/
def convert {d : Dimension}
    (c : UnitFactor d) (q : Quantity d) : Quantity d :=
  ⟨c.factor * q.magnitude⟩

def identity (d : Dimension) : UnitFactor d where
  factor := 1
  positive := by norm_num

def compose {d : Dimension}
    (outer inner : UnitFactor d) : UnitFactor d where
  factor := outer.factor * inner.factor
  positive := mul_pos outer.positive inner.positive

theorem compose_factor_positive {d : Dimension}
    (outer inner : UnitFactor d) :
    0 < (compose outer inner).factor :=
  (compose outer inner).positive

theorem convert_comp {d : Dimension}
    (outer inner : UnitFactor d) (q : Quantity d) :
    convert (compose outer inner) q = convert outer (convert inner q) := by
  cases q with
  | mk value =>
    change Quantity.mk ((outer.factor * inner.factor) * value) =
      Quantity.mk (outer.factor * (inner.factor * value))
    congr 1
    ring

theorem convert_identity {d : Dimension} (q : Quantity d) :
    convert (identity d) q = q := by
  cases q with
  | mk value =>
    change Quantity.mk (1 * value) = Quantity.mk value
    simp

theorem convert_preserves_positive {d : Dimension}
    (c : UnitFactor d) (q : Quantity d)
    (hq : 0 < q.magnitude) :
    0 < (convert c q).magnitude := by
  change 0 < c.factor * q.magnitude
  exact mul_pos c.positive hq

/-- For this declared calibration, a metre reading becomes 100 cm.
The value 100 is a supplied standard conversion, not measured by Lean. -/
def metresToCentimetres : UnitFactor lengthDim where
  factor := 100
  positive := by norm_num

theorem one_metre_is_one_hundred_centimetres :
    (convert metresToCentimetres (⟨1⟩ : Quantity lengthDim)).magnitude = 100 := by
  norm_num [convert, metresToCentimetres]

end AionFormal.Units
