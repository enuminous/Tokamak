"""Compare paired traces using an externally frozen, digest-bound SI contract."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path, unit):
    with path.open() as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=["time_s","value_"+unit]: raise ValueError("wrong columns or unit")
        data=[(float(r["time_s"]),float(r["value_"+unit])) for r in reader]
    if len(data)<2 or any(not all(map(math.isfinite,p)) for p in data):raise ValueError("missing or invalid samples")
    if any(a[0]>=b[0] for a,b in zip(data,data[1:])):raise ValueError("non-increasing time")
    return data

def compare(folder, contract):
    try:
        if contract["quantity"] not in {"surface_temperature":"K","axis_height":"m"} or contract["unit"]!={"surface_temperature":"K","axis_height":"m"}[contract["quantity"]]:
            raise ValueError("unknown physical quantity/unit")
        if contract["evidence_class"] not in {"fixture","measurement"}:raise ValueError("unknown evidence class")
        if not all(isinstance(contract[k],str) and contract[k].strip() for k in ("device","configuration","channel","clock","calibration","criterion_source")):
            raise ValueError("missing context")
        amplitude=contract["absolute_error_limit"];clock=contract["clock_tolerance_s"]
        if any(isinstance(x,bool) or not math.isfinite(x) or x<0 for x in (amplitude,clock)):raise ValueError("invalid allocation")
        n=contract["expected_samples"]
        if type(n) is not int or n<2:raise ValueError("invalid denominator")
        arrays=[]
        for role in ("forecast","observation"):
            f=folder/(role+".csv");ref=contract[role+"_sha256"]
            if digest(f)!=ref:raise ValueError(role+" digest mismatch")
            arrays.append(read_csv(f,contract["unit"]))
        a,b=arrays
        if len(a)!=n or len(b)!=n:raise ValueError("incomplete sample coverage")
        if max(abs(x[0]-y[0]) for x,y in zip(a,b))>clock:raise ValueError("unmatched clocks")
        err=max(abs(x[1]-y[1]) for x,y in zip(a,b))
        return {"verdict":"PASS" if err<=amplitude else "FAIL","evidence_class":contract["evidence_class"],
                "samples":n,"max_absolute_error":err,"unit":contract["unit"],"scope":"numerical agreement only"}
    except (KeyError,OSError,ValueError,TypeError) as e:
        return {"verdict":"UNRESOLVED","reason":str(e)}

def controls():
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp);a=p/"forecast.csv";b=p/"observation.csv"
        clean="time_s,value_K\n0,450\n1,500\n2,550\n"
        a.write_text(clean)
        contract=dict(quantity="surface_temperature",unit="K",evidence_class="fixture",device="synthetic slab",configuration="fixture A",
                      channel="surface",clock="fixture tick",calibration="synthetic unit test",criterion_source="fixture",
                      expected_samples=3,absolute_error_limit=2.,clock_tolerance_s=.01,forecast_sha256=digest(a))
        for label,data,expected in (
            ("known offset inside limit",clean.replace("500","501"),"PASS"),("known offset above limit",clean.replace("500","503"),"FAIL"),
            ("clock shifted",clean.replace("1,500","1.2,500"),"UNRESOLVED"),("wrong unit",clean.replace("_K","_C"),"UNRESOLVED"),
            ("omitted endpoint",clean.rsplit("2,550",1)[0],"UNRESOLVED"),("nonfinite",clean.replace("500","nan"),"UNRESOLVED"),
            ("duplicate tick",clean.replace("1,500","0,500"),"UNRESOLVED"),("tampered bytes",clean,"UNRESOLVED")):
            b.write_text(data);c={**contract,"observation_sha256":digest(b)}
            if label=="tampered bytes": b.write_text(data.replace("500","499"))
            actual=compare(p,c);results.append(dict(fixture=label,expected=expected,actual=actual,
                                                     test="PASS" if actual["verdict"]==expected else "FAIL"))
    return results

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures",action="store_true");p.add_argument("path",type=Path)
    args=p.parse_args()
    if args.fixtures:
        rows=controls();args.path.write_text(json.dumps(rows,indent=2)+"\n")
        raise SystemExit(any(r["test"]!="PASS" for r in rows))
    result=compare(args.path.parent,json.loads(args.path.read_text()))
    print(json.dumps(result,indent=2));raise SystemExit({"PASS":0,"FAIL":1,"UNRESOLVED":2}[result["verdict"]])
