"""Bounded physics screens; no MHD/transport/engineering certification."""
from pathlib import Path
import sys,json,hashlib,csv,argparse,itertools,time
import numpy as np
import h5py,contourpy
from scipy.interpolate import RectBivariateSpline
from scipy.integrate import solve_ivp
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'openstep-001'))
import benchmark as b
OUT=ROOT/'results';MU0=b.MU0

def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def csvsave(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def sources():
    manifest=json.loads((ROOT/'source/manifest.json').read_text())
    for row in manifest['files']:
        path=ROOT/'source'/Path(row['path']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    with h5py.File(ROOT/'source/STEP_SPP_001_EBCC_ftop.nc') as f,h5py.File(ROOT/'source/summary.h5') as h:
        cp=f['core_profiles/0'];eq=f['equilibrium/0'];cs=f['core_sources/0'];s=h['summary']
        scalar=lambda k:float(np.asarray(s[k]).ravel()[0])
        get=lambda k:np.asarray(cp['profiles_1d.'+k])[0]
        vol=get('grid.volume');pressure=get('pressure_thermal');ion_n=get('ion.density');mass=get('ion.element.a').ravel()
        # Extend to axis with the first profile value; that omitted central volume is tiny.
        integrate=lambda x:float(np.trapezoid(np.r_[x[0],x],np.r_[0,vol]))
        names=[x.decode() for x in cs['source.identifier.name'][...]]
        def power(name,field):return float(cs['source.global_quantities.'+field][names.index(name),0])
        result=dict(source='OpenSTEP EB-CC JETTO flat-top; distinct from Fiesta free-boundary',
            W_thermal_J=scalar('global_quantities&energy_thermal&value'),
            W_profile_integral_J=1.5*integrate(pressure),
            line_density_m3=scalar('line_average&n_e&value'),volume_density_m3=scalar('volume_average&n_e&value'),
            P_aux_W=power('auxiliary','power'),P_alpha_W=power('fusion','power'),
            P_ohmic_W=power('ohmic','electrons.power'),P_radiation_W=-power('radiation','electrons.power'),
            P_net_source_W=power('total','power'),P_neutron_W=scalar('fusion&neutron_power_total&value'),
            summary_tau_s=scalar('global_quantities&tau_energy&value'),summary_H98=scalar('global_quantities&h_98&value'),
            R0_m=float(eq['vacuum_toroidal_field.r0'][()]),B0_T=float(eq['vacuum_toroidal_field.b0'][0]),
            volume_m3=float(eq['time_slice.global_quantities.volume'][0]),Ip_A=float(eq['time_slice.global_quantities.ip'][0]),
            minor_radius_m=float(eq['time_slice.boundary.minor_radius'][0]),
            pressure_axis_Pa=float(eq['time_slice.profiles_1d.pressure'][0,0]),
            thermal_pressure_axis_Pa=float(pressure[0]),ion_mass_kg=integrate(np.sum(ion_n*mass[:,None],axis=0))*1.66053906892e-27,
            mean_fuel_mass_amu=2.5)
        result['P_heating_W']=result['P_aux_W']+result['P_alpha_W']+result['P_ohmic_W']
        result['P_transport_W']=result['P_heating_W']-result['P_radiation_W']
        result['P_fusion_total_W']=result['P_alpha_W']+result['P_neutron_W']
        result['source_power_closure_W']=result['P_transport_W']-result['P_net_source_W']
        result['thermal_integral_relative_difference']=result['W_profile_integral_J']/result['W_thermal_J']-1
    save('kinetic-inputs.json',result);return result

class Field:
    def __init__(self,arm,n,controlled=False):
        suffix='controlled' if controlled else 'symmetric'
        p=OUT/f'{arm}-{n}-{suffix}.npz'
        if not p.exists():p=b.ROOT/'results'/p.name
        self.report=json.loads(p.with_suffix('.json').read_text());assert self.report['converged']
        d=np.load(p);self.r=d['r'];self.z=d['z'];self.psi=d['psi'];self.plasma=d['plasma_psi']
        self.R,self.Z=np.meshgrid(self.r,self.z,indexing='ij');self.n=n;self.arm=arm;self.controlled=controlled
        self.ref=b.reference();self.ref['cell_average']=True
        self.pp=self.ref['pp'];self.ff=self.ref['ff']
        if controlled:
            from scipy.interpolate import PPoly
            self.pp=PPoly(self.pp.c*self.report['pressure_derivative_scale'],self.pp.x)
            self.ff=PPoly(self.ff.c*self.report['ff_derivative_scale'],self.ff.x)
        self.sp=RectBivariateSpline(self.r,self.z,self.psi);self.psp=RectBivariateSpline(self.r,self.z,self.plasma)
        self.vsp=RectBivariateSpline(self.r,self.z,self.psi-self.plasma)
        self.axis,self.xpoints=b.refined_critical(self.R,self.Z,self.psi);self.axis=self.axis[0]
        self.pa=self.axis[2];self.pb=self.xpoints[0][2];self.span=self.pa-self.pb
        p=b.PreciseProfiles(self.pp,self.ff,fvac=11.52);p.cell_average=True;self.j=p.Jtor(self.R,self.Z,self.psi)
        self.core=b.critical.core_mask(self.R,self.Z,self.psi,[self.axis],self.xpoints).astype(bool)
        self.s=np.clip((self.pa-self.psi)/self.span,0,1);self.da=(self.r[1]-self.r[0])*(self.z[1]-self.z[0])
        self.d=self.report['final']
    def f2(self,s):
        fi=self.ff.antiderivative();return 11.52**2+2*self.span*(fi(1)-fi(s))
    def bpol(self,r,z,sp=None):
        sp=self.sp if sp is None else sp
        return -sp.ev(r,z,dy=1)/r,sp.ev(r,z,dx=1)/r
    def surface(self,s):
        cg=contourpy.contour_generator(x=self.r,y=self.z,z=self.psi.T)
        paths=cg.lines(self.pa-s*self.span)
        candidates=[a for a in paths if len(a)>3 and np.linalg.norm(a[0]-a[-1])<1e-7 and Polygon(a).contains(Point(*self.axis[:2]))]
        if not candidates:raise ValueError(f'No closed surface at {s}')
        return max(candidates,key=lambda a:Polygon(a).area)

def qintegral(f,s,sub=1):
    a=f.surface(s);lo=a[:-1];dx=a[1:]-lo
    pts=lo[:,None,:]+((np.arange(sub)+.5)/sub)[None,:,None]*dx[:,None,:]
    rr=pts[:,:,0].ravel();zz=pts[:,:,1].ravel()
    grad=np.hypot(f.sp.ev(rr,zz,dx=1),f.sp.ev(rr,zz,dy=1)).reshape((-1,sub))
    return float(np.sum(np.linalg.norm(dx,axis=1)*np.mean(np.sqrt(f.f2(s))/(pts[:,:,0]*grad),axis=1))/(2*np.pi))

def magnetic(f):
    ss=np.r_[np.linspace(.01,.90,30),.95,.98,.99]
    qs=[qintegral(f,s,2) for s in ss];q95=qintegral(f,.95,4)
    rin,rout=f.d['midplane_radii_m'];R=(rin+rout)/2;a=(rout-rin)/2;B=11.52/R
    beta=2*MU0*f.d['pressure_integral_J']/f.d['core_volume_m3']/B**2
    result=dict(arm=f.arm,grid=f.n,q_min_sampled=min(qs),q95=q95,q95_quadrature_difference=abs(q95-qintegral(f,.95)),
        beta_toroidal=beta,beta_normalized=100*beta*a*B/(f.d['ip_A']/1e6),R_geometric_m=R,a_midplane_m=a,
        B_vacuum_at_Rgeom_T=B,F_squared_min_T2_m2=float(min(f.f2(np.linspace(0,1,501)))),
        physics_status='UNRESOLVED: q and beta are diagnostics, not MHD eigenmode tests')
    suffix='-controlled' if f.controlled else ''
    csvsave(f'{f.arm}-{f.n}{suffix}-q.csv',[dict(s=float(s),q=q) for s,q in zip(ss,qs)])
    return result

def vertical(f):
    select=np.abs(f.j)>1e-9;r=f.R[select];z=f.Z[select];j=f.j[select]
    # A rigid shift preserves R, J, dA. Plasma self-force integrates to zero;
    # fixed-coil field supplies Fz = -integral 2*pi*R*Jphi*BR_ext dA.
    def force(d):return float(np.sum(-2*np.pi*r*j*f.bpol(r,z+d,sp=f.vsp)[0])*f.da)
    zero=force(0);rows=[]
    for h in [.001,.005,.01]:
        fm,fp=force(-h),force(h);k=(fp-fm)/(2*h)
        rows.append(dict(arm=f.arm,grid=f.n,step_m=h,Fz_minus_N=fm,Fz_zero_N=zero,Fz_plus_N=fp,dFz_dz_N_per_m=k))
    return dict(arm=f.arm,grid=f.n,translations=rows,
        finding='DESTABILIZING' if rows[0]['dFz_dz_N_per_m']>0 else 'RESTORING',
        scope='Rigid fixed-current displacement; fixed external coils; no vessel eddy currents, feedback or plasma shape/current response. No physical growth rate inferred.')

def tau98(Ip,B,n,P,R,a,V):
    k=V/(2*np.pi**2*R*a*a)
    return .0562*(Ip/1e6)**.93*B**.15*(n/1e19)**.41*(P/1e6)**(-.69)*R**1.97*k**.78*(a/R)**.58*2.5**.19

def confinement(fields,kin):
    base=fields[0].d['pressure_integral_J'];rows=[];traces=[];central=[]
    for f in fields:
        rin,rout=f.d['midplane_radii_m'];R=(rin+rout)/2;a=(rout-rin)/2;B=11.52/R;V=f.d['core_volume_m3']
        W0=kin['W_thermal_J']*f.d['pressure_integral_J']/base
        tnet=tau98(f.d['ip_A'],B,kin['line_density_m3'],kin['P_transport_W'],R,a,V)
        ttot=tau98(f.d['ip_A'],B,kin['line_density_m3'],kin['P_heating_W'],R,a,V)
        central.append(dict(arm=f.arm,W_target_J=W0,tau98_transport_s=tnet,tau98_total_loss_s=ttot,
            H_required_transport=(W0/kin['P_transport_W'])/tnet,H_required_total_loss=(W0/kin['P_heating_W'])/ttot))
        for H,aux,rad in itertools.product([.7,1,1.3,1.6],[.8,1,1.2],[.8,1,1.2]):
            heat=kin['P_alpha_W']+kin['P_ohmic_W']+aux*kin['P_aux_W'];prad=rad*kin['P_radiation_W'];net=heat-prad
            assert net>0
            tau=H*tau98(f.d['ip_A'],B,kin['line_density_m3'],net,R,a,V)
            times=np.linspace(0,30,301);sol=solve_ivp(lambda t,w:[net-w[0]/tau],(0,30),[W0],t_eval=times,rtol=1e-10,atol=1e-2)
            assert sol.success
            analytic=net*tau+(W0-net*tau)*np.exp(-times/tau)
            error=float(np.max(np.abs(sol.y[0]-analytic))/W0)
            rows.append(dict(arm=f.arm,H_transport=H,aux_factor=aux,radiation_factor=rad,tau_s=tau,
                W_start_MJ=W0/1e6,W_30s_MJ=float(sol.y[0,-1]/1e6),W_equilibrium_MJ=net*tau/1e6,
                equilibrium_to_target=net*tau/W0,analytic_relative_error=error))
            if aux==rad==1:
                traces.extend(dict(arm=f.arm,H_transport=H,time_s=float(t),energy_MJ=float(w/1e6)) for t,w in zip(times,sol.y[0]))
    csvsave(f'confinement-sweep-{fields[0].n}.csv',rows);csvsave(f'confinement-traces-{fields[0].n}.csv',traces)
    return dict(cases=len(rows),central=central,max_analytic_relative_error=max(r['analytic_relative_error'] for r in rows),
        assumptions=['Fixed alpha, ohmic and radiative powers; no fusion-temperature feedback','Same line density and mean D-T mass in both arms','Thermal-energy target scales with pressure integral; baseline normalized to distinct JETTO thermal energy','H is an imposed transport-radiation-subtracted multiplier, not measured confinement'],
        physics_status='UNRESOLVED: sensitivity calculation, no turbulence or self-consistent burn simulation')

def walls():
    a=np.genfromtxt(ROOT/'source/SPR45_2D_Wall.csv',delimiter=',',skip_header=2)
    shapes=[]
    for i in range(3):
        p=a[:,2*i:2*i+2];p=p[np.isfinite(p).all(axis=1)]/1000
        if np.linalg.norm(p[0]-p[-1])>1e-9:p=np.vstack((p,p[0]))
        shapes.append(p)
    return shapes

def trace(f,offset,ds,wall):
    start=np.array([f.d['midplane_radii_m'][1]+offset,0.,0.]);y=start.copy();pts=[y.copy()]
    def rhs(v):
        br,bz=f.bpol(v[0],v[1]);bp=np.hypot(br,bz)
        return np.array([br/bp,bz/bp,np.hypot(bp,11.52/v[0])/bp])
    # Either direction is equivalent for exactly mirrored equilibria; use +B.
    hit=None
    for _ in range(int(50/ds)):
        k1=rhs(y);k2=rhs(y+.5*ds*k1);k3=rhs(y+.5*ds*k2);k4=rhs(y+ds*k3)
        new=y+ds*(k1+2*k2+2*k3+k4)/6
        crossing=LineString([y[:2],new[:2]]).intersection(wall)
        if not crossing.is_empty:
            candidates=[crossing] if crossing.geom_type=='Point' else list(getattr(crossing,'geoms',[]))
            candidates=[p for p in candidates if p.geom_type=='Point']
            if candidates:
                hit=min(candidates,key=lambda p:np.linalg.norm(np.array(p.coords[0])-y[:2]));xy=np.array(hit.coords[0]);frac=np.linalg.norm(xy-y[:2])/np.linalg.norm(new[:2]-y[:2]);y=np.r_[xy,y[2]+frac*(new[2]-y[2])];pts.append(y.copy());break
        y=new;pts.append(y.copy())
        if not (.5<y[0]<9 and -10<y[1]<10):break
    pts=np.array(pts);flux=f.sp.ev(pts[:,0],pts[:,1]);drift=float(np.max(np.abs(flux-flux[0]))/f.span)
    row=dict(arm=f.arm,grid=f.n,upstream_offset_m=offset,step_m=ds,hit=hit is not None,
        R_target_m=float(y[0]),Z_target_m=float(y[1]),connection_length_m=float(y[2]),normalized_flux_drift=drift)
    if hit is not None:
        segments=[]
        for w in walls():
            for lo,hi in zip(w[:-1],w[1:]):
                if np.linalg.norm(hi-lo)>1e-12:segments.append((LineString([lo,hi]).distance(hit),hi-lo))
        tangent=min(segments,key=lambda x:x[0])[1];normal=np.array([-tangent[1],tangent[0]])/np.linalg.norm(tangent)
        br,bz=f.bpol(y[0],y[1]);bn=abs(np.dot([br,bz],normal));br0,bz0=f.bpol(start[0],0);bpu=np.hypot(br0,bz0)
        row.update(Bnormal_target_T=float(bn),Bpol_upstream_T=float(bpu),area_expansion=float(bpu/bn),
            incidence_angle_deg=float(np.degrees(np.arcsin(bn/np.sqrt(br*br+bz*bz+(11.52/y[0])**2)))))
    return row,pts

def exhaust(fields,kin):
    wall=unary_union([LineString(w) for w in walls()]);traces=[];loads=[];paths={}
    for f in fields:
        for offset,ds in itertools.product([.001,.002,.005,.01,.02],[.01,.005]):
            row,p=trace(f,offset,ds,wall);traces.append(row)
            if ds==.005:paths[f'{f.arm}_{offset}']=p
            if not row['hit'] or ds!=.005:continue
            for lam,rad,share in itertools.product([.0018,.003,.006,.0127],[0,.5,.9],[.25,.5]):
                # Conserves power in a flux tube: q_target*dA_target = q_pol,u*2*pi*R_u*dx.
                rup=f.d['midplane_radii_m'][1]+offset
                q=share*kin['P_transport_W']*(1-rad)/(2*np.pi*rup*lam)*np.exp(-offset/lam)/row['area_expansion']
                loads.append(dict(arm=f.arm,grid=f.n,offset_m=offset,lambda_q_m=lam,SOL_radiation_fraction=rad,
                    power_fraction_one_target=share,projected_heat_MW_m2=float(q/1e6),above_10_MW_m2=bool(q>1e7)))
    n=fields[0].n
    csvsave(f'fieldline-traces-{n}.csv',traces);csvsave(f'heat-load-sweep-{n}.csv',loads);np.savez_compressed(OUT/f'fieldline-paths-{n}.npz',**paths)
    return dict(trace_count=len(traces),wall_hits=sum(t['hit'] for t in traces),load_samples=len(loads),
        sampled_max_MW_m2=max(r['projected_heat_MW_m2'] for r in loads) if loads else None,
        above_criterion=sum(r['above_10_MW_m2'] for r in loads),
        max_trace_flux_drift=max(t['normalized_flux_drift'] for t in traces),
        criterion_MW_m2=10,physics_status='CONDITIONAL SCREEN: sampled attached footprints; peak between samples, detachment, neutrals and transients unresolved')

def engineering(f,kin):
    mach=b.machine(f.ref,.1 if f.arm=='p9-inward' else 0);rows=[];coils=[]
    for circuit,current in zip(f.ref['c']['circuits'],f.ref['m']['icoil']['currents']):
        for co,pol in zip(circuit['coils'],circuit['polarity']):
            ff=co['fiesta_filament'];r=np.asarray(ff['r']);z=np.array(ff['z'],copy=True)
            if circuit['label']=='p9' and f.arm=='p9-inward':z-=np.sign(z.mean())*.1
            current=float(current) # polarity applied below per pack
            coils.append((co['label'],r,z,float(current*pol),ff))
    shapes=[];wall=unary_union([LineString(w) for w in walls()])
    for name,r,z,current,ff in coils:
        br,bz=f.bpol(r,z,sp=f.psp)
        for other,coil in mach.coils:
            if other!=name:br+=coil.Br(r,z);bz+=coil.Bz(r,z)
        weights=np.asarray(ff['turns']);Fz=float(np.sum(-2*np.pi*r*current*weights*br));Fr=float(np.sum(2*np.pi*r*current*weights*bz))
        loR=float(np.min(r-ff['dr']/2));hiR=float(np.max(r+ff['dr']/2));loZ=float(np.min(z-ff['dz']/2));hiZ=float(np.max(z+ff['dz']/2));shape=box(loR,loZ,hiR,hiZ);shapes.append((name,shape))
        area=float(np.sum(ff['dr']*ff['dz']));maxb=float(np.max(np.hypot(br,bz)));force=float(np.hypot(Fr,Fz))
        rows.append(dict(arm=f.arm,coil=name,equivalent_current_A=current,pack_area_m2=area,ampere_turn_density_A_m2=abs(current)/area,
            F_radial_generalized_N=Fr,F_vertical_N=Fz,resultant_generalized_N=force,
            external_poloidal_B_max_T=maxb,external_magnetic_pressure_Pa=maxb**2/(2*MU0),
            wall_outline_distance_m=shape.distance(wall),required_area_at_100MPa_m2=force/1e8,
            required_area_at_300MPa_m2=force/3e8,required_area_at_600MPa_m2=force/6e8))
    intersections=[dict(a=n1,b=n2,area_m2=p1.intersection(p2).area) for i,(n1,p1) in enumerate(shapes) for n2,p2 in shapes[i+1:] if p1.intersection(p2).area>1e-12]
    surf=f.surface(.999);clearance=LineString(surf).distance(wall)
    # Revolved supplied main-wall area; domes included separately, not a neutron transport solution.
    area=sum(float(np.sum(2*np.pi*(w[:-1,0]+w[1:,0])/2*np.linalg.norm(np.diff(w,axis=0),axis=1))) for w in walls())
    return dict(arm=f.arm,coils=rows,coil_pack_intersections=intersections,near_LCFS_to_wall_m=clearance,
        wall_area_m2=area,mean_neutron_wall_MW_m2=kin['P_neutron_W']/area/1e6,
        assumptions=['Radial force is generalized outward/hoop loading integrated around ring, not a net Cartesian force','Other packs plus plasma field only; self-force, TF field/structure, case and support load paths omitted','Pack-current density is equivalent ampere-turn density; winding current and fill factor not provided','Support-area sweep is load divided by assumed allowable stress, not stress FEA','Near-LCFS surface s=0.999, not exact separatrix; grid effects matter','Neutron power divided by revolved outline area assumes uniform deposition; no transport or damage calculation'],
        physics_status='UNRESOLVED: loads and geometry calculated, structural/thermal/neutronic feasibility not established')

def electric(kin):
    rows=[]
    for et,ew,par in itertools.product([.30,.35,.40,.45],[.30,.40,.50,.60,.70],[50,100,150,200]):
        thermal=(kin['P_fusion_total_W']+kin['P_aux_W']+kin['P_ohmic_W'])/1e6
        gross=et*thermal;draw=(kin['P_aux_W']+kin['P_ohmic_W'])/1e6/ew
        rows.append(dict(thermal_efficiency=et,heating_wallplug_efficiency=ew,other_electric_MW=par,
            gross_electric_MW=gross,heating_electric_MW=draw,net_electric_MW=gross-draw-par))
    csvsave('electric-sweep.csv',rows)
    return dict(cases=len(rows),minimum_net_MW=min(r['net_electric_MW'] for r in rows),maximum_net_MW=max(r['net_electric_MW'] for r in rows),positive_cases=sum(r['net_electric_MW']>0 for r in rows),
        assumptions=['Prescribed source fusion power, not predicted by our equilibrium model','Complete recovery of plasma and neutron heat; unity blanket multiplication','Assumed efficiency and parasitic ranges, not specified plant hardware','No tritium breeding or availability prediction'],physics_status='UNRESOLVED: accounting sensitivity, not net-electric demonstration')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--n',type=int,default=257);parser.add_argument('--part',choices=['all','core','exhaust','engineering'],default='all');a=parser.parse_args()
    start=time.time();kin=sources();fields=[Field(arm,a.n) for arm in ['baseline','p9-inward']]
    result=dict(grid=a.n,part=a.part,protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if a.part in ['core','all']:
        result['magnetic']=[magnetic(f) for f in fields];result['vertical']=[vertical(f) for f in fields]
        result['confinement']=confinement(fields,kin);result['electric']=electric(kin)
    if a.part in ['exhaust','all']:result['exhaust']=exhaust(fields,kin)
    if a.part in ['engineering','all']:result['engineering']=[engineering(f,kin) for f in fields]
    result['seconds']=time.time()-start;save(f'screens-{a.n}-{a.part}.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='engineering'},indent=2),flush=True)
if __name__=='__main__':main()
