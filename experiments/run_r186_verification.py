"""Checking Godelian-1's R186-QSigma rather than accepting it.

An external agent returned a scalar-holonomy no-go theorem and a quantum-shape
lift.  It is largely right, and several of its claims are EXACTLY checkable, so
they are checked -- the same rule this repository applies to its own output and
applied to the Wall-Sheaf audit in Round S7.

Confirmed here
--------------
1. The SU(2) group-commutator trace identity

       (1/2) Tr W(a,b) = 1 - 2 sin^2(a/2) sin^2(b/2),
       W = U_x(a) U_y(b) U_x(a)^dag U_y(b)^dag

   worst deviation 6.7e-16 over 200 random (a, b).

2. At a = b = pi/2: (1/2) Tr W = 0.500000000000000 exactly, theta = 2pi/3 to
   1e-15.  The 120-degree witness is real.

3. BCH leading term log W = -i(ab/2) sigma_z: relative residual 7.1e-02,
   7.1e-03, 7.1e-04 at a = b = 1e-1, 1e-2, 1e-3 -- one power per decade, so the
   stated leading term is correct and the remainder is one order down.

4. THEOREM 2, ker L_U isomorphic to Fix(Hol), on an 8-edge graph at fiber
   dimension 2:

       generic SU(2)   dim ker 0   dim Fix 0
       scalar stub     dim ker 2   dim Fix 2
       pure gauge      dim ker 2   dim Fix 2

   The pure-gauge null passes: U_{u->v} = G_v G_u^dag gives a trivial holonomy
   group and a full-fiber kernel.

Where I disagree, and it is about my own experiment
---------------------------------------------------
R186 argues that "deficit equals area" is arithmetic whenever both sides come
from one functional lineage.  That is right, and it is the sharpest thing in the
reply.  It does not apply to `run_continuum_holonomy.py`, and the reason is
measurable rather than rhetorical.

There the area comes from THREE interior angles via analytic tangents -- three
arccos evaluations at the vertices.  The holonomy comes from a 12,000-step
product of rotation matrices around the loop.  Those are different computational
channels, not one function named twice, and the evidence is the convergence
signature: a tautology returns exactly zero at every resolution, while the
measured residual falls 1.10e-06 -> 4.31e-09 with ratio EXACTLY 4.00 per
doubling.  Second-order convergence is what a genuine discretised comparison
looks like and what an identity cannot produce.

The distinction R186 draws is the right one.  Applied to this experiment it
comes out the other way, and the convergence sweep is what decides it -- the
same sweep that earlier caught a plateau at 5.86e-03 which turned out to be a
bug in my own tangent.

One loose statement
-------------------
R186 says delta = A "requires unit Gaussian curvature K = 1".  What is required
is |K| = 1; the sign fixes orientation, not magnitude.  The Poincare disk has
K = -1 and satisfies |delta| = A, which is exactly the case the calculator under
discussion implements.  Minor, and it does not touch the argument.

Run with:  PYTHONPATH=src python3 experiments/run_r186_verification.py
"""
