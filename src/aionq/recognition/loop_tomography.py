"""Null-loop tomography: the typed round-trip transport defect.

    [R]_loop(x; T, D) = D_X(x, T.backward(T.forward(x)))

The whole content of this module is that ``[R]_loop`` is a **TransportDefect** and
nothing else.  It is not a cohomology class, not a semantic incompleteness
remainder, not an empirical residual, and not a scalar obstruction constant.
This repository has a live rule against untyped transport between remainder
kinds, and the round-trip defect is exactly the quantity most likely to be
laundered into one of the other three, because it is a small nonnegative number
that appears wherever two representations meet.

So the defect is returned as a :class:`~aionq.recognition.types.TypedRemainder`
carrying its carrier and its metric, and the raw value is available *before* any
clipping or aggregation.

Three properties are load-bearing and are stated as theorem targets in
``formal/RecognitionChamber.lean``:

    P1  nonnegativity, for any pseudo-metric D
    P2  exact left inverse implies zero defect
    P3  invariance under conjugation by an isometry

P1 and P2 hold for any pseudo-metric by definition.  P3 is the one with content:
it says the defect is a property of the transport pair, not of the coordinates
chosen to express it, and it is what licenses comparing loop defects measured in
different gauges.  The metamorphic tests exercise all three numerically; the
Lean file states them and is **not** claimed to compile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..governance import RemainderKind
from .types import TypedRemainder, TransportReport

__all__ = ["TransportPair", "loop_defect", "frobenius_metric", "hamming_metric",
           "euclidean_metric", "LoopDefectReport", "gauge_conjugate"]


# --------------------------------------------------------------------------
# Metrics.  Each names its carrier so a defect can never be compared across two.
# --------------------------------------------------------------------------

def frobenius_metric(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float), "fro"))


def euclidean_metric(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, float).ravel()
                                - np.asarray(b, float).ravel()))


def hamming_metric(a, b) -> float:
    a = np.asarray(a, dtype=np.uint8).ravel()
    b = np.asarray(b, dtype=np.uint8).ravel()
    if a.size != b.size:
        return float(max(a.size, b.size))
    return float(np.count_nonzero(a != b))


METRIC_CARRIERS = {
    "frobenius": "real_matrix",
    "euclidean": "real_vector",
    "hamming": "f2_cochain",
}


@dataclass(frozen=True)
class TransportPair:
    """A forward map and its declared inverse, with the carrier named."""

    name: str
    forward: object
    backward: object
    carrier: str
    metric_name: str = "euclidean"
    preserved: tuple = ()
    transformed: tuple = ()
    lost: tuple = ()

    @property
    def metric(self):
        return {"frobenius": frobenius_metric, "euclidean": euclidean_metric,
                "hamming": hamming_metric}[self.metric_name]


@dataclass(frozen=True)
class LoopDefectReport:
    """The defect, its type, and the raw value before any post-processing."""

    raw_value: float
    remainder: TypedRemainder
    transport: TransportReport

    @property
    def value(self) -> float:
        return self.raw_value


def loop_defect(x, pair: TransportPair, provenance: str = "") -> LoopDefectReport:
    """D_X(x, backward(forward(x))), typed.

    Nonnegative for any pseudo-metric, exactly zero when ``backward`` is a left
    inverse of ``forward`` on ``x``.  The raw value is returned untouched; no
    clipping, no normalisation, no aggregation.
    """
    y = pair.forward(x)
    back = pair.backward(y)
    d = float(pair.metric(x, back))
    if not math.isfinite(d):
        raise ValueError(f"{pair.name}: non-finite loop defect; the metric or the "
                         "transport is malformed")
    if d < 0.0:
        raise ValueError(f"{pair.name}: negative loop defect; the supplied "
                         "comparison is not a pseudo-metric")
    remainder = TypedRemainder(
        remainder_type=RemainderKind.EMPIRICAL,
        carrier=pair.carrier,
        metric_or_comparison=f"{pair.metric_name} round-trip on {pair.carrier}",
        raw_value=d,
        assumptions=("transport defect only: NOT a cohomology class, NOT a "
                     "semantic remainder, NOT a scalar obstruction constant",),
        provenance=provenance or pair.name,
    )
    report = TransportReport(
        edge=pair.name,
        preserved=pair.preserved,
        transformed=pair.transformed,
        lost=pair.lost,
        remainder=remainder,
        evidence=f"loop_defect({pair.name})",
    )
    return LoopDefectReport(raw_value=d, remainder=remainder, transport=report)


def gauge_conjugate(pair: TransportPair, g, g_inv, name_suffix: str = "_gauged"
                    ) -> TransportPair:
    """Conjugate a transport pair by an isometry: T_G = G o T o G^-1.

    P3 says the loop defect is unchanged at the transported point, ``G(x)``.
    That is what makes the defect a property of the pair rather than of the
    coordinates, and it is checked numerically in the metamorphic tests.
    """
    return TransportPair(
        name=pair.name + name_suffix,
        forward=lambda z: g(pair.forward(g_inv(z))),
        backward=lambda z: g(pair.backward(g_inv(z))),
        carrier=pair.carrier,
        metric_name=pair.metric_name,
        preserved=pair.preserved,
        transformed=pair.transformed,
        lost=pair.lost,
    )
