"""Compare seeded native time evolution against the corresponding DIII-D mode."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "openstep-006"
sys.path.insert(0, str(BASE))
from native import OFT_env, TokaMaker, load_gs_mesh, read_eqdsk, save


def trajectory(bounds, step, amplitude, output, fixed_profiles):
    mesh = BASE / "results/diiid-mesh-1.h5"
    points, cells, regions, coils, conductors = load_gs_mesh(str(mesh))
    eqdsk = read_eqdsk(str(BASE / "source/g192185.02440"))
    notebook = json.loads((BASE / "source/DIIID_baseline_cells.json").read_text())
    with tempfile.TemporaryDirectory(prefix="openstep007-") as scratch:
        os.chdir(scratch)
        env = OFT_env(nthreads=2, unique_tempfiles="local_dir")
        gs = TokaMaker(env)
        gs.settings.maxits = 200
        gs.setup_mesh(points, cells, regions)
        gs.setup_regions(cond_dict=conductors, coil_dict=coils)
        gs.setup(order=2, F0=eqdsk["rcentr"] * eqdsk["bcentr"])
        scope = {"mygs": gs, "eqdsk": eqdsk, "np": np}
        for index in (6, 7, 8, 9, 10, 11, 16, 17, 21):
            exec("".join(notebook[index]["source"]), scope)
        reference = gs.copy_eq()
        flux = reference.get_psi(False).copy()
        span = abs(np.diff(reference.psi_bounds)[0])
        currents, _ = gs.get_coil_currents()
        eigenvalues, modes = gs.compute_linear_stability(5000, 10, bounds)
        unstable = np.flatnonzero((eigenvalues.real > 0) & (abs(eigenvalues.imag) < 1e-8))
        index = unstable[np.argmax(eigenvalues.real[unstable])]
        growth = float(eigenvalues.real[index])
        mode = modes[index].copy()
        mode /= mode[np.argmax(abs(mode))]
        dt = step / growth

        gs.settings.pm = False
        gs.update_settings()
        gs.set_isoflux_constraints(None)
        if fixed_profiles:
            gs.set_targets()
        else:
            gs.set_targets(Ip=eqdsk["ip"], Ip_ratio=5.6)
        gs.set_psi(flux + amplitude * span * mode, update_bounds=True)
        gs.setup_td(dt, 1e-13, 1e-11, pre_plasma=False)
        times = [0.0]
        fields = [gs.get_psi(False).copy()]
        retries = []
        for _ in range(round(1 / step)):
            time, _, _, _, retry = gs.step_td(times[-1], dt, coil_currents=currents)
            times.append(time)
            fields.append(gs.get_psi(False).copy())
            retries.append(retry)
        np.savez_compressed(output, times=times, fields=fields, mode=mode,
                            growth=growth, retries=retries)


def grade(positive, negative):
    with np.load(positive) as p, np.load(negative) as n:
        if not np.allclose(p["times"], n["times"], rtol=1e-9, atol=0):
            raise RuntimeError("Positive and negative trajectories have different time grids")
        if not np.allclose(p["mode"], n["mode"], rtol=1e-8, atol=1e-10) or not np.isclose(p["growth"], n["growth"], rtol=1e-9):
            raise RuntimeError("Positive and negative trajectories have different reference modes")
        if np.any(p["retries"]) or np.any(n["retries"]):
            raise RuntimeError("A solver retry changed the declared integration")
        centered = (p["fields"] - n["fields"]) / 2
        mode = p["mode"]
        times = p["times"]
        growth = float(p["growth"])
        amplitude = centered @ mode / (mode @ mode)
        orthogonal = centered - amplitude[:, None] * mode
        leakage = np.linalg.norm(orthogonal, axis=1) / np.linalg.norm(centered, axis=1)
        fitted = float(np.polyfit(times[1:], np.log(abs(amplitude[1:])), 1)[0])
        error = abs(fitted / growth - 1)
        return dict(eigenvalue_per_s=growth, fitted_per_s=fitted, relative_error=error,
                    verdict="PASS" if error <= .10 else "FAIL", max_orthogonal_fraction=max(leakage),
                    time_s=times, projected_amplitude=amplitude, orthogonal_fraction=leakage)


def main(output, fixed_profiles):
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    cases = [(True, .05, 5e-4), (True, .025, 5e-4), (True, .05, 5e-5)]
    if not fixed_profiles:
        cases.append((False, .05, 5e-4))
    for bounds, step, seed in cases:
        name = f"bounds-{int(bounds)}-step-{step:g}-seed-{seed:g}"
        paths = []
        for sign in (1, -1):
            path = output / f"{name}-{sign:+d}.npz"
            with path.with_suffix(".log").open("w") as log:
                subprocess.run([sys.executable, __file__, "--trajectory", str(int(bounds)),
                                str(step), str(sign * seed), str(path)]
                               + (["--fixed-profiles"] if fixed_profiles else []),
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            paths.append(path)
        results[name] = grade(*paths)
        save(output / "comparison.json", results)
        print(name, {k: results[name][k] for k in ("eigenvalue_per_s", "fitted_per_s",
                                                   "relative_error", "verdict")}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "results")
    parser.add_argument("--fixed-profiles", action="store_true")
    parser.add_argument("--trajectory", nargs=4, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.trajectory:
        bounds, step, amplitude, output = args.trajectory
        trajectory(bool(int(bounds)), float(step), float(amplitude), Path(output).resolve(), args.fixed_profiles)
    else:
        main(args.output.resolve(), args.fixed_profiles)
