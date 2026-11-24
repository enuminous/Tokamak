"""Replay historical entry points in separate clean worktrees, preserving each baseline."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import monotonic

BASE = "0cb88b21e8fce6106aa3b7d352a7a7dbfc0b22b7"
ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "lab": [("node", "verify.js"), ("node", "verify-trisphere.js"), ("node", "run-trisphere.js")],
    "001": [("verify.py",)],
    "002": [("verify.py",)],
    "003": [("verify.py",)],
    "004": [("validate.py", "preflight"), ("validate.py", "controls"), ("validate.py", "equilibria")],
    "005": [("run.py",)],
    "006": [("verify.py",), ("reactor.py",)],
}

def main(stage, output):
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "baseline"
        subprocess.run(["git", "worktree", "add", "--quiet", "--detach", str(tree), BASE], cwd=ROOT, check=True)
        try:
            results = []
            for args in CASES[stage]:
                if stage == "lab":
                    cmd = list(args)
                else:
                    cmd = [sys.executable, f"benchmarks/openstep-{stage}/{args[0]}", *args[1:]]
                name = "-".join([stage, *args]).replace(".py", "").replace(".js", "")
                start = monotonic()
                with (output / (name + ".log")).open("w") as log:
                    result = subprocess.run(cmd, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
                results.append(dict(command=["python" if a == sys.executable else a for a in cmd],
                                    exit_code=result.returncode, elapsed_s=round(monotonic()-start,2),
                                    log=name+".log"))
                if result.returncode:
                    break
            if stage != "lab":
                folder = tree / f"benchmarks/openstep-{stage}/results"
                for product in ("verification", "controls", "equilibria", "reactor"):
                    path = folder / (product+".json")
                    if not path.exists():
                        continue
                    obj = json.loads(path.read_text())
                    # Fresh and historical results can coexist in a worktree.
                    # Only identify fields emitted by the invoked targets.
                    if product == "verification" and stage in {"001","002","003","005","006"}:
                        results.append({"verification_counts":{k:v for k,v in obj.items() if isinstance(v,(str,int)) and k in {"passed","failed","status","verdict"}}})
            (output/(stage+".json")).write_text(json.dumps(results,indent=2)+"\n")
            return any(r.get("exit_code",0) for r in results)
        finally:
            subprocess.run(["git","worktree","remove","--force",str(tree)], cwd=ROOT,check=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=CASES)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    raise SystemExit(main(args.stage,args.output.resolve()))
