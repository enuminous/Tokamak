"""Replay OPENSTEP-008 on fresh output, including the conditional fine mesh."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main(output, workers, use_coarse_freeze):
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for mesh in ("1", "0.5"):
        folder = output / mesh
        folder.mkdir(exist_ok=True)
        def run(script, args, log):
            with (folder / log).open("x") as handle:
                subprocess.run([sys.executable, str(HERE/script), *args],
                               stdout=handle, stderr=subprocess.STDOUT, env=env, check=True)
        common = ["--mesh", mesh, "--output", str(output)]
        if not (use_coarse_freeze and mesh == "1"):
            run("run.py", ["predict", *common], "predict.log")
        frozen = folder / "freeze.json"
        record = {"observed_utc_before_validation":datetime.now(timezone.utc).isoformat(),
                  "sha256":hashlib.sha256(frozen.read_bytes()).hexdigest()}
        with (folder/"prevalidation.json").open("x") as file:
            json.dump(record, file, indent=2)
        def validate(case):
            arm, size = case
            run("run.py", ["validate", *common, "--arm", arm, "--case", size], f"{arm}-{size}.log")
        cases = [(arm, size) for arm in ("target","fixed") for size in ("base","half-step","small-seed")]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(validate, cases))
        run("assess.py", [str(output), "--mesh", mesh], "assess.log")
        grade = json.loads((folder/"summary.json").read_text())["target"]["projection"]["verdict"]
        print(f"Mesh {mesh}, targeted projection {grade}", flush=True)
        if grade != "PASS":
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, choices=[1,2,3], default=2)
    parser.add_argument("--use-coarse-freeze", action="store_true",
                        help="Continue directly after the coarse prediction has been written.")
    args = parser.parse_args()
    main(args.output.resolve(), args.workers, args.use_coarse_freeze)
