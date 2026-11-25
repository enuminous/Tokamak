"""Re-evaluate the new accepted field with the uncached free-boundary operator."""
from pathlib import Path
import json,sys,numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-004'))
import validate as v
def check():
    f=v.Field(ROOT/'results/coarse-B.npz');ref=v.b.reference()
    target=json.loads((v.b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    span=target['psi_axis']-target['psi_boundary']
    eq=v.b.prepare(ref,129,.05);assert eq._applyBoundary.__name__=='freeBoundaryHagenow'
    diffs=[]
    for plasma in [f.plasma, f.plasma+.01*ref['span']*np.exp(-((f.R-4)**2+f.Z**2)/.5)]:
        eq._updatePlasmaPsi(plasma.copy())
        eq.solve(v.Controlled(ref,span,target['ip_A']),psi=eq.psi())
        diffs.append(float(np.max(abs(eq.plasma_psi-plasma))/ref['span']))
    result=dict(operator='uncached freeBoundaryHagenow',saved_field_defect=diffs[0],perturbed_field_defect=diffs[1],threshold=1e-5,passed=diffs[0]<=1e-5<diffs[1])
    print(result);(ROOT/'results/uncached.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
if __name__=='__main__':check()
