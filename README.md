# Tri-Sphere / Tokamak Lab

A collection of browser labs and reproducible equilibrium calculations exploring the tokamak analogue of Beth's Universal 13-Layer Tri-Sphere Blueprint. The strongest correspondence is the separatrix: a magnetic surface that divides the confined region from field lines that can reach the divertor.

## Start here

**Equilibrium milestone, November 20:** [open the STEP benchmark](equilibrium.html) or read the [complete report and replay instructions](benchmarks/openstep-001/README.md). The published UKAEA equilibrium is reproduced within **0.154% core-flux RMSE** using explicit coils, currents, plasma profiles and SI units. A mirrored 10 cm coil movement is re-solved and compared across grids. The axis and current changes are resolved against observed refinement differences; the X-point shift remains unresolved. This is a static equilibrium benchmark, with confinement, stability and engineering still untested. Python dependencies apply to this benchmark; the earlier browser labs below remain dependency-free.

**New, November 20:** open [TriSphere prototype 02](trisphere-prototype.html) for the radial equation, a thirteen-versus-five comparison, separate particle and energy ledgers, a parameter scan, and complete JSON export. Read the [simulation contract](TRISPHERE-CONTRACT.md), [source snapshot](TRISPHERE-SOURCE-2026-11-20.md), and [recorded results](TRISPHERE-RESULTS-2026-11-20.md). Run `node verify-trisphere.js` for the new checks and `node run-trisphere.js` to reproduce the result bundle. The earlier labs remain available below.

1. Extract the ZIP into an empty folder, preserving its directory structure.
2. Open `index.html` in a modern browser. The lab runs offline with no build step.
3. Set the outward crossing and recycling fractions. The readout shows how the assumed fractions change the particle inventory.
4. Run `node verify.js` with Node.js 18 or newer to replay the numerical checks.

`model.js` supplies the same math to the browser and verification script. `lab.js` wires the controls. `style.css` supplies the layout. [PHYSICS.md](PHYSICS.md) describes the equations and every layer correspondence.

## Example

With 25% outward crossing and 60% recycling of the crossing fraction, 75% stays confined, 15% returns, and 10% is removed. The next inventory is 90% of the starting inventory. Changing these fractions leaves the static flux contours fixed.

These browser models illustrate topology and accounting. The separate STEP benchmark supplies a static equilibrium calculation. Predicting transport or reactor performance still requires additional plasma and material models and comparison with measurements.

## Reactor and TriSphere controls

The 3D + time schematic has azimuth, elevation, cutaway, tracer speed, field-line pitch, play/pause, and labels. The 2D flux section resolves the X-point independently. The particle and energy sliders reproduce the paper's 90% and 77.5% default inventories. The radial lab implements a center-kick example inspired by A. Beth Jones’s Equation 10, and a layer selector evaluates one point on each Hopf shell. See [model boundaries and live-source comparison](PHYSICS.md#joness-equations-and-the-model).

## Recirculating muon engine

Open [engine.html](engine.html) for the TriSphere-inspired engine simulator. It accounts for catalyst survival, sticking, recirculation, energy recovery, bootstrap power and ideal jet thrust. The proposed quark chamber appears as a speculative stage and carries zero power credit. See [ENGINE.md](ENGINE.md) for the model and its assumptions.

The [TriSphere–Tokamak comparison](https://github.com/enuminous/papers/blob/main/TriSphere-Tokamak-Model-Comparison-2026-11-19.md) documents which parts run today and specifies the proposed exhaust-versus-containment experiment.

Open the [TriSphere configuration lab](trisphere.html) to compare A. Beth Jones’s primary thirteen-layer model and her alternate Five-Structure under the same routing and boundary settings.

