"""Evaluate qualification prerequisites. Synthetic controls never enter the plant record."""
import argparse
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
# A graph of evidence required by a claim, not a causal or power-flow diagram.
GRAPH={
    "PLASMA": "EQ MHD WALL PCS DIS BURN RF DIAG",
    "EXHAUST": "EDGE TARGET COOL VAC FUEL DIAG",
    "MAGNETS": "TF PF JOINT QUENCH CRYO ELEC",
    "FUELCYCLE": "FUEL BLANKET SHIELD TPLANT VAC",
    "GENERATION": "BURN BLANKET COOL HEAT ELEC GRID",
    "FACILITY": "VESSEL SERVICE FAC OPS PROTECT DIAG ELEC",
    "MODEL": "INGEST SOLVE TRACE NATIVE TRANSPORT THERMAL BUDGET WEB SIGNAL CONFIG DECISION",
    "PLANT": "PLASMA EXHAUST MAGNETS FUELCYCLE GENERATION FACILITY MODEL",
}
GRAPH={k:v.split() for k,v in GRAPH.items()}

def inventory():
    ids=[]
    for line in (HERE/"COMPONENTS.md").read_text().splitlines():
        if line.startswith("| "):
            fields=[c.strip() for c in line.strip("|").split("|")]
            if fields[0]=="ID": continue
            if len(fields)!=6 or not all(fields) or fields[0] in ids:
                raise ValueError(f"Incomplete or duplicate component {fields}")
            ids.append(fields[0])
    return ids

def evaluate(graph, leaves):
    if set(graph)&set(leaves): raise ValueError("A claim cannot be its own input record")
    cache={}
    def visit(node, ancestors):
        if node in ancestors: raise ValueError("Dependency cycle at "+node)
        if node in cache: return cache[node]
        if node in graph:
            deps=graph[node]
            if not deps or len(set(deps))!=len(deps): raise ValueError("Empty/duplicate dependency")
            states=[visit(dep,ancestors|{node}) for dep in deps]
            result="FAIL" if "FAIL" in states else "UNRESOLVED" if "UNRESOLVED" in states else "PASS"
        else:
            if node not in leaves: raise ValueError("Missing dependency "+node)
            result=leaves[node]
            if result not in {"PASS","FAIL","UNRESOLVED"}: raise ValueError("Required component cannot be waived")
        cache[node]=result
        return result
    for node in graph: visit(node,set())
    return cache

def main(out):
    ids=inventory()
    essential=set(ids)-{"TOY"} # Standalone analogy and propulsion ledger outside plant design.
    assert essential=={d for deps in GRAPH.values() for d in deps if d not in GRAPH}
    actual={k:"UNRESOLVED" for k in essential} # Actual device-level qualification or device-specific software release.
    controls=[]
    green={k:"PASS" for k in essential}
    def record(name,condition): controls.append({"case":name,"verdict":"PASS" if condition else "FAIL"})
    record("synthetic fully evidenced plant",evaluate(GRAPH,green)["PLANT"]=="PASS")
    for component in sorted(essential):
        for status in ("FAIL","UNRESOLVED"):
            got=evaluate(GRAPH,{**green,component:status})
            record(component+" "+status,got["PLANT"]==status and all(got[g]==(status if component in deps else "PASS") for g,deps in GRAPH.items() if g!="PLANT"))
    for name,graph,leaves in (
        ("cycle",{**GRAPH,"PLASMA":["PLANT"]},green),
        ("missing leaf",GRAPH,{k:v for k,v in green.items() if k!="DIAG"}),
        ("duplicate prerequisite",{**GRAPH,"PLASMA":["EQ","EQ"]},green),
        ("empty gate",{**GRAPH,"EXHAUST":[]},green),
        ("waived required sensor",GRAPH,{**green,"DIAG":"NOT_APPLICABLE"}),
    ):
        try: evaluate(graph,leaves)
        except ValueError: record(name,True)
        else: record(name,False)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(device_qualification=evaluate(GRAPH,actual),
        exclusions={"TOY":{"verdict":"NOT_APPLICABLE","reason":"TriSphere and the speculative propulsion ledger are outside the power-plant design."}},
        dependencies=GRAPH,synthetic_controls=controls),indent=2,sort_keys=True)+"\n")
    print(len(ids),"components;",len(controls),"synthetic graph checks")
    return any(r["verdict"]!="PASS" for r in controls)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path)
    raise SystemExit(main(parser.parse_args().output))
