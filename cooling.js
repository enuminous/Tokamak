"use strict";

(() => {
  const byId = id => document.getElementById(id);
  const shift = byId("cooling-shift");
  const radius = byId("cooling-radius");
  const canvas = byId("cooling-chart");
  const message = byId("cooling-message");
  const number = new Intl.NumberFormat("en-US", {maximumFractionDigits: 1, minimumFractionDigits: 1});
  let current;

  function draw() {
    if (!current || !canvas.clientWidth) return;
    const [nominal, weaker] = current;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * ratio);
    canvas.height = Math.round(h * ratio);
    const ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);

    const left = 46, right = w - 14, top = 12, bottom = h - 43;
    const step = Math.max(nominal.peakK, weaker.peakK) > 3500 ? 1500 : 500;
    const ceiling = Math.ceil(1.05 * Math.max(1800, nominal.peakK, weaker.peakK) / step) * step;
    const x = t => left + (right - left) * t / 5;
    const y = kelvin => bottom - (bottom - top) * kelvin / ceiling;
    ctx.fillStyle = "#172b3c";
    ctx.fillRect(x(1), top, x(2) - x(1), bottom - top);
    ctx.font = "12px system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#ccd5dd";
    for (let k = 0; k <= ceiling; k += step) {
      ctx.strokeStyle = "#364959";
      ctx.beginPath();
      ctx.moveTo(left, y(k)); ctx.lineTo(right, y(k)); ctx.stroke();
      ctx.fillText(k.toLocaleString("en-US"), left - 7, y(k));
    }
    ctx.textAlign = "center";
    for (let t = 0; t <= 5; t++) ctx.fillText(String(t), x(t), bottom + 12);
    ctx.fillText("Time (s)", (left + right) / 2, h - 8);

    ctx.strokeStyle = "#c3bfd1";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();ctx.moveTo(left, y(1800));ctx.lineTo(right, y(1800));ctx.stroke();
    for (const run of current) {
      ctx.strokeStyle = run.degraded ? "#ffb871" : "#80d8de";
      ctx.lineWidth = 2.5;
      ctx.setLineDash(run.degraded ? [7, 4] : []);
      ctx.beginPath();
      run.points.forEach(([t, k], i) => {
        if (i === 0) ctx.moveTo(x(t), y(k));
        else ctx.lineTo(x(t), y(k));
      });
      ctx.stroke();
    }
  }

  function select() {
    const pair = coolingCases.filter(row => row.shiftCm === Number(shift.value) && row.radiusMm === Number(radius.value));
    const nominal = pair.find(row => !row.degraded);
    const weaker = pair.find(row => row.degraded);
    if (pair.length !== 2 || !nominal || !weaker || nominal.heatMWm2 !== weaker.heatMWm2) {
      current = null;
      byId("cooling-panel").hidden = true;
      message.hidden = false;
      message.textContent = "A matched pair is unavailable for this geometry. The source data are linked below.";
      return;
    }
    current = [nominal, weaker];
    byId("cooling-flux").textContent = nominal.heatMWm2.toFixed(2) + " MW/m² of incident heat flux in both runs.";
    for (const [row, name] of [[nominal, "nominal"], [weaker, "weak"]]) {
      byId("cooling-" + name).textContent = number.format(row.peakK) + " K";
      byId("cooling-first-" + name).textContent = row.firstAboveS === null ? "Never" : row.firstAboveS.toFixed(2) + " s";
    }
    byId("cooling-panel").hidden = false;
    message.hidden = true;
    draw();
  }

  if (typeof coolingCases === "undefined") return;
  shift.disabled = radius.disabled = false;
  shift.addEventListener("change", select);
  radius.addEventListener("change", select);
  select();
  new ResizeObserver(draw).observe(canvas);
})();
