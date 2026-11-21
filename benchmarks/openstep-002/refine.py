"""Grid extension; immutable OPENSTEP-001 functions supply the physics."""
from pathlib import Path
import sys, argparse, json, hashlib, time
import numpy as np
from scipy.interpolate import RectBivariateSpline
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-001'))
import benchmark as b
from cached_boundary import CachedHagenow
import critical_scope

def main():
    a=argparse.ArgumentParser();a.add_argument('--shift',type=float,default=0);a.add_argument('--n',type=int,default=513)
    args=a.parse_args();start=time.time();ref=b.reference();ref['cell_average']=True
    arm='baseline' if args.shift==0 else 'p9-inward'
    name=f'{arm}-{args.n}-symmetric';out=ROOT/'results'
    report=dict(arm=arm,grid=[args.n,2*args.n-1],p9_translation_m=args.shift,
                protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
                boundary_code_sha256=hashlib.sha256((ROOT/'cached_boundary.py').read_bytes()).hexdigest(),
                iterative_critical_search_bounds_m=critical_scope.BOUNDS,
                final_critical_search='original full domain',
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),iterations=[])
    eq=None
    try:
        critical_scope.install()
        eq=b.prepare(ref,args.n,args.shift)
        eq._applyBoundary=CachedHagenow(eq)
        old=np.load(b.ROOT/'results'/f'{arm}-257-symmetric.npz')
        eq._updatePlasmaPsi(RectBivariateSpline(old['r'],old['z'],old['plasma_psi'])(eq.R_1D,eq.Z_1D))
        print('Prepared',name,'seconds',time.time()-start,flush=True)
        report['root_solver']=b.solve_newton(eq,ref,40,report['iterations'])
        critical_scope.restore()
        print('Checking with original full-domain critical search',flush=True)
        report['final']=b.diagnostics(eq,ref)
        saved=eq.plasma_psi.copy();eq.solve(b.profiles(ref),psi=eq.psi())
        report['final_defect']=float(np.max(np.abs(eq.plasma_psi-saved))/ref['span'])
        eq._updatePlasmaPsi(saved);report['converged']=report['final_defect']<=1e-5
    except Exception as e:
        report.update(converged=False,error=f'{type(e).__name__}: {e}')
    finally:
        critical_scope.restore()
    report['seconds']=time.time()-start
    if eq is not None:
        np.savez_compressed(out/f'{name}.npz',r=eq.R_1D,z=eq.Z_1D,psi=eq.psi(),plasma_psi=eq.plasma_psi)
    (out/f'{name}.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
