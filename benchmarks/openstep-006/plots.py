"""Static evidence figures; all curves come from archived numerical results."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def read(n):return json.loads((OUT/(n+'.json')).read_text())
def run():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    data=np.load(OUT/'coarse-fields.npz');r=data['r'];lc=data['lc'];psi=data['psi'];geom=json.loads((ROOT/'source/DIIID_geom.json').read_text())
    for segment,eta in geom['vv']:
        p=np.array(segment);axs[0].fill(p[:,0],p[:,1],color='#8794a6',alpha=.8)
    p=np.array(geom['limiter']);axs[0].plot(p[:,0],p[:,1],color='#374151',lw=.7)
    axs[0].tricontour(r[:,0],r[:,1],lc,psi,levels=22,linewidths=.6,cmap='viridis')
    axs[0].set(xlim=(.7,2.6),ylim=(-1.8,1.8),xlabel='R (m)',ylabel='Z (m)',title='Published DIII-D model, native solution');axs[0].set_aspect('equal')
    for name,label,color in [('open-corrected-dt05','Open loop','#374151'),('feedback-pos20k','20 kA/m, ideal measurement','#0891b2'),
            ('feedback-pos100k','100 kA/m, ideal measurement','#16a34a'),('feedback-delay05ms','100 kA/m, 0.5 ms delay','#dc2626'),('feedback-delay10ms','100 kA/m, 1 ms delay','#9333ea')]:
        h=read(name)['history'];axs[1].plot([v['time_s']*1000 for v in h],[v['displacement_m']*1000 for v in h],label=label,color=color)
    axs[1].axhline(0,color='#94a3b8',lw=.7);axs[1].set(xlabel='Time (ms)',ylabel='Magnetic-axis displacement (mm)',title='Prescribed-current feedback: delay matters')
    axs[1].legend(fontsize=8);fig.suptitle('OPENSTEP-006 · Reference benchmark, not STEP hardware validation',fontsize=13)
    fig.savefig(OUT/'native-reference.png');fig.savefig(OUT/'native-reference.svg');plt.close(fig)
    from reactor import reactivity
    prof=list(csv.DictReader((OUT/'fuel-profiles.csv').open()));v=np.r_[0,[float(r['volume_m3']) for r in prof]]
    nd=np.array([float(r['D_density_m3']) for r in prof]);nt=np.array([float(r['T_density_m3']) for r in prof]);T=np.array([float(r['Ti_keV']) for r in prof])
    kin=read('reactor')['source_kinetic'];x=np.linspace(.5,2.5,401)
    pa=[]
    for z in x:
        p=nd*nt*reactivity(T*z)*3.5e6*1.602176634e-19;pa.append(np.trapezoid(np.r_[p[0],p],v))
    net=(kin['P_aux_W']+kin['P_ohmic_W']+np.array(pa)-kin['P_radiation_W']*np.sqrt(x)-kin['P_transport_W']*x)/1e6
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    axs[0].plot(x,net,color='#7c3aed',lw=2);axs[0].axhline(0,color='#64748b',lw=1);axs[0].axvline(1,color='#94a3b8',lw=1,ls='--')
    axs[0].set(xlabel='Temperature / source temperature',ylabel='Net plasma heating (MW)',title='Central reduced burn model is unstable')
    for root in read('reactor')['burn']['central_roots']:axs[0].plot(root['temperature_scale'],0,'o',color='#dc2626',label='Unstable equilibrium')
    axs[0].legend(fontsize=8)
    heat=read('reactor')['heat']['radiation_requirements'];labels=['Baseline','−1 cm','+1 cm','+5 cm'];vals=[100*r['required_SOL_radiation_fraction_for_10MW_m2'] for r in heat]
    bars=axs[1].bar(labels,vals,color=['#2563eb','#0891b2','#d97706','#dc2626']);axs[1].bar_label(bars,fmt='%.1f%%',padding=3)
    axs[1].axhline(50,color='#64748b',ls='--',label='50% assumed in source heat screen');axs[1].set(ylim=(0,105),ylabel='Required SOL radiation (%)',title='Requirement for assumed 10 MW/m² limit');axs[1].legend(fontsize=8,loc='lower left')
    fig.suptitle('Conditional STEP screens · Fixed profiles and geometry; no demonstrated detachment',fontsize=12)
    fig.savefig(OUT/'reactor-requirements.png');fig.savefig(OUT/'reactor-requirements.svg');plt.close(fig)
if __name__=='__main__':run()
