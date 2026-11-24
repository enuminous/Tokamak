"""An offline transfer test of pinned EXP-003 monitor code on known synthetic residuals."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.request

import numpy as np

URL="https://raw.githubusercontent.com/enuminous/EFMW-EXP-001/c955ba9bbb7339b04d6e6699f75649cda2c67ea3/EXP-003/monitors.py"
# sha256 set from inspected upstream source
EXPECTED="62f6640d09d8698d1cd1914ebab96bded2d22e338339062cbf078f94a90c4b58"

def packets(times, y, u):
    if len(times)!=100 or y.shape!=(len(times),) or u.shape!=y.shape:
        raise ValueError("Missing or extra observations")
    if not np.array_equal(times,np.arange(100)) or not np.isfinite(y).all() or not np.isfinite(u).all():
        raise ValueError("Invalid clock or sample")

def main(source,out):
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen(URL,timeout=30).read())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED:
        raise ValueError("Upstream monitor digest mismatch")
    spec=importlib.util.spec_from_file_location("exp003_monitors",source)
    monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)
    rows=[]
    for case in ("clean","bias","alternating","gap","duplicate","nonfinite"):
        times=np.arange(100);r=np.zeros(100);y=r.copy();u=r.copy()
        if case=="bias": r[30:]=1
        if case=="alternating": r[30:]=(-1.)**np.arange(70)
        for i in range(1,100): y[i]=.82*y[i-1]+r[i]
        invalid=case in ("gap","duplicate","nonfinite")
        if case=="gap": times=np.delete(times,50);y=np.delete(y,50);u=np.delete(u,50)
        if case=="duplicate": times[50]=times[49]
        if case=="nonfinite": y[50]=np.nan
        try: packets(times,y,u)
        except ValueError as exc:
            rows.append(dict(case=case,rejected=True,reason=str(exc),harness="PASS" if invalid else "FAIL"));continue
        np.testing.assert_allclose(monitor.residuals(y,u),r,atol=1e-12)
        for label,fn in (("absolute",monitor.baseline_score),("signed",monitor.efmw_score)):
            score=fn(y,u)
            onset=monitor.first_sustained_after(score,.25)
            result=("FAIL" if onset is not None else "PASS") if case=="clean" else ("PASS" if onset is not None and onset>=30 else "FAIL")
            rows.append(dict(case=case,monitor=label,alarm_sample=onset,delay_samples=onset-30 if onset is not None else None,
                             detection_verdict=result,harness="FAIL" if invalid else "PASS"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(source=URL,sha256=EXPECTED,cases=rows),indent=2)+"\n")
    print(rows)
    return any(r["harness"]!="PASS" for r in rows)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();raise SystemExit(main(a.source,a.output))
