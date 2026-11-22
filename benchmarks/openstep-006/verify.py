"""Verify archived results; failures are findings, not exceptions to hide."""
from pathlib import Path
import json,hashlib,platform,sys,importlib.metadata
import numpy as np
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent;OUT=ROOT/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((OUT/(n+'.json')).read_text())
def run():
    groups={k:[] for k in ['historical_integrity','input_and_execution_integrity','native_primary','native_diagnostics','reactor']}
    def check(group,name,ok,value=None,limit=None):groups[group].append(dict(name=name,status='PASS' if bool(ok) else 'FAIL',value=value,limit=limit))
    for exp in ['openstep-003','openstep-004','openstep-005']:
        m=json.loads((ROOT.parent/exp/'artifact-manifest.json').read_text())
        for r in m['files']:
            p=REPO/r['path'];check('historical_integrity',r['path'],p.exists() and sha(p)==r['sha256'])
    catalog=json.loads((ROOT/'source/catalog.json').read_text())
    for r in catalog['oft_files']:
        raw=(ROOT/'source'/r['local']).read_bytes()[:-1]
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        check('input_and_execution_integrity','upstream numeric bytes:'+r['local'],blob==r['git_blob_sha'])
    version_hashes={sha(p) for p in list(ROOT.glob('*.py'))+list((ROOT/'development').glob('*.py'))}
    cases=['coarse','fine','eta2-isolated','open-dt10-isolated','open-corrected-dt10','open-corrected-dt05',
        'feedback-neg100k','feedback-neg20k','feedback-pos20k','feedback-pos100k','feedback-delay05ms','feedback-delay10ms',
        'zero-seed','negative-seed','bounds-included','bounds-time05','bounds-time025']
    for name in cases:
        r=read(name);check('input_and_execution_integrity','completed:'+name,'elapsed_s' in r)
        check('input_and_execution_integrity','archived code:'+name,r['code_sha256'] in version_hashes)
        check('input_and_execution_integrity','frozen protocol:'+name,r['protocol_sha256']==sha(ROOT/'PROTOCOL.md'))
        check('input_and_execution_integrity','input hashes:'+name,all(sha(ROOT/'source'/p)==h for p,h in r['input_hashes'].items()))
        if 'history' in r:
            ts=np.array([h['time_s'] for h in r['history']]);u=np.array([h['correction_A'] for h in r['history']])
            check('input_and_execution_integrity','time progresses:'+name,np.all(np.diff(ts)>0))
            check('input_and_execution_integrity','current limit:'+name,np.max(abs(u))<=500+1e-8)
    a,b,c=read('coarse'),read('fine'),read('eta2-isolated');g=a['leading_gamma_per_s']
    tests=[('published eigenvalue',abs(g/945.98-1),.1),('two-grid growth agreement',abs(b['leading_gamma_per_s']/g-1),.1),
        ('two-grid slowest wall time',abs(b['wall_time_s'][0]/a['wall_time_s'][0]-1),.1),
        ('resistivity doubles growth',abs(c['leading_gamma_per_s']/(2*g)-1),.02),
        ('resistivity halves all wall times',float(np.max(abs(2*np.array(c['wall_time_s'])/a['wall_time_s']-1))),.001)]
    for name,value,limit in tests:check('native_primary',name,value<=limit,value,limit)
    for name in ['open-corrected-dt10','open-corrected-dt05']:
        r=read(name);v=abs(r['fitted_growth_per_s']/r['leading_gamma_per_s']-1)
        check('native_primary',name+' time/eigen growth agreement',v<=.1,v,.1)
    v=abs(read('open-corrected-dt10')['fitted_growth_per_s']/read('open-corrected-dt05')['fitted_growth_per_s']-1)
    check('native_primary','time-step fit agreement',v<=.05,v,.05)
    for name in ['bounds-time05','bounds-time025']:
        r=read(name);v=abs(r['fitted_growth_per_s']/r['leading_gamma_per_s']-1)
        check('native_diagnostics',name+' time/eigen growth agreement',v<=.1,v,.1)
    v=abs(read('bounds-time05')['fitted_growth_per_s']/read('bounds-time025')['fitted_growth_per_s']-1)
    check('native_diagnostics','bounds model time-step agreement',v<=.05,v,.05)
    # Sign sensitivity and no-seed drift are recorded as diagnostics, no post-hoc pass limit.
    diagnostics=dict(negative_seed_fit_per_s=read('negative-seed')['fitted_growth_per_s'],
        zero_seed_final_drift_m=read('zero-seed')['final_abs_z_m'],
        bounds_included_gamma_per_s=read('bounds-included')['leading_gamma_per_s'])
    reactor=read('reactor');groups['reactor']=reactor['checks']
    check('input_and_execution_integrity','reactor code hash',reactor['code_sha256']==sha(ROOT/'reactor.py'))
    check('input_and_execution_integrity','inherited reactor data',all(sha(ROOT.parent/p)==h for p,h in reactor['input_sha256'].items()))
    counts={k:{s:sum(c['status']==s for c in v) for s in ['PASS','FAIL']} for k,v in groups.items()}
    versions={k:importlib.metadata.version(k) for k in ['numpy','scipy','h5py','matplotlib','OpenFUSIONToolkit']}
    result=dict(groups=groups,counts=counts,diagnostics=diagnostics,python=sys.version,platform=platform.platform(),versions=versions,
        verdict='PARTIAL: native eigenvalue/refinement/scaling pass; two primary and two diagnostic time/eigenvalue comparisons fail; reactor models conditional')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(counts,indent=2))
    return result
if __name__=='__main__':run()
