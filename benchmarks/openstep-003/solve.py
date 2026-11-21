"""Fixed-p(s)/Ip continuation using the immutable 001/002 physical operator."""
from pathlib import Path
import argparse, hashlib, json, sys, time
import numpy as np
from scipy.interpolate import RectBivariateSpline, PPoly
from scipy.optimize import root
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-002'))
from controlled import Controlled, b
from cached_boundary import CachedHagenow
import critical_scope
OUT=ROOT/'results'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def name(n,shift):return f'shift-{int(round(shift*1000)):+04d}mm-{n}'

def solve(n,shift,warm,tag=None,rdiff=1e-7,line_search='armijo',maxits=60,alpha=1.):
    start=time.time();ref=b.reference();ref['cell_average']=True
    target=json.loads((b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    original=json.loads((b.ROOT/'results/baseline-129-symmetric.json').read_text())['final']
    target_span=target['psi_axis']-target['psi_boundary']
    span=(1-alpha)*(original['psi_axis']-original['psi_boundary'])+alpha*target_span
    ip=(1-alpha)*original['ip_A']+alpha*target['ip_A']
    pro=Controlled(ref,span,ip);b.profiles=lambda _:pro
    tag=tag or name(n,shift);warm=Path(warm).resolve()
    report=dict(tag=tag,grid=[n,2*n-1],p9_translation_m=shift,constraint='fixed p(s) and total Ip',
        target_ip_A=ip,target_pressure_axis_Pa=target['pressure_axis_Pa']*span/target_span,
        homotopy_alpha=alpha,rdiff=rdiff,line_search=line_search,max_iterations=maxits,
        acceptance_defect=1e-5,solver_fatol=1e-7,warm_start=str(warm.relative_to(ROOT.parent)),
        warm_sha256=sha(warm),protocol_sha256=sha(ROOT/'PROTOCOL.md'),code_sha256=sha(__file__),
        controlled_code_sha256=sha(ROOT.parent/'openstep-002/controlled.py'),
        iterations=[],converged=False,final_critical_search='original full domain')
    eq=None
    try:
        critical_scope.install();eq=b.prepare(ref,n,shift);eq._applyBoundary=CachedHagenow(eq)
        old=np.load(warm);eq._updatePlasmaPsi(RectBivariateSpline(old['r'],old['z'],old['plasma_psi'])(eq.R_1D,eq.Z_1D))
        half_shape=(n,n);calls=0
        def residual(x):
            nonlocal calls
            half=x.reshape(half_shape)*ref['span'];x=np.concatenate([half,half[:,-2::-1]],axis=1)
            eq._updatePlasmaPsi(x.copy());eq.solve(pro,psi=eq.psi())
            response=.5*(eq.plasma_psi+eq.plasma_psi[:,::-1]);calls+=1
            return ((x-response)[:,:n]/ref['span']).ravel()
        def callback(x,f):
            row=dict(iteration=len(report['iterations']),evaluations=calls,defect=float(np.max(np.abs(f))))
            report['iterations'].append(row);print(json.dumps(dict(tag=tag,**row)),flush=True)
        initial=(eq.plasma_psi[:,:n]/ref['span']).ravel().copy()
        report['initial_defect']=float(np.max(np.abs(residual(initial))))
        sol=root(residual,initial,method='krylov',callback=callback,
            options=dict(fatol=1e-7,maxiter=maxits,line_search=None if line_search=='none' else line_search,
                         jac_options=dict(rdiff=rdiff,inner_maxiter=20)))
        report['root_solver']=dict(success=bool(sol.success),message=str(sol.message),evaluations=calls)
        half=sol.x.reshape(half_shape)*ref['span'];eq._updatePlasmaPsi(np.concatenate([half,half[:,-2::-1]],axis=1))
        critical_scope.restore()
        saved=eq.plasma_psi.copy();eq.solve(pro,psi=eq.psi())
        report['final_defect']=float(np.max(np.abs(eq.plasma_psi-saved))/ref['span']);eq._updatePlasmaPsi(saved)
        pro.Jtor(eq.R,eq.Z,eq.psi());pscale,fscale=pro.pscale,pro.fscale
        scaled=dict(ref,pp=PPoly(ref['pp'].c*pscale,ref['pp'].x),ff=PPoly(ref['ff'].c*fscale,ref['ff'].x))
        report['final']=b.diagnostics(eq,scaled)
        report['pressure_derivative_scale']=pscale;report['ff_derivative_scale']=fscale
        pp=scaled['pp'].antiderivative();pp0=ref['pp'].antiderivative();ss=np.linspace(0,1,501)
        actual_span=report['final']['psi_axis']-report['final']['psi_boundary']
        report['pressure_profile_relative_error']=float(np.max(np.abs(actual_span*(pp(1)-pp(ss))-span*(pp0(1)-pp0(ss))))/report['target_pressure_axis_Pa'])
        report['current_relative_error']=abs(report['final']['ip_A']/ip-1)
        fi=scaled['ff'].antiderivative();report['F_squared_min_T2_m2']=float(np.min(11.52**2+2*actual_span*(fi(1)-fi(ss))))
        report['converged']=bool(report['final_defect']<=1e-5 and report['pressure_profile_relative_error']<=1e-9
            and report['current_relative_error']<=1e-9 and report['F_squared_min_T2_m2']>0
            and report['final']['up_down_asymmetry']<=1e-8 and np.all(np.isfinite(eq.psi())))
    except Exception as e:report['error']=f'{type(e).__name__}: {e}'
    finally:critical_scope.restore()
    report['seconds']=time.time()-start
    if eq is not None:np.savez_compressed(OUT/f'{tag}.npz',r=eq.R_1D,z=eq.Z_1D,psi=eq.psi(),plasma_psi=eq.plasma_psi)
    (OUT/f'{tag}.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['iterations','final']},indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,required=True);p.add_argument('--shift',type=float,default=0)
    p.add_argument('--warm',required=True);p.add_argument('--tag');p.add_argument('--rdiff',type=float,default=1e-7)
    p.add_argument('--line-search',choices=['armijo','none'],default='armijo');p.add_argument('--maxits',type=int,default=60);p.add_argument('--alpha',type=float,default=1)
    a=p.parse_args();r=solve(a.n,a.shift,a.warm,a.tag,a.rdiff,a.line_search,a.maxits,a.alpha)
    if not r['converged']:raise SystemExit(2)
