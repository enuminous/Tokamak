"""Assemble evidence without promoting surrogate checks to feasibility claims."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OLD=ROOT.parent/'openstep-001/results'
COLORS={'baseline':'#007a78','p9-inward':'#a95717'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.bbox':'tight','axes.titleweight':'bold'})

def read(p):return json.loads(p.read_text())
def rows(name):return list(csv.DictReader((OUT/name).open()))
def report_for(arm,n,kind='symmetric'):
    p=OUT/f'{arm}-{n}-{kind}.json'
    if not p.exists():p=OLD/p.name
    return read(p) if p.exists() else None
def screen(n,part):
    p=OUT/f'screens-{n}-{part}.json'
    if not p.exists():p=OUT/f'screens-{n}-all.json'
    return read(p)
def figsave(fig,name):
    fig.savefig(OUT/f'{name}.svg',facecolor='white');fig.savefig(OUT/f'{name}.png',dpi=160,facecolor='white');plt.close(fig)

def main():
    fine=513 if all((report_for(a,513) or {}).get('converged') for a in COLORS) and (OUT/'screens-513-all.json').exists() else 257
    previous=257 if fine==513 else 129
    core=screen(fine,'core');eng=screen(fine,'engineering');exhaust=screen(fine,'exhaust')
    numerical=[]
    for arm in COLORS:
        for n in [129,257,513]:
            r=report_for(arm,n)
            if r:numerical.append(dict(arm=arm,grid=n,converged=r.get('converged',False),defect=r.get('final_defect'),seconds=r.get('seconds')))
    def metrics(r):
        d=r['final'];xp=min(d['xpoints'],key=lambda x:abs(x[1]-6.1))
        return dict(axis_R_m=d['axis'][0],upper_X_R_m=xp[0],upper_X_Z_m=xp[1],Ip_A=d['ip_A'],pressure_axis_Pa=d['pressure_axis_Pa'],volume_m3=d['core_volume_m3'])
    base=metrics(report_for('baseline',fine));mod=metrics(report_for('p9-inward',fine));oldb=metrics(report_for('baseline',previous));oldm=metrics(report_for('p9-inward',previous))
    effects={k:dict(baseline=base[k],modified=mod[k],delta=mod[k]-base[k],observed_grid_variation=abs(base[k]-oldb[k])+abs(mod[k]-oldm[k]),
        resolved=abs(mod[k]-base[k])>abs(base[k]-oldb[k])+abs(mod[k]-oldm[k])) for k in base}
    controls=[]
    for arm in COLORS:
        for n in [129,257]:
            r=report_for(arm,n,'controlled')
            if r:controls.append(dict(arm=arm,grid=n,converged=r.get('converged',False),defect=r.get('final_defect'),metrics=metrics(r) if r.get('converged') else None,
                current_relative_error=r.get('current_relative_error'),pressure_relative_error=r.get('pressure_relative_error')))
    traces=rows(f'fieldline-traces-{fine}.csv');loads=rows(f'heat-load-sweep-{fine}.csv')
    representative=[r for r in loads if float(r['offset_m'])==.001 and float(r['lambda_q_m'])==.006 and float(r['power_fraction_one_target'])==.25]
    oldcore=screen(previous,'core')
    force_now=[x['translations'][0]['dFz_dz_N_per_m'] for x in core['vertical']]
    force_old=[x['translations'][0]['dFz_dz_N_per_m'] for x in oldcore['vertical']]
    force_delta=force_now[1]-force_now[0];force_variation=sum(abs(a-b) for a,b in zip(force_now,force_old))
    summary=dict(id='OPENSTEP-002',date='2026-11-20',selected_grid=fine,previous_grid=previous,
        reference_baseline_core_flux_nrmse=report_for('baseline',fine)['final']['core_flux_nrmse'],
        vertical_stiffness_change=dict(delta_N_per_m=force_delta,observed_grid_variation_N_per_m=force_variation,resolved=abs(force_delta)>force_variation),
        overall_status='SCREENED, NOT A VALIDATED TOKAMAK DESIGN',numerical=numerical,effects=effects,controlled=controls,
        magnetic=core['magnetic'],vertical=core['vertical'],confinement=core['confinement'],exhaust=exhaust['exhaust'],
        representative_heat_loads=representative,engineering=eng['engineering'],thermal=read(OUT/'thermal.json'),electric=core['electric'],
        not_run=[dict(test='Wall-coupled vertical eigenmodes and feedback',reason='Wall outline has no calibrated conducting volumes, resistivity/thickness, circuit and controller model'),
                 dict(test='3-D ideal/resistive/kinetic MHD spectrum',reason='No validated 3-D MHD model or eigenmode calculation in this suite'),
                 dict(test='Predictive turbulent transport and self-consistent burn',reason='Confinement scaling and prescribed-source ODE are reduced sensitivity models'),
                 dict(test='SOL detachment and neutral recycling',reason='Field-line geometry and imposed heat distribution do not solve SOL fluid/kinetic-neutral equations'),
                 dict(test='Full structural, superconducting and cooling qualification',reason='Support CAD, material allowables/critical surfaces and cooling circuits missing'),
                 dict(test='Neutron damage and tritium breeding',reason='Material composition and 3-D blanket/shield model missing')])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Magnetic diagnostics and vertical force; raw grid curves stay visible.
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for arm,color in COLORS.items():
        for n,style in [(previous,'--'),(fine,'-')]:
            q=rows(f'{arm}-{n}-q.csv');axes[0].plot([float(x['s']) for x in q],[float(x['q']) for x in q],style,color=color,alpha=.5 if n==previous else 1,label=f'{arm}, {n}')
        v=next(x for x in core['vertical'] if x['arm']==arm)['translations'];z=[-x['step_m']*1e3 for x in v]+[0]+[x['step_m']*1e3 for x in v];F=[x['Fz_minus_N']/1e3 for x in v]+[0]+[x['Fz_plus_N']/1e3 for x in v];ind=np.argsort(z);axes[1].plot(np.array(z)[ind],np.array(F)[ind],color=color,label=arm)
    axes[0].set(xlabel='Normalized poloidal flux s',ylabel='Safety factor q',title='q profile — diagnostic only');axes[0].legend(fontsize=8)
    axes[1].axhline(0,color='#ccc',lw=1);axes[1].set(xlabel='Rigid vertical displacement (mm)',ylabel='External vertical force (kN)',title='Both slopes are destabilizing');axes[1].legend(fontsize=8)
    fig.tight_layout();figsave(fig,'magnetic-screens')
    # Actual solved ODE trajectories.
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,arm in zip(axes,COLORS):
        rr=rows(f'confinement-traces-{fine}.csv');rr=[x for x in rr if x['arm']==arm]
        for H in [.7,1.,1.3,1.6]:
            r=[x for x in rr if float(x['H_transport'])==H];ax.plot([float(x['time_s']) for x in r],[float(x['energy_MJ']) for x in r],label=f'H = {H:g}')
        W=next(x for x in core['confinement']['central'] if x['arm']==arm)['W_target_J']/1e6
        ax.axhline(W,color='#555',ls='--',label='Initial target');ax.set(xlabel='Time (s)',ylabel='Thermal energy (MJ)',title=arm);ax.legend(fontsize=8)
    fig.suptitle('Prescribed-source energy balance · radiation-subtracted H convention',fontsize=11);fig.tight_layout();figsave(fig,'confinement')
    # Wall footprints and conditional projected heat load.
    import screens as s
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for w in s.walls():axes[0].plot(w[:,0],w[:,1],color='#8c9799',lw=1)
    paths=np.load(OUT/f'fieldline-paths-{fine}.npz')
    for arm,color in COLORS.items():
        p=paths[f'{arm}_0.001'];axes[0].plot(p[:,0],p[:,1],color=color,label=arm)
        r=[x for x in representative if x['arm']==arm];axes[1].plot([float(x['SOL_radiation_fraction']) for x in r],[float(x['projected_heat_MW_m2']) for x in r],marker='o',color=color,label=arm)
    axes[0].set(xlim=(4.8,6.2),ylim=(-8.85,-7.8),xlabel='R (m)',ylabel='Z (m)',title='Outer-leg wall intercept · 1 mm upstream');axes[0].set_aspect('equal');axes[0].legend(fontsize=8)
    axes[1].axhline(10,color='#555',ls='--',label='10 MW/m² criterion');axes[1].set(yscale='log',xlabel='Assumed SOL radiation fraction',ylabel='Sampled target heat flux (MW/m²)',title='6 mm width · 25% power to this target');axes[1].legend(fontsize=8)
    fig.tight_layout();figsave(fig,'exhaust')
    # Engineering and thermal responses.
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for offset,arm in [(-.18,'baseline'),(.18,'p9-inward')]:
        er=next(e for e in eng['engineering'] if e['arm']==arm)['coils'];er=[x for x in er if not x['coil'].endswith('_r')]
        axes[0].bar(np.arange(len(er))+offset,[x['resultant_generalized_N']/1e6 for x in er],width=.36,color=COLORS[arm],label=arm)
    axes[0].set_xticks(np.arange(len(er)),[x['coil'].replace('_coil','') for x in er]);axes[0].set(ylabel='Generalized resultant (MN)',title='External coil loads · excludes self-force');axes[0].legend(fontsize=8)
    for n,style in [(40,'--'),(80,'-'),(160,':')]:
        tr=rows(f'thermal-central-{n}.csv');axes[1].plot([float(x['time_s']) for x in tr],[float(x['surface_K']) for x in tr],style,label=f'{n} cells')
    axes[1].set(xlabel='Time (s)',ylabel='Surface temperature (K)',title='Assumed slab · 10 MW/m², k = 120 W/mK');axes[1].legend(fontsize=8)
    fig.tight_layout();figsave(fig,'engineering')
    print(json.dumps(dict(grid=fine,effects=effects,controlled=controls),indent=2))
if __name__=='__main__':main()
