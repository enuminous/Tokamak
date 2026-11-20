"use strict";
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const T = require("./trisphere-core.js");
const args = process.argv.slice(2);
if (args.some(a => a !== "--full")) throw new Error("Usage: node run-trisphere.js [--full]");
const dir = path.join(__dirname, "results/trisphere-v2"); fs.mkdirSync(dir, { recursive: true });
const save = (name, value) => fs.writeFileSync(path.join(dir, name), JSON.stringify(value, null, 2) + "\n");
const hash = file => crypto.createHash("sha256").update(fs.readFileSync(path.join(__dirname, file))).digest("hex");
function compact(r) {
  const copy = { ...r };
  for (const id of ["thirteen", "five"]) {
    const { trace, ...radial } = r[id].radial;
    const { trace: transportTrace, firstReturnTrace, ...transport } = r[id].transport;
    copy[id] = { radial, transport };
  }
  return copy;
}
const evidence = { schema: "trisphere-evidence/2", version: T.VERSION, date: "2026-11-20",
  runtime: { node: process.version, platform: process.platform, arch: process.arch },
  hashes: { core: hash("trisphere-core.js"), runner: hash("run-trisphere.js"), source: T.SOURCE_SHA256 },
  command: "node run-trisphere.js", stochastic: false, seeds: "NOT_APPLICABLE",
  independentReview: "UNRESOLVED", browserQA: "Recorded separately in the publication report", cases: {} };
for (const [name, p] of [["containment", {}], ["exhaust", { boundary: "exhaust" }], ["no-drive", { k: 0 }]]) {
  const r = T.compare(p); evidence.cases[name] = compact(r);
  if (name === "containment") {
    save("default-summary.json", compact(r));
    const fields = ["t", "x", "v", "energy", "work", "dampingHeat", "contactHeat", "exported", "residual"];
    const lines = ["configuration," + fields.join(",")];
    for (const id of ["thirteen", "five"]) r[id].radial.trace.forEach((row, i) => {
      if (i % 10 === 0 || i === r[id].radial.trace.length - 1) lines.push(id + "," + fields.map(k => row[k]).join(","));
    });
    fs.writeFileSync(path.join(dir, "radial-sampled-0.1.csv"), lines.join("\n") + "\n");
    const tf = ["t", "mass", "energy", "heat", "work", "exportedMass", "exportedEnergy", "returned", "returnedEnergy", "firstReturned", "firstReturnedEnergy", "product", "compost", "massResidual", "energyResidual"];
    const tl = ["configuration," + tf.join(",") + ",shelf0,shelf1,shelf2,shelf3,shelf4"];
    for (const id of ["thirteen", "five"]) for (const row of r[id].transport.trace) {
      const occupancy = Array(5).fill(0);
      row.occupancy.forEach((v, i) => { occupancy[id === "thirteen" ? T.mapLayer(i) : i] += v; });
      tl.push(id + "," + [...tf.map(k => row[k]), ...occupancy].join(","));
    }
    fs.writeFileSync(path.join(dir, "transport-all-ticks.csv"), tl.join("\n") + "\n");
    if (args.includes("--full")) save("default-full.json", r);
  }
  console.log(name + ": " + JSON.stringify(r.comparison));
}
evidence.convergence = [.02, .01, .005].map(dt => {
  const r = T.compare({ dt });
  return { dt, radialRMSE: r.comparison.radialRMSE, agreement: r.comparison.agreement,
    thirteenMaxResidual: r.thirteen.radial.maxResidual, fiveMaxResidual: r.five.radial.maxResidual };
});
const ks = [0, .25, .5, .75, 1], gs = [0, .15, .3, .6, 1], grid = [];
for (const gamma of gs) for (const k of ks) grid.push(T.scanCell(k, gamma));
save("parameter-scan.json", { schema: "trisphere-scan/2", parameters: T.settings(), kGrid: ks, gammaGrid: gs,
  perturbation: "+0.02 initial position", sourceSHA256: T.SOURCE_SHA256, version: T.VERSION, rows: grid,
  scope: "Finite-window recurrence and one initial-position perturbation; no bifurcation proof" });
const columns = ["k", "gamma", "configuration", "response", "amplitude", "recurrence", "perturbationDistance", "attractionCandidate", "numericalChecks", "maxEnergyResidual"];
const csv = [columns.join(",")];
for (const cell of grid) for (const id of ["thirteen", "five"]) {
  const row = { k: cell.k, gamma: cell.gamma, configuration: id, ...cell[id] };
  csv.push(columns.map(key => row[key]).join(","));
}
fs.writeFileSync(path.join(dir, "parameter-scan.csv"), csv.join("\n") + "\n");
save("evidence.json", evidence);
console.log("Saved replay evidence and 25 parameter pairs to results/trisphere-v2/");
