"""Replay the recovered coarse field with the original uncached FreeGS boundary."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'openstep-002'))
from controlled import Controlled,b

def main():
    path=ROOT/'results/recovery-homotopy-10.npz';d=np.load(path);ref=b.reference()
    target=json.loads((b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    span=target['psi_axis']-target['psi_boundary'];pro=Controlled(ref,span,target['ip_A'])
    eq=b.prepare(ref,129,0);saved=d['plasma_psi'].copy();eq._updatePlasmaPsi(saved.copy())
    eq.solve(pro,psi=eq.psi());defect=float(np.max(abs(eq.plasma_psi-saved))/ref['span'])
    result=dict(field_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),original_FreeGS_defect=defect,
        accepted=defect<=1e-5,threshold=1e-5,operator='FreeGS 0.8.2 original uncached von Hagenow boundary and full-domain critical search')
    (ROOT/'results/recovery-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['accepted']:raise SystemExit(1)
if __name__=='__main__':main()
