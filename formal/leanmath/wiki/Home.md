# LeanMath Wiki

A Lean 4 formalization of Cayley-Dickson algebras, Dirac operators, connection Laplacians, Turing halting in non-scalar hypercomplex spaces, and hypercomplex mind games.

## Getting Started

See [Installation](Installation.md) for setup instructions.

## Mathematical Structure

```
ℝ (level 0) → ℂ (level 1) → ℍ (level 2) → 𝕆 (level 3) → 𝕊 (level 4)
   |              |              |              |              |
   +-- Algebra --+-- Algebra --+-- Algebra --+-- Algebra --+
   |              |              |              |              |
   +-- Geometry: Dirac operator, connection Laplacian
   |              |              |              |              |
   +-- Computation: Turing halting, quines, holonomy
   |              |              |              |              |
   +-- Mind: Hypercomplex mind games
```

## Key Concepts

### Cayley-Dickson Construction

The Cayley-Dickson construction builds a sequence of algebras:
- **Level 0 (ℝ)**: Real numbers, commutative and associative
- **Level 1 (ℂ)**: Complex numbers, commutative and associative
- **Level 2 (ℍ)**: Quaternions, noncommutative but associative
- **Level 3 (𝕆)**: Octonions, noncommutative and nonassociative
- **Level 4 (𝕊)**: Sedenions, noncommutative, nonassociative, nonalternative

Each level doubles the dimension. The multiplication follows:
`(a₀ + a₁·e) * (b₀ + b₁·e) = (a₀*b₀ - conj(b₁)*a₁) + (conj(a₀)*b₁ + b₀*a₁)·e`

### Holonomy

Holonomy measures the failure of transport to close. In hypercomplex algebras:
- **Noncommutativity** (i·j ≠ j·i): order holonomy
- **Nonassociativity** ((ab)c ≠ a(bc)): association holonomy
- **Norm multiplicativity**: holds for levels 0-3, fails at level 4+

### Dirac Operator

The Dirac operator D = [0 B†; B 0] on H_V ⊕ H_E satisfies:
- D† = D (self-adjoint)
- D² = [B B† 0; 0 B† B] (square identity)

### Hardness Holonomy

Five carriers for holonomy witnesses:
1. **Diagonal**: Semantic holonomy (self-recognition failure)
2. **Protensor**: Relational holonomy (non-reconstructible remainder)
3. **Hypercomplex**: Algebraic holonomy (associator/commutator)
4. **Sectionability**: Transport holonomy (frustration/irregularity)
5. **Semantic**: Verifier holonomy (proof/execution mismatch)

## Repository Structure

```
leanmath/
├── Algebra/                    # Cayley-Dickson construction
│   ├── Basic.lean              # Complex numbers, quaternions
│   └── CD.lean                 # Full Cayley-Dickson R→C→H→O→S
│
├── Geometry/                   # Geometric operators
│   ├── Dirac.lean              # Dirac operator (complete)
│   └── ConnectionLaplacian.lean # Connection Laplacian
│
├── Computation/                # Turing halting in hypercomplex spaces
│   ├── TuringHalting_Master.lean # Master theorem
│   ├── TuringHalting_LeanLake.lean
│   └── TuringHalting_Hyperdim.lean
│
├── Mind/                       # Hypercomplex mind games
│   └── HypercomplexMindGames.lean
│
├── HardnessHolonomy.lean       # Five carriers
├── GRD.lean                    # Geodesic Resonance Descent
│
├── CLAUDE.md                   # AI/LLM instructions
├── SPECIFICATION.md            # Mathematical specification
└── wiki/                       # This wiki
```

## Key Theorems

| Theorem | File | Statement |
|---------|------|-----------|
| `CayleyDicksonRecurrenceLow` | `Algebra/CD.lean` | Recurrence holds for levels 1-3 |
| `CayleyDicksonRecurrenceGeneral` | `Algebra/CD.lean` | Recurrence holds for level ≥ 4 |
| `mul_alternative_octonions` | `Algebra/CD.lean` | Left alternativity for 𝕆 |
| `norm_mul_octonions` | `Algebra/CD.lean` | Norm multiplicativity for 𝕆 (Hurwitz) |
| `dirac_self_adjoint` | `Geometry/Dirac.lean` | D† = D |
| `dirac_square` | `Geometry/Dirac.lean` | D² = [B B† 0; 0 B† B] |
| `null_cone_hides_activity` | `Mind/HypercomplexMindGames.lean` | Null courier sits on null cone |
| `order_holonomy` | `Mind/HypercomplexMindGames.lean` | i·j ≠ j·i in 𝕆 |
| `association_holonomy` | `Mind/HypercomplexMindGames.lean` | (e₁·e₂)·e₄ ≠ e₁·(e₂·e₄) in 𝕆 |

## Verification

All theorems are verified (lake build passes):
```bash
cd /path/to/leanmath
lake build
```

## References

- "The Weave Never Ends" (r2) — main thesis
- "Universal Hyperdimensional Semantic Hyperexpansion" — N-scaling tensor-field sheaf
- "Peer Review and Iteration" — sheaf of becoming
