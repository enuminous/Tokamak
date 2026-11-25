"""Regression controls on the verdict logic. No fixture counts as external solver evidence."""
import copy,json
from compare import RESULTS,load_local,score
local=load_local()
def trial(name,change,expected):
    ext=copy.deepcopy(local);change(ext);out=score(local,ext)
    assert out['external']==expected
    return {'fixture':name,'expected':expected,'actual':out['external']}
def same_side(x):
    for grid in ('fine','coarse'):x['inward-'+grid]=copy.deepcopy(x['baseline-'+grid])
def ambiguous(x):x['inward-fine']['rows'][-1]['signed_corner_m']=.001
def disagree(x):
    for g in ('fine','coarse'):x['baseline-'+g]['rows'][-1]['Bnormal_target_T']+=.2
tests=[trial('constructed matching pair',lambda x:None,'PASS'),trial('resolved original face',same_side,'FAIL'),trial('corner inside guard',ambiguous,'UNRESOLVED'),trial('baseline normal mismatch',disagree,'UNRESOLVED')]
assert score(local)['external']=='UNRESOLVED'
tests.append({'fixture':'no independent return','actual':'UNRESOLVED','expected':'UNRESOLVED'})
(RESULTS/'verdict-controls.json').write_text(json.dumps(tests,indent=2)+'\n')
