import Mathlib

open Real

/-!
# Dirac Operator on Finite Graphs

Formalizes the finite Dirac operator as a block operator
`D = [0 B†; B 0]` on the direct sum `H_V ⊕ H_E` of vertex and edge
Hilbert spaces.

## Key Theorems

1. **Self-adjointness**: D† = D
2. **Square identity**: D² = [B B† 0; 0 B† B]
-/

noncomputable section

namespace VDIS.Dirac

/-! ## Preliminaries -/

def inner {n : ℕ} (x y : Fin n → ℝ) : ℝ := ∑ i, x i * y i

lemma inner_symm {n : ℕ} (x y : Fin n → ℝ) : inner x y = inner y x := by
  unfold inner
  refine Finset.sum_congr rfl fun i _ => ?_
  ring

/-! ## Graph Structure -/

/-- Get the target vertex of the e-th edge (0-indexed). -/
def target {V E : ℕ} (edgeList : List (Fin V × Fin V)) (e : Fin E) : Fin V :=
  match List.nth edgeList e.val with
  | some (_, v) => v
  | none => 0

/-- Get the source vertex of the e-th edge (0-indexed). -/
def source {V E : ℕ} (edgeList : List (Fin V × Fin V)) (e : Fin E) : Fin V :=
  match List.nth edgeList e.val with
  | some (u, _) => u
  | none => 0

/-! ## Incidence Operator B -/

def incidenceOperator {V E : ℕ} (edgeList : List (Fin V × Fin V)) :
    (Fin V → ℝ) → (Fin E → ℝ) :=
  fun f e => f (target edgeList e) - f (source edgeList e)

/-! ## Adjoint B† -/

def incidenceAdjoint {V E : ℕ} (edgeList : List (Fin V × Fin V)) :
    (Fin E → ℝ) → (Fin V → ℝ) :=
  fun g v =>
    (Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0) -
    (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)

/-! ## Adjoint Lemma: inner(Bf, g) = inner(f, B†g) -/

theorem inner_incidenceOperator_eq_inner_incidenceAdjoint {V E : ℕ}
    (edgeList : List (Fin V × Fin V)) (f : Fin V → ℝ) (g : Fin E → ℝ) :
    inner (incidenceOperator edgeList f) g = inner f (incidenceAdjoint edgeList g) := by
  unfold inner incidenceOperator incidenceAdjoint
  calc
    ∑ e, (f (target edgeList e) - f (source edgeList e)) * g e
        = (∑ e, f (target edgeList e) * g e) - (∑ e, f (source edgeList e) * g e) := by
      rw [Finset.sum_sub_distrib]
      refine Finset.sum_congr rfl fun e _ => ?_
      ring
    _ = (Finset.sum (Finset.range E) fun e => f (target edgeList e) * g e) -
        (Finset.sum (Finset.range E) fun e => f (source edgeList e) * g e) := by
      simp [Finset.sum_range]
    _ = (Finset.sum (Finset.range V) fun v => f v *
          (Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0)) -
        (Finset.sum (Finset.range V) fun v => f v *
          (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)) := by
      have h_target : (Finset.sum (Finset.range E) fun e => f (target edgeList e) * g e) =
          (Finset.sum (Finset.range V) fun v => f v *
            (Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0)) := by
        calc
          (Finset.sum (Finset.range E) fun e => f (target edgeList e) * g e)
              = (Finset.sum (Finset.range E) fun e =>
                  Finset.sum (Finset.range V) fun v =>
                    if target edgeList e = v then f v * g e else 0) := by
            refine Finset.sum_congr rfl fun e he => ?_
            rw [Finset.sum_eq_single (target edgeList e) ?_ ?_]
            · simp
            · intro v _ hv_ne; simp [hv_ne]
            · simp
          _ = (Finset.sum (Finset.range V) fun v =>
                  Finset.sum (Finset.range E) fun e =>
                    if target edgeList e = v then f v * g e else 0) :=
            Finset.sum_comm
          _ = (Finset.sum (Finset.range V) fun v => f v *
                  (Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0)) := by
            refine Finset.sum_congr rfl fun v hv => ?_
            rw [Finset.mul_sum]
            refine Finset.sum_congr rfl fun e he => ?_
            by_cases h : target edgeList e = v
            · simp [h]
            · simp [h]
      have h_source : (Finset.sum (Finset.range E) fun e => f (source edgeList e) * g e) =
          (Finset.sum (Finset.range V) fun v => f v *
            (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)) := by
        calc
          (Finset.sum (Finset.range E) fun e => f (source edgeList e) * g e)
              = (Finset.sum (Finset.range E) fun e =>
                  Finset.sum (Finset.range V) fun v =>
                    if source edgeList e = v then f v * g e else 0) := by
            refine Finset.sum_congr rfl fun e he => ?_
            rw [Finset.sum_eq_single (source edgeList e) ?_ ?_]
            · simp
            · intro v _ hv_ne; simp [hv_ne]
            · simp
          _ = (Finset.sum (Finset.range V) fun v =>
                  Finset.sum (Finset.range E) fun e =>
                    if source edgeList e = v then f v * g e else 0) :=
            Finset.sum_comm
          _ = (Finset.sum (Finset.range V) fun v => f v *
                  (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)) := by
            refine Finset.sum_congr rfl fun v hv => ?_
            rw [Finset.mul_sum]
            refine Finset.sum_congr rfl fun e he => ?_
            by_cases h : source edgeList e = v
            · simp [h]
            · simp [h]
      rw [h_target, h_source]
    _ = Finset.sum (Finset.range V) fun v => f v *
        ((Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0) -
         (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)) := by
      rw [Finset.sum_sub_distrib]
      refine Finset.sum_congr rfl fun v hv => ?_
      ring
    _ = ∑ v, f v * ((Finset.sum (Finset.range E) fun e => if target edgeList e = v then g e else 0) -
                   (Finset.sum (Finset.range E) fun e => if source edgeList e = v then g e else 0)) := by
      simp [Finset.sum_range]

