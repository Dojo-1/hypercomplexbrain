# QSigma-R1U — Non-abelian semidirect symmetry under time-dependent noise

**Status:** MEASURED negative result / self-attested. Preregistered claim killed.

**Frozen preregistration:** `d6df2240eed7fe1bf18ecedce31aff8e2d7ea77a`

This round injected a capacity-matched pair of 16-element regular group actions into the projected-superposition experiment from R1T:

- abelian control: `Z4 x Z4`;
- non-abelian treatment: `Z4 semidirect Z4` with inversion action,
  `a^4=b^4=e`, `b a b^-1 = a^-1`.

Both act on the same sixteen projected amplitudes. The same realized time-dependent noisy generator word is used for both groups. Three frozen noise profiles were used: ramp, sinusoid, and burst. Forward and reversed schedules contain exactly the same realized generator multiset; reversal changes chronology only.

## Structural gate

The non-abelian commutator is nontrivial:

`a b a^-1 b^-1 = (2,0)`

while the abelian control gives identity. Regular actions are bijections on all sixteen labels.

## Preregistered prediction

The round required both:

1. different non-abelian forward/reverse endpoint permutations in at least 75% of nontrivial cells;
2. at least one R1T projected-wavefunction metric to differ above `1e-8` in at least 50% of nondegenerate non-abelian cells.

The abelian forward/reverse control was required to remain identical.

## Measurement

The bounded local sweep used 8 projection seeds x 8 noise seeds x 3 temporal profiles = 192 matched cells per group, 384 group rows total.

Abelian control:

- forward/reverse endpoint permutation disagreement: `0.0` in every row;
- global forbidden-mass defect: `0.0`;
- sector forbidden-mass defect: `0.0`;
- off-diagonal forbidden-interference defect: `0.0`;
- maximum interference-closure defect: `2.22e-16`.

Non-abelian treatment:

- endpoint permutation disagreement positive in `0.50` of rows, median `0.5`, maximum `1.0`;
- global forbidden-mass defect: `0.0` in every row;
- sector forbidden-mass defect: `0.0` in every row;
- off-diagonal forbidden-interference defect: `0.0` in every row;
- maximum interference-closure defect: numerical zero in this bounded run.

## Verdict

**KILLED.** Both preregistered positive gates fail.

The non-abelian chronology is not absent: in half the cells, forward and reversed words induce different regular permutations. What fails is the proposed observer. The frozen R1T endpoint observables quotient those different carrier permutations to the same values.

Therefore the strongest supported statement is narrower:

> On this 16-state testbed, the injected `Z4 semidirect Z4` regular action retains time-order information at the carrier-permutation level, but the R1T endpoint tuple `(global forbidden mass, sector forbidden mass, off-diagonal forbidden interference)` is blind to that order information under the tested noisy schedules.

This is not evidence that non-abelian symmetry has no effect in general. It is evidence that this specific projected-partition observer does not resolve the effect.

## Most damaging obstruction

The metric blindness is exact across the bounded sweep despite non-identical endpoint permutations. Changing thresholds cannot rescue the claim. A future round would need a genuinely finer observable—e.g. time-resolved partition transport, noncommutative character data, or history-sensitive holonomy—but R1U does not add one after seeing the failure.

## Evidence ledger

- **P relative to the finite implementation:** the group laws, presentation relation, and left-regular permutations are exact finite objects.
- **M:** the bounded deterministic seed sweep and committed aggregate measurement summary.
- **R:** the preregistered claim that non-abelian chronology would be visible in the existing R1T endpoint wavefunction metrics.
- **H/S retained:** richer observers may expose the chronology; not tested here.
- **No independent witness.**

## Typed remainder

- `[R]_observer-blindness` — current endpoint observables erase the measured carrier-order distinction.
- `[R]_noise-model` — noise is an abstract time-dependent generator substitution process, not calibrated device noise.
- `[R]_group-family` — only one 16-element semidirect product is tested.
- `[R]_witness` — same GPT development line produced and evaluated the round.

## Stop rule

R1U stops on the killed gate. No post-hoc replacement metric, larger semidirect family, continuous noise model, sheaf, adiabatic, or holoportation lift is added to this round.
