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
