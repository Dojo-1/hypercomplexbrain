# CLAUDE.md — LeanMath Repository Instructions

## Overview

This repository contains a Lean 4 formalization of Cayley-Dickson algebras (ℝ → ℂ → ℍ → 𝕆 → 𝕊), Dirac operators, connection Laplacians, Turing halting in non-scalar hypercomplex spaces, and hypercomplex mind games.

## Mathematical Context

The formalization is based on the "Weave Never Ends" thesis and related hypercomplex/hyperdimensional geometry research. Key concepts:

- **Cayley-Dickson construction**: R → C → H → O → S (doubling each level)
- **Hypercomplex holonomy**: Noncommutativity (i·j ≠ j·i) and nonassociativity ((ab)c ≠ a(bc)) in 𝕆
- **Dirac operator**: D = [0 B†; B 0] on H_V ⊕ H_E
- **Hardness holonomy**: Five carriers (diagonal, protensor, hypercomplex, sectionability, semantic)
- **Turing halting in 𝕆**: Undecidability as geometric obstruction (nonzero associator)

## Repository Structure

```
leanmath/
├── Algebra/                    # Cayley-Dickson construction
│   ├── Basic.lean              # Complex numbers, quaternions, wedge products
│   └── CD.lean                 # Full Cayley-Dickson: R→C→H→O→S (540+ lines)
│
├── Geometry/                   # Geometric operators
│   ├── Dirac.lean              # Finite Dirac operator (305 lines, complete)
│   └── ConnectionLaplacian.lean # Connection Laplacian and holonomy (791 lines)
│
├── Computation/                # Turing halting in hypercomplex spaces
│   ├── TuringHalting_Master.lean # Master theorem: holonomy barrier (56k+ lines)
│   ├── TuringHalting_LeanLake.lean # Lean-lake computational holonomy
│   └── TuringHalting_Hyperdim.lean # Hyperdimensional halting (91k+ lines)
│
├── Mind/                       # Hypercomplex mind games (244 lines, complete)
│   └── HypercomplexMindGames.lean
│
├── HardnessHolonomy.lean       # Five carriers, interpretation maps (77k+ lines)
├── GRD.lean                    # Geodesic Resonance Descent
│
├── CLAUDE.md                   # This file
├── SPECIFICATION.md            # Mathematical specification
└── docs/                       # Documentation and papers
```

## Key Conventions

1. **All files are in `noncomputable section`** — real numbers require classical choice
2. **Elements are `Fin (2^n) → ℝ`** — coordinate-based representation
3. **Multiplication by level**: `mulByLevel level` dispatches to explicit kernels for levels 0-4
4. **Conjugation by level**: `conjByLevel level` negates imaginary components
5. **Norm by level**: `normByLevel level` computes √(∑ x_i²)
6. **`embedFirst`/`embedSecond`** split/join A_{n-1} elements within A_n
7. **Proof style**: `ext i; fin_cases i; simp; ring` for finite case analysis

## Build Instructions

```bash
cd /path/to/leanmath
lake build
```

Requires Lean 4 toolchain `v4.32.0-rc1`. Mathlib4 is automatically fetched.

## Verification

All theorems are verified (lake build passes). Key proven results:

- Cayley-Dickson recurrence (levels 1-3 and ≥4)
- Octonion left alternativity
- Octonion norm multiplicativity (Hurwitz)
- Dirac operator self-adjointness and square identity
- Three hypercomplex mind games with complete proofs

## Remaining `sorry` Instances

Some theorems have `sorry` placeholders blocked on external dependencies:
- Formal machine model for Turing halting
- Empirical measurement framework
- Loop enumeration for holonomy sums

These are documented with explicit blockers.

## Style Guide

- Use `interval_cases` for level enumeration (0,1,2,3)
- Use `fin_cases i` for Fin n case analysis
- Use `ext i; ...; ring` for function equality proofs
- Document `sorry` with explicit justification and blocker description
- Keep proofs in the same file as the definitions
- Use `noncomputable` for real number operations
