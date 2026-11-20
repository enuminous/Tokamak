# Numerical method and provenance notes

## Inputs and conventions

The source is Brown et al. (2025), *OpenSTEP: public data release of the STEP Prototype Powerplant scenario SPP-001*, UKAEA, DOI [10.14468/07jt-s540](https://doi.org/10.14468/07jt-s540), at commit `6f66ae09c60b361d600b178416ef3f22b8d0aa6a`. The original free-boundary calculation is associated with Hudoba et al., *Nuclear Fusion* 64 (2024) 086055, DOI [10.1088/1741-4326/ad53e2](https://doi.org/10.1088/1741-4326/ad53e2). This work uses that design case; it is not a measurement comparison or an endorsement from UKAEA.

`equilibrium.mat` identifies Fiesta 8.13, a 257 x 513 grid, seven circuit currents, and a converged result dated 22 September 2025. `coilset.mat` supplies fourteen coil packs with 2,196 numerical filaments in total. Each pack's filament weights sum to one. Circuit currents therefore represent the total equivalent one-turn toroidal current of each pack, not a newly specified winding current and physical turn count.

The original Fiesta field uses total poloidal flux. The internal FreeGS flux is `psi = Psi_Fiesta / (2*pi)` in Wb/radian. The native grid vector is reshaped as `(nz, nr)` in Fortran order, then transposed. R and Z are metres, pressure is Pa, current is A, current density is A/m², and F = R B_phi is T m.

The OpenSTEP README describes IMAS Data Dictionary 3 / COCOS 11. The actual NetCDF file declares Data Dictionary **4.0.0**, corresponding to COCOS **17**. Its flux is exactly the negative of the Fiesta flux. For this file, `psi_FreeGS = -Psi_NC/(2*pi)`, `pprime_FreeGS = -2*pi*dpressure_dpsi_NC`, and `FFprime_FreeGS = -2*pi*f_df_dpsi_NC`. The data, its metadata, the native MAT file, and current-density consistency checks determine this conversion; blindly following the README would give the wrong sign. The native piecewise cubic alpha/beta profiles, multiplied by their stored scale, are used for p' and FF', avoiding the NetCDF's additional 256-point profile resampling.

## Equations and boundary conditions

The code solves the static axisymmetric Grad-Shafranov equation:

`Delta* psi = -mu0 R J_phi`, with `J_phi = R p'(s) + FF'(s)/(mu0 R)` inside the connected plasma core and zero plasma current outside. `s = (psi - psi_axis)/(psi_boundary - psi_axis)`.

`Delta* = d²/dR² - (1/R)d/dR + d²/dZ²`. The total field is the sum of the plasma solution and the explicitly calculated field of all published coil filaments. Coil currents are fixed; the magnetic axis and separatrix are found from the solution. FreeGS's von Hagenow boundary routine computes the plasma contribution on the outer rectangular boundary; no published boundary flux is imposed there. The published plasma flux is an initial guess, not a fixed source term or a final answer.

Use `mu0 = 4*pi*1e-7 H/m`, matching the source software convention. Set p(edge)=0 Pa and F(edge)=11.52 T m. Native profile amplitudes and shapes are held fixed versus normalized flux, so integrated pressure and total plasma current can change after the coil movement. There is no total-current renormalization or coil-current fitting in the scored arms.

## Solver development

The protocol's numerical thresholds were recorded before the first solve and remain unchanged. Solver development was adaptive and is not independently preregistered.

Relaxed Picard runs and initial root-solver trials are retained as unsuccessful development attempts. During development, a wrapper bug was found: FreeGS updates the supplied plasma array's boundary in place. Root residuals must retain an unmodified copy of the trial field. The corrected wrapper does so, and checks the final full-domain residual independently after solving. Earlier results from the faulty wrapper are excluded from benchmark evidence even when its internal solver reported success.

FreeGS's default critical-point routine stops when the local poloidal field is below 1 mT. The wrapper refines those roots using derivatives of the same flux spline. Up-down symmetry is imposed, with half-domain unknowns in the final root solver; that restriction excludes antisymmetric perturbations and makes no statement about vertical stability.

A hard grid-node current cutoff at the separatrix produced non-smooth residuals. The scored implementation uses a cell-area fraction for cut cells: locally approximate normalized flux as linear across a rectangular cell and integrate the fraction with s<1 analytically. Cells disconnected from the magnetic-axis core are excluded. This changes the numerical treatment of a finite edge current density; it does not alter the published profile functions. Grid refinement is therefore part of acceptance. The full field equation is solved again for the translated coils. Failed hard-cutoff trials remain in the development record.

## Limits

This tests agreement between numerical equilibrium calculations under specified assumptions. It does not calculate MHD stability, turbulent transport, confinement time, wall/divertor heat loads, conductor stresses, electrical engineering, winding feasibility, structural clearance, fusion power, or net power. A preserved separatrix is insufficient evidence for any of those outcomes. The 0.10 m p9 translation is an exploratory interpretation of TriSphere's mirrored hourglass motif, not a mathematical consequence of its layer counts or evidence for a new force.
