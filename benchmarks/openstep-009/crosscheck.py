"""Second discretization: assemble driven heat balances directly at each step."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_banded

def integrate(q, degraded, dt):
    n=64
    dx=.005/n
    cap=2.5e6*dx/dt
    internal=120./dx
    state=np.full(n,450.)
    end=[]
    for duration,film,load in ((1.,50000.,q),(1.,10000. if degraded else 50000.,q),(3.,50000.,0.)):
        outlet=1./(dx/(2*120.)+1./film)
        bands=np.zeros((3,n))
        bands[0,1:]=-internal;bands[2,:-1]=-internal
        bands[1]=cap+2*internal
        bands[1,0]=cap+internal;bands[1,-1]=cap+internal+outlet
        source=np.zeros(n);source[0]=load;source[-1]=450.*outlet
        for _ in range(round(duration/dt)):
            state=solve_banded((1,1),bands,cap*state+source,check_finite=False)
        end.append(state[0]+load*dx/(2*120.))
    return np.array(end[1:])

def main(folder):
    with (folder/"histories.csv").open() as f: histories=list(csv.DictReader(f))
    with (folder/"cases.csv").open() as f: cases=list(csv.DictReader(f))
    results=[]
    for row in cases:
        key=[row[k] for k in ("tag","radius_m","degraded")]
        series=[h for h in histories if [h[k] for k in ("tag","radius_m","degraded")]==key]
        ref=np.array([float(next(h["surface_K"] for h in series if abs(float(h["time_s"])-t)<1e-9)) for t in (2.,5.)])
        args=float(row["heat_MW_m2"])*1e6,row["degraded"]=="True"
        delta={str(dt):list(integrate(*args,dt)-ref) for dt in (.004,.002)}
        status="PASS" if max(abs(v) for v in delta["0.002"])<=3 else "FAIL"
        if status=="FAIL": delta["0.001"]=list(integrate(*args,.001)-ref)
        results.append(dict(case=key,modal_K=list(ref),difference_K=delta,verdict=status))
    assert len(results)==len({tuple(r["case"]) for r in results})==32
    (folder/"crosscheck.json").write_text(json.dumps(results,indent=2)+"\n")
    print("Cases",len(results),"max discrepancy K",max(abs(x) for r in results for x in r["difference_K"]["0.002"]))
    return any(r["verdict"]=="FAIL" for r in results)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder",type=Path)
    raise SystemExit(main(p.parse_args().folder))
