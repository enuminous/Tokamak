"""Reproduce OpenSTEP using published profiles and fixed circuit currents.

Source data: Brown et al., OpenSTEP, DOI 10.14468/07jt-s540, CC BY 4.0.
FreeGS is an unmodified LGPL-3.0-or-later dependency. See PROTOCOL.md.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np
from scipy.io import loadmat
from scipy.interpolate import PPoly, RectBivariateSpline
from scipy.optimize import root, brentq
from scipy.ndimage import binary_dilation
import freegs
from freegs import critical
from freegs.filament_coil import FilamentCoil
from freegs.machine import Machine
from freegs.jtor import ProfilesPprimeFfprime

ROOT = Path(__file__).resolve().parent
MU0 = 4e-7 * np.pi
SOURCE_HASHES = {
    'coilset.mat': '7587fc76b5f7e14d7ac966d9cfd2504cbc212bea80aa5931cebad984c4e4066f',
    'equilibrium.mat': 'c06780bd75cde1dce793d6b4ec778869c8a6ef0e79ccd976e87522cbcef756e9',
    'STEP_SPP_001_EBCC_freeboundary.nc': 'b2391ae94b6a9c696d8bbb27b91999f6c93c8664afc06471cb889024146751a4',
}


def reference():
    for filename, digest in SOURCE_HASHES.items():
        assert hashlib.sha256((ROOT/'source'/filename).read_bytes()).hexdigest() == digest, filename
    m = loadmat(ROOT/'source/equilibrium.mat', simplify_cells=True)['equil']
    c = loadmat(ROOT/'source/coilset.mat', simplify_cells=True)['coilset']
    r, z = m['grid']['r'], m['grid']['z']
    shape = (len(z), len(r))
    psi = m['Psi']['data'].reshape(shape, order='F').T / (2*np.pi)
    vac = m['Psi_vac']['data'].reshape(shape, order='F').T / (2*np.pi)
    j = m['I']['data'].reshape(shape, order='F').T / ((r[1]-r[0])*(z[1]-z[0]))
    alpha = m['jprofile']['alpha']
    beta = m['jprofile']['beta']
    scale = m['jprofile']['scale']
    pp = PPoly(alpha['coefs'].T * scale, alpha['breaks'])
    ff = PPoly(beta['coefs'].T * scale, beta['breaks'])
    return dict(m=m, c=c, r=r, z=z, psi=psi, vac=vac, j=j,
                pp=pp, ff=ff, ip=float(m['jprofile']['fiesta_jprofile']['normalisation']),
                span=float((m['psi_axis']-m['psi_boundary'])/(2*np.pi)))


def machine(ref, shift=0):
    coils = []
    for circuit, current in zip(ref['c']['circuits'], ref['m']['icoil']['currents']):
        for co, polarity in zip(circuit['coils'], circuit['polarity']):
            f = co['fiesta_filament']
            assert np.allclose(f['turns'], 1/len(f['r']), rtol=0, atol=1e-14)
            z = np.array(f['z'], copy=True)
            if circuit['label'] == 'p9':
                z -= np.sign(z.mean()) * shift
            coils.append((co['label'], FilamentCoil(Rfil=f['r'], Zfil=z,
                         current=float(current*polarity), turns=1, control=False)))
    return Machine(coils)


def refined_critical(R, Z, psi):
    opt,xpt=critical.find_critical(R,Z,psi)
    spline=RectBivariateSpline(R[:,0],Z[0,:],psi)
    def refine(point):
        sol=root(lambda v:[spline.ev(*v,dx=1),spline.ev(*v,dy=1)],point[:2],tol=1e-10)
        if not sol.success and np.linalg.norm(sol.fun)>1e-9:
            raise RuntimeError('Critical-point refinement failed')
        return (float(sol.x[0]),float(sol.x[1]),float(spline.ev(*sol.x)))
    return [refine(p) for p in opt],[refine(p) for p in xpt]


class PreciseProfiles(ProfilesPprimeFfprime):
    """Same published profiles, with roots refined beyond FreeGS's 1 mT cutoff."""
    def Jtor(self,R,Z,psi,psi_bndry=None):
        opt,xpt=refined_critical(R,Z,psi)
        if not opt or not xpt:
            raise ValueError('Missing magnetic axis or separatrix X-point')
        self.psi_axis=opt[0][2]
        self.psi_bndry=xpt[0][2] if psi_bndry is None else psi_bndry
        mask=critical.core_mask(R,Z,psi,opt,xpt,self.psi_bndry)
        s=np.clip((psi-self.psi_axis)/(self.psi_bndry-self.psi_axis),0,1)
        if getattr(self,'cell_average',False):
            raw=(psi-self.psi_axis)/(self.psi_bndry-self.psi_axis)
            sr,sz=np.gradient(raw,R[:,0],Z[0,:],edge_order=2)
            a=np.abs(sr)*(R[1,0]-R[0,0])/2
            b=np.abs(sz)*(Z[0,1]-Z[0,0])/2
            hi=np.maximum(a,b);lo=np.minimum(a,b);t=1-raw
            hi=np.maximum(hi,1e-14);lo=np.maximum(lo,1e-14)
            frac=np.where(t < -hi+lo,(t+hi+lo)**2/(8*hi*lo),
                          np.where(t>hi-lo,1-(hi+lo-t)**2/(8*hi*lo),(t+hi)/(2*hi)))
            frac=np.where(t<=-hi-lo,0,np.where(t>=hi+lo,1,frac))
            # Exclude disconnected/private flux; include cut cells next to the core.
            mask=np.clip(frac,0,1)*binary_dilation(mask.astype(bool),iterations=1)
        return mask*(R*self.pprime(s)+self.ffprime(s)/(MU0*R))


