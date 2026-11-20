"use strict";
const canvas = document.getElementById("section");
const leak = document.getElementById("leak");
const recycle = document.getElementById("recycle");

const energyLeak = document.getElementById("energyLeak");
const energyReturn = document.getElementById("energyReturn");
const percent = value => (value * 100).toFixed(1) + "%";

function resize() {
  const { width, height } = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  Tokamak.draw(ctx, width, height);
}

function update() {
  document.getElementById("leakValue").value = leak.value + "%";
  document.getElementById("recycleValue").value = recycle.value + "%";
  const budget = Tokamak.budget(leak.valueAsNumber / 100, recycle.valueAsNumber / 100);
  for (const [name, value] of Object.entries(budget)) {
    document.getElementById(name).textContent = percent(value);
  }
  document.getElementById("energyLeakValue").value = energyLeak.value + "%";
  document.getElementById("energyReturnValue").value = energyReturn.value + "%";
  const energy = Tokamak.budget(energyLeak.valueAsNumber / 100, energyReturn.valueAsNumber / 100);
  document.getElementById("energyReturned").textContent = percent(energy.returned);
  document.getElementById("energyRemoved").textContent = percent(energy.removed);
  document.getElementById("energyNext").textContent = percent(energy.nextInventory);
}
energyLeak.addEventListener("input", update);
energyReturn.addEventListener("input", update);
leak.addEventListener("input", update);
recycle.addEventListener("input", update);
document.getElementById("reset").addEventListener("click", () => {
  leak.value = leak.defaultValue;
  recycle.value = recycle.defaultValue;
  energyLeak.value = energyLeak.defaultValue;
  energyReturn.value = energyReturn.defaultValue;
  update();
});
new ResizeObserver(resize).observe(canvas);
update();

const breaths = document.getElementById("breaths");
const damping = document.getElementById("damping");
const kick = document.getElementById("kick");
const layer = document.getElementById("layer");

function updateBreaths() {
  const gamma = damping.valueAsNumber;
  const work = kick.valueAsNumber;
  const { cycles, duration, position, equilibrium } = Tokamak.radialBreaths(gamma, work);
  const { width, height } = breaths.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  breaths.width = Math.round(width * scale);
  breaths.height = Math.round(height * scale);
  const ctx = breaths.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  const baseline = height - 25;
  // Fixed scale across the supported controls.
  const radialScale = (height - 45) / 4.2;
  ctx.font = "13px system-ui";
  ctx.fillStyle = "#bac8d8";
  ctx.fillText("ρ", 5, 15);
  ctx.fillText("Normalized time →", 12, height - 6);
  ctx.strokeStyle = "#94cbd0";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(12, baseline);
  cycles.forEach(({ energy }, i) => {
    for (let step = 1; step <= 60; step++) {
      const fraction = step / 60;
      ctx.lineTo(12 + (width - 24) * (i + fraction) / cycles.length,
        baseline - radialScale * position(energy, duration * fraction));
    }
  });
  ctx.stroke();
  document.getElementById("dampingValue").value = gamma.toFixed(2);
  document.getElementById("kickValue").value = work.toFixed(2);
  document.getElementById("firstLoss").textContent = cycles[0].loss.toFixed(3);
  document.getElementById("steadyEnergy").textContent = equilibrium.toFixed(3);
}

function updateHopf() {
  const rho = layer.valueAsNumber;
  const a = rho / Math.sqrt(2);
  const image = Tokamak.hopf(a, 0, a, 0).map(value => Math.round(value));
  document.getElementById("layerValue").value = rho;
  document.getElementById("hopfValue").textContent = rho === 0
    ? "The zero shell collapses to the origin."
    : "Equal real inputs on the shell map to (" + image.join(", ") + "), at image radius ρ².";
}
damping.addEventListener("input", updateBreaths);
kick.addEventListener("input", updateBreaths);
layer.addEventListener("input", updateHopf);
new ResizeObserver(updateBreaths).observe(breaths);
updateHopf();
