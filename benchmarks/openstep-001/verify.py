"""Independent checks for import conventions and the published result bundle."""
import hashlib
import json
from pathlib import Path
import numpy as np
import h5py
from scipy.interpolate import RectBivariateSpline
from benchmark import ROOT, reference, profiles, prepare, machine, MU0


def main():
    ref=reference();ref['cell_average']=True
    checks=[]
    def check(name,condition,detail):
        checks.append(dict(name=name,status='PASS' if bool(condition) else 'FAIL',detail=detail))
    R,Z=np.meshgrid(ref['r'],ref['z'],indexing='ij')
    with h5py.File(ROOT/'source/STEP_SPP_001_EBCC_freeboundary.nc') as h:
        check('NetCDF declares DD4',h.attrs['data_dictionary_version']==b'4.0.0','COCOS17; native flux has opposite sign')
        g=h['equilibrium/0'];psi=g['time_slice.profiles_2d.psi'][()].squeeze()
        err=float(np.max(np.abs(psi+2*np.pi*ref['psi'])))
        check('Native and NetCDF flux identity',err<1e-11,err)
        s=np.linspace(0,1,256)
        for key,pp in [('dpressure_dpsi',ref['pp']),('f_df_dpsi',ref['ff'])]:
            raw=g['time_slice.profiles_1d.'+key][()].squeeze()
            relative=float(np.linalg.norm(-2*np.pi*raw-pp(s))/np.linalg.norm(pp(s)))
            check('Native and NetCDF '+key,relative<1e-10,relative)
        jp=g['time_slice.profiles_2d.j_phi'][()].squeeze()
        check('NetCDF and native current density',np.allclose(jp,ref['j'],rtol=1e-12,atol=1e-6),float(np.max(np.abs(jp-ref['j']))))
    eq=prepare(ref,65,0)
    altered=machine(ref,.1)
    for (label,a),(other,b) in zip(eq.tokamak.coils,altered.coils):
        expected=a.points.copy()
        if label.startswith('p9_'):expected[:,1]-=np.sign(expected[:,1].mean())*.1
        check(label+' controlled change',label==other and a.current==b.current and np.array_equal(expected,b.points),
              'Only p9 Z coordinates move; all currents and R coordinates fixed')
    nativevac=RectBivariateSpline(ref['r'],ref['z'],ref['vac'])(eq.R_1D,eq.Z_1D)
    coilflux=eq.psi()-eq.plasma_psi
    error=float(np.max(np.abs(coilflux-nativevac)))
    check('Explicit coils reproduce native vacuum flux',error<1e-10,error)
    original=eq.plasma_psi.copy();p=profiles(ref)
    def response(x):
        eq._updatePlasmaPsi(x.copy());eq.solve(p,psi=eq.psi());return eq.plasma_psi.copy()
    a=response(original);b=response(original)
    check('Free-boundary response is deterministic',np.array_equal(a,b),float(np.max(np.abs(a-b))))
    check('Trial field survives boundary updates',np.array_equal(original,RectBivariateSpline(ref['r'],ref['z'],ref['psi']-ref['vac'])(eq.R_1D,eq.Z_1D)), 'Regression check for root-variable aliasing')
    source_s=np.clip((ref['psi']-ref['m']['psi_axis']/(2*np.pi))/-ref['span'],0,1)
    j=R*ref['pp'](source_s)+ref['ff'](source_s)/(MU0*R);mask=ref['j']>1e3
    err=float(np.linalg.norm(j[mask]-ref['j'][mask])/np.linalg.norm(ref['j'][mask]))
    check('Published profile/current consistency',err<.001,err)
    summary=json.loads((ROOT/'results/summary.json').read_text())
    codehash=hashlib.sha256((ROOT/'benchmark.py').read_bytes()).hexdigest()
    for label,name in summary['runs'].items():
        d=json.loads((ROOT/'results'/f'{name}.json').read_text())
        check(label+' uses current solver source',d['code_sha256']==codehash,d['code_sha256'])
        check(label+' independently checked residual',d['final_defect']<=1e-5,d['final_defect'])
        field=np.load(ROOT/'results'/f'{name}.npz')
        check(label+' finite field',np.isfinite(field['psi']).all(),list(field['psi'].shape))
        x=d['final']['xpoints'][:2]
        topology=len(x)==2 and x[0][1]*x[1][1]<0 and abs(x[0][2]-x[1][2])<1e-6
        check(label+' double-null topology',topology,x)
        integral=ref['ff'].antiderivative();dpsi=d['final']['psi_axis']-d['final']['psi_boundary']
        f2=11.52**2+2*dpsi*(integral(1)-integral(np.linspace(0,1,1025)))
        check(label+' real toroidal field',f2.min()>0,float(f2.min()))
    result=dict(status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',checks=checks)
    (ROOT/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
