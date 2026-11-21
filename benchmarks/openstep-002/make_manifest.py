"""Hash the complete publishable bundle after calculations and rendering finish."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent;repo=root.parent.parent
paths=[p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact-manifest.json']
paths += [repo/p for p in ['README.md','index.html','equilibrium.html','trisphere-prototype.html','screening.html','screening.js','screening.css']]
rows=[]
for path in sorted(paths):
    data=path.read_bytes();rows.append(dict(path=path.relative_to(repo).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),git_blob_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()))
manifest=dict(id='OPENSTEP-002',upstream_revision='6f66ae09c60b361d600b178416ef3f22b8d0aa6a',
              preceding_repository_revision='d8c6954ac76343c5883869bf41401ea7cc1fd4a3',
              note='Manifest excludes itself. OPENSTEP-001 is an unchanged prerequisite with its own artifact manifest.',files=rows)
(root/'artifact-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(len(rows),'files hashed')
