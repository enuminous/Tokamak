"""Export quantitative grid comparisons, with missing candidates left visible."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def main():
    data=json.loads((OUT/'summary.json').read_text());plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    metrics=[('representative_heat_MW_m2','Representative wall heat (MW/m²)',1),('H_required_transport','Required transport H',1),('near_LCFS_to_wall_m','Near-separatrix wall clearance (cm)',100),('axis_R_m','Magnetic-axis radius (m)',1)]
    colors={129:'#9b6cb4',257:'#007a78',513:'#b25c17'}
    for ax,(key,label,scale) in zip(axes.flat,metrics):
        for n in data['grids']:
            rows=sorted(data['rows_by_grid'][str(n)],key=lambda r:r['shift_m'])
            points={r['shift_m']:r for r in rows};shifts=[-.05,-.025,-.01,0,.01,.025,.05]
            x=[v*100 for v in shifts];y=[points[v][key]*scale if v in points and points[v][key] is not None else np.nan for v in shifts]
            ax.plot(x,y,'o-',color=colors[n],label=f'{n} × {2*n-1}',ms=5,lw=1.5)
        if key=='representative_heat_MW_m2':ax.axhline(10,color='#ad553b',ls=':',lw=1,label='10 MW/m² criterion')
        ax.set_xlim(-5.4,5.4);ax.set_xticks([-5,-2.5,-1,0,1,2.5,5]);ax.axvline(0,color='#abb5b5',ls=':',lw=.8);ax.set_xlabel('p9 shift (cm): outward ← 0 → inward');ax.set_ylabel(label);ax.grid(alpha=.15);ax.legend(fontsize=8)
    fig.suptitle('OPENSTEP-003 · Same pressure profile and plasma current\nRecorded equilibrium and conditional heat screens',fontsize=15)
    fig.savefig(OUT/'coil-scan.svg');fig.savefig(OUT/'coil-scan.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
    for n in [129,257]:
        rows={r['shift_m']:r for r in data['rows_by_grid'][str(n)]}
        base=rows[0.]['representative_heat_MW_m2'];xx=[-.01,0.,.01]
        yy=[rows[x]['representative_heat_MW_m2']-base if x in rows else np.nan for x in xx]
        ax.plot(np.array(xx)*100,yy,'o-',color=colors[n],label=f'{n} × {2*n-1}',lw=2)
    ax.axhline(0,color='#6d7777',ls=':',lw=1);ax.set_xticks([-1,0,1]);ax.set_xlim(-1.15,1.15)
    ax.set_xlabel('p9 movement (cm): outward ← 0 → inward')
    ax.set_ylabel('Heat change from same-grid baseline (MW/m²)')
    ax.set_title('Small coil moves: the apparent heat benefit changes sign',fontsize=13)
    ax.grid(alpha=.15);ax.legend();fig.savefig(OUT/'small-move-heat.svg');fig.savefig(OUT/'small-move-heat.png',dpi=180);plt.close(fig)

if __name__=='__main__':main()
