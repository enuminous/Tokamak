"""Plot signed-pair axis growth on each mesh with completed runs."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("results", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
meshes = [m for m in ("1","0.5") if (args.results/m/"summary.json").is_file()]
fig, axes = plt.subplots(1,len(meshes),figsize=(5.4*len(meshes),4.2),sharey=True,squeeze=False)
for mesh, ax in zip(meshes, axes.ravel()):
    folder = args.results/mesh
    record = json.loads((folder/"target/half-step/grade.json").read_text())
    t = np.array(record["time_s"])[1:]
    delta_t = t-t[0]
    z = np.abs(record["centered_z_m"][1:])
    amplitude = np.abs(record["projected_flux"][1:])
    ax.plot(delta_t*1000,np.exp(record["predicted_per_s"]*delta_t),color="#242424",
            linestyle="--",label="Frozen prediction",linewidth=2.4)
    ax.plot(delta_t*1000,amplitude/amplitude[0],color="#067065",linewidth=1.4,label="Nodal flux projection")
    ax.scatter(delta_t[::3]*1000,(z/z[0])[::3],s=16,facecolor="white",edgecolor="#ad501c",
               label="Magnetic-axis height",zorder=3)
    nodes = json.loads((folder/"freeze.json").read_text())["nodes"]
    ax.set_title(f"{nodes:,} mesh nodes",loc="left")
    ax.set_xlabel("Time since first sample (ms)")
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y",alpha=.2)
axes[0,0].set_ylabel("Amplitude / first sampled amplitude")
axes[0,0].legend(loc="upper left",frameon=False)
fig.suptitle("DIII-D simulated growth with current targets active",fontsize=14)
fig.tight_layout()
fig.savefig(args.output,dpi=160,bbox_inches="tight")
