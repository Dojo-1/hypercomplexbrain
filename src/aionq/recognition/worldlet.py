"""Worldlets and Tendrils: heterogeneous local states and typed bidirectional relations.

A Worldlet is deliberately NOT coerced into a common coordinate representation.
The four roles S4-G100 needs live on four genuinely different carriers -- real
orthogonal matrices, F_2 cochains, a bounded real box, and a discrete partial
order -- and forcing them into one vector space would destroy the only thing the
architecture claims: that transport between them costs something measurable.

A Tendril is a typed bidirectional relation.  The requirement that it declare
``preserved`` / ``transformed`` / ``lost`` before any transport runs is what makes
the round-trip defect interpretable: a nonzero defect on an edge whose ``lost``
list is empty is a bug, and a zero defect on an edge with a nonempty ``lost``
list means the metric is not seeing the loss.  Both are checked in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..governance import GovernanceError
from .types import TypedRemainder

__all__ = ["Worldlet", "Tendril", "Geometry", "AlgebraRegime", "Polycosmos"]


class Geometry:
    """The local geometries in play.  Distinctness here is load-bearing."""

    ORTHOGONAL_FROBENIUS = "orthogonal_group_frobenius"   # O(d) with ||.||_F
    HAMMING_F2 = "hamming_f2"                             # F_2^E with Hamming
    BOUNDED_BOX_L1 = "bounded_box_l1"                     # aperture box with L1
    DISCRETE_PARTIAL_ORDER = "discrete_partial_order"     # evidence lattice
    SL2_ABSOLUTE_PSEUDO_VOLUME = "sl2_absolute_pseudo_volume"
    DENSITY_OPERATOR_BURES = "density_operator_trace_bures"
    CAYLEY_DICKSON_L2 = "cayley_dickson_coordinate_l2"

    ALL = (ORTHOGONAL_FROBENIUS, HAMMING_F2, BOUNDED_BOX_L1,
           DISCRETE_PARTIAL_ORDER, SL2_ABSOLUTE_PSEUDO_VOLUME,
           DENSITY_OPERATOR_BURES, CAYLEY_DICKSON_L2)


class AlgebraRegime:
    """Which algebra a worldlet's carrier lives in.

    ``OCTONION`` and ``SEDENION`` are listed so the manifest validator can refuse
    them in a flat-sheaf role: RET-S3-OCTONIONIC_SHEAF established that a vertex
    gauge induces no flat connection above dimension 4, and that finding is a
    governing constraint on this round, not a preference.
    """

    REAL = "real"
    REAL_MATRIX = "real_matrix"
    GF2 = "gf2"
    COMPLEX = "complex"
    QUATERNION = "quaternion"
    OCTONION = "octonion"
    SEDENION = "sedenion"
    CD32 = "cayley_dickson_32"
    SYMBOLIC = "symbolic"

    ALL = (REAL, REAL_MATRIX, GF2, COMPLEX, QUATERNION, OCTONION, SEDENION,
           CD32, SYMBOLIC)
    #: regimes for which a vertex gauge is known NOT to induce a flat connection
    NON_FLAT = (OCTONION, SEDENION, CD32)


@dataclass
class Worldlet:
    """A heterogeneous local state object with its own geometry and clock."""

    id: str
    carrier: str
    local_state: object = None
    local_geometry: str = Geometry.ORTHOGONAL_FROBENIUS
    algebra_regime: str = AlgebraRegime.REAL_MATRIX
    clocks: tuple = ()
    observers: tuple = ()
    boundary: str = ""
    energy_or_cost: float = 0.0
    evidence_refs: tuple = ()
    typed_remainders: tuple = ()

    def __post_init__(self) -> None:
        if self.local_geometry not in Geometry.ALL:
            raise GovernanceError(f"{self.id}: unknown geometry "
                                  f"{self.local_geometry!r}")
        if self.algebra_regime not in AlgebraRegime.ALL:
            raise GovernanceError(f"{self.id}: unknown algebra regime "
                                  f"{self.algebra_regime!r}")
        for r in self.typed_remainders:
            if not isinstance(r, TypedRemainder):
                raise GovernanceError(f"{self.id}: carries an untyped remainder")


@dataclass
class Tendril:
    """A typed bidirectional relation between two Worldlets.

    ``return_transport`` may be ``None`` only if ``return_absent_reason`` says
    why.  A silently one-way relation is the failure mode this type exists to
    prevent: it is how a lossy projection gets treated as an identification.
    """

    id: str
    source: str
    target: str
    forward_transport: object = None
    return_transport: object = None
    preserved_fields: tuple = ()
    transformed_fields: tuple = ()
    lost_fields: tuple = ()
    transport_cost: float = 0.0
    typed_remainder: TypedRemainder | None = None
    return_absent_reason: str = ""
    woven: bool = True
    deweave_reason: str = ""

    def __post_init__(self) -> None:
        if self.return_transport is None and not self.return_absent_reason:
            raise GovernanceError(
                f"tendril {self.id}: a relation with no return transport must say "
                "why, or it is a lossy projection being passed off as an "
                "identification")
        if self.typed_remainder is not None and \
                not isinstance(self.typed_remainder, TypedRemainder):
            raise GovernanceError(f"tendril {self.id}: untyped remainder")

    @property
    def is_reversible(self) -> bool:
        return self.return_transport is not None

    @property
    def claims_lossless(self) -> bool:
        return not self.lost_fields

    def deweave(self, reason: str) -> "Tendril":
        """Retire the relation from the active coalition.  Recorded, not deleted."""
        if not reason:
            raise GovernanceError(f"tendril {self.id}: deweaving requires a reason")
        self.woven = False
        self.deweave_reason = reason
        return self

    def weave(self, reason: str = "") -> "Tendril":
        self.woven = True
        self.deweave_reason = ""
        return self


@dataclass
class Polycosmos:
    """A dynamic collection of Worldlets, Tendrils and higher-order relations.

    Not one vector space and not one homogeneous graph: worldlets keep their own
    carriers, and the hyperedges record constraints that no pair of worldlets can
    express alone.
    """

    worldlets: dict = field(default_factory=dict)
    tendrils: dict = field(default_factory=dict)
    hyperedges: tuple = ()

    def add_worldlet(self, w: Worldlet) -> Worldlet:
        if w.id in self.worldlets:
            raise GovernanceError(f"duplicate worldlet id {w.id}")
        self.worldlets[w.id] = w
        return w

    def add_tendril(self, t: Tendril) -> Tendril:
        if t.id in self.tendrils:
            raise GovernanceError(f"duplicate tendril id {t.id}")
        for end in (t.source, t.target):
            if end not in self.worldlets:
                raise GovernanceError(f"tendril {t.id}: endpoint {end} is not a "
                                      "worldlet in this polycosmos")
        self.tendrils[t.id] = t
        return t

    @property
    def geometries(self) -> set:
        return {w.local_geometry for w in self.worldlets.values()}

    @property
    def woven_tendrils(self) -> list:
        return [t for t in self.tendrils.values() if t.woven]

    def clocks(self) -> set:
        out: set = set()
        for w in self.worldlets.values():
            out |= set(w.clocks)
        return out
