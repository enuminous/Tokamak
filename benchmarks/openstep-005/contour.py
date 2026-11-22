"""Implicit flux-contour charts with independent connection-length quadrature."""
import argparse
import json
import time
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq
from common import ROOT, OUT, F, OFFSETS, FrozenField, Wall, inventory, stamp, save, csvsave, check, heat


class ContourError(RuntimeError):
    pass


def project(field, level, origin, coordinate, values):
    """Solve the dependent coordinate locally, not by marching an ODE."""
    u, v = coordinate, 1-coordinate
    values = np.atleast_1d(values)
    grad = field.grad(origin)
    points = np.tile(origin, (len(values), 1))
    points[:, u] = values
    points[:, v] += -(grad[u]/grad[v])*(values-origin[u])
    tolerance = 2e-13*max(abs(field.span), 1.)
    for _ in range(15):
        error = field.sp.ev(points[:, 0], points[:, 1])-level
        if np.max(abs(error)) <= tolerance:
            return points
        derivative = field.grad(points)[:, v]
        if np.any(abs(derivative) < 1e-12):
            raise ContourError('Implicit chart derivative vanished')
        points[:, v] -= error/derivative
        if (np.any(points[:, 0] < field.r[0]) or np.any(points[:, 0] > field.r[-1]) or
                np.any(points[:, 1] < field.z[0]) or np.any(points[:, 1] > field.z[-1])):
            raise ContourError('Projection left interpolation domain')
    raise ContourError('Implicit contour root failed to converge')


def next_grid(grid, value, sign):
    candidates = grid[(grid-value)*sign > 2e-10]
    return None if len(candidates) == 0 else float(candidates[0] if sign > 0 else candidates[-1])


