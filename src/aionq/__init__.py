"""AION-Omega^Q / QSigma-R: an audited almost-all-quantum brain architecture.

This package is the executable half of the architecture.  Its purpose is not to
implement a brain; it is to hold every quantitative claim the architecture makes
to a falsifiable test, so that "as close to 100% quantum as possible" becomes a
number that can be measured, argued with, and lowered by better classical
algorithms.

Modules
-------
residency     certified quantum residency Q_cert (replaces the additive metric)
coherentize   Stinespring coherentization and what it actually buys
budget        the coherence budget: why exhalation is forced, not chosen
process       process tensors and measurable temporal memory
fusion        Fibonacci fusion grammar with pentagon/hexagon verification
identity      polyholonomic identity, Gram PSD theorem, frame invariance
selfknowledge the no-cloning bound on self-tomography (quantum Anti-Loeb)
qrf           quantum reference frames: entanglement is frame-relative
"""

from . import budget, coherentize, fusion, identity, process, qrf, residency, selfknowledge

__version__ = "0.1.0"

__all__ = [
    "budget",
    "coherentize",
    "fusion",
    "identity",
    "process",
    "qrf",
    "residency",
    "selfknowledge",
    "__version__",
]
