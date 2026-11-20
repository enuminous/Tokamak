"use strict";

const versions = {
  thirteen: { title: "Thirteen layers · primary", shelf: layer => layer },
  five: { title: "Five-Structure · alternate", shelf: layer => layer <= 4 ? 1 : layer <= 7 ? 2 : 3 }
};
const compost = [8, 9, 10, 11];
const shelfLayers = [1, 2, 3, 4, 7];
const dwell = { 1: 0.45, 2: 0.35, 3: 0.25, 4: 0.15, 7: 0.4 };

function simulate(version, settings) {
  const { product, bias, damping, drive, materialLoss, energyLoss, steps, boundary } = settings;
  const config = versions[version];
  const shelves = new Map();
  for (const layer of shelfLayers) {
    const key = config.shelf(layer);
    if (!shelves.has(key)) shelves.set(key, { rates: [], mass: 0, energy: 0 });
    shelves.get(key).rates.push(dwell[layer]);
  }
  if (version === "five") shelves.set(3, { rates: [0], mass: 0, energy: 0 });
  const weights = compost.map((_, i) => 1 + bias * i);
  const weightSum = weights.reduce((a, b) => a + b, 0);
  let packets = [{ mass: 1, energy: 1, remaining: 12 }];
  let heat = 0, work = 0, exportedMass = 0, exportedEnergy = 0;
  let returned = 0, returnedEnergy = 0, firstReturn = null;
  let productMass = 0, compostMass = 0;
  for (let tick = 1; tick <= steps; tick++) {
    const next = [];
    function route({ mass, energy }) {
      const kick = drive * mass;
      work += kick;
      next.push({ mass, energy: energy + kick, remaining: 12 });
      returned += mass;
      returnedEnergy += energy;
      if (firstReturn === null && mass > 0) firstReturn = tick;
    }
    for (const shelf of shelves.values()) {
      const rate = shelf.rates.reduce((a, b) => a + b, 0) / shelf.rates.length;
      const mass = shelf.mass * rate;
      const energy = shelf.energy * rate;
      if (mass > 0 || energy > 0) route({ mass, energy });
      shelf.mass -= mass;
      shelf.energy -= energy;
    }
    for (const packet of packets) {
      heat += packet.energy * damping;
      packet.energy *= 1 - damping;
      packet.remaining--;
      if (packet.remaining === 6 && packet.routeLayer === undefined && packet.destination === undefined) {
        productMass += packet.mass * product;
        compostMass += packet.mass * (1 - product);
        const split = (layer, fraction) => {
          if (fraction > 0) next.push({ mass: packet.mass * fraction, energy: packet.energy * fraction,
            routeLayer: layer, remaining: packet.remaining });
        };
        split(7, product);
        compost.forEach((layer, i) => split(12 - layer, (1 - product) * weights[i] / weightSum));
      } else if (packet.remaining > 0) {
        next.push(packet);
      } else if (packet.destination !== undefined) {
        const shelf = shelves.get(packet.destination);
        shelf.mass += packet.mass;
        shelf.energy += packet.energy;
      } else {
        const massLoss = boundary === "exhaust" ? packet.mass * materialLoss : 0;
        const heatLoss = boundary === "exhaust" ? packet.energy * energyLoss : 0;
        exportedMass += massLoss;
        exportedEnergy += heatLoss;
        const mass = packet.mass - massLoss;
        const energy = packet.energy - heatLoss;
        if (mass > 0 || energy > 0) {
          next.push({ mass, energy, destination: config.shelf(packet.routeLayer),
            remaining: 12 - packet.routeLayer });
        }
      }
    }
    // Cohorts with the same destination and arrival time have identical future dynamics.
    const merged = new Map();
    for (const packet of next) {
      const key = [packet.destination, packet.routeLayer, packet.remaining].join("/");
      const prior = merged.get(key);
      if (prior) {
        prior.mass += packet.mass;
        prior.energy += packet.energy;
      } else merged.set(key, packet);
    }
    packets = [...merged.values()];
  }
  const transitMass = packets.reduce((sum, packet) => sum + packet.mass, 0);
  const transitEnergy = packets.reduce((sum, packet) => sum + packet.energy, 0);
  const totalMass = [...shelves.values()].reduce((sum, shelf) => sum + shelf.mass, transitMass);
  const totalEnergy = [...shelves.values()].reduce((sum, shelf) => sum + shelf.energy, transitEnergy);
  return { shelves, transitMass, transitEnergy, exportedMass, exportedEnergy, heat, work, returned,
    returnedEnergy, firstReturn, productMass, compostMass, massResidual: totalMass + exportedMass - 1,
    energyResidual: totalEnergy + heat + exportedEnergy - 1 - work };
}

