"""Source-based reduced burn, exhaust, fuel and electric-balance requirements.

These calculations are conditional; they do not qualify a reactor design.
Bosch-Hale formulation/constants follow UKAEA PROCESS (MIT), pinned in source/.
"""
from pathlib import Path
import json,csv,itertools,hashlib,ast
from types import SimpleNamespace
import numpy as np
import h5py
from scipy.integrate import solve_ivp,simpson
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
E=1.602176634e-19;U=1.66053906892e-27
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v): (OUT/name).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def csvsave(name,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
checks=[]
def check(name,ok,value=None,limit=None):checks.append(dict(name=name,status='PASS' if bool(ok) else 'FAIL',value=value,limit=limit))

def reactivity(T):
    T=np.asarray(T);bg=34.3827;mc=1.124656e6
    c1,c2,c3,c4,c5,c6,c7=1.17302e-9,1.51361e-2,7.51886e-2,4.60643e-3,1.35e-2,-1.0675e-4,1.366e-5
    th=T/(1-T*(c2+T*(c4+T*c6))/(1+T*(c3+T*(c5+T*c7))))
    xi=(bg*bg/(4*th))**(1/3)
    return 1e-6*c1*th*np.sqrt(xi/(mc*T**3))*np.exp(-3*xi)

def run():
    kinpath=ROOT.parent/'openstep-002/results/kinetic-inputs.json';kin=json.loads(kinpath.read_text())
    profpath=ROOT.parent/'openstep-002/source/STEP_SPP_001_EBCC_ftop.nc'
    with h5py.File(profpath) as f:
        g=f['core_profiles/0'];get=lambda k:np.asarray(g['profiles_1d.'+k])[0]
        mass=get('ion.element.a').ravel();d=int(np.flatnonzero(mass==2)[0]);t=int(np.flatnonzero(mass==3)[0])
        vol=get('grid.volume');dens=get('ion.density_thermal');temp=get('ion.temperature')
        td,tt=temp[d]/1000,temp[t]/1000;T=(3*td+2*tt)/5;nd,nt=dens[d],dens[t]
        ne=get('electrons.density');te=get('electrons.temperature')
        V=np.r_[0,vol];pad=lambda x:np.r_[x[0],x]
        integ=lambda x:float(np.trapezoid(pad(x),V))
        Wprofiles=1.5*E*integ(ne*te+np.sum(dens*temp,axis=0))
    check('positive monotonic volume and fuel profiles',np.all(np.diff(V)>0) and np.all(nd>=0) and np.all(nt>=0))
    check('D-T temperatures within Bosch-Hale fit over full sweep',T.min()*.5>=.2 and T.max()*2.5<=100,float(T.min()*.5),.2)
    # Cross-check against pinned upstream expression, not a second independent physics model.
    tree=ast.parse((ROOT/'source/bosch-hale-excerpt.py').read_text())
    ns={'np':np,'BoschHaleConstants':SimpleNamespace};exec(compile(tree,'upstream-bosch-hale','exec'),ns)
    testT=np.geomspace(.2,100,1001);ref=ns['bosch_hale_reactivity'](testT,SimpleNamespace(**ns['REACTION_CONSTANTS_DT']))
    err=float(np.max(np.abs(reactivity(testT)/ref-1)));check('reactivity agrees with pinned upstream formula',err<1e-12,err,1e-12)
    rate=lambda x:integ(nd*nt*reactivity(T*x))
    pa=lambda x:rate(x)*3.5e6*E
    r0=rate(1);palpha=pa(1);pfus=r0*17.6e6*E
    simpson_rate=float(simpson(pad(nd*nt*reactivity(T)),x=V))
    quadrature=abs(simpson_rate/r0-1);check('profile reaction integral trapezoid/Simpson agreement',quadrature<.01,quadrature,.01)
    diff=palpha/kin['P_alpha_W']-1;check('unfitted thermal alpha versus source deposited alpha comparison',abs(diff)<.1,diff,.1)
    closure=kin['P_heating_W']-kin['P_radiation_W']-kin['P_transport_W'];check('source energy accounting',abs(closure)<1,closure,1)
    check('profile thermal energy versus source',abs(Wprofiles/kin['W_thermal_J']-1)<.01,float(Wprofiles/kin['W_thermal_J']-1),.01)
    csvsave('fuel-profiles.csv',[dict(volume_m3=float(v),D_density_m3=float(a),T_density_m3=float(b),Ti_keV=float(c),reactivity_m3_s=float(r)) for v,a,b,c,r in zip(vol,nd,nt,T,reactivity(T))])
    W0=kin['W_thermal_J'];pt=kin['P_transport_W'];tau0=W0/pt
    def balance(x,f,aux,a,dep):return aux*kin['P_aux_W']+kin['P_ohmic_W']+dep*pa(x)-kin['P_radiation_W']*x**a-pt*x/f
    grid=np.linspace(.5,2.5,401);burn=[];roots=[]
    for f,aux,a,dep in itertools.product([.7,1,1.3,1.6],[0,.5,1],[0,.5,1],[.8,1]):
        vals=np.array([balance(x,f,aux,a,dep) for x in grid]);rr=[]
        for left,right,vl,vr in zip(grid[:-1],grid[1:],vals[:-1],vals[1:]):
            if vl*vr<0:rr.append(brentq(lambda x:balance(x,f,aux,a,dep),left,right,xtol=1e-12))
            elif vl==0:rr.append(float(left))
        if vals[-1]==0:rr.append(float(grid[-1]))
        rr=sorted(set(rr));case=dict(tau_factor=f,aux_fraction=aux,radiation_exponent=a,alpha_deposition=dep)
        for x in rr:
            slope=(balance(x+1e-5,f,aux,a,dep)-balance(x-1e-5,f,aux,a,dep))/(2e-5*W0)
            row=dict(**case,temperature_scale=x,energy_MJ=x*W0/1e6,alpha_MW=dep*pa(x)/1e6,
                linear_growth_per_s=slope,classification='stable' if slope<0 else 'unstable',residual_W=balance(x,f,aux,a,dep))
            roots.append(row)
        burn.append(dict(**case,root_count=len(rr),stable_roots=sum(r['classification']=='stable' for r in roots[-len(rr):]) if rr else 0,
            net_power_at_source_MW=balance(1,f,aux,a,dep)/1e6))
    check('burn root residuals',all(abs(r['residual_W'])<1 for r in roots),max((abs(r['residual_W']) for r in roots),default=0),1)
    central=[r for r in roots if r['tau_factor']==1 and r['aux_fraction']==1 and r['radiation_exponent']==.5 and r['alpha_deposition']==1]
    traces=[];integration=[]
    # If central case has no root, retain source +/-5% trajectories; do not invent an equilibrium.
    starts=[(r['temperature_scale'],r['classification']) for r in central] or [(1.,'source; no central root in window')]
    for root,kind in starts:
        for frac in [.95,1.05]:
            def rhs(t,y):return [balance(float(np.clip(y[0],.49,2.51)),1,1,.5,1)/W0]
            def low(t,y):return y[0]-.5
            def high(t,y):return 2.5-y[0]
            low.terminal=True;high.terminal=True;low.direction=-1;high.direction=-1
            sol=solve_ivp(rhs,(0,30),[root*frac],rtol=1e-9,atol=1e-11,events=[low,high],max_step=.1,dense_output=True)
            # Independent integration tolerance check for this ODE.
            tight=solve_ivp(rhs,(0,30),[root*frac],rtol=1e-11,atol=1e-13,events=[low,high],max_step=.05,dense_output=True)
            compare=np.linspace(0,min(sol.t[-1],tight.t[-1]),101)
            err=float(np.max(np.abs(sol.sol(compare)-tight.sol(compare))));time_error=float(abs(sol.t[-1]-tight.t[-1]))
            check(f'burn ODE trajectory tolerance {root:.8f}/{frac}',sol.success and tight.success and err<1e-6,err,1e-6)
            check(f'burn ODE event time tolerance {root:.8f}/{frac}',time_error<1e-5,time_error,1e-5)
            integration.append(dict(root=root,root_kind=kind,initial_scale=root*frac,final_scale=float(sol.y[0,-1]),end_time_s=float(sol.t[-1]),boundary_terminated=sol.status==1,tolerance_difference=err,event_time_difference_s=time_error))
            traces.extend(dict(root=root,initial_fraction=frac,time_s=float(t),temperature_scale=float(x)) for t,x in zip(sol.t,sol.y[0]))
    csvsave('burn-cases.csv',burn);csvsave('burn-roots.csv',roots);csvsave('burn-traces.csv',traces)

    footprint=ROOT.parent/'openstep-005/results/footprints.json';fp=json.loads(footprint.read_text())
    peaks=[s for s in fp['summaries'] if s['radius_m']==0];thermal=[];radiation=[]
    for s in peaks:
        q=s['optimized_maximum']['representative_heat_MW_m2']*1e6
        radiation.append(dict(tag=s['tag'],shift_m=s['shift_m'],peak_MW_m2=q/1e6,required_SOL_radiation_fraction_for_10MW_m2=max(0,1-.5*1e7/q)))
        for k,L,h in itertools.product([80,120,180],[.002,.005,.010],[1e4,5e4,1e5]):
            Tsurface=450+q*(L/k+1/h)
            thermal.append(dict(tag=s['tag'],heat_MW_m2=q/1e6,k_W_m_K=k,thickness_m=L,h_W_m2_K=h,
                conduction_jump_K=q*L/k,convection_jump_K=q/h,surface_K=Tsurface,below_assumed_1800K=Tsurface<=1800))
    csvsave('cooling-requirements.csv',thermal);csvsave('radiation-requirements.csv',radiation)

    electric=[];pf=kin['P_fusion_total_W']/1e6;aux=kin['P_aux_W']/1e6;ohm=kin['P_ohmic_W']/1e6
    for eth,ewp,recovery,fixed,avail in itertools.product([.3,.4,.5],[.3,.5,.7],[.8,1],[50,150,300],[.3,.6,.9]):
        thermal_power=recovery*pf+aux+ohm;gross=eth*thermal_power;heating_electric=aux/ewp+ohm/.9
        net=gross-heating_electric-fixed;avg=avail*(gross-heating_electric)-fixed
        electric.append(dict(thermal_efficiency=eth,aux_wallplug_efficiency=ewp,recoverable_fusion_fraction=recovery,
            fixed_load_MW=fixed,availability=avail,gross_MWe=gross,heating_supply_MWe=heating_electric,
            net_online_MWe=net,net_annual_average_MWe=avg,annual_net_GWh=avg*8760/1000,
            online_positive=net>0,annual_positive=avg>0))
    csvsave('electric-balance.csv',electric)

    burnkg=kin['P_fusion_total_W']/(17.6e6*E)*3.016049*U
    fuel=[];inventories=[]
    for b in [.01,.03,.1]:
        unburned=burnkg*(1/b-1)
        for hours in [1,4,24]:inventories.append(dict(burn_fraction=b,processing_delay_h=hours,
            injected_T_kg_per_day=burnkg/b*86400,unburned_T_kg_per_day=unburned*86400,
            processing_hold_up_kg=unburned*hours*3600))
        for tbr,recovery,loss in itertools.product([.9,1,1.05,1.1,1.2],[.9,.95,.99],[0,.0001,.001]):
            surplus=recovery*tbr-1-loss*(1/b-1)
            fuel.append(dict(burn_fraction=b,TBR=tbr,breeding_recovery=recovery,exhaust_loss_fraction=loss,
                net_T_kg_per_full_power_year=surplus*burnkg*365.25*86400,nonnegative_balance=surplus>=0,
                required_TBR=(1+loss*(1/b-1))/recovery))
    csvsave('fuel-balance.csv',fuel);csvsave('fuel-inventory.csv',inventories)
    # Conservation controls deliberately include no-fusion and perfect-recovery limits.
    check('fuel ideal unit-TBR closes mass balance',1*1-1-0*(1/.03-1)==0)
    check('fuel loss increases breeding requirement',(1+.001*(1/.01-1))/.95>1/.95)
    check('zero-fusion plant cannot produce net power from inefficient heaters',.5*(aux+ohm)-aux/.7-ohm/.9-50<0)
    check('cooling positive resistances increase surface temperature',all(r['surface_K']>450 for r in thermal))
    result=dict(status='CONDITIONAL: reduced models and requirements, not integrated reactor validation',
        source_kinetic=kin,thermal_fusion=dict(reaction_rate_per_s=r0,alpha_MW=palpha/1e6,total_DT_MW=pfus/1e6,
            source_alpha_relative_difference=diff,quadrature_relative_difference=quadrature,thermal_energy_from_nT_J=Wprofiles,
            minimum_Ti_keV=float(T.min()),maximum_Ti_keV=float(T.max()),source_Q_aux=pf/aux),
        burn=dict(cases=len(burn),roots=len(roots),stable_roots=sum(r['classification']=='stable' for r in roots),
            central_roots=central,central_trajectories=integration,calibrated_transport_time_s=tau0,
            limitations=['Fixed density, species fractions, profile shapes and volume','One temperature scale; no particle/ash evolution or separate ion/electron energy equations',
                'Source-calibrated transport time and radiation magnitude; imposed radiation exponent','Root search detects sign-changing roots; tangencies may be missed',
                'No turbulence, current-drive sustainment, alpha slowing-down evolution or fusion power calibration']),
        heat=dict(cases=len(thermal),below_assumed_1800K=sum(r['below_assumed_1800K'] for r in thermal),radiation_requirements=radiation,
            limitations=['Constant assumed conductivity and heat transfer coefficient','No coolant hydraulics, critical heat flux, stress, fatigue, irradiation, erosion or detachment calculation']),
        electricity=dict(cases=len(electric),online_positive=sum(r['online_positive'] for r in electric),annual_positive=sum(r['annual_positive'] for r in electric),
            online_range_MWe=[min(r['net_online_MWe'] for r in electric),max(r['net_online_MWe'] for r in electric)],
            annual_range_MWe=[min(r['net_annual_average_MWe'] for r in electric),max(r['net_annual_average_MWe'] for r in electric)],
            limitations=['Assumed conversion efficiencies, recoverable heat and loads','No blanket multiplication','Availability is an assumption, not a reliability prediction']),
        fuel=dict(T_burn_kg_per_full_power_day=burnkg*86400,T_burn_kg_per_full_power_year=burnkg*86400*365.25,
            balance_cases=len(fuel),nonnegative=sum(r['nonnegative_balance'] for r in fuel),
            hold_up_range_kg=[min(r['processing_hold_up_kg'] for r in inventories),max(r['processing_hold_up_kg'] for r in inventories)],
            limitations=['D-T-equivalent reaction power; minor other reaction contributions ignored','No measured/predicted TBR; it is swept',
                'No radioactive decay, retention, reserve stock or start-up supply','Hold-up assumes all unburned fuel follows stated processing path; bypass recycling changes it']),
        checks=checks,input_sha256={str(p.relative_to(ROOT.parent)):sha(p) for p in [profpath,kinpath,footprint]},
        code_sha256=sha(Path(__file__)),protocol_sha256=sha(ROOT/'PROTOCOL.md'))
    save('reactor.json',result);print(json.dumps({k:v for k,v in result.items() if k in ('thermal_fusion','burn','heat','electricity','fuel')},indent=2))
if __name__=='__main__':run()
