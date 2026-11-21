"""Generate the report from recorded results, including every failed attempt."""
from pathlib import Path
import json,platform,hashlib
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def f(x,d=4):return 'UNRESOLVED' if x is None else f'{x:.{d}f}'
def main():
 s=json.loads((OUT/'summary.json').read_text());v=json.loads((OUT/'verification.json').read_text())
 coarse=next((r for r in s['rows_by_grid'].get('129',[]) if r['shift_m']==0),None)
 chosen=s['candidate_for_refinement_m'];refined=s['refined_comparisons'];passes=[r for r in refined or [] if r['promising']]
 recovery='Recovered under the original physical operator and acceptance threshold.' if coarse else 'UNRESOLVED: the original coarse baseline did not meet acceptance.'
 decision=('No candidate met all frozen screening criteria on the first two grids. The optional 513 × 1025 refinement was not triggered.' if chosen is None else
           f'The {chosen*100:+g} cm candidate met the first comparison rule. '+('It also meets that rule on the finer pair.' if passes else 'It does not meet the rule on the finer pair.' if refined else 'Finer-grid confirmation is not recorded.'))
 lines=['# OPENSTEP-003 — fixed-pressure/current coil scan','',
 'Matthew Chenoweth Wright / Monolithic LLC · 21 November 2026','',
 f'**Coarse baseline:** {recovery}',f'**Design decision:** {decision}','',
 f'Planned grid/geometry cases: {len(s["case_status"])}; accepted: {sum(r["status"]=="ACCEPTED" for r in s["case_status"])}; unresolved: {sum(r["status"]=="UNRESOLVED" for r in s["case_status"])}. Unresolved numerical attempts do not prove that an equilibrium does not exist.','',
 f'Numerical verification: **{v["passed"]} PASS, {v["failed"]} FAIL**. These checks concern implementation and numerical acceptance, not reactor qualification.','',
 '## What changed','',
 'The previous +10 cm fixed-derivative experiment changed pressure and plasma current as well as coil geometry. This scan holds the entire p(s) function and total Ip at the published OPENSTEP-001 baseline 257-grid operating point while moving the two p9 packs by 1, 2.5 and 5 cm in either direction. Coil currents and F at the boundary stay fixed. Positive movement is toward the midplane.','',
 'The initial protocol precedes these solves. Additional restart routes are disclosed in [AMENDMENTS.md](AMENDMENTS.md). This is exploratory work, not independent preregistration or experimental validation.','',
 '## Complete accepted-field comparison','',
 '| Grid | p9 shift (cm) | Axis R (m) | q95 | Required H | Heat (MW/m²) | Wall clearance (cm) | Heat samples >10 |',
 '|---|---:|---:|---:|---:|---:|---:|---:|']
 for n in s['grids']:
  for r in sorted(s['rows_by_grid'][str(n)],key=lambda x:x['shift_m']):
   lines.append(f'| {n} × {2*n-1} | {r["shift_m"]*100:+g} | {f(r["axis_R_m"],5)} | {f(r["q95"],3)} | {f(r["H_required_transport"])} | {f(r["representative_heat_MW_m2"],2)} | {f(100*r["near_LCFS_to_wall_m"],2)} | {r["samples_above_10"]}/{r["load_samples"]} |')
 lines+=['',
 'Representative heat uses a 1 mm upstream offset, lambda_q = 6 mm, SOL radiation fraction 0.5, and one-target power share 0.25. The 120 heat samples per geometry cover the full 002 assumption grid. Counts are not probabilities. The sampled maximum need not equal the true footprint maximum. Wall clearance uses the s = 0.999 surface. H is a required radiation-subtracted transport multiplier under prescribed sources and a mapped thermal-energy target; it is not predicted turbulent confinement.','',
 '## Numerical decision rule','',
 'An effect is resolved in the exploratory grid comparison only when its magnitude exceeds the sum of the candidate and baseline changes between those grids. This observed difference is not a rigorous error bound or statistical confidence interval. A promising candidate must have resolved lower representative heat, lower sampled maximum heat, valid traces, and no resolved deterioration in clearance or H.','',
 '| Shift (cm) | Heat reduction resolved | Sampled maximum lower | Clearance criterion | H criterion | Promising |',
 '|---:|---|---|---|---|---|']
 for r in s['comparisons']:
  c=r['criteria'];yn=lambda x:'YES' if x else 'NO'
  lines.append('| '+ ' | '.join([f'{100*r["shift_m"]:+g}',yn(c['representative_heat_resolved_reduction']),yn(c['maximum_sampled_heat_reduced']),yn(c['no_resolved_clearance_deterioration']),yn(c['no_resolved_H_deterioration']),yn(r['promising'])])+' |')
 if refined:
  lines+=['','Finer-grid results:']
  for r in refined:lines.append(f'- {100*r["shift_m"]:+g} cm: '+('meets' if r['promising'] else 'does not meet')+' the same comparison rule. See summary.json for each effect and refinement difference.')
 lines+=['','## Numerical recovery and failures','',
 'The recovery retains the fourth-order FreeGS operator, cut-cell current source and 1e−5 full-domain residual threshold. Newton step size, line search and accepted warm-start paths are numerical choices. Intermediate pressure/current homotopy states have different operating points and are excluded from the geometry comparison. A solver failure is not proof that no physical equilibrium exists.','',
 '| Attempt | Grid | Defect | Recorded error |','|---|---:|---:|---|']
 for r in s['failed_attempts']:lines.append(f'| {r["tag"]} | {r["grid"]} | {r["defect"] if r["defect"] is not None else "not available"} | {r["error"] or "Acceptance threshold not met"} |')
 lines+=['','## Reproduce','',
 'Use Python 3.12 and the dependency pins inherited from OPENSTEP-001. From the repository root:',
 '```sh','python -m pip install -r benchmarks/openstep-003/requirements.txt',
 '# Replay the attempts and warm-start order recorded in COMMANDS.md.',
 'python benchmarks/openstep-003/screen_sweep.py --n 129',
 'python benchmarks/openstep-003/screen_sweep.py --n 257',
 '# If a 513-grid pair is recorded, screen it with --n 513 as well.',
 'python benchmarks/openstep-003/assess.py','python benchmarks/openstep-003/verify.py',
 'python benchmarks/openstep-003/plot.py','python benchmarks/openstep-003/write_report.py','```','',
 'Each solve JSON records its exact warm-start path/hash, code hash, finite-difference parameter, line search, target values, iteration history and acceptance residual. NPZ files contain the complete fields. The screen calculations reuse the immutable 002 implementations; 001/002 inputs enforce their pinned source hashes. See artifact-manifest.json for content hashes.','',
 '## Boundaries of the result','',
 'The vertical-force slope is a rigid-current, fixed-coil, no-wall diagnostic; its sign is not a wall-coupled MHD growth rate. The heat model traces imposed upstream power to the wall and does not solve detachment or neutrals. Current and p(s) constraints do not keep shape, q, pressure integral or the mapped thermal-energy target constant.','']
 lines += ['- NOT RUN: '+x for x in s['unrun']]
 lines+=['','## Sources and snapshot preservation','',
 '- UKAEA OpenSTEP, Brown et al., [DOI 10.14468/07jt-s540](https://doi.org/10.14468/07jt-s540), pinned commit `6f66ae09c60b361d600b178416ef3f22b8d0aa6a`, CC BY 4.0.',
 '- [OPENSTEP-001](../openstep-001/README.md) and [OPENSTEP-002](../openstep-002/README.md) contain the source mapping, model equations, units and primary physics references.',
 '- Historical 001/002 package files remain unchanged. Shared root navigation is updated; historical manifests describe their original commits, including root files as they stood then.',
 '- Previous published snapshot: `37ae3ea0d58830575eb11e25b1220453ad614c78`. FreeGS 0.8.2 and the inherited boundary cache are LGPL-3.0-or-later; licenses are retained in 002. No UKAEA endorsement is implied.','']
 (ROOT/'README.md').write_text('\n'.join(lines))
 print('Generated README from recorded results')
if __name__=='__main__':main()