if (typeof module !== "undefined") module.exports = { simulate };
if (typeof document !== "undefined") {
  const controls = [
    ["product", "Product fraction", 0, 1, 0.01, 0.45],
    ["bias", "Compost bias toward layer 11", 0, 3, 0.1, 0.5],
    ["damping", "Damping per tick", 0, 0.2, 0.01, 0.03],
    ["drive", "Work per returned unit", 0, 1, 0.01, 0.15],
    ["materialLoss", "Exhaust material fraction", 0, 1, 0.01, 0.25],
    ["energyLoss", "Exhaust energy fraction", 0, 1, 0.01, 0.6],
    ["steps", "Elapsed ticks", 0, 200, 1, 75]
  ];
  const byId = id => document.getElementById(id);
  const num = value => value.toFixed(4);
  for (const [id, label, min, max, step, value] of controls) {
    byId("controls").insertAdjacentHTML("beforeend", '<div><label for="' + id + '">' + label +
      '<output id="' + id + 'Value"></output></label><input type="range" id="' + id +
      '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + value + '"></div>');
    byId(id).addEventListener("input", update);
  }
  byId("boundary").addEventListener("change", update);
  update();
  function update() {
    const settings = { boundary: byId("boundary").value };
    for (const [key] of controls) {
      settings[key] = byId(key).valueAsNumber;
      byId(key + "Value").value = byId(key).value;
    }
    byId("materialLoss").disabled = settings.boundary === "contain";
    byId("energyLoss").disabled = settings.boundary === "contain";
    byId("comparison").replaceChildren(...Object.entries(versions).map(([id, version]) => {
      const result = simulate(id, settings);
      const section = document.createElement("section");
      const title = document.createElement("h2");
      title.textContent = version.title;
      const list = document.createElement("dl");
      const rows = [
        ["First material return (tick)", result.firstReturn ?? "Pending"],
        ["Returned material / energy (cumulative)", num(result.returned) + " / " + num(result.returnedEnergy)],
        ["Product / Compost (cumulative)", num(result.productMass) + " / " + num(result.compostMass)],
        ["In-transit material / energy", num(result.transitMass) + " / " + num(result.transitEnergy)],
        ["Exported material / energy", num(result.exportedMass) + " / " + num(result.exportedEnergy)],
        ["Internal heat / supplied work", num(result.heat) + " / " + num(result.work)],
        ...[...result.shelves].map(([key, shelf]) => [
          (id === "five" ? ["Center", "Lower membrane", "Avatar membrane", "Upper membrane"][key] :
            "Layer " + key) + " inventory (material / energy)", num(shelf.mass) + " / " + num(shelf.energy)]),
        ["Material / energy residual", result.massResidual.toExponential(1) + " / " + result.energyResidual.toExponential(1)]
      ];
      for (const [label, value] of rows) {
        const term = document.createElement("dt");
        const detail = document.createElement("dd");
        term.textContent = label;
        detail.textContent = value;
        list.append(term, detail);
      }
      section.append(title, list);
      return section;
    }));
  }
}
