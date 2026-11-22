"""Cache spline derivatives, preserving the original spline coefficients/model."""
import json
import numpy as np
from common import ROOT, FrozenField, Wall, inventory, stamp, save, check
from contour import trace, assess_difference, compare


class CachedField(FrozenField):
    def __init__(self, path):
        super().__init__(path)
        self.dr = self.sp.partial_derivative(1, 0)
        self.dz = self.sp.partial_derivative(0, 1)

    def grad(self, xy):
        xy = np.asarray(xy)
        return np.stack([self.dr(xy[...,0],xy[...,1],grid=False),
                         self.dz(xy[...,0],xy[...,1],grid=False)],axis=-1)

    def bpol(self, r, z):
        return -self.dz(r,z,grid=False)/r, self.dr(r,z,grid=False)/r


def main():
    result, checks, rows = stamp('derivative_cache_validation'), [], []
    original=json.loads((ROOT/'results/contours.json').read_text())
    assert original['completed'], 'Original uncached trace stage must complete first'
    rng=np.random.default_rng(5006)
    for path,_ in inventory():
        field=CachedField(path)
        points=np.column_stack([rng.uniform(field.r[0],field.r[-1],4096),
                                rng.uniform(field.z[0],field.z[-1],4096)])
        # Include all saved spline-grid intersections in one vectorized call.
        r,z=np.meshgrid(field.r,field.z,indexing='ij')
        points=np.vstack([points,np.column_stack([r.ravel(),z.ravel()])])
        expected=FrozenField.grad(field,points)
        cached=field.grad(points)
        delta=float(np.max(abs(expected-cached)))
        check(checks,field.arm+':gradient_cache',delta <= 1e-12,delta,1e-12)
        br,bz=field.bpol(points[:,0],points[:,1])
        ebr,ebz=FrozenField.bpol(field,points[:,0],points[:,1])
        delta=float(max(np.max(abs(br-ebr)),np.max(abs(bz-ebz))))
        check(checks,field.arm+':field_cache',delta <= 1e-12,delta,1e-12)
        row,_=trace(field,Wall(),.001,tight=True)
        old=next(r for r in original['rows'] if r['tag']==field.arm and r['offset_m']==.001 and r['tight'] and r['direction']==1)
        difference=compare(row,old)
        assess_difference(checks,field.arm+':cached_uncached_trace',difference)
        rows.append(dict(tag=field.arm,points_compared=len(points),cached_seconds=row['seconds'],
                         original_seconds=old['seconds'],**difference))
    result.update(checks=checks,rows=rows,seed=5006)
    save('derivative-cache.json',result)
    print(json.dumps({s:sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}),flush=True)
    if any(c['status']=='FAIL' for c in checks):
        raise SystemExit(1)


if __name__=='__main__':
    main()
