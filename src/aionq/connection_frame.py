"""Gauge invariance, and the third thing an invariance claim can be.

A device was proposed for this repository: on a finite mesh with a discretised
connection Laplacian, the eigensections form a Parseval frame, and a gauge
transformation conjugates the frame operator, so the frame bounds are
gauge-invariant.  It was offered as the correct formal foothold, and it is
correct.  It is also **empty**, and this module exists to say so with a
measurement rather than an opinion.

The proof of the device never touches the connection.  An orthonormal basis is a
Parseval frame with ``A = B = 1``; the spectral theorem supplies one for any
Hermitian matrix; unitary conjugation preserves spectra.  So the conclusion holds
for the zero connection, for a random Hermitian matrix, and for a connection
whose edges have been shuffled into a configuration that is not gauge-equivalent
to anything.  Measured on a 12-vertex ring with three chords and an ``SU(2)``
fiber:

                                gauge orbit        shuffled connection
    frame bounds (A, B)         (1.0, 1.0)         (1.0, 1.0)
    spectrum                    3.6e-15            3.6e-01
    holonomy traces             8.3e-16            1.60
    localisation (IPR)          3.5e-16            5.8e-02

Three of the four are invariant to machine precision under the gauge group and
move under the shuffle.  The frame bounds do not move under either.

THE TYPE THIS ADDS.  `movingframe` classifies a measurement as ORBIT-COLLAPSED --
constant on the frame orbit, therefore seeing the object -- or ORBIT-RESOLVING --
varying on it, therefore mistyped as a property of the object when it is a
property of the pair.  Collapse has been treated throughout this repository as
the good case.  It is not sufficient.  A third case exists:

    BLIND      collapsed on the frame orbit AND collapsed under a perturbation
               that is not a frame change.  Invariant because it has no content,
               not because it has found the object.

A claim of invariance is only informative relative to something the invariant is
supposed to fail on.  Without that control, perfect invariance and blindness are
the same measurement.  This is the eighth-instance pattern of this repository --
a guard whose witness cannot reach the case it asserts -- appearing for the first
time inside a proposed *theorem* rather than inside code.

WHAT SURVIVES.  The device's conclusion is not wrong and is not useless; it is
just not about connections.  Replace the frame bounds with the spectrum, the
holonomy conjugacy classes, or the eigensection localisation and the same
gauge-covariance statement becomes a real one, because all three discriminate.
The holonomies are the sharpest: they are the complete gauge-invariant content
of a connection on a graph, and the frame bounds see none of it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "Mesh",
    "ring_with_chords",
    "random_connection",
    "connection_laplacian",
    "gauge_transform",
    "shuffle_connection",
    "frame_bounds",
    "holonomy_traces",
    "localisation",
    "discrimination_report",
]


@dataclass(frozen=True)
class Mesh:
    """A finite graph with a cycle basis, which is where holonomy lives."""

    vertices: int
    edges: tuple
    cycles: tuple


def ring_with_chords(vertices: int = 12, chords=((0, 5), (2, 8), (3, 9))) -> Mesh:
    """A ring plus chords: enough independent cycles for holonomy to be non-trivial.

    A tree carries no holonomy at all -- every connection on a tree is
    gauge-equivalent to the identity -- so a mesh without cycles would make the
    discriminating observables vacuous too, and the comparison would prove
    nothing about anything.
    """
    edges = tuple([(index, (index + 1) % vertices) for index in range(vertices)]
                  + list(chords))
    cycles = (tuple(range(vertices)), (0, 1, 2, 3, 4, 5), (2, 3, 4, 5, 6, 7, 8))
    return Mesh(vertices=vertices, edges=edges, cycles=cycles)


def _haar(size: int, rng) -> np.ndarray:
    matrix = rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))
    unitary, _ = np.linalg.qr(matrix)
    return unitary


def random_connection(mesh: Mesh, fiber: int = 2, seed: int = 11) -> dict:
    """A unitary per directed edge, with ``U_ji = U_ij*``, as a connection must."""
    rng = np.random.default_rng(seed)
    connection = {}
    for tail, head in mesh.edges:
        transport = _haar(fiber, rng)
        connection[(tail, head)] = transport
        connection[(head, tail)] = transport.conj().T
    return connection


def connection_laplacian(mesh: Mesh, connection: dict, fiber: int = 2) -> np.ndarray:
    """``(L f)_i = sum_{j~i} (f_i - U_ij f_j)``, Hermitian and positive semidefinite."""
    size = mesh.vertices * fiber
    laplacian = np.zeros((size, size), dtype=complex)
    for tail, head in mesh.edges:
        for source, target in ((tail, head), (head, tail)):
            block = slice(source * fiber, (source + 1) * fiber)
            other = slice(target * fiber, (target + 1) * fiber)
            laplacian[block, block] += np.eye(fiber)
            laplacian[block, other] -= connection[(source, target)]
    return (laplacian + laplacian.conj().T) / 2.0


def gauge_transform(mesh: Mesh, connection: dict, fiber: int = 2,
                    seed: int = 3) -> tuple:
    """``U_ij -> G_i U_ij G_j*`` for a unitary ``G_i`` at each vertex.

    This is a frame change of the bundle: it relabels the fiber over each vertex
    independently and moves no physical content whatever.  It is the exact
    analogue, one level up, of the qubit relabelling `frame_orbit` applies to
    circuits.
    """
    rng = np.random.default_rng(seed)
    frames = [_haar(fiber, rng) for _ in range(mesh.vertices)]
    moved = {(tail, head): frames[tail] @ transport @ frames[head].conj().T
             for (tail, head), transport in connection.items()}
    return moved, frames


def shuffle_connection(mesh: Mesh, connection: dict, seed: int = 7) -> dict:
    """Permute the edge transports among edges. **Not** a gauge transformation.

    The control the device lacked.  A shuffle preserves the multiset of edge
    transports and the graph, and changes which edge carries which -- so it
    changes the holonomies, and any observable that cannot see it cannot see a
    connection.
    """
    rng = np.random.default_rng(seed)
    transports = [connection[edge] for edge in mesh.edges]
    rng.shuffle(transports)
    moved = {}
    for (tail, head), transport in zip(mesh.edges, transports):
        moved[(tail, head)] = transport
        moved[(head, tail)] = transport.conj().T
    return moved


def frame_bounds(laplacian) -> tuple:
    """``(A, B)`` for the eigensection frame. Always ``(1, 1)``, and that is the point.

    The frame operator of an orthonormal basis is the identity, so its extreme
    singular values are 1 whatever the operator was.  Computed rather than
    asserted, because the whole finding is that this number is the same for a
    connection, its gauge transform, and a shuffle.
    """
    _, basis = np.linalg.eigh(np.asarray(laplacian))
    operator = basis @ basis.conj().T
    spectrum = np.linalg.svd(operator, compute_uv=False)
    return float(spectrum.min()), float(spectrum.max())


def holonomy_traces(mesh: Mesh, connection: dict, fiber: int = 2) -> np.ndarray:
    """Trace of the ordered product around each cycle: the gauge-invariant content.

    Under ``U_ij -> G_i U_ij G_j*`` a cycle product conjugates by ``G`` at the
    base point, so its trace -- a class function -- is exactly invariant.  These
    traces are what a connection on a graph actually *is*, up to gauge, and the
    frame bounds see none of them.
    """
    out = []
    for cycle in mesh.cycles:
        product = np.eye(fiber, dtype=complex)
        for tail, head in zip(cycle, cycle[1:] + cycle[:1]):
            product = product @ connection[(tail, head)]
        out.append(complex(np.trace(product)))
    return np.array(out)


def localisation(laplacian, vertices: int, fiber: int = 2) -> np.ndarray:
    """Inverse participation ratio of each eigensection, per vertex.

    ``sum_i w_i^2`` for ``w_i`` the normalised weight of the section on vertex
    ``i``.  Gauge-invariant for a structural reason: a gauge acts as ``G_i`` on
    the fiber over vertex ``i``, which preserves ``||f_i||`` exactly.  So this is
    a genuine invariant that nonetheless moves when the connection changes --
    which is what the frame bounds fail to be.
    """
    _, basis = np.linalg.eigh(np.asarray(laplacian))
    out = []
    for column in range(basis.shape[1]):
        section = basis[:, column]
        weights = np.array([
            float(np.linalg.norm(section[index * fiber:(index + 1) * fiber])) ** 2
            for index in range(vertices)])
        weights = weights / weights.sum()
        out.append(float((weights ** 2).sum()))
    return np.array(out)


def discrimination_report(mesh: Mesh = None, fiber: int = 2,
                          seed: int = 11) -> dict:
    """Every observable against both a gauge change and a non-gauge control.

    The report is deliberately shaped as a two-column table.  One column alone
    cannot tell an invariant from a blind quantity, and reporting only the gauge
    column is exactly the omission that made the proposed device look like a
    theorem about connections.
    """
    mesh = mesh or ring_with_chords()
    base = random_connection(mesh, fiber, seed)
    gauged, _ = gauge_transform(mesh, base, fiber)
    shuffled = shuffle_connection(mesh, base)

    laplacians = {name: connection_laplacian(mesh, connection, fiber)
                  for name, connection in (("base", base), ("gauge", gauged),
                                           ("shuffle", shuffled))}
    spectra = {name: np.linalg.eigvalsh(matrix)
               for name, matrix in laplacians.items()}
    holonomies = {"base": holonomy_traces(mesh, base, fiber),
                  "gauge": holonomy_traces(mesh, gauged, fiber),
                  "shuffle": holonomy_traces(mesh, shuffled, fiber)}
    localisations = {name: localisation(matrix, mesh.vertices, fiber)
                     for name, matrix in laplacians.items()}

    def deviation(table, key):
        return float(np.abs(np.asarray(table["base"]) - np.asarray(table[key])).max())

    rows = {
        "frame_bounds": {
            "base": frame_bounds(laplacians["base"]),
            "gauge": float(max(abs(a - b) for a, b in
                               zip(frame_bounds(laplacians["base"]),
                                   frame_bounds(laplacians["gauge"])))),
            "shuffle": float(max(abs(a - b) for a, b in
                                 zip(frame_bounds(laplacians["base"]),
                                     frame_bounds(laplacians["shuffle"])))),
        },
        "spectrum": {"gauge": deviation(spectra, "gauge"),
                     "shuffle": deviation(spectra, "shuffle")},
        "holonomy": {"gauge": deviation(holonomies, "gauge"),
                     "shuffle": deviation(holonomies, "shuffle")},
        "localisation": {"gauge": deviation(localisations, "gauge"),
                         "shuffle": deviation(localisations, "shuffle")},
    }
    for name, row in rows.items():
        row["type"] = ("BLIND" if row["shuffle"] <= 1e-9
                       else "INVARIANT_AND_DISCRIMINATING")
    rows["spectrum_gap"] = float(np.min(np.diff(spectra["base"])))
    return rows
