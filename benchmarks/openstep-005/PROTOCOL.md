# OPENSTEP-005 — flux contours, corner peaks and wall-model readiness

Frozen before the new physical-field runs on 2026-11-21 (Pacific). Parent:
`4939a9314d2db8482a4a0f7421ca4bb1d125917d`. This experiment adds evidence;
it does not replace OPENSTEP-004's failed assertions.

## Fixed inputs and scope

Use all eight accepted OPENSTEP-003 fields, checking their recorded hashes.
Keep the same bicubic flux interpolant, wall outline, F = 11.52 T m and heat
model: 6 mm exponential upstream width, 50% SOL radiation and 25% of the
remaining power at one target. These are imposed model assumptions. No new
equilibrium, transport solution, CAD qualification or experimental validation
is implied. The wall-radius variants hold the equilibrium fixed.

## Contour and connection-length test

Follow psi = psi_launch using alternating R/Z implicit charts, selecting the
coordinate with the larger tangent component. Newton projection must converge;
reject branch jumps, domain exits, critical degeneracy and step exhaustion.
Split at interpolation-grid crossings. Integrate connection length separately
by Gauss-Legendre quadrature of

`sqrt(1 + (dv/du)^2) * sqrt(1 + F^2 / |grad psi|^2) du`.

Run maximum coordinate steps 20/10 mm with 8/16 quadrature nodes. Test offsets
1, 2, 5, 10, 20 mm in the positive field direction on all eight fields; repeat
1 mm in the reverse direction. Require hits, normalized flux error <= 1e-7,
wall error <= 1e-9 m; refinement changes <= 1e-5 m in strike, 1e-4 m in length
and 0.1% in heat. Mirror checks use the same tolerances. Compare against the
saved OPENSTEP-004 third-tolerance 1 mm results at those same limits. Other
saved tight DOP853 comparisons are diagnostics, not evidence that an old
failure disappeared. Controls include straight and curved analytic contours,
both directions, and deliberate field/flux inconsistency rejection.

## Heat peaks and corner rounding

On each of the four fine-grid fields, study the closed offset window
[0.25, 20] mm only. Map wall segments to launch flux, verify first-hit branch
membership with full traces, and sample/refine each connected target interval.
Locate segment transitions from the flux at the actual corner. At sharp
corners report both one-sided heat limits; there is no unique corner normal.
Compare nested sampling and bounded local maxima; require peak changes < 1%
and record branch/flux agreement. A converged search is not a certified global
bound or a statement about offsets outside this window.

Repeat with assumed circular fillets of radius 1, 5 and 10 mm at lower main-wall
vertex 13 and its upper mirror (357). Use analytic circular normals. These
radii are sensitivity cases, not measured dimensions. Preserve all other wall
segments and domes. Verify tangency, radius, mirror symmetry and first-hit
mapping. Do not call a nominal heat load a material qualification.

## Conducting wall and feedback

Inspect the available geometry/material/circuit/controller inputs. Build a
machine-readable input contract and fail closed on missing, invalid or
unreferenced physical parameters. Build and test a reduced wall-current and
feedback implementation using explicitly synthetic parameters: compare its
eigenvalues, ideal/no-wall limits, energy/passivity and time integration with
analytic controls; include an unstable feedback-sign control. Synthetic passes
do not establish tokamak stability. Actual-device wall modes/feedback remain
NOT RUN / UNRESOLVED unless the required calibrated inputs are present.

## Reporting

Record commands, versions, code/protocol/input hashes, every result and failure,
timings, raw trace/footprint tables, figures and a SHA-256/Git-blob manifest.
Any numerical implementation correction is documented before the affected
rerun; thresholds and historical outcomes remain unchanged. Distinguish
assertions, traces, independent controls and physical claims.
