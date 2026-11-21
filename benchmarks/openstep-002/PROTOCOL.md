# OPENSTEP-002 — extended simulation screens

Recorded 20 November 2026 (America/Los_Angeles), before the extension solves.
This is an exploratory follow-on to OPENSTEP-001, not an experimental validation
or an independently preregistered study. Historical OPENSTEP-001 results remain frozen.

## Scope and inputs

Compare the original coil arrangement with both p9 packs translated 0.10 m toward
the midplane. Reuse the pinned OpenSTEP and FreeGS inputs and conventions of 001.
Additional pinned inputs are the EB-CC flat-top kinetic/transport dataset, its
summary, and the SPR45 wall outline from the same OpenSTEP revision. The JETTO
flat-top and Fiesta free-boundary cases are related but not identical. Report
their differences; mapping a profile between them is an explicit assumption.

## Calculations and reporting rules

1. **Numerical refinement.** Attempt both arms at 513 × 1025 with warm starts
   from 257 × 513. Retain all attempts. Accept a solution only if its independently
   evaluated normalized fixed-point defect is ≤ 1e-5. Compare 129, 257, 513 results.
   Call an effect resolved only if it exceeds the sum of the two arms' last
   refinement changes. This heuristic is not a rigorous discretization bound.
2. **Operating-point control.** Repeat at 129 and 257 holding the baseline's
   pressure-versus-normalized-flux function and total plasma current fixed,
   rescaling p′ and FF′ at each iterate. Keep coil currents fixed. This tests
   whether the original pressure/current increases confound geometric effects.
3. **Stability screens.** Calculate q on closed flux surfaces, beta and normalized
   beta. Do not turn empirical beta limits into a universal stability verdict.
   Compute the vertical force on the unchanged plasma current distribution under
   ±1, ±5, ±10 mm rigid translations in the fixed external coil field. Positive
   dFz/dz is destabilizing in this no-wall rigid-displacement model. Compare grids
   and step sizes. Attempt an axisymmetric linear-stability calculation if an
   applicable solver and adequate inputs can be established. Full 3-D ideal,
   resistive and kinetic stability remain unresolved without those calculations.
4. **Confinement/power balance.** Extract source thermal energy, line-average
   density, auxiliary/alpha/ohmic/radiation powers. Evaluate IPB98(y,2), explicitly
   separating total-heating and radiation-subtracted conventions. Integrate a
   zero-dimensional thermal-energy balance over 30 s with H = 0.7, 1.0, 1.3, 1.6,
   auxiliary power factors 0.8, 1.0, 1.2, and radiation factors 0.8, 1.0, 1.2.
   Frozen heating/radiation is a sensitivity model, not a self-consistent burn or
   turbulence prediction. Report required H and losses without calling a chosen
   H an observed confinement improvement.
5. **Exhaust/heat loads.** Trace open field lines from outboard-midplane offsets
   1, 2, 5, 10, 20 mm to the supplied wall/domes; compare tracing resolution.
   Compute strike locations, connection lengths and geometric flux expansion.
   Sweep exponential upstream heat-flux widths 1.8, 3, 6, 12.7 mm, SOL radiation
   fractions 0, 0.5, 0.9 and outer-target power fractions 0.25, 0.5. Compare the
   resulting projected target loads with the published STEP 10 MW/m² steady
   target criterion. A load below that value is only a conditional screen; no
   detachment, recycling or neutral transport is simulated.
6. **Engineering and systems.** Check coil-pack intersections and wall clearance;
   calculate external magnetic forces on each pack (other coils plus plasma;
   no self-force), pack-average ampere-turn density and magnetic-pressure scales.
   Convert loads to required support area over an explicitly assumed allowable
   stress sweep (100, 300, 600 MPa), not a material qualification. Calculate
   wall-average neutron load and sweep net-electric accounting with thermal
   efficiency 0.30–0.45, auxiliary wall-plug efficiency 0.30–0.70, parasitic
   electricity 50–200 MW. Assume unity blanket energy multiplication and complete
   thermal capture for this accounting screen. Missing CAD, HTS critical surfaces,
   support/cooling design, neutron transport, damage and tritium breeding remain
   unresolved; they are not silently replaced by favorable assumptions.

## Verification and artifacts

Check source hashes, field conventions, equilibrium residuals, finite/nonnegative
physical quantities where required, q-integral refinement, force sign/refinement,
field-line flux conservation, energy-balance residual, analytic ODE agreement,
and power accounting. Export machine-readable results, plots, replay commands,
and explicit assumption/status fields. Code verification PASS does not mean a
tokamak feasibility PASS. Report execution, model finding and physical claim
separately. Implementation corrections and any protocol amendments go in a dated
development log; do not erase failed attempts or retune thresholds after seeing
results.
