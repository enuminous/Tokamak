"""Evaluate frozen criteria and create figures from completed equilibrium runs."""
import json
import platform
from pathlib import Path
import numpy as np
from scipy.interpolate import RectBivariateSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import h5py
from benchmark import ROOT, MU0, reference, refined_critical


def load_run(name):
    report=json.loads((ROOT/'results'/f'{name}.json').read_text())
    field=dict(np.load(ROOT/'results'/f'{name}.npz'))
    return report,field


def primary_x(d):
    # The two double-null separatrix points; other vacuum critical points are retained in raw data.
    x=d['xpoints'][:2]
    return np.array(sorted(x,key=lambda p:p[1]))[:,:2]


def main():
    ref=reference()
    names={'baseline_medium':'baseline-129-symmetric','baseline_fine':'baseline-257-symmetric',
           'modified_medium':'p9-inward-129-symmetric','modified_fine':'p9-inward-257-symmetric'}
    runs={k:load_run(v) for k,v in names.items()}
    R,Z=np.meshgrid(ref['r'],ref['z'],indexing='ij')
    opt,xpt=refined_critical(R,Z,ref['psi'])
    reference_diag={'axis':opt[0],'xpoints':xpt,'ip_A':ref['ip']}
    checks=[]
    def check(name,value,limit):
        checks.append(dict(name=name,value=float(value),limit=float(limit),status='PASS' if value<=limit else 'FAIL'))
    for k,(report,_) in runs.items():
        check(k+'_nonlinear_defect',report.get('final_defect',float('inf')),1e-5)
    b=runs['baseline_fine'][0]['final'];m=runs['modified_fine'][0]['final']
    check('baseline_core_flux_nrmse',b['core_flux_nrmse'],.01)
    check('baseline_axis_error_m',np.linalg.norm(np.array(b['axis'][:2])-opt[0][:2]),.05)
    check('baseline_primary_xpoint_max_error_m',np.max(np.linalg.norm(primary_x(b)-primary_x(reference_diag),axis=1)),.1)
    check('baseline_current_relative_error',abs(b['ip_A']/ref['ip']-1),.01)
    refinement={}
    for arm in ['baseline','modified']:
        a=runs[arm+'_medium'][0]['final'];f=runs[arm+'_fine'][0]['final']
        ra=float(np.linalg.norm(np.array(a['axis'][:2])-f['axis'][:2]))
        rx=float(np.max(np.linalg.norm(primary_x(a)-primary_x(f),axis=1)))
        ri=float(abs(a['ip_A']/f['ip_A']-1))
        check(arm+'_axis_refinement_m',ra,.05)
        check(arm+'_xpoint_refinement_m',rx,.05)
        check(arm+'_current_refinement_fraction',ri,.01)
        fa=runs[arm+'_medium'][1];ff=runs[arm+'_fine'][1]
        interp=RectBivariateSpline(fa['r'],fa['z'],fa['psi'])(ff['r'],ff['z'])
        mask=ref['j']>1e3;diff=interp-ff['psi'];diff-=diff[mask].mean()
        refinement[arm]=dict(axis_m=ra,xpoint_m=rx,current_fraction=ri,
                            core_flux_nrmse=float(np.sqrt(np.mean(diff[mask]**2))/ref['span']))
    deltas={}
    for key in ['ip_A','core_volume_m3','core_area_m2','pressure_axis_Pa','pressure_integral_J']:
        changes={g:runs['modified_'+g][0]['final'][key]-runs['baseline_'+g][0]['final'][key] for g in ['medium','fine']}
        numerical_bound=sum(abs(runs[a+'_fine'][0]['final'][key]-runs[a+'_medium'][0]['final'][key]) for a in ['baseline','modified'])
        deltas[key]=dict(**changes,relative_to_baseline=changes['fine']/b[key],
                        refinement_bound=numerical_bound,resolved_vs_refinement=abs(changes['fine'])>numerical_bound)
    for key,get in [('axis_R_m',lambda d:d['axis'][0]),('upper_X_R_m',lambda d:primary_x(d)[1,0]),
                    ('upper_X_Z_m',lambda d:primary_x(d)[1,1]),
                    ('midplane_inner_R_m',lambda d:d['midplane_radii_m'][0]),
                    ('midplane_outer_R_m',lambda d:d['midplane_radii_m'][1])]:
        changes={g:float(get(runs['modified_'+g][0]['final'])-get(runs['baseline_'+g][0]['final'])) for g in ['medium','fine']}
        numerical_bound=float(sum(abs(get(runs[a+'_fine'][0]['final'])-get(runs[a+'_medium'][0]['final'])) for a in ['baseline','modified']))
        deltas[key]=dict(**changes,refinement_bound=numerical_bound,resolved_vs_refinement=abs(changes['fine'])>numerical_bound)
    source_s=(ref['psi']-ref['m']['psi_axis']/(2*np.pi))/-ref['span']
    reconstructed=R*ref['pp'](np.clip(source_s,0,1))+ref['ff'](np.clip(source_s,0,1))/(MU0*R)
    mask=ref['j']>1e3
    jerr=float(np.linalg.norm(reconstructed[mask]-ref['j'][mask])/np.linalg.norm(ref['j'][mask]))
    with h5py.File(ROOT/'source/STEP_SPP_001_EBCC_freeboundary.nc') as h:
        ncpsi=h['equilibrium/0/time_slice.profiles_2d.psi'][()].squeeze()
        convention_error=float(np.max(np.abs(ncpsi+2*np.pi*ref['psi'])))
    summary=dict(benchmark='OPENSTEP-001',date='2026-11-20',
                 reference_commit='6f66ae09c60b361d600b178416ef3f22b8d0aa6a',
                 checks=checks,numerical_status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
                 reference=reference_diag,baseline=b,modified=m,refinement=refinement,deltas=deltas,
                 inputs=dict(profile_current_nrmse=jerr,netcdf_native_flux_identity_max_error_Wb=convention_error),
                 runs=names,python=platform.python_version(),physical_confinement='NOT_APPLICABLE',
                 mhd_stability='NOT_APPLICABLE',engineering_readiness='NOT_APPLICABLE')
    (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    make_plot(ref,runs)
    print(json.dumps(summary,indent=2))


def make_plot(ref,runs):
    colors=['#77818a','#007a78','#bd651c']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
                         'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(12,9),facecolor='#fcfaf5')
    gs=fig.add_gridspec(2,2,width_ratios=[1,1.25],hspace=.36,wspace=.3)
    whole=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);pressure=fig.add_subplot(gs[1,1])
    datasets=[(ref['r'],ref['z'],ref['psi'],{'psi_axis':ref['m']['psi_axis']/(2*np.pi),'psi_boundary':ref['m']['psi_boundary']/(2*np.pi)})]
    for arm in ['baseline','modified']:
        report,f=runs[arm+'_fine'];datasets.append((f['r'],f['z'],f['psi'],report['final']))
    for i,(r,z,p,d) in enumerate(datasets):
        norm=(p-d['psi_axis'])/(d['psi_boundary']-d['psi_axis'])
        whole.contour(r,z,norm.T,levels=[1],colors=[colors[i]],linewidths=1.5,
                      linestyles=['--' if i==0 else '-'])
        # Dense evaluation of the same interpolant, for display only.
        rr=np.linspace(2.35,2.75,501);zz=np.linspace(5.9,6.35,501)
        detail.contour(rr,zz,RectBivariateSpline(r,z,norm)(rr,zz).T,levels=[1],
                       colors=[colors[i]],linewidths=1.5,linestyles=['--' if i==0 else '-'])
        if i==1:
            whole.contour(r,z,norm.T,levels=[.2,.4,.6,.8],colors=[colors[i]],linewidths=.5,alpha=.4)
    for ci in ref['c']['circuits']:
        for co in ci['coils']:
            f=co['fiesta_filament'];rr=f['r'];zz=f['z']
            width=max(np.ptp(rr),.08);height=np.ptp(zz)
            whole.add_patch(plt.Rectangle((rr.mean()-width/2,zz.mean()-height/2),width,height,fill=False,lw=1,color='#53606a'))
            if zz.mean()>0:whole.text(rr.mean()+.25,zz.mean(),ci['label'],fontsize=8,va='center')
            if ci['label']=='p9':
                whole.add_patch(plt.Rectangle((rr.mean()-width/2,zz.mean()-np.sign(zz.mean())*.1-height/2),width,height,fill=False,lw=1,color=colors[2]))
    whole.set(xlim=(.5,9),ylim=(-10,10),xlabel='R (m)',ylabel='Z (m)',title='Published coil geometry and solved flux surfaces')
    whole.set_aspect('equal');whole.grid(alpha=.15)
    for i,arm in enumerate(['baseline','modified'],start=1):
        d=runs[arm+'_fine'][0]['final'];x=primary_x(d)[1]
        err=np.abs(x-primary_x(runs[arm+'_medium'][0]['final'])[1])
        detail.errorbar(*x,xerr=err[0],yerr=err[1],fmt='x',color=colors[i],ms=9,mew=2,capsize=3)
    d0=runs['baseline_fine'][0]['final'];d1=runs['modified_fine'][0]['final']
    xs=np.stack([primary_x(d0)[1],primary_x(d1)[1]])
    detail.set(xlim=(xs[:,0].min()-.1,xs[:,0].max()+.1),ylim=(xs[:,1].min()-.12,xs[:,1].max()+.12),
               xlabel='R (m)',ylabel='Z (m)',title='Upper X-point · shift unresolved at these grids')
    detail.set_aspect('equal',adjustable='box');detail.grid(alpha=.2)
    s=np.linspace(0,1,300);integral=ref['pp'].antiderivative()
    for i,(_,_,_,d) in enumerate(datasets):
        p=(integral(1)-integral(s))*(d['psi_axis']-d['psi_boundary'])/1e6
        pressure.plot(s,p,color=colors[i],ls='--' if i==0 else '-',lw=1.8)
    pressure.set(xlabel='Normalized flux s',ylabel='Pressure (MPa)',title="Pressure integrated from the same p′(s)")
    pressure.grid(alpha=.2)
    fig.legend([Line2D([0],[0],color=c,ls='--' if i==0 else '-') for i,c in enumerate(colors)],
               ['Published Fiesta reference','Recomputed baseline','p9 coils 0.10 m toward midplane'],
               loc='upper center',bbox_to_anchor=(.5,.96),ncol=3,frameon=False)
    fig.suptitle('OPENSTEP-001 | Free-boundary equilibrium benchmark',fontsize=16,y=.995)
    fig.text(.5,.02,'Bars: medium-to-fine grid variation, not statistical intervals. Dense contours interpolate the calculated grid.\nUKAEA OpenSTEP data · CC BY 4.0 · Confinement and stability untested.',
             ha='center',fontsize=9,color='#52616a')
    fig.savefig(ROOT/'results/equilibrium-comparison.svg',bbox_inches='tight')
    fig.savefig(ROOT/'results/equilibrium-comparison.png',dpi=160,bbox_inches='tight')
    fig.canvas.draw()
    for name,ax in [('coil-section',whole),('xpoint-detail',detail),('pressure-profile',pressure)]:
        box=ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted()).expanded(1.02,1.03)
        fig.savefig(ROOT/'results'/f'{name}.svg',bbox_inches=box)


if __name__=='__main__':main()
