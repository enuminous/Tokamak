"""One-dimensional transient conduction under archived STEP footprint scenarios."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import eigh_tridiagonal

HERE = Path(__file__).resolve().parent
FLUX = HERE.parent / "openstep-005/results/footprints.json"
REFERENCE = HERE.parent / "openstep-006/results/cooling-requirements.csv"
K, LENGTH, CAPACITY, BULK = 120., .005, 2.5e6, 450.
CASES = {"shift-+000mm-257":0., "shift--010mm-257":-.01,
         "inward-010mm-257":.01, "inward-050mm-257":.05}
RADII = (0., .001, .005, .01)

def validate(records):
    flux = {}
    for row in records:
        point = row["optimized_maximum"]
        key = (row["tag"], row["radius_m"])
        heat = point["representative_heat_MW_m2"]
        if (key in flux or CASES.get(key[0]) != row["shift_m"] or
                key != (point["tag"], point["radius_m"]) or point["shift_m"] != row["shift_m"]
                or not math.isfinite(heat) or heat <= 0):
            raise ValueError(f"Invalid heat input {key}")
        flux[key] = heat
    if set(flux) != set(itertools.product(CASES, RADII)):
        raise ValueError("Incomplete or unexpected geometry grid")
    return flux

def interval(temperatures, q, h, duration, k=K, depth=LENGTH, capacity=CAPACITY):
    """Temperatures above bulk in cell centers; flux is positive into the loaded face."""
    if not all(math.isfinite(x) and x > 0 for x in (h,k,depth,capacity,duration)):
        raise ValueError("Nonpositive or nonfinite slab data")
    if not math.isfinite(q) or not np.isfinite(temperatures).all():
        raise ValueError("Nonfinite heat or state")
    n = len(temperatures)
    dx = depth/n
    cell_capacity = capacity*dx
    conductance = k/dx
    outlet = 1/(.5*dx/k + 1/h)
    diagonal = np.full(n,-2*conductance)
    diagonal[0] = -conductance
    diagonal[-1] = -(conductance+outlet)
    ev, vec = eigh_tridiagonal(diagonal/cell_capacity,np.full(n-1,conductance/cell_capacity))
    x = (np.arange(n)+.5)*dx
    steady = q*(1/h + (depth-x)/k)
    weights = vec.T @ (temperatures-steady)
    times = np.linspace(0,duration,round(duration/.01)+1)
    states = steady + (np.exp(np.outer(times,ev))*weights) @ vec.T
    face = BULK + states[:,0] + q*dx/(2*k)
    energy_in = q*duration
    removed = outlet*(steady[-1]*duration + np.dot(weights*vec[-1],np.expm1(ev*duration)/ev))
    stored = cell_capacity*sum(states[-1]-temperatures)
    residual = abs(energy_in-removed-stored)/max(1.,abs(energy_in),abs(removed),abs(stored))
    return states[-1], times, face, residual

def simulate(n, q, degraded):
    state = np.zeros(n)
    time, faces, residuals = [], [], []
    elapsed = 0.
    for heat, h, seconds in ((q,5e4,1.),(q,1e4 if degraded else 5e4,1.),(0.,5e4,3.)):
        state, t, face, residual = interval(state,heat,h,seconds)
        time.extend(t+elapsed)
        faces.extend(face)
        residuals.append(residual)
        elapsed += seconds
    crossing = next((float(t) for t,v in zip(time,faces) if v>1800), None)
    return max(faces),crossing,max(residuals),time,faces

def write_csv(path, rows):
    with path.open("w",newline="") as output:
        writer=csv.DictWriter(output,fieldnames=rows[0],lineterminator="\n");writer.writeheader();writer.writerows(rows)

def main(output):
    output.mkdir(parents=True, exist_ok=True)
    records=json.loads(FLUX.read_text())["summaries"]
    flux=validate(records)
    with REFERENCE.open() as file:
        steady_refs={r["tag"]:float(r["surface_K"]) for r in csv.DictReader(file)
                     if (float(r["k_W_m_K"]),float(r["thickness_m"]),float(r["h_W_m2_K"]))==(K,LENGTH,5e4)}
    checks, rows, traces = [],[],[]
    def check(name, ok, value=None):
        checks.append(dict(test=name,verdict="PASS" if ok else "FAIL",value=value))
    for label, fixture in (("missing key",records[1:]),("duplicate key",records+[records[0]]),
                           ("wrong sign",[{**records[0],"shift_m":.05},*records[1:]]),
                           ("NaN heat",[{**records[0],"optimized_maximum":{**records[0]["optimized_maximum"],"representative_heat_MW_m2":float("nan")}},*records[1:]])):
        try: validate(fixture)
        except ValueError: check("reject "+label,True)
        else: check("reject "+label,False)
    try: interval(np.zeros(16),1.,0.,1.)
    except ValueError: check("reject zero film coefficient",True)
    else: check("reject zero film coefficient",False)
    check("zero flux",abs(simulate(32,0.,False)[0]-BULK)<1e-7)
    for (tag,radius), heat in flux.items():
        q=heat*1e6
        if radius==0:
            steady=BULK+q*(1/5e4+LENGTH/K)
            check(tag+" sharp 006 steady reference",abs(steady-steady_refs[tag])<1e-6,steady)
        n=32
        x=(np.arange(n)+.5)*LENGTH/n
        init=q*(1/5e4+(LENGTH-x)/K)
        _,_,face,_=interval(init,q,5e4,1.)
        check(f"{tag} {radius} stationary slab",np.max(abs(face-(BULK+q*(1/5e4+LENGTH/K))))<1e-6)
        peaks=[]
        for degraded in (False,True):
            results=[simulate(n,q,degraded) for n in (16,32,64)]
            peak,crossing,_,t,face=results[-1]
            diff=abs(peak-results[1][0])
            residual=max(r[2] for r in results)
            label=f"{tag} {radius} degraded={degraded}"
            check(label+" energy balance",residual<=1e-8,residual)
            check(label+" refinement",diff<=2,diff)
            row=dict(tag=tag,shift_m=CASES[tag],radius_m=radius,degraded=degraded,heat_MW_m2=heat,
                     peak16_K=results[0][0],peak32_K=results[1][0],peak64_K=peak,
                     first_sample_above_1800_s=crossing,max_relative_energy_error=residual)
            if diff>2: row["diagnostic128_K"]=simulate(128,q,degraded)[0]
            rows.append(row);peaks.append(peak)
            traces.extend(dict(tag=tag,radius_m=radius,degraded=degraded,time_s=time,surface_K=temp)
                          for time,temp in zip(t,face) if abs(time*10-round(time*10))<1e-8)
        check(f"{tag} {radius} fault ordering", peaks[1]>=peaks[0]-1e-6)
    check("case denominator",len(rows)==32,len(rows))
    for row in rows: row.setdefault("diagnostic128_K",None)
    write_csv(output/"cases.csv",rows);write_csv(output/"histories.csv",traces)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(protocol_sha256=digest(HERE/"PROTOCOL.md"),program_sha256=digest(Path(__file__)),
                inputs={p.name:digest(p) for p in (FLUX,REFERENCE)},checks=checks,
                exceeding={str(d):sum(r["degraded"]==d and r["first_sample_above_1800_s"] is not None for r in rows) for d in (False,True)})
    (output/"assessment.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(len(checks),"checks;",sum(r["verdict"]=="FAIL" for r in checks),"failures;",result["exceeding"])
    return any(r["verdict"]=="FAIL" for r in checks)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path)
    raise SystemExit(main(parser.parse_args().output))
