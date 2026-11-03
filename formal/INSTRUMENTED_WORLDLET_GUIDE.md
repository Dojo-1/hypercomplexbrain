# One geometric bridge, three things to check

**Research conception and direction:** Jesús Vilela Jato (Dojo-1).
AI-assisted formalization and review. Repository-controlled materials are
licensed under [CC BY 4.0](../LICENSE), subject to the
[authorship and third-party rights notice](../ATTRIBUTION.md).

Two Worldlets can agree perfectly about geometry and still disagree on
what their observers report. They may also use different clock readouts.
Treating those three questions as one scalar loses exactly the information
we want to preserve.

## Three separate instruments

A local Worldlet now has an independent *state carrier*, an observation
carrier, and a clock-readout carrier. Each may have its own type and
dimension. A bridge declares all three maps:

- A linear transport between the state carriers.
- A linear conversion between the observation carriers.
- A separate linear conversion between the clock-readout carriers.

The metric remainder is the full source bilinear-form defect:

\[
R_g = T^*g_Y-g_X.
\]

The observation remainder measures the failure of its own commuting
square, with observation maps \(O_X,O_Y\) and declared conversion \(U\):

\[
R_O = U O_X-O_Y T.
\]

The clock-readout remainder has its own clock maps \(C_X,C_Y\) and
conversion \(V\):

\[
R_C = V C_X-C_Y T.
\]

The three outputs have **different mathematical types**. A zero value
in one does not entitle us to erase the others.

## How they compose

Suppose X→Y carries bridge \(e\), and Y→Z carries bridge \(f\).
Then:

\[
R_g^{f\circ e}=R_g^e+T_e^*R_g^f,
\]

\[
R_O^{f\circ e}=U_f R_O^e+R_O^f T_e,
\]

\[
R_C^{f\circ e}=V_f R_C^e+R_C^f T_e.
\]

These are three *different* typed composition laws. A complete
compatibility contract asks for all three remainders to vanish.
The new Lean module proves preservation of that joint contract under
composition.

## One easy negative control

Take the same geometric identity map, with identical Euclidean source
and target forms. Its metric remainder is zero.

Now let the source observer read the first coordinate while the
target observer returns zero. Even with an identity conversion,
the observation remainder is nonzero. If a separate clock-readout
map disagrees, the third remainder can be nonzero independently.

A Python negative control constructs precisely this example, and a
mixed-dimensional test verifies the three composition identities.

## What this does not certify

All three maps are *linear readout models*. The clock channel is NOT
yet an order-preserving synchronization of physical time. The declared
observation conversion is NOT a proof of dimensional consistency in SI
units, calibrations, or common semantics.

In particular, zero geometric and readout remainders are necessary
conditions *under the chosen instruments*. They cannot prove that
two Worldlets express the same meaning, recognize each other, possess
the same identity, or realize a quantum advantage.

The next honest mathematical question is to attach explicit unit
dimensions and calibrated or monotone clock comparisons without
replacing all clocks with a single global scalar.

[Lean source](InstrumentedWorldlet.lean) ·
[Axiom inventory](ProofAudit.lean) ·
[Independent numerical controls](../tests/test_instrumented_worldlet.py).

**Evidence:** checked Lean claims are P only for the exact encoded
linear instruments; Python checks are bounded M; semantic and
physical interpretations remain H/S. Incompatible observations must
leave their typed remainders visible.
