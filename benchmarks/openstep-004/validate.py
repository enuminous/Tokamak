"""Independent numerical routes on immutable OPENSTEP-003 fields.

Shares the flux representation/profile source with earlier experiments. Does
not independently validate physics or model an evolving plasma/conducting wall.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np
from scipy.integrate import solve_ivp
from shapely.geometry import Point, Polygon, LineString

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
OLD = ROOT.parent / 'openstep-003'
OUT = ROOT / 'results'
sys.path.insert(0, str(OLD))
from screen_sweep import Field, b, s
from controlled import Controlled

OFFSETS = [.001, .002, .005, .01, .02]
PARENT = '2438abacf652478ec7865b3ce1fce5d17ad8ab1c'
FVAC = 11.52


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def csvsave(name, rows):
    if not rows:
        return
    with (OUT / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check(checks, name, ok, value=None, limit=None):
    checks.append(dict(name=name, status='PASS' if bool(ok) else 'FAIL',
                       value=value, limit=limit))


def inventory():
    rows = []
    for n in [129, 257]:
        recorded = json.loads((OLD / f'results/screens-{n}.json').read_text())
        for row, inp in zip(recorded['rows'], recorded['input_fingerprint']['fields']):
            path = ROOT.parent / inp['path']
            assert path.stem == row['tag']
            assert sha(path) == inp['sha256']
            assert sha(path.with_suffix('.json')) == inp['report_sha256']
            rows.append((path, row))
    assert len(rows) == 8
    return rows


def stamp(stage):
    return dict(stage=stage, parent_commit=PARENT,
                started_utc=datetime.now(timezone.utc).isoformat(),
                code_sha256=sha(__file__), protocol_sha256=sha(ROOT / 'PROTOCOL.md'))


class Wall:
    def __init__(self, shapes):
        self.shapes = [np.asarray(w, dtype=float) for w in shapes]
        self.polygons = [Polygon(w) for w in self.shapes]
        self.lines = [LineString(w) for w in self.shapes]
        assert all(p.is_valid for p in self.polygons)
        self.segments = []
        for component, w in enumerate(self.shapes):
            for index, (lo, hi) in enumerate(zip(w[:-1], w[1:])):
                delta = hi - lo
                if np.linalg.norm(delta) > 1e-12:
                    self.segments.append((component, index, lo, delta,
                                          LineString([lo, hi])))

    def signed_distance(self, xy):
        p = Point(float(xy[0]), float(xy[1]))
        values = [self.lines[0].distance(p) * (1 if self.polygons[0].covers(p) else -1)]
        values += [line.distance(p) * (-1 if poly.contains(p) else 1)
                   for line, poly in zip(self.lines[1:], self.polygons[1:])]
        return min(values)

    def target(self, xy):
        p = Point(float(xy[0]), float(xy[1]))
        comp, idx, lo, delta, line = min(self.segments, key=lambda v: v[4].distance(p))
        normal = np.array([-delta[1], delta[0]]) / np.linalg.norm(delta)
        return comp, idx, normal, float(line.distance(p))


def trace(field, wall, offset, tight=False, direction=1):
    """Adaptive integration in phi; wall hit is a continuous ODE event."""
    rup = field.d['midplane_radii_m'][1] + offset
    initial = [rup, 0., 0.]
    assert wall.signed_distance(initial[:2]) > 0, 'Launch outside open wall region'

    def rhs(phi, y):
        r, z, _ = y
        br, bz = field.bpol(r, z)
        dr = r * r * br / FVAC
        dz = r * r * bz / FVAC
        return [direction * dr, direction * dz, np.sqrt(r * r + dr * dr + dz * dz)]

    def hit(phi, y):
        return wall.signed_distance(y[:2])
    hit.terminal = True
    hit.direction = -1

    def edge(phi, y):
        r, z, _ = y
        return min(r-field.r[0], field.r[-1]-r, z-field.z[0], field.z[-1]-z)
    edge.terminal = True
    edge.direction = -1

    sol = solve_ivp(rhs, (0, 200), initial, method='DOP853', events=[hit, edge],
                    rtol=1e-11 if tight else 1e-9,
                    atol=[1e-12, 1e-12, 1e-10] if tight else [1e-10, 1e-10, 1e-8],
                    max_step=.05 if tight else .1, dense_output=True)
    end = sol.y[:, -1]
    # Include dense midpoints, not just accepted integration endpoints.
    t = np.sort(np.r_[sol.t, (sol.t[1:] + sol.t[:-1]) / 2])
    points = sol.sol(t).T
    flux = field.sp.ev(points[:, 0], points[:, 1])
    drift = float(np.max(abs(flux-flux[0])) / abs(field.span))
    result = dict(tag=field.arm, grid=field.n, offset_m=float(offset),
                  direction=direction, tight=tight, success=bool(sol.success),
                  hit=bool(len(sol.t_events[0])), domain_exit=bool(len(sol.t_events[1])),
                  R_target_m=float(end[0]), Z_target_m=float(end[1]),
                  connection_length_m=float(end[2]), phi_end_rad=float(sol.t[-1]),
                  normalized_flux_drift=drift, evaluations=sol.nfev,
                  component=None, segment=None, wall_distance_m=None,
                  Bnormal_target_T=None, Bpol_upstream_T=None, area_expansion=None)
    if result['hit']:
        comp, seg, normal, distance = wall.target(end[:2])
        br, bz = field.bpol(end[0], end[1])
        bn = abs(float(br*normal[0]+bz*normal[1]))
        br0, bz0 = field.bpol(rup, 0.)
        bpu = float(np.hypot(br0, bz0))
        result.update(component=comp, segment=seg, wall_distance_m=distance,
                      Bnormal_target_T=bn, Bpol_upstream_T=bpu, area_expansion=bpu/bn)
    return result, np.column_stack([t, points])


def heat(row, field, power):
    if not row['hit']:
        return None
    x = row['offset_m']
    rup = field.d['midplane_radii_m'][1] + x
    return float(.25*power*.5*np.exp(-x/.006)/(2*np.pi*rup*.006*row['area_expansion'])/1e6)


def difference(a, c):
    return dict(position_m=float(np.hypot(a['R_target_m']-c['R_target_m'],
                                         a['Z_target_m']-c['Z_target_m'])),
                length_m=abs(a['connection_length_m']-c['connection_length_m']),
                heat_relative=abs(a['representative_heat_MW_m2']/c['representative_heat_MW_m2']-1))


def check_trace(checks, label, row):
    check(checks, label+':hit', row['success'] and row['hit'] and not row['domain_exit'])
    check(checks, label+':flux', row['normalized_flux_drift'] <= 1e-7,
          row['normalized_flux_drift'], 1e-7)
    check(checks, label+':wall_event', row['wall_distance_m'] is not None and row['wall_distance_m'] <= 1e-9,
          row['wall_distance_m'], 1e-9)


def controls():
    result = stamp('controls')
    checks = []
    class UniformFlux:
        def __init__(self, inconsistent=False):
            self.inconsistent = inconsistent
        def ev(self, r, z):
            return .5*np.asarray(r)**2 + (.1*np.asarray(z) if self.inconsistent else 0)
    class UniformField:
        arm = 'analytic-uniform'
        n = 0
        r = np.array([.5, 4.])
        z = np.array([-2., 2.])
        span = 1.
        d = {'midplane_radii_m': [1., 1.999]}
        sp = UniformFlux()
        def bpol(self, r, z):
            return 0., 1.
    f = UniformField()
    wall = Wall([[[1, -1], [3, -1], [3, 1], [1, 1], [1, -1]]])
    traces = []
    length = float(np.sqrt(1+(FVAC/2)**2))
    for direction in [1, -1]:
        row, _ = trace(f, wall, .001, direction=direction)
        check_trace(checks, f'analytic:{direction}', row)
        err = float(np.hypot(row['R_target_m']-2, row['Z_target_m']-direction))
        check(checks, f'analytic:{direction}:exact_position', err < 1e-9, err, 1e-9)
        err = abs(row['connection_length_m']-length)
        check(checks, f'analytic:{direction}:exact_length', err < 1e-8, err, 1e-8)
        traces.append(row)
    f.sp = UniformFlux(True)
    row, _ = trace(f, wall, .001)
    check(checks, 'negative_control:inconsistent_flux_rejected',
          row['normalized_flux_drift'] > 1e-7, row['normalized_flux_drift'], 1e-7)
    result.update(checks=checks, analytic_traces=traces, inconsistent_trace=row)
    save('controls.json', result)
    print('Controls:', sum(c['status']=='PASS' for c in checks), '/', len(checks), flush=True)
    if any(c['status']=='FAIL' for c in checks):
        raise SystemExit(1)


def preflight():
    result = stamp('preflight')
    checks = []
    manifest = json.loads((OLD/'artifact-manifest.json').read_text())
    actual = []
    for row in manifest['files']:
        path = REPO/row['path']
        content = path.read_bytes()
        gitsha = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        check(checks, row['path'], gitsha == row['git_blob_sha'] and sha(path) == row['sha256'])
        actual.append(dict(path=row['path'], sha256=sha(path), git_blob_sha=gitsha))
    manifest_path = OLD/'artifact-manifest.json'
    expected_manifest = '"UNSET"'
    # Manifest itself is pinned by the published Git blob recorded in inputs.json.
    pins = json.loads((ROOT/'inputs.json').read_text())
    content = manifest_path.read_bytes()
    gitsha = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    check(checks, 'parent_manifest_blob', gitsha == pins['parent_manifest_blob'], gitsha, pins['parent_manifest_blob'])
    import scipy, freegs, shapely
    result.update(checks=checks, inputs=actual,
                  environment=dict(python=sys.version, platform=platform.platform(),
                                   numpy=np.__version__, scipy=scipy.__version__,
                                   freegs=freegs.__version__, shapely=shapely.__version__))
    save('preflight.json', result)
    print('Preflight:', sum(c['status']=='PASS' for c in checks), '/', len(checks), flush=True)
    if any(c['status']=='FAIL' for c in checks):
        raise SystemExit(1)


def equilibria():
    result = stamp('equilibria')
    checks, rows = [], []
    target = json.loads((b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
    span = target['psi_axis']-target['psi_boundary']
    for path, prior in inventory():
        start = time.time()
        f = Field(path)
        ref = b.reference()
        pro = Controlled(ref, span, target['ip_A'])
        eq = b.prepare(ref, f.n, f.report['p9_translation_m'])
        assert eq._applyBoundary.__name__ == 'freeBoundaryHagenow'
        eq._updatePlasmaPsi(f.plasma.copy())
        eq.solve(pro, psi=eq.psi())
        defect = float(np.max(abs(eq.plasma_psi-f.plasma))/ref['span'])
        check(checks, f.arm+':uncached_full_domain_residual', defect <= 1e-5, defect, 1e-5)
        negative = None
        if f.n == 129 and f.report['p9_translation_m'] == 0:
            perturbed = f.plasma + .01*ref['span']*np.exp(-((f.R-4)**2+f.Z**2)/.5)
            eq._updatePlasmaPsi(perturbed)
            eq.solve(Controlled(ref, span, target['ip_A']), psi=eq.psi())
            negative = float(np.max(abs(eq.plasma_psi-perturbed))/ref['span'])
            check(checks, 'negative_control:perturbed_equilibrium_rejected', negative > 1e-5, negative, 1e-5)
        select = abs(f.j) > 1e-9
        rr, zz, jj = f.R[select], f.Z[select], f.j[select]
        machine = b.machine(ref, f.report['p9_translation_m'])
        def force(dz):
            return float(np.sum(-2*np.pi*rr*jj*machine.Br(rr, zz+dz))*f.da)
        zero = force(0.)
        slopes = []
        for h in [.001, .005]:
            minus, plus = force(-h), force(h)
            slopes.append(dict(step_m=h, minus_N=minus, plus_N=plus,
                               stiffness_N_per_m=(plus-minus)/(2*h)))
        k = slopes[0]['stiffness_N_per_m']
        ratio = abs(k/prior['vertical_stiffness_N_per_m']-1)
        step = abs(slopes[1]['stiffness_N_per_m']/k-1)
        check(checks, f.arm+':analytic_coil_force_agreement', ratio <= .01, ratio, .01)
        check(checks, f.arm+':analytic_force_step', step <= .001, step, .001)
        check(checks, f.arm+':analytic_zero_force', abs(zero) <= 1., zero, 1.)
        rows.append(dict(tag=f.arm, grid=f.n, shift_m=f.report['p9_translation_m'],
                         field_sha256=sha(path), uncached_defect=defect,
                         recorded_defect=f.report['final_defect'], perturbed_control_defect=negative,
                         force_zero_N=zero, force_steps=slopes, stiffness_N_per_m=k,
                         force_relative_difference=ratio, force_step_relative_difference=step,
                         seconds=time.time()-start))
        result.update(checks=checks, rows=rows)
        save('equilibria.json', result)
        print(f'Equilibrium {f.arm}: defect {defect:.3g}, direct force difference {ratio:.3g}, {time.time()-start:.1f}s', flush=True)


def tracing():
    result = stamp('tracing')
    checks, rows, comparisons, dense, symmetry = [], [], [], [], []
    paths = {}
    wall = Wall(s.walls())
    power = json.loads((ROOT.parent/'openstep-002/results/kinetic-inputs.json').read_text())['P_transport_W']
    old = []
    for n in [129, 257]:
        old.extend(csv.DictReader((OLD/f'results/fieldline-traces-{n}.csv').open()))
    for path, prior in inventory():
        start = time.time()
        f = Field(path)
        cached = {}
        for offset in OFFSETS:
            pair = []
            for tight in [False, True]:
                row, points = trace(f, wall, offset, tight=tight)
                row['representative_heat_MW_m2'] = heat(row, f, power)
                rows.append(row)
                check_trace(checks, f'{f.arm}:{offset}:{tight}', row)
                pair.append(row)
                if tight:
                    paths[f'{f.arm}_{offset}'] = points
                else:
                    cached[offset] = row
            if all(r['hit'] for r in pair):
                delta = difference(*pair)
                check(checks, f'{f.arm}:{offset}:adaptive_tightening',
                      delta['position_m'] <= 1e-5 and delta['length_m'] <= 1e-4 and delta['heat_relative'] <= .001,
                      delta, dict(position_m=1e-5, length_m=1e-4, heat_relative=.001))
                prev = next(r for r in old if r['arm']==f.arm and float(r['upstream_offset_m'])==offset and float(r['step_m'])==.005)
                prev = {key: float(prev[key]) for key in ['R_target_m', 'Z_target_m', 'connection_length_m', 'area_expansion']}
                prev.update(hit=True, offset_m=offset)
                prev['representative_heat_MW_m2'] = heat(prev, f, power)
                delta = difference(pair[1], prev)
                check(checks, f'{f.arm}:{offset}:old_RK4_agreement',
                      delta['position_m'] <= .001 and delta['length_m'] <= .01 and delta['heat_relative'] <= .005,
                      delta, dict(position_m=.001, length_m=.01, heat_relative=.005))
                comparisons.append(dict(tag=f.arm, grid=f.n, shift_m=f.report['p9_translation_m'], offset_m=offset,
                                        **delta, adaptive_heat_MW_m2=pair[1]['representative_heat_MW_m2'],
                                        previous_heat_MW_m2=prev['representative_heat_MW_m2']))
        back, points = trace(f, wall, .001, tight=True, direction=-1)
        back['representative_heat_MW_m2'] = heat(back, f, power)
        rows.append(back)
        paths[f'{f.arm}_reverse'] = points
        check_trace(checks, f.arm+':reverse', back)
        forward = next(r for r in rows if r['tag']==f.arm and r['offset_m']==.001 and r['tight'] and r['direction']==1)
        if back['hit'] and forward['hit']:
            reflected = dict(back, Z_target_m=-back['Z_target_m'])
            delta = difference(forward, reflected)
            check(checks, f.arm+':mirror_trace', delta['position_m'] <= 1e-5 and delta['length_m'] <= 1e-4 and delta['heat_relative'] <= .001,
                  delta, dict(position_m=1e-5, length_m=1e-4, heat_relative=.001))
            symmetry.append(dict(tag=f.arm, **delta))
        if f.n == 257:
            offsets = sorted(set(np.geomspace(.00025, .02, 33).tolist()+OFFSETS))
            nested = set(np.geomspace(.00025, .02, 33)[::2].tolist())
            for offset in offsets:
                if offset in cached:
                    row = dict(cached[offset])
                else:
                    row, _ = trace(f, wall, offset)
                    row['representative_heat_MW_m2'] = heat(row, f, power)
                dense.append(dict(row, in_17=offset in nested,
                                  in_33=offset in set(np.geomspace(.00025, .02, 33).tolist())))
                check_trace(checks, f'{f.arm}:dense:{offset:.12g}', row)
        result.update(checks=checks, trace_count=len(rows), dense_samples=len(dense), comparisons=comparisons, symmetry=symmetry)
        save('tracing.json', result)
        csvsave('adaptive-traces.csv', rows)
        csvsave('dense-footprints.csv', dense)
        csvsave('tracer-comparison.csv', comparisons)
        np.savez_compressed(OUT/'adaptive-paths.npz', **paths)
        print(f'Traced {f.arm}: {len(rows)} core traces and {len(dense)} dense samples saved; {time.time()-start:.1f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['preflight', 'controls', 'equilibria', 'tracing'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    globals()[args.stage]()


if __name__ == '__main__':
    main()