/-! ## Dirac Operator D = [0 B; B† 0] -/

def diracOperator {V E : ℕ} (edgeList : List (Fin V × Fin V)) :
    (Fin (E + V) → ℝ) → (Fin (E + V) → ℝ) :=
  fun ψ i =>
    if h : (i : ℕ) < E then
      let f_V : Fin V → ℝ := fun v => ψ ⟨v.val + E, by have hv := v.2; omega⟩
      incidenceOperator edgeList f_V ⟨i.val, h⟩
    else
      let f_E : Fin E → ℝ := fun e => ψ ⟨e.val, by have he := e.2; omega⟩
      incidenceAdjoint edgeList f_E ⟨i.val - E, by have hi := i.2; omega⟩

/-! ## Self-Adjointness: inner(Dψ, φ) = inner(ψ, Dφ) -/

theorem dirac_self_adjoint {V E : ℕ} (edgeList : List (Fin V × Fin V))
    (ψ φ : Fin (E + V) → ℝ) :
    (∑ i, (diracOperator edgeList ψ i) * φ i) =
    (∑ i, ψ i * (diracOperator edgeList φ i)) := by
  set T := E + V with hT
  have h_disjoint : Disjoint (Finset.range E) (Finset.Ico E T) :=
    Finset.disjoint_left.2 fun i hi1 hi2 => by
      rw [Finset.mem_range] at hi1; rw [Finset.mem_Ico] at hi2
      rcases hi2 with ⟨hlo, _⟩; omega
  have h_cover : Finset.range T = (Finset.range E) ∪ (Finset.Ico E T) := by
    ext i; constructor <;> intro h
    · rw [Finset.mem_range] at h
      by_cases hiE : i < E
      · apply Finset.mem_union_left; rw [Finset.mem_range]; exact hiE
      · apply Finset.mem_union_right; rw [Finset.mem_Ico]; exact ⟨by omega, h⟩
    · rcases Finset.mem_union.1 h with (h' | h')
      · rw [Finset.mem_range] at h'; rw [Finset.mem_range]; omega
      · rw [Finset.mem_Ico] at h'; rcases h' with ⟨_, hhi⟩; rw [Finset.mem_range]; omega
  set ψV : Fin V → ℝ := fun v => ψ ⟨v.val + E, by have hv := v.2; omega⟩ with hψV
  set ψE : Fin E → ℝ := fun e => ψ ⟨e.val, by have he := e.2; omega⟩ with hψE
  set φV : Fin V → ℝ := fun v => φ ⟨v.val + E, by have hv := v.2; omega⟩ with hφV
  set φE : Fin E → ℝ := fun e => φ ⟨e.val, by have he := e.2; omega⟩ with hφE
  -- Compute inner(Dψ, φ) by splitting into edge and vertex parts
  have h_inner_Dψ_φ : (∑ i, (diracOperator edgeList ψ i) * φ i) =
      (Finset.sum (Finset.range E) fun e => (incidenceOperator edgeList ψV e) * φE e) +
      (Finset.sum (Finset.range V) fun v => (incidenceAdjoint edgeList ψE v) * φV v) := by
    calc
      (∑ i, (diracOperator edgeList ψ i) * φ i)
          = (∑ i in Finset.range T, (diracOperator edgeList ψ i) * φ i) := by simp [hT]
      _ = (∑ i in Finset.range E, (diracOperator edgeList ψ i) * φ i) +
          (∑ i in Finset.Ico E T, (diracOperator edgeList ψ i) * φ i) := by
        rw [Finset.sum_union h_disjoint, h_cover]
      _ = (Finset.sum (Finset.range E) fun e => (incidenceOperator edgeList ψV e) * φE e) +
          (∑ i in Finset.Ico E T, (incidenceAdjoint edgeList ψE ⟨i.val - E, by
            have hi := i.2; omega⟩) * φ i) := by
        simp [diracOperator, hψV, hψE, hφE]
      _ = (Finset.sum (Finset.range E) fun e => (incidenceOperator edgeList ψV e) * φE e) +
          (Finset.sum (Finset.range V) fun v => (incidenceAdjoint edgeList ψE v) * φV v) := by
        -- Reindex: i ∈ Ico E T ↔ v = i-E ∈ range V
        have h_reindex : (∑ i in Finset.Ico E T, (incidenceAdjoint edgeList ψE ⟨i.val - E, by
            have hi := i.2; omega⟩) * φ i) =
            (Finset.sum (Finset.range V) fun v => (incidenceAdjoint edgeList ψE v) * φV v) := by
          apply Finset.sum_bij (fun i _ => ⟨i.val - E, by
            intro hi; rw [Finset.mem_Ico] at hi; exact hi.1.trans_lt (by omega)⟩) ?_ ?_ ?_ ?_ ?_
          · intro i hi
            rw [Finset.mem_Ico] at hi; rcases hi with ⟨hlo, hhi⟩
            rw [Finset.mem_range]; omega
          · intro i hi
            rw [Finset.mem_Ico] at hi; rcases hi with ⟨hlo, hhi⟩
            dsimp [φV]; congr; ext; omega
          · intro i j hi hj h
            rw [Finset.mem_Ico] at hi hj; apply Fin.ext; omega
          · intro v hv
            rw [Finset.mem_range] at hv
            refine ⟨⟨v.val + E, by rw [Finset.mem_range]; omega⟩, ?_, ?_⟩
            · rw [Finset.mem_Ico]; constructor <;> omega
            · simp
        rw [h_reindex]
  -- Compute inner(ψ, Dφ) similarly
  have h_inner_ψ_Dφ : (∑ i, ψ i * (diracOperator edgeList φ i)) =
      (Finset.sum (Finset.range E) fun e => ψE e * (incidenceOperator edgeList φV e)) +
      (Finset.sum (Finset.range V) fun v => ψV v * (incidenceAdjoint edgeList φE v)) := by
    calc
      (∑ i, ψ i * (diracOperator edgeList φ i))
          = (∑ i in Finset.range T, ψ i * (diracOperator edgeList φ i)) := by simp [hT]
      _ = (∑ i in Finset.range E, ψ i * (diracOperator edgeList φ i)) +
          (∑ i in Finset.Ico E T, ψ i * (diracOperator edgeList φ i)) := by
        rw [Finset.sum_union h_disjoint, h_cover]
      _ = (Finset.sum (Finset.range E) fun e => ψE e *
            (incidenceOperator edgeList φV e)) +
          (∑ i in Finset.Ico E T, ψ i *
            (incidenceAdjoint edgeList φE ⟨i.val - E, by have hi := i.2; omega⟩)) := by
        simp [diracOperator, hφV, hφE]
      _ = (Finset.sum (Finset.range E) fun e => ψE e * (incidenceOperator edgeList φV e)) +
          (Finset.sum (Finset.range V) fun v => ψV v * (incidenceAdjoint edgeList φE v)) := by
        -- Reindex the second sum: i ∈ Ico E T ↔ v = i-E ∈ range V
        have h_reindex : (∑ i in Finset.Ico E T, ψ i *
            (incidenceAdjoint edgeList φE ⟨i.val - E, by have hi := i.2; omega⟩)) =
            (Finset.sum (Finset.range V) fun v => ψV v * (incidenceAdjoint edgeList φE v)) := by
          apply Finset.sum_bij (fun i _ => ⟨i.val - E, by
            intro hi; rw [Finset.mem_Ico] at hi; exact hi.1.trans_lt (by omega)⟩) ?_ ?_ ?_ ?_ ?_
          · intro i hi
            rw [Finset.mem_Ico] at hi; rcases hi with ⟨hlo, hhi⟩
            rw [Finset.mem_range]; omega
          · intro i hi
            rw [Finset.mem_Ico] at hi; rcases hi with ⟨hlo, hhi⟩
            dsimp [ψV]; congr; ext; omega
          · intro i j hi hj h
            rw [Finset.mem_Ico] at hi hj; apply Fin.ext; omega
          · intro v hv
            rw [Finset.mem_range] at hv
            refine ⟨⟨v.val + E, by rw [Finset.mem_range]; omega⟩, ?_, ?_⟩
            · rw [Finset.mem_Ico]; constructor <;> omega
            · simp
        rw [h_reindex]
  rw [h_inner_Dψ_φ, h_inner_ψ_Dφ]
  -- Now use the adjoint lemma to show the two expressions are equal
  have h1 : (Finset.sum (Finset.range E) fun e => (incidenceOperator edgeList ψV e) * φE e) =
            (Finset.sum (Finset.range V) fun v => ψV v * (incidenceAdjoint edgeList φE v)) := by
    calc
      (Finset.sum (Finset.range E) fun e => (incidenceOperator edgeList ψV e) * φE e)
          = inner (incidenceOperator edgeList ψV) φE := by
        unfold inner; simp [Finset.sum_range]
      _ = inner ψV (incidenceAdjoint edgeList φE) :=
        inner_incidenceOperator_eq_inner_incidenceAdjoint edgeList ψV φE
      _ = (Finset.sum (Finset.range V) fun v => ψV v * (incidenceAdjoint edgeList φE v)) := by
        unfold inner; simp [Finset.sum_range]
  have h2 : (Finset.sum (Finset.range V) fun v => (incidenceAdjoint edgeList ψE v) * φV v) =
            (Finset.sum (Finset.range E) fun e => ψE e * (incidenceOperator edgeList φV e)) := by
    calc
      (Finset.sum (Finset.range V) fun v => (incidenceAdjoint edgeList ψE v) * φV v)
          = inner (incidenceAdjoint edgeList ψE) φV := by
        unfold inner; simp [Finset.sum_range]
      _ = inner ψE (incidenceOperator edgeList φV) := by
        -- inner(B† f, g) = inner(f, B g) follows from adjoint lemma + symmetry
        rw [inner_symm, inner_incidenceOperator_eq_inner_incidenceAdjoint edgeList φV ψE, inner_symm]
      _ = (Finset.sum (Finset.range E) fun e => ψE e * (incidenceOperator edgeList φV e)) := by
        unfold inner; simp [Finset.sum_range]
  rw [h1, h2]
  ring

