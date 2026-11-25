"""Run the frozen attempts and retain the unmodified parent solver's raw reports and fields."""
from pathlib import Path
import argparse, sys, json
ROOT=Path(__file__).resolve().parent
B=ROOT.parent
sys.path.insert(0,str(B/'openstep-003'))
import solve
trial=argparse.ArgumentParser()
trial.add_argument('seed',choices=['A','B','C'])
key=trial.parse_args().seed
out=ROOT/'results'
seeds={'A':B/'openstep-003/results/inward-050mm-257.npz','B':B/'openstep-002/results/p9-inward-129-controlled.npz'}
if key=='C':
 reports=[json.loads((out/f'coarse-{s}.json').read_text()) for s in ('A','B')]
 if any(r['converged'] for r in reports):raise SystemExit('C is only scheduled if both primary attempts reject')
 choices=[out/'coarse-A.json',out/'coarse-B.json',B/'openstep-003/results/inward-050mm-129.json']
 valid=[p for p in choices if json.loads(p.read_text()).get('final_defect') is not None]
 seeds['C']=min(valid,key=lambda p:json.loads(p.read_text())['final_defect']).with_suffix('.npz')
solve.OUT=out
res=solve.solve(129,.05,seeds[key],f'coarse-{key}',rdiff=1e-5 if key=='C' else 1e-7)
raise SystemExit(0 if res['converged'] else 2)