def trace(field, wall, offset, tight=False, direction=1):
    started = time.time()
    stepmax, order = (.01, 16) if tight else (.02, 8)
    nodes, weights = leggauss(order)
    xy = np.array([field.d['midplane_radii_m'][1]+offset, 0.])
    assert wall.signed_distance(xy) > 0, 'Launch outside wall'
    level = float(field.sp.ev(*xy))
    length = 0.
    paths = [[*xy, length]]
    flux_error, consistency, halvings = 0., 0., 0
    hit, domain_exit, error = False, False, None
    try:
        for iteration in range(20000):
            grad = field.grad(xy)
            if np.linalg.norm(grad) < 1e-10:
                raise ContourError('Critical gradient degeneracy')
            tangent = direction*np.array([-grad[1], grad[0]])
            u = int(np.argmax(abs(tangent)))
            v = 1-u
            sign = float(np.sign(tangent[u]))
            grid = field.r if u == 0 else field.z
            edge = next_grid(grid, xy[u], sign)
            if edge is None:
                domain_exit = True
                raise ContourError('Interpolation-domain edge reached')
            du = sign*min(stepmax, abs(edge-xy[u]))
            for retry in range(20):
                try:
                    end = project(field, level, xy, u, [xy[u]+du])[0]
                    sample = project(field, level, xy, u, xy[u]+du*np.array([.25, .5, .75, 1.]))
                    g = field.grad(sample)
                    if (np.any(g[:, v]*grad[v] <= 0) or
                            np.any(abs(g[:, v]) < .2*np.linalg.norm(g, axis=1)) or
                            np.max(abs(sample[:, v]-xy[v])) > 2*abs(du)+1e-10):
                        raise ContourError('Chart turning or branch-jump guard')
                    break
                except ContourError:
                    if retry == 19:
                        raise
                    du /= 2
                    halvings += 1
            # Split at a dependent-coordinate interpolation grid crossing too.
            vgrid = field.z if v == 1 else field.r
            vedge = next_grid(vgrid, xy[v], np.sign(end[v]-xy[v]))
            if vedge is not None and (vedge-xy[v])*(vedge-end[v]) < -1e-20:
                def crossing(value):
                    p = np.empty(2)
                    p[u], p[v] = value, vedge
                    return float(field.sp.ev(*p)-level)
                uedge = brentq(crossing, *sorted([xy[u], xy[u]+du]), xtol=2e-14)
                du = uedge-xy[u]
                end = project(field, level, xy, u, [uedge])[0]
            # Inspect the curve, not the chord; root the first observed crossing.
            fractions = np.unique(np.r_[0., (nodes+1)/2, .5, 1.])
            points = project(field, level, xy, u, xy[u]+du*fractions)
            distances = [wall.signed_distance(p) for p in points]
            outside = np.flatnonzero(np.asarray(distances) <= 0)
            if len(outside):
                k = int(outside[0])
                if k == 0:
                    raise ContourError('Unexpected wall at chart origin')
                def event(value):
                    return wall.signed_distance(project(field, level, xy, u, [value])[0])
                uhit = brentq(event, *sorted([points[k-1, u], points[k, u]]), xtol=2e-14)
                du = uhit-xy[u]
                end = project(field, level, xy, u, [uhit])[0]
                hit = True
            # Separate Gaussian line quadrature on this implicit chart.
            qpoints = project(field, level, xy, u, xy[u]+du*(nodes+1)/2)
            g = field.grad(qpoints)
            slope = -g[:, u]/g[:, v]
            integrand = np.sqrt(1+slope*slope)*np.sqrt(1+F*F/np.sum(g*g, axis=1))
            length += float(abs(du)*np.dot(weights, integrand)/2)
            examined = np.vstack([xy, qpoints, end])
            flux_error = max(flux_error, float(np.max(abs(field.sp.ev(examined[:, 0], examined[:, 1])-level))/abs(field.span)))
            gp = field.grad(examined)
            bp = np.array(field.bpol(examined[:, 0], examined[:, 1])).T
            expected = np.column_stack([-gp[:, 1], gp[:, 0]])/examined[:, :1]
            consistency = max(consistency, float(np.max(np.linalg.norm(bp-expected, axis=1))))
            xy = end
            paths.append([*xy, length])
            if hit:
                break
            if length > 2000:
                raise ContourError('Connection-length cap reached')
        else:
            raise ContourError('Chart-step cap reached')
    except (ContourError, ValueError) as exc:
        error = str(exc)
    result = dict(tag=field.arm, grid=field.n, offset_m=float(offset), direction=direction,
                  tight=tight, radius_m=wall.radius, success=error is None and hit, hit=hit,
                  domain_exit=domain_exit, error=error, R_target_m=float(xy[0]),
                  Z_target_m=float(xy[1]), connection_length_m=length,
                  normalized_flux_drift=flux_error, bpol_consistency_T=consistency,
                  steps=len(paths)-1, halvings=halvings, component=None, segment=None,
                  wall_distance_m=None, Bnormal_target_T=None, Bpol_upstream_T=None,
                  area_expansion=None, representative_heat_MW_m2=None,
                  seconds=time.time()-started)
    if hit:
        comp, seg, normal, distance = wall.target(xy)
        result.update(component=comp, segment=seg, wall_distance_m=distance, **heat(field, offset, xy, normal))
    return result, np.asarray(paths)


def assess(checks, label, row):
    check(checks, label+':hit', row['success'] and not row['domain_exit'])
    check(checks, label+':flux', row['normalized_flux_drift'] <= 1e-7, row['normalized_flux_drift'], 1e-7)
    check(checks, label+':wall', row['wall_distance_m'] is not None and row['wall_distance_m'] <= 1e-9,
          row['wall_distance_m'], 1e-9)
    check(checks, label+':field_consistency', row['bpol_consistency_T'] <= 1e-10,
          row['bpol_consistency_T'], 1e-10)


def compare(a, b, mirror=False):
    return dict(position_m=float(np.hypot(a['R_target_m']-b['R_target_m'], a['Z_target_m']-(-1 if mirror else 1)*b['Z_target_m'])),
                length_m=abs(a['connection_length_m']-b['connection_length_m']),
                heat_relative=abs(a['representative_heat_MW_m2']/b['representative_heat_MW_m2']-1)
                    if a['hit'] and b['hit'] else None)


def assess_difference(checks, name, difference):
    for key, limit in [('position_m', 1e-5), ('length_m', 1e-4), ('heat_relative', .001)]:
        val = difference[key]
        check(checks, name+':'+key, val is not None and val <= limit, val, limit)


