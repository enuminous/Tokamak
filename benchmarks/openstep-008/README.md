# OPENSTEP-008 · Current-target mode growth on DIII-D

The original study and its failed first predictor have been recovered. The [archive report](ARCHIVE-REPORT.md), [amended protocol](PROTOCOL.md), [original protocol](initial/PROTOCOL.md), [frozen predictions and sampled series](record/results), [first predictor](record/initial-predictor-results/1/krylov.json) and executable replay are supplied. The public repository reuses OPENSTEP-006's two meshes, EFIT and recorded upstream input cells.

On November 24, all 81 entries in the original 407,559,786-byte archive were checked against its internal [manifest](ARCHIVE-SHA256SUMS). ZIP SHA-256: `e12313e4173cd100aa0dbcf6528a7e5b54d838f2a1da637d880556342c4e7439`. The original ZIP retains the full nodal trajectories, signed seeds, logs and plot. Git stores the original projections, axis histories, grading records and code. Replaying the command below regenerates full nodal fields locally. Paths in ARCHIVE-REPORT and ARCHIVE-SHA256SUMS refer to the original extracted ZIP layout.

| Current targets active | Coarse, 35,481 unknowns | Fine, 121,479 unknowns |
|---|---:|---:|
| Frozen forecast, per second | 774.94 | 760.82 |
| Finer-step projected flux fit, per second | 779.13 | 772.32 |
| Finer-step axis-height fit, per second | 779.14 | 772.31 |

Two distinct checks were completed. First, both historical raw-field pairs per arm/case were regraded on both meshes (24 signed trajectories, 12 paired cases). Second, the prediction and all 24 signed trajectories were freshly computed using the original native solver. Both observables passed for the two arms on both meshes. [Archive regrade log](../../verification/evidence/008-regrade.log) · [Fresh mesh reports](../../verification/evidence/native-008). The constrained and fixed-profile results concern the same DIII-D model. Both show instability. A STEP wall, circuit, controller and measured device response are separate obligations.

From the repository root in a new environment on Linux x86-64:

```sh
python -m pip install -r benchmarks/openstep-006/requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python benchmarks/openstep-008/replay.py /tmp/openstep008-new --workers 2
```

Choose a fresh output path for each replay. The first coarse prediction in the original study did not meet its residual criterion. The amended predictor passed before trajectory grading. The earlier OPENSTEP-006 and 007 counterexamples retain their original operator, assumptions and verdicts.
