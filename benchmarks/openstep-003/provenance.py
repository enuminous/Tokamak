"""Write replay commands and content-addressed artifact inventory."""
from pathlib import Path
import json,hashlib,platform,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent;OUT=ROOT/'results'

def main():
    reports={p.stem:json.loads(p.read_text()) for p in OUT.glob('*.json') if isinstance((x:=json.loads(p.read_text())),dict) and 'converged' in x}
    done=set();order=[]
    while len(done)<len(reports):
        eligible=[]
        for name,r in reports.items():
            if name in done:continue
            warm=Path(r['warm_start']);dep=warm.stem if warm.parts[0]=='openstep-003' else None
            if dep is None or dep in done:eligible.append(name)
        if not eligible:raise ValueError('Missing or cyclic warm start')
        for name in sorted(eligible):order.append(name);done.add(name)
    lines=['# Exact replay order','',
        'Run from the repository root with the pinned dependencies installed. Use one BLAS thread. These commands replay complete solves; failure exit code 2 is an expected recorded outcome for failed attempts. Intermediate homotopy files are numerical warm starts, not design candidates.','',
        '```sh','export OPENBLAS_NUM_THREADS=1']
    for name in order:
        r=reports[name];warm='benchmarks/'+r['warm_start']
        cmd=f'python benchmarks/openstep-003/solve.py --n {r["grid"][0]} --shift {r["p9_translation_m"]} --warm {warm} --tag {r["tag"]} --rdiff {r["rdiff"]} --line-search {r["line_search"]} --maxits {r["max_iterations"]} --alpha {r["homotopy_alpha"]}'
        lines.append(cmd if r['converged'] else cmd+' || test "$?" -eq 2')
    lines+=['```','','Interrupted exploratory trials are described in DEVELOPMENT.md. Their logs document the interruption; they have no accepted final field.','']
    (ROOT/'COMMANDS.md').write_text('\n'.join(lines))
    import numpy,scipy,freegs,shapely,matplotlib,h5py,contourpy
    env=dict(python=sys.version,platform=platform.platform(),packages={m.__name__:getattr(m,'__version__','unknown') for m in [numpy,scipy,freegs,shapely,matplotlib,h5py,contourpy]},blas_threads=1)
    (ROOT/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    rows=[]
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact-manifest.json')
    files += [REPO/n for n in ['coil-scan.html','coil-scan.js','README.md','index.html','screening.html']]
    for p in files:
        content=p.read_bytes();rows.append(dict(path=str(p.relative_to(REPO)),bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),git_blob_sha=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()))
    (ROOT/'artifact-manifest.json').write_text(json.dumps(dict(experiment='OPENSTEP-003',parent_commit='37ae3ea0d58830575eb11e25b1220453ad614c78',files=rows),indent=2)+'\n')
    print('Recorded',len(rows),'artifacts')
if __name__=='__main__':main()
