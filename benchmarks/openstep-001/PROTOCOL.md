# OPENSTEP-001: equilibrium reproduction and mirrored-coil perturbation

Protocol recorded on 2026-11-20 before the first equilibrium solve. Input inspection and unit/sign checks preceded this protocol; this is an exploratory computational benchmark, not an independently preregistered experiment.

## Reference and question

Reproduce the UKAEA OpenSTEP EB-CC free-boundary Fiesta equilibrium at upstream commit `6f66ae09c60b361d600b178416ef3f22b8d0aa6a`. This is a published design simulation, not an experimental discharge or a new reactor design. Preserve its seven circuit currents, fourteen coil filament sets, and pressure/current profile functions. Use SI units and explicitly convert flux conventions. Source data is CC BY 4.0; see `source/CITATION-OpenSTEP.cff` and `source/LICENSE-OpenSTEP.txt`.

Then test one chosen interpretation of the TriSphere hourglass/mirror idea: translate both p9 coil packs 0.10 m toward the midplane, preserving their internal filament geometry, circuit current, and every other coil. Upper p9: Z -> Z - 0.10 m; lower p9: Z -> Z + 0.10 m. This is an ordinary axisymmetric magnetic-coil perturbation inspired by the drawing. The displacement is an analyst-selected test value, not a prediction derived from the thirteen/five layers. No pressure, recycling, confinement, or fusion improvement is presumed.

## Arms and numerical procedure

1. Published reference field and current density, used only as the target, initial guess, and input consistency check.
2. Baseline free-boundary Grad-Shafranov solve with the published coils and currents.
3. Mirrored p9 translation with identical plasma profile functions and all currents fixed. Re-solve the plasma; a vacuum-only field addition does not count as an equilibrium result.

Use FreeGS 0.8.2 for the field operator, Green functions, and critical-point extraction. Initially use relaxed Picard iteration; if fixed-current Picard diverges, preserve that attempt and use a documented root solver without changing the physical inputs. Enforce up-down symmetry numerically; this does not establish vertical stability. Domain R = 0.5..9.0 m, Z = -10..10 m. Compare 65x129, 129x257, and 257x513 meshes. The highest mesh matches the released reference. No fitting of coils to the target is allowed in the primary reproduction.

Pressure derivative and FF' shapes, including their amplitudes, remain fixed as functions of normalized flux during each solve. Pressure itself is obtained by integration with p(edge)=0 Pa, and F(edge)=11.52 T m. If a separate total-current-normalized diagnostic is needed, label it separately; it cannot silently replace the primary arm.

## Pre-specified checks

- Data hashes and flux/current convention checks must pass.
- Nonlinear fixed-point residual: maximum plasma-flux defect / published axis-to-boundary flux difference <= 1e-5, with a finite closed core and appropriate axis/X-point topology. A small iteration step alone is insufficient.
- Fine-grid baseline reproduction: gauge-aligned core flux RMSE / reference flux span <= 1%; axis location error <= 0.05 m; each primary X-point location error <= 0.10 m; total plasma current difference <= 1%. Report all four, with the raw values.
- Numerical resolution: fine-versus-medium changes in axis and X-point locations <= 0.05 m, and total current <= 1%. Report flux discrepancies as well. If a tested effect is no larger than the observed refinement difference, label that effect unresolved.
- Modified-arm outputs: nonlinear residual, axis and X-point locations, enclosed cross-section and volume, total current, midplane radii, and integrated pressure. Report changes with both grids. None is a confinement-time or stability measure.

PASS means only that the named numerical criterion is met. FAIL means a completed comparison exceeded that criterion. UNRESOLVED means missing inputs, failed convergence, ambiguous topology, or inadequate numerical resolution prevents that comparison. NOT_APPLICABLE covers physical confinement, stability, heat loads, materials, engineering clearance, and net power, which this equilibrium test does not calculate. Preserve unsuccessful solver attempts; do not change thresholds after seeing results.
