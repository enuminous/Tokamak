"""Independent inward continuation while the outward branch completes."""
from pathlib import Path
import argparse,contextlib,json
from solve import solve,ROOT,OUT

def main():
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,required=True);p.add_argument('--baseline',required=True);a=p.parse_args()
 warm=Path(a.baseline).resolve();rows=[]
 selection=OUT/f'selection-{a.n}.json'
 choices=json.loads(selection.read_text()) if selection.exists() else {}
 for shift in [.01,.025,.05]:
  tag=f'inward-{int(round(1000*shift)):03d}mm-{a.n}'
  with (OUT/f'{tag}.log').open('w') as log,contextlib.redirect_stdout(log):r=solve(a.n,shift,warm,tag=tag)
  rows.append(dict(tag=tag,converged=r['converged']));print(json.dumps(rows[-1]),flush=True)
  if r['converged']:
   warm=OUT/f'{tag}.npz';choices[str(shift)]=tag
   selection.write_text(json.dumps(choices,indent=2)+'\n')
 (OUT/f'inward-sweep-{a.n}.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
