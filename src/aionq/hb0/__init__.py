"""HB-0: a typed polycosmic kernel for bounded architecture experiments.

Evidence floor: S/H.  The package is an executable architecture object, not an
AGI, consciousness, quantum-cognition, or hardware-advantage claim.  Hyperbolic
charts are local and optional; every promoted effect needs matched controls.
"""

from .core import *
from .identity import *
from .mind import *
from .transport import *
from .manifest import *
from .kernel import *

# Explicit public surface; private numerical helpers remain module-local.
__all__ = [name for name in globals() if not name.startswith("_")]
