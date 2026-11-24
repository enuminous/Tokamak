# OPENSTEP-008 | Current-target DIII-D mode growth

The calculation asks whether a small vertical displacement grows at the predicted rate while TokaMaker enforces plasma current and current ratio. Both the predictor and the nonlinear trajectories use the archived, axisymmetric DIII-D model.

## Results

| Mesh degrees of freedom | Profile treatment | Frozen rate (s⁻¹) | Finer-step flux fit (s⁻¹) | Finer-step axis fit (s⁻¹) | Flux / axis verdicts across all cases |
|---:|---|---:|---:|---:|---|
| 35,481 | Current targets active | 774.94 | 779.13 | 779.14 | PASS / PASS |
| 35,481 | Profiles fixed | 807.70 | 813.73 | 814.77 | PASS / PASS |
| 121,479 | Current targets active | 760.82 | 772.32 | 772.31 | PASS / PASS |
| 121,479 | Profiles fixed | 791.84 | 802.80 | 804.84 | PASS / PASS |

Refining the mesh changed the frozen targeted prediction by -1.82% relative to the coarse prediction. The protocol grades within-mesh agreement. Two meshes do not establish a continuum-limit rate.

## Signed-trajectory checks

The seed fraction multiplies the poloidal flux span. In each case the centered signal is half the positive-seed trajectory minus half the negative-seed trajectory. Growth rates use every positive-time sample through one predicted e-fold. The axis column comes from the native magnetic-axis height, in metres. Shape leakage is the fraction of the centered nodal norm orthogonal to the frozen mode.

| Mesh scale | Profiles | Case | Flux fit (s⁻¹) | Flux error | Axis fit (s⁻¹) | Axis error | Maximum shape leakage |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | target | base | 788.42 | 1.74% | 788.35 | 1.73% | 0.11% |
| 1 | target | half-step | 779.13 | 0.54% | 779.14 | 0.54% | 0.11% |
| 1 | target | small-seed | 796.22 | 2.75% | 796.50 | 2.78% | 0.22% |
| 1 | fixed | base | 822.87 | 1.88% | 822.58 | 1.84% | 0.08% |
| 1 | fixed | half-step | 813.73 | 0.75% | 814.77 | 0.88% | 0.13% |
| 1 | fixed | small-seed | 825.49 | 2.20% | 832.14 | 3.03% | 0.70% |
| 0.5 | target | base | 782.38 | 2.84% | 782.36 | 2.83% | 0.09% |
| 0.5 | target | half-step | 772.32 | 1.51% | 772.31 | 1.51% | 0.10% |
| 0.5 | target | small-seed | 785.35 | 3.22% | 787.70 | 3.53% | 0.57% |
| 0.5 | fixed | base | 813.58 | 2.75% | 813.74 | 2.77% | 0.03% |
| 0.5 | fixed | half-step | 802.80 | 1.38% | 804.84 | 1.64% | 0.41% |
| 0.5 | fixed | small-seed | 745.15 | 5.90% | 742.51 | 6.23% | 1.60% |

Halving the timestep must change the fitted rate by at most 5% of the finer-step value. Every growth-rate fit must fall within 10% of the frozen prediction. The tenfold smaller seed has the same growth-agreement requirement.

Mesh scale 1 returned 1.19% timestep change in projected flux and 1.18% in axis height.

Mesh scale 0.5 returned 1.30% timestep change in projected flux and 1.30% in axis height.

The figure in the replay ZIP (`results/axis-growth.png`) overlays the frozen prediction, flux projection and magnetic-axis height.

## What changed since OPENSTEP-007

OPENSTEP-007 projected the current-target trajectory onto the fixed-profile eigenvector. With that seed and projection, the finer-step fitted rate was 617.59 s⁻¹, compared with 807.70 s⁻¹ from the fixed-profile eigenproblem. OPENSTEP-008 takes centered differences of the target-active one-step solver, solves for a growing mode in the resulting Krylov subspace, and freezes that mode before seeding the signed nonlinear runs. The fixed-profile control starts from the native bounds-included eigenvector.

The absolute normalized dot product of the two coarse-mesh flux patterns is 0.521. The change of perturbation shape matters when comparing the two experiments. Both calculations share the same physics model and numerical implementation. Independent validation against measured DIII-D displacement and transfer to a STEP configuration remain unresolved.

## Prediction history

The initial coarse predictor finished 18 Krylov vectors with a fresh half-probe residual of 0.1037%. Its 0.1000% ceiling blocked a prediction. The preserved first attempt is UNRESOLVED. Before grading any trajectory, amendment A reduced the probe fourfold and tightened the linear and nonlinear solver tolerances for prediction only. The residual ceiling, growth tolerance and timestep tolerance stayed fixed. The prevalidation files record the frozen file hashes observed by the local runner.

Scale 1 froze the mode after 7 vectors at residual 0.0875%. Its half-probe projected rate was 778.40 s⁻¹.

Scale 0.5 froze the mode after 7 vectors at residual 0.0459%. Its half-probe projected rate was 762.39 s⁻¹.

## Sources and replay

Inputs and reference code come from [Tokamak at 0cb88b21](https://github.com/enuminous/Tokamak/tree/0cb88b21e8fce6106aa3b7d352a7a7dbfc0b22b7/benchmarks/openstep-006). The [previous comparison](https://github.com/enuminous/Tokamak/tree/0cb88b21e8fce6106aa3b7d352a7a7dbfc0b22b7/benchmarks/openstep-007) and [native time operator](https://github.com/hansec/OpenFUSIONToolkit/blob/73d8eb09bce0a4f4c56b88f13fcf36f951c53e91/src/physics/grad_shaf_td.F90) document the starting discrepancy and the treatment of profile amplitudes.

The ZIP contains the inputs, full positive/negative nodal fields and axes at every sample, iteration records, numerical prediction history, signed-run logs, grading code and SHA-256 file manifest. Each mesh has its own forecast and hash record. Independent recalculation from the archived fields checked the tabulated rates and shape diagnostics within floating-point tolerance. That recalculation was performed during this run. Physical measurements and controller feedback are outside its scope.

Extract the ZIP on Linux x86-64. From the extracted directory, the following commands use Python 3.12.14 and the pinned dependencies. The study ran in serial native processes. The replay driver can run two independent cases concurrently. Use a fresh output directory.

```bash
sha256sum -c SHA256SUMS
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r benchmarks/openstep-006/requirements.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python benchmarks/openstep-008/replay.py replay-output --workers 2
```

To verify the stored signed fields without running TokaMaker, use the following commands after installing NumPy.

```bash
OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-008/assess.py results --mesh 1
OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-008/assess.py results --mesh 0.5
```

The original predictor and protocol are under `benchmarks/openstep-008/initial/`, with logs under `initial-predictor-results/`. To replay the historical attempt, use a separate extracted copy, place those two files directly under `benchmarks/openstep-008/` and run `run.py predict --mesh 1 --output first-attempt` with the same thread settings.
