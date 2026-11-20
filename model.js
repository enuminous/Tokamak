"use strict";

// Dimensionless poloidal flux. x is radial offset and z is height.
const Tokamak = (() => {
  const edge = 1 / 6;
  const view = { left: -0.95, right: 0.95, bottom: -1.55, top: 0.85 };
  const flux = (x, z) => x * x / 2 + z * z / 2 + z ** 3 / 3;
  const field = (x, z) => [-z * (1 + z), x];
  function budget(leak, recycle) {
    const retained = 1 - leak;
    const returned = leak * recycle;
    const removed = leak * (1 - recycle);
    return { retained, returned, removed, nextInventory: retained + returned };
  }
  // Unnormalized Hopf map in real coordinates; output radius is rho squared.
  function hopf(a, b, c, d) {
    return [a*a + b*b - c*c - d*d, 2*(a*c + b*d), 2*(b*c - a*d)];
  }

  // Unit frequency, unit mass. Reflect at rho=0, then add work once per return.
  function radialBreaths(gamma, kick, count = 8) {
    const frequency = Math.sqrt(1 - gamma * gamma / 4);
    const duration = Math.PI / frequency;
    const retention = Math.exp(-gamma * duration);
    let energy = 1;
    const cycles = [];
    for (let i = 0; i < count; i++) {
      const next = retention * energy + kick;
      cycles.push({ energy, loss: (1 - retention) * energy, next });
      energy = next;
    }
    return { cycles, duration, retention, equilibrium: kick / (1 - retention),
      position: (energy, time) => Math.sqrt(2 * energy) *
        Math.exp(-gamma * time / 2) * Math.sin(frequency * time) / frequency };
  }

  function draw(ctx, width, height) {
    const px = x => (x - view.left) / (view.right - view.left) * width;
    const py = z => (view.top - z) / (view.top - view.bottom) * height;
    ctx.fillStyle = "#101c29";
    ctx.fillRect(0, 0, width, height);

    function contour(level, color, weight, side, from, to) {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = weight;
      let connected = false;
      for (let i = 0; i <= 900; i++) {
        const z = from + (to - from) * i / 900;
        const x2 = 2 * (level - flux(0, z));
        if (x2 < -1e-10) {
          connected = false;
          continue;
        }
        const x = side * Math.sqrt(Math.max(0, x2));
        if (connected) ctx.lineTo(px(x), py(z));
        else ctx.moveTo(px(x), py(z));
        connected = true;
      }
      ctx.stroke();
    }
    for (const side of [-1, 1]) {
      for (let i = 1; i <= 12; i++) {
        contour(edge * i / 13, "#5c9fa7", 1.2, side, -1, 0.5);
      }
      for (let i = 1; i <= 4; i++) {
        contour(edge + i * 0.022, "#7d96af", 1, side, view.bottom, view.top);
      }
      contour(edge, "#ffc57a", 2.6, side, view.bottom, -1);
      contour(edge, "#ffc57a", 2.6, side, -1, 0.5);
    }

    ctx.fillStyle = "#d3dce6";
    ctx.fillRect(0, height - 5, width, 5);
    ctx.font = "14px system-ui";
    for (const [z, label] of [[0, "Magnetic axis"], [-1, "X-point"]]) {
      ctx.beginPath();
      ctx.arc(px(0), py(z), 4, 0, 2 * Math.PI);
      ctx.fillStyle = "#ffc57a";
      ctx.fill();
      ctx.fillText(label, px(0) + 11, py(z) + 5);
    }
  }
  return { edge, view, flux, field, budget, draw, hopf, radialBreaths };
})();
if (typeof module !== "undefined") module.exports = Tokamak;
