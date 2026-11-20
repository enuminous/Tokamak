# TriSphere prototype 02: recorded results

November 20, 2026. These are executed computational results under the chosen [simulation contract](TRISPHERE-CONTRACT.md). No independent review or physical experiment is claimed.

## Main result

**Accounting passes. The default thirteen-versus-five radial comparison fails its exploratory tolerance.** This is a discrepancy between two specified closures, not a refutation of the entire blueprint. The position count, potential, transit clock, contact law, and release rates remain implementation assumptions.

| Run | Radial position RMSE | Mapped shelf L1 | Accounting | Candidate agreement |
|---|---:|---:|---|---|
| containment | 0.054597184 | 0.001684758 | PASS | FAIL |
| exhaust | 0.054597184 | 0.000202375 | PASS | FAIL |
| no-drive | 0.001687257 | 0.001684758 | PASS | PASS |

The position-RMSE tolerance is 0.05. Exhaust changes exported energy and material accounting; by construction it does not change the radial contact trajectory, so its radial RMSE is the same. The zero-drive PASS is agreement of settling traces, not preservation of an active breath. Because the transport clock is independent, material still circulates in that zero-drive inventory run. These limits are visible in the model contract.

## Timestep sensitivity

| Step | Position RMSE | Thirteen max energy residual | Five max energy residual | Agreement |
|---:|---:|---:|---:|---|
| 0.02 | 0.054594228 | 9.32285e-05 | 0.00045638 | FAIL |
| 0.01 | 0.054597184 | 9.04327e-05 | 0.000321129 | FAIL |
| 0.005 | 0.054600302 | 8.67672e-06 | 5.6236e-06 | FAIL |

Halving the default step from 0.01 to 0.005 changes the RMSE by about 0.00000312 and reduces the recorded energy errors. This supports the persistence of this particular discrepancy at these resolutions; it is not a convergence proof for all settings.

## Default containment inventory

| Quantity at time 96 | Thirteen | Five |
|---|---:|---:|
| Material remaining | 1.000000000 | 1.000000000 |
| Mobile energy | 0.038277728 | 0.038379720 |
| Retained heat | 1.975908733 | 1.978566982 |
| Supplied external work | 1.014186461 | 1.016946702 |
| First-return material fraction | 1.000000000 | 1.000000000 |
| First-return energy / initial energy | 0.069752366 | 0.070020775 |
| Repeated material returns, cumulative | 9.658918678 | 9.685206682 |

All energy in this table belongs to the inventory circuit, not the separate radial probe. Both have first material return at 6.5 time units. Mean first return over the observed returning material is 9.4907 for thirteen and 9.4655 for five. The repeated-return total can exceed one; it is not a recovery fraction.

## Drive–damping scan

The published grid contains 25 (k, gamma) pairs, each with both models and a +0.02 initial-position perturbation: 100 radial integrations at duration 96 and step 0.01. All grid numerical checks pass the stated 0.001 radial-energy bound. For each model, the five k=0 cells settle and the twenty nonzero-k cells meet both the finite-window recurrence and perturbation-distance criteria. Inelastic contacts also dissipate motion when gamma=0. No bifurcation location or general stability theorem follows from this coarse grid.

The grid uses k = 0, 0.25, 0.5, 0.75, 1 and gamma = 0, 0.15, 0.3, 0.6, 1. The full numerical values, recurrence errors, perturbation distances, and energy residuals are retained in [JSON](results/trisphere-v2/parameter-scan.json) and [CSV](results/trisphere-v2/parameter-scan.csv).

## Verification and evidence

- `node verify.js`: the existing flux, inventory, Hopf, and center-kick checks pass.
- `node verify-trisphere.js`: 14 checks pass, including analytic damped motion, independent potential differentiation, contact accounting, conservation across routing extremes, first-return bookkeeping, source hashing, deterministic replay, invalid inputs, and timestep sensitivity. [Verification record](results/trisphere-v2/verification.json).
- [Evidence JSON](results/trisphere-v2/evidence.json) records exact parameters, environment, source and implementation hashes, negative results, and convergence values.
- [Default summary](results/trisphere-v2/default-summary.json), [radial samples every 0.1 time unit](results/trisphere-v2/radial-sampled-0.1.csv), and [all transport ticks](results/trisphere-v2/transport-all-ticks.csv) are published. `node run-trisphere.js --full` and the browser export reproduce the complete unsampled radial traces.
- Execution environment: Node v24.22.3, linux / x64. No third-party runtime libraries or random seeds.
- The new interface is checked separately for default and exhaust runs, playback, observer-view independence, exports, and the parameter scan. Browser-specific findings are recorded in `results/trisphere-v2/interface-checks.json`.

## Next bounded test

Vary the contact law and shelf-release closure, then rerun a comparison with equal initial mechanical energies. The present five-position aggregation retains original route delays and route tags; a complete reduced model requires a separate derivation of its state and error bounds. LCL material laws, gravity sourcing, recognition-driven geometry, and independent physical validation remain UNRESOLVED.
