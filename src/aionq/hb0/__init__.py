"""HB-0: a typed polycosmic kernel for bounded architecture experiments.

Evidence floor: S/H.  The package is an executable architecture object, not an
AGI, consciousness, quantum-cognition, or hardware-advantage claim. The shared
Poincare base is mandatory; local hyperbolic fibers remain optional and
heterogeneous with Fisher/Riemannian/Euclidean controls. No pairwise projection
is a global n-ary decision.
"""

from .core import *
from .identity import *
from .mind import *
from .transport import *
from .manifest import *
from .kernel import *
from .wall import *
from .hyperbolic import *
from .decision_field import *
from .quantum_base import *
from .chiral_spin import *

# Explicit public surface; private numerical helpers remain module-local.
__all__ = [name for name in globals() if not name.startswith("_")]
