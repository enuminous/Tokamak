"""Trace the frozen 1 mm launch using two tolerances and the three-component wall."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parent; BENCH=ROOT.parent
sys.path.insert(0,str(BENCH/'openstep-004'))
import validate as v

def read_field(r,z,psi,axis_r,psi_axis,psi_sep,tag):
    """Use the solver's own axis and separatrix to locate its outboard launch."""
    class Field:
        def bpol(self,R,Z):
            return -self.sp.ev(R,Z,dy=1)/R,self.sp.ev(R,Z,dx=1)/R
    f=Field()
    f.r=np.array(r); f.z=np.array(z); f.n=len(r); f.arm=tag
    if psi.shape!=(len(r),len(z)) or not np.isfinite(psi).all() or not all(np.all(np.diff(x)>0) for x in (r,z)):
        raise ValueError('Expected finite R-major flux on an increasing rectangular grid')
    f.sp=RectBivariateSpline(r,z,psi)
    f.span=float(psi_axis-psi_sep)
    # Same axis-to-6.5 m bracket as OPENSTEP-001 and both reconstructed grids.
    bound=brentq(lambda R:float(f.sp.ev(R,0)-psi_sep),axis_r,6.5)
    f.d={'midplane_radii_m':[None,bound]}
    return f

def measure(f, include_heat=True):
    wall=v.Wall(v.s.walls())
    power=json.loads((BENCH/'openstep-002/results/kinetic-inputs.json').read_text())['P_transport_W']
    rows=[]
    for tighten in (False,True):
        row,_=v.trace(f,wall,.001,tight=tighten)
        row['representative_heat_MW_m2']=v.heat(row,f,power) if include_heat else None
        row['signed_corner_m']=None
        if row['component']==0 and row['segment'] in (12,13):
            RZ=np.array([row['R_target_m'],row['Z_target_m']]);vertex=wall.shapes[0][13]
            row['signed_corner_m']=float(np.linalg.norm(RZ-vertex))*(-1 if row['segment']==12 else 1)
        rows.append(row)
    move=float(np.hypot(rows[0]['R_target_m']-rows[1]['R_target_m'],rows[0]['Z_target_m']-rows[1]['Z_target_m']))
    dl=abs(rows[0]['connection_length_m']-rows[1]['connection_length_m'])
    ok=all(x['success'] and x['hit'] and not x['domain_exit'] and x['Z_target_m']<0 and x['normalized_flux_drift']<=1e-5 and x['wall_distance_m']<=1e-9 for x in rows) and move<=.001 and dl<=.01 and rows[0]['segment']==rows[1]['segment']
    return dict(rows=rows,trace_gates_pass=bool(ok),tightening_delta_RZ_m=move,tightening_delta_length_m=dl,launch_R_m=f.d['midplane_radii_m'][1]+.001)

def main():
    p=argparse.ArgumentParser();p.add_argument('case');args=p.parse_args()
    files={'baseline-coarse':BENCH/'openstep-003/results/recovery-homotopy-10','baseline-fine':BENCH/'openstep-003/results/shift-+000mm-257','inward-fine':BENCH/'openstep-003/results/inward-050mm-257','inward-coarse-A':ROOT/'results/coarse-A','inward-coarse-B':ROOT/'results/coarse-B','inward-coarse-C':ROOT/'results/coarse-C'}
    if args.case=='released-Fiesta-baseline':
        ref=v.b.reference();m=ref['m'];r,z=ref['r'],ref['z'];psi=ref['psi']
        axis,xx=v.b.refined_critical(*np.meshgrid(r,z,indexing='ij'),psi)
        f=read_field(r,z,psi,axis[0][0],m['psi_axis']/(2*np.pi),m['psi_boundary']/(2*np.pi),args.case)
        source=BENCH/'openstep-001/source/equilibrium.mat'
    else:
        path=files[args.case];source=path.with_suffix('.npz')
        f=v.Field(source)
    result=measure(f);result.update(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),case=args.case)
    (ROOT/'results'/f'trace-{args.case}.json').write_text(json.dumps(result,indent=2)+'\n')
    x=result['rows'][-1];print(args.case,result['trace_gates_pass'],x['segment'],x['signed_corner_m'],x['representative_heat_MW_m2'],flush=True)
if __name__=='__main__':main()
