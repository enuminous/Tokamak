"""Generate standalone, SI-unit inputs for a matched Fiesta baseline and inward p9 case."""
from pathlib import Path
import csv, hashlib, json, sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-004'))
import validate as v

def save_csv(path, fields, rows):
    with path.open('w', newline='') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(rows)

def generate():
    out=ROOT/'inputs'
    ref=v.b.reference()
    rec=json.loads((v.b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    span=rec['psi_axis']-rec['psi_boundary']
    s=np.linspace(0,1,501)
    a=ref['pp'].antiderivative()
    pressure=span*(a(1)-a(s))
    assert abs(pressure[0]/rec['pressure_axis_Pa']-1)<1e-12
    save_csv(out/'profile-samples.csv',['s_axis0_edge1','pressure_Pa','unscaled_pprime','unscaled_ffprime'],zip(s,pressure,ref['pp'](s),ref['ff'](s)))
    coeff={k:{'breaks':ref[k].x.tolist(),'coefs_descending_by_segment':ref[k].c.T.tolist()} for k in ('pp','ff')}
    coeff.update(target_span_Wb_per_rad=span, convention='In each segment evaluate the polynomial at s minus its left breakpoint. p(s)=target_span*integral_s^1 pp(t) dt. Scale pp in d/dpsi by target_span/(psi_axis-psi_sep); adjust the single multiplier on ff to obtain target Ip. Use F_edge=11.52 T m.')
    (out/'profiles.json').write_text(json.dumps(coeff,indent=2)+'\n')
    walls=v.s.walls()
    save_csv(out/'wall.csv',['component','vertex','R_m','Z_m'],((i,j,*pt) for i,w in enumerate(walls) for j,pt in enumerate(w)))
    for case,shift in [('baseline',0.),('inward-5cm',.05)]:
        rows=[]
        for c,amps in zip(ref['c']['circuits'],ref['m']['icoil']['currents']):
            for coil,polarity in zip(c['coils'],c['polarity']):
                f=coil['fiesta_filament']
                dz=-float(np.sign(np.mean(f['z'])))*shift if c['label']=='p9' else 0.
                for i,(r,z,w) in enumerate(zip(f['r'],f['z'],f['turns'])):
                    rows.append((c['label'],coil['label'],i,r,z+dz,w,int(polarity),amps,amps*polarity*w))
        save_csv(out/f'{case}-filaments.csv',['circuit','pack','filament','R_m','Z_m','turn_weight','polarity','circuit_A','signed_filament_A'],rows)
        common=dict(case=case,inward_shift_per_p9_pack_m=shift,filaments=f'{case}-filaments.csv',wall='wall.csv',profiles='profiles.json',target_Ip_A=rec['ip_A'],target_on_axis_pressure_Pa=rec['pressure_axis_Pa'],F_edge_T_m=11.52,R_minmax_m=[.5,9.],Z_minmax_m=[-10.,10.],main_grid_R_Z=[257,513],comparison_grid_R_Z=[129,257],wall_corner_R_Z_m=walls[0][13].tolist(),flux='total psi, Wb/rad; BR=-dpsi/dZ/R, BZ=dpsi/dR/R',launch='Z=0, own outboard midplane separatrix radius + 0.001 m; follow +B to first lower-wall hit',source_commit='6f66ae09c60b361d600b178416ef3f22b8d0aa6a',protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest())
        (out/f'{case}.json').write_text(json.dumps(common,indent=2)+'\n')
    with (out/'baseline-filaments.csv').open() as f,(out/'inward-5cm-filaments.csv').open() as g:
        left,right=list(csv.DictReader(f)),list(csv.DictReader(g));assert len(left)==len(right)
        for l,r in zip(left,right):
            expected=-np.sign(float(l['Z_m']))*.05 if l['circuit']=='p9' else 0.
            assert abs(float(r['Z_m'])-float(l['Z_m'])-expected)<2e-15
            assert all(l[k]==r[k] for k in l if k!='Z_m')
    print(len(left),'filaments per case;',sum(r['circuit']=='p9' for r in left),'shifted; corner:',walls[0][13])

if __name__=='__main__':generate()
