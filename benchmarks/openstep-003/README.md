# OPENSTEP-003 — fixed-pressure/current coil scan

Matthew Chenoweth Wright / Monolithic LLC · 21 November 2026

**Coarse baseline:** Recovered under the original physical operator and acceptance threshold.
**Design decision:** No candidate met all frozen screening criteria on the first two grids. The optional 513 × 1025 refinement was not triggered.

Planned grid/geometry cases: 14; accepted: 8; unresolved: 6. Unresolved numerical attempts do not prove that an equilibrium does not exist.

Numerical verification: **120 PASS, 0 FAIL**. These checks concern implementation and numerical acceptance, not reactor qualification.

## What changed

The previous +10 cm fixed-derivative experiment changed pressure and plasma current as well as coil geometry. This scan holds the entire p(s) function and total Ip at the published OPENSTEP-001 baseline 257-grid operating point while moving the two p9 packs by 1, 2.5 and 5 cm in either direction. Coil currents and F at the boundary stay fixed. Positive movement is toward the midplane.

The initial protocol precedes these solves. Additional restart routes are disclosed in [AMENDMENTS.md](AMENDMENTS.md). This is exploratory work, not independent preregistration or experimental validation.

## Complete accepted-field comparison

| Grid | p9 shift (cm) | Axis R (m) | q95 | Required H | Heat (MW/m²) | Wall clearance (cm) | Heat samples >10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 129 × 257 | -5 | 4.42891 | 7.468 | 1.4804 | 10.67 | 9.78 | 36/120 |
| 129 × 257 | -1 | 4.40541 | 7.553 | 1.4758 | 10.38 | 9.30 | 37/120 |
| 129 × 257 | +0 | 4.38382 | 7.586 | 1.4687 | 10.56 | 9.10 | 39/120 |
| 129 × 257 | +1 | 4.38152 | 7.599 | 1.4674 | 10.50 | 8.97 | 47/120 |
| 257 × 513 | -1 | 4.40222 | 7.572 | 1.4695 | 10.47 | 9.19 | 39/120 |
| 257 × 513 | +0 | 4.38965 | 7.596 | 1.4649 | 10.45 | 9.00 | 45/120 |
| 257 × 513 | +1 | 4.38305 | 7.617 | 1.4626 | 10.47 | 8.84 | 47/120 |
| 257 × 513 | +5 | 4.34462 | 7.714 | 1.4504 | 56.04 | 8.09 | 74/120 |

Representative heat uses a 1 mm upstream offset, lambda_q = 6 mm, SOL radiation fraction 0.5, and one-target power share 0.25. The 120 heat samples per geometry cover the full 002 assumption grid. Counts are not probabilities. The sampled maximum need not equal the true footprint maximum. Wall clearance uses the s = 0.999 surface. H is a required radiation-subtracted transport multiplier under prescribed sources and a mapped thermal-energy target; it is not predicted turbulent confinement.

## Numerical decision rule

An effect is resolved in the exploratory grid comparison only when its magnitude exceeds the sum of the candidate and baseline changes between those grids. This observed difference is not a rigorous error bound or statistical confidence interval. A promising candidate must have resolved lower representative heat, lower sampled maximum heat, valid traces, and no resolved deterioration in clearance or H.

| Shift (cm) | Heat reduction resolved | Sampled maximum lower | Clearance criterion | H criterion | Promising |
|---:|---|---|---|---|---|
| -1 | NO | NO | YES | YES | NO |
| +1 | NO | NO | YES | YES | NO |
| +5 | NO | NO | NO | NO | NO |

## Numerical recovery and failures

The recovery retains the fourth-order FreeGS operator, cut-cell current source and 1e−5 full-domain residual threshold. Newton step size, line search and accepted warm-start paths are numerical choices. Intermediate pressure/current homotopy states have different operating points and are excluded from the geometry comparison. A solver failure is not proof that no physical equilibrium exists.

| Attempt | Grid | Defect | Recorded error |
|---|---:|---:|---|
| shift--025mm-129 | 129 | not available | RuntimeError: Critical-point refinement failed |
| inward-025mm-129 | 129 | 0.014524464339774414 | Acceptance threshold not met |
| recovery-129-fd7 | 129 | not available | IndexError: list index out of range |
| shift--025mm-257 | 257 | 0.00040970101968326657 | Acceptance threshold not met |
| recovery-129-no-linesearch | 129 | 0.009343500904232508 | Acceptance threshold not met |
| shift--050mm-257 | 257 | 0.00013811146455615923 | Acceptance threshold not met |
| inward-025mm-257 | 257 | 0.004458412637616367 | Acceptance threshold not met |
| shift-+025mm-129 | 129 | not available | RuntimeError: Critical-point refinement failed |
| recovery-geometry-075mm | 129 | not available | RuntimeError: Critical-point refinement failed |
| inward-050mm-129 | 129 | 0.004105211728956118 | Acceptance threshold not met |

## Reproduce

Use Python 3.12 and the dependency pins inherited from OPENSTEP-001. From the repository root:
```sh
python -m pip install -r benchmarks/openstep-003/requirements.txt
# Replay the attempts and warm-start order recorded in COMMANDS.md.
python benchmarks/openstep-003/screen_sweep.py --n 129
python benchmarks/openstep-003/screen_sweep.py --n 257
# If a 513-grid pair is recorded, screen it with --n 513 as well.
python benchmarks/openstep-003/assess.py
python benchmarks/openstep-003/verify.py
python benchmarks/openstep-003/plot.py
python benchmarks/openstep-003/write_report.py
```

Each solve JSON records its exact warm-start path/hash, code hash, finite-difference parameter, line search, target values, iteration history and acceptance residual. NPZ files contain the complete fields. The screen calculations reuse the immutable 002 implementations; 001/002 inputs enforce their pinned source hashes. See artifact-manifest.json for content hashes.

## Boundaries of the result

The vertical-force slope is a rigid-current, fixed-coil, no-wall diagnostic; its sign is not a wall-coupled MHD growth rate. The heat model traces imposed upstream power to the wall and does not solve detachment or neutrals. Current and p(s) constraints do not keep shape, q, pressure integral or the mapped thermal-energy target constant.

- NOT RUN: Full 3-D MHD and wall/feedback stability
- NOT RUN: Predictive turbulent transport and burn
- NOT RUN: SOL detachment and neutrals
- NOT RUN: Structural, superconducting, cooling and neutron qualification

## Sources and snapshot preservation

- UKAEA OpenSTEP, Brown et al., [DOI 10.14468/07jt-s540](https://doi.org/10.14468/07jt-s540), pinned commit `6f66ae09c60b361d600b178416ef3f22b8d0aa6a`, CC BY 4.0.
- [OPENSTEP-001](../openstep-001/README.md) and [OPENSTEP-002](../openstep-002/README.md) contain the source mapping, model equations, units and primary physics references.
- Historical 001/002 package files remain unchanged. Shared root navigation is updated; historical manifests describe their original commits, including root files as they stood then.
- Previous published snapshot: `37ae3ea0d58830575eb11e25b1220453ad614c78`. FreeGS 0.8.2 and the inherited boundary cache are LGPL-3.0-or-later; licenses are retained in 002. No UKAEA endorsement is implied.
