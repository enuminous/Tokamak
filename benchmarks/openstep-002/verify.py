"""Conservation, analytic controls, numerical consistency and source checks."""
from pathlib import Path
import json,hashlib,csv
import numpy as np
from scipy.interpolate import RectBivariateSpline
import screens as s
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'

def main():
    checks=[]
    def check(name,condition,value=None,limit=None):
        checks.append(dict(name=name,status='PASS' if bool(condition) else 'FAIL',value=value,limit=limit))
    manifest=json.loads((ROOT/'source/manifest.json').read_text())
    for f in manifest['files']:
        got=hashlib.sha256((ROOT/'source'/Path(f['path']).name).read_bytes()).hexdigest()
        check('source_sha256:'+Path(f['path']).name,got==f['sha256'],got)
    kin=s.sources();check('kinetic_source_power_balance',abs(kin['source_power_closure_W'])<1,kin['source_power_closure_W'],1)
    check('thermal_energy_profile_vs_summary',abs(kin['thermal_integral_relative_difference'])<.005,kin['thermal_integral_relative_difference'],.005)
    boundary=json.loads((OUT/'boundary-equivalence.json').read_text())
    for row in boundary['checks']:
        check('cached_boundary:'+row['source'],row['passed'],row['max_absolute_difference'],1e-10)
    critical=json.loads((OUT/'critical-search-equivalence.json').read_text())
    for row in critical['checks']:
        check(f"iterative_critical_search:{row['arm']}-{row['grid']}",row['passed'],row['Jtor_relative_difference'],1e-9)
    force=json.loads((OUT/'force-independent-check.json').read_text())
    check('vertical_force:analytic_coil_crosscheck',force['relative_difference']<1e-3,force['relative_difference'],1e-3)
    for row in json.loads((OUT/'controlled-magnetic.json').read_text()):
        tag=f"controlled:{row['arm']}-{row['grid']}"
        check(tag+':F_squared_positive',row['F_squared_min_T2_m2']>0,row['F_squared_min_T2_m2'],0)
        check(tag+':full_pressure_profile',row['pressure_profile_relative_error']<1e-10,row['pressure_profile_relative_error'],1e-10)
        report=json.loads((OUT/f"{row['arm']}-{row['grid']}-controlled.json").read_text())
        check(tag+':current_constraint',report['current_relative_error']<1e-10,report['current_relative_error'],1e-10)
        check(tag+':independent_defect',report['final_defect']<=1e-5,report['final_defect'],1e-5)
    # Exact circular-flux analytic control: q = F/(c*sqrt(R0^2-rho^2)).
    class Circle:
        def __init__(self):
            r=np.linspace(2,6,129);z=np.linspace(-2,2,129);R,Z=np.meshgrid(r,z,indexing='ij')
            self.sp=RectBivariateSpline(r,z,-.5*((R-4)**2+Z**2))
        def surface(self,v):
            t=np.linspace(0,2*np.pi,2049);return np.c_[4+.8*np.cos(t),.8*np.sin(t)]
        def f2(self,v):return 100.
    q=s.qintegral(Circle(),.5,4);exact=10/np.sqrt(16-.8**2)
    check('q_integral_analytic_R_and_2pi_control',abs(q/exact-1)<2e-6,float(q/exact-1),2e-6)
    for n in [129,257,513]:
        for arm in ['baseline','p9-inward']:
            p=OUT/f'{arm}-{n}-symmetric.json'
            if p.exists():
                d=json.loads(p.read_text());check(f'{arm}-{n}:equilibrium_defect',d.get('converged',False),d.get('final_defect'),1e-5)
        p=OUT/f'screens-{n}-core.json'
        if not p.exists():p=OUT/f'screens-{n}-all.json'
        if p.exists():
            d=json.loads(p.read_text())
            for row in d['magnetic']:
                tag=f"{row['arm']}-{n}"
                check(tag+':F_squared_positive',row['F_squared_min_T2_m2']>0,row['F_squared_min_T2_m2'],0)
                check(tag+':q95_quadrature',row['q95_quadrature_difference']<1e-3,row['q95_quadrature_difference'],1e-3)
            for row in d['vertical']:
                v=row['translations'];kk=np.array([v1['dFz_dz_N_per_m'] for v1 in v]);rel=float(np.ptp(kk)/abs(kk[0]))
                check(f"{row['arm']}-{n}:force_step_consistency",rel<1e-3,rel,1e-3)
                antisym=max(abs(x['Fz_plus_N']+x['Fz_minus_N']) for x in v)
                check(f"{row['arm']}-{n}:force_antisymmetry",antisym<1,antisym,1)
            check(f'energy_ODE_{n}:analytic_control',d['confinement']['max_analytic_relative_error']<1e-8,d['confinement']['max_analytic_relative_error'],1e-8)
        p=OUT/f'fieldline-traces-{n}.csv'
        if p.exists():
            traces=list(csv.DictReader(p.open()));maxdrift=max(float(t['normalized_flux_drift']) for t in traces)
            check(f'fieldlines-{n}:flux_conservation',maxdrift<1e-5,maxdrift,1e-5)
            matched={}
            for t in traces:matched.setdefault((t['arm'],t['upstream_offset_m']),[]).append(t)
            position=[];length=[]
            for pair in matched.values():
                if len(pair)!=2:continue
                a,b=pair
                position.append(float(np.hypot(float(a['R_target_m'])-float(b['R_target_m']),float(a['Z_target_m'])-float(b['Z_target_m']))))
                length.append(abs(float(a['connection_length_m'])-float(b['connection_length_m'])))
            check(f'fieldlines-{n}:step_halving_position',max(position)<1e-3,max(position),1e-3)
            check(f'fieldlines-{n}:step_halving_length',max(length)<.01,max(length),.01)
    thermal=json.loads((OUT/'thermal.json').read_text())
    check('thermal_finite_volume_energy_conservation',thermal['max_energy_balance_relative']<1e-9,thermal['max_energy_balance_relative'],1e-9)
    err=max(abs(t['surface_at_20s_K']-t['analytic_steady_surface_K']) for t in thermal['refinement'])
    check('thermal_central_steady_solution',err<1e-4,err,1e-4)
    r=list(csv.DictReader((OUT/'electric-sweep.csv').open()))
    error=max(abs(float(x['gross_electric_MW'])-float(x['heating_electric_MW'])-float(x['other_electric_MW'])-float(x['net_electric_MW'])) for x in r)
    check('electric_accounting',error<1e-9,error,1e-9)
    report=dict(scope='Implementation and numerical checks only; physical feasibility is separate',passed=sum(x['status']=='PASS' for x in checks),failed=sum(x['status']=='FAIL' for x in checks),checks=checks)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if report['failed']:raise SystemExit(1)
if __name__=='__main__':main()
