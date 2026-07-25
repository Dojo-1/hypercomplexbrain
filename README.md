# hypercomplexbrain — AION-Ω^Q / QΣ-R

An audited almost-all-quantum polycosmic brain architecture, and the harness that
grades it.

The architecture is in **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

## The one-line correction

QΣ∞ measured quantumness by counting edges written as unitaries. That metric returns
**1.0000 for every core you can build** — its minimum equals its maximum across 150
random cognitive cores, so it cannot rank two designs or detect a regression.

QΣ-R measures quantumness by what a classical simulator is forced to pay:

```
Q_cert = log2(C_sim) / n            # fraction of the Hilbert-space exponent
```

```
                                          Q_naive   Q_cert
classical reversible core                  1.0000   0.0000
GHZ (maximal entanglement, zero magic)     1.0000   0.0000
random Clifford, depth 40                  1.0000   0.0000
Clifford + 35 T                            1.0000   0.9992
Hadamard + Toffoli (Grover-shaped)         1.0000   1.0000
```

## What this buys

Six results the draft architecture stated as targets, now decided by measurement:

- **Coherentization is not a residency gain.** Certified gain is 5.2% of advertised,
  and is bought by spending more magic, not by new capability.
- **Exhalation is forced**, by ancilla accounting and Bennett pebbling — not chosen
  by taste. The breath period is computable.
- **Entanglement is not quantumness** and is not even frame-invariant (0 bits in one
  frame, 1 bit in another, same situation).
- **The fusion grammar is coherent and order-sensitive**: pentagon and hexagon hold
  to 1e-16 while the associator is 1.11.
- **Identity capacity is `rank(G)`, not the count of holonomies.** Five loops, capacity
  three.
- **Self-tomography is impossible.** No-cloning is a sharper bound than Löb, which is
  why the evidence membrane is external for physical rather than governance reasons.

And one budget the draft never wrote down: `Q_cert ≥ 0.95` costs **4.16 non-Clifford
operations per logical qubit per episode** — about 830 magic states and ~10⁵ coherent
episodes on a 200-logical-qubit machine.

## Run it

```bash
pip install qiskit numpy scipy pytest

python3 experiments/run_audit.py      # every claim, computed
python3 experiments/acaf_sweep.py     # 150-core falsification sweep
python3 -m pytest tests/ -q           # 22 tests
```

## Layout

```
src/aionq/
  residency.py      certified quantum residency Q_cert
  coherentize.py    Stinespring coherentization and what it actually buys
  budget.py         coherence budget, forced breath schedule, magic budget
  process.py        process tensors and measurable temporal memory
  fusion.py         Fibonacci fusion grammar, pentagon/hexagon verification
  identity.py       polyholonomic identity, Gram PSD theorem, frame invariance
  selfknowledge.py  no-cloning bound on self-tomography
  qrf.py            quantum reference frames
experiments/        audit and ACAF sweep
tests/              one test per falsifiable claim
docs/ARCHITECTURE.md
```

## Status

`Q_cert` is an **upper bound on classical hardness** built from the simulation
strategies implemented here (basis-permutation, stabilizer, stabilizer rank). A better
classical algorithm lowers it. That direction is correct: the metric can only be
revised downward by classical progress, never inflated by notation.

Nothing here connects `Q_cert` to cognitive performance. The architecture is now
auditable; it is not yet justified. That gap is stated in
[`docs/ARCHITECTURE.md` §7](docs/ARCHITECTURE.md).

Not a consciousness claim, not an AGI claim, not a completed proof.
