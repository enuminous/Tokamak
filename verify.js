"use strict";
const assert = require("node:assert/strict");
const { flux, field, budget, edge } = require("./model.js");

const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} ≠ ${expected}`);
near(flux(0, 0), 0);
near(flux(0, -1), edge);
for (const z of [0, -1]) {
  for (const component of field(0, z)) near(component, 0);
}
for (const z of [-1.55, -1.1, -0.9, 0, 0.5]) {
  const x = Math.sqrt(Math.max(0, 2 * (edge - flux(0, z))));
  near(flux(x, z), edge);
  const [dx, dz] = field(x, z);
  near(x * dx + z * (1 + z) * dz, 0);
}
const targetFlux = flux(0, -1.55);
assert.ok(targetFlux < edge);
near(budget(0.25, 0.6).nextInventory, 0.9);
for (const leak of [0, 0.25, 1]) {
  for (const recycle of [0, 0.6, 1]) {
    const { retained, returned, removed, nextInventory } = budget(leak, recycle);
    near(retained + returned + removed, 1);
    near(nextInventory + removed, 1);
    near(removed, leak * (1 - recycle));
  }
}
console.log("PASS: critical points, separatrix, field tangency, target intersection, and particle accounting.");

const { hopf, radialBreaths } = require("./model.js");
const image = hopf(1, 2, 3, 4);
const rotated = hopf(-2, 1, -4, 3);
for (let i = 0; i < image.length; i++) near(image[i], rotated[i]);
near(Math.hypot(...image), 30);
near(Math.hypot(...hopf(0, 0, 0, 0)), 0);
for (const kick of [0, 0.35, 1]) {
  const run = radialBreaths(0.25, kick, 120);
  for (const cycle of run.cycles) {
    near(cycle.next - cycle.energy, kick - cycle.loss);
    near(run.position(cycle.energy, 0), 0);
    near(run.position(cycle.energy, run.duration), 0);
  }
  near(run.cycles.at(-1).next, run.equilibrium);
}
console.log("PASS: Hopf phase invariance and norm, radial returns, drive–loss balance, and fixed point.");
