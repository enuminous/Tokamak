"use strict";
const canvas = document.getElementById("section");
const leak = document.getElementById("leak");
const recycle = document.getElementById("recycle");

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
    document.getElementById(name).textContent = (value * 100).toFixed(1) + "%";
  }
}
leak.addEventListener("input", update);
recycle.addEventListener("input", update);
document.getElementById("reset").addEventListener("click", () => {
  leak.value = leak.defaultValue;
  recycle.value = recycle.defaultValue;
  update();
});
new ResizeObserver(resize).observe(canvas);
update();
