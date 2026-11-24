"""Read-only audit of the retained release, including expected failures and case denominators."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/"benchmarks"
V=ROOT/"verification"
E=V/"evidence"
def read(path): return json.loads(path.read_text())
def sha(path):return sha256(path.read_bytes()).hexdigest()

def run():
    checks={}
    def check(name,condition):checks[name]="PASS" if condition else "FAIL"
    thermal=B/"openstep-009"
    report=read(thermal/"results/assessment.json")
    check("009 source, protocol and input digests",
          sha(thermal/"thermal.py")==report["program_sha256"] and sha(thermal/"PROTOCOL.md")==report["protocol_sha256"]
          and report["inputs"]=={p.name:sha(p) for p in (B/"openstep-005/results/footprints.json",B/"openstep-006/results/cooling-requirements.csv")})
    check("009 primary obligations",len(report["checks"])==107 and all(r["verdict"]=="PASS" for r in report["checks"]))
    with (thermal/"results/cases.csv").open() as f: cases=list(csv.DictReader(f))
    geometry={(k["tag"],k["radius_m"],k["degraded"]) for k in cases}
    cross=read(thermal/"results/crosscheck.json")
    check("009 matched cases and two samples",len(geometry)==len(cases)==len(cross)==32 and
          {tuple(r["case"]) for r in cross}==geometry and all(len(r["difference_K"]["0.002"])==2 and
          max(map(abs,r["difference_K"]["0.002"]))<=3 and r["verdict"]=="PASS" for r in cross))
    for fault,expected in (("True",7),("False",4)):
        arm=[r for r in cases if r["degraded"]==fault]
        check("009 exceedances "+fault,len(arm)==16 and sum(float(r["peak64_K"])>1800 for r in arm)==expected)
    for mesh in ("1","0.5"):
        for folder in (E/"native-008"/mesh,B/"openstep-008/record/results"/mesh):
            freeze=read(folder/"freeze.json");summary=read(folder/"summary.json")
            check(str(folder.relative_to(ROOT))+" freeze",sha(folder/"freeze.json")==read(folder/"prevalidation.json")["sha256"]
                  and all(sha(B/"openstep-008"/x)==freeze["hashes"][x] for x in ("PROTOCOL.md","run.py")))
            arms={"fixed","target"};names={"base","half-step","small-seed"}
            check(str(folder.relative_to(ROOT))+" growth",set(summary)==arms and all(
                set(v["cases"])==names and all(v[o]["verdict"]=="PASS" and v[o]["timestep_relative_change"]<=.05
                and all(c[o]["verdict"]=="PASS" and abs(c[o]["rate_per_s"]/freeze[a+"_per_s"]-1)<=.1
                        for c in v["cases"].values()) for o in ("axis","projection")) for a,v in summary.items()))
    signed=read(E/"signals.json")["cases"]
    check("alternating fault remains visible",any(r.get("monitor")=="signed" and r["case"]=="alternating" and r["detection_verdict"]=="FAIL" for r in signed))
    controls=read(E/"trace-controls.json")
    check("paired trace controls",len(controls)==8 and all(r["test"]=="PASS" for r in controls))
    data=read(E/"assurance.json")
    check("component and plant gates",len(data["synthetic_controls"])==86 and all(r["verdict"]=="PASS" for r in data["synthetic_controls"]) and data["device_qualification"]["PLANT"]=="UNRESOLVED" and data["exclusions"]["TOY"]["verdict"]=="NOT_APPLICABLE")
    browser=read(E/"browser/browser.json")["cases"]
    pages={p.stem for p in ROOT.glob("*.html")}
    check("seven views at two widths and both error paths",len(pages)==7 and {(r["page"],r["width"]) for r in browser if "width" in r}==
          {(p,w) for p in pages for w in (390,1280)} and {r["page"] for r in browser if "fixture" in r}=={"screening","coil-scan"} and
          len(browser)==16 and all(r["verdict"]=="PASS" for r in browser))
    check("historical 004 negatives retained",read(B/"openstep-004/results/summary.json")["failed"]==220)
    print(json.dumps(checks,indent=2))
    return any(state!="PASS" for state in checks.values())
if __name__=="__main__": sys.exit(run())
