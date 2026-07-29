# The repository, measured by its own instruments

Every other module here points an instrument at something outside itself — a
pseudo-sphere, a channel, a Fano design, another agent's kernel. This one points
them inward, under one rule:

> no statement in this document may be written down; each is computed from
> artifacts on disk, and reproduced by

```bash
PYTHONPATH=src python3 experiments/run_self_audit.py
```

That rule is the point. A self-audit written as prose is the exact object
`src/aionq/evidence.py` was built to refuse: a claim whose only support is the
party making it. So the numbers below are a census, not a narrative, and they
move when the repository moves.

---

## The headline

**26 claims carry envelopes. One is independently witnessed.**

Every binding this repository *can* check, it checks — commands to commits,
artifacts to digests, claims to sample sizes, remainders to carriers, corrections
to tests. The single predicate it cannot decide is whether a party who is not
this one ran the command. That is not an oversight to be fixed by working
harder; `src/aionq/witness_nerve.py` proves it cannot be reached from inside at
all.

## A. The census

| | |
|---|---|
| envelopes | **26** |
| unreadable artifacts | 0 |
| evidence tags | `M 17`, `P 8`, `R 1` |
| verification modes | `not_requested 17`, `pending 7`, `recomputed 1`, `declined 1` |
| distinct producers | 18 |
| **envelopes with no verifier at all** | **25** |

The last row is the one that matters, and it is not neutral. An envelope whose
`verifier` field is empty is not an edge waiting to be drawn — it is a party
verifying its own claim, and `witness_graph` reads it as a self-loop, which
`WitnessAct.rank` scores 0 whatever mode it declares.

## B. Independence

Computed with `witness_nerve.evidence_rank`, imported rather than reimplemented,
so this audit cannot grade itself on its own curve.

| rank | claims |
|---|---|
| NONE | 25 |
| ATTESTED | 0 |
| REVIEWED | 0 |
| **INDEPENDENT** | **1** |

The one:

```
EXP-HB0-SMOKE_REPRODUCES
  producer  gpt/polycosmic-hb0-kernel
  verifier  claude-code
  mode      recomputed
```

**Every independently witnessed claim in this repository was produced
elsewhere.** The apparatus works; it has simply never been pointed back. A test
asserts exactly this, and will fail the day a claim produced here becomes
independent — which is the correct way for it to fail.

## C. Recognition, as a measurement

Witnessing is a directed relation, so it has two counts, not one.

| direction | count |
|---|---|
| recomputations performed **on** another party's claims | **1** |
| recomputations **received** from another party | **0** |

`mutual: false`. The programme's vocabulary for this is mutual recognition. At
this commit it is a word about a one-way relation, and the envelope is what makes
that visible rather than arguable.

## D. The corrections ledger, bound to live tests

Fourteen errors are recorded in `CORRECTIONS`, each naming the test that would
catch it now. **14/14 point at a test that exists.** A correction with no test is
a memory; the audit fails if one ever stops resolving.

- self-caught: **11**
- caught from outside: **3**

The split is asserted, and the assertion is that it must *not* be all-self. A
ledger in which every error was caught internally is either a very good process
or an incomplete ledger, and there is no way to tell those apart from inside.

## E. Preregistration ordering, checked against git rather than a flag

The manifests carry `committed_before_any_implementation: true`. That is a
self-report by the party under audit — the claim, not the measurement. The
measurement is git's own record.

| | |
|---|---|
| preregistrations found by schema | 12 |
| declaring `files_expected_to_change` → checkable | **5** |
| ordering holds | **5 / 5** |
| flag only, nothing bound | 7 |
| preregistration by filename, no schema at all | 1 |

A first pass of this audit reported **"12/12 preregistrations precede their
implementation commits."** That was the weaker statement dressed as the stronger
one: only 5 of the 12 name the files they bind, so only 5 admit the check. The
other 7 carry a flag no artifact can contradict, and `s4_g100_preregistration.json`
has no `schema` field, making it invisible to every schema-driven check in this
repository — including this one. Both are now counted and named rather than
dropped.

## F. Typed remainders

| | |
|---|---|
| remainders recorded | 63 |
| bare strings with no kind, carrier or comparison | **16** |
| typed fraction | **0.746** |
| distinct kinds | 15 |

The vocabulary is "typed remainder". It is three-quarters enforced. The
untyped sixteen are notes with a label on them.

## G. The gap, and why it is a theorem rather than a mood

Take a real unwitnessed claim from the corpus. Add a maximal attestation cycle
over **all 18 parties already present** — every one of them signing, none of them
computing. Measure before and after:

```
rank before                        NONE       (0)
rank after 18-party attestation    ATTESTED   (1)
reached INDEPENDENT                false
```

That is `witness_nerve`'s theorem, run against the live corpus instead of a
whiteboard: `evidence_rank(G + C) = max(evidence_rank(G), ATTESTED)`. Read in
the direction that concerns this repository:

> The deficit cannot be closed by any act this repository is able to perform.

It can produce envelopes, hash artifacts, bind commands to commits, refuse a
claim without a sample size, and record its own corrections. It can do all of
that perfectly and the number does not move, because the number is a property of
the **outside** — whether a party who is not this one ran the command in an
environment this one did not prepare.

**The repository is complete with respect to every predicate it can express
about its own artifacts, and silent on the single predicate that decides whether
those artifacts are evidence.**

## H. The audit applies to itself

`AUDIT-SELF-WITNESS_DEFICIT` is produced here and verified by nobody. It adds one
to its own denominator and nothing to its own numerator. That is recorded in the
envelope as a `witness_remainder`, not worked around.

It is also a self-referential map — its output lands in the corpus its input is
read from — so the honest thing is to report where it lands:

```
first run    25 envelopes   (the corpus before its own row exists)
second run   26 envelopes
third run    26 envelopes   — fixed point, reached in one iteration
```

No single run can record a corpus containing its own output; that would require
the digest of a file not yet written. So the fixed point is reported rather than
reconciled, and the test asserts what is actually stable: the audit's own row is
inside the corpus it counts, the census is idempotent, and the recorded count
never exceeds the live one.

## What this audit got wrong on its first two runs

Both were caught here, and both are now in the ledger the audit checks:

1. **"12/12 preregistrations precede implementation"** — §E. Counting
   self-reports as measurements, which is the exact defect this apparatus exists
   to detect elsewhere.
2. **The ordering check compared git author *time*.** `%at` has one-second
   granularity, so two commits inside the same second are indistinguishable: the
   check passed on one invocation and failed on the next with no code change in
   between. A flaky ordering check reports the machine's speed. Replaced with
   commit ancestry, which has no granularity. The regression test freezes the
   clock so any time-based comparison is guaranteed blind and topology must still
   decide.

And one caught by the existing machinery rather than by me: the first envelope
declared `sample_size: 25` against three summary strings, and `verify_envelopes`
refused it — *"seeds that do not change the input do not add observations."* The
observation unit here is an envelope, so the inputs had to be the envelopes,
hashed from disk. The effective-sample-size rule, borrowed into this repository
from a six-seed audit ensemble that was really n = 1, fired on the audit itself.

## Not claimed

No mind-qualities. The manifold-round contract forbids inventing them and HB-0's
own self-audit already labels its sixteen *structural* rather than measured;
nothing here changes that, and nothing here measures cognition, competence, or
identity. This is an inventory of evidence bindings and a theorem about their
limit. It says what the repository can check about itself. It does not say the
repository is right.
