"""Plot all cooling-screen cases from the public CSV."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def plot(folder):
    with (folder/"cases.csv").open() as handle: rows=list(csv.DictReader(handle))
    fig,axes=plt.subplots(1,2,figsize=(9.2,4.6),sharey=True,layout="constrained")
    for ax,degraded,title in zip(axes,("False","True"),("Nominal cooling","Weaker cooling for one second")):
        for shift,color in zip((-.01,0,.01,.05),("#305677","#208475","#b76810","#803c68")):
            rr=sorted((r for r in rows if r["degraded"]==degraded and float(r["shift_m"])==shift),key=lambda r:float(r["radius_m"]))
            ax.plot([1000*float(r["radius_m"]) for r in rr],[float(r["peak64_K"]) for r in rr],
                    "o-",color=color,label=f"p9 {100*shift:+.0f} cm")
        ax.axhline(1800,color="#444",linestyle="--",linewidth=1,label="1,800 K screen")
        ax.set(xlabel="Assumed corner radius (mm)",title=title,xticks=[0,1,5,10]);ax.grid(axis="y",alpha=.2)
    axes[0].set_ylabel("Peak simulated surface temperature (K)")
    axes[1].legend(fontsize=8,loc="center right")
    fig.suptitle("Same incident heat footprints, different cooling")
    fig.savefig(folder/"temperature-screen.png",dpi=150)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder",type=Path)
    plot(p.parse_args().folder)
