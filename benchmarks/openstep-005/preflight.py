"""Verify historical artifacts and record exact inputs/environment."""
import importlib.metadata
import json
import platform
import sys
from common import ROOT, REPO, OUT, inventory, stamp, sha, save, check


def main():
    result, checks = stamp('preflight'), []
    for experiment in ['openstep-003', 'openstep-004']:
        manifest = ROOT.parent/experiment/'artifact-manifest.json'
        data = json.loads(manifest.read_text())
        for row in data['files']:
            path = REPO/row['path']
            actual = sha(path) if path.exists() else None
            check(checks, 'unchanged:'+row['path'], actual == row['sha256'], actual, row['sha256'])
    fields = []
    for path, row in inventory():
        fields.append(dict(path=str(path.relative_to(REPO)),sha256=sha(path),
                           report_sha256=sha(path.with_suffix('.json')),grid=row['grid'],shift_m=row['shift_m']))
        check(checks,'accepted_field:'+path.stem,True)
    versions = {}
    for module in ['numpy','scipy','matplotlib','shapely','FreeGS']:
        versions[module] = importlib.metadata.version(module)
    inputs = dict(parent_commit=result['parent_commit'],protocol_sha256=sha(ROOT/'PROTOCOL.md'),
                  fields=fields,
                  inherited_data=[dict(path=str(p.relative_to(REPO)),sha256=sha(p)) for p in [
                      ROOT.parent/'openstep-002/source/SPR45_2D_Wall.csv',
                      ROOT.parent/'openstep-002/results/kinetic-inputs.json',
                      ROOT.parent/'openstep-004/results/representative-refinement.json']],
                  interpreter=sys.version,platform=platform.platform(),packages=versions)
    (ROOT/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    result.update(checks=checks,inputs=inputs)
    save('preflight.json',result)
    print(json.dumps({s:sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}),flush=True)


if __name__=='__main__':
    main()
