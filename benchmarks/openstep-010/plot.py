"""Plot the completed local controls using only the saved trace table."""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
root=Path(__file__).resolve().parent
with (root/'results/pair-comparison.csv').open() as f:
    rows={(r['case'],r['mesh']):r for r in csv.DictReader(f) if r['solver']=='local'}
fig,(left,right)=plt.subplots(1,2,figsize=(9.6,4.1),gridspec_kw={'width_ratios':[1.4,1]},layout='constrained')
colors={'baseline':'#286483','inward':'#a44725'}
for i,(grid,symbol) in enumerate([('coarse','s'),('fine','o')]):
    for case in colors:
        r=rows[case,grid];x=float(r['signed_corner_m'])*1000;heat=float(r['model_heat_MW_m2'])
        left.scatter(x,i,color=colors[case],marker=symbol,s=55,zorder=3)
        left.annotate(f'{x:+.2f}',(x,i),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
        right.scatter(heat,i,color=colors[case],marker=symbol,s=55,zorder=3)
        right.annotate(f'{heat:.2f}',(heat,i),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
for ax in (left,right):
    ax.set_ylim(-.45,1.6);ax.set_yticks([0,1],['129 × 257','257 × 513'])
    ax.spines[['right','left','top']].set_visible(False); ax.grid(axis='x',color='#dddddd');ax.tick_params(axis='y',length=0)
left.axvline(0,color='#333333',lw=1);left.set_xlim(-78,17);left.set_xlabel('Signed distance along the wall (mm)');left.set_title('Strike relative to the corner',loc='left',fontsize=12,weight='bold')
right.set_xlim(0,68);right.set_xlabel('Representative projected heat flux (MW/m²)');right.set_title('Identical heat mapping',loc='left',fontsize=12,weight='bold')
for k,label in [('baseline','Baseline'),('inward','p9 inward 5 cm')]:
    left.scatter([],[],s=45,color=colors[k],label=label)
left.legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.01),fontsize=8)
left.set_title('Strike relative to the corner',loc='left',fontsize=12,weight='bold',pad=26)
fig.savefig(root/'results/strike-comparison.png',dpi=170)
