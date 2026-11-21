# OPENSTEP-004 — numerical cross-checks of the accepted coil scan

Recorded 21 November 2026, before executing this suite. Parent publication:
`2438abacf652478ec7865b3ce1fce5d17ad8ab1c` (OPENSTEP-003).

This is an exploratory implementation-validation suite on the eight already
accepted fields. It is not a new geometry optimization, an independent review,
an independently preregistered experiment, or physical reactor qualification.
Do not rerun or alter the historical 001–003 artifacts.

## Frozen checks

1. Check all 164 files in the parent 003 artifact inventory, including its
   manifest, against their Git blob hashes before any publication/navigation
   edits. Record the source files and dependency versions used here.
2. Reapply the original, uncached FreeGS 0.8.2 von Hagenow boundary and the
   full-domain critical-point search to each of the eight accepted fields.
   Retain the normalized fixed-point acceptance limit of 1e-5. Test that an
   intentionally perturbed coarse baseline (1% of the reference flux span,
   smooth localized plasma-flux perturbation) is rejected by that same check.
3. Recalculate rigid vertical force directly from the shifted filament-coil
   magnetic field, instead of differentiating an interpolated vacuum-flux
   grid. Use ±1 and ±5 mm displacement and zero displacement. Require slope
   agreement within 1% with the recorded spline-field calculation, step
   agreement within 0.1%, and zero force within 1 N. Report the sign without
   converting it into a wall-coupled instability growth rate.
4. Independently trace all five original offsets (1, 2, 5, 10, 20 mm) in all
   eight fields using toroidal angle as the independent coordinate, adaptive
   DOP853, and signed-distance wall events. The old tracer used fixed-step RK4
   in poloidal arc length and straight chord/wall intersections. Both methods
   share the saved flux field, cubic interpolant, Fvac = 11.52 T m, and wall.
   Standard settings: rtol 1e-9, atol (1e-10 m, 1e-10 m, 1e-8 m), maximum
   toroidal-angle step 0.1 rad, maximum angle 200 rad. Tight settings: rtol
   1e-11, atol (1e-12, 1e-12, 1e-10), maximum step 0.05 rad. Retain failures.
5. Require each adaptive trace to hit the wall, stay within the field domain,
   and conserve normalized flux within 1e-7. Relative to old RK4 require
   strike agreement within 1 mm, length within 1 cm, and projected heat within
   0.5%. Require standard/tight adaptive agreement within 10 micrometres,
   0.1 mm connection length, and 0.1% projected heat. Check reverse-direction
   traces at 1 mm in all eight fields against reflected forward strikes using
   the same 10 micrometre / 0.1 mm / 0.1% limits. No symmetry of a supplied wall
   is assumed silently: a failed mirror check remains a failed check.
6. Verify wall events and length against an analytic uniform vertical field
   and rectangular wall in both directions. Position tolerance 1e-9 m, length
   1e-8 m. Trace an intentionally inconsistent flux/field pair and require
   flux conservation to reject it. These controls check the new tracer rather
   than asserting that a second implementation must be correct.
7. On all four accepted fine-grid fields, sample a nested 17/33-point geometric
   offset grid from 0.25 to 20 mm, also retaining the original five offsets.
   Report target component/segment, connection length and representative heat
   (6 mm width, 50% SOL radiation, 25% one-target share). This checks sparse
   sampling sensitivity; it does not prove a continuous maximum or remove
   equilibrium-grid, sub-grid launch, wall-shape, or physical-model uncertainty.
   A 17/33 sampled-maximum difference below 1% is only sampling consistency.
   Do not claim an improved candidate or trigger 513-grid optimization from
   these post hoc validation diagnostics.

## Reporting

Record PASS/FAIL for the numerical checks, raw traces and input/code hashes.
Report grid-dependent rankings and any newly exposed failure without rewriting
003's historical results. Shared physics and shared inputs limit independence.
Full MHD/wall feedback, predictive turbulence/burn, SOL detachment/neutrals,
structural/HTS/cooling qualification and neutron transport remain NOT RUN.

Method references: [SciPy solve_ivp](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.integrate.solve_ivp.html)
and [FreeGS field tracing](https://freegs.readthedocs.io/en/stable/diagnostics.html).
The toroidal-angle equations are dR/dφ = R²BR/F, dZ/dφ = R²BZ/F,
dL/dφ = R sqrt(1 + (RBR/F)² + (RBZ/F)²); reverse tracing changes the first
two signs only. Under the axisymmetric vacuum-SOL assumption F = Fvac.
