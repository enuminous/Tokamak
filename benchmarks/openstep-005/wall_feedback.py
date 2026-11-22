"""Synthetic electromechanical wall/coil controls, never a STEP eigenmode result.

State x = (z, v, I_wall, I_control). Equations:
 m dv/dt = k z - d v + g_w I_wall + g_c I_control
 L_w dI_wall/dt = -R_w I_wall - g_w v
 L_c dI_control/dt = u - R_c I_control - g_c v
 u = -Kp z - Kd v (optionally saturated).
The reciprocal g terms make the passive energy balance explicit.
"""
from copy import deepcopy
import json
import re
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from common import ROOT, stamp, save, csvsave, check, inventory, sha


def matrix(p):
    m,k,d,gw,gc,Lw,Lc,Rw,Rc = [p[x] for x in ['mass_kg','stiffness_N_m','damping_N_s_m','g_wall_N_A',
                                                'g_coil_N_A','L_wall_H','L_coil_H','R_wall_ohm','R_coil_ohm']]
    if min(m,Lw,Lc) <= 0 or min(d,Rw,Rc) < 0:
        raise ValueError('Mass/inductance must be positive and passive loss nonnegative')
    return np.array([[0,1,0,0],[k/m,-d/m,gw/m,gc/m],
                     [0,-gw/Lw,-Rw/Lw,0],[-p['Kp_V_m']/Lc,-(gc+p['Kd_V_s_m'])/Lc,0,-Rc/Lc]], float)


def energy(p, x):
    return .5*(p['mass_kg']*x[...,1]**2-p['stiffness_N_m']*x[...,0]**2+
               p['L_wall_H']*x[...,2]**2+p['L_coil_H']*x[...,3]**2)


def modes(a):
    return sorted(np.linalg.eigvals(a), key=lambda x:(round(x.real,10),x.imag))


def serialize_modes(values):
    return [dict(real=float(v.real), imaginary=float(v.imag)) for v in values]


def validate_inputs(data):
    """Completeness gate only. A supplied hash is not evidence of calibration."""
    missing = []
    if data.get('evidence_class') != 'calibrated_device_inputs':
        missing.append('evidence_class: calibrated device inputs required')
    for key in ['equilibrium','conductor_geometry','material_resistivity','electrical_connections',
                'active_coils','plasma_response','sensors','actuators','controller']:
        value = data.get(key)
        if not isinstance(value, dict):
            missing.append(key+': missing input record')
            continue
        for field in ['source_ref','sha256','units','model']:
            if not isinstance(value.get(field),str) or not value[field].strip():
                missing.append(key+'.'+field+': required')
        if value.get('sha256') and not re.fullmatch('[a-f0-9]{64}',value['sha256']):
            missing.append(key+'.sha256: invalid hash')
        if value.get('calibration_status') != 'reviewed':
            missing.append(key+'.calibration_status: review unresolved')
    geometry = data.get('conductor_geometry') or {}
    if geometry.get('model') not in ['axisymmetric_volume_mesh','thin_shell_mesh_with_thickness']:
        missing.append('conductor_geometry.model: an outline is not a conductor')
    for key in ['resistivity_ohm_m','temperature_K']:
        value = (data.get('material_resistivity') or {}).get(key)
        if not isinstance(value, (int,float)) or isinstance(value,bool) or not np.isfinite(value) or value <= 0:
            missing.append('material_resistivity.'+key+': positive finite value required')
    if geometry.get('model') == 'thin_shell_mesh_with_thickness':
        t = geometry.get('thickness_m')
        if not isinstance(t,(int,float)) or isinstance(t,bool) or not np.isfinite(t) or t <= 0:
            missing.append('conductor_geometry.thickness_m: positive finite value required')
    for section, keys in [('actuators',['voltage_limit_V','current_limit_A','bandwidth_Hz']),
                          ('sensors',['sample_rate_Hz'])]:
        for key in keys:
            val = (data.get(section) or {}).get(key)
            if not isinstance(val,(int,float)) or isinstance(val,bool) or not np.isfinite(val) or val <= 0:
                missing.append(section+'.'+key+': positive finite value required')
    for section in ['sensors','controller']:
        val = (data.get(section) or {}).get('latency_s')
        if not isinstance(val,(int,float)) or isinstance(val,bool) or not np.isfinite(val) or val < 0:
            missing.append(section+'.latency_s: finite nonnegative value required')
    return dict(schema_complete=not missing, blockers=missing,
                physical_validation='NOT ESTABLISHED BY THIS SCHEMA CHECK')