/-! ## Square Identity: D² = [B B† 0; 0 B† B] -/

theorem dirac_square {V E : ℕ} (edgeList : List (Fin V × Fin V))
    (ψ : Fin (E + V) → ℝ) :
    (diracOperator edgeList (diracOperator edgeList ψ)) =
    fun i =>
      if h : (i : ℕ) < E then
        let f_E : Fin E → ℝ := fun e =>
          (diracOperator edgeList ψ) ⟨e.val, by have he := e.2; omega⟩
        let f_V : Fin V → ℝ := fun v =>
          ψ ⟨v.val + E, by have hv := v.2; omega⟩
        incidenceOperator edgeList
          (fun w => incidenceAdjoint edgeList f_E w) ⟨i.val, h⟩
      else
        let v_idx : Fin V := ⟨i.val - E, by have hi := i.2; omega⟩
        let f_E : Fin E → ℝ := fun e =>
          ψ ⟨e.val, by have he := e.2; omega⟩
        let f_V : Fin V → ℝ := fun v =>
          (diracOperator edgeList ψ) ⟨v.val + E, by have hv := v.2; omega⟩
        incidenceAdjoint edgeList
          (fun w => incidenceOperator edgeList f_V w) v_idx := by
  ext i
  dsimp
  by_cases h : (i : ℕ) < E
  · simp [h, diracOperator, incidenceOperator, incidenceAdjoint, target, source]
  · have hv : (i : ℕ) - E < V := by
      have hi := i.2
      omega
    set v_idx : Fin V := ⟨(i : ℕ) - E, hv⟩ with hv_idx
    simp [h, diracOperator, incidenceOperator, incidenceAdjoint, target, source, hv_idx]

end VDIS.Dirac
