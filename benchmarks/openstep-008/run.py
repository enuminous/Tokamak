"""OPENSTEP-008. Run on Linux with OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import traceback
from importlib.metadata import version

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "openstep-006"
sys.path.insert(0, str(BASE))
from native import OFT_env, TokaMaker, load_gs_mesh, read_eqdsk, save

PRED_STEP = 2e-4
PROBE = 2.5e-6
STEP = .05 / 807.7026822838
CASES = [("base", STEP, 5e-4), ("half-step", STEP/2, 5e-4), ("small-seed", STEP, 5e-5)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def construct(scale):
    mesh = BASE / "results" / f"diiid-mesh-{scale}.h5"
    shot = BASE / "source/g192185.02440"
    cells = BASE / "source/DIIID_baseline_cells.json"
    points, triangles, regions, coils, conductors = load_gs_mesh(str(mesh))
    eq = read_eqdsk(str(shot))
    gs = TokaMaker(OFT_env(nthreads=1, unique_tempfiles="local_dir"))
    gs.settings.maxits = 200
    gs.setup_mesh(points, triangles, regions)
    gs.setup_regions(cond_dict=conductors, coil_dict=coils)
    gs.setup(order=2, F0=eq["rcentr"] * eq["bcentr"])
    scope = dict(mygs=gs, eqdsk=eq, np=np)
    notebook = json.loads(cells.read_text())
    for i in (6, 7, 8, 9, 10, 11, 16, 17, 21):
        exec("".join(notebook[i]["source"]), scope)
    currents, _ = gs.get_coil_currents()
    flux = gs.get_psi(False).copy()
    span = float(abs(np.diff(gs.psi_bounds)[0]))
    gs.settings.pm = False
    gs.update_settings()
    gs.set_isoflux_constraints(None)
    return gs, flux, span, currents, eq["ip"], {p.name: digest(p) for p in (mesh, shot, cells)}


def sign_normalize(x):
    return x / x[np.argmax(abs(x))]


def trajectory(gs, flux, span, currents, vector, amplitude, dt, count, path, probe=False):
    # A separate copy-on-write process starts from exactly the same native state for each sign.
    # OFT and BLAS must be single-threaded before this fork. Native work files are used serially.
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        try:
            gs.set_psi(flux + amplitude * span * vector, update_bounds=True)
            gs.setup_td(dt, 1e-14 if probe else 1e-13, 1e-13 if probe else 1e-11, pre_plasma=False)
            fields, heights, times = [gs.get_psi(False).copy()], [float(gs.o_point[1])], [0.]
            iterations = []
            for _ in range(count):
                t, used, nl, lin, retry = gs.step_td(times[-1], dt, coil_currents=currents)
                if retry or abs(t - times[-1] - dt) > 1e-8 * dt or abs(used-dt) > 1e-8*dt:
                    raise ValueError(f"Invalid native step {t=} {used=} {dt=} {retry=}")
                fields.append(gs.get_psi(False).copy())
                heights.append(float(gs.o_point[1]))
                times.append(t)
                iterations.append((nl, lin, retry))
            np.savez(path, fields=fields, height=heights, times=times, iterations=iterations)
            os._exit(0)
        except BaseException:
            traceback.print_exc()
            os._exit(1)
    _, status = os.waitpid(pid, 0)
    if status:
        raise RuntimeError(f"Native trajectory failed with wait status {status}")


def predict(gs, flux, span, currents, fixed_mode, folder):
    def tangent(vector, size):
        peak = np.max(abs(vector))
        outputs = []
        for sign in (1, -1):
            path = Path.cwd() / "probe.npz"
            trajectory(gs, flux, span, currents, vector/peak, sign*size, PRED_STEP, 1, path, probe=True)
            with np.load(path) as data:
                outputs.append(data["fields"][-1])
        return (outputs[0] - outputs[1]) * (peak / (2*size*span))

    basis = np.zeros((len(flux), 19), order="F")
    basis[:, 0] = fixed_mode / np.linalg.norm(fixed_mode)
    h = np.zeros((19, 18))
    history = []
    for k in range(18):
        q = basis[:, :k+1]
        w = tangent(q[:, k], PROBE)
        for _ in range(2):
            correction = q.T @ w
            h[:k+1, k] += correction
            w -= q @ correction
        h[k+1, k] = np.linalg.norm(w)
        if h[k+1, k] > 1e-14:
            basis[:, k+1] = w/h[k+1, k]
        vals, vecs = np.linalg.eig(h[:k+1, :k+1])
        candidates = np.flatnonzero((abs(vals.imag) < 1e-7) & (vals.real > 1))
        row = dict(vectors=k+1, spectrum_real=vals.real, spectrum_imag=vals.imag)
        history.append(row)
        if len(candidates):
            i = candidates[np.argmax(vals.real[candidates])]
            mu = float(vals.real[i])
            gamma = (1-1/mu)/PRED_STEP
            v = sign_normalize(q @ vecs[:, i].real)
            row.update(rate=gamma, multiplier=mu)
            if k >= 5:
                y = tangent(v, PROBE/2)
                residual = np.linalg.norm(y-mu*v)/np.linalg.norm(y)
                mu_half = float(v @ y / (v @ v))
                rate_half = (1-1/mu_half)/PRED_STEP
                row.update(half_probe_rate=rate_half, residual=residual)
                print("KRYLOV", k+1, gamma, residual, rate_half, flush=True)
                if residual <= .001 and abs(rate_half/gamma-1) <= .02:
                    save(folder / "krylov.json", history)
                    return gamma, v
        save(folder / "krylov.json", history)
        if h[k+1, k] <= 1e-14:
            break
    raise RuntimeError("UNRESOLVED: targeted tangent eigenpair failed probe checks")


def fit_signal(times, values, gamma, floor):
    series = np.asarray(values)[1:]
    if (not np.isfinite(series).all() or np.min(abs(series)) <= floor
            or np.any(np.sign(series) != np.sign(series[0]))):
        return dict(verdict="UNRESOLVED")
    fitted = float(np.polyfit(times[1:], np.log(abs(series)), 1)[0])
    err = abs(fitted/gamma - 1)
    return dict(rate_per_s=fitted, relative_error=err, verdict="PASS" if err <= .1 else "FAIL")


def verify_freeze(folder):
    freeze = json.loads((folder / "freeze.json").read_text())
    for name, sha in freeze["hashes"].items():
        path = HERE / name if name in ("run.py", "PROTOCOL.md") else folder / name
        if digest(path) != sha:
            raise ValueError(f"Frozen bytes changed: {name}")
    return freeze


def main(args):
    folder = args.output.resolve() / args.mesh
    folder.mkdir(parents=True, exist_ok=True)
    if args.stage == "predict" and (folder / "freeze.json").exists():
        raise FileExistsError("Use an empty output directory for a new prediction")
    gs, flux, span, currents, ip, inputs = construct(args.mesh)
    if args.stage == "predict":
        rates, modes = gs.compute_linear_stability(5000, 10, True)
        valid = np.flatnonzero((rates.real > 0) & (abs(rates.imag) < 1e-8))
        ix = valid[np.argmax(rates.real[valid])]
        fixed_rate = float(rates.real[ix])
        fixed_mode = sign_normalize(modes[ix])
        gs.set_targets(Ip=ip, Ip_ratio=5.6)
        rate, mode = predict(gs, flux, span, currents, fixed_mode, folder)
        np.savez_compressed(folder/"modes.npz", target=mode, fixed=fixed_mode, baseline_flux=flux)
        paths = [HERE/"PROTOCOL.md", HERE/"run.py", folder/"modes.npz", folder/"krylov.json"]
        save(folder/"freeze.json", dict(target_per_s=rate, fixed_per_s=fixed_rate,
             mesh=args.mesh, nodes=len(flux), flux_span=span, Ip_A=ip, current_ratio=5.6,
             inputs=inputs, hashes={p.name: digest(p) for p in paths},
             python=platform.python_version(), platform=platform.platform(),
             versions={n: version(n) for n in ("OpenFUSIONToolkit", "numpy", "scipy", "h5py")}))
        print("FROZEN", args.mesh, rate, fixed_rate, flush=True)
        return
    frozen = verify_freeze(folder)
    if inputs != frozen["inputs"]:
        raise ValueError("Mesh or input has changed since freeze")
    gamma = frozen[args.arm+"_per_s"]
    with np.load(folder/"modes.npz") as data:
        mode = data[args.arm].copy()
        if np.max(abs(data["baseline_flux"]-flux))/span > 1e-8:
            raise ValueError("Equilibrium replay differs from prediction")
    if args.arm == "target":
        gs.set_targets(Ip=ip, Ip_ratio=5.6)
    else:
        gs.set_targets()
    name, dt, size = next(case for case in CASES if case[0] == args.case)
    count = int(np.floor(1/(dt*gamma) + 1e-8))
    if count < 3:
        raise ValueError("Insufficient samples per e-fold")
    location = folder / args.arm / name
    location.mkdir(parents=True, exist_ok=True)
    for sign, label in ((1,"positive"), (-1,"negative")):
        trajectory(gs, flux, span, currents, mode, sign*size, dt, count, location/(label+".npz"))
    with np.load(location/"positive.npz") as pos, np.load(location/"negative.npz") as neg:
        times = pos["times"]
        if not np.array_equal(times, neg["times"]):
            raise ValueError("Unequal signed time grids")
        centered = (pos["fields"]-neg["fields"])/2
        projection = centered @ mode/(mode@mode)
        orth = centered - projection[:, None]*mode
        leakage = np.linalg.norm(orth, axis=1)/np.linalg.norm(centered, axis=1)
        z = (pos["height"]-neg["height"])/2
        summary = dict(arm=args.arm, case=name, dt_s=dt, steps=count, seed=size, predicted_per_s=gamma,
                   freeze_sha256=digest(folder/"freeze.json"), time_s=times,
                   projected_flux=projection, orthogonal_fraction=leakage, centered_z_m=z,
                   axis_plus_m=pos["height"], axis_minus_m=neg["height"],
                   iterations_plus=pos["iterations"], iterations_minus=neg["iterations"],
                   projection=fit_signal(times, projection, gamma, 1e-12*span),
                   axis=fit_signal(times, z, gamma, 1e-12))
        save(location/"grade.json", summary)
        print("GRADED", args.mesh, args.arm, name, summary["projection"], summary["axis"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["predict", "validate"])
    parser.add_argument("--mesh", choices=["1", "0.5"], default="1")
    parser.add_argument("--arm", choices=["target", "fixed"], default="target")
    parser.add_argument("--case", choices=[x[0] for x in CASES], default="base")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output = arguments.output.resolve()
    if os.environ.get("OPENBLAS_NUM_THREADS") != "1" or os.environ.get("OMP_NUM_THREADS") != "1":
        parser.error("Set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1 before starting Python")
    with tempfile.TemporaryDirectory(prefix="openstep008-") as scratch:
        os.chdir(scratch)
        main(arguments)
