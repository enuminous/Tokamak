"""Native axisymmetric TokaMaker reference benchmark, not STEP certification.

Adapted from OpenFUSIONToolkit v26.9 DIII-D examples (LGPL-3.0-only);
see source/OFT-LICENSE and source/*cells.json for upstream code extracts.
"""
from pathlib import Path
import argparse,json,hashlib,time,traceback
import numpy as np
from OpenFUSIONToolkit import OFT_env
from OpenFUSIONToolkit.TokaMaker import TokaMaker
from OpenFUSIONToolkit.TokaMaker.meshing import gs_Domain,save_gs_mesh,load_gs_mesh
from OpenFUSIONToolkit.TokaMaker.util import read_eqdsk
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)

def clean(v):
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    return v
def save(p,v):p.write_text(json.dumps(clean(v),indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def mesh(scale):
    p=OUT/f'diiid-mesh-{scale:g}.h5'
    if p.exists():return p
    geom=json.loads((ROOT/'source/DIIID_geom.json').read_text())
    d=gs_Domain();pd=.04*scale;cd=.03*scale;vd=.04*scale;ad=.10*scale
    d.define_region('air',ad,'boundary');d.define_region('plasma',pd,'plasma')
    d.define_region('vacuum',vd,'vacuum',allow_xpoints=True)
    for i,s in enumerate(geom['vv']):d.define_region(f'vv{i}',vd,'conductor',eta=s[1])
    for k,c in geom['coils'].items():
        if k.startswith('ECOIL'):
            for i,s in enumerate(c):d.define_region(f'{k}_{i}',cd,'coil',coil_set=k,nTurns=s['nturns'])
        else:d.define_region(k,cd,'coil',nTurns=c['nturns'])
    d.add_polygon(geom['limiter'],'plasma',parent_name='vacuum');d.add_enclosed([1.75,1.25],'vacuum')
    for i,s in enumerate(geom['vv']):d.add_polygon(s[0],f'vv{i}',parent_name='air')
    for k,c in geom['coils'].items():
        if k.startswith('ECOIL'):
            for i,s in enumerate(c):d.add_polygon(s['pts'],f'{k}_{i}',parent_name='air')
        else:d.add_polygon(c['pts'],k,parent_name='air')
    pts,lc,reg=d.build_mesh();save_gs_mesh(pts,lc,reg,d.get_coils(),d.get_conductors(),str(p))
    return p

def execute(args):
    t0=time.perf_counter();mp=mesh(args.scale);pts,lc,reg,coils,conds=load_gs_mesh(str(mp))
    for c in conds.values():
        if 'eta' in c:c['eta']*=args.eta
    env=OFT_env(nthreads=2);gs=TokaMaker(env);gs.settings.maxits=200
    eqdsk=read_eqdsk(str(ROOT/'source/g192185.02440'))
    gs.setup_mesh(pts,lc,reg);gs.setup_regions(cond_dict=conds,coil_dict=coils)
    gs.setup(order=2,F0=eqdsk['rcentr']*eqdsk['bcentr'])
    ns={'mygs':gs,'eqdsk':eqdsk,'np':np}
    cells=json.loads((ROOT/'source/DIIID_baseline_cells.json').read_text())
    # Execute only explicit, pinned upstream construction cells; no notebook outputs.
    for i in [6,7,8,9,10,11]:exec(''.join(cells[i]['source']),ns)
    inverse=gs.get_stats();axis_inverse=gs.o_point.copy()
    for i in [16,17]:exec(''.join(cells[i]['source']),ns)
    forward=gs.get_stats();axis_forward=gs.o_point.copy()
    exec(''.join(cells[21]['source']),ns)
    eq=gs.copy_eq();stats=gs.get_stats();psi0=eq.get_psi(False).copy();z0=float(eq.o_point[1])
    baseline_currents,_=gs.get_coil_currents()
    tau,wallvec=gs.compute_wall_modes(4)
    gamma,vec=gs.compute_linear_stability(5e3,10,False)
    # Reject a complex leading unstable mode for this real seed benchmark.
    select=np.flatnonzero((np.real(gamma)>0)&(np.abs(np.imag(gamma))<1e-8))
    if not len(select):raise ValueError('No real unstable mode found in requested spectral neighborhood')
    ix=select[np.argmax(np.real(gamma[select]))];g=float(np.real(gamma[ix]));mode=vec[ix].copy()
    result=dict(case=args.name,mesh_scale=args.scale,resistivity_factor=args.eta,
        mesh_vertices=len(pts),mesh_triangles=len(lc),finite_element_dofs=gs.np,
        inverse_stats=inverse,inverse_axis=axis_inverse,forward_stats=forward,forward_axis=axis_forward,
        ramped_stats=stats,ramped_axis=eq.o_point.copy(),wall_time_s=tau,
        gamma_real_per_s=np.real(gamma),gamma_imag_per_s=np.imag(gamma),leading_gamma_per_s=g,
        e_folding_time_s=1/g,baseline_currents_A=baseline_currents,mesh_sha256=sha(mp),
        input_hashes={p.name:sha(p) for p in (ROOT/'source').iterdir() if p.is_file()},
        code_sha256=sha(Path(__file__)),protocol_sha256=sha(ROOT/'PROTOCOL.md'))
    save(OUT/f'{args.name}.json',result)
    if args.modes_only:
        np.savez_compressed(OUT/f'{args.name}-fields.npz',r=gs.r,lc=gs.lc,psi=psi0,mode=mode,wall_modes=wallvec)
    else:
        span=abs(eq.psi_bounds[1]-eq.psi_bounds[0]);seed=mode*(span*.0005/np.max(np.abs(mode)))
        gs.set_psi(psi0+seed);gs.settings.pm=False;gs.update_settings()
        gs.set_isoflux_constraints(None);gs.set_targets(Ip=eqdsk['ip'],Ip_ratio=5.6)
        dt=args.dt/g;gs.setup_td(dt,1e-13,1e-11,pre_plasma=False)
        gs.set_psi(psi0+seed)
        simtime=0.;u=0.;history=[];vv=float(mode@mode)
        def sample(t,nl=0,li=0,retry=0,actual_dt=0.):
            e=gs.copy_eq();zz=float(e.o_point[1])-z0
            history.append(dict(time_s=t,displacement_m=zz,mode_projection=float(mode@(e.get_psi(False)-psi0)/vv),
                correction_A=u,nl_iterations=nl,linear_iterations=li,retries=retry,actual_dt_s=actual_dt))
        sample(0.)
        for i in range(round(2/args.dt)):
            measured=np.interp(max(0,simtime-args.delay),[r['time_s'] for r in history],[r['displacement_m'] for r in history])
            target=float(np.clip(-args.gain*measured,-500,500));u+=float(np.clip(target-u,-1e6*dt,1e6*dt))
            currents=baseline_currents.copy();currents['F9A']+=u;currents['F9B']-=u
            old=simtime;simtime,used,nl,li,retry=gs.step_td(simtime,dt,coil_currents=currents)
            sample(simtime,nl,li,retry,simtime-old)
            if i%10==0:print('TIME',args.name,i,simtime,history[-1]['displacement_m'],u,flush=True)
        ts=np.array([r['time_s'] for r in history]);a=np.abs([r['mode_projection'] for r in history])
        mask=(ts>0)&(ts<=1.0001/g)&(a>1e-30);fit=float(np.polyfit(ts[mask],np.log(a[mask]),1)[0])
        zi=abs(history[0]['displacement_m']);zf=abs(history[-1]['displacement_m']);zm=max(abs(r['displacement_m']) for r in history)
        result.update(gain_A_per_m=args.gain,delay_s=args.delay,dt_gamma=args.dt,history=history,
            fitted_growth_per_s=fit,fitted_relative_difference=fit/g-1,initial_abs_z_m=zi,final_abs_z_m=zf,
            peak_abs_z_m=zm,conditional_suppression=(zf<=zi and zm<=2*zi),
            scope='Ideal prescribed coil-current feedback; axisymmetric GS evolution; not a hardware controller or general MHD model')
    result['elapsed_s']=time.perf_counter()-t0;save(OUT/f'{args.name}.json',result)
    print('COMPLETE',args.name,'gamma',g,'elapsed',result['elapsed_s'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--scale',type=float,default=1.)
    ap.add_argument('--eta',type=float,default=1.);ap.add_argument('--modes-only',action='store_true')
    ap.add_argument('--dt',type=float,default=.1);ap.add_argument('--gain',type=float,default=0.)
    ap.add_argument('--delay',type=float,default=0.);args=ap.parse_args()
    try:execute(args)
    except Exception as e:
        save(OUT/f'{args.name}-failure.json',dict(error=str(e),traceback=traceback.format_exc(),args=vars(args)))
        raise
