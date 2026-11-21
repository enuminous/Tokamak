"""Run the frozen seven-point geometry grid; only accepted fields seed a step."""
from pathlib import Path
import argparse,contextlib,json
from solve import solve,ROOT,OUT,name

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,required=True);p.add_argument('--baseline',required=True);a=p.parse_args()
    warm=Path(a.baseline).resolve();zero=name(a.n,0);manifest=[]
    if (OUT/f'{zero}.json').exists():
        r=json.loads((OUT/f'{zero}.json').read_text())
    else:
        with (OUT/f'{zero}.log').open('w') as log,contextlib.redirect_stdout(log):r=solve(a.n,0,warm)
    manifest.append(dict(tag=zero,converged=r['converged']));print(json.dumps(manifest[-1]),flush=True)
    if r['converged']:warm=OUT/f'{zero}.npz'
    for sign in [-1,1]:
        previous=warm
        for magnitude in [.01,.025,.05]:
            shift=sign*magnitude;tag=name(a.n,shift)
            if (OUT/f'{tag}.json').exists():r=json.loads((OUT/f'{tag}.json').read_text())
            else:
                with (OUT/f'{tag}.log').open('w') as log,contextlib.redirect_stdout(log):r=solve(a.n,shift,previous)
            manifest.append(dict(tag=tag,converged=r['converged']));print(json.dumps(manifest[-1]),flush=True)
            if r['converged']:previous=OUT/f'{tag}.npz'
    (OUT/f'sweep-{a.n}.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
