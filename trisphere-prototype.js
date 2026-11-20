"use strict";
(() => {
  const T = window.TriSphere, $ = id => document.getElementById(id), teal = "#6dd6c5", gold = "#ffbd73";
  const controls = [
    ["k", "Valve opening k", 0, 1, .05, "core"], ["gamma", "Damping γ", 0, 2, .05, "core"],
    ["period", "Drive period", 2, 20, 1, "core"], ["duration", "Run duration", 16, 160, 8, "core"],
    ["product", "Product fraction σ", 0, 1, .05, "routing"], ["modulation", "Split modulation", 0, 1, .05, "routing"],
    ["release", "Shelf release rate", 0, 2, .1, "routing"], ["pump", "Work per return × k", 0, 1, .05, "routing"],
    ["particleExhaust", "Particle export fraction", 0, 1, .05, "routing"], ["energyExhaust", "Energy export fraction", 0, 1, .05, "routing"]
  ];
  let result = null, sweepResult = null, playing = false, frame = null, lastFrame = null, playbackTime = 0;
  const number = v => v === null ? "Not observed" : Math.abs(v) < 1e-5 && v !== 0 ? v.toExponential(2) : v.toFixed(4);
  for (const [id, label, min, max, step, group] of controls) {
    const div = document.createElement("div"), l = document.createElement("label"), out = document.createElement("output"), input = document.createElement("input");
    l.htmlFor = id; l.textContent = label; out.id = id + "-value"; out.htmlFor = id; l.append(out);
    Object.assign(input, { id, type: "range", min, max, step, value: T.defaults[id] });
    div.append(l, input); $(group + "-controls").append(div);
    input.addEventListener("input", edited);
  }
  function read() {
    const p = { boundary: $("boundary").value, mode: $("mode").value, weights: [0, 1, 2, 3].map(n => $("w" + n).valueAsNumber) };
    for (const [id] of controls) p[id] = $(id).valueAsNumber;
    return T.settings(p);
  }
  function outputs() {
    for (const [id] of controls) $(id + "-value").textContent = $(id).value;
    for (const id of ["particleExhaust", "energyExhaust"]) $(id).disabled = $("boundary").value === "contain";
  }
  function edited() { outputs(); $("run-status").textContent = "Inputs changed. Run comparison to update the results."; }
  $("boundary").addEventListener("change", edited); $("mode").addEventListener("change", edited);
  for (let n = 0; n < 4; n++) $("w" + n).addEventListener("input", edited);
  function stop() { playing = false; cancelAnimationFrame(frame); lastFrame = null; $("play").textContent = "Play recorded motion"; }
  function run(event) {
    if (event) event.preventDefault();
    stop(); $("run-status").classList.remove("error");
    try {
      const p = read(); $("run").disabled = true; $("run-status").textContent = "Computing both descriptions…";
      setTimeout(() => {
        try {
          result = T.compare(p); $("time").max = p.duration; $("time").value = 0;
          sweepResult = null; $("sweep-grid").replaceChildren(); $("export-sweep").hidden = true;
          $("sweep-status").textContent = "Not run for this comparison. A repeating response is a finite-run candidate, not a stability proof.";
          render(); $("run-status").textContent = "Run complete · " + p.duration + " time units · Δt " + p.dt + ".";
        } catch (error) { $("run-status").textContent = error.message; $("run-status").classList.add("error"); }
        finally { $("run").disabled = false; }
      }, 20);
    } catch (error) { $("run-status").textContent = error.message; $("run-status").classList.add("error"); $("run").disabled = false; }
  }
  $("settings").addEventListener("submit", run);
  $("reset").addEventListener("click", () => {
    for (const [id] of controls) $(id).value = T.defaults[id];
    $("boundary").value = "contain"; $("mode").value = "maintain";
    for (let n = 0; n < 4; n++) $("w" + n).value = 1;
    outputs(); run();
  });
  function chart(id, series, options = {}) {
    const c = $(id), ctx = c.getContext("2d"), w = c.width, h = c.height, pad = { l: 55, r: 15, t: 18, b: 32 };
    ctx.clearRect(0, 0, w, h);
    const xmax = options.xmax || result.parameters.duration;
    const values = series.flatMap(s => s.data.map(p => p[1]));
    const ymax = options.ymax || Math.max(.01, ...values) * 1.08;
    const px = t => pad.l + t / xmax * (w - pad.l - pad.r), py = v => h - pad.b - v / ymax * (h - pad.t - pad.b);
    ctx.font = "14px system-ui"; ctx.textAlign = "right";
    for (let i = 0; i <= 4; i++) {
      const value = ymax * i / 4, y = py(value); ctx.strokeStyle = "#304252"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      ctx.fillStyle = "#a8bacb"; ctx.fillText(value.toFixed(2), pad.l - 7, y + 5);
    }
    ctx.textAlign = "center";
    for (let i = 0; i <= 4; i++) { const t = xmax * i / 4; ctx.fillText(t.toFixed(0), px(t), h - 8); }
    for (const s of series) {
      ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.setLineDash(s.dashed ? [6, 5] : []); ctx.beginPath();
      s.data.forEach(([t, v], i) => i ? ctx.lineTo(px(t), py(v)) : ctx.moveTo(px(t), py(v))); ctx.stroke();
    }
    ctx.setLineDash([]);
  }
  function render() {
    const r = result, comp = r.comparison;
    for (const [id, value] of [["accounting", comp.numericalChecks], ["agreement", comp.agreement]]) {
      $(id).textContent = value; $(id).className = value.toLowerCase();
    }
    $("agreement-detail").textContent = comp.agreement === "FAIL" ? "At least one declared criterion missed" : comp.agreement === "PASS" ? "Only these settings and closures" : "Insufficient duration or numerical accuracy";
    $("radial-metric").textContent = "Position RMSE " + number(comp.radialRMSE) + " · tolerance ≤ " + T.thresholds.radialRMSE + ".";
    sizeCanvases();
    chart("motion", ["thirteen", "five"].map((id, i) => ({ color: i ? gold : teal, data: r[id].radial.trace.filter((_, j) => j % 5 === 0).map(v => [v.t, v.x]) })), { ymax: 1 });
    chart("energy", ["thirteen", "five"].flatMap((id, i) => [
      { color: i ? gold : teal, data: r[id].transport.trace.map(v => [v.t, v.energy]) },
      { color: i ? gold : teal, dashed: true, data: r[id].transport.trace.map(v => [v.t, v.heat]) }
    ]));
    const rows = [], add = (name, a, b) => rows.push([name, a, b]);
    add("Radial probe · independent energy units", null, null);
    const a = r.thirteen, b = r.five;
    const labels = { PERIODIC_CANDIDATE: "Periodic candidate", SETTLED: "Settled", TRANSIENT_OR_OTHER: "Transient / other", UNRESOLVED_SHORT_RUN: "Short run / unresolved" };
    add("Finite-run response", labels[a.radial.state], labels[b.radial.state]);
    for (const [label, key] of [["Mechanical energy", "energy"], ["External signed work", "work"], ["Damping heat", "dampingHeat"], ["Contact heat", "contactHeat"], ["Exported at shell", "exported"]]) add(label, number(a.radial.final[key]), number(b.radial.final[key]));
    add("Maximum radial balance residual", number(a.radial.maxResidual), number(b.radial.maxResidual));
    add("Inventory circuit · separate ledger", null, null);
    for (const [label, key] of [["Material remaining", "mass"], ["Material exported", "exportedMass"], ["First-return fraction", "firstReturned"], ["First-return energy / initial energy", "firstReturnedEnergy"], ["Repeated material returns (cumulative)", "returned"], ["Mobile energy", "energy"], ["Internal heat", "heat"], ["External supplied work", "work"], ["Energy exported", "exportedEnergy"], ["Product throughput (cumulative)", "product"], ["Compost throughput (cumulative)", "compost"]]) add(label, number(a.transport.final[key]), number(b.transport.final[key]));
    add("First return time", number(a.transport.firstTime), number(b.transport.firstTime));
    add("Mean first return time (returned subset)", number(a.transport.conditionalMeanFirstReturn), number(b.transport.conditionalMeanFirstReturn));
    add("Maximum material balance residual", number(a.transport.maxMassResidual), number(b.transport.maxMassResidual));
    add("Maximum transport energy residual", number(a.transport.maxEnergyResidual), number(b.transport.maxEnergyResidual));
    $("ledger").replaceChildren(...rows.map(([name, x, y]) => {
      const tr = document.createElement("tr");
      if (x === null) { const th = document.createElement("th"); th.colSpan = 3; th.textContent = name; tr.className = "subhead"; tr.append(th); }
      else for (const [i, value] of [name, x, y].entries()) { const cell = document.createElement(i ? "td" : "th"); cell.textContent = value; if (!i) cell.scope = "row"; tr.append(cell); }
      return tr;
    }));
    drawShelves(); drawStructure();
  }
  function sizeCanvases() {
    for (const id of ["structure", "motion", "energy", "shelves"]) {
      const c = $(id), width = Math.max(260, Math.floor(c.getBoundingClientRect().width));
      c.width = width; c.height = id === "structure" ? (width < 600 ? 460 : 300) : id === "shelves" ? 240 : 270;
    }
  }
  function drawShelves() {
    const c = $("shelves"), ctx = c.getContext("2d"), w = c.width, h = c.height;
    ctx.clearRect(0, 0, w, h);
    const a = result.comparison.mappedThirteenShelf, b = result.five.transport.final.occupancy;
    const max = Math.max(.01, ...a, ...b) * 1.2;
    const labels = ["CRP", "Lower / Time", "Filter / Space", "Upper / Phase", "Shell"];
    for (let i = 0; i < 5; i++) {
      const x = w * (i + .5) / 5, bar = Math.min(24, w / 13);
      [a[i], b[i]].forEach((v, j) => { const height = v / max * 155; ctx.fillStyle = j ? gold : teal; ctx.fillRect(x - bar - 2 + (bar + 4) * j, 180 - height, bar, height);
        if (w >= 600) { ctx.font = "14px system-ui"; ctx.textAlign = "center"; ctx.fillText(v.toFixed(3), x - bar / 2 - 2 + (bar + 4) * j, 172 - height); } });
      ctx.fillStyle = "#a8bacb"; ctx.font = "14px system-ui"; ctx.textAlign = "center";
      labels[i].split(" / ").forEach((word, line) => ctx.fillText(word, x, 208 + 19 * line));
    }
  }
  function drawStructure() {
    if (!result) return;
    const canvas = $("structure"), ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h); const t = $("time").valueAsNumber; $("time-label").textContent = t.toFixed(1);
    const rounded = $("standing").value === "source", nodes = Number($("nodes").value);
    ["thirteen", "five"].forEach((id, j) => {
      const stacked = w < 600, cx = stacked ? w / 2 : w * (j ? .75 : .25), cy = stacked ? 110 + j * 230 : 143;
      const color = j ? gold : teal, length = T.configs[id].length, radiusMax = Math.min(92, w / (stacked ? 3.5 : 7) - 8);
      ctx.strokeStyle = "#365366"; ctx.lineWidth = 1;
      for (let layer = 1; layer <= length; layer++) {
        const radius = 10 + layer / length * (radiusMax - 10); ctx.beginPath();
        if (rounded) ctx.ellipse(cx, cy, radius * 1.5, radius, 0, 0, 2 * Math.PI);
        else ctx.rect(cx - radius * 1.5, cy - radius, 3 * radius, 2 * radius);
        ctx.stroke();
      }
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
      for (let n = 0; n <= nodes; n++) { const a = -Math.PI / 2 + 2 * Math.PI * n / nodes, x = cx + 33 * Math.cos(a), y = cy + 33 * Math.sin(a); if (n) ctx.lineTo(x, y); else ctx.moveTo(x, y); } ctx.stroke();
      const row = result[id].radial.trace[Math.min(result[id].radial.trace.length - 1, Math.round(t / result.parameters.dt))];
      const mx = cx + row.x * radiusMax * 1.5; ctx.beginPath(); ctx.arc(mx, cy, 7, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill();
      ctx.font = "16px system-ui"; ctx.textAlign = "center"; ctx.fillText(j ? "FIVE POSITIONS" : "THIRTEEN LAYERS", cx, cy + radiusMax + 30);
      ctx.font = "14px system-ui"; ctx.fillStyle = "#a8bacb"; ctx.fillText("CRP", cx - 17, cy + 55); ctx.fillText("Shell", cx + radiusMax * 1.3, cy + 25);
    });
  }
  $("standing").addEventListener("change", drawStructure); $("nodes").addEventListener("change", drawStructure);
  $("time").addEventListener("input", () => { stop(); drawStructure(); });
  function animate(stamp) {
    if (!playing) return; if (lastFrame === null) lastFrame = stamp;
    let t = playbackTime + Math.min(.1, (stamp - lastFrame) / 1000) * 3;
    if (t > result.parameters.duration) t = 0;
    playbackTime = t; $("time").value = t; lastFrame = stamp; drawStructure(); frame = requestAnimationFrame(animate);
  }
  $("play").addEventListener("click", () => { if (playing) stop(); else if (result) { playing = true; playbackTime = $("time").valueAsNumber; $("play").textContent = "Pause motion"; frame = requestAnimationFrame(animate); } });
  function download(name, value) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
    const a = document.createElement("a"); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  $("export").addEventListener("click", () => { if (result) download("trisphere-run-v2.json", { ...result, observerView: { standing: $("standing").value, avatarNodes: Number($("nodes").value), affectsDynamics: false } }); });
  $("sweep").addEventListener("click", async () => {
    let p; try { p = read(); } catch (e) { $("sweep-status").textContent = e.message; return; }
    $("sweep").disabled = true; $("export-sweep").hidden = true;
    $("settings").querySelectorAll("input, select, button").forEach(el => { el.disabled = true; });
    const ks = [0, .25, .5, .75, 1], gs = [0, .15, .3, .6, 1], rows = [];
    try {
      for (const gamma of gs) for (const k of ks) {
        $("sweep-status").textContent = "Computing " + (rows.length + 1) + " of 25 settings…";
        await new Promise(resolve => setTimeout(resolve, 0)); rows.push(T.scanCell(k, gamma, p));
      }
      sweepResult = { schema: "trisphere-scan/2", version: T.VERSION, sourceSHA256: T.SOURCE_SHA256, parameters: p,
        kGrid: ks, gammaGrid: gs, perturbation: "+0.02 initial position", rows,
        scope: "Finite-window recurrence and initial-position probe; no bifurcation or stability proof" };
      const table = document.createElement("table"), head = table.createTHead().insertRow();
      for (const label of ["γ / k", ...ks]) { const th = document.createElement("th"); th.textContent = label; head.append(th); }
      const body = table.createTBody();
      for (const gamma of gs) {
        const tr = body.insertRow(), th = document.createElement("th"); th.scope = "row"; th.textContent = gamma; tr.append(th);
        for (const k of ks) {
          const row = rows.find(v => v.k === k && v.gamma === gamma), td = tr.insertCell();
          const label = r => r.numericalChecks === "FAIL" ? "Numerics fail" : r.response === "SETTLED" ? "Settled" : r.attractionCandidate ? "Periodic*" : r.response === "PERIODIC_CANDIDATE" ? "Repeats*" : "Unresolved";
          td.append(document.createTextNode("13: " + label(row.thirteen))); const small = document.createElement("small"); small.textContent = "5: " + label(row.five); td.append(small);
        }
      }
      $("sweep-grid").replaceChildren(table); $("sweep-status").textContent = "25 settings recorded at duration " + p.duration + ", period " + p.period + ", " + p.boundary + " boundary. *Periodic: recurrence plus the initial-position probe; repeats: recurrence alone. Finite-run candidates only.";
      $("export-sweep").hidden = false;
    } catch (e) { $("sweep-status").textContent = "Scan stopped: " + e.message; }
    finally { $("sweep").disabled = false; $("settings").querySelectorAll("input, select, button").forEach(el => { el.disabled = false; }); outputs(); }
  });
  $("export-sweep").addEventListener("click", () => { if (sweepResult) download("trisphere-scan-v2.json", sweepResult); });
  window.addEventListener("resize", () => { if (result) render(); });
  outputs(); run();
})();
