"""Apply the unchanged 002 diagnostic and exhaust models to the constrained grid."""
from pathlib import Path
import argparse,json,sys,time,hashlib
import numpy as np
from scipy.interpolate import RectBivariateSpline,PPoly
from shapely.geometry import LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-002'))
import screens as s
b=s.b;s.OUT=ROOT/'results';OUT=s.OUT

class Field(s.Field):
    def __init__(self,path):
        self.report=json.loads(path.with_suffix('.json').read_text());assert self.report['converged']
        d=np.load(path);self.r=d['r'];self.z=d['z'];self.psi=d['psi'];self.plasma=d['plasma_psi']
        self.R,self.Z=np.meshgrid(self.r,self.z,indexing='ij');self.n=len(self.r);self.arm=path.stem;self.controlled=True
        self.ref=b.reference();self.ref['cell_average']=True
        self.pp=PPoly(self.ref['pp'].c*self.report['pressure_derivative_scale'],self.ref['pp'].x)
        self.ff=PPoly(self.ref['ff'].c*self.report['ff_derivative_scale'],self.ref['ff'].x)
        self.sp=RectBivariateSpline(self.r,self.z,self.psi);self.psp=RectBivariateSpline(self.r,self.z,self.plasma)
        self.vsp=RectBivariateSpline(self.r,self.z,self.psi-self.plasma)
        self.axis,self.xpoints=b.refined_critical(self.R,self.Z,self.psi);self.axis=self.axis[0]
        self.pa=self.axis[2];self.pb=self.xpoints[0][2];self.span=self.pa-self.pb
        p=b.PreciseProfiles(self.pp,self.ff,fvac=11.52);p.cell_average=True;self.j=p.Jtor(self.R,self.Z,self.psi)
        self.core=b.critical.core_mask(self.R,self.Z,self.psi,[self.axis],self.xpoints).astype(bool)
        self.s=np.clip((self.pa-self.psi)/self.span,0,1);self.da=(self.r[1]-self.r[0])*(self.z[1]-self.z[0]);self.d=self.report['final']

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,required=True);a=p.parse_args();start=time.time()
    paths=list(OUT.glob(f'shift-*-{a.n}.json'));reports=[json.loads(p.read_text()) for p in paths]
    by_shift={r['p9_translation_m']:p.with_suffix('.npz') for p,r in zip(paths,reports) if r['converged']}
    selections=OUT/f'selection-{a.n}.json'
    if selections.exists():
        for shift,tag in json.loads(selections.read_text()).items():
            chosen=OUT/f'{tag}.npz';d=json.loads(chosen.with_suffix('.json').read_text())
            assert d['converged'] and d['homotopy_alpha']==1 and d['p9_translation_m']==float(shift)
            by_shift[float(shift)]=chosen
    accepted=list(by_shift.values())
    accepted.sort(key=lambda p:(0 if json.loads(p.with_suffix('.json').read_text())['p9_translation_m']==0 else 1,json.loads(p.with_suffix('.json').read_text())['p9_translation_m']))
    fingerprint=dict(code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inherited_screens_sha256=hashlib.sha256(Path(s.__file__).read_bytes()).hexdigest(),
        fields=[dict(path=str(p.relative_to(ROOT.parent)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),report_sha256=hashlib.sha256(p.with_suffix('.json').read_bytes()).hexdigest()) for p in accepted])
    cached=OUT/f'screens-{a.n}.json'
    if cached.exists() and json.loads(cached.read_text()).get('input_fingerprint')==fingerprint:
        print('Reusing unchanged accepted-field screens',a.n,flush=True);return
    fields=[Field(p) for p in accepted]
    assert fields and fields[0].report['p9_translation_m']==0,'Accepted same-grid baseline required'
    kin=json.loads((ROOT.parent/'openstep-002/results/kinetic-inputs.json').read_text())
    wall=unary_union([LineString(w) for w in s.walls()]);rows=[]
    confinement=s.confinement(fields,kin)
    for f,energy in zip(fields,confinement['central']):
        mag=s.magnetic(f);vert=s.vertical(f)
        row=dict(tag=f.arm,grid=a.n,shift_m=f.report['p9_translation_m'],axis_R_m=f.axis[0],
            upper_x_R_m=max(f.xpoints,key=lambda x:x[1])[0],upper_x_Z_m=max(f.xpoints,key=lambda x:x[1])[1],
            current_A=f.d['ip_A'],pressure_axis_Pa=f.d['pressure_axis_Pa'],pressure_integral_J=f.d['pressure_integral_J'],
            near_LCFS_to_wall_m=float(LineString(f.surface(.999)).distance(wall)),
            vertical_stiffness_N_per_m=vert['translations'][0]['dFz_dz_N_per_m'],
            H_required_transport=energy['H_required_transport'],q95=mag['q95'],magnetic=mag,vertical=vert,
            full_domain_defect=f.report['final_defect'],seconds_solve=f.report['seconds'])
        rows.append(row);print('Screened magnetic',f.arm,flush=True)
    exhaust=s.exhaust(fields,kin)
    import csv
    loads=list(csv.DictReader((OUT/f'heat-load-sweep-{a.n}.csv').open()))
    traces=list(csv.DictReader((OUT/f'fieldline-traces-{a.n}.csv').open()))
    for row in rows:
        ll=[x for x in loads if x['arm']==row['tag']];tt=[x for x in traces if x['arm']==row['tag']]
        central=[x for x in ll if float(x['offset_m'])==.001 and float(x['lambda_q_m'])==.006 and float(x['SOL_radiation_fraction'])==.5 and float(x['power_fraction_one_target'])==.25]
        row['representative_heat_MW_m2']=float(central[0]['projected_heat_MW_m2']) if central else None
        row['max_sampled_heat_MW_m2']=max(float(x['projected_heat_MW_m2']) for x in ll) if ll else None
        row['load_samples']=len(ll);row['samples_above_10']=sum(x['above_10_MW_m2']=='True' for x in ll)
        row['wall_hits']=sum(x['hit']=='True' for x in tt);row['trace_count']=len(tt)
        row['max_flux_drift']=max(float(x['normalized_flux_drift']) for x in tt)
        position=[];length=[]
        for offset in [.001,.002,.005,.01,.02]:
            pair=[x for x in tt if float(x['upstream_offset_m'])==offset]
            if len(pair)!=2 or any(x['hit']!='True' for x in pair):continue
            a1,a2=pair
            position.append(float(np.hypot(float(a1['R_target_m'])-float(a2['R_target_m']),float(a1['Z_target_m'])-float(a2['Z_target_m']))))
            length.append(abs(float(a1['connection_length_m'])-float(a2['connection_length_m'])))
        row['max_step_halving_position_m']=max(position) if position else None
        row['max_step_halving_length_m']=max(length) if length else None
        row['trace_checks_pass']=bool(row['wall_hits']==10 and row['max_flux_drift']<=1e-5 and len(position)==5 and max(position)<=.001 and max(length)<=.01)
    result=dict(grid=fields[0].n,accepted=len(fields),planned_geometries=7,input_fingerprint=fingerprint,rows=rows,confinement=confinement,
                exhaust=exhaust,seconds=time.time()-start)
    s.save(f'screens-{fields[0].n}.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','confinement']},indent=2),flush=True)
if __name__=='__main__':main()