def controls():
    result, checks, rows = stamp('analytic_controls'), [], []
    class Analytic:
        r = np.linspace(.5, 5.5, 51)
        z = np.linspace(-2, 2, 41)
        span, n = 1., 0
        def __init__(self, curved=False, corrupt=False):
            self.curved, self.corrupt = curved, corrupt
            self.arm = ('circle' if curved else 'straight')+('-corrupted' if corrupt else '')
            self.d = dict(midplane_radii_m=[1., 3.999 if curved else 1.999])
            self.sp = self
        def ev(self, r, z):
            return .5*((r-3.)**2+z*z) if self.curved else .5*r*r
        def grad(self, xy):
            xy = np.asarray(xy)
            return np.stack([xy[..., 0]-3. if self.curved else xy[..., 0],
                             xy[..., 1] if self.curved else np.zeros_like(xy[..., 1])], axis=-1)
        def bpol(self, r, z):
            g = self.grad(np.stack([r, z], axis=-1))
            return -g[..., 1]/r, g[..., 0]/r+(.1 if self.corrupt else 0)
    for curved in [False, True]:
        f = Analytic(curved)
        h = .6 if curved else 1.
        wall = Wall([[[1, -h], [5, -h], [5, h], [1, h], [1, -h]]])
        exact_length = (np.arcsin(.6)*np.sqrt(1+F*F) if curved else np.sqrt(1+(F/2)**2))
        for direction in [1, -1]:
            for tight in [False, True]:
                row, _ = trace(f, wall, .001, tight, direction)
                rows.append(row)
                label = f'{f.arm}:{direction}:{tight}'
                assess(checks, label, row)
                check(checks, label+':analytic_length', abs(row['connection_length_m']-exact_length) < 1e-8,
                      abs(row['connection_length_m']-exact_length), 1e-8)
                check(checks, label+':analytic_strike', abs(row['R_target_m']-(3.8 if curved else 2.)) < 1e-10)
    bad, _ = trace(Analytic(corrupt=True), Wall([[[1,-1],[5,-1],[5,1],[1,1],[1,-1]]]), .001)
    check(checks, 'corrupted_field_rejected', bad['bpol_consistency_T'] > 1e-10, bad['bpol_consistency_T'], 1e-10)
    result.update(checks=checks, rows=rows, negative_control=bad)
    save('controls.json', result)
    print(json.dumps({s: sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}), flush=True)


def physical():
    result, checks, rows, paths, comparisons = stamp('contour_traces'), [], [], {}, []
    wall = Wall()
    old = {row['tag']: row for row in json.loads((ROOT.parent/'openstep-004/results/representative-refinement.json').read_text())['rows']}
    for path, _ in inventory():
        f = FrozenField(path)
        print('Starting', f.arm, flush=True)
        for offset in OFFSETS:
            pair = []
            for tight in [False, True]:
                row, tracepath = trace(f, wall, offset, tight)
                rows.append(row)
                label = f'{f.arm}:{offset}:{tight}'
                paths[label] = tracepath
                assess(checks, label, row)
                pair.append(row)
            diff = compare(*pair)
            comparisons.append(dict(tag=f.arm, offset_m=offset, comparison='contour_refinement', **diff))
            assess_difference(checks, f'{f.arm}:{offset}:refinement', diff)
            if offset == .001:
                diff = compare(pair[1], old[f.arm])
                comparisons.append(dict(tag=f.arm, offset_m=offset, comparison='saved_third_DOP853', **diff))
                assess_difference(checks, f'{f.arm}:third_DOP853', diff)
                rev, rpath = trace(f, wall, offset, True, -1)
                rows.append(rev)
                paths[f'{f.arm}:reverse'] = rpath
                assess(checks, f'{f.arm}:reverse', rev)
                diff = compare(pair[1], rev, mirror=True)
                comparisons.append(dict(tag=f.arm, offset_m=offset, comparison='mirror', **diff))
                assess_difference(checks, f'{f.arm}:mirror', diff)
        print('Finished', f.arm, 'failures so far', sum(c['status']=='FAIL' for c in checks), flush=True)
        # Checkpoint complete fields without representing the stage as complete.
        save('contours.json', dict(**result, completed=False, rows=rows, checks=checks, comparisons=comparisons))
    result.update(completed=True, rows=rows, checks=checks, comparisons=comparisons)
    save('contours.json', result)
    csvsave('contour-traces.csv', rows)
    csvsave('contour-comparison.csv', comparisons)
    np.savez_compressed(OUT/'contour-paths.npz', **paths)
    print(json.dumps({s: sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['controls', 'physical'])
    args = parser.parse_args()
    controls() if args.stage == 'controls' else physical()