def pending_inputs():
    path = next(p for p,_ in inventory() if p.stem == 'shift-+000mm-257')
    outline = ROOT.parent/'openstep-002/source/SPR45_2D_Wall.csv'
    data = dict(evidence_class='incomplete_device_inputs',
        equilibrium=dict(source_ref=str(path.relative_to(ROOT.parent.parent)), sha256=sha(path),
                         units='m, Wb/rad, T', model='frozen_axisymmetric_FreeGS_equilibrium',
                         calibration_status='numerically_verified_only'),
        wall_outline=dict(source_ref=str(outline.relative_to(ROOT.parent.parent)),sha256=sha(outline),
                          units='mm',model='first_wall_outline_only'),
        conductor_geometry=None, material_resistivity=None, electrical_connections=None,
        active_coils=dict(source_ref='benchmarks/openstep-001/source/coilset.mat',
                         sha256=sha(ROOT.parent/'openstep-001/source/coilset.mat'),units='m, A turns',
                         model='fixed_filaments_without_dynamic_circuit',calibration_status='unresolved'),
        plasma_response=None,sensors=None,actuators=None,controller=None)
    (ROOT/'device-inputs.json').write_text(json.dumps(data,indent=2)+'\n')
    return data


def main():
    result, checks, cases, samples = stamp('synthetic_wall_feedback'), [], [], []
    p=dict(mass_kg=2.,stiffness_N_m=8.,damping_N_s_m=0.,g_wall_N_A=4.,g_coil_N_A=0.,
           L_wall_H=1.,L_coil_H=.5,R_wall_ohm=.5,R_coil_ohm=1.,Kp_V_m=0.,Kd_V_s_m=0.)
    # Closed-form limits of the same physical equations, not fitted target values.
    no_wall=dict(p,g_wall_N_A=0.)
    ev=modes(matrix(no_wall))
    check(checks,'no_wall_growth',abs(max(v.real for v in ev)-np.sqrt(p['stiffness_N_m']/p['mass_kg'])) < 1e-12)
    cases.append(dict(name='synthetic_no_wall',parameters=no_wall,eigenvalues=serialize_modes(ev)))
    ideal=dict(p,R_wall_ohm=0.)
    ev=modes(matrix(ideal))
    omega=np.sqrt((p['g_wall_N_A']**2/p['L_wall_H']-p['stiffness_N_m'])/p['mass_kg'])
    check(checks,'ideal_wall_oscillation',abs(max(abs(v.imag) for v in ev)-omega) < 1e-12)
    check(checks,'ideal_wall_no_positive_growth',max(v.real for v in ev) < 1e-12)
    cases.append(dict(name='synthetic_ideal_wall',parameters=ideal,eigenvalues=serialize_modes(ev)))
    ev=modes(matrix(p))
    cubic=np.roots([1,p['R_wall_ohm']/p['L_wall_H'],
                    p['g_wall_N_A']**2/(p['mass_kg']*p['L_wall_H'])-p['stiffness_N_m']/p['mass_kg'],
                    -p['stiffness_N_m']*p['R_wall_ohm']/(p['mass_kg']*p['L_wall_H'])])
    mismatch=max(min(abs(v-e) for e in ev) for v in cubic)
    check(checks,'resistive_wall_characteristic_polynomial',float(mismatch)<1e-11,float(mismatch),1e-11)
    check(checks,'finite_resistance_retains_growth',max(v.real for v in ev)>0)
    cases.append(dict(name='synthetic_resistive_wall',parameters=p,eigenvalues=serialize_modes(ev)))
    # Passive energy control with positive total energy (restoring k < 0).
    passive=dict(p,stiffness_N_m=-4.,damping_N_s_m=.2,g_wall_N_A=1.,g_coil_N_A=.6,
                 L_wall_H=.8,R_wall_ohm=.4,R_coil_ohm=.3)
    a=matrix(passive)
    rng=np.random.default_rng(5005)
    x=rng.normal(size=(100,4));dx=x@a.T
    derivative=(-passive['stiffness_N_m']*x[:,0]*dx[:,0]+passive['mass_kg']*x[:,1]*dx[:,1]+
                passive['L_wall_H']*x[:,2]*dx[:,2]+passive['L_coil_H']*x[:,3]*dx[:,3])
    dissipation=-passive['damping_N_s_m']*x[:,1]**2-passive['R_wall_ohm']*x[:,2]**2-passive['R_coil_ohm']*x[:,3]**2
    error=float(np.max(abs(derivative-dissipation)))
    check(checks,'passive_energy_balance_100_states',error<1e-12,error,1e-12)
    t=np.linspace(0,40,801);x0=np.array([.01,0.,0.,0.])
    sol=solve_ivp(lambda t,x:a@x,(t[0],t[-1]),x0,t_eval=t,method='DOP853',rtol=1e-11,atol=1e-13)
    e=energy(passive,sol.y.T)
    check(checks,'passive_energy_nonincreasing',float(np.max(np.diff(e))) < 1e-12)
    # Feedback and deliberately reversed-sign controls.
    for name,kp,kd in [('stable_feedback',10.,10.),('reversed_feedback',-10.,-10.),('position_only',10.,0.)]:
        par=dict(p,g_coil_N_A=2.,damping_N_s_m=.2,Kp_V_m=kp,Kd_V_s_m=kd)
        a=matrix(par);ev=modes(a);growth=max(v.real for v in ev)
        check(checks,name+':expected_stability',growth<0 if name=='stable_feedback' else growth>0,float(growth),0.)
        cases.append(dict(name='synthetic_'+name,parameters=par,eigenvalues=serialize_modes(ev)))
        end=40 if name=='stable_feedback' else 2
        tt=np.linspace(0,end,401)
        sol=solve_ivp(lambda t,x:a@x,(0,end),x0,t_eval=tt,method='DOP853',rtol=1e-11,atol=1e-13)
        exact=np.array([expm(a*time)@x0 for time in tt])
        error=float(np.max(abs(sol.y.T-exact)))
        check(checks,name+':time_vs_matrix_exponential',sol.success and error<1e-9,error,1e-9)
        for time,state in zip(tt,sol.y.T):
            samples.append(dict(case='synthetic_'+name,time_s=float(time),z_m=float(state[0]),v_m_s=float(state[1]),
                                wall_current_A=float(state[2]),coil_current_A=float(state[3]),
                                voltage_V=float(-kp*state[0]-kd*state[1])))
    # Saturated actuation is an explicitly nonlinear synthetic stress case.
    par=dict(p,g_coil_N_A=2.,damping_N_s_m=.2,Kp_V_m=10.,Kd_V_s_m=10.)
    a=matrix(par);voltage_limit=.02
    def rhs(t,x):
        raw=-par['Kp_V_m']*x[0]-par['Kd_V_s_m']*x[1]
        dx=a@x
        dx[3]+=(np.clip(raw,-voltage_limit,voltage_limit)-raw)/par['L_coil_H']
        return dx
    tt=np.linspace(0,2,401)
    sol=solve_ivp(rhs,(0,2),x0,t_eval=tt,method='DOP853',rtol=1e-11,atol=1e-13)
    raw=-10*sol.y[0]-10*sol.y[1];voltage=np.clip(raw,-voltage_limit,voltage_limit)
    check(checks,'saturation_active',bool(np.any(abs(raw)>voltage_limit)))
    check(checks,'saturation_respects_voltage_limit',sol.success and float(np.max(abs(voltage)))<=voltage_limit)
    for time,state,u in zip(tt,sol.y.T,voltage):
        samples.append(dict(case='synthetic_saturated',time_s=float(time),z_m=float(state[0]),v_m_s=float(state[1]),
                            wall_current_A=float(state[2]),coil_current_A=float(state[3]),voltage_V=float(u)))
    # Bounded synthetic gain map; no gain is transferred to the tokamak.
    gains=[]
    for kp in np.linspace(-5,20,26):
        for kd in np.linspace(0,20,21):
            growth=float(np.max(np.linalg.eigvals(matrix(dict(par,Kp_V_m=kp,Kd_V_s_m=kd))).real))
            gains.append(dict(Kp_V_m=float(kp),Kd_V_s_m=float(kd),max_real_eigenvalue_s_inverse=growth,asymptotically_stable=growth < -1e-10))
    pending=pending_inputs();readiness=validate_inputs(pending)
    check(checks,'missing_device_inputs_rejected',not readiness['schema_complete'])
    # Schema fixture is explicitly invented and never a calibrated data claim.
    fixture={'evidence_class':'calibrated_device_inputs'}
    for key in ['equilibrium','conductor_geometry','material_resistivity','electrical_connections','active_coils',
                'plasma_response','sensors','actuators','controller']:
        fixture[key]=dict(source_ref='synthetic://validator-fixture',sha256='0'*64,units='fixture-SI',
                          model='synthetic_fixture',calibration_status='reviewed')
    fixture['conductor_geometry'].update(model='thin_shell_mesh_with_thickness',thickness_m=.01)
    fixture['material_resistivity'].update(resistivity_ohm_m=1e-6,temperature_K=300.)
    fixture['actuators'].update(voltage_limit_V=1.,current_limit_A=1.,bandwidth_Hz=1.)
    fixture['sensors'].update(sample_rate_Hz=100.,latency_s=.001)
    fixture['controller'].update(latency_s=.001)
    check(checks,'complete_synthetic_schema_fixture_accepted',validate_inputs(fixture)['schema_complete'])
    mutations=[('conductor_geometry','thickness_m',-1.),('material_resistivity','resistivity_ohm_m',0.),
               ('material_resistivity','temperature_K',float('nan')),('controller','latency_s',-1.),
               ('actuators','voltage_limit_V',0.),('sensors','sample_rate_Hz',False),
               ('conductor_geometry','model','first_wall_outline'),('equilibrium','sha256','bad'),
               ('plasma_response','calibration_status','unresolved')]
    for section,key,value in mutations:
        bad=deepcopy(fixture);bad[section][key]=value
        check(checks,'invalid_input_rejected:'+section+'.'+key,not validate_inputs(bad)['schema_complete'])
    bad=deepcopy(fixture);bad['evidence_class']='synthetic'
    check(checks,'synthetic_inputs_rejected_as_device_evidence',not validate_inputs(bad)['schema_complete'])
    try:
        matrix(dict(p,L_wall_H=-1.));rejected=False
    except ValueError:
        rejected=True
    check(checks,'negative_inductance_rejected',rejected)
    result.update(evidence_class='SYNTHETIC_IMPLEMENTATION_CONTROLS_ONLY',checks=checks,cases=cases,
                  device_readiness=readiness,device_eigenmode_status='NOT RUN / UNRESOLVED',
                  gain_grid_cases=len(gains),stable_gain_cases=sum(x['asymptotically_stable'] for x in gains),
                  saturated_final_z_m=float(sol.y[0,-1]),seed=5005)
    save('wall-feedback.json',result);csvsave('synthetic-time-traces.csv',samples);csvsave('synthetic-gain-map.csv',gains)
    print(json.dumps({s:sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}),flush=True)


if __name__=='__main__':
    main()
