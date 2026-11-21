"""Check restricted iterative search against full-domain core source."""
import json,numpy as np
import screens as s
import critical_scope as scope
checks=[]
for arm in ['baseline','p9-inward']:
    for n in [129,257]:
        f=s.Field(arm,n);ref=f.ref
        full=s.b.profiles(ref).Jtor(f.R,f.Z,f.psi)
        scope.install()
        try:limited=s.b.profiles(ref).Jtor(f.R,f.Z,f.psi)
        finally:scope.restore()
        error=float(np.max(abs(full-limited))/np.max(abs(full)))
        outside=(f.R<scope.BOUNDS[0])|(f.R>scope.BOUNDS[1])|(f.Z<scope.BOUNDS[2])|(f.Z>scope.BOUNDS[3])
        check=dict(arm=arm,grid=n,Jtor_relative_difference=error,source_outside_search=bool(np.any(full[outside]!=0)),passed=error<1e-9 and not np.any(full[outside]!=0));checks.append(check)
report=dict(bounds_m=scope.BOUNDS,checks=checks,passed=all(x['passed'] for x in checks));s.save('critical-search-equivalence.json',report);print(json.dumps(report,indent=2));assert report['passed']
