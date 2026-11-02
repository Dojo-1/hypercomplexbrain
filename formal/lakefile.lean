import Lake
open Lake DSL

/-!
Native AION formalization project. The historical formal/leanmath/ archive
is deliberately outside this target: it has missing imports and is not proof
evidence. Mathlib is pinned to commit a3a10db0 (tag v4.27.0).
-/

package aionformal where
  moreLeanArgs := #["-DwarningAsError=true"]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @
    "a3a10db0e9d66acbebf76c5e6a135066525ac900"

@[default_target]
lean_lib AionFormal where
  -- Native sources are top-level siblings, not AionFormal.* submodules.
  -- List every root explicitly so Lake compiles them before the aggregator.
  roots := #[`OhniumObservatory, `RecognitionChamber, `R6Compact, `R6Dilation, `AionFormal]
