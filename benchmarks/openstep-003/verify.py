"""Independent field/profile checks, trace controls, and an uncached replay."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
from screen_sweep import Field,ROOT,OUT,b
sys.path.insert(0,str(ROOT.parent/'openstep-002'))
from controlled import Controlled

def main():
    checks=[]
    def check(name,ok,value=None,limit=None):checks.append(dict(name=name,status='PASS' if bool(ok) else 'FAIL',value=value,limit=limit))
    target=json.loads((b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    ref=b.reference();span=target['psi_axis']-target['psi_boundary'];pp=ref['pp'].antiderivative();ss=np.linspace(0,1,1001)
    expected=span*(pp(1)-pp(ss))
    paths=set()
    for p in OUT.glob('screens-*.json'):
        for row in json.loads(p.read_text())['input_fingerprint']['fields']:
            path=ROOT.parent/row['path'];paths.add(path)
            check(path.stem+':screen_input_hash',hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'] and hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest()==row['report_sha256'])
    for path in sorted(paths):
        report=json.loads(path.with_suffix('.json').read_text())
        if not report['converged']:continue
        f=Field(path);tag=path.stem
        check(tag+':full_domain_defect',report['final_defect']<=1e-5,report['final_defect'],1e-5)
        ppi=f.pp.antiderivative();err=float(np.max(abs(f.span*(ppi(1)-ppi(ss))-expected))/target['pressure_axis_Pa'])
        check(tag+':independent_entire_pressure_profile',err<=1e-9,err,1e-9)
        current=float(f.j.sum()*f.da);err=abs(current/target['ip_A']-1)
        check(tag+':independent_current_integral',err<=1e-9,err,1e-9)
        check(tag+':F_squared_positive',np.min(f.f2(ss))>0,float(np.min(f.f2(ss))),0)
        asym=float(np.max(abs(f.psi-f.psi[:,::-1])));check(tag+':mirror_symmetry',asym<=1e-8,asym,1e-8)
        check(tag+':finite_field',np.all(np.isfinite(f.psi)))
        # Every saved vacuum field must match the actual shifted coil machine.
        # Test on-grid plasma-region points; avoids spline interpolation error.
        i=np.arange(len(f.r)//4,3*len(f.r)//4,max(1,len(f.r)//16));j=np.arange(len(f.z)//4,3*len(f.z)//4,max(1,len(f.z)//16))
        RR,ZZ=np.meshgrid(f.r[i],f.z[j],indexing='ij');vac=b.machine(ref,report['p9_translation_m']).psi(RR,ZZ)
        verr=float(np.max(np.abs(vac-(f.psi-f.plasma)[np.ix_(i,j)])))
        check(tag+':fixed_currents_shifted_coil_field',verr<=1e-10,verr,1e-10)
        print('Verified fields',tag,flush=True)
    for p in sorted(OUT.glob('screens-*.json')):
        d=json.loads(p.read_text())
        for r in d['rows']:
            check(r['tag']+':trace_flux',r['max_flux_drift']<=1e-5,r['max_flux_drift'],1e-5)
            check(r['tag']+':trace_step_position',r['max_step_halving_position_m'] is not None and r['max_step_halving_position_m']<=.001,r['max_step_halving_position_m'],.001)
            check(r['tag']+':trace_step_length',r['max_step_halving_length_m'] is not None and r['max_step_halving_length_m']<=.01,r['max_step_halving_length_m'],.01)
            check(r['tag']+':all_wall_intersections',r['wall_hits']==r['trace_count'],r['wall_hits'],r['trace_count'])
            v=r['vertical']['translations'];k=[x['dFz_dz_N_per_m'] for x in v];delta=float(np.ptp(k)/abs(k[0]))
            check(r['tag']+':vertical_step_consistency',delta<1e-3,delta,1e-3)
            check(r['tag']+':q_quadrature',r['magnetic']['q95_quadrature_difference']<1e-3,r['magnetic']['q95_quadrature_difference'],1e-3)
        err=d['confinement']['max_analytic_relative_error'];check(p.stem+':energy_ODE_analytic_control',err<1e-8,err,1e-8)
    # Original-boundary replay is independently recorded by recovery_check.py.
    control=json.loads((OUT/'recovery-check.json').read_text())
    field=OUT/'recovery-homotopy-10.npz'
    check('recovered_baseline:replay_field_hash',hashlib.sha256(field.read_bytes()).hexdigest()==control['field_sha256'])
    defect=control['original_FreeGS_defect']
    check('recovered_baseline:original_FreeGS_boundary',defect<=1e-5,defect,1e-5)
    attempts=[d for p in OUT.glob('*.json') if isinstance((d:=json.loads(p.read_text())),dict) and 'converged' in d]
    warm_hashes=True;warm_accepted=True
    for r in attempts:
        warm=ROOT.parent/r['warm_start']
        warm_hashes &= hashlib.sha256(warm.read_bytes()).hexdigest()==r['warm_sha256']
        warm_accepted &= json.loads(warm.with_suffix('.json').read_text()).get('converged',False)
    check('provenance:all_warm_start_hashes',warm_hashes)
    check('provenance:only_accepted_warm_starts',warm_accepted)
    code_hash=hashlib.sha256((ROOT/'solve.py').read_bytes()).hexdigest()
    protocol_hash=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    check('provenance:solver_source_hashes',all(r['code_sha256']==code_hash for r in attempts))
    check('provenance:unchanged_protocol_hashes',all(r['protocol_sha256']==protocol_hash for r in attempts))
    result=dict(scope='Numerical implementation and accepted-field checks; not physical qualification',passed=sum(x['status']=='PASS' for x in checks),failed=sum(x['status']=='FAIL' for x in checks),checks=checks)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='checks'}),flush=True)
    if result['failed']:raise SystemExit(1)
if __name__=='__main__':main()
