# One metre, two clocks, and three separate promises

*A reader's route through the next Worldlet formalization.*

**Research conception and direction:** Jesús Vilela Jato · Dojo-1.
Formalization and implementation have used AI assistance. The repository's
[CC BY 4.0](../LICENSE) covers original material the licensor controls,
subject to [authorship and third-party provenance](../ATTRIBUTION.md).

## The story

Imagine one Worldlet reports that an object is **one metre** long.
A second reports **one hundred centimetres**. Their numerical
readings are different, yet the declared conversion reconciles them.

Now imagine another Worldlet reports **one second**. The fact that
this reading also happens to be "one" does not make it a length.
A number becomes an observation only with a declared *dimension*,
instrument and interpretation.

And imagine two clocks that run strictly forward, but the second
reads one second later. Monotonicity cannot certify they are synchronized.

This project deliberately refuses to disguise these distinctions
behind one compatibility score. Each has its own type, calculation,
obligation, and failure mode.

## 1. A quantity wears its physical dimension

[UnitDimensions.lean](UnitDimensions.lean) represents a dimension by
SEVEN integers. Each integer is an exponent on one SI base unit.

| Slot | Meaning |
|---|---|
| 0 | Length |
| 1 | Mass |
| 2 | Time |
| 3 | Electric current |
| 4 | Temperature |
| 5 | Amount of substance |
| 6 | Luminous intensity |

For example, speed corresponds to one length exponent minus one time
exponent. Multiplying quantities adds their dimension vectors.

The Lean type **Quantity d** carries the dimension index d, so its
ordinary addition and unit conversion cannot mix length and time.
The formal theorem **length_not_time** certifies the distinction.

For an explicitly supplied positive conversion factor c, the rule is

\[
\operatorname{convert}(c,q)=c\,q.
\]

Theorems check that positive conversions compose and preserve
positive magnitudes. The example **metresToCentimetres** has factor
100; Lean verifies that converting a magnitude 1 produces 100.

The **value** of that factor is supplied as a standard convention,
not independently established by proof. Temperature offsets,
logarithmic decibels, uncertainty, laboratory traceability and
sensor calibration are NOT licensed by this simple ratio conversion.

## 2. There is more than one clock

[MonotoneClocks.lean](MonotoneClocks.lean) associates a local clock
with its own identity tag, a discrete sequence of real readings,
and a Lean proof of **strictly increasing** readings.

To compare two clocks, a bridge must separately declare:

- a strictly increasing **tick correspondence** φ;
- a strictly positive rate a;
- an epoch offset b.

The predicted target reading is

\[
t_B^{\mathrm{predicted}}(n)=a\,t_A(n)+b.
\]

But being able to *predict* is different from being *correct*. The
exact signed clock remainder is

\[
R_C(n)=a\,t_A(n)+b-t_B(\phi(n)).
\]

Exact synchronization requires **R_C(n)=0 for every source tick n**.
A positive rate alone only preserves the ordering of readings.

For two composable clock bridges e and f, Lean targets the identity

\[
R_C^{f\circ e}(n)=a_fR_C^e(n)+R_C^f(\phi_e(n)).
\]

It also proves that two exact clock bridges compose to an exact
bridge. The deliberately wrong +1 epoch shift is a negative
control: both clocks advance strictly, yet their remainders remain
nonzero.

These are **discrete mathematical time readouts**, not the clock
hardware calibration, latency constraints, relativity, uncertainty
bounds, or synchronization protocols needed for real systems.

## 3. Three distinct remainders travel with a Worldlet

[CalibratedWorldlet.lean](CalibratedWorldlet.lean) combines a
previously verified **positive** state geometry with a
dimension-indexed real linear observation and an independently
tagged local clock.

Its bridge has three declared components:

1. a state tendril T;
2. a strictly positive, same-dimension observer conversion u;
3. a typed clock bridge (φ,a,b).

It does NOT infer the second and third from the first.

The geometric remainder belongs to the source **bilinear-form**
carrier:

\[
R_g=T^*g_Y-g_X.
\]

The chosen, dimension-indexed observer reports a separate scalar
for each source state v:

\[
R_O(v)=u\,O_X(v)-O_Y(Tv).
\]

The clock remainder belongs to the discrete source tick domain:

\[
R_C(n)=a\,t_X(n)+b-t_Y(\phi(n)).
\]

These are not three names for one scalar. They differ in input,
codomain and composition law:

\[
R_g^{f\circ e}=R_g^e+T_e^*R_g^f,
\]

\[
R_O^{f\circ e}(v)=u_fR_O^e(v)+R_O^f(T_ev),
\]

\[
R_C^{f\circ e}(n)=a_fR_C^e(n)+R_C^f(\phi_e(n)).
\]

The integrated **JointlyCompatible** predicate asks for all
three remainders to vanish independently. The formalization checks
that two jointly compatible bridges compose to a jointly compatible
bridge. Because their state geometries are positive, exact geometric
agreement also forces the tendril to be injective.

The observer here is ONE typed linear readout. A vector of distinct
physical measurement dimensions, affine sensor biases, correlated
uncertainties and nonlinear observables require additional structure.

## Four small negative controls

- **Geometry is perfect, observer disagrees.** Identity state map,
  identical positive metrics, but target observer reads zero.
  Then R_g=0 while R_O is nonzero.
- **Geometry and observer agree, epoch differs.** Both clocks strictly
  increase but one has a +1 offset: R_C is nonzero.
- **A positive embedding is not an equivalence.** A 2→3 injective
  tendril can preserve source geometry without reaching the third
  target direction.
- **One second is not one metre.** A time quantity cannot be supplied
  to the typed conversion expecting a length quantity.

## What has *not* been proved?

The mathematical model does not establish SI-traceable calibration,
real-clock synchronization, shared semantics between observers,
nonlinear or stochastic dynamics, physical quantum implementations,
artificial cognition or consciousness.

A fresh successful pinned Lean/Lake build supplies P-level evidence
for the encoded theorem. NumPy tests are bounded M-level controls.
Broader meanings remain S/H. A failure is retained as a correction
rather than silently reclassified.

## Follow it into Lean

The native formal project pins **Lean 4.27.0** and a specific Mathlib
commit in [lakefile.lean](lakefile.lean). The full source trail is:

- [UnitDimensions.lean](UnitDimensions.lean) — quantities and unit factors.
- [MonotoneClocks.lean](MonotoneClocks.lean) — plural ordered clocks.
- [CalibratedWorldlet.lean](CalibratedWorldlet.lean) — integrated bridge.
- [ProofAudit.lean](ProofAudit.lean) — the exact named axiom inventory.
- [Numerical adversarial controls](../tests/test_typed_units_clocks.py).

From a local repository clone, enter the formal directory and run:

    lake exe cache get
    lake build
    lake env lean ProofAudit.lean

Only a successful run **at the relevant commit** supports the proof
claims. The imported historical LeanMath archive remains outside
the native target and is not promoted by these checks.
