# OPENSTEP-010 · the p9 strike crosses the lower-wall corner on both grids

**24 November 2026 · STEP SPP-001 EB-CC · computational comparison**

The accepted coarse solve fills the missing +5 cm entry from OPENSTEP-003. Both local meshes put the baseline strike on wall face 12 and the displaced strike on face 13. At the fixed 1 mm upstream launch, the projected heat flux increases by a factor of 5.35 on the coarse grid and 5.36 on the fine grid. The independent displaced Fiesta result remains **UNRESOLVED**.

| Local grid (R × Z) | Baseline strike relative to corner | +5 cm strike relative to corner | Baseline projected heat flux | +5 cm projected heat flux |
| --- | ---: | ---: | ---: | ---: |
| 129 × 257 | −65.69 mm | +3.74 mm | 10.56 MW/m² | 56.44 MW/m² |
| 257 × 513 | −54.54 mm | +5.44 mm | 10.45 MW/m² | 56.04 MW/m² |

Distances run along the supplied wall polygon. Zero is the shared vertex at (R, Z) = (5.855, −8.52316) m. Positive is the side corresponding to face 13. Only the upper and lower p9 packs moved, each 5 cm toward the midplane. The implied quantity is normal heat flux at one field-line strike for the same assumed incident power, radiation fraction, target share and upstream width. The physical peak load and onset displacement remain open. Neither grid had an accepted +2.5 cm field in the prior scan.

## What changed in the numerical evidence

- **Coarse recovery.** The restart from the archived coarse +10 cm controlled field passed with full-domain normalized defect 3.07417 × 10⁻⁸ against a 10⁻⁵ ceiling. Pressure-profile relative error was 1.22 × 10⁻¹⁵, total-current relative error was zero at reported precision, minimum F² was 115.0253 T² m² and up/down asymmetry was 1.42 × 10⁻¹⁴ Wb/rad.
- **Negative evidence.** The other preregistered restart, from the accepted fine +5 cm field, ended with an IndexError before full-domain acceptance. Its last saved iterate, raw report and log are included. The conditional third restart was unnecessary. The earlier failed attempts in OPENSTEP-003 keep their historical verdicts.
- **Uncached check.** Reapplying the original full-domain boundary operator to the accepted field returned a defect of 3.07419 × 10⁻⁸. An imposed perturbation raised this to 0.01202 and was rejected by the same threshold. Both implementations share FreeGS.
- **Resolution.** The displaced strike moved 1.710 mm between grids. Including the larger trace-tightening displacement gives an observed numerical allowance of 1.712 mm, below the 2 mm minimum guard. Both displaced strikes lie beyond that guard. The corresponding baseline allowance was 11.154 mm; both baseline strikes clear it on the opposite side. These are two-grid diagnostics, not rigorous continuum error bounds.
- **Heat diagnostic.** The fine-grid change is +45.5911 MW/m². The sum of the absolute baseline and displaced coarse-to-fine heat changes is 0.49765 MW/m². This passes the historical effect-size check for an *increase*. The design-selection criterion in OPENSTEP-003 sought a reduction.
- **Released Fiesta field.** On UKAEA’s archived, unshifted 257 × 513 equilibrium, the same tracer hit face 12, 56.58 mm before the vertex, 2.035 mm from the reconstructed fine-grid strike. The archived input declares 22.7604612 MA, whereas the matched pair requires 22.7744106 MA. This is a useful baseline comparison. The release supplies no independently solved +5 cm counterpart for this test. No Fiesta solver executable or matched return was available here.

## What is ready for an independent Fiesta run

The two case files in `inputs/` specify the mesh, launch rule, wall, nonlinear pressure/current constraint, exact profile coefficients, and signed filament currents and positions in SI units. Each file set has 2,196 filaments; 414 p9 filaments move, with all other positions and currents checked for equality. The scale factors on the pressure and FF′ shapes in the local code enforce the matched operating point. Holding the native normalisation fixed instead would change the comparison.

The frozen protocol specifies a 5 mm baseline position tolerance, a normal-field tolerance of the larger of 0.02 T or 10%, a 2 mm minimum corner guard, and a separate quantitative comparison after the face decision. These are proposed numerical tolerances. A case with insufficient resolution, an unmatched baseline, a third face, or missing inputs remains unresolved. The recorded uncertainty is the distance between coarse and fine strikes plus the larger trace-tightening shift. Independent review of source matching, residual definitions and solver provenance is a prerequisite for accepting external fields.

The table `results/pair-comparison.csv` contains the four local rows and four blank independent rows. `FIESTA-RETURN.md` gives the return format. SHA-256 of the protocol before the new solves was `c8e1348a25d214982e5a9aa1d72cf14489daa8f5d341a79b483e9cf2e8c9808b`. This was a local protocol freeze; the historical fine-grid prediction was already public.

## Sources and replication

Parent code and historical fields are pinned at [enuminous/Tokamak, 149f5eca](https://github.com/enuminous/Tokamak/tree/149f5eca9e82464fdc0c6bf274f757bd12221772). Source geometry and baseline equilibrium are from Theodore Brown, Francis Casson, Agnieszka Hudoba, Stephen Marsden, Emmi Tholerus, Thomas Wilson and the STEP Team. The bundle includes their CC BY 4.0 terms, citation, hashes and the derived coil, profile and wall tables. [OpenSTEP dataset](https://doi.org/10.14468/07jt-s540) · [Pinned UKAEA source](https://github.com/ukaea/OpenSTEP/tree/6f66ae09c60b361d600b178416ef3f22b8d0aa6a) · [Earlier p9 working paper](https://github.com/enuminous/papers/blob/main/STEP-EB-CC-p9-Strike-Point-and-Fiesta-Comparison-2026-11-24.md).

The archive includes the scripts and historical inputs needed for this replay. See its top-level REPLAY.md for exact commands, environment and output files.
