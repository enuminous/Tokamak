'use strict';
const base='benchmarks/openstep-002/results/';
const get=id=>document.getElementById(id);
const fmt=(v,d=2)=>Number(v).toFixed(d);
function parseCsv(text){const lines=text.trim().split(/\r?\n/),header=lines.shift().split(',');return lines.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[header[i],v])));}
async function json(path){const r=await fetch(base+path);if(!r.ok)throw new Error(path+' unavailable');return r.json();}
async function csv(path){const r=await fetch(base+path);if(!r.ok)throw new Error(path+' unavailable');return parseCsv(await r.text());}
function addRow(name,finding,scope){const tr=document.createElement('tr');for(const text of [name,finding,scope]){const td=document.createElement('td');td.textContent=text;tr.append(td);}get('results-table').append(tr);}
(async()=>{try{
  const s=await json('summary.json');const n=s.selected_grid;
  const [energy,electric,verify]=await Promise.all([csv(`confinement-sweep-${n}.csv`),csv('electric-sweep.csv'),json('verification.json')]);
  const v=s.vertical.map(x=>fmt(x.translations[0].dFz_dz_N_per_m/1e6));
  addRow('Grid refinement',`${n} × ${2*n-1} selected; baseline flux mismatch ${fmt(s.reference_baseline_core_flux_nrmse*100,3)}%.`, 'Convergence tolerance 1e−5; observed grid differences are not rigorous error bounds.');
  const control=s.controlled.filter(x=>x.grid===257);const cb=control.find(x=>x.arm==='baseline'),cm=control.find(x=>x.arm==='p9-inward');
  addRow('Fixed pressure & current',cb?.converged&&cm?.converged?`Axis shift ${fmt(100*(cm.metrics.axis_R_m-cb.metrics.axis_R_m))} cm at 257 × 513.`:'Control comparison unresolved on the fine grid.','The medium-grid baseline control did not converge; the comparison is not fully verified across grids.');
  addRow('Vertical force',`Baseline ${v[0]}, changed ${v[1]} MN/m; both destabilizing.`,'Rigid current distribution, no conducting wall or feedback.');
  addRow('Confinement',`Required transport H: ${s.confinement.central.map(x=>fmt(x.H_required_transport,3)).join(' → ')}.`,'Prescribed power sources and mapped thermal energy; no turbulence prediction.');
  addRow('Exhaust',`${s.exhaust.wall_hits}/${s.exhaust.trace_count} traces hit the wall; ${s.exhaust.above_criterion}/${s.exhaust.load_samples} sampled loads exceed 10 MW/m².`,'Counts describe the chosen grid of assumptions, not a probability.');
  addRow('Engineering',`Largest external generalized coil load: ${fmt(Math.max(...s.engineering.flatMap(x=>x.coils.map(c=>c.resultant_generalized_N)))/1e6)} MN.`,'External magnetic loads, clearance and illustrative thermal diffusion only.');
  addRow('Electric budget',`${fmt(s.electric.minimum_net_MW,0)} to +${fmt(s.electric.maximum_net_MW,0)} MW across stated assumptions.`,'Source fusion power is imposed; no net-electric performance demonstrated.');
  for(const x of s.not_run){const li=document.createElement('li');li.textContent=x.test+' — '+x.reason+'.';get('not-run').append(li);}
  const updateEnergy=()=>{const r=energy.find(x=>x.arm===get('arm').value&&+x.H_transport===+get('h').value&&+x.aux_factor===+get('aux').value&&+x.radiation_factor===+get('rad').value);get('energy-output').textContent=r?`${fmt(r.W_start_MJ,1)} → ${fmt(r.W_30s_MJ,1)} MJ after 30 s · transport time ${fmt(r.tau_s)} s`:'Recorded case unavailable';};
  const updateElectric=()=>{const r=electric.find(x=>+x.thermal_efficiency===+get('eta-t').value&&+x.heating_wallplug_efficiency===+get('eta-w').value&&+x.other_electric_MW===+get('parasite').value);get('electric-output').textContent=r?`${+r.net_electric_MW>=0?'+':''}${fmt(r.net_electric_MW,1)} MW in this accounting case`:'Recorded case unavailable';};
  ['arm','h','aux','rad'].forEach(id=>get(id).addEventListener('change',updateEnergy));['eta-t','eta-w','parasite'].forEach(id=>get(id).addEventListener('change',updateElectric));updateEnergy();updateElectric();
  get('load-status').textContent=`Recorded results loaded · ${verify.passed} numerical checks pass, ${verify.failed} fail. Physical feasibility remains unresolved.`;
}catch(error){get('load-status').textContent='Results could not be loaded. Open the linked report or JSON for the recorded findings.';console.error(error);}})();
