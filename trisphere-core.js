/* TriSphere prototype 2. Dimensionless, prescribed closures; not a physical validation. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.TriSphere = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const VERSION = "2.0.0";
  const SOURCE_SHA256 = "312976f809ea1c3215872e6b18542321d99af84982e80cb01c3529dd4f7e8320";
  const configs = {
    thirteen: { title: "Thirteen-layer atlas", length: 12, filter: 6, shelves: [4 / 12, 8 / 12, 11.5 / 12] },
    five: { title: "Five-position candidate", length: 4, filter: 2, shelves: [0.25, 0.5, 0.75] }
  };
  const defaults = Object.freeze({ k: 0.7, gamma: 0.3, period: 8, height: 0.16,
    amplitude: 1.2, dt: 0.01, duration: 96, x0: 0.15, v0: 0,
    boundary: "contain", product: 0.45, modulation: 0, weights: [1, 1, 1, 1],
    release: 0.6, mode: "maintain", pump: 0.15, particleExhaust: 0.25, energyExhaust: 0.6 });
  const limits = { k: [0, 1], gamma: [0, 2], period: [2, 20], height: [0, 1], amplitude: [0, 3],
    dt: [0.001, 0.02], duration: [0, 240], x0: [0, 1], v0: [-2, 2], product: [0, 1],
    modulation: [0, 1], release: [0, 2], pump: [0, 1], particleExhaust: [0, 1], energyExhaust: [0, 1] };
  const thresholds = Object.freeze({ mass: 1e-10, transportEnergy: 1e-10, radialEnergy: 1e-3,
    radialRMSE: 0.05, shelfL1: 0.1, firstReturn: 0.05, periodicDistance: 0.01, activeAmplitude: 0.02 });
  const sum = values => values.reduce((a, b) => a + b, 0);
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  function settings(input = {}) {
    for (const key of Object.keys(input)) if (!(key in defaults)) throw new Error("Unknown setting: " + key);
    const p = { ...defaults, ...input, weights: [...(input.weights || defaults.weights)] };
    for (const [key, [lo, hi]] of Object.entries(limits)) {
      if (!Number.isFinite(p[key]) || p[key] < lo || p[key] > hi) throw new Error(key + " is outside [" + lo + ", " + hi + "]");
    }
    if (!["contain", "exhaust"].includes(p.boundary)) throw new Error("Unknown boundary");
    if (!["repair", "maintain", "decay"].includes(p.mode)) throw new Error("Unknown shelf mode");
    if (p.weights.length !== 4 || p.weights.some(x => !Number.isFinite(x) || x < 0) || sum(p.weights) <= 0) {
      throw new Error("Four nonnegative Compost weights with a positive sum are required");
    }
    // Keep a regular sample grid, including exact final time. Also used by the CLI.
    if (Math.abs(p.duration / p.dt - Math.round(p.duration / p.dt)) > 1e-7) throw new Error("duration must be a multiple of dt");
    return p;
  }
  function config(id) {
    if (!Object.hasOwn(configs, id)) throw new Error("Unknown configuration: " + id);
    return configs[id];
  }
  function mapLayer(n) {
    if (!Number.isInteger(n) || n < 0 || n > 12) throw new Error("Layer must be an integer from 0 to 12");
    return n === 0 ? 0 : n === 12 ? 4 : n <= 4 ? 1 : n <= 7 ? 2 : 3;
  }
  // Monotone C1 potential: three cubic ramps separated by flat shelf bands.
  // Its shape and height are implementation assumptions, not seam-derived physics.
  function potential(x, id, height) {
    const shelves = config(id).shelves, width = 0.035, weights = [0.4, 0.35, 0.25];
    let value = 0, gradient = 0, start = 0;
    for (let j = 0; j < 3; j++) {
      const end = shelves[j] - width, span = end - start, z = clamp((x - start) / span, 0, 1);
      value += height * weights[j] * z * z * (3 - 2 * z);
      if (z > 0 && z < 1) gradient += height * weights[j] * 6 * z * (1 - z) / span;
      start = shelves[j] + width;
    }
    return { value, gradient };
  }
  const force = (t, p) => p.k * p.amplitude * Math.sin(2 * Math.PI * t / p.period);
  function derivative(y, t, id, p) {
    const [x, v] = y, d = force(t, p), a = -potential(x, id, p.height).gradient - p.gamma * v + d;
    // Unilateral stationary contact; the actuator does no work while contact holds.
    if ((x <= 0 && Math.abs(v) < 1e-13 && a <= 0) || (x >= 1 && Math.abs(v) < 1e-13 && a >= 0)) return [0, 0, 0, 0];
    return [v, a, d * v, p.gamma * v * v];
  }
  function rk4(y, t, h, id, p) {
    const add = (a, b, f) => a.map((v, i) => v + f * b[i]);
    const a = derivative(y, t, id, p), b = derivative(add(y, a, h / 2), t + h / 2, id, p);
    const c = derivative(add(y, b, h / 2), t + h / 2, id, p), d = derivative(add(y, c, h), t + h, id, p);
    return y.map((v, i) => v + h * (a[i] + 2 * b[i] + 2 * c[i] + d[i]) / 6);
  }
  function radial(id, input = {}) {
    config(id);
    const p = settings(input), steps = Math.round(p.duration / p.dt);
    let y = [p.x0, p.v0, 0, 0], contactHeat = 0, exported = 0, contacts = 0;
    const initial = 0.5 * y[1] ** 2 + potential(y[0], id, p.height).value;
    const trace = [], dwell = [0, 0, 0];
    let maxResidual = 0;
    function record(t) {
      const energy = 0.5 * y[1] ** 2 + potential(y[0], id, p.height).value;
      const residual = energy + y[3] + contactHeat + exported - initial - y[2];
      maxResidual = Math.max(maxResidual, Math.abs(residual));
      trace.push({ t, x: y[0], v: y[1], energy, work: y[2], dampingHeat: y[3], contactHeat, exported, residual });
    }
    record(0);
    for (let i = 0; i < steps; i++) {
      let left = p.dt, local = i * p.dt, count = 0;
      while (left > 1e-12) {
        if (++count > 8) throw new Error("Unresolved contact integration; reduce dt");
        const trial = rk4(y, local, left, id, p);
        if (trial[0] >= 0 && trial[0] <= 1) { y = trial; break; }
        const wall = trial[0] < 0 ? 0 : 1;
        // Isolate impact time instead of clipping an overshoot and losing its energy.
        let lo = 0, hi = left;
        for (let b = 0; b < 34; b++) {
          const mid = (lo + hi) / 2, x = rk4(y, local, mid, id, p)[0];
          if (wall === 0 ? x > 0 : x < 1) lo = mid; else hi = mid;
        }
        y = rk4(y, local, hi, id, p);
        const loss = 0.5 * y[1] ** 2;
        const out = wall === 1 && p.boundary === "exhaust" ? p.energyExhaust * loss : 0;
        contactHeat += loss - out; exported += out; contacts++;
        y[0] = wall; y[1] = 0;
        local += hi; left -= hi;
      }
      if (!y.every(Number.isFinite)) throw new Error("Nonfinite radial state");
      config(id).shelves.forEach((s, j) => { if (Math.abs(y[0] - s) <= 0.035) dwell[j] += p.dt; });
      record((i + 1) * p.dt);
    }
    const tailStart = Math.max(0, p.duration - 2 * p.period);
    const tail = trace.filter(row => row.t >= tailStart);
    const xs = tail.map(row => row.x), amplitude = Math.max(...xs) - Math.min(...xs);
    const speedRMS = Math.sqrt(sum(tail.map(row => row.v ** 2)) / tail.length);
    let recurrence = null;
    if (p.duration >= 4 * p.period) {
      let err = 0, n = 0;
      for (const row of trace) if (row.t >= p.duration - p.period) {
        const prior = sample(trace, row.t - p.period, p.dt);
        err += (row.x - prior.x) ** 2 + (row.v - prior.v) ** 2; n++;
      }
      recurrence = Math.sqrt(err / n);
    }
    const state = recurrence === null ? "UNRESOLVED_SHORT_RUN" : amplitude < 0.01 && speedRMS < 0.01 ? "SETTLED" :
      amplitude >= thresholds.activeAmplitude && recurrence < thresholds.periodicDistance ? "PERIODIC_CANDIDATE" : "TRANSIENT_OR_OTHER";
    return { trace, initial, final: trace.at(-1), maxResidual, contacts, dwell, amplitude, speedRMS, recurrence, state };
  }
  function sample(trace, t, dt) {
    const at = clamp(t / dt, 0, trace.length - 1), i = Math.floor(at), f = at - i;
    const a = trace[i], b = trace[Math.min(i + 1, trace.length - 1)];
    return { x: a.x + f * (b.x - a.x), v: a.v + f * (b.v - a.v) };
  }
  // A separate inventory circuit. Transit delays retain original route memory in
  // both configurations; compression pools release rates, not that hidden memory.
  function transport(id, input = {}) {
    config(id);
    const p = settings(input), tick = 0.25, steps = Math.floor(p.duration / tick + 1e-9);
    const group = n => id === "five" ? mapLayer(n) : n;
    const shelfLayers = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11];
    const factor = { repair: 1.5, maintain: 1, decay: 0.5 }[p.mode];
    const layerRate = n => p.release * factor * (0.6 + 0.08 * n);
    const rate = n => {
      const members = id === "five" ? shelfLayers.filter(m => group(m) === group(n)) : [n];
      return sum(members.map(layerRate)) / members.length;
    };
    // age is retained exactly until first return; later recirculation is cumulative.
    let packets = [{ stage: "filter", remaining: 6, target: 0, mass: 1, energy: 1, fresh: true }], shelves = [];
    let heat = 0, work = 0, exportedMass = 0, exportedEnergy = 0, returned = 0, returnedEnergy = 0;
    let firstReturned = 0, firstReturnedEnergy = 0, firstTime = null, firstMoment = 0, product = 0, compost = 0;
    let maxMassResidual = 0, maxEnergyResidual = 0;
    const trace = [], firstReturnTrace = [], decay = 1 - Math.exp(-p.gamma * tick);
    function summary(t) {
      const mass = sum(packets.map(o => o.mass)) + sum(shelves.map(o => o.mass));
      const energy = sum(packets.map(o => o.energy)) + sum(shelves.map(o => o.energy));
      const occupancy = Array(config(id).length + 1).fill(0);
      for (const s of shelves) occupancy[group(s.target)] += s.mass;
      const massResidual = mass + exportedMass - 1, energyResidual = energy + heat + exportedEnergy - 1 - work;
      maxMassResidual = Math.max(maxMassResidual, Math.abs(massResidual));
      maxEnergyResidual = Math.max(maxEnergyResidual, Math.abs(energyResidual));
      const row = { t, mass, energy, heat, work, exportedMass, exportedEnergy, returned, returnedEnergy,
        firstReturned, firstReturnedEnergy, product, compost, occupancy, massResidual, energyResidual };
      trace.push(row); return row;
    }
    summary(0);
    const merge = list => {
      const map = new Map();
      for (const o of list) {
        const key = [o.stage, o.remaining, o.target, o.direction, o.fresh].join("/");
        if (map.has(key)) { const prior = map.get(key); prior.mass += o.mass; prior.energy += o.energy; }
        else map.set(key, { ...o });
      }
      return [...map.values()];
    };
    for (let step = 1; step <= steps; step++) {
      const t = step * tick, next = [], retained = [];
      const sigma = clamp(p.product + p.modulation * Math.sin(2 * Math.PI * t / p.period), 0, 1);
      for (const o of [...packets, ...shelves]) { const lost = o.energy * decay; heat += lost; o.energy -= lost; }
      for (const s of shelves) {
        const f = 1 - Math.exp(-rate(s.target) * tick), released = { ...s, mass: s.mass * f, energy: s.energy * f };
        retained.push({ ...s, mass: s.mass * (1 - f), energy: s.energy * (1 - f) });
        next.push({ ...released, stage: s.direction === "out" ? "shell" : "center",
          remaining: s.direction === "out" ? 12 - s.target : s.target });
      }
      for (const o of packets) {
        o.remaining--;
        if (o.remaining > 0) { next.push(o); continue; }
        if (o.stage === "filter") {
          product += o.mass * sigma; compost += o.mass * (1 - sigma);
          const split = (target, fraction) => { if (fraction > 0) next.push({ ...o, target, stage: "shelf", direction: "out",
            remaining: target - 6, mass: o.mass * fraction, energy: o.energy * fraction }); };
          split(7, sigma);
          p.weights.forEach((w, j) => split(8 + j, (1 - sigma) * w / sum(p.weights)));
        } else if (o.stage === "shelf") retained.push(o);
        else if (o.stage === "shell") {
          const dm = p.boundary === "exhaust" ? o.mass * p.particleExhaust : 0;
          const de = p.boundary === "exhaust" ? o.energy * p.energyExhaust : 0;
          exportedMass += dm; exportedEnergy += de;
          next.push({ ...o, mass: o.mass - dm, energy: o.energy - de, stage: "shelf", direction: "in",
            target: 12 - o.target, remaining: o.target });
        } else if (o.stage === "center") {
          returned += o.mass; returnedEnergy += o.energy;
          if (o.fresh) {
            firstReturned += o.mass; firstReturnedEnergy += o.energy; firstMoment += t * o.mass;
            if (firstTime === null && o.mass > 0) firstTime = t;
            firstReturnTrace.push({ t, mass: o.mass, energy: o.energy });
          }
          const added = p.k * p.pump * o.mass; work += added;
          next.push({ ...o, stage: "filter", target: 0, direction: undefined, remaining: 6, energy: o.energy + added, fresh: false });
        }
      }
      packets = merge(next); shelves = merge(retained);
      summary(t);
    }
    return { trace, final: trace.at(-1), firstTime, conditionalMeanFirstReturn: firstReturned > 0 ? firstMoment / firstReturned : null,
      firstReturnTrace, maxMassResidual, maxEnergyResidual, elapsed: steps * tick, tick };
  }
  function compare(input = {}) {
    const p = settings(input), a = { radial: radial("thirteen", p), transport: transport("thirteen", p) };
    const b = { radial: radial("five", p), transport: transport("five", p) };
    const rmse = Math.sqrt(sum(a.radial.trace.map((v, i) => (v.x - b.radial.trace[i].x) ** 2)) / a.radial.trace.length);
    const mapped = Array(5).fill(0);
    a.transport.final.occupancy.forEach((v, i) => { mapped[mapLayer(i)] += v; });
    const shelfL1 = sum(mapped.map((v, i) => Math.abs(v - b.transport.final.occupancy[i])));
    const firstReturnDifference = Math.abs(a.transport.final.firstReturned - b.transport.final.firstReturned);
    const numerics = [a, b].every(r => r.radial.maxResidual < thresholds.radialEnergy &&
      r.transport.maxMassResidual < thresholds.mass && r.transport.maxEnergyResidual < thresholds.transportEnergy);
    const enough = p.duration >= 4 * p.period && a.transport.firstTime !== null && b.transport.firstTime !== null;
    const agreement = !numerics || !enough ? "UNRESOLVED" : rmse <= thresholds.radialRMSE && shelfL1 <= thresholds.shelfL1 &&
      firstReturnDifference <= thresholds.firstReturn ? "PASS" : "FAIL";
    return { schema: "trisphere-run/2", version: VERSION, sourceSHA256: SOURCE_SHA256, parameters: p,
      assumptions: "TRISPHERE-CONTRACT.md", thresholds, thirteen: a, five: b,
      comparison: { radialRMSE: rmse, shelfL1, firstReturnDifference, mappedThirteenShelf: mapped, agreement,
        numericalChecks: numerics ? "PASS" : "FAIL", physicalValidation: "UNRESOLVED", observerProjection: "NOT_APPLICABLE" } };
  }
  function scanCell(k, gamma, input = {}) {
    const p = settings({ ...input, k, gamma }), row = { k, gamma };
    for (const id of Object.keys(configs)) {
      const r = radial(id, p), twin = radial(id, { ...p, x0: clamp(p.x0 + 0.02, 0, 1) });
      const start = Math.max(0, r.trace.length - Math.round(p.period / p.dt));
      const distance = Math.sqrt(sum(r.trace.slice(start).map((v, i) => (v.x - twin.trace[start + i].x) ** 2 +
        (v.v - twin.trace[start + i].v) ** 2)) / (r.trace.length - start));
      row[id] = { response: r.state, amplitude: r.amplitude, recurrence: r.recurrence, perturbationDistance: distance,
        attractionCandidate: r.state === "PERIODIC_CANDIDATE" && distance < thresholds.periodicDistance,
        numericalChecks: Math.max(r.maxResidual, twin.maxResidual) < thresholds.radialEnergy ? "PASS" : "FAIL",
        maxEnergyResidual: Math.max(r.maxResidual, twin.maxResidual) };
    }
    return row;
  }
  return { VERSION, SOURCE_SHA256, configs, defaults, thresholds, settings, mapLayer, potential, radial, transport, compare, scanCell };
});
