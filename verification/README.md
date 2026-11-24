# Tokamak verification series · November 24, 2026

[System specification and interfaces](SYSTEM.md) · [41 component requirements and failure modes](COMPONENTS.md) · [Test protocol](PROTOCOL.md) · [New target heat study](../benchmarks/openstep-009/README.md) · [Recovered native stability study](../benchmarks/openstep-008/README.md).

**Result.** The target-cooling calculation changes a decision in three of sixteen geometries when a single thermal assumption changes. The positive 1 cm p9 case with a sharp target rises from 1,793 K to 2,588 K. The two independently coded heat balances agree to 2.13 K at their tested comparison times. On a different machine model, a fresh DIII-D replay reproduced growth of an unstable vertical mode on two meshes and in two observables. Neither result qualifies a STEP component. The plant-level finding remains **UNRESOLVED**.

## Evidence by stage

| Stage and method | What was tested or inspected on this pass | Findings and boundaries |
|---|---|---|
| [Lab models](../TRISPHERE-CONTRACT.md) | Fresh Node model checks, full TriSphere sweep and seven browser entry points | Accounting and UI behavior are checkable. Thirteen/five dynamics differ; their equivalence is not established. Quark-stage power stays zero. These models give no plant power credit. |
| [001](../benchmarks/openstep-001/README.md) | Fresh 129 × 257 FreeGS baseline solve plus historical verifier | Final normalized defect 8.26 × 10⁻⁸; converged. Historical fine baseline core mismatch about 0.154%. Native MAT/NetCDF data are from a Fiesta simulation, so this is a source comparison. |
| [002](../benchmarks/openstep-002/README.md) | Ran original saved-field verifier; 66/66 checks passed | Refinement, heat and balance outputs remain conditional. A prescribed source cannot establish sustained burn. |
| [003](../benchmarks/openstep-003/README.md) | Ran original accepted-field, identity and warm-start verifier; 120/120 checks passed | Eight of 14 planned grid/shift pairs supplied accepted fields. The +5 cm and −5 cm cases do not form grid-matched pairs on both grids. No candidate met the selection rule. |
| [004](../benchmarks/openstep-004/README.md) | Recomputed preflight, analytic controls and independent defect/force checks on eight fields | Original complete tracing report retains 792 PASS / 220 FAIL. The surface-normal change between polygon faces 12 and 13 helps explain the +5 cm spike. Its applicability to hardware stays open. |
| [005](../benchmarks/openstep-005/README.md) | Ran the entire original suite from a clean baseline | New run 2,076 PASS / 0 FAIL. The published run had 2,064 PASS / 0 FAIL. In the baseline source, two archived stage records captured only two program files apiece; the current runner stamps eight. The twelve extra provenance comparisons account for the count difference. No new measured physics is credited. |
| [006](../benchmarks/openstep-006/README.md) | Original archived native verifier and fresh source-profile reactor calculation | Historical 23 PASS / 4 FAIL model comparisons and 340 integrity checks are distinct. Wrong-operator time comparisons still fail. Controller delay, burn stability, parasitics and fuel loss remain consequential. |
| [007](../benchmarks/openstep-007/README.md) | Recomputed all three signed fixed-profile pairs using native OFT | Finer-step fit 813.73/s vs eigenvalue 807.70/s. OPENSTEP-007 current-target controls failed against the different, fixed-profile eigenvector. |
| [008](../benchmarks/openstep-008/README.md) | Verified 81 original archive entries and regraded 24 signed trajectories; recomputed both predictors and 24 new signed trajectories | 12 paired cases, both projected flux and axis height, both meshes; all within the original 10% growth and 5% timestep gates. Rates remain positive. No independent experimental replication. |
| [009](../benchmarks/openstep-009/README.md) | Computed 32 thermal transients on three grids, analytic and rejection controls, plus a second time integration | 107/107 registered checks; 32/32 separate cross-checks. Four nominal and seven degraded cases exceed the assumed 1,800 K screen. Peak is extrapolative where the solid model breaks down. |

## Multimodal tests and adverse results

