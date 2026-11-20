"use strict";
(() => {
  const canvas = document.getElementById("reactor");
  const ctx = canvas.getContext("2d");
  const controls = Object.fromEntries(["yaw", "tilt", "cut", "speed", "pitch"]
    .map(id => [id, document.getElementById(id)]));
  const labels = document.getElementById("annotations");
  const button = document.getElementById("animate");
  const tau = 2 * Math.PI;
  const radians = angle => angle * Math.PI / 180;
  let playing = false;
  let phase = 0;
  let frame;
  let previous;

  function ring(radius, theta, z) {
    return [radius * Math.cos(theta), radius * Math.sin(theta), z];
  }

  function surface(minor, theta, phi) {
    return ring(2.4 + minor * Math.cos(phi), theta, minor * Math.sin(phi));
  }

  function draw() {
    const { width, height } = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(width * dpr);
    const pixelHeight = Math.round(height * dpr);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const values = Object.fromEntries(Object.entries(controls).map(([name, input]) => {
      const unit = ["yaw", "tilt", "cut"].includes(name) ? "°" : "";
      document.getElementById(name + "Value").value = input.value + unit;
      return [name, input.valueAsNumber];
    }));
    const azimuth = radians(values.yaw);
    const elevation = radians(values.tilt);
    const cut = radians(values.cut);
    const scale = Math.min(width / 8.6, height / 7.4);

    function project([x, y, z]) {
      const horizontal = x * Math.cos(azimuth) - y * Math.sin(azimuth);
      const depth = x * Math.sin(azimuth) + y * Math.cos(azimuth);
      return [width / 2 + scale * horizontal,
        height / 2 + scale * (depth * Math.sin(elevation) - z * Math.cos(elevation))];
    }

    function line(path, color, begin = 0, end = tau, count = 144, weight = 1) {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = weight;
      for (let i = 0; i <= count; i++) {
        const point = project(path(begin + (end - begin) * i / count));
        if (i === 0) ctx.moveTo(...point);
        else ctx.lineTo(...point);
      }
      ctx.stroke();
    }

    for (const z of [-1.45, 1.45]) {
      line(theta => ring(2.65, theta, z), "#6ea8e1", cut, tau, 144, 2);
    }
    for (let i = 0; i < 12; i++) {
      const theta = i * tau / 12;
      if (theta < cut) continue;
      line(phi => surface(1.26, theta, phi), "#bca4dc", 0, tau, 48, 1.8);
      line(phi => surface(0.99, theta, phi), "#7d96af", 0, tau, 48);
    }
    for (let i = 0; i < 8; i++) {
      const phi = i * tau / 8;
      line(theta => surface(0.99, theta, phi), "#526c88", cut);
      line(theta => surface(0.70, theta, phi), "#4d99a4", cut);
    }
    for (const radius of [2.08, 2.72]) {
      line(theta => ring(radius, theta, -0.96), "#ffc57a", cut, tau, 144, 2.5);
    }
    if (cut > 0) {
      line(phi => surface(0.70, cut, phi), "#94cbd0", 0, tau, 60, 2);
      line(phi => surface(0.70, 0, phi), "#94cbd0", 0, tau, 60, 2);
    }
    for (let i = 0; i < 12; i++) {
      const theta = (phase + i * tau / 12) % tau;
      if (theta < cut) continue;
      const [x, y] = project(surface(0.63, theta, values.pitch * theta));
      ctx.beginPath();
      ctx.fillStyle = "#ffc57a";
      ctx.arc(x, y, 3, 0, tau);
      ctx.fill();
    }
    if (labels.checked && width >= 490) {
      ctx.font = "13px system-ui";
      const annotations = [
        ["Poloidal-field coil", ring(2.65, Math.PI, 1.45), 12, 18],
        ["Toroidal-field coils", surface(1.26, Math.PI / 2, 0), width - 132, 18],
        ["Vacuum vessel", surface(0.99, Math.PI, 0), 12, 43],
        ["Confined plasma", surface(0.70, cut, 0), width - 120, height - 34],
        ["Divertor targets", ring(2.72, Math.PI / 2, -0.96), 12, height - 12]
      ];
      for (const [label, point, x, y] of annotations) {
        const [px, py] = project(point);
        ctx.beginPath();
        ctx.strokeStyle = "#8194a9";
        ctx.lineWidth = 1;
        ctx.moveTo(x + 4, y + 2);
        ctx.lineTo(px, py);
        ctx.stroke();
        ctx.fillStyle = "#e7edf3";
        ctx.fillText(label, x, y);
      }
    }
  }

  function animate(time) {
    const elapsed = previous === undefined ? 0 : Math.min(0.1, (time - previous) / 1000);
    previous = time;
    phase = (phase + elapsed * controls.speed.valueAsNumber) % tau;
    draw();
    frame = requestAnimationFrame(animate);
  }

  for (const input of [...Object.values(controls), labels]) {
    input.addEventListener("input", draw);
  }
  button.addEventListener("click", () => {
    playing = !playing;
    button.textContent = playing ? "Pause tracers" : "Play tracers";
    if (playing) {
      previous = undefined;
      frame = requestAnimationFrame(animate);
    } else cancelAnimationFrame(frame);
  });
  new ResizeObserver(draw).observe(canvas);
})();
