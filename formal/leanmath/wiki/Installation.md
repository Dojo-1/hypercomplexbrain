# Installation

## Prerequisites

- **Lean 4** toolchain `v4.32.0-rc1` or later
- **Mathlib4** (automatically fetched via lake)

## Clone the Repository

```bash
git clone https://github.com/jesusvilela/leanmath.git
cd leanmath
```

## Build

```bash
lake build
```

This fetches mathlib4 and builds all modules.

## Verify

All theorems are verified:
- Cayley-Dickson recurrence (levels 1-3 and ≥4)
- Octonion alternativity and norm multiplicativity
- Dirac operator self-adjointness and square identity
- Three hypercomplex mind games with complete proofs

## Troubleshooting

### Lean toolchain mismatch

If you get toolchain errors, check your lean-toolchain:
```bash
cat lean-toolchain
# Should be: leanprover/lean4:v4.32.0-rc1
```

### Lake build fails

Try fetching cache:
```bash
lake exe cache get
lake build
```

## Repository Structure

```
leanmath/
├── Algebra/                    # Cayley-Dickson construction
├── Geometry/                   # Geometric operators
├── Computation/                # Turing halting in hypercomplex spaces
├── Mind/                       # Hypercomplex mind games
├── HardnessHolonomy.lean       # Five carriers
├── GRD.lean                    # Geodesic Resonance Descent
├── CLAUDE.md                   # AI/LLM instructions
├── SPECIFICATION.md            # Mathematical specification
└── wiki/                       # Documentation
```
