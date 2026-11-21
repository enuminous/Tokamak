"""Compare all recorded candidates against the frozen numerical decision rule."""
from pathlib import Path
import json,csv
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
METRICS=['axis_R_m','upper_x_R_m','upper_x_Z_m','representative_heat_MW_m2','max_sampled_heat_MW_m2','near_LCFS_to_wall_m','H_required_transport','vertical_stiffness_N_per_m','q95']

def compare(coarse,fine):
    c={r['shift_m']:r for r in coarse['rows']};f={r['shift_m']:r for r in fine['rows']};cb=c[0.];fb=f[0.];out=[]
    for shift,r in sorted(f.items()):
        if not shift:continue
        row=dict(shift_m=shift,coarse_grid=coarse['grid'],fine_grid=fine['grid'],fine=r,coarse=c.get(shift),metrics={},promising=False)
        for k in METRICS:
            effect=r[k]-fb[k] if r[k] is not None and fb[k] is not None else None
            bound=abs(r[k]-c[shift][k])+abs(fb[k]-cb[k]) if shift in c and all(v is not None for v in [r[k],c[shift][k],fb[k],cb[k]]) else None
            row['metrics'][k]=dict(fine_effect=effect,observed_refinement_sum=bound,resolved=bool(effect is not None and bound is not None and abs(effect)>bound))
        m=row['metrics'];heat=m['representative_heat_MW_m2'];H=m['H_required_transport'];clear=m['near_LCFS_to_wall_m'];maxq=m['max_sampled_heat_MW_m2']
        row['criteria']=dict(two_grids=shift in c,
            trace_quality=bool(shift in c and all(x['trace_checks_pass'] for x in [r,c[shift],fb,cb])),
            representative_heat_resolved_reduction=bool(heat['resolved'] and heat['fine_effect']<0),
            maximum_sampled_heat_reduced=bool(maxq['fine_effect'] is not None and maxq['fine_effect']<0),
            no_resolved_clearance_deterioration=bool(shift in c and not(clear['resolved'] and clear['fine_effect']<0)),
            no_resolved_H_deterioration=bool(shift in c and not(H['resolved'] and H['fine_effect']>0)))
        row['promising']=all(row['criteria'].values());out.append(row)
    return out

def main():
    grids={int(p.stem.split('-')[1]):json.loads(p.read_text()) for p in OUT.glob('screens-*.json')}
    first=compare(grids[129],grids[257]);eligible=[r for r in first if r['promising']]
    chosen=min(eligible,key=lambda r:r['fine']['representative_heat_MW_m2'])['shift_m'] if eligible else None
    refined=compare(grids[257],grids[513]) if 513 in grids else None
    failed=[dict(tag=d['tag'],grid=d['grid'][0],shift_m=d['p9_translation_m'],error=d.get('error'),defect=d.get('final_defect'))
            for p in OUT.glob('*.json') if isinstance((d:=json.loads(p.read_text())),dict) and d.get('converged') is False]
    attempts=[d for p in OUT.glob('*.json') if isinstance((d:=json.loads(p.read_text())),dict) and 'converged' in d]
    case_status=[]
    for n in [129,257]:
        for shift in [-.05,-.025,-.01,0,.01,.025,.05]:
            matching=[d for d in attempts if d['grid'][0]==n and d['p9_translation_m']==shift and d['homotopy_alpha']==1]
            status='ACCEPTED' if any(d['converged'] for d in matching) else 'UNRESOLVED' if matching else 'NOT_COMPLETED'
            case_status.append(dict(grid=n,shift_m=shift,status=status,attempts=[d['tag'] for d in matching]))
    summary=dict(experiment='OPENSTEP-003',date='2026-11-21',scope='Exploratory fixed-p(s), fixed-Ip equilibrium and reduced heat screens',
        case_status=case_status,grids=sorted(grids),rows_by_grid={str(n):d['rows'] for n,d in grids.items()},comparisons=first,
        candidate_for_refinement_m=chosen,refined_comparisons=refined,failed_attempts=failed,
        interrupted_attempts=json.loads((OUT/'interrupted-attempts.json').read_text())['attempts'],
        physical_qualification='UNRESOLVED',unrun=['Full 3-D MHD and wall/feedback stability','Predictive turbulent transport and burn','SOL detachment and neutrals','Structural, superconducting, cooling and neutron qualification'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    table=[]
    for n,d in sorted(grids.items()):
        for r in sorted(d['rows'],key=lambda r:r['shift_m']):
            table.append({k:r[k] for k in ['grid','shift_m','full_domain_defect','axis_R_m','q95','H_required_transport','vertical_stiffness_N_per_m','representative_heat_MW_m2','max_sampled_heat_MW_m2','near_LCFS_to_wall_m','samples_above_10','load_samples','trace_checks_pass']})
    with (OUT/'candidate-grid.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(candidate_for_refinement_m=chosen,comparisons=[{k:r[k] for k in ['shift_m','promising','criteria']} for r in first],failed_attempts=failed),indent=2))
if __name__=='__main__':main()
