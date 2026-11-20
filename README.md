# Tri-Sphere / Tokamak Lab

A flat, dependency-free repository for exploring the tokamak analogue of Beth's Universal 13-Layer Tri-Sphere Blueprint. The strongest correspondence is the separatrix: a magnetic surface that divides the confined region from field lines that can reach the divertor.

## Start here

1. Extract the ZIP into an empty folder. All files are at the archive root.
2. Open `index.html` in a modern browser. The lab runs offline with no build step.
3. Set the outward crossing and recycling fractions. The readout shows how the assumed fractions change the particle inventory.
4. Run `node verify.js` with Node.js 18 or newer to replay the numerical checks.

`model.js` supplies the same math to the browser and verification script. `lab.js` wires the controls. `style.css` supplies the layout. [PHYSICS.md](PHYSICS.md) describes the equations and every layer correspondence.

## Example

With 25% outward crossing and 60% recycling of the crossing fraction, 75% stays confined, 15% returns, and 10% is removed. The next inventory is 90% of the starting inventory. Changing these fractions leaves the static flux contours fixed.

The model illustrates topology and accounting. Predicting plasma behavior would require an equilibrium solution, transport equations, material interactions, and comparison with measurements.

## Reactor and TriSphere controls

The 3D + time schematic has azimuth, elevation, cutaway, tracer speed, field-line pitch, play/pause, and labels. The 2D flux section resolves the X-point independently. The particle and energy sliders reproduce the paper's 90% and 77.5% default inventories. The radial lab implements a center-kick example inspired by A. Beth Jones’s Equation 10, and a layer selector evaluates one point on each Hopf shell. See [model boundaries and live-source comparison](PHYSICS.md#joness-equations-and-the-model).

## Recirculating muon engine

Open [engine.html](engine.html) for the TriSphere-inspired engine simulator. It accounts for catalyst survival, sticking, recirculation, energy recovery, bootstrap power and ideal jet thrust. The proposed quark chamber appears as a speculative stage and carries zero power credit. See [ENGINE.md](ENGINE.md) for the model and its assumptions.