def profiles(ref):
    p=PreciseProfiles(ref['pp'], ref['ff'], fvac=11.52)
    p.cell_average=ref.get('cell_average',False)
    return p


def prepare(ref, n, shift=0):
    r = np.linspace(.5, 9., n)
    z = np.linspace(-10., 10., 2*n-1)
    initial = RectBivariateSpline(ref['r'],ref['z'],ref['psi']-ref['vac'])(r,z)
    eq = freegs.Equilibrium(machine(ref, shift), Rmin=.5,Rmax=9.,Zmin=-10.,Zmax=10.,
                           nx=n,ny=2*n-1,psi=initial,
                           boundary=freegs.boundary.freeBoundaryHagenow,order=4)
    return eq


def diagnostics(eq, ref):
    psi = eq.psi()
    opt, xpt = refined_critical(eq.R, eq.Z, psi)
    core = critical.core_mask(eq.R, eq.Z, psi, opt, xpt).astype(bool)
    target = RectBivariateSpline(ref['r'],ref['z'],ref['psi'])(eq.R_1D,eq.Z_1D)
    published_j = RectBivariateSpline(ref['r'],ref['z'],ref['j'])(eq.R_1D,eq.Z_1D)
    mask = published_j > 1e3
    difference = psi-target
    gauge = np.mean(difference[mask])
    p = profiles(ref)
    j = p.Jtor(eq.R,eq.Z,psi)
    dA = eq.dR*eq.dZ
    # Exact antiderivatives of the published piecewise-cubic functions.
    s = np.clip((psi-p.psi_axis)/(p.psi_bndry-p.psi_axis),0,1)
    ppint = ref['pp'].antiderivative()
    pressure = (ppint(1)-ppint(s))*(p.psi_axis-p.psi_bndry)*core
    spline = RectBivariateSpline(eq.R_1D,eq.Z_1D,psi)
    def refine(point):
        sol=root(lambda v: [spline.ev(*v,dx=1),spline.ev(*v,dy=1)],point[:2],tol=1e-10)
        assert sol.success or np.linalg.norm(sol.fun)<1e-9
        return [float(sol.x[0]),float(sol.x[1]),float(spline.ev(*sol.x))]
    refined_axis=refine(opt[0]); refined_x=[refine(pt) for pt in xpt]
    boundary=refined_x[0][2]
    mid=lambda rr: spline.ev(rr,0)-boundary
    midplane=[brentq(mid,1.1,refined_axis[0]),brentq(mid,refined_axis[0],6.5)]
    return dict(axis=refined_axis,xpoints=refined_x,
                ip_A=float(j.sum()*dA),core_area_m2=float(core.sum()*dA),
                core_volume_m3=float((core*2*np.pi*eq.R).sum()*dA),
                pressure_integral_J=float((pressure*2*np.pi*eq.R).sum()*dA),
                pressure_axis_Pa=float((ppint(1)-ppint(0))*(p.psi_axis-p.psi_bndry)),
                core_flux_nrmse=float(np.sqrt(np.mean((difference[mask]-gauge)**2))/ref['span']),
                gauge_offset_Wb_per_rad=float(gauge),
                midplane_radii_m=midplane,
                psi_axis=float(p.psi_axis),psi_boundary=float(p.psi_bndry),
                up_down_asymmetry=float(np.max(np.abs(psi-psi[:,::-1]))))


