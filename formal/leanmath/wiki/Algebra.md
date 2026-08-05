# Algebra — Cayley-Dickson Construction

The Cayley-Dickson construction builds a tower of algebras:
ℝ (level 0) → ℂ (level 1) → ℍ (level 2) → 𝕆 (level 3) → 𝕊 (level 4)

Each level doubles the dimension. Elements are `Fin (2^n) → ℝ`.

## Key Definitions

### Multiplication

- `mulByLevel level x y` — dispatch to explicit kernel for given level
- `mulReal` — ℝ multiplication (level 0)
- `mulComplex` — ℂ multiplication (level 1)
- `mulQuat` — ℍ multiplication (level 2)
- `mulOct` — 𝕆 multiplication (level 3)
- `mulSedenion` — 𝕊 multiplication (level 4)

### Conjugation

- `conjByLevel level x` — negate imaginary components
- `conj` — recursive Cayley-Dickson conjugation

### Norm

- `normByLevel level x` — √(∑ x_i²)
- `normSedenion` — 𝕊 norm

### Half-Operations

- `firstHalf x` — first half (indices 0..2^{n-1}-1)
- `secondHalf x` — second half (indices 2^{n-1}..2^n-1)
- `embedFirst x` — embed into first half
- `embedSecond x` — embed into second half

## Key Theorems

| Theorem | Statement |
|---------|-----------|
| `CayleyDicksonRecurrenceLow` | Recurrence holds for levels 1-3 |
| `CayleyDicksonRecurrenceGeneral` | Recurrence holds for level ≥ 4 |
| `mul_alternative_octonions` | Left alternativity for 𝕆 |
| `norm_mul_octonions` | Norm multiplicativity for 𝕆 (Hurwitz) |
| `mul_assoc_levels_0_1_2` | Associativity for levels 0-2 |
| `conj_fixes_real` | Conjugation fixes the real line |

## File Structure

```
Algebra/
├── Basic.lean       # Complex numbers, quaternions, wedge products
└── CD.lean          # Full Cayley-Dickson R→C→H→O→S (540+ lines)
```

## Proof Style

Level enumeration: `interval_cases level`
Fin case analysis: `fin_cases i`
Function equality: `ext i; fin_cases i; simp; ring`

## Known Limitations

- Level ≥ 5 uses general recurrence (recursive), not explicit kernel
- Norm multiplicativity for 𝕊 (level 4) is not multiplicative (Hurwitz: only 0-3)
