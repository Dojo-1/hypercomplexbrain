"""AION-Omega^Q / QSigma-R: an audited almost-all-quantum brain architecture.

This package is the executable half of the architecture.  Its purpose is not to
implement a brain; it is to hold every quantitative claim the architecture makes
to a falsifiable test, so that "as close to 100% quantum as possible" becomes a
number that can be measured, argued with, and lowered by better classical
algorithms.

Modules
-------
atlas         Quantum Necessity Atlas: intervals, free-theory bundle, transport
advantage     causal advantage cone: promotion is a region, not a scalar
stack         typed quantities and transport holonomy around free-theory loops
governance    the P/A/M/H/S/R evidence lattice as executable CI policy
visibility    coupling field g_r: structure invisible to depth-r local probes
cayley_dickson  the associator failure ladder as an observability atlas
residency     simulation-cost interval (one coordinate of the atlas)
coherentize   Stinespring coherentization and what it actually buys
budget        the coherence budget: periodic model (A-tier heuristic)
bordon        Bordon respiration: reservoir dynamics, drone ceiling, polyrhythm
quantities    typed coordinates: units, uncertainty, base-relativity
process       process tensors and measurable temporal memory
fusion        Fibonacci fusion grammar with pentagon/hexagon verification
identity      polyholonomic identity, Gram PSD theorem, frame invariance
selfknowledge bounds on self-knowledge, and the syndrome counterexample to them
qrf           quantum reference frames: entanglement is frame-relative
"""

from . import (advantage, atlas, bordon, budget, cayley_dickson, coherentize,
               fusion, governance, identity, process, qrf, quantities, residency,
               selfknowledge, stack, visibility)

__version__ = "0.1.0"

__all__ = [
    "advantage",
    "atlas",
    "bordon",
    "budget",
    "cayley_dickson",
    "coherentize",
    "fusion",
    "governance",
    "identity",
    "process",
    "quantities",
    "qrf",
    "residency",
    "selfknowledge",
    "stack",
    "visibility",
    "__version__",
]
