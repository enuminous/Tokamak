"""Bounded continuation fallback; stop a path at its first unaccepted stage."""
from pathlib import Path
import argparse,contextlib,json
from solve import solve,ROOT,OUT

def main():
    p=argparse.ArgumentParser();p.add_argument('path',choices=['operating-point','geometry']);a=p.parse_args()
    if a.path=='operating-point':
        warm=ROOT.parent/'openstep-001/results/baseline-129-symmetric.npz'
        stages=[(0,k/10,f'recovery-homotopy-{k:02d}') for k in range(11)]
    else:
        warm=ROOT.parent/'openstep-002/results/p9-inward-129-controlled.npz'
        stages=[(shift,1,f'recovery-geometry-{int(round(shift*1000)):03d}mm') for shift in [.075,.05,.025,.01,0]]
    rows=[]
    for shift,alpha,tag in stages:
        with (OUT/f'{tag}.log').open('w') as log,contextlib.redirect_stdout(log):r=solve(129,shift,warm,tag=tag,alpha=alpha)
        rows.append(dict(tag=tag,converged=r['converged'],alpha=alpha,shift=shift,defect=r.get('final_defect')))
        print(json.dumps(rows[-1]),flush=True)
        if not r['converged']:break
        warm=OUT/f'{tag}.npz'
    (OUT/f'recovery-path-{a.path}.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
