"""Fetch pinned supplementary OpenSTEP inputs and verify SHA-256 and Git SHA."""
from pathlib import Path
import json,hashlib,urllib.request
root=Path(__file__).resolve().parent/'source'
manifest=json.loads((root/'manifest.json').read_text())
for item in manifest['files']:
    data=urllib.request.urlopen(item['url']).read()
    assert hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob_sha']
    (root/Path(item['path']).name).write_bytes(data)
    print(Path(item['path']).name,'verified',len(data))
