"use strict";

function engine({ ns, sticking, recycle, cost, recovery, rate, nozzle, flow, external }) {
  const survival = Math.exp(-ns / 2196.98);
  const continuation = survival * (1 - sticking / 100) * recycle / 100;
  const fusions = survival / (1 - continuation);
  const decay = (1 - survival) / (1 - continuation);
  const stuck = survival * sticking / 100 / (1 - continuation);
  const returnLoss = survival * (1 - sticking / 100) * (1 - recycle / 100) / (1 - continuation);
  const neutron = 14.1 * fusions;
  const charged = 3.5 * fusions;
  const recovered = charged * recovery / 100;
  const wattsPerMeV = rate * 1e15 * 1.602176634e-13;
  const bootstrapWatts = cost * 1000 * wattsPerMeV;
  const available = (external ? recovered : Math.max(0, recovered - cost * 1000)) * wattsPerMeV;
  const jetWatts = available * nozzle / 100;
  const thrust = Math.sqrt(2 * flow * 1e-6 * jetWatts);
  return { fusions, decay, stuck, returnLoss, neutron, charged, recovered, available, jetWatts, thrust,
    bootstrapWatts, margin: recovered - cost * 1000 };
}

if (typeof module !== "undefined") module.exports = engine;
if (typeof document !== "undefined") {
  const parameters = [
    ["ns", "Fusion cycle time (ns)", 5, 200, 1, 15],
    ["sticking", "Effective sticking (%)", 0, 5, 0.1, 0.6],
    ["recycle", "Return of surviving unstuck muons (%)", 0, 100, 0.1, 99.5],
    ["cost", "Bootstrap cost (GeV per delivered muon)", 0.1, 12, 0.1, 9],
    ["recovery", "Charged energy recovered (%)", 0, 100, 1, 60],
    ["rate", "Delivered muons (10¹⁵ per second)", 0.1, 10, 0.1, 1],
    ["nozzle", "Jet conversion efficiency (%)", 0, 100, 1, 50],
    ["flow", "Propellant flow (mg/s)", 10, 1000, 10, 100]
  ];
  const byId = id => document.getElementById(id);
  for (const [id, name, min, max, step, value] of parameters) {
    byId("inputs").insertAdjacentHTML("beforeend",
      '<label for="' + id + '">' + name + '<output id="' + id + 'Out"></output></label>' +
      '<input type="range" id="' + id + '" min="' + min + '" max="' + max +
      '" step="' + step + '" value="' + value + '">');
    byId(id).addEventListener("input", update);
  }
  byId("external").addEventListener("input", update);
  byId("concept").addEventListener("input", update);
  update();

  function update() {
    const external = byId("external").checked;
    const state = { external };
    for (const [id] of parameters) {
      state[id] = byId(id).valueAsNumber;
      byId(id + "Out").value = byId(id).value;
    }
    const m = engine(state);
    const rows = [
      ["Fusions per delivered muon", m.fusions.toFixed(2)],
      ["Muon losses to decay / sticking / return", [m.decay, m.stuck, m.returnLoss].map(v => (v * 100).toFixed(1) + "%").join(" / ")],
      ["Neutron energy outside jet budget", m.neutron.toFixed(1) + " MeV/μ"],
      ["Charged fusion energy", m.charged.toFixed(1) + " MeV/μ"],
      ["Recovered charged energy", m.recovered.toFixed(1) + " MeV/μ"],
      ["Bootstrap power demand", (m.bootstrapWatts / 1000).toFixed(2) + " kW"],
      ["Net margin before the jet", m.margin.toFixed(1) + " MeV/μ"],
      ["Quark-stage power credit", "0 W"],
      ["Ideal directed jet power", (m.jetWatts / 1000).toFixed(3) + " kW"],
      ["Ideal thrust", m.thrust.toFixed(4) + " N"]
    ];
    byId("ledger").replaceChildren(...rows.flatMap(([name, value]) => {
      const term = document.createElement("dt");
      const detail = document.createElement("dd");
      term.textContent = name;
      detail.textContent = value;
      return [term, detail];
    }));
    byId("status").textContent = external
      ? "External bootstrap selected. The displayed jet is externally supported."
      : m.margin <= 0
        ? "Bootstrap deficit. The recirculating budget leaves no power for the torch."
        : "Positive modeled margin under these inputs. Auxiliary loads and feasibility remain open.";
    byId("quark").textContent = byId("concept").checked
      ? "Speculative flow: bootstrap → D–T loop → proposed quark chamber → torch. The proposed chamber is inactive and supplies zero power."
      : "Modeled flow: bootstrap → D–T loop → charged-energy recovery → conditional torch.";
  }
}
