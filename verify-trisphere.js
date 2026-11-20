"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const crypto = require("node:crypto");
const T = require("./trisphere-core.js");
const checks = [];
function test(name, fn) { fn(); checks.push({ name, status: "PASS" }); console.log("PASS:", name); }
const near = (a, b, eps = 1e-10) => assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}, tolerance ${eps}`);
test("source snapshot hash matches the recorded model provenance", () => {
  const data = fs.readFileSync(require.resolve("./TRISPHERE-SOURCE-2026-11-20.md"));
  const hash = crypto.createHash("sha256").update(data).digest("hex");
  assert.equal(hash, T.SOURCE_SHA256);
  assert.equal(hash, require("./trisphere-source.json").snapshot_sha256);
});
test("compression preserves the mirror, separate endpoints, and Filter", () => {
  for (let n = 0; n <= 12; n++) near(T.mapLayer(12 - n), 4 - T.mapLayer(n));
  near(T.mapLayer(0), 0); near(T.mapLayer(6), 2); near(T.mapLayer(12), 4);
});
test("potential gradient agrees with differentiation; plateau locations are explicit", () => {
  for (const id of Object.keys(T.configs)) {
    for (let i = 0; i <= 100; i++) {
      const x = i / 100, h = 1e-6;
      near(T.potential(x, id, 0.16).gradient,
        (T.potential(x + h, id, 0.16).value - T.potential(x - h, id, 0.16).value) / (2 * h), 5e-6);
    }
    for (const x of T.configs[id].shelves) near(T.potential(x, id, 0.16).gradient, 0);
  }
});
test("force-free damped motion agrees with the analytic solution", () => {
  const p = { height: 0, k: 0, gamma: 0.3, x0: 0.4, v0: 0.05, duration: 2 };
  const r = T.radial("thirteen", p), v = p.v0 * Math.exp(-p.gamma * p.duration);
  near(r.final.v, v, 1e-11);
  near(r.final.x, p.x0 + p.v0 * (1 - Math.exp(-p.gamma * p.duration)) / p.gamma, 1e-11);
  near(r.final.dampingHeat, (p.v0 ** 2 - v ** 2) / 2, 1e-11);
});
test("wall impact retains kinetic energy as heat or exports its declared fraction", () => {
  for (const boundary of ["contain", "exhaust"]) {
    const r = T.radial("thirteen", { height: 0, k: 0, gamma: 0, x0: 0.9, v0: 1, duration: 1, boundary });
    near(r.final.x, 1); near(r.final.v, 0); near(r.final.contactHeat + r.final.exported, 0.5);
    near(r.final.exported, boundary === "exhaust" ? 0.3 : 0);
    assert.ok(r.maxResidual < 1e-10);
  }
});
test("zero drive dissipates initial radial energy without injecting work", () => {
  const r = T.radial("five", { k: 0, gamma: 0.3, duration: 32 });
  near(r.final.work, 0); assert.ok(r.final.energy < 1e-8);
  for (let i = 1; i < r.trace.length; i++) assert.ok(r.trace[i].energy <= r.trace[i - 1].energy + 1e-8);
});
test("particle and energy balances and nonnegativity across routing extremes", () => {
  for (const id of Object.keys(T.configs)) for (const boundary of ["contain", "exhaust"]) {
    for (const product of [0, 0.45, 1]) for (const gamma of [0, 0.3, 2]) for (const release of [0, 0.6, 2]) {
      const r = T.transport(id, { boundary, product, gamma, release, duration: 32, weights: [0, 0, 0, 1] });
      assert.ok(r.maxMassResidual < 1e-10 && r.maxEnergyResidual < 1e-10);
      for (const row of r.trace) {
        for (const key of ["mass", "energy", "heat", "exportedMass", "exportedEnergy", "firstReturned"]) assert.ok(row[key] >= -1e-12);
        assert.ok(row.occupancy.every(x => x >= 0));
        assert.ok(row.firstReturned <= 1 + 1e-12);
      }
      if (boundary === "contain") { near(r.final.exportedMass, 0); near(r.final.exportedEnergy, 0); }
      if (release === 0) { near(r.final.returned, 0); near(r.final.work, 0); }
    }
  }
});
test("first return is separate from repeated circulation; full exhaust blocks particle return", () => {
  const r = T.transport("thirteen", { duration: 96 });
  assert.ok(r.final.returned > 1 && r.final.firstReturned <= 1 + 1e-12);
  assert.ok(r.firstTime >= 6); // 24 transit ticks plus at least two shelf-release ticks.
  const e = T.transport("thirteen", { boundary: "exhaust", particleExhaust: 1, duration: 96 });
  near(e.final.firstReturned, 0); near(e.final.work, 0); assert.equal(e.firstTime, null);
});
test("zero-loss and zero-work inventory retains all initial energy", () => {
  const r = T.transport("five", { gamma: 0, k: 0, duration: 96 });
  near(r.final.energy, 1); near(r.final.heat, 0); near(r.final.work, 0);
});
test("invalid, nonfinite, and unknown inputs are rejected", () => {
  for (const p of [{ k: NaN }, { gamma: -1 }, { dt: 0 }, { boundary: "magic" }, { weights: [0, 0, 0, 0] }, { standing: "Source" }]) {
    assert.throws(() => T.settings(p));
  }
  assert.throws(() => T.radial("unknown"));
});
const base = T.compare();
test("default numerical checks pass while the declared model comparison fails", () => {
  assert.equal(base.comparison.numericalChecks, "PASS");
  assert.equal(base.comparison.agreement, "FAIL");
  assert.equal(base.comparison.physicalValidation, "UNRESOLVED");
});
test("halving the timestep preserves the comparison and reduces energy error", () => {
  const refined = T.compare({ dt: 0.005 });
  assert.equal(refined.comparison.agreement, base.comparison.agreement);
  near(refined.comparison.radialRMSE, base.comparison.radialRMSE, 1e-4);
  for (const id of Object.keys(T.configs)) assert.ok(refined[id].radial.maxResidual < base[id].radial.maxResidual);
});
test("short runs cannot claim agreement or periodicity", () => {
  const r = T.compare({ duration: 2 });
  assert.equal(r.comparison.agreement, "UNRESOLVED");
  assert.equal(r.thirteen.radial.state, "UNRESOLVED_SHORT_RUN");
});
test("repeated runs are deterministic", () => assert.deepEqual(T.compare({ duration: 4 }), T.compare({ duration: 4 })));
console.log(JSON.stringify({ schema: "trisphere-verification/1", version: T.VERSION, checks,
  count: checks.length, status: "PASS", scope: "implementation and prescribed numerical closures; no physical confirmation" }));
