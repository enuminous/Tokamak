# Tokamak system specification

**Mission and design basis.** Study whether the public, historical SPP-001 EB-CC flat-top equilibrium can support a defensible chain from magnetic geometry to exhaust, heat management, fuel balance and net electricity. Scope includes the browser teaching models and the separate DIII-D solver benchmark. The public UKAEA conceptual workflow describes a 100 MWe net and tritium-self-sufficiency mission; using either as acceptance criteria here would require an adopted duty cycle, uncertainty allocation and independently measured inputs. The release represents a 2023 design milestone. It cannot establish the as-built or present STEP design. [OpenSTEP](https://github.com/ukaea/OpenSTEP/tree/6f66ae09c60b361d600b178416ef3f22b8d0aa6a) · [UKAEA conceptual design workflow](https://scientific-publications.ukaea.uk/papers/conceptual-design-workflow-for-the-step-prototype-powerplant/).

The [41-component register](COMPONENTS.md) sets functional requirements for engineering and software. Target acceptance requires model validation, design qualification and operating evidence appropriate to each claim. The only available actual-device input to the native vertical study is an archived EFIT reconstruction and reference model. A computational trace of that reconstructed shot is still a model output.

## Operating modes and required transitions

| Mode | Required evidence before transition | Evidence collected or required on exit |
|---|---|---|
| Offline configuration and maintenance | Asset/configuration identifiers, assembled geometry, service state and calibrations under review | Reconciled as-maintained baseline and outstanding isolation state |
| Pre-operation and commissioning | Component acceptance, cooling, cryogenics, power, vacuum and independent protection readiness | Instrumented low-energy commissioning against frozen reference; denied-start tests |
| Startup and ramp | Valid startup scenario, sensing, actuation and permitted transition envelope | Observed trajectories and margins through startup and ramp; abnormal termination replay |
| Flat top | Profile, boundary, current, wall and load definitions at matched times | Time-aligned records for confinement, control, exhaust, coolant, fuel and electrically imported/exported energy |
| Ramp-down, shutdown and cooldown | Observable state and remaining stored energy/inventory, including loss-of-utility cases | Evidence of safe removal of stored heat and energy, accounting closure and recovery |
| Fault, unavailable channel and restart | Independent state assessment and a defined protection and restart basis | Measured detection and response time, residual loads, cause disposition and authorized restart |
| Availability and retirement | Duty history, maintenance assumptions, activation and waste records | Annual net export, outage causes, access and end-of-life inventory within adopted criteria |

The scenario results in this repository primarily cover a model flat top, short perturbations and an illustrative cooling transient. The remaining transitions are requirements with open evidence.

## Interface control

| Handoff | Data contract | Check and treatment of failure |
|---|---|---|
| Source → equilibrium | Case, time slice, grid/time units, handedness, COCOS, flux sign and Wb or Wb/rad, A vs A-turns and profiles | Verify netCDF/MAT identities, shape and axis bounds before solving. An outline in mm is converted once to m. Withhold derived fields if the convention cannot be reconciled. |
| Equilibrium → wall/exhaust | Ordered R,Z in m, flux interpolation, field and surface normals, incidence, launch window and segment identifiers | Require converged field, same mesh/coil tag, invertible coordinate map and explicit wall-normal convention. Retain grazing/endpoint and unresolved branches. |
| Exhaust → thermal/structure | Spatial heat-flux density in W/m² on registered geometry, incident duration in s, local vs integrated power, material and boundary data | Keep representative 1 mm launch sample, optimized local maximum and integrated heat separate. Convert MW/m² once. CAD, contact resistance, true heat history and material limits remain open. |
| Plasma/wall → circuits and controls | Magnetic axis in m, growth in s⁻¹, wall decay in s, signed transfer function, L/R/M topology and coil V/A, sample time/delay in s | Pair the correct constraint operator with its trajectory. Require consistent polarity, voltage/current authority, latency and calibrated bandwidth before grading control. |
| Transport → burn and fuel inventory | Species densities and temperatures with units, volume and time bases, production/deposition rates, burn/extraction/processing delay | Reconcile volume integrals and species mass balance. Unknown storage, retention and reserve remain explicit. Never infer breeding from a swept TBR. |
| Plant auxiliaries → grid | Thermal vs electrical MW, online vs standby consumption, energy integration window and scheduled vs forced unavailability | Distinguish gross power, net online power and annual net energy. Meter heating, cooling, cryogenics, fuel processing and other loads without double counting. |
| Sensors → paired evidence | Device, configuration, quantity, signed SI unit, sensor/clock/calibration identity, coverage, uncertainty, digest-bound paired forecasts and observations | Preserve missing, saturated and stale samples. Predeclare uncertainty/error and alignment limits; no imputation or favorable time shifting in the comparison. |
| Computation → publication and operator | Pinned code/data, toolchain, status, scope, exclusions and provenance | Numerical PASS attaches to the exact test. A missing hardware record stays UNRESOLVED. Fictional/schematic propulsion is outside the plant acceptance graph. |

## Coupled failures and verification allocation

| Initiating event | Propagation and diverse observations | Test and decision |
|---|---|---|
| p9 displacement plus weak cooling | Flux geometry → contact normal and footprint → surface temperature → possible armor/bond damage. Check survey, IR, backside thermometry and coolant calorimetry. | 009 runs 32 cases; 7 exceed the assumed screen with degraded cooling. Measured CAD, incident profiles, material and coolant data gate any operational margin. |
| Passive wall or circuit error plus delayed feedback | Drift appears in magnetics, controller requests current, supply rails, displacement grows. Common sensors can make model and control agree on the same wrong position. | 006 native prescribed-current delay controls and 007/008 mode tests; require blind synchronized position and current data plus representative coil-supply HIL for closure. |
| Diagnostic corruption plus persistent/alternating error | Timing or polarity errors corrupt both control inputs and the recorded evidence. A signed monitor can cancel a real alternating fault. | Side-by-side clean and injected streams, separate signed/absolute monitors; a lost or corrupt channel invalidates its dependent claim. No actuation path in this test. |
| Heating loss or radiation increase during a cooling fault | Core power balance changes and the spatial footprint can move; target peak and net export may diverge | Couple time-dependent transport and SOL predictions on the same clock, plus IR, radiation, flow and electric meters. The present thermal transient holds the footprint fixed. |
| Loss of external electric supply | Heating, pumping, cooling, diagnostics and protection may share a common service; delayed heat and stored energy persist | Site-specific failure analysis, backup-bus and final-heat-sink HIL, independently powered records. A plant decision requires evidence for all affected branches. |
| Fuel processing outage during maintenance | Inventory remains in processing, breeding is delayed and remote access imposes downtime | Timed fuel balance and assay, full-scale remote intervention rehearsal and metered standby loads; evaluate integrated net export and conservative inventory, including recovery. |

High-consequence common causes require independent instruments, power sources and reviewers where allocated. Their effectiveness is an open obligation. No failure probability, severity score or regulatory approval has been assigned in the absence of a site-specific hazards basis.

## Measured-trace entry point

`compare_trace.py contract.json` reads sibling `forecast.csv` and `observation.csv`; both use headers `time_s,value_K` (surface temperature) or `time_s,value_m` (axis height). Supply the following identifiers from the actual experiment: quantity (`surface_temperature` or `axis_height`), unit, evidence_class (`measurement` or `fixture`), device, configuration, channel, clock, calibration, criterion_source, expected_samples, absolute_error_limit, clock_tolerance_s, forecast_sha256 and observation_sha256. The program rejects incomplete coverage, unequal units, nonfinite values, mismatched clocks or file digests. It performs no resampling. Time zero, coordinate registration, uncertainty allocation, independence and proof of a premeasurement forecast must be reviewed outside this arithmetic comparator. A supplied source label or hash cannot establish that an instrument or reviewer exists.

**Closure at the next level of detail.** Replace each functional subsystem with its approved configuration/parts list, measured and modeled interfaces, operating limits and hazard allocation. Link each child requirement to a witnessed acceptance method, raw record, uncertainty and authorizing review. Failure of a required child blocks the parent; unassessed applicability defaults to UNRESOLVED. The recursive graph represents evidence prerequisites. Electrical/thermal causal feedback requires a dynamic simulation and a separate stability argument.

[ITER supporting systems, as a coverage cross-check](https://www.iter.org/machine/supporting-systems) · [UKAEA on STEP maintenance and magnet joints](https://doi.org/10.1098/rsta.2023.0415) · [OpenSTEP source and licenses](https://github.com/ukaea/OpenSTEP/tree/6f66ae09c60b361d600b178416ef3f22b8d0aa6a).
