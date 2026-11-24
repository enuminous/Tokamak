"""Verify signed fields and aggregate OPENSTEP-008 using its frozen criteria."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np


def load(path):
    return json.loads(path.read_text())


def check_mesh(folder):
    freeze = load(folder / "freeze.json")
    fingerprint = hashlib.sha256((folder/"freeze.json").read_bytes()).hexdigest()
    with np.load(folder / "modes.npz") as data:
        modes = {key: data[key] for key in ("target", "fixed")}
    out = {}
    for arm, mode in modes.items():
        obs = {"projection": [], "axis": []}
        cases = {}
        for name in ("base", "half-step", "small-seed"):
            loc = folder / arm / name
            rec = load(loc / "grade.json")
            assert rec["freeze_sha256"] == fingerprint
            with np.load(loc/"positive.npz") as p, np.load(loc/"negative.npz") as n:
                times = p["times"]
                np.testing.assert_array_equal(times, n["times"])
                np.testing.assert_allclose(np.diff(times), rec["dt_s"], rtol=1e-9, atol=0)
                for item in (p, n):
                    assert (item["iterations"][:,2] == 0).all()
                centered = (p["fields"] - n["fields"]) * .5
                projection = centered @ mode / np.dot(mode, mode)
                z = (p["height"]-n["height"]) * .5
                resid = np.linalg.norm(centered-np.outer(projection,mode),axis=1)/np.linalg.norm(centered,axis=1)
            for key, series in (("projected_flux",projection),("centered_z_m",z),("orthogonal_fraction",resid)):
                np.testing.assert_allclose(series, rec[key], rtol=1e-8, atol=1e-12)
            row = {"max_shape_fraction": float(max(resid)), "steps":len(times)-1,
                   "z_first_m":float(z[1]), "z_last_m":float(z[-1])}
            for label, vals in (("projection", projection), ("axis", z)):
                if rec[label]["verdict"] == "UNRESOLVED":
                    obs[label].append(None)
                    row[label] = rec[label]
                    continue
                rate = statistics.linear_regression(times[1:], np.log(abs(vals[1:]))).slope
                assert abs(rate-rec[label]["rate_per_s"]) < 1e-6
                error = abs(rate/freeze[arm+"_per_s"]-1)
                assert rec[label]["verdict"] == ("PASS" if error <= .1 else "FAIL")
                row[label] = rec[label]
                obs[label].append(rate)
            cases[name] = row
        grades = {}
        for key,rates in obs.items():
            if None in rates:
                grades[key] = {"verdict":"UNRESOLVED"}
                continue
            refinement = abs(rates[0]/rates[1] - 1)
            passed = refinement <= .05 and all(case[key]["verdict"]=="PASS" for case in cases.values())
            grades[key] = {"verdict":"PASS" if passed else "FAIL", "timestep_relative_change":refinement}
        out[arm] = {"predicted_per_s":freeze[arm+"_per_s"], "cases":cases, **grades}
    return out


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mesh", choices=["1","0.5"], required=True)
    args = parser.parse_args()
    folder = args.output / args.mesh
    summary = check_mesh(folder)
    (folder/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    for arm,values in summary.items():
        print(arm,values["projection"],values["axis"])
