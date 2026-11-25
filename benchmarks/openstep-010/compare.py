"""Compare matched grid pairs. An optional return manifest references four independent flux exports."""
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from trace_pair import ROOT, measure, read_field
RESULTS=ROOT/'results'
CASES=('baseline','inward')
GRIDS={'coarse':129,'fine':257}

def row(trace):
    return trace['rows'][-1]

def distance(a,b):
    return math.hypot(a['R_target_m']-b['R_target_m'],a['Z_target_m']-b['Z_target_m'])

def pair_metrics(pair):
    out={}
    for case in CASES:
        c,f=[pair[case+'-'+g] for g in GRIDS]
        err=distance(row(c),row(f))+max(c['tightening_delta_RZ_m'],f['tightening_delta_RZ_m'])
        vals=[row(t)['signed_corner_m'] for t in (c,f)]
        side=None
        if c['trace_gates_pass'] and f['trace_gates_pass'] and all(x is not None for x in vals):
            if min(vals)>max(.002,err):side=1
            if max(vals)<-max(.002,err):side=-1
        out[case]=dict(observed_strike_uncertainty_m=err,corner_guard_m=max(.002,err),resolved_side=side)
    return out

def score(local,external=None):
    lm=pair_metrics(local)
    out=dict(local_mesh='PASS' if [lm[k]['resolved_side'] for k in CASES]==[-1,1] else 'UNRESOLVED',local=lm,external='UNRESOLVED',external_reason='Missing independent matched Fiesta pair and its refinement.')
    if external is None:return out
    em=pair_metrics(external);out['Fiesta']=em
    for k in CASES:
        a=row(local[k+'-fine']);b=row(external[k+'-fine'])
        delta=distance(a,b)
        db=abs(a['Bnormal_target_T']-b['Bnormal_target_T']) if a['Bnormal_target_T'] is not None and b['Bnormal_target_T'] is not None else None
        out[k+'_agreement']=dict(distance_m=delta,normal_difference_T=db,coordinate_pass=delta<=.005,normal_pass=db is not None and db<=max(.02,.1*a['Bnormal_target_T']))
    agree=out['baseline_agreement']
    if out['local_mesh']!='PASS' or em['baseline']['resolved_side']!=-1 or not (agree['coordinate_pass'] and agree['normal_pass']):
        out['external_reason']='Baseline, local crossing, or mesh/trace uncertainty fails to establish a comparison.'
    elif em['inward']['resolved_side']==1:
        out.update(external='PASS',external_reason='Both solvers resolve the baseline and the adjacent-face crossing.')
        power=json.loads((ROOT.parent/'openstep-002/results/kinetic-inputs.json').read_text())['P_transport_W']
        for t in external.values():
            for obs in t['rows']:
                obs['representative_heat_MW_m2']=(.25*.5*power*math.exp(-.001/.006)/
                    (2*math.pi*t['launch_R_m']*.006*obs['area_expansion'])/1e6)
        out['external_model_heat_ratio']=row(external['inward-fine'])['representative_heat_MW_m2']/row(external['baseline-fine'])['representative_heat_MW_m2']
    elif em['inward']['resolved_side']==-1:
        out.update(external='FAIL',external_reason='Baseline agrees and the independently solved displaced strike stays on face 12.')
    else:out['external_reason']='Displaced strike or its uncertainty does not distinguish the two faces.'
    return out

def load_local():
    return {tag:json.loads((RESULTS/('trace-'+file+'.json')).read_text()) for tag,file in [('baseline-coarse','baseline-coarse'),('baseline-fine','baseline-fine'),('inward-coarse','inward-coarse-B'),('inward-fine','inward-fine')]}

def load_external(path):
    m=json.loads(path.read_text()); protocol=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    if m.get('protocol_sha256')!=protocol or not m.get('solver_revision') or not str(m.get('solver','')).lower().startswith('fiesta'):
        raise ValueError('Supply the Fiesta revision and matching frozen protocol digest.')
    if m.get('independent_input_and_solver_review')!='accepted' or not m.get('review_evidence'):
        raise ValueError('Matching of the two inputs, solver convergence and independent provenance require documented review.')
    fields={}
    for grade,n in GRIDS.items():
        for case in CASES:
            tag=f'{case}-{grade}';entry=m['fields'][tag];src=path.parent/entry['file']
            if hashlib.sha256(src.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError(tag+' SHA-256')
            with np.load(src,allow_pickle=False) as z:
                if z['r'].shape!=(n,) or z['z'].shape!=(2*n-1,) or not np.allclose(z['r'],np.linspace(.5,9,n),rtol=0,atol=1e-12) or not np.allclose(z['z'],np.linspace(-10,10,2*n-1),rtol=0,atol=1e-12):
                    raise ValueError(tag+' grid differs from frozen grid')
                f=read_field(z['r'],z['z'],z['psi'],float(z['axis_R_m']),float(z['psi_axis']),float(z['psi_sep']),tag)
                fields[tag]=measure(f,include_heat=False)
    return fields

def main():
    p=argparse.ArgumentParser();p.add_argument('--fiesta-manifest',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();local=load_local();external=load_external(args.fiesta_manifest) if args.fiesta_manifest else None
    out=score(local,external)
    for g in GRIDS:
        q0=row(local['baseline-'+g])['representative_heat_MW_m2']; q1=row(local['inward-'+g])['representative_heat_MW_m2']
        out[g+'_local_heat']=dict(baseline=q0,inward=q1,delta=q1-q0,ratio=q1/q0)
    def q(k):return row(local[k])['representative_heat_MW_m2']
    out['heat_refinement_sum_MW_m2']=sum(abs(q(k+'-fine')-q(k+'-coarse')) for k in CASES)
    native=json.loads((RESULTS/'trace-released-Fiesta-baseline.json').read_text())
    out['published_Fiesta_baseline_offset_from_local_fine_m']=distance(row(native),row(local['baseline-fine']))
    with (RESULTS/'pair-comparison.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['solver','case','mesh','R_target_m','Z_target_m','face','signed_corner_m','abs_Bnormal_T','model_heat_MW_m2','trace_checks'])
        for name,group in [('local',local),('Fiesta',external or {})]:
            for k in CASES:
                for g in GRIDS:
                    tag=k+'-'+g;t=group.get(tag)
                    if t is None:w.writerow([name,k,g,'','','','','','','UNRESOLVED']);continue
                    r=row(t);w.writerow([name,k,g,r['R_target_m'],r['Z_target_m'],r['segment'],r['signed_corner_m'],r['Bnormal_target_T'],r['representative_heat_MW_m2'],t['trace_gates_pass']])
    result=json.dumps(out,indent=2,allow_nan=False)
    if args.output:args.output.write_text(result+'\n')
    print(result)
if __name__=='__main__':main()