def solve_picard(eq, ref, maxits=240, blend=.8, log=None):
    p = profiles(ref)
    log = [] if log is None else log
    for it in range(maxits):
        old = eq.plasma_psi.copy()
        total = eq.psi()
        eq.solve(p, psi=total)
        new = .5*(eq.plasma_psi+eq.plasma_psi[:,::-1])
        defect = float(np.max(np.abs(new-old))/ref['span'])
        row = dict(iteration=it,defect=defect,ip_A=float(eq.plasmaCurrent()))
        log.append(row)
        if it%5==0: print(json.dumps(row),flush=True)
        if not np.isfinite(defect) or defect>1e3:
            raise ValueError('Nonfinite or runaway flux defect')
        if defect<=1e-5:
            eq._updatePlasmaPsi(new)
            return log
        eq._updatePlasmaPsi(blend*old+(1-blend)*new)
    return log


def solve_newton(eq, ref, maxits, log):
    """Root of the full free-boundary plasma response; coil currents stay fixed."""
    p=profiles(ref)
    half_shape=(eq.nx,(eq.ny+1)//2)
    span=ref['span']
    calls=0
    def residual(x):
        nonlocal calls
        half=x.reshape(half_shape)*span
        x=np.concatenate([half,half[:,-2::-1]],axis=1)
        # FreeGS writes boundary values into its input plasma array in place.
        # Keep the root variable intact when forming x - response(x).
        eq._updatePlasmaPsi(x.copy())
        eq.solve(p,psi=eq.psi())
        response=.5*(eq.plasma_psi+eq.plasma_psi[:,::-1])
        calls+=1
        return ((x-response)[:,:half_shape[1]]/span).ravel()
    def callback(x,f):
        row=dict(iteration=len(log),evaluations=calls,defect=float(np.max(np.abs(f))))
        log.append(row)
        print(json.dumps(row),flush=True)
    solution=root(residual,(eq.plasma_psi[:,:half_shape[1]]/span).ravel(),method='krylov',callback=callback,
                  options=dict(fatol=1e-5,maxiter=maxits,line_search='armijo',
                               jac_options=dict(rdiff=1e-5,inner_maxiter=15)))
    half=solution.x.reshape(half_shape)*span
    eq._updatePlasmaPsi(np.concatenate([half,half[:,-2::-1]],axis=1))
    return dict(success=bool(solution.success),message=str(solution.message),evaluations=calls)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--n',type=int,default=65)
    parser.add_argument('--shift',type=float,default=0)
    parser.add_argument('--maxits',type=int,default=240)
    parser.add_argument('--tag',default='')
    parser.add_argument('--method',choices=['picard','newton'],default='picard')
    parser.add_argument('--edge',choices=['hard','cell'],default='hard')
    args=parser.parse_args()
    start=time.time(); ref=reference();ref['cell_average']=args.edge=='cell'
    eq=prepare(ref,args.n,args.shift)
    print('Prepared',args.n,args.shift,'seconds',time.time()-start,flush=True)
    out=ROOT/'results';out.mkdir(exist_ok=True)
    name=f"{'baseline' if args.shift==0 else 'p9-inward'}-{args.n}{args.tag}"
    report=dict(grid=[args.n,2*args.n-1],p9_translation_m=args.shift,method=args.method,
                max_iterations=args.maxits,blend=.8,edge=args.edge,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest())
    try:
        report['initial']=diagnostics(eq,ref)
        report['iterations']=[]
        if args.method=='picard':
            solve_picard(eq,ref,args.maxits,log=report['iterations'])
        else:
            report['root_solver']=solve_newton(eq,ref,args.maxits,report['iterations'])
        report['final']=diagnostics(eq,ref)
        saved=eq.plasma_psi.copy()
        eq.solve(profiles(ref),psi=eq.psi())
        report['final_defect']=float(np.max(np.abs(eq.plasma_psi-saved))/ref['span'])
        eq._updatePlasmaPsi(saved)
        report['converged']=report['final_defect']<=1e-5
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}'
        report['converged']=False
    report['seconds']=time.time()-start
    np.savez_compressed(out/f'{name}.npz',r=eq.R_1D,z=eq.Z_1D,psi=eq.psi(),plasma_psi=eq.plasma_psi)
    (out/f'{name}.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
