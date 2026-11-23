# OPENSTEP-007 — matched DIII-D mode and time evolution

Exploratory follow-up to OPENSTEP-006 at Tokamak commit `7f2842f3086fae73ad51c1b784830862c314658f`. The historical verdict and checks remain as recorded.

## Method

Use the archived coarse, second-order DIII-D mesh and the same EFIT input, vessel, coils, equilibrium reconstruction and edge-current ramp. Run OpenFUSIONToolkit 26.9. Build the eigenmode at the reconstructed equilibrium. In each time trajectory, clear the numerical axis-position target and prescribe the baseline coil currents with zero applied voltages. Seed the flux before initializing the native time solver, which copies the initial flux, and recalculate plasma bounds when applying the seed. Normalize the mode with a deterministic sign, then run separate positive and negative seeds. Fit the log of the absolute nodal projection of half their difference over the first e-folding interval, excluding time zero. This centered diagnostic removes a common drift to first order. The relative orthogonal nodal norm measures changes in shape away from the reference eigenvector. It is not a left-eigenvector projection or a physical energy norm.

The nonlinear solver recomputes flux bounds. The matched case therefore includes the bounding-flux terms in the eigensolve. The nonlinear operator also rescales pressure and toroidal-field profile amplitudes when the total-current and current-ratio targets are active. The explicit eigenvalue assembly uses fixed amplitudes. The fixed-profile runs clear those targets after constructing the equilibrium so both calculations use the same amplitude treatment. The targeted cases retain both current targets as controls. The fixed-bounds eigenvalue with active time-domain targets serves as a historical-style control. See the pinned [native operators](https://github.com/hansec/OpenFUSIONToolkit/blob/73d8eb09bce0a4f4c56b88f13fcf36f951c53e91/src/physics/grad_shaf_td.F90#L697) and [eigenvalue assembly](https://github.com/hansec/OpenFUSIONToolkit/blob/73d8eb09bce0a4f4c56b88f13fcf36f951c53e91/src/physics/grad_shaf_td.F90#L1299).

Use the historical 10% growth agreement criterion and check whether halving the timestep changes the fitted rate by no more than 5%. The smaller seed tests sensitivity to perturbation size. These are new diagnostics after the historical failure. Neither the controls nor the matched cases claim independent experimental validation.

## Result

The matched comparison passes on the archived coarse mesh. With boundary terms included and profile amplitudes fixed, halving the timestep reduced the difference from 1.88% to 0.75%. The timestep change in the fitted rate was 1.11%, inside the 5% screen. The tenfold smaller seed also passed, with a 2.20% difference from the eigenvalue. The current-target controls miss the 10% growth criterion at both steps and both seed amplitudes. The principal mode remains unstable in the matched comparison.

The discrepancy has a demonstrated source in the treatment of profile amplitudes for this bounds-included setup. The original 945.98/s eigenvalue belongs to a different, fixed-bounds calculation. An eigenvalue that linearizes the current-target rescaling is still needed to grade the targeted evolution against its own operator. This work does not rerun the feedback, qualify DIII-D hardware, or supply the missing STEP passive-wall and controller inputs.

See [fixed profiles](results/matched.json) and [active current targets](results/targets.json) for per-step projection and mode-shape records.

## Replay

Install the dependencies in [OPENSTEP-006](../openstep-006/requirements.txt) and run from the repository root. Output directories are separate because case names overlap.

```bash
OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-007/compare.py --fixed-profiles --output /tmp/openstep007-matched
OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-007/compare.py --output /tmp/openstep007-targets
```

The replay writes signed raw field trajectories, solver logs and grading summaries. Solver retries, unequal signed time grids or incompatible signed modes stop grading. The recorded environment was Python 3.12.14 with NumPy 2.3.5, SciPy 1.17.0 and h5py 3.16.0 on Linux x86-64.

## Input hashes

| Archived OPENSTEP-006 input | SHA-256 |
|---|---|
| `results/diiid-mesh-1.h5` | `80420dc5d1aefa9280d2a293a19b20c8c497f539a083254bfb82652f7dadc4a5` |
| `source/g192185.02440` | `685426f5eb54573d921466beea78e19db01ec5c88b2e254eff7d924de5f0600b` |
| `source/DIIID_baseline_cells.json` | `1c58a776362e6b6e6aa09e70e9e45c615afb7b9722c507d002ef58d96f268d1e` |
