<div align="center">

# HypercomplexBrain

**AION-Ω^Q · QΣ**

### What survives when the representation changes?

*A research workshop for geometry, quantum information, artificial intelligence, and the things that do not fit neatly into one representation.*

**Research conception & direction: [Jesús Vilela Jato](https://github.com/jesusvilela) · [Dojo-1](https://github.com/Dojo-1)**

[Explore the mathematics](formal/README.md) · [Read the field guide](docs/HB0_POLYCOSMIC_KERNEL.md) · [See the evidence](docs/ARCHITECTURE.md) · [License: CC BY 4.0](LICENSE)

</div>

> **A laboratory, not a finished artificial brain.** Here, “brain”, “identity”, “memory” and “recognition” describe mathematical and software models. They do not establish consciousness, human-like cognition, AGI, biological fidelity, quantum hardware use, or quantum advantage.

## Begin with a question

Suppose two investigators are looking at the same world. One sees distances, another sees probabilities; one keeps a history, another remembers only the present. Can they speak to each other without forcing either world into the other's coordinates?

And when their descriptions agree, **what, exactly, has survived the journey?**

This is the question behind AION. A *Worldlet* is a local model with its own geometry, observables, clocks, and boundaries. A *Tendril* is a declared transport between models. Every transport has obligations: what it preserves, what it changes, what it costs under a specified instrument, and what remains unresolved.

We do not assume that a prettier geometry supplies a more capable intelligence. We build small, inspectable objects, test their boundaries, and retain the failures that teach us something.

## A tiny example: the number that missed the geometry

Consider a two-dimensional map that **doubles the first coordinate and halves the second**:

\[
T=\begin{pmatrix}2&0\\0&1/2\end{pmatrix}.
\]

Start from \(v=(1,2)\). Its squared length is \(1^2+2^2=5\). After transport, \(Tv=(2,1)\), whose squared length is *also* \(5\).

One measurement declares a perfect return: **no change detected**. And yet one direction was stretched while another was compressed.

The fuller geometric record is

\[
D_T=T^\mathsf{T}T-I
=\begin{pmatrix}3&0\\0&-3/4\end{pmatrix}\ne0.
\]

There is no contradiction. The scalar was true of *that one input*; it was simply not the whole story.

That distinction is now an exact, scoped Lean formalization in [R6MetricDefect](formal/R6MetricDefect.lean), with a [gentle mathematical explanation](formal/R6_METRIC_DEFECT_GUIDE.md). It is a theorem about explicit **real 2×2 symmetric forms**—not proof of a general Worldlet geometry, a quantum-energy expense, or a cognitive gain.

## A map of the workshop

\`\`\`mermaid
flowchart LR
    A["Local world A"] --> T["Declared transport"]
    T --> B["Local world B"]
    T --> Q["What changed, what survived?"]
    Q --> G{"Proofs · controls · counterexamples"}
    G -->|"Supported within scope"| E["Retained result"]
    G -->|"Failed or unresolved"| R["Correction / typed remainder"]
\`\`\`

| Where to look | What you will find | What it does **not** establish |
|---|---|---|
| [Worldlets & the HB-0 kernel](docs/HB0_POLYCOSMIC_KERNEL.md) | An executable architecture with heterogeneous local models and explicit transport contracts | A biologically faithful or conscious brain |
| [Native Lean formalizations](formal/README.md) | Checked, narrowly stated results on R6 boosts, finite dilations, orthogonal frames, local remainder accounting, and symmetric-form defects | Universal quantum-resource bounds or general manifold theorems |
| [Quantum substrate studies](docs/QUANTUM_SUBSTRATE_COST.md) | A fixed encoding's costs, postselection, simulations, and limitations | Execution on quantum hardware or quantum advantage |
| [Experiment and correction history](docs/ARCHITECTURE.md) | Reproductions, failures, adversarial tests, and source-specific outcomes | Independent validation of every scientific interpretation |

A particularly important split is **mathematics versus implementation versus measurement**. Lean checks theorems as *encoded*. Python tests executable contracts. Neither, on its own, proves that the intended scientific interpretation is correct.

The historical [imported LeanMath archive](formal/LEANMATH_PROVENANCE.md) remains **unverified and outside the native proof target**.

## What have we actually learned?

Not every useful result is a success story.

- In the [S4 recognition chamber](docs/S4_G100_RESULTS.md), six of ten preregistered gates failed. We preserve that negative result.
- The [S8 decoder study](docs/S8_FANO_DECODER.md) reported local identifiability, while retaining a confound that limits the stronger interpretation.
- The [S9 finite Hofstadter probe](docs/S9_FQHE_PROBE.md) retired a parameter-point claim after a frame repair.
- In the R6 formal track, the exact **real** dilation, frame covariance, signed local accounting, and form-valued defect are separately stated and checked. The most recent example above shows why a zero scalar observation does not license a zero geometric defect.

AION does not have a useful single “percentage quantum”. The answer depends on the operation, state, simulation model, and hardware. Its quantum-information experiments are presently **classical computations and simulations**, not a demonstrated physical quantum cognitive system.

## Choose your path

**Curious reader:** Start with the [HB-0 field guide](docs/HB0_POLYCOSMIC_KERNEL.md), then return to the example above. The [mathematical reference](docs/MANIFOLD_REFERENCE.md) offers familiar analogies and identifies where they break.

**Mathematician:** Begin at [formal/README.md](formal/README.md). Read the exact theorem statements, their hypotheses, and the corresponding guides: [finite dilation](formal/R6_DILATION_GUIDE.md), [signed remainder](formal/R6_REMAINDER_GUIDE.md), and [metric-pullback defect](formal/R6_METRIC_DEFECT_GUIDE.md).

**Engineer or experimentalist:** Go to [src/aionq/](src/aionq/), [tests/](tests/), [experiments/](experiments/), and [manifests/](manifests/). Inspect the actual code path, controls, seeds, and archived evidence before rerunning an experiment.

**Historical reading:** The [78-page Human Guide, publisher-review edition v2.0](docs/HypercomplexBrain_Human_Guide_Publisher_Review_Edition_v2.0.pdf) is a **snapshot** of an earlier state, not a current proof certificate or independent peer review. The source repository and current correction ledger take precedence.

## Run a small part of the workshop

The Python package is called \`aionq\` and supports Python 3.10+. It uses NumPy, SciPy, and Qiskit.

\`\`\`bash
git clone https://github.com/Dojo-1/hypercomplexbrain.git
cd hypercomplexbrain
python -m venv .venv
\`\`\`

For macOS and Linux:

\`\`\`bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python experiments/run_audit.py
\`\`\`

For Windows PowerShell:

\`\`\`powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe experiments/run_audit.py
\`\`\`

To inspect the native Lean proofs, install the pinned Lean toolchain and build tools, then run:

\`\`\`bash
cd formal
lake exe cache get
lake build
lake env lean ProofAudit.lean
\`\`\`

The native project pins Lean 4.27.0 and a specific Mathlib commit. The imported historical LeanMath tree is intentionally **not** in that build. The [Lean CI workflow](.github/workflows/lean.yml) reports the compiler and axiom checks.

**Before running experiment producers:** Some artifacts are append-once and tied to frozen manifests. Read the experiment contract before regenerating anything. To check existing first-party evidence envelopes, use \`python -m aionq.verify_envelopes artifacts\`. A passing test is not an independent scientific reproduction.

## Evidence without ornament

We retain a small vocabulary to avoid making every attractive result sound equally established:

| Mark | Meaning |
|---|---|
| **P** | Proved within the exact stated formal object |
| **A** | Explicit assumption, axiom, or weaker surrogate |
| **M** | Bounded measurement, with its instrument and conditions |
| **H** | Open, falsifiable hypothesis |
| **S** | Semantic or architectural proposal |
| **R** | Retired or corrected interpretation |

A typed **[R] remainder** is different from the **R** evidence mark. A remainder is an unresolved observation or loss to account for, not an automatic failure or a universal obstruction. Our [witness protocol](docs/WITNESS_WEAVE.md) separates local checks, first-party evidence, and independent replication.

## An invitation

There is room here for the reader who offers a counterexample, the engineer who finds a hidden assumption, the mathematician who gives a simpler lemma, and the scientist who designs the matched control that makes a hypothesis fall.

You need not adopt the project’s vocabulary to improve its mathematics. A useful issue or PR names the claim, the assumptions, what has been inspected, and the smallest example or experiment that might settle the disagreement.

**Research conception and direction:** **Jesús Vilela Jato** ([GitHub](https://github.com/jesusvilela)), through **Dojo-1**. This programme has been developed with substantial **AI-assisted coding, formalization, review, and editing**; such assistance is not an independent proof witness. Other contributors' work and upstream materials retain their respective provenance and rights.

**License and attribution:** The original material for which the project licensor holds grantable rights is released under **[Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE)**. Reuse, including adaptation and commercial reuse, requires appropriate credit, a license link, and indication of changes. See [ATTRIBUTION.md](ATTRIBUTION.md) and [CITATION.cff](CITATION.cff) for a practical citation and rights boundary. Imported or third-party material is not relicensed by this notice. Creative Commons recommends software-specific licenses for software; the choice of CC BY for this repository should not be confused with such a license.

**Observe. Verify. Leave the remainder visible.**
