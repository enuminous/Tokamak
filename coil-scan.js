'use strict';
(async()=>{
 const base='benchmarks/openstep-003/results/';
 const [s,v]=await Promise.all(['summary.json','verification.json'].map(async p=>{const r=await fetch(base+p);if(!r.ok)throw Error(p);return r.json();}));
 const el=id=>document.getElementById(id),cm=x=>`${x>0?'+':''}${(x*100).toFixed(1)} cm`,cell=x=>{const e=document.createElement('td');e.textContent=x;return e;};
 const rows=Object.values(s.rows_by_grid).flat();el('accepted').textContent=`${rows.length} / ${s.case_status.length} cases`;
 const coarse=s.rows_by_grid['129']?.find(r=>r.shift_m===0);el('recovery').textContent=coarse?'Recovered':'Unresolved';
 const refined=s.refined_comparisons;const survives=refined?.some(r=>r.promising);
 el('decision').textContent=survives?'Survives refinement':refined?'Ranking did not survive':s.candidate_for_refinement_m!==null?'Candidate identified':'No qualifying candidate';
 el('decision-note').textContent=s.candidate_for_refinement_m!==null?`Selected movement: ${cm(s.candidate_for_refinement_m)}. ${refined?'The finer-grid comparison is included below and in the report.':'A finer-grid result has not been recorded.'}`:'No movement met every frozen screening criterion on the first two grids.';
 el('load-status').textContent=`Recorded results loaded · ${v.passed} numerical checks pass, ${v.failed} fail. Physical qualification remains unresolved.`;
 for(const n of s.grids){const o=new Option(`${n} × ${2*n-1}`,String(n));el('grid').add(o);}el('grid').value=s.grids.includes(257)?'257':String(s.grids[0]);
 function showCase(){const r=s.rows_by_grid[el('grid').value].find(r=>String(r.shift_m)===el('shift').value);if(!r)return;
  el('case-output').textContent=`${cm(r.shift_m)} · ${r.representative_heat_MW_m2?.toFixed(2)??'unresolved'} MW/m² representative heat`;
  el('case-detail').textContent=`Required transport H ${r.H_required_transport.toFixed(4)}; q95 ${r.q95.toFixed(3)}; vertical force slope ${(r.vertical_stiffness_N_per_m/1e6).toFixed(3)} MN/m (${r.vertical_stiffness_N_per_m>0?'destabilizing':'restoring'} in the rigid no-wall model). ${r.samples_above_10}/${r.load_samples} heat samples exceed 10 MW/m². These counts are not probabilities.`;
 }
 function showGrid(){const rr=[...s.rows_by_grid[el('grid').value]].sort((a,b)=>a.shift_m-b.shift_m);el('shift').replaceChildren();el('sweep-table').replaceChildren();
  for(const r of rr)el('shift').add(new Option(cm(r.shift_m),String(r.shift_m))); const planned=Number(el('grid').value)===513?rr.map(r=>r.shift_m):[-.05,-.025,-.01,0,.01,.025,.05]; for(const shift of planned){const r=rr.find(r=>r.shift_m===shift),tr=document.createElement('tr');const values=r?[cm(r.shift_m),r.axis_R_m.toFixed(5),r.representative_heat_MW_m2?.toFixed(2)??'unresolved',r.H_required_transport.toFixed(4),(r.near_LCFS_to_wall_m*100).toFixed(2),r.trace_checks_pass?'PASS':'FAIL']:[cm(shift),'Unresolved solve','—','—','—','Not screened'];values.forEach(x=>tr.append(cell(x)));el('sweep-table').append(tr);}el('shift').value='0';showCase();}
 el('grid').addEventListener('change',showGrid);el('shift').addEventListener('change',showCase);showGrid();
 for(const r of s.comparisons){const c=r.criteria;const tr=document.createElement('tr');[cm(r.shift_m),c.representative_heat_resolved_reduction,c.maximum_sampled_heat_reduced,c.no_resolved_clearance_deterioration,c.no_resolved_H_deterioration,r.promising].forEach(x=>tr.append(cell(typeof x==='boolean'?(x?'Yes':'No'):x)));el('decision-table').append(tr);}
 el('failure-note').textContent=`${s.failed_attempts.length} unsuccessful complete numerical attempts and ${s.interrupted_attempts.length} interrupted exploratory attempts are retained. Failed fields are excluded from physical comparisons.`;
 for(const x of s.unrun){const li=document.createElement('li');li.textContent=x;el('unrun').append(li);}
})().catch(e=>{document.getElementById('load-status').textContent='Results could not be loaded. The repository report and raw files remain available through the links above.';console.error(e);});
