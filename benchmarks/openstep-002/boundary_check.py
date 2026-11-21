"""Compare cached and original operators on published and perturbed sources."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'openstep-001'))
import benchmark as b
from cached_boundary import CachedHagenow
ref=b.reference();ref['cell_average']=True;eq=b.prepare(ref,129);cache=CachedHagenow(eq)
j=b.profiles(ref).Jtor(eq.R,eq.Z,eq.psi());checks=[]
for tag,current in [('physical',j),('asymmetric',j*(1+.03*eq.Z))]:
    u=eq.plasma_psi.copy();v=u.copy()
    b.freegs.boundary.freeBoundaryHagenow(eq,current,u);cache(eq,current,v)
    err=float(np.max(abs(u-v)));checks.append(dict(source=tag,max_absolute_difference=err,passed=err<1e-10))
report=dict(checks=checks,passed=all(x['passed'] for x in checks),criterion=1e-10)
(ROOT/'results/boundary-equivalence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert report['passed']
