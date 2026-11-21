"""Hold baseline p(s) and Ip fixed while changing p9 geometry."""
from pathlib import Path
import sys,json,argparse,hashlib,time
import numpy as np
from scipy.interpolate import RectBivariateSpline
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-001'))
import benchmark as b
from cached_boundary import CachedHagenow

class Controlled(b.PreciseProfiles):
    def __init__(self,ref,span,ip):
        self.ref=ref;self.target_span=span;self.target_ip=ip;self.pscale=1.;self.fscale=1.
        super().__init__(lambda s:self.pscale*ref['pp'](s),lambda s:self.fscale*ref['ff'](s),fvac=11.52)
        self.cell_average=True
    def Jtor(self,R,Z,psi,psi_bndry=None):
        # Obtain exactly the same connected cut-cell mask as OPENSTEP-001.
        opt,xpt=b.refined_critical(R,Z,psi)
        self.pscale=self.target_span/(opt[0][2]-xpt[0][2])
        self.fscale=0.
        jp=super().Jtor(R,Z,psi,psi_bndry)
        self.pscale=0.;self.fscale=1.
        jf=super().Jtor(R,Z,psi,psi_bndry)
        da=(R[1,0]-R[0,0])*(Z[0,1]-Z[0,0])
        self.fscale=(self.target_ip-jp.sum()*da)/(jf.sum()*da)
        self.pscale=self.target_span/(self.psi_axis-self.psi_bndry)
        return jp+self.fscale*jf

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=129);p.add_argument('--shift',type=float,default=.1);p.add_argument('--warm-grid',type=int,default=257);p.add_argument('--warm-controlled',action='store_true');a=p.parse_args()
    start=time.time();ref=b.reference();ref['cell_average']=True
    target=json.loads((b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    span=target['psi_axis']-target['psi_boundary'];ip=target['ip_A']
    pro=Controlled(ref,span,ip);b.profiles=lambda _:pro
    arm='baseline' if a.shift==0 else 'p9-inward';name=f'{arm}-{a.n}-controlled';out=ROOT/'results'
    report=dict(arm=arm,grid=[a.n,2*a.n-1],constraint='fixed p(s) and total Ip',p9_translation_m=a.shift,
                target_ip_A=ip,target_pressure_axis_Pa=target['pressure_axis_Pa'],warm_grid=a.warm_grid,iterations=[],
                protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
                boundary_code_sha256=hashlib.sha256((ROOT/'cached_boundary.py').read_bytes()).hexdigest(),
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    eq=b.prepare(ref,a.n,a.shift)
    eq._applyBoundary=CachedHagenow(eq)
    warm=out/f'{arm}-{a.warm_grid}-controlled.npz' if a.warm_controlled else b.ROOT/'results'/f'{arm}-{a.warm_grid}-symmetric.npz'
    report['warm_start']=str(warm.relative_to(ROOT.parent))
    old=np.load(warm)
    eq._updatePlasmaPsi(RectBivariateSpline(old['r'],old['z'],old['plasma_psi'])(eq.R_1D,eq.Z_1D))
    try:
        report['root_solver']=b.solve_newton(eq,ref,40,report['iterations'])
        saved=eq.plasma_psi.copy();eq.solve(pro,psi=eq.psi())
        report['final_defect']=float(np.max(np.abs(eq.plasma_psi-saved))/ref['span']);eq._updatePlasmaPsi(saved)
        pro.Jtor(eq.R,eq.Z,eq.psi());pscale,fscale=pro.pscale,pro.fscale
        # Diagnostics integrate the actual scaled profile, not the original one.
        scaled=dict(ref,pp=ref['pp'].__class__(ref['pp'].c*pscale,ref['pp'].x),ff=ref['ff'].__class__(ref['ff'].c*fscale,ref['ff'].x))
        report['final']=b.diagnostics(eq,scaled);report['pressure_derivative_scale']=pscale;report['ff_derivative_scale']=fscale
        report['converged']=report['final_defect']<=1e-5
        report['current_relative_error']=abs(report['final']['ip_A']/ip-1)
        report['pressure_relative_error']=abs(report['final']['pressure_axis_Pa']/target['pressure_axis_Pa']-1)
    except Exception as e:report.update(converged=False,error=f'{type(e).__name__}: {e}')
    report['seconds']=time.time()-start
    np.savez_compressed(out/f'{name}.npz',r=eq.R_1D,z=eq.Z_1D,psi=eq.psi(),plasma_psi=eq.plasma_psi)
    (out/f'{name}.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