- **Magnetic fields and time signals.** Signed full-field arrays, projected flux, reconstructed axis height, seed reversal, step halving and mesh refinement constrain the internal native result. [Fresh mesh results](evidence/native-008) · [Original archive regrade](evidence/008-regrade.log).
- **Heat, geometry and time.** Spatially selected footprints feed the slab calculation; stored energy and time-integrated cooling independently check the energy account. Simulated histories and a derived figure identify where the threshold changes. [Numerical histories](../benchmarks/openstep-009/results/histories.csv) · [Two heat methods](../benchmarks/openstep-009/results/crosscheck.json).
- **Sensor records.** Pinned EXP-003 code was exercised on clean, sustained-bias and alternating-residual streams. Both monitors stayed quiet on clean data. The signed monitor detected sustained bias after nine samples and **missed the alternating fault**; the absolute monitor detected both after two. Three malformed streams were rejected before scoring. These are deterministic fixtures with a common exercise threshold. [Evidence](evidence/signals.json).
- **Visual and interactive.** Seven HTML entry points passed at desktop and phone widths. Three missing-data tests and an offline file test also passed (18/18). All 32 cooling readouts were compared against the source CSV on both screen sizes and offline. Tests covered keyboard inputs, real JSON downloads, readout-to-CSV/JSON correspondence, nonblank visible canvases, image loading, width and error feedback. The initial desktop Chromium executable could not obtain its process socket; the run used Google's Chromium headless shell 151.0.7922.34. [Case record and rendered witnesses](evidence/browser).
- **Measured-data contract.** Eight paired-trace fixtures distinguished tolerable error, out-of-tolerance observations and unusable records. Wrong units, bad clocks, duplicate/missing times, nonfinite data and changed bytes cannot produce agreement. Physical IR, calorimetry, neutron counts, strain, leak, dose and hardware-in-loop signals have no supplied acceptance records. [Fixture results](evidence/trace-controls.json) · [Measurement gates](COMPONENTS.md).
- **Failure propagation.** The register covers 29 physical and 12 computational subsystems. Forty required device/release obligations feed the plant decision. One toy subsystem is NOT_APPLICABLE to that decision. All 86 synthetic controls passed, including a decisive failure and a missing-evidence state injected at each required leaf; unrelated branches stayed eligible. In the real qualification record all required leaves remain UNRESOLVED. The synthetic all-green case only exercises software. [Dependency graph and outcomes](evidence/assurance.json).

Run `python verification/verify_release.py` for a read-only check of retained case denominators, frozen input bindings, numerical outcomes and expected negative findings. [Release check output](evidence/release-checks.json).

## Source selection, replay and stopping point

Screened [171 public repository names](portfolio-screen.json) under enuminous, then inspected relevant sources and pinned [six specific transfers from four repositories](external-sources.json). The implemented signal comparison imports the exact hashed EXP-003 monitor code. The ATC evaluation contributes read-only clean/fault controls. The ALEX trust-boundary document informs how file identity and independent observation are treated. Earlier papers locate historical claims. Cross-project analogies, cosmology, unrelated Lean builds and schematic propulsion supply no device-validation credit.

The [recorded environment](evidence/environment.json) uses Linux x86-64, Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, FreeGS 0.8.2 and OpenFUSIONToolkit 26.9. Use a clone with baseline commit `0cb88b21e8fce6106aa3b7d352a7a7dbfc0b22b7` available. Historical checks use separate detached worktrees. Original failures and unselected geometry cases remain available. A fresh rerun is by the same analysis workflow and shares source physics.

```sh
python -m pip install -r benchmarks/openstep-001/requirements.txt -r benchmarks/openstep-006/requirements.txt playwright==1.62.0
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for stage in lab 001 002 003 004 005 006; do python verification/replay_baseline.py "$stage" /tmp/tok-baseline || exit 1; done
python benchmarks/openstep-007/compare.py --fixed-profiles --output /tmp/tok-007
python benchmarks/openstep-008/replay.py /tmp/tok-008 --workers 2
python benchmarks/openstep-009/thermal.py /tmp/tok-009
python benchmarks/openstep-009/crosscheck.py /tmp/tok-009
python verification/signals.py /tmp/tok-exp003.py /tmp/signals.json
python verification/compare_trace.py --fixtures /tmp/paired-trace.json
python verification/assurance.py /tmp/dependencies.json
python verification/browser.py /tmp/tok-browser --chromium /path/to/chrome-headless-shell
```

For the extra 001 integration, use the detached baseline and run `python benchmarks/openstep-001/benchmark.py --n 129 --method newton --edge cell --tag=-vv-replay --maxits 40`. The [solver output](evidence/fresh-001.json), [007 replay](evidence/fresh-007.json) and [per-command logs](evidence/baseline) record the checks. Fresh 008 saves all signed fields in the user-selected output directory. The indexed 008 archive preserves its original raw evidence separately from the published source.

**First physical decision.** The +1 cm sharp model passes the assumed screen by only 7 K under nominal cooling and exceeds it under degraded cooling. A measured CAD corner, synchronized incident heat, front-face IR, backside temperature and coolant calorimetry on a representative coupon can test whether the difference survives. A matched-resolution Fiesta/FreeGS comparison tests the upstream coil sensitivity separately. For control, the next discriminating evidence is calibrated passive-wall and circuit data plus a separately observed position transient. These inputs are absent. Further numerical agreement alone cannot decide those three questions.
